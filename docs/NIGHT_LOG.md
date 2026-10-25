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
