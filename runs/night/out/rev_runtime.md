# Live Final robustness review: buyer agent runtime

**Scope.** I read `client.py`, `threads.py`, `runner.py`, `agent.py` and `policy.py`, with `NIGHT_CONTEXT.md`, the procurecabana `learnings.md`/`design.md` and `EVALUATION.md` as evidence.

**Notation.** Line numbers are approximate (±3). "E" marks what the evidence shows. "I" marks what I infer.

**Points model.** A final wave has about 5 cases, and our average score is about 0.7. So one case lost to a walk or no deal costs about 14 points in that wave. A network incident during a wave hits every open session at once.

---

## Findings, ranked by expected points

### 0. Operational, no code: do not run the final on venue Wi-Fi (largest EV)

- **E.** The brief says "Run your agent where you like, with your own LLM keys" (§7.4). We lost 5 cases to one 3-minute outage. `learnings.md` says "a session does not pause while our process is down."
- **I.** No client code survives an outage longer than about 2–3 minutes. The arena keeps timing threads out, and three timeouts end a thread.
- **Fix.** Run `buyer final` on a small cloud VM (EU region, `tmux` or `systemd`, NTP-synced clock). Do the pre-flight from that machine on Sunday morning.
- **Never run two runner instances on one key.** The 409 resume would let both act on the same sessions.
- **EV.** If P(an incident hits a wave) is about 25%, the expected loss is roughly 25% × 50–70 points ≈ 12–18 points. That is more than everything below combined.

### 1. One HTTP timeout of 180 s for every phase, ×4 attempts, no TCP keepalive (`client.py:17, :51, :62-75`)

- **E.** `httpx.Client(timeout=180)` applies 180 s to connect, write, read and pool. `retries=3` means up to 4 attempts. One call can therefore block about 12 minutes, longer than the 8-minute wave cap.
- **Scenario (matches the 180 s hangs you saw).**
  - The Wi-Fi drops for 20 s while a POST is in its read phase.
  - The TCP path is dead but gets no RST, so the read waits the full 180 s.
  - The arena meanwhile records timeouts (I: auto-fired every 60 s; E: "a waiting thread needs a message or it collects timeouts") and ends the thread.
  - A 20 s blip cost a whole case.
- **Fix.** Keep a long read timeout (the reply can take ~60 s plus serialisation; E: 36/54/72 s for three simultaneous RFQ messages). Change the rest:
  - connect 6 s and write 15 s;
  - TCP keepalive (idle 10 s, interval 5 s, count 3). A live server's kernel ACKs probes during a legitimate wait, but a dead path is detected in about 25 s.
  - Diff A. It needs httpx ≥ 0.25 for `socket_options`.
- **EV.** About +5–10 points (it converts blips under 60 s from "thread dead" to "one late move at most").

### 2. A worker dies on any network error during resync, and on any 5xx (`threads.py:304-310, :321-335`)

- **E.** In `_exchange`, a network failure goes to `_refresh`. `_refresh` calls `client.session()` and `client.thread()` with no try. If the network is still down, the exception escapes `_send` and `_worker`. `play()` logs "a thread crashed", and that thread is never played again.
- **E.** A 5xx after retries hits `if e.status != 409: raise`, with the same result.
- **Scenario, single-supplier case.**
  - The worker dies, so `_supervise_close` runs immediately.
  - `policy.closing` accepts the current standing sheet in round 2–3, before any concession: about 0.3–0.5 instead of about 0.8. If the sheet is not eligible, it walks for 0.
  - With the network still down, the close attempts themselves hang (finding 1).
- **Scenario, RFQ.** The dead bidder's thread is never answered again.
- **Fix.** Make `_refresh` keep asking with a 2 s backoff (bounded at 600 s or by `ended`). Treat 5xx and 429 like a network error (diff B).
- **EV.** About +4–8 points.

### 3. A resend that lands after the window becomes a push after a final offer (`client.py:60-75`, `threads.py:298`)

