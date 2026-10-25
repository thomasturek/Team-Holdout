# What the digest shows about our prose, and what to change before 13:00

## Read first: the bots barely read prose

Across 200 sessions, suppliers' moves track our **term-sheet steps**, not our words. Same sheets + different prose → same path: P03 nine sessions at 0.9351 to four decimals (angle-A through v6), P02 nine at 0.7345, P10 all 25 sessions final_offer in round 1 at 33.6-34.0/31.7-32.1 whatever we wrote. Bare template e-mails ("Dear colleagues… Thank you for your message. [options]") got normal moves (P07 `bdeae9d4` r3 → 5.51/5.45, our best P07 session; P18 `13e6c049` r4 → final 5.10, our best P18). The remaining P08/P11/P18 spread (5.40 vs 5.50 first counter, 45.50 vs 46.00) does **not** separate on any prose feature I could find: I compared the "payment terms are fixed" wording (P11: 3 sessions 45.50, 4 sessions 46.00), the Option-A framing, the decision-maker paragraph, goodwill, and the open question. It separates on the supplier's first counter, which varies by one scripted step between identical openings. That is supplier-side randomness (api.md: "identical messages need not get identical replies").

What prose *does* do, reliably, is **trigger scripted reactions**: proof demands, "I am fully authorized", "which volume can you commit to", irritation at tiny or backward steps. The gains below are therefore mostly in pacing (policy) and in removing triggers (writer). Findings are ranked by expected mean gain; "shows" = in the digest, "infer" = my reading.

---

## Finding 1 — Equal-value cash trades end the supplier's concession run early (P01 −0.03)

**Shows.** Brandlhuber says "Faster payment is welcome; we can reflect it in the price" in every reply, so the policy's `lever_trades` puts a 14-day sheet (priced C-equal to the 30-day one) on the table by round 3-4. The supplier accepts it at once and the thread ends:
- `9c0ba9cd`, `38367dc0`: r4 134.60@14 → `agreed` → 0.9092; `934ed1e9`: r4 134.70@14 → 0.9046; `6d1edc5d`: r3 135.29@14 → 0.8753; `478e95da`: r3 134.60@14 → 0.9092.
- Steady 30-day stepping instead: `d5066cc6` 126.53→127.37→128.00 got 135.5→134.7→133.9→final 133.3 → **0.9691**; `1e887324`/`36af37af` 134.8@30 → 0.9263; `a37615af` 135.2 → 0.9106.
- Lever-trade group mean 0.90, steady group 0.93. The 14-day discount it grants (≈0.65 %) barely exceeds our 16-day interest cost (0.36 %).

**Infer.** The bot accepts any sheet worth at least its standing offer to it; an equal-value trade therefore freezes the price at the current level and forfeits the 2-3 scripted steps (0.5-1.0 each) it still had. The same accept-at-once behaviour shows at Dralveck (28.06@30 `f08d345b`, 28.05 ×2) and Nordmark (9× round-1 accepts).

**Change** — offer cash levers only in the endgame:

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
-        if self.p["lever_trades"] > 0.5 and (t.holding or asks):
-            trades = [x for x in self.lever_trades(case, t, a, asks) if x not in sheets]
+        endgame = t.rounds_left <= 2 or t.status == "final_offer" or t.holds >= 2
+        if self.p["lever_trades"] > 0.5 and (t.holding or asks):
+            trades = [x for x in self.lever_trades(case, t, a, asks, endgame) if x not in sheets]
@@
-    def lever_trades(self, case, t, a, asks=()):
+    def lever_trades(self, case, t, a, asks=(), endgame=True):
@@
         for v in lever_values(case, a, t.standard, t.profile):
             if not v["must_haves_ok"]:
                 continue
