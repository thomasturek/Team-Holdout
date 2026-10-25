# What sets the first counter and the number of counters

## Round-1 inputs → first counter (all 200 practice threads in the digest)

Opening = our lead price vs. the quote. "Steps" = the supplier's later moves per reply. "Final@" = the reply in which it sent `final_offer` (counting its quote as reply 0).

| Supplier (case) | Our round-1 inputs | First counter | Steps | Final@ | Deal (score) |
|---|---|---|---|---|---|
| Brandlhuber P01, quote 138.55/30d/Nov | no claims, 3 sheets 60/45/30 at −9 % (75b0649b, b4535c94) | 140.30/Apr; 142.90/Apr | 1.5, 0.5, 0.4 | 4 | 137.9 (0.760), 140.5 (0.616) |
| | notice+ppm verified, same sheets (1e887324, 36af37af, d5066cc6) | 137.8/Apr + 134.8/Jan ×2; **135.5** single ×1 | 1.3, 1.0, 0.7 / 0.8, 0.8, 0.6 | 4–5 | 134.8 (0.926) ×2, **133.3 (0.969)** |
| | notice+ppm, 2 sheets at −7 % (a37615af) | 137.8 + 134.9/Jan | 1.3, 0.6, 0.4, 0.3 | 5 | 135.2 (0.911) |
| | notice+ppm, 14-day sheets (2c6e9cc0) | 137.0/14 + 134.2/Jan | 1.0, 0.6, 0.5, 0.4 | 5 | 134.5/14 (0.914) |
| | notice+ppm, sheets 45/60/90 at −4.5 % (df366f6a, cac09d93, 773a42a5, 551cb8be, 478e95da) | 138.6/45 + 135.4/Jan ×4; 136.8/45 ×1 | holds when our lead price fell or moved 0.04 | 2–5 | 138.6 (0.762, accepted r2), 135.5 (0.864), 136.6 (0.842) ×2, 134.6 (0.909) |
| | 3 claims, −9.5 % at 30/45/60, with/without escalation paragraph, open question, goodwill paragraph, fc claim (9c0ba9cd, 38367dc0, 934ed1e9, 6d1edc5d, d9cfc61a, 7807fb7a) | 137.8 + 134.8–134.9/Jan ×3; 137.4; 136.5 single; 136.9 + 134.2 | 1.3, 1.0 then we jumped to its price | 3–4 | 134.6–134.7/14 (0.905–0.909); 136.49 (0.848); 137.3 (0.800) |
| | 3 claims, −5 % at 30/45/60 (c006eed3, 081a155f) | 138.1/60 + 136.5/30; 137.8/60 + 136.2/30 | hold, 0.6, 1.0 | 5 | 134.9/14 (0.895), 135.6 (0.893) |
| Nordmark P02 | no clause: any opening (−8.4 %, −3.4 %), any claims | 372.55/60 + 370.50/30 (5 of 5) | 0.3, 0.3, 0.3 | 5 | 371.6–372.2 (0.16–0.24) |
| | one sheet with CU clause, 5 % deadband, ≥355.81 (13 of 13) | **agreed in round 1** | – | – | 355.81 (0.611) … 361.72/90 (0.7345) |
| Selvbrunn P03 | anything | price table by payment days: 14d 426.97–427.12, 30d 428.85, 45d 429.43–429.58, 60d 430.16–430.31, 90d 431.63–431.77; vol 5496 → 424.61/60 | 0 | 6–7 | 431.63/90 (0.935) |
| Wälzlager P04 | anything (36 m no effect) | table: 14d 4.87, 30d 4.88, 45d 4.89–4.90, 60d 4.91, 90d 4.94 | 0.01 | 3–4 | 4.89/45 (0.874) only if the final still lists it; else 4.94/90 (0.860) |
| Dralveck P05 | ppm only, −12 % (42fd7e08, 25a2dfb2) | 32.50/30 | 0.5 | 4 | 32.0 |
| | ppm + rival 31.50 (+index), opening 26.6–27.9, 1–3 sheets (12 sessions) | 30.50 (14 or 30 d) ×10, 30.00 ×2 | 2.0–2.5 then 0.05–0.5 | 2–3 | 28.00/14 (0.8136) ×9, **28.05/30 (0.8186)** ×2 |
| Fuchsreiter P05 | 0–1 claim / rival+otd / rival+otd / rival+news+ppm | 32.00 / 31.50 / 31.00 / 30.50 | 0.5 | 4–5 | floor seen 28.50/14 (9bd523d1 r3) |
| Hrvelec P05 | any | 34.0–34.5/35d + 31.0/52d | 0.5 | 4–5 | never ≤33.0 at ≤42 d |
| Leitner P07 | 60/45/30 sheets, 2 claims (4 early sessions) | 5.53/30 | 0.02–0.04 ≈ ours | 3–4 | 5.42–5.49/30 (0.65–0.69) |
| | 90/45/60 sheets, po/fc claims, with or without escalation/goodwill text (20 sessions) | 5.55–5.56/60 (6×) or 5.60/60 (14×), + a 45d sheet 0.02–0.05 lower | 0.02–0.05 ≈ ours | 4 | final ≈ first − 0.10: 5.42–5.46 (0.69–0.705) vs 5.49–5.51 (0.65–0.66) |
| Donautal P08 | po+otd, opening −8 % (84890ecf) / −18 % (9b159f07, ff799fbc) / no claims (fbbf38c9) | 5.40/60 db0 / 5.28–5.29/60 db0 / 5.54 | 0.05–0.11, not ours | 4–5 | 5.20–5.28 (0.59–0.68) |
| | falling AS-14404 −5.5 % + PPI-C2431 −2.1 % + po (12 sessions; "not our reality" but verified) | 5.20–5.23/45 db0 (+5.32–5.37/45 db5) ×9; 5.35 single ×3 | 0.05–0.11 | 4–5 | 5.02–5.05 (0.83–0.86) vs 5.07–5.13 (0.74–0.80); walk 769d64fc |
| Ravensteiner P10 | any (cost claim: −0.2) | **final at reply 1**: 33.6–34.0/42d + 31.7–32.1/54d; with fc claim 33.0/42 only (930e2eba) | – | 1 | 31.7/56 (0.663); 33.0/42 (0.617) |
| Kalwisz P11 | any (ppm+po, with/without on-time-payment pledge) | 47.00/300 + 46.50/1500 (13×) or 46.50 + 46.00 (3×) | 0.50 on a "bump", holds otherwise | 4–7 | 45.50 when final@≥6 (6 of 16), 46.00 otherwise; 46.50 after a backward sheet (52716f49) |
| Werdenfels P18 | otd / otd + rival po (irrelevant) / clause sheet in r1 | 5.60 / 5.70 / 5.80 db5 | 0.10 fixed | 4–5 | 5.50–5.70 (0.23–0.36) |
| | falling AS/PPI claims + po, same sheets (12 sessions) | 5.50/90 db0 + 5.50/45 db5 ×7; **5.40 + 5.40** ×5 | 0.10 fixed | 5 | 5.20 db5 (0.63) / 5.10 db5 (0.696) |

