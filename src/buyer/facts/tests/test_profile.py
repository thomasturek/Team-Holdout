import json

import pytest
from facts_cases import practice_cases

from buyer.facts.profile import (
    OVERRIDES_FILE,
    _rows,
    apply_overrides,
    market_price,
    pairs,
    profile,
    profile_all,
    supplier_profile,
)

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
    p = supplier_profile("sup:70140", "part:310020")  # P11: latest price 45.15, castings ratio ~1.03 capped at 1
    assert p["floor_estimate"] == pytest.approx(45.15)


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


# ------------------------------------------------------------------ the 46 suppliers of the final

INTERFACE = {"supplier_id", "name", "country", "owner_type", "archetype", "floor_estimate", "floor_confidence",
             "cash_rate_estimate", "cash_pressure", "approval_style", "cost_drivers", "history", "quality", "notes",
             "standard_terms"}


@pytest.fixture(scope="module")
def all_profiles(tmp_path_factory):
    path = tmp_path_factory.mktemp("profiles") / "all.json"
    with pytest.MonkeyPatch.context() as mp:  # module scope runs before the autouse env fixture
        mp.delenv("ARENA_DATA", raising=False)
        return path, profile_all(path)["profiles"]


def test_profile_all_covers_every_detailed_supplier_and_pair(all_profiles):
    path, profiles = all_profiles
    assert path.is_file()
    expected = {(s, p) for s, p in pairs()}
    assert len({s for s, _ in expected}) == 46
    assert {(s, p) for s, parts in profiles.items() for p in parts} == expected
    assert {(r["supplier_id"], r["part_id"]) for r in _rows("SELECT supplier_id, part_id FROM sourcing")} <= expected


def test_every_profile_is_complete(all_profiles):
    _, profiles = all_profiles
    for sid, parts in profiles.items():
        for part, p in parts.items():
            assert INTERFACE <= set(p), (sid, part, INTERFACE - set(p))
            assert p["name"] and p["name"] != sid
            assert p["archetype"] in ARCHETYPES - {"unknown"}, (sid, p["archetype"])
            assert p["floor_estimate"] and p["floor_estimate"] > 0, (sid, part)
            assert p["approval_style"] in ("flat", "ladder")


def test_market_floor_never_above_todays_price(all_profiles):
    _, profiles = all_profiles
    for sid, parts in profiles.items():
        for part, p in parts.items():
            if p["floor_source"] in ("own_price", "market_price"):
                price, _ = market_price(sid, part)
                assert p["floor_estimate"] <= price + 1e-9, (sid, part)


def test_profile_reads_the_precomputed_file(all_profiles, monkeypatch):
    path, profiles = all_profiles
    import buyer.facts.profile as pr

    monkeypatch.setattr(pr, "computed_profile", lambda *a: pytest.fail("computed although precomputed"))
    p = profile(PRACTICE["case:P01"], path)["sup:70110"]
    assert p["floor_estimate"] == profiles["sup:70110"]["part:310010"]["floor_estimate"]


def test_missing_pair_is_computed_on_the_fly(tmp_path):
    p = profile({"suppliers": ["sup:70110"], "parts": ["part:310011"]}, tmp_path / "none.json")["sup:70110"]
    assert p["part_id"] == "part:310011" and p["floor_estimate"]


def test_overrides_apply_and_are_explained():
    p = supplier_profile("sup:70570", "part:350050")
    assert p["archetype"] == "group_ladder" and p["approval_style"] == "ladder"
    assert any("pricing committee" in why for why in p["overrides"])
    p = supplier_profile("sup:70140", "part:310020")
    assert p["archetype"] == "cash_short_jobshop" and p["cash_pressure"] == 0.6 and p["cash_rate_estimate"] >= 0.176


def test_override_rules():
    overrides = {"sup:1": {"archetype": "group_ladder", "notes": ["n2"], "_why": "because"},
                 "sup:1|part:2": {"floor_estimate": 9.0, "_why": "pair"}}
    computed = {"notes": ["n1"], "approval_style": "flat", "floor_estimate": 5.0}
    p = apply_overrides(computed, "sup:1", "part:2", overrides)
    assert p["archetype"] == "group_ladder" and p["approval_style"] == "ladder"
    assert p["notes"] == ["n1", "n2"] and p["floor_estimate"] == 9.0 and p["overrides"] == ["because", "pair"]
    assert apply_overrides(dict(p), "sup:1", "part:2", overrides) == p  # applying twice changes nothing


def test_every_override_names_its_evidence():
    for key, o in json.loads(OVERRIDES_FILE.read_text(encoding="utf-8")).items():
        if not key.startswith("_"):
            assert o.get("_why"), key


def test_profile_all_stores_claims_and_a_review_sheet(all_profiles):
    path, profiles = all_profiles
    p = profiles["sup:70110"]["part:310010"]
    assert {"notice:sup:70110", "otd:sup:70110"} <= {c["key"] for c in p["claims"]}
    sheet = (path.parent / "review.md").read_text(encoding="utf-8")
    assert sheet.count("\n## ") == 46 and "notice:sup:70110" in sheet
