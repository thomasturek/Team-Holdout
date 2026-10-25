# P02 (Nordmark, group_ladder, stabilise): supplier model, value gap, changes

## Bottom line

Our current agent makes 0.7345 on P02 (`e560d673`, `2882d2eb`, identical runs). It agrees in round 1 at 361.72 €, 90 days, with a CU-NOTATION clause at a 5 % deadband. This is the best deal in all 15 logged sessions.

Within the clause structure there is almost nothing left. The relationship charge already sits near its minimum, and the clause carries a fixed index-risk cost of about €17.7k. The record of 0.847 decodes to a **fixed-price, no-clause** deal at about 368–369.5 € at 90 days. Nordmark's fixed path never went below 373.65 € at 90 days in our logs. The remaining value is therefore structural, not more haggling.

I propose two general changes, plus a short list of checks before running them:
1. A one-shot "release" probe after a clause agreement, with a restore of the agreed package if the probe backfires.
2. The writer wording for that probe.

---

## Findings, ranked

### F1. The cost arithmetic caps the clause path at about 0.75; the record needs a fixed price

**Evidence: our cost breakdowns.**

| Item | Value | How it was obtained |
|---|---|---|
| Volume | 6110 pcs | 371.6 × 6110 = 2,270,476 exactly (`e2b20240`), so the horizon is 1 year and starts at the effective date |
| Payment rates | reference 60 d, buyer 8 %/yr | `d8613777`: 2,283,002 × 0.08 × 30/360 = 15,220 |
| Index risk | 4 % on a 0.2 material share | `cda59278`: 17,392 / (2,173,999 × 0.2) = 4.0 % |
| Index clause at 5 % deadband | €0 | the index-clause line is absent from the breakdown, so path ≤ +5 % |
| Index clause at 0 % deadband | 1.8 % of spend | learnings; implies path = +5 % (0.2 × (0.05 + 0.04) = 1.8 %) |
| C_open | 2,282,867 | 370.96 × 6110 + 15,110 (30 d early) + 1,191 quality; matches the scores |
| C_best | ≈ 2,235,515 | solved from two score/C pairs |
| Score denominator | 47,353 € | C_open − C_best |

| Deal (sessions) | C | Relationship charge | Score |
|---|---|---|---|
| 372.2 / 60 d fixed (`24bac3e3`, `e36d2ea9`) | 2,275,333 | 0 | 0.159 |
| 371.58–371.7 / 60 d fixed (`e2b20240`, `1782088a`, `c75e3d16`) | 2,271.5–2,272.3k | 0 | 0.224–0.239 |
| 373.65 / 90 d fixed (`d8613777`) | 2,268,973 | 0 | 0.293 |
| 355.81 / 60 d / CU db5 (`cda59278`, `20cb611e`) | 2,253,957 | 61,375 | 0.611 |
| 359.59 / 60 d / CU db5 (`fe77cf7f`, `f73f076a`, `b1108895`) | 2,250,474 | 34,611 | 0.684 |
| **361.72 / 90 d / CU db5 (`e560d673`, `2882d2eb`)** | **2,248,085** | **33,838** | **0.7345** |
| Record (NIGHT_CONTEXT) | ≈ 2,242,760 | ? | 0.847 |

**Inference from a fit of the three relationship charges plus learnings' 5,483 / 901.** This fit is model-dependent; the residuals are about 1k €.

- **Supplier rate.** Nordmark's cost of money is about 6–7 %/yr. Two observations agree:
  - Its 90-day sheet is priced about 1.03 % above 30 days (370.5 → 374.32, winners `680eb114` r1→r2).
  - 361.72 @ 90 d and 359.59 @ 60 d draw almost the same charge (33.8k vs 34.6k). That solves to r ≈ 7 %.
  - This contradicts learnings' "cost of money about 0".
- **Other fitted parameters.** Full cost is about 368 € and the relationship rate about €32k per margin point².

**Why the clause path is capped.**
- In the 90 d clause structure, dC/dp at 361.72 is only about +€250–300 per € of price. The relationship charge eats almost every euro of price cut.
- The C-optimum is about 360.9, worth ≤ €1k, i.e. ≤ +0.02.
- Add the index risk of 0.8 % of spend (~€17.7k), which no deadband removes. The clause path cannot exceed roughly 0.75.

**What reaches the record.** Only removing the clause does. A fixed price at 90 d breaks even with our deal at about 369.7 €. It reaches the record at about 368.3–368.5 € under my fit (learnings decode 369.5 under theirs).