What the data shows: (1) for every supplier that moves at all, the deal is the first counter minus a nearly constant descent (Brandlhuber −2.6…−3.2, Leitner −0.10, Donautal −0.15…−0.20, Werdenfels −0.30, Fuchsreiter −1.0…−2.0) and the number of replies before `final_offer` is fixed per supplier (3–5), not stretched by smaller steps on our side. (2) The first counter depends on the number and kind of verified claims (P01: none → 140–143, two → 136–138; P05 Fuchsreiter 32.0 → 30.5 with three; P08 5.54 → 5.28 → 5.20) and barely on our opening price (P01 125–132 all → 137.8; P02 339 vs 358 → 372.55 both; P07 5.15 vs 5.26 → 5.53). Donautal is the one supplier where a deeper opening lowered the counter (−8 % → 5.40, −18 % → 5.28, same claims). (3) Escalation paragraphs, "what would you need", goodwill offers, cost-breakdown questions (refused 12/12) and the forecast claim changed no first counter beyond the ±0.03–0.05 (P07), ±0.1 (P18), ±2 EUR (P01) run-to-run noise; the fc claim in P10 cost the 54-day alternative. (4) Walk-aways: any price below a `final_offer` (4 of 4: fc419f05, 4e73fdf4, cdbf6466, 6fd02e7e); two identical sheets in a row to Donautal (769d64fc); Hrvelec after we cited a rival (61d079be). A package the supplier itself had offered, sent back after its final, was accepted 16 of 16 times (P04 ×3, P07 ×12, P18 ×1).

