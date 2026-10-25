# Review: reader → signals → policy (Team Holdout buyer agent)

**Scope and conventions.** Line numbers are approximate (`≈`) because the files were pasted without numbering, so I also name the function or constant. Each finding separates **Shown**, meaning visible in the code or quoted docs, from **Inferred**, meaning my reasoning, which needs a log check.

**Points arithmetic.** The final has 5 waves, each scored as mean case score × 100. A gain of +0.01 in mean score is therefore about +5 final points.

---

## Ranked findings

### 1. The LLM reader almost never reaches the policy, and the keyword rules miss the most common ask. Expected gain: +0.01 to +0.02 mean (5–10 pts), mostly on hidden suppliers.

**Shown: the LLM reading arrives too late.** Trace `PolicyAgent.decide` in `agent.py`:

- `_read` (≈L150–175) runs `read(..., use_llm=False)`, stores the rules reading as `readings[sid] = (n, rules)`, and starts the LLM in a daemon thread.
- Control returns at once. `_state` then copies `readings[sid]`, still the rules reading, into `t.signals`.
- `policy.decide` runs on those signals. The writer also receives the same rules `reading` object.
- `_read_in_background` swaps in the LLM reading only if `current[0] == n`. By then the policy has already decided for reply `n`.
- On the next reply, `n` has changed. `_read` re-reads with the rules and overwrites the slot.

**Consequence.** The LLM signal lands in time only on the first move of a case, while `_warm` loads profiles for a few seconds. On every later move the policy plays on regexes. The module docstring's claim ("its Signals replace the rules' for this reply as soon as they arrive") is true for the log, not for the decision.

**Shown: the rules miss the top ask.** The learnings record "Which volume can you commit to?" 152 times in 829 supplier e-mails, the most frequent ask. `ASK_RULES["volume"]` (`reader.py` ≈L262) cannot match it:

- It needs `more|additional|higher|larger|extra` before "volume", or "volume commitment", "spare capacity" and similar.
- "Which volume can you commit to?" contains none of these.
- "A binding higher volume would help us" does match, through "higher volume".

**Scenario.** P07 (Leitner, spare second shift) asks "Which volume can you commit to?":

- `t.signals["asks"]` is `[]`.
- `offer()` (≈L330) adds `lever_trades` only when `t.holding or asks`, so no volume package is offered.
- The writer's code volume line answers in words only, and per api.md "term sheets bind, nothing else".
- Ours is 0.65–0.705 against a record of 0.779 (NIGHT_CONTEXT). Winners closed at 36 m.

**Inferred: hidden-case risk.** New personas will phrase things the 40+ regexes have never seen. That is exactly where the LLM reader earns its cost, and today it is bypassed.

**Fix (Diffs 1 and 2a).**
- Wait a bounded time for the LLM: 4 s by default, set by `BUYER_READER_WAIT_S`; use 0 to restore today's behaviour.
- Add the volume-question patterns to the rules as the fallback.

**Check first.** In the run logs, compare `trace.diplomat.reader.signals.asks` with `reader_llm.signals.asks` per move.

**Caveat.** `MAX_TOKENS = 10000` suggests a reasoning model may be in use. The wait only pays off if the reader model is non-reasoning or uses low effort.

---

### 2. `accept_gap_pct` is measured against total C, not against the room still open, so the agent closes one round early. Expected gain: +0.005 to +0.015 mean.

**Shown.** In `Policy.decide` (≈L185):

```
close = c_track(standing) <= our_costs[-1] * (1 + accept_gap_pct/100)
```

with a default of 1.0, followed by `self.close(...)`. A further detail loosens the threshold more: `our_costs[-1]` is the **max** C over all our sheets (`offer()`, ≈L345), and lever-trade sheets are included in that max.

**Inferred: the threshold is wide relative to what is still negotiable.** Here, 1 % of C is roughly 1 % of price.

- **P08, Donautal.** Learnings: "counters of +0.04 to +0.20" above our ask.
  - At our ask of 5.36, its counter of 5.40 is 0.75 % above. We accept 5.40.
  - The record is 5.21–5.35, and C_best is about 5.10 fixed.
  - 0.04 is about 6 % of the score range.
- **P01, Brandlhuber.**
  - At our ask of 129.90, its counter of 131.00 is 0.85 % above, so we close.
  - Learnings: stepping on reached 129.5–129.8 (0.987–0.995) against 131.27 (0.909).
  - Its median concession is 0.62 of our move, so one more round is worth about 0.02–0.05 on that case.

