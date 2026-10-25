# P11 (Kalwisz 70140, quality / quality_first): analysis and proposed changes

## 0. Decoding the score

Every figure below comes from the cost breakdowns in the digest. These are exact relations, not estimates.

| Quantity | Value | Derivation |
|---|---|---|
| Committed units | 15,900 | price 731,400 / 46.0 |
| Freight | €1.54/unit (24,486) | constant in every deal |
| Cost per defect | €450 | 300 ppm, cb 0 → quality 2,146 = 4.77 defects × 450; cb 150 → 1,431 ✓; 1500 ppm, cb 150 → 7,155 ✓ |
| C_open | 817,578 | 47.00 × 15,900 + 24,486 + 6400 ppm × 450 (45,792) |
| C_open − C_best | 95,078 | 45.5 vs 46.0 sessions: 7,950 / 0.08362; also 715.5 / 0.00753 from the cb-150 pair |
| C_best | ≈ 722,500 | ≈ **43.77 at 300 ppm / cb 0**, or 43.90 with cb ≥ 450 (the package is hidden; either fits) |

Consequences:

- Every €0.50 on price is 7,950, which is **0.0836 score**.
- With cb ≥ 450, the quality cost is zero at any ppm. With cb 0, going from 300 to 1500 ppm costs us €0.54/unit.
- Getting from the 6400 ppm opening to 300 ppm is worth 43,646 (0.46 of the score range) by itself.
- The record 0.807 decodes to C ≈ 740,850. That is about **44.92 at 300/0**, or 45.05 with cb ≥ 450. 45.00/300/0 would score 0.793.
- The winners' probes closed at 47.0/300/0 (C 773,932), which scores 0.459.

---

## 1. Supplier response model (evidence first, inference flagged)

### First counter vs. our first message (evidence, 17 sessions)

| Our r1 lead sheet | Claims | r1 counter |
|---|---|---|
| 43.05 / 300 / cb 500 (5c6ad7af, 63790d86) | otd + po | **49.0, 47.5** /300/500, text "chargeback too high", alternative with lower cb |
| 43.05 / 1500 / cb 500 (901d44ee, e64718a7, 94018805) | otd + po | 49.0 ×3 |
| 43.05 / 2500 / cb 500 (c67f7615) | otd + po | 48.5 |
| 43.05 menu {1500/500, 300/300, 300/150} (bc683f28) | otd + po | 46.5 / 300 / 150 |
| 40.41 / 300 / 0 (a77bf2af) | otd + po | 47.0 / 300 / 0 |
| 39.85–40.41 menu {1500, 800, 300} all cb 0 (7 current sessions) | otd+po ×3, ppm+po ×4 | 47.0 ×4, 46.5 ×3 at 300 / 0 |
| 45.15 / 1500 / 0 (winners) | none | 46.5 / 1500 / 0 |

What the table shows:

- **Anchor depth does nothing to the first counter.** Anchors 40.41 and 45.15 both drew 46.5–47.0. This matches the learnings ("first counters unchanged by anchor or claims").
- **Claims do nothing measurable.** Every r1 reply contains "we see your figures, but we cannot give up margin right now. Faster payment would help us more than anything." Both claim sets produced the same 46.5/47.0 split.
- **The chargeback is priced heavily.**
  - cb 500 adds €1.5–2.0 at r1 (49.0 vs 47.0 at the same 300 ppm).
  - Dropping cb 500 → 150 in r2 bought 49.0 → 46.0 at once (901d44ee, e64718a7, 94018805).
  - Inference: the supplier pays chargebacks at its *real* defect rate (scorecard ≈ 2,400 ppm per learnings), roughly 1.2 €/unit for cb 500. We gain only 0.135 €/unit, because our C uses the *committed* 300 ppm. cb 0 is the right side of this trade, and the current agent leads with it.
- **The ppm commitment is nearly free.**
  - 300 ppm at 47.0 equals its 6400 ppm opening price.
  - 300 vs 1500 ppm costs +0.50 (winners r2: 46.5/1500 → 47.0/300).
  - 300 vs 800 ppm costs about 0 (learnings).
  - For us, 1500 ppm at −0.50 is neutral (−0.04). So **300/0 is the right structure**, and the remaining value is in the unit price only.

