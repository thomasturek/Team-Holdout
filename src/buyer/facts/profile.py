"""Supplier profiles (SCOUT): floor, cash and archetype per supplier of a case.

    from buyer.facts.profile import profile
    profile(case)   # -> {supplier_id: {"floor_estimate", "floor_confidence", "cash_rate_estimate",
                    #                   "cash_pressure", "archetype", "approval_style", ...}}

Floor: the part's should-cost (supplier-specific, else the cheapest estimate x country factor);
without one, the market price (this supplier's latest price, else the lowest current price of any
source, else the part's standard price) x the cost-to-price ratio measured on the parts that have
both, by category. Archetype: rules over supplier_intel, sourcing, news and our payment record.
"""

import sqlite3
import statistics
from functools import lru_cache

from .features import build_feature_vector
from .features.store import DEFAULT_DB

AS_OF = "2026-09-30"
COUNTRY_FACTOR = {"DE": 1.0, "AT": 1.05, "CH": 1.05, "CZ": 0.82, "PL": 0.82, "HU": 0.82, "TR": 0.75, "CN": 0.7}
BASE_RATE = 0.08
MARKET_CONFIDENCE = 0.15          # floor from a price, not a cost estimate
CASH_NEWS = {"credit_watch": 0.35, "credit_downgrade": 0.35, "short_time_work": 0.3, "restructuring": 0.3}
CAPACITY_NEWS = {"allocation", "full_order_book", "chip_shortage"}
BIG_TURNOVER = 50e6


