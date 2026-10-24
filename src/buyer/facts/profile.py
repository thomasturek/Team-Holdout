import sqlite3
from functools import lru_cache

from .features import build_feature_vector
from .features.store import DEFAULT_DB

AS_OF = "2026-09-30"
COUNTRY_FACTOR = {"DE": 1.0, "AT": 1.05, "CH": 1.05, "CZ": 0.82, "PL": 0.82, "HU": 0.82, "TR": 0.75, "CN": 0.7}
BASE_RATE = 0.08


@lru_cache(maxsize=1)
def _skonto():
    con = sqlite3.connect(f"file:{DEFAULT_DB}?mode=ro", uri=True)
    rows = con.execute("SELECT id, payment_days, skonto_days, skonto_pct FROM suppliers WHERE skonto_pct > 0").fetchall()
    con.close()
    return {sid: (pay, days, pct) for sid, pay, days, pct in rows}


def cash_rate(supplier_id, v):
    s = _skonto().get(supplier_id)
    if s and s[0] and s[0] > s[1]:
        return round(s[2] / 100 * 360 / (s[0] - s[1]), 4)
    rate = BASE_RATE
    if v.get("equity_ratio_pct") is not None and v["equity_ratio_pct"] < 25:
        rate += 0.04
    if v.get("credit_index") is not None and v["credit_index"] >= 230:
        rate += 0.04
    return rate


def floor(v):
    cost = v.get("estimated_unit_cost")
    if cost is None:
        return None, None
    if v.get("should_cost_supplier_specific"):
        return cost, (v.get("should_cost_confidence_pct") or 5) / 100
    factor = COUNTRY_FACTOR.get(v.get("supplier_country") or "DE", 1.0)
    return cost * factor, max(0.10, (v.get("should_cost_confidence_pct") or 10) / 100)


def supplier_profile(supplier_id, part_id):
    try:
        v = build_feature_vector(supplier_id, part_id, AS_OF)
    except Exception:
        return {}
    est, conf = floor(v)
    rate = cash_rate(supplier_id, v)
    return {
        "floor_estimate": est,
        "floor_confidence": conf,
        "cash_rate_estimate": rate,
        "cash_pressure": round(min(1.0, max(0.0, (rate - BASE_RATE) / 0.16)), 3),
        "archetype": "unknown",
        "country": v.get("supplier_country"),
    }


def profile(case):
    part = (case.get("parts") or [None])[0]
    return {sid: supplier_profile(sid, part) for sid in case.get("suppliers", [])}
