# Review: claims bank, supplier profiles, memory

**Scope.** I could see `policy.py`, `claims.py`, `profile.py`, `memory.py`, the kit's `cost.py`, the writer prompt and the docs. I could not see `runner.py`, `costing.py`, `params.json`, `package.py` or `strategy.py`.

- Line numbers are approximate (≈). Treat function names as the anchors.
- **[E]** marks what the evidence shows: code as written, api.md, logged sessions.
- **[I]** marks what I infer.
- Point estimates are per affected wave (0-100 scale) and are rough.

---

## Ranked findings

### 1. Rival quotes and offers are rationed as if they were once-per-case IDs, and never built for single-supplier cases
**Where:** `policy.py` `pick_claims` (≈l.640-685): `self.used_refs.isdisjoint(c.refs)` in the pool filter, `self.used_refs |= set(c.refs)` after choosing, and the gate `len(case["suppliers"]) > 1`.

**[E] The rule.** api.md "What counts" says a rival's quote "counts once per supplier: in an RFQ you may cite it to every other bidder". `claims.py`'s own docstring and `compatible()` say the same ("put the ones cited to this supplier only"). The policy ignores this: the first bidder that gets `offer:70210-…` spends that ID for everyone.

**Scenario (P05, three bidders).**
- Round 1 cites Dralveck's opening offer to Hrvelec.
- Fuchsreiter then cannot get that claim. It gets the next-cheapest rival or nothing.

**[E] Evidence it matters.**
- Our NIGHT_CONTEXT: rival claims moved suppliers 65 % of the time.
- procurecabana: "cheapest rival offer was verified as a claim for every other bidder every round (P05 0.83)".
- EVALUATION.md: RFQ score went from 0.67 to 0.82 once the cheapest rival bid led every message to a dearer bidder.

**Second leak (single-supplier cases).** These have a `quote` alternative (`_case_quote_refs` includes `alternative.ref`), but rival claims are never built for them. That case is common: a supplier asks +9.5 %, and the alternative quote sits between today's price and the ask. `rival_claims` already filters out quotes at or above the standing price, so only helpful quotes would be cited.

**[I] Impact.** +3 to 8 on an RFQ wave. +1 to 3 on waves with quote alternatives.

**Fix:** D1.

### 2. Claim bookkeeping is not scoped to a case
**Where:** `policy.py:146` `self.used_refs, self.used_keys = …, set(), set()`. `used_keys` is keyed `(supplier_id, key)` and has no case.

**[I] If one `Policy` instance serves several sessions:**
- In a parallel practice batch, or a Live Final wave (up to 10 sessions in parallel), the first case to cite a shared driver window spends it for every other case.
- Shared driver windows are common: `index:AS-14404` is shared by P08 and P18, and LCI-C and PPI-D351 drive many parts.
- The other cases silently drop the claim. It is never sent, so there is no "duplicate", just a lost falling-index argument (45 % move rate).

**If it is one `Policy` per session,** there is no bug today, but repeated sessions of the same case in one process still bleed.

**Check:** `grep -n "Policy(" src/buyer`.

**[I] Impact.** If shared: +1 to 4 per wave (round-1 claims carry most of the movement: "suppliers give almost everything in round 1").

**Fix:** D1 keys both sets by `case_id`. It is harmless either way.

### 3. Profiles are blind to the Sunday release and are served from a pre-Sunday cache
**Where:**
- `profile.py` `_news`, `_meeting_notes`, `_overdue_letters` read SQLite only.
- `lookup_profile` returns `runs/profiles/all.json` whenever that file exists.

**[E] Evidence.** procurecabana learnings: "The Sunday release … reaches the kit's ID index …, not SQLite". The brief says "Hidden cases may cite its facts. Your agent should read it."

**[I] Scenario.** A release news item puts a supplier on `credit_watch`, or reports an `allocation`. What goes wrong:
- `cash_pressure` stays low, so there is no cash-for-price trade.
- `archetype` misses `near_monopolist` and capacity.
- The writer's dossier and `notes` (used by `offer()` for the cost-breakdown question) lack the new letter or memo.
- Even after a fix to `_news`, an `all.json` built Saturday keeps serving the old profile, because `stored()` wins.

**Impact.** A risk, not a bug in practice. It is +1 to 3 on any wave themed on the release.

