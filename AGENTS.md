# AGENTS.md - source of truth

Read this first. It is the plan, the architecture, the roles and the priorities for our entry in the
Tacto Negotiation Arena. If code, a chat or another doc disagrees with this file, this file wins until
someone updates it. Change it deliberately, in its own commit, and tell the team.

Background you must know before touching anything: [`CHALLENGE.md`](CHALLENGE.md),
[`brief/brief.md`](brief/brief.md), [`brief/api.md`](brief/api.md),
[`starter-kit/README.md`](starter-kit/README.md), [`data/README.md`](data/README.md).

---

## 1. The idea in one paragraph

Our buyer agent learns how suppliers behave **before** it meets a real one. We build a synthetic
supplier in code from the rules in the brief, randomise its hidden settings, and train a small
negotiation policy against thousands of them (self-play). The real arena (sandbox without quota,
200 practice sessions per 24 h) is used to calibrate the simulator, not to learn from scratch. At run
time the agent plays every thread and every case in parallel.

**Code knows the rules. Machine learning learns the strategy. The LLM speaks the language.**

| Layer | Does | Never does |
|---|---|---|
| Plain code | Reads the data, computes C with the official formula, builds data claims with exact IDs and figures, checks must-haves and the alternative | Guess |
| ML policy | Chooses term sheets, trades between levers, decides accept / walk / push | Write text |
| LLM | Reads supplier e-mails into fixed signals; writes our e-mail around the terms the policy chose | Decide or change a number, a term, an ID, or accept / walk |

---

## 2. Hard facts and constraints (from the brief - do not violate)

| Fact | Consequence for us |
|---|---|
| Score per case = `(C_open - C_deal) / (C_open - C_best)`, clipped 0..1; broken must-have = 0; no deal = alternative's score | Every decision is evaluated in € with `arena_kit.cost.total_cost`. Never accept a sheet that breaks a must-have or loses to the alternative |
| Only term sheets bind; missing fields close on the supplier's **standard terms** (quote PDF) | Always send complete term sheets (`complete_offer`); always read standard terms (`docs.standard_terms`) before costing or accepting |
| 60 s per message per thread, counted from the supplier's reply; 3 timeouts in a row end the thread | Decision + LLM writing must finish in **< 25 s**. Per-thread concurrency is mandatory in RFQs |
| Supplier reply can take up to ~60 s | HTTP timeout 180 s (kit default). Plan for ~6-7 rounds per thread inside an 8-min wave, not 10 |
| Up to 3 term sheets per message | Use 2-3 sheets every round to probe what the supplier values |
| Claims: max 3 checked per message, ID + figure in the same sentence, wrong figure / unknown ID = `contradicted` = lost trust | Claims are built and verified in code only; the LLM pastes them verbatim |
| Rival quotes/offers may be cited in RFQs (once per supplier) | Cite the cheapest rival to every other bidder |
| `stabilise` / `secure_supply`: C charges for leaving the supplier below `sustainable_margin_pct` | Policy stops pushing at the supplier's sustainable margin in those cases |
| Limits per key: 10 calls/s, 10 open sessions | One shared, paced `ArenaClient` per process |
| Practice quota: 200 sessions / rolling 24 h. Sandbox (`case:D01`, `case:D02`) and final do not count | Sandbox = unlimited training data. Practice = budgeted calibration and validation (see section 6) |
| Final: 5 waves x 8 min, hidden cases, new suppliers, no human in the loop, must not read `/v1/events`, `/screen`, `/leaderboard`, `/results` | Agent never touches those endpoints. Ever. |
| Sunday 08:00: data release (`arena data`), hidden cases may cite it; hidden case files may carry their own `facts` | Data layer merges the release and `case["facts"]` automatically |
| Code freeze Sun 13:00, final from 13:30 | Everything below is planned backwards from that |

---

## 3. Architecture

```
                 GET /v1/cases (case files arrive before the clock runs)
                                   |
                                   v
 +---------------- SCOUT (plain code) -----------------+
 | DataPackage + case.facts + Sunday release             |
 | SupplierProfile per supplier  |  Claim bank per case  |
 | Costing: C of any term sheet, standard terms, must-haves, alternative |
 +-------------------------------------------------------+
                                   |
                                   v
 +--------------- ANALYST (ML policy) ----------------------+
 | Policy(params.json): state -> Decision                 |
 | state = case, profile, offers so far, signals, rounds/time left |
 | trained offline against SyntheticSupplier population   |
 +--------------------------------------------------------+
            ^ signals                       | Decision (terms, claims, intent)
            |                               v
 +--------------- DIPLOMAT (LLM) -------------------------+
 | Reader: supplier e-mail + attachments -> Signals (JSON)|
 | Writer: Decision -> subject + body (claims verbatim)   |
 +--------------------------------------------------------+
                                   |
                                   v
 +--------------- OPERATOR (runtime) ---------------------+
 | Per-thread workers, per-case sessions, wave runner,    |
 | deadlines, retries, logging of everything, harvesting  |
 +--------------------------------------------------------+
                                   |
                                   v
                     arena.tacto.ai  /  arena-sim
```

