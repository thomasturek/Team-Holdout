# Live Final safety review - runtime path by path

Scope: `threads.py`, `runner.py`, `agent.py`, `writer.py`, `reader.py`, `client.py` as shown. Line references are given as `file:function` with the quoted statement, since the files were supplied without line numbers. "Shows" = in the files or the reports; "infer" = my reading.

## What is already safe (checked, no change)

- **LLM calls have hard wall-clock limits.** `client.py:LLMClient.complete` runs every attempt in a daemon thread (`_run_in_daemon`) and abandons it at `budget = min(timeout_s, left)`; `end = min(t0 + total_s, deadline)`. Writer: 20 s/attempt, 25 s total, deadline `start + MOVE_BUDGET_S` (23) from `agent.py:PolicyAgent.decide`. Reader: 10 s. SDK retries are off (`max_retries=0`), socket timeout `timeout_s + 1`.
- **Accept / walk never touch the model.** `writer.py:to_message` returns the action for `kind in ("accept","walk")` before `write()`; `agent.py:PolicyAgent.decide` reads the reply with the keyword rules only (`read(..., use_llm=False)`) and starts the LLM reader in the background; `closing()` never calls the reader and `policy.closing` returns only accept/walk.
- **Template fallback.** `writer.py:write` wraps the model path in `try/except Exception` → `fallback()` → `template_body` → `_minimal_body`; `reader.py:read` falls back to `rule_signals` on `LLMUnavailable`, bad JSON or empty fields.
- **Rate limits.** One `SafeClient` for the whole final (`runner.py:main`), `client.py:_pace` 9 calls/s across all threads; 429 with a short `Retry-After` is retried, quota 429 is not. One session per case, `parallel=min(10)`.
- **Idempotent retries.** Same `X-Move-Id` on every retry of a POST (`client.py:_call`), including `httpx.TimeoutException` (a `TransportError`), so a reply lost in transit is fetched, not replayed.
- **Lost accept supervision.** `threads.py:_attempt` → `_reconcile` after any failed/unanswered terminal action; `_supervise_close` keeps trying until `cap + AFTER_CAP_S`.

The evidence for what is *not* safe: `fable_rules.md` §1 - five sessions in one 14-minute batch ended `end=timeout` with score 0 (`37b4e28d`, `bf98975f`, `76b7cbbb`, `49409787`, `9ebd2de0`), four of them with an `accept` pending; the identical code closed all five ten minutes later. The logs shown do not identify the cause; what they show is that **nothing was sent at all** in those moves (not even the holding message), i.e. the stall was below the decision layer - HTTP or process-level. The fixes below are ranked by how many zero paths they close.

---

## 1. A crashed or unstartable final case is never restarted, and a stuck case can starve the whole wave pool

