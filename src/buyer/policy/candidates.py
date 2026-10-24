"""THE ANALYST, Phase 2 (A1): a small set of complete, safe candidate actions, generated in code.

Families (docs/PHASE2_SAFE_ARCHITECTURE.md):
  v0          what Policy V0 decides - always a candidate, and the fallback
  price_step  V0's offer with a smaller / larger concession (or a softer / harder opening)
  cash_trade  a faster payment term for a lower price, when the supplier may be short of cash
  accept      the standing offer, when V0's own acceptance rules pass
  walk        no deal: the alternative

Every candidate is costed by the SCOUT (`facts.shield.cost_features`) and checked by its shield
(`facts.shield.validate`); invalid ones are kept, marked, and never ranked. Nothing here mutates the
real ThreadState: V0 runs on copies.
"""

from __future__ import annotations

import copy
import math

from arena_kit.cost import complete_offer, total_cost

from ..facts import shield
from ..interfaces import CandidateAction
from .policy import Policy, ThreadState

CONSERVATIVE = {"v0", "price_step"}  # medium confidence: only these may replace V0's move
STEPS = (0.5, 1.5)  # concession multipliers around V0's
OPEN_FRACS = (0.5, 1.6)  # first offer: opening position multipliers around V0's
CASH_MIN_PRESSURE = 0.3


def _primary_price(decision) -> float | None:
    return decision.term_sheets[0]["unit_price"] if decision.kind == "send" and decision.term_sheets else None


def _candidate(cid, family, decision, sid) -> CandidateAction:
    return CandidateAction(
        candidate_id=cid, kind=decision.kind, supplier_id=sid, term_sheets=list(decision.term_sheets),
        claims=list(decision.claims), questions=list(decision.questions), intent=decision.intent,
        buyer_cost=None, saving_vs_open=None, improvement_vs_alternative=None, supplier_value_estimate=None,
        features={}, valid=True, rejection_reasons=[], accept_sheet_id=decision.accept_sheet_id, family=family,
    )  # fmt: skip


def _cash_signal(t: ThreadState) -> bool:
    sig = t.signals or {}
    return (
        (t.profile or {}).get("cash_pressure", 0) >= CASH_MIN_PRESSURE
        or bool(sig.get("cash_pressure"))
        or "faster_payment" in (sig.get("asks") or [])
    )


def _cash_trade(case, policy: Policy, t: ThreadState, base_sheet: dict, v0) -> object | None:
    """Lead with the fastest payment the case allows, priced so the buyer gains: the supplier's
    value of the earlier cash (its cash rate), the buyer's own interest cost of paying earlier
    added back, and only if the result is cheaper for the buyer than V0's sheet."""
    options = (case.get("term_options") or {}).get("payment_days") or []
    days = base_sheet.get("payment_days")
    if "payment_days" not in case["negotiable"] or days is None:
        return None
    faster = sorted(d for d in options if d < days)
    if not faster:
        return None
    d = faster[0]
    rate = (t.profile or {}).get("cash_rate_estimate") or 0.08
    worth_to_supplier = rate * (days - d) / 360
    sheet = complete_offer(case, {**base_sheet, "payment_days": d,
                                  "unit_price": base_sheet["unit_price"] * (1 - worth_to_supplier)})  # fmt: skip
    if total_cost(case, sheet, t.standard) >= total_cost(case, base_sheet, t.standard):
        return None
    out = copy.copy(v0)
    out.term_sheets = [sheet, base_sheet][: shield.MAX_SHEETS]
    out.intent = "firm, constructive: offer faster payment against a lower price"
    return out


