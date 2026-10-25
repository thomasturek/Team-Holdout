"""Three fixes from the night's ceiling analysis (runs/night/out/fable_ceiling.md): walk faster against
mirroring suppliers, close instead of an identical resend, and keep the supplier's own lead time on the
table."""

import copy
import json
from pathlib import Path

import pytest
from arena_kit.cost import complete_offer, total_cost

from buyer.policy.policy import Decision, Policy, ThreadState

KIT = Path(__file__).resolve().parents[1] / "starter-kit" / "arena_kit" / "sim_cases"
S01 = json.loads((KIT / "S01.json").read_text(encoding="utf-8"))  # unit_price + payment_days, no alternative
S02 = json.loads((KIT / "S02.json").read_text(encoding="utf-8"))  # + lead_time_days options 21..49


def thread(case, terms, ours=(), theirs=(), rounds=6):
    sid = case["suppliers"][0]
    t = ThreadState(sid, f"offer:{sid[4:]}-{len(theirs)}", dict(terms), "open", {"payment_days": 30}, rounds)
    t.our_prices, t.their_prices = list(ours), list(theirs)
    return t


# --- mirroring suppliers --------------------------------------------------------------------------------
def test_a_mirroring_supplier_gets_a_bigger_step():
    # ours +1.0, +0.8 -> its -0.8, -0.7 (ratios 0.8, 0.875): it mirrors
    t = thread(S01, {"unit_price": 134.8}, ours=[128.0, 129.0, 129.8], theirs=[140.0, 136.3, 135.5, 134.8])
    gap, default = 134.8 - 129.8, 0.1
    step = Policy().mirror_step(t, 134.8, gap, default)
    assert step == pytest.approx(0.3 * gap)  # at least mirror_frac of the gap
    assert step <= gap - 1.5 * 0.7  # and below where its next mirrored step lands


def test_a_fixed_stepper_or_a_silent_supplier_keeps_the_normal_step():
    # Werdenfels: -0.10 per reply whatever we do; ours +0.10 then +0.06 -> ratios 1.0 and 1.67
    t = thread(S01, {"unit_price": 5.10}, ours=[4.80, 4.90, 4.96], theirs=[5.40, 5.30, 5.20, 5.10])
    assert Policy().mirror_step(t, 5.10, 0.14, 0.02) == 0.02
    held = thread(S01, {"unit_price": 46.0}, ours=[44.0, 44.2, 44.4], theirs=[47.0, 46.0, 46.0, 46.0])
    assert Policy().mirror_step(held, 46.0, 1.6, 0.2) == 0.2  # it held: no mirroring
    short = thread(S01, {"unit_price": 134.8}, ours=[128.0, 129.0], theirs=[140.0, 136.3, 135.5])
    assert Policy().mirror_step(short, 134.8, 5.8, 0.7) == 0.7  # one ratio is not enough


def test_the_mirror_step_never_shrinks_our_step_and_can_be_switched_off():
    t = thread(S01, {"unit_price": 134.8}, ours=[128.0, 129.0, 129.8], theirs=[140.0, 136.3, 135.5, 134.8])
    assert Policy().mirror_step(t, 134.8, 5.0, 4.0) == 4.0
    assert Policy({"mirror_frac": 0.0}).mirror_step(t, 134.8, 5.0, 0.1) == 0.1
    misaligned = thread(S01, {"unit_price": 134.8}, ours=[128.0, 129.0, 129.8], theirs=[140.0, 134.8])
    assert Policy().mirror_step(misaligned, 134.8, 5.0, 0.1) == 0.1


