# P10 / Ravensteiner (near-monopolist, `secure_supply`): analysis and changes

## 0. Score arithmetic for this case

All figures here are derived from the digest's cost breakdowns. Four of our deals fit one linear model to within 0.0001 of their scores.

**Our terms in every deal.** Volume 23,400/yr × 2 years = 46,800 units. Payment 30 days against a 60-day reference. 300 ppm at €380 per defect gives €5,335. Late cost is €2,400/day beyond 42 days; 56 days costs €33,600.

**Reproducing the scores:**
- 31.7 / 56 d: C = 1,483,560 + 9,890 + 33,600 + 5,335 = **€1,532,385** → 0.6629 ✓
- 31.9 / 56 d: **€1,541,808** → 0.6473 ✓
- 32.1 / 56 d: €1,551,230 → 0.6317 ✓
- 34.0 / 42 d: €1,607,143 → 0.5391 ✓

**Solving for the yardsticks:**
- **C_open ≈ €1,932.5k.** It is this high because the quote covers only 19,890 units for 12 months, so most of the need falls back at a 25 % risk rate.
- **C_best ≈ €1,328.9k.** This is consistent with learnings.md's "28.21 at 42 days", though not exactly decodable.
- **No relationship charge appears in any deal**, so its margin floor is not binding at 31–34.

**Exchange rates:**
- €0.01/unit ≈ €471 of C ≈ **0.00078 score**.
- One lead-time day beyond 42 = €2,400 ≈ **0.0040 score** ≈ **€0.051 per unit**.
- **Record 0.702** (NIGHT_CONTEXT) ⇒ C ≈ €1,508.8k. By my inference that is about **31.20 at 56 d / 30 d / 300 ppm**, or about 31.94 at 42 d.
  - learnings.md mentions a deal at 31.10 ("no charge at 31.10") without terms.

---

## 1. Findings (ranked)

### F1. The supplier's response function

The evidence is 14 of our sessions and one winners' probe (d0a64f6e).

**It is close to deterministic.** Identical first messages produced identical replies:
- 33.8 in 7/7 sessions with anchor 28.5–29.15, 24 m, delivery + price-history claims;
- 33.6 in 4/4 sessions with the should-cost claim.

This is unlike the 1–2 % spread learnings.md reports for distributors. So single-sample differences of €0.1 here are plausibly real, not noise. Treat that as a hypothesis with n=1 behind each specific delta.

**First counter (round 1), with our first sheet always 24 or 36 m / 23,400 / 42 d:**

| Our r1 | Claims | Its r1 @42 d | Its alt @56 d (= our r2 ask, agreed) | Sessions |
|---|---|---|---|---|
| 25.66 (−20 %) | otd, po | 34.0 final | ≤32.1 | 34cdb95d, 60ecd641 |
| 29.15 (−9.5 %) | otd, po | 33.8 final | 31.9 | 1ac5d497 |
| 28.5 (−11.5 %) | otd, po | 33.8 final | 31.9 | e74ede01, 9031109a, 7b7e3423, 43f6a74c, a288ff3c, 9e05bbcc |
| 28.5, **36 m** | otd, po | 33.7 final | 31.8 | ccb1025c (n=1) |
| 28.5 | ppm, po, **should_cost** | 33.6 final | 31.7 | b8ac8abb, 1cc02268, 9b49cc18, 3f16a895 |
| winners 29.89 (−7.2 %), 12 m, **56 d**, no claims | – | **32.0 open** @56 d, 12 m, volume back to 19,890 | – | d0a64f6e |

The pattern fits roughly:

> r1 price @42 d ≈ 33.8 − 0.2·[should-cost claim] − 0.1·[36 m] + 0.2·[anchor ≥ 20 % below]

- The anchor is otherwise inert between −7 % and −11.5 %.
- A deeper anchor only hurt (25.66 → 34.0).
- The 56-day alternative is always exactly €1.90 below the 42-day price. That is 14 days, ≈ **€0.136/unit/day ≈ 0.42 %/day**.
- d0a64f6e r3 independently shows 56 d → 35 d priced +3.00 = €0.143/day.
- Its speed premium is therefore **2.7× our late cost** (€0.051/unit/day).

**What triggers `final_offer`.** It came in round 1 in **13/13** of our sessions, and **not** in the only probe that asked 56 d at −7 % (d0a64f6e, "My call: counter").
- Two explanations fit, and the logs cannot separate them:
  - (a) asking for a lead time below its standard (54 d);
  - (b) a low patience threshold on the gap. Learnings: "Ravensteiner finalled in round 1 at 15 %". Our gaps were 13.8–24 % against its 42 d counter; the probe's was 6.6 %.
