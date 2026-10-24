"""Run logs: layout, thread safety, logs before the session exists, reading back, backfill."""

import json
import threading
from dataclasses import dataclass

from arena_kit.client import ArenaError

from buyer.runtime.log import SessionLog, backfill, iter_logs, read, safe, summary


def test_one_file_per_session_with_safe_names(tmp_path):
    lg = SessionLog("practice", "case:P01", root=tmp_path)
    lg.bind("sess:42")
    lg("case", case_id="case:P01", session_id="sess:42")
    assert lg.path == tmp_path / "practice" / "case_P01" / "sess_42.jsonl"
    (event,) = read(lg.path)
    assert event["kind"] == "case" and event["case_id"] == "case:P01" and event["t"] > 0


def test_lines_before_bind_are_kept_in_order(tmp_path):
    lg = SessionLog("sandbox", "case:D01", root=tmp_path)
    lg("case", n=1)
    lg("opening", n=2)
    lg.bind("s1")
    lg.bind("s2")  # a second bind changes nothing
    lg("sent", n=3)
    assert [e["n"] for e in read(lg.path)] == [1, 2, 3]
    assert lg.path.name == "s1.jsonl"


def test_a_failed_open_still_leaves_a_file(tmp_path):
    lg = SessionLog("practice", "case:P02", root=tmp_path)
    lg("error", status=429, detail="practice limit: ...")
    lg.close()
    assert lg.path.name.startswith("failed-") and read(lg.path)[0]["status"] == 429


def test_many_threads_write_whole_lines(tmp_path):
    lg = SessionLog("sandbox", "case:D02", root=tmp_path)
    lg.bind("s")

    def write(sid):
        for i in range(200):
            lg("sent", supplier_id=sid, i=i, body="x" * 500)

    workers = [threading.Thread(target=write, args=(f"sup:{n}",)) for n in range(5)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    events = read(lg.path)
    assert len(events) == 1000
    for n in range(5):
        assert [e["i"] for e in events if e["supplier_id"] == f"sup:{n}"] == list(range(200))


@dataclass
class Decision:
    kind: str
    term_sheets: list


def test_anything_the_agent_hands_over_is_logged(tmp_path):
    lg = SessionLog("sim", "case:S01", root=tmp_path)
    lg.bind("s")
    lg("decision", trace=Decision("send", [{"unit_price": 1.0}]), raw=b"%PDF", ids={"a"}, err=ValueError("x"))
    (e,) = read(lg.path)
    assert e["trace"] == {"kind": "send", "term_sheets": [{"unit_price": 1.0}]}
    assert e["raw"] == "<4 bytes>" and e["ids"] == ["a"] and e["err"] == "ValueError: x"


def test_a_line_cut_off_by_a_crash_is_skipped(tmp_path):
    path = tmp_path / "x.jsonl"
    path.write_text(json.dumps({"kind": "case"}) + "\n" + '{"kind": "se', encoding="utf-8")
    assert read(path) == [{"kind": "case"}]


def test_iter_logs_by_set(tmp_path):
    for set_, case in (("practice", "case:P01"), ("sandbox", "case:D01"), ("sandbox", "case:D02")):
        lg = SessionLog(set_, case, root=tmp_path)
        lg.bind("s")
        lg("case")
    assert len(iter_logs(root=tmp_path)) == 3
    assert {p.parent.name for p in iter_logs("sandbox", root=tmp_path)} == {safe("case:D01"), safe("case:D02")}


class FakeArena:
    """The final's after-the-end rules: trace and back office only once `over` is set."""

    def __init__(self):
        self.over, self.calls = False, []

    def session(self, sid):
        self.calls.append(("session", sid))
        result = {"deal": True, "score": 0.7, **({"trace": [{"round": 1}]} if self.over else {})}
        return {"session_id": sid, "status": "ended", "result": result}

    def backoffice(self, sid):
        self.calls.append(("backoffice", sid))
        if not self.over:
            raise ArenaError(403, "the back office opens after the final")
        return {"messages": ["sales asked the MD"]}


def final_log(root, case, sid):
    lg = SessionLog("final", case, root=root)
    lg.bind(sid)
    lg("case", case_id=case, session_id=sid)
    lg("result", result={"deal": True, "score": 0.7})
    return lg.path


def test_backfill_waits_for_the_end_of_the_final_then_adds_both_once(tmp_path):
    arena, path = FakeArena(), final_log(tmp_path, "case:H01", "f1")
    assert backfill(arena, "final", tmp_path) == {}  # final still running: nothing to add
    arena.over = True
    assert backfill(arena, "final", tmp_path) == {path: ["trace", "backoffice"]}
    kinds = [e["kind"] for e in read(path)]
    assert kinds == ["case", "result", "session", "backoffice"]
    arena.calls.clear()
    assert backfill(arena, "final", tmp_path) == {} and arena.calls == []  # complete: no calls
    assert "complete" in summary(path)


def test_backfill_fetches_only_what_is_missing(tmp_path):
    arena, path = FakeArena(), final_log(tmp_path, "case:H02", "f2")
    arena.over = True
    SessionLog.at(path)("backoffice", data={"messages": []})
    assert backfill(arena, "final", tmp_path) == {path: ["trace"]}
    assert ("backoffice", "f2") not in arena.calls


def test_backfill_skips_logs_without_a_session(tmp_path):
    lg = SessionLog("final", "case:H03", root=tmp_path)
    lg("error", status=403)
    lg.close()
    assert backfill(FakeArena(), "final", tmp_path) == {}