### Per-round path (current agent, 7 sessions)

| Round | Supplier price |
|---|---|
| r1 | 47.0 / 46.5 |
| r2 | **46.0** (5/7; two sessions at 46.5 then 46.0 at r3) |
| r3–r5 | hold at 46.0 in every session; "absolute limit / rock bottom / let's lock it in" from r3–r4 |
| r5 | **final at 46.0** (a1275e31, 6161534a, 56b83cac) or still open (a77bf2af, 2dc0e660, 31d63381, 49409787) |
| r6 | the open ones step to **45.5** (4/4; 31d63381 already as final) |
| r7 | final at 45.5 |

- The supplier quotes on a €0.50 grid. After r2 it moves at most once, by one grid step.
- Our steps after r2 were 0.12–0.27 per round. The total we moved from r2 to the final was about 1.0, ending at an ask of 44.4–44.6.
- **Noise:** 56b83cac sent the same r1–r4 prices as a77bf2af/2dc0e660/31d63381 (43.54 / 43.70 / 43.97 / 44.20). It got a final at r5 (46.0) where the others stayed open and later reached 45.5. So whether r5 is final or open looks like a coin flip on identical input. **The run-to-run spread is one grid step, 0.084.**

### Triggers

- **`agreed`:** only when our sheet equals its standing price (winners r4, 47.0/300/0). After that the price is frozen: a push to 46.30 got "Our agreed offer stands" (winners r6). We never saw an `agreed` below its own counter, but we also never asked within €1 of it.
- **`final_offer`:** r5–r7 after 3–4 replies at one price. This happened whatever our step size:
  - 5c6ad7af stepped 0.3–0.5 per round and still held flat at 48.5 until a final at r7, because cb 500 was the blocker.
  - Old 901d44ee re-sent cb 500 after the supplier had accepted 150. Reply: "we already dropped our price … with the 150 chargeback, we need to stick to that". Final came at r5.
- **Walk:** a timeout after `final_offer` → `walked_away` (49409787 r8: "Since we haven't heard back from you on our final offer, I guess we're done here").

### What it says it wants (counted in replies)

- **Faster payment:** in essentially every reply. Payment is fixed at 60 days in this case.
- **On-time payment:** "your payments are often late", 10+ times. It responds well when we commit: "Thanks for confirming you will pay exactly on the due date" (2dc0e660 r1).
- **Binding volume:** "Which volume can you commit to?". Volume is fixed (15,900 in every deal).
- **A lower chargeback.**
- **A call.**
- **Proof:** "**Which figures is that based on? Please send us the data.**" This appears in **7/7 current sessions**, always in r2–r4, which are the replies to our messages with `claims=[]`. It never appears after an r1 message that carried claims.

---

## 2. Best deal reached

**45.50 / 300 ppm / cb 0 / 60 d, score 0.7099**, in three sessions: a77bf2af, 2dc0e660 and 31d63381. 49409787 also had a final at 45.5 but lost it to the timeout.

Common elements:

1. The lead sheet was 300 ppm and cb 0 from r1 or r2. This captured the free 6400 → 300 ppm move and avoided the chargeback penalty.
2. Steady small upward asks, 43.54 → 44.41.
3. **The thread was still open at r6**, where the supplier made its single post-r2 step of 0.50.

Nothing in our messages distinguishes these sessions from the 46.0 ones: the prices and claim sets are identical, and the structure is the same. The 46.0 vs 45.5 split is the supplier's schedule plus noise.

Other evidence for where the floor sits:

- Another team reached 45.00 "with two more rounds" (procurecabana learnings).
- The record decodes to about 44.92.
- C_best decodes to about 43.77 at 300/0.

**Inference:** 45.5 and 46.0 are finals set by its schedule, not its floor. An ask of 45.0–45.2 is likely above its floor and therefore agreeable. This is not proven: we never sent such an ask.

---

## 3. Where the current agent leaves value

Measured over the latest 7 sessions: mean **0.561**. Without the walk it is 0.654.

