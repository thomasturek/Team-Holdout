# Policy walk-through of the 21 case files - findings, ranked

Method: every case file in `runs/cases/practice.json` and `sandbox.json` was walked through `agent._state → Policy.decide → next_price → offer → best_options/adopt_structure → menu/lever_trades → close/closing`, and `cost.py` arithmetic was done by hand for the levers. "Shows" = in the files/digest; "infer" = my reading.

## 0. What holds (checked, no change)

- **Sheets are complete and snapped**: `complete_offer` fills every `negotiable` field from standing → plan → `options[0]`; `index_clause: null` survives because `None in options`. Every case's negotiable non-price field has `term_options` (P06 tooling, P12 lead, D02 incoterm, P09/P17 volume).
- **Must-haves at accept**: `eligible_cost` runs `must_haves_ok(standing, standard)` before `accept`/`closing`; `best_options` filters options per field, `menu` and `lever_trades` filter sheets. Hrvelec's 52-day sheet (P05) is never accepted; P10's volume option 23400 is forced.
- **Costly structures avoided**: P03 volume 5,496 ×2 y = 1,832 unneeded units × 424.61 = €778k - `best_options` picks the need; contract 12 m on a 2-year horizon leaves half the need uncovered at fallback +10 % - it picks 24/36; P16 deadband 3 vs 5 at path +3 % cost us the same (index_risk 0.8 % of spend only) while the supplier values db3 1.6 pp more (`0.8 × (6.5−3)` vs `(6.5−5)`) - all three option pickers take the first tie (db3) ✓; P13 April start saves ≈ 0.25 × 17,900 × 1.14 ≈ €5.1k ✓.
- **Alternatives**: P12 current contract = 899,257 + 2,997 (45 d) + 4,622 (4,118 ppm, cb 150) = €906,876; a quote at 100.14/2,500 ppm/cb 0 costs 908,428 → correctly *not* acceptable (walk = alternative is the right score). P09 alternative 16.33 @ 56 d: 254,748 + 849 + 2,496 freight + 50,400 late + 800 + 1,376 = €310,669 (it breaks the case's own must-have; harmless as a ceiling). D01 (`alternative` without `terms`), D02 (`current_unit_price: null`, no `effective_date`) do not crash: `alt.get("terms", {})`, `_units_before` returns 0.
- **Unknown suppliers/parts**: `scout_profiles` and `profile()` degrade to `{}`; `floor_ask` uses `theirs × 0.85`; the claim bank is retried and never cached empty.

## 1. A final that breaks a must-have or sits above our alternative walks at once - no repair counter (zero path, capacity/quality/secure_supply cases)

**Shows.** `decide`: `if t.status == "final_offer": ... return self.close(...)`; `close` ends with `return self.accept(t) if acceptable else Decision("walk", ...)`. `acceptable` is false when the standing sheet breaks a must-have or its C exceeds `alternative_cost`. P10's supplier finals at its *first* reply in 25/25 sessions (fable_round1 table) and the case is literally "Ravensteiner cuts the seal allocation" with options 16,379/19,890/23,400 and must-have ≥ 22,230; P09 (never played, Obermaier "is full") has lead options up to 49 with must-have ≤ 42 and `late_cost 1,800/day`; P05 Hrvelec offers 52 days. No alternative in P05/P06/P10/P14/P17: a walk scores **0** (P10 deal at 33.0/42 = 46,800 × 33 = €1.54M scored 0.617; walk 0.000).

**Infer.** A hidden full supplier that finals on its reduced allocation or its standard lead time ends the case at 0. A structural counter at its own price was accepted 2/2 and its own packages 16/16 (fable_ceiling F4); only price cuts under a final walked (4/4). When our only other move is a walk, a counter costs nothing: if it walks, the score is what walking gives.

**Change** (`policy.py`):

```diff
@@ def close(self, case, t, acceptable, c_theirs, rival_best_c):
+        if not acceptable and t.rounds_left > 1 and not t.pushed_final and c_theirs <= rival_best_c:
+            repaired = self.repair(case, t)
+            if repaired is not None:
+                t.pushed_final = True
+                t.our_prices.append(repaired["unit_price"])
+                t.our_costs.append(self.c(case, repaired, t))
+                return Decision("send", t.supplier_id, term_sheets=[repaired],
+                                intent="appreciative: we take your package as it stands, with one term adjusted")
         alt = t.alt
@@ def clause_variants(self, case, t, sheet):
+    def repair(self, case, t):
+        own = complete_offer(case, dict(t.standing_terms))
+        sheet = dict(own)
+        for m in case["buyer"].get("must_haves", []):
+            f = m["field"]
+            if f not in case["negotiable"] or must_haves_ok(case, sheet, t.standard):
+                continue
+            ok = [o for o in (case.get("term_options") or {}).get(f) or []
+                  if must_haves_ok(case, {**sheet, f: o}, t.standard)]
+            if ok:
+                sheet[f] = min(ok, key=lambda o: abs(o - sheet[f])
+                               if isinstance(o, int | float) and isinstance(sheet.get(f), int | float) else 0)
+        if not must_haves_ok(case, sheet, t.standard):
+            return None
+        cap = alternative_cost(case) * (1 - self.p["accept_gap_pct"] / 100)
+        c = self.c(case, sheet, t)
+        if c <= cap:
+            return sheet if sheet != own else None
+        slope = self.c(case, {**sheet, "unit_price": sheet["unit_price"] + 1}, t) - c
+        if slope <= 0:
+            return None
+        price = round(sheet["unit_price"] - (c - cap) / slope, 2)
+        return {**sheet, "unit_price": price} if price > 0 else None
```

**Affects.** P05 (Hrvelec thread), P09, P10, P12, any hidden capacity/quality case; RFQ threads with a cheaper rival are untouched (`c_theirs <= rival_best_c`). **Expected.** Turns some 0s into 0.6-0.7 (P10 type); otherwise identical. **Risk.** None on score (walk = same outcome); one extra round. Test: P10 on the sim with a reduced-volume final; P12 variant on the sim.

## 2. `agent._state` can raise on an unreadable quote PDF or a thread without a sheet - two raises drop the thread (zero path)

**Shows.** `agent.py _state`: `sheet_id, terms = standing(events)` and `t.standard = standard_terms(events) or t.standard` are unguarded; `ThreadState(sid, sheet_id, terms, ...)` then calls `terms.get(...)` in `decide`. `threads.py _worker`: `except Exception: failures += 1 ... if failures >= MAX_FAILURES (2): drop`. The EHL learnings (same starter kit) report exactly this: "A quote line the kit's parser cannot read (`int("none")`) raised in `standard_terms` ... P10 and P11 with six fields walked (0.0); with a reader that skips the line they closed (0.814, 0.499)". After a drop, `_supervise_close` → `closing()` → `_state` raises again → the kit's `closing_move` decides.

**Change** (`agent.py`):

```diff
@@ def _state(self, case, sid, events):
-        sheet_id, terms = standing(events)
+        try:
+            sheet_id, terms = standing(events)
+        except Exception:
+            log.exception("%s: standing offer unreadable", sid)
+            sheet_id, terms = None, {}
+        terms = terms or {}
         t = self.states.get(sid)
@@
-        t.standard = standard_terms(events) or t.standard
+        try:
+            t.standard = standard_terms(events) or t.standard
+        except Exception:
+            log.exception("%s: quote PDF unreadable - keeping the earlier standard terms", sid)
```

**Affects.** Every case; hidden suppliers' PDFs are new renders. **Risk.** None; a missing standard falls back to the buyer's plan in `closing_terms` (the pre-existing behaviour before the PDF is downloaded).

## 3. `adopt_structure` copies the supplier's raw structure unsnapped - a clause, date or lead time outside `term_options` is a 422; two in a row drop the thread

**Shows.** `adopt_structure`: `out[f] = best[1][f]` for every negotiable field, and for `index_clause` it only re-picks when `insists`. `complete_offer` snaps *before* this call, so a supplier clause with another `base_month`/`deadband` (P14 CU share 0.55, P16 PPI-C241 - never played), an effective date like `2026-12-01` (P13 options Nov/Jan/Apr), or a standard lead of 50 days (P09 options 21..49) goes out as is. `api.md`: "a value outside the allowed options" → 422; `_worker`: 422 → `failures += 1`, second → `drop` → only an accept is left. In P08/P18 the distributors' clauses happened to match the options.

**Change** (`policy.py`):

```diff
-from arena_kit.cost import complete_offer, must_haves_ok, supplier_value, total_cost
+from arena_kit.cost import complete_offer, must_haves_ok, snap, supplier_value, total_cost
@@ def adopt_structure(self, case, sheet, t):
             for f in case["negotiable"]:
                 if f not in ("unit_price", "payment_days") and f in best[1]:
-                    out[f] = best[1][f]
+                    out[f] = best[1][f] if f in STRUCTURAL else snap(case, f, best[1][f])
@@
         for f in STRUCTURAL:
             insists = bool(t.offers) and all(terms.get(f) is not None for _, terms in t.offers)
-            if best and len(structures) > 1 and f in best[1] and not insists:
-                continue
             options = [v for v in (case.get("term_options") or {}).get(f) or [] if v is not None] \
                 or [v for v in t.struct_seen.get(f) or [] if v is not None]
+            allowed = [v for v in (case.get("term_options") or {}).get(f) or [] if v is not None]
+            if out.get(f) is not None and allowed and out[f] not in allowed:
+                out[f] = min(allowed, key=lambda v: self.c(case, {**out, f: v}, t))
+            if best and len(structures) > 1 and f in best[1] and not insists:
+                continue
```

**Affects.** P02, P08, P14, P16, P18 and every hidden raw-material/renewal case with a clause; P01/P13/D01 dates; P05/P06/P09/P10/P12 lead times. **Risk.** A snapped date moves to the nearest *listed* option; `best_options` re-picks by cost right after, as today.

## 4. A supplier that quotes without a price is answered with a walk-away

**Shows.** `decide`: `if t.status in ("walked_away", "no_bid") or theirs is None: return Decision("walk", sid)`. `cost.py total_cost` explicitly anticipates "a supplier that quotes none". In a single-supplier case the runtime sends the walk (`len(live_threads) > 1` is false) → no deal → 0 or the alternative. A capacity supplier that first asks "which volume?" (152 such asks in 829 e-mails) can well open without a price.

**Change** (`policy.py`):

```diff
@@ def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
-        if t.status in ("walked_away", "no_bid") or theirs is None:
+        if t.status in ("walked_away", "no_bid"):
             return Decision("walk", sid)
         t.case_type = case.get("type")
+        if theirs is None:
+            anchor = self.anchor(case, t)
+            if anchor is None or t.rounds_left <= 1:
+                return Decision("walk", sid)
+            return self.offer(case, t, anchor, intent="firm: please quote against these options",
+                              rival_best_c=rival_best_c)
         self.pick_offer(case, t)
@@ def floor_ask(self, t, theirs):
+    def anchor(self, case, t):
+        b = case["buyer"]
+        ref = b.get("current_unit_price") or ((b.get("alternative") or {}).get("terms") or {}).get("unit_price") \
+            or b.get("fallback_unit_price")
+        if not ref:
+            return None
+        floor = (t.profile or {}).get("floor_estimate")
+        low = floor * (1 + self.p["floor_margin_pct"] / 100) if floor else ref * (1 - self.p["min_open_discount_pct"] / 100)
+        return round(min(low, ref), 2)
```

`offer()` already guards every use of the standing price (`if t.standing_terms.get("unit_price") is not None`, `theirs and ...`, `c_cap = inf`), `opening_cost`/`their_costs` are first set when a priced reply arrives. **Affects.** Hidden capacity/RFQ cases; nothing in practice. **Risk.** Low; test on the sim with a price-less opening.

## 5. Holding rotates a cheaper package into the lead - read as "moved backwards"; the visible-step guard then prices that package *up*

**Shows.** `offer`: `if t.holding: k = t.holds % len(sheets); sheets = sheets[k:] + sheets[:k]`. P01 `773a42a5`: 14-day sheet 132.22 → 130.81 as lead → "you have moved backwards on the very option we are discussing" → counter *worse* (135.7 → 136.6), 0.842; `cac09d93` 0.864; same opening with a monotone lead 0.909 (`478e95da`). Fuchsreiter `a89a4dad`: "your prices just went backwards" → final. With the merged `VISIBLE_STEP` block the rotated 14-day sheet is now lifted to `last_p + 0.2 %` - i.e. a 14-day sheet priced *above* our 60-day one (≈ +1.3 % in C: 0.2 % price plus 46 days' interest at 8 %), and Brandlhuber/Dralveck accept any sheet at or above their value at once.

**Change** (`policy.py`):

```diff
         if t.holding:
-            k = t.holds % len(sheets)
-            sheets = sheets[k:] + sheets[:k]
             intent = "firm on price, open on the other terms"
```

**Affects.** P01, P05, P11 and every family/job-shop persona. **Expected.** P01 +0.04 in the 2/20 sessions that hit it; no downside: the alternatives stay on the sheet as options B/C.

## 6. Closing with clause variants while `open`: the supplier's own db0 sheet is still sent beside our db5 variant

**Shows.** `close` second branch: `term_sheets=[*variants, own][:3]`. The first branch was fixed, the second not. P18 `c43e456e`: given [5.10 db5, 5.21 db5, 5.10 db0] Werdenfels "accepted Option C" - its own db0 sheet: 0.621 vs 0.696 when db5 went alone (`13e6c049`, `c80f8b2a`, `783dd48d`, `c50dad81`); index cost €6,527 vs €1,088. In the open branch there is no walk risk at all (no final yet) and its own sheet stays its standing offer.

```diff
-                return Decision("send", t.supplier_id, term_sheets=[*variants, own][:3],
+                return Decision("send", t.supplier_id, term_sheets=variants[:3],
```

**Affects.** P08, P16, P18, P14/P02 with a supplier clause. **Expected.** +0.07 on ~1 in 5 P18-type closes.

## 7. Cash levers before the endgame end the supplier's concession run; the cash-short rate makes 14 days the lead

**Shows.** Brandlhuber: lever-trade group (14-day sheet accepted at once, r3-r4) 0.875-0.909 (`6d1edc5d`, `9c0ba9cd`, `38367dc0`, `934ed1e9`, `478e95da`) vs steady 30/60-day stepping 0.911-0.969 (`a37615af`, `1e887324`, `36af37af`, `d5066cc6`): mean 0.90 vs 0.93. Dralveck 28.00/14 (0.8136) vs 28.05/30 (0.8186): 16 days bought 0.18 %, our interest costs 0.36 %. `ARCHETYPE_RATE["cash_short_jobshop"] = 0.18` ≥ `CASH_HUNGRY_RATE 0.15` makes the menu price a 14-day sheet 0.8 % below the 30-day one; the supplier takes the structure at a 0.2 % discount and `agreed` freezes the price.

```diff
-ARCHETYPE_RATE = {"cash_short_jobshop": 0.18, "group_ladder": 0.07, "near_monopolist": 0.07}
+ARCHETYPE_RATE = {"cash_short_jobshop": 0.10, "group_ladder": 0.07, "near_monopolist": 0.07}
@@
-CASH_HUNGRY_RATE = 0.15
+CASH_HUNGRY_RATE = 0.20
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
+        endgame = t.rounds_left <= 2 or t.status == "final_offer" or t.holds >= 2
         if self.p["lever_trades"] > 0.5 and (t.holding or asks):
-            trades = [x for x in self.lever_trades(case, t, a, asks) if x not in sheets]
+            trades = [x for x in self.lever_trades(case, t, a, asks, endgame) if x not in sheets]
@@
-    def lever_trades(self, case, t, a, asks=()):
+    def lever_trades(self, case, t, a, asks=(), endgame=True):
@@
         for v in lever_values(case, a, t.standard, t.profile):
             if not v["must_haves_ok"]:
                 continue
+            if v["field"] in CASH_LEVERS and not endgame:
+                continue
```

Structural trades (P02's clause, P06 tooling as a lever) are untouched. **Expected.** P01 +0.03, P05 +0.005; hidden cash-short shops (Hrvelec-type at 17 %/yr still gets the 14-day sheet when it *signals* cash: `cash()` raises the rate to 0.2). **Risk.** Low; the steady group never saw a walk.

## 8. Risks seen, deliberately not changed (no safe fix in 90 min)

- **Relationship floor clamp for non-family archetypes** (`next_price`: `low = min(max(low, rel), theirs)`). P17: incumbent price 34.35 is 8.4 % *below* the should-cost (learnings) → full cost 0.98 × 37.5 ≈ 36.75, sustainable 0.5 % → `relationship_floor` ≈ 36.9, i.e. we open at the letter's +8 % and close in round 2. If the arena's full cost is lower (P01: 129.5-130.7 vs 132.64 should-cost), that costs the case. But at 34.35 the charge would be `soft(7.5) × 10,250 = €51k` against €55k of price increase - roughly a wash, so the estimate may be right. Leave; the P01 learnings show the knee is steep both ways.
- `cost_breakdown`: `freight[t["incoterm"]]` raises on an Incoterm outside the case's dict (a hidden supplier quoting CIF); api.md restricts incoterm to EXW/FCA/DAP.
- `eligible_cost` compares a C *with* our relationship estimate against an alternative *without* it; in practice the margin to the alternative is 3-10 %, no case flips.
- RFQ keepalive of an `agreed` bidder (fable_rules #4): untested against a live bot; the arena serialises calls per session - leave.

## Test order (sim, no quota): P10 with a reduced-volume final and P12 (finding 1); a thread with a price-less opening (4); a supplier clause with `base_month` 2026-07 on P16/P14 and a 2026-12-01 date on P13 (3); then one hosted P01 and one P18 pre-flight for 5-7.