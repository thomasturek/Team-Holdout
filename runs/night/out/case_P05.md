# P05 analysis: Dralveck / Hrvelec / Fuchsreiter RFQ (leverage, 3 bidders)

## 0. Yardstick decoded from our own results (evidence + arithmetic)

The cost breakdowns give two fixed points: 28.05 @ 30 d is C 238,320 at score 0.8186, and 28.00 @ 14 d is C 238,733 at score 0.8136. From these:

- **C_open ≈ 305,545.** This is Dralveck's opening of 36.00 @ 30 d at 1,200 ppm: 302,400 + 2,016 interest + 1,129 quality. Hrvelec's 31.50 @ 52 d breaks the ≤42 d must-have, so it does not set C_open.
- **C_open − C_best ≈ 82,100, so C_best ≈ 223,400.** That equals Dralveck at about 26.3 @ 30 d. Every other score in the digest reproduces to ±0.001 (for example 32.00 @ 30 d, 600 ppm gives 0.4188).
- **Price equivalence (our 8 %, 60 d reference):**
  - 14 d costs us 1.02 % of spend; 30 d costs 0.67 %.
  - So 28.00 @ 14 d ≈ 28.10 @ 30 d.
  - 27.86 @ 14 d is the record in NIGHT_CONTEXT/learnings, scoring 0.828.
  - 27.83 @ 14 d would score ≈ 0.831.
- **Quality:** ppm 1,200 is Dralveck and ppm 600 is Fuchsreiter, which identifies the winner of each deal.

---

## 1. Findings, ranked by value

### F1. All three bidders counter on a €0.50 grid; "agreed" takes our exact figure. The money is in the gap between the grid and the floor.

**Evidence: every supplier counter in the digest is a multiple of 0.50.**
- Dralveck: 32.5, 32.0, 30.5, 30.0, 28.5, 28.0.
- Fuchsreiter: 38.5, 32.0, 31.5, 31.0, 30.5, 30.0, 29.5, 36.5.
- Hrvelec: 34.5, 34.0, 33.5, 33.0.

**Every "agreed" is our own two-decimal figure:**
- Dralveck: 31.57 (e3d74883), 28.06 (f08d345b), 28.05 (a89a4dad, 891fdbdf).
- Dralveck in the winners' probes: 34.92 and 35.76 (9798d98c, d35aae9c).
- Fuchsreiter: 31.64 (25a2dfb2), 36.45 (d35aae9c).
- Hrvelec: 33.98 (9798d98c).

**Three clean "grid counter, then exact agree just below it" sequences:**
- a89a4dad and 891fdbdf, Dralveck: we asked 28.01 @ 30 d and it countered 28.50. Next round we asked 28.05 @ 30 d and it **agreed 28.05**.
- d35aae9c, Fuchsreiter: we asked 36.39 and it countered 36.50. We asked 36.45 @ 14 d and it **agreed**.

**The opposite case: a probe too deep gets the counter repeated as a final, not a walk.**
- 9798d98c, Fuchsreiter: we asked 35.95 @ 14 d and got final 36.50.
- 0af6f2ee, b962f2c6, c15e7332, Dralveck: we asked 26.73 and got final 28.00.

**Inference.** The bot computes a threshold and agrees if our ask is at or above it. Otherwise it counters with its own price rounded *up* to the grid. A grid counter therefore sits up to €0.49 above a price it would sign.

### F2. Dralveck's response function (the deal-maker in 12 of 14 sessions)

**Round 1. Rival claim present or not is the dominant input; payment and anchor barely matter.**

| Our r1 to Dralveck | Claims | Reply | Sessions |
|---|---|---|---|
| ~31.6–31.8 (60/45/30 d) | quality only | 32.50 counter | 42fd7e08, 25a2dfb2 |
| same, 31.57 @ 30 | rival + quality | **agreed 31.57** | e3d74883 |
| 27.7–28.0 (3 sheets) or 27.45 @ 45 | rival + quality | 30.50 @ 30 + "clarify internally, come back on price" | f08d345b, a89a4dad, 891fdbdf, e1e9c3b9 |
| 26.61 @ 14 single | rival + quality (± index) | 30.50 @ 14 (30.00 once with index) | 0af6f2ee, 61d079be, f25cb509, b962f2c6, c15e7332, b31f265b, 3871f28a |
| 34.92 / 35.76, no claims | – | agreed (winners) | 9798d98c, d35aae9c |