def generate(case, t: ThreadState, policy: Policy, v0, rival_best_c=math.inf, claims=(), ctx=None):
    """Candidates for this thread's move. `v0` is V0's Decision on a copy of `t` (the caller keeps
    the copy to commit V0's state); `claims` are verified claims the writer may use (SCOUT)."""
    sid = t.supplier_id
    ctx = ctx or {}
    out = [_candidate("v0", "v0", v0, sid)]
    theirs = t.standing_terms.get("unit_price")
    can_talk = t.status == "open" and t.rounds_left > 1 and theirs is not None and v0.kind == "send"

    if can_talk:
        p = policy.p
        for m in STEPS if t.our_prices else OPEN_FRACS:
            tc = copy.deepcopy(t)
            if t.our_prices:
                price = policy.next_price(tc, theirs, step=min(0.95, p["concede"] * m))
            else:
                price = Policy({**p, "open_frac": min(0.95, p["open_frac"] * m)}).next_price(tc, theirs)
            d = policy.offer(case, tc, price, intent=v0.intent, rival_best_c=rival_best_c)
            out.append(_candidate(f"price_step:{m}", "price_step", d, sid))
        if _cash_signal(t) and v0.term_sheets:
            d = _cash_trade(case, policy, t, v0.term_sheets[0], v0)
            if d is not None:
                out.append(_candidate("cash_trade", "cash_trade", d, sid))

    if v0.kind != "accept" and t.standing_id and theirs is not None:
        c = policy.cost(case, t)
        if policy.acceptable(case, t, c, rival_best_c):
            out.append(_candidate("accept", "accept", policy.accept(t), sid))
    if v0.kind != "walk":
        out.append(_candidate("walk", "walk", type(v0)("walk", sid), sid))

    if claims:  # the same verified claims ride on every "send" candidate; the shield checks them
        for cand in out:
            if cand.kind == "send" and not cand.claims:
                cand.claims = list(claims)
    return finish(case, t, out, ctx)


def finish(case, t: ThreadState, cands, ctx):
    """Cost, validate and de-duplicate."""
    c_open = t.opening_cost if t.opening_cost is not None else total_cost(case, t.standing_terms, t.standard)
    c_standing = total_cost(case, t.standing_terms, t.standard)
    full_ctx = {"standing_id": t.standing_id, "standing_terms": t.standing_terms, "standard": t.standard,
                "profile": t.profile, **ctx}  # fmt: skip
    seen, out = set(), []
    for cand in cands:
        key = (cand.kind, cand.accept_sheet_id, tuple(tuple(sorted(s.items(), key=str)) for s in cand.term_sheets))
        if key in seen:
            continue
        seen.add(key)
        if cand.kind == "send" and cand.term_sheets:
            terms = cand.term_sheets[0]
        elif cand.kind == "accept":
            terms = t.standing_terms
        else:
            terms = None
        if terms is not None:
            f = shield.cost_features(case, terms, t.standard, t.profile, c_open)
            cand.buyer_cost, cand.saving_vs_open = f["buyer_cost"], f["saving_vs_open"]
            cand.improvement_vs_alternative = f["improvement_vs_alternative"]
            margin = f["supplier_margin_pct"]
        else:  # walk: the alternative
            c_alt = shield.alternative_cost(case)
            cand.buyer_cost = c_alt
            cand.saving_vs_open = None if c_alt == math.inf else round(c_open - c_alt, 2)
            cand.improvement_vs_alternative = 0.0 if c_alt < math.inf else None
            margin = None
        cand.features = features(case, t, cand, c_open, c_standing, margin)
        cand.rejection_reasons = shield.validate(case, cand, full_ctx)
        cand.valid = not cand.rejection_reasons
        out.append(cand)
    return out


def features(case, t: ThreadState, cand, c_open, c_standing, margin) -> dict:
    """The fixed state x candidate feature schema the ranker reads (stable names, unitless)."""
    scale = c_open if c_open and c_open not in (math.inf, 0) else 1.0
    floor = (t.profile or {}).get("floor_estimate")
    price = cand.term_sheets[0].get("unit_price") if cand.term_sheets else None
    cost = cand.buyer_cost if cand.buyer_cost not in (None, math.inf) else None
    return {
        "kind": cand.kind,
        "family": cand.family,
        "saving_vs_standing": 0.0 if cost is None else (c_standing - cost) / scale,
        "price_vs_floor": 0.0 if not (floor and price) else (price - floor) / floor,
        "rounds_left": t.rounds_left,
        "rounds_left_frac": t.rounds_left / max(1, case.get("round_limit", 10)),
        "status_final": t.status == "final_offer",
        "cash_pressure": float((t.profile or {}).get("cash_pressure") or 0.0),
        "floor_known": bool(floor),
        "floor_confidence": float((t.profile or {}).get("floor_confidence") or 1.0),
        "supplier_margin_pct": -1.0 if margin is None else float(margin),
        "n_sheets": len(cand.term_sheets),
        "n_claims": len(cand.claims),
        "alternative_known": shield.alternative_cost(case) < math.inf,
    }
