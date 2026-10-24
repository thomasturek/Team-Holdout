# alex-thomas

Hackathon project by Thomas, Halichem, Felix and Alex for the Tacto Negotiation Arena. Challenge instructions: [`CHALLENGE.md`](CHALLENGE.md).

## The idea

See [`docs/IDEA.md`](docs/IDEA.md).

## Getting started

Everything runs from the repo root (Python 3.12, [uv](https://docs.astral.sh/uv/)):

```bash
git clone https://github.com/thomasturek/Team-Holdout.git
cd Team-Holdout
cp .env.example .env      # fill in ARENA_API_KEY and ANTHROPIC_API_KEY; never commit .env
uv sync                   # our package (src/buyer) + the starter kit (arena-kit) as an editable dependency
uv run arena me           # the key works: practice quota and best scores
uv run pytest
```

### Running the agent

```bash
uv run buyer quota                                      # practice sessions used / left (200 per 24 h)
uv run buyer practice --agent naive --purpose baseline  # every hosted practice case once (costs quota; keeps 20)
uv run buyer practice --cases P01 P04 --repeat 2
uv run buyer sandbox --repeat 3                         # case:D01 + case:D02, free
uv run buyer final                                      # the Live Final: every wave until the last has closed
uv run python -m buyer.runtime.harvest                  # sandbox non-stop for the Analyst (see docs/LOGS.md)
```

Switches (environment or `.env`):

```bash
BUYER_POLICY=v1        # default: Policy V0. shadow = V0 plays, V2 decides on a copy and is only logged;
                       # v2 = safe candidate ranking plays (docs/PHASE2_SAFE_ARCHITECTURE.md), V0 as fallback
BUYER_READER=parallel  # default: the LLM reader runs beside the writer; blocking = reader first, then the move
uv run python -m buyer.policy.report --set sandbox      # V2 evidence: sources, shadow agreement, reasons, latency
uv run python -m buyer.sim.compare --episodes 200       # V1 vs V2 on the same synthetic suppliers
uv run python -m buyer.sim.robust run --split development   # V3: adversarial suite, properties, calibration
uv run python -m buyer.llm.accuracy --locked            # V3: reader precision / recall on misleading e-mails
```

Logs: `runs/<set>/<case>/<session>.jsonl`, one JSON file per session in `runs/<set>_sessions/`,
the runner's own log in `runs/runner-<mode>-<time>.log`. Format: [`docs/LOGS.md`](docs/LOGS.md).

Our code imports the kit directly (`from arena_kit.cost import total_cost`); edits in `starter-kit/`
take effect without reinstalling. `buyer.runtime.env.load()` reads `.env`, then `starter-kit/.env`.

## Project structure

```
.
├── src/
├── scripts/
├── docs/
│   └── IDEA.md
├── brief/
├── data/
├── starter-kit/
├── CHALLENGE.md
├── .env.example
└── README.md
```

## Team

| Who | Role | Focus |
|---|---|---|
| Thomas | [ANALYST](roles/ANALYST.md) | ML: simulator, policy, training, calibration |
| Halichem | [DIPLOMAT](roles/DIPLOMAT.md) | LLM: reading supplier e-mails, writing ours |
| Felix | [SCOUT](roles/SCOUT.md) | Data and rules: costs, supplier profiles, claims |
| Alex | [OPERATOR](roles/OPERATOR.md) | Runtime and ops: API, parallelism, logging, final runner |
