"""The policy adapter and the sandbox harvester against arena-sim (its 3 cases stand in for the sandbox)."""

import json

from buyer.runtime import agent as agents
from buyer.runtime.agent import PolicyAgent, new_agent
from buyer.runtime.harvest import Harvester, report, save_cases
from buyer.runtime.log import SessionLog, iter_logs, read
from buyer.runtime.threads import play_case


def test_the_analysts_policy_plays_every_case_to_an_end(sim, tmp_path):
    client, _, _ = sim
    for case in client.cases("sandbox"):
        lg = SessionLog("sim", case["case_id"], root=tmp_path)
        result = play_case(client, case["case_id"], new_agent("policy"), case=case, log=lg)
        assert result["ended"]
        decisions = [e for e in read(lg.path) if e["kind"] == "decision"]
        assert decisions and {"kind", "supplier_id", "term_sheets"} <= set(decisions[0]["trace"]["decision"])
        for e in read(lg.path):
            if e["kind"] == "sent":  # complete term sheets, no stray numbers in the template body
                assert all(set(ts["terms"]) == set(case["negotiable"]) for ts in e["message"]["term_sheets"])
                assert not any(ch.isdigit() for ch in e["message"]["body"])


def test_a_partial_parameter_set_keeps_the_trained_values():
    from buyer.policy.policy import load_params

    trained = load_params()
    p = PolicyAgent({"concede": 0.5}).policy.p
    assert p["concede"] == 0.5 and all(p[k] == v for k, v in trained.items() if k != "concede")


def test_harvest_runs_every_parameter_set_on_every_case_and_logs_them(sim, tmp_path, monkeypatch):
    client, _, _ = sim
    explore = tmp_path / "explore.json"
    explore.write_text(json.dumps([{"concede": 0.1}, {"concede": 0.6}]))
    monkeypatch.setattr(agents, "EXPLORE", explore)
    h = Harvester(client, parallel=3, root=tmp_path / "runs")
    results = h.run(sessions=6)
    assert len(results) == 6
    pairs = {(i, c) for i, c, _, _ in results}
    assert pairs == {(i, c["case_id"]) for i in (0, 1) for c in h.cases}  # every set x every case
    logs = iter_logs("sandbox", root=tmp_path / "runs")
    assert len(logs) == 6
    runs = [next(e for e in read(p) if e["kind"] == "case")["run"] for p in logs]
    assert {r["params"]["concede"] for r in runs} == {0.1, 0.6}
    assert {r["harvest"] for r in runs} == {h.id} and all(r["agent"] == "policy" for r in runs)
    assert len(report(results)) == 6


def test_without_explore_json_the_trained_params_run(sim, tmp_path, monkeypatch):
    client, _, _ = sim
    monkeypatch.setattr(agents, "EXPLORE", tmp_path / "missing.json")
    results = Harvester(client, parallel=2, root=tmp_path).run(sessions=2)
    assert {i for i, *_ in results} == {0}


def test_a_failed_session_is_logged_and_the_harvest_goes_on(sim, tmp_path, monkeypatch):
    client, _, _ = sim
    h = Harvester(client, parallel=1, root=tmp_path)
    real, calls = client.open_session, {"n": 0}

    def flaky(case_id):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("network down")
        return real(case_id)

    monkeypatch.setattr(client, "open_session", flaky)
    monkeypatch.setattr("buyer.runtime.harvest.ERROR_WAIT_S", 0)
    results = h.run(sessions=3)
    assert len(results) == 2
    failed = [p for p in iter_logs(root=tmp_path) if p.name.startswith("failed-")]
    assert failed and read(failed[0])[0]["kind"] == "error"


def test_case_files_are_saved_for_the_simulator(sim, tmp_path):
    client, _, _ = sim
    assert save_cases(client, root=tmp_path) == {"sandbox": 3, "practice": 3}
    cases = json.loads((tmp_path / "cases" / "sandbox.json").read_text(encoding="utf-8"))
    assert {c["case_id"] for c in cases} == {"case:S01", "case:S02", "case:S03"}
