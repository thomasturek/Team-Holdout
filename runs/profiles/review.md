# Supplier review

46 suppliers. Correct anything in `src/buyer/facts/overrides.json` (with `_why`); drop a claim with `"drop_claims": ["<key>"]`.

## Gießerei Brandlhuber GmbH & Co. KG (sup:70110)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked 0.43 % on average, settled -2.37 %
- quality 2026Q3: OTD 85.2 %, 712 ppm, amber
- part:310010: floor 135.19 (observed_best, +-3%)
- part:310012: floor 353.94 (should_cost+observed_bias, +-5%)

Notes:
- 2026-07-15 Visit by the owner: Visit by the owner of Gießerei Brandlhuber GmbH & Co. KG. He reminded us that in 2022 they kept supplying at the old price for a quarter and said he expects partnership in return. (doc:20260715-70110-M5)
- 2026-08-24 Price discussion: Call with the owner of Gießerei Brandlhuber GmbH & Co. KG: he asked where we get our index figures from - he works from his own spreadsheet, last updated two years ago. (doc:20260824-70110-M1)
- 2026-09-02 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260902-70110-M2)
- 2026-09-09 Visit by the owner: The owner of Gießerei Brandlhuber GmbH & Co. KG admitted he had not followed his material and energy prices closely since the 2022 peak; his office manager does the costing. (doc:20260909-70110-M4)
- 2026-09-17 Visit by the owner: Visit by the owner of Gießerei Brandlhuber GmbH & Co. KG. He reminded us that in 2022 they kept supplying at the old price for a quarter and said he expects partnership in return. (doc:20260917-70110-M3)