- **E.** `EVALUATION.md` records: "an arena 503 was retried after the arena had already recorded our timeout and the supplier's final offer; the retried message read as a push after the final offer and the supplier withdrew."
- **E.** Two code paths cause it:
  - the kit retries with the same `X-Move-Id` without any deadline;
  - `threads.py` has no resend of its own, but every later message is a fresh decision on a stale snapshot.
- **I.** A same-id resend is safe in both directions only while the arena's 60 s surely still run. If the original landed, we get the cached reply. If it did not, our move lands in time. Past the window, a non-landed original makes the resend a late, new move.
- **Fix.**
  - Pass `move_id` and `deadline` through to `send_message`.
  - In `_exchange`, resend with the same id inside `replied_at + 60 − 6 s`.
  - After that, never re-POST: GET the thread and decide again on the arena's state (diffs A and B).
- **EV.** About +3–5 points (prevents walk-aways on recovery).

### 4. `_refresh` gives the thread a fresh 60 s and may miss a timeout answer (`threads.py:334`, `:331`)

- **E, clock.** `s.replied_at[sid] = time.monotonic()  # the arena answered our late move just now`. This is wrong when our move never arrived. The arena's clock has been running since the supplier's last reply.
- **Scenario, clock.**
  - After a 70 s blip, the arena has about 10 s left.
  - We think we have 60 s, and the writer budget plus `HOLD_AT_S=48` overshoot.
  - That is a second timeout, and a third ends the thread.
- **Fix, clock.** `_clocks` and `_sync` already use `seconds_left`. `_refresh` fetches the session state but ignores it, so use it there too.
- **E, timeouts.** `api.md` says GET thread returns `timeouts` ("the supplier's answers to your late moves") separately from `messages`. `_refresh` and `_sync` store only `messages`.
- **I, timeouts.** The supplier's answer to a timeout may carry its new standing sheet with `final_offer`. Then `latest()` still shows the older `open` sheet, the policy pushes, and the supplier walks. That is the incident in finding 3 by another path. It also makes `standing()` return a stale `offer_id`, which gives a 422 at accept.
- **Fix, timeouts.** When the session's `offer_id` is not on any message, append the timeout answer that carries it (diff B, `merged`).
- **Verify.** Check the `timeouts` item shape in a logged D01 deliberate-timeout session before the freeze. The merge is a no-op if the list is empty.
- **EV.** About +2–4 points.

### 5. The final runner never restarts a case whose `play_case` raised (`runner.py`, `play_final`, ≈l.150-158)

- **E.** `one()` returns the exception. `if cid not in started` is then false forever.
- **Scenario.** A blip at wave start makes `POST /sessions` fail after retries, or a crash escapes before the session is played. The case is lost for the whole wave and scores the alternative or 0.
- **E.** `RemoteTable(client, case)` resumes a running final session on the 409 (docstring, `threads.py:112`), so a restart is safe.
- **Fix.** Resubmit, up to 3 times, while the wave is open and more than 20 s remain (diff C).
- **EV.** About +2–4 points.

### 6. One slow round pulls every later close minutes early (`threads.py:318`, `_cap_near`)

- **E.** `s.slowest = max(s.slowest, now - s.replied_at[sid])` feeds `max(CLOSE_BEFORE_CAP_S, slowest + ROUND_MARGIN_S)`.
- **Scenario.**
  - A round that hung through an outage (190 s) sets `slowest` to 190.
  - The case then closes about 205 s before the cap instead of 90 s, accepting mid-negotiation sheets in every thread of that case.
- **Fix.** Cap the contribution at 75 s (diff B).
- **EV.** About +1–2 points, only after an incident.

### 7. Policy state drifts from what was actually sent: holds, 422s, restarts (`agent.py:_state`; `policy.py:offer` appends before sending)

- **E.** `Policy.offer` appends to `t.our_prices`, `t.our_costs` and `t.last_sheet`, and marks claims used, inside `decide`. The runtime can still drop that decision:
  - a late decision is replaced by `HOLD_BODY`;
  - a 422 is replaced by a hold;
  - a `closing` started meanwhile.
