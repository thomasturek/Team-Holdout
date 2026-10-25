# How a team averages 0.83 - and what our data says is attainable

## 0. The frame (what the digest shows)

Score is decided almost entirely by the **supplier's final price**, not by our last sheet: in 110+ threads the closed price is the supplier's standing or alternative sheet (we accept it); the supplier declares `final_offer` at its 5th-6th reply in every case except P10 (1st) and P05 (3rd). Structural levers are already priced to a wash by the bots:

- Payment days: suppliers' implied rates equal ours (Leitner 5.57@90 vs 5.51@45 = 8.7 %/yr, `f1bbfe`; Wälzlager 4.94@90 vs 4.89@45 = 8.1 %; Donautal 5.22@14 vs 5.25@45 = 6.7 %, `08407e`). Exceptions, both used already: Dralveck values 14 days at 0.5 EUR (28.0@14 vs 28.5@30, `0af6f2` vs `a89c4`); Nordmark/Selvbrunn below 8 % so 90 days wins (P02, P03).
- Index deadband: Donautal and Werdenfels price db5 at +0.12 over db0 (5.02 db0 / 5.14 db5, `2f6a0b`), i.e. 2.3 % = 0.45 x 5 %: exactly our cost.py difference. Wash.
- Contract months, volume: no C effect beyond the horizon (P03/P04/P07/P08/P10/P18 at 24 or 36 give identical breakdowns); P03 5,496 units costs ~780k of unneeded units; P10 volume is pinned by the must-have.
- ppm/chargeback (P11): Kalwisz prices chargeback 500 at +1.5 to +2.5 (48.5 vs 46.5, `5c6ad7`); it saves us 2,146. 300 ppm costs +0.5 and saves 0.54/unit. Wash.
- Effective date (P01): Apr at 137.8 and Jan at 134.8 differ by 2.6k; Apr wins and every final was Apr.

So terms are exhausted; what is left is (i) the price path, (ii) not throwing deals away. Per-case ceilings with the suppliers as observed (c_open/c_best/breakdowns, cost.py):

| Case | Our range | Best seen (terms) | c_best decodes to | Would the bot plausibly give it? |
|---|---|---|---|---|
| P01 | 0.80-0.97 | 0.969: 133.3@30, Apr (`d5066c`) | ~133.0@30 (relationship charge rises below) | yes, when steps are large (Finding 1) |
| P02 | 0.73 | 0.735: 361.72@90, CU db5 | unexplained; fitted full cost 367.6, rate 6.6 % (two breakdowns `cda592`, `e560d6`) put the optimum at 361-362@90 db5 = our deal | no further room |
| P03 | 0.93 | 0.935: 431.63@90 | 429.4@90 | never offered; 90 d is the only lever |
| P04 | 0.86-0.87 | 0.874: 4.89@45 | 4.88@45 | at ceiling |
| P05 | 0.81-0.82 | 0.819: 28.05@30; 0.828 last year 27.86@14 | 26.5@60 | no: Dralveck agrees at >=28.05 (`f08d34`, `a89c4`), finals at 28.0@14 |
| P07 | 0.65-0.70 | 0.705: 5.42@45 | 4.99@60 | no; record 0.779 = 5.32-5.36 (Finding 1, uncertain) |
| P08 | 0.74-0.86 + one 0 | 0.860: 5.02@45 db0 | 4.89 db0 / 5.03 fixed | first counter 5.20-5.35 is random, final = first - 0.2 |
| P10 | 0.62-0.66 | 0.663: 31.7@56, 36 m | 28.1@42 | no: final at reply 1; 56 d beats 42 d by 0.046 |
| P11 | 0.63-0.71 | 0.710: 45.5, 300 ppm, 0 cb | 43.9 with cb 500 | 45.0 plausible (Finding 1); record 0.807 = 44.9 |
| P18 | 0.62-0.70 | 0.696: 5.1@45 db5 | 4.64 db5 | no: 0.1 per reply, final at reply 5; record 0.677 |

