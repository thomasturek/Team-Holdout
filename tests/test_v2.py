"""Phase 2: the shield, safe candidates, ranking with fallback, and the v1 / shadow / v2 switch."""

import dataclasses
import math
import random

import pytest
from arena_kit.cost import complete_offer

from buyer.facts import shield
from buyer.interfaces import CandidateAction, Claim
from buyer.policy import ood
from buyer.policy.candidates import generate
from buyer.policy.policy import Policy, ThreadState
from buyer.policy.ranker import PRIOR, Ranker
from buyer.policy.v2 import PolicyV2
from buyer.runtime.agent import new_agent, policy_mode
from buyer.runtime.log import SessionLog, read
from buyer.runtime.threads import play_case
from buyer.sim.env import episode, load_cases
from buyer.sim.population import sample
from buyer.sim.supplier import SyntheticSupplier

CASES = {c["case_id"]: c for c in load_cases()}
S01 = CASES["case:S01"]


def thread(case, seed=0, **change):
    """A ThreadState at the supplier's opening quote, as the simulator builds it."""
    rng = random.Random(seed)
    sid = case["suppliers"][0]
    params, profile = sample(case, rng)
    s = SyntheticSupplier(case, sid, params, rng)
    o = s.opening()
    t = ThreadState(sid, o["term_sheet_id"], o["terms"], "open", s.standard, case.get("round_limit", 10),
                    profile={**profile, "archetype": "family_foundry", "floor_confidence": 0.05},
                    their_prices=[o["terms"]["unit_price"]])  # fmt: skip
    for k, v in change.items():
        setattr(t, k, v)
    return t


def cand(kind, sheets=(), sheet_id=None, claims=()):
    return CandidateAction("x", kind, "sup:1", list(sheets), list(claims), [], "", None, None, None, None, {}, True,
                           [], accept_sheet_id=sheet_id)  # fmt: skip


# --- the shield ----------------------------------------------------------------------------------
def test_the_shield_passes_a_complete_offer_and_names_every_problem():
    t = thread(S01)
    good = complete_offer(S01, {**t.standing_terms, "unit_price": t.standing_terms["unit_price"] * 0.97})
    ctx = {"standing_id": t.standing_id, "standing_terms": t.standing_terms, "standard": t.standard}
    assert shield.validate(S01, cand("send", [good]), ctx) == []
    missing = {k: v for k, v in good.items() if k != "payment_days"}
    assert any("missing" in r for r in shield.validate(S01, cand("send", [missing]), ctx))
    assert any("term_options" in r for r in shield.validate(S01, cand("send", [{**good, "payment_days": 999}]), ctx))
    assert shield.validate(S01, cand("send", [good] * 4), ctx)  # at most 3 term sheets
    assert any("stale" in r for r in shield.validate(S01, cand("accept", sheet_id="offer:old"), ctx))


def test_the_shield_never_lets_a_bad_accept_through():
    t = thread(S01)
    ctx = {"standing_id": t.standing_id, "standing_terms": t.standing_terms, "standard": t.standard}
    strict = {**S01, "buyer": {**S01["buyer"], "must_haves": [{"field": "payment_days", "op": ">=", "value": 1000}]}}
    assert "breaks a must-have" in shield.validate(strict, cand("accept", sheet_id=t.standing_id), ctx)
    alt = {"kind": "quote", "terms": {**t.standing_terms, "unit_price": 0.01}}
    cheap_alt = {**S01, "buyer": {**S01["buyer"], "alternative": alt}}
    assert "costs more than the alternative" in shield.validate(cheap_alt, cand("accept", sheet_id=t.standing_id), ctx)


def test_the_shield_rejects_unknown_and_repeated_claim_ids():
    t = thread(S01)
    sheet = complete_offer(S01, t.standing_terms)
    claim = Claim("po:x", "Price was EUR 1.00 (po:1, po:2).", ["po:1", "po:2"], "verified", 0.5)
    ctx = {"standing_id": t.standing_id, "standard": t.standard, "known_id": lambda r: r != "po:2",
           "used_refs": {"po:1"}}  # fmt: skip
    reasons = shield.validate(S01, cand("send", [sheet], claims=[claim]), ctx)
    assert "claim ref po:2 unknown" in reasons and "claim ref po:1 already used" in reasons


