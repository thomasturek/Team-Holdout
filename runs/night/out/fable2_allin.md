# Bold general changes before the freeze - ranked

**Frame (shown by the data).** In 110+ practice threads the deal is the supplier's own final or agreed sheet; the final comes at a fixed reply (3-5 for job shops/foundries/distributors, 1 for Ravensteiner, 5-7 for Kalwisz) and lands at first-counter minus a per-supplier descent (Brandlhuber -2.6…-3.2, Leitner -0.10, Donautal -0.15…-0.20, Werdenfels -0.30). Three things move that landing: how big our steps are against a supplier that mirrors (fable_ceiling F1), whether we hand it an equal-value cash sheet it can `agree` to before its last step (fable_language F1: lever-trade group 0.90 vs steady group 0.93 on P01), and whether the cheaper structure is on the table when it finals (P10 `930e2e`, 0.617 vs 0.663). Zeros came from counters below a final (4/4), two identical sheets (769d64fc) and timeouts - the first two are closed by `push_final=0` and the merged `VISIBLE_STEP`.

**Inferred:** suppliers fall into three response types visible from their first two moves: *mirror-with-cap* (its step ≈ ours up to a cap: Brandlhuber 0.9, Kalwisz 0.5), *fixed-stepper* (its step constant whatever ours: Donautal 0.05-0.11, Werdenfels 0.10, Leitner ≈0.03 cap) and *table-driven* (holds, finals on its clock, or agrees at any sheet above its floor: Nordmark, Selvbrunn, Wälzlager, Ravensteiner). Only the first type rewards bigger steps; the third punishes a lower ask (it agrees at our price - P02 355.81 scored 0.611 for the relationship charge). Every change below is a rule keyed to that observed pattern, never to a supplier id.

---

## 1. Classify the step pattern from reply 2 and size our step to it (+0.03-0.08 on mirror suppliers, 0 elsewhere)

**Evidence.** `1e887324`: ours +1.44/+1.03/+0.78 → Brandlhuber -1.3/-1.0/-0.7, final 134.8 with 6.2 EUR of gap left; `d5066cc6`: ours +1.08/+0.84/+0.63 → -0.8/-0.8/-0.6, final 133.3 (0.969); `75b0649b`: ours +1.68/+1.28/+1.06 → -1.5/-0.5/-0.4 (the cap). Kalwisz holds 46.0 through four replies while we creep +0.16/+0.27 (`5168ff`, `e1e70f`, `43436f`: 46.0) and drops 0.5 the reply after we move +0.9 (`476b3b`, `273c88` → 45.5). Fixed steppers ignore us: Werdenfels -0.10 against +0.10/+0.06/+0.04 (`62ba92`) or +0.07/+0.05/+0.03 (`13e6c0`); Donautal -0.11/-0.05/-0.05 against +0.03/+0.01/+0.01 (`2f6a0b78`, best P08 0.860 - small visible steps get the most counters from a fixed stepper). Table-driven suppliers' move is 0 (P03, P04) or they agree at any sheet (P02 13/13).

