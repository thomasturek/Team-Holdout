# Buyer agent review: the writer, its prompt and guards (plus three policy items they depend on)

**Evidence used.** The diffs are against the files shown. Line numbers marked "≈" are counted by hand. Hunk headers name the function, so apply by context.

"Shows" means the code or the logs prove it. "Infer" means the claim is my reasoning. The expected-points ranges are rough judgements, not measurements.

Context from the logs: suppliers give most of what they will give in round 1, and identical sheets differ by 1–2 % between runs. Words alone moved the deterministic sandbox foundry D01 by about 1.2 % (learnings, "Words, D01"). A fully model-written e-mail matched the template to the cent on P02 and P18. So the writer's leverage lies mainly in **not losing** concessions: not ignoring asks, not contradicting the sheets, and not dropping its own useful sentences. Producing extra concession through style has less evidence behind it.

---

## Findings, ranked by expected points

### 1. Claim de-duplication has the wrong scope: rival offers reach only the first dearer bidder, and refs may leak across cases (policy.py `pick_claims`, ≈ lines 560–585)

**Shows.**
- `self.used_refs` and `self.used_keys` live on the `Policy` instance (`__init__`). They are keyed by ref, and by `(supplier_id, key)`, never by case.
- The pool filter `self.used_refs.isdisjoint(c.refs)` treats a rival `offer:` ref like any other ref.
- In an RFQ with bidders A (cheapest), B and C:
  - B gets "A's offer" as a `rival:` claim, which puts `offer:A-n` into `used_refs`.
  - C can then never be shown that offer.

**Rules and evidence.**
- api.md: "a rival's quote: in an RFQ you may cite it to every other bidder, and it counts once per supplier."
- Rival claims move suppliers 65 % of the time (NIGHT_CONTEXT).
- The other team's best RFQ runs cited the cheapest rival offer to *every* other bidder, every round (learnings: P05 0.83, D02 0.73). Their runs that skipped it scored 0.66.

**Infer.** If the runner shares one `Policy` across cases (the `self.banks` key `(case_id, supplier)` suggests it), two things follow:
- A falling-index ID used in case 1 blocks the same ID in case 2 of the same wave.
- The same supplier appearing in two hidden cases has its claim keys burned.

Check with `grep -n "Policy(" src/buyer/`.

**Expected value.** +0.02–0.05 per RFQ case with three bidders. If the policy is shared, more is at stake: up to several points per wave across the parallel cases.

**Diff A** below.

### 2. Asks we cannot meet get ignored or contradicted, and suppliers punish that (writer_system.md rule 2; writer.py `PLAYBOOK["quality"]` ≈ 258; dossier.py `ANGLES["cash_short_jobshop"]`)

**Shows.** The prompt layers conflict:
- Rule 2: "Mention a term … only if an option changes it."
- The quality playbook: "never offer, mention or imply faster payment."
- Angle A for cash-short shops: "lead with the faster-payment option as the reason Option A works."

When payment is fixed (P11; P12 too, per learnings), the model has two bad choices. It can obey the angle, which promises something the sheets do not give. Or it can obey rule 2 and stay silent about the supplier's main ask.

**Evidence.** Kalwisz asked for faster payment five times, then wrote "you just ignore it" and sent a final offer (learnings, Asks). P11 sits at 0.63–0.71 against a record of 0.807.

**Hidden-case risk.** The quality playbook hard-codes "payment terms and volume are fixed". A hidden quality case with negotiable payment would then forbid the model from mentioning an option we actually send. The same playbook says "a lower chargeback for a better price". That is the supplier's direction; C_best for P11 has chargeback 500. So the model may describe the sheets backwards.

**Infer.** A generic rule fixes all three: tell the model which fields are negotiable here. For any ask outside them, it acknowledges the ask in one sentence ("fixed in this enquiry") and points to what the options give instead.

**Expected value.** +0.03–0.08 on quality and cash-short cases, and it lowers early-final risk everywhere.

**Diffs B and C** below.

### 3. The volume line contradicts the volume trades the policy just built (writer.py `volume_line` ≈ 267–282)