Claims:
- `notice:sup:70110` (0.99) Your letter of 11 September 2026 (doc:20260911-70110-P01) gives 51 days' notice, while our contract (ctr:4600070110) requires 90 days.
- `ppm:sup:70110` (0.71) Your quality was 712 ppm defective parts in the four quarters to 2026Q3 (sc:70110@2026Q3).
- `po:sup:70110:part:310010` (0.65) Our orders of Volute casing HN 50-200 with you were placed at EUR 128.42 on 2024-10-04 (po:4500011493-10), EUR 128.27 on 2025-06-03 (po:4500012541-10), EUR 126.53 on 2026-01-16 (po:4500013434-10) and EUR 126.53 on 2026-09-21 (po:4500014428-10): the price has not risen.
- `otd:sup:70110` (0.49) Your on-time delivery was 85.2% in the four quarters to 2026Q3 (sc:70110@2026Q3).
- `index:LCI-C` (0.46) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-C241` (0.16) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).
- `index:PPI-D351` (0.12) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `po:sup:70110:part:310012` (0.65) Our orders of Volute casing HN 100-315 with you were placed at EUR 388.80 on 2024-10-07 (po:4500011507-10), EUR 388.31 on 2025-06-10 (po:4500012563-10), EUR 383.06 on 2026-01-19 (po:4500013439-10) and EUR 383.06 on 2026-09-23 (po:4500014449-10): the price has not risen.

## Eisengießerei Velkenreith GmbH (sup:70120)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked 0.45 % on average, settled -1.83 %
- quality 2026Q3: OTD 74.5 %, 734 ppm, amber
- part:310030: floor 35.98 (should_cost, +-5%)
- part:310031: floor 54.42 (own_price, +-15%)

Notes:
- 2026-07-19 Visit by the owner: Visit by the owner of Eisengießerei Velkenreith GmbH. He reminded us that in 2022 they kept supplying at the old price for a quarter and said he expects partnership in return. (doc:20260719-70120-M1)

Claims:
- `otd:sup:70120` (1.00) Your on-time delivery was 74.5% in the four quarters to 2026Q3 (sc:70120@2026Q3).
- `ppm:sup:70120` (0.73) Your quality was 734 ppm defective parts in the four quarters to 2026Q3 (sc:70120@2026Q3).
- `po:sup:70120:part:310030` (0.65) Our orders of Impeller HN 200 with you were placed at EUR 34.77 on 2024-09-30 (po:4500011477-10), EUR 34.73 on 2025-05-30 (po:4500012521-10), EUR 34.26 on 2026-01-26 (po:4500013473-10) and EUR 34.26 on 2026-09-28 (po:4500014459-10): the price has not risen.
- `index:LCI-C` (0.31) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.18) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).
- `po:sup:70120:part:310031` (0.50) Our orders of Impeller HN 250 with you were placed at EUR 54.42 on 2024-09-30 (po:4500011477-20), EUR 54.42 on 2025-05-30 (po:4500012521-20), EUR 54.42 on 2026-01-27 (po:4500013483-10) and EUR 54.42 on 2026-09-28 (po:4500014459-20): the price has been unchanged.

## Gießerei Wimbacher GmbH (sup:70130)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked -0.27 % on average, settled -2.37 %
- quality 2026Q3: OTD 82.4 %, 651 ppm, green
- part:310011: floor 180.19 (should_cost, +-5%)
- part:310012: floor 370.21 (should_cost, +-5%)

Notes:
- 2026-03-22 Owner of Gießerei Wimbacher GmbH seeks a successor (news:20260322-05)
- 2026-03-21 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260321-70130-M5)
- 2026-03-22 Customer portfolio: The sales director of Gießerei Wimbacher GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260322-70130-M6)
- 2026-06-02 Supplier visit: Visit at Gießerei Wimbacher GmbH: half the shop floor was idle, two shifts are on short hours, and the MD spoke mostly about cash and the banks. (doc:20260602-70130-M4)
- 2026-06-07 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260607-70130-M2)
- 2026-08-02 Liquidity: Call with the managing director of Gießerei Wimbacher GmbH: he asked twice whether we could pay earlier and said the bank is watching every month. 'I cannot sign anything that lowers our margin now.' (doc:20260802-70130-M1)
- 2026-09-11 Customer portfolio: The sales director of Gießerei Wimbacher GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260911-70130-M3)

Claims:
- `ppm:sup:70130` (0.65) Your quality was 651 ppm defective parts in the four quarters to 2026Q3 (sc:70130@2026Q3).
- `po:sup:70130:part:310011` (0.65) Our orders of Volute casing HN 65-250 with you were placed at EUR 183.22 on 2024-09-30 (po:4500011478-10), EUR 183.00 on 2025-05-16 (po:4500012459-10), EUR 180.52 on 2026-01-14 (po:4500013430-10) and EUR 180.52 on 2026-09-16 (po:4500014418-10): the price has not risen.
- `otd:sup:70130` (0.63) Your on-time delivery was 82.4% in the four quarters to 2026Q3 (sc:70130@2026Q3).
- `index:LCI-C` (0.29) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.20) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).
- `po:sup:70130:part:310012` (0.65) Our orders of Volute casing HN 100-315 with you were placed at EUR 364.55 on 2024-10-01 (po:4500011490-10), EUR 364.10 on 2025-06-02 (po:4500012531-20), EUR 359.17 on 2026-01-19 (po:4500013440-10) and EUR 359.17 on 2026-09-17 (po:4500014419-10): the price has not risen.

## Odlewnia Kalwisz Sp. z o.o. (sup:70140)

- PL, private; **cash_short_jobshop**, approval flat; cash pressure 0.6 (rate 18%)
  - cash: Odlewnia Kalwisz Sp. z o.o. restructures (news:20260911-28)
  - override: MD: 'the bank is watching every month', asked twice to pay earlier, won't sign anything that lowers margin (doc:20260715-70140-M1); asks for payment in 10 days (doc:20260710-70140-M2); restructures (news:20260911-28); red scorecard (sc:70140@2026Q3)
- history: 8 renewals, asked -0.18 % on average, settled -2.37 %
- quality 2026Q3: OTD 63.5 %, 2376 ppm, red
- part:310010: floor 105.75 (should_cost_country+observed_bias, +-10%)
- part:310020: floor 43.90 (observed_best, +-3%)
- part:310030: floor 28.69 (should_cost_country+observed_bias, +-10%)

Notes:
- 2026-09-11 Odlewnia Kalwisz Sp. z o.o. restructures (news:20260911-28)
- 2026-07-10 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260710-70140-M2)
- 2026-07-15 Liquidity: Call with the managing director of Odlewnia Kalwisz Sp. z o.o.: he asked twice whether we could pay earlier and said the bank is watching every month. 'I cannot sign anything that lowers our margin now.' (doc:20260715-70140-M1)

Claims:
- `otd:sup:70140` (1.00) Your on-time delivery was 63.5% in the four quarters to 2026Q3 (sc:70140@2026Q3).
- `ppm:sup:70140` (1.00) Your quality was 2376 ppm defective parts in the four quarters to 2026Q3 (sc:70140@2026Q3).
- `index:LCI-C` (0.30) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.12) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).
- `po:sup:70140:part:310020` (0.75) Our orders of Bearing bracket HN with you were placed at EUR 46.33 on 2024-10-18 (po:4500011561-10), EUR 46.33 on 2025-06-20 (po:4500012598-10), EUR 45.15 on 2026-01-19 (po:4500013441-20) and EUR 45.15 on 2026-09-21 (po:4500014429-10): the price has not risen.
- `po:sup:70140:part:310030` (0.50) Our orders of Impeller HN 200 with you were placed at EUR 30.14 on 2024-10-04 (po:4500011494-10), EUR 30.14 on 2025-06-20 (po:4500012598-20), EUR 30.14 on 2026-01-20 (po:4500013457-10) and EUR 30.14 on 2026-09-21 (po:4500014429-20): the price has been unchanged.

## Tarsevi Döküm Sanayi A.Ş. (sup:70150)

- TR, family; **family_foundry**, approval flat; cash pressure 0.3 (rate 13%)
  - cash: Tarsevi Döküm Sanayi A.Ş. restructures (news:20260809-22)
- history: 4 renewals, asked 1.0 % on average, settled -2.13 %
- quality 2026Q3: OTD 52.0 %, 2652 ppm, red
- part:310060: floor 29.87 (should_cost_country, +-12%)

Notes:
- 2026-08-09 Tarsevi Döküm Sanayi A.Ş. restructures (news:20260809-22)
- 2026-04-14 Capacity: Call with sales at Tarsevi Döküm Sanayi A.Ş.: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260414-70150-M5)
- 2026-04-18 Price discussion: Call with the owner of Tarsevi Döküm Sanayi A.Ş.: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260418-70150-M2)
- 2026-04-19 Capacity: Call with sales at Tarsevi Döküm Sanayi A.Ş.: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260419-70150-M3)
- 2026-06-10 Supplier visit: Visit at Tarsevi Döküm Sanayi A.Ş.: half the shop floor was idle, two shifts are on short hours, and the MD spoke mostly about cash and the banks. (doc:20260610-70150-M1)
- 2026-08-04 Liquidity: Call with the managing director of Tarsevi Döküm Sanayi A.Ş.: he asked twice whether we could pay earlier and said the bank is watching every month. 'I cannot sign anything that lowers our margin now.' (doc:20260804-70150-M4)
- 2026-09-05 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260905-70150-M6)

Claims:
- `otd:sup:70150` (1.00) Your on-time delivery was 52.0% in the four quarters to 2026Q3 (sc:70150@2026Q3).
- `ppm:sup:70150` (1.00) Your quality was 2652 ppm defective parts in the four quarters to 2026Q3 (sc:70150@2026Q3).
- `po:sup:70150:part:310060` (0.69) Our orders of Pump housing HB 40 with you were placed at EUR 32.87 on 2024-10-07 (po:4500011509-10), EUR 32.87 on 2025-06-10 (po:4500012564-20), EUR 32.87 on 2026-01-27 (po:4500013484-10) and EUR 32.24 on 2026-09-23 (po:4500014450-10): the price has not risen.
- `index:LCI-C` (0.29) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.12) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).

## Meridune Precision Castings Co., Ltd. (sup:70160)

- CN, private; **family_foundry**, approval flat; cash pressure 0.25 (rate 12%)
  - override: privately owned, flat decisions; asks for payment in 10 days against a cash discount (doc:20260701-70160-M1); has accepted below full cost to keep volume (negotiation_history)
- history: 4 renewals, asked -0.9 % on average, settled -2.57 %
- quality 2026Q3: OTD 84.0 %, 0 ppm, green
- part:310051: floor 84.97 (should_cost, +-5%)

Notes:
- 2026-07-01 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260701-70160-M1)

Claims:
- `po:sup:70160:part:310051` (0.76) Our orders of Impeller HI 250 with you were placed at EUR 81.60 on 2024-10-04 (po:4500011495-10), EUR 81.34 on 2025-06-25 (po:4500012619-10), EUR 79.44 on 2026-01-30 (po:4500013502-10) and EUR 79.44 on 2026-09-21 (po:4500014430-10): the price has not risen.
- `otd:sup:70160` (0.55) Your on-time delivery was 84.0% in the four quarters to 2026Q3 (sc:70160@2026Q3).
- `index:LCI-C` (0.27) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.18) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).
- `ppm:sup:70160` (0.00) Your quality was 0 ppm defective parts in the four quarters to 2026Q3 (sc:70160@2026Q3).

## Slévárna Vrbenský s.r.o. (sup:70170)

- CZ, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked -0.23 % on average, settled -2.53 %
- quality 2026Q3: OTD 91.7 %, 5682 ppm, red
- part:310050: floor 559.61 (own_price, +-15%)

Notes:
- 2026-04-20 Slévárna Vrbenský s.r.o. opens a new moulding line (news:20260420-09)
- 2026-02-10 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260210-70170-M1)
- 2026-05-12 Supplier day: At our supplier day Slévárna Vrbenský s.r.o. said Hollerau is an important reference customer for them. (doc:20260512-70170-M2)

Claims:
- `ppm:sup:70170` (1.00) Your quality was 5682 ppm defective parts in the four quarters to 2026Q3 (sc:70170@2026Q3).
- `po:sup:70170:part:310050` (0.67) Our orders of Volute casing HI 80-250 with you were placed at EUR 569.40 on 2024-10-04 (po:4500011496-10), EUR 569.40 on 2025-05-20 (po:4500012476-10), EUR 559.61 on 2026-01-19 (po:4500013443-10) and EUR 559.61 on 2026-09-21 (po:4500014431-10): the price has not risen.
- `index:LCI-C` (0.24) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `otd:sup:70170` (0.17) Your on-time delivery was 91.7% in the four quarters to 2026Q3 (sc:70170@2026Q3).
- `index:PPI-D351` (0.12) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).

## Feinguss Allgäu-Reiter GmbH (sup:70180)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked -0.27 % on average, settled -2.53 %
- quality 2026Q3: OTD 73.1 %, 526 ppm, amber
- part:310050: floor 654.52 (own_price, +-15%)
- part:310051: floor 84.97 (should_cost_country, +-10%)

Notes:
- 2026-09-24 Visit by the owner: Visit by the owner of Feinguss Allgäu-Reiter GmbH. He reminded us that in 2022 they kept supplying at the old price for a quarter and said he expects partnership in return. (doc:20260924-70180-M1)

Claims:
- `otd:sup:70180` (1.00) Your on-time delivery was 73.1% in the four quarters to 2026Q3 (sc:70180@2026Q3).
- `po:sup:70180:part:310050` (0.71) Our orders of Volute casing HI 80-250 with you were placed at EUR 668.32 on 2024-10-15 (po:4500011554-10), EUR 668.32 on 2025-05-30 (po:4500012523-10), EUR 654.52 on 2026-01-27 (po:4500013485-10) and EUR 654.52 on 2026-09-29 (po:4500014470-10): the price has not risen.
- `ppm:sup:70180` (0.53) Your quality was 526 ppm defective parts in the four quarters to 2026Q3 (sc:70180@2026Q3).
- `index:LCI-C` (0.24) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.12) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).
- `po:sup:70180:part:310051` (0.80) Our orders of Impeller HI 250 with you were placed at EUR 122.45 on 2024-10-15 (po:4500011554-20), EUR 122.45 on 2025-06-30 (po:4500012633-20), EUR 118.73 on 2026-01-28 (po:4500013494-10) and EUR 118.73 on 2026-09-28 (po:4500014460-10): the price has not risen.

## Gießerei Pfaffenreuth GmbH (sup:70190)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked 0.5 % on average, settled -1.87 %
- quality 2026Q3: OTD 85.1 %, 715 ppm, amber
- part:310011: floor 180.19 (should_cost_country, +-10%)
- part:310020: floor 45.15 (market_price, +-15%)
- part:310030: floor 35.98 (should_cost_country, +-10%)
- part:310040: floor 33.93 (should_cost, +-5%)
- part:310060: floor 39.82 (should_cost_country, +-12%)

Notes:
- 2026-04-26 Gießerei Pfaffenreuth GmbH secures power prices (news:20260426-10)
- 2026-06-23 Material purchasing: Call with Gießerei Pfaffenreuth GmbH: they bought their electricity forward until December 2028 and said the market price is 'not our reality' before then. (doc:20260623-70190-M1)

Claims:
- `ppm:sup:70190` (0.71) Your quality was 715 ppm defective parts in the four quarters to 2026Q3 (sc:70190@2026Q3).
- `otd:sup:70190` (0.49) Your on-time delivery was 85.1% in the four quarters to 2026Q3 (sc:70190@2026Q3).
- `index:LCI-C` (0.29) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.20) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).
- `po:sup:70190:part:310040` (0.75) Our orders of Casing cover HB with you were placed at EUR 34.82 on 2024-10-07 (po:4500011511-10), EUR 34.82 on 2025-05-19 (po:4500012463-10), EUR 33.94 on 2026-01-19 (po:4500013444-10) and EUR 33.94 on 2026-09-07 (po:4500014376-10): the price has not risen.
- `po:sup:70190:part:310060` (0.50) Our orders of Pump housing HB 40 with you were placed at EUR 43.39 on 2024-10-04 (po:4500011497-10), EUR 43.39 on 2025-05-22 (po:4500012488-10), EUR 43.39 on 2026-01-20 (po:4500013458-10) and EUR 43.39 on 2026-09-03 (po:4500014361-10): the price has been unchanged.

## Zerspanung Dralveck GmbH (sup:70210)

- DE, founder; **family_foundry**, approval flat; cash pressure 0.25 (rate 36%)
  - cash: complains about our overdue invoices (doc:20260504-70210-P)
  - cash: offers a cash discount
- history: 8 renewals, asked 0.52 % on average, settled -1.58 %
- quality 2026Q3: OTD 80.8 %, 1863 ppm, amber
- part:320010: floor 25.22 (should_cost_country, +-10%)
- part:320011: floor 32.75 (market_price, +-15%)
- part:320080: floor 41.24 (own_price, +-15%)

Notes:
- 2024-05-14 Zerspanung Dralveck becomes a GmbH (news:20240514-00)
- wrote about overdue invoices (doc:20260504-70210-P)
- 2026-07-22 Capacity: Call with sales at Zerspanung Dralveck GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260722-70210-M2)
- 2026-09-08 Visit by the owner: The owner of Zerspanung Dralveck GmbH admitted he had not followed his material and energy prices closely since the 2022 peak; his office manager does the costing. (doc:20260908-70210-M1)
- 2026-09-10 Supplier day: At our supplier day Zerspanung Dralveck GmbH said Hollerau is an important reference customer for them. (doc:20260910-70210-M3)

Claims:
- `ppm:sup:70210` (1.00) Your quality was 1863 ppm defective parts in the four quarters to 2026Q3 (sc:70210@2026Q3).
- `po:sup:70210:part:320010` (0.80) Our orders of Pump shaft HN 24 mm with you were placed at EUR 26.31 on 2024-10-04 (po:4500011498-10), EUR 25.13 on 2025-05-16 (po:4500012460-10), EUR 24.37 on 2026-01-20 (po:4500013459-10) and EUR 24.37 on 2026-09-03 (po:4500014362-10): the price has not risen.
- `otd:sup:70210` (0.71) Your on-time delivery was 80.8% in the four quarters to 2026Q3 (sc:70210@2026Q3).
- `index:LCI-C` (0.31) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.02) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).
- `po:sup:70210:part:320080` (0.50) Our orders of Lantern (motor stool) HN with you were placed at EUR 41.63 on 2024-10-04 (po:4500011498-20), EUR 41.63 on 2025-06-02 (po:4500012532-10), EUR 41.63 on 2026-01-19 (po:4500013445-10) and EUR 41.63 on 2026-09-17 (po:4500014420-10): the price has been unchanged.

## CNC-Technik Obermaier & Huber GmbH (sup:70220)

- DE, founder; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 2.07 % on average, settled -1.37 %
- quality 2026Q3: OTD 56.0 %, 731 ppm, amber
- part:320030: floor 15.40 (should_cost, +-5%)

Notes:
- 2026-03-20 CNC-Technik Obermaier & Huber GmbH fully booked into next year (news:20260320-04)
- 2026-02-24 Supplier day: At our supplier day CNC-Technik Obermaier & Huber GmbH said Hollerau is an important reference customer for them. (doc:20260224-70220-M2)
- 2026-05-11 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260511-70220-M1)

Claims:
- `otd:sup:70220` (1.00) Your on-time delivery was 56.0% in the four quarters to 2026Q3 (sc:70220@2026Q3).
- `ppm:sup:70220` (0.73) Your quality was 731 ppm defective parts in the four quarters to 2026Q3 (sc:70220@2026Q3).
- `po:sup:70220:part:320030` (0.50) Our orders of Flange DN 65 PN 16, machined with you were placed at EUR 16.02 on 2024-09-30 (po:4500011479-10), EUR 16.02 on 2025-05-28 (po:4500012517-10), EUR 16.02 on 2026-01-13 (po:4500013427-10) and EUR 16.02 on 2026-09-10 (po:4500014399-10): the price has been unchanged.
- `index:LCI-C` (0.31) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.04) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).

## Präzisionsteile Lindlbauer KG (sup:70230)

- DE, family; **family_foundry**, approval flat; cash pressure 0.25 (rate 45%)
  - cash: complains about our overdue invoices (doc:20260812-70230-P)
  - cash: offers a cash discount
- history: 12 renewals, asked 1.66 % on average, settled -1.22 %
- quality 2026Q3: OTD 82.1 %, 544 ppm, green
- part:320020: floor 11.95 (own_price, +-15%)
- part:320031: floor 25.10 (own_price, +-15%)
- part:320060: floor 16.15 (own_price, +-15%)

Notes:
- wrote about overdue invoices (doc:20260812-70230-P)
- 2026-07-24 Visit by the owner: The owner of Präzisionsteile Lindlbauer KG admitted he had not followed his material and energy prices closely since the 2022 peak; his office manager does the costing. (doc:20260724-70230-M1)
- 2026-08-09 Price discussion: Call with the owner of Präzisionsteile Lindlbauer KG: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260809-70230-M3)
- 2026-09-12 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260912-70230-M2)

Claims:
- `notice:sup:70230` (1.00) Your letter of 27 September 2026 (doc:20260927-70230-P13) gives 35 days' notice, while our contract (ctr:4600070230) requires 90 days.
- `otd:sup:70230` (0.65) Your on-time delivery was 82.1% in the four quarters to 2026Q3 (sc:70230@2026Q3).
- `ppm:sup:70230` (0.54) Your quality was 544 ppm defective parts in the four quarters to 2026Q3 (sc:70230@2026Q3).
- `po:sup:70230:part:320020` (0.50) Our orders of Shaft sleeve with you were placed at EUR 12.06 on 2024-10-07 (po:4500011512-10), EUR 12.06 on 2025-06-04 (po:4500012549-10), EUR 12.06 on 2026-01-16 (po:4500013435-10) and EUR 12.06 on 2026-09-21 (po:4500014432-10): the price has been unchanged.
- `index:LCI-C` (0.42) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.08) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:AS-14404` (0.04) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `po:sup:70230:part:320031` (0.50) Our orders of Flange DN 100 PN 16, machined with you were placed at EUR 25.34 on 2024-10-02 (po:4500011491-10), EUR 25.34 on 2025-05-20 (po:4500012477-10), EUR 25.34 on 2026-01-20 (po:4500013460-10) and EUR 25.34 on 2026-09-21 (po:4500014432-20): the price has been unchanged.

