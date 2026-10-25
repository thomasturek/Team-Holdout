import json
from pathlib import Path

import pytest
from arena_kit.cost import must_haves_ok, total_cost

from buyer.policy.policy import Policy, ThreadState, load_params

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


@pytest.mark.parametrize("case_id, quote", [
    ("case:P02", {"unit_price": 370.96, "payment_days": 30, "index_clause": None}),
    ("case:P08", {"unit_price": 6.05, "payment_days": 30, "contract_months": 12, "index_clause": None}),
])
def test_the_packages_are_worth_the_same_to_the_supplier_and_cheapest_for_us(case_id, quote):
    case = practice(case_id)
    t = ThreadState("sup:x", "offer:x-1", quote, "open", {"payment_days": 30}, 9)
    p = Policy({"claims_per_msg": 0})
    sheets = p.decide(case, t).term_sheets
    model = p.supplier_model(case, t)
    worth = [p.worth(case, s, model) for s in sheets]
    costs = [total_cost(case, s, {"payment_days": 30}) for s in sheets]
    assert len(sheets) >= 2
    assert max(worth) - min(worth) < 0.01 * sheets[0]["unit_price"]
    assert max(costs) <= min(costs) * 1.003 + 1
    assert all(c < total_cost(case, quote, {"payment_days": 30}) for c in costs)


def test_no_package_costs_us_more_at_the_suppliers_own_price():
    case = practice("case:P03")
    quote = {"unit_price": 438.21, "payment_days": 30, "contract_months": 12, "volume_per_year": 4580}
    t = ThreadState("sup:x", "offer:x-1", quote, "open", {"payment_days": 30}, 9)
    p = Policy({"claims_per_msg": 0})
    sheets = p.decide(case, t).term_sheets
    assert sheets and all(s["payment_days"] >= 45 for s in sheets)


def test_a_chargeback_the_supplier_pays_for_is_traded_for_price():
    case = practice("case:P11")
    quote = {"unit_price": 47.0, "ppm_commitment": 6400, "chargeback_eur_per_complaint": 0}
    t = ThreadState("sup:x", "offer:x-1", quote, "open", {}, 9)
    sheets = Policy({"claims_per_msg": 0}).decide(case, t).term_sheets
    assert sheets[0]["chargeback_eur_per_complaint"] == 0
    assert all(must_haves_ok(case, s, {}) for s in sheets)


def test_a_floor_that_stops_our_concession_holds_instead_of_closing():
    from buyer.runtime.agent import scout_profiles

    case = practice("case:P01")
    sid = "sup:70110"
    quote = {"unit_price": 138.55, "effective_date": "2026-11-01"}
    std = {"payment_days": 30, "ppm_commitment": 900, "chargeback_eur_per_complaint": 0.0}
    p = Policy({**load_params(), "claims_per_msg": 0})
    t = ThreadState(sid, "offer:70110-0", quote, "open", std, 9, profile=scout_profiles(case)[sid])
    assert p.decide(case, t).kind == "send"
    t.standing_id = "offer:70110-1"
    t.standing_terms = {"unit_price": 138.6, "payment_days": 45, "effective_date": "2027-04-01"}
    t.rounds_left = 8
    assert p.decide(case, t).kind == "send"


def test_a_lever_trade_never_costs_us_more_at_the_suppliers_own_price():
    case = practice("case:P03")
    quote = {"unit_price": 438.21, "payment_days": 30, "contract_months": 12, "volume_per_year": 4580}
    p = Policy({**load_params(), "claims_per_msg": 0})
    from buyer.runtime.agent import scout_profiles

    std = {"payment_days": 30, "incoterm": "DAP"}
    t = ThreadState("sup:70530", "offer:1", quote, "open", std, 9, profile=scout_profiles(case)["sup:70530"])
    first = p.decide(case, t)
    t.standing_id = "offer:2"
    t.standing_terms = {**first.term_sheets[0], "unit_price": 431.63, "payment_days": 90}
    t.rounds_left, t.signals = 8, {"asks": ["volume", "forecast"]}
    assert all(s["payment_days"] >= 45 for s in p.decide(case, t).term_sheets)


def test_the_index_clause_trade_survives_with_the_long_payment_term():
    from buyer.runtime.agent import scout_profiles

    case = practice("case:P02")
    sid = "sup:70510"
    quote = {"unit_price": 370.96, "payment_days": 30, "index_clause": None}
    p = Policy({**load_params(), "claims_per_msg": 0})
    t = ThreadState(sid, "offer:1", quote, "open", {"payment_days": 30}, 9, profile=scout_profiles(case)[sid])
    t.signals = {"cost_drivers_claimed": ["CU-NOTATION", "LCI-C", "PPI-C241"]}
    clause_sheets = [s for s in p.decide(case, t).term_sheets if s.get("index_clause")]
    assert clause_sheets and clause_sheets[0]["payment_days"] == 90
