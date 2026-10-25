# The Operator: runtime, runners and logs

This folder holds the part of the agent that talks to the arena. It opens sessions, runs every supplier thread at the same time, keeps every move inside the time limit, ends cases safely and logs everything. The owner of this folder is Alex.


## Step 1: Settings

`env.py` loads the settings. It reads `.env` at the root of the repository first and then `starter-kit/.env`, and real environment variables always win over both files. It also defines where logs are written. The default is the `runs/` folder, and the variable `BUYER_RUNS` can point it somewhere else.


## Step 2: Agents

`agent.py` defines the agents the runtime can play. Each is chosen by name. The `naive` agent is the starter kit's simple baseline. The `llm` agent is the starter kit's language model agent. The `policy` agent is ours, and it is the default. It combines the Scout's profiles, the Analyst's policy and the Diplomat's reader and writer.

One move of the policy agent has a budget of 23 seconds from the moment it is called. It reads the reply with fast keyword rules, lets the policy decide, and then lets the writer produce the e-mail. The language model reader runs in the background at the same time as the writer, so a move costs the writer's time rather than both.


## Step 3: Playing every thread at once

`threads.py` plays one case. Every supplier thread gets its own worker and its own clock, and all workers share one view of the case so that the policy can see every rival's offer.

Each move must leave within 25 seconds of the supplier's reply. If the decision is still missing after 40 seconds, the worker sends a short holding message that contains no numbers, so the thread does not time out. If the agent fails twice in a row, or the arena refuses its messages twice in a row, the worker stops playing that thread.

Ending a case is supervised until the arena confirms it. After any failed or unanswered attempt to accept or walk away, the runtime first asks the arena what state the case is in, and only then tries again with a fresh decision. It never sends two final actions without an answer in between.


## Step 4: Runners

`runner.py` provides the command line tool `buyer`. It has four commands.

```bash
uv run buyer quota
uv run buyer sandbox --repeat 3
uv run buyer practice --cases P01 P04 --repeat 2 --purpose my-change
uv run buyer final
```

The `quota` command prints how many practice sessions have been used and how many are left. The `sandbox` command plays the two free demo cases. The `practice` command plays hosted practice cases, keeps a reserve of 20 sessions and refuses to start a run that would use it up. The `final` command plays the live final. It polls for new waves, plays each wave's cases in parallel, closes every case before the wave's time runs out, and resumes its running sessions if it is restarted.

The commands that play accept `--agent` to choose an agent and `--parallel` to set how many sessions run at once. The runner never reads the arena's event feed, screen, leaderboard or results.


## Step 5: The harvester

`harvest.py` plays the sandbox cases without stopping, to collect free data for the simulator.

```bash
uv run python -m buyer.runtime.harvest --sessions 40
```

Each session uses the next parameter set from `src/buyer/policy/explore.json`. Every third session is a probe that behaves slightly differently on purpose, for example by pushing once past a final offer, so that we learn how suppliers react. The harvester also saves the sandbox and practice case files to `runs/cases/` for the simulator.


## Step 6: Logs

`log.py` writes one log file per session to `runs/<set>/<case>/<session>.jsonl`. Every line is one event with a timestamp, such as a message we sent, a supplier reply, a decision or the final result. A complete copy of every finished session is also saved to `runs/<set>_sessions/`. The full format is described in [docs/LOGS.md](../../../docs/LOGS.md).

Two commands help with the logs. The first prints one line per session, and the second adds the detailed traces that the arena only opens after the final is over.

```bash
uv run python -m buyer.runtime.log summary --set practice
uv run python -m buyer.runtime.log backfill --set final
```

The same logs feed the simulator's calibration and the Counterpart dashboard.


## Tests

The runtime's tests live in the top level `tests/` folder.

```bash
uv run pytest tests
```