## Strojírna Hrvelec s.r.o. (sup:70240)

- CZ, founder; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 1.57 % on average, settled -1.03 %
- quality 2026Q3: OTD 62.5 %, 980 ppm, amber
- part:320030: floor 12.63 (should_cost_country, +-10%)
- part:320031: floor 19.72 (own_price, +-15%)

Notes:
- 2026-07-10 Strojírna Hrvelec s.r.o. fully booked into next year (news:20260710-18)
- 2026-09-24 New volumes: Order intake is very strong. We can confirm additional volumes only against a binding 12-month commitment. (doc:20260924-70240-M1)

Claims:
- `otd:sup:70240` (1.00) Your on-time delivery was 62.5% in the four quarters to 2026Q3 (sc:70240@2026Q3).
- `ppm:sup:70240` (0.98) Your quality was 980 ppm defective parts in the four quarters to 2026Q3 (sc:70240@2026Q3).
- `index:LCI-C` (0.31) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.04) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `po:sup:70240:part:320031` (0.80) Our orders of Flange DN 100 PN 16, machined with you were placed at EUR 20.53 on 2024-10-07 (po:4500011513-10), EUR 20.53 on 2025-06-06 (po:4500012561-10), EUR 19.90 on 2026-01-19 (po:4500013447-10) and EUR 19.90 on 2026-09-22 (po:4500014442-10): the price has not risen.

## Drehteile Fuchsreiter GmbH (sup:70250)

- DE, founder; **family_foundry**, approval flat; cash pressure 0.3 (rate 13%)
  - cash: equity ratio 19.6 %
  - cash: complains about our overdue invoices (doc:20260818-70250-P)
- history: 4 renewals, asked -1.13 % on average, settled -2.43 %
- quality 2026Q3: OTD 88.0 %, 318 ppm, green
- part:320060: floor 16.15 (market_price, +-15%)
- part:320090: floor 4.60 (own_price, +-15%)

Notes:
- 2026-03-09 Drehteile Fuchsreiter GmbH looks for new customers (news:20260309-03)
- wrote about overdue invoices (doc:20260818-70250-P)
- 2026-06-20 Capacity: Call with sales at Drehteile Fuchsreiter GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260620-70250-M3)
- 2026-07-23 Capacity: Call with sales at Drehteile Fuchsreiter GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260723-70250-M1)
- 2026-08-11 Supplier day: At our supplier day Drehteile Fuchsreiter GmbH said Hollerau is an important reference customer for them. (doc:20260811-70250-M2)
- 2026-09-04 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260904-70250-M4)

Claims:
- `otd:sup:70250` (0.35) Your on-time delivery was 88.0% in the four quarters to 2026Q3 (sc:70250@2026Q3).
- `index:LCI-C` (0.32) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `ppm:sup:70250` (0.32) Your quality was 318 ppm defective parts in the four quarters to 2026Q3 (sc:70250@2026Q3).
- `index:PPI-D351` (0.10) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `po:sup:70250:part:320090` (0.71) Our orders of Spacer sleeve with you were placed at EUR 4.74 on 2024-09-30 (po:4500011480-10), EUR 4.74 on 2025-05-20 (po:4500012478-10), EUR 4.64 on 2026-01-19 (po:4500013448-10) and EUR 4.64 on 2026-09-21 (po:4500014433-10): the price has not risen.
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).

## Mechanik Tauvelt GmbH (sup:70260)

- AT, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 1.43 % on average, settled -1.77 %
- quality 2026Q3: OTD 92.3 %, 0 ppm, green
- part:320012: floor 104.89 (own_price, +-15%)

Notes:
- 2026-02-12 Price discussion: Call with the owner of Mechanik Tauvelt GmbH: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260212-70260-M1)
- 2026-03-22 Visit by the owner: Visit by the owner of Mechanik Tauvelt GmbH. He reminded us that in 2022 they kept supplying at the old price for a quarter and said he expects partnership in return. (doc:20260322-70260-M4)
- 2026-05-22 Customer portfolio: The sales director of Mechanik Tauvelt GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260522-70260-M3)
- 2026-09-13 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260913-70260-M2)

Claims:
- `po:sup:70260:part:320012` (0.64) Our orders of Pump shaft HI duplex with you were placed at EUR 107.34 on 2024-10-14 (po:4500011543-10), EUR 106.98 on 2025-06-12 (po:4500012583-10), EUR 105.87 on 2026-01-28 (po:4500013495-10) and EUR 105.87 on 2026-09-30 (po:4500014472-10): the price has not risen.
- `index:LCI-C` (0.30) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `otd:sup:70260` (0.14) Your on-time delivery was 92.3% in the four quarters to 2026Q3 (sc:70260@2026Q3).
- `index:PPI-D351` (0.02) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).
- `ppm:sup:70260` (0.00) Your quality was 0 ppm defective parts in the four quarters to 2026Q3 (sc:70260@2026Q3).

## Obrábění Kraslin s.r.o. (sup:70270)

- CZ, founder; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 1.5 % on average, settled -0.9 %
- quality 2026Q3: OTD 84.6 %, 1531 ppm, amber
- part:320050: floor 15.73 (own_price, +-15%)

Notes:
- 2026-02-23 Customer portfolio: The sales director of Obrábění Kraslin s.r.o. said they are reviewing small accounts and will focus on customers with volume. (doc:20260223-70270-M2)
- 2026-03-18 Visit by the owner: Visit by the owner of Obrábění Kraslin s.r.o.. He reminded us that in 2022 they kept supplying at the old price for a quarter and said he expects partnership in return. (doc:20260318-70270-M3)
- 2026-08-09 Price discussion: Call with the owner of Obrábění Kraslin s.r.o.: he asked where we get our index figures from - he works from his own spreadsheet, last updated two years ago. (doc:20260809-70270-M1)

Claims:
- `ppm:sup:70270` (1.00) Your quality was 1531 ppm defective parts in the four quarters to 2026Q3 (sc:70270@2026Q3).
- `otd:sup:70270` (0.52) Your on-time delivery was 84.6% in the four quarters to 2026Q3 (sc:70270@2026Q3).
- `index:LCI-C` (0.34) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.06) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).

## Wälzhammer Präzision GmbH (sup:70280)

- DE, family; **cash_short_jobshop**, approval flat; cash pressure 1.0 (rate 54%)
  - cash: credit index 302
  - cash: credit index +72 in 12 months
  - cash: equity ratio 20.3 %
  - cash: Wälzhammer Präzision GmbH under pressure (news:20260725-20)
  - cash: Wälzhammer Präzision GmbH introduces short-time work (news:20260926-38)
  - cash: complains about our overdue invoices (doc:20260720-70280-P)
  - cash: offers a cash discount
- history: 4 renewals, asked 1.43 % on average, settled -1.63 %
- quality 2026Q3: OTD 88.9 %, 425 ppm, green
- part:320011: floor 32.75 (own_price, +-15%)

Notes:
- 2026-07-25 Wälzhammer Präzision GmbH under pressure (news:20260725-20)
- 2026-09-26 Wälzhammer Präzision GmbH introduces short-time work (news:20260926-38)
- wrote about overdue invoices (doc:20260720-70280-P)
- 2026-06-17 Price discussion: Call with the owner of Wälzhammer Präzision GmbH: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260617-70280-M3)
- 2026-06-19 Capacity: Call with sales at Wälzhammer Präzision GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260619-70280-M2)
- 2026-07-07 Liquidity: Call with the managing director of Wälzhammer Präzision GmbH: he asked twice whether we could pay earlier and said the bank is watching every month. 'I cannot sign anything that lowers our margin now.' (doc:20260707-70280-M1)

Claims:
- `po:sup:70280:part:320011` (0.80) Our orders of Pump shaft HN 32 mm with you were placed at EUR 34.07 on 2024-10-04 (po:4500011500-10), EUR 33.06 on 2025-05-19 (po:4500012468-10), EUR 33.06 on 2026-02-02 (po:4500013510-10) and EUR 33.06 on 2026-09-03 (po:4500014364-10): the price has not risen.
- `ppm:sup:70280` (0.42) Your quality was 425 ppm defective parts in the four quarters to 2026Q3 (sc:70280@2026Q3).
- `otd:sup:70280` (0.30) Your on-time delivery was 88.9% in the four quarters to 2026Q3 (sc:70280@2026Q3).
- `index:LCI-C` (0.29) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.10) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).

