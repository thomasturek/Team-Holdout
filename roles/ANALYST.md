# THE ANALYST (data and rules)

> Read [`../AGENTS.md`](../AGENTS.md) first: the idea, hard constraints, architecture, interfaces
> (`SupplierProfile`, `Claim`, `Signals`, `Decision`), timeline and guardrails. This file is your job.
> Start every task by saying "Acting as ANALYST".

**Mission:** turn the data package and the case file into exact numbers, a profile of every supplier
and a bank of claims that always come back `verified`.

**Owns:** `src/buyer/facts/`. Outputs `SupplierProfile`, `Claim`, costing helpers.

**Tasks, in priority order**

P0 - must exist by Saturday evening
- [ ] `package.py`: load `DataPackage(ARENA_DATA)`; merge `case["facts"]`; merge the Sunday release
      automatically when present. One function `lookup(id)` that checks case facts first.
- [ ] `costing.py`: `c(case, terms, std, supplier=None)` and `c_alt(case)` over `arena_kit.cost`;
      `lever_values(case, terms, std)` = € change in C for each lever step (payment days per option,
      effective date per option, volume, lead time, incoterm). The Coach uses these directly.
- [ ] Floor estimate: `should_cost` row for the part (prefer the row with this `supplier_id`, error
      ~5 %); else German base x country factor (AT/CH 1.05, CZ/PL/HU 0.82, TR 0.75, CN 0.7, DE 1.0),
      error 5-15 %. Convert to the case's `price_unit`. Fallbacks when no should-cost row: lowest
      price in `quotes` / `price_conditions` for the part minus a typical margin; mark confidence low.
- [ ] Claim bank per case, every claim verified offline against `facts.json` with the API's check
      rules (api.md "What counts", tolerance +-0.5 pp / +-0.5 %):
  - index claims: for each `cost_drivers` series of the part, the 12-month change ending at the
    series' latest month (window <= 12 months, ending within the last 12 months of the data). Keep
    the ones that fell or rose less than the supplier's asked %. Sentence names the series in words.
  - rival quote / offer claims (RFQ): filled in at run time from the opening quotes.
  - notice claims: price letter `doc` (notice days) vs contract `ctr` clause notice; only when the
    letter gives less notice than the contract requires.
  - scorecard / quality claims: `sc` rows (OTD mean, ppm mean), `qn` for quality cases.
  - PO price history: 2-8 `po` lines of the same part showing stable or falling prices.
  - should-cost claim: `cost:<part>` with its unit_cost (use with care - it reveals our estimate).
  - forecast claims: `fc:` volume changes (more volume = leverage).
- [ ] `profile.py`: SupplierProfile from `suppliers`, `supplier_intel` (equity ratio, credit index
      and its 12-month change, owner type, staff, turnover), `invoices` (how late Hollerau pays
      it), `negotiation_history` (asked vs settled), `scorecards`, `contracts`/`contract_clauses`,
      `news`, `documents` + `correspondence/` text.

P1 - Saturday night
- [ ] Archetype classifier (rules first): family foundry, group with approval ladder, cash-short job
      shop, near-monopolist, unknown. Inputs: owner_type, group_parent, equity ratio, credit index
      trend, sourcing (number of qualified sources for the part), notes keywords.
- [ ] `cash_rate_estimate` and `cash_pressure` from equity ratio, credit index (higher = worse,
      German style), our late payments, notes/news mentioning liquidity, quote remarks.
- [ ] Supplier estimate for the relationship term (`full_cost`, `interest_rate`, `standard`) so the
      Coach can price `stabilise` / `secure_supply` cases with `total_cost(..., supplier)`.
- [ ] Correspondence miner: extract per supplier the facts that move it (cash, capacity, owner
      succession, new customer, energy contract, strike...). Rules + optional LLM pass **offline**,
      cached to `runs/profiles/*.json`. Noise exists: keep only notes with a supplier and a date.

P2 - Sunday 08:00-12:00
- [ ] Re-run with the Sunday release; diff new news / letters / memo per supplier; add new claims.
- [ ] Unit tests: every claim in the bank for all 19 practice cases checks as `verified` against
      `facts.json` with our own checker.

**Definition of done:** for any case file, `build(case)` returns profiles and a claim bank in < 2 s,
zero claims that would be `contradicted`.
