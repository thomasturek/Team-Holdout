"""Point-in-time feature extraction for (supplier, part, as_of_date).

Cutoff convention: a feature vector "as of D" uses only information known at the end of day D.
For a historical negotiation on day N the training row is built as of N - 1 day, so the
negotiation's own outcome and anything else dated N or later can never enter its features.

Every feature is described in FEATURES.md (generated from spec.py).
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from statistics import fmean, stdev

from .store import (
    FILING_LAG_MONTHS,
    SNAPSHOT_DATE,
    FeatureStore,
    Renewal,
    canonical_supplier,
    default_store,
    last_complete_month,
    month_index,
    to_date,
)

WINDOW_DAYS = 365
HALF_LIFE_DAYS = 365          # recency weight of a past negotiation halves every year
OVERDUE_8D_DAYS = 60          # SCORECARD.md: complaints older than 60 days without closed 8D
BELOW_COST_NOTE = "accepted below full cost to keep the volume"

# Keys accepted in ``current_conditions``. Fill-ins only replace values the database does not have.
FILL_IN_KEYS = {
    "supplier_country", "owner_type", "group_parent", "turnover_eur", "turnover_band",
    "equity_ratio_pct", "credit_index", "staff",
    "part_category", "material_group", "net_weight_kg", "price_unit", "part_uom",
}
CONTEXT_KEYS = {"asked_pct", "quoted_unit_price"}


def build_feature_vector(
    supplier_id: str | None,
    part_id: str,
    as_of_date: str | date,
    current_conditions: dict | None = None,
    store: FeatureStore | None = None,
) -> dict:
    """Flat, ML-ready feature dict for one supplier-part combination as of ``as_of_date``.

    supplier_id may be None or unknown (a supplier the database has never seen): supplier-level
    features are then null and history falls back to category / global aggregates.
    part_id may be unknown if ``current_conditions`` supplies ``part_category`` etc.

    current_conditions (optional) holds what the live negotiation tells us:
      - ``asked_pct``: the supplier's requested price change in %
      - ``quoted_unit_price``: the supplier's quoted price per the part's price_unit
      - fill-ins for unknown suppliers / parts (``FILL_IN_KEYS``): used only where the
        database has no value; never overwrite database facts.

    Identifiers (supplier_id, part_id, as_of_date) are not part of the returned dict.
    """
    store = store or default_store()
    as_of = to_date(as_of_date)
    cc = dict(current_conditions or {})
    unknown = set(cc) - FILL_IN_KEYS - CONTEXT_KEYS
    if unknown:
        raise ValueError(f"unknown current_conditions keys: {sorted(unknown)}")

    sid = canonical_supplier(supplier_id)
    known = store.is_known_supplier(sid)
    if not known:
        sid = None

    f: dict = {"is_known_supplier": int(known)}
    f.update(product_features(store, sid, part_id, as_of))
    for k in ("part_category", "material_group", "net_weight_kg", "price_unit", "part_uom", "supplier_country"):
        if f.get(k) is None and cc.get(k) is not None:
            f[k] = cc[k]
    f.update(negotiation_features(store, sid, part_id, f["part_category"], as_of))
    f.update(price_features(store, sid, part_id, as_of, f["price_unit"]))
    f.update(financial_features(store, sid, as_of, cc))
    f.update(cost_features(store, sid, part_id, as_of, f["previous_unit_price"]))
    f.update(performance_features(store, sid, as_of))
    f.update(payment_features(store, sid, as_of))
    f.update(context_features(f, cc))
    return f


# --------------------------------------------------------------------------- product / competition


def product_features(store: FeatureStore, sid: str | None, part_id: str, as_of: date) -> dict:
    part = store.parts.get(part_id, {})
    sup = store.suppliers.get(sid, {}) if sid else {}
    start, complete = _window(store, as_of)

    approved = {canonical_supplier(r["supplier_id"]) for r in store.sourcing_by_part.get(part_id, [])
                if to_date(r["approved_since"]) <= as_of}
    # Active = ordered from in the last 12 months. At the snapshot this equals sourcing.status
    # == 'active' for every part, and unlike the status it can be reconstructed for any date.
    ordering = {canonical_supplier(r["supplier_id"]) for r in store.po_by_part.get(part_id, [])
                if start <= to_date(r["order_date"]) <= as_of}
    active = len(ordering) if complete else None
    return {
        "part_category": part.get("category"),
        "material_group": part.get("material_group"),
        "net_weight_kg": part.get("net_weight_kg"),
        "price_unit": part.get("price_unit"),
        "part_uom": part.get("uom"),
        "part_abc_class": part.get("abc_class"),
        "supplier_country": sup.get("country"),
        "approved_supplier_count": len(approved) if part else None,
        "active_supplier_count": active if part else None,
        "qualified_supplier_count": len(approved - ordering) if part and complete else None,
    }


# --------------------------------------------------------------------------- negotiation history


def negotiation_features(store: FeatureStore, sid: str | None, part_id: str, category: str | None,
                         as_of: date) -> dict:
    prior = [r for r in store.renewals if r.date <= as_of]
    sup = [r for r in prior if sid is not None and r.supplier_id == sid]
    pair = [r for r in sup if r.part_id == part_id]
    cat = [r for r in prior if category is not None and store.parts.get(r.part_id, {}).get("category") == category]

    level, chosen = "none", []
    for name, rows in (("pair", pair), ("supplier", sup), ("category", cat), ("global", prior)):
        if rows:
            level, chosen = name, rows
            break
    individual = pair or sup          # "last" and "days since" only make sense for this supplier

    prior_events = [e for e in store.events if e["_date"] <= as_of and sid is not None
                    and e["supplier_id"] == sid and e["part_id"] == part_id]
    return {
        "hist_negotiation_count": len(sup),
        "hist_pair_count": len(pair),
        "hist_level": level,
        "hist_level_count": len(chosen),
        "hist_is_fallback": int(level != "pair"),
        "hist_avg_asked_pct": _mean([r.asked_pct for r in chosen]),
        "hist_avg_settled_pct": _mean([r.settled_pct for r in chosen]),
        "hist_avg_concession_pp": _mean([r.concession_pp for r in chosen]),
        "hist_concession_std": stdev([r.concession_pp for r in chosen]) if len(chosen) >= 2 else None,
        "hist_weighted_concession_pp": _recency_mean(chosen, as_of),
        "hist_last_concession_pp": individual[-1].concession_pp if individual else None,
        "hist_days_since_last": (as_of - individual[-1].date).days if individual else None,
        "hist_below_full_cost_note": (int(any(e["note"] == BELOW_COST_NOTE for e in prior_events))
                                      if prior_events else None),
        "supplier_avg_concession_pp": _mean([r.concession_pp for r in sup]),
        "category_avg_concession_pp": _mean([r.concession_pp for r in cat]),
        "category_negotiation_count": len(cat),
        "global_avg_concession_pp": _mean([r.concession_pp for r in prior]),
        "global_negotiation_count": len(prior),
    }


def _recency_mean(rows: list[Renewal], as_of: date) -> float | None:
    if not rows:
        return None
    w = [0.5 ** ((as_of - r.date).days / HALF_LIFE_DAYS) for r in rows]
    return sum(wi * r.concession_pp for wi, r in zip(w, rows, strict=True)) / sum(w)


# --------------------------------------------------------------------------- prices and purchasing


def price_features(store: FeatureStore, sid: str | None, part_id: str, as_of: date,
                   price_unit: int | None) -> dict:
    in_force = [r for r in store.conditions_by_pair.get((sid, part_id), []) if to_date(r["valid_from"]) <= as_of]
    prev = in_force[-1] if in_force else None
    before = in_force[-2] if len(in_force) >= 2 else None

    # Reference price of the part: mean over suppliers of each supplier's price in force.
    latest_per_supplier: dict[str, float] = {}
    for r in store.conditions_by_part.get(part_id, []):
        if to_date(r["valid_from"]) <= as_of:
            latest_per_supplier[canonical_supplier(r["supplier_id"])] = r["price"]

    start, complete = _window(store, as_of)
    lines = [r for r in store.po_by_pair.get((sid, part_id), []) if start <= to_date(r["order_date"]) <= as_of]
    fresh = [r for r in lines if r["price_note"] != "stale_condition"]
    part_lines = [r for r in store.po_by_part.get(part_id, []) if start <= to_date(r["order_date"]) <= as_of]
    known = sid is not None
    part_volume = sum(r["qty"] for r in part_lines) if complete and part_id in store.parts else None

    fc_cap = last_complete_month(as_of)
    snaps = [r for r in store.forecasts_by_part.get(part_id, []) if month_index(r["snapshot_month"]) <= fc_cap]
    fc = snaps[-1]["qty_next_12m"] if snaps else None

    return {
        "previous_unit_price": prev["price"] if prev else None,
        "previous_price_per_uom": prev["price"] / prev["price_unit"] if prev else None,
        "previous_price_basis": prev["basis"] if prev else None,
        "price_change_last_pct": _pct(prev["price"], before["price"]) if prev and before else None,
        "part_ref_unit_price": _mean(list(latest_per_supplier.values())),
        "po_window_complete": int(complete),
        "po_12m_volume": sum(r["qty"] for r in lines) if known and complete else None,
        "po_12m_spend": (sum(r["qty"] * r["price"] / r["price_unit"] for r in lines)
                         if known and complete else None),
        "po_12m_order_count": len(lines) if known and complete else None,
        # qty-weighted price per price_unit; stale conditions (KNOWN_ISSUES #6) are not the agreed price
        "po_12m_avg_unit_price": (sum(r["qty"] * r["price"] / r["price_unit"] for r in fresh)
                                  / sum(r["qty"] for r in fresh) * (price_unit or fresh[0]["price_unit"])
                                  if fresh else None),
        "po_rush_order_share": _share(lines, lambda r: r["change_type"] == "rush"),
        "po_stale_condition_share": _share(lines, lambda r: r["price_note"] == "stale_condition"),
        "part_po_12m_volume": part_volume,
        "forecast_12m_volume": fc,
        "forecast_growth_pct": _pct(fc, part_volume) if fc is not None and part_volume else None,
    }


# --------------------------------------------------------------------------- financials


def financial_features(store: FeatureStore, sid: str | None, as_of: date, cc: dict) -> dict:
    intel = store.intel.get(sid, {}) if sid else {}
    filed = bool(intel) and as_of >= filing_available_from(intel["filed_fy"])
    # supplier_intel is the snapshot at SNAPSHOT_DATE: credit_index is the value at the snapshot,
    # credit_index_12m_ago the value one year earlier. Use each only once it existed.
    if intel and as_of >= SNAPSHOT_DATE:
        credit = intel["credit_index"]
        credit_chg = intel["credit_index"] - intel["credit_index_12m_ago"]
    elif intel and as_of >= SNAPSHOT_DATE.replace(year=SNAPSHOT_DATE.year - 1):
        credit, credit_chg = intel["credit_index_12m_ago"], None
    else:
        credit, credit_chg = None, None

    f = {
        "owner_type": intel.get("owner_type"),
        "group_parent": intel.get("group_parent"),
        "has_group_parent": int(intel["group_parent"] is not None) if intel else None,
        "supplier_age_years": as_of.year - intel["founded"] if intel.get("founded") else None,
        "has_financials": int(filed),
        "turnover_eur": intel.get("turnover_eur") if filed else None,
        "turnover_band": intel.get("turnover_band") if filed else None,
        "equity_ratio_pct": intel.get("equity_ratio_pct") if filed else None,
        "staff": intel.get("staff") if filed else None,
        "credit_index": credit,
        "credit_index_change": credit_chg,
    }
    for k in ("owner_type", "group_parent", "turnover_eur", "turnover_band", "equity_ratio_pct", "credit_index",
              "staff"):
        if f[k] is None and cc.get(k) is not None:
            f[k] = cc[k]
    if f["has_group_parent"] is None and f["owner_type"] is not None:
        f["has_group_parent"] = int(f["group_parent"] is not None)
    return f


def filing_available_from(filed_fy: int) -> date:
    """Last day of the month FILING_LAG_MONTHS after the fiscal year end (31 Dec), capped at the
    snapshot: whatever supplier_intel holds was public by then at the latest."""
    y, m = divmod(month_index(date(filed_fy, 12, 1)) + FILING_LAG_MONTHS + 1, 12)
    return min(date(y, m + 1, 1) - timedelta(days=1), SNAPSHOT_DATE)


# --------------------------------------------------------------------------- production cost


def cost_features(store: FeatureStore, sid: str | None, part_id: str, as_of: date,
                  previous_price: float | None) -> dict:
    rows = [r for r in store.should_cost_by_part.get(part_id, []) if to_date(r["estimate_date"]) <= as_of]
    own = [r for r in rows if sid is not None and r["supplier_id"] == sid]
    sc = (own or sorted(rows, key=lambda r: r["unit_cost"]))[0] if rows else None
    unit = sc["unit_cost"] if sc else None

    drivers = store.cost_drivers_by_part.get(part_id, [])
    changes = {d["series_id"]: index_change_12m(store, d["series_id"], as_of) for d in drivers}
    primary = max(drivers, key=lambda d: d["weight"]) if drivers else None
    usable = [d for d in drivers if changes[d["series_id"]] is not None]
    return {
        "has_should_cost": int(sc is not None),
        "should_cost_supplier_specific": int(bool(own)) if sc else None,
        "estimated_unit_cost": unit,
        "should_cost_confidence_pct": sc["confidence_pct"] if sc else None,
        "cost_to_price_ratio": unit / previous_price if unit and previous_price else None,
        "material_cost_share": sc["material_eur"] / unit if sc else None,
        "conversion_cost_share": sc["conversion_eur"] / unit if sc else None,
        "overhead_cost_share": sc["overhead_eur"] / unit if sc else None,
        "primary_cost_driver": primary["series_id"] if primary else None,
        "market_index_change_12m": changes[primary["series_id"]] if primary else None,
        "weighted_cost_driver_change": (sum(d["weight"] * changes[d["series_id"]] for d in usable)
                                        if usable else None),
        "cost_driver_weight_total": sum(d["weight"] for d in drivers) if drivers else None,
    }


def latest_index_month(store: FeatureStore, series_id: str, as_of: date) -> int | None:
    cap = last_complete_month(as_of) - store.index_lag.get(series_id, 0)
    months = [m for m in store.index_values.get(series_id, {}) if m <= cap]
    return max(months) if months else None


def index_change_12m(store: FeatureStore, series_id: str, as_of: date) -> float | None:
    last = latest_index_month(store, series_id, as_of)
    if last is None:
        return None
    vals = store.index_values[series_id]
    return _pct(vals[last], vals.get(last - 12))


# --------------------------------------------------------------------------- supplier performance


def performance_features(store: FeatureStore, sid: str | None, as_of: date) -> dict:
    cards = [r for r in store.scorecards_by_supplier.get(sid, []) if to_date(r["period_end"]) <= as_of] if sid else []
    sc = cards[-1] if cards else None
    year_ago = None
    if sc:
        label = f"{int(sc['quarter'][:4]) - 1}{sc['quarter'][4:]}"
        year_ago = next((r for r in cards if r["quarter"] == label), None)

    start, complete = _window(store, as_of)
    qns = [r for r in store.qn_by_supplier.get(sid, []) if r["supplier_caused"] == 1] if sid else []
    window_qns = [r for r in qns if start <= to_date(r["qn_date"]) <= as_of]
    overdue = sum(1 for r in qns
                  if to_date(r["qn_date"]) < as_of - timedelta(days=OVERDUE_8D_DAYS)
                  and (r["d8_date"] is None or to_date(r["d8_date"]) > as_of))
    return {
        "has_scorecard": int(sc is not None),
        "supplier_otd_pct": sc["otd_pct"] if sc else None,
        "supplier_otd_confirmed_pct": sc["otd_confirmed_pct"] if sc else None,
        "supplier_ppm": sc["ppm"] if sc else None,
        "supplier_score": sc["score"] if sc else None,
        "otd_trend_pp": sc["otd_pct"] - year_ago["otd_pct"] if year_ago else None,
        "open_8d_overdue": overdue if sid else None,
        "qn_count_12m": len(window_qns) if sid and complete else None,
        "quality_cost_12m": sum(r["cost_recharged_eur"] for r in window_qns) if sid and complete else None,
    }


# --------------------------------------------------------------------------- payment behaviour


def payment_features(store: FeatureStore, sid: str | None, as_of: date) -> dict:
    start, _ = _window(store, as_of)
    invoices = store.invoices_by_supplier.get(sid, []) if sid else []
    due = [r for r in invoices if start <= to_date(r["due_date"]) <= as_of]

    def paid_by_cutoff(r):
        return r["paid_date"] is not None and to_date(r["paid_date"]) <= as_of

    paid = [r for r in due if paid_by_cutoff(r)]
    net = [r for r in paid if r["discount_taken"] == 0]
    return {
        "invoice_count_12m": len(due) if sid else None,
        "avg_payment_delay_days": (_mean([(to_date(r["paid_date"]) - to_date(r["due_date"])).days for r in net])),
        # unpaid at the cutoff and past due counts as late (we know it is late, not by how much)
        "late_payment_rate": _share(due, lambda r: not paid_by_cutoff(r) or r["paid_date"] > r["due_date"]),
        "avg_realized_payment_days": _mean([(to_date(r["paid_date"]) - to_date(r["invoice_date"])).days
                                            for r in paid]),
        "discount_taken_rate": _share(paid, lambda r: r["discount_taken"] == 1),
    }


# --------------------------------------------------------------------------- live negotiation context


def context_features(f: dict, cc: dict) -> dict:
    asked = cc.get("asked_pct")
    quoted = cc.get("quoted_unit_price")
    prev = f.get("previous_unit_price")
    if quoted is None and asked is not None and prev is not None:
        quoted = prev * (1 + asked / 100)
    cost = f.get("estimated_unit_cost")
    hist_asked = f.get("hist_avg_asked_pct")
    return {
        "cur_asked_pct": asked,
        "cur_quoted_unit_price": quoted,
        "cur_quoted_vs_previous_pct": _pct(quoted, prev) if quoted is not None and prev else None,
        "cur_quote_to_cost_ratio": quoted / cost if quoted is not None and cost else None,
        "cur_asked_minus_hist_avg_pp": asked - hist_asked if asked is not None and hist_asked is not None else None,
    }


# --------------------------------------------------------------------------- helpers


def _window(store: FeatureStore, as_of: date) -> tuple[date, bool]:
    """Trailing 365-day window ending at as_of (inclusive); complete if the data reaches back that far."""
    start = as_of - timedelta(days=WINDOW_DAYS - 1)
    return start, start >= store.activity_start


def _mean(xs: list) -> float | None:
    return fmean(xs) if xs else None


def _share(rows: list, pred) -> float | None:
    return sum(1 for r in rows if pred(r)) / len(rows) if rows else None


def _pct(new: float | None, old: float | None) -> float | None:
    if new is None or not old or (isinstance(old, float) and math.isnan(old)):
        return None
    return (new / old - 1) * 100