## Feinmechanik Rottaler GmbH (sup:70290)

- DE, founder; **family_foundry**, approval flat; cash pressure 0.15 (rate 10%)
  - cash: equity ratio 21.7 %
- history: 4 renewals, asked 0.8 % on average, settled -1.87 %
- quality 2026Q3: OTD 75.9 %, 921 ppm, amber
- part:320010: floor 25.22 (should_cost, +-5%)

Notes:
- 2026-03-23 Feinmechanik Rottaler GmbH wins large hydraulics contract (news:20260323-06)
- 2026-03-15 New volumes: Order intake is very strong. We can confirm additional volumes only against a binding 12-month commitment. (doc:20260315-70290-M1)
- 2026-05-01 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260501-70290-M2)
- 2026-06-19 New volumes: Order intake is very strong. We can confirm additional volumes only against a binding 12-month commitment. (doc:20260619-70290-M3)

Claims:
- `otd:sup:70290` (0.95) Your on-time delivery was 75.9% in the four quarters to 2026Q3 (sc:70290@2026Q3).
- `ppm:sup:70290` (0.92) Your quality was 921 ppm defective parts in the four quarters to 2026Q3 (sc:70290@2026Q3).
- `po:sup:70290:part:320010` (0.79) Our orders of Pump shaft HN 24 mm with you were placed at EUR 25.67 on 2024-09-30 (po:4500011481-10), EUR 25.67 on 2025-05-26 (po:4500012499-10), EUR 24.92 on 2026-01-26 (po:4500013474-10) and EUR 24.92 on 2026-09-28 (po:4500014461-10): the price has not risen.
- `index:LCI-C` (0.31) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.02) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).

## Drehzentrum Ilzauer GmbH (sup:70295)

- DE, founder; **family_foundry**, approval flat; cash pressure 0.15 (rate 10%)
  - cash: complains about our overdue invoices (doc:20260515-70295-P)
- history: 12 renewals, asked 2.53 % on average, settled -0.01 %
- quality 2026Q3: OTD 84.4 %, 1000 ppm, amber
- part:320020: floor 11.55 (own_price, +-15%)
- part:320040: floor 13.46 (own_price, +-15%)
- part:320090: floor 4.56 (own_price, +-15%)

Notes:
- 2026-05-14 Drehzentrum Ilzauer GmbH looks for new customers (news:20260514-12)
- wrote about overdue invoices (doc:20260515-70295-P)
- 2026-04-15 Supplier day: At our supplier day Drehzentrum Ilzauer GmbH said Hollerau is an important reference customer for them. (doc:20260415-70295-M6)
- 2026-04-19 Capacity: Call with sales at Drehzentrum Ilzauer GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260419-70295-M5)
- 2026-05-05 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260505-70295-M2)
- 2026-07-17 Visit by the owner: The owner of Drehzentrum Ilzauer GmbH admitted he had not followed his material and energy prices closely since the 2022 peak; his office manager does the costing. (doc:20260717-70295-M1)
- 2026-08-28 Supplier day: At our supplier day Drehzentrum Ilzauer GmbH said Hollerau is an important reference customer for them. (doc:20260828-70295-M3)
- 2026-09-09 Visit by the owner: The owner of Drehzentrum Ilzauer GmbH admitted he had not followed his material and energy prices closely since the 2022 peak; his office manager does the costing. (doc:20260909-70295-M4)

Claims:
- `ppm:sup:70295` (1.00) Your quality was 1000 ppm defective parts in the four quarters to 2026Q3 (sc:70295@2026Q3).
- `otd:sup:70295` (0.53) Your on-time delivery was 84.4% in the four quarters to 2026Q3 (sc:70295@2026Q3).
- `po:sup:70295:part:320020` (0.50) Our orders of Shaft sleeve with you were placed at EUR 11.66 on 2024-10-07 (po:4500011515-10), EUR 11.66 on 2025-06-05 (po:4500012558-10), EUR 11.66 on 2026-01-16 (po:4500013437-10) and EUR 11.66 on 2026-09-21 (po:4500014434-10): the price has been unchanged.
- `index:LCI-C` (0.32) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.08) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).
- `index:CU-NOTATION` (0.00) The copper notation changed +47.7% from 2025-09 to 2026-09 (idx:CU-NOTATION@2025-09, idx:CU-NOTATION@2026-09).
- `po:sup:70295:part:320090` (0.67) Our orders of Spacer sleeve with you were placed at EUR 4.68 on 2024-10-04 (po:4500011501-10), EUR 4.60 on 2025-06-03 (po:4500012543-20), EUR 4.60 on 2026-01-20 (po:4500013461-10) and EUR 4.60 on 2026-09-21 (po:4500014434-30): the price has not risen.

## Blechtechnik Aichbauer GmbH (sup:70310)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 1.2 % on average, settled -2.0 %
- quality 2026Q3: OTD 63.0 %, 4118 ppm, red
- part:330010: floor 99.21 (own_price, +-15%)

Notes:
- 2026-09-11 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260911-70310-M1)

Claims:
- `otd:sup:70310` (1.00) Your on-time delivery was 63.0% in the four quarters to 2026Q3 (sc:70310@2026Q3).
- `ppm:sup:70310` (1.00) Your quality was 4118 ppm defective parts in the four quarters to 2026Q3 (sc:70310@2026Q3).
- `po:sup:70310:part:330010` (0.50) Our orders of Base frame HN 50/65, welded, painted with you were placed at EUR 100.14 on 2024-10-10 (po:4500011532-10), EUR 100.14 on 2025-06-10 (po:4500012566-10), EUR 100.14 on 2026-01-27 (po:4500013487-10) and EUR 100.14 on 2026-09-25 (po:4500014457-10): the price has been unchanged.
- `index:LCI-C` (0.27) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.12) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).

## Stahlbau Ganghofer-Lenz GmbH (sup:70320)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked -0.5 % on average, settled -2.83 %
- quality 2026Q3: OTD 88.0 %, 949 ppm, green
- part:330011: floor 179.61 (own_price, +-15%)

Notes:
- 2026-06-07 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260607-70320-M1)

Claims:
- `ppm:sup:70320` (0.95) Your quality was 949 ppm defective parts in the four quarters to 2026Q3 (sc:70320@2026Q3).
- `po:sup:70320:part:330011` (0.69) Our orders of Base frame HN 100, welded, painted with you were placed at EUR 184.72 on 2024-10-17 (po:4500011558-10), EUR 184.72 on 2025-06-04 (po:4500012550-10), EUR 181.29 on 2026-02-02 (po:4500013512-10) and EUR 181.29 on 2026-09-17 (po:4500014422-10): the price has not risen.
- `otd:sup:70320` (0.35) Your on-time delivery was 88.0% in the four quarters to 2026Q3 (sc:70320@2026Q3).
- `index:LCI-C` (0.25) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.06) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).

## Lasertechnik Varnoszeg Kft. (sup:70330)

- HU, private; **cash_short_jobshop**, approval flat; cash pressure 0.5 (rate 16%)
  - override: second shift on hold since spring, could take additional parts at short notice (doc:20260206-70330-M1); asks for payment in 10 days against a cash discount (doc:20260316-70330-M2)
- history: 4 renewals, asked 0.3 % on average, settled -3.33 %
- quality 2026Q3: OTD 70.8 %, 1879 ppm, amber
- part:330040: floor 118.00 (own_price, +-15%)

Notes:
- 2026-02-06 Capacity: Call with sales at Lasertechnik Varnoszeg Kft.: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260206-70330-M1)
- 2026-03-16 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260316-70330-M2)

Claims:
- `otd:sup:70330` (1.00) Your on-time delivery was 70.8% in the four quarters to 2026Q3 (sc:70330@2026Q3).
- `ppm:sup:70330` (1.00) Your quality was 1879 ppm defective parts in the four quarters to 2026Q3 (sc:70330@2026Q3).
- `po:sup:70330:part:330040` (0.75) Our orders of Control cabinet housing HI with you were placed at EUR 122.14 on 2024-10-14 (po:4500011544-10), EUR 122.14 on 2025-06-10 (po:4500012567-10), EUR 119.11 on 2026-01-28 (po:4500013496-10) and EUR 119.11 on 2026-09-28 (po:4500014462-10): the price has not risen.
- `index:LCI-C` (0.27) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:AS-14301` (0.00) The alloy surcharge for stainless grade 304 changed +8.6% from 2025-09 to 2026-09 (idx:AS-14301@2025-09, idx:AS-14301@2026-09).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).

## Metallbau Steinfelder KG (sup:70340)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked -0.12 % on average, settled -2.65 %
- quality 2026Q3: OTD 88.5 %, 489 ppm, green
- part:330020: floor 17.99 (own_price, +-15%)
- part:330030: floor 15.48 (own_price, +-15%)

Notes:
- 2026-04-18 Supplier day: At our supplier day Metallbau Steinfelder KG said Hollerau is an important reference customer for them. (doc:20260418-70340-M3)
- 2026-07-21 Price discussion: Call with the owner of Metallbau Steinfelder KG: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260721-70340-M2)
- 2026-07-28 Price discussion: Call with the owner of Metallbau Steinfelder KG: he asked where we get our index figures from - he works from his own spreadsheet, last updated two years ago. (doc:20260728-70340-M1)

Claims:
- `po:sup:70340:part:330020` (0.73) Our orders of Coupling guard, galvanised with you were placed at EUR 18.59 on 2024-10-14 (po:4500011545-10), EUR 18.39 on 2025-06-10 (po:4500012568-10), EUR 18.16 on 2026-02-04 (po:4500013531-10) and EUR 18.16 on 2026-09-24 (po:4500014452-10): the price has not risen.
- `ppm:sup:70340` (0.49) Your quality was 489 ppm defective parts in the four quarters to 2026Q3 (sc:70340@2026Q3).
- `otd:sup:70340` (0.33) Your on-time delivery was 88.5% in the four quarters to 2026Q3 (sc:70340@2026Q3).
- `index:LCI-C` (0.29) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.02) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).
- `po:sup:70340:part:330030` (0.50) Our orders of Motor bracket HB with you were placed at EUR 15.63 on 2024-10-14 (po:4500011545-20), EUR 15.63 on 2025-06-10 (po:4500012568-20), EUR 15.63 on 2026-01-26 (po:4500013475-10) and EUR 15.63 on 2026-09-24 (po:4500014452-20): the price has been unchanged.

## Oberflächentechnik Weißacher GmbH (sup:70350)

- DE, founder; **cash_short_jobshop**, approval flat; cash pressure 1.0 (rate 36%)
  - cash: credit index 343
  - cash: credit index +95 in 12 months
  - cash: Credit agency lowers rating of Oberflächentechnik Weißacher GmbH (news:20260904-26)
  - cash: complains about our overdue invoices (doc:20260820-70350-P)
  - cash: offers a cash discount
- history: 4 renewals, asked 0.7 % on average, settled -2.0 %
- quality 2026Q3: OTD 53.8 %, 5556 ppm, red
- part:330060: floor 9.90 (own_price, +-15%)

Notes:
- 2026-09-04 Credit agency lowers rating of Oberflächentechnik Weißacher GmbH (news:20260904-26)
- wrote about overdue invoices (doc:20260820-70350-P)
- 2026-08-21 Payment of invoices: Could you pay our invoices within 10 days? In return we would grant a cash discount. (doc:20260821-70350-M2)
- 2026-09-12 Liquidity: Call with the managing director of Oberflächentechnik Weißacher GmbH: he asked twice whether we could pay earlier and said the bank is watching every month. 'I cannot sign anything that lowers our margin now.' (doc:20260912-70350-M1)

Claims:
- `otd:sup:70350` (1.00) Your on-time delivery was 53.8% in the four quarters to 2026Q3 (sc:70350@2026Q3).
- `ppm:sup:70350` (1.00) Your quality was 5556 ppm defective parts in the four quarters to 2026Q3 (sc:70350@2026Q3).
- `po:sup:70350:part:330060` (0.50) Our orders of Cover plate set, powder coated with you were placed at EUR 9.99 on 2024-09-30 (po:4500011482-10), EUR 9.99 on 2025-06-02 (po:4500012534-10), EUR 9.99 on 2026-01-19 (po:4500013450-10) and EUR 9.99 on 2026-09-18 (po:4500014424-10): the price has been unchanged.
- `index:LCI-C` (0.32) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.14) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).

## Kantteile Strasser GmbH (sup:70360)

- AT, founder; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 1.4 % on average, settled -2.0 %
- quality 2026Q3: OTD 76.0 %, 762 ppm, amber
- part:330020: floor 17.99 (market_price, +-15%)
- part:330030: floor 15.96 (own_price, +-15%)

Notes:
- 2026-05-27 Capacity: Call with sales at Kantteile Strasser GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260527-70360-M2)
- 2026-06-06 Price discussion: Call with the owner of Kantteile Strasser GmbH: he asked where we get our index figures from - he works from his own spreadsheet, last updated two years ago. (doc:20260606-70360-M1)
- 2026-08-12 Supplier day: At our supplier day Kantteile Strasser GmbH said Hollerau is an important reference customer for them. (doc:20260812-70360-M3)

Claims:
- `otd:sup:70360` (0.95) Your on-time delivery was 76.0% in the four quarters to 2026Q3 (sc:70360@2026Q3).
- `ppm:sup:70360` (0.76) Your quality was 762 ppm defective parts in the four quarters to 2026Q3 (sc:70360@2026Q3).
- `index:LCI-C` (0.29) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-D351` (0.02) German electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).
- `po:sup:70360:part:330030` (0.50) Our orders of Motor bracket HB with you were placed at EUR 16.11 on 2024-10-07 (po:4500011516-10), EUR 16.11 on 2025-06-05 (po:4500012559-10), EUR 16.11 on 2026-01-20 (po:4500013462-10) and EUR 16.11 on 2026-09-21 (po:4500014435-20): the price has been unchanged.

