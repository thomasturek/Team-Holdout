import json
import math
from pathlib import Path

from .supplier import SupplierParams

RANGES_FILE = Path(__file__).with_name("ranges.json")

DEFAULT_RANGES = {
    "open_margin": (0.06, 0.25),
    "min_margin": (-0.03, 0.08),
    "max_concession": (0.01, 0.06),
    "cash_rate": (0.05, 0.20),
    "concede": (0.10, 0.50),
    "approval_step_pct": (1.0, 5.0),
    "patience": (1, 3),
    "walk_after_final": (0.1, 0.6),
    "cost_vs_current": (0.75, 0.95),
    "floor_error": 0.08,
}


def load_ranges():
    r = dict(DEFAULT_RANGES)
    if RANGES_FILE.is_file():
        r.update({k: tuple(v) if isinstance(v, list) else v for k, v in json.loads(RANGES_FILE.read_text()).items()})
    return r


def sample(case, rng, ranges=None):
    r = ranges or load_ranges()
    u = lambda k: rng.uniform(*r[k])
    reference = case["buyer"].get("current_unit_price") or case["buyer"]["fallback_unit_price"]
    full_cost = reference * u("cost_vs_current")
    options = case.get("term_options", {}).get("payment_days") or [case["buyer"]["reference_payment_days"]]
    open_margin = u("open_margin")
    min_margin = max(open_margin - u("max_concession"), r["min_margin"][0])
    weights = r.get("std_payment_weights")
    if weights:
        days = [d for d in options if str(d) in weights] or options
        std_days = rng.choices(days, [weights.get(str(d), 0.01) for d in days])[0]
    else:
        std_days = rng.choice([d for d in options if d <= 60] or options)
    params = SupplierParams(
        full_cost=full_cost,
        open_margin=open_margin,
        min_margin=min_margin,
        cash_rate=u("cash_rate"),
        concede=u("concede"),
        approval_step_pct=u("approval_step_pct"),
        patience=rng.randint(*r["patience"]),
        walk_after_final=u("walk_after_final"),
        std_payment_days=std_days,
    )
    estimate = full_cost * math.exp(rng.gauss(0, r["floor_error"]))
    profile = {"floor_estimate": estimate, "cash_rate_estimate": params.cash_rate}
    return params, profile