def _rows(sql, params=()):
    con = sqlite3.connect(f"file:{DEFAULT_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, params)]
    finally:
        con.close()


@lru_cache(maxsize=1)
def _skonto():
    rows = _rows("SELECT id, payment_days, skonto_days, skonto_pct FROM suppliers WHERE skonto_pct > 0")
    return {r["id"]: (r["payment_days"], r["skonto_days"], r["skonto_pct"]) for r in rows}


@lru_cache(maxsize=1)
def _news():
    out = {}
    for r in _rows("SELECT id, date, supplier_id, topic, headline FROM news "
                   "WHERE supplier_id IS NOT NULL ORDER BY date"):
        out.setdefault(r["supplier_id"], []).append(r)
    return out


@lru_cache(maxsize=1)
def _overdue_letters():
    """Suppliers that wrote to us about overdue invoices in the last 12 months: {supplier: [doc ids]}."""
    out = {}
    for r in _rows("SELECT id, supplier_id FROM documents "
                   "WHERE subject LIKE 'Overdue invoice%' AND date > date(?, '-12 months')", (AS_OF,)):
        out.setdefault(r["supplier_id"], []).append(r["id"])
    return out


@lru_cache(maxsize=1)
def _cost_to_price():
    """Median of should-cost / that supplier's latest price, by part category (and 'all')."""
    rows = _rows("""
        SELECT p.category, s.unit_cost,
               (SELECT price FROM price_conditions c WHERE c.part_id = s.part_id AND c.supplier_id = s.supplier_id
                ORDER BY valid_from DESC LIMIT 1) AS price
        FROM should_cost s JOIN parts p ON p.id = s.part_id WHERE s.supplier_id IS NOT NULL""")
    ratios = {}
    for r in rows:
        if r["price"]:
            ratios.setdefault(r["category"], []).append(r["unit_cost"] / r["price"])
    out = {cat: statistics.median(v) for cat, v in ratios.items() if len(v) >= 3}
    out["all"] = statistics.median([x for v in ratios.values() for x in v])
    return out


def market_price(supplier_id, part_id):
    """(price per price_unit, source) for the part: this supplier's latest condition, else the
    lowest latest condition among its sources, else the standard price."""
    rows = _rows("""SELECT supplier_id, price FROM price_conditions c WHERE part_id = ? AND valid_from =
                    (SELECT max(valid_from) FROM price_conditions d WHERE d.part_id = c.part_id
                     AND d.supplier_id = c.supplier_id)""", (part_id,))
    own = [r["price"] for r in rows if r["supplier_id"] == supplier_id]
    if own:
        return own[0], "own_price"
    if rows:
        return min(r["price"] for r in rows), "market_price"
    std = _rows("SELECT standard_price FROM parts WHERE id = ?", (part_id,))
    if std and std[0]["standard_price"]:
        return std[0]["standard_price"], "standard_price"
    return None, None


def floor(v, supplier_id=None, part_id=None):
    """(floor_estimate, floor_confidence, source) in EUR per price_unit."""
    cost = v.get("estimated_unit_cost")
    if cost is not None:
        if v.get("should_cost_supplier_specific"):
            return cost, (v.get("should_cost_confidence_pct") or 5) / 100, "should_cost"
        factor = COUNTRY_FACTOR.get(v.get("supplier_country") or "DE", 1.0)
        return cost * factor, max(0.10, (v.get("should_cost_confidence_pct") or 10) / 100), "should_cost_country"
    price, source = market_price(supplier_id, part_id) if part_id else (None, None)
    if price is None:
        return None, None, None
    ratios = _cost_to_price()
    ratio = ratios.get(v.get("part_category"), ratios["all"])
    return round(price * ratio, 4), MARKET_CONFIDENCE, source


def cash_pressure(supplier_id, v):
    """0..1 and the reasons: weak or worsening credit, thin equity, distress news, letters about
    our overdue invoices, a cash discount on offer."""
    score, why = 0.0, []
    credit, change = v.get("credit_index"), v.get("credit_index_change")
    if credit is not None and credit >= 300:  # German style: higher is worse, 300+ is weak
        score += 0.35
        why.append(f"credit index {credit:g}")
    if change is not None and change >= 30:
        score += 0.25
        why.append(f"credit index +{change:g} in 12 months")
    equity = v.get("equity_ratio_pct")
    if equity is not None and equity < 22:
        score += 0.15
        why.append(f"equity ratio {equity:g} %")
    for n in _news().get(supplier_id, []):
        if n["topic"] in CASH_NEWS:
            score += CASH_NEWS[n["topic"]]
            why.append(f"{n['headline']} ({n['id']})")
    overdue = _overdue_letters().get(supplier_id)
    if overdue:
        score += 0.15
        why.append(f"complains about our overdue invoices ({', '.join(overdue)})")
    if supplier_id in _skonto():
        score += 0.1
        why.append("offers a cash discount")
    return round(min(1.0, score), 3), why


def cash_rate(supplier_id, v, pressure=None):
    """What money is worth to the supplier per year: the rate its cash discount implies, else the
    base rate plus up to 16 points for cash pressure."""
    if pressure is None:
        pressure, _ = cash_pressure(supplier_id, v)
    rate = BASE_RATE + 0.16 * pressure
    s = _skonto().get(supplier_id)
    if s and s[0] and s[0] > (s[1] or 0):
        rate = max(rate, s[2] / 100 * 360 / (s[0] - (s[1] or 0)))
    return round(rate, 4)


def archetype(supplier_id, v, pressure):
    """family_foundry | group_ladder | cash_short_jobshop | near_monopolist | unknown, and the
    approval style that goes with it (flat | ladder)."""
    owner = v.get("owner_type")
    group = owner == "group" or bool(v.get("group_parent"))
    turnover = v.get("turnover_eur") or 0
    sources = v.get("approved_supplier_count")
    capacity = any(n["topic"] in CAPACITY_NEWS for n in _news().get(supplier_id, []))
    style = "ladder" if group else "flat"
    if pressure >= 0.5 and not group:
        return "cash_short_jobshop", style
    if sources is not None and sources <= 1 and (group or turnover >= BIG_TURNOVER or capacity):
        return "near_monopolist", style
    if group:
        return "group_ladder", style
    if owner in ("family", "founder"):
        return "family_foundry", style
    return "unknown", style


def notes(supplier_id):
    out = [f"{n['date']} {n['headline']} ({n['id']})" for n in _news().get(supplier_id, []) if n["topic"] != "noise"]
    out += [f"wrote about overdue invoices ({d})" for d in _overdue_letters().get(supplier_id, [])]
    return out


def supplier_profile(supplier_id, part_id):
    try:
        v = build_feature_vector(supplier_id, part_id, AS_OF)
    except Exception:
        return {}
    est, conf, source = floor(v, supplier_id, part_id)
    pressure, why = cash_pressure(supplier_id, v)
    kind, style = archetype(supplier_id, v, pressure)
    return {
        "supplier_id": supplier_id,
        "floor_estimate": est,
        "floor_confidence": conf,
        "floor_source": source,
        "cash_rate_estimate": cash_rate(supplier_id, v, pressure),
        "cash_pressure": pressure,
        "cash_reasons": why,
        "archetype": kind,
        "approval_style": style,
        "owner_type": v.get("owner_type"),
        "country": v.get("supplier_country"),
        "notes": notes(supplier_id),
    }


def profile(case):
    """Profile per supplier for the case's first part, plus ``floor_by_part`` for bundles."""
    parts = case.get("parts") or [None]
    out = {}
    for sid in case.get("suppliers", []):
        p = supplier_profile(sid, parts[0])
        if p and len(parts) > 1:
            p["floor_by_part"] = {part: (supplier_profile(sid, part) or {}).get("floor_estimate") for part in parts}
        out[sid] = p
    return out
