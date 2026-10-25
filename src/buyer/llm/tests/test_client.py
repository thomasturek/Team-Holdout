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


def test_settings_from_env_with_role_override(monkeypatch):
    # Every LLM_* variable goes, not a fixed list: buyer.runtime loads .env (LLM_WRITER_MODEL, ...) on import.
    for k in [k for k in os.environ if k.startswith("LLM_")] + ["ANTHROPIC_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    assert settings_from_env().disabled  # no model, no key
    env = {"LLM_MODEL": "big", "ANTHROPIC_API_KEY": "x", "LLM_READER_MODEL": "fast", "LLM_READER_EFFORT": ""}
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    w, r = settings_from_env("writer"), settings_from_env("reader")
    assert (w.model, w.effort, w.disabled) == ("big", "low", False)
    assert r.model == "fast" and r.effort == "low"  # an empty role variable falls through
    monkeypatch.setenv("LLM_EFFORT", "")
    assert settings_from_env("writer").effort is None
    monkeypatch.setenv("LLM_DISABLED", "1")
    assert settings_from_env("writer").disabled


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


# --- circuit breaker --------------------------------------------------------------------------------------
def test_three_failed_calls_open_the_breaker_and_calls_then_fail_at_once(monkeypatch):
    calls = []

    def broken(s, u, mt, t):
        calls.append(1)
        raise RuntimeError("overloaded")

    c = client(broken)
    for _ in range(3):
        with pytest.raises(LLMUnavailable):
            c.complete("s", "u", retries=0)
    n = len(calls)
    t0 = time.monotonic()
    with pytest.raises(LLMUnavailable, match="circuit open"):
        c.complete("s", "u")
    assert len(calls) == n and time.monotonic() - t0 < 0.05  # the provider is not asked while open


def test_an_auth_error_opens_the_breaker_at_once():
    def unauthorised(s, u, mt, t):
        raise RuntimeError("Error code: 401 - authentication_error: invalid x-api-key")

    c = client(unauthorised)
    with pytest.raises(LLMUnavailable):
        c.complete("s", "u", retries=0)
    with pytest.raises(LLMUnavailable, match="circuit open"):
        c.complete("s", "u")


def test_after_the_pause_one_call_tries_again_and_a_success_closes_it(monkeypatch):
    import buyer.llm.client as mod

    monkeypatch.setattr(mod, "BREAK_S", 0.1)
    state = {"broken": True}

    def flaky(s, u, mt, t):
        if state["broken"]:
            raise RuntimeError("401 invalid x-api-key")
        return "back"

    c = client(flaky)
    with pytest.raises(LLMUnavailable):
        c.complete("s", "u", retries=0)
    time.sleep(0.15)
    state["broken"] = False
    assert c.complete("s", "u") == "back" and c._fails == 0


def test_a_success_between_failures_resets_the_count():
    seq = iter(["fail", "fail", "ok", "fail", "fail"])

    def fn(s, u, mt, t):
        if next(seq) == "fail":
            raise RuntimeError("overloaded")
        return "fine"

    c = client(fn)
    for _ in range(2):
        with pytest.raises(LLMUnavailable):
            c.complete("s", "u", retries=0)
    assert c.complete("s", "u", retries=0) == "fine"
    for _ in range(2):
        with pytest.raises(LLMUnavailable, match="overloaded"):  # 2 in a row again: still closed
            c.complete("s", "u", retries=0)
