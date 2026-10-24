# Overnight improvement loop - plan and briefing

**Who this is for.** The Claude session(s) that improve the agent unattended overnight, and the team
that reviews the result in the morning. If you are the overnight Claude: read this whole file, then
`AGENTS.md`, before touching anything. Everything you need is here or linked from here; nobody will
answer questions until the morning.

**Goal.** Raise the arena score of our buyer agent with changes that are *measured*, keep only the ones
that beat the noise, and hand the team a short evidence-backed list before the policy freeze (Sun 25 Oct
11:00, code freeze 13:00). Credits are limited: spend tokens on writing code, never on trying values.

**The idea in one line: a ratchet.** Every experiment is a small change measured against one fixed
scoreboard on the same supplier draws. It is kept only if it beats the noise; otherwise it is reverted
and the reason is logged. Complexity that does not move the score never survives the night.

---

## 0. Orientation for the overnight Claude

### 0.1 The project in five sentences

We are a team of four building a buyer agent for the Tacto Negotiation Arena: it negotiates with
LLM-driven supplier bots over term sheets, and each case is scored
`score = (C_open - C_deal) / (C_open - C_best)`, clipped to 0..1, where `C` is the buyer's total cost
from `arena_kit.cost.total_cost` (price, payment terms, freight, uncovered need, quality, index clause,
and for `stabilise` / `secure_supply` cases a relationship cost). Plain code owns every number; the
policy (`src/buyer/policy/policy.py`, "V0", owned by Thomas) chooses offers; the LLM only reads supplier
e-mails and writes ours. The final is on Sunday afternoon, 5 waves x 8 minutes, hidden cases, no human
in the loop. `main` is the submission and must stay green and untouched by you.

### 0.2 Where things are

| Path | What | Owner |
|---|---|---|
| `AGENTS.md` | The rules. Read sections 2, 3, 7 and 9 | all |
| `src/buyer/policy/policy.py` | Policy V0: `Policy.decide(case, ThreadState, rival_best_c)`, `closing`, `offer`, `best_options`; parameters in `params.json`, bounds in `BOUNDS` | Thomas (ANALYST) |
| `src/buyer/sim/` | Synthetic supplier (`supplier.py`), population sampling (`population.py`, `ranges.json`), episode runner (`env.py`), trainer (`train.py`, CMA-ES-like), calibration (`calibrate.py`, `metrics.py`), V1-vs-V2 (`compare.py`), V3 harness (`robust.py`, `mutations.py`) | Thomas |
| `src/buyer/facts/` | Data package, supplier profiles (`profile.py`, `memory.py` + `memory.json`), verified claims (`claims.py`), V2 shield (`shield.py`), V3 case gates (`case_check.py`) | Felix (SCOUT) |
| `src/buyer/llm/` | LLM client, reader (e-mail -> `Signals`), writer, keyword rules, accuracy tool (`accuracy.py`) | Hichem (DIPLOMAT) |
| `src/buyer/runtime/` | Agent wiring (`agent.py`, `BUYER_POLICY`, `BUYER_READER`), per-thread loop (`threads.py`), runner, logs | Alex (OPERATOR) |
| `runs/cases/practice.json`, `runs/cases/sandbox.json` | 21 real cases as lists (19 practice P01-P19, sandbox D01-D02); `sim.env.load_cases()` adds the 3 kit cases S01-S03 = 24 | data |
| `src/buyer/facts/costing.py` | The relationship charge with the Scout's estimate of the supplier (Felix, `71b59f1`) | Felix |
| `runs/practice_sessions/*.json`, `runs/sandbox_sessions/*.json` | 34 + 341 complete logged real sessions (format in 0.4) | data |
| `runs/practice/<case>/*.jsonl`, `runs/sandbox/<case>/*.jsonl` | Per-session event logs (our decisions, traces) | data |
| `tests/` + `src/buyer/llm/tests/` | `uv run pytest` runs these; **`src/buyer/facts/tests` is not in `testpaths`** - run it explicitly too | all |
| `docs/PHASE2_SAFE_ARCHITECTURE.md`, `docs/V3_ROBUSTNESS_PLAN.md` | V2 / V3 (on branches `feature/safe-candidate-policy`, `feature/v3-robustness`, not on `main`) | - |