- The rival claim is worth ≥ 0.93 in round 1: 31.57 was agreed with it, 32.50 was the counter without it.
- The r1 counter is the same 30.50 whether we offer 14 d or 30 d, and whether we anchor at 26.61 or 28.0.
- The index claim got 30.00 instead of 30.50 once in three tries. That is noise-level.

**Round 2 ("We have clarified this internally and can move further").** It lands at max(our ask, X2), rounded up to the grid.

| Our r2 ask | Reply | Session |
|---|---|---|
| 26.92 / 26.87 @ 14 d | 28.00 @ 14 | 7 of 7 sessions |
| 28.06 @ 30 d | agreed 28.06 | f08d345b |
| 28.01 @ 30 d | 28.50 @ 30 | a89a4dad, 891fdbdf |
| 27.77 / 28.11 @ 45 d | 28.50 @ 30 ("my best price") | e1e9c3b9 |

From this, X2 @ 30 d lies in (28.01, 28.06]. The record run agreed 27.86 @ 14 d at "our second sheet" (learnings, v12). That puts X2 @ 14 d at or below 27.86 in that run; the practice bots vary 1–2 % between runs.

**Round 3.**
- An ask in [X2, grid counter) was **agreed** in 2 of 2 sessions.
- An ask below X2, or one that moved backwards, got **final_offer at the grid counter** in 5 of 5 (0af6f2ee, b962f2c6, c15e7332, e1e9c3b9 at 28.50, 61d079be).
- It **walked away** only after our two consecutive timeouts (61d079be r4).

**Levers and what it says it wants.**
- Payment: it **refuses anything above 30 d** ("we absolutely need to stick to the 30 days"), and always picked our 30 d option out of a 60/45/30 menu. It takes 14 d happily ("helps us out").
- It asks for proof of competitors when we mention them without a claim (F5).
- Its talk is about machines running and cash being tight.

### F3. Faster payment buys almost nothing from these bots, but costs us 0.36 % of spend (14 d vs 30 d).

- Dralveck's r1 counter is 30.50 at both 14 d and 30 d.
- At 14 d it settles 28.00 (×7). At 30 d it agrees 28.05–28.06 (×3). The difference is 0.05, about 0.18 %, against our cost of about 0.10/unit.
- After agreeing at 34.92 @ 30 d, Dralveck answered 34.39 @ 14 d with "Our agreed offer stands" at 34.92 @ 30 d (9798d98c r4). It also accepted 14 d at the *same* 35.76 (d35aae9c r4).
- Fuchsreiter: 35.95 @ 14 d drew final 36.50 @ 14 d (no price for 14 d). 36.45 @ 14 d was agreed (0.14 %).
- "Faster payment is welcome; we can reflect it in the price" appears in nearly every reply, apparently boilerplate.

**Evidence strength.** These are cross-session comparisons, not paired runs, and the 30 d path needs one more round and has a worse tail (e1e9c3b9 got 28.50 because our sheets were at 45 d). The mean of the 30 d deals (28.165) is actually worse than 28.00 @ 14 d. So this is suggestive, not proven.

**Why we do it.** `menu()` and `lever_trades()` skip the own-price check for `cash_hungry` suppliers (`policy.py`, `if theirs and not cash_hungry …`). The supplier then counters on its own schedule regardless.

### F4. Our asks sometimes go backwards, and suppliers punish it with a final offer.

- To Dralveck: 26.61 → 26.92 → **26.73** @ 14 d (0af6f2ee, b962f2c6, 61d079be); 26.87 → **26.73** (c15e7332). All four were followed by final 28.00.
- To Fuchsreiter: 28.66 → **28.34** @ 30 d (a89a4dad r4): *"your prices just went backwards compared to your last email, what is going on?"* followed by final. Also 28.55 → **28.29** @ 45 d (e1e9c3b9 r4): *"your new price offer is actually lower than your last one, which makes no sense"* followed by final.

**Cause: not identifiable from the digest.**
- The Fuchsreiter cases are probably the rival-undercut block in `offer()`, because Dralveck had just agreed. That is legitimate pressure, but it was sent without a rival claim in a89a4dad r4.
- The Dralveck cases have no cheaper rival, so they are a concession-bookkeeping artefact. `our_prices` holds the 60 d base price, while the menu re-prices to 14 d at the cash rate.

**Effect on P05:** about 0, because Dralveck's floor binds either way. It is a credibility leak that will matter with suppliers that still have room.

### F5. "Several bidders" without a figure triggers demands for proof, in the latest four sessions only.

