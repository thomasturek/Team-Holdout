# Counterpart dashboard

A live view of everything the buyer agent negotiates: overview, negotiations (inbox and conversation), suppliers.

```bash
cd frontend
npx pnpm@9.4.0 install
npx pnpm@9.4.0 dev        # http://localhost:5173
```

No backend needed: the Vite dev server reads the agent's run logs (`runs/<set>/case_*/*.jsonl`) and
supplier profiles (`runs/profiles/all.json`) and serves them at `/api` (`server/runs.ts`). The page
polls every 4 s, so new and running negotiations appear on their own. `RUNS_DIR=/path/to/runs` points
it at other logs.

Name, icon and polling interval: `src/app.ts`.
