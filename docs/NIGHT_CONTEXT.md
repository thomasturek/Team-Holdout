# What we know (Team Holdout, night of 24/25 Oct 2026)

Practice score per run (10 hosted cases, mean x100). Start of the night 56.7; now 77.2 (angle A) / 78.0 (angle B),
both clean (10/10 deals). Target 85-90. Live Final on hidden cases drawn from the same pool of 46 profiled
suppliers; last edition's winners averaged about 70 per wave there.

## Latest per-case scores and the best any team reached (EHL 2026 practice board)
| Case | Type / goal | Supplier (archetype) | Ours now | Record | Notes |
|---|---|---|---|---|---|
| P01 | price_increase / stabilise | 70110 Brandlhuber (family_foundry, stale costing) | 0.89 | 0.995 | low opening (126.9) gave 0.91-0.97; relationship floor lifted it to 131.6 and finals rose to 134.6-136.6 |
| P02 | price_increase / stabilise | 70510 Nordmark (group_ladder, committee >2 %) | 0.735 | 0.847 | wins with CU clause 5 % deadband + 90 d at 361.72 (agreed in round 1); record structure unknown |
| P03 | renewal / stabilise | 70530 Selvbrunn (group_ladder, price frozen) | 0.935 | 0.936 | refuses all price trades; 90 d at 431.77 |
| P04 | renewal / routine | 70620 Wälzlager (distributor, price frozen) | 0.87 | 0.874 | at record |
| P05 | rfq / leverage, 3 bidders | 70210 Dralveck (job shop, cash 0.36), 70240 Hrvelec (full book, 52 d lead breaks must-have <=42), 70250 Fuchsreiter (free capacity) | 0.814 | 0.828 | closes with 70210 at 28.00 / 14 d |
| P07 | bundling / routine | 70610 Leitner (family, idle 2nd shift) | 0.65-0.705 | 0.779 | asks "Which volume can you commit to?"; winners 5.35 / 45 d / 36 m |
| P08 | raw_material / leverage | 70710 Donautal (distributor, alloy hedged until 03/2027) | 0.83 | 0.916 | keep fixed sheets, never adopt its clause; record 5.21-5.35 |
| P10 | capacity / secure_supply | 70410 Ravensteiner (near-monopolist, sold out, allocates) | 0.663 | 0.702 | final offer in round 1 always; should-cost claim 24.31 "taken into account" |
| P11 | quality / quality_first | 70140 Kalwisz (cash-short job shop, red scorecard, we pay late 93 %) | 0.63-0.71 | 0.807 | alternates 45.50 / 46.00; chargeback trade; payment fixed 60 d |
| P18 | raw_material / leverage | 70740 Werdenfels (family distributor) | 0.696 | 0.756 | keep fixed sheets; winners 5.00 with its clause |

## Mechanics established (our logs + winners' docs/learnings.md)
- Suppliers give almost everything in reply to round 1; final offers come on a fairly fixed schedule
  (P10 r1, P08/P18 r3, P02 r4, P01 r5-6). Concession per round about min(0.8 x our move, shrinking cap);
  a 40 % move gets the same as 30 %; tiny moves (<0.1 %) or identical sheets trigger the final.
- "agreed" freezes the price; an ask the supplier agrees to was above its floor.
- Claims: notice period 100 % moved, quality record 72 %, rival quote 65 %, falling index 45 %, price history
  38 % (48 % rejected), delivery record 23 % (56 % rejected). Rising index -> "Your figures confirm our case".
  should_cost and forecast claims get "taken into account". No supplier shares a cost breakdown.
- Supplier values an index clause at material_share x (driver 12-month change - deadband): Nordmark ~9.5 %,
  distributors <= 2.7 %. Clause trade only above 4 %.
- Packages: menu of 2-3 sheets of equal value to the supplier (kit supplier_value), cheapest for us within
  0.3 %; never a payment trade that costs us more at the supplier's own price (except cash-short suppliers).
- Relationship charge (stabilise / secure_supply): quadratic below the sustainable margin; Felix's memory fits
  each supplier's full cost from logged charges. Floor applied except for family foundries (they negotiate down).
- Writer: Sonnet 5.5, guard forbids any digit in model prose (figures only via code blocks); code-written
  volume line; situation playbooks by case type; late-payment commitment when the supplier complains.
- Wi-Fi drops lost whole cases twice (timeouts -> supplier walks). Network robustness matters in the final.

## Open questions
- What lowers the round-1 counter further (P02, P08 records sit below any first counter we have seen)?
- P11: which package reaches 44.9-45.0 reliably (chargeback/ppm combinations)?
- P07/P10: does the 36-month contract (now on) move them?
- What should the agent do for persona traits never seen in practice (hedged, approval_2pct, partnership_2022,
  reference_customer, deprioritising_us, complains_late_pay) - the final will contain them.
