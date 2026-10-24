# `buyer.llm` - THE DIPLOMAT

The LLM reads supplier e-mails into `Signals` and writes our e-mails around the ANALYST's `Decision`.
Code guarantees the Definition of Done; the model only chooses words.

## How the OPERATOR calls it (one move of one thread)

```python
from buyer.llm import read, to_message

# 1. the supplier's reply -> Signals for the policy (<= 10 s, keyword rules as fallback)
reading = read(reply, last_decision=previous_decision)       # Reading(signals, source, latency_s, error, from_rules)

# 2. the policy decides (ANALYST) -> Decision(kind="send" | "accept" | "walk", ...)

# 3. the Decision -> the API message (<= 25 s, template as fallback)
message, email = to_message(
    decision, case, thread, profile, reading.signals,
    known_id=lambda i: scout_lookup(i) is not None or i in offer_ids_of_this_session,
)
client.send_message(session_id, decision.supplier_id, message)
# log reading (source, latency_s, error) and email (source, latency_s, warnings) with the move
```

- `reply` / `thread`: messages in the starter kit's format (`from`, `subject`, `body`, `status`,
  `claim_results`, `term_sheets`, attachments with `text`).
- `to_message` returns `{"subject", "body", "term_sheets": [{"terms": …}], "refs"}` for `send`,
  `{"action": {"type": "accept", "term_sheet_id": …}}` for `accept`, `{"action": {"type": "walk_away"}}`
  for `walk` (no LLM involved; `email` is `None` then). Term sheets go out exactly as in the Decision.
- `refs` = the IDs of the Decision's claims, in order.
- `known_id`: pass it. Without it only the IDs of the Decision's claims count as known, and every
  other data ID the model writes is removed.

## Time limits (DIPLOMAT.md, kept literally - team decision)

| Call | Per attempt | Retries | Whole call at most | Then |
|---|---|---|---|---|
| writer | 20 s hard wall-clock | 1 | 25 s | template |
| reader | 10 s | 1 (only if time is left) | 10 s | keyword rules |

The SDK's own retries are off. **OPERATOR: reader + writer in the same move can take up to 35 s in
the worst case** - more than the 25 s per-move budget in AGENTS.md. If that matters, pass
`deadline=` (a `time.monotonic()` value) to `read` / `write` / `to_message`; the call then ends by
that time and falls back.

## Environment (`.env`)

| Variable | Default | |
|---|---|---|
| `LLM_PROVIDER` | `anthropic` | or `openai` (any OpenAI-compatible endpoint), `none` |
| `LLM_MODEL` | - | unset = LLM off (templates and keyword rules only) |
| `LLM_EFFORT` | `low` | sent as `output_config.effort`; empty = not sent; dropped automatically if the model rejects it |
| `ANTHROPIC_API_KEY` | - | for `anthropic` |
| `LLM_BASE_URL`, `LLM_API_KEY` | - | for `openai` |
| `LLM_DISABLED` | - | `1` = no LLM at all (cheap mode, e.g. the sandbox harvester) |
| `LLM_READER_*`, `LLM_WRITER_*` | - | per-role override of any of the above, e.g. `LLM_READER_MODEL` for a faster reader |
| `BUYER_SIGNATURE` | `Purchasing\nHollerau Pumpenwerke GmbH` | our sign-off |

## What the writer guarantees

1. **Claims verbatim, each on its own line, in the Decision's order.** The model writes `[[CLAIM_n]]`,
   `[[OFFERS]]`, `[[QUESTIONS]]` (sloppy forms like `[CLAIM_1]` or `{{OFFERS}}` are understood);
   code fills in the exact claim sentences, the term-sheet lines and the questions. Text glued to a
   placeholder is dropped (an intro ending in ":" stays as its own line). Missing ones are injected,
   extra ones removed. At most 3 claims. Because body order = `refs` order = `Decision.claims`
   order, `claim_results[i]` in the reply belongs to `Decision.claims[i]`.
2. **No figures in the model's prose at all.** A sentence is dropped if it holds a digit token not
   found in the case title, the supplier's name or our questions (e.g. "HN 50-200", "IE3", "8D"),
   a number with a unit ("8%", "EUR 120", "14k") or a number in words with a unit ("ten percent").
   Every figure comes from code. A sentence with an ID of one of our claims (a reworded claim) is
   dropped too.
3. **No unknown IDs** (`known_id`), as in the kit's `agents/llm.py`.
4. **No leaks.** Sentences about urgency, deadlines, budget, targets, a missing alternative, our
   costs or the supplier's finances are dropped (`vocab.LEAK_RE`). Talk of other suppliers or
   offers is dropped unless the `intent` contains "alternative", "competition", "rival",
   "other offer" or "second source".
