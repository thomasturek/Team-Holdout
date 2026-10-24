"""V3 (docs/V3_ROBUSTNESS_PLAN.md): metamorphic properties, the harness, dataset discipline."""

import copy
import dataclasses
import logging
import random
from pathlib import Path

import pytest
from arena_kit.cost import complete_offer, total_cost

from buyer.facts.case_check import check
from buyer.policy import ood
from buyer.policy.policy import Policy, ThreadState
from buyer.policy.v2 import PolicyV2
from buyer.sim import robust
from buyer.sim.env import load_cases
from buyer.sim.mutations import MUTATIONS, adversarial
from buyer.sim.population import sample
from buyer.sim.supplier import SyntheticSupplier

CASES = {c["case_id"]: c for c in load_cases()}


@pytest.fixture(autouse=True)
def quiet():
    logging.disable(logging.CRITICAL)  # V2 logs every fallback it takes
    yield
    logging.disable(logging.NOTSET)


def states(n_rounds=(0, 2, 4), seeds=range(3)):
    """Thread states across every training case: at the opening and a few rounds in (V0 playing)."""
    out = []
    for case in CASES.values():
        for seed in seeds:
            rng = random.Random(seed)
            sid = case["suppliers"][0]
            params, profile = sample(case, rng)
            s = SyntheticSupplier(case, sid, params, rng)
            o = s.opening()
            t = ThreadState(sid, o["term_sheet_id"], o["terms"], "open", s.standard, case.get("round_limit", 10),
                            profile={**profile, "archetype": "family_foundry", "floor_confidence": 0.1},
                            their_prices=[o["terms"]["unit_price"]])  # fmt: skip
            policy = Policy()
            for r in range(max(n_rounds) + 1):
                if r in n_rounds and t.status == "open":
                    out.append((case, copy.deepcopy(t)))
                d = policy.decide(case, t)
                if d.kind != "send":
                    break
                t.rounds_left -= 1
                reply = s.respond(d.term_sheets)
                t.status, t.standing_id, t.standing_terms = reply["status"], reply["term_sheet_id"], reply["terms"]
    return out


STATES = states()


def kind(policy, case, t):
    return policy.select(case, copy.deepcopy(t)).decision.kind if isinstance(policy, PolicyV2) else \
        policy.decide(case, copy.deepcopy(t)).kind


# --- metamorphic properties ------------------------------------------------------------------------------
def test_dearer_exw_freight_never_makes_an_exw_sheet_cheaper():
    for case in CASES.values():
        sheet = complete_offer(case, {"unit_price": case["buyer"].get("current_unit_price") or 10.0})
        sheet = {**sheet, "incoterm": "EXW"} if "incoterm" in sheet else {**sheet}
        dearer = copy.deepcopy(case)
        dearer["buyer"]["freight_eur_per_unit"]["EXW"] += 1.0
        assert total_cost(dearer, sheet) >= total_cost(case, sheet)


def test_a_better_alternative_never_makes_accepting_more_likely():
    for case, t in STATES:
        terms = {**t.standard, **case.get("fixed_terms", {}), **t.standing_terms}
        for policy in (Policy(), PolicyV2()):
            worse_alt, better_alt = copy.deepcopy(case), copy.deepcopy(case)
            for c, factor in ((worse_alt, 1.2), (better_alt, 0.9)):
                alt_terms = {**terms, "unit_price": terms["unit_price"] * factor}
                c["buyer"]["alternative"] = {"kind": "quote", "terms": alt_terms}
            if kind(policy, better_alt, t) == "accept":
                assert kind(policy, worse_alt, t) == "accept", (case["case_id"], type(policy).__name__)


def test_a_dearer_defect_never_helps_a_high_ppm_sheet():
    for case in (c for c in CASES.values() if "ppm_commitment" in c["negotiable"]):
        price = case["buyer"].get("current_unit_price") or 10.0
        low, high = (complete_offer(case, {"unit_price": price, "ppm_commitment": p}) for p in (300, 2500))
        dearer = copy.deepcopy(case)
        dearer["buyer"]["cost_per_defect"] = case["buyer"].get("cost_per_defect", 0) * 2 + 1
        assert total_cost(dearer, high) - total_cost(dearer, low) >= total_cost(case, high) - total_cost(case, low)