## Dichtungswerk Ravensteiner GmbH (sup:70410)

- DE, group; **near_monopolist**, approval ladder; cash pressure 0.0 (rate 8%)
- history: 12 renewals, asked 3.18 % on average, settled 1.01 %
- quality 2026Q3: OTD 79.5 %, 270 ppm, green
- part:340010: floor 28.09 (observed_best, +-3%)
- part:340011: floor 39.95 (should_cost_country+observed_bias, +-10%)
- part:340030: floor 2.20 (own_price+observed_bias, +-15%)

Notes:
- 2026-08-22 Dichtungswerk Ravensteiner GmbH allocates volumes (news:20260822-23)
- 2026-03-10 Annual review: Annual review with Dichtungswerk Ravensteiner GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260310-70410-M1)
- 2026-03-27 New volumes: Order intake is very strong. We can confirm additional volumes only against a binding 12-month commitment. (doc:20260327-70410-M2)

Claims:
- `otd:sup:70410` (0.78) Your on-time delivery was 79.5% in the four quarters to 2026Q3 (sc:70410@2026Q3).
- `po:sup:70410:part:340010` (0.50) Our orders of Mechanical seal 24 mm, SiC/carbon, EPDM with you were placed at EUR 29.89 on 2024-10-07 (po:4500011517-10), EUR 29.89 on 2025-05-19 (po:4500012472-10), EUR 29.89 on 2026-01-19 (po:4500013451-10) and EUR 29.89 on 2026-09-21 (po:4500014436-10): the price has been unchanged.
- `ppm:sup:70410` (0.27) Your quality was 270 ppm defective parts in the four quarters to 2026Q3 (sc:70410@2026Q3).
- `index:LCI-C` (0.26) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-C2219` (0.06) German producer prices for rubber products changed +3.9% from 2025-08 to 2026-08 (idx:PPI-C2219@2025-08, idx:PPI-C2219@2026-08).

## Gleitring-Systeme Kaltenbrunn AG (sup:70420)

- CH, group; **near_monopolist**, approval ladder; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 2.27 % on average, settled 0.0 %
- quality 2026Q3: OTD 95.8 %, 0 ppm, green
- part:340012: floor 273.72 (should_cost, +-5%)

Notes:
- 2026-09-12 Gleitring-Systeme Kaltenbrunn AG extends drinking-water approvals (news:20260912-29)
- 2026-03-02 Annual review: Annual review with Gleitring-Systeme Kaltenbrunn AG. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260302-70420-M2)
- 2026-08-23 Annual review: Annual review with Gleitring-Systeme Kaltenbrunn AG. Their sales director said there is no room on price this year: head office has frozen all price reductions until December 2027. He was open on payment terms and ... (doc:20260823-70420-M1)

Claims:
- `po:sup:70420:part:340012` (0.50) Our orders of Cartridge seal HI 45 mm, ATEX, drinking-water approved with you were placed at EUR 319.11 on 2024-10-08 (po:4500011526-10), EUR 319.11 on 2025-06-23 (po:4500012609-10), EUR 319.11 on 2026-01-20 (po:4500013463-10) and EUR 319.11 on 2026-09-23 (po:4500014451-10): the price has been unchanged.
- `index:LCI-C` (0.29) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-C2219` (0.05) German producer prices for rubber products changed +3.9% from 2025-08 to 2026-08 (idx:PPI-C2219@2025-08, idx:PPI-C2219@2026-08).
- `otd:sup:70420` (0.00) Your on-time delivery was 95.8% in the four quarters to 2026Q3 (sc:70420@2026Q3).
- `ppm:sup:70420` (0.00) Your quality was 0 ppm defective parts in the four quarters to 2026Q3 (sc:70420@2026Q3).

## Elasto-Dicht Hermannsdorfer GmbH (sup:70430)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked 2.8 % on average, settled 0.83 %
- quality 2026Q3: OTD 91.8 %, 291 ppm, green
- part:340020: floor 56.11 (own_price, +-15%)
- part:340030: floor 1.91 (market_price, +-15%)
- part:340040: floor 86.62 (own_price, +-15%)

Notes:
- 2026-03-26 Price discussion: Call with the owner of Elasto-Dicht Hermannsdorfer GmbH: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260326-70430-M2)
- 2026-05-15 Customer portfolio: The sales director of Elasto-Dicht Hermannsdorfer GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260515-70430-M1)

Claims:
- `po:sup:70430:part:340020` (0.50) Our orders of O-ring set EPDM, drinking-water approved with you were placed at EUR 63.87 per 100 units on 2024-10-10 (po:4500011533-10), EUR 63.87 per 100 units on 2025-06-10 (po:4500012569-10), EUR 65.41 per 100 units on 2026-01-26 (po:4500013476-10) and EUR 63.87 per 100 units on 2026-09-24 (po:4500014453-10): the price has not risen.
- `ppm:sup:70430` (0.29) Your quality was 291 ppm defective parts in the four quarters to 2026Q3 (sc:70430@2026Q3).
- `index:PPI-C2219` (0.22) German producer prices for rubber products changed +3.9% from 2025-08 to 2026-08 (idx:PPI-C2219@2025-08, idx:PPI-C2219@2026-08).
- `otd:sup:70430` (0.16) Your on-time delivery was 91.8% in the four quarters to 2026Q3 (sc:70430@2026Q3).
- `index:LCI-C` (0.13) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).

## Kohlering-Technik Pirkheim GmbH (sup:70440)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked 3.18 % on average, settled 0.65 %
- quality 2026Q3: OTD 75.5 %, 387 ppm, green
- part:340011: floor 34.74 (should_cost, +-5%)
- part:340040: floor 95.80 (own_price, +-15%)

Notes:
- 2026-08-27 Kohlering-Technik Pirkheim GmbH allocates volumes (news:20260827-25)
- 2026-05-24 Annual review: Annual review with Kohlering-Technik Pirkheim GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260524-70440-M2)
- 2026-09-10 Commercial terms: Kohlering-Technik Pirkheim GmbH stated that standard items are not discounted; only multi-year volume agreements change prices. (doc:20260910-70440-M1)

Claims:
- `otd:sup:70440` (0.97) Your on-time delivery was 75.5% in the four quarters to 2026Q3 (sc:70440@2026Q3).
- `ppm:sup:70440` (0.39) Your quality was 387 ppm defective parts in the four quarters to 2026Q3 (sc:70440@2026Q3).
- `index:LCI-C` (0.31) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-C2219` (0.07) German producer prices for rubber products changed +3.9% from 2025-08 to 2026-08 (idx:PPI-C2219@2025-08, idx:PPI-C2219@2026-08).

## Antriebstechnik Nordmark AG (sup:70510)

- DE, group; **group_ladder**, approval ladder; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked 2.35 % on average, settled -0.0 %
- quality 2026Q3: OTD 90.4 %, 273 ppm, green
- part:350010: floor 238.35 (should_cost+observed_bias, +-5%)
- part:350011: floor 365.68 (observed_best, +-3%)
- part:350012: floor 576.59 (should_cost_country+observed_bias, +-10%)
- part:350013: floor 1529.15 (should_cost_country+observed_bias, +-10%)

Notes:
- 2026-02-27 Annual review: Annual review with Antriebstechnik Nordmark AG. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260227-70510-M2)
- 2026-04-10 Annual review: Annual review with Antriebstechnik Nordmark AG. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260410-70510-M1)

Claims:
- `ppm:sup:70510` (0.27) Your quality was 273 ppm defective parts in the four quarters to 2026Q3 (sc:70510@2026Q3).
- `otd:sup:70510` (0.23) Your on-time delivery was 90.4% in the four quarters to 2026Q3 (sc:70510@2026Q3).
- `index:LCI-C` (0.22) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:CU-NOTATION` (0.00) The copper notation changed +47.7% from 2025-09 to 2026-09 (idx:CU-NOTATION@2025-09, idx:CU-NOTATION@2026-09).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).

