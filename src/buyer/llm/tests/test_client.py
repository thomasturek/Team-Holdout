import os
import time

import pytest

from buyer.llm.client import LLMClient, LLMUnavailable, Settings, latency_summary, settings_from_env

S = Settings("anthropic", "m", "low", None, "k", False)


def client(fn):
    return LLMClient(S, complete_fn=fn)


def test_answer_and_stats():
    c = client(lambda s, u, mt, t: "hello")
    assert c.complete("sys", "user", tag="t") == "hello"
    assert c.stats[-1]["ok"] and c.stats[-1]["attempts"] == 1 and c.stats[-1]["tag"] == "t"


def test_disabled_raises_at_once():
    c = LLMClient(Settings("anthropic", None, None, None, None, True))
    assert not c.enabled
    t0 = time.monotonic()
    with pytest.raises(LLMUnavailable):
        c.complete("s", "u")
    assert time.monotonic() - t0 < 0.05


def test_hard_timeout_then_one_retry_within_total():
    def slow(s, u, mt, t):
        time.sleep(2.0)
        return "late"

    c = client(slow)
    t0 = time.monotonic()
    with pytest.raises(LLMUnavailable):
        c.complete("s", "u", timeout_s=0.2, retries=1, total_s=5.0)
    took = time.monotonic() - t0
    assert took < 0.6  # two attempts of 0.2 s, not the 2 s the provider takes
    assert c.stats[-1]["attempts"] == 2 and not c.stats[-1]["ok"]


def test_total_cap_is_never_exceeded():
    def slow(s, u, mt, t):
        time.sleep(2.0)
        return "late"

    c = client(slow)
    t0 = time.monotonic()
    with pytest.raises(LLMUnavailable):
        c.complete("s", "u", timeout_s=0.3, retries=5, total_s=0.5)
    assert time.monotonic() - t0 < 0.6


def test_no_retry_when_too_little_time_left():
    calls = []

    def slow(s, u, mt, t):
        calls.append(t)
        time.sleep(1.0)
        return "late"

    c = client(slow)
    with pytest.raises(LLMUnavailable):
        c.complete("s", "u", timeout_s=0.3, retries=1, total_s=1.0)  # 0.7 s left < MIN_RETRY_S
    assert len(calls) == 1


def test_retry_after_error_succeeds():
    calls = []

    def flaky(s, u, mt, t):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("overloaded")
        return "ok"

    c = client(flaky)
    assert c.complete("s", "u") == "ok"
    assert c.stats[-1]["attempts"] == 2


def test_empty_answer_counts_as_failure():
    c = client(lambda s, u, mt, t: "   ")
    with pytest.raises(LLMUnavailable):
        c.complete("s", "u", retries=1)


def test_deadline_shortens_the_call():
    def slow(s, u, mt, t):
        time.sleep(2.0)
        return "late"

    c = client(slow)
    t0 = time.monotonic()
    with pytest.raises(LLMUnavailable):
        c.complete("s", "u", timeout_s=20, total_s=25, deadline=time.monotonic() + 0.3)
    assert time.monotonic() - t0 < 0.5


def test_settings_from_env_with_role_override():
    keys = ["LLM_PROVIDER", "LLM_MODEL", "LLM_EFFORT", "LLM_READER_MODEL", "LLM_READER_EFFORT", "ANTHROPIC_API_KEY",
            "LLM_DISABLED", "LLM_READER_DISABLED"]  # fmt: skip
    saved = {k: os.environ.get(k) for k in keys}
    try:
        for k in keys:
            os.environ.pop(k, None)
        assert settings_from_env().disabled  # no model, no key
        os.environ.update({"LLM_MODEL": "big", "ANTHROPIC_API_KEY": "x", "LLM_READER_MODEL": "fast", "LLM_READER_EFFORT": ""})  # noqa: E501
        w, r = settings_from_env("writer"), settings_from_env("reader")
        assert (w.model, w.effort, w.disabled) == ("big", "low", False)
        assert r.model == "fast" and r.effort == "low"  # an empty role variable falls through
        os.environ["LLM_EFFORT"] = ""
        assert settings_from_env("writer").effort is None
        os.environ["LLM_DISABLED"] = "1"
        assert settings_from_env("writer").disabled
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_latency_summary():
    stats = [{"latency_s": x, "ok": x < 9} for x in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)]
    s = latency_summary(stats)
    assert s["calls"] == 10 and s["max"] == 10 and s["failed"] == 2 and s["p50"] in (5, 6) and s["p95"] >= 9
    assert latency_summary([]) == {"calls": 0}


def test_abandoned_calls_run_in_daemon_threads():
    import threading

    seen = {}

    def slow(s, u, mt, t):
        seen["daemon"] = threading.current_thread().daemon
        time.sleep(0.5)
        return "late"

    with pytest.raises(LLMUnavailable):
        client(slow).complete("s", "u", timeout_s=0.1, retries=0, total_s=0.1)
    assert seen["daemon"] is True  # never blocks the process from exiting