- **Scenario, dropped decision.** The next concession is computed from a price the supplier never saw, a jump of our own. `prev == decision.term_sheets[0]` and the hold detection compare against a phantom sheet.
- **Scenario, restart.** After a process restart mid-wave, a fresh `ThreadState` has `our_prices=[]`. `next_price` re-anchors at `low + open_frac × gap`, below our previous asks. That is a visible retreat.
- **E, why a retreat hurts.** The supplier's cumulative gap rises: Dralveck walked at a cumulative gap of 39% after a 3% deeper anchor (`practice-v12-P05.log`).
- **Fix.** On every `_state`, if `len(our_prices)` differs from the number of buyer messages with sheets, rebuild `our_prices` and `last_sheet` from those messages, and mark their refs used (diff D).
  - The invariant holds because every `send` with sheets appends exactly one price, and holds carry no sheets.
- **Not fixed by diff D.** Claims chosen for a dropped decision stay marked as used.
- **EV.** About +1–3 points.

### 8. Repeated 409 loop at the arena's round limit (`threads.py:304-306`)

- **E.** `learnings.md`: "Timeouts count as a round." `moves_left` counts only our messages.
- **Scenario.**
  - After a timeout we believe one round is left, so we send.
  - We get 409 (round limit), refresh, decide and send again: another 409.
  - Each lap costs an LLM call.
  - In practice there is no cap, so it loops until the thread lapses. In the final it loops until the cap, when the close accepts.
- **Fix.** After two 409s in a row, stop the worker. `play()` then supervises the close and accepts the best eligible sheet (diff B).
- **EV.** About +1 point.

### 9. Missed opportunity, RFQ: a rival offer is cited to only one other bidder (`policy.py:pick_claims`)

- **E, rules.** `api.md`: a rival's quote "you may cite it to every other bidder, and it counts once per supplier."
- **E, code.** The pool filters `self.used_refs.isdisjoint(c.refs)`, and `used_refs` is shared across suppliers. So once `offer:A-2` is cited to B, C never gets it in that round.
- **E, value.** Rival citations were the strongest RFQ lever: "RFQ 0.67 → 0.82" (`EVALUATION.md`, `697cf46d`). Our `used_keys` is already per supplier.
- **Fix.** Exempt `rival:` keys from the global `used_refs` (diff E).
- **Verify.** Confirm in a P05 log that rival claim keys start with `rival:`. `offer()` relies on that prefix.
- **EV.** About +1–2 points if a wave has 3-bidder RFQs.

### 10. A failed opening-quote download leaves standard terms empty, which can break a must-have (`threads.py:128-130`)

- **E.** The download is retried only "with the next message that carries it". The quote PDF comes again only with `final_offer` or `agreed`. Then `standard_terms` is empty and `t.standard` is `{}`.
- **E.** `closing_terms` fills any field left out with the buyer's plan, for example `lead_time_days = need`. `must_haves_ok` can then pass a sheet whose real standard term breaks the must-have. A broken must-have scores 0.
- **I.** This matters most for unfamiliar hidden suppliers whose term sheets leave fields out (`missing_fields`).
- **Fix (no diff here).**
  - Retry opening downloads before the workers start.
  - Make `eligible_cost` refuse a sheet when a must-have field is neither in the sheet nor in `t.standard`.

### 11. Calls in `_finish` hold final pool slots (`threads.py:175-193`)

- **E.** `backoffice` is a guaranteed 403 during the final. `archive_session` makes several GETs.
- **E.** With 180 s timeouts during an outage, these keep a `parallel=10` worker busy, so the next wave's cases queue. `_docs_pool.shutdown(wait=True)` does the same.
- **Fix.** Skip `backoffice` when a deadline is set (diff B). Archive the final after it ends, using `GET /v1/sessions?set=final`.