## Vesmo Elektromotory a.s. (sup:70520)

- CZ, group; **group_ladder**, approval ladder; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked 2.27 % on average, settled -0.0 %
- quality 2026Q3: OTD 81.1 %, 764 ppm, green
- part:350010: floor 221.47 (should_cost, +-5%)
- part:350012: floor 591.20 (should_cost, +-5%)

Notes:
- 2026-02-18 Annual review: Annual review with Vesmo Elektromotory a.s.. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260218-70520-M3)
- 2026-04-13 Customer portfolio: The sales director of Vesmo Elektromotory a.s. said they are reviewing small accounts and will focus on customers with volume. (doc:20260413-70520-M2)
- 2026-04-26 Annual review: Annual review with Vesmo Elektromotory a.s.. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260426-70520-M5)
- 2026-06-20 Material costs: Dear Sir or Madam, for your information: our copper requirement is covered at fixed prices until March 2027. Market movements reach our costs only after that. Yours faithfully, Vesmo Elektromotory a.s. (doc:20260620-70520-M1)
- 2026-07-01 Material purchasing: Call with Vesmo Elektromotory a.s.: they bought their copper forward until March 2027 and said the market price is 'not our reality' before then. (doc:20260701-70520-M4)

Claims:
- `ppm:sup:70520` (0.76) Your quality was 764 ppm defective parts in the four quarters to 2026Q3 (sc:70520@2026Q3).
- `otd:sup:70520` (0.69) Your on-time delivery was 81.1% in the four quarters to 2026Q3 (sc:70520@2026Q3).
- `index:LCI-C` (0.18) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:CU-NOTATION` (0.00) The copper notation changed +47.7% from 2025-09 to 2026-09 (idx:CU-NOTATION@2025-09, idx:CU-NOTATION@2026-09).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).

## Selvbrunn Drive Systems GmbH (sup:70530)

- DE, group; **group_ladder**, approval ladder; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 2.1 % on average, settled -0.13 %
- quality 2026Q3: OTD 84.6 %, 0 ppm, green
- part:350020: floor 426.53 (observed_best, +-3%)
- part:350021: floor 733.00 (should_cost_country+observed_bias, +-10%)

Notes:
- 2026-08-26 Annual review: Annual review with Selvbrunn Drive Systems GmbH. Their sales director said there is no room on price this year: head office has frozen all price reductions until December 2027. He was open on payment terms and call-off ... (doc:20260826-70530-M1)
- 2026-09-09 Annual review: Annual review with Selvbrunn Drive Systems GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260909-70530-M2)

Claims:
- `po:sup:70530:part:350020` (0.55) Our orders of Frequency converter 7.5 kW, IP55 with you were placed at EUR 414.61 on 2024-10-14 (po:4500011548-10), EUR 400.19 on 2025-06-30 (po:4500012634-10), EUR 412.74 on 2026-01-27 (po:4500013491-10) and EUR 412.74 on 2026-09-28 (po:4500014465-10): the price has not risen.
- `otd:sup:70530` (0.52) Your on-time delivery was 84.6% in the four quarters to 2026Q3 (sc:70530@2026Q3).
- `index:LCI-C` (0.13) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-C2611` (0.00) German producer prices for electronic components changed +13.5% from 2025-08 to 2026-08 (idx:PPI-C2611@2025-08, idx:PPI-C2611@2026-08).
- `index:CU-NOTATION` (0.00) The copper notation changed +47.7% from 2025-09 to 2026-09 (idx:CU-NOTATION@2025-09, idx:CU-NOTATION@2026-09).
- `ppm:sup:70530` (0.00) Your quality was 0 ppm defective parts in the four quarters to 2026Q3 (sc:70530@2026Q3).

## Konvertek Antriebselektronik GmbH (sup:70540)

- AT, group; **group_ladder**, approval ladder; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 2.33 % on average, settled 0.0 %
- quality 2026Q3: OTD 81.5 %, 0 ppm, green
- part:350020: floor 423.37 (should_cost_country, +-10%)
- part:350021: floor 692.92 (should_cost, +-5%)

Notes:
- 2026-03-02 Konvertek Antriebselektronik GmbH warns of longer delivery times (news:20260302-01)
- 2026-02-23 Customer portfolio: The sales director of Konvertek Antriebselektronik GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260223-70540-M2)
- 2026-07-11 Annual review: Annual review with Konvertek Antriebselektronik GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260711-70540-M3)
- 2026-09-06 Price list 2027: Our price list applies to all customers without exception until June 2027. We are happy to discuss logistics and payment conditions. (doc:20260906-70540-M1)

Claims:
- `otd:sup:70540` (0.68) Your on-time delivery was 81.5% in the four quarters to 2026Q3 (sc:70540@2026Q3).
- `index:LCI-C` (0.13) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-C2611` (0.00) German producer prices for electronic components changed +13.5% from 2025-08 to 2026-08 (idx:PPI-C2611@2025-08, idx:PPI-C2611@2026-08).
- `index:CU-NOTATION` (0.00) The copper notation changed +47.7% from 2025-09 to 2026-09 (idx:CU-NOTATION@2025-09, idx:CU-NOTATION@2026-09).
- `ppm:sup:70540` (0.00) Your quality was 0 ppm defective parts in the four quarters to 2026Q3 (sc:70540@2026Q3).
- `po:sup:70540:part:350021` (0.50) Our orders of Frequency converter 15 kW, IP55 with you were placed at EUR 684.92 on 2024-10-04 (po:4500011502-10), EUR 684.92 on 2025-05-26 (po:4500012504-20), EUR 684.92 on 2026-02-02 (po:4500013516-10) and EUR 684.92 on 2026-09-25 (po:4500014458-10): the price has been unchanged.

## Platinenwerk Lausitz GmbH (sup:70550)

- DE, private; **near_monopolist**, approval flat; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 0.93 % on average, settled -1.13 %
- quality 2026Q3: OTD 85.7 %, 701 ppm, green
- part:350030: floor 37.24 (should_cost, +-5%)

Notes:
- 2026-04-17 Annual review: Annual review with Platinenwerk Lausitz GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260417-70550-M1)

Claims:
- `ppm:sup:70550` (0.70) Your quality was 701 ppm defective parts in the four quarters to 2026Q3 (sc:70550@2026Q3).
- `po:sup:70550:part:350030` (0.66) Our orders of Control board HB smart pump (PCBA) with you were placed at EUR 34.90 on 2024-10-04 (po:4500011503-10), EUR 34.21 on 2025-05-22 (po:4500012492-10), EUR 34.35 on 2026-01-19 (po:4500013453-10) and EUR 34.35 on 2026-09-07 (po:4500014387-10): the price has not risen.
- `otd:sup:70550` (0.47) Your on-time delivery was 85.7% in the four quarters to 2026Q3 (sc:70550@2026Q3).
- `index:LCI-C` (0.27) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-C2611` (0.00) German producer prices for electronic components changed +13.5% from 2025-08 to 2026-08 (idx:PPI-C2611@2025-08, idx:PPI-C2611@2026-08).

## Kabelwerk Rhönsberg GmbH (sup:70560)

- DE, group; **near_monopolist**, approval ladder; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 4.47 % on average, settled 2.2 %
- quality 2026Q3: OTD 88.5 %, 111 ppm, green
- part:350040: floor 304.49 (should_cost, +-5%)

Notes:
- 2026-04-15 Annual review: Annual review with Kabelwerk Rhönsberg GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260415-70560-M2)
- 2026-06-17 Material purchasing: Call with Kabelwerk Rhönsberg GmbH: they bought their copper forward until March 2027 and said the market price is 'not our reality' before then. (doc:20260617-70560-M1)

Claims:
- `otd:sup:70560` (0.33) Your on-time delivery was 88.5% in the four quarters to 2026Q3 (sc:70560@2026Q3).
- `ppm:sup:70560` (0.11) Your quality was 111 ppm defective parts in the four quarters to 2026Q3 (sc:70560@2026Q3).
- `index:LCI-C` (0.10) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:CU-NOTATION` (0.00) The copper notation changed +47.7% from 2025-09 to 2026-09 (idx:CU-NOTATION@2025-09, idx:CU-NOTATION@2026-09).

## Sensorik Ammertal GmbH (sup:70570)

- DE, private; **group_ladder**, approval ladder; cash pressure 0.0 (rate 8%)
  - override: price changes above 2 % need the pricing committee, meets every two weeks (doc:20260314-70570-M2); head office froze price reductions until Dec 2027, open on payment terms and call-off flexibility (doc:20260927-70570-M1); acquired by an investor (news)
- history: 4 renewals, asked 2.87 % on average, settled 0.43 %
- quality 2026Q3: OTD 88.0 %, 271 ppm, green
- part:350050: floor 22.47 (should_cost, +-5%)

Notes:
- 2026-06-22 Sensorik Ammertal GmbH acquired by an investor (news:20260622-16)
- 2026-03-14 Annual review: Annual review with Sensorik Ammertal GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260314-70570-M2)
- 2026-09-27 Annual review: Annual review with Sensorik Ammertal GmbH. Their sales director said there is no room on price this year: head office has frozen all price reductions until December 2027. He was open on payment terms and call-off ... (doc:20260927-70570-M1)

Claims:
- `otd:sup:70570` (0.35) Your on-time delivery was 88.0% in the four quarters to 2026Q3 (sc:70570@2026Q3).
- `ppm:sup:70570` (0.27) Your quality was 271 ppm defective parts in the four quarters to 2026Q3 (sc:70570@2026Q3).
- `index:LCI-C` (0.26) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:PPI-C2611` (0.00) German producer prices for electronic components changed +13.5% from 2025-08 to 2026-08 (idx:PPI-C2611@2025-08, idx:PPI-C2611@2026-08).

## Motorenwerk Saalach GmbH (sup:70580)

- DE, group; **group_ladder**, approval ladder; cash pressure 0.15 (rate 10%)
  - cash: complains about our overdue invoices (doc:20260612-70580-P)
- history: 4 renewals, asked 3.2 % on average, settled 0.07 %
- quality 2026Q3: OTD 95.8 %, 0 ppm, green
- part:350011: floor 374.95 (should_cost_country, +-10%)
- part:350013: floor 1567.90 (should_cost, +-5%)

Notes:
- 2026-03-27 Motorenwerk Saalach GmbH sharpens its focus (news:20260327-07)
- wrote about overdue invoices (doc:20260612-70580-P)
- 2026-03-22 Annual review: Annual review with Motorenwerk Saalach GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260322-70580-M2)
- 2026-09-08 Customer portfolio: The sales director of Motorenwerk Saalach GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260908-70580-M3)
- 2026-09-26 Account review: Their new sales director said Hollerau's volumes are 'not strategic' for Motorenwerk Saalach GmbH any more; replies have become slower since the summer. (doc:20260926-70580-M1)

