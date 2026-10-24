"""THE SCOUT, V3 (docs/V3_ROBUSTNESS_PLAN.md, gates 1 and 2): is a generated case valid?

    schema_errors(case)     documented type, goal, fields, operators, options, alternative
    economic_errors(case)   coherent need / horizon / prices, a costable plan, at least one valid action

Deterministic code decides whether a generated test is kept; [] = keep. An LLM may propose cases,
it never decides this.
"""

from __future__ import annotations

import math

from arena_kit.cost import complete_offer, must_haves_ok, total_cost

TYPES = {"price_increase", "renewal", "rfq", "bundling", "raw_material", "capacity", "quality"}
GOALS = {"stabilise", "secure_supply", "quality_first", "leverage", "routine"}
FIELDS = {"unit_price", "payment_days", "lead_time_days", "volume_per_year", "contract_months", "effective_date",
          "index_clause", "incoterm", "tooling_eur", "ppm_commitment", "chargeback_eur_per_complaint"}  # fmt: skip
OPS = {"<=", ">=", "<", ">", "==", "!="}
INCOTERMS = {"EXW", "FCA", "DAP"}
BUYER_KEYS = ("need_per_year", "horizon_years", "fallback_unit_price", "interest_rate", "reference_payment_days",
              "need_lead_time_days", "category_goal", "freight_eur_per_unit", "must_haves", "alternative")  # fmt: skip


def schema_errors(case) -> list[str]:
    errs = []
    if case.get("type") not in TYPES:
        errs.append(f"type {case.get('type')!r} undocumented")
    b = case.get("buyer")
    if not isinstance(b, dict):
        return errs + ["no buyer block"]
    errs += [f"buyer.{k} missing" for k in BUYER_KEYS if k not in b]
    if b.get("category_goal") not in GOALS:
        errs.append(f"category_goal {b.get('category_goal')!r} undocumented")
    neg = case.get("negotiable") or []
    if "unit_price" not in neg:
        errs.append("unit_price not negotiable")
    errs += [f"negotiable field {f!r} undocumented" for f in neg if f not in FIELDS]
    for m in b.get("must_haves") or []:
        if m.get("op") not in OPS or m.get("field") not in FIELDS:
            errs.append(f"must-have {m} invalid")
    for f, options in (case.get("term_options") or {}).items():
        if f not in FIELDS or not isinstance(options, list) or not options:
            errs.append(f"term_options.{f} invalid")
        elif f == "incoterm" and set(options) - INCOTERMS:
            errs.append(f"incoterm options {options}")
        elif f in ("payment_days", "lead_time_days", "contract_months") and not all(
            isinstance(o, int) and o >= 0 for o in options
        ):
            errs.append(f"term_options.{f} not non-negative ints")
    if set(b.get("freight_eur_per_unit") or {}) != INCOTERMS:
        errs.append("freight_eur_per_unit must price EXW, FCA, DAP")
    alt = b.get("alternative") or {}
    if alt.get("kind") not in (None, "none", "quote", "current_contract"):
        errs.append(f"alternative kind {alt.get('kind')!r}")
    if not case.get("suppliers"):
        errs.append("no suppliers")
    return errs


def economic_errors(case) -> list[str]:
    errs = []
    b = case["buyer"]
    for k in ("need_per_year", "horizon_years", "fallback_unit_price"):
        if not isinstance(b.get(k), int | float) or b[k] <= 0:
            errs.append(f"buyer.{k} = {b.get(k)!r}")
    if errs:
        return errs
    ref = b.get("current_unit_price") or b["fallback_unit_price"]
    try:
        plan = complete_offer(case, {"unit_price": ref})
        c_plan = total_cost(case, plan)
    except Exception as e:
        return [f"plan not costable: {type(e).__name__}: {e}"]
    if not math.isfinite(c_plan) or c_plan <= 0:
        errs.append(f"plan cost {c_plan}")
    if not _some_valid_action(case, ref):
        errs.append("no term sheet meets the must-haves")
    alt = b.get("alternative") or {}
    if alt.get("kind") not in (None, "none") and (alt.get("terms") or {}).get("unit_price"):
        c_alt = total_cost(case, alt["terms"])
        if not math.isfinite(c_alt) or c_alt <= 0:
            errs.append(f"alternative cost {c_alt}")
    return errs


def _some_valid_action(case, price) -> bool:
    """A sheet built from the term options (first combination that works) meets every must-have."""
    combos = [{}]
    for f, opts in (case.get("term_options") or {}).items():
        if f in case["negotiable"] and f != "unit_price":
            combos = [{**c, f: o} for c in combos for o in opts][:256]
    return any(must_haves_ok(case, complete_offer(case, {"unit_price": price, **c})) for c in combos)


def check(case) -> dict:
    return {"schema": schema_errors(case), "economic": [] if schema_errors(case) else economic_errors(case)}
