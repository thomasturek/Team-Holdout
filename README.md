# alex-thomas

Hackathon project by Thomas, Halichem, Felix and Alex for the Tacto Negotiation Arena. Challenge instructions: [`CHALLENGE.md`](CHALLENGE.md).

## The idea

See [`docs/IDEA.md`](docs/IDEA.md).

## Getting started

```bash
git clone <repo-url>
cd alex-thomas
cd starter-kit
cp .env.example .env
uv sync --all-extras
uv run arena me
```

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