**Shows.** `runner.py:play_final`, `one()` catches every exception and *returns* it; the poll loop only submits `if cid not in started` - a case whose `play_case` raised (network at `table.open`, `429` "open sessions", a crash in `play()`) stays in `started` forever with its exception. Nothing re-opens it, although `RemoteTable` resumes a running session on `409` when given the case file (docstring in `threads.py:CasePlayer.__init__`). Second, `ThreadPoolExecutor(max_workers=parallel)` = 10 slots for 10 open sessions: a case of wave N still inside `play()` after its cap (e.g. a worker blocked in a 180 s HTTP read × 3 retries, see §3, or `_supervise_close` up to `cap + 30 s`, or `_docs_pool.shutdown(wait=True)` in `play()`'s `finally`) holds a slot; wave N+1's cases queue behind it and **are not played** (the alternative's score).

**Infer.** The pool size was copied from the 10-open-sessions limit, but that limit is enforced server-side on *open* sessions; an ended session in a lingering thread does not count.

```diff
--- a/src/buyer/runtime/runner.py
+++ b/src/buyer/runtime/runner.py
@@
 RESERVE = 20  # practice sessions kept for Sunday's pre-flight (AGENTS.md section 6)
 POLL_S = 3.0
+RESTARTS = 3
+RESTART_MIN_S = 45.0
@@ def play_final(client, *, agent="policy", params=None, waves=5, parallel=10, poll=POLL_S, root=env.RUNS):
-    started, closed, caps = {}, set(), {}  # caps: wave -> its cap as time.time()
+    started, closed, caps, restarts = {}, set(), {}, {}  # caps: wave -> its cap as time.time()
@@
-    with ThreadPoolExecutor(max_workers=parallel, thread_name_prefix="final") as pool:
+    with ThreadPoolExecutor(max_workers=3 * parallel, thread_name_prefix="final") as pool:
@@
                 if case.get("seconds_left") is not None:  # each wave has its own cap; follow an extension
                     caps[wave] = time.time() + case["seconds_left"]
+                f = started.get(cid)
+                if f is not None and f.done():
+                    err = f.exception() or f.result()
+                    if (isinstance(err, BaseException) and (case.get("seconds_left") or 0) > RESTART_MIN_S
+                            and restarts.get(cid, 0) < RESTARTS):
+                        restarts[cid] = restarts.get(cid, 0) + 1
+                        log.warning("%s failed (%s) - restart %d", cid, err, restarts[cid])
+                        del started[cid]
                 if cid not in started and case.get("seconds_left"):
```

**Affects.** Every hidden case; a transient `open_session` failure or crash now costs one poll (3 s) instead of the case. **Risk.** A restart on a session that did open hits `409` → `RemoteTable` resumes it (resume path exercised in practice per the docstring; test once on the sandbox with a monkeypatched `play_case` that raises on the first call). Run the final with `--waves 9`: the loop then only ends when killed, so a replayed or extended wave is still polled.

## 2. A failed send kills the worker thread; the case is then closed early at whatever stands

**Shows.** `threads.py:_worker`: `if self._send(sid, msg, decide_s=...) == INVALID:` is outside any `try`. `_exchange` re-raises every `ArenaError` that is not 422/409 (5xx after the client's 3 retries, 413, 403 "wave not running", 429 quota) and `_refresh` itself can raise (`client.session`, `client.thread` during the same network trouble). The exception leaves `_worker`; `play()` logs "a thread crashed" and, once all workers are gone, calls `_supervise_close("no thread left to play")` → `policy.closing` → **accepts the current standing offer or walks**, in round 1 if that is where the crash hit. The decide path has exactly the guard the send path lacks (`failures`, `MAX_FAILURES`, hold).

```diff
--- a/src/buyer/runtime/threads.py
+++ b/src/buyer/runtime/threads.py
@@ def _worker(self, sid):
-            if self._send(sid, msg, decide_s=time.monotonic() - t0) == INVALID:
+            try:
+                sent = self._send(sid, msg, decide_s=time.monotonic() - t0)
+            except Exception as e:
+                failures += 1
+                log.exception("%s %s: sending failed (%d in a row)", self.case_id, sid, failures)
+                self.log("error", supplier_id=sid, detail=e, where="send")
+                if failures >= MAX_FAILURES:
+                    self.log("drop", supplier_id=sid, reason="sending failed repeatedly")
+                    return
+                s.ended.wait(CLOSE_RETRY_S)
+                continue
+            if sent == INVALID:
```

**Affects.** Every case on a flaky venue network. The next loop iteration re-reads the snapshot and decides again; if the message did land, the arena answers the resend with `409` → `_refresh` picks up the reply. **Risk.** None beyond what already happens on a 409.

## 3. Opening-quote downloads run synchronously inside the 60 s clock, with a 180 s socket timeout

**Shows.** `threads.py:play`: `for m in events: self._documents(m, sid, wait=True)` runs before the workers start and before `_clocks()`; with `_docs_pool is None` every PDF is fetched in the calling thread through `client._call` (timeout 180 s, up to 3 retries with backoff on transport errors). The arena's 60 s per thread run from session creation. One hung `GET .../attachments/...` therefore blows the first move of **every** thread of the case; three such timeouts end a thread. `client.py:__init__` sets a single `timeout=180` for connect and read alike, so a half-open Wi-Fi connection hangs 180 s before the first retry. The same connect hang applies to every send and to the accept.

```diff
--- a/src/buyer/runtime/threads.py
+++ b/src/buyer/runtime/threads.py
@@
-from concurrent.futures import ThreadPoolExecutor
+from concurrent.futures import ThreadPoolExecutor, wait
 from concurrent.futures import TimeoutError as FutureTimeout
@@
 DOWNLOADS = 4  # attachment downloads at once per case
+OPENING_DOCS_S = 20.0
@@ def play(self):
-        for sid, events in threads.items():  # the opening quotes: before any thread plays, so wait for them
-            for m in events:
-                self._documents(m, sid, wait=True)
+        self._docs_pool = ThreadPoolExecutor(max_workers=DOWNLOADS, thread_name_prefix="docs")
+        opening = [self._docs_pool.submit(self._documents, m, sid, True)
+                   for sid, events in threads.items() for m in events]
+        if wait(opening, timeout=OPENING_DOCS_S).not_done:
+            self.log("opening_docs_late", pending=list(s.pending))
         self.log("opening", threads=threads)
@@
         self._decide_pool = ThreadPoolExecutor(max_workers=len(workers) * 2, thread_name_prefix="decide")
-        self._docs_pool = ThreadPoolExecutor(max_workers=DOWNLOADS, thread_name_prefix="docs")
@@
             self._decide_pool.shutdown(wait=False, cancel_futures=True)
-            self._docs_pool.shutdown(wait=True)  # the case is over: the arena answers these at once now
+            self._docs_pool.shutdown(wait=False)
```

```diff
--- a/starter-kit/arena_kit/client.py
+++ b/starter-kit/arena_kit/client.py
@@
 TIMEOUT_S = 180.0
+CONNECT_TIMEOUT_S = 10.0
@@ def __init__(
-        self.http = httpx.Client(base_url=f"{base_url}/v1", headers=headers, timeout=timeout, transport=transport)
+        if not isinstance(timeout, httpx.Timeout):
+            timeout = httpx.Timeout(timeout, connect=CONNECT_TIMEOUT_S)
+        self.http = httpx.Client(base_url=f"{base_url}/v1", headers=headers, timeout=timeout, transport=transport)
```

**Affects.** Every case: the first move starts at most 20 s after the open even if a PDF hangs (the late text is filled in by `_download` when it arrives; `standard_terms` falls back to the quote e-mail meanwhile). A dead connection fails in 10 s and is retried instead of 180 s. **Risk.** With the PDF late, `t.standard` is `{}` for the first move only; the policy's first sheet does not depend on it. The read timeout stays at 180 s on purpose: a reply queued behind another bidder's reply can legitimately take 2 min (learnings: 66 s p90 with 3 bidders) and a shorter read timeout plus same-`X-Move-Id` retry has not been tested against an in-flight duplicate.

## 4. Two unguarded exceptions in the per-move path drop a thread after two moves

**Shows.**
(a) `agent.py:PolicyAgent._state`: `t.standard = standard_terms(events) or t.standard` - the kit parser raised `int("none")` on a quote line it could not read (learnings, "Hidden-case readiness": P10 and P11 variants walked, 0.0). It is called under the policy lock on **every** move for every thread; one odd hidden quote PDF raises on every decision → `MAX_FAILURES=2` → `drop` → `_supervise_close` accepts/walks at round 2.
(b) `writer.py:write`: `offers_block`, `volume_line`, `questions_block`, `allowed_tokens`, `prose_rules` run **before** the `try:` whose `fallback()` guarantees "never raises for a send Decision". A term sheet with an unexpected value type (a hidden case with a new negotiable field, `index_clause` dicts, `incoterm` strings) that trips one of them propagates through `to_message` → `message_for` → `decide` → the same two-failure drop.

```diff
--- a/src/buyer/runtime/agent.py
+++ b/src/buyer/runtime/agent.py
@@ def _state(self, case, sid, events):
-        t.standard = standard_terms(events) or t.standard
+        try:
+            t.standard = standard_terms(events) or t.standard
+        except Exception:
+            log.exception("%s: standard terms unreadable - keeping the earlier ones", sid)
@@ def message_for(decision, case, events, profile=None, signals=None, known_id=None, deadline=None):
     from buyer.llm import to_message
 
-    message, email = to_message(decision, case, events, profile, signals, known_id=known_id, deadline=deadline)
+    try:
+        message, email = to_message(decision, case, events, profile, signals, known_id=known_id, deadline=deadline)
+    except Exception:
+        if decision.kind != "send":
+            raise
+        log.exception("%s: the writer raised - sending a bare e-mail", decision.supplier_id)
+        subject = next((m.get("subject") for m in events if m.get("subject")), "your offer")
+        sentences = [c.sentence for c in decision.claims or [] if getattr(c, "sentence", None)][:3]
+        body = "\n\n".join(["Dear colleagues,", "Thank you for your message. Our options are in the term sheets.",
+                            *sentences, "Best regards\nHollerau Pumpenwerke, Purchasing"])
+        sheets = [{"terms": dict(s)} for s in decision.term_sheets[:3] if isinstance(s, dict)]
+        subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
+        message, email = {"subject": subject, "body": body, "term_sheets": sheets, "refs": []}, None
     return {"supplier_id": decision.supplier_id, "message": message}, email
```

**Affects.** Hidden cases with new structures (the brief: "mostly suppliers, parts and situations practice never shows"). The bare e-mail still carries the term sheets (which bind) and the claim sentences (which the arena checks from the body). **Risk.** None for accept/walk (re-raised as before). A 422 on the bare sheets is handled by the existing hold path.

## 5. Profiles and case data are built inside the first move's 60 s

**Shows.** `agent.py:PolicyAgent.decide` → `self._warm(case)` → `scout_profiles` → `profile()` (`lookup_profile`, `dossier`, `strategy.initial`, SQLite reads) + `CaseData(case)` (`load_package`, "about a second") on the **first** move, after the clock has started; for an RFQ the other two threads wait on `_init_lock` meanwhile. The writer's deadline is absolute (`start + 23`), so a slow warm-up leaves it seconds and the first e-mail - "the negotiation" per `fable_round1.md` - goes out as a template or, past `HOLD_AT_S`, as the holding message. The case file is in hand before the session is opened (`play_case(..., case=case)` in `runner.py:play_final`).

```diff
--- a/src/buyer/runtime/threads.py
+++ b/src/buyer/runtime/threads.py
@@ def play(self):
+        warm = getattr(self.agent, "_warm", None)
+        if warm is not None and self.case_file:
+            try:
+                warm(self.case_file)
+            except Exception:
+                log.exception("%s: warming the agent failed", self.case_id)
         case, threads = self.table.open(self.case_id)
```

**Affects.** Every case; the first decision now spends its budget on policy + writer. **Risk.** `_warm` already swallows its own failures; a slow warm-up delays the open by a few seconds of the wave's 8 minutes.

## 6. The holding message at 48 s is itself late in a serialised RFQ session

**Shows.** `threads.py:HOLD_AT_S = 48`; the hold is sent only then, and the arena serialises calls within a session: with three bidders a message waits ~21 s per pending rival reply (learnings "Final-day safety": 44 s, 66 s at p90; "P05 had one late move"). A hold leaving at 48 s plus that queue is a timeout; the normal decision (≤ ~25 s: `MOVE_BUDGET_S` 23 + policy) is not.

```diff
--- a/src/buyer/runtime/threads.py
+++ b/src/buyer/runtime/threads.py
@@
-HOLD_AT_S = 48  # still no decision: send the holding message (the arena's limit is 60 s)
+HOLD_AT_S = 40  # still no decision: send the holding message (the arena's limit is 60 s)
```

**Affects.** RFQ cases (P05-like, 2-3 bidders) and any case on a slow arena. **Risk (infer).** A decision landing between 40 and 48 s is now dropped for a hold; in the logs the writer's p95 is bounded by its 23 s deadline and the policy lock holds for seconds, so this band is near-empty. Whether the server-side queue counts against the 60 s is not stated in `api.md`; the learnings' late move says it can.

---

## Noted, not changed (outside the six files or not minimal)

- **Must-have on a term the supplier left out.** `policy.eligible_cost` → `must_haves_ok(case, standing_terms, t.standard)`: with `t.standard == {}` (PDF not read), `closing_terms` fills `lead_time_days` / `volume_per_year` from the buyer's own plan, so a sheet that would close on a breaking standard term looks fine and scores 0. Fix 3 keeps this to the first move; a guard in `policy.py` (treat a must-have field missing from both sheet and standard as not eligible) is a policy change and could block all acceptances if the standard never arrives - leave it, pre-flight once on P05.
- **An abandoned late decision still mutated policy state** (`t.our_prices`, `last_sent`, `sent_prices`) although the hold went out; the next sheet may therefore step from a price never sent (`no_step_back`). Low frequency after fix 5; not minimal to undo.
- **A 180 s read timeout on the accept** (`_attempt`): a stall there runs to the cap; the same-`X-Move-Id` retry then returns the stored result if the arena processed it. No cheap improvement without testing the duplicate-in-flight behaviour.
- **Cause of the five timeouts** in `fable_rules.md` §1 is not identifiable from the files shown; fixes 1-3 and 6 are the generic protections for an HTTP stall, and fix 1 turns a dead case into a restarted one.

## Test plan (≤ 60 min)

1. `arena-sim`, sandbox D02 (2 bidders): run `buyer sandbox --cases D02 --repeat 2` with the diffs; expect no `error`/`drop` events and the first `sent` within 25 s of the open.
2. Monkeypatch tests: `standard_terms` raising → the move is still sent; `offers_block` raising → bare e-mail sent with the sheets; `play_case` raising once in `play_final` → the case is resubmitted on the next poll (fake `client.cases` with `seconds_left: 300`); a transport that hangs on connect → `ArenaError`/`TransportError` after ≈10 s × retries, not 180 s.
3. Pre-flight on P05 (3 bidders, must-have) through `buyer final`-equivalent settings (`--parallel 10`, LLM on): check `opening_docs_late` absent and no `hold` events.

Start the runner before 13:30 with `uv run buyer final --waves 9 --parallel 10`, the Anthropic spend limit raised (night log 04:10: a blocked key silently turns every e-mail into a template), and `BUYER_READER` unset (parallel mode).