### 12. Risk in code I cannot see: LLM client timeouts

- **E.** `_decide_pool` has `len(workers) × 2` threads. Late decisions keep running.
- **I.** If the writer or reader HTTP calls ignore `deadline` (for example when the LLM provider is unreachable during the same outage), stuck calls fill the pool. Every later move then becomes a `HOLD_BODY`: no sheet, a round burned and no movement, and the supplier sends its final offer.
- **Fix.** Check that the `buyer/llm` client sets a hard timeout no longer than the remaining deadline, and that `LLM_DISABLED` is honoured when the provider fails.

**Testing before the freeze.** Run sandbox D02 with a fault-injecting transport, such as an `httpx.MockTransport` wrapper that stalls or drops every Nth call. Or pull the cable for 30 s and 90 s mid-thread. Expect no worker crash, no resend after the window, and the clock taken from `seconds_left`.

---

## Diffs

### A. `client.py`: split timeouts, keepalive, `move_id` and `deadline`

```diff
--- a/starter-kit/arena_kit/client.py
+++ b/starter-kit/arena_kit/client.py
@@ -1,8 +1,9 @@
 """Thin HTTP client for the arena API. Every method returns the JSON the server sends."""
 
 import os
+import socket
 import threading
 import time
 import uuid
 
 import httpx
@@ -15,6 +16,21 @@
 # A supplier's reply can take up to about a minute (its time does not count against your 60 s),
 # and a call may wait for another call on the same session first: wait long enough for both.
 TIMEOUT_S = 180.0
+# ...but a dead Wi-Fi must not look like a slow supplier: connect and write fail fast, and TCP
+# keepalive ends a read whose path is gone (~25 s) - a live server's kernel ACKs the probes.
+CONNECT_TIMEOUT_S = 6.0
+WRITE_TIMEOUT_S = 15.0
+
+
+def _keepalive():
+    opts = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
+    idle = getattr(socket, "TCP_KEEPIDLE", None) or getattr(socket, "TCP_KEEPALIVE", None)  # Linux / macOS
+    for opt, value in ((idle, 10), (getattr(socket, "TCP_KEEPINTVL", None), 5), (getattr(socket, "TCP_KEEPCNT", None), 3)):
+        if opt is not None:
+            opts.append((socket.IPPROTO_TCP, opt, value))
+    return opts
+
 # Practice has a daily quota per team: every practice session start carries what is left in this
 # header, and GET /v1/me tells where the team stands.
 REMAINING_HEADER = "X-Practice-Remaining"
@@ -48,13 +64,19 @@ class ArenaClient:
         headers = {"X-API-Key": key} if key else {}
         self.retries, self.rate, self._lock, self._next = retries, rate, threading.Lock(), 0.0
         self.practice_remaining = None  # from the last practice reply that said so
-        self.http = httpx.Client(base_url=f"{base_url}/v1", headers=headers, timeout=timeout, transport=transport)
+        timeouts = httpx.Timeout(timeout, connect=CONNECT_TIMEOUT_S, write=WRITE_TIMEOUT_S, pool=30.0)
+        transport = transport or httpx.HTTPTransport(socket_options=_keepalive())
+        self.http = httpx.Client(base_url=f"{base_url}/v1", headers=headers, timeout=timeouts, transport=transport)
 
@@ -60,8 +82,13 @@ class ArenaClient:
-    def _call(self, method, path, body=None, params=None, raw=False):
-        headers = {MOVE_ID_HEADER: uuid.uuid4().hex} if method == "POST" else {}
+    def _call(self, method, path, body=None, params=None, raw=False, move_id=None, deadline=None):
+        """`move_id`: one id for every resend of the same move. `deadline` (monotonic): no resend after it -
+        a resend that lands after the arena timed the move out is a new, late move."""
+        headers = {MOVE_ID_HEADER: move_id or uuid.uuid4().hex} if method == "POST" else {}
         for attempt in range(self.retries + 1):
+            if attempt and deadline is not None and time.monotonic() > deadline:
+                raise TimeoutError(f"{method} {path}: past the move's deadline, not resent")
             self._pace()
@@ -101,9 +128,9 @@ class ArenaClient:
-    def send_message(self, session_id, supplier_id, message):
+    def send_message(self, session_id, supplier_id, message, move_id=None, deadline=None):
         """Your e-mail to one supplier; returns its reply (or the result, if `action` closes)."""
         path = f"/sessions/{session_id}/threads/{supplier_id}/messages"
-        return self._call("POST", path, {"message": message})
+        return self._call("POST", path, {"message": message}, move_id=move_id, deadline=deadline)
```

