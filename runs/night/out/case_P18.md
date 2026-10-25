# P18 (Werdenfels, `raw_material` / `leverage`, family distributor): analysis and changes

## Decoding the score (from the digest's cost breakdowns)

Several anchors are derived arithmetically from the logged breakdowns. They are inferences, but checked against four sessions.

- **Volume.** Need 23,700/yr over 2 years: price 5.60 × 47,400 = 265,440 (`a9a2846e`).
- **Payment.** Reference 60 d at 8 %. 45 d costs 0.333 % of spend (837 / 251,220 in `990f4f5b`).
- **Clause cost.** AS-14404 share 0.45, path +6 %, index risk 1 %:
  - deadband 0 %: 2.70 % + 0.45 % = **3.15 % of spend**
  - deadband 3 %: **1.80 %**
  - deadband 5 %: **0.90 %**
- **Score scale.** `13e6c049` (C 244,722, 0.6957) and `62ba92eb` (C 249,520, 0.6295) give **C_open − C_best ≈ €72,480**. That implies C_open ≈ €295,146 and C_best ≈ €222,666. C_best is about **4.73 at 90 d fixed**, matching learnings.md.
- **Check.** This predicts `990f4f5b` 0.5633 and `76dd9948` 0.3620, both exactly as logged.
- **Rule of thumb.** One supplier step of €0.10 ≈ €4.8k ≈ **0.066 score**. 15 payment days ≈ €0.8k ≈ 0.011. Deadband 0→5 % ≈ €5.4k ≈ 0.075.
- **The record.** 0.756 means C ≈ €240.4k. That is consistent with about 5.00 / 45 d / 5 % deadband (0.762) or 5.05 / 90 d / 5 % (0.762). It is **not** consistent with "5.00 with its 0 % clause": that gives 0.688 at 45 d and 0.699 at 60 d. NIGHT_CONTEXT's reading of the winners' structure is therefore probably wrong on the deadband.

---

## 1. How this supplier responds (reconstruction)

### 1a. It moves in €0.10 steps, about one per counter

Every supplier price in 15 sessions is a multiple of 0.10: 6.0, 5.8, 5.7, 5.6, 5.5, 5.4, 5.3, 5.2, 5.1.

The latest best path (`13e6c049`, `c80f8b2a`, identical) was **5.4 → 5.3 → 5.2 → 5.1, final_offer at r4**. Our steps were +0.07, +0.05, +0.03 (about 11 % of the gap each).

Its step did not depend on our step size: 0.10 in reply to +0.03 to +0.10. This matches learnings ("40 % got the same 0.10 as 30 %").

### 1b. The first counter is the main lever

Grouped by what we sent in r1 (the opening is always 6.10 / 30 d / 12 m):

| r1 message | Sessions | First counter |
|---|---|---|
| Anchor about 5.59 (−8 %), 24 m, otd + po claims | `a9a2846e`, `7c970402`, `21b6e032` | 5.7 (3/3) |
| Anchor about 4.81 (−21 %), 24 m, fixed, otd claim | `76dd9948`, `6a0c9455`, `5a09e68b` | 5.6 (3/3) |
| −21 %, one **5 % clause sheet** in the menu, otd claim | `521717f9` | 5.8 |
| −21 %, clause sheet + **2 falling-index claims** | `ab179a29`, `9ebd2de0`, `990f4f5b`, `62ba92eb` | 5.6 (4/4) |
| −21 %, **fixed sheets only** + 2 falling-index claims | `900758ae`, `13e6c049`, `c80f8b2a` | 5.5, 5.4, 5.4 |

What this shows:

- **Falling-index claims are worth about −0.2 on the first counter**, two pairs consistent. The supplier says "verified the recent decreases… reduce our price" while answering "That remains" for each rising driver.
- **A clause sheet in r1 costs about +0.2**, two pairs consistent. Learnings report the same: 1.5–2 % on P08/P18.
- **A deep anchor (−21 % vs −8 %) is worth about −0.1.**
- **Run-to-run noise is ±0.1** on identical r1 sheets: 5.5 vs 5.4 vs 5.4.

### 1c. When `final_offer` comes

