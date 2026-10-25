# Running the agent

This is the practical guide. It takes you from a fresh checkout to a running agent, explains the three places the agent can play, and ends with what to do when something goes wrong. Every command runs from the root of the repository.


## Step 1: Install the tools

The agent needs Python 3.12 and the [uv](https://docs.astral.sh/uv/) package manager. The Counterpart dashboard also needs Node.js, but you can skip that if you only want to run the agent.


## Step 2: Add your keys

Copy the example environment file and open it in an editor.

```bash
cp .env.example .env
```

Fill in `ARENA_API_KEY` with the team's arena key and `ANTHROPIC_API_KEY` with a key for the language model. The file `.env` is ignored by git and must never be committed.

The language model is optional. If you set `LLM_DISABLED=1`, or leave the model unset, the Diplomat falls back to its keyword reader and its template writer. The agent still negotiates, but its e-mails are plainer. This mode is useful for cheap sandbox runs.


## Step 3: Install the project

Install our package and Tacto's starter kit in one step.

```bash
uv sync
```

Then check that the key works. This command prints the team's details, the practice allowance and the best scores so far.

```bash
uv run arena me
```

Finally, run the tests to make sure everything is in order.

```bash
uv run pytest
```


## Step 4: Play the sandbox

The sandbox holds two demo cases, `case:D01` and `case:D02`. Sessions there are free and unlimited, so the sandbox is the right place for any experiment.

```bash
uv run buyer sandbox --repeat 3
```

This plays both sandbox cases three times. Each case runs with the full agent, every supplier thread in parallel.


## Step 5: Play practice cases

The practice set holds ten hosted cases. The team can play at most 200 practice sessions in any 24 hour window, so practice is for checking a change, not for experiments. Please agree with the team before you start a practice run.

First check how many sessions are left.

```bash
uv run buyer quota
```

Then play the cases you want. A case can be named by its short code.

```bash
uv run buyer practice --cases P01 P04 --repeat 2
```

You can also give the run a purpose label, which is stored in the logs and makes it easy to compare two versions later.

```bash
uv run buyer practice --purpose my-change
```

The runner keeps a reserve of 20 sessions. It refuses to start a run that would eat into that reserve, and it stops starting new sessions once the arena reports that the reserve has been reached.


## Step 6: Play the live final

The final runs on hidden cases in five waves of eight minutes. No human may take part while it runs, so the runner must be started before the final begins and then left alone.

```bash
uv run buyer final
```

The runner polls the case list every few seconds. When a wave opens, it plays all of that wave's cases in parallel and closes each one before the wave's time runs out. If the runner is restarted in the middle of a wave, it picks up its running sessions and continues.

After the whole final is over, the arena opens the detailed traces of each session. This command adds them to the logs.

```bash
uv run python -m buyer.runtime.log backfill --set final
```


## Step 7: Harvest data for tuning

The harvester plays the sandbox cases without stopping, several sessions at once. It is how we collect free data for the simulator and for tuning the policy.

```bash
uv run python -m buyer.runtime.harvest
uv run python -m buyer.runtime.harvest --sessions 40
uv run python -m buyer.runtime.harvest --hours 8
```

The first form runs until you press Control and C, the second stops after 40 sessions, and the third stops after eight hours. Each session uses one of the parameter sets listed in `src/buyer/policy/explore.json`, so different settings can be compared on the same cases.


## Step 8: Look at the results

Every session is logged in `runs/`. A file per session is written to `runs/<set>/<case>/<session>.jsonl`, and a complete copy of each finished session is saved in `runs/<set>_sessions/`. The runner's own log goes to `runs/runner-<mode>-<time>.log`.

To print one line per logged session, run the summary command.

```bash
uv run python -m buyer.runtime.log summary --set practice
```

To compare two practice batches by their purpose labels, use the comparison script.

```bash
uv run python scripts/compare_batches.py version-a version-b
```

The easiest way to look at results is the Counterpart dashboard. Start it as described in [frontend/README.md](../frontend/README.md) and open the Negotiations page.


## Step 9: When something goes wrong

If `uv run arena me` fails, the arena key in `.env` is missing or wrong.

If the agent's e-mails look like templates, the language model is not being used. Check that `ANTHROPIC_API_KEY` and `LLM_MODEL` are set and that `LLM_DISABLED` is not set.

If a practice run refuses to start, the practice allowance is close to the reserve. Check it with `uv run buyer quota` and wait for older sessions to leave the 24 hour window.

If a thread ends with timeouts, look at the runner log for slow decisions or slow model calls. A move should finish within 25 seconds of the supplier's reply. Holding messages in the log mean the decision came back too late.

If a session never shows a result, it may have ended on the arena's side while our runner was stopped. The Counterpart dashboard shows such sessions as stalled after fifteen minutes without activity.
