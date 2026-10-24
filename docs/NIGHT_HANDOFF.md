# Night handoff - Sat 24 / Sun 25 Oct (from Hichem)

**For:** the teammate who sets up and watches the night, and the Claude session(s) that work through it.
**Mandate (Hichem):** full confidence to maximise our Live Final score. The overnight Claude may use the
Tacto arena (practice and sandbox runs) to get real data and validate changes, **but must leave at
least 50 practice runs untouched** for Sunday. Everything below is the plan; nothing in it has been run.

Read together with [`OVERNIGHT_PLAN.md`](OVERNIGHT_PLAN.md) (the keep-or-revert loop, the backlog, the
log format) and [`AGENTS.md`](../AGENTS.md). **Where this file and OVERNIGHT_PLAN.md disagree, this file
wins** - it is newer and adds arena access and the EHL merge.

---

## 1. Context that is not in the repo

### 1.1 Rules of the final (from https://arena.tacto.ai/faq#final, read 25 Oct 00:30)

| Rule | What it means for us |
|---|---|
| Code freeze **13:00**: submit repo + commit hash on the organisers' platform | Everything merged and tagged by ~12:30 |
| Start the runner **before 13:30**, leave it until wave 5 closes; 5 themed waves x 8 min, **one attempt per case**, all teams at once | `uv run buyer final` on the final machine, logs to a file, laptop on power, no sleep |
| Open at the 8-min cap or never opened = no deal | Closing before the cap is worth more than one more round |
| Score per case `(C_open - C_deal)/(C_open - C_best)` clipped 0..1; **no deal = the alternative's score (0 if none); broken must-have = 0; a deal worse than the opening = 0** | Never accept above `C_open`; never let a case time out when there is no alternative |
| Wave score = mean x 100; points = sum of the 5 waves (max 500); every case weighs the same | Weak case types cost as much as strong ones gain: fix P02 / P18-type losses first |
| **Ties: more deals, then fewer rounds** | A safe deal beats a no-deal; don't waste rounds |
| Practice does not rank; the board shows the best score per hosted case | Practice is for learning and validation only |
| Practice quota: 200 per rolling 24 h; sandbox D01 / D02 outside the quota; 10 open sessions per key | Section 3 |
| During the final the agent must not read the leaderboard, screen or event feed; no hand-picked cases or hand-written messages; restarting a crashed runner is fine | `SafeClient` already blocks those endpoints |
| Sunday 08:00 data release (`uv run arena data` after 08:00); morning pre-flight: one practice case on the final machine, then start the final runner for a minute (403 = keep waiting) | Section 5 |
| **Places 1-3 are set by the jury from the final score AND the pitch** (top 5 pitch at 15:10, 5 min + 2 min questions; "What did your agent learn about suppliers, and from where?") | Whatever we copy, we must understand and credit (section 4) |
| The top 5 are checked for pushes after the freeze | No commits to the submitted branch after 13:00 |
| Clocks go back tonight: 03:00 becomes 02:00 | One extra hour; every Sunday time is the new time |
| Reusing code: the FAQ and brief say nothing against it ("everything else counts"; banned: attacks on the service or other teams, sharing keys) | Allowed, but respect the other repo's licence and credit it |

### 1.2 Where we stand (measured 25 Oct ~00:30)

- **Real practice scores** on the 10 hosted cases (latest batch, 23:46, Thomas): mean ~0.66.
  Strong and stable: P01 ~0.93, P03 0.90, P04 0.81, P05 0.82. **Weak and stable: P02 0.16-0.24,
  P18 0.23-0.36.** Unstable: P11 (0.00-0.57), P08 (0.45-0.68), P10 (0.00-0.65).
- **Practice is close to deterministic per case** (P03 scored 0.90 in four batches, P04 0.81 in four):
  one or two runs per case already tell a lot - practice runs are high-value evidence, not noise.
- **Practice quota:** 45 practice sessions are logged in `runs/practice_sessions/` since 20:44 yesterday;
  with a rolling 24 h window none of them frees up before the final. Expect ~155 left; **check with
  `uv run buyer quota` before spending any.**
