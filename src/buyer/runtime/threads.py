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

A walk-away while other bidders are still live only stops this worker (walking away would end the
whole case); the last live thread's walk-away ends it.
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
HOLD_BODY = (
    "Thank you for your message. We are reviewing it internally and will come back to you with our "
    "position shortly.\n\nBest regards\nHollerau Pumpenwerke, Purchasing"
)


class CaseState:
    """Everything the workers of one case share. All access under `lock`."""

    def __init__(self, case, threads):
        self.case, self.threads = case, threads
        self.lock = threading.Lock()
        self.over = threading.Event()  # set once the case has ended (or a close is under way)
        self.result = None
        self.closed = set()  # threads the arena has closed (timeouts, walked away, no bid)
        self.replied_at = {sid: time.monotonic() for sid in threads}  # our 60 s run from here
        self.slowest = 0.0  # longest round so far, any thread: decision + supplier reply
        self.texts = {}  # attachment_id -> text, so refreshed threads keep their documents
        self.pending = {}  # attachment_id -> attachment dicts waiting for its text (download running)

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
            with self._close_lock:  # a close still in flight (watchdog, another worker): wait for its result
                pass
            if not s.over.is_set() and s.live_threads():  # every worker stopped, the case is open: close it
                self._close(self._closing_decision(), "no thread left to play")
            s.over.set()
        finally:
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
        s, failures = self.state, 0
        while not s.over.is_set() and s.live(sid):
            view = s.snapshot()
            if self._cap_near():
                return self._close(self._closing_decision(), "the wave's cap is near")
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
            if s.over.is_set():
                return
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
                return self._close(decision, "the agent's decision")
            if moves_left(s.case, view[sid]) <= 0:  # round limit: only an accept is left
                self.log("drop", supplier_id=sid, reason="round limit")
                return
            if self._send(sid, msg, decide_s=time.monotonic() - t0) == INVALID:
                # 422: nothing happened and no round was used; hold now, while the clock still allows
                failures += 1
                if failures >= MAX_FAILURES:
                    self.log("drop", supplier_id=sid, reason="the agent's messages were refused repeatedly")
                    return
                self._send(sid, self._hold(view, sid, t0)["message"], decide_s=time.monotonic() - t0)

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
                if self.state.over.is_set():
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
        s, sent = self.state, time.monotonic()
        self.log("sent", supplier_id=sid, message=msg, decide_s=round(decide_s, 2))
        try:
            reply = self.client.send_message(self.table.session_id, sid, msg)
        except ArenaError as e:
            self.log("error", supplier_id=sid, status=e.status, detail=e.detail)
            if e.status == 422:
                log.warning("%s %s: message refused: %s", self.case_id, sid, e.detail)
                return INVALID
            if e.status != 409:
                raise
            return self._refresh(sid)  # late, round limit, thread or case ended: ask the arena
        except Exception as e:  # the network, after the client's own retries: did the message land?
            log.warning("%s %s: send failed (%s) - asking the arena", self.case_id, sid, e)
            self.log("error", supplier_id=sid, detail=e, where="send")
            return self._refresh(sid)
        now = time.monotonic()
        self.log("reply", supplier_id=sid, message=reply, wait_s=round(now - sent, 2))
        if "result" in reply:  # e.g. the last live supplier walked away
            return self._ended(reply["result"])
        self._documents(reply, sid)
        with s.lock:
            s.threads[sid] += [{**msg, "from": "buyer"}, reply]
            s.slowest = max(s.slowest, now - s.replied_at[sid])
            s.replied_at[sid] = now

    def _refresh(self, sid):
        """After a 409: the session's state and this thread as the arena has them."""
        s = self.state
        state = self.client.session(self.table.session_id)
        if state.get("status") == "ended":
            return self._ended(state.get("result") or {"deal": False, "end_reason": state.get("end_reason")})
        t = self.client.thread(self.table.session_id, sid)
        for m in t["messages"]:
            self._documents(m, sid)
        with s.lock:
            s.threads[sid] = t["messages"]
            if t.get("closed"):
                s.closed.add(sid)
            s.replied_at[sid] = time.monotonic()  # the arena answered our late move just now
        self.log("refresh", supplier_id=sid, thread=t)

    # -- closing --------------------------------------------------------------------------------
    def _cap_near(self):
        cap = self.deadline() if callable(self.deadline) else self.deadline
        return bool(cap) and time.time() > cap - max(CLOSE_BEFORE_CAP_S, self.state.slowest + ROUND_MARGIN_S)

    def _watch(self):
        """The workers check the cap before every move, but they may all be waiting for replies."""
        while not self.state.over.wait(WATCH_EVERY_S):
            if self._cap_near():
                self._close(self._closing_decision(), "the wave's cap is near (watchdog)")
                return

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
        """Accept or walk away - once per case, whichever worker or the watchdog gets here first."""
        s = self.state
        with self._close_lock:
            if s.over.is_set():
                return
            s.over.set()
            sid, msg = decision["supplier_id"], decision["message"]
            self.log("closing", supplier_id=sid, message=msg, why=why)
            log.info("%s %s %s (%s)", self.case_id, sid, msg.get("action"), why)
            try:
                reply = self.client.send_message(self.table.session_id, sid, msg)
            except ArenaError as e:
                self.log("error", supplier_id=sid, status=e.status, detail=e.detail, where="closing")
                if e.status != 409:  # e.g. a stale term sheet (422): nothing happened, play on
                    log.warning("%s: closing move refused: %s", self.case_id, e)
                    s.over.clear()
                    return
                state = self.client.session(self.table.session_id)
                if state.get("status") != "ended":  # a late accept: the case goes on
                    s.over.clear()
                    self._refresh(sid)
                    return
                reply = {"result": state.get("result") or {"deal": False, "end_reason": state.get("end_reason")}}
            s.result = reply.get("result", reply)

    def _ended(self, result):
        s = self.state
        with s.lock:
            s.result = s.result or result
        s.over.set()

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


def play_case(client, case_id, agent, *, case=None, deadline=None, log=None, hold_at=HOLD_AT_S, run=None, archive=None):
    """Play one case to its end with every thread at once; returns the result. `run`: the settings
    it ran with (agent, params, ...), logged on the case line. `archive`: a folder - each ended
    session is also saved there as one JSON file (see log.archive_session)."""
    player = CasePlayer(
        client, case_id, agent, case=case, deadline=deadline, log=log, hold_at=hold_at, run=run, archive=archive
    )
    return player.play()
