# Persona-trait playbook for the Live Final, with diffs to `dossier.py` and `policy.py`

## 0. Scope and caveats

- **Trait phrases are not attached.** Traits come from fixed phrases in `SIGNALS` in `buyer/personas.py` (learnings.md, "Data package"), and that file is not part of what you sent. So the trait-detection regexes below are **inferred from the trait names and from note wording we have seen**. Before the freeze, grep the package notes against them (see §4).
- **Several "never seen" traits have partial evidence:**
  - *hedged*: Donautal, "alloy hedged until 03/2027" (NIGHT_CONTEXT, P08 row).
  - *approval_2pct*: Nordmark, "committee >2 %" (NIGHT_CONTEXT, P02).
  - *complains_late_pay*: Kalwisz wrote "we often see late payments" (learnings.md, "Asks"). The package also has seven overdue letters.
  - *partnership_2022*: `dossier.py` already matches "kept supplying at the old price".
  - *stale_costing*, *open_book*, *price_frozen*, *cash_need*, *spare_capacity*, *capacity_full*: all observed (learnings.md, "Data package").
- **Notation:** **E** = evidence, **I** = my inference.

## 1. Findings, ranked by expected score impact

**1. Round 1 is the negotiation, so the trait-specific trade must be in the first message.**
- E: In `dossiers.json`, `later_move` is exactly 0.0 for 7 of 12 suppliers. Examples: 70140, 70210, 70410, 70530, 70620, 70710 and 70740, against first moves of 0.017 to 0.17.
- E: NIGHT_CONTEXT: "Suppliers give almost everything in reply to round 1". Final offers come at fixed rounds: P10 r1, P08/P18 r3, P02 r4, P01 r5-6.
- E (gap in code): `policy.offer` only adds lever trades `if t.holding or asks` (policy.py, `offer`). So before a supplier asks or holds, round 1 carries no trait trade.
- I: The cheapest general gain is to pre-load each trait's known asks into round 1.

**2. Never anchor more than about 24 % below the standing price.**
- E: EVALUATION.md ("Anchors"): asks more than 25 % below drew "far below any calculation we can make". That was 5 replies from 3 suppliers, none at 24 % or less, and the first concession was about a third of the usual (36.0→32.5 instead of 30.5).
- E: P05 at 26.79 (25.6 % below 36.00) got a first counter of 30.0, then a walk-away at 39 % cumulative gap. The held 27.86 (22.6 %) scored 0.828 (learnings.md; `practice-v12-P05.log`).
- E (gap in code): `next_price` can open below that. `low = min(floor_ask, theirs·(1−disc))`, and `floor_ask` comes from a market ratio with confidence 0.15 (`profile.MARKET_CONFIDENCE`). With `open_frac` 0.3, a floor at 0.6×quote opens at 28 % below. No cap exists.

**3. Hedged suppliers and distributors: never send index-clause sheets, but keep citing falling indices.**
- E: A 5 % deadband clause sheet in round 1 drew a first counter 1.5-2 % above the 0 % clause the supplier adds itself. That held on P08 (5.60-5.64) and P18 (5.50), six runs (learnings.md).
- E: Keeping fixed sheets while the supplier countered with its own clause closed P18 at 5.00 (0.688, `e86f454a59ff98f0`), against 5.10 (0.621) in four sessions that adopted the clause. P08 closed at 5.25 (`22f82a186bc4fb08`) against 5.30-5.38.
- E: Hedged stainless suppliers answered an index fall with "not our reality", yet their first counter came lower: 5.36-5.46 against 5.42-5.69, 21 runs each (EVALUATION.md).
- E (gap in code): `adopt_structure` counters an insisted clause with our cheapest deadband (policy.py, the `insists` loop). `offer` appends `index_clause` to asks when `clause_wanted`. Both send clause sheets to a hedged supplier.

**4. Capacity-full suppliers sell speed; buy the long lead time instead.**
- E: Hrvelec quoted 31.50 at 52 d, 33.00 at 42 and 34.50 at 35. Ravensteiner quoted 32.00 at 56 and 35.00 at 35. That is about 0.2-0.5 % of the price per day.
- E: Raising the assumed overtime cost from 0.1 % to 0.3 % per day moved P10 from 0.58 to 0.66 (EVALUATION.md, run `26e559b2`). P10 also took 36 months, which unlocked full volume (learnings.md).
- E (gap in code): `ARCHETYPE_LEAD_EFFORT` uses 0.005 only for `near_monopolist`. A capacity-full supplier with any other archetype (Hrvelec is not one) is valued at 0.001.