## Finding 1 - Mirror-with-cap suppliers starve on our reciprocal steps (expected +0.02–0.04 mean)

**Evidence.** Brandlhuber's step equals ours up to a declining cap: ours 1.17/0.60/0.46/0.35 → its 1.3/0.6/0.4/0.3 (a37615af); ours 1.36/1.03/0.78 → 1.3/1.0/0.7 (1e887324); ours 1.68/1.28/1.06 → 1.5/0.5/0.4 (75b0649b, the cap). Leitner: ours 0.05/0.04/0.03 → 0.04/0.04/0.03 (151d1659); ours 0.02/0.03 → 0.02/0.02 (a26d2404); our 0.29 jump → 0.05 (065b4789). Both go final at reply 4–5 whatever the pace. The winners' log saw Leitner step 3.5 %, 2.2 %, 1.1 % (0.19, 0.12, 0.06) against larger moves and closed at ≈5.32 (record 0.779); our best is 5.42. Donautal (0.05–0.11), Werdenfels (0.10), Kalwisz (0.50) step on their own clock regardless of ours.

**Mechanism (inferred).** its_step = min(k·our_step, cap_round), k≈1 for Brandlhuber/Leitner, with a fixed reply budget. With `reciprocity` on, both sides copy the other's last small step and the budget runs out at first_counter − 3 small caps. The lever is the size of our first two or three steps, not more rounds.

**Change** (`policy.py`, `concession`): when the supplier matched our last step, step 1.5× its move, still capped at half the gap.

```diff
@@ def concession(self, case, t, theirs, last):
             if move > tol:
                 t.holds = 0
                 step = min(p["reciprocity"] * move, 0.5 * gap)
+                # mirror-with-cap suppliers (Brandlhuber, Leitner, Dralveck) answer our step with one of the
+                # same size up to a per-round cap and go final after a fixed number of replies: a bigger
+                # step buys a bigger step. If it matched our last step, step 1.5x its move.
+                ours = t.our_prices[-1] - t.our_prices[-2] if len(t.our_prices) >= 2 else 0.0
+                if ours > tol and move / ours >= p.get("mirror_ratio", 0.8):
+                    step = min(max(step, p.get("mirror_gain", 1.5) * move), 0.5 * gap)
```

**Cases.** P01 +0.02 (descent 3.0 → ≈3.7 EUR), P07 +0.04 to +0.15 if Leitner's caps are what the winners saw, P05/P11 ±0.01, P02/P03/P04/P08/P10/P18 unchanged. **Risk.** Our ask can land above the supplier's would-be final when it agrees to our sheet early (Dralveck agreed at our 28.05 while its final is 28.00; Brandlhuber agreed at our 134.60); the 0.5·gap cap limits this to a few tenths of a percent.

## Finding 2 - In stabilise cases our relationship estimate freezes or mirrors our price (P01 +0.015 mean; hidden stabilise cases at risk)

**Evidence.** df366f6a accepted 138.60/45d at round 2 (0.762; the same opening ended 0.86–0.91 elsewhere). d9cfc61a sent 136.49 against its 136.50 (0.848) and 7807fb7a sent 136.89 and 137.30 against its 136.90 (0.800), both at round 2 and both closed there; the same first-counter range otherwise ended 134.6–134.8 (0.905–0.926). The arena's own relationship charge at 133.3 was 10,848 and the deal there scored 0.969 - the best - so the true full cost sits below 130, while the should-cost is 132.64 (learnings).

**Mechanism (inferred from `offer`/`decide`).** With an overstated full cost, `relationship_c` makes a low ask cost us more than the supplier's own price; `same_cost` then lifts our price to its price (mirror), and the "repeated sheet → close" rule plus the relationship floor in `next_price` close the thread at round 2. The suppliers would have conceded 2.6–3.2 EUR more over three replies.

**Change** (`policy.py`): never send a lead price within 0.4 % of its price before its third reply, and never close on a repeated sheet before the third reply.

```diff
@@ def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
-        if prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding:
+        if (prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding
+                and len(t.their_costs) >= 3):
             return self.close(case, t, acceptable, c_theirs, rival_best_c)
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
             if self.c(case, a, t) > c_theirs:  # never ask for more than they already give us
                 a = self.same_cost(case, a, t.standing_terms, t.standard)
+            theirs_p = t.standing_terms["unit_price"]
+            cap = round(theirs_p * 0.996, 2)
+            if a["unit_price"] > cap and len(t.their_costs) < 3:
+                # our C model says its price is already the optimum; the arena's relationship charge is
+                # smaller than ours (P01 d9cfc61a, 7807fb7a): keep walking instead of mirroring its price
+                a = {**a, "unit_price": min(cap, round(t.our_prices[-1] + 0.01 * theirs_p, 2)) if t.our_prices else cap}
```