- Both point to the same remedy: ask its long lead time with a moderate anchor.

**What triggers `agreed`.**
- In 11/11 sessions it agreed when our r2 sheet was exactly its own alternative, which `close()` mirrors.
- In d0a64f6e it agreed when the sheet was at its last counter's price plus a lever it values (12 → 24 m at 32.0).
- After `agreed` the price is frozen: d0a64f6e r6 asked 31.96 and got "Our agreed offer stands".
- **A sheet above the agreed price is agreed at the higher price** (d0a64f6e r4: 32.45 replaced the agreed 32.0, about −0.035 score). Our `decide()` accepts on `agreed` immediately, which is correct; keep it.

**Steps after round 1.** Our logs have none, because the thread was always final after r1. Learnings.md (winners) reports a round-2 sheet at 30.36/30.53 drew a further final at 31.60, against 31.70 after an ask at 31.42. That is "2 counters" with no walk. n is small and the terms are unknown.

**Levers it values:**
- **Lead time:** strongly, about 0.42 %/day.
- **Contract length:** at 12 m it cut volume to 19,890; 24 m unlocked the full 23,400 ("The extended 24-month contract term enables us to allocate the volume"). 36 m was worth about −0.1 (n=1). It said "further price adjustments would require a longer contract term" (d0a64f6e r1).
- **Should-cost claim:** "took it into account", −0.2.

**What does nothing:**
- Delivery record, price history and quality record: "does not change our calculation", 13/13, 13/13 and 3/3.
- A rising index (LCI-C +2.7 %): "Your figures confirm our case".
- Breakdown requests are refused every time.

**What it says it wants:** capacity-planning security ("aligns with our capacity requirements"), volume ("Which volume can you commit to?" in about half its replies, even after we committed the full need), data behind our figures ("Which figures is that based on?"), and its own lead time.

### F2. The best deal in the logs

**0.6629: 31.7 / 24 m / 23,400 / 56 d / 30 d.** Four identical sessions: b8ac8abb, 1cc02268, 9b49cc18, 3f16a895. The path was:
1. r1 sheet 28.5 @42 d with should-cost + price-history + quality claims;
2. r1 final at 33.6 @42 d, carrying the 56-day alternative;
3. `close()` mirrors the alternative at 31.7;
4. `agreed` in r2; accepted.

The only gain against the 31.9 runs is the should-cost claim (−0.2, ≈ +0.016 score).

The winners' probe finished worse: its own accepted 32.45 computes to ≈ 0.604 (inferred, not shown). The 0.679 entry in learnings.md (31.50 / 56 d / 36 m) is not in this digest.

### F3. Where the current agent leaves value

**(a) We spend our only real move on a speed we cannot afford.**
- `offer()` → `best_options()` picks lead 42 because, at a fixed price, 42 d has no late cost.
- In `menu()`, any 56-day combination is then filtered by the `OWN_PRICE_SLACK` test. At the supplier's own price, 56 d costs us +€33,600, which exceeds 0.5 % of C. So Option A is always 42 d. This is inferred from the code and matches the single 42-day sheet in every r1.
- The supplier answers with its speed premium and, in 13/13 cases, a round-1 final.
- We end at 56 d anyway (13/14). We merely lost the chance to bargain over the 56-day price.
- **We also depend on the supplier volunteering the long-lead alternative.** When we did not take it (34cdb95d, accepting 34.0 @42 d), the score was 0.539. A hidden near-monopolist that sends only the 42-day price would leave us there.

**(b) We never test below its alternative.** `close()` mirrors the alternative exactly ("we accept your alternative proposal as offered"). Learnings' 31.60 suggests about €0.10 more was available (≈ 0.008), but at the risk of a walk after a final.

**(c) 36 months is free for us** (a commitment beyond the 2-year horizon "neither costs nor earns") and was worth about €0.1 (ccb1025c, n=1).
- `best_options` with `LONG_CONTRACT_TYPES` should already pick 36 m for a capacity case.
- Yet the four latest (best) sessions sent 24 m. Either they predate that rule, or something overrides it.
- **Verify before the final**: should-cost + 36 m might give 31.6, if the effects add (an inference).

**(d) Gap to the record:** ≈ €0.50/unit ≈ €23.6k ≈ 0.039.

