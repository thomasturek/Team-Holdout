# Arena mechanics we misuse — ranked by expected gain

Method: every "theirs vs ours" figure below is read from `sessions_digest.txt`; C-arithmetic uses `cost.py`. What is already right and therefore skipped: we accept only standing sheets, we never counter a `final_offer` (4/4 walks when we did), we send menus, we treat the alternative as a ceiling, we cite rival offers once per bidder, and P02/P03/P04 sit within 0.01 of the public records — nothing to gain there.

---

## 1. Latency: a move that misses the 60-s clock scores 0 (and four of five such moves were plain accepts)

**Evidence.** In one batch (purpose `final-candidate`, 01:38–01:52) five sessions ended `end=timeout`, score 0: P03 `37b4e28d` (open at r4, nothing sent), P07 `bf98975f` (supplier `final_offer` 5.57/5.51, no reply from us), P08 `76b7cbbb` (`final_offer` 5.39, no reply), P11 `49409787` (`final_offer` 45.50 — our best-ever P11 price, no reply), P18 `9ebd2de0` (open at r2, no reply). The rerun 10 minutes later (`final-candidate-rerun`) closed all of them (0.932, 0.666, 0.679, 0.000→n/a, 0.563). Mean of that batch lost ≈0.33 across five cases.

**Mechanism (inferred).** The LLM calls (reader, writer) sat in the per-move path. api.md: a late message counts as a timeout; three in a row, or one after the last round, end the thread. Four of the five pending moves were `accept` — which needs no model at all (`to_message` returns the action without calling `write`). In the Live Final the risk is larger: up to 10 parallel sessions, the arena serialises calls within an RFQ session, and the 8-min wave cap.

**Change.** (a) Decide and act on `final_offer`/`agreed` before any model call: the policy only needs `claim_results`/terms, not the reader's prose signals. (b) A default budget inside the writer so it can never be the cause:

