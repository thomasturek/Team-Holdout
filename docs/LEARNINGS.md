# Learnings from replays

One entry per finding: what happened, the replay link, the supplier, and what we changed. Newest on
top. (AGENTS.md section 9.) Draft material: `uv run python -m buyer.llm.review report --out runs/review/practice.md`.

| When | Who | Case / supplier | Replay | What happened | What we changed |
|---|---|---|---|---|---|
| Sun 25 Oct 01:41 | OPERATOR | P03 P07 P08 P18 (P05, P11 hit too) | runs/practice/case_P07/bf98975f20a3416f.jsonl | Wi-Fi gone ~160 s. E-mails in flight hung the full 180 s read timeout on dead connections (waits 180-229 s); a send that failed fast crashed its worker (`_refresh` re-raised). Suppliers took 2-3 timeouts and walked: P03 0, P07 0.12, P08 0, P18 0. Also D02 (sandbox, 21:23): laptop asleep ~154 s | fix/network-resilience: TCP keepalive (a dead connection fails in ~30 s, the kit retries with the same move id), connect timeout 10 s, bounded `_recover` (reads back what landed, resends only what never arrived), final cases whose play failed are started again (409 resume) |

## DIPLOMAT - wording

<!-- e.g. "Citing the electricity index to sup:70130 got 'not our reality' (forward-bought); the writer
now does not repeat rejected arguments" -->

## SCOUT - data and claims

## ANALYST - policy

## OPERATOR - runtime
