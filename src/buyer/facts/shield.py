"""THE SCOUT's safety shield for Phase 2 (docs/PHASE2_SAFE_ARCHITECTURE.md, S1 + S2).

One validator for every candidate action the Analyst generates, and the euro features the ranker
uses. The Analyst never re-implements these rules; every figure comes from `arena_kit.cost`.

    feats = cost_features(case, terms, standard, profile, c_open)
    reasons = validate(case, candidate, ctx)     # [] = safe to rank

`ctx` is a dict: standing_id, standing_terms, standard (the supplier's standard terms), profile,
used_refs (IDs already cited to this supplier), known_id (callable: the ID exists in the data).
"""

from __future__ import annotations

import math

from arena_kit.cost import (
    RELATIONSHIP_GOALS,
    complete_offer,
    cost_breakdown,
    must_haves_ok,
    supplier_value,
    total_cost,
)

MAX_MARGIN_GAP_PTS = 5.0  # stabilise / secure_supply: never offer more than 5 margin points below sustainable
MAX_SHEETS = 3
MAX_CLAIMS = 3


def alternative_cost(case) -> float:
    alt = case["buyer"].get("alternative") or {}
    if alt.get("kind") in (None, "none") or not (alt.get("terms") or {}).get("unit_price"):
        return math.inf
    return total_cost(case, alt["terms"])


def supplier_estimate(profile, standard) -> dict | None:
    """Our estimate of the supplier for the kit's relationship term, or None without a floor."""
    profile = profile or {}
    std = {**(profile.get("standard_terms") or {}), **(standard or {})}
    floor = profile.get("floor_estimate")
    if not floor or std.get("payment_days") is None:
        return None
    return {"standard": std, "interest_rate": profile.get("cash_rate_estimate") or 0.08, "full_cost": floor}


def supplier_margin_pct(case, terms, standard, profile) -> float | None:
    est = supplier_estimate(profile, standard)
    if est is None:
        return None
    try:
        worth = supplier_value(case, terms, est)
    except Exception:  # odd standard terms: no estimate rather than a wrong one
        return None
    return (worth - est["full_cost"]) / worth * 100 if worth else None


def cost_features(case, terms, standard=None, profile=None, c_open=None) -> dict:
    """C of a complete term sheet with the supplier's standard terms, and what the ranker needs."""
    est = supplier_estimate(profile, standard)
    c = total_cost(case, terms, standard)
    c_rel = total_cost(case, terms, standard, supplier=est) if est else c
    parts = cost_breakdown(case, terms, standard, supplier=est) if terms.get("unit_price") is not None else {}
    c_alt = alternative_cost(case)
    return {
        "buyer_cost": c_rel,  # incl. our estimate of the relationship cost (strategic / bottleneck)
        "buyer_cost_kit": c,  # without it: what the plain cost function says
        "relationship_cost": round(c_rel - c, 2),
        "uncovered_need": parts.get("uncovered_need", 0.0),
        "alternative_cost": c_alt,
        "beats_alternative": c_rel < c_alt,
        "improvement_vs_alternative": None if c_alt == math.inf else round(c_alt - c_rel, 2),
        "must_haves_ok": must_haves_ok(case, terms, standard),
        "saving_vs_open": None if c_open in (None, math.inf) else round(c_open - c_rel, 2),
        "supplier_margin_pct": supplier_margin_pct(case, terms, standard, profile),
    }


def check_terms(case, terms) -> list[str]:
    """A term sheet the API accepts: every negotiable field, nothing else, values inside term_options."""
    reasons = []
    fields, negotiable = set(terms), set(case["negotiable"])
    if fields != negotiable:
        missing, extra = sorted(negotiable - fields), sorted(fields - negotiable)
        reasons.append(f"fields: missing {missing}, extra {extra}")
    price = terms.get("unit_price")
    if not isinstance(price, int | float) or price <= 0:
        reasons.append(f"unit_price {price!r}")
    for f, options in (case.get("term_options") or {}).items():
        if f in terms and options and terms[f] not in options:
            reasons.append(f"{f}={terms[f]!r} not in term_options")
    return reasons


def _uncovered_trap(case, terms, standard) -> bool:
    """The sheet leaves need uncovered that the buyer's own plan at the same price would cover."""
    try:
        mine = cost_breakdown(case, terms, standard)["uncovered_need"]
        plan = complete_offer(case, {"unit_price": terms["unit_price"]})
        return mine > cost_breakdown(case, plan, standard)["uncovered_need"] + 1.0
    except Exception:
        return False


def _margin_too_low(case, terms, standard, profile) -> bool:
    b = case["buyer"]
    if b.get("category_goal") not in RELATIONSHIP_GOALS or not b.get("sustainable_margin_pct"):
        return False
    if (profile or {}).get("floor_confidence", 1.0) > 0.15:  # a rough floor must not block an offer
        return False
    margin = supplier_margin_pct(case, terms, standard, profile)
    return margin is not None and margin < b["sustainable_margin_pct"] - MAX_MARGIN_GAP_PTS


def _claim_reasons(claims, used_refs, known_id) -> list[str]:
    reasons, seen = [], set(used_refs or ())
    if len(claims) > MAX_CLAIMS:
        reasons.append(f"{len(claims)} claims (the arena checks {MAX_CLAIMS})")
    for c in claims:
        refs = list(getattr(c, "refs", None) or (c.get("refs") if isinstance(c, dict) else []) or [])
        if not refs:
            reasons.append(f"claim {getattr(c, 'key', '?')} without refs")
        for r in refs:
            if known_id is not None and not known_id(r):
                reasons.append(f"claim ref {r} unknown")
            if r in seen:
                reasons.append(f"claim ref {r} already used")
            seen.add(r)
    return reasons


def validate(case, cand, ctx) -> list[str]:
    """Why a candidate is unsafe; [] = safe. Never raises: an error is a rejection reason."""
    try:
        return _validate(case, cand, ctx)
    except Exception as e:
        return [f"shield error: {type(e).__name__}: {e}"]


def _validate(case, cand, ctx) -> list[str]:
    standard, profile = ctx.get("standard") or {}, ctx.get("profile") or {}
    if cand.kind == "walk":
        return []
    if cand.kind == "accept":
        reasons = []
        if not cand.accept_sheet_id or cand.accept_sheet_id != ctx.get("standing_id"):
            reasons.append(f"stale term sheet {cand.accept_sheet_id!r} (standing {ctx.get('standing_id')!r})")
        terms = ctx.get("standing_terms") or {}
        if not must_haves_ok(case, terms, standard):
            reasons.append("breaks a must-have")
        if total_cost(case, terms, standard) >= alternative_cost(case):
            reasons.append("costs more than the alternative")
        return reasons
    if cand.kind != "send":
        return [f"unknown kind {cand.kind!r}"]
    reasons = []
    if not 1 <= len(cand.term_sheets) <= MAX_SHEETS:
        reasons.append(f"{len(cand.term_sheets)} term sheets")
    for i, terms in enumerate(cand.term_sheets):
        reasons += [f"sheet {i}: {r}" for r in check_terms(case, terms)]
        if terms.get("unit_price") and _uncovered_trap(case, terms, standard):
            reasons.append(f"sheet {i}: leaves need uncovered")
        if terms.get("unit_price") and _margin_too_low(case, terms, standard, profile):
            reasons.append(f"sheet {i}: supplier margin far below sustainable")
    reasons += _claim_reasons(cand.claims, ctx.get("used_refs"), ctx.get("known_id"))
    return reasons
