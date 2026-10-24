import pytest
from facts_cases import practice_cases

from buyer.facts.profile import profile, supplier_profile

PRACTICE = {c["case_id"]: c for c in practice_cases()}
ARCHETYPES = {"family_foundry", "group_ladder", "cash_short_jobshop", "near_monopolist", "unknown"}


@pytest.mark.parametrize("case_id", sorted(PRACTICE))
def test_every_practice_supplier_has_a_floor(case_id):
    case = PRACTICE[case_id]
    p = profile(case)[case["suppliers"][0]]
    assert p["floor_estimate"] and p["floor_estimate"] > 0
    assert 0 < p["floor_confidence"] <= 0.15
    assert p["archetype"] in ARCHETYPES
    assert p["approval_style"] in ("flat", "ladder")
    assert 0 <= p["cash_pressure"] <= 1 and p["cash_rate_estimate"] >= 0.08


@pytest.mark.parametrize("case_id", ["case:P04", "case:P07", "case:P08", "case:P11", "case:P18"])
def test_gap_cases_use_the_market_price(case_id):
    case = PRACTICE[case_id]
    p = profile(case)[case["suppliers"][0]]
    assert p["floor_source"] in ("own_price", "market_price")
    assert p["floor_confidence"] == 0.15


def test_floor_is_close_to_current_price():
    p = supplier_profile("sup:70140", "part:310020")  # P11: latest price 45.15, castings ratio ~1.03
    assert 43 < p["floor_estimate"] < 48


def test_bundle_has_a_floor_per_part():
    case = PRACTICE["case:P07"]
    floors = profile(case)["sup:70610"]["floor_by_part"]
    assert set(floors) == set(case["parts"]) and all(f and f > 0 for f in floors.values())


def test_archetypes():
    assert supplier_profile("sup:70110", "part:310010")["archetype"] == "family_foundry"
    assert supplier_profile("sup:70510", "part:350011")["archetype"] == "group_ladder"
    assert supplier_profile("sup:70510", "part:350011")["approval_style"] == "ladder"
    assert supplier_profile("sup:70410", "part:340010")["archetype"] == "near_monopolist"  # group, sole source
    p = supplier_profile("sup:70280", "part:320011")  # credit 230 -> 302, short-time work, overdue invoices
    assert p["archetype"] == "cash_short_jobshop" and p["cash_pressure"] >= 0.5 and p["cash_reasons"]


def test_new_supplier_still_gets_the_part_floor():
    p = supplier_profile("sup:99999", "part:310010")  # hidden cases bring new suppliers
    assert p["archetype"] == "unknown" and p["floor_estimate"] == pytest.approx(132.64)