**Risk.** One extra round on a supplier that was about to go final (none observed going worse after a reply except Nordmark when we asked 90 days). Cap the full-cost estimate in `costing.py` (not shown) at the supplier's own counter divided by (1 + sustainable margin) as well.

## Finding 3 - A repeated or lower lead price reads as "no movement" and triggers hold → final → walk (+0.005 mean; removes a 0-score path)

**Evidence.** Donautal: identical sheets in r4 and r5 → "your options remain unchanged" → `walked_away` (769d64fc, 0); one repeat → final (7976d643). Kalwisz: 46.06 then 45.42 three times → "exact same numbers again" → final 46.50 (52716f49, 0.543 vs 0.63–0.71). Brandlhuber: lead 132.33 then 130.81 → "moved backwards … no upward movement" → holds, final 135.5/136.6 (cac09d93 0.864, 773a42a5 0.842, vs 0.909 for the same opening with monotone leads in 478e95da). Fuchsreiter: "your prices just went backwards" → final (a89c4da). `no_step_back` is keyed per package, and `holding` rotates a cheaper package into the lead, so the headline price still falls.

**Change** (`policy.py`, end of `offer`):

```diff
         sheets = [self.no_step_back(t, s) for s in sheets]
+        # suppliers read the lead price only: it must rise by a visible step every message, whatever package
+        # leads (Donautal walked after two repeats 769d64fc; Kalwisz finalled at 46.50 after a lower lead 52716f49)
+        theirs_p = t.standing_terms.get("unit_price")
+        if t.our_prices and theirs_p and sheets[0].get("unit_price") is not None:
+            lead_floor = round(max(t.our_prices) + 0.003 * theirs_p, 2)
+            if sheets[0]["unit_price"] < lead_floor < theirs_p:
+                sheets[0] = {**sheets[0], "unit_price": lead_floor}
         t.last_sheet = sheets[0]
```

**Cases.** P08 (1 walk in 22), P11 (1 in 16), P01 (2 in 20); hidden cases with the same personas. **Risk.** The 0.3 % token step gives away ≈0.3 % per held round; against the fixed-step suppliers (Werdenfels, Donautal) it changes nothing else.

## Finding 4 - After a final, mirror the best package the supplier ever offered; never re-offer its worse sheet (+0.01 mean)

**Evidence.** Wälzlager offers 4.89/45 in reply 2 but its `final_offer` lists only 4.94/90 in 7 of 10 sessions (b8732e82, f37d2d23, c17314a6, 2bc9926a, b61bfa0b, 0f8fe5fb, de335729 → 0.860); when the final still listed it, sending 4.89/45 back got `agreed` 3 of 3 (0.874). Mirroring the supplier's own alternative after a final was accepted 16/16 times; pricing below a final walked 4/4. Inverse bug: c43e456e sent [5.10/45 db5, 5.21 db5, 5.10 db0] after Werdenfels' final - it picked its own db0 sheet (0.621 vs 0.696 in five sessions that sent the db5 variant alone).

**Mechanism.** `pick_offer` sees only the current message's sheets, so a package withdrawn from the final is forgotten; `close` appends the supplier's own standing sheet, and the supplier chooses the option best for it.

**Change** (`policy.py`):

```diff
@@ class ThreadState:
     clause_countered: bool = False
+    best_offered: tuple | None = None  # (C, sheet_id, terms) cheapest package it ever offered in this thread
@@ def pick_offer(self, case, t):
             c = self.c(case, terms, t)
             if t.alt is None or c < t.alt[0]:
                 t.alt = (c, sheet_id, terms)
+        for sheet_id, terms in t.offers or []:
+            if terms.get("unit_price") is None or not must_haves_ok(case, terms, t.standard):
+                continue
+            c = self.c(case, terms, t)
+            if t.best_offered is None or c < t.best_offered[0]:
+                t.best_offered = (c, sheet_id, terms)
@@ def close(self, case, t, acceptable, c_theirs, rival_best_c):
-        alt = t.alt
+        alt = t.alt
+        if t.best_offered and (alt is None or t.best_offered[0] < alt[0]):
+            alt = t.best_offered  # a package it offered earlier and dropped from its final: sent back, agreed 16/16
@@
-                return Decision("send", t.supplier_id, term_sheets=[*variants, own][:3],
+                return Decision("send", t.supplier_id, term_sheets=(variants or [own])[:3],
```