+            if v["field"] in CASH_LEVERS and not endgame:
+                continue  # an equal-value cash trade is accepted at once and ends its concession run (P01 night-v1..v6)
```
Structural trades (index clause, P02's whole gain) are untouched. **Affects:** any cash-short supplier that still has steps left (P01 +0.03; P05 Dralveck ±0). **Risk:** low — the steady group never saw a walk-away; the final at r5 still arrives.

## Finding 2 — Tiny, zero or backward price steps are read as "no movement" and answered with a hold or a worse price (P01, P05, P08, P11, P18)

**Shows.**
- P01 `c006eed3` r2 step +0.28 (0.2 %) → "without movement from your side we cannot move either"; `081a155f` same; `551cb8be` steps +0.04 → two holds; `cac09d93` +0.01 → "a one-cent adjustment does not constitute the realistic step forward" → final at 135.5 (0.864); `773a42a5` 14-day sheet 132.22→130.81 (backward on one package) → "you have moved backwards on the very option we are discussing" → next counter **worse** (135.7→136.6), 0.8423.
- Steps ≥0.8 % always got a counter-step (`d5066cc6`, `1e887324`, `36af37af`).
- Identical sheet sets: P08 `7976d643` r4 repeat → final; `0a4d2074` r4 repeat → final; `769d64fc` r5 repeat → **walked away (0)**; P18 `7c970402` repeat → final 5.60; P11 `52716f49` r3-r5 repeats at 45.42 → "you just sent the exact same numbers again" → final 46.50 (0.5427, worst P11 deal).
- P05 `e1e9c3b9`/`a89a4dad`: a lower price on a package we had priced higher → "your prices just went backwards, what is going on?" → final.

**Infer.** Family/job-shop bots gate their step on ours with a threshold near 0.5 % of their price; distributor bots run a fixed schedule (Donautal 0.10/round for ~5 rounds, Leitner 0.03-0.06) as long as we move at all, and final or walk on an exact repeat. The night log turned `min_step_pct` off on one run each of P18 (0.630, band 0.62-0.70) and P07 (0.653, band 0.65-0.70) — inside noise. The package-level `no_step_back` already covers backward steps; the identical-set hole is not covered when `t.holding` is set or sheets are reordered.

**Change:**

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ DEFAULTS = {
-    "min_step_pct": 0.0,
+    "min_step_pct": 0.5,
@@ class ThreadState:
     last_sheet: dict | None = None
+    last_sheets: list = field(default_factory=list)
@@ def decide(...):
         prev = t.last_sheet
+        prev_set = sorted(json.dumps(s, sort_keys=True) for s in t.last_sheets)
         decision = self.offer(case, t, self.next_price(t, theirs, case=case), rival_best_c=rival_best_c)
-        if prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding:
-            return self.close(case, t, acceptable, c_theirs, rival_best_c)
+        same = bool(prev_set) and sorted(json.dumps(s, sort_keys=True) for s in decision.term_sheets) == prev_set
+        if same or (prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding):
+            if acceptable:
+                return self.close(case, t, acceptable, c_theirs, rival_best_c)
+            lead = decision.term_sheets[0]  # an exact repeat drew a final (P08 x2, P18) or a walk (P08 769d64fc)
+            lead["unit_price"] = round(min(theirs, lead["unit_price"] + 0.005 * theirs), 2)
+            t.our_prices[-1] = lead["unit_price"]
         return decision
@@ def concession(...):
-        if not t.holding and gap > 0 and p["reciprocity"] <= 0:
+        if not t.holding and gap > 0:
             step = max(step, min(p["min_step_pct"] / 100 * theirs, MIN_STEP_GAP * gap))
@@ def offer(...):
         t.last_sheet = sheets[0]
+        t.last_sheets = list(sheets)
```
**Affects:** P01 +0.02-0.05 (no holds), P08 removes a 1-in-3 walk on repeats (+0.03 expected on P08), P11 avoids the 46.50 outcome. **Risk:** 0.5 % steps burn gap faster at distributors — bounded by `MIN_STEP_GAP` (40 % of the gap), and Donautal gave five counters to steps of 0.01-0.03 (`2f6a0b78`) so its schedule is not step-sensitive.

## Finding 3 — Every factual-sounding sentence without an ID draws "Which figures is that based on? Please send us the data." and a hold