**Fixes:**
- D5: merge release news into `_news`.
- Operations: rebuild profiles after 08:00 (`uv run python -m buyer.facts.profile`), or delete `runs/profiles/all.json` on the final machine.
- `runs/` is not committed (memory.py docstring). Check whether the final machine has the file at all.
  - If it does not, every profile is computed at session open (`build_feature_vector`, note files, dossier, strategy) for up to 10 sessions at once. Time it against the 60 s clock, or prebuild at agent start.

### 4. The supplier's cost of money ignores our best evidence
**Where:** `policy.py` `supplier_model` ≈l.351-352: `rate = ARCHETYPE_RATE.get(archetype, rate or 0.08)`.

**[E] What the code does.**
- The profile's `cash_rate_estimate` and the memory's `interest_rate_observed` are both overridden for every `group_ladder`, `near_monopolist` and `cash_short_jobshop` supplier.
  - `cash_rate_estimate` includes the cash-discount (skonto) implied rate: 37 to 56 %/yr for four suppliers (learnings).
  - `interest_rate_observed` is fitted from billed relationship charges in `memory.fit_relationship`, and is never read by the policy.
- A cash-short job shop whose skonto implies 45 % is valued at 18 %.
- A group supplier with a skonto and credit pressure is valued at 7 %.
- Nordmark's observed rate is about 0 % ("cost of money about 0", learnings), but the menu prices 90-day sheets at 7 %.

**[I] Consequence.**
- Payment trades are mispriced in `menu` (equal-value prices) and `lever_trades` (`hungry` gate at 15 %).
- For a group supplier, `cash_hungry` stays False, so the fast-payment-for-price sheet is filtered out by the own-price check. That is exactly the trade the brief flags ("a supplier short of cash may care more about when it is paid than about the price").
- For Nordmark-type suppliers we pay ~7 %×60/360 ≈ 1.2 % of price too much on longer-payment sheets.

**Impact.** +1 to 3 on cases with cash-short or skonto suppliers.

**Fix:** D3. Observed rate first; archetype only when we have no cash evidence.

### 5. Should-cost floors are uncalibrated, and the "negotiates down" exemption covers two-thirds of the pool
**Where:**
- `profile.py` `floor()`: the should-cost is used raw.
- `profile.py` `archetype()`: `owner in ("family", "founder")` → `family_foundry`.
- `policy.py` `NEGOTIATES_DOWN`, `floor_binds`.

**[E] Should-cost overshoots true full cost.** Relationship charges imply full cost ≈1.5 % below should-cost:

| Case | Implied full cost | Should-cost | Ratio |
|---|---|---|---|
| P01 | 129.5 to 130.7 | 132.64 | 0.976 to 0.985 |
| P02 | 367.4 to 371.7 | 374.95 | 0.980 to 0.991 |
| P03 | 394.7 to 399.4 | 403.21 | 0.979 to 0.991 |

**[E] What the overshoot cost us.**
- NIGHT_CONTEXT, P01: "relationship floor lifted it to 131.6" (0.89), against 129.5 to 130.1 (0.97 to 0.995) when the floor was bounded lower.
- With the trained `accept_target_pct` (≈2.3) switched on, `at_target` treats a supplier-specific should-cost (confidence 0.05) as a sure floor. It would accept up to ~4 % above true cost.

**Why the exemption is an overfit.** It was added because the floor hurt P01. It is keyed to archetype, not to the overshoot, and `archetype()` labels every family **and founder** company as `family_foundry`: 31 of 46 profiled suppliers.

**[I] Hidden-case risk.** In a `secure_supply` case (sustainable margin 4 to 10 %, linear charge beyond 5 points) with a founder job shop, we ignore the relationship floor completely. Pushing it to its cost floor can cost more in relationship charge than it saves in price.

**Fix:**
- D4: calibrate the should-cost by 0.985. It is general and addresses the cause.
- Then consider restricting `NEGOTIATES_DOWN` to `owner_type == "family"`. Low confidence, so no diff. Test on P01 and P03 first.
- Rebuild `memory.json` after D4: `supplier_bias` divides by the stored old `estimate`, so other-part floors would otherwise shift twice.

**Impact.** +1 to 3 on stabilise and secure_supply waves.

### 6. Should-cost claims vanish in RFQs and on new parts
**Where:** `claims.py` `cost_claims` ≈l.380.

**[E] The bug.** `current = buyer.current_unit_price`. In an RFQ for a new series, or any case without a current price, `gap = 0.0`, then `break`, so no claim.