**Reference point.** The Munich team's rule was "within 5 % of the way from the opening cost to our last ask", which is relative to the room, not to C.

**Fix (Diff 3).** Allow `min(1 % of C, 10 % of the room)`. Final offers still go to `close()` and are accepted, so the downside is extra rounds, not walk-aways. We never push a final offer (`push_final = 0`).

---

### 3. Reader false positives inflate the supplier's cash rate and drop negations. Expected gain: +0.005 to +0.01 mean.

**3a. A boilerplate acknowledgement is read as cash pressure.**

**Shown.** The arena's own reply to a 14-day sheet (api.md example) contains: "Faster payment helps our cash flow; that is reflected in the price." This sentence triggers three things:

- `CASH_RE` matches via `cash ?flow` and `faster payment`, so `cash_pressure = True`.
- `ASK_RULES["faster_payment"]` matches via `faster payment` and `payment helps our cash`.
- No negation follows the match, so neither hit is discarded.

The policy then escalates the supplier's cash rate:

- `Policy.cash` (≈L470) sets the rate to `max(..., 0.2)` and pressure to 0.6.
- `supplier_model` (≈L355) applies `pressure >= 0.5`, so the rate becomes `max(rate, 0.18)`.
- That gives `cash_hungry`, which does two things:
  - `menu()` skips the `OWN_PRICE_SLACK` filter.
  - `lever_trades` adds payment-day trades.

**Inferred: a feedback loop.**
- Our menu offers shorter payment, the supplier acknowledges it, and we then treat it as 18 %/yr cash-short.
- We offer more early-payment packages, priced as if 46 days were worth about 2.3 % of price to it.
- Suppliers answer our levers at their own price. Munich saw 430.01 at 30 d come back instead of 432.94 at 90 d.
- Learnings measured real rates far lower: distributors about 0, Nordmark about 6 %, Selvbrunn about 4 %.
- For Nordmark, 14 days cost us about 1.0 % of spend. It moved 0.7 % for it once (learnings), a net loss in a case whose whole range is small.

**Fix (Diffs 2b and 4).** Exclude sentences that only price *our* proposal ("reflected in the price", "priced in") from the cash and ask rules, and tell the LLM the same.

**3b. "We cannot …" is not treated as a negation.**

**Shown.** `NEGATION_BEFORE_RE` (≈L334) contains `\bnot\b`. In "cannot" there is no word boundary before "not", and the `n't` branch does not apply either.

**Scenario.** "We cannot offer an index clause" produces `asks = ["index_clause"]`. `lever_trades` then ranks a clause sheet at `(0, delta_c)` every round, wasting one of three sheet slots and signalling that we did not listen. The same happens with "we cannot offer a volume discount", "we cannot accept a longer contract" and similar.

**Fix (Diff 2c).** Add `we|I cannot`, `unable`, `declin*` and `refus*` as negations. "You cannot commit to a binding higher volume" (Nordmark) deliberately remains an ask.

---

### 4. `capacity_issue` never reaches the policy's speed pricing. Expected gain: +0.003 to +0.01 mean (hidden capacity and bottleneck cases).

**Shown.** In `supplier_model`, the lead-time effort is `ARCHETYPE_LEAD_EFFORT.get(archetype, 0.001)`, and only `near_monopolist` gets 0.005. The reader's `capacity_issue` is never read by the policy.

**Evidence (Munich EVALUATION).**
- Suppliers with a full order book priced speed at 0.2–0.5 % of price per day.
- Raising their prior to 0.3 % lifted the capacity case from 0.58 to 0.66.
- Hrvelec: 31.50 at 52 d, 33.00 at 42 d.

**Inferred: hidden-case scenario.** A sold-out supplier whose Scout archetype is `unknown` or `family_foundry` writes "our order book is full, lead times have been extended".
- Our menu still values each day of speed at 0.1 %, so it keeps asking for the short lead time at nearly the same price.
- The supplier prices in overtime and finals on its own lead time.
- We miss the cheaper long-lead package, within must-haves, that C may prefer.

**Fix (Diff 5).** Set the lead effort to at least 0.003 when the supplier signals capacity. This is not keyed to a case or supplier id.

---

### 5. Signals are replaced on every reply, not accumulated. Expected gain: +0.002 to +0.005 mean; also reduces oscillation.

