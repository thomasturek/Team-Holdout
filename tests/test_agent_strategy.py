"""The BUYER_STRATEGY switch: off by default; a forced strategy's parameters apply to one move only."""

from buyer.facts.strategy import PARAMS
from buyer.policy.policy import ThreadState
from buyer.runtime.agent import PolicyAgent

CASE = {"case_id": "case:T", "suppliers": ["sup:70110"], "parts": ["part:310010"], "type": "price_increase",
        "buyer": {"category_goal": "routine"}}


def thread():
    return ThreadState("sup:70110", "offer:x-0", {"unit_price": 10.0}, "open", {}, 9, profile={"archetype": "unknown"})


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("BUYER_STRATEGY", raising=False)
    assert PolicyAgent._strategy(CASE, thread(), []) is None


def test_a_forced_strategy_and_auto(monkeypatch):
    monkeypatch.setenv("BUYER_STRATEGY", "aggressive")
    s = PolicyAgent._strategy(CASE, thread(), [])
    assert s.name == "aggressive" and s.params == PARAMS["aggressive"]
    monkeypatch.setenv("BUYER_STRATEGY", "auto")
    assert PolicyAgent._strategy(CASE, thread(), []).name in PARAMS


def test_the_overrides_never_stick(monkeypatch):
    monkeypatch.setenv("BUYER_STRATEGY", "secure")
    agent = PolicyAgent()
    assert agent.policy.p == agent.base_p  # outside a move the policy keeps its own parameters