**[E] Evidence it matters.**
- The should-cost claim was "taken into account" at D01, J1, P01, P05 and P10.
- D01 alone: 51.00 against 51.30 without it.
- Estimates exist for the RFQ parts of P05 and P06.

**Keep the comparison against the current price where there is one.** In a price-increase case, a should-cost between today's price and the ask must not be cited. That would signal we accept paying it. The fallback is to the supplier's own opening price.

**Impact.** +0.5 to 2 per RFQ case.

**Fix:** D2(b) and the `ref_price` passed in D1.

### 7. Forecast claims are limited to bundling and renewal
**Where:** `claims.py` `VOLUME_CASES`.

**[E] Evidence.**
- Forecast claims were "taken into account" in every case where used (learnings).
- P08 forecast instead of PO prices: path 5.30, 5.20, 5.10 (1 run).
- P01 has `fc:310010@2026-09` at +10.1 % but never cites it.

**Exclusion.** Keep `capacity` out: growth there tells a sold-out near-monopolist we depend on it.

**Impact.** +0.5 to 1.5 on price-increase and raw-material waves.

**Fix:** D2(c).

### 8. Price anchor ignores today's price when the floor is market-based
**Where:** `policy.py:246` `low = min(floor_ask, theirs*(1-discount))`.

**[E] What happens.** For most hidden suppliers there is no should-cost, so `floor()` returns price × median cost/price ratio (≈0.9 to 1.0). Then:
- `floor_ask` ≥ the quote.
- `low` = quote × 0.96.
- The opening is `low + 0.3×gap`: only about 2.8 % below a letter that asks +7 to +9.5 %, so it sits above today's price.

**[E] Data.**
- Price letters overshoot the weighted driver move (P01 +9.5 against +2.3 %; P13; P17).
- 82 % of 225 renewals settled flat or lower.
- procurecabana anchors at or below today's price in increase and renewal cases.

**Caveat.** I cannot see `params.json` or `strategy.py`. P01's 126.9 opening suggests something already anchors there on some paths. D6 only lowers `low` and the relationship floor still lifts it. Test P03 and P04 (price-frozen) before shipping.

**Impact.** +1 to 4 on price-increase waves, if the path is live.

### 9. Index claims: token falls and supplier-named drivers
**Where:** `claims.py` `index_claims`.

**[E] Token falls.**
- A 12-month change of -0.2 % keeps full strength (`if change <= 0`).
- The steeper recent window (`_recent_fall`) is only searched when the 12-month change is positive.

**[I] Supplier-named drivers.** `check()` marks any series not in our `cost_drivers` table as irrelevant, so we never build claims for drivers the supplier itself names ("Our costs move with LCI-C, PPI-C241, PPI-D351", api.md example). Parse those series from its round-0/1 e-mail and add falling windows for them.

**Fix:** D2(d) for token falls only.

### 10. Formatting traps in claim sentences
**[E] Thousand separator.** `_eur` writes `per 1,000 units`. Learnings: "'2,637' was read as 2.637 and contradicted". A contradicted claim costs trust.
- This affects every PO and rival claim on parts priced per 1,000 (fasteners).
- `cost_claims` skips those parts entirely.

**Fix:** D2(a).

**[E/I] Scorecard sort.** `scorecard_claims` sorts on `f["quarter"]`, but api.md lists `sc` facts as `supplier, otd_pct, ppm` only. If that is true:
- The "latest" row is whatever came last in the file.
- The sentence reads "in the four quarters to  (sc:…)".

**Fix:** sort on the `@2026Q3` suffix of the ID (D2(e)).

**[E/I] Same issue for orders.** api.md lists `po` facts without `date`. If so, `_recent` filters every order out and no PO claim is ever built. Low loss (0 of 23 PO citations moved a supplier), but check it.

### 11. Memory floors are not "the supplier's floor"
**Where:** `memory.py` `best_price`, `supplier_bias`.

**[E] The method.** `best_price` solves `total_cost(case, our_deal_terms) = c_best`:
- without the relationship term, and
- at *our* deal's structure.

**[I] Two distortions.**
- **Stabilise and secure_supply cases.** `c_best` contains a relationship charge, so the implied price is too high.
- **Different structures.** When C_best's package uses other levers (P10: 42 days against our 56), the late cost pushes the implied price below anything the supplier accepts at our lead time.