```diff
--- a/src/buyer/llm/writer.py
+++ b/src/buyer/llm/writer.py
@@
 MAX_TOKENS = 10000
+DEFAULT_BUDGET_S = 20.0  # the e-mail must exist 20 s after the supplier's reply, model or template
@@ def write(
     t0 = time.monotonic()
+    if deadline is None:
+        deadline = t0 + DEFAULT_BUDGET_S
     if attr(decision, "kind") != "send":
```
(c) The same hard budget for the reader (not shown here; the night log's `runs/night/runtime_resilience.patch` has pieces of it) with the rule-based signals as fallback. Learnings: template e-mails produced the same prices as model e-mails on P02/P18.

**Affects / expected.** Every case. If 2–5 % of final moves would otherwise time out: +0.02–0.05 mean; in the batch above it was +0.33. **Risk:** more template e-mails; no score risk.

---

## 2. `same_cost` capitulation: the relationship-loaded cost of our *ask* makes us price our sheet at the supplier's price minus one cent, and the lever trades then close the deal early

**Evidence (data).** Every P01 session since the relationship charge entered `Policy.c` (purpose `claims-commit-relationship` onwards) that contains a sheet at exactly `theirs − 0.01` closed within one round of it:

| session | supplier standing | our sheets that round | result |
|---|---|---|---|
| `7807fb7a` r2 | 136.90@30 | 136.89@30, 137.30@30 | agreed 137.30 → 0.800 |
| `d9cfc61a` r2 | 136.50@30 | 136.49@30 | agreed → 0.848 |
| `6d1edc5d` r3 | 136.10@30 | 135.29@14, 136.09@30 | agreed 135.29@14 → 0.875 |
| `9c0ba9cd` r4 | 135.40@30 | 134.60@14, 135.39@30 | agreed → 0.909 |
| `38367dc0` r4 | 135.40@30 | 134.60@14, 135.39@30 | agreed → 0.909 |
| `934ed1e9` r4 | 135.50@30 | 134.70@14, 135.49@30 | agreed → 0.905 |

Before that code (`1e887324`, `d5066cc6`, `36af37af`) we kept stepping 126.9 → 127.4 → 128.0 and Brandlhuber walked itself down 137.8 → 136.5 → 135.5 → 134.8/133.3 and *finalled* there: 0.926, 0.969, 0.926. The arena's own relationship charge at the 133.30 deal was only €10,848 (breakdown of `d5066cc6`); at 136.49 it was €2,379 — i.e. the price term dominates down to ≈133 (C_best 1,096,816 ≈ a 133 deal).

**Mechanism (inferred, consistent with every row).** `offer()`: `if self.c(case, a, t) > c_theirs: a = self.same_cost(...)`. `self.c` includes the relationship charge priced from the Scout's full-cost estimate; at an ask of 128 with a full cost near the should-cost (132.6), `soft(g)` adds ≈€55k, so our *ask* looks dearer than the supplier's 135–137 offer, and `same_cost` (which itself uses `total_cost`) pins `a` at theirs − 0.01. `lever_trades` then prices the 14-day sheet at equal cost to that pinned `a`, the supplier answers `agreed`, and `agreed` freezes the price. The comparison treats our ask as if it were the deal; the deal lands 5–8 € below the ask every time.

**Change.**
```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
-        if t.standing_terms.get("unit_price") is not None:
-            c_theirs = self.c(case, t.standing_terms, t)
-            if self.c(case, a, t) > c_theirs:  # never ask for more than they already give us
+        if t.standing_terms.get("unit_price") is not None:
+            # compare asks on the same basis as same_cost(): an ask is not a deal, and the
+            # relationship charge of an ask we will never close at must not pin us to their price
+            c_theirs = self.c_track(case, t.standing_terms, t)
+            if self.c_track(case, a, t) > c_theirs:  # never ask for more than they already give us
                 a = self.same_cost(case, a, t.standing_terms, t.standard)
```
`c_track` already drops the charge for archetypes in `NEGOTIATES_DOWN` and keeps it where `floor_binds` (groups), and `next_price` still clamps the ask to `relationship_floor` for those — so P02/P03/P10 behaviour is untouched (they agreed/finalled in round 1 anyway).

**Affects / expected.** Stabilise and secure_supply cases with a cost estimate and a supplier that steps (P01: from a 0.80–0.91 band to 0.93–0.97, +0.05 on average over the 16 affected sessions). Hidden stabilise price increases are the likely place this bites. **Risk:** low — the supplier finals by itself (reply 5 in all three pre-relationship sessions) and we accept the final.

---

## 3. An identical or sub-cent repeat of our sheet is read as "no move": it triggers the supplier's final at its current price, or a walk

**Evidence (data).**
- P08 `769d64fc` (`v6-opencap`): r4 and r5 identical sheets 5.05/5.02/5.01 while Donautal stood at 5.05@45 db0 → `walked_away` at r5 without a prior final, score 0 (its standing sheet would have scored 0.826). `7976d643`, `55d090be`, `0a4d2074`: one identical repeat → final at the then-current 5.04/5.05 (0.826–0.837). `2f6a0b78` with steps of 0.01–0.03: Donautal moved 0.05 per reply for two more replies and finalled at 5.02 (0.860, our best P08).
- P11 `52716f49`: 45.42 sent three times → "You just sent the exact same numbers again" → final 46.50 (0.543; the same code otherwise lands 45.50–46.00, 0.626–0.710).
- P05 `cac09d93`: 130.81 → 130.82: "a one-cent adjustment does not constitute the realistic step" → two holds, final 135.50 (0.864 vs 0.909 for the identical code in `478e95da`).
- P01 `c006eed3`: +0.28 (0.2 %) → "without movement from your side we cannot move either"; `551cb8be`: +0.04 → two holds → 0.842.

**Mechanism.** `concession()` returns step 0 and sets `holding` while the supplier holds; `offer()` then rotates the package but keeps the price, so `no_step_back` resends the same figures. The bots read the e-mail, not our intent; four different personas answered the same way. The hoped-for gain of holding (the supplier moving while we don't) did not appear in any session; the suppliers that kept conceding did so against *tiny* moves.

**Change.** Always move the lead sheet by a visible minimum (0.2 % of their price, at least 0.01):
```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
         sheets = [self.no_step_back(t, s) for s in sheets]
+        theirs = t.standing_terms.get("unit_price")
+        last_p = (t.last_sheet or {}).get("unit_price")
+        if theirs and last_p is not None and sheets[0].get("unit_price") is not None:
+            # a repeated or sub-cent sheet reads as "no move" and triggers a final or a walk
+            # (P08 769d64fc walked, P11 52716f49 +1.0, P05 cac09d93 +3.5): always step visibly
+            floor_step = round(min(theirs, last_p + max(0.002 * theirs, 0.01)), 2)
+            if sheets[0] == t.last_sheet or sheets[0]["unit_price"] < floor_step:
+                sheets[0] = {**sheets[0], "unit_price": floor_step}
+                t.holding = False
         t.last_sheet = sheets[0]
```
This also neutralises the `decision.term_sheets[0] == prev → close` path in `decide()`, which is what accepted 138.60 in round 2 of `df366f6a` (0.762).

**Affects / expected.** Distributors and job shops that final/walk on a hold: P08 (+0.08 expected: removes the 1-in-10 walk and buys the extra reply), P11 (+0.02), P05/P01 (+0.01). The night log's "min step 0.75 % hurt" was confounded with the empty-claim-bank bug (P01 0.616 that run); 0.2 % per round adds at most ≈1 € over six rounds. **Risk:** low.

---

## 4. RFQ: an `agreed` sheet stands — we accept it the moment it appears instead of using it as a cited floor against a bidder that is still moving

**Evidence (data).** P05 `9bd523d1`: Dralveck `agreed` 28.00@14 at its reply 2; we accepted at once. In the same session Fuchsreiter was still `open` at its reply 3 at 28.50@14 ("let's get it signed"), having moved 38.50 → 30.50 → 29.00 → 28.50, each step after a rival/quality citation ("checked the rival quote; it holds; took it into account"). C_best 223,424 decodes to ≈26.6 — some bidder in this case accepts far below 28.00, and Dralveck's own "absolute limit" is 28.00/28.05 in 10 sessions; by elimination it is Fuchsreiter (news: looks for new customers; "free capacity"). Learnings: after `agreed`, pushes got "our agreed offer stands" (16 of 19). api.md: a message without a term sheet "is answered, and the quote stands".

**What I infer.** Fuchsreiter at 28.50 open, with Dralveck's 28.00 citable as `offer:70210-…`, had a fair chance of one more 0.5 step (27.9 → 0.823, 27.5 → 0.872, 27.0 → 0.92). In other sessions it finalled at 29.5–30.5 after 3–4 replies, so this is a bet, not a certainty.

**Change.** Hold an agreed bidder with a no-sheet message while another bidder is open and still stepping; `rival_claims` already cites the agreed price to the others.
```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ class ThreadState:
     clause_countered: bool = False
+    keepalives: int = 0  # no-sheet messages sent to an agreed bidder while a rival still moves
@@ def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
         if t.status == "agreed":
+            if acceptable and t.keepalives < 2 and t.rounds_left > 3 and self.rival_still_moving(t):
+                t.keepalives += 1  # its agreed sheet stands (api.md); keep the clock alive, no new terms
+                return Decision("send", sid, term_sheets=[],
+                                intent="brief hold: we are finalising internally and will confirm shortly")
             if acceptable:
                 return self.accept(t)
@@ def accept(self, t):
+    @staticmethod
+    def rival_still_moving(t, drop=0.01):
+        """Another bidder is open and its last reply cut its standing price by >= `drop`."""
+        for sid, msgs in (t.case_threads or {}).items():
+            if sid == t.supplier_id:
+                continue
+            prices, status = [], None
+            for m in msgs or []:
+                if m.get("from") == "buyer" or not m.get("term_sheets"):
+                    continue
+                status = m.get("status")
+                prices.append((m["term_sheets"][0].get("terms") or {}).get("unit_price"))
+            if status == "open" and len(prices) >= 2 and None not in prices[-2:] \
+                    and prices[-2] - prices[-1] >= drop * prices[-1]:
+                return True
+        return False
```
The runner must then message the moving rival first (its 60-s clock) and come back to the agreed one; `closing()` already picks the cheapest live sheet at the cap.

**Affects / expected.** RFQ cases only: +0.03–0.1 on P05-like cases if the open bidder takes one more step; 0 if it finals. **Risk:** the agreed bidder's thread must receive a message within 60 s (else timeouts, three end the thread); a keepalive costs a round; untested whether an LLM-driven bot keeps `agreed` after a non-accepting message (learnings say yes). Flag: test once in pre-flight on P05 before enabling.

---

## 5. Menu at the close: never put the supplier's own sheet beside a variant we prefer — it picks what suits it

**Evidence (data).** P18 `c43e456e` (`night-v6`, current code): Werdenfels final [5.20@90 db0, 5.10@45 db0]; `close()` mirrored and sent [5.10@45 **db5**, 5.21@45 db5 (equal C to its sheet), 5.10@45 db0 (its own)]. It "accepted Option C" — its own db0 sheet: 0.6207 versus 0.6957 for 5.10 db5, the score every other session reached when we sent only the db5 sheet (`13e6c049`, `c80f8b2a`, `783dd48d`, `c50dad81`). The deadband is worth 5,439 € to us at the same price (`index_clause` 6,527 vs 1,088 in the breakdowns); the equal-cost 5.21 db5 gives it +0.11 for nothing it loses.

**Mechanism.** `clause_variants` + `close()` append `own` "so its package stays on the table". The supplier's choice among our sheets is free, and it chooses by its own value: db0 > db5 for a seller. Our menu must contain only sheets we are willing to close on.

**Change.**
```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def close(self, case, t, acceptable, c_theirs, rival_best_c):
-                return Decision("send", t.supplier_id, term_sheets=[*variants, sheet][:3], intent=intent)
+                # its own sheet only when we have no equal-cost variant to offer in exchange
+                sheets = variants if len(variants) >= 2 else [*variants, sheet]
+                return Decision("send", t.supplier_id, term_sheets=sheets[:3], intent=intent)
```
and the same for the second branch (`[*variants, own]`).

**Affects / expected.** Raw-material cases with a 0 %-deadband final: +0.075 on P18-type finals where only db0 sheets are on the table (≈1 in 5 P18 finals; most finals already carry a db5 alternative). **Risk:** a non-own sheet after a `final_offer` could be met with a walk (0). Price pushes after a final walked 4/4; a structural swap that pays the supplier more has not been tested. If pre-flight shows a walk, revert this one only.

---

## Checked and left alone (no evidence of gain)

- **Cost-breakdown question:** 12 of 12 refusals, no price effect either way (P04/P08/P18 identical with and without it).
- **"What would you need to confirm Option A?":** answered with "faster payment / volume" and proof requests; prices unchanged (P05, P10, P18).
- **Attachments:** never sent; no supplier asked for data we could attach except Kalwisz's "proof of payment history" — not in the package.
- **Claims:** what visibly moved first counters were `news:` on Fuchsreiter (32.0 → 31.5 → 30.5), `cost:` on Ravensteiner (final 31.9 → 31.7), falling-index pairs on Werdenfels (5.70 → 5.40–5.50) and `fc:` on Brandlhuber (137.8/134.9 → 136.9/134.2, n=1, then lost to finding 2). `otd:` was "does not change our calculation" at P02, P03, P04, P07, P08, P18 (6/6 groups and distributors) — its weight 0.15 already keeps it out of the first message. Extending `forecast_claims` beyond `VOLUME_CASES` is a one-line change, but P10 `930e2eba` shows the downside (the forecast read as a volume ask, single-sheet final 33.0@42, 0.617 vs 0.663): n=1 each way, so not ranked.
- **P07, P08, P18 first-counter spread** (5.53–5.60, 5.20–5.35, 5.40–5.70 with identical sheets) is supplier-side noise; the final is a fixed number of 0.03/0.05/0.10 steps below it. Nothing in our code sets it beyond the claims above.