There were seven replies in b962f2c6, c15e7332, b31f265b and 3871f28a, all to round-2 messages with `claims=[]`:
- Dralveck ×4: "You mention several bidders… send me the proof".
- Fuchsreiter: "without proof I can't just drop the price more", then held at 30.00. Also "You mention our costs for labour and steel, but I don't see any numbers".
- Hrvelec: "can you show us some proof or target prices".

None of the earlier ten sessions shows it, so a recent change introduced the wording. It is either the writer or the RFQ playbook; the digest cannot tell which. Its price effect on P05 is nil, because Dralveck still went to 28.00. In an RFQ where the cheapest bidder is the one demanding proof, it costs a concession.

### F6. Timeouts cost the most in the logs.

61d079be scored 0.573 against 0.814: three buyer timeouts at r3–r4, then Dralveck withdrew ("will fill the capacity with other jobs") and Hrvelec walked. Earlier timeouts appear in 42fd7e08 and 25a2dfb2. The latest five sessions have none. This is a runner and network issue, not policy; keep the final-day safety work.

### F7. The other two bidders never threaten Dralveck at ~28.

- **Fuchsreiter** (free capacity): steps of 0.50 per round from 32.0/31.5; finals at 29.5–31.0; wants 30 d (also took 14 d) and "a binding higher volume / call-off plan".
- **Hrvelec** (full book): 34.5 → 34.0 → 33.5 at 35 d. It prices a shorter lead time at about 3 % ("overtime"; winners: 33.0 @ 42 → 34.5 @ 35) and 90 d payment at +0.5 (≈12 %/yr). "German labour costs don't really matter for our CZ plant": its LCI-C argument is irrelevant to it.

Both serve only as rival-claim ammunition.

---

## 2. Best deal in the logs, and how it came about

**Best in our logs: 28.05 @ 30 d, Dralveck, score 0.8186 (a89a4dad, 891fdbdf).** Same path both times:
1. **r1:** three sheets (≈28.1 @ 60, 27.3 @ 45, 27.9 @ 30) plus rival and quality claims. Reply: 30.50 @ 30 with "clarify internally".
2. **r2:** sheets including 28.01 @ 30. Reply: grid counter 28.50 @ 30 ("clarified, can move further").
3. **r3:** a sheet at its insisted term, 28.05 @ 30, nudged up 0.04 from our last ask and 0.45 under its counter. Reply: **agreed 28.05**.

f08d345b got 28.06 one round earlier the same way, with our r2 ask landing just above X2.

**Record (another team, not in the digest): 27.86 @ 14 d, score 0.828.** Learnings describe a held anchor after Dralveck's deep first drop, agreed on the second sheet. Mechanically it is the same thing: an ask inside [X2, grid counter).

**Practical ceiling.** No logged path goes below X2 ≈ 27.85 @ 14 d / 28.03 @ 30 d. That caps P05 at about 0.83 with the observed levers. The remaining ~0.17 to C_best (≈26.3 eq.) is not reachable by any behaviour we have seen.

**Untested lever.** Lead time up to the 42 d must-have may lower its price, but our late-cost rate is unknown and Dralveck never said 35 d costs it anything. Inference only.

---

## 3. Where the current agent leaves value

The current agent is the latest five sessions: f25cb509, b962f2c6, c15e7332, b31f265b, 3871f28a. **All five closed at 28.00 @ 14 d, score 0.8136.** That is very stable, so this path is close to deterministic. Breaking the value gap down:

| Source | € vs our current deal | Score | Evidence strength |
|---|---|---|---|
| Accepting the grid counter 28.00 instead of probing just below. Three sessions accepted it at r2 (f25cb509, b31f265b, 3871f28a); two pushed with a backward ask and got final 28.00 | ≈ 1,180 (to 27.86 @ 14) | +0.014 | F1, F2: strong mechanism, the floor varies 1–2 % |
| 14 d instead of 30 d | ≈ 410 (vs 28.05 @ 30) | +0.005 | F3: weak, cross-session |
| Backward asks | 0 on this case | 0 | F4: strong as behaviour, nil here |
| Gap to C_best | ≈ 15,300 | 0.186 | Not reachable by any observed path |

Against NIGHT_CONTEXT's record of 0.828, we lose 0.014. Essentially all of it is F1.

---

## 4. Proposed changes

### Change 1 (main): probe one sheet just below an open counter before taking it

**Rule.** When the policy is about to close on an **open** counter (the existing near-ask close branch), it first sends once, per thread, the supplier's **own standing terms** at `probe_pct` (0.5 %) below its price. The next round then accepts whatever comes:
- "agreed" at our figure;
- the same counter;
- a final offer.

