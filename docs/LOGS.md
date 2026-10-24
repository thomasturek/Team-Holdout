# Run logs (OPERATOR → ANALYST, DIPLOMAT)

Every session the runtime plays is logged in full, one file per session:

```
runs/<set>/<case>/<session>.jsonl      e.g. runs/sandbox/case_D02/9f3c...jsonl
```

`<set>` is `practice`, `sandbox`, `final` (or `sim` for the local simulator). `:` in IDs becomes `_`
(Windows file names). `runs/` is gitignored; curated datasets can be added with `git add -f`.
`BUYER_RUNS=<folder>` logs somewhere else (e.g. tries against arena-sim).

## The sandbox harvester

```bash
uv run python -m buyer.runtime.harvest                  # until Ctrl+C (running sessions finish first)
uv run python -m buyer.runtime.harvest --sessions 40    # or --hours 8; --parallel 8 (default)
```

Plays `case:D01` and `case:D02` non-stop with the Analyst's policy (`--agent policy`, the default):
episode `n` plays case `n % 2` with parameter set `(n // 2) % len(sets)` from
`src/buyer/policy/explore.json` - a JSON list of parameter dicts, re-read before every session, so
it can be edited while the harvester runs. A set only needs the keys it changes; the rest come from
`params.json`. No file: `params.json` alone. Sandbox sessions cost no practice quota. It also saves
the sandbox and practice case files to `runs/cases/sandbox.json` and `runs/cases/practice.json`
(what `sim/env.py` loads). Until the Scout and Diplomat are wired in, the policy plays without
supplier profiles (`profile` is `{}`) and with a fixed template e-mail.

**Probes.** Every 3rd session (`--probe-every 3`, `0` = none) is a probe: the same policy, but it
pushes once past a final offer (`push_final` forced on), or proposes one of the case's
`payment_days` options on every term sheet, or both - cycling through the variants. Probe sessions
carry `run.probe`, e.g. `{"push_final": true, "payment_days": 30}` (`null` for plain sessions), so
they can be studied or left out. In a payment probe the `decision` trace keeps the policy's own
sheets under `trace.probe.agent_sheets`.

## One JSON file per sandbox session: `runs/sandbox_sessions/`

Each ended session is also saved as one file, `runs/sandbox_sessions/<ended at>_<case>_<session>.json`
(sorted by time), everything fetched from the API after the end:

| key | |
|---|---|
| `session_id`, `case_id`, `set`, `saved_at`, `end_reason`, `replay_url` | |
| `run` | the settings it ran with, as on the JSONL `case` line (parameter set, probe, harvest id) |
| `case` | the case file |
| `threads` | `{supplier_id: GET /v1/sessions/{sid}/threads/{supplier_id}}` exactly as returned: `messages` (every e-mail both ways, in order), `status`, `closed`, `offer_id`, `timeouts` |
| `result` | the session result (deal, terms, `c_open`, `c_deal`, `c_alt`, `c_best`, `score`, `cost_breakdown`) with the `trace` |

Attachment text and our timings and decisions are only in the JSONL logs below.

## Reading them

```python
from buyer.runtime.log import iter_logs, read

for path in iter_logs("sandbox"):          # oldest first; iter_logs() = every set
    events = read(path)                     # list of dicts, in the order they happened
```

```bash
uv run python -m buyer.runtime.log summary --set sandbox    # one line per session
```

## Events

Every line is one JSON object with `t` (unix time, seconds) and `kind`. Supplier messages are
exactly as the API returns them (see `brief/api.md`, Messages), attachments with their text under
`"text"`.

| kind | when | fields |
|---|---|---|
| `case` | first line | `case_id`, `session_id`, `case` (the full case file), `run`: `{agent, params, params_index, explore, harvest, episode}` - `explore` is a fingerprint of explore.json, `harvest` the harvester run's id |
| `opening` | right after | `threads`: `{supplier_id: [opening message]}` with quote PDF text |
| `sent` | each message we send | `supplier_id`, `message` (as sent), `decide_s` (supplier reply → our send) |
| `reply` | each supplier reply | `supplier_id`, `message` (status, term_sheets, claim_results, signals, attachments - their text follows in `attachment` events), `wait_s` (how long the reply took) |
| `attachment` | an attachment of a reply finished downloading (in the background, so a thread never waits for it) | `supplier_id`, `attachment_id`, `name`, `text` |
| `decision` | before each move of the policy | `supplier_id`, `trace`: `{decision: {kind, supplier_id, term_sheets, accept_sheet_id, claims, questions, intent}, rival_best_c}` (later also Signals) |
| `hold` | the decision was too slow; a holding message went out instead | `supplier_id`, `after_s` |
| `drop` | we stopped playing a thread (agent walked away from one bidder, or the round limit) | `supplier_id`, `reason` |
| `refresh` | after a `409` (late, round limit, thread ended), or with `why: "closing"` after a failed closing attempt: the thread as the arena has it | `supplier_id`, `thread`, `why` |
| `error` | an API error or a crash in a thread | `supplier_id`, `status`, `detail`, `where` |
| `closing` | one attempt to end the case (accept or walk away); there can be several if one fails | `supplier_id`, `message`, `why` (agent / cap near / no thread left) |
| `close_failed` | the attempt was refused (422 e.g. a stale term sheet, 409) or got no answer (network) | `supplier_id`, `status`, `detail`, `unconfirmed` (true: it may have landed - the arena is asked before anything else) |
| `closed` | the arena confirmed the end | `supplier_id`, `how` (`reply`: the result came with the answer; `reconciled`: GET session said ended), `end_reason` |
| `close_unresolved` | outside a wave the runtime stopped trying (MAX_CLOSE_ATTEMPTS) with the case still open | `why`, `attempts` |
| `result` | the case ended | `result` (deal, terms, `c_open`, `c_deal`, `c_alt`, `c_best`, `score`, `cost_breakdown`) |
| `session` | after the end | `data` = `GET /v1/sessions/{sid}`; `data.result.trace` = per move `{round, actor, move, reasons}` |
| `backoffice` | after the end | `data` = `GET /v1/sessions/{sid}/backoffice`, or `error` (403 in the final) |

Fields may be missing when they don't apply; read with `.get()`.

**In the final** the trace and the back office stay closed until the whole final is over, so those
logs end with a `session` without trace and a `backoffice` error. Afterwards:

```bash
uv run python -m buyer.runtime.log backfill --set final
```

appends the missing `session` / `backoffice` lines (marked `"backfill": true`). Running it twice
adds nothing twice.

## Example: score per parameter set

```python
from collections import defaultdict
from buyer.runtime.log import iter_logs, read

scores = defaultdict(list)
for path in iter_logs("sandbox"):
    events = read(path)
    run = next(e for e in events if e["kind"] == "case").get("run", {})
    result = next((e["result"] for e in events if e["kind"] == "result"), None)
    if result:
        scores[(run.get("explore"), run.get("params_index"))].append(result.get("score") or 0)
```

Per-round concessions for calibration: the `reply` events of one `supplier_id`, in order -
`message.term_sheets[0].terms.unit_price` and `message.status`, against the `sent` term sheets
before them; `wait_s` is how long each reply took.