**Shows.**
- The line reads only the lead sheet (`sheets[0]`) and asserts "Binding volume in every option: X units a year over M months."
- It fires exactly when the supplier asked about volume.
- That is also when `Policy.lever_trades` adds sheets with "the smallest volume step, a contract beyond the horizon" (policy.py `lever_trades` docstring; `offer()` inserts trades as Options B/C when `asks`).

So the e-mail says every option has volume X while Option B offers more. That undercuts the trade, and the statement is false.

**Evidence.** Volume is the most frequent ask: 152 + 62 of 829 supplier e-mails. Answering it in figures "registered" (learnings).

**Expected value.** +0.01–0.03 where volume or contract length is negotiable (14 of 21 case files).

**Diff D** below.

### 4. Replace the wasted cost-breakdown question in hold rounds with the question that moved D01 (policy.py `offer()`, holding branch ≈ 300–306; vocab.py `QUESTIONS`)

**Shows.**
- On every first hold, `offer()` asks for a cost breakdown.
- Suppliers refused a breakdown 12 of 12 times; the practice suppliers never sent one (learnings).
- D01, identical sheets: plain 50.00; "What would you need from us to move further?" 49.40 (one run, deterministic bot).
- The policy already turns `signals.asks` into lever trades.

**Counter-evidence.** Asking that question *every round* on practice got "volume!" with volume fixed, then no movement (P05, P18). So the proposal is once, on the first hold, which is where the useless breakdown request sits today.

**Expected value.** Uncertain; test on D01 first (deterministic, no quota). Possibly +0.01–0.02 on hold-prone suppliers. Keep the round-1 breakdown question for suppliers whose notes say "calculation".

**Diff E** below.

### 5. "Alternatives": the prompt asks for a word the guard drops, and the guard permits competitor talk on a false trigger (writer.py `SIGNAL_ALT_RE` ≈ 107; writer_system.md point 3)

**Shows, part 1.** Point 3 says "The other options are genuine alternatives for its convenience." `ALTERNATIVES_RE` drops any sentence containing "alternative(s)" unless the intent signals alternatives. The sentence that names Option A as our package is often the one that goes.

**Shows, part 2.** `SIGNAL_ALT_RE` matches "alternativ" anywhere in the intent. The mirror intent "we accept your alternative proposal as offered" (policy.py `close()`) therefore unlocks talk of other suppliers in single-supplier cases. That invites a bluff the model cannot back.

**Evidence.** Bluffs drew "built on mutual reliability, not on pressure" with no price gain (3 runs, learnings).

**Note.** Check whether the analyst emits intents with "alternatives": `grep -rn "alternativ" src/buyer`.

**Diffs F and G** below.

### 6. Background notes pass digits to the model, so its best sentences get dropped (writer.py `_clean_note` ≈ 305–311)

**Shows.**
- `_clean_note` strips IDs but keeps years and figures ("2022", "+9.5 %").
- The model is told to use the notes for emphasis, repeats the figure, and `foreign_numbers` drops the whole sentence.
- Enough drops push prose under `MIN_OWN_WORDS`, and the template replaces the model.

**Evidence.** Learnings: 9 of 15 dropped paragraphs carried the year 2022 from the persona text (5 of 8 on P01 at pre-flight). The dossier already strips digits (`dossier()` last line). The notes path does not.

**Expected value.** Small, but it hits the first e-mail, which is the one that counts.

**Diff H** below.

### 7. "Option A" does not exist when we send one sheet (compose.py `offers_block`)

**Shows.** With one sheet the block reads "Our proposal: …", yet the prompt says "Option A is always the first" and asks the model to name it ("Option A is the package we can approve"). Single-sheet messages are common: the mirror/close path, `menu` returning one sheet, `[a]` fallbacks. The supplier then reads a reference to an option that is not in the e-mail.

**Diff I** below.

### 8. False-positive late-payment confession (writer.py `LATE_PAY_RE` ≈ 285; `complains_of_late_payment`)

**Shows.**
- The regex fires on any non-buyer text with "late/overdue/delayed/slow" within 40 characters of "pay/payment/invoice".
- That includes boilerplate in an opening quote such as "Late payments incur interest".
- The prompt then orders: "it says we pay its invoices late. Acknowledge it plainly."

**Infer.** On a supplier that never complained, we admit late payment unprompted. That hands it a cash and relationship argument.

