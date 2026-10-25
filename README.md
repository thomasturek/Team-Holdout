# Team Holdout: a buyer agent for the Tacto Negotiation Arena

This repository holds our entry for the Tacto Negotiation Arena hackathon. It contains a software agent that buys industrial parts on behalf of a manufacturer. The agent negotiates with suppliers by e-mail and tries to close each deal at the lowest total cost. The repository also contains a dashboard called Counterpart, which shows every negotiation the agent plays, live, in the style of a modern CRM.

The team is Thomas, Halichem, Felix and Alex. The official challenge text is in [`CHALLENGE.md`](CHALLENGE.md), and the brief from Tacto is in [`brief/brief.md`](brief/brief.md).


## 1. The problem we are solving

In the arena, our team plays the buyer. Each case describes a real looking purchasing situation. A supplier might announce a price increase, a contract might be up for renewal, or we might need quotes from several suppliers for a new part. The suppliers are simulated by the arena, and they answer our e-mails the way real sales people would. They make offers, push back, ask for faster payment and sometimes declare a final offer.

Every case is scored by money. The arena computes the total cost of a deal, which covers far more than the unit price. It includes payment terms, freight, lead time, quality risk, tooling and index clauses. A case scores between 0 and 1. A score of 0 means we did no better than the supplier's opening offer, and a score of 1 means we reached the best deal the case allowed. If we break one of the buyer's must-haves the score is 0, and if we walk away we receive the score of our fallback option.

The final round is played with no human in the loop. The agent has to negotiate on its own, in parallel across many cases, and answer every supplier within 60 seconds.


## 2. How the agent works

The agent is built on one simple principle. Code knows the rules, a tuned policy decides the strategy, and a language model only handles the words. We never let the language model decide a number, a term or whether to accept a deal, because a single invented figure can cost a whole case.

The work is split into four parts, and each part belongs to one person on the team.

The first part is the Scout, which lives in [`src/buyer/facts/`](src/buyer/facts/). It reads the data package that Tacto provides, which describes 46 suppliers, their contracts, quality records, price histories and the market indices that drive their costs. From this data the Scout builds a profile of every supplier. The profile estimates how low the supplier can go, how badly it needs cash and how it tends to negotiate. The Scout also builds a bank of facts that we can cite in our e-mails, such as a supplier's real quality record or the true change in a steel index. Each of these facts is checked against the arena's own rules before it is ever sent, so the supplier cannot dismiss it.

The second part is the Analyst, which lives in [`src/buyer/policy/`](src/buyer/policy/). This is the decision maker. After every supplier reply it decides what to do next. It can send new offers, accept the best one on the table or walk away. When it makes an offer it usually sends two or three complete term sheets at once, which lets us learn which terms the supplier values most. Its behaviour is controlled by a small set of tuned parameters in [`params.json`](src/buyer/policy/params.json), such as how far below the supplier's floor to open and how quickly to concede. Those parameters are tuned in a simulator, which lives in [`src/buyer/sim/`](src/buyer/sim/). The simulator models how suppliers behave, is calibrated on our real sandbox and practice sessions, and plays the policy against thousands of synthetic suppliers.

The third part is the Diplomat, which lives in [`src/buyer/llm/`](src/buyer/llm/). It has two jobs. First, it reads each supplier e-mail and turns the prose into fixed signals, such as whether the supplier is short of cash or is using final offer language. Second, it writes our reply around the decision the Analyst has already made. The language model writes only the surrounding prose. Every number, term sheet and cited fact is inserted by code, and a guard checks the finished e-mail before it goes out. If the model is slow or fails, a template writer produces a safe e-mail instead.

The fourth part is the Operator, which lives in [`src/buyer/runtime/`](src/buyer/runtime/). It talks to the arena's API, opens sessions and runs every supplier thread of every case at the same time, each with its own clock. It also handles retries and recovery after a crash, and it writes a complete log of everything that happens.


## 3. What happens in a single negotiation

It helps to follow one case from start to finish.

When a case opens, the Operator downloads the case file and the opening e-mail from each supplier, including the quote document with the supplier's standard terms. The Scout looks up the supplier profiles and prepares the facts that fit this case.

The Analyst then chooses an opening position. It aims below the supplier's estimated floor, builds two or three complete term sheets that trade price against other terms, and picks up to three facts to cite. The Diplomat writes the e-mail, and the Operator sends it.

When the supplier replies, the Diplomat reads the reply into signals and the Analyst updates its view. Perhaps the supplier accepted one of our arguments, or perhaps it said it needs faster payment. The Analyst moves its offer a measured step, and the loop repeats.