### 0.3 Commands

```bash
uv run pytest -q                                   # must stay green (~2 min); 2 live-LLM tests skip
uv run pytest -q src/buyer/facts                   # Felix's tests, not in the default run
uv run ruff check <changed files>                  # lint only what you touched; other files have old warnings
uv run python -m buyer.sim.train --iters 15 --pop 32 --episodes 80      # V0 parameter search (~12 min, 1 core)
uv run python -m buyer.sim.compare --episodes 100                        # V1 vs V2
uv run python -m buyer.sim.robust run --split development --episodes 2   # V3 harness (V3 branch only)
uv run python -m buyer.llm.accuracy                                      # reader precision / recall
```

Speed on this laptop (Ryzen, 16 threads, 14 GB): one simulated episode ~19 ms; training and evaluation
run on **one core**, so parallelising episodes across cores (`multiprocessing.Pool`) is a cheap 8-10x win.

### 0.4 The logged real sessions - format (verified)

`runs/practice_sessions/*.json` and `runs/sandbox_sessions/*.json`, one session per file:

```text
{session_id, case_id, set, saved_at, run, case, threads, result, end_reason, replay_url}
result = {ended, deal, supplier_id, offer_id, terms, c_open, c_deal, c_alt, c_best, score, must_haves_ok,
          cost_breakdown (null), trace}
trace  = [{round, actor, move, reasons}, ...]            # every move of both sides
move   = {offer_id, round, status, terms, alternatives, missing_fields, claims, claim_results, signals, text}
```

- `c_open`, `c_deal`, `c_alt`, `c_best`, `score` are **the arena's own numbers** - ground truth.
  Already checked: our `alternative_cost(case)` equals `c_alt` in 195 of 195 sessions.
- `reasons` (2,088 of 4,715 supplier moves have them) are the supplier engine's own explanation, **with
  the numbers blanked as "…"**, e.g. `"Alternatively, with Zahlungsziel … days net: €… per unit."`,
  `"Any further step needs approval from our management."`, `"Our management has approved a further
  step."`, `"Faster payment is welcome; we can reflect it in the price."`, `"With overtime we can deliver
  in … days, at a premium."`, `"We have free capacity for your parts."`
- **The numbers are in `move.alternatives`** (structured: `[{offer_id: "offer:70710-1-a", terms: {...}}]`,
  next to the standing `move.terms`) and in `move.text` (the e-mail). Read figures from `alternatives` /
  `terms`, never by parsing the reasons.
- Reasons and traces exist only **after** a session ends (practice / sandbox). In the final the agent
  never sees them - they are training and evaluation data only.

### 0.5 Gotchas we already paid for (do not rediscover them)

- **Windows + PowerShell:** commit messages with double quotes break `git commit -m`; write the message
  to a file and use `git commit -F <file>`. "LF will be replaced by CRLF" warnings are harmless.
- **Test isolation:** tests that set environment variables must use `monkeypatch` so they are undone
  (`ARENA_DATA` leaked once and silently emptied the data layer for later tests).
- **RFQ nondeterminism:** in an RFQ each thread undercuts the other's *current* offer, so two runs of the
  same policy can differ with thread timing. Compare per supplier, or use single-supplier cases.
- **Timing tests:** keep generous margins; the full suite runs ~2 min and loads the machine.
- `sim.env.load_cases()` reads `runs/cases`; the V2 / V3 "familiar case" logic derives from it.
- The simulator's supplier is our own model. **A gain in the simulator is only real if the simulator is
  right** - hence the order of the backlog.

---

## 1. Principles