**Fix.** Require a complaint addressed to us ("you/your", "we often see"). Kalwisz's real wording, "we often see late payments", still matches.

**Diff J** below.

### 9. Final timing: model latency in RFQs with three bidders (writer.py `write`, client 20 s / retry / 25 s)

**Shows.**
- The arena serialises a session's calls; each bidder waits about (N−1) × 21 s, which for three bidders is 44 s median and 66 s p90 (learnings).
- The writer may use 25 s.
- `deadline` is optional in `write()`.

**Not shown.** Whether the runner passes `deadline`. If it does not, a 25 s writer on the third bidder overruns the 60 s clock. Timeouts drop the supplier's patience, and after a final offer one led to a walk (learnings).

**Recommendation (no diff; runner not shown).** Pass `deadline = thread_clock_start + 60 − (p90 policy time + 10 s)`. Use the template whenever three or more threads are waiting, as the other team did ("With three suppliers waiting we decide without the model", EVALUATION.md). Also check: three bidders × 10 rounds × 21 s = 630 s, which is more than the 480 s wave cap, so the cap-close rule must win over round planning.

### 10. Template and style sentences that are not true

All of these are flagged by inference; whether they cost price is unmeasured.

- **`concern_sentences`:** "We have taken your wishes on payment timing into account" fires whenever `payment_days` is a sheet field. It is always a field when negotiable, even if every sheet carries the reference 60 days. Gate it on a sheet's payment days being below the supplier's last standing term.
- **`CLOSING["cash_short_jobshop"]` and `STYLE` for cash-short shops:** they assert "punctual payment" as a fact. The data and Kalwisz say otherwise ("we pay late 93 %"; "we often see late payments"). Rephrase as forward-looking: "payment on the agreed due date".
- **Writer prompt:** it calls Hollerau "family-owned". The brief does not say so. The family-foundry angle ("both family companies") builds on it. Verify in the data, or drop the claim.

### 11. Digit tokens the guard should allow (guard.py `allowed_tokens`)

**Shows.** "8D" is natural in a quality case, but the only allowed source is the raw question keyword ("8d report"). Token matching is case-sensitive, so a model sentence with "8D report" is dropped. Part names outside the case title (bundles: "DN 65 flange") are dropped the same way. Low value; fix if time allows.

### 12. Hidden case types with no playbook

**Shows.** `price_increase` and `renewal` have no `PLAYBOOK` entry.

**Evidence.** Notice-period claims moved suppliers 100 % of the time. Price-frozen suppliers said "we can talk about the terms instead" (P03, P04).

**Proposal.** Two generic lines (Diff C):
- price_increase: it asked for more, so the claims answer it, and a later effective date in an option is framed as what the notice period allows.
- renewal: if it will not move on price, the options trade on the other terms.

### Other hidden-case risks (checked, no change needed)

- **Unknown archetypes** ("distributor", new Sunday-release suppliers with no SQL profile) fall back to `STYLE["unknown"]` and `ANGLES["unknown"]`.
- **Missing supplier name** gives the greeting "Dear Sir or Madam". Names in the supplier's e-mails are learned from `thread_text`, so greetings that use the signer's name survive the guard.
- **Hedged suppliers:** the prompt already says not to repeat a rejected argument. The other team found an index fall still lowered the first counter there, so keep citing it once.

---

## Diffs

**A — claim scope (policy.py, `pick_claims`)**

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def pick_claims(self, case, t):
         pool = [
             c for c in bank
             if c.strength >= self.p["claim_min_strength"]
-            and (t.supplier_id, c.key) not in self.used_keys
+            and (case["case_id"], t.supplier_id, c.key) not in self.used_keys
             and c.key not in rejected
-            and self.used_refs.isdisjoint(c.refs)
+            # an ID counts once per case - except a rival's offer, which may go to every other bidder
+            and (c.key.startswith("rival:") or self.used_refs.isdisjoint((case["case_id"], r) for r in c.refs))
         ]
@@ def pick_claims(self, case, t):
         for c in chosen:
-            self.used_refs |= set(c.refs)
-            self.used_keys.add((t.supplier_id, c.key))
+            self.used_refs |= {(case["case_id"], r) for r in c.refs}
+            self.used_keys.add((case["case_id"], t.supplier_id, c.key))
         return chosen