Sum of ceilings reachable with the observed bots: mean ~0.80-0.81. **Inference:** 0.83 needs first counters below any we saw (P08 record needs 4.97 db0; our lowest first counter 5.20); our 20+ round-1 variants (anchor, claim set, text, questions) did not move P02/P08/P18 first counters beyond +/-0.1 noise. So the honest target for today is the ceiling column plus removing zeros.

## Finding 1 - Size our step to the supplier's reciprocity (P01, P11, maybe P07): +0.05 / +0.08 / +0.03

**Evidence (data).** Brandlhuber mirrors our step and never reaches the gap: `1e8873` ours +1.44, +1.03, +0.78 -> it -1.3, -1.0, -0.7, final 134.8 with 6.2 EUR gap left; `d5066c` ours +1.08, +0.84, +0.63 -> it -0.8, -0.8, -0.6, final 133.3. Both finals at its 5th reply. Kalwisz holds 46.0 through four replies while we creep +0.16/+0.27 (`5168ff`, `e1e70f`, `43436f`: final 46.0) and drops 0.5 the reply after we move +0.9 (`476b3b`, `273c88` 44.91 -> 45.5; `54e206`, `2dc0e6`, `31d633`: ours reaching 44.4 -> 45.5). Leitner: ours +0.05/+0.04/+0.03 -> it -0.04/-0.04/-0.03 (`151d16`), +0.05/+0.05/+0.04 -> -0.03/-0.03/-0.04 (`f1bbfe`), but +0.07/+0.05/+0.04 -> -0.03/-0.02/-0.03 (`121a69`): a cap near 0.03. Fixed steppers ignore us: Werdenfels -0.1 per reply whether ours is +0.10/+0.06/+0.04 (`62ba92`) or +0.07/+0.05/+0.03 (`13e6c0`); Donautal -0.11/-0.05/-0.05 against ours +0.03/+0.01/+0.01 (`2f6a0b`).

**Mechanism (inference).** params.json runs `reciprocity` ~1.1, so both sides mirror each other and the exchange decays geometrically before the supplier's 5th reply. For a mirroring supplier the landing point is `theirs - r*(our ascent)`; our ascent is the lever. For fixed steppers nothing changes except overshoot risk, so the rule must be conditional on a measured ratio and capped below where the supplier will land next (Dralveck agreed at 28.05/28.06 when our sheet crossed its floor, `a89c4`, `f08d34` - a sheet above the supplier's next price is paid in full).

**Change** (`policy.py`, `concession`):

```diff
@@ DEFAULTS = {
     "lever_trades": 1.0,  # > 0.5 = on
     "min_step_pct": 0.0,
+    "mirror_ratio": 0.4,  # its step / our step from which we treat it as mirroring
+    "mirror_frac": 0.3,   # then our step is at least this share of the remaining gap
 }
@@ def concession(self, case, t, theirs, last):
             if move > tol:
                 t.holds = 0
                 step = min(p["reciprocity"] * move, 0.5 * gap)
+                ours = t.our_prices[-1] - t.our_prices[-2] if len(t.our_prices) >= 2 else 0.0
+                if ours > tol and move / ours >= p["mirror_ratio"]:
+                    # it lands where our ascent lets it (Brandlhuber 0.9, Kalwisz 0.5): walk faster,
+                    # but stay below where its next step will land, or it agrees at our price
+                    step = max(step, p["mirror_frac"] * gap)
+                    step = min(step, max(0.0, gap - 1.5 * move))
             else:
```

**Cases / expected.** P01 0.91 -> ~0.96 (lands at the 133 floor by reply 5); P11 0.67 -> ~0.78 (meeting 45.0: C 742,132); P07 +0.03 only if Leitner's 0.03 cap is soft (one contrary run `121a69`). Hidden cases: any family firm / owner persona that mirrors. Fixed steppers unaffected (ratio < 0.4).

**Risk.** Overshoot against a supplier that agrees at our price (cap above); no walk-away risk seen from bigger steps (Dralveck walked at a 39 % cumulative gap from a *lower* anchor, night log, not from faster closing). Kalwisz walked only when we countered a final (`cdbf64`).

## Finding 2 - Two guards that delete zeros and freak closes: +0.02 mean, more on hidden cases

