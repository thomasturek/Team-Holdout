---
name: hackathon-plan
description: Hackathon timeline, practice-quota budget and open questions for Tacto - use when planning practice runs, quota or the schedule up to the code freeze and the final.
---

# Hackathon plan (moved from AGENTS.md)

## 5. Timeline (Saturday 24 Oct -> Sunday 25 Oct, CET; clocks go back overnight)

| When | Scout | Analyst | Diplomat | Operator |
|---|---|---|---|---|
| Sat now -> 18:00 | package, costing, floor, claim bank | policy v0 | client, writer, template fallback | pyproject, logging, per-thread loop, harvester |
| Sat 18:00 | **Integration: full agent v0 plays all 10 practice cases once + sandbox** | | | |
| Sat 18:00 -> 24:00 | profiles, archetypes, cash, miner | SyntheticSupplier, population, env, train | reader, doc parsing | runner, quota manager, rehearsal; harvester runs all night |
| Sat night | | training runs | | sandbox harvesting |
| Sun 08:00 | Sunday release | calibrate on logs, retrain | replay review, latency test | `arena data`, pre-flight |
| Sun 11:00 | | **policy freeze candidate** | | full practice run with frozen params |
| Sun 12:00 | | `params.json` frozen | | README, tag commit |
| Sun 13:00 | **Code freeze, submit hash** | | | |
| Sun 13:15 | | | | final runner started |

If anything slips: policy v0 + writer + per-thread loop is a complete, submittable agent. Protect it.

---

## 6. Practice quota budget (200 per rolling 24 h)

| Use | Sessions |
|---|---|
| Baseline: naive and LLM kit agents on all 10 hosted cases | 20 |
| Agent v0 on all 10 cases | 10 |
| Calibration runs (varied params, logged for the Analyst) | 90 |
| Validation of trained policy (held-out comparison) | 40 |
| Sunday pre-flight and final check | 20 |
| Reserve | 20 |

Sandbox runs are unlimited: default to the sandbox for anything experimental.

---

## 8. Open questions for Tacto (ask at office hours, record answers in `docs/IDEA.md`)

- Do sandbox and practice suppliers use the same engine as the hidden ones, only with different settings?
- Supplier reply latency in the final with every team playing at once?
- Are hidden-case suppliers among the 46 in the package, or new?
- Does a longer contract or volume commitment lower the price in practice?

---