`SafeClient._call(self, method, path, *args, **kwargs)` passes the new keywords through unchanged.

### B. `threads.py`: resilient resend and refresh, arena clock, timeout answers, capped `slowest`, 409 guard, no backoffice in the final

```diff
--- a/src/buyer/runtime/threads.py
+++ b/src/buyer/runtime/threads.py
@@ -38,6 +38,7 @@
 import logging
 import threading
 import time
+import uuid
 from concurrent.futures import ThreadPoolExecutor
@@ -69,6 +70,24 @@
 AFTER_CAP_S = 30.0  # past the wave's cap the arena has ended the case: confirm it, then stop
+SEND_MARGIN_S = 6.0  # resend with the same move id only while the arena's 60 s surely still run
+REFRESH_GIVE_UP_S = 600.0  # network down: keep asking the arena this long before the worker gives up
+SLOWEST_CAP_S = 75.0  # a round stretched by an outage must not pull every close minutes early
+CONFLICT = "conflict"
+
+
+def merged(t, th):
+    """The thread's e-mails, plus the supplier's answer to a timed-out move when that answer carries its
+    standing offer (GET thread lists those under `timeouts`, not `messages`)."""
+    messages, standing = list(t.get("messages") or []), th.get("offer_id") or t.get("offer_id")
+    carried = {ts.get("term_sheet_id") for m in messages for ts in m.get("term_sheets") or []}
+    if standing and standing not in carried:
+        answers = [m for m in t.get("timeouts") or []
+                   if any(ts.get("term_sheet_id") == standing for ts in m.get("term_sheets") or [])]
+        messages += answers[-1:]
+    return messages
+
 HOLD_BODY = (
@@ -178,4 +197,6 @@ class CasePlayer:
         for kind, get in (("session", self.client.session), ("backoffice", self.client.backoffice)):
+            if kind == "backoffice" and self.deadline:  # the final: 403 until it is over
+                continue
             try:
@@ -196,3 +217,3 @@ class CasePlayer:
     def _worker(self, sid):
-        s, failures, close_failures = self.state, 0, 0  # close_failures: not reset by a fresh decision
+        s, failures, close_failures, conflicts = self.state, 0, 0, 0  # close_failures: not reset by a fresh decision
         while not s.ended.is_set() and s.live(sid):
@@ -246,4 +267,10 @@ class CasePlayer:
-            if self._send(sid, msg, decide_s=time.monotonic() - t0) == INVALID:
+            sent = self._send(sid, msg, decide_s=time.monotonic() - t0)
+            conflicts = conflicts + 1 if sent == CONFLICT else 0
+            if conflicts >= 2:  # the arena counts rounds we don't (timeouts): stop; the close accepts the best
+                self.log("drop", supplier_id=sid, reason="repeated 409")
+                return
+            if sent == INVALID:
                 # 422: nothing happened and no round was used; hold now, while the clock still allows
@@ -295,16 +322,25 @@ class CasePlayer:
     def _exchange(self, sid, msg):
-        s, sent = self.state, time.monotonic()
-        try:
-            reply = self.client.send_message(self.table.session_id, sid, msg)
-        except ArenaError as e:
-            self.log("error", supplier_id=sid, status=e.status, detail=e.detail)
-            if e.status == 422:
-                log.warning("%s %s: message refused: %s", self.case_id, sid, e.detail)
-                return INVALID
-            if e.status != 409:
-                raise
-            return self._refresh(sid)  # late, round limit, thread or case ended: ask the arena
-        except Exception as e:  # the network, after the client's own retries: did the message land?
-            log.warning("%s %s: send failed (%s) - asking the arena", self.case_id, sid, e)
-            self.log("error", supplier_id=sid, detail=e, where="send")
-            return self._refresh(sid)
+        s, sent, move_id = self.state, time.monotonic(), uuid.uuid4().hex
+        window = s.replied_at[sid] + MOVE_LIMIT_S - SEND_MARGIN_S
+        while True:
+            try:
+                reply = self.client.send_message(self.table.session_id, sid, msg, move_id=move_id, deadline=window)
+                break
+            except ArenaError as e:
+                self.log("error", supplier_id=sid, status=e.status, detail=e.detail)
+                if e.status == 422:
+                    log.warning("%s %s: message refused: %s", self.case_id, sid, e.detail)
+                    return INVALID
+                if e.status == 409:  # late, round limit, thread or case ended: ask the arena
+                    self._refresh(sid)
+                    return CONFLICT
+                if e.status < 500 and e.status != 429:
+                    raise
+            except Exception as e:  # the network, after the client's own retries
+                log.warning("%s %s: send failed (%s)", self.case_id, sid, e)
+                self.log("error", supplier_id=sid, detail=e, where="send")
+            if s.ended.is_set() or time.monotonic() > window - 1.0:
+                return self._refresh(sid)  # past the window a resend may land as a new, late move: ask first
+            s.ended.wait(1.0)  # inside the window the same move id is safe whether it landed or not
         now = time.monotonic()
@@ -317,18 +353,31 @@ class CasePlayer:
             s.threads[sid] += [{**msg, "from": "buyer"}, reply]
-            s.slowest = max(s.slowest, now - s.replied_at[sid])
+            s.slowest = max(s.slowest, min(now - s.replied_at[sid], SLOWEST_CAP_S))
             s.replied_at[sid] = now
 
     def _refresh(self, sid):
-        """After a 409: the session's state and this thread as the arena has them."""
+        """After a 409 or a lost reply: the session and this thread as the arena has them, the clock from
+        `seconds_left`. While the network is down: keep asking - the arena's answer decides."""
         s = self.state
-        state = self.client.session(self.table.session_id)
+        give_up = time.monotonic() + REFRESH_GIVE_UP_S
+        while True:
+            try:
+                state = self.client.session(self.table.session_id)
+                t = None if state.get("status") == "ended" else self.client.thread(self.table.session_id, sid)
+                break
+            except Exception as e:
+                self.log("error", supplier_id=sid, detail=e, where="refresh")
+                if s.ended.is_set():
+                    return None
+                if time.monotonic() > give_up:
+                    raise
+                s.ended.wait(2.0)
         if state.get("status") == "ended":
             return self._ended(state.get("result") or {"deal": False, "end_reason": state.get("end_reason")})
-        t = self.client.thread(self.table.session_id, sid)
-        for m in t["messages"]:
+        th = (state.get("threads") or {}).get(sid) or {}
+        messages = merged(t, th)
+        for m in messages:
             self._documents(m, sid)
         with s.lock:
-            s.threads[sid] = t["messages"]
-            if t.get("closed"):
+            s.threads[sid] = messages
+            if t.get("closed") or th.get("closed"):
                 s.closed.add(sid)
-            s.replied_at[sid] = time.monotonic()  # the arena answered our late move just now
+            left = th.get("seconds_left")  # the arena's clock, not ours: our move may never have arrived
+            s.replied_at[sid] = time.monotonic() - (max(0.0, MOVE_LIMIT_S - left) if left is not None else 0.0)
         self.log("refresh", supplier_id=sid, thread=t)
@@ -470,3 +519,3 @@ class CasePlayer:
                     continue
-                s.threads[sid] = t["messages"]
+                s.threads[sid] = merged(t, th)
                 if t.get("closed") or th.get("closed"):
```

