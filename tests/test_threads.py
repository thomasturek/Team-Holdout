"""Per-thread play against arena-sim: concurrency, one close, holds, the cap, 409s, failures, network outages.

case:S01 and case:S03 have one supplier; case:S02 is an RFQ with sup:70340 and sup:70360.
"""

import threading
import time

from arena_kit.play import CLOSE_BEFORE_CAP_S, standing

from buyer.runtime.agent import new_agent
from buyer.runtime.log import SessionLog, read
from buyer.runtime.threads import play_case

RFQ, A, B = "case:S02", "sup:70340", "sup:70360"


def logged(tmp_path, case_id):
    return SessionLog("sim", case_id, root=tmp_path)


def kinds(lg, kind):
    return [e for e in read(lg.path) if e["kind"] == kind]


def accept(threads, sid):
    return {"supplier_id": sid, "message": {"action": {"type": "accept", "term_sheet_id": standing(threads[sid])[0]}}}


class Scripted:
    """Per supplier: a function (case, threads, sid) -> decision; everyone else plays naive."""

    def __init__(self, **per_supplier):
        self.naive, self.per = new_agent("naive"), {k.replace("_", ":"): v for k, v in per_supplier.items()}

    def decide(self, case, threads, sid):
        fn = self.per.get(sid)
        return fn(case, threads, sid) if fn else self.naive.decide(case, threads, sid)


def test_naive_plays_every_case_to_a_logged_end(sim, tmp_path):
    client, _, _ = sim
    for case_id in ("case:S01", RFQ, "case:S03"):
        lg = logged(tmp_path, case_id)
        result = play_case(client, case_id, new_agent("naive"), log=lg)
        assert result["ended"] and result["deal"]
        assert len(kinds(lg, "closing")) == 1 and kinds(lg, "result") and kinds(lg, "session")


def test_rfq_threads_are_played_at_the_same_time(sim, tmp_path):
    client, _, _ = sim
    calls, naive = [], new_agent("naive")

    class Slow:
        def decide(self, case, threads, sid):
            start = time.monotonic()
            time.sleep(0.3)
            calls.append((sid, start, time.monotonic()))
            return naive.decide(case, threads, sid)

    lg = logged(tmp_path, RFQ)
    assert play_case(client, RFQ, Slow(), log=lg)["deal"]
    (a0, a1), (b0, b1) = [next((s, e) for x, s, e in calls if x == sid) for sid in (A, B)]
    assert a0 < b1 and b0 < a1  # the first decisions for both suppliers overlapped
    assert {e["supplier_id"] for e in kinds(lg, "sent")} == {A, B}


def test_two_accepts_at_once_close_the_case_once(sim, tmp_path):
    client, _, _ = sim
    both = threading.Barrier(2)

    def at_once(case, threads, sid):
        both.wait(timeout=5)
        return accept(threads, sid)

    lg = logged(tmp_path, RFQ)
    result = play_case(client, RFQ, Scripted(sup_70340=at_once, sup_70360=at_once), log=lg)
    assert result["deal"] and len(kinds(lg, "closing")) == 1 and not kinds(lg, "error")


def test_a_slow_decision_sends_a_hold_and_play_goes_on(sim, tmp_path):
    client, _, _ = sim
    slow = {"first": True}

    def once_slow(case, threads, sid):
        if slow.pop("first", False):
            time.sleep(1.0)
        return new_agent("naive").decide(case, threads, sid)

    lg = logged(tmp_path, "case:S01")
    result = play_case(client, "case:S01", Scripted(sup_70270=once_slow), log=lg, hold_at=0.3)
    assert result["deal"]
    (hold,) = kinds(lg, "hold")
    first_sent = kinds(lg, "sent")[0]["message"]
    assert "term_sheets" not in first_sent and first_sent["subject"].startswith("Re:")
    assert hold["after_s"] < 1.0


def test_the_cap_closes_before_the_first_move(sim, tmp_path):
    client, _, _ = sim
    lg = logged(tmp_path, "case:S01")
    result = play_case(client, "case:S01", new_agent("naive"), deadline=time.time(), log=lg)
    assert result["deal"] and not kinds(lg, "sent")
    assert "cap" in kinds(lg, "closing")[0]["why"]