- **On schedule.** After about the 4th counter when we keep moving (`ab179a29`, `990f4f5b`, `62ba92eb`, `13e6c049`, `c80f8b2a`: final at r4).
- **Early, on no real move.** Unchanged sheets gave "your proposed terms remain unchanged" (`7c970402` r3). +0.01 got "price increase insufficient" (`21b6e032` r2, final in r2).
- **After a hold.** `76dd9948` and `6a0c9455` held in r2, then went final in r3.
- **After a timeout.** `9ebd2de0`: r3 timeout → final; r4 timeout → **walked_away**, score 0.

### 1d. When `agreed` comes

- **When we send its own price**, even with a structure better for us. After `final_offer`, all **8 of 8** post-final single-sheet counters at its price were agreed: `76dd9948`, `6a0c9455`, `521717f9`, `990f4f5b`, `62ba92eb`, `900758ae`, `13e6c049`, `c80f8b2a`.
- **6 of those 8 replaced its clause with a 5 % deadband.** In `13e6c049`/`c80f8b2a` its sheets showed only the 0 % clause, yet 5.1 / 45 d / 5 % was agreed.
- **The winners' probe** got `agreed` the moment it matched 6.0 (r2). Every later push got "Our agreed offer stands" (r3–r6), so `agreed` freezes the price.

Inference: since a 5 % deadband at an unchanged price is accepted after `final_offer`, its final price sits above its floor by at least what it values the deadband at. By the learnings fit, 0.45 × 5 ≈ 2.25 % ≈ €0.11. The final is not its floor. A **price** push after final is still untested here, and D01 walked on one.

### 1e. Levers it values (what it says, and what it does)

| Lever | What it says / does |
|---|---|
| **Contract ≥ 24 m** | Requires the AS-14404 clause, every session ("cannot offer a fixed price over a 24-month period"). 36 m gave nothing extra (`5a09e68b`: 5.6). Fixed price only at 12 m: the winners' probe agreed 6.0 at 12 m. |
| **Deadband** | Prices it in early rounds (r1 sheet +0.2). Concedes it free at the close (8/8). |
| **Payment** | Nearly free to it. The winners' probe asked 6.0 at 30 d, then **agreed 6.0 at 90 d** in the next round. In `13e6c049`/`c80f8b2a` it put 90 d into its own standing sheet. Once (`900758ae` r2) it offered a lower price for 14 d. Learnings: "distributors 0 (free)". |
| **Option A** | It **builds on our Option A**: "Building on your Option A" in `521717f9`, `ab179a29`, `990f4f5b`, `62ba92eb`, `900758ae`. Whatever lever sits in our first sheet is kept, and the concession is applied there. |
| **Asks** | "A binding higher volume would help us and can improve the price"; "Which volume can you commit to?"; "please provide the data or forecast to substantiate" (`13e6c049` r3–r4, `c80f8b2a` r3–r4, `62ba92eb`, `990f4f5b`, `900758ae`). **We never answered with data.** |
| **Claims** | Delivery record got "it holds, but it does not change our calculation" every time (9 sessions). Price history got "does not concern this part". |
| **Tone** | It signs as "family company… reliable cooperation". In `900758ae` it replied twice: "I am fully authorized… making escalation unnecessary". Our decision-maker paragraph (writer rule 5) read as escalation to an owner-run firm. No measurable price effect. |

---

## 2. Best deal in the logs, and what produced it

**€5.10 / 45 d / 24 m / AS-14404 with 5 % deadband: score 0.6957, C €244,722** (`13e6c049` and `c80f8b2a`, identical). What produced it:

1. **r1:** −21 % anchor (4.79), **three fixed sheets** (45 / 90 / 60 d, 24 m, no clause), **two falling-index claims** (AS-14404, PPI-C2431). First counter **5.4** at 0 % clause, the best first counter in the logs.
2. **r2–r4:** fixed sheets kept (we never adopted its clause). Steps of about 11 % of the gap, one useless otd claim in r2. The supplier stepped 0.10 each round to 5.1 and went final at r4.
3. **r5:** we sent one sheet at its price with a 5 % instead of 0 % deadband. It agreed, and we accepted.

The near-identical `900758ae` (same r1 code, 0.497) differs in two ways:

