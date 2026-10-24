"""The one LLM client of the team (AGENTS.md: DIPLOMAT owns it; the SCOUT may call it offline).

Provider and model come from the environment (`.env`), Anthropic by default:

    LLM_PROVIDER      anthropic (default) | openai (any OpenAI-compatible endpoint) | none
    LLM_MODEL         e.g. claude-opus-5-5 (the starter kit's default). Unset -> client disabled
    LLM_EFFORT        low (default) - sent as output_config.effort to Anthropic; empty = not sent
    ANTHROPIC_API_KEY for anthropic
    LLM_BASE_URL, LLM_API_KEY   for openai
    LLM_DISABLED=1    no LLM at all: the reader uses keyword rules, the writer the template
                      (cheap mode, e.g. for the sandbox harvester)

Per role (`get_client("reader")`), every variable can be overridden with a role prefix, e.g.
LLM_READER_MODEL, LLM_READER_EFFORT, LLM_WRITER_MODEL.

Time limits (DIPLOMAT.md, kept literally): every attempt has a hard wall-clock timeout of 20 s, one
retry, then the caller falls back (template / keyword rules). The whole call never takes longer than
`total_s` (25 s): a retry only gets the time that is left. The reader uses 10 s for both. The SDK's own
retries are switched off - they would break these limits. A call that is still running when its time
is up is abandoned (it finishes in the background and is ignored); the caller gets `LLMUnavailable`.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass

log = logging.getLogger("buyer.llm")

ATTEMPT_TIMEOUT_S = 20.0  # hard wall-clock limit per attempt (DIPLOMAT.md)
RETRIES = 1  # one retry (DIPLOMAT.md)
TOTAL_S = 25.0  # never block a move past 25 s (DIPLOMAT.md)
MIN_RETRY_S = 2.0  # a retry with less time than this left is not worth starting
READER_TIMEOUT_S = 10.0  # the reader: < 10 s (DIPLOMAT.md)
DEFAULT_EFFORT = "low"


class LLMUnavailable(Exception):
    """No usable answer in time: disabled, timed out, or failed on every attempt. Fall back."""


@dataclass
class Settings:
    provider: str
    model: str | None
    effort: str | None
    base_url: str | None
    api_key: str | None
    disabled: bool


def _env(role, name, default=None):
    """LLM_<ROLE>_<NAME>, else LLM_<NAME>, else default. An empty role variable falls through."""
    if role:
        v = os.environ.get(f"LLM_{role.upper()}_{name}")
        if v not in (None, ""):
            return v
    v = os.environ.get(f"LLM_{name}")
    return default if v is None else v


def settings_from_env(role=None) -> Settings:
    provider = (_env(role, "PROVIDER", "anthropic") or "anthropic").strip().lower()
    model = (_env(role, "MODEL") or "").strip() or None
    effort = _env(role, "EFFORT", DEFAULT_EFFORT)
    effort = (effort or "").strip() or None
    disabled = (_env(role, "DISABLED", "") or "").strip().lower() in ("1", "true", "yes")
    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY") or None
    else:
        api_key = _env(role, "API_KEY") or None
    base_url = (_env(role, "BASE_URL") or "").strip() or None
    if provider == "none" or model is None:
        disabled = True
    if provider == "anthropic" and not api_key:
        disabled = True
    return Settings(provider, model, effort, base_url, api_key, disabled)


class LLMClient:
    """`complete(system, user)` -> text, inside hard time limits, or `LLMUnavailable`.

    `complete_fn(system, user, max_tokens, timeout_s) -> str` replaces the provider (tests, other
    providers); it must raise on failure.
    """

    def __init__(self, settings: Settings | None = None, complete_fn=None, name="llm"):
        self.settings = settings or settings_from_env()
        self.name = name
        self._fn = complete_fn
        self._sdk = None
        self._sdk_lock = threading.Lock()
        self._effort_ok = True  # switched off once if the API rejects the effort parameter
        self.stats = deque(maxlen=20_000)  # one dict per call: tag, ok, latency_s, attempts, error

    @property
    def enabled(self) -> bool:
        return self._fn is not None or not self.settings.disabled

    # --- the call ---------------------------------------------------------------------------------
    def complete(
        self,
        system: str,
        user: str,
        *,
        timeout_s: float = ATTEMPT_TIMEOUT_S,
        retries: int = RETRIES,
        total_s: float = TOTAL_S,
        max_tokens: int = 800,
        deadline: float | None = None,
        tag: str = "",
    ) -> str:
        """The model's text. `deadline` (time.monotonic()) optionally ends the call earlier."""
        t0 = time.monotonic()
        end = t0 + total_s if deadline is None else min(t0 + total_s, deadline)
        if not self.enabled:
            self._record(tag, False, 0.0, 0, "disabled")
            raise LLMUnavailable("LLM disabled (LLM_DISABLED, no LLM_MODEL or no API key)")
        errors = []
        attempt = 0
        while attempt <= retries:
            left = end - time.monotonic()
            if left <= 0 or (attempt > 0 and left < MIN_RETRY_S):
                break
            budget = min(timeout_s, left)
            attempt += 1
            done, box = _run_in_daemon(self._call, (system, user, max_tokens, budget))
            if not done.wait(budget):  # still running: abandoned, it ends in the background, ignored
                errors.append(f"timeout after {budget:.1f}s")
                continue
            if "error" in box:  # provider error: retry if time is left
                e = box["error"]
                errors.append(f"{type(e).__name__}: {str(e)[:200]}")
                continue
            text = box.get("text")
            if not text or not text.strip():
                errors.append("empty answer")
                continue
            self._record(tag, True, time.monotonic() - t0, attempt, None)
            return text
        took = time.monotonic() - t0
        self._record(tag, False, took, attempt, "; ".join(errors) or "no time left")
        log.warning("%s %s: no answer after %.1fs (%s)", self.name, tag, took, "; ".join(errors))
        raise LLMUnavailable("; ".join(errors) or "no time left")

    def _record(self, tag, ok, latency, attempts, error):
        self.stats.append({"tag": tag, "ok": ok, "latency_s": round(latency, 3), "attempts": attempts,
                           "error": error, "at": time.time()})  # fmt: skip

    def _call(self, system, user, max_tokens, timeout_s):
        if self._fn is not None:
            return self._fn(system, user, max_tokens, timeout_s)
        if self.settings.provider == "anthropic":
            return self._anthropic(system, user, max_tokens, timeout_s)
        if self.settings.provider == "openai":
            return self._openai(system, user, max_tokens, timeout_s)
        raise LLMUnavailable(f"unknown LLM_PROVIDER {self.settings.provider!r}")

    # --- providers ----------------------------------------------------------------------------------
    def _anthropic(self, system, user, max_tokens, timeout_s):
        import anthropic

        with self._sdk_lock:
            if self._sdk is None:
                # max_retries=0: the SDK would otherwise retry twice on its own and break our limits
                extra = {"base_url": self.settings.base_url} if self.settings.base_url else {}
                self._sdk = anthropic.Anthropic(
                    api_key=self.settings.api_key, max_retries=0, timeout=ATTEMPT_TIMEOUT_S + 5, **extra
                )
        kwargs = {
            "model": self.settings.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "timeout": timeout_s + 1.0,  # the socket gives up just after we stop waiting
        }
        if self.settings.effort and self._effort_ok:
            kwargs["extra_body"] = {"output_config": {"effort": self.settings.effort}}
        try:
            r = self._sdk.messages.create(**kwargs)
        except anthropic.BadRequestError as e:
            if "extra_body" in kwargs and ("effort" in str(e) or "output_config" in str(e)):
                log.warning("%s: model %s rejects effort - sending without it from now on",
                            self.name, self.settings.model)  # fmt: skip
                self._effort_ok = False
                kwargs.pop("extra_body")
                r = self._sdk.messages.create(**kwargs)
            else:
                raise
        if getattr(r, "stop_reason", None) == "max_tokens":  # cut off: half an e-mail is no e-mail
            raise RuntimeError("answer cut off at max_tokens")
        return "".join(getattr(b, "text", "") for b in r.content if getattr(b, "type", "") == "text")

    def _openai(self, system, user, max_tokens, timeout_s):
        import httpx

        base = (self.settings.base_url or "https://api.openai.com/v1").rstrip("/")
        headers = {"Authorization": f"Bearer {self.settings.api_key or ''}"}
        body = {
            "model": self.settings.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        r = httpx.post(f"{base}/chat/completions", json=body, headers=headers, timeout=timeout_s + 1.0)
        r.raise_for_status()
        choice = r.json()["choices"][0]
        if choice.get("finish_reason") == "length":
            raise RuntimeError("answer cut off at max_tokens")
        return choice["message"]["content"] or ""


def _run_in_daemon(fn, args):
    """Run fn(*args) in a daemon thread: (done event, {"text": ...} or {"error": ...}). A call we stop
    waiting for keeps no pool slot and never delays the process from exiting."""
    done, box = threading.Event(), {}

    def target():
        try:
            box["text"] = fn(*args)
        except BaseException as e:  # noqa: BLE001 - handed to the caller
            box["error"] = e
        finally:
            done.set()

    threading.Thread(target=target, name="llm-call", daemon=True).start()
    return done, box


_clients: dict[str, LLMClient] = {}
_clients_lock = threading.Lock()


def get_client(role: str = "writer") -> LLMClient:
    """One shared client per role ("writer", "reader", or anything else), built from the environment."""
    with _clients_lock:
        if role not in _clients:
            s = settings_from_env(role)
            _clients[role] = LLMClient(s, name=f"llm-{role}")
            if s.disabled:
                log.warning("LLM %s disabled (provider %s, model %s): templates / keyword rules only",
                            role, s.provider, s.model)  # fmt: skip
        return _clients[role]


def reset_clients():
    """Forget the shared clients (tests, or after changing the environment)."""
    with _clients_lock:
        _clients.clear()


def latency_summary(stats) -> dict:
    """p50 / p95 / max latency and the failure rate of a list of call records."""
    lat = sorted(s["latency_s"] for s in stats)
    if not lat:
        return {"calls": 0}

    def pct(p):
        return lat[min(len(lat) - 1, max(0, int(round(p * (len(lat) - 1)))))]

    fails = sum(not s["ok"] for s in stats)
    return {"calls": len(lat), "p50": pct(0.5), "p95": pct(0.95), "max": lat[-1], "failed": fails,
            "failed_pct": round(100 * fails / len(lat), 1)}  # fmt: skip