**Cases.** P04 +0.014 in ~60 % of runs, P18 +0.075 in ~10 %, hidden renewal/bundling/raw-material cases with distributors. **Risk.** A supplier could refuse a withdrawn package and repeat its final; none did in 16 sends, and its final stays acceptable.

## Finding 5 - Round-1 content: three verified claims, nothing else moves the counter; cheap-payment sheets lose money (+0.005 mean, mostly hidden-case protection)

**Evidence.** Claims drive the first counter (table above): P01 none → 140.3/142.9 vs two → 135.5–137.8 (one claim-bank outage cost 0.31 in b4535c94); Fuchsreiter 32.0 → 31.5 → 31.0 → 30.5 as claims grew from 0–1 to 3; Donautal 5.54 → 5.28 → 5.20. Rising-index claims only earn "confirms our case" (P02 c75e3d16). Opening depth: no effect on six suppliers, −0.11 on Donautal for −18 % vs −8 %. Text features (escalation paragraph, open question, goodwill list, forecast claim): first counters inside noise (P07 5.56/5.60 with and without; P01 137.4–137.8), and the fc claim in P10 produced a single 33.0/42 final (0.617 vs 0.663). Payment lever: Dralveck 28.00/14 (0.8136) vs 28.05/30 (0.8186) - 16 days bought 0.18 %, our interest costs 0.36 %; Brandlhuber 134.6/14 (0.909) vs 134.8/30 (0.926); Wälzlager 4.87/14 vs 4.88/30; Fuchsreiter 30.50 at both 14 and 30 d (a89c4da r3). Only Hrvelec and Fuchsreiter's final priced 14 days near 17–38 %/yr.

**Mechanism (inferred).** `ARCHETYPE_RATE["cash_short_jobshop"]=0.18` and `CASH_HUNGRY_RATE=0.15` make the menu price a 14-day sheet 0.8 % below the 30-day one; the supplier adopts the structure at a 0.2 % discount and `agreed` closes it. The forecast claim prompts "which volume can you commit to" and a volume-only counter.

**Change.** Keep `FIRST_MESSAGE_CLAIMS = 3` and the claim-bank retry (done); lower the cash assumption so 14 days is a menu option, never the lead, unless the supplier itself priced faster payment at more than our interest:

```diff
-ARCHETYPE_RATE = {"cash_short_jobshop": 0.18, "group_ladder": 0.07, "near_monopolist": 0.07}
+ARCHETYPE_RATE = {"cash_short_jobshop": 0.10, "group_ladder": 0.07, "near_monopolist": 0.07}
-CASH_HUNGRY_RATE = 0.15
+CASH_HUNGRY_RATE = 0.20  # only a supplier that asked for cash (signals) gets a 14-day lead sheet
```

and keep `forecast_claims` limited to `VOLUME_CASES = ("bundling", "renewal")` as in `claims.py` (the night-v4 branch that added it elsewhere should not be merged). In the writer, nothing to change: the first e-mail's length and paragraphs did not move any counter, so the 140-word cap can stay.

**Cases.** P05 +0.005, P01 +0.017 when the 14-day path fired (3 of 20), P10 +0.046 when fc was cited (1 of 25). **Risk.** A genuinely cash-starved hidden supplier (Hrvelec-like, 17 %/yr) gets a less attractive menu; the menu still contains the 14-day sheet, so it can pick it.

## Not worth touching before the freeze

P02, P03, P04, P10 are table-driven and at their reachable optimum (P02's C_best needs a clause-free ≈363/90 that Nordmark never gave; P03's 429/90 is behind a price freeze; P10 answers once). P11 lands on 45.50 or 46.00 by the supplier's own patience draw (final at reply 6–7 vs 4–5 with identical sheet paths, e.g. 31d63381 vs c006eed3); nothing in our inputs separates the two groups. P18's 5.40/5.50 first counter is likewise a coin flip on identical inputs (5 vs 7). Pushing below any final is a walk, every time.