- In r2 it put a **5 % clause on all three sheets**, and the supplier **held** (5.5 → 5.5).
- It then went final at r3 instead of r4.

That is one more pair supporting "no clause sheets while price is moving". It is one session, though, and the r1 counter was already 0.1 worse by noise.

---

## 3. Where the current agent leaves value

Baseline: the current agent's 0.696.

| Gap | € | Score | Evidence |
|---|---|---|---|
| **A. Option A carries 45 d**, so the supplier locks in 45 d. Payment is free to it; we pay 0.33 % of spend. | 806 vs 60 d, 2,418 vs 90 d | +0.011 / +0.033 | Deals at 45 d in 6 of the latest 7. The menu sorts 45 d first because, at the default supplier rate 0.08, it looks a hair cheaper. `OWN_PRICE_SLACK=0.005` (policy.py menu) passes it: 45 d at their price costs us only 0.33 % more. |
| **B. Closing counter ignores the supplier's longer payment term.** It keeps the payment days of the sheet it mirrors, though the supplier showed 90 d in its own standing. | about 1,612 | +0.022 | `13e6c049`/`c80f8b2a` r4 standing showed 90 d. 5.1 / 90 d / 5 % would score **0.729**. |
| **C. No closing counter after `final_offer` when its standing is the cheapest sheet.** `close()` runs the clause-variant branch only when `t.status == "open"`, so it accepts the final as is. | 2,300 (3 %→5 %), up to 5,400 (0 %→5 %) | +0.03 / +0.075 when it fires | `ab179a29` accepted 5.4 / 60 d / **3 %** at r4 final. The same supplier agreed to a 5 % deadband at its final price in 8 of 8 post-final counters. |
| **D. One supplier step.** Its final is above its floor (§1d). | about 4,800 | +0.066 (≈ record) | Record ≈ 5.00–5.05 with 5 % deadband, one 0.10 step below us. **What buys the extra step is not established.** Candidates: a 5.3 first counter (seen once in learnings v10 with falling claims), a 5th counter via slower steps (one run), or answering the volume / forecast proof request (asked 2–3× per session, never answered). |
| **E. Robustness.** | — | 0 vs 0.5+ | `9ebd2de0` lost the case to two consecutive timeouts after a 5.4 counter. One loss in 15 sessions at this supplier. Network / runner issue, not policy. |

A, B and C are cheap, mechanical, and supported by this supplier's own behaviour. D is where the record lies but needs experiments, not a code guess. A + B together would move the latest path from 0.696 to about **0.729**, roughly half the gap to the record.

**Noise caveat.** The first counter varies ±0.1 (±0.066 score) on identical messages. Any single-run comparison on P18 below about 0.07 is inside noise. A/B/C act on structure at a fixed price path, so they should show even within noise, provided the supplier's price path is unchanged.

---

## 4. Proposed changes

### Change 1: no payment shorter than our reference for suppliers not short of cash

**Rule (general).** Suppliers keep the levers of our Option A and apply their own price to it (here; and in munich EVALUATION.md: "430.01 with 30 days instead of 432.94 with 90 days"). So a sheet that pays earlier than `reference_payment_days` only pays off when the supplier values cash above us. Keyed on the existing `cash_hungry` signal: rate ≥ 0.15, set by cash-short archetype, cash pressure or a faster-payment ask in `Policy.cash`.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def menu(self, case, t, a, c_cap):
         theirs = t.standing_terms.get("unit_price")
         at_theirs = self.c(case, {**a, "unit_price": theirs}, t) if theirs else math.inf
         rel_case, rel_floors = relationship_case(case) and floor_binds(t), {}
         cash_hungry = model["interest_rate"] >= CASH_HUNGRY_RATE
+        ref_days = case["buyer"]["reference_payment_days"]
         found = []
         for combo in itertools.product(*domains.values()):
@@
             terms = complete_offer(case, {**levers, "unit_price": price})
             if not must_haves_ok(case, terms, t.standard):
                 continue
+            if not cash_hungry and (terms.get("payment_days") or ref_days) < ref_days:
+                continue  # it keeps Option A's term but not our price: early payment only for cash-hungry suppliers
             if rel_case:
@@ def lever_trades(self, case, t, a, asks=()):
             if (theirs and not hungry and v["field"] == "payment_days"
                     and self.c(case, {**sheet, "unit_price": theirs}, t) > at_theirs * (1 + OWN_PRICE_SLACK) + 1.0):
                 continue
+            if (not hungry and v["field"] == "payment_days"
+                    and (sheet.get("payment_days") or 0) < case["buyer"]["reference_payment_days"]):
+                continue
             gain = v["supplier_gain"] or 0.0
```

**Expected on P18.**
- With the 45 d sheet gone, the cost-sorted menu leads with 90 d. At supplier rate 0.08, 4.84 / 90 d is slightly cheaper for us than 4.81 / 60 d.
- The supplier builds on Option A and has shown it takes 90 d at no charge (winners' probe; its own 90 d standing). Expected 5.1 / 90 d / 5 % = **0.729** (+0.033); at worst 60 d, 0.707 (+0.011).
- It does not change the r1 claims or the "fixed sheets only" structure that produced the 5.4 first counter.

**Risk elsewhere.**
- **Cash-short suppliers are unaffected.** P05 Dralveck, P11 Kalwisz and P01 Brandlhuber (cash_need) are hungry via `cash()`.
- **P07 Leitner (rate about 8.5 %)** is the main regression risk. The winners' deal there was 5.35 / 45 d, and 45 d is roughly zero-sum for us. Expected change is about ±0.005, worth one run as a check.
- **Hidden cases** with a full-book supplier charging 12–17 %/yr (Hrvelec type) lose a small genuine trade. Bounded: a 15-day trade is worth under 0.3 % to us.
- **Empty menu.** If the menu ends up empty, `offer()` falls back to `[a]` at the reference term. No crash path.

### Changes 2 and 3: the closing counter also after `final_offer`, led by the supplier's own longest payment term

**Rule (general).**
- **Change 2.** Before accepting a final or near-final offer, send once a sheet at **its price** combining the levers cheapest for us that it either already offered itself (payment term) or that the case allows as a structure (widest deadband). Its own package stays as the last sheet.
- **Change 3.** Today this one-time counter fires only on `open`, so finals like `ab179a29` (3 % deadband) were accepted unimproved. Extend it to `final_offer`.

No new price demand is made.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def close(self, case, t, acceptable, c_theirs, rival_best_c):
             if alt[0] < alternative_cost(case) and alt[0] <= rival_best_c:
                 t.mirrored = True
                 sheet = complete_offer(case, dict(alt[2]))
-                variants = self.clause_variants(case, t, sheet)  # its package, but our cheapest deadband first
+                variants = self.with_its_terms(case, t, sheet)  # its package: our cheapest deadband, its longest payment
                 t.clause_countered = t.clause_countered or bool(variants)
                 t.our_prices.append(sheet["unit_price"])
                 t.our_costs.append(self.c(case, sheet, t))
                 intent = "appreciative: we accept your alternative proposal as offered"
                 if variants:
-                    intent += "; we would prefer the same with a wider index deadband"
-                return Decision("send", t.supplier_id, term_sheets=[*variants, sheet][:3], intent=intent)
-        if acceptable and t.status == "open" and t.rounds_left > 1 and not t.clause_countered:
-            variants = self.clause_variants(case, t, complete_offer(case, dict(t.standing_terms)))
+                    intent += "; we would prefer the same on the best of the terms you have offered"
+                return Decision("send", t.supplier_id, term_sheets=[*variants[:2], sheet], intent=intent)
+        if acceptable and t.status in ("open", "final_offer") and t.rounds_left > 1 and not t.clause_countered:
+            variants = self.with_its_terms(case, t, complete_offer(case, dict(t.standing_terms)))
             if variants:  # one more message before closing: its own package stays on the table as the last sheet
                 t.clause_countered = True
                 own = complete_offer(case, dict(t.standing_terms))
                 t.our_prices.append(own["unit_price"])
                 t.our_costs.append(self.c(case, own, t))
-                return Decision("send", t.supplier_id, term_sheets=[*variants, own][:3],
-                                intent="appreciative: we can agree to your offer; we would prefer it with a wider "
-                                       "index deadband")
+                return Decision("send", t.supplier_id, term_sheets=[*variants[:2], own],
+                                intent="appreciative: we can agree to your offer at your price; we would prefer it "
+                                       "on the best of the terms you have offered")
         return self.accept(t) if acceptable else Decision("walk", t.supplier_id)
 
+    def with_its_terms(self, case, t, sheet):
+        """clause_variants of ``sheet``, led by the same sheet at the longest payment term the supplier itself
+        put in one of its current sheets - if that is cheaper for us and keeps the must-haves. Its own levers,
+        its own price: no new demand on it."""
+        variants = self.clause_variants(case, t, sheet)
+        base = variants[0] if variants else sheet
+        paid = [s.get("payment_days") for _, s in t.offers or [] if s.get("payment_days") is not None]
+        if "payment_days" in case["negotiable"] and paid and max(paid) > (base.get("payment_days") or 0):
+            longer = complete_offer(case, {**base, "payment_days": max(paid)})
+            if must_haves_ok(case, longer, t.standard) and self.c(case, longer, t) < self.c(case, base, t) - 1.0:
+                variants = [longer, *variants]
+        return variants
+
     def clause_variants(self, case, t, sheet):
```