5. **No invented people.** A greeting or sentence naming someone ("Mr Huber") who never appeared
   in the supplier's name or e-mails is replaced / dropped; the model's sign-off is cut and ours added.
6. `verify_email` checks the finished body; on any problem the deterministic **template** goes out.
   The template is also used when the LLM is off, late or broken, or anything raises - `write`
   never raises for a `send` Decision.

What the model sees: supplier name, country, archetype and style, case title and type, the
`intent`, the Signals, profile notes **without IDs**, the last 4 messages of the thread, the claim
sentences, the term-sheet lines and the questions. It never sees the briefing, the buyer block
(need, prices, alternative, must-haves) or any C.

## For the ANALYST: `Decision` fields the writer reads

- `term_sheets`: complete terms dicts (or `{"terms": …}`), up to 3, rendered as "Option A/B/C".
- `claims`: up to 3 `Claim`s (`sentence` pasted verbatim, `refs` go into `refs`).
- `questions`: free strings; these keywords get a well-phrased question (`vocab.QUESTIONS`):
  `cost breakdown`, `8D report` / `corrective`, `delivery schedule`, `lead time`, `variants`,
  `capacity`, `payment`, `volume` / `contract length`, `index`, `approval`. Anything else is asked as written.
- `intent`: one line on tone and firmness, shown to the model (its numbers are never allowed into
  the e-mail). Contains "final", "closing", "best and final" or "last offer / round / move / push" ->
  the template says "This is our best proposal at this stage." Contains "alternative" (or
  "competition", "rival", "other offer", "second source") -> the e-mail may mention other offers.

## For the ANALYST: reading `claim_results`

The reply's `claim_results[i]` belongs to `Decision.claims[i]` of the Decision it answers (claims
go out in that order, first in `refs`). This holds as long as each `Claim` is one argument for the
arena (the SCOUT's design) and the model wrote no other known data ID in its prose - such IDs come
after the claims, so they can only add results at the end.

## For the ANALYST: `Signals` values (fixed vocabularies, `vocab.py`)

| Field | Values |
|---|---|
| `asks` | `faster_payment`, `volume`, `longer_contract`, `forecast`, `earlier_effective_date`, `index_clause`, `longer_lead_time`, `tooling_payment`, `incoterm`, or `other: <few words>` |
| `cost_drivers_claimed` | an index series code as written (`LCI-C`, `PPI-C241`, …) or `energy`, `labour`, `raw_material`, `steel`, `copper`, `aluminium`, `nickel`, `electronics`, `polymers`, `logistics`, `financing` |
| `accepted_args`, `rejected_args` | the `Claim.key` of our argument when it can be told, else a few words |
| `tone` | `warm`, `neutral`, `irritated` |
| `final_offer_language` | also `True` whenever the reply's status is `final_offer` |
| `capacity_issue` | the supplier is short of capacity; free capacity is `asks: volume` instead |

The keyword rules (used when the model is off or late, and for fields the model left out) ignore
signature and footer lines, negated phrases ("no shortage", "would not change our price") and
material words outside a sentence about costs ("made of stainless steel").

## Files

| File | |
|---|---|
| `client.py` | the one LLM client (Anthropic / OpenAI-compatible), hard time limits, latency stats |
| `writer.py` | Decision -> e-mail (`write`, `to_message`) |
| `template.py` | the deterministic fallback e-mail |
| `reader.py` | e-mail -> Signals (`read`, `rule_signals`) |
| `compose.py` | code-made text: term-sheet lines, questions, subject, greeting, sign-off |
| `guard.py` | numbers, IDs, leaks, the final check |
| `vocab.py` | vocabularies, archetype styles, leak words |
| `prompts/` | the system prompts |
| `bench.py` | latency under load: `uv run python -m buyer.llm.bench` (10 cases x 3 threads; `--dry` for the harness) |
| `review.py` | replay review and fixture export: `uv run python -m buyer.llm.review report|fixtures` |
| `tests/` | `uv run pytest src/buyer/llm`; the live model test runs with `LLM_LIVE_TESTS=1` |

## Sunday checklist (P2)

1. `uv run python -m buyer.llm.review report --set practice --limit 25 --out runs/review/practice.md`;
   read it, write findings with replay link and supplier into `docs/LEARNINGS.md`, tune `prompts/` and `vocab.py`.
2. `uv run python -m buyer.llm.review fixtures --limit 30 --out src/buyer/llm/tests/fixtures/recorded_emails.json`;
   correct `expected` by hand and merge them into `supplier_emails.json`.
3. `LLM_LIVE_TESTS=1 uv run pytest src/buyer/llm -k live -s` - the reader model on the fixtures.
4. `uv run python -m buyer.llm.bench` - must print PASS (move p95 <= 15 s). If not: faster model or
   lower effort for the slow role (`LLM_READER_MODEL`, `LLM_WRITER_EFFORT`, …) and run again.