```

**B — tell the writer what is negotiable, and never ignore an ask (writer.py `build_prompt`, `PLAYBOOK`)**

```diff
--- a/src/buyer/llm/writer.py
+++ b/src/buyer/llm/writer.py
@@ PLAYBOOK = {
-    "quality": "Payment terms and volume are fixed in this enquiry: never offer, mention or imply faster payment or a "
-    "different volume. The trade is in the quality terms: a lower chargeback for a better price.",
+    "quality": "The trade is in the quality terms (defect commitment, chargeback) against the price: describe them "
+    "exactly as the options set them. A term not listed under NEGOTIABLE HERE is fixed: never offer or imply it.",
+    "price_increase": "It asks for more: the claim lines answer its reasons. If an option moves the effective date, "
+    "present that date as what the agreed notice allows.",
+    "renewal": "If it holds its price, keep the price of Option A and point to what the other options give it on "
+    "the other terms.",
@@ def build_prompt(decision, case, thread, profile, signals, claims, offers, questions) -> str:
     if attr(case, "type") in PLAYBOOK:
         lines.append(f"PLAYBOOK FOR THIS SITUATION: {PLAYBOOK[attr(case, 'type')]}")
+    negotiable = [str(f).replace("_", " ") for f in attr(case, "negotiable") or []]
+    if negotiable:
+        lines.append("NEGOTIABLE HERE: " + ", ".join(negotiable) + ". Every other term is fixed in this enquiry: if "
+                     "the supplier asks for one, say in one sentence that it is fixed in this enquiry and point to "
+                     "what the options give instead - never leave an ask unanswered.")
```

**C — prompt rule 2, alternatives wording, and the cash-short angle (writer_system.md, dossier.py)**

```diff
--- a/src/buyer/llm/prompts/writer_system.md
+++ b/src/buyer/llm/prompts/writer_system.md
@@ HOW TO WIN THE REPLY
-3. Option A is the package. Name Option A as the package we can approve, and give the reason in one sentence drawn from the claims and the options. The other options are genuine alternatives for its convenience.
+3. Option A is the package. Name Option A as the package we can approve, and give the reason in one sentence drawn from the claims and the options. Options B and C are genuine choices for its convenience - call them options, never alternatives.
@@ HARD RULES
-2. Promise nothing that is not in the options: no volumes, dates, payment terms, orders or commitments of your own. Mention a term (payment, volume, contract length, lead time, index clause) only if an option changes it. One exception: if ITS PAYMENT COMPLAINT is given, commit that we will pay every invoice on its agreed due date.
+2. Promise nothing that is not in the options: no volumes, dates, payment terms, orders or commitments of your own. Mention a term (payment, volume, contract length, lead time, index clause) only if an option changes it - or if the supplier asked for it: then say in one sentence that it is fixed in this enquiry (see NEGOTIABLE HERE) and what the options offer instead. One exception: if ITS PAYMENT COMPLAINT is given, commit that we will pay every invoice on its agreed due date.
--- a/src/buyer/facts/dossier.py
+++ b/src/buyer/facts/dossier.py
@@ ANGLES = {
-    "cash_short_jobshop": "Cash first: lead with the faster-payment option as the reason Option A works for it - "
-                          "never mention its finances.",
+    "cash_short_jobshop": "Cash first: if an option pays faster, lead with it as the reason Option A works for it; "
+                          "if none does, lead with steady orders and the terms the options do move - never mention "
+                          "its finances.",
```

**D — volume line (writer.py `volume_line`)**

```diff
--- a/src/buyer/llm/writer.py
+++ b/src/buyer/llm/writer.py
@@ def volume_line(case, decision, signals=None, thread=()) -> str:
     term = f" over {months} months" if months else ""
-    return f"Binding volume in every option: {volume:,} units a year{term}."
+    same = all(s.get("volume_per_year", volume) == volume and s.get("contract_months", months) == months
+               for s in sheets)
+    return f"Binding volume in {'every option' if same else 'Option A'}: {volume:,} units a year{term}."
```

**E — the needs question on the first hold (policy.py `offer`, vocab.py). Test on D01 before switching on.**

```diff
--- a/src/buyer/policy/policy.py
+++ b/src/buyer/policy/policy.py
@@ def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
         if t.holding:  # same price: lead with another package, ask for its costs once
             k = t.holds % len(sheets)
             sheets = sheets[k:] + sheets[:k]
             intent = "firm on price, open on the other terms"
             if not t.asked_breakdown:
-                questions, t.asked_breakdown = ["cost breakdown"], True
+                # no supplier shared a breakdown (12 of 12); D01 moved most on this question (49.40 vs 50.00)
+                questions, t.asked_breakdown = ["what would you need from us to move further"], True
--- a/src/buyer/llm/vocab.py
+++ b/src/buyer/llm/vocab.py
@@ QUESTIONS = (
+    ("needs", ("move further", "what would you need"),
+     "What would you need from us to move further on price?"),
     ("cost_breakdown", ("breakdown", "calculation", "cost structure", "cost split"),
```

**F — the alternatives trigger (writer.py)**

```diff
--- a/src/buyer/llm/writer.py
+++ b/src/buyer/llm/writer.py
@@
-SIGNAL_ALT_RE = re.compile(r"alternativ|competit|rival|other (?:offer|supplier|quote|bidder)|second source", re.I)
+# "your alternative proposal" (a mirrored package) is no licence to talk about other suppliers
+SIGNAL_ALT_RE = re.compile(r"signal alternatives|competit|rival|other (?:offer|supplier|quote|bidder)|second source",
+                           re.I)
```

**G** is the prompt line in Diff C (point 3).

**H — notes without figures (writer.py `_clean_note`)**

```diff
--- a/src/buyer/llm/writer.py
+++ b/src/buyer/llm/writer.py
@@ def _clean_note(note) -> str:
     note = ID_RE.sub("", str(note))
     note = re.sub(r"\b(?:sup|part|rfq|ctr|doc|news):[\w.:@#/-]*\w", "", note)
+    note = re.sub(r"[^\s()]*\d[^\s()]*", "", note)  # the model repeats a year or figure and the guard drops its sentence
     note = EMPTY_PARENS.sub("", note)
```

**I — one sheet is still "Option A" (compose.py `offers_block`)**

```diff
--- a/src/buyer/llm/compose.py
+++ b/src/buyer/llm/compose.py
@@ def offers_block(term_sheets) -> str:
     if len(sheets) == 1:
-        return "Our proposal: " + offer_line(sheets[0])
+        return "Our proposal, Option A: " + offer_line(sheets[0])
```

**J — only a real complaint triggers the payment commitment (writer.py)**

```diff
--- a/src/buyer/llm/writer.py
+++ b/src/buyer/llm/writer.py
@@
+COMPLAINT_RE = re.compile(r"\byour?\b|\bwe (?:often|regularly|still|keep|repeatedly) (?:see|receive|wait|get)\b", re.I)
+
+
 def complains_of_late_payment(thread) -> bool:
-    return any(LATE_PAY_RE.search(str(m.get("body") or "")) for m in (thread or []) if m.get("from") != "buyer")
+    sentences = (s for m in (thread or []) if m.get("from") != "buyer"
+                 for s in re.split(r"(?<=[.!?])\s+", str(m.get("body") or "")))
+    return any(LATE_PAY_RE.search(s) and COMPLAINT_RE.search(s) for s in sentences)
```

---

## How to validate without burning quota

1. **Offline tests:**
   - Diff D: a three-sheet decision whose Option B has a larger `volume_per_year` must produce "in Option A".
   - Diff J: "Late payments incur interest" must yield `False`, and "we often see late payments" must yield `True`.
   - Diff H: a note "held prices in 2022 (+9.5 %)" must have no digits.
   - Diff A: in a two-bidder simulator case, both dearer bidders must receive a `rival:` claim with the same `offer:` ref.
2. **D01 (deterministic) for Diff E:** paired runs with the hold question on and off, same sheets.
3. **Hosted, one run each:**
   - P05 (Diff A; watch `claim_results` on the third bidder).
   - P11 (Diffs B and C; watch for "you just ignore it" and the round of the final offer).
   - P07 (Diff D).

   Score noise is 1–2 % per run (learnings), so judge on the mechanism in the replay, not the score delta.
4. **Before the freeze:** confirm whether the runner passes `deadline=` to `write()` and how many `Policy` instances a wave uses (findings 1 and 9).