def test_the_watchdog_closes_while_every_thread_is_busy(sim, tmp_path):
    client, _, _ = sim

    def stuck(case, threads, sid):
        time.sleep(3)
        return new_agent("naive").decide(case, threads, sid)

    lg = logged(tmp_path, RFQ)
    t0 = time.monotonic()
    deadline = time.time() + CLOSE_BEFORE_CAP_S + 1
    result = play_case(client, RFQ, Scripted(sup_70340=stuck, sup_70360=stuck), deadline=deadline, log=lg)
    assert result["deal"] and not kinds(lg, "sent")
    assert "watchdog" in kinds(lg, "closing")[0]["why"] and time.monotonic() - t0 < 3


def test_the_agents_closing_move_is_used_at_the_cap(sim, tmp_path):
    client, _, _ = sim

    class WithClosing(Scripted):
        def closing(self, case, threads):
            return accept(threads, B)

    lg = logged(tmp_path, RFQ)
    result = play_case(client, RFQ, WithClosing(), deadline=time.time(), log=lg)
    assert result["deal"] and result["supplier_id"] == B


def test_a_late_message_is_read_back_and_played_on(sim, tmp_path):
    client, _, clock = sim
    late = {"first": True}

    def first_late(case, threads, sid):
        if late.pop("first", False):
            clock.now += 61  # the arena now counts this move as a timeout: 409
        return new_agent("naive").decide(case, threads, sid)

    lg = logged(tmp_path, "case:S01")
    result = play_case(client, "case:S01", Scripted(sup_70270=first_late), log=lg)
    assert result["deal"]
    assert kinds(lg, "error")[0]["status"] == 409 and kinds(lg, "refresh")


def test_walking_away_from_one_bidder_keeps_the_rfq_going(sim, tmp_path):
    client, _, _ = sim
    walk = lambda case, threads, sid: {"supplier_id": sid, "message": {"action": {"type": "walk_away"}}}  # noqa: E731
    lg = logged(tmp_path, RFQ)
    result = play_case(client, RFQ, Scripted(sup_70340=walk), log=lg)
    assert result["deal"] and result["supplier_id"] == B
    assert [e["supplier_id"] for e in kinds(lg, "drop")] == [A]


def test_walking_away_from_the_last_supplier_ends_the_case(sim, tmp_path):
    client, _, _ = sim
    walk = lambda case, threads, sid: {"supplier_id": sid, "message": {"action": {"type": "walk_away"}}}  # noqa: E731
    lg = logged(tmp_path, "case:S01")
    result = play_case(client, "case:S01", Scripted(sup_70270=walk), log=lg)
    assert result["deal"] is False and result.get("end_reason", "walked_away") == "walked_away"


def test_a_crashing_agent_holds_then_drops_its_thread_only(sim, tmp_path):
    client, _, _ = sim

    def broken(case, threads, sid):
        raise RuntimeError("policy bug")

    lg = logged(tmp_path, RFQ)
    result = play_case(client, RFQ, Scripted(sup_70340=broken), log=lg)
    assert result["deal"] and result["supplier_id"] == B
    assert [e["where"] for e in kinds(lg, "error") if e.get("supplier_id") == A] == ["decide", "decide"]
    assert len([h for h in kinds(lg, "hold") if h["supplier_id"] == A]) == 1
    assert [e["supplier_id"] for e in kinds(lg, "drop")] == [A]


def test_a_refused_message_is_replaced_by_a_hold(sim, tmp_path):
    client, _, _ = sim
    bad = {"first": True}

    def invalid_once(case, threads, sid):
        if bad.pop("first", False):  # four term sheets: a 422, nothing happens
            return {"supplier_id": sid, "message": {"body": "x", "term_sheets": [{"terms": {}}] * 4}}
        return new_agent("naive").decide(case, threads, sid)

    lg = logged(tmp_path, "case:S01")
    result = play_case(client, "case:S01", Scripted(sup_70270=invalid_once), log=lg)
    assert result["deal"]
    assert kinds(lg, "error")[0]["status"] == 422 and len(kinds(lg, "hold")) == 1


