# Next steps

## Thomas (Analyst), now
1. Commit and push my two changes: `src/buyer/facts/profile.py` and the hook in `src/buyer/runtime/agent.py`.
2. After the practice runs: calibrate on the 10 new suppliers, retrain, and fix RFQs (rival citing and acting on signals).

## Alex (Operator), now, the main blocker
1. In `runtime/agent.py`, swap the template for Hichem's calls. Each supplier reply goes through `read()`,
   and the resulting signals go into the thread state. Each decision goes out through `to_message()`, with
   `known_id` and a deadline so a move never passes 25 seconds.
2. Run Hichem's latency benchmark (`python -m buyer.llm.bench`) with the key set. It must print PASS.
3. Ping Thomas when it's merged. Thomas then runs the 10 practice cases.

## Hichem (Diplomat), now
1. Put the team's Anthropic API key in `.env` on every machine that runs the agent. It's empty on Thomas's laptop.
2. Run the live test (`LLM_LIVE_TESTS=1 pytest src/buyer/llm -k live`) and confirm it passes.
3. Help Alex wire it in.
4. After the practice runs: read the replays and tune the wording.

## Felix (Scout), next 1 to 2 hours
1. Build the claim bank: `claims(case)` returns verified sentences with their IDs, for index changes on the
   part's cost drivers, notice-period violations, scorecard and quality figures, and PO price history. Every
   claim must check as verified against `facts.json`. This feeds the Diplomat's e-mails directly.
2. Fill the cost gaps: floor estimates for P04, P07, P08, P11 and P18 from price history or category averages.
3. Add archetypes to the profiles: family, group, cash-short or near-monopolist.

## Order
Alex and Hichem wire in the LLM, then the 10 practice runs, then calibrate and retrain, with Felix's claims
merged as soon as they're ready.
