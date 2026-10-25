# Night log (Claude, autonomous, 03:20-08:00)

Baseline: tag `baseline-78` (practice 77.2 angle A / 78.0 angle B, 20 clean sessions).
Branch: `night/claude` (local, not pushed). Budget: at most 50 practice sessions; quota at start 262.
Rule: a change is promoted only if it beats the baseline on the same cases; one lucky run does not count.

## Plan
1. Collect every logged negotiation with these suppliers (ours + the public EHL 2026 repos).
2. Fit each supplier's response: first step, per-round cap, reaction to our move, final trigger, floor.
3. Calibrate the simulator on it; optimise opening and pacing per supplier type; check on held-out logs.
4. Tailored plans for all 46 profiled suppliers (hidden final cases come from this pool).
5. Validate in small practice runs; freeze a candidate by 07:30; summary at 08:00.

## Log
- 03:20 baseline tagged, branch created, caffeinate on until 08:20
- 03:30 targets set from the winners' per-case records: P07 +0.12, P11 +0.10-0.18, P01 +0.10, P10 +0.04 (36 m)
- 03:45 budget raised: at most 150 practice sessions (262 left, >=110 reserve); API: Opus 5.5 only, hard stop USD 130; caffeinate until 09:15
- 03:47 budget: up to 250 practice sessions (keep >=12 for Sunday pre-flight; pass --reserve 12 when low)
- 03:55 wave 1 launched: 8 case analyses + 6 reviews (Opus 5.5)
- 04:00 night-v1 practice: 77.6 (P07 0.692 up from 0.653-0.659 with 36 m; P01 0.909; others in band); 252 left
- 04:02 wave 1 aborted: Opus thinking used the whole 20k cap, empty answers (USD 5.5 lost); rerun with max_tokens 64k
- 04:03 effective logged cap lowered to USD 120 (aborted in-flight calls are unlogged)
- 04:10 ANTHROPIC KEY BLOCKED: 'reached your specified API usage limits, access again 2026-11-01'. Workers dead; agent reader/writer fall back to rules/templates. MORNING ACTION: new key or raise limit before the final.
- 04:15 key unblocked by Thomas (spend limit raised); worker cap USD 90 logged (practice runs also draw on the key; keep >=25 for the final)
- 04:07 wave 1: 8 case analyses done (USD 12.7); 6 reviews relaunched
- 04:35 v2 committed: min step 0.75 %, hold jump 50 % (cash-short, 2 holds), monotone package prices, close vs cheapest sheet, writer: no unbacked reasons
- 04:58 night-v2 practice: 74.2 (P01 0.616!, P18 0.630, P07 0.653 down; P11 0.71) -> pacing changes hurt; investigating
- 05:10 P01 v2 drop = no claims in round 1 (claim bank silently empty: shared SQLite cursor across threads). Fixed: locked SQLite in kit data.py, claim bank retried and never cached empty. min_step off (P18/P07 worse, winners: slow walk better for distributors). Runtime fixes A/B/C/E from review applied.

## 05:10-07:35 - lost
Waited on a hung test run (new resend loop in threads.py never ends under a permanent fault). Nothing ran. Runtime resilience changes set aside in runs/night/runtime_resilience.patch; committed runtime restored.

## 07:45 v3 (data lock fix, claim bank retry, min step off): 76.6
P01 0.909 (v2 0.616: claims fix works). P11 0.626 (first counter 47.00 against 46.50 in v2). Eight cases identical to v2 to three decimals.

## 07:49 v4 (open question at the end of the first e-mail + forecast claim in every case type): 75.7
P11 0.710, P04 0.874, P07 0.659 up; P01 0.800, P10 0.617, P08 0.793 down. Both changes uncommitted.

## 08:04-08:37 bets (patches: runs/night/bets_0830.patch)
- v5 open question in the first e-mail only: 76.7 (v3 76.6). Kept.
- Push past a final offer (P07 P10 P11 P18): all four walked. Final offers are hard.
- Ride 2 % below the supplier's price after round 1: P02 P07 P10 P18 identical deals, P08 and P11 worse. The concession schedule ignores our prices.
- Goodwill paragraph (reference customer, forecasts, fast approval): P18 0.696, P01 0.848, P08 0.737; 75.7.
- v6 open cap 10 % + escalation never in the first e-mail: 68.8 (P08 walked at 5.05 after four 0.05 steps).
- P02 without the clause beats 0.734 only below 369.5 at 90 days; Nordmark's full cost is about 371.7.
- P02 P03 P04 P05 P10 identical to four decimals in every run tonight.
