"""The runner against arena-sim: quota guard, practice/sandbox runs, the final's waves, resume, forbidden endpoints."""

import json
import time

import pytest

from buyer.runtime import runner
from buyer.runtime.agent import new_agent
from buyer.runtime.log import iter_logs, read
from buyer.runtime.runner import QuotaRefused, SafeClient, check_quota, play_final, play_set
from buyer.runtime.threads import play_case


def safe(client):
    return SafeClient(
        str(client.http.base_url).rstrip("/").removesuffix("/v1"), client.http.headers["X-API-Key"], rate=1000
    )


def test_the_agent_never_reads_what_is_for_people(sim):
    client = safe(sim[0])
    for call in (
        client.leaderboard,
        lambda: client._call("GET", "/results"),
        lambda: client._call("GET", "/events/stream"),
    ):
        with pytest.raises(PermissionError):
            call()
    assert client.cases("practice")  # everything else works


def test_a_practice_run_that_would_eat_the_reserve_is_refused(sim, monkeypatch):
    client = safe(sim[0])
    monkeypatch.setattr(client, "me", lambda: {"practice": {"used": 175, "left": 25, "limit": 200, "resets_at": "t"}})
    assert check_quota(client, 5, reserve=20)["left"] == 25
    with pytest.raises(QuotaRefused):
        check_quota(client, 6, reserve=20)


def test_practice_stops_starting_sessions_at_the_reserve(sim, tmp_path):
    client = safe(sim[0])
    cases = client.cases("practice")  # 3 cases; the arena-sim quota starts at 200 left
    out = play_set(client, "practice", cases, agent="naive", parallel=1, reserve=198, root=tmp_path)
    played = [r for _, r in out if isinstance(r, dict)]
    refused = [r for _, r in out if not isinstance(r, dict)]
    assert len(played) == 2 and len(refused) == 1 and "reserve" in str(refused[0])
    assert client.practice_remaining == 198


def test_practice_and_sandbox_runs_log_and_save_every_session(sim, tmp_path):
    client = safe(sim[0])
    for set_ in ("practice", "sandbox"):
        out = play_set(
            client, set_, client.cases(set_), agent="policy", repeat=2, run={"purpose": "test"}, root=tmp_path
        )
        assert len(out) == 6 and all(isinstance(r, dict) and r["ended"] for _, r in out)
        saved = sorted((tmp_path / f"{set_}_sessions").glob("*.json"))
        assert len(saved) == 6
        doc = json.loads(saved[0].read_text(encoding="utf-8"))
        assert doc["run"]["purpose"] == "test" and doc["run"]["agent"] == "policy" and doc["threads"]
        assert len(iter_logs(set_, root=tmp_path)) == 6


def test_the_final_plays_both_rehearsal_waves(sim, tmp_path):
    client, state, _ = sim
    state.clock = time.time  # a real clock: the runner reads time.time() for each wave's cap
    state.rehearse(wait=0.3, cap=3, brk=0.3)
    out = play_final(safe(client), agent="naive", waves=2, poll=0.05, root=tmp_path)
    assert sorted(out) == [f"case:R{n}-S0{i}" for n in (1, 2) for i in (1, 2, 3)]
    assert all(isinstance(r, dict) and r["ended"] for r in out.values())
    assert len(list((tmp_path / "final_sessions").glob("*.json"))) == 6
    # a 3 s cap is inside the closing margin: every case closed at once, none ran into the cap
    assert all(r.get("end_reason") != "wave_cap" for r in out.values())


def test_after_a_crash_the_running_final_session_is_picked_up(sim, tmp_path):
    client, state, _ = sim
    state.rehearse(wait=0, cap=240, brk=30)  # the test clock stands still: the wave stays open
    client = safe(client)
    case = next(c for c in client.cases("final") if c["case_id"] == "case:R1-S01")
    first = client.open_session("case:R1-S01")  # the runner opened it, sent once, then crashed
    sid, sup = first["session_id"], case["suppliers"][0]
    terms = first["threads"][sup][0]["term_sheets"][0]["terms"]
    from arena_kit.cost import complete_offer

    sheet = complete_offer(case, {**terms, "unit_price": round(terms["unit_price"] * 0.9, 2)})
    client.send_message(sid, sup, {"subject": "Re", "body": "Our offer.", "term_sheets": [{"terms": sheet}]})
    from buyer.runtime.log import SessionLog

    lg = SessionLog("final", "case:R1-S01", root=tmp_path)
    result = play_case(client, "case:R1-S01", new_agent("naive"), case=case, log=lg)
    assert result["ended"] and result["deal"]
    events = read(lg.path)
    assert lg.path.stem == sid and any(e["kind"] == "resumed" for e in events)
    assert sum(e["kind"] == "sent" for e in events) >= 1  # played on from where it stood


def test_a_final_case_whose_start_failed_is_started_again_and_picks_up_its_session(sim, tmp_path, monkeypatch):
    import httpx

    client, state, _ = sim
    state.clock = time.time
    state.rehearse(wait=0.3, cap=4, brk=0.3)
    monkeypatch.setattr(runner, "RESTART_S", 0.2)
    client = safe(client)
    real, opened = client.open_session, []

    def open_session(case_id):  # the first open of R1-S01 reaches the arena; its answer is lost
        opened.append(case_id)
        out = real(case_id)
        if opened.count(case_id) == 1 and case_id == "case:R1-S01":
            raise httpx.ReadTimeout("the response was lost")
        return out

    monkeypatch.setattr(client, "open_session", open_session)
    out = play_final(client, agent="naive", waves=1, poll=0.05, root=tmp_path)
    assert opened.count("case:R1-S01") == 2
    assert all(isinstance(r, dict) and r["ended"] for r in out.values()), out
    assert len([s for s in state.sessions.values() if s["case"]["case_id"] == "case:R1-S01"]) == 1  # the same one


def test_the_clients_connections_notice_a_dropped_network(sim):
    import socket

    options = runner.keepalive_options()
    assert (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) in options
    assert len(options) >= 2  # an idle time as well, on Linux, macOS and Windows
    client = safe(sim[0])
    assert client.http.timeout.connect == runner.CONNECT_TIMEOUT_S and client.http.timeout.read == 180
    assert client.cases("practice")  # the keepalive transport works


def test_the_quota_command(sim, monkeypatch, capsys):
    client = sim[0]
    monkeypatch.setenv("ARENA_URL", str(client.http.base_url).rstrip("/").removesuffix("/v1"))
    monkeypatch.setenv("ARENA_API_KEY", client.http.headers["X-API-Key"])
    runner.main(["quota"])
    assert "left 200 of 200" in capsys.readouterr().out


def test_unknown_cases_are_refused_before_anything_starts(sim, monkeypatch, tmp_path):
    client = sim[0]
    monkeypatch.setenv("ARENA_URL", str(client.http.base_url).rstrip("/").removesuffix("/v1"))
    monkeypatch.setenv("ARENA_API_KEY", client.http.headers["X-API-Key"])
    monkeypatch.setattr(runner.env, "RUNS", tmp_path)
    with pytest.raises(SystemExit, match="not playable"):
        runner.main(["practice", "--cases", "P99"])
    assert client.me()["practice"]["used"] == 0