class AskBreakdown:
    """Lowballs with a cost-breakdown question, so every supplier reply carries an attachment;
    accepts after `rounds` messages."""

    def __init__(self, rounds=4):
        self.rounds = rounds

    def decide(self, case, threads, sid):
        events = threads[sid]
        if sum(m.get("from") == "buyer" for m in events) >= self.rounds:
            return accept(threads, sid)
        sheet_id, terms = standing(events)
        from arena_kit.cost import complete_offer

        sheet = complete_offer(case, {**terms, "unit_price": round(terms["unit_price"] * 0.5, 2)})
        body = "Thank you. Could you send a cost breakdown?"
        return {
            "supplier_id": sid,
            "message": {"subject": "Re: offer", "body": body, "term_sheets": [{"terms": sheet}]},
        }


def test_a_thread_answers_without_waiting_for_another_suppliers_reply(slow_sim, tmp_path):
    """Serial arena: B's reply carries a cost breakdown while A's supplier takes 1.5 s per reply.
    B must decide and send at once, not after A's supplier has answered."""
    client = slow_sim({A: 1.5, B: 0.0}, serial=True)
    lg = logged(tmp_path, RFQ)
    play_case(client, RFQ, AskBreakdown(), log=lg)
    b_sends = [e for e in kinds(lg, "sent") if e["supplier_id"] == B][1:]  # after a reply with an attachment
    assert b_sends and max(e["decide_s"] for e in b_sends) < 0.5, [e["decide_s"] for e in b_sends]
    texts = [e for e in kinds(lg, "attachment") if e["supplier_id"] == B]
    assert texts and all(e["name"] == "cost-breakdown.xlsx" and e["text"] for e in texts)


def test_a_fast_thread_plays_several_rounds_while_a_slow_supplier_writes(slow_sim, tmp_path):
    """Parallel arena: B gets all its rounds in while A's supplier is still writing its first reply."""
    client = slow_sim({A: 2.0, B: 0.0}, serial=False)
    lg = logged(tmp_path, RFQ)
    play_case(client, RFQ, AskBreakdown(rounds=10), log=lg)
    first_a_reply = next(e["t"] for e in kinds(lg, "reply") if e["supplier_id"] == A)
    b_before = [e for e in kinds(lg, "reply") if e["supplier_id"] == B and e["t"] < first_a_reply]
    assert len(b_before) >= 3


# -- the closing lifecycle: supervised until the arena confirms the end --------------------------
STALE = "offer:70270-999"  # not a standing offer: the arena answers 422, as for a stale term sheet


def actions(lg):
    return [e for e in read(lg.path) if e["kind"] == "closing"]


def stale_accept(sid):
    return {"supplier_id": sid, "message": {"action": {"type": "accept", "term_sheet_id": STALE}}}


def faulty_sends(monkeypatch, client, fault):
    """Wrap send_message: `fault(n, call)` decides for the n-th terminal action (accept / walk away)."""
    real, calls = client.send_message, {"n": 0, "landed": 0}

    def send(session_id, supplier_id, message):
        if not message.get("action"):
            return real(session_id, supplier_id, message)
        calls["n"] += 1

        def call():
            reply = real(session_id, supplier_id, message)
            calls["landed"] += 1
            return reply

        return fault(calls["n"], call)

    monkeypatch.setattr(client, "send_message", send)
    return calls


def test_a_stale_offer_at_the_cap_is_refreshed_and_the_current_one_accepted(sim, tmp_path):
    client, _, _ = sim

    class StaleFirst(Scripted):
        calls = 0

        def closing(self, case, threads):
            self.calls += 1
            return stale_accept("sup:70270") if self.calls == 1 else accept(threads, "sup:70270")

    lg = logged(tmp_path, "case:S01")
    result = play_case(client, "case:S01", StaleFirst(), deadline=time.time(), log=lg)
    assert result["deal"]
    (failed,) = kinds(lg, "close_failed")
    assert failed["status"] == 422 and not failed["unconfirmed"]
    assert len(actions(lg)) == 2 and [e["how"] for e in kinds(lg, "closed")] == ["reply"]
    assert any(e.get("why") == "closing" for e in kinds(lg, "refresh"))