1. **Only what we can measure offline runs overnight.** The scoreboard is the simulator plus the logged
   real sessions. E-mail wording, claim choice and tone are invisible to it - they wait for morning
   practice A/B runs. Spending credits on them overnight buys unmeasured changes.
2. **Compute is free, tokens are not.** Parameter search, training, calibration and evaluation are plain
   Python on the laptop. Claude writes code for a *new idea*; the optimiser tries values.
3. **Every change pays rent** (section 3.3). A final pruning pass removes any kept component whose
   removal does not lower the score.
4. **The submission is never at risk.** All work on the branch `overnight/<date>`; never push to `main`,
   never move the `v1-working` tag, never run `buyer practice` / `buyer final` (practice quota is the
   team's), never set `BUYER_LOCKED_EVAL=1` except in the single end-of-night evaluation.
5. **Fix the simulator before trusting it.** Gains on a mis-specified simulator are fake: the first
   experiments improve its fidelity, only then does optimising against it make sense.
6. **Stay in your lane where you can.** Changes to another role's module are allowed on the overnight
   branch (the team reviews in the morning), but keep them minimal, tested, and explained in the commit.

## 2. What we measured before writing this plan

| Finding | Evidence | Consequence |
|---|---|---|
| The simulator ignored the relationship cost - **fixed by Felix** | Until `edb820b`, `policy.py` and `sim/env.py` called `total_cost` without `supplier=`; 9 of 24 training cases are `stabilise` / `secure_supply`. For those, V0 scored **0.42** in the simulator but **0.61** scored the arena's way. Felix's `71b59f1` + `c3400e1` make the simulator score with the supplier's true economics and the policy cost with the Scout's estimate (`facts/costing.py`) | E1 is now *verify, don't rebuild*. Every parameter in `params.json` was tuned on the old, blind simulator: retraining (E4) is the first real gain |
| Zero scores are concentrated | ~6 % of simulated episodes score 0, ~10 % in the relationship cases | p10 is dominated by no-deals and walk-aways: the cheapest p10 gains |
| Our costing matches the arena on the alternative | 195 / 195 sessions, `alternative_cost == result.c_alt` | Costing is trustworthy there; `c_open` / `c_deal` not yet audited (needs standard terms) |
| The supplier engine explains itself | 2,088 supplier moves with `reasons`; structured `alternatives` with full terms | Free calibration data and free labels for the reader (ideas A1-A4) |
| Suppliers often stop conceding ("holders") | Thomas's practice analysis 24 Oct: 50-70 % hold after 1-3 steps; modelled in `sim/population.py` (`hold_share`, `hold_after`, `decay`) | Pushing a holder wastes rounds and risks a walk-away (idea B1) |
| V2 with the prior ranker = V1 | `buyer.sim.compare`, 24 cases | V2 adds nothing until the ranker is trained |
| Speed | 19 ms per episode on one core; default training ~12 min; a scoreboard ~1.5 min | ~10 experiments fit easily into one night, more with multiprocessing |

## 3. How the loop works

### 3.1 The scoreboard (experiment E0 builds it; frozen afterwards)

`uv run python -m buyer.sim.scoreboard --params <file> [--seed-set dev-A|dev-B]` prints one JSON line
and writes it to `runs/overnight/scoreboard-<git sha>.json`:

```text
{"J": 0.6421, "mean": ..., "p10": ..., "zeros": ..., "by_goal": {...}, "by_type": {...},
 "sim_real_gap": ..., "tests": "green", "decide_ms_p95": ..., "seed_set": "dev-A", "n": 4800}
```

- **J** = mean score over fixed paired episodes (all 24 cases x 100 draws, fixed seeds), scored with the
  corrected cost (relationship term included, the synthetic supplier's true parameters) - i.e. as the
  arena scores, as far as the simulator can tell.
- **Guards** (all must hold, whatever J says): p10 not lower, zero rate not higher, `sim_real_gap` not
  wider (idea A4, once built), `uv run pytest` green, decision time p95 under 50 ms.
- **Seed sets:** dev-A decides, dev-B confirms. Episodes for the same (case, seed) must be identical
  between old and new so the comparison is paired.
- Runs episodes in parallel across cores (`multiprocessing.Pool`, deterministic per (case, seed)).
- After E0 is merged, `sim/scoreboard.py` and the seed sets are **frozen**: no later experiment may edit
  them. A scoreboard bug found later is logged and left for the morning.

### 3.2 One iteration (one fresh Claude session)

```text
1. git switch overnight/<date> && git pull --ff-only (if the branch is pushed) ; read BACKLOG.md, last 10 rows of LOG.md
2. take the top idea whose status is "open" ; set it to "in progress" in BACKLOG.md
3. git switch -c exp/<id>-<slug>
4. implement the smallest version that tests the idea, with a unit test
5. if the idea has parameters: tune them with the optimiser (CPU), not by hand
6. scoreboard on dev-A for the current overnight head (cached by sha) and for exp/<id>
7. decide (3.3): keep -> confirm on dev-B -> merge into overnight/<date> (no fast-forward: one merge commit per idea)
                 reject -> delete exp/<id>
8. append one row to LOG.md ; set the idea to "kept" / "reverted" ; add follow-up ideas at the bottom of BACKLOG.md
9. stop
```

State lives in files, not in a conversation, so the cost per iteration stays flat all night.

### 3.3 When a change counts as better

- Paired difference per episode (same case and seed, old vs new): mean and standard error.
- Keep only if `mean_diff > 2 x SE` **and** `mean_diff >= 0.005` on dev-A, and `mean_diff > 0` on dev-B,
  and every guard holds.
- **Complexity tax:** a change that adds a component (new module, candidate family, model, state) must
  clear `mean_diff >= 0.01`. A bug fix, a simulator-fidelity fix or a pure parameter change only needs to
  beat the noise.
- **Simulator-fidelity experiments are judged differently** (E1-E3, A1-A4): they change the yardstick
  itself, so J before / after is not comparable. They are kept when their own fidelity metric improves
  (named per idea) and tests stay green; after them, re-measure the baseline J and say so in LOG.md.

### 3.4 Budget and stop rules

| Limit | Value |
|---|---|
| Experiments per night | 12 |
| Claude turns per experiment | 40 (hitting the cap = revert) |
| Wall time per experiment | 45 min |
| Stop early | 3 reverted experiments in a row, or no open idea with an expected gain above the threshold |
| Stop hard | 06:30 (morning check before the 08:00 data release) |
| End of night | pruning pass (5.4), then one V3 locked evaluation if the V3 branch is merged into the overnight branch, then the handoff (section 6) |

Write `STOP: <reason>` as the last line of LOG.md to stop the runner.

## 4. Mechanics in Claude Code

### 4.1 Runner (`scripts/overnight.sh`, Git Bash)

```bash
for i in $(seq 1 12); do
  [ "$(date +%H%M)" -ge 0630 ] && [ "$(date +%H%M)" -lt 1200 ] && break
  claude -p "$(cat docs/overnight/ITERATION.md)" --max-turns 40 --permission-mode acceptEdits \
    >> runs/overnight/session-$i.log 2>&1
  tail -1 docs/overnight/LOG.md | grep -q '^STOP' && break
done
```

One headless session per iteration. (Alternative: `/loop` in one interactive session - simpler to start,
but the context grows all night: more tokens per step and more drift.)

### 4.2 The instruction (`docs/overnight/ITERATION.md`)

"You are the overnight Claude. Read `docs/OVERNIGHT_PLAN.md` (all of it), `AGENTS.md`, `BACKLOG.md` and
the last 10 rows of `LOG.md`. Run exactly one iteration of section 3.2. Obey sections 1, 3.3, 3.4 and
4.3. Finish by appending one row to `LOG.md`. If nothing is left to do, append `STOP: <reason>`."

### 4.3 Hooks and permissions (`.claude/settings.json`, committed)

- **Stop hook:** `uv run pytest -q && uv run pytest -q src/buyer/facts` + `ruff check` on changed files.
  Red -> the session cannot end; fix or revert.
- **PreToolUse hook (Bash):** blocks `git push` to anything but `overnight/*`; `git switch main`,
  `git reset` on `main`, tag edits; `buyer practice`, `buyer final`, `buyer sandbox`; `BUYER_LOCKED_EVAL=1`
  outside the end-of-night step; edits to `src/buyer/sim/scoreboard.py` and the seed sets after E0.
- **Environment:** `LLM_DISABLED=1` for everything in the loop - the simulator does not read prose and
  evaluation must not call an LLM.

### 4.4 LOG.md row format

```text
| # | time | idea | branch | J dev-A old -> new | diff +- SE | p10 | zeros | dev-B diff | verdict | why (one line) |
```

---

## 5. The backlog (ranked; take them in this order)

For each idea: **what** to change, **where**, **how it is measured**, **when to kill it**. Tier 0 always
first. Sizes: S < 1 h, M 1-2 h, L > 2 h (of the night).

### Tier 0 - foundations (in this order; mostly plain code)

**E0 - Scoreboard + noise estimate.** (S-M)
- What: `src/buyer/sim/scoreboard.py` as in 3.1; two seed sets in `src/buyer/sim/seeds.json`; parallel
  episodes; paired output (per-episode scores saved so two runs can be diffed); a `--diff old.json new.json`
  mode that prints `mean_diff`, `SE`, and the guard checks.
- Measure: the same params twice -> identical J; a known-worse params file (e.g. `concede` x 2) -> lower J.
- Use `sim.env`'s scoring (relationship-aware since Felix's `71b59f1`) - do not re-implement it.

**E1 - Relationship cost in scoring and costing - DONE by Felix (`71b59f1`, `c3400e1`): verify only.** (S)
- Already on `main`: `sim/env.py` scores `c_open`, `c_deal`, `c_best` with the synthetic supplier's true
  `full_cost` / `cash_rate` / standard terms; the policy costs with the Scout's estimate via
  `facts/costing.py` (the never-ask-more check and sheet C are relationship-aware).
- Verify, do not rebuild: (1) `Policy.cost`, `acceptable` and `closing` - do they all include the charge,
  or only some paths? (2) Does `sim/train.py` use the same scoring (it calls `env.episode`, so it should)?
  (3) The V2 shield (`facts/shield.py`, V2/V3 branches) duplicates part of this - note it for the team,
  do not merge branches tonight. Log the findings; fix only a clear gap, with a test.

**E2 - Calibrate the population on the logged real sessions.** (M) *(fidelity)*
- Thomas already fitted the holder share by hand. Use `sim/calibrate.py` / `sim/metrics.py`
  (`replay_error`, `transfer_error`) on all 375 sessions to fit the remaining ranges in `ranges.json`.
- Measure: replay error must drop on a held-out 25 % of the sessions; kill if it does not.

**A1 - The supplier's own exchange rates from its alternatives.** (M) *(fidelity, feeds E2 and the profiles)*
- Data: every supplier move with `move.alternatives` gives pairs (standing `terms`, alternative `terms`)
  that differ in one or two levers (payment days, index clause, lead time, contract months).
- Compute per supplier and per lever: price change per payment day (-> the supplier's implied cash rate:
  `rate ~ (dP / P) * 360 / dDays`), price per week of lead time, price of an index clause.
- Use: write the per-supplier rates into a data file the Scout's profile can read
  (`cash_rate_estimate` instead of the guessed 0.08) and the population ranges (`cash_rate`,
  `lead_premium_pct_week`). Do not edit `memory.json` by hand - add a new file and a reader, Felix decides.
- Measure: replay error / the simulator's predicted alternatives vs the logged ones.

**E3 - Realistic round budget.** (S) *(fidelity)*
- From `runs/practice/**.jsonl` and the session files: how many rounds per thread are actually played
  before the wave cap / an end? The simulator assumes `round_limit` (10). Sample the episode's round
  budget from the logged distribution.
- Measure: rounds-to-close distribution, simulator vs logs (e.g. KS distance).

**A4 - Simulator-vs-reality gap as a guard.** (S)
- For each hosted case: the simulator's mean score for V0 (with the params that played) vs the logged
  real `result.score`. One number: mean absolute gap. Add it to the scoreboard as `sim_real_gap`.
- This becomes a guard: no later change may widen it.

**E4 - Retrain V0's parameters on the corrected simulator.** (S, CPU) - the first real J gain.
- `sim/train.py` with the scoreboard's objective; save to a new params file, compare with the ratchet;
  only then write `params.json`.

### Tier 1 - strategy (measurable once Tier 0 is in)

**B3 - Optimise for the weak cases, not only the mean.** (S)
- Change the trainer's objective to `mean + 0.5 * p10` (or `mean - zero_rate`) and retrain. One-line
  idea, directly targets zero scores. Keep if J holds and p10 / zeros improve.

**B1 - Detect holders and stop pushing them.** (M)
- When a supplier has not moved its price for 2 rounds (or `status == final_offer`), stop conceding
  price: either change lever (B5 / packages) or close (accept if acceptable). Saves rounds and avoids
  walk-aways. The simulator already models holders, so this is measurable now.
- Kill if J or zeros do not improve.

**E5 - Zero-score autopsy -> fix the top cause only.** (M)
- Classify every zero episode on dev-A: walked away after our push / no deal before the round limit /
  nothing better than the alternative / must-have impossible. Report the shares in LOG.md and fix only the
  biggest *policy-caused* class.

**B2 - Approval-aware pacing.** (S-M)
- When the supplier's last message says management approval is pending (reader signal
  `approval_pending`, or in the simulator the approval step), do not concede again: repeat our standing
  terms (a hold) until it answers. Do not bid against ourselves. Needs the simulator's approval model to
  be right (E2 / A2) - check before building.