C_best is defined as a package the supplier "would ever accept". Its value (2,235.5k) is below the clause-path minimum (~2,247k). So C_best itself must be a no-clause package, which means **Nordmark accepts some fixed ~366–369 € @ 90 d deal under some lever set.** This is an inference from the score definition, not an observation.

### F2. Nordmark's response function

**First counter (fixed sheets).** It is insensitive to anchor and claims and depends only on the payment term of the sheet it answers:

- Formula: counter ≈ 370.96 × (1 + 0.062 × (d − 30)/360) − ~0.45 €.

| Payment term | Predicted | Observed |
|---|---|---|
| 30 d | 370.5 | 370.5 / 370.6 (winners, anchors 359.83 / 363.7) |
| 45 d | 371.0 | 371.2 (`d8613777`) |
| 60 d | 372.4 | 372.55 / 372.55 / 372.6 / 372.65 / 372.55 (five sessions, anchors 339.74–358.66) |
| 90 d | 374.3 | 374.32 (winners r2), 374.05 (ours r2) |

- Anchor depth (−8.4 % vs −3.4 %) changed nothing.
- Claims changed nothing measurable: 0 claims gave 372.55 twice, 2 claims gave 372.6 and 372.65. That spread of +0.05 to +0.10 is noise-sized.

**Later rounds (fixed path).**
- Steps of 0.35 / 0.30 / 0.30 (`e2b20240`), 0.35 / 0.25 / 0.25 (`1782088a`), 0.19 / 0.16 / 0.10 (`24bac3e3`) and 0.18 / 0.10 / 0.07 (`e36d2ea9`).
- Total 0.35–1.02 € from round 1 to round 4.
- Bigger moves of ours (~4 €/round) got slightly more (0.85–1.02) than small ones (~1.5 €/round, 0.35–0.45). Reciprocity is about 0.08–0.25.

**`final_offer`.**
- Round 4 in 6 of 6 fixed sessions, regardless of our step size.
- Never earlier: 0 of 13 round 1–3 replies were finals.
- It never walked in these 15 sessions.

**`agreed`.**
- Any sheet with CU-NOTATION at a 5 % deadband at ≥ 355.81 € was agreed instantly in round 1: 7 of 7 sessions (355.81 / 60, 359.59 / 60, 361.72 / 90). Its floor with a clause is therefore ≤ 355.81 @ 60 d.
- Its fixed final was 371.6 @ 60. The clause is worth ≥ 15.8 €/unit (≥ 4.3 %) to it, consistent with NIGHT_CONTEXT's ~9.5 % estimate.
- When offered fixed 361.85 / 90 next to clause 361.72 / 90 (`e560d673`), it took the clause.
- Winners got `agreed` by sending its own 0 % clause back (`680eb114`, `d52ccdd3` r3).

**After `agreed`.**
- A lower price on the same package got "Our agreed offer stands", and the agreed sheet **stayed standing**. This happened 4 times across `680eb114` r4, r5, r6 and `d52ccdd3` r6. Learnings report 16 of 19 such replies across suppliers, none listed as losing an agreed sheet.
- A *different* package was agreed anew once: `d52ccdd3` r4, 366.41 @ 14 d after 369.12 @ 90 d.

**Levers it values.**
- **Index clause.** Very highly valued.
- **Payment days.** Priced at about 6–7 %/yr. This is below our 8 %, so 90 d is a small net gain for us (~0.15 % of spend).
- **Arguments.**
  - Quality record: 9 of 9 times "does not change our calculation".
  - Rising LCI-C: "Your figures confirm our case" (`c75e3d16`, `24bac3e3`, winners r5).
  - Should-cost 374.95, which is *above* its quote, was "taken into account" (winners). That is self-harm.