### Code layout (target)

```
pyproject.toml              root project; depends on starter-kit (arena-kit) as a path dependency
src/buyer/
  facts/                    SCOUT
    package.py              load DataPackage + Sunday release + case.facts
    profile.py              SupplierProfile builder
    claims.py               Claim bank: verified sentences with IDs
    costing.py              thin wrappers over arena_kit.cost (C, deltas, lever values)
  policy/                   ANALYST
    policy.py               Policy class: decide(state) -> Decision
    params.json             trained parameters (versioned, committed)
  sim/                      ANALYST
    supplier.py             SyntheticSupplier
    population.py           sampling of hidden supplier settings
    env.py                  episode runner using real case files + cost.py scoring
    train.py                optimiser (CMA-ES / random search)
    calibrate.py            fit population ranges to logged real runs
  llm/                      DIPLOMAT
    client.py               provider wrapper, timeouts, fallback
    reader.py               e-mail -> Signals
    writer.py               Decision -> e-mail
    prompts/                prompt files
  runtime/                  OPERATOR
    agent.py                BuyerAgent: wires Scout + Analyst + Diplomat
    threads.py              concurrent per-thread loop
    runner.py               practice / sandbox / final runners
    harvest.py              sandbox + practice data collection
    log.py                  JSONL run logs
runs/                       logs and harvested data (gitignored, except curated datasets)
```

### Interfaces (contracts between roles)

These are the seams. Change them only with agreement of both sides; update this section when you do.
They live in [`src/buyer/interfaces.py`](src/buyer/interfaces.py) - import them from there. The fixed
values of the `Signals` lists are in [`src/buyer/llm/README.md`](src/buyer/llm/README.md).

```python
@dataclass
class SupplierProfile:              # SCOUT -> ANALYST, DIPLOMAT
    supplier_id: str
    name: str
    country: str
    owner_type: str                 # family | group | ... (supplier_intel)
    archetype: str                  # family_foundry | group_ladder | cash_short_jobshop | near_monopolist | unknown
    floor_estimate: float | None    # EUR per price_unit: full cost (should_cost x country factor, or derived)
    floor_confidence: float         # relative error, e.g. 0.05 / 0.15
    cash_rate_estimate: float       # what money is worth to it per year (>= 0.08 when cash-short)
    cash_pressure: float            # 0..1 from equity ratio, credit index trend, our late payments, notes
    approval_style: str             # flat | ladder
    cost_drivers: list[dict]        # [{series, weight, change_12m_pct, ids: (from, to)}]
    history: dict                   # past asked vs settled changes (negotiation_history)
    quality: dict                   # latest scorecard: otd_pct, ppm, colour, ids
    notes: list[str]                # short findings from correspondence and news, with doc/news IDs
    standard_terms: dict            # from the quote PDF once the session is open

@dataclass
class Claim:                        # SCOUT -> DIPLOMAT (via ANALYST)
    key: str                        # e.g. "index:PPI-D351", "rival_quote:70140", "notice:doc+ctr"
    sentence: str                   # final English sentence, figure and IDs included, verified offline
    refs: list[str]
    expected: str                   # "verified"
    strength: float                 # 0..1 prior from the SCOUT; only the ANALYST uses it to choose

@dataclass
class Signals:                      # DIPLOMAT (reader) -> ANALYST
    cash_pressure: bool
    capacity_issue: bool
    final_offer_language: bool
    approval_pending: bool
    cost_drivers_claimed: list[str] # series or words the supplier blames
    accepted_args: list[str]        # what it said "fair point" to
    rejected_args: list[str]        # "not our reality"
    asks: list[str]                 # what it wants: volume, longer contract, faster payment, earlier date...
    offered_variants: list[str]     # cheaper engineering variants etc. (information only)
    tone: str                       # warm | neutral | irritated

@dataclass
class Decision:                     # ANALYST -> DIPLOMAT, OPERATOR
    kind: str                       # "send" | "accept" | "walk"
    supplier_id: str
    term_sheets: list[dict]         # complete, snapped (complete_offer); empty for accept/walk
    accept_sheet_id: str | None
    claims: list[Claim]             # <= 3, never one already used in this case for this supplier
    questions: list[str]            # e.g. "cost breakdown", "earliest lead time"
    intent: str                     # one line for the writer: "firm, appreciative, signal alternatives"
```

---

## 4. The roles

Each role has its own file with its tasks, priorities and definition of done. Pick one, read it, work
only inside its folder.

