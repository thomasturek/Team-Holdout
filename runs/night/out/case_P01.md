# P01 (Brandlhuber, family foundry, `price_increase` / `stabilise`): analysis and three general fixes

## 0. Bottom line

- **The supplier mirrors our step.** After round 1, Brandlhuber matches our absolute step about 1:1, up to a cap that shrinks each round. It holds on steps of about 0.2 % or less. It hardens on any step backwards. It calls its final in round 4 or 5 whatever we do.
- **The early agent was better on this case.** It anchored deep (126.89) and stepped €0.6–1.7 per round, scoring 0.91–0.97. The current agent scores 0.76–0.91, mean 0.858 over the last 7 sessions. It loses value in three ways:
  - tiny or zero steps that trigger holds;
  - sheets priced *below* a package we already sent, which the supplier reads as backward moves;
  - accepting open offers in rounds 1–3. One cause is a 1 % C gap rule that equals 20 % of the whole scoring range on this case.
- **Three general diffs follow (§4):** a minimum visible step, monotone per-package prices, and an accept gate measured against the negotiable span plus a "still moving" check. Expected effect on P01: back to roughly 0.92–0.95. The record (0.995) also needs a lucky first counter.

## 1. Derived economics (inference from the score breakdowns)

These figures come from solving the logged breakdowns. Every check below reproduces a logged score.

- **Effective-date split.** Price 137.9 vs 133.3 (April start, 30 days) gives price 1,085,549 vs 1,063,569.
  - That implies 4,778 units at the new price and 3,372 units (Nov–Mar, 151/365 × 8,150) at the current price.
  - **The current price is about €126.53.**
- **Effective date is value-neutral in cash.** A November price P equals an April price of (8,150·P − 426,662)/4,778.
  - The quote, 138.55 from November, ≡ **147.03 from April**.
  - Our best deal, 133.3 from April, ≡ 130.50 from November.
  - The record, 129.50 Nov at 14 days, ≡ 131.6 April at 14 days.
- **Score anchors.** Solving three logged scores (0.7603, 0.9691, 0.9263) gives **C_open ≈ 1,153,779** and **C_best ≈ 1,096,815**, a span of 56,964.
  - Check: 136.6/30 gives C 1,105,802, which reproduces 0.8422 ✓.
- **Relationship charge.** sqrt(R) is linear in price: R ≈ 300·(139.33 − P)² at April/30 and 300·(138.37 − P)² at April/14.
  - Fit residual is under 1 %. This fit also reproduces the record's implied R (13.8k).
  - The C minimum sits near 131.3 (April/30) and 130.3 (April/14, C ≈ 1,096,570 ≈ C_best).
  - **Brandlhuber never offered below 133.3**, so the relationship floor never binds on anything attainable. Any floor on our asks only weakens our anchor and steps.
- **Scale.** In the 133–137 April range, **1 € ≈ 0.03–0.05 score**.

## 2. Supplier response model (evidence, 13 of our threads + 1 winners' probe)