**Shows** (the ask appears in ~40 supplier replies; each time the supplier did not move in that round):
- P02 `c75e3d16`: "Our data shows a more balanced picture" → "please provide this documentation" repeated in all four later replies; 0.239.
- P05 `e3d74883`: we wrote "We are not in a position to commit to quantities at this stage" → Fuchsreiter: "Since you can't commit to any volume, I really can't drop the price" → hold.
- P05 prose "Several bidders are competing… the award goes to the best package" (PLAYBOOK rfq) → Dralveck `45a8c2e4` "send me the proof", `c15e7332` "please send some proof of these other offers", Fuchsreiter `3871f28a` "without proof I can't drop the price more" → 30.50 hold; with a verified rival **claim** in the same round Fuchsreiter moved every time (`891fdbdf` 30.5→30.0/29.5, `c15e7332` → 29.5@14, `25a4b54b` → 30.0/29.5).
- "Binding volume in every option: 30,000 units" (the case's fixed need, emitted every round by `volume_line`) → P07/P18/P04/P11 "please provide the data supporting this projection" ×12; P07 PLAYBOOK's "business on top of what you supply today" → "please provide the exact volume figures for this additional business" (`5b71599f`, `121a69f6`, `fc419f05` which then walked after a push).
- P11 `3ab9d154`: bare promise "we will pay every invoice on its agreed due date" → "please send us the data to prove this"; `273c889c` the same promise **with** an explicit admission ("our invoices have reached you late") → "Good to hear… that is a big deal for us", 46.00 one round earlier.
- P01 `b4535c94`: first e-mail with no claims at all → 142.9 (every claim-bearing first e-mail: 135.5-138.6); 0.6158.

**Infer.** The bot classifies assertions without IDs as unbacked and answers with a scripted proof request; verified claims are the only prose channel that moves it. Code-side changes:

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
@@
-    "rfq": "Several bidders compete: state plainly that the award goes to the best package, without promising it.",
+    "rfq": "Several bidders compete. Mention competition only in the sentence that introduces a rival [[CLAIM_n]]; "
+    "with no such claim listed, say nothing about other bidders - it asks for proof and holds.",
@@ def volume_line(case, decision, signals=None, thread=()) -> str:
-    if not (asked or (first and attr(case, "type") in VOLUME_TYPES)):
+    already = any("Binding volume in every option" in str(m.get("body") or "")
+                  for m in (thread or []) if m.get("from") == "buyer")
+    if already or not (asked or (first and attr(case, "type") in VOLUME_TYPES)):
         return ""
```
Prompt side: see the new writer_system.md (rules 3, 4, 10). **Affects:** hidden RFQs where a Fuchsreiter-type is cheapest (+0.02-0.05), hidden bundling cases; practice ≈0. **Risk:** none.

## Finding 4 — The decision-maker paragraph is neutral at best; the bot answers it with "I am fully authorized" and nothing else

**Shows.** ~20 replies contain "I am fully authorized / authorized decision-maker" (Wälzlager `b8732e82`, `3e9bfb9c` ×2; Leitner `121a69f6`, `1be677c7`, `2efba28d` ×2, `0ce438f7`; Werdenfels `62ba92eb`, `900758ae` "making escalation unnecessary", `b4f57890` ×2; Donautal `f6c1bff5`, `3b553d9a`). Prices in those rounds followed the usual schedule. Where a supplier played the ladder ("we have discussed this with our management, we are authorized to make a further concession": Leitner `bdeae9d4` → 5.42, best P07; Wälzlager `c6d78c8e` → two-sheet final 4.89, best P04; Donautal `7976d643`) the concession was the same 0.03-0.10 step as elsewhere. P07 first counters with the paragraph (5.58-5.60) sat at or above those without (5.53-5.56), n=5 vs 7, inside noise.

**Infer.** The paragraph costs words and once a supplier has declared authority, repeating it reads as not listening (Werdenfels `900758ae` 0.497, the one P18 session with no clause option and the paragraph in r2 and r3). **Change:** prompt only (rule 7 below): use it once, only when the DOSSIER or the supplier itself says approval is needed, never after "fully authorized". **Gain:** ≈0; removes a negative. **Risk:** none.

## Finding 5 — The sentence filter leaves headless paragraphs; comparisons in words trigger it

**Shows.** `c43e456e` r2 opens "Dear Mr Seidl, None of our options carries one."; `4fc01445` r2 "They also give you a fixed volume…"; `121a69f6` r1 "Our options give you that:"; `476b3b55` r2 "We have taken that seriously". The dropped sentences contained "twice as long", "longer than the one you quoted", "half" — number words, which the digit guard removes, leaving a pronoun with no antecedent. No supplier reacted visibly, but a hidden-case jury reads replays. Likewise FORM_RE drops "Thank you for your revised offer" sentences although the polite form-letter sessions were our best P01 (`d5066cc6` 0.969) and P07 (`151d1659` 0.693): the rule buys nothing and costs sentences.

**Change:** prompt rules 11-12 below (standalone paragraphs, no comparative quantities in words, a one-line thanks allowed). **Gain:** quality/jury; score ≈0.

---

## Improved `src/buyer/llm/prompts/writer_system.md` (full replacement)

```
You write one e-mail for the purchasing team of Hollerau Pumpenwerke GmbH, a family-owned German pump maker in Lower Bavaria, to one of its industrial suppliers. The reader is a real person - an owner, a key account manager, an export manager or someone in inside sales - who reacts to arguments, tone and relationship as people do.

Our negotiator (code) has already decided every term, every figure and every data argument. You choose the words. The supplier's moves follow our term sheets and the checked data lines; your prose cannot buy price, but it can lose a round: a sentence that sounds like a fact and carries no data line makes the supplier ask for proof and hold its price.

WHY THIS E-MAIL MATTERS
The first e-mail (MESSAGE: first) sets the supplier's opening reaction: it must carry every claim line and the options, complete and decisive. Later e-mails keep the same line, answer the supplier's last ask in one breath, and get out of the way of the options.

OUTPUT
- The e-mail body only: plain English text in short paragraphs. No subject line, no markdown, no bullet points, no JSON, no notes about the task.
- Start with a greeting to the supplier. End with exactly the sign-off given in the input.
- Your own words: at most 140 in a first e-mail, at most 60 later; the inserted blocks do not count. Every sentence must earn its place.

PLACEHOLDERS - code replaces each with exact text. Put each on its own line, use each one listed exactly once, never alter, translate or explain it:
- [[CLAIM_1]], [[CLAIM_2]], [[CLAIM_3]]: one data argument each; you see their content in the input. Use exactly the ones listed. Introduce each with at most a few words that name its topic plainly ("On the cost side:", "On delivery:", "On the notice period:"). Never say what "our data", "the figures", "the market" or "our records" show, and never summarise a claim in your own words - the claim lines speak for themselves.
- [[OFFERS]]: our term sheet(s), inserted with their own introduction line. Option A is always the first.
- [[QUESTIONS]]: our questions. Only if the input lists questions.

HOW TO WIN THE REPLY
1. Their concern first. The first sentence after the greeting answers what the supplier cares about most (DOSSIER, SIGNALS, its last e-mail) - in its own terms, and with what our options do about it. Pick up one short phrase it used (no figures) so it knows it was heard.
2. Solutions, not counter-arguments. If it blames a cost (copper, alloy, steel, energy) and our options include an index clause (see CLAUSE IN OPTIONS), present the clause as the answer: we take that risk above the deadband, so the base price no longer needs a risk premium. If it wants cash, volume, a longer contract or its standard payment term, point to the option that gives it - only if an option really does.
3. Nothing factual without a data line. Every statement about costs, prices, indices, deliveries, volumes, forecasts, other suppliers, our payment behaviour or the supplier's situation must be a [[CLAIM_n]] line. Your own sentences describe only what the options give the supplier. Never call our price fair, justified, in line with anything or based on anything; never say what we know, see, estimate or have taken into account.
4. Competition. Other bidders, other offers, quotes or alternatives are mentioned only in the few words that introduce a rival [[CLAIM_n]] listed in the input. With no such claim, say nothing about competition, bidders or the award.
5. Option A is the package. Name Option A as the package we can approve, and say in one sentence what it gives the supplier in its own terms (planning security, a longer term, prompt payment, no chargeback, the clause) - only what the options really contain. The other options are genuine alternatives for its convenience.
6. A clear way to yes. Only if CONFIRM AT ONCE is yes: say that if it confirms Option A as it stands, we can confirm the order straight away. If it is no, never promise to confirm, accept or award at once.
7. The person who decides. Add a short paragraph its decision-maker can approve as it stands only if the DOSSIER says our contact needs approval, or the supplier itself wrote that it must clarify internally or present to management - and only once per thread. If the supplier has said it is authorized to decide, never mention approval, management or escalation again.
8. The STRATEGY line sets how hard to press (aggressive, cooperative, patient, escalate, secure) - follow its tone. The right voice for this supplier (ANGLE in the DOSSIER, STYLE): owner to owner for a family firm, a short approver-ready paragraph for a group, cash first for a cash-short shop, security and planning for a supplier we depend on.
9. One open question, first e-mail only (MESSAGE: first) and only if QUESTIONS is none: just before the sign-off, ask in one short sincere sentence what the supplier would need from us to confirm Option A. Never ask it in later e-mails.
10. Say what the options give, never what we cannot do. Do not write that we cannot commit, cannot change a term, have no room, or that a term is fixed in this enquiry - the supplier uses it against us. If a term is not in the options, do not mention it.
11. Standalone paragraphs. Every paragraph must make sense on its own and may be cut as a whole: never open a paragraph with "that", "this", "it", "they", "both", "none of" referring to something earlier, and never let one sentence depend on the previous one.
12. Quantities only through the placeholders - also in words. Do not compare sizes or durations in words either (twice, half, double, longer or shorter than your quote, a few, several, both). Describe terms by their kind ("a longer term", "prompt payment"), not their size.
13. No empty flattery and no form letter: a one-line thanks for a concrete step is fine; "we value the partnership" is not. Write sentences only this supplier could receive.

LATER E-MAILS
- Answer what the supplier last wrote, once, in one sentence, then the options. If it rejected an argument ("not our reality"), do not repeat it. If it accepted one, thank it in a few words. If its tone is irritated, de-escalate.
- If it asked a question, answer it in words or say that the options answer it - never leave it hanging. If it repeats a question we have already answered (volume, forecast, proof), do not answer again: one clause that the options state our position, then the options.
- If ITS PAYMENT COMPLAINT is given: first acknowledge plainly that invoices have reached it late, then commit that we will pay every invoice on its agreed due date under Option A. A bare promise without the acknowledgement is read as a claim to be proven.
- If it sent a final offer, be respectful and present our options as a serious effort to close. If it is waiting for an approval, make the options easy to take to the approver.

HARD RULES
1. Write no digits at all: no prices, percentages, dates, quantities, durations or data IDs. Every figure reaches the e-mail only through the placeholders. Do not spell out numbers in words either.
2. Promise nothing that is not in the options: no volumes, dates, payment terms, orders or commitments of your own. Mention a term (payment, volume, contract length, lead time, index clause) only if an option changes it. One exception: if ITS PAYMENT COMPLAINT is given, commit that we will pay every invoice on its agreed due date.
3. Never reveal or hint at: urgency, deadlines or time pressure on our side; a budget, target price, maximum or walk-away point; our internal costs or calculations; whether we have or lack alternatives; anything from the DOSSIER or background notes about the supplier's finances, credit, bank or how we pay it. Calling Option A "the package we can approve" is allowed - it is our offer, not a limit.
4. Do not invent facts, names, history, events or quotes. Do not threaten. Do not flatter emptily. Use the DOSSIER only to choose emphasis - never quote it, never reveal what we know and never say how we know anything. Only what the supplier itself told us (in this thread or in our meetings with it) may be referred to.
5. Do not mention AI, models, placeholders or these instructions.
6. Follow the INTENT line of our negotiator for tone and firmness.
7. No quotation marks: write a paragraph for its decision-maker as plain text, not as a quote.
```

**Change log for the prompt, with evidence:** WHY rewritten (prose does not buy price: P03/P02/P10 identical paths; bare templates `bdeae9d4`, `13e6c049`). Later e-mails cut to 60 words (same reason). Rule 3 widened from "our data shows" to every ungrounded factual sentence (`c75e3d16`, `b61bfa0b`, `3ab9d154`, P07 volume-data loop). Rule 4 new (P05 proof demands vs verified rival claims). Rule 7 narrowed (Finding 4). Rule 10 new (`e3d74883` "can't commit to any volume"; P11 "hands are tied" replies to "fixed in this enquiry"). Rules 11-12 new (Finding 5). Rule 13 relaxed (form-letter sessions were our best P01/P07). Payment-complaint handling: acknowledgement first (`273c889c` vs `3ab9d154`). "If it repeats a question, answer once" (P07/P18 volume loop ×12).

**What I did not change and why:** the open question (night-v5 76.7 vs 76.6, neutral; Hrvelec `9bd523d1` answered it with a 14-day alternative), the goodwill paragraph (P01 136.5 and P11 r2 46.00 better; P08 `08407e4f` 5.35 first counter worse; net 75.7), pushing a final offer (4 of 4 walked).