# Learnings from replays

One entry per finding: what happened, the replay link, the supplier, and what we changed. Newest on
top. (AGENTS.md section 9.) Draft material: `uv run python -m buyer.llm.review report --out runs/review/practice.md`.

| When | Who | Case / supplier | Replay | What happened | What we changed |
|---|---|---|---|---|---|
| Sun 25 Oct 11:49 | DIPLOMAT (practice batches) | P18 / sup:70740 Werdenfels | runs/practice/case_P18/16157957d5424ad5.jsonl | After its final offer we sent its cheaper alternative package back with a wider index deadband (0 -> 5 %): a changed term after a final is a push, it walked, score 0. All 3 walk-aways in today's 86 sessions followed a sheet that changed its terms after a final / agreed offer; countering a final with its own package was agreed 29 of 34 times | `close()`: after a final offer its alternative goes back exactly as offered. Next batch: P18 0.000 -> 0.696, all clean |
| Sun 25 Oct 11:42 | DIPLOMAT | all (this laptop) | runs/runner-practice-*.log | `.env` still had placeholder model names (`PASTE-SONNET-MODEL-ID`): every writer call waited 20 s, then the template; moves took 25.2-25.3 s, over the budget. Last night's blocked key (04:10) did the same | LLM circuit breaker (`llm/client.py`): 3 failed calls in a row or one auth / model error -> calls fail at once for 60 s. Check `.env` model names on the final machine |
| Sun 25 Oct 12:00 | DIPLOMAT | P11 / sup:70140 Kalwisz | runs/practice/case_P11/ | Same code scores 0.626 or 0.710: if Kalwisz steps 47 -> 46 and holds twice, our cash-short hold jump (+0.94) gets 45.5; if it steps 47 -> 46.5 -> 46, it finals at 46.0 first. One good run proved nothing - the mirror rule looked like it fixed P11 but never fired there | Mirror rule stays off (P01 +0.01, P07 +0.015 over 3-4 runs: too little evidence) |
| Sun 25 Oct 11:42-12:15 | DIPLOMAT | all | - | One arena key on several machines: 10 open sessions per key, so concurrent practice runs refused 17 of 20, then 3-4 of 10 sessions per batch (HTTP 429) | In the final: exactly one runner on one machine |
| Sun 25 Oct 01:41 | OPERATOR | P03 P07 P08 P18 (P05, P11 hit too) | runs/practice/case_P07/bf98975f20a3416f.jsonl | Wi-Fi gone ~160 s. E-mails in flight hung the full 180 s read timeout on dead connections (waits 180-229 s); a send that failed fast crashed its worker (`_refresh` re-raised). Suppliers took 2-3 timeouts and walked: P03 0, P07 0.12, P08 0, P18 0. Also D02 (sandbox, 21:23): laptop asleep ~154 s | fix/network-resilience: TCP keepalive (a dead connection fails in ~30 s, the kit retries with the same move id), connect timeout 10 s, bounded `_recover` (reads back what landed, resends only what never arrived), final cases whose play failed are started again (409 resume) |

## DIPLOMAT - wording

<!-- e.g. "Citing the electricity index to sup:70130 got 'not our reality' (forward-bought); the writer
now does not repeat rejected arguments" -->

## SCOUT - data and claims

## ANALYST - policy

## OPERATOR - runtime