1. **Operational timeouts, about −0.11 per run.**
   - 49409787 timed out after a 45.5 final, and the supplier walked: **−0.71**.
   - 9775604d timed out twice in r4–r5. The supplier finalled at 46.0 in r5, losing the r6 chance (likely −0.084).
   - That is 2 of 7 sessions with timeouts in a **single-thread** case, so no RFQ waiting is involved. The cause is in the runner, the model calls or the network, and the logs here don't show which. This is the largest item, and it is not fixable in policy.py or the writer prompt (see §5).
2. **The r5-final coin flip, about −0.04 per run.** 3 of 6 clean sessions ended at 46.0 instead of 45.5. Our asks at that point were still about €1.6 below its price, and nothing in our behaviour changed between rounds 3 and 5. We kept making token steps that never earned a counter. The supplier's own text reads "Thanks for the small bump in price, but …" (56b83cac r4, 49409787 r7).
3. **Versus the record, about −0.10.** Even the 45.5 runs closed €0.5–0.6 above the record and about €1.7 above C_best. We never tested an ask the supplier could simply agree to: our closing asks were 44.4–44.6, below anything it had signalled.
4. **The writer creates proof requests.** In 7/7 sessions, once the claim bank is spent after r1, the supplier asks "which figures is that based on?". Most likely the writer justifies Option A's price with an unsupported reason; the prompt rule 3 under HOW TO WIN asks for "the reason in one sentence". We never answer these requests. The price effect is unproven, but it is a recurring friction in a case where the supplier's only stated objection is cash.
5. **Not a loss source:**
   - Structure: 300/0 is right.
   - Claims: no measurable effect, though they did no harm in the current version.
   - Anchor depth: no effect on the first counter.
   - The extra cb 150/300 sheets are dominated for this supplier. It chose cb 0 in 7/7 sessions, so they are harmless filler.

Older-version lessons, already fixed:

- Leading with cb 500 cost 0.3–0.5 (5c6ad7af 0.23, 63790d86 0.40).
- Citing a rising index drew "Your figures confirm our case" (c67f7615, 901d44ee).
- An unexplained walk from a 47.5/2500/500 final that would have scored 0.398 (c67f7615).

---

## 4. Proposed changes

### Change 1 (policy): one large step when a cash-pressed supplier holds twice

**Rule.** Applies when:
- the supplier shows cash pressure (`cash()` pressure ≥ 0.5, i.e. profile cash pressure or a `faster_payment` ask), and
- its last two replies did not lower our C.

Then make *one* step of 50 % of the remaining gap, once per thread. It is gated on observable signals, not on any id.

**Evidence.**
- This supplier finalled 1–3 replies after its second hold in every session.
- Token steps of 0.12–0.27 never earned a counter.
- Our asks never came within €1.5 of its price, so we never tested whether it would *agree* below its final.
- Cash-short job shops agreed to near asks elsewhere: Dralveck "agreed at our second sheet in every run" (learnings).
- C_best and the record put its floor at about 43.8–44.9.

**Expected effect on P11.** At r5 the ask jumps from about 44.2 to about 45.0–45.1. Possible outcomes:
- (a) it agrees at about 45.0 → **0.79**;
- (b) it counters 45.5 → 0.71, the same as today's good runs;
- (c) it finals at 46.0 → 0.63, which happens anyway in half the runs today.

The supplier never raised its price on a price-only move in any log; its rises came only with chargeback changes. If (a) happens in ≥ 1 of 3 runs, the mean rises about +0.03 to +0.06. This is inference and must be measured.

**Risk elsewhere.**
- P01 (Brandlhuber, cash_need) and P05 bidders carry the cash signal. Brandlhuber concedes most rounds (ratio 0.62), so two flat replies come only near its final, and the relationship floor still clamps our ask. Dralveck usually agrees before two holds.
- Distributors have punished 55 % jumps (P08: 5.55 → 5.58), but they are not cash-gated.
- The step fires once per thread and stays below its standing price, so the worst case is closing at the supplier's own final one round earlier.

**Line numbers are approximate. Apply with `git apply --recount` or `patch -F3`.**

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -33,3 +33,4 @@ BOUNDS = {
     "accept_target_pct": (0.0, 10.0),
     "lever_trades": (0.0, 1.0),
+    "hold_jump_frac": (0.0, 0.8),
 }
