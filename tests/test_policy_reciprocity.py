"""Reciprocal concessions (policy) and front-loaded-then-hold suppliers (simulator).

Practice 2026-10-24: suppliers held still in 51 % of their replies while our fixed step kept moving
us towards them (P02, P03, P11). Our step now follows theirs."""

import json
import random
from pathlib import Path

import pytest

from buyer.policy.policy import Policy, ThreadState
from buyer.sim.supplier import SupplierParams, SyntheticSupplier

KIT = Path(__file__).resolve().parents[1] / "starter-kit" / "arena_kit" / "sim_cases"
CASE = json.loads((KIT / "S01.json").read_text(encoding="utf-8"))  # unit_price + payment_days
SID = CASE["suppliers"][0]


ON = {"reciprocity": 0.8, "accept_target_pct": 3.0}  # off by default until params.json switches them on


def start(price=20.0, rounds=10, profile=None, **params):
    policy = Policy({**ON, **params})
    t = ThreadState(SID, f"offer:{SID[4:]}-0", {"unit_price": price, "payment_days": 30}, "open",
                    {"payment_days": 30}, rounds, profile=profile or {})
    first = policy.decide(CASE, t)
    assert first.kind == "send"
    return policy, t


def reply(policy, t, price, n):
    t.standing_id, t.standing_terms = f"offer:{SID[4:]}-{n}", {"unit_price": price, "payment_days": 30}
    t.rounds_left -= 1
    before = t.our_prices[-1]
    d = policy.decide(CASE, t)
    return d, (t.our_prices[-1] - before) if d.kind == "send" else None


def test_we_match_a_supplier_step_not_the_gap():
    policy, t = start()
    d, step = reply(policy, t, 19.6, 1)  # it moves 0.40
    assert d.kind == "send" and step == pytest.approx(0.8 * 0.40, abs=0.02)


def test_a_holding_supplier_gets_a_token_step_then_a_hold_with_another_package(monkeypatch):
    monkeypatch.setattr("buyer.policy.policy.VISIBLE_STEP", 0.0)
    policy, t = start()
    reply(policy, t, 19.6, 1)
    _, token = reply(policy, t, 19.6, 2)  # first hold: a token step
    old_step = policy.p["concede"] * (19.6 - (t.our_prices[-1] - token))
    assert 0 < token <= policy.p["token_frac"] * old_step + 0.01
    d, held = reply(policy, t, 19.6, 3)  # second hold: we hold too
    assert d.kind == "send" and held == 0 and t.holding
    assert d.questions == ["cost breakdown"] and "firm on price" in d.intent
    d2, held2 = reply(policy, t, 19.6, 4)
    assert d2.kind == "send" and held2 == 0 and d2.questions == []  # asked once only
    assert d2.term_sheets[0] != d.term_sheets[0] or len(d.term_sheets) == 1  # the lead package changes


def test_a_step_back_is_not_rewarded(monkeypatch):
    monkeypatch.setattr("buyer.policy.policy.VISIBLE_STEP", 0.0)
    policy, t = start()
    reply(policy, t, 19.6, 1)
    d, step = reply(policy, t, 19.9, 2)  # it raises its price
    assert d.kind == "send" and step == 0


def test_endgame_allows_one_bigger_step():
    policy, t = start(rounds=4)
    reply(policy, t, 19.6, 1)
    _, step = reply(policy, t, 19.6, 2)  # rounds_left 2: the endgame, even though it held
    assert step >= policy.p["endgame_frac"] * (19.6 - (t.our_prices[-1] - step)) - 0.01


def test_reciprocity_zero_is_the_old_fixed_step():
    policy, t = start(reciprocity=0)
    last = t.our_prices[-1]
    _, step = reply(policy, t, 19.6, 1)
    assert step == pytest.approx(policy.p["concede"] * (19.6 - last), abs=0.01)


def test_accept_at_a_sure_target_only():
    sure = {"floor_estimate": 19.0, "floor_confidence": 0.03}
    policy, t = start(profile=sure, accept_gap_pct=0)  # isolate the target from the old "close to us" rule
    d, _ = reply(policy, t, 19.5, 1)  # within 3 % of an observed floor
    assert d.kind == "accept"
    policy, t = start(profile={**sure, "floor_confidence": 0.15}, accept_gap_pct=0)
    d, _ = reply(policy, t, 19.5, 1)  # an unsure floor never decides
    assert d.kind == "send"


# ------------------------------------------------------------------ the simulated supplier

def supplier(**kw):
    p = dict(full_cost=15.0, open_margin=0.25, min_margin=0.0, cash_rate=0.08, concede=0.3, approval_step_pct=50.0,
             patience=1, walk_after_final=0.0, std_payment_days=30)
    return SyntheticSupplier(CASE, SID, SupplierParams(**{**p, **kw}), random.Random(1))


def sheet(price, days=30):
    return {"unit_price": price, "payment_days": days}


def test_holder_stops_after_its_steps_unless_a_lever_moves_it():
    s = supplier(hold_after=1, decay=0.3)
    asks = [s.opening()["terms"]["unit_price"]]
    for price in (15.0, 15.5, 16.0, 16.5):
        asks.append(s.respond([sheet(price)])["terms"]["unit_price"])
    assert asks[1] < asks[0]  # the front-loaded step
    assert asks[2] == asks[3] == asks[4]  # then it holds although we kept moving
    moved = s.respond([sheet(16.6, days=14)])["terms"]["unit_price"]  # faster payment is worth something to it
    assert moved < asks[4]


def test_it_reads_every_package():
    s = supplier()
    r = s.respond([sheet(15.0), sheet(17.5)])  # the second package is worth more to it
    assert r["status"] == "agreed" or r["terms"]["unit_price"] <= s.opening()["terms"]["unit_price"]
    assert s.best_seen["unit_price"] == 17.5


def test_a_buyer_who_stops_moving_gets_a_final_offer_not_a_walk_out():
    s = supplier(patience=1)
    s.respond([sheet(15.0)])
    statuses = [s.respond([sheet(15.0)])["status"] for _ in range(3)]
    assert "final_offer" in statuses and statuses[0] != "walked_away"


def test_off_by_default():
    p = Policy({})
    assert p.p["reciprocity"] == 0 and p.p["accept_target_pct"] == 0