Notes on the diff:
- `[*variants[:2], own]` guarantees the supplier's own package survives the 3-sheet cap. The old `[*variants, sheet][:3]` would drop it once three variants exist.
- `self.c` includes the relationship charge, so in `stabilise` / `secure_supply` cases a longer term that squeezes the supplier's margin is rejected by the C check.
- No loop: `clause_countered` / `mirrored` make the counter one-time, after which the next `final_offer` closes.

**Expected on P18.**
- Latest path: the r5 counter becomes [5.1 / 90 d / 5 %, 5.1 / 45 d / 5 %, …] → 0.729 if it picks the first, 0.696 (status quo) if the second.
- Paths like `ab179a29` (final at 3 %, standing cheapest) gain about +0.03.

**Risk.** Two assumptions are unverified.

1. **No walk after a post-final counter at its own price.** 8/8 here and in P18 only. Nordmark (P02) and D01 walked on **price** pushes after final, not on structure. The variants only fire where a cheaper allowed deadband exists, or the supplier itself offered a longer term.
2. **Which sheet the supplier picks when given several.** The digest shows the agreed post-final messages with one sheet. Whether the running code sent more is not visible. If the supplier picks the sheet best for itself and that is its own package, Change 2 can fall back to its standing, i.e. what we would have accepted anyway, so no loss versus accepting. Before merging, read the raw r5 message of `13e6c049` (`GET …/threads/sup:70740`). If it carried a single sheet, consider dropping `own` from the post-final counter.

**Broader exposure.**
- Distributors with clauses (P08 Donautal) behave like P18 and should gain similarly.
- Group-ladder suppliers rarely have a cheaper deadband left at final; the counter then does not fire.

### Not proposed as code (needs runs, not a guess)

- **Finding the extra €0.10 (gap D).** These ideas are worth 2–3 runs each, compared on first counter and number of counters, not on score:
  - A third r1 claim. The slot is unused: 2 of `FIRST_MESSAGE_CLAIMS=3`, and the r2 otd claim never moved it.
  - Answering the forecast / volume-proof request with an `fc:` claim in the round it is asked.
  - Steps of about 8 % instead of 11 % of the gap, to see whether a 5th counter appears. Learnings: one run gave 5 counters at a 12 % walk.
- **Writer rule 5** (decision-maker paragraph). It produced "escalation unnecessary" twice from an owner-run distributor in `900758ae`. Worth gating on the DOSSIER's owner type, but there is no price evidence, so no diff.

### Validation plan

1. Run P18 twice with Change 1 alone.
2. Then twice with 1 + 2/3.
3. Guard runs: P07 (payment), P08 (closing counter) and P05 (cash-hungry, should be unchanged).

**What to read.**
- On P18, judge by **final terms at a given price path** (payment days and deadband of the deal), not by score alone. The ±0.1 first-counter noise swamps 0.011–0.033.
- Watch for any walk after a post-final counter. One walk is enough to restrict Change 3 back to `open` for non-distributors.