Claims:
- `index:LCI-C` (0.20) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:CU-NOTATION` (0.00) The copper notation changed +47.7% from 2025-09 to 2026-09 (idx:CU-NOTATION@2025-09, idx:CU-NOTATION@2026-09).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).
- `otd:sup:70580` (0.00) Your on-time delivery was 95.8% in the four quarters to 2026Q3 (sc:70580@2026Q3).
- `ppm:sup:70580` (0.00) Your quality was 0 ppm defective parts in the four quarters to 2026Q3 (sc:70580@2026Q3).

## Schraubenhandel Leitner & Sohn GmbH (sup:70610)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 12 renewals, asked 2.47 % on average, settled 0.17 %
- quality 2026Q3: OTD 88.6 %, 68 ppm, green
- part:360010: floor 12.34 (own_price, +-15%)
- part:360012: floor 4.86 (own_price, +-15%)
- part:360030: floor 12.66 (own_price, +-15%)

Notes:
- 2026-04-01 Capacity: Call with sales at Schraubenhandel Leitner & Sohn GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260401-70610-M2)
- 2026-05-13 Annual review: Annual review with Schraubenhandel Leitner & Sohn GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260513-70610-M1)
- 2026-05-14 Capacity: Call with sales at Schraubenhandel Leitner & Sohn GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260514-70610-M3)

Claims:
- `index:PPI-C2594` (0.67) German producer prices for fasteners changed +1.7% from 2025-08 to 2026-08 (idx:PPI-C2594@2025-08, idx:PPI-C2594@2026-08).
- `po:sup:70610:part:360010` (0.50) Our orders of Hex bolt ISO 4017 M12x40 8.8, zinc with you were placed at EUR 12.46 per 100 units on 2024-09-30 (po:4500011486-10), EUR 12.46 per 100 units on 2025-05-26 (po:4500012506-10), EUR 12.46 per 100 units on 2026-01-26 (po:4500013479-10) and EUR 12.46 per 100 units on 2026-09-30 (po:4500014475-10): the price has been unchanged.
- `otd:sup:70610` (0.32) Your on-time delivery was 88.6% in the four quarters to 2026Q3 (sc:70610@2026Q3).
- `index:LCI-C` (0.07) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `ppm:sup:70610` (0.07) Your quality was 68 ppm defective parts in the four quarters to 2026Q3 (sc:70610@2026Q3).
- `po:sup:70610:part:360012` (0.50) Our orders of Hex nut ISO 4032 M12 8, zinc with you were placed at EUR 4.91 per 100 units on 2024-09-30 (po:4500011486-20), EUR 4.91 per 100 units on 2025-06-02 (po:4500012538-10), EUR 4.91 per 100 units on 2026-01-30 (po:4500013504-10) and EUR 4.91 per 100 units on 2026-09-28 (po:4500014466-10): the price has been unchanged.
- `po:sup:70610:part:360030` (0.50) Our orders of Washer ISO 7089 M12, zinc with you were placed at EUR 12.78 per 1,000 units on 2024-10-10 (po:4500011536-10), EUR 12.78 per 1,000 units on 2025-06-11 (po:4500012581-10), EUR 12.78 per 1,000 units on 2026-01-29 (po:4500013501-10) and EUR 12.78 per 1,000 units on 2026-09-28 (po:4500014466-20): the price has been unchanged.

## Wälzlager-Zentrum Süd GmbH (sup:70620)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 12 renewals, asked 4.13 % on average, settled 1.78 %
- quality 2026Q3: OTD 85.0 %, 302 ppm, green
- part:360020: floor 4.90 (observed_best, +-3%)
- part:360021: floor 8.07 (own_price+observed_bias, +-15%)
- part:360022: floor 25.44 (own_price+observed_bias, +-15%)

Notes:
- 2026-06-19 Wälzlager-Zentrum Süd GmbH sharpens its focus (news:20260619-15)
- 2026-04-27 Customer portfolio: The sales director of Wälzlager-Zentrum Süd GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260427-70620-M5)
- 2026-05-01 Customer portfolio: The sales director of Wälzlager-Zentrum Süd GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260501-70620-M3)
- 2026-06-16 Price discussion: Call with the owner of Wälzlager-Zentrum Süd GmbH: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260616-70620-M6)
- 2026-06-27 Commercial terms: Wälzlager-Zentrum Süd GmbH stated that standard items are not discounted; only multi-year volume agreements change prices. (doc:20260627-70620-M2)
- 2026-07-06 Range changes: We are reorganising our range around our key accounts. Standard items will be supplied from stock at list conditions; individual agreements will not be extended. (doc:20260706-70620-M1)
- 2026-09-17 Account review: Their new sales director said Hollerau's volumes are 'not strategic' for Wälzlager-Zentrum Süd GmbH any more; replies have become slower since the summer. (doc:20260917-70620-M4)

Claims:
- `index:PPI-C2815` (0.83) German producer prices for bearings and gears changed +0.8% from 2025-08 to 2026-08 (idx:PPI-C2815@2025-08, idx:PPI-C2815@2026-08).
- `otd:sup:70620` (0.50) Your on-time delivery was 85.0% in the four quarters to 2026Q3 (sc:70620@2026Q3).
- `ppm:sup:70620` (0.30) Your quality was 302 ppm defective parts in the four quarters to 2026Q3 (sc:70620@2026Q3).
- `index:LCI-C` (0.08) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).

## Normteile Brucker KG (sup:70630)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked -0.08 % on average, settled -2.15 %
- quality 2026Q3: OTD 88.0 %, 257 ppm, green
- part:360013: floor 28.96 (own_price, +-15%)
- part:360030: floor 12.52 (own_price, +-15%)

Notes:
- 2026-03-27 Commercial terms: Normteile Brucker KG stated that standard items are not discounted; only multi-year volume agreements change prices. (doc:20260327-70630-M2)
- 2026-07-06 Price list 2027: Our price list applies to all customers without exception until December 2027. We are happy to discuss logistics and payment conditions. (doc:20260706-70630-M3)
- 2026-07-24 Annual review: Annual review with Normteile Brucker KG. Their sales director said there is no room on price this year: head office has frozen all price reductions until December 2027. He was open on payment terms and call-off ... (doc:20260724-70630-M1)
- 2026-09-23 Annual review: Annual review with Normteile Brucker KG. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260923-70630-M4)

Claims:
- `po:sup:70630:part:360013` (0.80) Our orders of Stud bolt M10 A2-70 with you were placed at EUR 31.24 per 100 units on 2024-10-14 (po:4500011551-10), EUR 30.38 per 100 units on 2025-06-10 (po:4500012575-10), EUR 29.23 per 100 units on 2026-01-28 (po:4500013497-10) and EUR 29.23 per 100 units on 2026-09-28 (po:4500014468-10): the price has not risen.
- `index:PPI-C2594` (0.43) German producer prices for fasteners changed +1.7% from 2025-08 to 2026-08 (idx:PPI-C2594@2025-08, idx:PPI-C2594@2026-08).
- `otd:sup:70630` (0.35) Your on-time delivery was 88.0% in the four quarters to 2026Q3 (sc:70630@2026Q3).
- `ppm:sup:70630` (0.26) Your quality was 257 ppm defective parts in the four quarters to 2026Q3 (sc:70630@2026Q3).
- `index:LCI-C` (0.09) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:AS-14301` (0.00) The alloy surcharge for stainless grade 304 changed +8.6% from 2025-09 to 2026-09 (idx:AS-14301@2025-09, idx:AS-14301@2026-09).
- `po:sup:70630:part:360030` (0.50) Our orders of Washer ISO 7089 M12, zinc with you were placed at EUR 12.64 per 1,000 units on 2024-10-07 (po:4500011521-10), EUR 12.64 per 1,000 units on 2025-06-10 (po:4500012575-20), EUR 12.64 per 1,000 units on 2026-01-23 (po:4500013470-10) and EUR 12.64 per 1,000 units on 2026-09-28 (po:4500014468-20): the price has been unchanged.

## Kugellager-Vertrieb Inntal GmbH (sup:70640)

- AT, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked 3.88 % on average, settled 1.53 %
- quality 2026Q3: OTD 86.5 %, 0 ppm, green
- part:360020: floor 4.16 (own_price, +-15%)
- part:360021: floor 7.14 (own_price, +-15%)

Notes:
- 2026-02-01 Capacity: Call with sales at Kugellager-Vertrieb Inntal GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260201-70640-M5)
- 2026-02-28 Annual review: Annual review with Kugellager-Vertrieb Inntal GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260228-70640-M3)
- 2026-05-12 Annual review: Annual review with Kugellager-Vertrieb Inntal GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260512-70640-M2)
- 2026-07-15 Capacity: Call with sales at Kugellager-Vertrieb Inntal GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260715-70640-M4)
- 2026-08-19 Customer portfolio: The sales director of Kugellager-Vertrieb Inntal GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260819-70640-M1)

Claims:
- `index:PPI-C2815` (0.83) German producer prices for bearings and gears changed +0.8% from 2025-08 to 2026-08 (idx:PPI-C2815@2025-08, idx:PPI-C2815@2026-08).
- `otd:sup:70640` (0.42) Your on-time delivery was 86.5% in the four quarters to 2026Q3 (sc:70640@2026Q3).
- `index:LCI-C` (0.08) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `ppm:sup:70640` (0.00) Your quality was 0 ppm defective parts in the four quarters to 2026Q3 (sc:70640@2026Q3).

## Verbindungstechnik Mairhofer GmbH (sup:70650)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 12 renewals, asked 2.53 % on average, settled -0.09 %
- quality 2026Q3: OTD 84.1 %, 296 ppm, green
- part:360010: floor 14.39 (own_price, +-15%)
- part:360011: floor 37.29 (own_price, +-15%)
- part:360012: floor 5.55 (own_price, +-15%)

Notes:
- 2026-08-03 Verbindungstechnik Mairhofer GmbH sharpens its focus (news:20260803-21)
- 2026-02-19 Customer portfolio: The sales director of Verbindungstechnik Mairhofer GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260219-70650-M6)
- 2026-03-27 Annual review: Annual review with Verbindungstechnik Mairhofer GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260327-70650-M3)
- 2026-04-11 Capacity: Call with sales at Verbindungstechnik Mairhofer GmbH: they could take additional parts at short notice; the second shift has been on hold since spring. (doc:20260411-70650-M5)
- 2026-05-11 Customer portfolio: The sales director of Verbindungstechnik Mairhofer GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260511-70650-M2)
- 2026-06-02 Account review: Their new sales director said Hollerau's volumes are 'not strategic' for Verbindungstechnik Mairhofer GmbH any more; replies have become slower since the summer. (doc:20260602-70650-M4)
- 2026-08-17 Range changes: We are reorganising our range around our key accounts. Standard items will be supplied from stock at list conditions; individual agreements will not be extended. (doc:20260817-70650-M1)

