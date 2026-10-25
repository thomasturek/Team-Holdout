# P07 (Leitner, 70610): supplier behaviour, where we lose value, and three policy changes

## 0. Decoding the yardstick

**Evidence: our 14 sessions, cost function in `cost.py`.** Every deal has 60,000 units (30,000 a year × 2 years), an 8 % interest rate, a 60-day reference payment term and a quality cost of €29. That means:

- €0.01 per unit is €600 of C, about **0.0065 score**.
- From bdeae9d4 (C = 326,313, score 0.7051) and 71ce4d10 (C = 331,129, score 0.6526): **C_open − C_best ≈ €91,785**, so **C_open ≈ €391,027** and **C_best ≈ €299,242**.
- C_best corresponds to about 5.02 at 90 days. This matches the "P07 5.03" in learnings.md.

**Inference from these figures:**

- The record of 0.779 is C ≈ 319,500. That is **≈5.31 at 45 days, 5.32 at 60 days or 5.36 at 90 days**.
- procurecabana's 5.35 / 45 d / 36 m is C = 322,099, score 0.751. That is their own row, not the record.
- The walk in bf98975f scored 0.121, which is the alternative (C_alt ≈ €379.9k).

Comparable cost in this case: payment shifts price by 8 %/360 per day against the 60-day reference. So 5.48 at 90 days is "5.443 at 60 days".

## 1. Findings, ranked by € at stake

### F1. Leitner answers our step size, and its final comes at a fixed round. Our small steps are the binding constraint (≈ 0.04–0.08 score)

**Evidence.** Price moves in runs where payment terms stayed constant (ours on the 30-day sheet, theirs at 30 days):

| Session | Our steps r1→r2→r3→r4 | Their steps | Ratio (theirs/ours) | Final |
|---|---|---|---|---|
| 151d1659 | +0.05, +0.04, +0.03 | −0.04, −0.04, −0.03 | 0.8, 1.0, 1.0 | 5.42 @ 30 d (r4) |
| ab0314a3 (36 m) | +0.05, +0.04, +0.03 | −0.04, −0.03, −0.02 | 0.8, 0.75, 0.67 | 5.44 @ 30 d (r4) |
| 75710688 | +0.04, +0.04, +0.02 | −0.02, −0.02, ≈−0.02 eff | 0.5, 0.5, ~0.9 | 5.51 @ 60 d (r4) |
| 37b8c235 (comparable C) | +0.065, +0.05, +0.04 | −0.037, −0.02, −0.03 | 0.57, 0.4, 0.75 | 5.55 @ 90 d (r4) |

- Our step is consistently **≈14 % of the gap**. In 151d, r2 is 0.05 of a 0.38 gap, r3 is 0.04 of 0.29, r4 is 0.03 of 0.21. The default `concede` is 0.35 (policy.py `DEFAULTS`, ~L38), so params.json (not shown) must hold about 0.14.
- **Final round:** final_offer came in **r4 in 12 of 14** of our threads and r3 in 2 (a26d2404, 4a101a1b).
- **Total concession after the first counter** (comparable C): 0.04–0.11, typically ≈0.09.

**Evidence from learnings.md (procurecabana).** "Leitner: 3.5 %, 2.2 %, 1.1 %, final in round 3 (5 of 5)" and a median ratio of 0.36. Compounding from the 5.74 quote:

> 5.74 × 0.965 = 5.54 → × 0.978 = 5.42 → × 0.989 = **5.36**

This is exactly their 5.35 deal.

**Inference: a coherent model.**

- Below a per-round cap, Leitner concedes about **0.5–1.0 × our last move**. This is the D01 pattern `min(0.8 × our move, cap)`.
- The caps are roughly 2.2 % in r2 and 1.1 % in r3. procurecabana's low 0.36 ratio is what you see when *their* big steps hit the caps.
- It issues its final after about 3–4 rounds regardless of how much gap remains.
- If the gap closes before the final, the meeting point is about **C0 − 0.44·(C0 − A0)** = 5.53 − 0.44 × (5.53 − 5.15) ≈ **5.36**.
- With our 14 %-of-gap steps, the final arrives with 0.15–0.25 of gap still open. We then pocket only 0.8 × Σ(our steps) ≈ 0.10.
- **Size of the loss:** about 0.06–0.10 per unit, €3.6–6k, **0.04–0.065 score per run**.

**Skepticism.**