def test_an_accept_that_landed_with_its_response_lost_is_not_sent_again(sim, tmp_path, monkeypatch):
    import httpx

    client, _, _ = sim

    def lost_answer(n, call):
        call()  # the arena took it ...
        raise httpx.ReadTimeout("the response was lost")  # ... and we never heard back

    calls = faulty_sends(monkeypatch, client, lost_answer)
    lg = logged(tmp_path, "case:S01")
    result = play_case(client, "case:S01", new_agent("naive"), log=lg)
    assert result["deal"] and calls == {"n": 1, "landed": 1}
    assert kinds(lg, "close_failed")[0]["unconfirmed"] and kinds(lg, "closed")[0]["how"] == "reconciled"


def test_an_accept_that_never_arrived_is_tried_again_after_asking(sim, tmp_path, monkeypatch):
    import httpx

    client, _, _ = sim

    def first_lost(n, call):
        if n == 1:
            raise httpx.ConnectError("the request never left")
        return call()

    calls = faulty_sends(monkeypatch, client, first_lost)
    lg = logged(tmp_path, "case:S01")
    result = play_case(client, "case:S01", new_agent("naive"), log=lg)
    assert result["deal"] and calls["landed"] == 1 and calls["n"] >= 2
    assert kinds(lg, "close_failed")[0]["unconfirmed"] and kinds(lg, "closed")[-1]["how"] == "reply"


def test_the_watchdog_closes_on_current_offers_while_replies_are_in_flight(slow_sim, tmp_path):
    """One call per session at a time and 2 s replies: the cap comes while both threads wait for
    their supplier; the offer the watchdog picks may be stale by the time its accept is processed."""
    client = slow_sim({A: 2.0, B: 2.0}, serial=True)
    lg = logged(tmp_path, RFQ)
    result = play_case(client, RFQ, new_agent("naive"), deadline=time.time() + CLOSE_BEFORE_CAP_S + 0.5, log=lg)
    assert result["ended"] and result["deal"]
    assert len(kinds(lg, "closed")) == 1 and not kinds(lg, "close_unresolved")
    first_close = actions(lg)[0]["t"]
    assert not [e for e in kinds(lg, "sent") if e["t"] > first_close]  # no new offer once closing began


def test_after_a_restart_an_accept_that_landed_is_not_played_again(sim, tmp_path):
    client, state, _ = sim
    state.rehearse(wait=0, cap=240, brk=30)  # a final wave; the test clock stands still
    case = next(c for c in client.cases("final") if c["case_id"] == "case:R1-S01")
    opened = client.open_session("case:R1-S01")
    sid, sup = opened["session_id"], case["suppliers"][0]
    sheet_id = opened["threads"][sup][0]["term_sheets"][0]["term_sheet_id"]
    client.send_message(sid, sup, {"action": {"type": "accept", "term_sheet_id": sheet_id}})  # then: crash
    lg = SessionLog("final", "case:R1-S01", root=tmp_path)
    result = play_case(client, "case:R1-S01", new_agent("naive"), case=case, log=lg)
    assert result["deal"] and lg.path.stem == sid and not actions(lg)


def test_when_every_worker_has_stopped_play_sees_the_close_through(sim, tmp_path):
    client, _, _ = sim
    lg = logged(tmp_path, "case:S01")
    agent = Scripted(sup_70270=lambda case, threads, sid: stale_accept(sid))  # its accepts always fail
    result = play_case(client, "case:S01", agent, log=lg)
    assert result["deal"]  # the kit's closing move on the current offer
    assert [e["status"] for e in kinds(lg, "close_failed")] == [422, 422]
    assert kinds(lg, "drop") and actions(lg)[-1]["why"] == "no thread left to play"


