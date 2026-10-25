"""Lever trades: give the supplier a term it values at equal cost to us.

Practice 2026-10-25: every losing deal closed at the supplier's holding price; our sheets only ever varied
the payment days while suppliers asked for volume, longer contracts and index clauses (P03, P07, P08, P18)."""

import json
from pathlib import Path

import pytest

from buyer.facts.costing import asked, c, lever_values
from buyer.policy.policy import MAX_TRADE_DROP, Policy, ThreadState

ROOT = Path(__file__).resolve().parents[1]
CASES_FILE = ROOT / "runs" / "cases" / "practice.json"
CASES = {x["case_id"]: x for x in json.loads(CASES_FILE.read_text(encoding="utf-8"))} if CASES_FILE.is_file() else {}
pytestmark = pytest.mark.skipif(not CASES, reason="no runs/cases/practice.json")

P03_TERMS = {"unit_price": 430.31, "payment_days": 60, "contract_months": 24, "volume_per_year": 4580}
CLAUSE0 = {"series": "AS-14404", "material_share": 0.45, "deadband_pct": 0, "base_month": "2026-08"}
P18_TERMS = {"unit_price": 5.6, "payment_days": 60, "contract_months": 24, "index_clause": CLAUSE0}


def test_equal_cost_sheets_cost_us_the_same():
    case = CASES["case:P03"]
    for v in lever_values(case, P03_TERMS, {}, {}):
        if v["sheet"]:
            units = v["sheet"]["volume_per_year"] * 2  # a cent of rounding on every unit of the horizon
            assert c(case, v["sheet"], {}, {}) == pytest.approx(c(case, P03_TERMS, {}, {}), abs=0.01 * units + 1)


def test_a_contract_beyond_the_horizon_is_free_and_answers_longer_contract():
    case = CASES["case:P03"]  # 2-year horizon: 36 months neither costs nor earns
    v = next(v for v in lever_values(case, P03_TERMS, {}, {}) if v["field"] == "contract_months" and v["option"] == 36)
    assert v["delta_c"] == 0 and asked(v, P03_TERMS, ["longer_contract"])
    assert not asked(v, P03_TERMS, ["faster_payment"])


def thread(case, terms, asks=(), holding=False, profile=None):
    t = ThreadState(case["suppliers"][0], "offer:x-1", dict(terms), "open", {"payment_days": 30}, 8,
                    profile=profile or {}, signals={"asks": list(asks)})
    t.holding = holding
    return t


def test_an_asked_lever_is_offered_at_equal_cost():
    case = CASES["case:P03"]
    policy = Policy({})
    t = thread(case, P03_TERMS, asks=["longer_contract"])
    trades = policy.lever_trades(case, t, P03_TERMS, ["longer_contract"])
    assert any(x["contract_months"] == 36 and x["unit_price"] == pytest.approx(430.31) for x in trades)
    # more volume would cost us far more than 5 % of the price: not offered, though asked
    assert not policy.lever_trades(case, t, P03_TERMS, ["volume"])


def _p03_with_faster_payment_asked(lever_trades):
    case = CASES["case:P03"]
    t = thread(case, {**P03_TERMS, "unit_price": 438.21}, asks=["faster_payment"])
    return Policy({"lever_trades": lever_trades}).decide(case, t)


def test_trades_enter_the_message_when_asked():
    d = _p03_with_faster_payment_asked(1)
    assert d.kind == "send" and "other terms" in d.intent
    assert any(s["payment_days"] == 45 for s in d.term_sheets)


def test_no_trades_when_switched_off():
    d = _p03_with_faster_payment_asked(0)
    assert "other terms" not in d.intent
    assert not any(s["payment_days"] == 45 for s in d.term_sheets)


def test_a_free_longer_contract_is_not_forced_on_the_supplier():
    d = _p03_with_faster_payment_asked(0)
    assert all(s["contract_months"] == P03_TERMS["contract_months"] for s in d.term_sheets)


def test_a_clause_worth_little_to_the_supplier_is_not_adopted():
    """Distributors value their alloy clause at 0.4-2.7 % of the price; keeping our fixed sheet closed
    P18 at 5.00 against 5.10 when the clause was taken (EHL 2026 winners' log, 15 runs)."""
    case = CASES["case:P18"]
    policy = Policy({})
    t = thread(case, P18_TERMS)
    t.offers = [("offer:x-1", dict(P18_TERMS))]  # it insists on the clause with 0 % deadband
    d = policy.decide(case, t)
    assert d.kind == "send"
    assert all(not s.get("index_clause") for s in d.term_sheets)