**Keyed to observable signals only:** status `open`, our ask already within `accept_gap_pct` of the counter, at least 3 rounds left. There are no case or supplier ids. It never goes below the relationship floor, because it uses `above_floor`.

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@
     "accept_target_pct": (0.0, 10.0),
     "lever_trades": (0.0, 1.0),
+    "probe_pct": (0.0, 2.0),
 }
@@
     "lever_trades": 1.0,  # > 0.5 = on
+    # before taking an open counter, one sheet on its own terms this far below it: counters were rounded up
+    # to a coarse grid above the price the supplier agrees to (28.50 counter -> 28.05 agreed; 36.50 -> 36.45)
+    "probe_pct": 0.5,
 }
@@ class ThreadState:
     clause_countered: bool = False  # we offered its package with a wider index deadband once before closing
+    probed: bool = False  # we sent one sheet just below its open counter before taking it
@@ def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
         close = t.our_costs and self.c_track(case, t.standing_terms, t) <= t.our_costs[-1] * gap
         if close and acceptable and c_theirs < t.opening_cost:
+            probe = self.probe(case, t)
+            if probe is not None:
+                return probe
             return self.close(case, t, acceptable, c_theirs, rival_best_c)
@@
     def accept(self, t):
         return Decision("accept", t.supplier_id, accept_sheet_id=t.standing_id)
 
+    def probe(self, case, t):
+        """Once per thread, before taking an open counter: its own terms at `probe_pct` below its price.
+        'agreed' takes our exact figure; at worst it repeats the counter (or finals) and we take that."""
+        pct = self.p.get("probe_pct", 0.0)
+        if pct <= 0 or t.probed or t.status != "open" or t.rounds_left <= 2:
+            return None
+        theirs = t.standing_terms["unit_price"]
+        sheet = complete_offer(case, {**t.standing_terms, "unit_price": round(theirs * (1 - pct / 100), 2)})
+        sheet = self.above_floor(case, t, sheet)
+        if sheet["unit_price"] >= theirs or not must_haves_ok(case, sheet, t.standard):
+            return None
+        t.probed, t.last_sheet = True, sheet
+        t.our_prices.append(sheet["unit_price"])
+        t.our_costs.append(self.c_track(case, sheet, t))
+        return Decision("send", t.supplier_id, term_sheets=[sheet],
+                        intent="appreciative: we are nearly there; on your own terms this figure closes it")
+
```

On the next reply, if the supplier repeats the counter, `close` is still true and `probe()` returns `None`, so `close()` accepts. "agreed" and "final_offer" already route to accept.

**Expected effect on P05.** In the 3 of 5 latest sessions that closed via this branch, 28.00 @ 14 d becomes a probe at 27.86 @ 14 d.
- If X2 ≤ 27.86 (true in the record run), the result is 0.828 (+0.014).
- Otherwise it is 28.00 (±0) after one more round, about 20–45 s in a three-bidder session.
- Realistic mean gain is +0.005–0.01, because X2 varies 1–2 % between runs.
- Note that 0.5 % happens to reproduce the record figure. Treat it as a tunable parameter, not a calibrated one. Also try 0.3 %.

**Risk to other cases.**
- The branch fires only where we would have accepted anyway, so the only downside is a walk. EVALUATION.md (another team's agent) records one P05 bidder that "sat 0.7 % above our ask and walked after our next step". In our logs, every too-deep near-final ask got the counter as a final, with no walk (5 instances, F2/F1). Our walks followed timeouts or a cumulative gap of 39 %, and the probe adds about 0.5 %.
- Price-frozen suppliers (P03, P04) lose one round for nothing.
- Wave time: one more round per affected thread. The runner's cap guard (`max(90 s, slowest + 15 s)`) still applies.
- **Validate on P01, P03, P04 and P07 before merging.**

### Change 2: our asks never go backwards (in C), unless a rival now beats our last ask

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
         sheets = sheets[:3]
+        if t.last_sheet is not None:  # an ask below our last one reads as bad faith and drew final offers;
+            prev_c = self.c(case, t.last_sheet, t)  # a cheaper rival offer is the one reason to ask for less
+            if rival_best_c >= prev_c:
+                sheets = [self.raise_to(case, t, s, prev_c) for s in sheets]
         questions = []
@@
     @staticmethod
     def above_floor(case, t, terms):
@@
         return {**terms, "unit_price": floor} if floor and terms["unit_price"] < floor else terms
 
+    def raise_to(self, case, t, sheet, c_min):
+        """``sheet`` repriced up so that its C to us is at least ``c_min`` (never down)."""
+        c = self.c(case, sheet, t)
+        if c >= c_min - 0.5:
+            return sheet
+        slope = self.c(case, {**sheet, "unit_price": sheet["unit_price"] + 1}, t) - c
+        if slope <= 0:  # below the relationship-cost minimum C is not monotone: leave it
+            return sheet
+        return {**sheet, "unit_price": round(sheet["unit_price"] + (c_min - c) / slope, 2)}
+
```