def test_without_a_cap_a_close_that_keeps_failing_is_given_up_in_bounded_time(sim, tmp_path, monkeypatch):
    from arena_kit.client import ArenaError

    from buyer.runtime import threads as runtime

    client, _, _ = sim
    monkeypatch.setattr(runtime, "CLOSE_RETRY_S", 0.05)

    def refused(n, call):
        raise ArenaError(422, "not a standing offer in this session")

    faulty_sends(monkeypatch, client, refused)
    lg = logged(tmp_path, "case:S01")
    t0 = time.monotonic()
    play_case(client, "case:S01", Scripted(sup_70270=lambda case, threads, sid: accept(threads, sid)), log=lg)
    assert time.monotonic() - t0 < 30
    (unresolved,) = kinds(lg, "close_unresolved")
    assert unresolved["attempts"] == runtime.MAX_CLOSE_ATTEMPTS


# -- the network drops: a thread waits for the arena (bounded), reads back what landed, never sends twice ----
class Network:
    """The network as the runtime sees it once the client's own retries are spent. `cut_next_send` cuts
    the next e-mail (not an accept / walk-away): after it reached the arena (the reply is lost) or before
    (it never left). Then every call fails for `down_s` seconds (None: for good) while the arena's clock
    moves on `arena_s` seconds (the 60-second rule)."""

    def __init__(self, monkeypatch, client, clock=None):
        self.real, self.clock, self.lock = client._call, clock, threading.Lock()
        self.until, self.cut, self.failed = 0.0, None, 0
        monkeypatch.setattr(client, "_call", self._call)

    def cut_next_send(self, *, landed, down_s, arena_s=0.0):
        self.cut = (landed, down_s, arena_s)

    def _call(self, method, path, body=None, params=None, raw=False):
        import httpx

        with self.lock:
            if time.monotonic() < self.until:
                self.failed += 1
                raise httpx.ConnectError("[Errno 8] nodename nor servname provided, or not known")
            email = method == "POST" and path.endswith("/messages") and not body["message"].get("action")
            cut, self.cut = (self.cut, None) if email else (None, self.cut)
        if not cut:
            return self.real(method, path, body, params, raw)
        landed, down_s, arena_s = cut
        if landed:
            self.real(method, path, body, params, raw)
        if self.clock:
            self.clock.now += arena_s
        with self.lock:
            self.until = float("inf") if down_s is None else time.monotonic() + down_s
        if landed:
            raise httpx.ReadTimeout("the response was lost")
        raise httpx.ConnectError("the request never left")


def finishes(fn, within=20):
    """fn() in a thread; the test fails (instead of hanging the suite) if it is still running after `within` s."""
    out = {}

    def run():
        try:
            out["value"] = fn()
        except BaseException as e:  # noqa: BLE001 - reported to the test
            out["error"] = e

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(within)
    assert not worker.is_alive(), f"still running after {within} s"
    return out


def arena_emails(state, lg, sid):
    """Our e-mails to `sid` as the arena has them (every one of them, duplicates included)."""
    session = state.sessions[lg.path.stem]
    return [m for m in session["threads"][sid]["messages"] if m.get("from") == "buyer"]


def outage(monkeypatch, client, clock=None):
    from buyer.runtime import threads as runtime

    monkeypatch.setattr(runtime, "RECOVER_PAUSE_S", (0.05, 0.2))
    monkeypatch.setattr(runtime, "CLOSE_RETRY_S", 0.05)
    return Network(monkeypatch, client, clock)


def test_a_reply_lost_in_an_outage_is_read_back_and_not_sent_again(sim, tmp_path, monkeypatch):
    client, state, _ = sim
    net = outage(monkeypatch, client)
    net.cut_next_send(landed=True, down_s=1.0)
    lg = logged(tmp_path, "case:S01")
    result = finishes(lambda: play_case(client, "case:S01", new_agent("naive"), log=lg))["value"]
    assert result["deal"] and net.failed > 0 and not kinds(lg, "drop") and not kinds(lg, "resend")
    assert kinds(lg, "error")[0]["where"] == "send" and kinds(lg, "refresh")  # read back from the arena
    assert len(arena_emails(state, lg, "sup:70270")) == len(kinds(lg, "sent"))  # each e-mail once