**5. Cash need: offer faster payment in round 1, priced at the supplier's rate.**
- E: Dralveck (cash pressure 0.36, below the 0.5 cash-short threshold) asked for faster payment and closed at 14 d in every P05 run (0.82-0.83).
- E: Kalwisz asked for faster payment five times, then wrote "you just ignore it" and sent a final.
- E: Cash discounts imply 37-56 %/yr for four suppliers; our cost is 0.67 % of spend per 30 days (learnings.md).
- E (gap in code): `supplier_model` lifts the rate to 0.18 only at `pressure >= 0.5`, or after a live ask.

**6. Price-frozen suppliers: ask for terms at their price and close fast.**
- E: P03 and P04 refused every price trade (36 months, 14-day payment, +20 % volume) with "we can talk about the terms instead".
- E: Deals were 90 d at the frozen price (431.77-432.15 and 4.94). Scores were at the record: 0.935/0.936 and 0.87/0.874.
- I: Opening below the frozen price earns nothing and costs rounds. Rounds are the second tie-break.

**7. Approval ladders (`approval_2pct`, `group_ladder`): smaller gap, one structural trade, a memo for the approver.**
- E: Nordmark conceded 0.93, 0.88, 0.30 and 0.07 EUR on about 370. It walked at 19 % cumulative gap with sheets 2-7 % below its counter. From an anchor of 345 it withdrew (`ea485d8c4db527aa`).
- E: A 5 % deadband CU clause at 358.00 was agreed at once, 4.3 % below the fixed price.
- I: Moves above the threshold need the boss. A structural trade gets approved where price steps stall.
- I, case-dependent (stabilise): the P02 record decodes to about 369.5 against C_best 368.34 at 90 d (learnings.md). Our 361.67 with a clause scored only 0.735, so near full cost plus long payment beats clause plus low price there. This is not in the diffs and needs a test.

**8. Spare capacity: deeper opening, and give contract length that costs us nothing.**
- E: The biggest first moves are 70250 Fuchsreiter at 0.163, 70610 Leitner at 0.146 and 70210 at 0.117. Fuchsreiter went 38.50→31.50.
- E: These suppliers ask for volume and a longer contract (`dossiers.json` asks).
- E: In `cost.py` `_years`, months beyond the horizon cost and earn nothing, so a longer contract is free for us.

**9. Stale costing: claims are the lever, spread over rounds.**
- E: P01 "We did not know that - a fair point"; the price moved 134.80→133.60 once. Price letters overshoot the driver move (P01: +9.5 % asked against +2.3 %).
- E: Claim effectiveness: notice period moved the supplier 100 % of the time, falling index 45 %, rising index "Your figures confirm our case" (NIGHT_CONTEXT).
- E: On D01, three claims spread over rounds gave 0.998; all at once gave 0.969 (relationship charge).

**10. Untested traits (`reference_customer`, `deprioritising_us`, `not_strategic`, `partnership_2022`): mainly tone, plus walk-risk control.**
- E (analogues): Ravensteiner finals in round 1 at 15 % gap; Nordmark walks at 19 %; others final at 36-42 % (learnings.md).
- E: Writer: 9 of 15 dropped paragraphs carried the year 2022 that the persona text handed the model.

**11. `open_book`: asking is free, but expect nothing.**
- E: 12 of 12 suppliers said "we do not share" a breakdown, the open_book-tagged one included. The brief says "an open supplier sends one".

## 2. Playbook per trait and archetype

Columns: opening depth / claims / trades / tone / never say. All prices stay at most 24 % below the standing price.

**Traits**