| Aspect | Evidence | Confidence |
|---|---|---|
| **Opening** | 138.55, effective 2026-11-01, standard 30 days ("return to our standard 30-day payment term"). | certain |
| **First counter vs anchor** | Hardly depends on anchor level. At 30-day equivalent: anchor 126.89 → 137.8 / 135.5 / 137.8; anchor 130.41 → 137.8; anchor 131.59 (sheets at 30/45/60 d) → 138.1/60 and 137.8/60 (≈136.1–136.4 at 30 d); anchor 132.33/45 → 138.6/45 (×4) and 136.8/45. | medium |
| **First counter vs claims** | No claims (75b0649b): **140.3**. Quality + notice claims: 135.5–137.8. Notice always got "we did not know that - a fair point". About **€2.5–3 from claims** (n=1 without claims). | medium |
| **Noise** | Identical round-1 message and sheets (1e887324, 36af37af, d5066cc6) drew 137.8, 137.8 and **135.5**. Finals 134.8 / 134.8 / 133.3. Spread ≈ €1.5 ≈ 0.04 score. | solid |
| **Effective date** | Accepts April in round 1 in every thread with an April sheet. Often adds a "valid from January" alternative ("to respect the notice period"). One protest (df366f6a: "cannot sustain our operations with a delay until April") still came at April. | solid |
| **Later rounds: mirror** | Supplier step ≈ our previous step (30-day sheet), see the table below. | strong (5 threads) |
| **Hold triggers** | Steps ≤ about €0.3 (0.2 %) or zero got holds: 081a155f r2 (+0.28) "polite response", no move; c006eed3 r2 (+0.28) "Without movement from your side we cannot move either"; 551cb8be r2/r3 (0 / +0.04) held twice; cac09d93 r4 (+0.01) "a one-cent adjustment does not constitute the realistic step forward". | strong |
| **Backward triggers** | 773a42a5 r3 (14-day sheet 132.22 → 130.81): "you have moved backwards on the very option we are discussing, we cannot make any further concessions". cac09d93 r3 (same pattern): "no upward movement… must maintain". c006eed3 r5 (April/14 131.91 → 130.67, plus Nov 128.96): "expect our partners to move forward, not backward", then final at its held price. | strong |
| **Final offer** | Round 4 in the deep-anchor 3-sheet runs (4/4). Round 5 in the 2-sheet, 14-day and higher-anchor runs. Also immediately after a backward move. Never `agreed` (we were always ≥ €3 below). **Never walked** (0/13). | solid |
| **Levers it values** | 14 days ≈ €0.9 below 30 days (773a42a5: "135.7/14 → 136.6/30, maintaining the exact value"; 478e95da: 135.9/30 → 134.6/14). 45 / 60 days cost it ≈ €0.85 / €1.7. For us 14 days costs ≈ €0.79 per new-price unit, so the trade is about neutral (+≈€500 C). | medium |
| **Claims after round 1** | Order prices (`po`): "it holds, but it does not change our calculation" in 6/6. Rising LCI-C (1e887324 r2): "Your figures confirm our case: that driver rose". Winners' probe r4 (PPI-D351 falling + notice): 134.8 → 133.6 on a €0.79 step, larger than the mirror. | n=1, weak |
| **What it says it wants** | "a realistic step forward", movement, faster payment ("supports our family business"), owner-to-owner tone, a phone call. Refuses any cost breakdown. Asked "Which volume can you commit to?" only in the November-start probe; volume is not negotiable in our sheets. | solid |

Mirror evidence (supplier step vs our previous step on the 30-day sheet):

| Session | Our steps (€) | Its steps (€) | Pattern |
|---|---|---|---|
| 1e887324 | 1.35, 1.02, 0.78 | 1.3, 1.0, 0.7 | mirror |
| a37615af | 1.17, 0.60, 0.46, 0.35 | 1.3, 0.6, 0.4, 0.3 | mirror |
| 2c6e9cc0 (14 d) | 0.81, 0.60, 0.44, 0.33 | 1.0, 0.6, 0.5, 0.4 | mirror |
| d5066cc6 | 1.07, 0.84, 0.63 | 0.8, 0.8, 0.6 | mirror |
| 75b0649b (no claims) | 1.67, 1.27, 1.05 | 1.5, 0.5, 0.4 | capped |

- The caps seen are at least ~1.0 %, 0.75 %, 0.5 %, 0.3 % of price by round. This fits the D01 rule in learnings.md. Caps were lower without claims.
- **Inference:** final ≈ first counter − Σ min(our step, cap_r) over 3–4 rounds. A bigger step costs us nothing, because we accept *its* final, not our ask.

## 3. Best deal in the logs, and how it came about

**In this digest: d5066cc6, 133.3 / 30 days / April, score 0.969.**

- **Round 1:** three equal-value sheets (126.89/60, 123.18/45, 125.46/30, April) plus quality and notice claims. It drew the low-noise first counter, **135.5** at 30 days.
- **Round 2:** step €1.07 plus index and order-price claims → 134.7.
- **Rounds 3–4:** steps 0.84 and 0.63, mirrored 0.8 and 0.6 → final 133.3 in round 4, accepted.
- **Repeatability:** the same message twice more gave 134.8. The 0.969 is the lucky draw of a 0.93-level policy.

