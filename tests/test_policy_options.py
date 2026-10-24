"""Policy.best_options and the counter it builds on practice case P11 (quality first, ppm <= 1500).

P11 regression: the supplier offered ppm 2500 with chargeback 500. Under that chargeback every ppm
costs us the same, and handing the supplier back its own ppm broke the must-have - every later offer
was unacceptable and the agent walked away from a final offer.
"""

import json
from pathlib import Path

import pytest
from arena_kit.cost import must_haves_ok

from buyer.policy.policy import Policy, ThreadState

CASES = Path(__file__).resolve().parents[1] / "runs" / "cases" / "practice.json"
SID = "sup:70140"


@pytest.fixture
def case():
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    cases = cases if isinstance(cases, list) else list(cases.values())
    return next(c for c in cases if c["case_id"] == "case:P11")


def test_best_options_keep_the_must_haves(case):
    theirs = {"unit_price": 47.5, "ppm_commitment": 2500, "chargeback_eur_per_complaint": 500.0}
    out = Policy.best_options(case, theirs, {})
    assert must_haves_ok(case, out, {})
    assert out["ppm_commitment"] == 1500  # the allowed ppm closest to theirs: free for us under chargeback 500
    assert out["chargeback_eur_per_complaint"] == 500.0


def test_the_counter_to_a_must_have_breaking_offer_keeps_the_must_haves(case):
    terms = {"unit_price": 48.5, "ppm_commitment": 2500, "chargeback_eur_per_complaint": 500.0}
    t = ThreadState(SID, "offer:70140-1", terms, "open", {}, 5)
    decision = Policy({"claims_per_msg": 0}).decide(case, t)
    assert decision.kind == "send"
    assert all(must_haves_ok(case, s, {}) for s in decision.term_sheets)