**Mechanism (inferred).** `policy.py::concession` steps `reciprocity × move` (≈1.1× their last step): both sides copy the other's shrinking step and the fixed reply budget runs out above the floor. A mirror supplier lands where our ascent lets it; a fixed stepper lands at first-counter minus its descent whatever we do; a table-driven supplier never moves, so the branch is never entered. The classifier is the ratio of its move to our previous step: inside [0.4, 2.5] it is mirroring (Brandlhuber 0.9, Kalwisz 0.55); outside (Donautal 3.7-5 on tiny steps, Nordmark 0.1) it is not. For a mirror we step the larger of the reciprocal step and 30 % of the remaining gap, but never past where its next step lands (`gap − 1.5·move`) - a sheet above its next price is paid in full (Dralveck agreed at our 28.05, `f08d34`). `DEFAULTS["reciprocity"]` is 0.0 in code; params.json carries ≈1.1 (fable_ceiling) - the default is set here so a missing params.json cannot switch the branch off. The accept gap drops from 1 % to 0.3 %: faster convergence must not make `decide()` accept a standing sheet one reply before the supplier's final (no supplier worsened its offer after a reply except on a backward step, now impossible).

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ DEFAULTS = {
     "floor_margin_pct": 4.0,
-    "accept_gap_pct": 1.0,
+    "accept_gap_pct": 0.3,
     "cash_discount_pct": 1.5,
@@ DEFAULTS = {
-    "reciprocity": 0.0,  # our step per step of theirs (trained: about 1.1)
+    "reciprocity": 1.1,
@@ DEFAULTS = {
     "lever_trades": 1.0,  # > 0.5 = on
     "min_step_pct": 0.0,
+    "mirror_ratio": 0.4,
+    "mirror_frac": 0.3,
+    "mirror_margin": 1.5,
 }
@@ def concession(self, case, t, theirs, last):
             if move > tol:
                 t.holds = 0
                 step = min(p["reciprocity"] * move, 0.5 * gap)
+                ours = t.our_prices[-1] - t.our_prices[-2] if len(t.our_prices) >= 2 else 0.0
+                if ours > tol and p["mirror_ratio"] <= move / ours <= 1 / p["mirror_ratio"]:
+                    step = max(step, p["mirror_frac"] * gap)
+                    step = min(step, max(0.0, gap - p["mirror_margin"] * move))
             else:
```

**Cases.** P01: with first counter 135.5 and ours 128, the path 130.3 → 131.6 → 132.5 reaches the 133 floor region by reply 5 (0.91 → ≈0.95). P11: meeting Kalwisz's 0.5 steps with ≥0.3·gap reaches 45.0 (C 742,132, ≈0.78) in the sessions where it drops at all (0.67 mean → ≈0.74). P07: +0.02 only if Leitner's 0.03 cap is soft (`121a69` says it is not). P08/P18: the cap `gap − 1.5·move` keeps us below their next landing; same finals (worked through for Werdenfels 5.50 → 5.20: identical deal). P02/P03/P04/P10: branch never entered. P05: Dralveck agrees at our sheet once it crosses its floor; the cap limits overshoot to ≤0.05 (0.005).

**Risk.** Overshoot on a supplier that agrees at our price before finalling (observed only on Dralveck, ≤0.05). No walk risk: no supplier walked on a bigger step; walks came only from counters below a final and identical repeats.

---

## 2. Cash levers only in the endgame: an equal-value 14-day sheet freezes the price (+0.03 P01; hidden cash-short suppliers)

**Evidence.** Brandlhuber writes "faster payment is welcome" in every reply; the reader turns it into `asks: faster_payment`, `lever_trades` prices a 14-day sheet at equal C to our 30-day one, and the thread ends: `9c0ba9cd`, `38367dc0` r4 134.60@14 → agreed 0.909; `934ed1e9` 134.70@14 → 0.905; `6d1edc5d` r3 135.29@14 → 0.875; `478e95da` r3 → 0.909. Steady 30-day stepping: `d5066cc6` 0.969, `1e887324`/`36af37af` 0.926, `a37615af` 0.911. Group means 0.90 vs 0.93. The discount it grants for 14 days (≈0.65 %) barely exceeds our interest (0.36 %); Dralveck 28.00/14 (0.8136) vs 28.05/30 (0.8186) and Wälzlager 4.87/14 vs 4.88/30 say the same. The menu does it too: `ARCHETYPE_RATE["cash_short_jobshop"]=0.18 ≥ CASH_HUNGRY_RATE` makes `menu()` keep 14/30-day sheets that cost us 0.7-1.0 % at the supplier's price.

**Mechanism (inferred).** The bot accepts any sheet worth at least its standing offer to it; an equal-value trade freezes the price at the current step and forfeits the 2-3 scripted steps left. In the endgame (it has finalled, holds twice, or rounds run out) the same trade is pure gain, so the lever stays available there.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def flat_replies(t, tol=1.0):
         return n
 
+    @staticmethod
+    def endgame(t):
+        return t.rounds_left <= 2 or t.status == "final_offer" or t.holds >= 2
+
     def at_target(self, case, t, c_theirs):
@@ def menu(self, case, t, a, c_cap):
         rel_case, rel_floors = relationship_case(case) and floor_binds(t), {}
-        cash_hungry = model["interest_rate"] >= CASH_HUNGRY_RATE
+        cash_hungry = model["interest_rate"] >= CASH_HUNGRY_RATE and self.endgame(t)
         found = []
@@ def lever_trades(self, case, t, a, asks=()):
         for v in lever_values(case, a, t.standard, t.profile):
             if not v["must_haves_ok"]:
                 continue
+            if v["field"] in CASH_LEVERS and not self.endgame(t):
+                continue
             sheet = self.above_floor(case, t, complete_offer(case, v["sheet"]))
```

**Cases.** P01 +0.03 mean (the 14-day accept path fired in 5 of 20). P05 ±0 (Dralveck's own final is 28.00/14 anyway). P02's clause trade is structural and untouched. Hidden cash-short job shops and any supplier whose reply says "faster payment helps" (the kit's own P01 example reply).

**Risk.** A supplier that values cash far above our 8 % (Hrvelec 17-38 %/yr) gets the 14-day sheet two rounds later than before; it still gets it before we close. No walk path touched.

---

## 3. Always carry the supplier's own lead time on a sheet (capacity cases: +0.02-0.05 P10; Hrvelec-type bidders)

**Evidence.** Ravensteiner finals at reply 1 in 25/25 sessions; its 54/56-day alternative is worth 0.046 (31.7@56 = 0.663 vs 33.6@42 = 0.617: it charges 1.9/unit = 88,920 for the faster lead against our 33,600 of late cost). In `930e2e` the reply carried no 54-day alternative and our only sheet was 42 days → 0.617. Hrvelec prices 31.50@52 / 33.00@42 / 34.50@35; `9bd523d1` answered our open question with a 14-day alternative, i.e. the bots price the structures we put on the table plus their own when they feel like it.

**Mechanism.** `best_options` picks the lead time cheapest for us at zero late cost (42), `menu()` never produces the longer one (its `lead_effort` of 0.001·price/day keeps it outside `MENU_SPREAD`), and `adopt_structure` only adopts a structure the supplier already offered. In round 1 nothing has been offered.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@
-from arena_kit.cost import complete_offer, must_haves_ok, supplier_value, total_cost
+from arena_kit.cost import complete_offer, must_haves_ok, snap, supplier_value, total_cost
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
         sheets = self.menu(case, t, a, c_cap) or [a]
+        leads = [x for x in (t.standing_terms.get("lead_time_days"), (t.standard or {}).get("lead_time_days")) if x]
+        if "lead_time_days" in case["negotiable"] and leads and max(leads) > (a.get("lead_time_days") or 0):
+            own_lead = complete_offer(case, {**a, "lead_time_days": snap(case, "lead_time_days", max(leads))})
+            own_lead = self.above_floor(case, t, self.same_cost(case, own_lead, a, t.standard))
+            if (own_lead["lead_time_days"] != a["lead_time_days"] and own_lead not in sheets
+                    and must_haves_ok(case, own_lead, t.standard)):
+                sheets = [sheets[0], own_lead, *sheets[1:]]
         if t.last_sheet is not None and sheets[0] == t.last_sheet:
```

**Cases.** P10: 0.617 → ≈0.71 in the runs where the alternative vanished (33.0 − 1.9 ≈ 31.1@56, C 1,504,100); otherwise unchanged (it already volunteers 54 days). P05: Hrvelec's 52 days breaks the ≤42 must-have → filtered; Dralveck/Fuchsreiter quote ≤42 → no extra sheet. Hidden capacity/RFQ cases with full suppliers (P09 quotes 42 vs our 28: the sheet is sent at equal C and the supplier reveals what speed costs it).

**Risk.** None on price (`same_cost` keeps our C; `above_floor` keeps the relationship floor); the sheet is second, so Option A stays our structure.

---

## 4. Never put the supplier's own package beside our clause variant - second branch of `close()` (+0.015 P18 mean, free)

**Evidence.** `c43e456e`: Werdenfels' final 5.20@90 db0 / 5.10@45 db0; we sent [5.10 db5, 5.21 db5, 5.10 db0]; it "accepted Option C, which perfectly matches our final offer" → 0.621 vs 0.696 in five sessions that sent the db5 sheet alone (`13e6c049`, `c80f8b2a`, `783dd48d`, `c50dad81`). The deadband is worth 5,439 EUR at the same price (index_clause 6,527 vs 1,088 in the breakdowns). The merged fix covers the first branch (`variants[:1] or [sheet]`); the second branch (status `open`, acceptable, clause variants) still sends `[*variants, own]`.

**Mechanism.** The supplier chooses freely among our sheets by its own value; db0 beats db5 for a seller every time. The second branch runs while the thread is `open`, where no counter has ever triggered a walk (walks: 4/4 below a final, 0/50+ open counters), and its standing sheet stays acceptable if it merely repeats itself.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def close(self, case, t, acceptable, c_theirs, rival_best_c):
-                return Decision("send", t.supplier_id, term_sheets=[*variants, own][:3],
+                return Decision("send", t.supplier_id, term_sheets=variants[:3],
                                 intent="appreciative: we can agree to your offer; we would prefer it with a wider "
                                        "index deadband")
```

**Cases.** P08/P18 whenever we would close on a db0 sheet while open (≈1 in 5 P18 closes: +0.075 each); hidden raw-material cases (P14, P16 structures). **Risk.** It repeats its sheet or finals at it: we accept, same score as before.

---

## 5. Writer: remove the sentences that draw a scripted proof demand (hidden RFQ and bundling cases; practice ≈0)

**Evidence (shows).** ~40 supplier replies ask "which figures is that based on? please send the data", and in each the supplier did not move that round. Triggers: PLAYBOOK `rfq` prose "the award goes to the best package" → Dralveck `45a8c2e4`/`c15e7332` "send me the proof", Fuchsreiter `3871f28a` "without proof I can't drop the price" (30.50 hold) - while a verified rival **claim** in the same round moved Fuchsreiter every time (`891fdbdf` 30.5 → 30.0/29.5, `25a4b54b`); PLAYBOOK `bundling` "business on top of what you supply today" → "please provide the exact volume figures" (`5b71599f`, `121a69f6`, `fc419f05`); the `volume_line` repeated every round → 12 "data supporting this projection" loops (P07/P18/P04/P11). Prose otherwise does not buy price (P03 nine sessions at 0.9351 to four decimals; bare templates gave our best P07 `bdeae9d4` and P18 `13e6c049`), so shorter later e-mails lose nothing.

```diff
--- a/src/buyer/llm/writer.py
+++ b/src/buyer/llm/writer.py
@@ PLAYBOOK = {
-    "bundling": "This is a bundle: the options move more of our parts to this supplier. Its gain is volume and steady "
-    "load for its plant - say that the bundle is business on top of what it supplies today (the volume line under the "
-    "options states it) and that Option A secures it.",
+    "bundling": "This is a bundle: the options put the whole kit under one agreement with this supplier. Its gain is "
+    "one steady, planned load; the volume line under the options states it. Never call it additional or new business "
+    "and never estimate what it supplies today - it asks for figures.",
@@ PLAYBOOK = {
-    "rfq": "Several bidders compete: state plainly that the award goes to the best package, without promising it.",
+    "rfq": "Several bidders compete. Mention competition only in the sentence that introduces a rival [[CLAIM_n]]; "
+    "with no such claim listed, say nothing about other bidders - it asks for proof and holds.",
 }
@@ def volume_line(case, decision, signals=None, thread=()) -> str:
     first = not any(m.get("from") == "buyer" for m in (thread or []))
-    if not (asked or (first and attr(case, "type") in VOLUME_TYPES)):
+    already = any("Binding volume in every option" in str(m.get("body") or "")
+                  for m in (thread or []) if m.get("from") == "buyer")
+    if already or not (asked or (first and attr(case, "type") in VOLUME_TYPES)):
         return ""
```
```diff
--- a/src/buyer/llm/prompts/writer_system.md
+++ b/src/buyer/llm/prompts/writer_system.md
@@
-- Your own words: at most 140 in a first e-mail, at most 90 later; the inserted blocks do not count. Every sentence must earn its place.
+- Your own words: at most 140 in a first e-mail, at most 60 later; the inserted blocks do not count. Every sentence must earn its place.
```

**Cases.** Hidden RFQs where a Fuchsreiter-type bidder is cheapest (+0.02-0.05 when the proof hold is the round it would have stepped), hidden bundling (P15-type). **Risk.** None: fewer sentences, same term sheets.

---

## Checked and deliberately not changed

- **Keepalives to an agreed bidder while a rival still steps** (fable_rules #4): untested whether the bot keeps `agreed` after a non-accepting message, and the agreed thread's 60-s clock keeps running under the arena's per-session serialisation (3 bidders: 44 s between our messages, 66 s at p90). Three timeouts end the thread - a path to zero on the one bidder we know we can close. Not before the final.
- **Re-offering a package the supplier withdrew from its final** (`best_offered`, fable_round1 #4): the 16/16 acceptances were of packages still listed; a withdrawn one at a lower price than the final has never been sent. Gain ≤0.014 on P04. Not worth a possible walk.
- **Forecast claim in every case type**: n=1 each way (P01 136.9 vs P10's lost alternative). Finding 3 removes the downside, but the upside is inside first-counter noise.
- **Pushing a final** (4/4 walks), **deeper anchors** (no first-counter effect on six suppliers; Dralveck walked at a 39 % cumulative gap), **table-driven suppliers** (P02/P03/P04/P10 at their reachable optimum; our price path is irrelevant to them unless we go lower, which Nordmark then agrees to at a relationship charge).
- **Runtime**: accepts never call the model (`to_message` returns the action), the writer runs under a 23-s deadline, the hold message goes at 48 s. The 01:38 timeout batch was the hung resend loop set aside in the night log; nothing in this patch touches the per-move path.

---

## Test plan: 20 sessions, then freeze

P01 ×4, P11 ×4 (the mirror cases - the bands to beat: 0.80-0.93 and 0.63-0.71), P07 ×2, P10 ×2, P08 ×2, P18 ×2, P05 ×2, P02/P03/P04 ×1 each (deterministic to four decimals: any change there is a bug). Promotion rule: no zero, P02/P03/P04 unchanged, P01 and P11 means above their baseline bands; one lucky run does not count.

| Case | Baseline band | F1 | F2 | F3 | F4 | Expected |
|---|---|---|---|---|---|---|
| P01 | 0.80-0.97 (mean 0.91) | +0.03 | +0.03 | - | - | ≈0.95 |
| P02 | 0.7345 | 0 | 0 (clause trade structural) | - | - | 0.7345 |
| P03 | 0.9351 | 0 | 0 | - | - | 0.9351 |
| P04 | 0.860/0.874 | 0 | 0 | - | - | unchanged |
| P05 | 0.814-0.819 | ±0.005 | 0 | 0 (must-have filters Hrvelec) | - | ≈0.82 |
| P07 | 0.65-0.705 | 0 to +0.02 | 0 | - | - | ≈0.68 |
| P08 | 0.74-0.86 | 0 (fixed stepper, capped) | 0 | - | +0.01 | ≈0.80 |
| P10 | 0.617-0.663 | 0 | 0 | +0.03 (fc runs) | - | ≈0.66-0.71 |
| P11 | 0.63-0.71 | +0.05 | 0 | - | - | ≈0.74 |
| P18 | 0.62-0.70 | 0 | 0 | - | +0.015 | ≈0.68 |

Practice mean ≈ 0.78 → 0.80-0.81; the hidden-case value sits in the general rules behind F1-F3 (any family firm or owner that mirrors, any supplier that asks for faster payment, any full supplier that prices speed) and in the zero paths that stay closed.