def test_decide_walks_faster_against_a_mirroring_supplier_end_to_end():
    def play(policy):
        t = thread(S01, {"unit_price": 140.0, "payment_days": 30}, theirs=[140.0], rounds=8)
        policy.decide(S01, t)
        price = 140.0
        for n in range(1, 4):  # it answers each of our steps with 0.8 of it
            step = t.our_prices[-1] - (t.our_prices[-2] if len(t.our_prices) > 1 else t.our_prices[-1] - 4.0)
            price = round(price - 0.8 * step, 2)
            t.standing_id, t.standing_terms = f"offer:x-{n}", {"unit_price": price, "payment_days": 30}
            t.their_prices.append(price)
            t.rounds_left -= 1
            if policy.decide(S01, t).kind != "send":
                break
        return t.our_prices

    fast, slow = play(Policy()), play(Policy({"mirror_frac": 0.0}))
    assert fast[-1] - fast[-2] > slow[-1] - slow[-2]  # the last step is bigger with the mirror rule


# --- no identical resend ---------------------------------------------------------------------------------
def test_an_identical_resend_at_its_price_becomes_an_accept(monkeypatch):
    policy = Policy()
    sheet = complete_offer(S01, {"unit_price": 5.05, "payment_days": 45})
    t = thread(S01, {"unit_price": 5.05, "payment_days": 45}, ours=[4.9, 5.0, 5.05], theirs=[5.4, 5.2, 5.1, 5.05])
    t.last_sheet, t.opening_cost, t.our_costs = dict(sheet), 10**9, [1.0]  # our_costs low: no early close

    def same_offer(case, tt, price, **kw):
        tt.holding = True  # offer() marks a repeated sheet as a hold
        return Decision("send", tt.supplier_id, term_sheets=[dict(sheet)])

    monkeypatch.setattr(policy, "offer", same_offer)
    assert policy.decide(S01, t).kind == "accept"


def test_a_repeated_sheet_below_its_price_is_still_a_hold(monkeypatch):
    policy = Policy()
    sheet = complete_offer(S01, {"unit_price": 5.00, "payment_days": 45})
    t = thread(S01, {"unit_price": 5.20, "payment_days": 45}, ours=[4.9, 5.0], theirs=[5.4, 5.3, 5.2])
    t.last_sheet, t.opening_cost, t.our_costs = dict(sheet), 10**9, [1.0]

    def same_offer(case, tt, price, **kw):
        tt.holding = True
        return Decision("send", tt.supplier_id, term_sheets=[dict(sheet)])

    monkeypatch.setattr(policy, "offer", same_offer)
    assert policy.decide(S01, t).kind == "send"  # it is above our price: holding on is deliberate


# --- the supplier's own lead time ------------------------------------------------------------------------
def test_its_own_longer_lead_time_rides_along_at_equal_cost():
    a = complete_offer(S02, {"unit_price": 16.0, "payment_days": 60, "lead_time_days": 28})
    t = thread(S02, {"unit_price": 17.0, "payment_days": 60, "lead_time_days": 49})
    own = Policy().own_lead_sheet(S02, t, a)
    assert own is not None and own["lead_time_days"] == 49
    tick = total_cost(S02, {**a, "unit_price": a["unit_price"] + 0.01}, t.standard) - total_cost(S02, a, t.standard)
    assert abs(total_cost(S02, own, t.standard) - total_cost(S02, a, t.standard)) <= tick  # equal up to 1 cent


def test_no_own_lead_sheet_when_it_breaks_a_must_have_or_is_not_longer():
    strict = copy.deepcopy(S02)
    strict["buyer"]["must_haves"] = [{"field": "lead_time_days", "op": "<=", "value": 42}]
    a = complete_offer(strict, {"unit_price": 16.0, "payment_days": 60, "lead_time_days": 28})
    t = thread(strict, {"unit_price": 17.0, "payment_days": 60, "lead_time_days": 49})
    assert Policy().own_lead_sheet(strict, t, a) is None
    same = thread(S02, {"unit_price": 17.0, "payment_days": 60, "lead_time_days": 28})
    assert Policy().own_lead_sheet(S02, same, a) is None
    assert Policy().own_lead_sheet(S01, thread(S01, {"unit_price": 5.0}), {"unit_price": 4.9}) is None
