"""A standing offer that breaks a must-have, with no eligible rival: walking scores the alternative (0 in
11 of 12 practice cases), and so does a counter the supplier walks away from - so counter once more."""

import json
import math
from pathlib import Path

from arena_kit.cost import must_haves_ok

from buyer.policy.policy import Policy, ThreadState

CASES = Path(__file__).resolve().parents[1] / "runs" / "cases" / "practice.json"


def practice(case_id):
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    cases = cases if isinstance(cases, list) else list(cases.values())
    return next(c for c in cases if c["case_id"] == case_id)


def policy():
    return Policy({"claims_per_msg": 0})


def p10_final(rounds_left):
    # its final offer leaves the volume out: its standard 16,379 / year breaks volume >= 22,230 (no alternative)
    t = ThreadState("sup:x", "offer:x-5", {"unit_price": 29.59}, "final_offer",
                    {"volume_per_year": 16379, "contract_months": 12, "lead_time_days": 35}, rounds_left)
    t.our_prices = [28.88]
    return t


def test_a_final_offer_breaking_a_must_have_gets_its_own_terms_back_with_the_must_have_met():
    case = practice("case:P10")
    d = policy().decide(case, p10_final(5))
    assert d.kind == "send" and len(d.term_sheets) == 1
    s = d.term_sheets[0]
    assert set(s) == set(case["negotiable"]) and must_haves_ok(case, s, {})
    assert s["unit_price"] == 29.59 and s["volume_per_year"] == 23400
    assert s["contract_months"] == 12 and s["lead_time_days"] == 35  # its other terms unchanged


def test_after_the_round_limit_it_still_walks():
    assert policy().decide(practice("case:P10"), p10_final(0)).kind == "walk"


def test_the_last_round_sends_the_rescue_and_the_next_decision_accepts_its_agreement():
    case = practice("case:P11")
    t = ThreadState("sup:70140", "offer:70140-9", {"unit_price": 46.0, "ppm_commitment": 2500,
                    "chargeback_eur_per_complaint": 500.0}, "open", {"payment_days": 60}, 1)
    t.our_prices = [45.8]
    p = policy()
    d = p.decide(case, t)
    assert d.kind == "send" and d.term_sheets[0]["ppm_commitment"] <= 1500 and d.term_sheets[0]["unit_price"] == 46.0
    t.status, t.standing_id, t.standing_terms, t.rounds_left = "agreed", "offer:70140-10", d.term_sheets[0], 0
    assert p.decide(case, t).kind == "accept"


def test_with_an_eligible_rival_it_still_walks():
    case = practice("case:P10")
    assert policy().decide(case, p10_final(5), rival_best_c=1.0e6).kind == "walk"


def test_dearer_than_the_alternative_gets_one_repair_below_the_alternative_not_a_rescue():
    # must-haves kept, only dearer than the current contract: not the rescue's job. Thomas's repair (main,
    # 1d155b0) counters once below the alternative - a walk-away by the supplier costs no more than ours
    from buyer.policy.policy import alternative_cost

    case = practice("case:P07")  # current contract at 6.29
    t = ThreadState("sup:70610", "offer:70610-4", {"unit_price": 6.40, "payment_days": 30, "contract_months": 12},
                    "final_offer", {"payment_days": 30}, 6)
    t.our_prices = [5.3]
    p = policy()
    d = p.decide(case, t, rival_best_c=math.inf)
    assert d.kind == "send" and p.c(case, d.term_sheets[0], t) < alternative_cost(case)
    assert "only our must-have term differs" not in d.intent  # the repair, not the rescue
    assert p.decide(case, t, rival_best_c=math.inf).kind == "walk"  # once only: then it walks as before


def test_an_unread_quote_never_makes_a_left_out_must_have_field_eligible():
    case = practice("case:P05")  # lead time <= 42; Hrvelec leaves it out, its standard is 52 days
    p = policy()
    unread = ThreadState("sup:70240", "offer:70240-3", {"unit_price": 31.5, "payment_days": 30}, "open", {}, 6)
    known = ThreadState("sup:70210", "offer:70210-3", {"unit_price": 33.0, "payment_days": 30, "lead_time_days": 42},
                        "open", {}, 6)
    assert p.eligible_cost(case, unread) is None and p.eligible_cost(case, known) is not None
    d = p.closing(case, {"sup:70240": unread, "sup:70210": known})
    assert d.kind == "accept" and d.supplier_id == "sup:70210"


def test_a_lone_supplier_with_an_unread_quote_gets_the_must_have_stated_not_a_walk():
    # unread quote, lead time left out, no other bidder: the guard makes it ineligible, so the rescue must
    # state the must-have field explicitly - a walk would be a certain 0
    case = practice("case:P05")
    t = ThreadState("sup:70240", "offer:70240-5", {"unit_price": 31.5, "payment_days": 30}, "final_offer", {}, 3)
    t.our_prices = [30.0]
    d = policy().decide(case, t)
    assert d.kind == "send" and d.term_sheets[0]["lead_time_days"] <= 42 and d.term_sheets[0]["unit_price"] == 31.5