**[I] Hidden-case effect.** Hidden cases do not repeat practice cases, so mostly `supplier_bias` applies (±30 %/+15 %, other parts, any case type). For P10's supplier on a new part, that can be a +11 % floor bias, built on a lead-time artefact.

**Recommendation.** Run `python -m buyer.facts.memory --check`. Drop relationship-goal and capacity entries from `supplier_bias` until `best_price` is computed with the fitted `full_cost_observed`. No diff, given the word budget.

### 12. Smaller items
- **`_asked_pct` is dead.** It reads `asked_pct`, but `doc` facts carry `asked_price` (api.md). No score effect, because strength is capped at 1 for falls.
- **Notice claims** use `valid[:1]` of the supplier's contracts. If `ctr` facts lack `valid_from`/`valid_to` (api.md lists `supplier, days`), the claim may pair the letter with the wrong contract. It still verifies if the days differ, but it could miss a longer contract.
  - Prefer the contract with the largest `days`.
  - Notice claims moved the supplier 100 % of the time.
- **No `qn:` claim for quality cases.** api.md lets `qn` back a ppm figure. Part-level notifications usually show worse ppm than the scorecard. The quality record moved suppliers 72 % of the time. Worth a builder before the final if a quality wave comes.
- **Failures are silent.** `pick_claims` swallows every exception into an empty bank. Log it, or a Sunday-data parse error silently removes all arguments for a whole wave.

---

## Diffs

### D1: case-scoped bookkeeping, rival refs once per supplier, rivals for quote alternatives, RFQ should-cost (findings 1, 2, 6)
```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -144,3 +144,4 @@ class Policy:
     def __init__(self, params=None):
         self.p = {**DEFAULTS, **(params if params is not None else load_params())}
-        self.banks, self.used_refs, self.used_keys = {}, set(), set()
+        # used_refs: case_id -> IDs spent in that case; used_keys: (case_id, supplier, claim key)
+        self.banks, self.used_refs, self.used_keys = {}, {}, set()
@@ -645,28 +646,35 @@ class Policy:
-        key = (case["case_id"], t.supplier_id)
+        used = self.used_refs.setdefault(case["case_id"], set())
+        key = (case["case_id"], t.supplier_id)
         if key not in self.banks:
             try:
                 from buyer.facts.claims import claims
 
-                self.banks[key] = sorted(claims(case, t.supplier_id), key=lambda c: -c.strength)
+                self.banks[key] = sorted(claims(case, t.supplier_id, ref_price=t.standing_terms.get("unit_price")),
+                                         key=lambda c: -c.strength)
             except Exception:
                 self.banks[key] = []
         rejected = set((t.signals or {}).get("rejected_args") or [])
         bank = list(self.banks[key])
-        if t.case_threads and len(case.get("suppliers") or []) > 1:
-            try:
-                from buyer.facts.claims import rival_claims
-
-                bank = sorted(bank + rival_claims(case, t.case_threads, t.supplier_id), key=lambda c: -c.strength)
-            except Exception:
-                pass
+        try:
+            from buyer.facts.claims import _case_quote_refs, rival_claims
+
+            if len(case.get("suppliers") or []) > 1 or _case_quote_refs(case):
+                threads = t.case_threads or {t.supplier_id: [
+                    {"from": "supplier", "term_sheets": [{"terms": t.standing_terms}]}]}
+                bank = sorted(bank + rival_claims(case, threads, t.supplier_id), key=lambda c: -c.strength)
+        except Exception:
+            pass
         pool = [
             c for c in bank
             if c.strength >= self.p["claim_min_strength"]
-            and (t.supplier_id, c.key) not in self.used_keys
+            and (case["case_id"], t.supplier_id, c.key) not in self.used_keys
             and c.key not in rejected
-            and self.used_refs.isdisjoint(c.refs)
+            # a rival's quote or offer counts once per supplier (api.md), every other ID once per case
+            and (c.key.startswith("rival:") or used.isdisjoint(c.refs))
         ]
@@ -680,6 +688,7 @@ class Policy:
         for c in chosen:
-            self.used_refs |= set(c.refs)
-            self.used_keys.add((t.supplier_id, c.key))
+            if not c.key.startswith("rival:"):
+                used |= set(c.refs)
+            self.used_keys.add((case["case_id"], t.supplier_id, c.key))
         return chosen
```
Check that nothing else (runner, writer) reads `used_refs` as a set: `grep -rn used_refs src/`.