# --- candidates and ranking ----------------------------------------------------------------------
def test_candidates_are_costed_checked_and_v0_is_always_one():
    policy = Policy()
    t = thread(S01)
    v0 = policy.decide(S01, t)
    cands = generate(S01, t, policy, v0)
    assert cands[0].candidate_id == "v0" and {"price_step", "walk"} <= {c.family for c in cands}
    for c in cands:
        assert c.features and c.buyer_cost is not None
        if c.valid and c.kind == "send":
            assert all(shield.check_terms(S01, s) == [] for s in c.term_sheets)


def test_select_leaves_the_thread_alone_and_decide_commits_like_v0():
    t = thread(S01)
    before = dataclasses.asdict(t)
    sel = PolicyV2().select(S01, t)
    assert dataclasses.asdict(t) == before and sel.policy_source.startswith(("v2", "v0"))
    t_v0, t_v2 = thread(S01), thread(S01)
    d0, d2 = Policy().decide(S01, t_v0), PolicyV2().decide(S01, t_v2)
    assert d0.term_sheets == d2.term_sheets and t_v0.our_prices == t_v2.our_prices  # the prior ranker keeps V0's move


def test_a_trained_ranker_can_pick_another_safe_candidate_and_the_state_follows():
    prefers_hard = {**PRIOR, "bias:v0": 0.0, "bias:price_step": 0.0, "saving_vs_standing": 10.0}
    v2 = PolicyV2(ranker=Ranker(members=[prefers_hard] * 3))
    t = thread(S01)
    sel = v2.select(S01, t, commit=True)
    price = sel.decision.term_sheets[0]["unit_price"]
    chosen = next(r for r in sel.ranked_candidates if r.get("id") and r["price"] == price)
    assert sel.policy_source == "v2_ml" and chosen["valid"] and chosen["id"] != "v0"
    assert t.our_prices[-1] == sel.decision.term_sheets[0]["unit_price"]


def test_unfamiliar_states_fall_back_to_v0_and_say_why():
    t = thread(S01)
    t.profile = {}  # no floor, no archetype
    odd = {**S01, "type": "spot_buy"}  # no training case has it
    sel = PolicyV2().select(odd, t)
    d0 = Policy().decide(odd, thread(S01, profile={}))
    assert sel.policy_source == "v0_fallback" and sel.confidence < ood.MEDIUM
    assert {"no floor estimate", "unfamiliar case type"} <= set(sel.ood_reasons)
    assert sel.decision.term_sheets == d0.term_sheets


def test_more_uncertainty_never_raises_confidence():
    full = PolicyV2().select(S01, thread(S01))
    t = thread(S01)
    t.profile = {**t.profile, "floor_estimate": None}
    less = PolicyV2().select(S01, t)
    assert less.confidence < full.confidence


def test_rules_and_errors_belong_to_v0():
    final = PolicyV2().select(S01, thread(S01, status="final_offer"))
    assert final.policy_source == "v0_rule"

    class Broken(Ranker):
        def rank(self, cands):
            raise RuntimeError("model bug")

    sel = PolicyV2(ranker=Broken()).select(S01, thread(S01))
    assert sel.policy_source == "v0_fallback" and "model bug" in sel.ood_reasons[0]
    assert sel.decision.term_sheets == Policy().decide(S01, thread(S01)).term_sheets


def test_v2_plays_the_simulator_like_v1_with_the_prior_ranker():
    for case in CASES.values():
        for i in range(5):
            a = episode(case, Policy(), random.Random(i))["score"]
            b = episode(case, PolicyV2(), random.Random(i))["score"]
            assert a == pytest.approx(b), (case["case_id"], i)


