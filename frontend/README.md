# Counterpart: the negotiation dashboard

Counterpart is the visual side of the project. It shows every negotiation our buyer agent plays, live, in the style of a modern purchasing CRM. You can follow a negotiation round by round, read every e-mail both sides sent, see what each deal saved and look up any supplier.

This document explains how to start the dashboard, what each page shows, where its data comes from and how to change it.


## Step 1: Start it

You need Node.js. The project uses the pnpm package manager, which you can run through `npx` without installing it. From the root of the repository, run the following commands.

```bash
cd frontend
npx pnpm@9.4.0 install
npx pnpm@9.4.0 dev
```

Then open http://localhost:5173 in your browser. There is no separate server to start. The dashboard reads the agent's logs directly from the `runs/` folder next to it.

If your logs live somewhere else, point the dashboard at them before starting it.

```bash
RUNS_DIR=/path/to/runs npx pnpm@9.4.0 dev
```


## Step 2: Find your way around

The header holds the app's name on the left, the three pages in the middle and two controls on the right. The first control shows how many negotiations are running right now. The second filters every page to one set of sessions, such as practice or sandbox, or shows all of them together.

The dashboard checks for new data every four seconds. When a new negotiation starts, a deal closes or a negotiation ends without a deal, a small notice appears in the bottom right corner. Clicking the notice opens that negotiation.


## Step 3: The Overview page

The Overview page answers the question of how the agent is doing overall.

Five figures run across the top. They show the number of negotiations, the share that ended in a deal, the average score out of 100, the total amount saved compared with the suppliers' opening offers, and the average number of rounds.

The chart below shows the score over time. Every grey dot is one finished negotiation and the blue line is the average of the last ten, so a better or worse version of the agent shows up as a change in the line. Hovering over the chart shows the exact values. Beside it, a bar shows how all negotiations ended, split into deals, walk-aways, failures, time-outs and stalled sessions.

At the bottom, a table lists every case with its type, its number of runs, its deal rate, the average amount saved and the average score. Clicking a row opens the case's most recent negotiation. The activity feed beside it lists the newest events.


## Step 4: The Negotiations page

The Negotiations page works like an e-mail inbox.

The list on the left holds every negotiation, newest first. Each row shows the supplier, the case, the outcome, the number of rounds and the score. The tabs above the list show all negotiations, only live ones, only deals or only those without a deal. The search box finds a supplier, a case or a session, and the drop-down limits the list to one case.

Clicking a row opens the negotiation on the right. Its header names the case, the buyer, the volume and the session. Four figures summarise the result. They show the score, the amount saved against the opening offer, the final price compared with the supplier's first quote, and the number of rounds used out of the limit.

The price chart shows the unit price round by round. The orange line is what the supplier asked for and the blue line is what we offered. Two dashed lines mark the price we pay today and the price of our fallback option. When a case has several suppliers, buttons above the chart switch between them.

The conversation below the chart shows every e-mail in order. Each message shows who sent it and when, how long the supplier took to reply or how long our agent took to answer, and the term sheets it contained. When we cited facts, a label shows how many the arena confirmed. Clicking a message shows its full text. The conversation ends with the moment we accepted an offer or walked away.

The panel on the right shows the agreed terms, a breakdown of the total cost by category, a check of each must-have, a short card about the supplier and the original case brief.


## Step 5: The Suppliers page

The Suppliers page lists all 46 suppliers from the data package. Each row shows the supplier's country, its type, its defect rate with a coloured quality rating, its on-time delivery rate, how much cash pressure it is under, and how many negotiations and deals we have had with it, with the average score. You can search the list and sort it by activity, score, cash pressure or name.

Clicking a supplier opens a side panel. It shows the parts the supplier makes with their estimated floor price, opening price and best deal, our recent negotiations with it, notes from its correspondence and the facts we can cite against it.


## Step 6: Where the data comes from

The dashboard has no database of its own. While the development server runs, a small plugin in `server/runs.ts` reads two sources and serves them at `/api`.

The first source is the session logs at `runs/<set>/case_*/<session>.jsonl`, which the agent's runtime writes. The plugin reads each file, rebuilds the conversation of every supplier thread with its timestamps, extracts the price each side offered in each round, and picks up the result once the session has ended. It keeps the parsed files in memory and only reads a file again when it changes, so polling stays fast even with hundreds of sessions.

The second source is the supplier profiles at `runs/profiles/all.json`, which the Scout builds.

The plugin decides the status of each negotiation from its log. A session with a deal in its result is a deal. A session with a result but no deal is a walk-away, a time-out or no deal, depending on why it ended. A session without a result is live while its log changed in the last fifteen minutes, and stalled after that.

The plugin offers three endpoints. `GET /api/sessions` returns a summary of every session. `GET /api/sessions/<set>/<session id>` returns one session in full, with every thread, message and price. `GET /api/suppliers` returns every supplier profile.


## Step 7: How the code is organised

The application is written in Vue 3 with TypeScript, styled with Tailwind CSS and a small stylesheet of its own, and built with Vite.

`src/main.ts` starts the app, and `src/App.vue` holds the header, the splash screen and the loading bar. `src/router.ts` defines the three pages and the navigation. The pages themselves are in `src/views/`, one file per page.

`src/stores/desk.ts` holds the shared state. It polls the API, keeps the list of sessions and suppliers, loads the selected negotiation, and raises the notices when something changes.

`src/api/` holds the API client and the data types. `src/format.ts` holds the helpers that format money, scores, dates and term values, and the labels and colours for each status.

`src/components/` holds the shared building blocks. `NegotiationDetail.vue` is the right hand side of the Negotiations page. `charts/LineChart.vue` draws both charts, including the hover tooltip. `StatusPill.vue`, `Avatar.vue` and `Toasts.vue` draw the status labels, the supplier initials and the notices.

`src/styles/desk.css` holds the visual design. Its colours are defined once as variables at the top of the file.


## Step 8: Change it

The name, the icon and the polling interval are set in `src/app.ts`. The icon is the name of any symbol from Google's Material Symbols set.

To add a page, create a new file in `src/views/`, add a route for it in `src/router.ts`, and add an entry to the `navItems` list in the same file so it appears in the header.

To show more data, add the field to the summary or detail object in `server/runs.ts`, add it to the matching type in `src/api/types.ts`, and use it in the page.

To check your changes for type errors, or to build the app, run the following commands.

```bash
npx pnpm@9.4.0 typecheck
npx pnpm@9.4.0 build
```

A production build contains the pages only. The data endpoints exist inside the development server, so the dashboard should be run with the `dev` command for demos.