- **Simulator:** relationship-aware since Felix's `71b59f1` / `c3400e1` (it was blind to it before: 0.42
  vs 0.61 on the 9 stabilise / secure_supply cases). Holder suppliers calibrated by hand by Thomas.
  `params.json` was tuned on the old, blind simulator - retraining is the first real gain.
- **Latest policy work on `main`:** Felix's lever trades (offer the term a holding supplier asks for, at
  equal cost to us) and index-clause variants (`2820fc9`); Thomas's eligibility and reciprocity rules.
- **Branches not on `main`:** `feature/safe-candidate-policy` (V2: safe candidate ranking behind
  `BUYER_POLICY`, ranker untrained = plays like V1) and `feature/v3-robustness` (V3: adversarial
  harness, 17 mutations, reader benchmark; contains V2). Not needed tonight; their harness is useful as a
  safety check if someone merges them.
- **Tag `v1-working` = `7562be9`**: the first version that ran live. Rollback point of last resort.
- **Repo:** `https://github.com/thomasturek/Team-Holdout` (the old `alex-thomas` URL redirects).

### 1.3 Decisions already taken (do not change without the owner)

- Shared dataclasses live in `src/buyer/interfaces.py`.
- LLM time limits: writer 20 s per attempt, 1 retry, 25 s total; reader 10 s. Move budget 23 s.
- The writer uses placeholders that code fills in; the LLM never produces a number that reaches a term
  sheet; only unknown data IDs are stripped from e-mails.
- The LLM reader runs in the background beside the writer (`BUYER_READER=parallel`, default); the policy
  decides on the keyword rules' signals. `BUYER_READER=blocking` restores the old order.
- Default policy `BUYER_POLICY=v1` (V2 / V3 only on their branches).

### 1.4 Things a teammate told Hichem (unverified in the repo)

- With real LLM keys a move took ~20 s on average in one run and ~35 s in another (unclear whether per
  move or per session; 35 s per move would break the 25 s budget - check `decide_s` in the logs).