Claims:
- `index:PPI-C2594` (0.67) German producer prices for fasteners changed +1.7% from 2025-08 to 2026-08 (idx:PPI-C2594@2025-08, idx:PPI-C2594@2026-08).
- `otd:sup:70650` (0.55) Your on-time delivery was 84.1% in the four quarters to 2026Q3 (sc:70650@2026Q3).
- `po:sup:70650:part:360010` (0.50) Our orders of Hex bolt ISO 4017 M12x40 8.8, zinc with you were placed at EUR 14.52 per 100 units on 2024-10-09 (po:4500011530-10), EUR 14.52 per 100 units on 2025-06-10 (po:4500012577-10), EUR 14.52 per 100 units on 2026-01-23 (po:4500013471-10) and EUR 14.52 per 100 units on 2026-09-28 (po:4500014469-10): the price has been unchanged.
- `ppm:sup:70650` (0.30) Your quality was 296 ppm defective parts in the four quarters to 2026Q3 (sc:70650@2026Q3).
- `index:LCI-C` (0.07) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `po:sup:70650:part:360011` (0.54) Our orders of Hex bolt ISO 4017 M16x60 8.8, zinc with you were placed at EUR 37.81 per 100 units on 2024-10-08 (po:4500011529-10), EUR 37.81 per 100 units on 2025-06-10 (po:4500012577-20), EUR 37.64 per 100 units on 2026-01-28 (po:4500013498-10) and EUR 37.64 per 100 units on 2026-09-24 (po:4500014454-10): the price has not risen.
- `po:sup:70650:part:360012` (0.80) Our orders of Hex nut ISO 4032 M12 8, zinc with you were placed at EUR 5.78 per 100 units on 2024-09-30 (po:4500011488-10), EUR 5.78 per 100 units on 2025-05-30 (po:4500012530-10), EUR 5.60 per 100 units on 2026-01-27 (po:4500013493-10) and EUR 5.60 per 100 units on 2026-09-24 (po:4500014454-20): the price has not risen.

## Edelstahl-Service Donautal GmbH (sup:70710)

- DE, group; **group_ladder**, approval ladder; cash pressure 0.0 (rate 8%)
- history: 4 renewals, asked 0.7 % on average, settled -2.4 %
- quality 2026Q3: OTD 88.0 %, 75 ppm, green
- part:370010: floor 4.91 (observed_best, +-3%)
- part:370021: floor 3.65 (market_price+observed_bias, +-15%)

Notes:
- 2026-04-21 Price discussion: Call with the owner of Edelstahl-Service Donautal GmbH: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260421-70710-M2)
- 2026-07-06 Material costs: Dear Sir or Madam, for your information: our nickel and alloys requirement is covered at fixed prices until March 2027. Market movements reach our costs only after that. Yours faithfully, Edelstahl-Service Donautal GmbH (doc:20260706-70710-M1)

Claims:
- `po:sup:70710:part:370010` (0.50) Our orders of Round bar 1.4404 dia 30 mm, peeled with you were placed at EUR 5.45 on 2024-10-07 (po:4500011523-10), EUR 5.33 on 2025-06-05 (po:4500012560-10), EUR 5.24 on 2026-01-26 (po:4500013482-10) and EUR 5.45 on 2026-09-24 (po:4500014455-10): the price has not risen.
- `otd:sup:70710` (0.35) Your on-time delivery was 88.0% in the four quarters to 2026Q3 (sc:70710@2026Q3).
- `ppm:sup:70710` (0.07) Your quality was 75 ppm defective parts in the four quarters to 2026Q3 (sc:70710@2026Q3).
- `index:LCI-C` (0.03) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `index:AS-14301` (0.00) The alloy surcharge for stainless grade 304 changed +8.6% from 2025-09 to 2026-09 (idx:AS-14301@2025-09, idx:AS-14301@2026-09).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).

## Stahlhandel Rupprecht-Kessel GmbH (sup:70720)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 8 renewals, asked -2.95 % on average, settled -5.32 %
- quality 2026Q3: OTD 92.2 %, 44 ppm, green
- part:370012: floor 124.88 (own_price, +-15%)
- part:370020: floor 83.56 (own_price, +-15%)

Notes:
- 2026-04-09 Supplier day: At our supplier day Stahlhandel Rupprecht-Kessel GmbH said Hollerau is an important reference customer for them. (doc:20260409-70720-M4)
- 2026-04-15 Price discussion: Call with the owner of Stahlhandel Rupprecht-Kessel GmbH: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260415-70720-M2)
- 2026-07-12 Price discussion: Call with the owner of Stahlhandel Rupprecht-Kessel GmbH: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260712-70720-M3)
- 2026-09-24 Supplier day: At our supplier day Stahlhandel Rupprecht-Kessel GmbH said Hollerau is an important reference customer for them. (doc:20260924-70720-M1)

Claims:
- `po:sup:70720:part:370012` (0.73) Our orders of Round bar C45 dia 50 mm, cold drawn with you were placed at EUR 129.00 per 100 units on 2024-10-10 (po:4500011538-10), EUR 129.00 per 100 units on 2025-06-10 (po:4500012578-10), EUR 126.05 per 100 units on 2026-01-23 (po:4500013472-10) and EUR 126.05 per 100 units on 2026-09-24 (po:4500014456-10): the price has not risen.
- `otd:sup:70720` (0.14) Your on-time delivery was 92.2% in the four quarters to 2026Q3 (sc:70720@2026Q3).
- `index:LCI-C` (0.06) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `ppm:sup:70720` (0.04) Your quality was 44 ppm defective parts in the four quarters to 2026Q3 (sc:70720@2026Q3).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `po:sup:70720:part:370020` (0.80) Our orders of Sheet S235JR 3 mm, hot rolled, cut to size with you were placed at EUR 92.33 per 100 units on 2024-10-07 (po:4500011524-10), EUR 86.35 per 100 units on 2025-06-04 (po:4500012553-10), EUR 84.34 per 100 units on 2026-01-23 (po:4500013472-20) and EUR 84.34 per 100 units on 2026-09-22 (po:4500014448-10): the price has not risen.
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).

## Inox Center Ostalpen GmbH (sup:70730)

- AT, private; **group_ladder**, approval ladder; cash pressure 0.0 (rate 8%)
  - override: price changes above 2 % need the pricing committee (doc:20260308-70730-M2); bought nickel and alloys forward until Jan 2027, market price 'not our reality' (doc:20260727-70730-M1); owner offered to walk us through the calculation (doc:20260806-70730-M3)
- history: 4 renewals, asked -2.0 % on average, settled -4.3 %
- quality 2026Q3: OTD 96.0 %, 89 ppm, green
- part:370021: floor 4.01 (own_price, +-15%)

Notes:
- 2026-03-08 Annual review: Annual review with Inox Center Ostalpen GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260308-70730-M2)
- 2026-07-27 Material purchasing: Call with Inox Center Ostalpen GmbH: they bought their nickel and alloys forward until January 2027 and said the market price is 'not our reality' before then. (doc:20260727-70730-M1)
- 2026-08-06 Price discussion: Call with the owner of Inox Center Ostalpen GmbH: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260806-70730-M3)

Claims:
- `po:sup:70730:part:370021` (0.80) Our orders of Sheet 1.4301 2 mm, 2B, cut to size with you were placed at EUR 4.21 on 2024-10-04 (po:4500011505-10), EUR 4.11 on 2025-06-02 (po:4500012540-10), EUR 3.83 on 2026-01-19 (po:4500013455-10) and EUR 4.05 on 2026-09-21 (po:4500014440-10): the price has not risen.
- `ppm:sup:70730` (0.09) Your quality was 89 ppm defective parts in the four quarters to 2026Q3 (sc:70730@2026Q3).
- `index:LCI-C` (0.04) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:AS-14301` (0.00) The alloy surcharge for stainless grade 304 changed +8.6% from 2025-09 to 2026-09 (idx:AS-14301@2025-09, idx:AS-14301@2026-09).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).
- `otd:sup:70730` (0.00) Your on-time delivery was 96.0% in the four quarters to 2026Q3 (sc:70730@2026Q3).

## Blankstahl Werdenfels GmbH (sup:70740)

- DE, family; **family_foundry**, approval flat; cash pressure 0.0 (rate 8%)
- history: 12 renewals, asked -0.01 % on average, settled -2.87 %
- quality 2026Q3: OTD 81.0 %, 32 ppm, green
- part:370010: floor 4.55 (observed_best, +-3%)
- part:370011: floor 2.50 (own_price+observed_bias, +-15%)
- part:370012: floor 111.81 (own_price+observed_bias, +-15%)
- part:370020: floor 65.76 (market_price+observed_bias, +-15%)

Notes:
- 2026-05-14 Price discussion: Call with the owner of Blankstahl Werdenfels GmbH: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260514-70740-M6)
- 2026-06-01 Customer portfolio: The sales director of Blankstahl Werdenfels GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260601-70740-M4)
- 2026-08-12 Annual review: Annual review with Blankstahl Werdenfels GmbH. Their key account manager explained that price changes above 2 % need the approval of their pricing committee, which meets every two weeks. (doc:20260812-70740-M3)
- 2026-08-13 Customer portfolio: The sales director of Blankstahl Werdenfels GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260813-70740-M2)
- 2026-09-04 Price discussion: Call with the owner of Blankstahl Werdenfels GmbH: he offered to walk us through their calculation (hourly rates and material) if that helps to settle prices. (doc:20260904-70740-M1)
- 2026-09-16 Customer portfolio: The sales director of Blankstahl Werdenfels GmbH said they are reviewing small accounts and will focus on customers with volume. (doc:20260916-70740-M5)

Claims:
- `otd:sup:70740` (0.70) Your on-time delivery was 81.0% in the four quarters to 2026Q3 (sc:70740@2026Q3).
- `ppm:sup:70740` (0.03) Your quality was 32 ppm defective parts in the four quarters to 2026Q3 (sc:70740@2026Q3).
- `index:LCI-C` (0.03) German labour costs in manufacturing changed +2.7% from 2025-06 to 2026-06 (idx:LCI-C@2025-06, idx:LCI-C@2026-06).
- `index:AS-14404` (0.00) The alloy surcharge for stainless grade 316L changed +5.9% from 2025-09 to 2026-09 (idx:AS-14404@2025-09, idx:AS-14404@2026-09).
- `index:PPI-C2431` (0.00) German producer prices for cold-drawn bars changed +12.3% from 2025-08 to 2026-08 (idx:PPI-C2431@2025-08, idx:PPI-C2431@2026-08).
- `index:PPI-C241` (0.00) German producer prices for basic iron and steel changed +6.5% from 2025-08 to 2026-08 (idx:PPI-C241@2025-08, idx:PPI-C241@2026-08).