| Trait | Opening | Claims | Trades | Tone | Never say |
|---|---|---|---|---|---|
| **cash_need** | normal (open_frac 0.3); RFQ deep (job shops drop 12-15 %) | rival, should-cost, scorecard | shorter payment from round 1, priced at its rate (≥18 %); if payment is fixed: ppm/quality package plus on-time commitment | cash first; answer its payment ask every time (Kalwisz) | its credit, bank or finances |
| **complains_late_pay** | normal | normal; skip `otd` (otd 23 %, often rejected) | do not trade *longer* payment for price; commit to due-date payment (writer's ITS PAYMENT COMPLAINT) | answer the complaint first, plainly (I) | denial, blame, "as you know we pay…" |
| **spare_capacity** | deep (20 %) | rival, should-cost | longer contract (free beyond horizon), volume exactly = need, in figures | work for its shop | volume above need; anything unbacked by a sheet |
| **capacity_full** | normal | one strong claim (should-cost "taken into account") | longest lead time the must-have/late cost allows; 36 m; full volume; never buy speed | planning security | urgency, dependence |
| **price_frozen** | at its price | none needed (sc/po "do not change our calculation") | longest payment, contract, effective date; close in 1-2 rounds | "your price, our terms" | price arguments |
| **hedged** | normal (raw_material deep) | falling index yes; rising index never | fixed price; payment 90 (distributor rate ≈0); never a clause sheet from us; accept its clause only inside its standing sheet if C is lower | businesslike | "share index risk" |
| **stale_costing** | at or below today's price | notice (doc+ctr), falling driver, weighted driver vs letter, forecast; spread over rounds | 14 d only if its rate > ours | "please recheck your calculation" | rising indices |
| **approval_2pct** | shallower (open_frac 0.55) | the 1-2 best (an approver can forward them) | one structural trade (clause with deadband if clause worth ≥4 %, contract, volume) | approver-ready paragraph | many tiny steps |
| **partnership_2022** | normal; nothing aggressive (I) | notice, index; skip `po` price history | contract length, on-time payment | thank once, specifically | the year (writer guard); "your price is excessive" |
| **reference_customer** | normal | normal | longer contract | long, visible partnership (I) | promises of publicity not in sheets; switching threats |
| **deprioritising_us** | shallow (0.6); close early | one strong | lock lead time and contract | "easy, reliable customer to keep" | threats; dependence |
| **open_book** | normal | normal | — | ask for the breakdown politely, round 1 | — |
| **not_strategic** | normal; rival leads in RFQ | normal | — | short, one clear package (I) | — |

**Archetypes**

| Archetype | Tactic | Evidence |
|---|---|---|
| **family_foundry** (Brandlhuber; Leitner likely) | Negotiates down. Move share 0.62, final r5-6. Floor not binding (`NEGOTIATES_DOWN`). Spread claims. Owner to owner. | P01 129.50-129.80 → 0.987-0.995 (`1c9b55304adcb64f`) |
| **group_ladder** (Nordmark, Selvbrunn) | Small steps (move share 0.15). Payment is cheap for them (Selvbrunn ≈4 %/yr, Nordmark ≈0-6 %), so ask 90 d. Approver memo. | ANGLES_B "planning security +5.8 pp" is confounded (dossier.py comment) |
| **cash_short_jobshop** | As cash_need. Kalwisz priced 300 ppm at +0.50 over 1500. It ignored chargeback 500 twice. | `1f36a83c6e80e818`, `a74b89173c96c23c` |
| **near_monopolist** | Final in round 1, so the round-1 package must be complete: long lead, 36 m, full volume, should-cost claim. Firm, never adversarial. | P10 0.66-0.68 |
| **distributor** (not an archetype in `profile.archetype`) | First counter is insensitive to the anchor (0.787 and 0.85 of the quote both got 5.45/5.50). A slow walk of 12 %/round got five counters and 5.31 against 5.33-5.39 (`50502ff781d898c6`). Payment is free to them. Refuses 24 m fixed. | Gap: Werdenfels ("family distributor") gets `family_foundry` and so the "negotiates down" treatment. I suggest an `overrides.json` archetype, not code. |

**General never-say list:** urgency, budget or target, no alternative, rising indices, the supplier's finances, how we know anything, any digit in model prose.

## 3. Diffs

The design: a trait detector in `dossier.py` (profile notes, history notes, practice observations). It is cached in the profile and read by `policy.py`. Hunk line numbers are approximate; apply by context.

```diff
--- a/src/buyer/facts/dossier.py
+++ b/src/buyer/facts/dossier.py
@@ -48,6 +48,45 @@ PHRASES = {  # what a supplier said, as a short note in words
     "wants_clause": r"index clause|preisgleitklausel|alloy surcharge index|surcharge clause",
     "asks_for_proof": r"which figures|send us the data|provide (?:this|the) documentation",
 }
+# Persona traits readable before the first message (profile notes, news headlines, history notes).
+# Phrasings inferred from the trait names and notes seen so far - grep the package before relying on them.
+TRAITS = {
+    "hedged": r"hedg|bought forward|forward[- ](?:bought|purchas|cover)",
+    "approval_2pct": r"(?:above|over|more than|beyond) (?:2|two) ?(?:%|per ?cent)",
+    "partnership_2022": r"partnership in return|kept supplying at the old price|held (?:the|its|our) (?:old )?price",
+    "reference_customer": r"reference (?:customer|account|project|installation)|showcase",
+    "deprioritising_us": r"deprioriti|not a priority|focus(?:es|ing)? on (?:larger|bigger|other) customers",
+    "complains_late_pay": r"overdue invoice|late payment|paid late|pays? late",
+    "open_book": r"open[- ]book|shares? (?:its|their) (?:costs|calculation)",
+    "stale_costing": r"old (?:calculation|costing)|outdated (?:cost|calcul)|not (?:re)?calculated",
+    "spare_capacity": PHRASES["free_capacity"] + r"|second shift|idle (?:capacity|shift|machines)",
+    "capacity_full": PHRASES["full_capacity"] + r"|full order book|sold out|order backlog",
+    "price_frozen": r"price (?:is )?frozen|cannot (?:change|touch|move) (?:the|its|our)(?: list)? price",
+    "not_strategic": r"not (?:a )?(?:strategic|core) (?:customer|account)|small (?:customer|account)",
+}
+TRAIT_LINES = {  # for the writer: tone and what never to say; no figures, nothing about its finances
+    "hedged": "Its material is covered forward: ask for a fixed price and let the claim lines show its cost did "
+              "not follow the index; never offer to share index risk in words.",
+    "approval_2pct": "Bigger price moves need approval above our contact: one short paragraph the approver can sign, "
+                     "naming what Option A gives the supplier.",
+    "partnership_2022": "It held its price for us in a hard year: thank it once, specifically, never name the year, "
+                        "never call its price excessive.",
+    "reference_customer": "Being a visible, lasting customer matters to it: speak of a long partnership; promise "
+                          "nothing beyond the options and never hint at switching.",
+    "deprioritising_us": "We are not its priority right now: show we are an easy, reliable customer to keep - clear "
+                         "terms, quick decision; no threats, never hint we depend on it.",
+    "complains_late_pay": "If it raises our payments, answer that first and plainly; never ask for a longer payment "
+                          "term as a favour.",
+    "open_book": "It is open about its costs: welcome that and treat its figures as the basis for a fair price.",
+    "stale_costing": "Its price rests on an older costing: invite it to recheck its calculation against the claim "
+                     "lines; never argue with a cost driver that rose.",
+    "capacity_full": "Its capacity is tight: lead with the lead time and planning certainty in our options; never "
+                     "ask for speed it would have to buy with overtime.",
+    "price_frozen": "It does not move its price: do not argue price; present Option A as its price with better terms.",
+    "not_strategic": "We are a small account for it: be brief and decisive, one clear package.",
+}
 ANGLES = {
@@ -170,6 +209,22 @@ def observed(supplier_id: str, path: Path = DOSSIER_FILE) -> dict:
         return {}
 
 
+def traits(profile: dict | None, obs: dict | None = None) -> list[str]:
+    """Persona traits of the supplier from its notes, history notes, cash signals and what practice showed."""
+    p = profile or {}
+    o = observed(p.get("supplier_id") or "") if obs is None else obs
+    text = " ".join(str(n) for n in [*(p.get("notes") or []), *((p.get("history") or {}).get("notes") or [])])
+    out = [k for k, rx in TRAITS.items() if re.search(rx, text, re.I)]
+    said = set(o.get("said") or [])
+    if (p.get("cash_pressure") or 0) >= 0.35 or "needs_cash" in said:
+        out.append("cash_need")
+    for trait, key in (("spare_capacity", "free_capacity"), ("capacity_full", "full_capacity")):
+        if key in said and trait not in out:
+            out.append(trait)
+    return out
+
+
 def _movement(o: dict) -> str | None:
@@ -228,6 +283,11 @@ def dossier(profile: dict | None, obs: dict | None = None) -> str:
     if cares:
         lines.append("It cares about " + ", ".join(cares) + ".")
 
+    found = traits(p, o)
+    if profile is not None:
+        profile["traits"] = found  # read by the policy (policy.traits_of)
+    lines += [TRAIT_LINES[k] for k in found if k in TRAIT_LINES]
+
     drivers = _driver_words(o.get("drivers") or [])
```

The cash_need threshold of 0.35 is an inference from one supplier: Dralveck at 0.36 behaved cash-short.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -74,6 +74,24 @@ CLAIM_WEIGHT = {"notice": 1.0, "ppm": 0.75, "rival": 0.7, "cost": 0.6, "news": 0.55, "index": 0.5, "fc": 0.45,
 OWN_PRICE_SLACK = 0.005
 CASH_HUNGRY_RATE = 0.15
+MAX_OPEN_DISCOUNT = 0.24  # asks > 25 % below its price: "far below any calculation", a third of the concession
+SHALLOW_OPEN = {"approval_2pct": 0.55, "deprioritising_us": 0.6}  # open_frac where walks come at a small gap
+DEEP_OPEN_TRAITS = ("spare_capacity",)
+TRAIT_ASKS = {"cash_need": ("faster_payment",), "spare_capacity": ("longer_contract",),
+              "capacity_full": ("longer_lead_time", "longer_contract")}  # offered before it asks: round 1 decides
+
+
+def traits_of(t):
+    """Persona traits of t's supplier (buyer.facts.dossier.traits), cached in its profile."""
+    prof = t.profile if t.profile is not None else {}
+    if "traits" not in prof:
+        try:
+            from buyer.facts.dossier import traits
+
+            prof["traits"] = traits(prof)
+        except Exception:
+            prof["traits"] = []
+    return set(prof["traits"])
 
 
 @dataclass
@@ -207,9 +225,10 @@ class Policy:
     def next_price(self, t, theirs, step=None, case=None):
+        tr = traits_of(t)
         discount = self.p["min_open_discount_pct"]
-        if t.case_type in DEEP_OPEN_TYPES:
+        if t.case_type in DEEP_OPEN_TYPES or tr.intersection(DEEP_OPEN_TRAITS):
             discount = max(discount, self.p["deep_open_pct"])
         low = min(self.floor_ask(t, theirs), theirs * (1 - discount / 100))
         if case is not None and floor_binds(t):  # stabilise / secure_supply: below it the charge costs more
@@ -218,7 +237,11 @@ class Policy:
                 low = min(max(low, rel), theirs)
         t.holding = False
         if not t.our_prices:
-            price = low + self.p["open_frac"] * (theirs - low)
+            frac = max([self.p["open_frac"], *(SHALLOW_OPEN[k] for k in tr if k in SHALLOW_OPEN)])
+            price = max(low + frac * (theirs - low), theirs * (1 - MAX_OPEN_DISCOUNT))
+            if "price_frozen" in tr:
+                price = theirs  # it never trades price: ask for terms at its price
         else:
             last = t.our_prices[-1]
@@ -262,10 +285,12 @@ class Policy:
     def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
         b = case["buyer"]
+        tr = traits_of(t)
+        frozen = "price_frozen" in tr  # its price stands: the longest payment and best terms at that price
         base = {**t.standing_terms, "unit_price": price}
         if "payment_days" in case["negotiable"]:
             base["payment_days"] = b["reference_payment_days"]
-        a = self.best_options(case, complete_offer(case, base), t.standard, skip={"payment_days"})
+        a = self.best_options(case, complete_offer(case, base), t.standard, skip=() if frozen else {"payment_days"})
         a = self.adopt_structure(case, a, t)
@@ -281,12 +306,18 @@ class Policy:
         c_cap = self.c(case, t.standing_terms, t) if t.standing_terms.get("unit_price") is not None else math.inf
-        sheets = self.menu(case, t, a, c_cap) or [a]
+        sheets = [a] if frozen else (self.menu(case, t, a, c_cap) or [a])
         if t.last_sheet is not None and sheets[0] == t.last_sheet:
             t.holding = True
         asks = list((t.signals or {}).get("asks") or [])
-        if clause_wanted(case, t.signals) and "index_clause" not in asks and self.clause_worth(case, t) >= CLAUSE_WORTH:
+        for x in (x for k in sorted(tr) for x in TRAIT_ASKS.get(k, ())):
+            if x not in asks:
+                asks.append(x)
+        if "hedged" in tr:  # its cost is locked forward: keep fixed sheets; it may add its own clause
+            asks = [x for x in asks if x != "index_clause"]
+        elif clause_wanted(case, t.signals) and "index_clause" not in asks and self.clause_worth(case, t) >= CLAUSE_WORTH:
             asks.append("index_clause")  # it blames the driver a clause would follow: offer the clause
@@ -298,7 +329,7 @@ class Policy:
         questions = []
         notes = " ".join(str(n) for n in (t.profile or {}).get("notes") or []).lower()
-        if not t.asked_breakdown and not t.our_prices and "calculation" in notes:
+        if not t.asked_breakdown and not t.our_prices and ("calculation" in notes or "open_book" in tr):
             questions, t.asked_breakdown = ["cost breakdown"], True
@@ -323,7 +354,7 @@ class Policy:
         rate, pressure = self.cash(t)
         rate = ARCHETYPE_RATE.get((t.profile or {}).get("archetype"), rate or 0.08)
-        if pressure >= 0.5:
+        if pressure >= 0.5 or "cash_need" in traits_of(t):
             rate = max(rate, ARCHETYPE_RATE["cash_short_jobshop"])
@@ -333,7 +364,8 @@ class Policy:
         ppm = max(std.get("ppm_commitment") or 0, offered or 0, (t.profile or {}).get("ppm_actual") or 0)
-        lead = ARCHETYPE_LEAD_EFFORT.get((t.profile or {}).get("archetype"), 0.001)
+        lead = ARCHETYPE_LEAD_EFFORT.get((t.profile or {}).get("archetype"),
+                                         0.003 if "capacity_full" in traits_of(t) else 0.001)
         return {"standard": std, "interest_rate": rate, "usual_rate": 0.07, "ref_price": ref, "ppm": ppm,
@@ -548,7 +580,7 @@ class Policy:
             options = [v for v in (case.get("term_options") or {}).get(f) or [] if v is not None] \
                 or [v for v in t.struct_seen.get(f) or [] if v is not None]
-            if f in case["negotiable"] and insists and options:
+            if f in case["negotiable"] and insists and options and "hedged" not in traits_of(t):
                 out[f] = min(options, key=lambda v: self.c(case, {**out, f: v}, t))
```

**What each change does, and why:**

1. **Anchor cap (opening only).** It is applied to the opening price, not to `low`, so P05's held 27.86 (22.6 % below) is unaffected; only the 26.79-type anchor is blocked.
2. **Trait asks in round 1.** These reuse the existing `lever_trades` path and the ask vocabulary already in `dossiers.json` (`faster_payment`, `longer_contract`, `longer_lead_time`). `lever_values` still checks must-haves and the 5 % price-drop cap.
3. **Hedged.** We stop sending clause sheets. A clause the supplier puts into its own standing sheet can still be accepted at close if its C is lower. That is the P18 5.00 path (`e86f454a59ff98f0`).
4. **Price frozen.** The first sheet is its price with the cheapest-for-us options, including payment (the P03/P04 deal shape). The menu is skipped because its lower-price sheets are refused.
5. **Lead effort 0.3 %/day for capacity_full.** This is the value EVALUATION.md measured (`26e559b2`, P10 0.58→0.66). It now applies whatever the archetype.

**Deliberately left out (needs a test before shipping):**
- `complains_late_pay` and `partnership_2022` policy changes: the writer line only, since evidence is thin.
- A fixed near-full-cost sheet next to the clause for `approval_2pct` in stabilise cases (finding 7).
- A distributor archetype: use `overrides.json`, no code.

## 4. Before the freeze

1. **Detector check (offline, no quota).** Run `traits(lookup_profile(sid, part))` for all 46 suppliers and print the hits. Expected:
   - Donautal → hedged
   - Kalwisz → complains_late_pay and cash_need
   - Leitner and Fuchsreiter → spare_capacity
   - Ravensteiner and Hrvelec → capacity_full

   Any trait with zero hits means its regex misses the real phrasing: grep `data/` and the Sunday release for it. For price_frozen and approval_2pct the phrase may exist only in quote remarks or in the supplier's e-mail. If so, add the same `TRAITS` regex over supplier bodies in the reader's signals; that is a one-line follow-up I can't diff without the reader.

2. **Regression guards (one hosted run each, about 6 sessions):**

   | Case | What it checks | Watch for |
   |---|---|---|
   | P03, P04 | frozen | rounds fall, score ≥ 0.93 / 0.87 |
   | P05 | cap, cash_need | still about 27.86 / 14 d |
   | P08, P18 | hedged | no clause sheet sent by us |
   | P10 | capacity_full | still at 0.66 or better |
   | P07 | spare_capacity deep open | Leitner finals in r3; check that no walk-away appears |

3. **Noise.** Practice suppliers vary 1-2 % between identical runs, and P08 spread 0.47-0.72 for the same first ask. Treat one run as a guard against breakage, not as proof of gain.