**Shown.** `_state` (≈L95) sets `t.signals = asdict(latest reading)`.

**Effects.**
- An ask made once (often in round 1) disappears from `asks` on the next reply, and so does its lever trade.
- `cash_pressure` can flip 0.18 ↔ 0.07 between rounds. `menu()` reprices every payment combination, so our packages can jump or even step back.
- Learnings: Kalwisz asked for faster payment five times, then wrote "you just ignore it" and sent a final.

**Fix (Diff 6).** Make `cash_pressure`, `capacity_issue` and `asks` sticky within a thread. Do this together with Diff 2b, otherwise a one-off false positive becomes permanent.

---

### 6. Pushing after a `final_offer` through the mirror path. Tail risk: a walk scores 0, or the alternative.

**Shown.**
- `decide`, on `final_offer`, calls `close()`.
- If its alternative sheet is cheaper, `close()` mirrors it and prepends `clause_variants`, i.e. the same package with a wider deadband (≈L520).
- After a final offer this is a push.
- api.md: "push further and it may walk". Learnings: D01 walked after one sheet 0.1 below its final; distributors refused every deadband.

**Fix (Diff 7).** Mirror the alternative alone after a final offer.

---

### 7. The policy ignores tone, approval and final-language signals. No diff; test proposal.

**Shown.** The policy reads only these signal fields:
- `asks`
- `cash_pressure`
- `rejected_args`
- whatever `clause_wanted` reads (`costing.py`, not shown)

The fields `tone` (`IRRITATED_RE` includes "withdraw our offer", "no basis for further"), `approval_pending` and `final_offer_language` feed only the writer.

**Hidden traits likely to matter.** `approval_2pct` and `deprioritising_us` may appear in the final.

**Suggestions to test, not ship blind:**
- When `tone == "irritated"` and the offer is `acceptable`, close instead of stepping.
- When `approval_pending`, do not count the next unchanged reply as a hold.

---

### 8. Dead or mis-keyed argument feedback. Low impact.

- **Rejections never block anything new.** `_verified_keys` maps `claim_results[i]` to `last_decision.claims[i]` by position.
  - If the writer's guard drops a claim, or the arena reads an extra ID from the body, the indexes shift.
  - The fallback strings "not our reality" and "accepted an argument" never equal a `Claim.key`.
  - `pick_claims` already excludes used keys through `used_keys`.
  - Net effect: the `rejected` filter blocks almost nothing; a rejected `index:` argument never suppresses other index claims.
- **One sentence counts as both.** The bot's standard "it holds, but it does not change our calculation" matches both `ACCEPT_RE` and `REJECT_RE`.

---

### 9. False asks from the supplier restating its own terms. Low impact.

`longer_contract` matches `contract (?:length|duration|period) of` and `(?:two|three)-year`. Round-0 quote e-mails restating standard terms ("contract period of 12 months") can create an ask. I have not verified this in logs.

---

### 10. Sunday-release series codes. Low impact.

`SERIES_RE` accepts known prefixes only. A new series prefix in a hidden case's driver sentence is invisible to the rules, and therefore to `clause_wanted`. Only the LLM path accepts `LOOSE_SERIES_RE`, and per #1 that path does not reach the policy today.

---

## Live-final risks (summary)

- **Unknown personas.** These rest on regex coverage until Diff 1 is in.
- **Late-payment complaints.** The trait `complains_late_pay` matches `late payments?` in `CASH_RE`, which escalates the rate to 0.18. The supplier wants on-time payment, not shorter terms. The writer's commitment handles the relationship; the policy then also offers early-payment trades. Diff 2b does not change this.
- **Timing.** Diff 1 adds up to 4 s per move.
  - In a 3-bidder RFQ, the arena serialises replies (about 21 s each), and `MOVE_BUDGET_S = 23` already sits inside 60 s.
  - The writer still has its template fallback.
  - Set `BUYER_READER_WAIT_S=0` if the pre-flight shows replies arriving later than about 30 s.

---

## Diffs

### Diff 1: bounded wait for the LLM reading (finding 1)

