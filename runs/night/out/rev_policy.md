# Buyer agent review: policy and economics (`policy.py`, `costing.py`)

**Scope.** The review covers `src/buyer/policy/policy.py` (shown) and `src/buyer/facts/costing.py` (shown). The runner and the claim bank are not shown. Where a finding depends on them, I say so.

**Line numbers** are counted from the files as pasted and may be off by ±2.

**Two cautions on the evidence.**
- `docs/learnings.md` and `docs/design.md` belong to the other team (procurecabana), not to us. Their `bound_full_cost` (the full-cost estimate bounded by the supplier's own counters) **does not exist in our `costing.py`**.
- Expected points assume about 4 cases per wave. One case moving by 0.1 is therefore about 2.5 wave points.

## Ranked findings

| # | Finding | Kind | Est. points over the final | Confidence |
|---|---|---|---|---|
| 1 | A should-cost that overshoots lifts the relationship floor to the quote, so we ask the supplier's own price and score about 0 | bug / hidden risk | +5…15 if one such case occurs | mechanism certain, frequency inferred |
| 2 | The claim ledger `used_refs` is global: rival quotes are blocked for the 3rd bidder, and refs and keys leak across cases if `Policy` is shared | bug | +2…6 | RFQ part certain; cross-case part depends on the runner |
| 3 | The opening anchor has no lower bound; a low floor estimate puts it more than 25 % below the price, which suppliers punish | value leak | +1…3 | evidence from `EVALUATION.md` |
| 4 | The menu prices a shorter lead time at 0.1 %/day for full-book suppliers that charge 0.2–0.65 %/day | value leak / hidden risk | +1…3 | evidence from both teams' notes |
| 5 | Hold detection only runs when `reciprocity > 0`, so lever trades never fire on holds and the identical-sheet guard is dead | bug | +0.5…2 | code certain, effect uncertain |
| 6 | `relationship_floor` runs 100 ternary iterations × up to 300 menu combos: seconds of CPU per move, in parallel at wave start | timeout risk | protects against 0-score threads | inferred |
| 7 | `alternative_cost` is infinite for a `current_contract` alternative that has no price | hidden risk | +0…3 | inferred |
| 8 | Smaller items (no diffs) | — | — | — |

---

### 1. The relationship floor can sit at or above the quote: we then ask the supplier's price (score ≈ 0)

**Evidence (code)**
- `costing.py:76`: the estimate is `full_cost = 0.98 × should_cost`. Nothing bounds it by what the supplier actually quotes.
- `relationship_floor` (`costing.py:98-120`) minimises our C over price, relationship charge included.
- `policy.py:248-251` then sets `low = min(max(low, rel), theirs)`. If `rel ≥ theirs`, then `low = theirs` and the opening ask is the quote (`next_price` line 254).
- The menu fails at the same time:
  - `menu` lifts every combo to the relationship floor (`policy.py:417-422`).
  - The `cost >= c_cap - 0.5` filter (line 424) then drops all of them.
  - `offer()` line 312 compares `self.c(a)` (charge included) with `c_theirs`. If a price below the quote "costs" more on our estimate, `same_cost` (line 313, plain C) puts `a` back at the supplier's price.
- The supplier then answers `agreed`, line 165 accepts, and C_deal = C_open, so the score is 0.

**Evidence (data)**
- Incumbents sit below should-cost: P17 −8.4 %, P02 −7.6 %, P01 −4.8 % (learnings, "Data package").
- The package states a 5–15 % should-cost error.
- **P17 scenario:** the letter asks +8 % on a price 8.4 % below should-cost. The quote is therefore about 0.989 × should-cost, and our full-cost estimate (0.98 × should-cost) is about 0.991 × quote. That is a 0.9 % margin at the quote.
  - With a sustainable margin above roughly 1.5 % (stabilise allows 0.5–8 %), the C-minimising price is at or above the quote.
  - P17's goal is not in the shown files, so this is inference.
- **P02 does not trigger:** the estimate is 367.45 against a quote of 370.96, a 0.95 % margin against a sustainable margin of 0.5 %.

**Inference.** Hidden cases are "mostly suppliers practice never shows", so `full_cost_observed` from memory will usually be missing. The overshoot path is then the default in any relationship case that has should-cost.

**Fix (minimal; diff 1).** Bound the data estimate by the supplier's own quote, so it is never below the sustainable margin at its quote: `full_cost ≤ quote × (1 − S/100)`.
- The record team does the same ("capped at the quote less the sustainable margin in relationship goals").
- `full_cost_observed` stays unbounded.
- Errors are asymmetric: underestimating the charge costs a gentle quadratic amount; overestimating it zeroes the case.

### 2. Claim ledger: rival citations blocked for the third bidder, and refs leaking across cases

**Evidence (code)**
- `policy.py:146` sets `self.used_refs = set()` once per `Policy`.
- `pick_claims` (lines 642-648) filters with `self.used_refs.isdisjoint(c.refs)` for **every** claim, rival claims included.
- `used_keys` is keyed `(supplier_id, key)` with no case id (lines 645, 661).

**Evidence (rules).** `api.md` "What counts": "each ID counts once per case, except a rival's quote: in an RFQ you may cite it to every other bidder, and it counts once per supplier."

**Scenario A (certain, within one RFQ)**
- Three bidders. A is cheapest, B and C are viable.
- Round 1: A's `offer:`/`quote:` ref is cited to B and enters `used_refs`. The same claim for C is then filtered out.
- C sees the rival only once A issues a new offer id, which is after round 1.
- Both teams found that round 1 is where suppliers give almost everything. The munich `EVALUATION.md` records RFQ 0.67 → 0.82 when the rival bid leads *every* message to a dearer bidder.

**Scenario B (conditional on the runner reusing one `Policy` for several sessions, which the practice batches and `arena run --set final` with parallel cases would invite)**
- P08 and P18 both rest on AS-14404 (learnings: −5.5 % from 2026-06).
- Whichever case cites it first blocks the other.
- Hidden waves are **themed**, so several cases in one wave likely share index series.
- One supplier appearing in two hidden cases also loses its claim keys in the second.
- **Check:** grep the runner for `Policy(` and confirm one instance per session.

**Fix (diff 2).** Keep `used_refs` per `case_id`, exempt `rival*` claims from the cross-supplier ref check, and key `used_keys` by `(case_id, supplier_id)`. Also grep for other readers of `used_refs`/`used_keys` before merging.

### 3. Anchor depth is unbounded below

**Evidence (code)**
- `policy.py:247`: `low = min(floor_ask, theirs × (1 − discount))` with `floor_ask = floor_estimate × 1.0255` (line 241, `params.json` `floor_margin_pct` 2.55).
- The opening is `low + 0.101 × (theirs − low)` (line 254).
- No clamp exists. A `floor_estimate` at 0.70 × the quote gives an opening ask of about 0.746 × the quote, which is 25.4 % below.

**Evidence (arena)**
- Munich `EVALUATION.md`: "asks more than 25 % below the supplier's current price drew 'your offer is far below any calculation we can make' (five replies, three suppliers, none at 24 % or less) and a third of the usual first concession." Examples: 6.05 → 5.76 instead of 5.36, and 36.0 → 32.5 instead of 30.5.
- Procurecabana P05: a 3 % deeper anchor (26.79) led to a walk-away.

**Hidden risk.** For unknown suppliers `floor_estimate` comes from market or country-factor estimates with ±10–15 % error (`interfaces.py` comment and the costing docstring). The low tail of that error lands exactly here.

**Fix (diff 3).** `low ≥ theirs × (1 − 22 %)`. With `open_frac` 0.101 the first ask then stays at or above about 0.80 × the price. The clamp binds only when the estimate is that low, so practice openings are unchanged unless they were already that deep.

### 4. Full-book suppliers: the menu thinks a shorter lead time is nearly free for them

**Evidence (code).** `supplier_model` line 361 uses `lead = ARCHETYPE_LEAD_EFFORT.get(archetype, 0.001)`, so only `near_monopolist` gets 0.005. `effort()` (line 366) charges `ref × lead × days`.

**Evidence (arena)**

| Supplier | Observed prices | Implied cost per day |
|---|---|---|
| Hrvelec (job shop, full book, P05) | 31.50 at 52 d, 33.00 at 42, 34.50 at 35 | 0.48 %/day, then 0.65 %/day |
| Ravensteiner | 32.00 at 56, 35.00 at 35 | 0.45 %/day |

- Munich `EVALUATION.md`: moving the prior from 0.1 % to 0.3 % for sold-out suppliers took the capacity case from 0.58 to 0.66.

**Scenario.** A hidden capacity or RFQ case with a full-book job shop (not archetype `near_monopolist`):
- Our menu offers the short lead time at almost its price.
- The supplier answers at +5–10 % ("overtime is priced in").
- We keep sheets that are cheap only on our wrong model.

**Fix (diff 4).** When `signals.capacity_issue` is set, `lead ≥ 0.003`. This is a general rule keyed to a signal, not to a supplier id.

### 5. Hold detection only runs when `reciprocity > 0`

**Evidence (code)**
- `t.holds` is only changed inside `concession()` (lines 273-281), which line 267 skips when `reciprocity <= 0`.
- `params.json` does not set `reciprocity`, so the default of 0 applies.

Consequences under the current parameters:

| Line(s) | Mechanism | What goes wrong |
|---|---|---|
| 321 | Lever trades fire when `t.holding or asks` | `t.holding` is set only when *our* `sheets[0]` repeats (line 317), not when *the supplier* holds. The 2026-10-25 feature ("every losing deal closed at the supplier's holding price") fires only on parsed asks. |
| 332 | Rotation `k = t.holds % len(sheets)` | Always 0, so the "lead with another package" rotation never happens and we resend the identical sheet. |
| 187 | Identical-sheet guard `... == prev and acceptable and not t.holding` | Dead: `offer()` has just set `t.holding = True` on exactly that condition (lines 316-317). |

Why the repeat matters: both teams observed that identical sheets or moves below 0.1 % trigger the supplier's final offer. Identical sheets arise when the gap is under about 0.04 on 2-decimal prices (P08/P18 scale: 0.125 × 0.03 rounds to 0).

**Fix (diff 5)**
- Count holds in `decide()` when `reciprocity` is off.
- Let holds trigger lever trades.
- Base the guard on `t.holds` (the supplier moved and we can't, so close) instead of the always-true `t.holding`.

The effect on score is unmeasured. Run P07, P11 and P18 three times each before keeping it.

### 6. CPU per move in relationship cases (timeout risk at wave start)

**Evidence (code)**
- `relationship_floor` runs `range(100)` ternary iterations, i.e. 200 `total_cost` calls (`costing.py:113`).
- `menu` calls it once per distinct lever combo (`policy.py:418-420`), up to `MENU_COMBOS` = 300.
- `lever_values` and `relationship_case` checks add more calls on top.

**Inference**
- 60k `total_cost` calls (each with up to three `closing_terms`) at about 40 µs comes to about 2–3 s per move.
- In a wave, up to 10 sessions × 1–3 threads compute in one Python process under the GIL, mostly in the first seconds.
- Learnings record two whole cases lost to timeouts, a supplier walk after a timeout, and suppliers that "barely move" after round 1. A late *first* message is the most expensive place to time out.

**Fix (diff 6).** 48 iterations already shrink the interval by (2/3)^48 ≈ 4·10⁻⁹. That is cents-exact for any price, with no behaviour change. Also measure p95 decide time with 10 parallel sessions on the sim.

### 7. A `current_contract` alternative without `unit_price` is infinite

**Evidence (code)**
- `alternative_cost` (`policy.py:136-140`) returns `inf` when `alt.terms.unit_price` is missing.
- The accept gate then accepts any must-have-safe deal (`eligible_cost`, line 226), including one dearer than keeping the current contract.

**Inference**
- The brief: "some cases are best left without a deal".
- Procurecabana stress-tested "no or a current-contract alternative" because hidden cases may use it.
- If the arena fills the alternative's price from `current_unit_price`, we mis-price C_alt.

**Fix (diff 7).** Fall back to `current_unit_price` for `current_contract`.

### 8. Smaller findings (no diffs)

**a. Concession mixes term sets.** `next_price` steps `last + 0.125 × (theirs − last)` in raw price (line 257). `our_prices` records `a` (always at reference payment, line 300), while `theirs` may be the supplier's 14-day price, and the menu's `sheets[0]` can differ from `a`.
- Scenario: P01 example. The supplier answers our 14-day sheet at 139.80/14 d, and we compare that to our 60-day `a`.
- Result: slightly over-generous steps. Low value; the clean fix is stepping in C (as `concession` already does when `reciprocity > 0`).

**b. Must-haves are not rechecked after transformations.**
- `lever_trades` checks `v["must_haves_ok"]` before `above_floor`/`cheap_money_term` changes the sheet (lines 470-478).
- `adopt_structure`'s insisted-clause branch (lines 595-596) sets a clause without rechecking.
- The accept gate still protects the score (`eligible_cost` line 223), so the cost is wasted rounds and a confusing signal. A hidden must-have such as `index_clause == null` or `payment_days <= 90` would hit this.

**c. `at_target` treats `floor_confidence = 0.0` as unsure.** `(prof.get("floor_confidence") or 1.0) > 0.05` (line 291) maps 0.0 to 1.0. This is dormant because `accept_target_pct` is 0, but it is a trap if someone enables it.

**d. Relationship charge counts 0 without should-cost** (`SURE_SOURCES`, `costing.py:33`). In `secure_supply` (sustainable margin 4–10 %, charge linear beyond 5 points), squeezing an unknown bottleneck supplier 10 points costs `(10 − 2.5) × €/pt × years`, and we cannot see it.
- After diff 1 one could add a *soft* guard (never ask below `quote × (1 − S)` in secure_supply without a sure estimate).
- Untested, so I don't propose it now.

**e. The writer can promise a confirmation the code will not keep.** If `CONFIRM AT ONCE` is set for Option A and the supplier agrees while a cheaper rival exists, `decide` (lines 167-170) counters instead of accepting. That breaks a written promise, which the brief says has consequences.
- Make sure the runner sets `CONFIRM AT ONCE` only when `rival_best_c` is infinite.
- This is a runner/writer check, not policy.

**f. Missed opportunity: a final offer above the alternative.**
- We walk at once (`close`, line 542).
- One sheet at the price where C meets C_alt costs only one round and can only gain.
- Low value on practice (alternatives sat 3–10 % above deals); possibly higher on hidden "best without a deal" cases.

**g. Menu domain pruning drops the supplier's standing value.**
- `keep = [a.get(f), v[0], v[-1], v[mid]]` (line 396) can drop, for example, its 56-day lead time.
- We then cannot mirror its own lever unless it sent two structures (`adopt_structure`).
- Add `t.standing_terms.get(f)` to `keep` if you touch this.

---

## Diffs

### Diff 1: bound the full-cost estimate by the supplier's own quote (finding 1)

```diff
--- a/src/buyer/facts/costing.py
+++ b/src/buyer/facts/costing.py
@@ -74,6 +74,12 @@ def supplier_estimate(case: dict, profile: dict | None, standard: dict | None = None,
         if not estimate or (sure_only and source not in SURE_SOURCES):
             return None
         full_cost = FULL_COST_FACTOR * estimate
+        # a data estimate never leaves the supplier below the sustainable margin at its own quote: should-cost
+        # runs 5-15 % off, and an overshoot lifts relationship_floor to the quote (we would ask its own price)
+        quoted = profile.get("quoted_price")
+        if quoted:
+            margin = (case["buyer"].get("sustainable_margin_pct") or 0) / 100
+            full_cost = min(full_cost, quoted * (1 - margin))
     b = case["buyer"]
     freight = b.get("freight_eur_per_unit") or {}
     vendor = {k: v for k, v in (profile.get("vendor_terms") or {}).items() if v is not None}
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -151,6 +151,8 @@ class Policy:
         if t.status in ("walked_away", "no_bid") or theirs is None:
             return Decision("walk", sid)
         t.case_type = case.get("type")
+        if "quoted_price" not in (t.profile or {}):  # its first price bounds our full-cost estimate (costing)
+            t.profile = {**(t.profile or {}), "quoted_price": theirs}  # a copy: the Scout's profile is shared
         self.pick_offer(case, t)
         c_theirs = self.cost(case, t)
         if t.standing_id not in t.seen_ids:
```

**Notes on diff 1**
- The profile is copied so that a supplier in two cases does not carry one case's quote into the other.
- If the runner replaces `t.profile` later, the bound is re-taken from the then-current counter. That is a tighter but still valid bound.
- **Offline test:** a P02-like case with `should_cost` = 1.08 × quote and S = 4 %. Before the diff the first sheet's `unit_price` equals the quote; after it, the sheet is below.

### Diff 2: claim ledger per case; rival quotes once per supplier (finding 2)

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -144,7 +144,7 @@ class Policy:
     def __init__(self, params=None):
         self.p = {**DEFAULTS, **(params if params is not None else load_params())}
-        self.banks, self.used_refs, self.used_keys = {}, set(), set()
+        self.banks, self.used_refs, self.used_keys = {}, {}, set()  # used_refs per case: an ID counts once per case
 
     def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
         p, sid = self.p, t.supplier_id
@@ -631,6 +631,7 @@ class Policy:
             except Exception:
                 self.banks[key] = []
         rejected = set((t.signals or {}).get("rejected_args") or [])
+        used_refs = self.used_refs.setdefault(case["case_id"], set())
         bank = list(self.banks[key])
         if t.case_threads and len(case.get("suppliers") or []) > 1:
             try:
@@ -642,9 +643,9 @@ class Policy:
         pool = [
             c for c in bank
             if c.strength >= self.p["claim_min_strength"]
-            and (t.supplier_id, c.key) not in self.used_keys
+            and (key, c.key) not in self.used_keys
             and c.key not in rejected
-            and self.used_refs.isdisjoint(c.refs)
+            and (c.key.startswith("rival") or used_refs.isdisjoint(c.refs))  # a rival's quote: once per supplier
         ]
         pool.sort(key=lambda c: -c.strength * CLAIM_WEIGHT.get(c.key.split(":", 1)[0], 0.3))
         strong = [c for c in pool if CLAIM_WEIGHT.get(c.key.split(":", 1)[0], 0.3) >= WEAK_CLAIM]
@@ -657,7 +658,7 @@ class Policy:
             if len(chosen) == limit:
                 break
         for c in chosen:
-            self.used_refs |= set(c.refs)
-            self.used_keys.add((t.supplier_id, c.key))
+            used_refs |= set(c.refs)
+            self.used_keys.add((key, c.key))
         return chosen
```

### Diff 3: cap the anchor at 22 % below the supplier's current price (finding 3)

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -75,6 +75,7 @@ CLAIM_WEIGHT = {"notice": 1.0, "ppm": 0.75, "rival": 0.7, "cost": 0.6, "news": 0.55, "index": 0.5, "fc": 0.45,
                 "po": 0.3, "otd": 0.15}
 OWN_PRICE_SLACK = 0.005
 CASH_HUNGRY_RATE = 0.15
+MAX_ANCHOR_PCT = 22.0  # asks > 25 % below its price drew "far below any calculation" and a third of the concession
 
 
 @dataclass
@@ -245,6 +246,7 @@ class Policy:
         if t.case_type in DEEP_OPEN_TYPES:
             discount = max(discount, self.p["deep_open_pct"])
         low = min(self.floor_ask(t, theirs), theirs * (1 - discount / 100))
+        low = max(low, theirs * (1 - MAX_ANCHOR_PCT / 100))  # a low floor estimate (+-15 %) must not anchor deeper
         if case is not None and floor_binds(t):  # stabilise / secure_supply: below it the charge costs more
             rel = relationship_floor(case, t.standing_terms, t.standard, t.profile)
             if rel is not None:
```

### Diff 4: price a shorter lead time realistically for full-book suppliers (finding 4)

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -63,6 +63,7 @@ DEFAULTS = {
 }
 DEEP_OPEN_TYPES = ("raw_material", "rfq")
 ARCHETYPE_LEAD_EFFORT = {"near_monopolist": 0.005}
+CAPACITY_LEAD_EFFORT = 0.003  # full order books price a day of shorter lead time at 0.2-0.65 % of the price
 ARCHETYPE_RATE = {"cash_short_jobshop": 0.18, "group_ladder": 0.07, "near_monopolist": 0.07}
 MENU_SPREAD = 0.003
 MENU_COMBOS = 300
@@ -359,6 +360,8 @@ class Policy:
             std["ppm_commitment"] = offered
         ppm = max(std.get("ppm_commitment") or 0, offered or 0, (t.profile or {}).get("ppm_actual") or 0)
         lead = ARCHETYPE_LEAD_EFFORT.get((t.profile or {}).get("archetype"), 0.001)
+        if (t.signals or {}).get("capacity_issue"):
+            lead = max(lead, CAPACITY_LEAD_EFFORT)
         return {"standard": std, "interest_rate": rate, "usual_rate": 0.07, "ref_price": ref, "ppm": ppm,
                 "lead_effort": lead}
```

### Diff 5: detect supplier holds without reciprocity; revive the identical-sheet guard (finding 5)

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -156,6 +156,8 @@ class Policy:
         if t.standing_id not in t.seen_ids:
             t.seen_ids.append(t.standing_id)
             t.their_costs.append(c_theirs)
+            if p["reciprocity"] <= 0 and len(t.their_costs) >= 2:  # concession() counts holds only with reciprocity
+                t.holds = t.holds + 1 if t.their_costs[-1] >= t.their_costs[-2] * 0.9995 else 0
         if t.opening_cost is None:
             t.opening_cost = c_theirs
             t.opening_payment_days = t.standing_terms.get("payment_days")
@@ -184,7 +186,7 @@ class Policy:
             return self.close(case, t, acceptable, c_theirs, rival_best_c)
         prev = t.last_sheet
         decision = self.offer(case, t, self.next_price(t, theirs, case=case), rival_best_c=rival_best_c)
-        if prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding:
+        if prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holds:
             return self.close(case, t, acceptable, c_theirs, rival_best_c)
         return decision
 
@@ -318,7 +320,7 @@ class Policy:
         asks = list((t.signals or {}).get("asks") or [])
         if clause_wanted(case, t.signals) and "index_clause" not in asks and self.clause_worth(case, t) >= CLAUSE_WORTH:
             asks.append("index_clause")  # it blames the driver a clause would follow: offer the clause
-        if self.p["lever_trades"] > 0.5 and (t.holding or asks):
+        if self.p["lever_trades"] > 0.5 and (t.holding or t.holds or asks):
             trades = [x for x in self.lever_trades(case, t, a, asks) if x not in sheets]
             if trades:
                 sheets = [sheets[0], *trades[:2], *sheets[1:]]
```

### Diff 6: fewer ternary iterations (finding 6; identical result to the cent)

```diff
--- a/src/buyer/facts/costing.py
+++ b/src/buyer/facts/costing.py
@@ -110,7 +110,7 @@ def relationship_floor(case: dict, terms: dict, standard: dict | None = None,
         return total_cost(case, {**terms, "unit_price": price}, standard, supplier)
 
     lo, hi = 0.5 * supplier["full_cost"], 2.0 * supplier["full_cost"]
-    for _ in range(100):  # C is convex in the price: linear spend plus a convex charge below the margin
+    for _ in range(48):  # (2/3)^48 of 1.5 x full cost: well below a cent; C is convex in the price
         m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
         if cost(m1) < cost(m2):
             hi = m2
```

### Diff 7: give a priceless current-contract alternative today's price (finding 7)

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -135,9 +135,12 @@ def load_params(path=PARAMS_FILE):
 
 def alternative_cost(case):
     alt = case["buyer"].get("alternative") or {}
-    if alt.get("kind") in (None, "none") or not alt.get("terms", {}).get("unit_price"):
+    terms = dict(alt.get("terms") or {})
+    if alt.get("kind") == "current_contract" and not terms.get("unit_price"):
+        terms["unit_price"] = case["buyer"].get("current_unit_price")  # keeping today's contract: today's price
+    if alt.get("kind") in (None, "none") or not terms.get("unit_price"):
         return math.inf
-    return total_cost(case, alt["terms"])
+    return total_cost(case, terms)
```

---

## Validation plan (before the 13:00 freeze)

1. **Offline, no quota.** Add unit tests for:
   - diff 1: a should-cost-overshoot case, where the first sheet must sit below the quote;
   - diff 2: an RFQ with three bidders, where the rival claim must reach both dearer bidders in round 1;
   - diff 3: `floor_estimate` = 0.6 × the quote, where the first ask must stay at or above 0.78 × the quote.

   Then run all 21 case files plus the variants through `arena-sim`, checking no exceptions, no must-have breaks and no deals above C_alt.
2. **Timing.** Run 10 parallel sim sessions and record p95 decide time before and after diff 6.
3. **Hosted runs, about 20 sessions.**
   - Diffs 1–4 and 6–7 should leave practice cases unchanged, except P05 for diffs 2 and 4 and P10 for diff 4. Run P05 and P10 twice each as guards.
   - Diff 5 changes behaviour on every case. Run P07, P11 and P18 three times each and keep diff 5 only if their mean does not drop, given the 0.47–0.72 spread between identical runs.
4. **Runner check.** Confirm one `Policy` per session (finding 2B), and that `CONFIRM AT ONCE` is never set while a cheaper rival exists (finding 8e).