| Role | File | Owns | Mission |
|---|---|---|---|
| THE SCOUT | [`roles/SCOUT.md`](roles/SCOUT.md) | `src/buyer/facts/` | Exact numbers, supplier profiles, claims that always verify |
| THE ANALYST | [`roles/ANALYST.md`](roles/ANALYST.md) | `src/buyer/policy/`, `src/buyer/sim/` | Policy trained in simulation, calibrated on real runs |
| THE DIPLOMAT | [`roles/DIPLOMAT.md`](roles/DIPLOMAT.md) | `src/buyer/llm/` | LLM reads supplier e-mails, writes ours; fast and safe |
| THE OPERATOR | [`roles/OPERATOR.md`](roles/OPERATOR.md) | `src/buyer/runtime/`, `pyproject.toml`, `runs/` | Everything in parallel, nothing times out, everything logged |

### Who owns what (no overlaps - if it's not here, ask before building it)

| Thing | Owner | Others |
|---|---|---|
| Reading the data package, case facts, Sunday release | SCOUT | nobody else reads raw data |
| Cost C, lever values in €, must-have and alternative checks | SCOUT | everyone calls `facts/costing.py` |
| Supplier profiles, floor / cash / archetype estimates, `runs/profiles/all.json` | SCOUT | |
| Verified claims (building and checking them) | SCOUT | |
| Parsing session documents (quote PDF, cost breakdown, 8D, schedule) into numbers | SCOUT | |
| Synthetic supplier, training population, training, calibration | ANALYST | |
| Policy: offers, levers, claim choice, accept / walk / push, closing move | ANALYST | |
| `params.json`, `explore.json` | ANALYST | |
| LLM client (the only one), prompts | DIPLOMAT | SCOUT may call the client offline |
| Reading supplier e-mail prose into `Signals` | DIPLOMAT | |
| Writing our e-mails, template fallback | DIPLOMAT | |
| API calls, sessions, threads, parallelism, clock, retries, crash resume | OPERATOR | |
| Logging, harvesting, practice quota, final runner, submission | OPERATOR | |

---

## 5. Timeline (Saturday 24 Oct -> Sunday 25 Oct, CET; clocks go back overnight)

| When | Scout | Analyst | Diplomat | Operator |
|---|---|---|---|---|
| Sat now -> 18:00 | package, costing, floor, claim bank | policy v0 | client, writer, template fallback | pyproject, logging, per-thread loop, harvester |
| Sat 18:00 | **Integration: full agent v0 plays all 10 practice cases once + sandbox** | | | |
| Sat 18:00 -> 24:00 | profiles, archetypes, cash, miner | SyntheticSupplier, population, env, train | reader, doc parsing | runner, quota manager, rehearsal; harvester runs all night |
| Sat night | | training runs | | sandbox harvesting |
| Sun 08:00 | Sunday release | calibrate on logs, retrain | replay review, latency test | `arena data`, pre-flight |
| Sun 11:00 | | **policy freeze candidate** | | full practice run with frozen params |
| Sun 12:00 | | `params.json` frozen | | README, tag commit |
| Sun 13:00 | **Code freeze, submit hash** | | | |
| Sun 13:15 | | | | final runner started |

If anything slips: policy v0 + writer + per-thread loop is a complete, submittable agent. Protect it.

---

## 6. Practice quota budget (200 per rolling 24 h)

| Use | Sessions |
|---|---|
| Baseline: naive and LLM kit agents on all 10 hosted cases | 20 |
| Agent v0 on all 10 cases | 10 |
| Calibration runs (varied params, logged for the Analyst) | 90 |
| Validation of trained policy (held-out comparison) | 40 |
| Sunday pre-flight and final check | 20 |
| Reserve | 20 |

Sandbox runs are unlimited: default to the sandbox for anything experimental.

---

## 7. Guardrails (every role, always)

- Never accept a sheet that breaks a must-have or costs more than the alternative. Check with
  `must_haves_ok` and `total_cost` including the supplier's standard terms.
- Never send an ID that is not in `facts.json`, the Sunday release or `case["facts"]`.
- Never let the LLM produce a number that reaches a term sheet.
- Never read `/v1/events`, `/screen`, `/leaderboard`, `/results` from agent code.
- Never commit `.env`, keys, or LLM keys. `runs/` raw logs stay out of git.
- One API key, one shared paced client per process.
- Every move inside 25 s of the supplier's reply.

---

## 8. Open questions for Tacto (ask at office hours, record answers in `docs/IDEA.md`)

- Do sandbox and practice suppliers use the same engine as the hidden ones, only with different settings?
- Supplier reply latency in the final with every team playing at once?
- Are hidden-case suppliers among the 46 in the package, or new?
- Does a longer contract or volume commitment lower the price in practice?

---

## 9. Working rules for agents

- State your role at the start of a task. Stay inside your folder unless the task says otherwise.
- Interface changes (section 3) need both sides' agreement and an update to this file.
- Write tests for your module; `uv run pytest` must stay green.
- Log learnings from replays in `docs/LEARNINGS.md` with the replay link and the supplier.
- When in doubt, protect the submittable agent first (section 5, last line).