@@ -61,3 +62,7 @@ DEFAULTS = {
     # varied the payment days, while suppliers asked for volume, longer contracts, index clauses.
     "lever_trades": 1.0,  # > 0.5 = on
+    # a cash-pressed supplier that held twice is on its own closing schedule (final 1-3 replies later):
+    # one step of this share of the gap, once per thread, so we ask a price it can agree to (0 = off).
+    # Practice 2026-10-25: token steps of 0.5 % never earned a counter; finals came at its held price.
+    "hold_jump_frac": 0.5,
 }
@@ -127,2 +132,3 @@ class ThreadState:
     asked_breakdown: bool = False
     clause_countered: bool = False  # we offered its package with a wider index deadband once before closing
+    jumped: bool = False  # the one hold-jump step (hold_jump_frac) of this thread is spent
@@ -268,4 +274,18 @@ class Policy:
             if t.rounds_left <= round(p["endgame_moves"]) + 1:
                 step, t.holding = max(step, p["endgame_frac"] * gap), False
+        if (p.get("hold_jump_frac", 0) > 0 and not t.jumped and case is not None
+                and self.cash(t)[1] >= 0.5 and self.flat_replies(t) >= 2):
+            step, t.holding, t.jumped = max(step, p["hold_jump_frac"] * gap), False, True
         return step
 
+    @staticmethod
+    def flat_replies(t, tol=1.0):
+        """Supplier replies in a row, up to the latest, that did not lower our C by more than ``tol`` EUR."""
+        n = 0
+        for prev, cur in zip(reversed(t.their_costs[:-1]), reversed(t.their_costs[1:]), strict=True):
+            if cur < prev - tol:
+                break
+            n += 1
+        return n
+
     def at_target(self, case, t, c_theirs):
```

Notes on the diff:
- It sits outside the reciprocity branch, so it works with `reciprocity` 0 or on.
- `their_costs` gets one entry per new standing id. The supplier issues a new offer id per reply (winners' quote-offer-70140-4/-5/-6), so holds are counted. Verify this in a log before trusting it.

### Change 2 (writer): no unsupported reasons once the claims are spent

**Evidence.** "Which figures is that based on? Please send us the data." appears in 7/7 current sessions, exclusively after messages with `claims=[]`. An older reply quotes the offending prose: "You say this price fits the improved quality setup, but please show us the figures behind this" (5c6ad7af r3). The brief: "data you cite is checked … the supplier will ask for proof of anything else". Prompt rule 3 under HOW TO WIN currently demands a reason every time.

**Expected effect.** It removes an unanswered challenge from about every second reply. The effect on price is unknown, possibly zero. Its value is mainly trust and tone in a case where the supplier's text grows irritated over the rounds.

**Risk.** Low. Later e-mails lose one persuasive sentence. Suppliers that respond to warmth (D01: −1.2 % on words) still get the "what Option A gives you" sentence.

```diff
--- a/src/buyer/llm/prompts/writer_system.md
+++ b/src/buyer/llm/prompts/writer_system.md
@@ -20,3 +20,3 @@ HOW TO WIN THE REPLY
 2. Solutions, not counter-arguments. If it blames a cost (copper, alloy, steel, energy) and our options include an index clause (see CLAIM IN OPTIONS), present the clause as the answer: we take that risk above the deadband, so the base price no longer needs a risk premium. If it wants cash, volume, a longer contract or its standard payment term, point to the option that gives it - only if an option really does.
-3. Option A is the package. Name Option A as the package we can approve, and give the reason in one sentence drawn from the claims and the options. The other options are genuine alternatives for its convenience.
+3. Option A is the package. Name Option A as the package we can approve, and give the reason in one sentence drawn from the claims and the options. If no [[CLAIM_n]] is listed, the reason is only what Option A gives the supplier in its own terms - never call our price fair, justified, in line with anything or based on anything: a supplier answers such words by asking for the figures behind them. The other options are genuine alternatives for its convenience.
 4. A clear way to yes. Only if CONFIRM AT ONCE is yes: say that if it confirms Option A as it stands, we can confirm the order straight away (true there: our negotiator accepts at once). If it is no, never promise to confirm, accept or award at once.