**What it says it wants.**
- Coverage of copper and labour costs.
- "Which volume can you commit to?" / "an increase in order volume would be necessary" (both winners' sessions, r1).
- Its standard payment term ("our standard and preferred payment term is … days net", `c75e3d16` r3–r4).
- Copper documentation: `c75e3d16`'s e-mail implied we had copper data without a claim, and drew three data requests.
- It never shares a cost breakdown.

**Noise and text reliability.**
- Clause sessions are deterministic to the cent for identical sheets: 3× 359.59, 2× 355.81, 2× 361.72. Fixed-path finals vary by ±0.6 €.
- Supplier prose regularly contradicts its sheet:
  - `e560d673`: "a fixed price without an index clause", while the standing sheet has the clause.
  - `24bac3e3`: "Building on your Option C … 30-day", while the standing sheet is at 60 d.
- Only `term_sheets` should be trusted.

### F3. The best deal and what produced it

`e560d673` and `2882d2eb` scored 0.7345. Round 1 offered two sheets, 361.85 / 90 fixed and **361.72 / 90 / CU db5**, plus one quality claim. The supplier answered `agreed` on the clause sheet, and we accepted in round 1.

It came from three things the code already does:
- **Deadband choice.** The 5 % deadband equals the case's +5 % path, so the clause line is €0 and we pay only the 0.8 % risk.
- **Payment term.** 90 days captures the 8 % vs ~7 % rate gap (−€14.7k against 359.59 / 60 d).
- **Price level.** The price sits at the relationship floor (`relationship_floor` via `next_price` and `menu`). Going lower to 355.81 raised the charge by €27k for a €23k price cut.

### F4. Where the current agent leaves value

- **Against the best ever: nothing.** It *is* the best ever.
- **Against the record: 0.112, about €5.3k.** None of it is reachable within the clause structure (F1). It needs a fixed sheet ≤ ~368.5 @ 90 d; break-even is 369.7.
- **Against C_best: €12.6k.**
- **What the agent never does.** It never tests whether Nordmark would trade the clause back for a fixed price once it has agreed. `decide` accepts any acceptable `agreed` at once (policy.py `decide`, the `if t.status == "agreed": if acceptable: return self.accept(t)` branch).
  - The evidence above shows such a probe is cheap: a rejected new package left the agreed sheet standing every time we saw it.
  - The one real risk is a counter on the fixed sheet replacing the agreed one. Re-sending the agreed package would very likely be re-agreed (7 of 7 instant agreements on db5 sheets), but this is not proven.
- **Fixed haggling is a dead end.** The fixed path ends at 373.65 @ 90 (0.293). The supplier's fixed-price concessions total ≤ ~1 € and its final comes in round 4. More rounds or bigger steps do not help.

### F5. The winners' probes in the digest are not the record and scored 0

The digest shows no scores for them, so I computed C myself with path +5 % and risk 4 %.

| Winners' deal | Spend | Payment | Index | Risk | Relationship | Quality | C |
|---|---|---|---|---|---|---|---|
| 368.70 / 90 / db0 | 2,252,757 | −15,018 | +22,528 | +18,022 | +5,483 | +1,191 | ≈ 2,285.0k |
| 366.41 / 14 / db0 | — | — | — | — | — | — | ≈ 2,304k |

Both are above C_open, so they clip to 0. Do not copy their structure: a 0 % deadband clause, should-cost above the quote, rising-index claims.

What they *do* show is useful: pushes after `agreed` never cost them the agreement (4 of 4).

### F6. Secondary levers (unverified negotiability; check the case file before acting)

- **Contract length.** If `contract_months` is negotiable, a contract beyond the 1-year horizon costs us €0 in C. It might answer the "volume commitment" ask.
  - Not observed: our P02 sheets never varied it.
  - Learnings saw no price gain from contract length at P03, P04 or P10.
- **Chargeback.** If `chargeback_eur_per_complaint` is negotiable, quality costs us at most €1,191. That is irrelevant at this scale.
- **Longer payment.** If `payment_days` allowed 120, my fit says the clause path at 120 d would reach about 0.83. But the menu already prices every option and chose 90, so 120 is probably not on offer.

---

## Proposed changes

### Change 1: release probe after a clause agreement, plus restore (policy.py)

**Rule.** It is general, keyed only to observable state:
- the supplier has **agreed** to a package carrying an index clause;
- the case allows `index_clause: null`;
- removing the clause would save us ≥ 0.5 % of C at the same price;
- ≥ 3 rounds are left.

**What it does.** Once, send the same package without the clause. Price it by bisection so that our C sits halfway between the agreed C and the fixed-at-same-price C. Then:
- If the reply is `agreed`, or an open counter cheaper for us than the agreed C, the normal accept / close path takes it.
- If the reply is an *open* counter dearer than the agreed C, re-send the agreed package exactly, once.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ -73,6 +73,8 @@
 OWN_PRICE_SLACK = 0.005
 CASH_HUNGRY_RATE = 0.15
+RELEASE_SHARE = 0.5  # release probe: our C this share of the clause's cost below the agreed C
+RELEASE_MIN = 0.005  # probe only when dropping the clause saves us at least this share of C at the same price
 
 
 @dataclass
@@ -121,6 +123,8 @@
     holding: bool = False  # this move we hold our price and change the package instead
     asked_breakdown: bool = False
     clause_countered: bool = False  # we offered its package with a wider index deadband once before closing
+    released: bool = False  # we offered an agreed clause package without its clause once
+    agreed_sheet: tuple | None = None  # (C, terms) of the cheapest package it agreed to
 
 
 def floor_binds(t):
@@ -165,9 +169,15 @@
             t.opening_payment_days = t.standing_terms.get("payment_days")
         acceptable = self.acceptable(case, t, c_theirs, rival_best_c)
+        if t.status == "agreed" and acceptable and (t.agreed_sheet is None or c_theirs < t.agreed_sheet[0]):
+            t.agreed_sheet = (c_theirs, dict(t.standing_terms))
+        restore = self.restore_agreed(case, t, c_theirs)
+        if restore is not None:
+            return restore
 
         if t.status == "agreed":
             if acceptable:
-                return self.accept(t)
+                return self.release_probe(case, t, c_theirs) or self.accept(t)
             if self.eligible_cost(case, t, include_dropped=True) is not None and t.rounds_left > 1:
                 # it agrees, but an eligible rival is cheaper: keep this bidder in play with a counter priced
                 # against that rival instead of walking away from a valid fallback
@@ -199,6 +209,49 @@
             return self.close(case, t, acceptable, c_theirs, rival_best_c)
         return decision
 
+    def release_probe(self, case, t, c_agreed):
+        """It agreed to a package with an index clause: once, the same package without the clause, priced so
+        our C sits RELEASE_SHARE of the clause's cost below the agreed C. A supplier values a clause far above
+        its cost to us when the case's index path sits inside the deadband; a fixed price it accepts beats the
+        clause. A new package it does not take has left the agreed sheet standing so far ("Our agreed offer
+        stands"); restore_agreed handles a dearer counter."""
+        f = "index_clause"
+        options = (case.get("term_options") or {}).get(f) or []
+        if t.released or t.rounds_left < 3 or f not in case["negotiable"] or None not in options:
+            return None
+        if t.standing_terms.get(f) is None:
+            return None
+        fixed = complete_offer(case, {**t.standing_terms, f: None})
+        c_same = self.c(case, fixed, t)
+        if c_agreed - c_same < RELEASE_MIN * c_agreed:
+            return None
+        target = c_agreed - RELEASE_SHARE * (c_agreed - c_same)
+        lo, hi = fixed["unit_price"], fixed["unit_price"] * 1.15
+        if self.c(case, {**fixed, "unit_price": hi}, t) <= target:
+            return None
+        for _ in range(40):  # C rises with price above the relationship minimum; bisect to the target
+            mid = (lo + hi) / 2
+            lo, hi = (mid, hi) if self.c(case, {**fixed, "unit_price": mid}, t) < target else (lo, mid)
+        sheet = complete_offer(case, {**fixed, "unit_price": round(lo, 2)})
+        if not must_haves_ok(case, sheet, t.standard):
+            return None
+        t.released, t.last_sheet = True, sheet
+        t.our_prices.append(sheet["unit_price"])
+        t.our_costs.append(self.c(case, sheet, t))
+        return Decision("send", t.supplier_id, term_sheets=[sheet],
+                        intent="appreciative of the agreement; a firm price instead of the index clause")
+
+    def restore_agreed(self, case, t, c_theirs):
+        """It answered our release probe with an open package dearer than the one it agreed to: once, send
+        that agreed package back exactly."""
+        if not t.released or t.agreed_sheet is None or t.status != "open" or t.rounds_left <= 1:
+            return None
+        if c_theirs <= t.agreed_sheet[0] + 1.0:
+            return None
+        sheet = complete_offer(case, dict(t.agreed_sheet[1]))
+        t.agreed_sheet, t.last_sheet = None, sheet
+        t.our_prices.append(sheet["unit_price"])
+        t.our_costs.append(self.c(case, sheet, t))
+        return Decision("send", t.supplier_id, term_sheets=[sheet],
+                        intent="appreciative: we confirm the package you agreed to")
+
     def closing(self, case, threads: dict) -> Decision:
```

**Ordering.** `restore_agreed` runs before the accept-gap close in `decide`. A counter within 1 % of our probe target but dearer than the agreed C (e.g. 371 @ 90 d) is therefore not accepted. A counter cheaper than the agreed C (e.g. 369 @ 90 d) falls through to the existing gap close and is accepted.

**Expected effect on P02.** The probe price depends on the agent's own full-cost estimate. Under my fit it is about 367.4 € / 90 d, worth ≈ 0.92 if taken.

Possible outcomes:

| Reply | Result | Evidence for this outcome |
|---|---|---|
| "Our agreed offer stands" | accept 361.72 / clause, 0.7345 unchanged, +1 round | most likely; 4 of 4 Nordmark pushes |
| Agrees, or counters below ~369.7 @ 90 d | ~0.75–0.92 | C_best implies such a fixed deal exists; the fixed-path counters (≥ 373.65 @ 90) make me put this at ≤ ~20–30 % |
| Open fixed counter ~374 @ 90 d | restore → very likely re-agreed → 0.7345, +2 rounds | 7 of 7 instant agreements on db5 sheets |

The residual downside is a failed re-agreement or a `final_offer` on the probe reply. In that case we would accept a ~0.29 final instead of walking. I deliberately do not restore against a `final_offer`, because pushing finals has caused walk-aways (D01; Nordmark `ea485d8c4db527aa`). Nordmark gave 0 finals before round 4 in 13 replies, so I rate this risk low but not zero.

Run P02 2–3 times before trusting this.

**Risk to other cases.**
- **Leverage distributors (P08 / P18).** The probe fires only on `agreed` with a clause. They mostly finalled on their own clause rather than agreeing, and "refused 24 months fixed". Expect "stands" or restore, at a cost of 1–2 rounds of ~20 s each.
- **Hidden cases with `hedged` suppliers.** A hedged supplier has less reason to want a clause, so a fixed price is plausibly *more* acceptable there.
- **RFQs.** A probe in RFQs delays the close by one reply. The `rounds_left >= 3` guard plus the wave-cap closing (`closing`) bound this.
- **No-clause cases.** No effect.

### Change 2: writer framing for the probe and the restore (writer_system.md)

**Why.** A probe e-mail that disparages the agreed package, or hints at a copper view without a claim, provokes data requests (`c75e3d16`: three rounds of "Which figures? Please send the data"). It can also make the group's approver reopen the deal.

Two observations argue for a "firm price, less administration" frame:
- Nordmark's own prose twice volunteered a preference for "administrative efficiency" / "a clear commercial footing" without a clause (`20cb611e`, `e560d673`). This is LLM text, unreliable as a signal, but harmless to echo only if it said so in-thread.
- The approver-ready memo matches the group_ladder archetype.

```diff
--- a/src/buyer/llm/prompts/writer_system.md
+++ b/src/buyer/llm/prompts/writer_system.md
@@ -33,6 +33,8 @@
 - If it sent a final offer, be respectful and present our options as a serious effort to close.
 - If it is waiting for an approval, make the options easy to take to the approver.
 - If it asked us a question, answer it in words or say that the options answer it - never leave it hanging.
+- If the INTENT offers a firm price instead of the index clause after the supplier agreed to a package: thank it for the agreement in a few words, leave its agreed package untouched (do not withdraw, criticise or reopen it, and do not say whether we would accept it), and present Option A as the simpler contract - one firm price, no index administration or recalculation for either side, planning certainty for its plant and ours. Make no claim about where any index or market is heading. Ask our contact to check Option A with whoever approves prices.
+- If the INTENT confirms a package the supplier agreed to earlier: say plainly that we take that package as agreed. No new arguments, no new terms.
```

**Expected effect.** Neutral to slightly positive on the probe's chance. Mainly it prevents the failure mode where the e-mail itself turns a "stands" reply into a reopening.

**Risk.** Only active under these two intents, so no other case is affected.

### Considered and not proposed

- **Down-weighting the scorecard / quality claim.** It fails 9 of 9 at Nordmark, and at P03, P04, P07, P08 and P18 per learnings. But it was "taken into account" at D01, P01, P05 and P11. The evidence is mixed by archetype and the claim is harmless here, so I leave `CLAIM_WEIGHT` alone.
- **Deeper anchors or bigger steps on fixed sheets.** These are refuted by F2: round-1 counters are invariant and the final comes in round 4.

## Verify before spending practice runs

1. In the P02 case file, check `term_options.index_clause` contains `null`; Change 1 depends on it. Our early fixed sheets imply it does.
2. Check the maximum of `term_options.payment_days`, and whether `contract_months`, `volume_per_year` and `chargeback` are negotiable (F6).
3. Run 2–3 P02 sessions. Then run one P08 and one P18 as guards against extra rounds or walk-aways.