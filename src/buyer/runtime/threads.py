"""Play one case with every supplier thread at once.

The kit's `play()` sends one message at a time and waits for that reply (up to about a minute);
meanwhile the other threads of an RFQ run past their 60 s and time out. Here every supplier thread
has its own worker and its own clock; all workers share one `CaseState` (every thread, so the
policy can cite a rival's offer), and the first accept or walk-away closes the case for all.

The agent (see `agent.py`) is shared by the workers of a case and called concurrently:
  decide(case, threads, supplier_id) -> {"supplier_id", "message"[, "trace"]}
      the next move in this supplier's thread; `threads` is a snapshot of every thread.
      "trace" (optional, any JSON) is logged as a "decision" event and never sent.
  closing(case, threads) -> {"supplier_id", "message"}   (optional; default: the kit's closing_move)
      what to do when the wave's cap is near. The runtime decides *when*; the Analyst decides *what*.

Per move: the decision should take < DECIDE_BUDGET_S. If it has not come back HOLD_AT_S after the
supplier's reply, the worker sends a holding message without term sheets (no numbers invented, the
quote stands) instead of letting the thread time out, and drops the late decision. The same holding
message covers an agent that raises or a message the arena refuses (422); after MAX_FAILURES in a
row the worker stops playing that thread. A 409 or a network failure: the worker asks the arena
what the thread now says and plays on from there.

Network outages (`_recover`): when an e-mail fails after the client's own retries (or a 409 / 5xx),
the worker keeps asking the arena - pauses growing from RECOVER_PAUSE_S[0] to [1] - until it
answers, then plays on from the thread as the arena has it, with the arena's clock (`seconds_left`).
Our e-mail arrived: its reply is taken, never sent twice. It never arrived and the thread is
unchanged: the same e-mail is sent again, at most MAX_RESENDS times. Bounded: the worker gives up
the thread (`drop`) if the arena stays out of reach past the wave's cap + AFTER_CAP_S (without a
cap: RECOVER_MAX_S); every attempt waits at least the pause, so a permanent fault never spins.

A walk-away while other bidders are still live only stops this worker (walking away would end the
whole case); the last live thread's walk-away ends it.

Closing (accept or walk away) is supervised until the arena confirms the end:
  - `closing` (an attempt is in flight) and `ended` (the arena said so: a result in the reply, or
    GET /sessions/{sid} reports `ended`) are separate. While an attempt is in flight no worker sends
    a new offer; workers stop for good only on `ended`.
  - After any failed or unanswered attempt - 422 (e.g. a stale term sheet), 409, a network error
    with the response lost - the runtime asks the arena (`_reconcile`). Ended: take its result, never
    act again. Still open: re-read every live thread and try again with a fresh closing decision.
    If even that question fails, the next attempt asks first: never two terminal actions without
    the arena's answer in between.
  - The watchdog keeps trying near the cap until the case has ended (the arena ends it at the cap);
    when every worker has stopped, `play` supervises the close the same way.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from arena_kit.client import ArenaError
from arena_kit.docs import read_document
from arena_kit.play import (
    CLOSE_BEFORE_CAP_S,
    ENDED,
    MOVE_LIMIT_S,
    ROUND_MARGIN_S,
    RemoteTable,
    closing_move,
    latest,
    moves_left,
)

from .log import NullLog, archive_session

log = logging.getLogger("buyer.threads")

DECIDE_BUDGET_S = 25  # AGENTS.md: every move inside 25 s of the supplier's reply
HOLD_AT_S = 48  # still no decision: send the holding message (the arena's limit is 60 s)
WATCH_EVERY_S = 1.0
DOWNLOADS = 4  # attachment downloads at once per case
MAX_FAILURES = 2  # the agent failing (or its messages refused) this often in a row: stop playing the thread
INVALID = "invalid"
CLOSE_RETRY_S = 1.0  # between closing attempts after a failed one
MAX_CLOSE_ATTEMPTS = 5  # without a wave cap (practice, sandbox): give up supervising after this many
AFTER_CAP_S = 30.0  # past the wave's cap the arena has ended the case: confirm it, then stop
RECOVER_PAUSE_S = (1.0, 4.0)  # network down: first and longest pause between two attempts to reach the arena
RECOVER_MAX_S = 300.0  # without a wave cap: give the thread up after this long out of reach (3 timeouts = 180 s)
MAX_RESENDS = 1  # an e-mail the arena never received is sent again (thread unchanged) at most this often
# What the arena says after a failed e-mail (`_recover`):
LANDED, LOST, CHANGED, PENDING, ENDED_CASE, UNREACHABLE = "landed", "lost", "changed", "pending", "ended", "unreachable"
HOLD_BODY = (
    "Thank you for your message. We are reviewing it internally and will come back to you with our "
    "position shortly.\n\nBest regards\nHollerau Pumpenwerke, Purchasing"
)


class CaseState:
    """Everything the workers of one case share. All access under `lock`."""

    def __init__(self, case, threads):
        self.case, self.threads = case, threads
        self.lock = threading.Lock()
        self.ended = threading.Event()  # the arena confirmed the end (a result, or GET session: ended)
        self.closing = threading.Event()  # an accept / walk-away is in flight: no new offers meanwhile
        self.unconfirmed = False  # a terminal action may have landed but the arena's answer is unknown
        self.retry_at = 0.0  # monotonic: no new closing attempt before this
        self.result = None
        self.closed = set()  # threads the arena has closed (timeouts, walked away, no bid)
        self.replied_at = {sid: time.monotonic() for sid in threads}  # our 60 s run from here
        self.slowest = 0.0  # longest round so far, any thread: decision + supplier reply
        self.texts = {}  # attachment_id -> text, so refreshed threads keep their documents
        self.pending = {}  # attachment_id -> attachment dicts waiting for its text (download running)
        self.inflight = set()  # threads with a message of ours on its way (the worker records the reply)

    def snapshot(self):
        with self.lock:
            return {sid: list(ev) for sid, ev in self.threads.items()}

    def live(self, sid):
        with self.lock:
            return sid not in self.closed and latest(self.threads[sid]).get("status") not in ENDED

    def live_threads(self):
        return [sid for sid in self.threads if self.live(sid)]


class CasePlayer:
    def __init__(
        self, client, case_id, agent, *, case=None, deadline=None, log=None, hold_at=HOLD_AT_S, run=None, archive=None
    ):
        self.client, self.case_id, self.agent, self.run = client, case_id, agent, run or {}
        self.archive, self.case_file = archive, case  # archive: a folder for one JSON file per ended session
        self.table = RemoteTable(client, case)  # with the case file, a final 409 resumes the running session
        self.deadline, self.log, self.hold_at = deadline, log or NullLog(), hold_at
        self.state = None
        self._close_lock = threading.Lock()
        self._decide_pool = self._docs_pool = None
        self._stopped = threading.Event()  # play() is done: the watchdog stops

    # -- the case -------------------------------------------------------------------------------
    def play(self):
        case, threads = self.table.open(self.case_id)
        self.case_file = case or self.case_file
        self.log.bind(self.table.session_id)
        self.log("case", case_id=self.case_id, session_id=self.table.session_id, case=case, run=self.run)
        if self.table.done:  # resumed a case that had already ended
            return self._finish(self.table.done)
        self.state = s = CaseState(case, threads)
        for sid, events in threads.items():  # the opening quotes: before any thread plays, so wait for them
            for m in events:
                self._documents(m, sid, wait=True)
        self.log("opening", threads=threads)
        self._clocks()
        workers = list(threads)
        # A decision that came back too late keeps running; don't wait for it at the end.
        self._decide_pool = ThreadPoolExecutor(max_workers=len(workers) * 2, thread_name_prefix="decide")
        self._docs_pool = ThreadPoolExecutor(max_workers=DOWNLOADS, thread_name_prefix="docs")
        try:
            threading.Thread(target=self._watch, daemon=True, name=f"cap-{self.case_id}").start()
            with ThreadPoolExecutor(max_workers=len(workers), thread_name_prefix="thread") as pool:
                for f in [pool.submit(self._worker, sid) for sid in workers]:
                    try:
                        f.result()
                    except Exception as e:  # one broken thread must not stop the case
                        log.exception("%s: a thread crashed", self.case_id)
                        self.log("error", detail=e)
            self._supervise_close("no thread left to play")  # every worker stopped: see the case to its end
        finally:
            self._stopped.set()
            self._decide_pool.shutdown(wait=False, cancel_futures=True)
            self._docs_pool.shutdown(wait=True)  # the case is over: the arena answers these at once now
        return self._finish(s.result or self.table.result())

    def _clocks(self):
        """Each thread's 60 s as the arena counts them (`seconds_left`) - after a crash and a resume
        part of them is gone - and the threads it has already closed."""
        s = self.state
        try:
            state = self.client.session(self.table.session_id)
        except Exception as e:
            self.log("error", detail=e, where="session state at start")
            return
        now, resumed = time.monotonic(), any(m.get("from") == "buyer" for ev in s.threads.values() for m in ev)
        with s.lock:
            for sid, th in (state.get("threads") or {}).items():
                if sid not in s.replied_at:
                    continue
                if th.get("seconds_left") is not None:
                    s.replied_at[sid] = now - max(0.0, MOVE_LIMIT_S - th["seconds_left"])
                if th.get("closed"):
                    s.closed.add(sid)
        if resumed:
            self.log("resumed", threads=state.get("threads"))

    def _finish(self, result):
        self.log("result", result=result)
        sid = self.table.session_id
        for kind, get in (("session", self.client.session), ("backoffice", self.client.backoffice)):
            try:
                self.log(kind, data=get(sid))
            except ArenaError as e:  # backoffice: 403 in the final until it is over
                self.log(kind, error={"status": e.status, "detail": e.detail})
            except Exception as e:
                self.log(kind, error=str(e))
        if self.archive:
            try:
                path = archive_session(self.client, sid, self.case_file or {}, self.archive, self.run)
                self.log("archived", path=str(path))
            except Exception as e:  # the JSONL log still has everything
                log.exception("%s: archiving session %s failed", self.case_id, sid)
                self.log("error", detail=e, where="archive")
        return result

    # -- one supplier thread --------------------------------------------------------------------
    def _worker(self, sid):
        s, failures, close_failures = self.state, 0, 0  # close_failures: not reset by a fresh decision
        while not s.ended.is_set() and s.live(sid):
            if s.closing.is_set():  # an accept / walk-away is in flight: no new offer until it is settled
                s.ended.wait(WATCH_EVERY_S / 5)
                continue
            view = s.snapshot()
            if self._cap_near():
                if self._close_now("the wave's cap is near"):
                    return
                if self._past_cap():  # the arena has ended the case at its cap; play() confirms it
                    self.log("drop", supplier_id=sid, reason="the wave's cap has passed")
                    return
                s.ended.wait(CLOSE_RETRY_S)  # not closed (yet): the arena's state is re-read, try again
                continue
            t0 = s.replied_at[sid]
            try:
                decision = self._decide(view, sid, t0)
            except Exception as e:  # a bug in the agent: hold this round, give up the thread if it repeats
                failures += 1
                log.exception("%s %s: the agent failed (%d in a row)", self.case_id, sid, failures)
                self.log("error", supplier_id=sid, detail=e, where="decide")
                if failures >= MAX_FAILURES:
                    self.log("drop", supplier_id=sid, reason="the agent failed repeatedly")
                    return
                decision = None
            else:
                failures = 0 if decision else failures
            if s.ended.is_set():
                return
            if s.closing.is_set():  # a close started while this decision was made: it would race with it
                continue
            if decision is None:  # too slow or failed: hold the thread instead of letting it time out
                decision = self._hold(view, sid, t0)
            msg = decision["message"]
            action = (msg.get("action") or {}).get("type")
            if action == "walk_away" and len(s.live_threads()) > 1:
                # Walking away ends the whole case; with other bidders still live, just stop
                # answering this one (its thread lapses after three timeouts).
                self.log("drop", supplier_id=sid)
                return
            if action:
                if self._close(decision, "the agent's decision"):
                    return
                close_failures += 1  # refused or unconfirmed, the case still open: decide again on fresh state
                if close_failures >= MAX_FAILURES:
                    self.log("drop", supplier_id=sid, reason="its closing moves failed repeatedly")
                    return
                s.ended.wait(CLOSE_RETRY_S)
                continue
            if moves_left(s.case, view[sid]) <= 0:  # round limit: only an accept is left
                self.log("drop", supplier_id=sid, reason="round limit")
                return
            outcome = self._send(sid, msg, decide_s=time.monotonic() - t0)
            if outcome == INVALID:
                # 422: nothing happened and no round was used; hold now, while the clock still allows
                failures += 1
                if failures >= MAX_FAILURES:
                    self.log("drop", supplier_id=sid, reason="the agent's messages were refused repeatedly")
                    return
                outcome = self._send(sid, self._hold(view, sid, t0)["message"], decide_s=time.monotonic() - t0)
            if outcome == UNREACHABLE:  # out of reach until the cap (or RECOVER_MAX_S): nothing left to play
                self.log("drop", supplier_id=sid, reason="the arena could not be reached")
                return

    def _hold(self, view, sid, t0):
        self.log("hold", supplier_id=sid, after_s=round(time.monotonic() - t0, 1))
        return {"supplier_id": sid, "message": {"subject": self._subject(view[sid]), "body": HOLD_BODY}}

    def _decide(self, view, sid, t0):
        """The agent's move, or None if it is not back HOLD_AT_S after the supplier's reply."""
        future = self._decide_pool.submit(self.agent.decide, self.state.case, view, sid)
        while True:  # in slices, so a case closed meanwhile (cap, another thread) frees this worker at once
            left = t0 + self.hold_at - time.monotonic()
            try:
                decision = future.result(timeout=max(0.0, min(WATCH_EVERY_S / 5, left)))
                break
            except FutureTimeout:
                if self.state.ended.is_set():
                    return None
                if left <= 0:
                    log.warning("%s %s: no decision %ss after the reply - holding", self.case_id, sid, self.hold_at)
                    return None
        took = time.monotonic() - t0
        if took > DECIDE_BUDGET_S:
            log.warning("%s %s: decision took %.1fs (budget %ss)", self.case_id, sid, took, DECIDE_BUDGET_S)
        if decision.get("supplier_id") != sid:
            log.warning("%s: asked about %s, got a move for %s", self.case_id, sid, decision.get("supplier_id"))
            decision = {**decision, "supplier_id": sid}
        if "trace" in decision:
            decision = dict(decision)
            self.log("decision", supplier_id=sid, trace=decision.pop("trace"))
        return decision

    def _send(self, sid, msg, decide_s):
        """One e-mail and its reply. None, or INVALID (422), or an outcome of `_recover`."""
        s = self.state
        self.log("sent", supplier_id=sid, message=msg, decide_s=round(decide_s, 2))
        with s.lock:
            s.inflight.add(sid)
            ours = _ours(s.threads[sid])  # our e-mails in the thread before this one
        try:
            return self._exchange(sid, msg, ours)
        finally:  # after the reply is recorded: a resync from now on sees it
            with s.lock:
                s.inflight.discard(sid)

    def _exchange(self, sid, msg, ours):
        s, until = self.state, None  # until: when to stop trying to reach the arena, fixed at the first failure
        for attempt in range(MAX_RESENDS + 1):  # a resend only after the arena said it never got the e-mail
            sent = time.monotonic()
            try:
                reply = self.client.send_message(self.table.session_id, sid, msg)
            except ArenaError as e:
                self.log("error", supplier_id=sid, status=e.status, detail=e.detail)
                if e.status == 422:
                    log.warning("%s %s: message refused: %s", self.case_id, sid, e.detail)
                    return INVALID
                if e.status != 409 and e.status < 500:
                    raise
                # 409 (late, round limit, ended, busy) or 5xx after the client's retries: ask the arena
                until = until or self._recover_until()
                outcome = self._recover(sid, ours, until)
                if e.status == 409:
                    return outcome  # the arena answered: what it holds is current, decide again on it
            except Exception as e:  # the network, after the client's own retries: did the message land?
                log.warning("%s %s: send failed (%s) - asking the arena", self.case_id, sid, e)
                self.log("error", supplier_id=sid, detail=e, where="send")
                until = until or self._recover_until()
                outcome = self._recover(sid, ours, until)
            else:
                return self._record(sid, msg, reply, sent)
            if outcome != LOST or attempt == MAX_RESENDS or s.closing.is_set() or self._cap_near():
                return outcome
            self.log("resend", supplier_id=sid, attempt=attempt + 1)  # it never arrived: same e-mail, once more
        return LOST

    def _record(self, sid, msg, reply, sent):
        s, now = self.state, time.monotonic()
        self.log("reply", supplier_id=sid, message=reply, wait_s=round(now - sent, 2))
        if "result" in reply:  # e.g. the last live supplier walked away
            return self._ended(reply["result"])
        self._documents(reply, sid)
        with s.lock:
            s.threads[sid] += [{**msg, "from": "buyer"}, reply]
            s.slowest = max(s.slowest, now - s.replied_at[sid])
            s.replied_at[sid] = now

    def _recover_until(self):
        """When (monotonic) a worker stops trying to reach the arena: the wave's cap + AFTER_CAP_S (the
        arena has ended the case by then), or RECOVER_MAX_S from now without a cap."""
        cap = self._cap()
        if cap:
            return time.monotonic() + max(0.0, cap + AFTER_CAP_S - time.time())
        return time.monotonic() + RECOVER_MAX_S

    def _recover(self, sid, ours, until):
        """Ask the arena about this thread until it answers - LANDED, LOST, CHANGED or ENDED_CASE (see
        `_refresh`) - or UNREACHABLE once `until` (monotonic) has passed. Each failed attempt waits a
        growing pause (or until the case ends), so this never spins and always ends."""
        s, pause, tries = self.state, RECOVER_PAUSE_S[0], 0
        while not s.ended.is_set():
            tries += 1
            try:
                outcome = self._refresh(sid, ours)
            except ArenaError as e:
                if e.status < 500 and e.status not in (409, 429):  # 401, 403, 404: asking again won't help
                    self.log("error", supplier_id=sid, status=e.status, detail=e.detail, where="recover")
                    return UNREACHABLE
                outcome = None  # busy, rate limit, the arena's own trouble: ask again
            except Exception as e:  # still no network
                if tries == 1:
                    self.log("error", supplier_id=sid, detail=e, where="recover")
                outcome = None
            if outcome not in (None, PENDING):
                if tries > 1:
                    log.warning("%s %s: the arena answered again after %d tries", self.case_id, sid, tries)
                return outcome
            if time.monotonic() + pause > until:
                log.warning("%s %s: the arena out of reach (%d tries) - giving the thread up", self.case_id, sid, tries)
                self.log("unreachable", supplier_id=sid, tries=tries)
                return UNREACHABLE
            s.ended.wait(pause)
            pause = min(2 * pause, RECOVER_PAUSE_S[1])
        return ENDED_CASE

    def _refresh(self, sid, ours=None):
        """One look at the session and this thread as the arena has them (network errors go to the
        caller); the thread's clock from the arena's `seconds_left`. With `ours` (our e-mails in the
        thread before the one that failed): LANDED (it arrived, the reply is here), LOST (it never
        arrived, the thread is open), CHANGED (closed meanwhile), PENDING (it arrived, the supplier is
        still writing: nothing recorded yet); ENDED_CASE if the case is over."""
        s = self.state
        state = self.client.session(self.table.session_id)
        if state.get("status") == "ended":
            self._ended(state.get("result") or {"deal": False, "end_reason": state.get("end_reason")})
            return ENDED_CASE
        t = self.client.thread(self.table.session_id, sid)
        msgs, th = t["messages"], (state.get("threads") or {}).get(sid) or {}
        arrived = ours is not None and _ours(msgs) > ours
        if arrived and msgs[-1].get("from") == "buyer":
            return PENDING
        for m in msgs:
            self._documents(m, sid)
        closed = bool(t.get("closed") or th.get("closed"))
        with s.lock:
            s.threads[sid] = msgs
            if closed:
                s.closed.add(sid)
            left = th.get("seconds_left")  # after a timeout or an outage our 60 s did not start just now
            s.replied_at[sid] = time.monotonic() - (max(0.0, MOVE_LIMIT_S - left) if left is not None else 0.0)
        self.log("refresh", supplier_id=sid, thread=t)
        return LANDED if arrived else CHANGED if closed or ours is None else LOST

    # -- closing --------------------------------------------------------------------------------
    def _cap(self):
        return self.deadline() if callable(self.deadline) else self.deadline

    def _past_cap(self):
        cap = self._cap()
        return bool(cap) and time.time() > cap + AFTER_CAP_S

    def _cap_near(self):
        cap = self._cap()
        return bool(cap) and time.time() > cap - max(CLOSE_BEFORE_CAP_S, self.state.slowest + ROUND_MARGIN_S)

    def _watch(self):
        """The workers check the cap before every move, but they may all be waiting for replies. Once
        the cap is near it keeps trying (a failed attempt is retried) until the arena confirms the end."""
        s = self.state
        while not s.ended.wait(WATCH_EVERY_S) and not self._stopped.is_set():
            if self._cap_near():
                self._close_now("the wave's cap is near (watchdog)")

    def _supervise_close(self, why):
        """Every worker has stopped and the case may still be open: close it and stay with it until the
        arena confirms the end - with a wave cap until the cap has passed (the arena ends the case
        there), without one for at most MAX_CLOSE_ATTEMPTS attempts."""
        s, attempts = self.state, 0
        while not s.ended.is_set():
            cap = self._cap()
            if cap and time.time() > cap + AFTER_CAP_S:
                self._reconcile(None)  # past the cap: the arena has ended the case, take its result
                break
            if not cap and attempts >= MAX_CLOSE_ATTEMPTS:
                break
            attempts += 1
            if s.live_threads():
                self._close_now(why)
            else:  # no live thread: the arena ends the case by itself
                self._reconcile(None)
            if not s.ended.is_set():
                s.ended.wait(CLOSE_RETRY_S)
        if not s.ended.is_set():
            log.warning("%s: the case is still open after %d closing attempts", self.case_id, attempts)
            self.log("close_unresolved", why=why, attempts=attempts)

    def _close_now(self, why):
        """The closing decision on the current state, played; True once the case has ended."""
        try:
            decision = self._closing_decision()
        except Exception as e:  # e.g. no live thread left for the kit's closing move
            self.log("error", detail=e, where="closing decision")
            return self.state.ended.is_set()
        return self._close(decision, why)

    def _closing_decision(self):
        view = self.state.snapshot()
        live = {sid: ev for sid, ev in view.items() if self.state.live(sid)} or view
        try:
            if hasattr(self.agent, "closing"):
                return self.agent.closing(self.state.case, live)
        except Exception as e:
            log.exception("%s: the agent's closing move failed - using the kit's", self.case_id)
            self.log("error", detail=e, where="closing")
        return closing_move(self.state.case, live)

    def _close(self, decision, why):
        """Accept or walk away - one attempt at a time, whichever worker or supervisor gets here first.
        True once the arena has confirmed the end. After a failed attempt the next one waits
        CLOSE_RETRY_S, so its caller decides again on the state the failure re-read."""
        s = self.state
        with self._close_lock:
            if s.ended.is_set():
                return True
            if time.monotonic() < s.retry_at:  # an attempt just failed: decide again first
                return False
            s.closing.set()
            try:
                self._attempt(decision, why)
            finally:
                s.closing.clear()
                if not s.ended.is_set():
                    s.retry_at = time.monotonic() + CLOSE_RETRY_S
            return s.ended.is_set()

    def _attempt(self, decision, why):
        """One terminal action, then - unless the reply carries the result - the arena's word on it."""
        s = self.state
        if s.unconfirmed and not self._reconcile(None):  # an earlier action's outcome is unknown: ask first
            return
        if s.ended.is_set():
            return
        sid, msg = decision["supplier_id"], decision["message"]
        self.log("closing", supplier_id=sid, message=msg, why=why)
        log.info("%s %s %s (%s)", self.case_id, sid, msg.get("action"), why)
        try:
            reply = self.client.send_message(self.table.session_id, sid, msg)
        except ArenaError as e:  # 422 (e.g. a stale term sheet), 409 (late, ended), 5xx after retries
            s.unconfirmed = e.status >= 500  # a server error: the action may have landed
            log.warning("%s: closing move failed (%s) - asking the arena", self.case_id, e)
            self.log("close_failed", supplier_id=sid, status=e.status, detail=e.detail, unconfirmed=s.unconfirmed)
        except Exception as e:  # the network, after the client's retries: the response is lost
            s.unconfirmed = True
            log.warning("%s: closing move unanswered (%s) - asking the arena", self.case_id, e)
            self.log("close_failed", supplier_id=sid, detail=e, unconfirmed=True)
        else:
            if "result" in reply:
                self._ended(reply["result"])
                self.log("closed", supplier_id=sid, how="reply")
                return
            s.unconfirmed = True  # an answer without the result: ask
        self._reconcile(sid)

    def _reconcile(self, sid):
        """Ask the arena whether the case has ended. Ended: take its result. Still open: re-read every
        thread no worker is waiting on (the offers may have moved on). False if the arena could not be
        asked - the outcome of the last action stays unknown and the next attempt asks again first."""
        s = self.state
        try:
            state = self.client.session(self.table.session_id)
        except Exception as e:
            self.log("error", detail=e, where="reconcile")
            return False
        s.unconfirmed = False
        if state.get("status") == "ended":
            self._ended(state.get("result") or {"deal": False, "end_reason": state.get("end_reason")})
            self.log("closed", supplier_id=sid, how="reconciled", end_reason=state.get("end_reason"))
            return True
        self._sync(state)
        return True

    def _sync(self, state):
        """Every thread as the arena has it, with its clock from `seconds_left` - except those a worker
        has a message in flight on (that worker records the reply itself)."""
        s = self.state
        for sid, th in (state.get("threads") or {}).items():
            with s.lock:
                if sid not in s.threads or sid in s.inflight:
                    continue
            try:
                t = self.client.thread(self.table.session_id, sid)
            except Exception as e:
                self.log("error", supplier_id=sid, detail=e, where="sync")
                continue
            for m in t["messages"]:
                self._documents(m, sid)
            with s.lock:
                if sid in s.inflight:  # a worker sent meanwhile: its reply is the newer state
                    continue
                s.threads[sid] = t["messages"]
                if t.get("closed") or th.get("closed"):
                    s.closed.add(sid)
                if th.get("seconds_left") is not None:
                    s.replied_at[sid] = time.monotonic() - max(0.0, MOVE_LIMIT_S - th["seconds_left"])
            self.log("refresh", supplier_id=sid, thread=t, why="closing")

    def _ended(self, result):
        s = self.state
        with s.lock:
            s.result = s.result or result
        s.ended.set()

    # -- helpers --------------------------------------------------------------------------------
    def _documents(self, message, sid=None, wait=False):
        """Add each attachment's text, downloaded once per attachment. In play the download runs in
        the background (`wait=False`): the arena may hold a GET until another supplier's reply on the
        same session is written, and this thread must not wait for that - its text is filled in when
        it arrives (and logged as an "attachment" event). Until then a decision sees the attachment
        without "text"; `standard_terms` falls back to the opening quote."""
        s = self.state
        for att in message.get("attachments") or []:
            aid = att.get("attachment_id")
            if not aid or "text" in att:
                continue
            with s.lock:
                if aid in s.texts:
                    att["text"] = s.texts[aid]
                    continue
                waiting = s.pending.setdefault(aid, [])
                waiting.append(att)
                if len(waiting) > 1:  # already downloading
                    continue
            if wait or self._docs_pool is None:
                self._download(aid, att["name"], sid, log_it=False)
            else:
                self._docs_pool.submit(self._download, aid, att["name"], sid)
        return message

    def _download(self, aid, name, sid, log_it=True):
        s = self.state
        try:
            text = read_document(name, self.table.attachment(aid))
        except Exception as e:  # asked again with the next message that carries it
            log.warning("%s %s: attachment %s: %s", self.case_id, sid, name, e)
            self.log("error", supplier_id=sid, detail=e, where="attachment", attachment_id=aid)
            with s.lock:
                s.pending.pop(aid, None)
            return
        with s.lock:
            s.texts[aid] = text
            for att in s.pending.pop(aid, []):
                att["text"] = text
        if log_it:
            self.log("attachment", supplier_id=sid, attachment_id=aid, name=name, text=text)

    @staticmethod
    def _subject(events):
        subject = next((m.get("subject") for m in events if m.get("subject")), "Your offer")
        return subject if subject.lower().startswith("re:") else f"Re: {subject}"


def _ours(events):
    """How many of the e-mails in a thread are ours."""
    return sum(m.get("from") == "buyer" for m in events)


def play_case(client, case_id, agent, *, case=None, deadline=None, log=None, hold_at=HOLD_AT_S, run=None, archive=None):
    """Play one case to its end with every thread at once; returns the result. `run`: the settings
    it ran with (agent, params, ...), logged on the case line. `archive`: a folder - each ended
    session is also saved there as one JSON file (see log.archive_session)."""
    player = CasePlayer(
        client, case_id, agent, case=case, deadline=deadline, log=log, hold_at=hold_at, run=run, archive=archive
    )
    return player.play()