**Record (learnings.md, not in this digest): 129.50 / 14 days / November, 0.995** (`1c9b55304adcb64f`), ≡ 131.6 April/14.

- Procurecabana's version bounded its full-cost estimate by the supplier's counters (`bound_full_cost`) and so "stepped on" past its old target. It ran 5–6 counters.
- Their 130.18 Nov/14 (0.974) ≡ about 133.6/30 April, which is level with our best.
- The winners' probe in the digest (ef0c817c) ended at 133.6 Nov/14 ≡ 138.6 April: **about 0.64 by our C model, worse than ours**. It wasted round 1 on a sheetless questions-only e-mail ("Without movement… we cannot move either").

## 4. Where the current agent leaves value (ranked)

Baseline: our last 7 sessions average 0.858. Best of ours is 0.969, the record 0.995. The gap is about €2–3 in April terms.

**F1. Premature acceptance of open offers.** About €1–3.5 lost in 3 of 7 sessions.
- **df366f6a** accepted **138.6/45 in round 1** (0.762). Every comparable thread got €2–4 more.
- I recomputed `decide()`'s `close` test (inference, exact arithmetic):
  - `our_costs[-1]` is the **max** C over our sheets. That is the 134.57/90 sheet: c_track ≈ 1,099,452 (no relationship charge, since the family foundry is exempt from the floor).
  - ×1.01 gives 1,110,447, which is at or above the supplier's 1,109,593, so `close` fired and the offer was accepted.
  - **1 % of C ≈ 11,000 € ≈ 20 % of the whole C_open–C_best span**, about €2.3 per new-price unit.
- **478e95da** r3 accepted 134.6/14 by the same arithmetic (1,097,786 < 1,098,671).
- **081a155f** r3 accepted an open 135.6/30 with 7 rounds left. `close` does not fire there; it is `at_target` or the repeated-sheet rule (cannot tell from the digest; check the decision log).
- In every thread that went on, the supplier gave €0.3–1.0 per round more and never walked.

**F2. Backward steps on an already-sent package.** About €0.5–1.5 lost in 3 of 7 sessions.
- Affected: 773a42a5, cac09d93, c006eed3 (quotes in §2). Each produced a hold or a final at the held price.
- Mechanism (inference from `offer()`): the same lever combination is priced by different rules in different rounds.
  - A `lever_trades` sheet is priced at equal cost to us.
  - A menu sheet is priced at equal value to the supplier, using rate 0.2 once it "asks" for faster payment (`cash()`).
  - So the 14-day price can drop between rounds.
- The supplier compares by package (it names "Option B/C"). It does not compare by C.

**F3. Steps too small to register.** About €0.5–1 lost in 4 of 7 sessions.
- Current round-2 steps were 0.0–0.28; the early agent's were 1.0–1.7.
- With a 1:1 mirror this directly raises the final.
- A contributing factor (inference): the higher anchor (131.59 / 132.33 vs 126.89) shrinks `concede × gap`. The exact path that produced the 0.28 step (a hold misread in `concession()`, or the menu) is not visible in the digest.
- NIGHT_CONTEXT says the "relationship floor lifted it to 131.6". `floor_binds` exempts `family_foundry`. **Verify that 70110's profile archetype really is `family_foundry`**; the latest sessions still opened at 131.59.

**F4. Claim slots wasted.** Small, under €0.5, weak evidence.
- `po` (CLAIM_WEIGHT 0.3 ≥ WEAK_CLAIM 0.2) is spent in round 1 (5/5 latest, "does not change our calculation").
- Nothing is cited after round 1. The falling PPI-D351 (−3.7 %, verified in the api.md example) was never used.
- Not diffed: the bank lives in `buyer/facts/claims.py`, which I don't have.

**F5. Noise.** The first counter varies ±€1.2 on identical input. No policy fixes this. The record needs both good play and a good draw.

