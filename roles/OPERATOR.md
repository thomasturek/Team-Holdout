# THE OPERATOR (runtime, parallelism, data harvesting)

**Owner: Alex**

> Read [`../AGENTS.md`](../AGENTS.md) first: the idea, hard constraints, architecture, interfaces
> (`SupplierProfile`, `Claim`, `Signals`, `Decision`), timeline and guardrails. This file is your job.
> Start every task by saying "Acting as OPERATOR".

**Mission:** every case and every thread runs at the same time, nothing times out, nothing crashes,
and every byte of every run is logged for the Analyst.

**Owns:** `src/buyer/runtime/`, root `pyproject.toml`, `.env` handling, `runs/`.

**Tasks, in priority order**

P0 - first, everyone depends on it
- [ ] Root `pyproject.toml` with `arena-kit` as path dependency on `starter-kit/`; `uv run` works
      from repo root. `.env` loaded, never committed.
- [ ] `log.py`: JSONL per session in `runs/<set>/<case>/<session>.jsonl`: case file, every message
      both ways with timestamps, attachments text, Decisions, Signals, and at the end result +
      trace + back office (`GET /v1/sessions/{sid}` and `/backoffice`).
- [ ] **Per-thread concurrency** (`threads.py`). The kit's `play()` sends one message at a time and
      waits up to ~60 s for the reply - other RFQ threads time out meanwhile. Our loop: one worker
      per supplier thread, each with its own 60 s clock; a shared case state (all offers, so the
      Analyst can cite rivals); a single accept closes the case, all workers stop.
- [ ] Deadline handling: per move < 25 s budget; wave cap from `seconds_left`; 90 s before the cap
      (or slowest round + margin) call the Analyst's `policy.closing(state)` and execute it. You own
      the clock; the Analyst owns what the closing move is.
- [ ] `harvest.py`: run the sandbox (`case:D01`, `case:D02`) continuously, 10 sessions in
      parallel, with the exploration parameter sets the Analyst provides in
      `src/buyer/policy/explore.json`. You run and log; you never choose policy parameters.

P1 - Saturday night
- [ ] `runner.py`: `practice`, `sandbox`, `final` modes. Final mode = our version of `play_waves`
      with our per-thread loop; resume after crash (409 -> pick up session); one shared paced
      client; never calls `/v1/events`, `/screen`, `/leaderboard`, `/results`.
- [ ] Practice quota manager: reads `GET /v1/me`, refuses to start practice runs beyond the budget
      in section 6.
- [ ] Rehearsal: `arena-sim serve --final-rehearsal` with our runner, 2 waves, no errors.

P2 - Sunday morning
- [ ] `arena data` after 08:00, confirm release loaded.
- [ ] Pre-flight: one practice case through the final machine and network.
- [ ] Freeze: tag the commit, write README run instructions, submit hash by 13:00.
- [ ] 13:15: start `final` runner with logs to file, laptop on power, sleep off.

**Definition of done:** 10 parallel cases with 3 threads each, zero timeouts caused by us, every run
fully logged, final runner survives kill-and-restart.