**Evidence (data).** `769d64` (P08): rounds 4 and 5 sent the identical set [5.05@90, 5.02@60, 5.01@45] after Donautal had come down to 5.05@45 db0 (our lead price); its reply: "your options remain unchanged ... withdrawing" -> score 0 against 0.826 for accepting the same offer in `7976d6`. `55d090` got the same complaint ("options remain unchanged and still exclude the index clause") and finalled instead of walking: the resend is the trigger, the outcome is a coin. `7807fb` (P01): round-2 lead sheet 136.89@30 / 137.3@30 after a round-1 ask of 125.45 - a jump of the whole gap - and the supplier "agreed" at 137.3 (0.80 vs 0.91-0.97 elsewhere). The jump comes from `same_cost(a, standing_terms)` after `adopt_structure` took its Jan sheet (134.2@Jan costs the same C as 137.3@Apr).

**Mechanism.** `decide()` only closes a repeated sheet when `not t.holding`, but `offer()` sets `holding` precisely when the sheet repeats; and no rule bounds how far one round may move our lead price.

**Change** (`policy.py`):

```diff
@@ def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
         prev = t.last_sheet
         decision = self.offer(case, t, self.next_price(t, theirs, case=case), rival_best_c=rival_best_c)
-        if prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding:
+        lead = decision.term_sheets[0]
+        matched = lead.get("unit_price") is not None and theirs <= lead["unit_price"]  # it is at our price
+        if prev is not None and lead == prev and acceptable and (matched or not t.holding):
             return self.close(case, t, acceptable, c_theirs, rival_best_c)
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
         if t.standing_terms.get("unit_price") is not None:
             c_theirs = self.c(case, t.standing_terms, t)
             if self.c(case, a, t) > c_theirs:  # never ask for more than they already give us
                 a = self.same_cost(case, a, t.standing_terms, t.standard)
+        theirs = t.standing_terms.get("unit_price")
+        if t.our_prices and theirs is not None:  # one round never jumps more than half the remaining gap
+            cap = t.our_prices[-1] + 0.5 * max(0.0, theirs - t.our_prices[-1])
+            if a["unit_price"] > cap:
+                a = {**a, "unit_price": round(cap, 2)}
```

**Cases / expected.** P08: 1 walk in 12 sessions -> +0.07 on its mean; P01: one 0.80 run -> +0.01 mean. In hidden cases with cheaper structures in a supplier's second sheet (Jan dates, clauses, longer lead times) the jump bug fires more often than in practice.

**Risk.** None observed: the guard only accepts what we already deemed acceptable, and the cap keeps a slower walk that every supplier tolerated.

## Finding 3 - Capacity cases: always carry the supplier's own lead time on a sheet (P10): +0.02-0.05

**Evidence (data).** Ravensteiner finals at its first reply in 25/25 sessions. Its 54-day alternative is worth 0.046: 31.7@56 (late 14 d x 2,400 = 33,600) scores 0.663 against 33.6@42 0.617 - it charges 1.9/unit (88,920) for the faster lead. In `930e2e` the forecast claim lowered the 42-day price to 33.0 ("volume change data ... we took it into account") but the reply carried no 54-day alternative, and our only sheet was at 42 days -> 0.617. In 24 other sessions it volunteered "Alternatively, with Lieferzeit 54 days".

**Mechanism (inference).** The bot prices the structures we put on the table plus its own standard when it feels like it. With one 42-day sheet the cheaper structure can vanish. `menu()` never produced a 56-day sheet (lead_effort pricing kept it outside MENU_SPREAD).

**Change** (`policy.py`, `offer`, after `sheets = self.menu(...) or [a]`):