## 5. Changes

### Change A: minimum visible step when we are not deliberately holding (fixes F3)

General rule: a concession under ~0.2 % reads as "no movement" (P01 ×4; D01 "tiny moves trigger the final").

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@
     "accept_target_pct": (0.0, 10.0),
     "lever_trades": (0.0, 1.0),
+    "min_step_pct": (0.0, 2.0),
 }
@@
     "lever_trades": 1.0,  # > 0.5 = on
+    # smallest step we send when we mean to move (share of its price): suppliers that mirror our steps answer a
+    # step under ~0.2 % with "without movement from your side we cannot move either" and hold
+    "min_step_pct": 0.6,
 }
@@ def next_price(self, t, theirs, step=None, case=None):
         else:
             last = t.our_prices[-1]
             price = last + (step * (theirs - last) if step is not None else self.concession(case, t, theirs, last))
+            if not t.holding and theirs > last:
+                price = max(price, last + min(self.p["min_step_pct"] / 100 * theirs, 0.5 * (theirs - last)))
         return round(min(max(price, low), theirs), 2)
```

- **Expected on P01:** round-2 steps go from €0.28 to about €0.81, avoiding one hold round. Roughly +€0.5–1, +0.02–0.04.
- **Risk elsewhere:**
  - Price-frozen suppliers (P03, P04) do not move, so there is no effect on the deal; we only state higher asks.
  - Stingy mirrors (Nordmark, ratio 0.15) bear a small risk of an `agreed` at our higher ask. That ask would still be above its floor, which caps the loss.
  - Deliberate holds (`t.holding`, reciprocity mode) are untouched.

### Change B: never price an already-sent package lower outside a rival race (fixes F2)

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ class ThreadState:
     clause_countered: bool = False  # we offered its package with a wider index deadband once before closing
+    sent_floor: dict = field(default_factory=dict)  # highest price we offered per package (its non-price terms)
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
         sheets = sheets[:3]
+        if rival_best_c == math.inf:  # a lower price on a package it has seen reads as a step backwards
+            raised = [self.not_below_sent(t, s) for s in sheets]
+            sheets = [s for s in raised if self.c(case, s, t) < c_cap - 0.5] or raised[:1]
         questions = []
@@
         t.last_sheet = sheets[0]
+        for s in sheets:
+            k = self.package_key(s)
+            t.sent_floor[k] = max(t.sent_floor.get(k, 0.0), s["unit_price"])
         t.our_prices.append(a["unit_price"])
@@
     @staticmethod
     def above_floor(case, t, terms):
@@
         return {**terms, "unit_price": floor} if floor and terms["unit_price"] < floor else terms
 
+    @staticmethod
+    def package_key(sheet):
+        return tuple(sorted((k, str(v)) for k, v in sheet.items() if k != "unit_price"))
+
+    def not_below_sent(self, t, sheet):
+        """Keep a package at least at the highest price we offered for it before: suppliers answered a lower
+        one with "you have moved backwards ... no further concessions" and held or called their final."""
+        prev = t.sent_floor.get(self.package_key(sheet))
+        return {**sheet, "unit_price": prev} if prev is not None and sheet["unit_price"] < prev else sheet
+
     def lever_trades(self, case, t, a, asks=()):
```