The negotiation ends when the Analyst accepts an offer that beats our fallback and satisfies every must-have, or when it walks away because no acceptable deal is in reach. The arena then reports the total cost and the score, and the Operator writes everything to the logs.


## 4. Setting up the project

The project uses Python 3.12 and the [uv](https://docs.astral.sh/uv/) package manager. Every command below runs from the root of the repository.

Start by cloning the repository and moving into it.

```bash
git clone https://github.com/thomasturek/Team-Holdout.git
cd Team-Holdout
```

Next, create your environment file from the example and fill in the arena key and the Anthropic key. This file must never be committed.

```bash
cp .env.example .env
```

Then install the project. This installs our own package from `src/buyer` together with Tacto's starter kit, which lives in `starter-kit/`.

```bash
uv sync
```

Finally, check that your key works and that the tests pass.

```bash
uv run arena me
uv run pytest
```


## 5. Running the agent

The arena offers three places to play. The sandbox has two demo cases and can be played as often as you like. The practice set has ten hosted cases, limited to 200 sessions in any 24 hours. The live final is played once, in five waves of eight minutes each.

To see how much of the practice allowance is left, run the following command.

```bash
uv run buyer quota
```

To play the sandbox cases, which costs nothing, run the following command.

```bash
uv run buyer sandbox --repeat 3
```

To play chosen practice cases, name them. Each session counts against the daily allowance, so please agree with the team before running practice sessions.

```bash
uv run buyer practice --cases P01 P04 --repeat 2
```

To play the live final, run the final runner. It plays every wave until the last one has closed.

```bash
uv run buyer final
```

There is also a harvester that plays the sandbox without stopping, which gives us free data for tuning the policy.

```bash
uv run python -m buyer.runtime.harvest
```


## 6. Where the results go

Every session is logged in full. Each one gets its own file at `runs/<set>/<case>/<session>.jsonl`, where every line records one event, such as an e-mail we sent, a supplier reply, a decision or the final result. A complete JSON copy of every finished session is also saved in `runs/<set>_sessions/`. The format of these logs is described in [`docs/LOGS.md`](docs/LOGS.md).


## 7. The Counterpart dashboard

Counterpart is the visual side of the project. It lives in [`frontend/`](frontend/) and turns the agent's logs into something a person can follow at a glance. It is designed to look and feel like a modern sales or purchasing CRM rather than a technical tool. As the agent plays, new negotiations appear on their own, deals light up as they close, and every conversation can be read in full.

### Starting it

You need Node.js installed. From the root of the repository, move into the frontend folder, install its packages and start it.

```bash
cd frontend
npx pnpm@9.4.0 install
npx pnpm@9.4.0 dev
```

Then open http://localhost:5173 in your browser.

The dashboard needs no separate server. While it runs, it reads the log files in `runs/` and the supplier profiles in `runs/profiles/all.json` directly, and it checks for new data every four seconds. To point it at a different folder of logs, set the `RUNS_DIR` environment variable before starting it.

### The Overview page

The Overview page is the first thing you see. Across the top it shows five headline figures. These are the number of negotiations played, the share that ended in a deal, the average score out of 100, the money saved compared with the suppliers' opening offers, and the average number of rounds per negotiation.

Below these figures, a chart shows how the score has developed over time. Each grey dot is one finished negotiation, and the blue line is the average of the last ten, so you can see whether a new version of the agent is doing better or worse. Next to the chart, a bar shows how the negotiations ended, split into deals, walk-aways, failures and time-outs.

At the bottom, a table lists every case with its number of runs, deal rate, average saving and average score. Clicking a case opens its most recent negotiation. Beside the table, an activity feed lists the latest events as they happen.

### The Negotiations page

The Negotiations page works like an inbox. On the left is a list of every negotiation, newest first. Each row shows the supplier, the case, the outcome, the number of rounds and the score. Tabs at the top filter the list to live negotiations, deals or failures, and a search box and case filter narrow it further. A negotiation that has just arrived is marked with a blue line, and a small notice appears in the corner of the screen.

Selecting a negotiation opens it on the right. The header names the case and the buyer, and four figures summarise the result. These are the score, the money saved, the final unit price compared with the supplier's first quote, and the number of rounds used.

Below the summary is a chart of the unit price, round by round. The orange line is what the supplier asked for and the blue line is what we offered, so you can watch the two sides close the gap. Dashed lines mark the price we pay today and the price of our fallback option. In cases with several suppliers, you can switch between them above the chart.

Under the chart is the full conversation as a timeline. Every e-mail from the supplier and from our side appears in order, with its time and the term sheets it contained. Messages show how quickly the supplier replied and how quickly our agent answered. When we cited facts, a label shows how many the arena confirmed. Clicking a message expands it to its full text. The timeline ends with the moment we accepted an offer or walked away.

The panel on the right shows the agreed terms, a breakdown of the total cost by category, a check of each must-have, a short card about the supplier and the original case brief.

### The Suppliers page

The Suppliers page lists all 46 suppliers from the data package. For each one it shows the country, the type of company, its quality record in defective parts per million, its on-time delivery rate, how much cash pressure it is under, and how our negotiations with it have gone. You can search the list and sort it by activity, score or cash pressure.

Clicking a supplier opens a side panel with more detail. It shows the parts the supplier makes, with the estimated floor price, the opening price and the best price we reached. It also lists our recent negotiations with that supplier, the notes gathered from its correspondence and the facts we can cite against it.

### Where the code lives

The data layer is a small plugin for the Vite development server in [`frontend/server/runs.ts`](frontend/server/runs.ts). It reads the logs, works out the status of each negotiation and serves the results at `/api`. The pages are written in Vue and live in [`frontend/src/views/`](frontend/src/views/), and the shared pieces, such as the chart and the conversation view, live in [`frontend/src/components/`](frontend/src/components/). The name, the icon and the refresh rate of the dashboard are set in [`frontend/src/app.ts`](frontend/src/app.ts). The [frontend README](frontend/README.md) explains every page, the data flow and how to extend the dashboard.


## 8. How the repository is organised

The folder `src/buyer/` holds the agent itself. Inside it, `facts/` is the Scout, `policy/` is the Analyst, `sim/` is the simulator the Analyst tunes against, `llm/` is the Diplomat and `runtime/` is the Operator. The file `src/buyer/interfaces.py` defines the data that passes between them.

The folder `tests/` holds the tests for the policy and the runtime, and the Diplomat and the Scout keep further tests next to their code. Running `uv run pytest` covers the main tests and the Diplomat's, and `uv run pytest src/buyer/facts` runs the Scout's.

The folder `frontend/` holds the Counterpart dashboard. The folder `docs/` holds the project documentation described in the next section. The folder `scripts/` holds a helper script for comparing two batches of practice runs.

The folder `starter-kit/` holds Tacto's starter kit, which provides the API client and the official cost formula that we use everywhere. The folders `brief/` and `data/` hold the challenge brief and the supplier data package, exactly as Tacto published them. The folder `runs/` holds the logs of every session the agent has played.

The file [`AGENTS.md`](AGENTS.md) is the team's working agreement. It records the architecture, the contracts between the four parts, who owns what and the rules every contributor follows, including coding assistants.


## 9. Where to read more

The [documentation folder](docs/README.md) explains the project step by step. [How scoring works](docs/SCORING.md) explains exactly how the arena prices a deal. [Architecture](docs/ARCHITECTURE.md) explains how the four parts fit together and follows one move through the system. [Running the agent](docs/RUNNING.md) is the practical guide to setup, practice, the final and troubleshooting. [Run logs](docs/LOGS.md) describes the log format.

Each part of the agent also has its own README next to its code. They are [the Scout](src/buyer/facts/README.md), [the Analyst](src/buyer/policy/README.md), [the simulator](src/buyer/sim/README.md), [the Diplomat](src/buyer/llm/README.md), [the Operator](src/buyer/runtime/README.md) and [the Counterpart dashboard](frontend/README.md).


## 10. Rules we never break

A few rules protect every case, and the code enforces them. The agent never accepts a deal that breaks a must-have or costs more than our fallback. It never cites a data reference that does not exist in the data package or the case. The language model never produces a number that ends up in a term sheet. The agent never reads the arena's leaderboard, results or event feed. Secrets and API keys are never committed. Every reply goes out within 25 seconds of the supplier's message, which leaves a safe margin inside the arena's 60 second limit.


## 11. The team

| Person | Role | Focus |
|---|---|---|
| Thomas | [Analyst](src/buyer/policy/README.md) | The decision policy, its parameters and their tuning |
| Halichem | [Diplomat](src/buyer/llm/README.md) | Reading supplier e-mails and writing ours |
| Felix | [Scout](src/buyer/facts/README.md) | Data, costing, supplier profiles and verified facts |
| Alex | [Operator](src/buyer/runtime/README.md) | The API, parallel play, logging and the final runner |