**Behaviour.**
- The guard compares in C, so a change of payment term counts.
- It never lowers a sheet.
- It keeps the deliberate rival undercut after another bidder has agreed or offered lower, which is the a89a4dad r4 situation. In that case the existing `pick_claims` should carry the rival figure; it did not in a89a4dad r4, so look at why separately.
- If the guard makes sheet[0] equal to the last sheet, `decide()`'s existing identical-sheet rule closes on the standing offer instead of sending a repeat.

**Expected effect on P05:** about 0 on score (Dralveck's floor binds). It removes the r3 regression seen in 4 of 7 single-sheet sessions and the two Fuchsreiter complaints.

**Risk.**
- It can hide the underlying bookkeeping bug rather than fix it. Still investigate `next_price`/`concession`: base price at reference days versus a menu re-priced at the cash rate.
- In a relationship case where the supplier raised its price, we cannot re-anchor lower. That is rare, and `decide()` will close or walk on the existing gates.

### Change 3 (backstop, lower confidence): no competition talk without the rival figure in the same e-mail

```diff
--- a/src/buyer/llm/prompts/writer_system.md
+++ b/src/buyer/llm/prompts/writer_system.md
@@ HARD RULES
 3. Never reveal or hint at: urgency, deadlines or time pressure on our side; a budget, target price, maximum or walk-away point; our internal costs or calculations; whether we have or lack alternatives (mention other suppliers or offers only if the INTENT explicitly asks to signal alternatives); anything from the DOSSIER or background notes about the supplier's finances, credit, bank or how we pay it. Calling Option A "the package we can approve" is allowed - it is our offer, not a limit.
+3a. Mention competition, other bidders or other offers only in an e-mail whose claim lines include a rival offer or quote, and then refer only to that line ("the offer quoted above") - never "several bidders" or "competitors" in general. Likewise name a cost (labour, steel) only if a claim line in this e-mail carries it. Suppliers ask for proof of anything they cannot check, and hold their price until they get it.
```

**Evidence:** seven proof demands, all after round-2 messages with no claims, all in the latest four sessions (F5).

**Caveat.** If the phrase comes from a code template or the RFQ playbook rather than the model, this rule will not help. Grep for "bidders" and "competing" in the writer templates and playbooks first.

**Effect on P05:** about 0 on score. It protects RFQs where the cheapest bidder is the one asking for proof.

**Risk:** minimal. It narrows what the model may say. The rival claim still leads every message where it is new, so the "rival quote leads" gain from EVALUATION.md is kept.

---

## 5. Not proposed as a diff yet, worth one paired test: drop the payment exemption for cash-hungry suppliers (F3)

The exemption is at `menu()` and `lever_trades()`, `not cash_hungry` / `not hungry`. Removing it would move P05 from 14 d to 30 d sheets, worth about +0.005 if F3 holds. However, P01's best deals (130.18 at 14 d, score 0.974) may depend on it.

**Test before changing:** run 2 × P05 with a 30 d-only menu against 2 × the current agent, and check P01 with the same toggle.

---

## 6. Validation plan (about 12 practice sessions)

1. **P05 ×3 with Change 1 + 2.**
   - Success: at least one 27.8x @ 14 d agreed, no walk.
   - Expected mean: 0.815–0.825.
2. **Guards ×1–2 each: P01, P03, P04, P07** (the close-branch users).
   - Fail if any case drops by more than its known spread: P01 0.909–0.995, P04 0.86–0.874, P07 0.65–0.75.
   - Fail on any walk-away after a probe.
3. **Check the logs:**
   - every probe is followed by agreed, the counter, or final; never walked;
   - no sheet[0] C below the previous sheet[0] C without a rival claim in the same message.

Practice suppliers vary 1–2 % run to run. A single session of +0.01 on P05 proves nothing; three sessions at 28.00 against three with any 27.8x agreed would.