def test_an_email_that_never_left_is_sent_again_once_the_arena_answers(sim, tmp_path, monkeypatch):
    client, state, _ = sim
    net = outage(monkeypatch, client)
    net.cut_next_send(landed=False, down_s=1.0)
    lg = logged(tmp_path, "case:S01")
    result = finishes(lambda: play_case(client, "case:S01", new_agent("naive"), log=lg))["value"]
    assert result["deal"] and net.failed > 0 and not kinds(lg, "drop")
    assert len(kinds(lg, "resend")) == 1
    assert len(arena_emails(state, lg, "sup:70270")) == len(kinds(lg, "sent"))


def test_every_thread_of_an_rfq_plays_on_after_an_outage(sim, tmp_path, monkeypatch):
    client, state, _ = sim
    net = outage(monkeypatch, client)
    net.cut_next_send(landed=True, down_s=1.0)
    lg = logged(tmp_path, RFQ)
    result = finishes(lambda: play_case(client, RFQ, new_agent("naive"), log=lg))["value"]
    assert result["deal"] and net.failed > 0
    assert not [e for e in kinds(lg, "drop") if "reach" in str(e.get("reason"))]
    for sid in (A, B):
        sent = [e for e in kinds(lg, "sent") if e["supplier_id"] == sid]
        assert len(arena_emails(state, lg, sid)) == len(sent)


def test_an_outage_longer_than_60_s_costs_one_timeout_not_the_case(sim, tmp_path, monkeypatch):
    client, state, clock = sim
    net = outage(monkeypatch, client, clock)
    net.cut_next_send(landed=True, down_s=0.5, arena_s=75)  # the supplier's reply waited 75 s for us
    lg = logged(tmp_path, "case:S01")
    result = finishes(lambda: play_case(client, "case:S01", new_agent("naive"), log=lg))["value"]
    assert result["deal"] and not kinds(lg, "drop")
    assert len(state.sessions[lg.path.stem]["threads"]["sup:70270"]["late"]) == 1


def test_an_outage_longer_than_three_timeouts_ends_the_case_and_play_returns(sim, tmp_path, monkeypatch):
    client, _, clock = sim
    net = outage(monkeypatch, client, clock)
    net.cut_next_send(landed=True, down_s=0.5, arena_s=185)  # 3 x 60 s: the arena ends the thread
    lg = logged(tmp_path, "case:S01")
    result = finishes(lambda: play_case(client, "case:S01", new_agent("naive"), log=lg))["value"]
    assert result["deal"] is False and result["ended"]


def test_a_network_that_never_comes_back_ends_play_in_bounded_time(sim, tmp_path, monkeypatch):
    from buyer.runtime import threads as runtime

    client, _, _ = sim
    net = outage(monkeypatch, client)
    monkeypatch.setattr(runtime, "RECOVER_MAX_S", 0.5)
    net.cut_next_send(landed=False, down_s=None)
    lg = logged(tmp_path, "case:S01")
    t0 = time.monotonic()
    out = finishes(lambda: play_case(client, "case:S01", new_agent("naive"), log=lg))
    assert time.monotonic() - t0 < 10 and "error" in out  # the result itself cannot be read
    (drop,) = kinds(lg, "drop")
    assert "reach" in drop["reason"] and kinds(lg, "close_unresolved")


def test_a_network_that_never_comes_back_is_given_up_after_the_wave_cap(sim, tmp_path, monkeypatch):
    from buyer.runtime import threads as runtime

    client, _, _ = sim
    net = outage(monkeypatch, client)
    monkeypatch.setattr(runtime, "CLOSE_BEFORE_CAP_S", 1.0)
    monkeypatch.setattr(runtime, "ROUND_MARGIN_S", 0.5)
    monkeypatch.setattr(runtime, "AFTER_CAP_S", 0.5)
    net.cut_next_send(landed=False, down_s=None)
    lg = logged(tmp_path, RFQ)
    t0 = time.monotonic()
    out = finishes(lambda: play_case(client, RFQ, new_agent("naive"), deadline=time.time() + 2.0, log=lg))
    assert time.monotonic() - t0 < 10 and "error" in out
    assert kinds(lg, "closing")  # the cap's close was tried while the arena could not be reached