### C. `runner.py`: restart a crashed final case while its wave runs

```diff
--- a/src/buyer/runtime/runner.py
+++ b/src/buyer/runtime/runner.py
@@ def play_final(client, *, agent="policy", params=None, waves=5, parallel=10, poll=POLL_S, root=env.RUNS):
     started, closed, caps = {}, set(), {}  # caps: wave -> its cap as time.time()
+    tries = {}  # case -> restarts after a crash; the arena's 409 resumes the running session
     archive = root / "final_sessions"
@@
                 if case.get("seconds_left") is not None:  # each wave has its own cap; follow an extension
                     caps[wave] = time.time() + case["seconds_left"]
+                f = started.get(cid)
+                if (f is not None and f.done() and isinstance(f.result(), BaseException)
+                        and tries.get(cid, 0) < 3 and (case.get("seconds_left") or 0) > 20):
+                    tries[cid] = tries.get(cid, 0) + 1
+                    log.warning("%s: restarting after %r (%d of 3)", cid, f.result(), tries[cid])
+                    del started[cid]
                 if cid not in started and case.get("seconds_left"):
```

### D. `agent.py`: keep policy state equal to what the supplier actually received

```diff
--- a/src/buyer/runtime/agent.py
+++ b/src/buyer/runtime/agent.py
@@ def _state(self, case, sid, events):
             t = self.states[sid] = ThreadState(sid, sheet_id, terms, "open", {}, 0, profile=profile)
         t.standing_id, t.standing_terms = sheet_id, terms
+        ours = [m["term_sheets"][0]["terms"] for m in events if m.get("from") == "buyer" and m.get("term_sheets")]
+        if len(t.our_prices) != len(ours):  # a resumed case, or a decision that never went out (hold, 422)
+            t.our_prices = [o.get("unit_price") for o in ours]
+            t.our_costs = t.our_costs[: len(ours)]
+            t.last_sheet = ours[-1] if ours else None
+            self.policy.used_refs |= {r for m in events if m.get("from") == "buyer" for r in m.get("refs") or []}
         t.offers = [(ts["term_sheet_id"], ts["terms"]) for ts in latest(events).get("term_sheets") or [] if ts.get("term_sheet_id")]
```