### D2: claim builders (findings 6, 7, 9, 10)
```diff
--- a/src/buyer/facts/claims.py
+++ b/src/buyer/facts/claims.py
@@ def _eur(value: float, price_unit) -> str:
-    unit = f" per {int(price_unit):,} units" if price_unit and price_unit != 1 else ""
+    # (a) no thousands comma: the arena read "2,637" as 2.637 -> contradicted
+    words = {10: "ten", 100: "hundred", 1000: "thousand"}
+    unit = f" per {words.get(int(price_unit), int(price_unit))} units" if price_unit and price_unit != 1 else ""
     return f"EUR {value:.2f}{unit}"
@@ def index_claims(data: CaseData, idx: _Index) -> list[Claim]:
     for series, weight, start, end, id0, id1, change in _driver_windows(data, idx, data.case.get("parts") or []):
-        if change > 0:
+        if change > -1.0:  # (d) rising or a token fall: the steepest recent fall, if any
             fall = _recent_fall(idx, series)
             if fall:
                 start, end, id0, id1, change = fall
         sentence = f"{_series_words(data, series)} changed {change:+.1f}% from {start} to {end} ({id0}, {id1})."
         bar = asked if asked else 5.0  # a change well below what is asked speaks for us
-        strength = min(1.0, 2 * weight) * max(0.0, min(1.0, (bar - change) / bar)) if change <= 0 else 0.0
+        strength = min(1.0, 2 * weight) * max(0.0, min(1.0, (bar - change) / bar)) if change <= -0.5 else 0.0
@@ def scorecard_claims(data: CaseData, idx: _Index, sid: str) -> list[Claim]:
-    rows = sorted(idx.sc.get(sid, []), key=lambda x: x[1].get("quarter") or "")
+    # (e) facts.json sc rows may carry no "quarter" (api.md): take it from the ID suffix
+    rows = sorted(idx.sc.get(sid, []), key=lambda x: x[1].get("quarter") or x[0].rsplit("@", 1)[-1])
     if not rows:
         return []
     sc_id, sc = rows[-1]
-    q = sc.get("quarter") or ""
+    q = sc.get("quarter") or sc_id.rsplit("@", 1)[-1]
@@
 HELPFUL_NEWS = ("free_capacity", "short_time_work", "supply_normalises")
-VOLUME_CASES = ("bundling", "renewal")
+# (c) forecast growth is more business for the supplier; not in capacity cases (it signals dependence)
+VOLUME_CASES = ("bundling", "renewal", "price_increase", "raw_material", "rfq", "quality")
@@
-def cost_claims(data: CaseData, sid: str) -> list[Claim]:
+def cost_claims(data: CaseData, sid: str, ref_price: float | None = None) -> list[Claim]:
     """Our should-cost of a part of the case, if the price we pay today sits clearly above it."""
     out = []
-    current = (data.case.get("buyer") or {}).get("current_unit_price")
+    # (b) no current price (RFQ, new part): compare with the supplier's own quote
+    current = (data.case.get("buyer") or {}).get("current_unit_price") or ref_price
@@
 def claims(case: dict, supplier_id: str | None = None, data: CaseData | None = None,
-           threads: dict | None = None) -> list[Claim]:
+           threads: dict | None = None, ref_price: float | None = None) -> list[Claim]:
@@
-        bank += cost_claims(data, sid) + news_claims(data, sid) + forecast_claims(data)
+        bank += cost_claims(data, sid, ref_price) + news_claims(data, sid) + forecast_claims(data)
```

### D3: the supplier's cost of money (finding 4)
```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -350,4 +350,11 @@ class Policy:
         rate, pressure = self.cash(t)
-        rate = ARCHETYPE_RATE.get((t.profile or {}).get("archetype"), rate or 0.08)
+        prof = t.profile or {}
+        arch_rate = ARCHETYPE_RATE.get(prof.get("archetype"))
+        if prof.get("interest_rate_observed") is not None:  # fitted from billed relationship charges
+            rate = prof["interest_rate_observed"]
+        elif arch_rate is not None and (rate or 0.0) < CASH_HUNGRY_RATE:  # archetype only without cash evidence
+            rate = arch_rate
+        else:
+            rate = rate or 0.08
         if pressure >= 0.5:
             rate = max(rate, ARCHETYPE_RATE["cash_short_jobshop"])
```