- Hichem's `.env` once had a placeholder `LLM_WRITER_MODEL=PASTE-SONNET-MODEL-ID`: with it every writer
  call fails and falls back to the template. Check every machine's `.env` (the kit example now uses
  `claude-sonnet-5-5`). Thomas raised the reader / writer `MAX_TOKENS` to 10000 (probably because the
  effort setting's thinking tokens truncated answers) - confirm with `uv run python -m buyer.llm.bench`.
- **The same challenge ran at an earlier Tacto hackathon ("EHL", the week before last).** The team wants
  to take the winner's approach and merge it with ours (section 4).

### 1.5 The laptop

Hichem's laptop (Ryzen, 16 threads, 14 GB): one simulated episode ~19 ms on one core, a default
training run ~12 min, a scoreboard ~1.5 min. Training is single-core - parallelising is a cheap 8-10x.
Plugged in, sleep off, Windows Update paused, stable Wi-Fi.

---

## 2. Night schedule (new time after 03:00 -> 02:00)

| When | Who | What |
|---|---|---|
| 00:45-01:15 | teammate | Setup (section 6): branch, runner, hooks, `uv run buyer quota`, EHL material into `docs/ehl/` |
| 01:15 | overnight Claude | E0 scoreboard (OVERNIGHT_PLAN 5) |
| ~01:45 | overnight Claude | **EHL study** (section 4, step 1-2): one session reads the winner's code / write-up, writes `docs/ehl/ANALYSIS.md` and adds its ideas to `BACKLOG.md` |
| ~02:15 -> 05:30 | overnight Claude | Tier 0 (verify E1, calibration, exchange rates, round budget, sim-vs-real guard, retrain), then the ranked backlog with EHL ideas merged in (section 4.3); practice runs only as in section 3 |
| 05:30-06:15 | overnight Claude | Pruning pass; **validation batch** on the hosted cases (section 3, budget line C) |
| 06:15-06:30 | overnight Claude | Handoff: summary on top of `LOG.md`, branch pushed, recommendation. `STOP` |
| 07:00 | team | Review, decide what to merge |
| 08:00 | team | Data release: `uv run arena data`; Felix checks claims / profiles on the new data |
| 08:30-11:00 | team | Merge, one confirmation batch (budget line D), policy freeze 11:00 |
| 11:00-12:30 | team | Pre-flight on the final machine, README, tag, submission text |
| 13:00 | | Code freeze, submit hash |
| before 13:30 | | `uv run buyer final` running, logging to a file |

## 3. Practice and sandbox budget

**Hard floor: 50 practice runs left at all times.** The runner enforces it: always pass
`--reserve 50` (`uv run buyer practice ... --reserve 50`); it refuses to start a run that would go below
and stops starting sessions when the arena reports the reserve reached. Check `uv run buyer quota` before
and after every practice run and log the number in `LOG.md`.

Assuming ~155 left at 01:00 (re-plan if `buyer quota` says otherwise):

| Line | Use | Runs |
|---|---|---|
| A | **No new baseline needed**: Thomas's batch at 23:46 is the baseline for the current `main` (same code apart from `2820fc9` - if that matters, re-run only P08 and P11, the clause cases: 2) | 0-2 |
| B | **Targeted experiments on the weak cases** P02, P18, P11, P08 (and P10): an idea that wins in the simulator is tried on these 4-5 cases, 1 run each (practice is near-deterministic per case); max ~8 ideas | <= 40 |
| C | **Overnight validation**: the night's final candidate on all 10 hosted cases, twice | 20 |
| D | **Morning confirmation** after the 08:00 release and the team's merge: all 10 hosted cases once | 10 |
| E | **Pre-flight** on the final machine (the FAQ asks for one practice case) | 1-2 |
| | Spare (unplanned) | ~30 |
| | **Reserve, never touched** | **50** |

Rules for practice runs:
- A practice run is the *last* step of an experiment, never the first: only ideas that already won on the
  simulator scoreboard (OVERNIGHT_PLAN 3.3) earn real runs.
- An idea is kept for the weak cases only if it does not lose on any of the 10 hosted cases in line C
  (practice is near-deterministic: a drop of more than 0.03 on a case is a real loss).
- **Sandbox (D01, D02) is free** - use it for anything exploratory against the real supplier engine
  (`uv run buyer sandbox --repeat N`, or the harvester with explore parameter sets). Run with
  `LLM_DISABLED=1` unless the experiment is about prose, to save LLM credits.
- Never `buyer final`. Never set `BUYER_LOCKED_EVAL=1` except in the one end-of-night V3 evaluation (only
  if the V3 branch was merged into the overnight branch).
- Every run is logged automatically (`runs/<set>/...`, `runs/<set>_sessions/...`): commit the new
  session files on the overnight branch so the Analyst can calibrate on them.

## 4. Merging the EHL winner's approach

We do not have the winner's material in the repo yet. **Before the night starts, the teammate puts what
we have into `docs/ehl/`**: repo link or code (as a git submodule or a copy under `docs/ehl/src/`, not
inside `src/buyer/`), their README / write-up / slides, their replays or scores if public, and the
licence. Without that material the overnight Claude skips this section and says so in `LOG.md`.

### 4.1 Rules

- **Licence first.** If their code has a licence (MIT etc.), copying is fine with credit; record it in
  `docs/ehl/ANALYSIS.md` and in our README ("parts adapted from <team>, EHL hackathon, <link>, <licence>").
  No licence = all rights reserved: take ideas, not code, and still credit the inspiration.
- **The same challenge is not the same arena.** Their case set, supplier settings, data package and API
  version may differ from ours (we have holders, relationship charges, lever trades, Sunday data). Treat
  every one of their ideas as a hypothesis to test, not a result.
- **Ideas, not a replacement.** Their code does not replace our runtime (per-thread concurrency, 25 s
  budget, logging, crash resume, forbidden endpoints) or our safety rules (AGENTS.md section 7). We port
  their *decision logic* into our policy, one idea at a time, through the same ratchet.
- **The pitch.** The jury asks what our agent learned and why it wrote what it wrote. Every adopted idea
  needs a one-line "why it works" in `ANALYSIS.md` that a teammate can say out loud.

### 4.2 Step by step

1. **Study (one Claude session, ~30 min, no code changes):** read their code and write-up; write
   `docs/ehl/ANALYSIS.md` with: their architecture in 10 lines; their opening / concession / closing
   rules; which levers they trade; how they use the data package and claims; their RFQ play; anything
   about supplier quirks they exploited; their final score and per-case-type strengths if known; the
   licence.
2. **Diff against ours:** a table "their idea | do we already do it? (file / function) | expected gain |
   size | risk". Ideas we already have are dropped; overlapping ideas become a parameter or variant of
   ours, not a second mechanism.
3. **Backlog:** each new idea becomes an `EHL-n` entry in `BACKLOG.md`, ranked into OVERNIGHT_PLAN's
   backlog by expected gain per effort. Ideas that are measurable in the simulator go through the normal
   ratchet; ideas about prose or claims (unmeasurable offline) go to the morning practice A/B list.
4. **Port one at a time** behind a parameter or flag in `policy.py` (e.g. `params["ehl_close_rule"]`), so
   the ratchet can compare on / off on the same seeds, and the optimiser can tune it.
5. **Real check:** a kept EHL idea gets practice runs on the weak cases (budget line B) like any other.
6. **If their whole policy looks clearly better on paper,** do not swap it in at night. Port it as a
   separate policy class (`policy/ehl.py`, `new_agent("ehl")`) and run it once on the 10 hosted cases
   (10 runs from line B) next to ours; the team decides in the morning.

## 5. Morning (team)

1. 07:00 - read the summary on top of `docs/overnight/LOG.md`; check `uv run buyer quota` (>= 50 + D + E).
2. 08:00 - `uv run arena data`; Felix re-runs profiles / claims checks on the release; run the test suite.
3. Merge the recommended overnight commits into `main` (owners review their modules: Thomas policy / sim,
   Felix facts, Alex runtime, Hichem llm).
4. Budget line D: one full hosted run of the merged `main`. Compare per case with the 23:46 baseline and
   the night's line C. If anything is worse than the baseline on a case by more than 0.03, revert that
   change or fall back to the last good commit.
5. 11:00 policy freeze; tag the commit (`final-candidate`); README: run command, env variables (no
   values), and credit for the EHL ideas; the submission description (approach, data, offers, closing).
6. Pre-flight on the final machine (line E), `uv run arena me`, LLM credits for ~1 h of parallel play.
7. 13:00 submit the hash; before 13:30 start `uv run buyer final` with logging; hands off.

## 6. Setup checklist (before starting the loop)

The setup session of Claude Code works through this list itself - see `OVERNIGHT_PLAN.md`, "START
HERE": it runs every step, builds anything missing, and asks the teammate only for keys, the EHL link and
laptop settings.


- [ ] `git pull` on `main`; `uv sync`; `uv run pytest -q` and `uv run pytest -q src/buyer/facts` green.
- [ ] `.env` has `ARENA_API_KEY` and a working LLM key + real model names (not the placeholder);
      `uv run arena me` answers; `uv run buyer quota` -> write the number at the top of `LOG.md`.
- [ ] EHL material in `docs/ehl/` (section 4), with its licence.
- [ ] Branch `overnight/2026-10-25` from `main`, pushed.
- [ ] `docs/overnight/ITERATION.md`, `BACKLOG.md` (OVERNIGHT_PLAN section 5 + EHL placeholder), `LOG.md`.
- [ ] `scripts/overnight.sh` (OVERNIGHT_PLAN 4.1) - 12 iterations, stop at 06:30 new time.
- [ ] `.claude/settings.local.json` hooks (OVERNIGHT_PLAN 4.3, local to the night laptop) **with these changes for tonight**:
      allow `buyer practice` only with `--reserve 50` (block it otherwise); allow `buyer sandbox`;
      still block `buyer final`, pushes to `main`, tag edits, edits to the frozen scoreboard and seeds.
- [ ] `LLM_DISABLED=1` in the loop's environment by default; experiments about prose (none planned
      tonight) would need it off and cost credits.
- [ ] Laptop: power, sleep off, updates paused, `claude` logged in.
- [ ] Post the branch name and the quota number in the team chat; set an alarm for 07:00.

## 7. What "done" looks like at 06:30

- `overnight/2026-10-25` pushed, kept commits only, each with simulator and (if any) practice numbers.
- `docs/overnight/LOG.md`: one row per experiment; a summary on top with the recommended merge order.
- `docs/ehl/ANALYSIS.md` (if the material was there) with the adopted / rejected ideas and why.
- Quota at the end of the night written in `LOG.md`, **>= 50 + 12 (lines D + E)**.
- `main` untouched.