def test_less_time_never_turns_an_accept_into_another_probe():
    for case, t in STATES:
        for policy in (Policy(), PolicyV2()):
            if kind(policy, case, t) == "accept":
                fewer = dataclasses.replace(copy.deepcopy(t), rounds_left=max(1, t.rounds_left - 2))
                assert kind(policy, case, fewer) != "send", case["case_id"]


def test_removing_evidence_never_raises_confidence():
    v2 = PolicyV2()
    for case, t in STATES:
        full = v2.select(case, t).confidence
        for drop in ({"floor_estimate": None}, {"archetype": None}, {"floor_confidence": 0.5}):
            less = dataclasses.replace(copy.deepcopy(t), profile={**t.profile, **drop})
            assert v2.select(case, less).confidence <= full + 1e-9, (case["case_id"], drop)
        assert v2.select(case, dataclasses.replace(copy.deepcopy(t), profile={})).confidence <= full + 1e-9


# --- validators and mutations ----------------------------------------------------------------------------
def test_every_training_case_passes_the_scouts_gates():
    for case in CASES.values():
        assert check(case) == {"schema": [], "economic": []}, case["case_id"]


def test_the_gates_reject_broken_cases():
    case = copy.deepcopy(CASES["case:S01"])
    case["type"], case["buyer"]["need_per_year"] = "mystery", 0
    case["buyer"]["must_haves"] = [{"field": "payment_days", "op": ">=", "value": 10_000}]
    assert check(case)["schema"] == ["type 'mystery' undocumented"]
    case["type"] = "renewal"
    assert "buyer.need_per_year = 0" in check(case)["economic"]


def test_mutations_are_reproducible_and_carry_properties():
    parent = CASES["case:P05"]
    for name in MUTATIONS:
        a, b = adversarial(parent, 1234, name), adversarial(parent, 1234, name)
        assert a == b
        if a is not None:
            assert a.expected_properties and a.mutations == [name]
            assert a.distribution == "far_ood" or check(a.case) == {"schema": [], "economic": []}


def test_the_suites_use_disjoint_seeds_and_the_locked_one_is_guarded(monkeypatch):
    seeds = [set(r) for r in robust.SPLITS.values()]
    assert all(not (a & b) for i, a in enumerate(seeds) for b in seeds[i + 1:])
    dev = robust.load_suite("development")
    assert all(a.seed in robust.SPLITS["development"] for a in dev)
    monkeypatch.delenv("BUYER_LOCKED_EVAL", raising=False)
    with pytest.raises(robust.LockedSuite):
        robust.load_suite("locked")


def test_training_code_never_reads_the_adversarial_suites():
    root = Path(robust.__file__).parent
    for name in ("train.py", "calibrate.py", "population.py", "env.py", "metrics.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "robust" not in text and "generated" not in text and "locked" not in text, name


# --- the harness on the development suite ----------------------------------------------------------------
def test_the_development_suite_holds_every_safety_property():
    suite = robust.load_suite("development")[::3]  # a third of it keeps the test quick
    s = robust.run(suite, episodes=1)
    assert not s["v1_violations"], s["v1_violations"]
    hard = {"no_exception", "no_invalid_sheet", "must_not_break_must_have", "must_not_accept_worse_than_alternative",
            "must_not_accept_opening", "must_close_within_round_limit", "confidence_must_not_rise", "must_fallback"}
    assert not hard & set(s["v2_violations"]), s["v2_violations"]
    assert s["far_ood_fallback_recall"] in (None, 1.0) and not s["errors"]


def test_unseen_case_types_and_far_cases_fall_back():
    case = {**CASES["case:S01"], "type": robust.adversarial.__globals__["UNSEEN_TYPE"]}
    _, t = next((c, t) for c, t in STATES if c["case_id"] == "case:S01")
    assert PolicyV2().select(case, t).policy_source == "v0_fallback"
    big = copy.deepcopy(CASES["case:S01"])
    big["buyer"]["need_per_year"] *= 1000
    assert ood.distance_to_training(big) > ood.FAR_DISTANCE
    assert "far from every training case" in PolicyV2().select(big, t).ood_reasons
