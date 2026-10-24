"""Feature registry: the single description of every column the pipeline emits.

FEATURES.md is generated from this file (``python -m buyer.facts.features.build``) and a test
checks that the registry and the produced columns are identical.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    name: str
    dtype: str            # float | int | bool (0/1) | category | id | date
    group: str
    source: str           # table(s)
    columns: str          # source column(s)
    join: str             # join keys
    formula: str
    cutoff: str
    missing: str
    meaning: str


# Shared wording -------------------------------------------------------------------------------
ASOF = "as_of"
W12 = "trailing 365-day window [as_of - 364 d, as_of]"
PAIR = "supplier_id + part_id"
SUP = "supplier_id"
PART = "part_id"
STATIC = "time-invariant master data (no history in the database); used for every date"
NOSUP = "null when the supplier is unknown"
INCOMPLETE = "null when the 12-month window starts before the first PO line (2023-10-02), see po_window_complete"
HIST_CUT = "renewals with date <= as_of; training rows use as_of = negotiation date - 1 day"
LEVELS = "pair -> supplier -> category -> global: the first level with >= 1 prior renewal (hist_level)"

IDS = [
    Feature("event_id", "id", "id", "negotiation_history", "event_id", "-", "copied", "-", "never null",
            "Tracking key of the historical negotiation. Not a feature."),
    Feature("negotiation_date", "date", "id", "negotiation_history", "date", "-", "copied", "-", "never null",
            "Day the negotiation was settled. Not a feature."),
    Feature("as_of_date", "date", "id", "-", "-", "-", "negotiation_date - 1 day (training); requested date (current)",
            "-", "never null", "Information cutoff (end of day) of the row. Not a feature."),
    Feature("supplier_id", "id", "id", "negotiation_history / sourcing", "supplier_id", "-",
            "copied; sup:71999 is mapped to sup:70210 (KNOWN_ISSUES #5)", "-", "null for an unknown supplier",
            "Lookup key only. Never use as a predictor."),
    Feature("part_id", "id", "id", "negotiation_history / sourcing", "part_id", "-", "copied", "-", "never null",
            "Lookup key only. Never use as a predictor."),
]

TARGETS = [
    Feature("target_settled_pct", "float", "target", "negotiation_history", "settled_pct", "event_id",
            "settled_pct", "outcome of the row's own negotiation - target only", "never null (225 renewals)",
            "Agreed price change in %. NOT the supplier's minimum acceptable change: Hollerau may have "
            "stopped pushing early, so this is an upper bound on the supplier's walk-away point."),
    Feature("target_concession_pp", "float", "target", "negotiation_history", "asked_pct, settled_pct", "event_id",
            "asked_pct - settled_pct", "outcome - target only", "never null",
            "How far the supplier came down from its ask, in percentage points. A lower bound on what it "
            "could have conceded."),
    Feature("target_settled_unit_price", "float", "target", "price_conditions", "price", "event_id",
            "price of the price condition created by this event (per price_unit)", "outcome - target only",
            "never null", "Agreed price per price_unit, valid from the next 1 January. Same caveat as "
            "target_settled_pct."),
]

FEATURES = [
    # ---------------------------------------------------------------- flags
    Feature("is_known_supplier", "bool", "flags", "suppliers", "id", SUP, "1 if supplier_id is in the vendor master",
            STATIC, "never null", "0 = unseen supplier: every supplier-level feature is null or a fallback."),
    # ---------------------------------------------------------------- product / competition
    Feature("part_category", "category", "product", "parts", "category", PART, "copied", STATIC,
            "from current_conditions for an unknown part, else null", "Commodity category (castings, seals, ...)."),
    Feature("material_group", "category", "product", "parts", "material_group", PART, "copied", STATIC,
            "as part_category", "Material group (cast_iron, ...)."),
    Feature("net_weight_kg", "float", "product", "parts", "net_weight_kg", PART, "copied", STATIC,
            "as part_category", "Net weight per piece in kg."),
    Feature("price_unit", "int", "product", "parts", "price_unit", PART, "copied", STATIC, "as part_category",
            "Pieces (or kg/m) per price: 1, 100 or 1000. Every price feature is per this unit."),
    Feature("part_uom", "category", "product", "parts", "uom", PART, "copied", STATIC, "as part_category",
            "Unit of measure of quantities (pc, kg, m)."),
    Feature("part_abc_class", "category", "product", "parts", "abc_class", PART, "copied", STATIC,
            "null if unknown part",
            "ABC class of the part by spend."),
    Feature("supplier_country", "category", "product", "suppliers", "country", SUP, "copied", STATIC,
            "unknown supplier: current_conditions['supplier_country'], else null", "ISO country of the supplier."),
    Feature("approved_supplier_count", "int", "competition", "sourcing", "supplier_id, approved_since", PART,
            "count of source-list rows with approved_since <= as_of", "approved_since <= as_of",
            "null for an unknown part",
            "Suppliers on the source list. Assumes no supplier was ever removed (removals are not recorded)."),
    Feature("active_supplier_count", "int", "competition", "po_lines", "supplier_id, order_date", PART,
            "distinct suppliers with a PO line for the part in the window", W12,
            INCOMPLETE + "; null for an unknown part",
            "Suppliers currently delivering. Rebuilt from POs, not from sourcing.status (a snapshot); "
            "identical to status = 'active' at 2026-09-30 (tested)."),
    Feature("qualified_supplier_count", "int", "competition", "sourcing, po_lines", "supplier_id", PART,
            "approved suppliers not ordered from in the window", W12, "as active_supplier_count",
            "Qualified but idle second sources: the credible alternatives. "
            "Equals status = 'qualified' at the snapshot."),
    # ---------------------------------------------------------------- negotiation history
    Feature("hist_negotiation_count", "int", "history", "negotiation_history", "event_id", SUP,
            "count of the supplier's prior renewals (all parts)", HIST_CUT, "0 when none (also for unknown suppliers)",
            "How much negotiation history this supplier has."),
    Feature("hist_pair_count", "int", "history", "negotiation_history", "event_id", PAIR,
            "count of prior renewals of this supplier-part pair", HIST_CUT, "0 when none",
            "Reliability of the pair-level estimates."),
    Feature("hist_level", "category", "history", "negotiation_history", "-", "-", LEVELS, HIST_CUT,
            "'none' when no renewal at all precedes as_of",
            "Which aggregation level the hist_avg_* features come from."),
    Feature("hist_level_count", "int", "history", "negotiation_history", "-", "-",
            "number of renewals at hist_level", HIST_CUT, "0 when hist_level = 'none'",
            "Sample size behind hist_avg_* / hist_concession_std."),
    Feature("hist_is_fallback", "bool", "history", "negotiation_history", "-", "-", "1 if hist_level != 'pair'",
            HIST_CUT, "never null", "Missing-value indicator for pair-level history."),
    Feature("hist_avg_asked_pct", "float", "history", "negotiation_history", "asked_pct", PAIR,
            "mean asked_pct at hist_level", HIST_CUT, "null when hist_level = 'none'",
            "Typical opening ask of this supplier (or its peers)."),
    Feature("hist_avg_settled_pct", "float", "history", "negotiation_history", "settled_pct", PAIR,
            "mean settled_pct at hist_level", HIST_CUT, "null when hist_level = 'none'", "Typical agreed change."),
    Feature("hist_avg_concession_pp", "float", "history", "negotiation_history", "asked_pct, settled_pct", PAIR,
            "mean(asked_pct - settled_pct) at hist_level", HIST_CUT, "null when hist_level = 'none'",
            "Typical distance the supplier moved from its ask. sup:70110/part:310010 as of 2025-12-03: "
            "mean(3.4, 2.0, 3.5) = 2.97."),
    Feature("hist_concession_std", "float", "history", "negotiation_history", "asked_pct, settled_pct", PAIR,
            "sample standard deviation of concessions at hist_level", HIST_CUT, "null when hist_level_count < 2",
            "How predictable the supplier's concession is."),
    Feature("hist_weighted_concession_pp", "float", "history", "negotiation_history", "asked_pct, settled_pct, date",
            PAIR, "sum(w_i c_i) / sum(w_i), w_i = 0.5 ^ (days(as_of - date_i) / 365), at hist_level", HIST_CUT,
            "null when hist_level = 'none'", "Concession with recent negotiations weighted more (half-life 1 year)."),
    Feature("hist_last_concession_pp", "float", "history", "negotiation_history", "asked_pct, settled_pct", PAIR,
            "concession of the latest prior renewal: pair, else same supplier on another part", HIST_CUT,
            "null without own history (no category/global fallback)", "Most recent behaviour of this supplier."),
    Feature("hist_days_since_last", "int", "history", "negotiation_history", "date", PAIR,
            "as_of - date of that latest renewal (pair, else supplier)", HIST_CUT, "null without own history",
            "Time since we last negotiated with it."),
    Feature("hist_below_full_cost_note", "bool", "history", "negotiation_history", "note", PAIR,
            "1 if any prior event of the pair (incl. the initial price) has note 'accepted below full cost to keep "
            "the volume'", "events with date <= as_of; the row's own note is never used",
            "null when the pair has no prior event", "The supplier has sold this part below its full cost before."),
    Feature("supplier_avg_concession_pp", "float", "history", "negotiation_history", "asked_pct, settled_pct", SUP,
            "mean concession over the supplier's prior renewals, all parts", HIST_CUT, "null when none",
            "Supplier-level concession, independent of hist_level."),
    Feature("category_avg_concession_pp", "float", "history", "negotiation_history, parts", "asked_pct, settled_pct, "
            "category", "part_id -> parts.category",
            "mean concession over prior renewals of parts in the same category",
            HIST_CUT, "null when none", "Fallback for unseen suppliers; also a peer benchmark."),
    Feature("category_negotiation_count", "int", "history", "negotiation_history, parts", "event_id", "parts.category",
            "count of prior renewals in the category", HIST_CUT, "0 when none",
            "Reliability of category_avg_concession_pp."),
    Feature("global_avg_concession_pp", "float", "history", "negotiation_history", "asked_pct, settled_pct", "-",
            "mean concession over all prior renewals", HIST_CUT, "null before the first renewal (2023-11-12)",
            "Last-resort fallback / market-wide baseline."),
    Feature("global_negotiation_count", "int", "history", "negotiation_history", "event_id", "-",
            "count of all prior renewals", HIST_CUT, "0 when none", "Reliability of global_avg_concession_pp."),
    # ---------------------------------------------------------------- prices and purchasing
    Feature("previous_unit_price", "float", "price", "price_conditions", "price, valid_from", PAIR,
            "price of the pair's latest condition with valid_from <= as_of (per price_unit)",
            "valid_from <= as_of: the price in force, never the one this negotiation creates",
            "null when the pair has no price (unknown supplier, new pair)", "Price we pay today, per price_unit."),
    Feature("previous_price_per_uom", "float", "price", "price_conditions", "price, price_unit", PAIR,
            "previous_unit_price / price_unit", "as previous_unit_price", "as previous_unit_price",
            "Same price per single piece / kg / m, comparable across parts."),
    Feature("previous_price_basis", "category", "price", "price_conditions", "basis", PAIR,
            "basis of that condition: contract | renewal | index_adjustment", "as previous_unit_price",
            "as previous_unit_price", "How the price in force came about (index_adjustment = index clause part)."),
    Feature("price_change_last_pct", "float", "price", "price_conditions", "price", PAIR,
            "(price in force / price of the condition before it - 1) x 100", "as previous_unit_price",
            "null with fewer than 2 conditions", "Last price move of the pair."),
    Feature("part_ref_unit_price", "float", "price", "price_conditions", "price", PART,
            "mean over suppliers of each supplier's price in force for the part", "valid_from <= as_of",
            "null when the part has no price yet", "Incumbent price level of the part; use for unseen suppliers."),
    Feature("po_window_complete", "bool", "price", "po_lines", "order_date", "-",
            "1 if as_of - 364 d >= first PO order date (2023-10-02)", ASOF, "never null",
            "0 = PO/QN/invoice data covers less than 12 months (all 2023 renewals): 12-month sums are null."),
    Feature("po_12m_volume", "int", "price", "po_lines", "qty", PAIR, "sum(qty) in the window, in part_uom", W12,
            INCOMPLETE + "; " + NOSUP + "; 0 when known supplier ordered nothing",
            "Volume we bought from the supplier."),
    Feature("po_12m_spend", "float", "price", "po_lines", "qty, price, price_unit", PAIR,
            "sum(qty x price / price_unit) in EUR (KNOWN_ISSUES #4)", W12, "as po_12m_volume",
            "Spend with the supplier."),
    Feature("po_12m_order_count", "int", "price", "po_lines", "id", PAIR, "count of PO lines in the window", W12,
            "as po_12m_volume", "Ordering frequency."),
    Feature("po_12m_avg_unit_price", "float", "price", "po_lines", "qty, price, price_unit, price_note", PAIR,
            "sum(qty x price / price_unit) / sum(qty) x price_unit over lines without price_note = 'stale_condition'",
            W12, "null when no non-stale line in the window (partial windows allowed: it is an average)",
            "Volume-weighted price actually ordered, per price_unit. Stale conditions are outdated prices "
            "(KNOWN_ISSUES #6) and are excluded."),
    Feature("po_rush_order_share", "float", "price", "po_lines", "change_type", PAIR,
            "share of lines with change_type = 'rush'", W12, "null when no lines in the window",
            "How often we needed the supplier to rush - our dependency."),
    Feature("po_stale_condition_share", "float", "price", "po_lines", "price_note", PAIR,
            "share of lines with price_note = 'stale_condition'", W12, "null when no lines",
            "Purchase price variance indicator."),
    Feature("part_po_12m_volume", "int", "price", "po_lines", "qty", PART, "sum(qty) over all suppliers of the part",
            W12, INCOMPLETE, "Total consumption of the part over the last year."),
    Feature("forecast_12m_volume", "int", "price", "forecasts", "qty_next_12m, snapshot_month", PART,
            "qty_next_12m of the latest snapshot with snapshot_month <= last complete month at as_of",
            "a snapshot of month M is known from the last day of M", "null before 2023-12 (first snapshot)",
            "Forecast demand for the next 12 months (shared with suppliers)."),
    Feature("forecast_growth_pct", "float", "price", "forecasts, po_lines", "qty_next_12m, qty", PART,
            "(forecast_12m_volume / part_po_12m_volume - 1) x 100", "as both inputs",
            "null when either input is null or zero", "Expected volume growth vs. last year: more volume = leverage."),
    # ---------------------------------------------------------------- financials
    Feature("owner_type", "category", "financial", "supplier_intel", "owner_type", SUP, "copied", STATIC,
            NOSUP + " (current_conditions may fill it)", "family | founder | group | private."),
    Feature("group_parent", "category", "financial", "supplier_intel", "group_parent", SUP, "copied", STATIC,
            "null = no parent (or unknown supplier)", "Parent group name; sparse - prefer has_group_parent."),
    Feature("has_group_parent", "bool", "financial", "supplier_intel", "group_parent", SUP,
            "1 if group_parent is set", STATIC, NOSUP, "Belongs to a group (approval ladder, deeper pockets)."),
    Feature("supplier_age_years", "int", "financial", "supplier_intel", "founded", SUP,
            "year(as_of) - founded", STATIC, NOSUP, "Age of the company."),
    Feature("has_financials", "bool", "financial", "supplier_intel", "filed_fy", SUP,
            "1 if the filed accounts are public at as_of", "public from 31 Dec of filed_fy + 1 "
            "(FILING_LAG_MONTHS = 12), capped at the 2026-09-30 snapshot", "never null",
            "Missing-value indicator of the four filing features. 0 for every historical renewal: "
            "the only filings in the data (FY2024/FY2025) were not public before 2025-12-31."),
    Feature("turnover_eur", "int", "financial", "supplier_intel", "turnover_eur", SUP, "copied",
            "only when has_financials = 1", "null when not public, or the supplier files no P&L (KNOWN_ISSUES #13)",
            "Filed turnover in EUR."),
    Feature("turnover_band", "category", "financial", "supplier_intel", "turnover_band", SUP, "copied",
            "only when has_financials = 1", "null when not public", "Turnover band; always set for filers."),
    Feature("equity_ratio_pct", "float", "financial", "supplier_intel", "equity_ratio_pct", SUP, "copied",
            "only when has_financials = 1", "null when not public", "Equity ratio: low = thin cushion, cash pressure."),
    Feature("staff", "int", "financial", "supplier_intel", "staff", SUP, "copied", "only when has_financials = 1",
            "null when not public", "Headcount."),
    Feature("credit_index", "int", "financial", "supplier_intel", "credit_index, credit_index_12m_ago", SUP,
            "credit_index if as_of >= 2026-09-30; credit_index_12m_ago if as_of >= 2025-09-30",
            "each value is used only from the date it was measured", "null before 2025-09-30",
            "German-style credit index: higher = riskier."),
    Feature("credit_index_change", "int", "financial", "supplier_intel", "credit_index, credit_index_12m_ago", SUP,
            "credit_index - credit_index_12m_ago", "only from 2026-09-30", "null before the snapshot",
            "Credit trend: positive = deteriorating."),
    # ---------------------------------------------------------------- production cost
    Feature("has_should_cost", "bool", "cost", "should_cost", "estimate_date", PART,
            "1 if a should-cost estimate for the part exists at as_of", "estimate_date <= as_of (all are 2026-07-15)",
            "never null", "Missing-value indicator of the should-cost features. 0 for every historical renewal."),
    Feature("should_cost_supplier_specific", "bool", "cost", "should_cost", "supplier_id", PAIR,
            "1 if the estimate is for this supplier's plant, 0 if for another supplier of the part",
            "as has_should_cost", "null when has_should_cost = 0",
            "0 = estimate borrowed from another plant (larger error)."),
    Feature("estimated_unit_cost", "float", "cost", "should_cost", "unit_cost", PART,
            "unit_cost of the supplier's own row, else the lowest row of the part (per price_unit)",
            "as has_should_cost", "null when has_should_cost = 0",
            "Bottom-up cost without margin, German cost base, error 5-15 % (KNOWN_ISSUES #14)."),
    Feature("should_cost_confidence_pct", "int", "cost", "should_cost", "confidence_pct", PART, "copied",
            "as has_should_cost", "null when has_should_cost = 0", "Stated error of the estimate in %."),
    Feature("cost_to_price_ratio", "float", "cost", "should_cost, price_conditions", "unit_cost, price", PAIR,
            "estimated_unit_cost / previous_unit_price", "as both inputs", "null when either is null",
            "> 1: the price is below our cost estimate (little room); < 1: margin to negotiate."),
    Feature("material_cost_share", "float", "cost", "should_cost", "material_eur, unit_cost", PART,
            "material_eur / unit_cost", "as has_should_cost", "null when has_should_cost = 0",
            "Material share of cost."),
    Feature("conversion_cost_share", "float", "cost", "should_cost", "conversion_eur, unit_cost", PART,
            "conversion_eur / unit_cost", "as has_should_cost", "null when has_should_cost = 0",
            "Labour/machine share of cost."),
    Feature("overhead_cost_share", "float", "cost", "should_cost", "overhead_eur, unit_cost", PART,
            "overhead_eur / unit_cost", "as has_should_cost", "null when has_should_cost = 0",
            "Overhead share of cost."),
    Feature("primary_cost_driver", "category", "cost", "cost_drivers", "series_id, weight", PART,
            "series with the highest weight for the part",
            "weights are the category team's estimate of 2026-06, treated as a time-invariant part property",
            "null when the part has no drivers", "Main cost driver (e.g. LCI-C labour, PPI-C241 steel)."),
    Feature("market_index_change_12m", "float", "cost", "index_values, cost_drivers", "value", "series_id",
            "(v[L] / v[L-12] - 1) x 100 of primary_cost_driver, L = latest month published at as_of",
            "month M of a series with publication lag k (months behind 2026-09 at the snapshot) is known from "
            "the end of month M + k", "null when no value or no value 12 months earlier",
            "Year-on-year change of the main cost driver."),
    Feature("weighted_cost_driver_change", "float", "cost", "index_values, cost_drivers", "value, weight", PART,
            "sum(weight_i x change_12m_i) over the part's drivers with data; weights not renormalised",
            "as market_index_change_12m", "null when no driver has data",
            "Expected % change of the part's cost from market indices alone "
            "(the remaining weight is fixed cost/margin)."),
    Feature("cost_driver_weight_total", "float", "cost", "cost_drivers", "weight", PART, "sum(weight)",
            "as primary_cost_driver", "null when no drivers",
            "Indexed share of cost (scale of weighted_cost_driver_change)."),
    # ---------------------------------------------------------------- performance
    Feature("has_scorecard", "bool", "performance", "scorecards", "period_end", SUP,
            "1 if a scorecard with period_end <= as_of exists", "period_end <= as_of (first: 2024Q3)", "never null",
            "Missing-value indicator of the scorecard features."),
    Feature("supplier_otd_pct", "float", "performance", "scorecards", "otd_pct", SUP,
            "otd_pct of the latest scorecard (rolling 12 months, vs. requested date)", "period_end <= as_of",
            "null when has_scorecard = 0", "On-time delivery."),
    Feature("supplier_otd_confirmed_pct", "float", "performance", "scorecards", "otd_confirmed_pct", SUP,
            "same, vs. first confirmed date", "period_end <= as_of", "null when has_scorecard = 0",
            "On-time vs. the supplier's own promise."),
    Feature("supplier_ppm", "int", "performance", "scorecards", "ppm", SUP, "ppm of the latest scorecard",
            "period_end <= as_of", "null when has_scorecard = 0", "Defects per million (rolling, see SCORECARD.md)."),
    Feature("supplier_score", "float", "performance", "scorecards", "score", SUP, "score of the latest scorecard",
            "period_end <= as_of", "null when has_scorecard = 0", "Overall score (A >= 85, B 70-85, C < 70)."),
    Feature("otd_trend_pp", "float", "performance", "scorecards", "otd_pct, quarter", SUP,
            "otd_pct(latest) - otd_pct(same quarter one year earlier)", "both period_end <= as_of",
            "null without a scorecard one year earlier (before 2025Q3)",
            "Year-on-year delivery trend (non-overlapping rolling windows)."),
    Feature("open_8d_overdue", "int", "performance", "quality_notifications", "qn_date, d8_date, supplier_caused", SUP,
            "supplier-caused QNs with qn_date < as_of - 60 d and no 8D closed by as_of (d8_date null or > as_of)",
            "qn_date <= as_of; a later d8_date counts as still open", NOSUP,
            "Overdue complaints; computed at any date, equals the scorecard field at quarter ends (tested)."),
    Feature("qn_count_12m", "int", "performance", "quality_notifications", "id, qn_date", SUP,
            "count of supplier-caused QNs in the window", W12, INCOMPLETE + "; " + NOSUP, "Complaint frequency."),
    Feature("quality_cost_12m", "float", "performance", "quality_notifications", "cost_recharged_eur", SUP,
            "sum(cost_recharged_eur) of supplier-caused QNs in the window", W12, INCOMPLETE + "; " + NOSUP,
            "Quality cost recharged to the supplier (EUR)."),
    # ---------------------------------------------------------------- payments
    Feature("invoice_count_12m", "int", "payment", "invoices", "id, due_date", SUP,
            "invoices with due_date in the window", W12, NOSUP, "Sample size of the payment features."),
    Feature("avg_payment_delay_days", "float", "payment", "invoices", "paid_date, due_date, discount_taken", SUP,
            "mean(paid_date - due_date) over invoices due in the window, paid by as_of, no cash discount",
            W12 + "; paid_date <= as_of", "null when none", "How late Hollerau pays this supplier (+ = late)."),
    Feature("late_payment_rate", "float", "payment", "invoices", "paid_date, due_date", SUP,
            "share of invoices due in the window paid after due_date or still unpaid at as_of", W12,
            "null when no invoice due in the window", "Our payment discipline towards the supplier (cash lever)."),
    Feature("avg_realized_payment_days", "float", "payment", "invoices", "paid_date, invoice_date", SUP,
            "mean(paid_date - invoice_date) over invoices due in the window and paid by as_of", W12,
            "null when none", "Effective payment term the supplier experiences."),
    Feature("discount_taken_rate", "float", "payment", "invoices", "discount_taken", SUP,
            "share of paid invoices with discount_taken = 1", W12, "null when none",
            "Cash discount usage (0 when the supplier offers none)."),
    # ---------------------------------------------------------------- live negotiation context
    Feature("cur_asked_pct", "float", "context", "current_conditions / negotiation_history", "asked_pct", "-",
            "the supplier's requested change; training rows: negotiation_history.asked_pct",
            "known when the negotiation opens", "null when not given",
            "The ask on the table. In training rows this is an input, not an outcome."),
    Feature("cur_quoted_unit_price", "float", "context", "current_conditions", "quoted_unit_price", "-",
            "given quote, else previous_unit_price x (1 + cur_asked_pct / 100)", "known when the negotiation opens",
            "null when neither is available", "Asked price per price_unit."),
    Feature("cur_quoted_vs_previous_pct", "float", "context", "current_conditions", "-", "-",
            "(cur_quoted_unit_price / previous_unit_price - 1) x 100", "as inputs", "null when an input is null",
            "Ask in % even when only a price was quoted."),
    Feature("cur_quote_to_cost_ratio", "float", "context", "current_conditions, should_cost", "-", "-",
            "cur_quoted_unit_price / estimated_unit_cost", "as inputs", "null when an input is null",
            "Implied margin of the ask over our cost estimate."),
    Feature("cur_asked_minus_hist_avg_pp", "float", "context", "current_conditions, negotiation_history", "-", "-",
            "cur_asked_pct - hist_avg_asked_pct", "as inputs", "null when an input is null",
            "Is this ask higher than the supplier's usual?"),
]

ID_COLUMNS = [f.name for f in IDS]
TARGET_COLUMNS = [f.name for f in TARGETS]
FEATURE_COLUMNS = [f.name for f in FEATURES]
CATEGORICAL = [f.name for f in FEATURES if f.dtype == "category"]
NUMERIC = [f.name for f in FEATURES if f.dtype in ("float", "int", "bool")]
BY_NAME = {f.name: f for f in IDS + TARGETS + FEATURES}
