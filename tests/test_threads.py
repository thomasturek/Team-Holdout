"""Per-thread play against arena-sim: concurrency, one close, holds, the cap, 409s, failures.

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