```diff
--- a/src/buyer/runtime/agent.py
+++ b/src/buyer/runtime/agent.py
@@
 MOVE_BUDGET_S = 23.0  # reader + policy + writer, from the call; threads.DECIDE_BUDGET_S (25) runs from the reply
 READER_BUDGET_S = 10.0  # DIPLOMAT.md: the reader answers in < 10 s, else its keyword rules
+# the policy waits this long for the LLM reading of the reply it decides on (0 = rules only, as before)
+READER_WAIT_S = float(os.environ.get("BUYER_READER_WAIT_S", "4"))
 CLOSING_BUDGET_S = 8.0  # near the wave's cap: accept / walk need no LLM; a rare closing e-mail must be quick
@@ def _read(self, sid, events, deadline):
         if not self.blocking_reader and get_client("reader").enabled:
-            threading.Thread(
+            th = threading.Thread(
                 target=self._read_in_background, args=(sid, latest(events), n, last, deadline),
                 daemon=True, name=f"reader-{sid}",
-            ).start()  # fmt: skip
+            )  # fmt: skip
+            th.start()
+            th.join(timeout=max(0.0, min(READER_WAIT_S, deadline - time.monotonic())))
+            with self._lock:  # the LLM's reading of this reply if it came in time, else the rules'
+                current = self.readings.get(sid)
+                if current and current[0] == n:
+                    reading = current[1]
         return reading
```

### Diff 2: reader rules (findings 1, 3a, 3b)

```diff
--- a/src/buyer/llm/reader.py
+++ b/src/buyer/llm/reader.py
@@ ASK_RULES = (
     ("volume", _re(
         r"(?:more|additional|higher|larger|extra) (?:volume|parts|quantities|business|work)",
+        r"(?:which|what|how much) (?:annual |yearly |binding )?(?:volume|quantit(?:y|ies))",
+        r"(?:volume|quantit(?:y|ies)) (?:can|could|will|would) you (?:commit|guarantee|bind)",
+        r"binding (?:higher |annual |larger )?volume",
         r"free (?:machine )?capacity",
@@
+# a sentence that only prices a term WE proposed ("Faster payment helps our cash flow; that is
+# reflected in the price.") is the supplier answering our sheet - not an ask and not cash pressure
+ACK_RE = _re(r"reflected in (?:the|our) (?:price|offer|angebot)", r"(?:is|are|has been) priced in")
+
 NEGATION_BEFORE_RE = re.compile(
-    r"(?:\b(?:no|not|without|never|nor|nothing|none|kein\w*|nicht)\b|n't)\W+(?:\w+\W+){0,3}$", re.I
+    r"(?:\b(?:no|not|without|never|nor|nothing|none|unable|declin\w*|refus\w*|kein\w*|nicht)\b|n't"
+    r"|\b(?:we|i) cannot\b)\W+(?:\w+\W+){0,3}$", re.I
 )
@@ def rule_signals(message: dict, last_decision=None) -> Signals:
     body = _prose(str(message.get("body") or ""))
     claims = _claim_list(last_decision)
     sentences = _sentences(body)
+    ask_body = "\n".join(s for s in sentences if not ACK_RE.search(s))
@@
-    asks = [name for name, rx in ASK_RULES if _hit(rx, body, after=True)]
+    asks = [name for name, rx in ASK_RULES if _hit(rx, ask_body, after=True)]
@@
     return Signals(
-        cash_pressure=_hit(CASH_RE, body, after=True),
+        cash_pressure=_hit(CASH_RE, ask_body, after=True),
```

### Diff 3: accept gap measured against the room still open (finding 2)

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@
 OWN_PRICE_SLACK = 0.005
 CASH_HUNGRY_RATE = 0.15
+NEAR_ASK_SHARE = 0.1  # "close to our ask" = within this share of the room between its opening and our ask
@@ def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
-        gap = 1 + p["accept_gap_pct"] / 100
-        close = t.our_costs and self.c_track(case, t.standing_terms, t) <= t.our_costs[-1] * gap
+        slack = 0.0
+        if t.our_costs:  # 1 % of C is often a third of the whole negotiable range: cap it by the room left
+            room = max(0.0, t.opening_cost - t.our_costs[-1])
+            slack = min(t.our_costs[-1] * p["accept_gap_pct"] / 100, NEAR_ASK_SHARE * room)
+        close = t.our_costs and self.c_track(case, t.standing_terms, t) <= t.our_costs[-1] + slack
         if close and acceptable and c_theirs < t.opening_cost:
