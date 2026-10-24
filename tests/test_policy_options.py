import json
from pathlib import Path

import pytest
from arena_kit.cost import must_haves_ok, total_cost

from buyer.policy.policy import Policy, ThreadState

CASES = Path(__file__).resolve().parents[1] / "runs" / "cases" / "practice.json"
SID = "sup:70140"


def practice(case_id):
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    cases = cases if isinstance(cases, list) else list(cases.values())
    return next(c for c in cases if c["case_id"] == case_id)


@pytest.fixture
def case():
    return practice("case:P11")


def test_best_options_keep_the_must_haves(case):
    theirs = {"unit_price": 47.5, "ppm_commitment": 2500, "chargeback_eur_per_complaint": 500.0}
    out = Policy.best_options(case, theirs, {})
    assert must_haves_ok(case, out, {})
    assert out["ppm_commitment"] == 1500
    assert out["chargeback_eur_per_complaint"] == 500.0


def test_the_counter_to_a_must_have_breaking_offer_keeps_the_must_haves(case):
    terms = {"unit_price": 48.5, "ppm_commitment": 2500, "chargeback_eur_per_complaint": 500.0}
    t = ThreadState(SID, "offer:70140-1", terms, "open", {}, 5)
    decision = Policy({"claims_per_msg": 0}).decide(case, t)
    assert decision.kind == "send"
    assert all(must_haves_ok(case, s, {}) for s in decision.term_sheets)


def test_the_counter_offers_a_longer_payment_term_that_saves_us_money():
    case = practice("case:P02")
    terms = {"unit_price": 370.96, "payment_days": 30, "index_clause": None}
    t = ThreadState("sup:70240", "offer:70240-1", terms, "open", {}, 9)
    decision = Policy({"claims_per_msg": 0}).decide(case, t)
    a = decision.term_sheets[0]
    slow = [s for s in decision.term_sheets if s["payment_days"] == 90]
    assert slow and slow[0]["unit_price"] > a["unit_price"]
    assert total_cost(case, slow[0], {}) < total_cost(case, a, {})
