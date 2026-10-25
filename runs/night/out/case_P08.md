# P08 (Donautal, stainless distributor, hedged until 03/2027): analysis and proposed changes

## Basis: the cost decode, checked against our own logs

I solved two of our own sessions and verified the result on the rest (every score fits to ±0.0005). Values marked † are inferences from that fit, not read from a file.

- Need is 94,800 units a year over 2 years.
- Interest is 8 %/yr; reference payment is 60 days.
- The index clause has `material_share` 0.45 on AS-14404.
- †The index path is +6 % and `index_risk_pct` is 1 %. So a 0 % deadband clause costs 3.15 % of spend and a 5 % deadband clause costs 0.90 %.
- †C_open ≈ €1,135,890 and C_best ≈ €960,310. One score point (0.01) is about €1,756.
- †C_best matches "5.10 fixed" or "4.94 with a 0 % clause" from `learnings.md` only at **90-day payment** (960,514 / 959,932). At 60 days the same prices give about 966.5k.
  - Inference: the hidden best package includes 90 days. That is weak but real evidence that this supplier accepts 90 days.
- †The record of 0.916 means C ≈ 975.1k. With this supplier's mandatory 0 % deadband clause, that is about **5.02 at 90 days** or 4.97 at 45 days.
  - The "record 5.21–5.35" in NIGHT_CONTEXT and learnings does not fit this decode at any payment term. I would drop it.

**Effective price** below means C ÷ 189,600, i.e. a fixed price at 60 days. It makes clause and non-clause deals comparable.

| Session | Deal | Effective price | Score |
|---|---|---|---|
| 84890ecf, 776dccc0, e7fe5b7e | 5.40 / 60 d / db0 | 5.570 | 0.454 |
| fbbf38c9 | 5.39 / 60 d / db0, 36 months | 5.560 | 0.466 |
| ff799fbc | 5.28 / db0 | 5.446 | 0.588 |
| 66c34341 | 5.36 / 60 d / db5 | 5.408 | 0.629 |
| 557c4428 | 5.34 / 60 d / db5 | 5.388 | 0.651 |
| f6c1bff5 | 5.36 / 90 d / db5 | 5.372 | 0.668 |
| 9b159f07 | 5.20 / 60 d / db0 | 5.364 | 0.677 |
| 201eeaab | 5.35 / 90 d / db5 | 5.362 | 0.679 |
| be2d7196 | 5.29 / 45 d / db5 | 5.355 | 0.686 |
| 7976d643 | 5.05 / 45 d / db0 | 5.226 | 0.826 |
| **55d090be** | **5.04 / 45 d / db0** | **5.216** | **0.837** |
| 76b7cbbb | timeout after final_offer → walked | – | 0 |

---

## 1. How the supplier responds (evidence first)

### 1.1 Structure: 24 months only with a 0 % deadband clause

