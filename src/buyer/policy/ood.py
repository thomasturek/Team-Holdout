"""THE ANALYST, Phase 2 (A3): how far can the ranker be trusted in this state?

`assess` starts from full confidence and only subtracts: every missing input, unfamiliar case
feature, ensemble disagreement or disagreement with V0 lowers it and names a reason. More
uncertainty therefore never raises confidence (V3 invariant 8). The routing (`v2.py`) uses
HIGH / MEDIUM. Familiar = what the simulator and the practice runs cover; widen the sets only with
evidence from training on such cases.
"""

from __future__ import annotations

HIGH = 0.75  # at or above: the ranker's choice
MEDIUM = 0.5  # at or above: the ranker, restricted to conservative families; below: V0

FAMILIAR_TYPES = {"price_increase", "renewal", "rfq"}
FAMILIAR_FIELDS = {"unit_price", "payment_days", "lead_time_days", "contract_months", "incoterm", "volume_per_year"}
FAMILIAR_GOALS = {"stabilise", "secure_supply", "quality_first", "leverage", "routine"}
KNOWN_ARCHETYPES = {"family_foundry", "group_ladder", "cash_short_jobshop", "near_monopolist"}

PENALTY = {
    "no floor estimate": 0.4,
    "rough floor estimate": 0.15,
    "unknown archetype": 0.1,
    "unfamiliar case type": 0.5,
    "unfamiliar negotiable field": 0.3,
    "unfamiliar category goal": 0.2,
    "no standard terms": 0.15,
    "few valid candidates": 0.3,
    "ranker disagrees with V0 on the action": 0.3,
}
DISAGREEMENT_WEIGHT = 0.5  # x share of ensemble members with another winner


def assess(case, t, ranked, disagreement, v0) -> tuple[float, list[str]]:
    reasons = []
    profile = t.profile or {}
    if not profile.get("floor_estimate"):
        reasons.append("no floor estimate")
    elif (profile.get("floor_confidence") or 1.0) > 0.15:
        reasons.append("rough floor estimate")
    if profile.get("archetype") not in KNOWN_ARCHETYPES:
        reasons.append("unknown archetype")
    if case.get("type") not in FAMILIAR_TYPES:
        reasons.append("unfamiliar case type")
    if set(case.get("negotiable") or []) - FAMILIAR_FIELDS:
        reasons.append("unfamiliar negotiable field")
    if (case.get("buyer") or {}).get("category_goal") not in FAMILIAR_GOALS:
        reasons.append("unfamiliar category goal")
    if not t.standard and not profile.get("standard_terms"):
        reasons.append("no standard terms")
    if len(ranked) < 2:
        reasons.append("few valid candidates")
    if ranked and ranked[0][0].kind != v0.kind:
        reasons.append("ranker disagrees with V0 on the action")
    confidence = 1.0 - sum(PENALTY[r] for r in reasons)
    if disagreement > 0:
        reasons.append(f"ensemble disagreement {disagreement:.2f}")
        confidence -= DISAGREEMENT_WEIGHT * disagreement
    return max(0.0, min(1.0, round(confidence, 3))), reasons