### D4: should-cost calibration (finding 5)
```diff
--- a/src/buyer/facts/profile.py
+++ b/src/buyer/facts/profile.py
@@
 BASE_RATE = 0.08
 MARKET_CONFIDENCE = 0.15          # floor from a price, not a cost estimate
+# full cost implied by billed relationship charges / should-cost: P01 0.976-0.985, P02 0.980-0.991,
+# P03 0.979-0.991 (docs/learnings.md); the package names a 5-15 % should-cost error
+SHOULD_COST_BIAS = 0.985
@@ def floor(v, supplier_id=None, part_id=None):
     if cost is not None:
         if v.get("should_cost_supplier_specific"):
-            return cost, (v.get("should_cost_confidence_pct") or 5) / 100, "should_cost"
+            return cost * SHOULD_COST_BIAS, (v.get("should_cost_confidence_pct") or 5) / 100, "should_cost"
         factor = COUNTRY_FACTOR.get(v.get("supplier_country") or "DE", 1.0)
-        return cost * factor, max(0.10, (v.get("should_cost_confidence_pct") or 10) / 100), "should_cost_country"
+        return (cost * factor * SHOULD_COST_BIAS, max(0.10, (v.get("should_cost_confidence_pct") or 10) / 100),
+                "should_cost_country")
```
Afterwards, rebuild `runs/profiles/all.json` and `memory.json` (`supplier_bias` uses the stored estimates).

### D5: Sunday release news in profiles (finding 3)
This assumes the release unpacks to `data/release-sunday/facts.json` (learnings) with `supplier`, `topic` and `headline` on `news:` IDs; `news_claims` already reads those fields.
```diff
--- a/src/buyer/facts/profile.py
+++ b/src/buyer/facts/profile.py
@@
 PROFILES_FILE = REPO_ROOT / "runs" / "profiles" / "all.json"
 OVERRIDES_FILE = Path(__file__).with_name("overrides.json")
+RELEASE_FACTS = REPO_ROOT / "data" / "release-sunday" / "facts.json"
@@ def _news():
     out = {}
     for r in _rows("SELECT id, date, supplier_id, topic, headline FROM news "
                    "WHERE supplier_id IS NOT NULL ORDER BY date"):
         out.setdefault(r["supplier_id"], []).append(r)
+    try:  # the Sunday release reaches facts.json, not SQLite
+        release = json.loads(RELEASE_FACTS.read_text(encoding="utf-8"))
+    except (OSError, ValueError):
+        release = {}
+    for ref, f in sorted(release.items()):
+        if ref.startswith("news:") and f.get("supplier"):
+            out.setdefault(f["supplier"], []).append(
+                {"id": ref, "date": f.get("date") or "2026-10", "supplier_id": f["supplier"],
+                 "topic": f.get("topic"), "headline": f.get("headline") or ref})
     return out
```

### D6: anchor no higher than today's price in increase and renewal cases (finding 8; ship only after P03/P04 pass)
```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -246,2 +246,6 @@ class Policy:
         low = min(self.floor_ask(t, theirs), theirs * (1 - discount / 100))
+        current = ((case or {}).get("buyer") or {}).get("current_unit_price")
+        if current and t.case_type in ("price_increase", "renewal"):
+            low = min(low, current)  # letters overshoot their drivers; 82 % of 225 renewals settled flat or lower
         if case is not None and floor_binds(t):  # stabilise / secure_supply: below it the charge costs more
```

---

## Validating before the freeze (cheap first)

1. **Offline, no quota.**
   - Unit tests:
     - `pick_claims` cites the same rival offer to two bidders and an index ID only once per case.
     - Two cases in one `Policy` do not block each other.
     - `claims()` on P05 with `ref_price` yields a `cost:` claim.
     - A per-1,000 part sentence has no comma.
   - Run every case file and the 613 stress variants through `arena-sim`.
   - Run `memory --check` after rebuilding.
2. **Hosted practice runs.**
   - P05 ×2 (D1). Expect bidder 2 or 3 to cite the cheapest offer in round 1.
   - P01, P02, P03 ×1 (D4). Watch the relationship line in `cost_breakdown`.
   - P04 and P03 for D6 (price-frozen guard).
   - P08 and P18 ×1 (D2 token-fall and forecast).
   That is about ten sessions.
3. **Sunday 08:00.**
   - Download the release.
   - Rebuild profiles.
   - Grep `all.json` for a release `news:` ID.
   - Run the pre-flight with `all.json` present and absent, and time the first message per case at 10 parallel sessions.