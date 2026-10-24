"""The policy agent's reader: keyword rules on the move's path, the LLM reader in the background."""

import json
import time

import pytest

from buyer.llm import client as llm_client
from buyer.llm.client import LLMClient, Settings
from buyer.runtime.agent import new_agent
from buyer.runtime.log import SessionLog, read
from buyer.runtime.threads import play_case

READER_S = 2.0  # far above a loaded machine's move time, so "did not wait" and "waited" never overlap
ANSWER = json.dumps({"tone": "warm", "cash_pressure": True, "asks": ["faster payment"]})


@pytest.fixture
def slow_reader():
    """A reader LLM that takes READER_S per reply; the writer stays disabled (conftest)."""

    def fn(system, user, max_tokens, timeout_s):
        time.sleep(READER_S)
        return ANSWER

    settings = Settings("anthropic", "fake", None, None, "x", False)
    with llm_client._clients_lock:
        llm_client._clients["reader"] = LLMClient(settings, complete_fn=fn, name="llm-reader")
    yield


def play(client, tmp_path, agent=None):
    lg = SessionLog("sim", "case:S01", root=tmp_path)
    assert play_case(client, "case:S01", agent or new_agent("policy"), log=lg)["ended"]
    events = read(lg.path)
    return [e for e in events if e["kind"] == "sent"], [e for e in events if e["kind"] == "decision"]


def test_the_llm_reader_does_not_delay_the_move(sim, tmp_path, slow_reader):
    client, _, _ = sim
    agent = new_agent("policy")
    sent, decisions = play(client, tmp_path, agent)
    later = [e["decide_s"] for e in sent[1:]]  # the first move also loads the case's profiles and data, once
    assert later and max(later) < READER_S / 2, later
    llm = [d["trace"]["diplomat"].get("reader_llm") or d["trace"]["diplomat"].get("reader_llm_previous")
           for d in decisions]  # fmt: skip
    assert llm and all(r for r in llm)  # each move logs the LLM reading, or that it is still running
    time.sleep(READER_S + 1.0)  # the background readings finish after the (instant) simulated game
    readings = list(agent.llm_readings.values())
    assert readings and all(r[1].source.startswith("llm") and r[1].signals.tone == "warm" for r in readings)


def test_blocking_mode_waits_for_the_llm_reader(sim, tmp_path, slow_reader, monkeypatch):
    monkeypatch.setenv("BUYER_READER", "blocking")
    client, _, _ = sim
    sent, decisions = play(client, tmp_path)
    assert sent and min(e["decide_s"] for e in sent) >= READER_S
    assert decisions[0]["trace"]["diplomat"]["reader"]["source"].startswith("llm")
    assert "reader_llm" not in decisions[0]["trace"]["diplomat"]


def test_without_an_llm_nothing_is_pending(sim, tmp_path):
    client, _, _ = sim
    _, decisions = play(client, tmp_path)
    assert decisions and all("reader_llm" not in d["trace"]["diplomat"] for d in decisions)
    assert all(d["trace"]["diplomat"]["reader"]["source"] == "rules" for d in decisions)