def test_an_insisted_clause_worth_a_lot_is_countered_with_the_cheapest_deadband():
    case = CASES["case:P02"]
    clause = {"series": "CU-NOTATION", "material_share": 0.2, "deadband_pct": 0, "base_month": "2026-08"}
    terms = {"unit_price": 370.96, "payment_days": 30, "index_clause": clause}
    t = thread(case, terms, profile={"cost_drivers": [{"series": "CU-NOTATION", "change_12m_pct": 47.73}]})
    t.offers = [("offer:x-1", dict(terms))]
    d = Policy({}).decide(case, t)
    assert d.kind == "send"
    assert any((s.get("index_clause") or {}).get("deadband_pct") == 5 for s in d.term_sheets)


def test_no_trade_cuts_the_price_by_more_than_the_limit():
    case = CASES["case:P18"]
    policy = Policy({})
    t = thread(case, P18_TERMS, asks=["index_clause", "volume", "longer_contract"])
    for x in policy.lever_trades(case, t, P18_TERMS, t.signals["asks"]):
        assert P18_TERMS["unit_price"] - x["unit_price"] <= MAX_TRADE_DROP * P18_TERMS["unit_price"] + 0.01


# ------------------------------------------------------------------ the closing step keeps the cheap deadband

def test_mirroring_its_alternative_offers_the_wider_deadband_first():
    """P18 2026-10-24: the close step copied the supplier's alternative with a 0 % deadband as-is."""
    case = CASES["case:P18"]
    policy = Policy({})
    t = thread(case, {**P18_TERMS, "unit_price": 5.7})
    alt = {**P18_TERMS, "unit_price": 5.5}
    t.offers = [("offer:x-1", dict(t.standing_terms)), ("offer:x-1-a", alt)]
    policy.pick_offer(case, t)
    d = policy.close(case, t, True, policy.cost(case, t), float("inf"))
    assert d.kind == "send" and len(d.term_sheets) == 1
    (first,) = d.term_sheets
    assert first["index_clause"]["deadband_pct"] == 5 and first["unit_price"] == 5.5
    assert policy.c(case, first, t) < policy.c(case, alt, t)


def test_closing_on_an_open_offer_counters_the_deadband_once_then_accepts():
    case = CASES["case:P18"]
    policy = Policy({})
    t = thread(case, P18_TERMS)
    t.offers = [("offer:x-1", dict(P18_TERMS))]
    d = policy.close(case, t, True, policy.cost(case, t), float("inf"))
    assert d.kind == "send" and all(s["index_clause"]["deadband_pct"] == 5 for s in d.term_sheets)
    assert policy.close(case, t, True, policy.cost(case, t), float("inf")).kind == "accept"  # only once


def test_no_counter_without_a_clause():
    case = CASES["case:P03"]
    policy = Policy({})
    t = thread(case, P03_TERMS)
    assert policy.close(case, t, True, policy.cost(case, t), float("inf")).kind == "accept"


def test_a_final_that_breaks_a_must_have_gets_one_repair_counter_not_a_walk():
    case = CASES["case:P10"]
    policy = Policy({})
    final = {"unit_price": 31.7, "volume_per_year": 16379, "contract_months": 36, "lead_time_days": 56}
    t = thread(case, final)
    t.status = "final_offer"
    t.offers = [("offer:x-1", dict(final))]
    d = policy.decide(case, t)
    assert d.kind == "send" and len(d.term_sheets) == 1
    assert d.term_sheets[0]["volume_per_year"] >= 22230 and d.term_sheets[0]["unit_price"] == 31.7
    t.standing_id = "offer:x-2"
    assert policy.decide(case, t).kind == "walk"


def test_an_opening_without_a_price_gets_an_offer_not_a_walk():
    case = CASES["case:P10"]
    policy = Policy({})
    t = thread(case, {"volume_per_year": 23400})
    d = policy.decide(case, t)
    assert d.kind == "send" and d.term_sheets and d.term_sheets[0]["unit_price"] > 0
