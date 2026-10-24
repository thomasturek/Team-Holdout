# THE ANALYST (simulator, policy, training)

> Read [`../AGENTS.md`](../AGENTS.md) first: the idea, hard constraints, architecture, interfaces
> (`SupplierProfile`, `Claim`, `Signals`, `Decision`), timeline and guardrails. This file is your job.
> Start every task by saying "Acting as ANALYST".

**Mission:** a policy that wins against suppliers it has never seen, trained in simulation,
calibrated on real runs.

**Owns:** `src/buyer/policy/`, `src/buyer/sim/`, `params.json`.

**Boundary with the SCOUT:** the Scout describes, you decide. You never read the raw data package
or reimplement costing; you consume `SupplierProfile`, `Claim` and the costing helpers from
`src/buyer/facts/`. You own every choice: which offers, which levers, which claims and in what
order, when to accept or walk. Missing a fact? Ask the Scout to add it to the profile.

**Tasks, in priority order**

P0 - Saturday evening
- [ ] **Policy v0, hand-tuned, no training needed.** It must already beat the naive agent. Logic:
  - target price = max(floor_estimate x (1 + margin_floor), what C_best-like reasoning allows);
    walk-away = alternative's C (or fallback-based C if no alternative).
  - open: 2-3 sheets. Sheet A: low price at our reference terms. Sheet B: lower price for shorter
    payment (if cash_pressure) or for a later effective date. Sheet C: price for a longer contract
    or higher volume if the case allows. All computed so each sheet has a similar C for us; the
    supplier's pick reveals what it values.
  - each round: concede a small step towards the supplier's last price (reciprocity), never below
    floor; keep using 2-3 sheets; rotate in a new verified claim (max 3 per message, each once).
  - `final_offer`: push at most once with a small step, only if rounds and time allow; else accept
    if C beats the alternative and must-haves hold.
  - `agreed`: accept.
  - RFQ: run all threads; cite the cheapest rival offer to the others; close with the best C.
  - stabilise / secure_supply: stop when the estimated supplier margin reaches
    `sustainable_margin_pct`.
  - deadline: `closing(state)` = best standing sheet that keeps must-haves and beats the
    alternative, else walk. The Operator calls it when time is short; you define it.
  - `explore.json`: parameter sets for the Operator's sandbox harvester (spread around v0).
- [ ] Policy parameters in `params.json` (initial guesses): open_discount, concession_rate,
      concession_decay, cash_trade_ratio, date_trade_ratio, push_after_final (bool/prob),
      accept_gap_pct, walk_margin_pct, sheets_per_round, claim_order.

P1 - Saturday night
- [ ] **SyntheticSupplier** (`sim/supplier.py`), behaviour from the brief:
  - hidden: floor (full cost), target margin, cash rate, approval threshold and delay, concession
    rate per our move, patience, sensitivity to claims (verified claim = small concession or
    "not our reality" by archetype), walk probability after pushing a final offer.
  - never below floor; gives nothing without a move from us; bigger steps need approval (slower,
    smaller); answers the term sheet it likes best at its own price; `final_offer` near its limit;
    `agreed` when we meet its price; values payment days at its cash rate, contract length as
    security only.
- [ ] **Population** (`sim/population.py`): ranges per archetype built from the Scout's
      `runs/profiles/all.json` (never from the raw data). Domain randomisation: wide ranges.
- [ ] **Env** (`sim/env.py`): runs Policy vs SyntheticSupplier on real practice case files; scores
      with the official formula (C_open from the synthetic opening, C_best from the hidden floor
      with every lever applied).
- [ ] **Train** (`sim/train.py`): CMA-ES or random search over policy params, objective = mean
      score over thousands of episodes across case types; also report the 10th percentile (we hate
      zeros). Output `params.json` + a report.

P2 - Sunday morning
- [ ] **Calibrate** (`sim/calibrate.py`): from Operator logs, fit population ranges so simulated
      concession curves, final-offer timing, payment-day pricing and `c_best` match real runs
      (least squares on per-round price moves). Retrain. Compare sim-predicted vs real score on
      held-out practice cases.
- [ ] Freeze `params.json` by Sun 12:00 with the commit that the final runs.

**Definition of done:** trained policy beats policy v0 on held-out real practice cases, no case
scores 0 from a broken must-have or a bad accept.