```

`opening_cost` uses `c` (relationship-aware) and `our_costs` uses `c_track`. For family foundries the room is therefore slightly overstated, which is acceptable for a threshold.

### Diff 4: reader prompt (finding 3a)

```diff
--- a/src/buyer/llm/prompts/reader_system.md
+++ b/src/buyer/llm/prompts/reader_system.md
@@
-- cash_pressure: cash matters to it now - it asks for faster payment, a cash discount or prepayment, mentions cash flow, liquidity, its bank or overdue invoices, or says faster payment is valuable to it.
+- cash_pressure: cash matters to it now - it asks for faster payment, a cash discount or prepayment, mentions cash flow, liquidity, its bank or overdue invoices, or says faster payment is valuable to it. NOT when it only says that a payment term WE proposed is reflected in its price ("Faster payment helps our cash flow; that is reflected in the price").
@@
-- asks: what it wants from us, from this list: faster_payment, volume, longer_contract, forecast, earlier_effective_date, index_clause, longer_lead_time, tooling_payment, incoterm. Anything else as "other: <a few words>".
+- asks: what it wants from us, from this list: faster_payment, volume, longer_contract, forecast, earlier_effective_date, index_clause, longer_lead_time, tooling_payment, incoterm. Anything else as "other: <a few words>". A question counts ("Which volume can you commit to?" = volume). Something it refuses ("we cannot offer an index clause") is not an ask, and neither is pricing a term we proposed.
```

### Diff 5: capacity signal sets the price of speed (finding 4)

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@
 ARCHETYPE_LEAD_EFFORT = {"near_monopolist": 0.005}
+CAPACITY_LEAD_EFFORT = 0.003  # sold-out suppliers priced speed at 0.2-0.5 % of the price per day
@@ def supplier_model(self, case, t):
         lead = ARCHETYPE_LEAD_EFFORT.get((t.profile or {}).get("archetype"), 0.001)
+        if (t.signals or {}).get("capacity_issue"):  # any archetype: a full book makes speed overtime
+            lead = max(lead, CAPACITY_LEAD_EFFORT)
```

### Diff 6: sticky thread signals (finding 5)

```diff
--- a/src/buyer/runtime/agent.py
+++ b/src/buyer/runtime/agent.py
@@ def _state(self, case, sid, events):
         reading = self.readings.get(sid)
         if reading:  # the Diplomat's reading of this supplier's latest reply
-            t.signals = dataclasses.asdict(reading[1].signals)
+            new, old = dataclasses.asdict(reading[1].signals), t.signals or {}
+            for f in ("cash_pressure", "capacity_issue"):  # what it told us once stays true in this thread
+                new[f] = bool(new.get(f) or old.get(f))
+            new["asks"] = list(dict.fromkeys([*(new.get("asks") or []), *(old.get("asks") or [])]))
+            t.signals = new
         return t
```

The merge is idempotent across repeated `_state` calls, because OR and union with itself change nothing.

### Diff 7: no deadband push after a final offer (finding 6)

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def close(self, case, t, acceptable, c_theirs, rival_best_c):
                 t.mirrored = True
                 sheet = complete_offer(case, dict(alt[2]))
-                variants = self.clause_variants(case, t, sheet)  # its package, but our cheapest deadband first
+                # its package, our cheapest deadband first - never after a final offer (a push: it may walk)
+                variants = [] if t.status == "final_offer" else self.clause_variants(case, t, sheet)
```

---

## Validation (cheap, before spending quota)

1. **Diff 1.** Grep the run logs for moves where `reader_llm.signals` differs from `reader.signals` in `asks` or `cash_pressure`. This sizes the finding on real e-mails.
2. **Diffs 2 and 4.** Replay every logged supplier body through `rule_signals` before and after the change. Count:
   - `cash_pressure` hits on suppliers whose archetype is not `cash_short_jobshop`;
   - `index_clause` asks in sentences containing "cannot";
   - volume questions caught.
3. **Diff 3.** Count past closes that fired through the `close` branch rather than `final_offer` or `agreed`, together with their gap as a share of the room.
4. **Hosted runs.** Spend a hosted batch only on P07, P01 and P08, with 2 runs each because of the 1–2 % supplier noise. Use P03 and P04 as no-change guards.
5. **Pre-flight.** Run with `BUYER_READER_WAIT_S` at 4 and check that no RFQ thread exceeds about 30 s per move.

**What is not covered.** `costing.lever_asked` and `clause_wanted` were not shown. Check that `"volume"` maps to `volume_per_year` and/or `contract_months` when they are negotiable; otherwise finding 1's gain on volume asks is zero.