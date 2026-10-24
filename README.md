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