Because every policy `send` with sheets appends exactly one price, this branch never fires in a normal move. It changes nothing in the 77–78 practice behaviour.

### E. `policy.py`: rival offers to every other bidder

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def pick_claims(self, case, t):
         pool = [
             c for c in bank
             if c.strength >= self.p["claim_min_strength"]
             and (t.supplier_id, c.key) not in self.used_keys
             and c.key not in rejected
-            and self.used_refs.isdisjoint(c.refs)
+            and (c.key.startswith("rival:") or self.used_refs.isdisjoint(c.refs))  # api.md: once per supplier
         ]
@@
         for c in chosen:
-            self.used_refs |= set(c.refs)
+            if not c.key.startswith("rival:"):
+                self.used_refs |= set(c.refs)
             self.used_keys.add((t.supplier_id, c.key))
```

---

## Evidence versus inference, summarised

**Shown by evidence:**
- the 180 s hangs and the 5 lost cases;
- the 503 resend that became a push after a final offer;
- timeouts counting as rounds;
- the arena serialising calls within a session;
- `timeouts` listed separately in GET thread;
- code paths that crash a worker (findings 2 and 8);
- the global `used_refs`.

**Inferred, and why:**
- **Auto timeouts every 60 s.** Consistent with "collects timeouts" and the walk after about 3 minutes.
- **The shape of `timeouts` items.** Unverified. `merged` is a no-op when they don't match.
- **The arena's behaviour on a same-id resend while the original is still being processed.** Unknown. Diff B falls back to a GET on 409.

Diffs A–C carry most of the code-side EV. Finding 0 (the VM) carries more than all of them together.