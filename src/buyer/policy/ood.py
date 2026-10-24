"""THE ANALYST, Phase 2 (A3) + V3: how far can the ranker be trusted in this state?

`assess` -> (confidence, reasons, cap).
  confidence  from the inputs only: starts at 1 and every missing input, unfamiliar case feature or
              distance from the training cases subtracts and names a reason. Less evidence can
              therefore never raise it (V3 invariant 8) - by construction, whatever the model does.
  cap         the model's own doubts (ensemble disagreement, disagreeing with V0 on the action, too
              few valid candidates) cap the route at "conservative" or "fallback"; they can only make
              it more cautious. (A first version subtracted them from confidence: the V3 metamorphic
              test caught a rougher floor estimate raising confidence through a calmer ensemble.)
The routing (`v2.py`) uses HIGH / MEDIUM and the cap. Familiar = the case types, fields and goals of
the cases the simulator trains on (`familiar()`); a hidden case outside them falls back.
"""

from __future__ import annotations

import math
import statistics

HIGH = 0.75  # at or above: the ranker's choice
MEDIUM = 0.5  # at or above: the ranker, restricted to conservative families; below: V0

# Without training cases on disk (fresh machine): the kit simulator's coverage
FAMILIAR_TYPES = {"price_increase", "renewal", "rfq"}
FAMILIAR_FIELDS = {"unit_price", "payment_days", "lead_time_days", "contract_months", "incoterm", "volume_per_year"}
FAMILIAR_GOALS = {"leverage", "routine"}
_familiar = None


def familiar():
    """(types, fields, goals) the simulator trains on: the kit's cases plus runs/cases (practice,
    sandbox). Computed once; the constants above if no case file can be read."""
    global _familiar
    if _familiar is None:
        try:
            from ..sim.env import load_cases

            cases = load_cases()
        except Exception:
            cases = []
        if cases:
            _familiar = ({c.get("type") for c in cases}, {f for c in cases for f in c.get("negotiable") or []},
                         {(c.get("buyer") or {}).get("category_goal") for c in cases})  # fmt: skip
        else:
            _familiar = (FAMILIAR_TYPES, FAMILIAR_FIELDS, FAMILIAR_GOALS)
    return _familiar
KNOWN_ARCHETYPES = {"family_foundry", "group_ladder", "cash_short_jobshop", "near_monopolist"}

PENALTY = {  # tuned on the V3 development suite (tests/generated/development), never on the locked one
    "no supplier profile": 0.6,
    "no floor estimate": 0.4,
    "rough floor estimate": 0.15,
    "unknown archetype": 0.1,
    "unfamiliar case type": 1.0,  # alone enough to fall back
    "unfamiliar negotiable field": 0.6,
    "unfamiliar category goal": 0.2,
    "far from every training case": 0.6,
    "no standard terms": 0.15,
    "few valid candidates": 0.3,
    "ranker disagrees with V0 on the action": 0.3,
}
DOUBT_DISAGREEMENT = 0.4  # share of ensemble members with another winner: a doubt (route capped at conservative)
FALLBACK_DISAGREEMENT = 0.6  # ... this much: V0
# standardised distance to the nearest training case: the 24 training cases lie at most 1.91 from each
# other (leave-one-out, p90 1.18), so 2.2 is just outside everything the policy was trained on
FAR_DISTANCE = 2.2
NEAR_DISTANCE = 1.2
_train_vectors = None


def case_vector(case) -> list[float]:
    """What makes cases alike for the policy: size, price level, rounds, levers."""
    b = case.get("buyer") or {}
    ref = b.get("current_unit_price") or b.get("fallback_unit_price") or 1.0
    return [math.log(max(1.0, b.get("need_per_year") or 1.0)), math.log(max(0.01, ref)),
            float(case.get("round_limit", 10)), float(len(case.get("negotiable") or []))]  # fmt: skip


def distance_to_training(case) -> float:
    """Standardised distance to the nearest training case; 0 without training cases."""
    global _train_vectors
    if _train_vectors is None:
        try:
            from ..sim.env import load_cases

            vecs = [case_vector(c) for c in load_cases()]
        except Exception:
            vecs = []
        sd = [statistics.pstdev(col) or 1.0 for col in zip(*vecs, strict=True)] if len(vecs) > 1 else []
        _train_vectors = (vecs, sd)
    vecs, sd = _train_vectors
    if not vecs or not sd:
        return 0.0
    x = case_vector(case)
    return min(math.sqrt(sum(((a - b) / s) ** 2 for a, b, s in zip(x, v, sd, strict=True))) for v in vecs)


def assess(case, t, ranked, disagreement, v0) -> tuple[float, list[str]]:
    reasons = []
    profile = t.profile or {}
    if not profile:
        reasons.append("no supplier profile")
    if not profile.get("floor_estimate"):
        reasons.append("no floor estimate")
    elif (profile.get("floor_confidence") or 1.0) > 0.15:
        reasons.append("rough floor estimate")
    if profile.get("archetype") not in KNOWN_ARCHETYPES:
        reasons.append("unknown archetype")
    types, fields, goals = familiar()
    if case.get("type") not in types:
        reasons.append("unfamiliar case type")
    if set(case.get("negotiable") or []) - fields:
        reasons.append("unfamiliar negotiable field")
    if (case.get("buyer") or {}).get("category_goal") not in goals:
        reasons.append("unfamiliar category goal")
    if distance_to_training(case) > FAR_DISTANCE:
        reasons.append("far from every training case")
    if not t.standard and not profile.get("standard_terms"):
        reasons.append("no standard terms")
    confidence = max(0.0, min(1.0, round(1.0 - sum(PENALTY[r] for r in reasons), 3)))

    # the model's own doubts: they can only make the route more cautious (a cap), never raise confidence
    doubts = []
    if len(ranked) < 2:
        doubts.append("few valid candidates")
    if ranked and ranked[0][0].kind != v0.kind:
        doubts.append("ranker disagrees with V0 on the action")
    if disagreement >= DOUBT_DISAGREEMENT:
        doubts.append(f"ensemble disagreement {disagreement:.2f}")
    cap = "fallback" if len(doubts) >= 2 or disagreement >= FALLBACK_DISAGREEMENT else \
        "conservative" if doubts else "ml"
    return confidence, reasons + doubts, cap