```

The context line 2 must match the file exactly, including "see CLAUSE IN OPTIONS" (my rendering above contains a typo there). Regenerate the hunk with `git diff` after editing.

### Change 3 (writer, lower confidence, A/B only): answer repeated asks for fixed terms once, plainly

**Evidence.**
- The supplier repeats "faster payment" and "which volume" in almost every reply. Both are fixed in this case.
- Older versions that circled the topic drew irritation: "you keep talking about payment timing without actually changing the payment terms" (c67f7615 r6) and "please state the exact days" (e64718a7 r5). One misread it as an offer: "Thanks for agreeing to better payment timing" (901d44ee r2).
- The learnings record Kalwisz saying "you just ignore it" before a final.
- The explicit on-time commitment drew the warmest reply in the logs (2dc0e660 r1).

**Counter-evidence.** a1275e31 r2: "if payment terms are fixed, we don't have much room on the price". That session finalled at 46.0. Making fixedness explicit could shorten the supplier's patience. Hence A/B only.

```diff
--- a/src/buyer/llm/prompts/writer_system.md
+++ b/src/buyer/llm/prompts/writer_system.md
@@ -31,3 +31,4 @@ LATER E-MAILS
 - If it is waiting for an approval, make the options easy to take to the approver.
 - If it asked us a question, answer it in words or say that the options answer it - never leave it hanging.
+- If it asks again for a term that no option changes (faster payment, a binding higher volume), say once, plainly and without reasons, that this term is set for this order, and name what the options do give it instead; never imply that the term might still change. With ITS PAYMENT COMPLAINT, pair this with our commitment to pay every invoice on its agreed due date.
 
@@ -36,1 +37,1 @@ HARD RULES
-2. Promise nothing that is not in the options: no volumes, dates, payment terms, orders or commitments of your own. Mention a term (payment, volume, contract length, lead time, index clause) only if an option changes it. One exception: if ITS PAYMENT COMPLAINT is given, commit that we will pay every invoice on its agreed due date.
+2. Promise nothing that is not in the options: no volumes, dates, payment terms, orders or commitments of your own. Mention a term (payment, volume, contract length, lead time, index clause) only if an option changes it, or to say once that it is set for this order (see LATER E-MAILS). One exception: if ITS PAYMENT COMPLAINT is given, commit that we will pay every invoice on its agreed due date.
```

**Risk elsewhere.** Price-frozen suppliers (P03, P04) and committee suppliers asking for volume would hear "set for this order" sooner. That may close finals earlier. Measure P02/P11 together.

---

## 5. Not a diff, but the biggest lever: timeouts after a final offer

The runner is not in the files shown, so I give no diff.

Requirements:
1. A reply with `final_offer` or `agreed` whose sheet passes `eligible_cost` must be accepted without any model call: no analyst, writer, rehearsal or memory before the POST.
2. Every other move needs a hard ~45 s deadline, after which the template fallback is sent. design.md promises this, but 9775604d (r4, r5) and 49409787 (r8) show it was breached.
3. Network errors should be retried with the same `X-Move-Id`.

Check the run logs of those two sessions for which call blocked. Expected gain on P11: about +0.11 per run, and the same protection in every final wave.

---

## 6. Test protocol and skepticism

- **Noise.** Identical sheets gave either 46.0 or 45.5 (±0.084). With a binary outcome, use **≥ 4 runs per arm** for Change 1.
- **Guards.** Run P01 (cash_need, family foundry), P05 (cash-short job shop in an RFQ), and D01 on the sandbox, which is deterministic per sheet path and the cleanest check that the jump fires only after two flat replies.
- **Stop conditions.** Any walk-away, or a P11 mean below 0.66.
- **What would falsify Change 1.**
  - The supplier answers the jump with a final at 46.0 in most runs: it reads the jump as reaching its price, not as an agreeable ask. Turn it off.
  - It counters 45.5 every time: its finals are schedule-driven and there is no gain. Keep it off; the cost is zero but so is the value.
- **What stays unknown.**
  - How the other team reached 44.9–45.0. Their account only says "two more rounds".
  - Which C_best package the arena uses: 43.77/300/0 or 43.90 with cb ≥ 450. In both cases, unit price is the only lever left on this supplier.