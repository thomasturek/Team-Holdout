# Run logs (OPERATOR → ANALYST, DIPLOMAT)

Every session the runtime plays is logged in full, one file per session:

```
runs/<set>/<case>/<session>.jsonl      e.g. runs/sandbox/case_D02/9f3c...jsonl
```

`<set>` is `practice`, `sandbox`, `final` (or `sim` for the local simulator). `:` in IDs becomes `_`
(Windows file names). `runs/` is gitignored; curated datasets can be added with `git add -f`.

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
| `case` | first line | `case_id`, `session_id`, `case` (the full case file) |
| `opening` | right after | `threads`: `{supplier_id: [opening message]}` with quote PDF text |
| `sent` | each message we send | `supplier_id`, `message` (as sent), `decide_s` (supplier reply → our send) |
| `reply` | each supplier reply | `supplier_id`, `message` (status, term_sheets, claim_results, signals, attachments), `wait_s` (how long the reply took) |
| `decision` | when the agent hands over a trace | `supplier_id`, `trace` (e.g. the Decision and Signals - whatever the agent returns under `"trace"`) |
| `hold` | the decision was too slow; a holding message went out instead | `supplier_id`, `after_s` |
| `drop` | we stopped playing a thread (agent walked away from one bidder, or the round limit) | `supplier_id`, `reason` |
| `refresh` | after a `409` (late, round limit, thread ended): the thread as the arena has it | `supplier_id`, `thread` |
| `error` | an API error or a crash in a thread | `supplier_id`, `status`, `detail`, `where` |
| `closing` | the accept or walk-away that ends the case | `supplier_id`, `message`, `why` (agent / cap near / no thread left) |
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

**Planned:** the harvester and runner will add the run's settings (agent name, policy parameter set
from `explore.json`) to the `case` line, so each episode can be matched to the parameters it ran with.