**A3 - Use the supplier's alternative offers.** (S)
- Its messages can carry several term sheets (`alternatives` with their own `offer_id`). Cost every one
  (with standard terms); accept / counter on the cheapest for us, not only the first. Check first whether
  Thomas's `t.offers` already does this (`policy.py`, `ThreadState.offers`) - if yes, add a test and
  move on.

**B5 - Negotiate the effective date in price-increase cases.** (M)
- Units bought before `effective_date` cost the old price (see the cost formula in `brief/api.md`). Add
  sheets that trade a later date for price; let `best_options` / the costing show the value.
- Measure: J on `price_increase` cases; complexity tax applies.

**E6 - Lever packages: cheap for us, valuable to the supplier.** (M)
- 2-3 sheets of equal buyer cost that differ in one lever, priced with the kit's `supplier_value` and the
  exchange rates from A1. Measure on cases with >= 3 negotiable fields; complexity tax applies.

**E7 - A three-state belief from which sheet the supplier built on.** (M)
- States: cash-sensitive / security-sensitive / price-only. Update from which of our sheets its counter
  follows (and from A1's rates); next round's sheet mix follows the belief. Measure belief accuracy where
  the simulator knows the truth (kill if < 60 %) and J.

**E8 - RFQ play.** (S-M) Undercut size, when to cite the rival, accept timing between two live bidders;
tune with the optimiser on the RFQ cases.

**B4 - Per-case-type parameters with shrinkage.** (M) Separate parameter sets for rfq / price_increase /
capacity+quality, penalised towards the global set. Keep only if dev-B confirms (24 cases overfit easily).

**E9 - Train the V2 ranker** (only if the V2/V3 branch is merged into the overnight branch). Train
`ranker.json` on simulator episodes; compare with `sim.compare` + the V3 harness. If it does not clear
the complexity tax, V2 stays off - a valid result.

### Tier 1b - the Diplomat's offline ideas (no scoreboard effect; judged by their own metric)

**A2 - A reader benchmark on real e-mails, labelled from the reasons.** (M)
- Map reasons to `Signals` labels: "needs approval" -> `approval_pending`; "Faster payment is welcome" ->
  `asks: faster_payment` and cash; "free capacity" -> `capacity_issue = False` + `asks: volume`;
  "we must maintain a … lead time" / "overtime" -> capacity; "approved a further step" -> not pending.
  The labelled text is `move.text`. Build `src/buyer/llm/tests/fixtures/recorded_labelled.json` (a sample
  of ~200, half for tuning, half held out) and extend `buyer.llm.accuracy` with `--recorded`.
- Measure the keyword rules on it (free). The LLM reader only on a sample of <= 100 messages and only if
  the team left a key in `.env` for this - otherwise skip the LLM part (`LLM_DISABLED=1`).
- Improve the rules on the tuning half only; report the held-out half. Never weaken an existing test.

### Tier 2 - not overnight

| Idea | Why not tonight |
|---|---|
| Writer prompt / tone, LLM vs template | The simulator ignores prose. Morning practice A/B (section 6) |
| Claim choice and ordering | The simulator does not model claims. Morning A/B + log analysis |
| V4 planner, calibrated response model | Needs the calibrated simulator first and much more data |
| Experience retrieval (V4) | High complexity for little data |
| LLM-proposed adversarial mutations (V3) | Costs credits; the programmatic catalogue already finds real failures |

### 5.4 End-of-night pruning pass

For every kept component (not parameter changes): remove it, re-run the scoreboard. If J does not drop
by more than the noise, remove it for good and log "pruned". Simplest version that keeps the score wins.

## 6. Morning handoff (07:00)

The team finds:

1. `docs/overnight/LOG.md` - one row per experiment with the numbers and the verdict.
2. Branch `overnight/<date>` (pushed) with only kept commits, each with its numbers in the message.
3. `runs/overnight/scoreboard-*.json` - final J vs the start of the night, by goal and case type.
4. A summary at the top of LOG.md: what to merge before the 11:00 freeze, in which order, and the
   practice validation to run first (e.g. 20 sessions on the hosted cases, old vs new params - about
   10 % of the daily quota).
5. Questions only practice can answer, ready to run: writer LLM vs template; claims on vs off; how often
   the wave cap cut a negotiation (latency).

The team decides; the loop never merges to `main`.

## 7. Risks and how the plan handles them

| Risk | Handling |
|---|---|
| Overfitting the simulator | Tier 0 first; dev-B confirmation; `sim_real_gap` guard; practice A/B before merging |
| Credits burned on dead ends | Fresh sessions, turn caps, 3-reverts stop, optimiser for values, `LLM_DISABLED=1` |
| Breaking the submission | Branch only; hooks block `main`, the tag, practice and final; tests green before a session ends |
| Gaming the scoreboard by accident | Scoreboard and seeds frozen after E0, write-protected by the hook |
| Noise mistaken for gains | Paired seeds, 2 x SE, a second seed set |
| Editing another role's module badly | Minimal changes, tests, clear commit messages; the owner reviews in the morning |
| The laptop sleeps or reboots | Plugged in, sleep off, Windows Update paused; the runner can be restarted, state is in files |

## 8. Before the first night (human, ~30 min)

| Piece | Who |
|---|---|
| Agree on thresholds (3.3, 3.4) and the backlog order; Thomas OK for E1 / E4 touching `policy.py` and `sim/` | team, 10 min |
| `scripts/overnight.sh`, `docs/overnight/ITERATION.md`, empty `BACKLOG.md` (copy of section 5's list with status "open") and `LOG.md` | anyone |
| `.claude/settings.json` hooks and permissions (4.3) | anyone |
| Create and push the branch `overnight/<date>` from `main` | anyone |
| Laptop: plugged in, sleep off, updates paused, `uv sync` done, `claude` logged in | the laptop owner |

E0 (the scoreboard) is the overnight loop's first experiment; everything after it is produced by the loop.