- **Expected on P01:** it would have kept 773a42a5's and cac09d93's 14-day sheet at ≥ 132.22 and c006eed3's April/14 sheet at ≥ 131.91. Those three sessions get +€0.5–1.5; the mean gains about +0.02–0.03.
- **Not covered:** a *new* package at a lower raw price (c006eed3's Nov 128.96, value-equivalent to April 130.67) is still allowed. The lead sheet's own backward move is the one caught.
- **Risk elsewhere:**
  - RFQs are exempt, so undercutting a rival still works.
  - A raised sheet costs us more than its equal-value twin, and the menu's within-0.3 % property can break. Bounded by the `c_cap` filter.
  - The `close()` mirror and clause-variant paths are not recorded. They send the supplier's own package, which is never below our earlier ask.

### Change C: accept an open offer early only when close in the negotiable range and the supplier has stopped moving (fixes F1)

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@
 OWN_PRICE_SLACK = 0.005
 CASH_HUNGRY_RATE = 0.15
+ACCEPT_SPAN_SHARE = 0.05  # "close" also means within 5 % of the way from its opening cost to our last ask
@@ def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
         gap = 1 + p["accept_gap_pct"] / 100
         close = t.our_costs and self.c_track(case, t.standing_terms, t) <= t.our_costs[-1] * gap
+        if close:  # 1 % of C can be a fifth of the whole negotiable range: measure against the span too
+            close = self.c_track(case, t.standing_terms, t) - t.our_costs[-1] <= \
+                ACCEPT_SPAN_SHARE * max(0.0, t.opening_cost - t.our_costs[-1])
+        moving = self.still_moving(t)
         if close and acceptable and c_theirs < t.opening_cost:
             return self.close(case, t, acceptable, c_theirs, rival_best_c)
-        if acceptable and self.at_target(case, t, c_theirs):
+        if acceptable and not moving and self.at_target(case, t, c_theirs):
             return self.close(case, t, acceptable, c_theirs, rival_best_c)
         prev = t.last_sheet
         decision = self.offer(case, t, self.next_price(t, theirs, case=case), rival_best_c=rival_best_c)
-        if prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding:
+        if prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding and not moving:
             return self.close(case, t, acceptable, c_theirs, rival_best_c)
         return decision
 
+    @staticmethod
+    def still_moving(t):
+        """Its last reply came down by more than 0.1 % of C and rounds remain: it is still conceding."""
+        c = t.their_costs
+        return len(c) >= 2 and c[-2] - c[-1] > 0.001 * c[-1] and t.rounds_left > 2
+
     def closing(self, case, threads: dict) -> Decision:
```

- **Recomputed on the logged sessions:**
  - df366f6a r1: gap 10,141 vs 5 % × 54,327 = 2,716, so the offer is not accepted.
  - 478e95da r3: gap ≈ 9,900, not accepted.
  - 081a155f r3: last move 137.8/60 → 135.6/30 is more than 0.1 % of C, so neither `at_target` nor repeat-close fires.
  - Final offers, `agreed` and round-limit paths are unchanged.
- **Expected on P01:** the 0.76 and r3-accept sessions recover €0.5–3.5, about +0.02–0.04 on the mean.
- **Risk elsewhere:**
  - More rounds means more walk-away risk with ladder suppliers. Nordmark walked at a 19 % cumulative gap, though bigger steps (A) shrink that gap.
  - More rounds also means more wall time in an 8-minute wave. At ~20 s per reply, +2 rounds ≈ 40 s.
  - The 0.1 % threshold lets a supplier that "moves" in sub-0.1 % steps be accepted. That is acceptable.

**Combined expectation for P01:** about 0.86 → 0.92–0.95, the level of the old deep-anchor runs. These changes interact, so confirm with one paired batch. The spread of identical runs is ±0.04 on this case, so one run proves nothing; judge by thread mechanics (holds, backward complaints, accept round) rather than by the score alone.

## 6. Not proposed, and checks before the final

- **Anchor in value terms.** We compare April asks with a November quote (`next_price` uses the raw `theirs`). The first counter barely reacts to the anchor, so this is not worth a change. But the anchor sets `concede × gap`, and Change A neutralises that.
- **Claims (F4).** In `buyer/facts/claims.py`, never offer a rising index. Keep one falling-driver claim (PPI-D351) for round 2 or 3. Drop `po` below WEAK_CLAIM. Evidence n=1; low priority.
- **Writer.** Nothing to change for this supplier. It responds to "family companies / owner to owner". It offers phone calls repeatedly; the template should decline politely and point to the options.
- **Verify:**
  1. 70110's profile archetype, which decides whether `floor_binds`.
  2. Which rule accepted 081a155f r3.
  3. Whether `params.json` turns on `reciprocity` / `accept_target_pct`, which change the paths above.