- Every one of the 13 counters to a 24- or 36-month request carries an AS-14404 clause. The supplier says this explicitly, e.g. 7976d643 r2: "the AS-14404 index clause remains mandatory".
- It prefers no deadband (e7fe5b7e r3: "does not include a deadband, ensuring immediate and fair adjustments").
- 12 months can be fixed (winners' probe: 5.93 / 90 d / 12 m). But 12 months leaves half the need uncovered at the fallback (~5.72 × 1.03), so it is useless to us.
- 36 months gained nothing: first counter 5.54 against 5.28/5.29 for 24 months with the same anchor (n = 1, and claims were also absent). Months beyond the horizon are worth nothing to us anyway.

### 1.2 The first counter depends mostly on whether a deadband sheet is on the table

| Our first message | First counter | n |
|---|---|---|
| All fixed, asks 5.38–5.54; claims: delivery record + price history | 5.40 / db0 | 3 |
| All fixed, asks 4.82–4.96; claims: delivery record + price history | 5.28, 5.29 / db0 | 2 |
| All fixed, asks 4.95–4.99 incl. a 45-day sheet; claims: index ×2 + price history | 5.20, 5.21, 5.20 / db0 / 45 d | 3 |
| One db5 sheet among fixed ones; claims: delivery + price history | 5.51 / db5 | 1 |
| Same, claims: index ×2 | 5.60, 5.63, 5.60 / db5 | 3 |
| Same, claims: index ×2 + price history | 5.48 / db5 | 1 |
| All fixed, 36 months, no claims | 5.54 / db0 | 1 |

What this shows:

- **When a db5 sheet is on offer, it picks that sheet** and answers 0.28–0.43 higher in unit price. The deadband is worth about 2.25 % of spend to us, roughly 0.12. The db5 counters are therefore worse even after adjusting for the clause (effective about 5.53 against 5.38).
- With all-fixed sheets it attaches db0 itself. It answers at or below our fixed ask when the ask is high (5.40 against our 5.54).
  - Inference: it measures distance in unit price and treats its own clause as free. That is why low fixed sheets pull its db0 price down.
- Its first concession saturates at about −14 % (6.05 → 5.20). A deeper anchor below about 4.95 is untested.
- The index ×2 claims draw "not our reality … covered at fixed prices until March". Yet those runs had the lowest first counter (5.20). This is confounded by the payment menu and sits within noise. `learnings.md` reports the same pattern.

### 1.3 Later rounds

- **Fixed sheets kept throughout** (7976d643, 55d090be): 5.21 → 5.14 → 5.05, and 5.20 → 5.15 → 5.04.
  - The r3 step is larger (−0.09 / −0.11) and comes with "escalated to management".
  - Our own moves were only +0.02 to +0.03. Total movement after r1 was −0.16 (3 %).
- **Its db0 adopted by us** (fbbf38c9): −0.05, −0.04, −0.06.
- **db5 sessions**: −0.13 to −0.25 in r2, partly because it switched to a db3 it proposed itself. Then −0.03 to −0.05, then final.
- **Switching back from db5 to fixed sheets mid-way** (ff799fbc): it held 5.28 and went final.

### 1.4 When it goes final, and when it agrees

- **final_offer**:
  - At once on identical sheets: 776dccc0 r3, e7fe5b7e r3, 7976d643 r4, 55d090be r4. That is 4/4, always at the unchanged price, with "your options remain unchanged".
  - Otherwise at r3 after a tiny move (ff799fbc: "slight increase … not sufficient"), or at r4 at the latest.
  - It never went final later than r4 across 13 deals.
- **agreed**: only when we sent back a package worth at least as much to it as its final.
  - 557c4428: final 5.30 db3 → we sent 5.34 db5 → agreed.
  - 66c34341: final 5.40/90 db5 → we sent 5.36/60 db5 → agreed.
  - Winners: we matched 5.93 → agreed and frozen ("Our agreed offer stands" ×4).
  - Two out of two post-final variant messages were agreed. None walked.
- **walked_away**: after one buyer timeout following final_offer (76b7cbbb). This is a transport problem, not a tactic, but it cost a full case.

### 1.5 Levers it values

- **Deadband: priced at about share × width.** This is the cleanest inference in the logs. In three sessions the step from db3/60 d to db5/90 d was +0.04, +0.04 and +0.05: 201eeaab 5.31 → 5.35, f6c1bff5 5.32 → 5.36, 66c34341 5.35 → 5.40. Two deadband points × 0.45 ≈ 0.9 % ≈ 0.048, which leaves about 0 for 30 extra days of payment.
  - Against this: when offered 4.99/90, 4.96/60 and 4.95/45, it chose 45 d, and in 9b159f07 it said shorter payment "allows us to offer a more competitive price".
  - So its payment rate is somewhere between ~0 and ~8 %/yr. Unresolved.
- **Contract length**: 24 months welcomed as "planning security" but only with the clause. Volume was asked once in the winners' probe; volume is fixed at the need here.
- **Claims**:
  - Price history: "took into account" in 9 of 10.
  - Delivery record: "does not change our calculation" in 9 of 9.
  - Index falls: "not our reality" (hedge).
  - It never shares a cost breakdown.

### 1.6 What it says it wants

- An index clause with no deadband for any period beyond 12 months.
- Recognition of its hedge.
- **Proof for our writer's assertion that the clause removes a risk premium.** It asked four times: 76b7cbbb r3, 201eeaab r3–r4, f6c1bff5 r3–r4, be2d7196 r3. In be2d7196 it went final explicitly because the proof never came: "we must otherwise hold our offer".
- Respect for its authority: "I am fully authorized…", said twice in f6c1bff5 after our "take Option A to your decision-maker" paragraph.
- Offers of a call or meeting.

---

## 2. Best deal in the logs and what produced it

**55d090be, score 0.837: 5.04 / 45 d / 24 months / db0** (7976d643 is the near-twin at 5.05, 0.826). What produced it:

1. **Round 1:**
   - Three fixed sheets at roughly equal value to the supplier: 4.99/90, 4.96/60, 4.95/45.
   - Three claims: index ×2 and price history.
   - Result: 5.20 db0 at 45 d. It picked the lowest-price sheet, which is also the one dearest for us in C.
2. **Rounds 2–3:** we never adopted its clause.
   - Under the current code, `adopt_structure` reverts the clause because `clause_worth` ≈ 0.45 × 5.9 % = 2.7 %, which is below `CLAUSE_WORTH` (4 %).
   - We stepped +0.02 to +0.03 per round. It conceded −0.05, then −0.11 at "management".
   - It sees itself 0.04 apart from us; in C the real gap is 3.8 %.
3. **Round 4:** our sheets were identical → immediate final at the same price → accept.

**Near-controlled comparison.** be2d7196 had the same r1 sheets, the same claims and the same 5.20 counter. In r2 it offered db5 clause sheets and ended at 5.29 db5 (0.686), against 0.826 and 0.837 for keeping fixed sheets. That is **−0.14 from proposing a deadband** (n = 1 against 2). It is consistent with e7fe5b7e, where db5 at the same price was refused ("index clause as originally proposed").

---

## 3. Where the current agent leaves value

Current state: 0.826 / 0.837. Best logged: 0.837. Record: 0.916, a gap of about €13.9k.

1. **Payment term: about +0.054 available (best estimate).**
   - We close at 45 days, which costs €3,185 against the 60-day reference.
   - The same price at 90 days would cost €979.3k instead of €988.9k: **+0.054, score about 0.89**.
   - The supplier's price for days ranges from free (the deadband-step inference) to about 7 %/yr. At 7 %/yr the gain is only about +0.006.
   - The C_best decode suggests 90 days is in its acceptable set.
   - The 45-day choice is a side effect of the r1 menu: equal value to the supplier, and it picks the lowest price. Nothing later re-opens payment. `close()` only builds variants for the index clause, and only when the status is `open`. On `final_offer` it accepts directly.
2. **A wasted round on identical sheets.**
   - In r4 our sheets were byte-identical to r3. The cause is in `offer()`: it sets `t.holding = True` when `sheets[0] == t.last_sheet`, and that disables the guard in `decide()` (`... and not t.holding`).
   - The identical message buys nothing (4/4 finals at an unchanged price) and wastes the round in which a variant could have been offered.
3. **The 0 % deadband clause itself, €30.1k (≈ 0.17).** This is the structural gap to C_best.
   - The supplier refuses db5 at an equal price, and prices db5 at about its value to us.
   - So I see no general lever here, beyond not making it worse by offering a deadband.
4. **The remaining ~0.025 to the record** is roughly 0.02/unit of price.
   - Plausibly reachable if the r3 "management" step comes from a lower base. Untested, inside noise, no change proposed.
5. **The writer's risk-premium line and the decision-maker paragraph.**
   - These provoked repeated data demands and one explicit final from a hedged supplier.
   - In the current all-fixed path the clause rule does not fire, so the impact on P08 today is small. Hedged and `approval` personas are explicitly expected in the final.
6. **Timeout after a final offer → walk (1 of 14).** This is a runner and transport issue; I flag it only.
   - Every extra post-final message (change 1) is one more 60-second window. It must use the template fallback when the model is late.

Noise: in our latest code the r1 counter repeated at 5.20 / 5.21 / 5.20 and the finals at 5.05 / 5.04, so the noise is about 1 %. But n = 3. `learnings.md` reports 0.47–0.72 spreads on older paths.

---

## 4. Proposed changes

### Change 1 (largest expected gain): closing variants also cover payment, and also after `final_offer`

**Rule:** before accepting an acceptable `open` or `final_offer` sheet, send once:

- the supplier's own package as the last sheet, and
- up to two variants that change one term to the option cheapest for us: index deadband or payment days. The payment variant is skipped for cash-hungry suppliers, using our supplier model's rate.

The variants are sorted by our gain.

**Expected effect on P08:**
- It agrees to the 90-day variant: about +0.054.
- It picks its own package: 0 change, with "agreed" or a repeated final either way, after which we accept because `clause_countered` is set.
- The db5 same-price variant will very likely be refused (e7fe5b7e). It costs nothing.

**Evidence that post-final variants are safe here:** 2 of 2 agreed. P10 also kept answering after its round-1 final in `learnings.md`.

**Risk:**
- One extra round, and exposure to a timeout.
- A supplier might read the message after a final as a push (D01 walked on a sheet *below* its final; ours always includes the final unchanged).
- Cash-short shops are excluded by the rate guard.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@
 PARAMS_FILE = Path(__file__).with_name("params.json")
 STRUCTURAL = ("index_clause",)
+VARIANT_LEVERS = ("payment_days",)  # closing variants: its package with this term at our cheapest option
 CASH_LEVERS = ("payment_days", "incoterm", "tooling_eur")  # where our estimate of the supplier's gain holds
@@ def close(self, case, t, acceptable, c_theirs, rival_best_c):
                 intent = "appreciative: we accept your alternative proposal as offered"
                 if variants:
-                    intent += "; we would prefer the same with a wider index deadband"
-                return Decision("send", t.supplier_id, term_sheets=[*variants, sheet][:3], intent=intent)
-        if acceptable and t.status == "open" and t.rounds_left > 1 and not t.clause_countered:
+                    intent += "; we would prefer the same with one term changed"
+                return Decision("send", t.supplier_id, term_sheets=[*variants[:2], sheet], intent=intent)
+        if acceptable and t.status in ("open", "final_offer") and t.rounds_left > 1 and not t.clause_countered:
             variants = self.clause_variants(case, t, complete_offer(case, dict(t.standing_terms)))
             if variants:  # one more message before closing: its own package stays on the table as the last sheet
                 t.clause_countered = True
                 own = complete_offer(case, dict(t.standing_terms))
                 t.our_prices.append(own["unit_price"])
                 t.our_costs.append(self.c(case, own, t))
-                return Decision("send", t.supplier_id, term_sheets=[*variants, own][:3],
-                                intent="appreciative: we can agree to your offer; we would prefer it with a wider "
-                                       "index deadband")
+                return Decision("send", t.supplier_id, term_sheets=[*variants[:2], own],
+                                intent="appreciative: we can agree to your offer as it stands (the last option); "
+                                       "we would prefer one of the first options, each changes one term only")
         return self.accept(t) if acceptable else Decision("walk", t.supplier_id)
@@ def clause_variants(self, case, t, sheet):
         out = []
-        for f in STRUCTURAL:
+        for f in (*STRUCTURAL, *VARIANT_LEVERS):
             if f not in case["negotiable"] or sheet.get(f) is None:
                 continue
-            options = [v for v in (case.get("term_options") or {}).get(f) or [] if v is not None]
+            if f in VARIANT_LEVERS and self.supplier_model(case, t)["interest_rate"] >= CASH_HUNGRY_RATE:
+                continue  # a cash-short supplier reads later payment at its price as ignoring its ask
+            options = [v for v in (case.get("term_options") or {}).get(f) or []
+                       if v is not None and must_haves_ok(case, {**sheet, f: v}, t.standard)]
             if not options:
                 continue
@@
                 if equal_cost not in out and equal_cost != sheet:
                     out.append(equal_cost)
-        return out
+        return sorted(out, key=lambda s: self.c(case, s, t))  # our largest gain first; equal-cost ones last
```

The cap of two variants also fixes a latent bug: the old `[*variants, own][:3]` would drop the supplier's own package once there are three or more variants.

### Change 2: identical sheets close instead of being re-sent

**Rule:** if the full sheet list repeats our last message, the offer is acceptable, and no new claim is attached, go to `close()`. With change 1 that means the variant message instead of a dead round.

**Expected effect on P08:**
- At an unchanged price: the r4 identical message is replaced by the variants message, one round earlier.
- On its own (without change 1): accept at r4 instead of final at r4. Neutral, and one round faster, which helps the tie-break and the wave cap.

**Evidence:** identical sheets drew 4 of 4 finals at an unchanged price here. `learnings.md` reports the same for D01 ("a constant sheet got no concession").

**Risk:** with `reciprocity` enabled, a deliberate "hold" whose sheets come out identical now closes. The evidence says such holds never bought a move.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ class ThreadState:
     asked_breakdown: bool = False
     clause_countered: bool = False  # we offered its package with a wider index deadband once before closing
+    last_sheets: list | None = None  # the full sheet list of our last message
+    repeated: bool = False  # this message's sheets equal the last message's (suppliers answer that with a final)
@@ def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
         prev = t.last_sheet
         decision = self.offer(case, t, self.next_price(t, theirs, case=case), rival_best_c=rival_best_c)
-        if prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding:
+        same = t.repeated and not decision.claims  # nothing new for it: a resend only provokes "unchanged"
+        if acceptable and prev is not None and (same or (decision.term_sheets[0] == prev and not t.holding)):
             return self.close(case, t, acceptable, c_theirs, rival_best_c)
         return decision
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
             if not t.asked_breakdown:
                 questions, t.asked_breakdown = ["cost breakdown"], True
+        t.repeated = sheets == t.last_sheets
+        t.last_sheets = list(sheets)
         t.last_sheet = sheets[0]
         t.our_prices.append(a["unit_price"])
```

### Change 3 (low risk, mainly for hidden hedged or approval personas): writer stops unbacked assertions

**Rule:**
- Do not pitch the clause as removing a risk premium when the supplier says its material is hedged or bought at fixed prices.
- Never promise data we do not attach.
- Drop the decision-maker paragraph once the supplier says it can decide.

**Expected effect on P08:** small. In the all-fixed path the clause pitch does not fire. It does remove the be2d7196-type early final where a db5 or variant sheet is present, including change 1's variants.

**Risk:** slightly weaker clause framing for non-hedged suppliers is avoided, because the rule is conditional on the supplier's own statement.

```diff
--- a/src/buyer/llm/prompts/writer_system.md
+++ b/src/buyer/llm/prompts/writer_system.md
@@ HOW TO WIN THE REPLY
-2. Solutions, not counter-arguments. If it blames a cost (copper, alloy, steel, energy) and our options include an index clause (see CLAUSE IN OPTIONS), present the clause as the answer: we take that risk above the deadband, so the base price no longer needs a risk premium. If it wants cash, volume, a longer contract or its standard payment term, point to the option that gives it - only if an option really does.
+2. Solutions, not counter-arguments. If it blames a cost (copper, alloy, steel, energy) and our options include an index clause (see CLAUSE IN OPTIONS), present the clause as the answer: we take that risk above the deadband, so the base price no longer needs a risk premium. If it says its material is hedged, bought forward or covered at fixed prices, never speak of a risk premium; present the clause only as the planning security it asked for. If it wants cash, volume, a longer contract or its standard payment term, point to the option that gives it - only if an option really does.
@@
-5. The person who decides. Follow the DOSSIER: if our contact needs approval or has little authority, add one short paragraph its decision-maker can approve as it stands - what Option A gives the supplier, in plain words - and ask our contact to take Option A to that person.
+5. The person who decides. Follow the DOSSIER: if our contact needs approval or has little authority, add one short paragraph its decision-maker can approve as it stands - what Option A gives the supplier, in plain words - and ask our contact to take Option A to that person. If our contact has said it is authorised to decide, never suggest anyone else again.
@@ LATER E-MAILS
 - If it asked us a question, answer it in words or say that the options answer it - never leave it hanging.
+- If it asks for data or figures behind a statement of ours that no claim line supports, do not repeat the statement and do not promise data; say plainly that our options stand on their own.
@@ HARD RULES
 7. No quotation marks: write a paragraph for its decision-maker as plain text, not as a quote.
+8. Never offer, announce or promise data, figures, calculations or documents. Only the claim lines carry data.
```

### Not changed (evidence too thin)

- **A deeper r1 anchor than about 4.95.** The first concession saturates around −14 %, and the >25 % "far below" effect is documented elsewhere.
- **Dropping the delivery-record claim in r2.** 9 of 9 were rejected, but there is no sign of harm; it falls through because `strong or pool` re-admits weak claims once the strong ones are used.
- **Menu ordering.** The supplier picks the lowest-price sheet, so our cheapest-for-us 90-day sheet never wins in r1. Change 1 recovers this at the close with less risk.

**Validation plan (P08 plus guards):** run P08 three times, plus one run each of P01, P05 and P10 to check that the post-final message does not trigger a walk. Track whether the 90-day variant is taken, and every `walked_away` after a final.