- The ratio evidence comes from 3–4 runs with clean payment terms. Effective-price ratios are noisy (one r3 ratio was 0.4).
- The cap values come from a single source (procurecabana's 5 runs).
- Counter-evidence from other suppliers: Donautal gave *more* to a 12 % slow walk (learnings: 5.31 against 5.33–5.39), and a 55 % move drew a hold. So this must not become a universal rule.

### F2. The first counter is noisy, and that noise carries straight to the final (≈0.03–0.05 score of run-to-run spread)

**Evidence.**

- Identical round-1 inputs (sheets 5.18 @ 90 / 5.13 @ 45 / 5.15 @ 60, claims po + po ± fc) drew first counters of **5.55, 5.56, 5.56, 5.56, 5.60, 5.60, 5.60, 5.60, 5.60 (all @ 60 d)**.
- The finals follow:
  - first counter 5.55–5.56 → 5.42 / 5.44 / 5.45 / 5.46
  - first counter 5.60 → 5.48 / 5.49 / 5.50 / 5.50
- All three latest sessions (71ce4d10, 5b71599f, 37b8c235) drew 5.60.
- Anchor depth 5.12–5.23 (30-day sheet) made no difference: 5.53 @ 30 every time in a26, 4a10, 7571, 151d and ab03.
- Claims made no difference either:
  - fc runs: 5.56 / 5.60 / 5.60 / 5.60
  - non-fc runs: 5.55 / 5.56 / 5.56 / 5.60 / 5.60

**Inference.**

- The ±0.025 spread looks like supplier-side randomness. Anchor and claims do not visibly drive it.
- So **the latest sessions are not worse code. They are mostly worse draws**, plus F1.
- Nothing in the logs reliably lowers the first counter.

### F3. Which levers it values, and what it asks for

**Contract length**

- Our runs: 24 m in round 1 gives a first counter of 5.53 @ 30.
- Winners' probe 28f74251: 12 m gives 5.63 @ 30, then 24 m at that same 5.63 is `agreed` at once.
- **Inference (confounded by different anchors):** 12→24 m is worth about 0.10 on the first counter. It is mandatory for us anyway, since 12 m leaves half the need uncovered at fallback ≈ 6.91.
- 36 m (ab0314a3, one run): first counter 5.53, final 5.44, inside the 24 m band. **No visible effect.** NIGHT_CONTEXT's open question "does 36 m move them?" has so far a "not measurably" answer (n = 1).

**Payment days**

- 0.06 for 90→45 days (bdeae9d4: 5.48 @ 90 vs 5.42 @ 45).
- 0.04 for 60→30 days (4a101a1b: 5.53 @ 60 vs 5.49 @ 30; 442ead10 the same).
- That is ≈8.7 %/yr against our 8 %. **Payment is close to C-neutral.** Our three-sheet payment menu buys almost nothing and only decides which sheet it "builds on".

**Volume**

- It asks "Which volume can you commit to?" / "A binding higher volume would help us and can improve the price" in 7 of 14 threads. It also asks for "exact volume figures for this additional business" after our forecast claim (f1bbfe23 r4, 5b71599f r4).
- **Inference:** committing above the 30,000 need buys surplus units. +10 % is 6,000 units ≈ €32k, while the price gain is at most a few €k. Do not trade volume here. Stating 30,000 as binding is right.

**Claims: none moved the price.**

| Claim | Supplier's answer |
|---|---|
| Rising index (a26, 4a10, 7571, 151d) | "Your figures confirm our case: that driver rose" |
| `po` | "does not concern this part or our company" (a26 r1/r3), otherwise "does not change our calculation" |
| Delivery record | "does not change our calculation" |
| `fc` | "taken into account", but the first counter was the same |

- a26d2404 r3: the supplier read our order prices as "competitor pricing ... we cannot verify", then issued the final that same round.

**What it says it wants:** planning security (24 m), "fair compromise", movement from us ("In response to your movement..."), and volume.

### F4. Triggers

- **`agreed` = our sheet equals its own standing offer or its own alternative.**
  - All 12 post-final mirrors were agreed.
  - Winners' r2: 5.63 @ 24 m, its own price.
  - Never agreed below its last counter.
- **`agreed` freezes the price.** Winners' r3–r6: a 90-day change, a 5.48 sheet, three claims and a 5.55 push all got "Our agreed offer stands".
- **`final_offer`:** r4 (12/14), r3 (2/14 ours, 5/5 procurecabana).
  - Possibly earlier when it is irritated: both of our r3 finals followed the "competitor pricing" quarrel.
  - Possibly earlier when its concession budget is spent: procurecabana's big steps.
  - Both are inference.

### F5. The post-final "mirror" earns ~€300 and risks the whole case (≈0.04 expected score)

**Evidence.** After every final we sent its cheaper alternative back (`close()`, policy.py ~L520). Gains:

| Session | Final | Mirror | Gain |
|---|---|---|---|
| 4a101a1b | 5.53 @ 60 | 5.49 @ 30 | €204 |
| 75710688 | 5.51 @ 60 | 5.47 @ 30 | €212 |
| 442ead10 | 5.49 @ 60 | 5.45 @ 30 | €220 |
| c7d4 | 5.54 @ 90 | 5.48 @ 45 | €288 |
| bdeae9d4 | 5.48 @ 90 | 5.42 @ 45 | €324 |

- That is 0.002–0.0035 score each.
- In bf98975f the r5 message after the final **timed out**. The supplier withdrew ("we assume you have decided to pursue other options") and the case scored **0.121 instead of ≈0.66**.
- 1 bad outcome in 13 post-final sends.

**Inference.** The cause of the timeout (writer latency or network) is not visible here. But any round trip after a final carries tail risk. At even a 1-in-50 walk rate, a €300 gain has negative expected value.

### F6. We kept asking an owner to escalate

**Evidence.**

- "As previously stated, we are fully authorized ... without the need for escalation" (bf98975f r4).
- "I have reviewed your request for escalation" (71ce4d10 r2).
- "As the authorized representative ... fully empowered" (37b8c235 r1/r3/r4).

The source is writer rule 5 ("ask our contact to take Option A to that person"), re-issued every round.

**Skepticism.**

- The 4 threads with "authorized representative" replies all drew 5.60 first counters.
- But bdeae9d4, our best run, answered the same request with "discussed with our management as requested ... authorized to make a further concession".
- **No price effect is demonstrable.** This is a hygiene fix: stop repeating a request the supplier rejected.

## 2. The best deals in the logs and what led to them

**bdeae9d4: 5.42 @ 45 d, 24 m, score 0.7051 (our best).**

- First counter 5.55 @ 60, the lowest draw in the 90-day configuration (F2).
- Steps in comparable price: −0.047, −0.03, −0.03.
- Final 5.48 @ 90 with a 45-day alternative; we mirrored it and got 5.42 @ 45.
- Only one feature differed from its siblings, the first counter. **It was a good draw, not a better tactic.**
- 151d1659 (5.42 @ 30, 0.693) is the cleanest tactical run: four full reciprocal concessions (0.04, 0.04, 0.03) with no payment noise.

**Record 0.779 (≈5.31 @ 45 / 5.36 @ 90)** and **procurecabana 5.35 / 45 / 36 (0.751).**

- The digest has no sessions from those teams except a probe that agreed at 5.63.
- Their learnings give 3.5 / 2.2 / 1.1 % concessions with a final in r3. That fits F1's model: big steps from them, caps reached, final at r3 at ≈5.36.
- How the record went about 0.04 lower is unknown. Plausibly a lucky first counter (F2) on top of the same pacing.

## 3. Where the current agent leaves value

Latest runs 71ce4d10, 5b71599f, 37b8c235: 5.50 / 5.50 / 5.49 @ 45, scores 0.653 / 0.653 / 0.659, C ≈ 331.1k.

| Comparison | € | Score | Cause (evidence → inference) |
|---|---|---|---|
| vs our best (bdeae9d4) | ≈4.8k | 0.05 | First counter 5.60 vs 5.55 (≈€3k, noise, F2). Our three small steps bought only 0.087 of comparable concession. |
| vs procurecabana 5.35 | ≈9k | 0.10 | F1: our steps sum to ≈0.12, theirs ≈0.25; the final arrives with the gap open. |
| vs record 0.779 | ≈11.6k | 0.126 | F1 + F2, plus ≈€2.6k unexplained. |
| Tail risk | — | ≈0.04 expected | F5: one post-final timeout cost 0.54. |

Things that do *not* matter here, on the evidence:

- the 3-sheet payment menu (C-neutral)
- claims (no visible effect)
- 36 months (n = 1, no effect)
- the forecast claim (no effect, and it triggers volume questions we cannot satisfy)

Not addressed in code:

- A deeper anchor (current ask 5.15 @ 60 ≈ 10 % below quote) would only help if the gap is actually closed before the final. That requires F1 first.
- The munich team observed that >25 % below quote backfires.

## 4. Proposed changes

### Change 1 (highest value). Step to the gap when the supplier answers our steps in proportion

**Rule (general, observable).** In bilateral non-relationship cases, outside RFQs and raw-material cases:

- If the supplier's last step was at least **0.4 ×** our last step (both measured in € of C), our next step is at least **35 % of the gap**.
- When it stops reciprocating, we drop back to the trained `concede`.

The gate is self-limiting. When a supplier hits its per-round cap, its ratio falls (procurecabana's 0.36) and the boost switches off.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -76,6 +76,8 @@
 OWN_PRICE_SLACK = 0.005
 CASH_HUNGRY_RATE = 0.15
+STEP_MATCH_SHARE = 0.35  # our step (share of the gap) while the supplier answers our steps in proportion
+STEP_MATCH_MIN_RATIO = 0.4  # its last step / our last step, both in EUR of C
 
 
 @dataclass
@@ -253,6 +255,8 @@ class Policy:
         default = p["concede"] * gap
         if case is None or p["reciprocity"] <= 0 or len(t.their_costs) < 2:
             step = default
+            if case is not None and self.matches_steps(case, t):
+                step = max(step, STEP_MATCH_SHARE * gap)
         else:
             slope = self.c(case, {**t.standing_terms, "unit_price": theirs + 1}, t) - t.their_costs[-1]
             move = (t.their_costs[-2] - t.their_costs[-1]) / slope if slope > 0 else 0.0  # their step, in price
@@ -271,6 +275,21 @@ class Policy:
                 step, t.holding = max(step, p["endgame_frac"] * gap), False
         return step
 
+    @staticmethod
+    def matches_steps(case, t):
+        """It answered our last step with at least STEP_MATCH_MIN_RATIO of it (EUR of C). Such a supplier
+        concedes in proportion to our move up to a per-round cap and issues its final on its own schedule,
+        so token steps leave the gap open at its final. Not in relationship goals (the floor rules),
+        RFQs (rivals pace it) or raw-material cases (distributors gave more to a slow walk)."""
+        if relationship_case(case) or t.case_type in DEEP_OPEN_TYPES:
+            return False
+        if len(t.our_costs) < 2 or len(t.their_costs) < 3:
+            return False
+        ours = t.our_costs[-1] - t.our_costs[-2]
+        theirs = t.their_costs[-2] - t.their_costs[-1]
+        return ours > 0 and theirs >= STEP_MATCH_MIN_RATIO * ours
+
     def at_target(self, case, t, c_theirs):
```

**Index alignment.**

- `their_costs` = [quote, r1, r2, ...], with the quote excluded by `len ≥ 3`.
- `our_costs` = [m1, m2, ...].
- At the decision for m3, the comparison is r1−r2 against m2−m1.
- If the supplier repeats a standing ID, `their_costs` is not appended and the comparison goes stale for a round. That is acceptable: it can only switch the boost off.

**Expected effect on P07** (inference from the F1 model; 151d-style path):

| Round | Ours | Theirs |
|---|---|---|
| r2 | 5.20 (unchanged) | 5.49 |
| r3 | 5.20 + 0.35 × 0.29 ≈ 5.30 | ≈5.41–5.43 (capped near 1.1 %) |
| r4 | ≈5.34–5.36 (boost if ratio holds) | final ≈5.38–5.41 |

- That is ≈0.03–0.10 below today's finals, so **+0.02 to +0.06 score**, still inside the F2 noise.
- It needs at least 6 paired runs to see.
- Round 2 stays unboosted because the r1 counter is confounded by the 12→24 m change. A round-2 prior (for example, a first counter ≥2 % below the quote on unchanged terms) is a sensible next test, not part of this diff.

**Risk.**

- Excluded by the gate: P01/P02/P03/P10 (relationship goals), P05 (RFQ), P08/P18 (raw_material).
- P04 and other price-frozen suppliers: ratio 0, so never triggered.
- **P11 (Kalwisz, quality_first)** is the exposed case. Its 0.50 steps could pass the gate. Its ratio is reported as 0.0 overall, so the gate likely stays off, but watch it.
- Hidden cases: bilateral routine/leverage/quality cases with a reciprocating supplier. If a supplier's final comes *later* when we walk slowly (Donautal-like but not tagged raw_material), we lose rounds. The ratio gate does not detect that.

### Change 2. Don't spend a round trip after a final for a trivial alternative

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -78,6 +78,7 @@
 STEP_MATCH_SHARE = 0.35  # our step (share of the gap) while the supplier answers our steps in proportion
 STEP_MATCH_MIN_RATIO = 0.4  # its last step / our last step, both in EUR of C
+MIRROR_MIN_GAIN = 0.005  # after a final offer, mirror its alternative only if it saves this share of C
 
 
 @dataclass
@@ -519,6 +520,8 @@ class Policy:
     def close(self, case, t, acceptable, c_theirs, rival_best_c):
         alt = t.alt
+        if alt and acceptable and t.status == "final_offer" and c_theirs - alt[0] < MIRROR_MIN_GAIN * c_theirs:
+            alt = None  # its last word: one more send risks a late move and a walk-away, for a few hundred EUR
         if alt and alt[0] < c_theirs and t.rounds_left > 1 and not t.mirrored:
             if alt[0] < alternative_cost(case) and alt[0] <= rival_best_c:
                 t.mirrored = True
```

**Expected effect on P07.** About −€200–320 per run (−0.003). In exchange it removes the post-final send that walked bf98975f. If that tail is even 2 %, expected value is +0.01; on the observed 1/13, about +0.04.

**Risk.**

- Large alternatives are still mirrored. P10's longer-lead-time alternative saved several % of C (EVALUATION.md: 0.57 → 0.66), far above 0.5 %.
- The skip only applies when the standing sheet is acceptable, so it never turns a mirror into a walk.
- Separately, but not shown here: the runner should send post-final moves via the template (no model call), since that path has no latitude.

### Change 3 (hygiene, low confidence). Stop asking someone who has said they decide to escalate

```diff
--- a/src/buyer/llm/prompts/writer_system.md
+++ b/src/buyer/llm/prompts/writer_system.md
@@ -20,7 +20,7 @@ HOW TO WIN THE REPLY
 2. Solutions, not counter-arguments. If it blames a cost (copper, alloy, steel, energy) and our options include an index clause (see CLAUSE IN OPTIONS), present the clause as the answer: we take that risk above the deadband, so the base price no longer needs a risk premium. If it wants cash, volume, a longer contract or its standard payment term, point to the option that gives it - only if an option really does.
 3. Option A is the package. Name Option A as the package we can approve, and give the reason in one sentence drawn from the claims and the options. The other options are genuine alternatives for its convenience.
 4. A clear way to yes. Only if CONFIRM AT ONCE is yes: say that if it confirms Option A as it stands, we can confirm the order straight away (true there: our negotiator accepts at once). If it is no, never promise to confirm, accept or award at once.
-5. The person who decides. Follow the DOSSIER: if our contact needs approval or has little authority, add one short paragraph its decision-maker can approve as it stands - what Option A gives the supplier, in plain words - and ask our contact to take Option A to that person.
+5. The person who decides. Follow the DOSSIER: if our contact needs approval or has little authority, add one short paragraph its decision-maker can approve as it stands - what Option A gives the supplier, in plain words - and ask our contact to take Option A to that person. Never do this if the supplier has written in this thread that it is authorised, empowered or able to decide itself, or if an owner writes: then address the writer as the decision-maker and do not mention escalation, management or approval again.
 6. The STRATEGY line sets how hard to press (aggressive, cooperative, patient, escalate, secure) - follow its tone. The right voice for this supplier (ANGLE in the DOSSIER, STYLE): owner to owner for a family firm, an approver-ready memo for a group, cash first for a cash-short shop, security and planning for a supplier we depend on.
```

**Expected effect on P07.** No measurable price effect is claimed (see F6). It removes repeated irritation ("As previously stated...") and keeps the writer's few words on the package.

**Risk.** Minimal. Group or approval-ladder suppliers that do not claim authority still get the approver paragraph.

## Not changed, but worth noting

- **Order-price claims** (`CLAIM_WEIGHT["po"] = 0.3`, ~L75) never moved Leitner or the 23 citations in the munich logs. In P07 they once drew "competitor pricing ... we cannot verify" right before an r3 final. Dropping `po` below `WEAK_CLAIM` is a cheap follow-up. The evidence for harm is n = 1.
- **Validation plan for Change 1.** Paired runs on P07 and P11, plus P04 as a no-trigger control, with ≥3 each. Judge on the final minus the first counter (comparable C), not the raw score, because F2's ±0.025 noise dominates single runs.