# --- the runtime switch --------------------------------------------------------------------------
def run(client, tmp_path, case_id, mode, monkeypatch):
    if mode:
        monkeypatch.setenv("BUYER_POLICY", mode)
    else:
        monkeypatch.delenv("BUYER_POLICY", raising=False)
    lg = SessionLog("sim", case_id, root=tmp_path / (mode or "default"))
    result = play_case(client, case_id, new_agent("policy"), log=lg)
    events = read(lg.path)
    return result, [e for e in events if e["kind"] == "sent"], [e for e in events if e["kind"] == "decision"]


def test_v1_is_the_default_and_an_unknown_mode_plays_v1(monkeypatch):
    monkeypatch.delenv("BUYER_POLICY", raising=False)
    assert policy_mode() == "v1"
    monkeypatch.setenv("BUYER_POLICY", "v9")
    assert policy_mode() == "v1"


def test_shadow_mode_logs_v2_but_sends_exactly_what_v1_sends(sim, tmp_path, monkeypatch):
    client, _, _ = sim
    # single-supplier cases: in an RFQ each thread undercuts the other's current offer, so even two V1 runs
    # differ with the threads' timing
    for case_id in ("case:S01", "case:S03"):
        _, sent_v1, dec_v1 = run(client, tmp_path / case_id[-3:], case_id, None, monkeypatch)
        _, sent_sh, dec_sh = run(client, tmp_path / case_id[-3:], case_id, "shadow", monkeypatch)
        assert [e["message"].get("term_sheets") for e in sent_v1] == [e["message"].get("term_sheets") for e in sent_sh]
        assert all("shadow" not in d["trace"] and "v2" not in d["trace"] for d in dec_v1)
        assert dec_sh and all("policy_source" in d["trace"]["shadow"] for d in dec_sh)
    _, _, dec_rfq = run(client, tmp_path / "S02", "case:S02", "shadow", monkeypatch)
    assert {d["supplier_id"] for d in dec_rfq if "policy_source" in d["trace"]["shadow"]} == {"sup:70340", "sup:70360"}


def test_v2_mode_plays_every_case_to_an_end_with_valid_sheets(sim, tmp_path, monkeypatch):
    from arena_kit.data import DataPackage

    from buyer.runtime.env import ROOT

    client, state, _ = sim
    state.facts = DataPackage(str(ROOT / "data")).facts  # as `arena-sim --data` runs: the data IDs exist
    for c in client.cases("sandbox"):
        result, sent, decisions = run(client, tmp_path, c["case_id"], "v2", monkeypatch)
        assert result["ended"] and decisions
        assert all(d["trace"]["v2"]["policy_source"] in ("v2_ml", "v2_conservative", "v0_fallback", "v0_rule")
                   for d in decisions)  # fmt: skip
        for e in sent:
            for ts in e["message"].get("term_sheets") or []:
                assert shield.check_terms(c, ts["terms"]) == []
        assert all(d["trace"]["v2"]["latency_s"] < 1.0 for d in decisions)
        assert any(d["trace"]["decision"]["claims"] for d in decisions)  # the Scout's verified claims go out
        lg = next((tmp_path / "v2").rglob("*.jsonl"))
        results = [r.get("result") for e in read(lg) if e["kind"] == "reply"
                   for r in (e["message"].get("claim_results") or [])]  # fmt: skip
        assert "contradicted" not in results and "duplicate" not in results, results


def test_the_report_reads_shadow_logs(sim, tmp_path, monkeypatch):
    from buyer.policy.report import collect, render
    from buyer.runtime.log import iter_logs

    client, _, _ = sim
    run(client, tmp_path, "case:S01", "shadow", monkeypatch)
    by_mode = collect(iter_logs(root=tmp_path / "shadow"))
    assert by_mode["shadow"]["decisions"] and by_mode["shadow"]["agree"]
    assert "shadow agrees with V1" in render(by_mode)


def test_alternative_cost_matches_the_policy():
    from buyer.policy.policy import alternative_cost

    for case in CASES.values():
        a, b = shield.alternative_cost(case), alternative_cost(case)
        assert a == b or (math.isinf(a) and math.isinf(b))