**(e) Gap to C_best** (0.34 of the score) is not reachable with these mechanics. The supplier's floor at 42 d is ≤ 28.21, yet no log shows it below 33.6 at 42 d or 31.6 at 56 d. Its stopping point is set by its concession schedule (final after 1–2 replies), not by cost.

**(f) Payment** is 30 d in every deal (€9.9k, 0.016). The digest never shows us varying it. Even if it is negotiable, at an assumed 7 % supplier rate against our 8 %, a trade nets about €1k. Not worth a move.

---

## 2. Changes

### Change 1: for a supplier that prices speed above our late cost, ask its own lead time and open at most 10 % below

**The rule (general).** Applies when the supplier model's lead effort × price exceeds twice our late cost per committed unit and day. Today this holds only for the `near_monopolist` archetype (`ARCHETYPE_LEAD_EFFORT`); default suppliers have 0.001 × price, which is below the threshold. When it holds:
- keep the longest lead time the supplier has itself put on the table, if every must-have still holds;
- cap the opening discount at 10 %.

**Evidence.**
- Its speed premium is €0.136–0.143/unit/day (12 sessions plus d0a64f6e r3) against our €0.051.
- The only r1 reply that stayed open came to a 56-day sheet at −7.2 %.
- Deeper anchors never lowered its counter. −20 % raised it by €0.2.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@
 OWN_PRICE_SLACK = 0.005
 CASH_HUNGRY_RATE = 0.15
+SOLD_OUT_MAX_OPEN = 0.10  # a supplier that charges for speed finals early on deep asks; deeper anchors never helped
@@ def next_price(self, t, theirs, step=None, case=None):
         t.holding = False
         if not t.our_prices:
             price = low + self.p["open_frac"] * (theirs - low)
+            if case is not None and self.lead_priced(case, t):
+                price = max(price, theirs * (1 - SOLD_OUT_MAX_OPEN))
         else:
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
         b = case["buyer"]
         base = {**t.standing_terms, "unit_price": price}
+        skip = {"payment_days"}
         if "payment_days" in case["negotiable"]:
             base["payment_days"] = b["reference_payment_days"]
-        a = self.best_options(case, complete_offer(case, base), t.standard, skip={"payment_days"})
+        leads = [x.get("lead_time_days") for x in [t.standing_terms, *(o for _, o in t.offers or [])]
+                 if x.get("lead_time_days") is not None]
+        if leads and "lead_time_days" in case["negotiable"] and self.lead_priced(case, t):
+            longest = {**base, "lead_time_days": max(leads)}
+            if must_haves_ok(case, complete_offer(case, longest), t.standard):
+                base, skip = longest, skip | {"lead_time_days"}  # its own lead time: speed costs us more in price
+        a = self.best_options(case, complete_offer(case, base), t.standard, skip=skip)
         a = self.adopt_structure(case, a, t)
@@
     @staticmethod
     def effort(terms, model):
