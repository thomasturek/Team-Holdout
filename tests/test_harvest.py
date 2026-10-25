"""The policy adapter and the sandbox harvester against arena-sim (its 3 cases stand in for the sandbox)."""

import json

from buyer.llm.compose import offers_block, sign_off
from buyer.llm.guard import foreign_numbers
from buyer.runtime import agent as agents
from buyer.runtime.agent import PolicyAgent, new_agent, probe_agent, probes
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
            if e["kind"] == "sent":  # complete term sheets; figures only in the code-made term-sheet lines
                sheets = e["message"].get("term_sheets") or []
                assert all(set(ts["terms"]) == set(case["negotiable"]) for ts in sheets)
                prose = e["message"]["body"].replace(offers_block(sheets), " ").replace(sign_off(), " ")
                decision = [d for d in decisions if d["supplier_id"] == e["supplier_id"] and d["t"] <= e["t"]][-1]
                for claim in decision["trace"]["decision"].get("claims") or []:
                    prose = prose.replace(claim["sentence"], " ")
                assert not foreign_numbers(prose, set()), prose


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
    h = Harvester(client, parallel=3, root=tmp_path / "runs", probe_every=0)
    results = h.run(sessions=6)
    assert len(results) == 6
    pairs = {(i, c) for i, c, _, _ in results}
    assert pairs == {(f"set {i}", c["case_id"]) for i in (0, 1) for c in h.cases}  # every set x every case
    logs = iter_logs("sandbox", root=tmp_path / "runs")
    assert len(logs) == 6
    runs = [next(e for e in read(p) if e["kind"] == "case")["run"] for p in logs]
    assert {r["params"]["concede"] for r in runs} == {0.1, 0.6}
    assert {r["harvest"] for r in runs} == {h.id} and all(r["agent"] == "policy" for r in runs)
    assert len(report(results)) == 6


def test_without_explore_json_the_trained_params_run(sim, tmp_path, monkeypatch):
    client, _, _ = sim
    monkeypatch.setattr(agents, "EXPLORE", tmp_path / "missing.json")
    results = Harvester(client, parallel=2, root=tmp_path, probe_every=0).run(sessions=2)
    assert {i for i, *_ in results} == {"set 0"}


def test_a_failed_session_is_logged_and_the_harvest_goes_on(sim, tmp_path, monkeypatch):
    client, _, _ = sim
    h = Harvester(client, parallel=1, root=tmp_path, probe_every=0)
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


def archived(folder):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]


def test_every_session_is_saved_as_one_json_file_as_the_api_returns_it(sim, tmp_path):
    client, _, _ = sim
    h = Harvester(client, parallel=3, root=tmp_path, probe_every=0)
    h.run(sessions=3)
    assert h.archive == tmp_path / "sandbox_sessions"
    docs = archived(h.archive)
    assert len(docs) == 3 and len({d["session_id"] for d in docs}) == 3
    for doc in docs:
        assert {"case", "threads", "result", "run", "session_id", "case_id"} <= set(doc)
        assert set(doc["threads"]) == set(doc["case"]["suppliers"])
        for sid, thread in doc["threads"].items():
            api = client.thread(doc["session_id"], sid)
            assert thread == json.loads(json.dumps(api))  # exactly the API's answer
            senders = [m["from"] == "buyer" for m in thread["messages"]]
            assert senders[0] is False and len(senders) > 1  # the opening quote first, then in order
        assert doc["result"]["ended"] and "score" in doc["result"]


def test_a_push_probe_answers_a_final_offer_with_another_offer(sim, tmp_path, monkeypatch):
    monkeypatch.setattr("buyer.runtime.agent.scout_profiles", lambda case: {})  # the probe, not the floor
    client, _, _ = sim
    case = next(c for c in client.cases("sandbox") if c["case_id"] == "case:S01")
    params = {"concede": 0.02, "accept_gap_pct": 0.0, "reciprocity": 0, "min_step_pct": 0}
    agent = probe_agent("policy", params, {"push_final": True})
    play_case(client, "case:S01", agent, case=case, archive=tmp_path)
    (doc,) = archived(tmp_path)
    messages = next(iter(doc["threads"].values()))["messages"]
    finals = [i for i, m in enumerate(messages) if m.get("status") == "final_offer"]
    assert finals, "the simulator made no final offer"
    after = messages[finals[0] + 1]
    assert after["from"] == "buyer" and after.get("term_sheets") and not after.get("action")


def test_a_payment_probe_proposes_those_payment_days_on_every_sheet(sim, tmp_path):
    client, _, _ = sim
    case = next(c for c in client.cases("sandbox") if c["case_id"] == "case:S03")
    days = case["term_options"]["payment_days"][0]
    lg = SessionLog("sim", "case:S03", root=tmp_path)
    play_case(client, "case:S03", probe_agent("policy", {}, {"payment_days": days}), case=case, log=lg)
    sent = [e["message"] for e in read(lg.path) if e["kind"] == "sent" and e["message"].get("term_sheets")]
    assert sent and all(ts["terms"]["payment_days"] == days for m in sent for ts in m["term_sheets"])
    traces = [e["trace"] for e in read(lg.path) if e["kind"] == "decision"]
    assert all(t["probe"]["payment_days"] == days for t in traces if t["decision"]["kind"] == "send")


def test_every_third_session_is_a_probe_marked_in_its_logs(sim, tmp_path):
    client, _, _ = sim
    h = Harvester(client, parallel=2, root=tmp_path)
    results = h.run(sessions=6)
    labels = sorted(label for label, *_ in results)
    assert sum(label.startswith("probe") for label in labels) == 2
    runs = [doc["run"] for doc in archived(h.archive)]
    marked = [r["probe"] for r in runs if r["probe"]]
    assert len(marked) == 2 and all(m in probes(h.cases[r["episode"] % 3]) for r in runs if (m := r["probe"]))