```diff
-from arena_kit.cost import complete_offer, must_haves_ok, supplier_value, total_cost
+from arena_kit.cost import complete_offer, must_haves_ok, snap, supplier_value, total_cost
@@
         sheets = self.menu(case, t, a, c_cap) or [a]
+        std_lead = t.standing_terms.get("lead_time_days") or (t.standard or {}).get("lead_time_days")
+        if "lead_time_days" in case["negotiable"] and std_lead and std_lead > (a.get("lead_time_days") or 0):
+            # its own lead time, priced at equal cost to us: the cheaper structure stays on the table
+            own_lead = complete_offer(case, {**a, "lead_time_days": snap(case, "lead_time_days", std_lead)})
+            own_lead = self.above_floor(case, t, self.same_cost(case, own_lead, a, t.standard))
+            if must_haves_ok(case, own_lead, t.standard) and own_lead not in sheets:
+                sheets = [sheets[0], own_lead, *sheets[1:]]
```

**Cases / expected.** P10 0.617 -> ~0.71 in forecast-claim runs (33.0 - 1.9 = 31.1@56: C 1,504,100); otherwise unchanged. Hidden capacity/RFQ cases with full suppliers (Hrvelec charges 31.5@52 / 33.0@42 / 34.5@35).

**Risk.** A 56-day sheet breaks P05's must-have (<= 42): `must_haves_ok` filters it. No price risk: `same_cost` keeps our C.

## Finding 4 - At a close with clause variants, do not resend the supplier's own package (P18): +0.004 mean, free

**Evidence (data).** `c43e45`: Werdenfels' final 5.2@90 db0 / 5.1@45 db0; we sent [5.1 db5, 5.21 db5, 5.1 db0]; it "accepted Option C, which perfectly matches our final offer" -> 5.1 db0, index cost 6,527 vs 1,088: 0.621 against 0.696. Where we sent db5 alone at its price it agreed: `13e6c0`, `c80f8b`, `783dd4`, `990f4b` (5.3@45 db5 after a 5.3 db3/db5 final). 

**Change** (`policy.py`, `close`, first branch):

```diff
-                return Decision("send", t.supplier_id, term_sheets=[*variants, sheet][:3], intent=intent)
+                return Decision("send", t.supplier_id, term_sheets=(variants or [sheet])[:3], intent=intent)
```

**Risk.** A counter after `final_offer` can trigger a walk (4/4 when the price moved); 2/2 same-price structure counters were accepted. Leave the second (status `open`) branch as is.

## Finding 5 - Cite the forecast claim in every case type: +0.01-0.02 on P01/P10-type cases

**Evidence (data).** Every supplier that saw `fc:` verified it and "took it into account": P01 first counter 136.9 (`7807fb`) against 137.8 in nine other 3-claim runs; P10 33.0 (`930e2e`) against 33.6; P03, P07, P11 neutral. The night-v4 batch looked mixed (75.7) because `7807fb` hit the jump bug and `930e2e` lost the 54-day sheet - both fixed above. `claims.py` returns forecast claims only for bundling/renewal.

**Change** (`claims.py`):

```diff
 def forecast_claims(data: CaseData) -> list[Claim]:
     """Growth in our forecast for a part: more business for a supplier that wants volume."""
-    if data.case.get("type") not in VOLUME_CASES:
-        return []
     out = []
```

**Risk.** It invites "Which volume can you commit to?" (152 such asks already); `volume_line` answers it. No contradiction seen (figure is the data's own).

## What the data does not support

- Deeper anchors or more claims do not lower first counters for distributors or groups: P08 5.20-5.35 and P18 5.4-5.6 with identical round-1 sheets and claims; P02 instant agreement at any ask with the db5 clause (`cda592` 355.81 scored 0.61 because the relationship charge rose to 61k).
- Pushing a final offer: 4/4 walked (`fc419f`, `4e73fd`, `cdbf64`, P18 `6fd02e`).
- P05: a second-round ask near 27.8@14 could pick up ~0.015 (last year's 27.86 agreement) but Dralveck's 28.0@14 final is its floor region; c_best 26.5 is never on offer.
- Inferred mechanism for the leaders' 0.83: lower first counters we cannot reproduce; a fraction of their edge is luck in the +/-0.1 first-counter noise over single plays (our P08 alone spans 0.74-0.86 on identical inputs).

Expected after Findings 1-5 on the ten practice cases: ~0.80-0.81 mean, with the zero-removal guards worth more on hidden cases than here.