+    def lead_priced(self, case, t, model=None):
+        """The supplier charges more per day of faster delivery (lead effort x its price) than twice our late
+        cost per committed unit and day - a sold-out supplier (practice: ~0.14 EUR/unit/day against our 0.05)."""
+        b = case["buyer"]
+        model = model or self.supplier_model(case, t)
+        units = (b.get("need_per_year") or 0) * (b.get("horizon_years") or 0)
+        if not units or not model.get("ref_price"):
+            return False
+        return model.get("lead_effort", 0.001) * model["ref_price"] > 2 * (b.get("late_cost_per_day") or 0) / units
+
+    @staticmethod
+    def effort(terms, model):
```

The `@staticmethod` on `effort` moves below the new method; the hunk is shown in context.

**What the change produces in P10.**
- r1 sheet: 28.98 @ 56 d (54 snapped to the nearest option), 36 m (`LONG_CONTRACT_TYPES`), should-cost claim unchanged.
- In `menu()`, 42-day variants are priced about 1.9 higher at equal supplier worth. That is more than 0.3 % dearer for us, so they are dropped.
- The result is one sheet, structurally like d0a64f6e r1.

**Expected effect on P10 (inference, not evidence).**
- The thread stays open in r1 at about 31.7–32.0 @56 d.
- Our concession loop then gets 1–2 more counters. Learnings report a final at 31.6 after a deeper second ask.
- Range: 31.4–31.6 gives **0.671–0.686** (+0.008…+0.023).
- **Downside:** if it finals at 31.9 in r2 we accept it: 0.647 (−0.016).
- Because this supplier is deterministic, **two practice runs decide it**. Revert if both land below 0.663.

**Risk to other cases.**
- It fires only where lead effort is above default, i.e. near-monopolist profiles. A hidden near-monopolist with a high late cost per unit fails the 2× test and is unchanged.
- Must-have lead-time caps are respected: P05's Hrvelec has ≤ 42 and the default archetype, so it is untouched either way.
- The anchor cap could cost value against a near-monopolist that would have moved further on a deep anchor. There is no observation of that; the brief describes them as barely moving.
- The robustness gain is real: we no longer rely on the supplier volunteering a long-lead alternative (34cdb95d shows the cost of not getting there, −0.12).

### Change 2 (opt-in, off by default): after a final that carries a cheaper alternative, put a slightly lower copy of it first and its own alternative last

This mirrors the existing `clause_variants` "can only gain" pattern, but on price.

**Evidence.**
- d0a64f6e: "We accept your first proposal" when we sent two sheets.
- Learnings: a second ask below the alternative after a final drew 31.60 instead of 31.70, with no walk. n ≈ 2, terms partly unknown.

**Expected gain:** about €0.1/unit ≈ +0.008 on P10.

**Risk:** "push further and it may walk"; P10 has no alternative, so a walk is −0.66. At +0.008 this only pays if the walk probability is below about 1.2 %. The evidence cannot show that.
- It therefore ships at 0.
- Test with `"final_probe": 1.5` in params.json on P10 and on one final-in-round-3 supplier (P08), two runs each, before enabling.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ DEFAULTS = {
     "lever_trades": 1.0,  # > 0.5 = on
+    # after a final that carries a cheaper alternative, ask this % below it first, its own sheet last; 0 = off
+    "final_probe": 0.0,
 }
@@ def close(self, case, t, acceptable, c_theirs, rival_best_c):
                 variants = self.clause_variants(case, t, sheet)  # its package, but our cheapest deadband first
+                probe = self.p.get("final_probe", 0.0)
+                if probe > 0 and t.status == "final_offer" and t.rounds_left > 2:
+                    low = {**sheet, "unit_price": round(sheet["unit_price"] * (1 - probe / 100), 2)}
+                    low = self.above_floor(case, t, low)
+                    if low["unit_price"] < sheet["unit_price"]:
+                        variants = [low, *variants]
                 t.clause_countered = t.clause_countered or bool(variants)
                 t.our_prices.append(sheet["unit_price"])
                 t.our_costs.append(self.c(case, sheet, t))
-                intent = "appreciative: we accept your alternative proposal as offered"
+                intent = ("appreciative: we can take your alternative as offered (last option); please meet us on "
+                          "the first" if probe > 0 and variants and variants[0]["unit_price"] < sheet["unit_price"]
+                          else "appreciative: we accept your alternative proposal as offered")
                 if variants:
```

**Risk to other cases:** none while it is 0.

**When enabled:** the writer must not say "we accept" while Option A is lower. The intent string handles that. The writer's rule 4 ("Only if CONFIRM AT ONCE is yes…") must also stay false here, or it would promise acceptance of Option A.

### Verification item (no diff yet): 36 months in capacity cases

The current `best_options` should send 36 m (ties → `max` for `LONG_CONTRACT_TYPES`), but the last four sessions sent 24 m.
- Run one P10 session on current main and check the r1 sheet.
- If it is still 24 m, look at what overrides it. `adopt_structure()` copies the best offer's `contract_months` once more than one structure has been seen.
- The fix is worth about €0.1 (≈ 0.008), costs us nothing (beyond the horizon), and matches the supplier's stated want ("further price adjustments would require a longer contract term").

---

## 3. What I would not change, and why

- **Claims.** Price-history, delivery and quality records never moved this supplier, but they cost nothing beyond a slot. Rising indices actively hurt, and current `claims.py` already restricts index claims to falling windows. Should-cost is the one claim that helped and is already chosen.
- **Writer prompt.** No logged evidence ties wording to price for this supplier. Learnings found practice suppliers flat on fully model-written e-mails.
- **Acceptance on `agreed`.** It is correct as is. d0a64f6e shows what happens otherwise: re-sending a changed sheet after `agreed` replaced 32.0 with 32.45.

**Net:** the realistic upside on P10 is +0.01 to +0.04, worth 0.1–0.4 points on the 10-case mean. The more important effect of Change 1 is general: it stops us asking near-monopolists for a speed whose price exceeds our late cost, and from depending on them to offer the cheaper alternative themselves.