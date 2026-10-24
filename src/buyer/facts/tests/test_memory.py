import json

import pytest
from arena_kit.cost import complete_offer, total_cost
from facts_cases import kit_cases

from buyer.facts import memory as mem
from buyer.facts.profile import bundle_floor, profile

S01 = next(c for c in kit_cases() if c["case_id"] == "case:S01")
LOGGED = mem.observations()  # runs/practice_sessions on this machine (not in git): may be empty


def _session(case, price, best, supplier=None):
    sid = supplier or case["suppliers"][0]
    terms = complete_offer(case, {"unit_price": price})
    c_best = total_cost(case, {**terms, "unit_price": best})
    thread = {"messages": [{"from": "sales", "term_sheets": [{"term_sheet_id": "offer:x-0",
                                                              "terms": {"unit_price": price * 1.1}}]}]}
    return {"session_id": "s1", "case": case, "threads": {sid: thread},
            "result": {"deal": True, "supplier_id": sid, "terms": terms, "c_best": c_best, "score": 0.5}}


def test_best_price_inverts_the_cost_function():
    doc = _session(S01, price=16.0, best=14.2)
    o = mem.observation(doc)
    assert o["best_price"] == pytest.approx(14.2, abs=0.01)
    assert o["deal_price"] == 16.0 and o["opening_price"] == pytest.approx(17.6)


def test_no_deal_is_no_observation():
    doc = _session(S01, 16.0, 14.2)
    doc["result"]["deal"] = False
    assert mem.observation(doc) is None


MEMORY = {"entries": {
    "sup:1|part:A": {"supplier_id": "sup:1", "parts": ["part:A"], "rfq": False, "best_price": 9.0, "estimate": 10.0,
                     "deal_price": 9.5, "opening_price": 11.0, "cases": ["case:X"], "scores": [0.4]},
    "sup:2|part:R": {"supplier_id": "sup:2", "parts": ["part:R"], "rfq": True, "best_price": 5.0, "estimate": 8.0,
                     "deal_price": 6.0, "opening_price": 7.0, "cases": ["case:Y"], "scores": [0.4]}},
    "rfq_caps": {"part:R": 5.0}}


def test_same_supplier_same_part_uses_the_observed_best():
    p = mem.apply_memory({"floor_estimate": 10.0, "floor_confidence": 0.05, "floor_source": "should_cost"},
                         "sup:1", ["part:A"], MEMORY)
    assert p["floor_estimate"] == 9.0 and p["floor_source"] == "observed_best" and p["floor_confidence"] == 0.03
    assert p["floor_computed"] == 10.0 and p["memory"]["cases"] == ["case:X"]
    assert mem.apply_memory(dict(p), "sup:1", ["part:A"], MEMORY) == p  # repeatable


def test_other_parts_of_the_supplier_get_its_bias():
    p = mem.apply_memory({"floor_estimate": 20.0, "floor_source": "own_price"}, "sup:1", ["part:B"], MEMORY)
    assert p["floor_estimate"] == pytest.approx(18.0)  # 20 x (9 / 10)
    assert p["floor_source"] == "own_price+observed_bias"


def test_rfq_best_caps_every_bidder():
    p = mem.apply_memory({"floor_estimate": 7.5, "floor_source": "should_cost"}, "sup:3", ["part:R"], MEMORY)
    assert p["floor_estimate"] == 5.0 and p["floor_source"] == "rfq_observed_best"
    p = mem.apply_memory({"floor_estimate": 4.0, "floor_source": "should_cost"}, "sup:3", ["part:R"], MEMORY)
    assert p["floor_estimate"] == 4.0  # a cap, never a raise


def test_unknown_supplier_is_left_alone():
    p = mem.apply_memory({"floor_estimate": 7.5, "floor_source": "x"}, "sup:9", ["part:Z"], MEMORY)
    assert p["floor_estimate"] == 7.5 and p["floor_source"] == "x"


def test_bundle_floor_is_per_kit(monkeypatch):
    kit = {"case_id": "case:K", "type": "bundling", "parts": ["part:360010", "part:360011", "part:360012"],
           "suppliers": ["sup:70610"], "buyer": {"current_unit_price": 6.29}}
    est, conf, source = bundle_floor(kit, "part:360010")
    assert 5.5 < est <= 6.29 and source == "bundle_current_price" and conf == 0.15
    monkeypatch.setattr(mem, "load", lambda *a: {"entries": {}, "rfq_caps": {}})
    p = profile(kit)["sup:70610"]
    assert p["floor_estimate"] == est  # not the bolt's price per 100 (about 12.34)
    assert set(p["floor_by_part"]) == set(kit["parts"])


def test_committed_memory_is_well_formed():
    m = json.loads(mem.MEMORY_FILE.read_text(encoding="utf-8"))
    assert m["built_from"] > 0 and m["entries"]
    for k, e in m["entries"].items():
        assert k == mem.key(e["supplier_id"], e["parts"]) and e["best_price"] > 0 and e["cases"]


@pytest.mark.skipif(not LOGGED, reason="no session logs in runs/practice_sessions")
def test_no_floor_above_a_logged_best_price():
    """A floor above the best price keeps the policy from ever asking low enough (P02, P05, P08,
    P11, P18 on 2026-10-24). New logs without a rebuilt memory.json fail here."""
    bad = [(r["case_id"], r["supplier_id"], r["floor"], r["best_price"]) for r in mem.check()
           if r["floor"] is None or r["floor"] > r["best_price"] * 1.02]
    assert not bad, f"floors above the logged best price - run `python -m buyer.facts.memory`: {bad}"
