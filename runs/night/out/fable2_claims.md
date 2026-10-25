# Claims for hidden cases: what the arena checks, what we build, what is missing

## 0. Frame

**Evidence (fable_round1.md, round-1 table).** The first counter moves with the number of verified claims in the first e-mail and with little else: Brandlhuber 0 claims → 140.3/142.9 (75b0649b, b4535c94), 2 → 135.5–137.8; Fuchsreiter 0–1 → 32.0, 2 → 31.5/31.0, 3 → 30.5; Donautal 0 → 5.54, po+otd → 5.40, falling AS-14404 + PPI-C2431 + po → 5.20–5.23. The one claim-bank outage cost 0.31 on P01 (b4535c94). Later rounds: Fuchsreiter stepped every time a rival or quality claim arrived and held on prose alone (fable_language F3: 3871f28a vs 891fdbdf).

**Inference.** Hidden cases are won or lost in the claim bank: a supplier for which `claims()` yields fewer than three verified sentences starts 2–4 % higher and we never recover it (descent is fixed per supplier, fable_round1 "what the data shows" (1)).

**Allowed by api.md ("What counts") vs built by `claims.py`:**

| api.md type | checked | built | gap |
|---|---|---|---|
| 2×`idx` | % change | `index_claims` (falling only; rising → strength 0, never sent) | overshoot rebuttal when the letter asks more than its drivers moved |
| `quote` of the case / rival `offer` | EUR | `rival_claims`, RFQ only (`claims.py` `if threads and len(suppliers) > 1`, `policy.py pick_claims` same gate) | the case alternative is never cited in single-supplier cases |
| `sc` (quality also `qn`) | mean % / ppm | `scorecard_claims` latest `sc` row | `qn` rows never built |
| 2–8×`po` | prices | `po_claims` | ok |
| `cost` | EUR | `cost_claims`, needs `current_unit_price` and gap ≥ 8 %, `price_unit` 1 only | silent for a new RFQ part (`current_unit_price` null, sandbox D02), for ×100 price units (P14, P16) |
| `fc` | % | bundling/renewal only | keep (P10 930e2eba lost the 54-day sheet; the lead-time fix of fable_ceiling F3 is not merged) |
| `news` | about this supplier | `news_claims`, last one of three topics | fine; allow two for later rounds |
| `doc`+`ctr` | days | `notice_claims` | ok |

Not citable at all (api.md "Data IDs" table has no type for them; `package.py` docstring: `inv:`/`gr:` rows "can be looked up but not cited"): our payment history, `negotiation_history` events (`profile.py history()`), meeting notes. A sentence about them without an ID draws "which figures is that based on" and a hold (fable_language F3, 40 replies). They stay out of e-mails; the payment complaint is already answered in prose (`writer.py complains_of_late_payment`).

Ranking below is by expected gain on unseen suppliers × certainty.

---

## Finding 1 — The first e-mail must carry three verified claims; `pick_claims` throws usable ones away (+0.01–0.03 on thin-bank suppliers; removes the P01-0.616 path)

**Evidence.** `policy.py pick_claims`: `pool = [c … if c.strength >= p["claim_min_strength"]]` (0.2) then `strong = […weight >= WEAK_CLAIM]; pool = strong or pool`. A good supplier's ppm claim (`scorecard_claims`: strength `ppm/1000` → 150 ppm = 0.15) and a mild index fall (`index_claims`: `(bar-change)/bar × 2w` → 0.1–0.2) are dropped; `otd` (weight 0.15) is dropped whenever one strong claim exists. Result: a supplier with one letter and a green scorecard gets one claim. The outage session shows the cost of an empty first e-mail (142.9 vs 137.8, 0.616 vs 0.909). Fuchsreiter's otd claim counted in its ladder (32.0 → 31.5).

**Inference.** Count beats strength in round 1. Rising-index claims (strength exactly 0) stay out: they earn "your figures confirm our case" (fable_rules, P02 c75e3d16).

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@
 WEAK_CLAIM = 0.2
+FILLER_STRENGTH = 0.1
 CLAIM_WEIGHT = {"notice": 1.0, "ppm": 0.75, "rival": 0.7, "cost": 0.6, "news": 0.55, "index": 0.5, "fc": 0.45,
-                "po": 0.3, "otd": 0.15}
+                "po": 0.3, "otd": 0.15, "overshoot": 0.55, "qn": 0.6}
@@ def pick_claims(self, case, t):
                 try:
-                    self.banks[key] = sorted(claims(case, t.supplier_id), key=lambda c: -c.strength)
+                    self.banks[key] = sorted(claims(case, t.supplier_id, threads=t.case_threads),
+                                             key=lambda c: -c.strength)
                     break
@@
-        if t.case_threads and len(case.get("suppliers") or []) > 1:
+        if t.case_threads:
             try:
                 from buyer.facts.claims import rival_claims
 
                 bank = sorted(bank + rival_claims(case, t.case_threads, t.supplier_id), key=lambda c: -c.strength)
             except Exception:
                 pass
-        pool = [
+        eligible = [
             c for c in bank
-            if c.strength >= self.p["claim_min_strength"]
+            if c.strength > 0
             and (t.supplier_id, c.key) not in self.used_keys
             and c.key not in rejected
             and (c.key.startswith("rival:") or self.used_refs.isdisjoint(c.refs))
         ]
-        pool.sort(key=lambda c: -c.strength * CLAIM_WEIGHT.get(c.key.split(":", 1)[0], 0.3))
+        eligible.sort(key=lambda c: -c.strength * CLAIM_WEIGHT.get(c.key.split(":", 1)[0], 0.3))
+        pool = [c for c in eligible if c.strength >= self.p["claim_min_strength"]]
         strong = [c for c in pool if CLAIM_WEIGHT.get(c.key.split(":", 1)[0], 0.3) >= WEAK_CLAIM]
         pool = strong or pool
         chosen, seen = [], set()
         for c in pool:
             if seen.isdisjoint(c.refs):
                 chosen.append(c)
                 seen |= set(c.refs)
             if len(chosen) == limit:
                 break
+        if len(t.our_prices) <= 1:
+            for c in eligible:
+                if len(chosen) >= limit:
+                    break
+                if c.strength >= FILLER_STRENGTH and c not in chosen and seen.isdisjoint(c.refs):
+                    chosen.append(c)
+                    seen |= set(c.refs)
         for c in chosen:
```

**Affects.** Every hidden supplier whose bank has fewer than three claims of strength ≥ 0.2; practice P03/P04/P07 (green scorecards) unchanged in price per the table ("anything" → same path). **Risk.** A weak otd/ppm line to a group earns "does not change our calculation" (6/6) — no price penalty seen. **Test (5 min offline).** `profile_all()` already lists each supplier's bank in `runs/profiles/review.md`; count suppliers with < 3 lines of strength ≥ 0.2 before and after.

---

## Finding 2 — Cite the case's own alternative quote to a single supplier the moment its price exceeds it (turns alternative-scores into deals; RFQ unchanged)

**Evidence.** api.md: "a `quote` of this case (in its `refs` or your alternative)" is checkable; `check()` already verifies it for any supplier (`kinds <= {"quote","offer"}` branch, `_case_quote_refs` includes `alt.get("ref")`). But `claims()` and `pick_claims` only call `rival_claims` when `len(suppliers) > 1`. Rival claims moved Dralveck/Fuchsreiter in every session they appeared (891fdbdf 30.5→30.0/29.5; c15e7332 → 29.5; 25a4b54b → 30.0/29.5), with proof demands when the rival was prose only. In single-supplier cases we hold `quote:7200001` (P01 143.22), `quote:7200009` (P09 16.33 vs current 16.02 for a full supplier), `quote:7200013` (P13). `eligible_cost` returns None once the standing C ≥ `alternative_cost` → the policy walks (alternative score) without ever telling the supplier the alternative exists.

**Inference.** `rival_claims` filters `price >= theirs` out, so the alternative is cited only when it is cheaper than the supplier's standing price — exactly when a credible walk-away is on the table and nothing is leaked otherwise (second-source quotes sit 8–21 % above incumbents, learnings).

```diff
--- a/src/buyer/facts/claims.py
+++ b/src/buyer/facts/claims.py
@@ def claims(case: dict, supplier_id: str | None = None, data: CaseData | None = None,
         bank = [c for c in bank if check(case, sid, c.sentence, data=data) == "verified"]
-        if threads and len(case.get("suppliers") or []) > 1:
+        if threads:
             bank += rival_claims(case, threads, sid, data=data)
```
(the `pick_claims` gate is removed in Finding 1's diff.)

**Affects.** Hidden capacity/price-increase cases with a quote alternative and a supplier above it (P09-like). **Risk.** Reveals the quote to that supplier (api.md) — only when it is better than its price. P01 unchanged (143.22 > every Brandlhuber price).

---

## Finding 3 — Overshoot rebuttal: the price letter asks more than its cost drivers moved (price_increase cases; n=0, one test)

**Evidence.** Data: letters overshoot the index-weighted driver move — P01 +9.5 % vs +2.3 %, P13 +7.0 vs +4.0, P17 +8.0 vs +5.5 (learnings "Data package"); the trigger `doc:` fact carries `asked_pct`/`asked_price` (`claims.py _asked_pct`, api.md `doc … asked_price`). The supplier itself argues with its rising drivers (api.md example: "LCI-C rose 2.7 % … 30 % of our cost. That remains."). `index_claims` gives every rising series strength 0, so the heaviest driver of P01 (LCI-C, weight 0.30, +2.7 %) is never cited; only PPI-D351's fall is.

**Inference.** A rising driver cited bare "confirms our case"; cited *as* the comparison with the letter's ask it is a rebuttal the bot reads as prose. The arena checks the single % figure in the sentence against the two `idx` IDs (our `check()` requires all `NUM%` figures to match → the letter's ask must not appear as a digit; it is named by date). Fires only when the weighted 12-month driver move is below half the ask, and only for a series `_recent_fall` did not already turn into a falling claim (no two sentences on one series).

```diff
--- a/src/buyer/facts/claims.py
+++ b/src/buyer/facts/claims.py
@@ def _asked_pct(data: CaseData) -> float | None:
     doc = data.case.get("trigger_doc")
     fact = data.lookup(doc) if doc else None
-    return (fact or {}).get("asked_pct")
+    if not fact:
+        return None
+    if fact.get("asked_pct") is not None:
+        return fact["asked_pct"]
+    current = (data.case.get("buyer") or {}).get("current_unit_price")
+    price = fact.get("asked_price")
+    return (price / current - 1) * 100 if price and current else None
@@ def index_claims(data: CaseData, idx: _Index) -> list[Claim]:
     return out
 
 
+def overshoot_claims(data: CaseData, idx: _Index) -> list[Claim]:
+    asked = _asked_pct(data)
+    if not asked or asked <= 0:
+        return []
+    windows = list(_driver_windows(data, idx, data.case.get("parts") or []))
+    total = sum(w for _, w, *_ in windows)
+    if not windows or total <= 0:
+        return []
+    weighted = sum(w * chg for _, w, _, _, _, _, chg in windows) / total
+    if weighted >= 0.5 * asked:
+        return []
+    doc = data.lookup(data.case.get("trigger_doc") or "") or {}
+    when = f" of {_long_date(doc['date'])}" if doc.get("date") else ""
+    for series, weight, start, end, id0, id1, change in windows:
+        if not 0 < change < asked or _recent_fall(idx, series):
+            continue
+        sentence = (f"{_series_words(data, series)}, a main cost driver of this part, changed {change:+.1f}% "
+                    f"from {start} to {end} ({id0}, {id1}): a fraction of the increase your letter{when} asks for.")
+        strength = min(1.0, 2 * weight) * (asked - change) / asked
+        return [Claim(f"overshoot:{series}", sentence, [id0, id1], "verified", round(strength, 3))]
+    return []
+
+
 def notice_claims(data: CaseData, idx: _Index, sid: str) -> list[Claim]:
@@ def claims(case: dict, supplier_id: str | None = None, data: CaseData | None = None,
-    shared = index_claims(data, idx)
+    shared = index_claims(data, idx) + overshoot_claims(data, idx)
```

**Affects.** price_increase cases with a short letter and rising drivers (P01-like, P13, P17 and hidden ones); nothing else (no `asked_pct` → []). P01 strength: 0.6 × 0.72 = 0.43, weight 0.55 → ranks after notice and ppm, i.e. the third slot (today PPI-D351 −3.7 %; the two compete by refs only). **Risk.** The bot may still answer "that remains" — n = 0. Play one P01 session: keep if the first counter is ≤ 137.8 (the two-claim band), revert this function otherwise.

---

## Finding 4 — Three cheap bank extensions for case types practice never showed (qn rows, cost vs the standing price, two news items)

**Evidence.** (a) api.md: "`sc` rows (quality also `qn`)"; `qn:` facts carry `supplier, part, ppm`; `_Index` has no `qn` bucket, so quality cases have one quality ref (`sc`) for the whole thread, while Kalwisz dropped 0.50 only "on a bump" and held otherwise (fable_round1 P11; 45.50 when final@≥6). (b) `cost_claims` compares the should-cost with `current_unit_price` only: a new part (RFQ, D02 `current_unit_price: null`) or a ×100 price unit (P14, P16: `price_unit not in (None, 1)` → skipped) never gets the claim that moved Ravensteiner (−0.2, fable_round1) and Dralveck ("cost: taken into account … P05", learnings). (c) `news_claims` keeps one item; Fuchsreiter's ladder 32.0 → 30.5 counted the news line.

**Inference.** For (b) the figure the supplier should-cost is weighed against is its own standing quote in this session (`_standing_price`), not what we paid someone else.

```diff
--- a/src/buyer/facts/claims.py
+++ b/src/buyer/facts/claims.py
@@ class _Index:
         self.sc: dict[str, list[tuple[str, dict]]] = defaultdict(list)
+        self.qn: dict[tuple[str, str], list[tuple[str, dict]]] = defaultdict(list)
         self.letters: dict[str, list[tuple[str, dict]]] = defaultdict(list)  # docs with notice days
@@ def add(self, facts: dict):
             elif kind == "sc":
                 self.sc[f["supplier"]].append((ref, f))
+            elif kind == "qn" and f.get("ppm") is not None:
+                self.qn[(f.get("supplier"), f.get("part"))].append((ref, f))
             elif kind == "doc" and f.get("days") is not None:
@@ def _index(data: CaseData) -> _Index:
-    for name in ("series", "po", "sc", "letters", "contracts"):
+    for name in ("series", "po", "sc", "qn", "letters", "contracts"):
@@ def scorecard_claims(data: CaseData, idx: _Index, sid: str) -> list[Claim]:
     return out
 
 
+def qn_claims(data: CaseData, idx: _Index, sid: str) -> list[Claim]:
+    out = []
+    for part in data.case.get("parts") or []:
+        rows = sorted(idx.qn.get((sid, part), []), key=lambda r: r[1].get("date") or "")[-3:]
+        if not rows:
+            continue
+        ppm = round(sum(f["ppm"] for _, f in rows) / len(rows), 1)
+        ids = ", ".join(r for r, _ in rows)
+        sentence = (f"Our quality notifications on {_part_words(data, part)} from you record {ppm:g} ppm "
+                    f"defective parts ({ids}).")
+        out.append(Claim(f"qn:{sid}:{part}", sentence, [r for r, _ in rows], "verified",
+                         round(max(0.0, min(1.0, ppm / 1000)), 3)))
+    return out
+
+
 def _recent(rows, as_of: date):
@@ def cost_claims(data: CaseData, sid: str) -> list[Claim]:
-def cost_claims(data: CaseData, sid: str) -> list[Claim]:
+def cost_claims(data: CaseData, sid: str, threads: dict | None = None) -> list[Claim]:
     """Our should-cost of a part of the case, if the price we pay today sits clearly above it."""
     out = []
-    current = (data.case.get("buyer") or {}).get("current_unit_price")
+    current = _standing_price((threads or {}).get(sid)) or (data.case.get("buyer") or {}).get("current_unit_price")
     for part in data.case.get("parts") or []:
         code = part.split(":", 1)[1]
         for ref in (f"cost:{code}-{sid.split(':', 1)[1]}", f"cost:{code}"):
             f = data.lookup(ref) if data.citable(ref) else None
-            if not f or not f.get("unit_cost") or f.get("price_unit") not in (None, 1):
+            if not f or not f.get("unit_cost"):
                 continue
             gap = (current - f["unit_cost"]) / current if current else 0.0
             if gap < 0.08:
                 break
-            sentence = f"Our cost estimate for {_part_words(data, part)} is {_eur(f['unit_cost'], 1)} per unit ({ref})."
+            sentence = (f"Our cost estimate for {_part_words(data, part)} is "
+                        f"{_eur(f['unit_cost'], f.get('price_unit'))} ({ref}).")
@@ def news_claims(data: CaseData, sid: str) -> list[Claim]:
-    return out[-1:]
+    return out[-2:]
@@ def claims(case: dict, supplier_id: str | None = None, data: CaseData | None = None,
-        bank = shared + notice_claims(data, idx, sid) + scorecard_claims(data, idx, sid) + po_claims(data, idx, sid)
-        bank += cost_claims(data, sid) + news_claims(data, sid) + forecast_claims(data)
+        bank = shared + notice_claims(data, idx, sid) + scorecard_claims(data, idx, sid)
+        bank += qn_claims(data, idx, sid) + po_claims(data, idx, sid)
+        bank += cost_claims(data, sid, threads) + news_claims(data, sid) + forecast_claims(data)
@@ def check(case: dict, supplier_id: str, sentence: str, used: set[str] = frozenset(),
+    if kinds == {"qn"}:
+        rows = list(facts.values())
+        if any(f.get("supplier") != supplier_id or f.get("part") not in parts for f in rows):
+            return "irrelevant"
+        stated = re.findall(rf"({NUM})\s*ppm", sentence)
+        mean = sum(f["ppm"] for f in rows) / len(rows)
+        return "verified" if stated and all(_rel_ok(_num(s), mean) for s in stated) else "contradicted"
+
     if kinds == {"po"}:
```

`_standing_price` and `_long_date` are defined above these call sites in the module (functions resolve at call time; `cost_claims` runs after both are defined). The quote-time standing price reaches the bank through the `threads=t.case_threads` argument added in Finding 1.

**Affects.** Quality cases (P11, P12-like): a second quality ref for the hold rounds; RFQs on new parts and ×100-unit parts: a cost claim where there was none; job shops with two helpful news items. **Risk.** `_rel_ok` (±0.5 %) on a tiny ppm mean would be contradicted — our `check()` filters such a sentence before it is ever sent; `qn` key weight 0.6 sits below `ppm` so the scorecard still leads.

---

## What the question asked for and the data cannot verify

- **Payment history / "we pay on time".** Invoices and payments are table rows, not facts (`package.py`: "`inv:` or `gr:` can be looked up but not cited"); Kalwisz's "we often see late payments" is best met by the acknowledgement line the writer already adds (`ITS PAYMENT COMPLAINT`; 273c889c moved one round earlier than the bare promise of 3ab9d154). No claim.
- **Negotiation history settled-vs-asked.** `negotiation_history` has no citable ID type (api.md "Data IDs"). Keep it where it is: `profile.history` → opening discount. No sentence.
- **Capacity news about the supplier.** `profile.py CAPACITY_NEWS` (allocation, full order book) is about us being weak; `CASH_NEWS` (credit watch, restructuring) is the DOSSIER content writer rule 3 forbids — a verified `news:` claim is only "about this supplier", and telling a person it is on credit watch is an irritation trigger with no observed upside. Only `HELPFUL_NEWS` stays.
- **Forecast in capacity cases.** The gain (P10 33.0 vs 33.6) is real but was eaten by the lost 54-day sheet (930e2eba 0.617 vs 0.663). Extend `VOLUME_CASES` only after fable_ceiling F3 (the supplier's own lead time on a sheet) is merged and tested once; not in this window.
- **Driver fallback for a part outside `cost_drivers`.** `_drivers` reads SQLite; a release-only part gets no index claims. The only honest fallback is the series the supplier names itself, and the arena marks an index outside the part's drivers `irrelevant` (learnings). Not worth a slot.

## Test plan (fits 40 minutes)

1. Offline (5 min): for every case in `runs/cases/practice.json` and `sandbox.json`, `claims(case)` must raise nothing and every sentence must pass `check()` — the existing filter guarantees nothing unverified leaves; assert P11's bank now holds a `qn:` key, P01's an `overshoot:LCI-C` key, P05's `cost:` for at least one bidder.
2. Offline (5 min): `profile_all()` → count suppliers with < 3 claims of strength ≥ 0.1 in `runs/profiles/review.md`; that count is the share of hidden suppliers Finding 1 cannot help.
3. Practice (2 sessions): P01 (Finding 3 go/no-go on the first counter: ≤ 137.8 keep, otherwise drop `overshoot_claims` from `shared`), P05 (cost claim verified, no `contradicted` in `claim_results`). Everything else is bank-only and changes nothing on the table-driven suppliers (P02, P03, P04, P10 identical to four decimals across 200 sessions).