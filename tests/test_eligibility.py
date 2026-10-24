"""One eligibility rule for rivals, acceptance and the closing move (Policy.eligible_cost).

The case is the kit's RFQ S02 with the must-have of practice case P05 (lead time <= 42 days): a
bidder quoting 49 days can never be accepted, so it must not count as a rival either.
"""

import json
import math
import random
from pathlib import Path

import arena_kit
import pytest

from buyer.policy.policy import Policy, ThreadState
from buyer.runtime.agent import PolicyAgent

A, B = "sup:70340", "sup:70360"


@pytest.fixture
def case():
    c = json.loads((Path(arena_kit.__file__).parent / "sim_cases" / "S02.json").read_text(encoding="utf-8"))
    c["buyer"]["must_haves"] = [{"field": "lead_time_days", "op": "<=", "value": 42}]
    return c


def thread(sid, price, lead, status="open", n=1, **kw):
    terms = {"unit_price": price, "payment_days": 60, "lead_time_days": lead}
    return ThreadState(sid, f"offer:{sid[4:]}-{n}", terms, status, {}, 5, **kw)


def policy():
    return Policy({"claims_per_msg": 0})  # claims are not what these tests are about


def test_a_cheaper_rival_that_breaks_a_must_have_does_not_block_an_agreed_offer(case):
    p = policy()
    states = {A: thread(A, 16.00, 42, "agreed"), B: thread(B, 14.00, 49)}
    assert p.cost(case, states[B]) < p.cost(case, states[A])  # B is cheaper - and breaks lead time <= 42
    rival = p.rival_best(case, states, states[A])
    assert rival == math.inf
    decision = p.decide(case, states[A], rival_best_c=rival)
    assert decision.kind == "accept" and decision.accept_sheet_id == states[A].standing_id


def test_a_rival_breaking_a_must_have_only_through_its_standard_terms_is_not_eligible(case):
    p = policy()
    b = thread(B, 14.00, 42)
    del b.standing_terms["lead_time_days"]  # its sheet leaves the lead time out ...
    b.standard = {"lead_time_days": 49}  # ... so the deal would close on its standard 49 days
    assert p.eligible_cost(case, b) is None


def test_a_bidder_we_walked_away_from_is_no_rival_but_still_closable(case):
    p = policy()
    states = {A: thread(A, 16.00, 42, "agreed"), B: thread(B, 14.00, 35, dropped=True)}
    assert p.rival_best(case, states, states[A]) == math.inf
    assert p.decide(case, states[A], rival_best_c=math.inf).kind == "accept"
    closing = p.closing(case, {B: states[B]})  # at the cap a live eligible offer still beats no deal
    assert closing.kind == "accept" and closing.supplier_id == B


def test_offers_without_a_standing_id_or_a_price_are_ignored(case):
    p = policy()
    no_id = thread(B, 14.00, 35)
    no_id.standing_id = None
    no_price = thread(B, None, 35)
    for rival in (no_id, no_price):
        states = {A: thread(A, 16.00, 42), B: rival}
        assert p.rival_best(case, states, states[A]) == math.inf


def test_an_agreed_offer_with_a_cheaper_eligible_rival_gets_a_counter_not_a_walk_away(case):
    p = policy()
    states = {A: thread(A, 16.00, 42, "agreed"), B: thread(B, 14.00, 35)}
    rival = p.rival_best(case, states, states[A])
    assert rival == p.cost(case, states[B])
    decision = p.decide(case, states[A], rival_best_c=rival)
    assert decision.kind == "send" and decision.term_sheets
    assert p.cost(case, ThreadState(A, None, decision.term_sheets[0], "open", {}, 5)) < p.cost(case, states[A])


def test_without_rounds_left_an_agreed_but_beaten_offer_is_left(case):
    p = policy()
    states = {A: thread(A, 16.00, 42, "agreed"), B: thread(B, 14.00, 35)}
    states[A].rounds_left = 1
    assert p.decide(case, states[A], rival_best_c=p.rival_best(case, states, states[A])).kind == "walk"


def test_the_closing_move_takes_the_cheapest_eligible_offer(case):
    p = policy()
    states = {A: thread(A, 16.00, 42), B: thread(B, 14.00, 49)}
    closing = p.closing(case, states)
    assert closing.kind == "accept" and closing.supplier_id == A


def message(sid, price, lead, status, n):
    sheet = {"term_sheet_id": f"offer:{sid[4:]}-{n}", "terms": {"unit_price": price, "payment_days": 60,
                                                                  "lead_time_days": lead}}  # fmt: skip
    return {"from": f"sales@{sid[4:]}", "subject": "Quote", "body": "Our offer.", "status": status,
            "term_sheets": [sheet], "attachments": [], "claim_results": []}  # fmt: skip


def test_the_runtime_agent_passes_only_eligible_rivals_to_the_policy(case):
    agent = PolicyAgent({"claims_per_msg": 0})
    threads = {A: [message(A, 16.00, 42, "agreed", 1)], B: [message(B, 14.00, 49, "open", 1)]}
    move = agent.decide(case, threads, A)
    assert move["message"]["action"] == {"type": "accept", "term_sheet_id": "offer:70340-1"}
    assert move["trace"]["rival_best_c"] == math.inf


def test_a_bidder_the_policy_walks_away_from_stops_counting_as_a_rival(case):
    agent = PolicyAgent({"claims_per_msg": 0})
    threads = {A: [message(A, 16.00, 42, "open", 1)], B: [message(B, 14.00, 35, "walked_away", 1)]}
    assert agent.decide(case, threads, B)["message"]["action"] == {"type": "walk_away"}
    assert agent.states[B].dropped and agent.policy.rival_best(case, agent.states, agent.states[A]) == math.inf


def test_the_simulator_uses_the_same_rule(case):
    from buyer.sim.env import episode

    rng = random.Random(0)
    scores = [episode(case, policy(), rng)["score"] for _ in range(5)]
    assert all(0.0 <= s <= 1.0 for s in scores)
