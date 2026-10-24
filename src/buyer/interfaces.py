"""The contracts between the roles - AGENTS.md section 3, copied field for field.

Change a field only with the agreement of both sides and update AGENTS.md in the same commit.
Plain dataclasses, no logic: every role imports from here, so there are no circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SupplierProfile:  # SCOUT -> ANALYST, DIPLOMAT
    supplier_id: str
    name: str
    country: str
    owner_type: str  # family | group | ... (supplier_intel)
    archetype: str  # family_foundry | group_ladder | cash_short_jobshop | near_monopolist | unknown
    floor_estimate: float | None  # EUR per price_unit: full cost (should_cost x country factor, or derived)
    floor_confidence: float  # relative error, e.g. 0.05 / 0.15
    cash_rate_estimate: float  # what money is worth to it per year (>= 0.08 when cash-short)
    cash_pressure: float  # 0..1 from equity ratio, credit index trend, our late payments, notes
    approval_style: str  # flat | ladder
    cost_drivers: list[dict]  # [{series, weight, change_12m_pct, ids: (from, to)}]
    history: dict  # past asked vs settled changes (negotiation_history)
    quality: dict  # latest scorecard: otd_pct, ppm, colour, ids
    notes: list[str]  # short findings from correspondence and news, with doc/news IDs
    standard_terms: dict  # from the quote PDF once the session is open


@dataclass
class Claim:  # SCOUT -> DIPLOMAT (via ANALYST)
    key: str  # e.g. "index:PPI-D351", "rival_quote:70140", "notice:doc+ctr"
    sentence: str  # final English sentence, figure and IDs included, verified offline
    refs: list[str]
    expected: str  # "verified"
    strength: float  # 0..1 prior from the SCOUT; only the ANALYST uses it to choose


@dataclass
class Signals:  # DIPLOMAT (reader) -> ANALYST
    cash_pressure: bool
    capacity_issue: bool
    final_offer_language: bool
    approval_pending: bool
    cost_drivers_claimed: list[str]  # series or words the supplier blames
    accepted_args: list[str]  # what it said "fair point" to
    rejected_args: list[str]  # "not our reality"
    asks: list[str]  # what it wants: volume, longer contract, faster payment, earlier date...
    offered_variants: list[str]  # cheaper engineering variants etc. (information only)
    tone: str  # warm | neutral | irritated


@dataclass
class Decision:  # ANALYST -> DIPLOMAT, OPERATOR
    kind: str  # "send" | "accept" | "walk"
    supplier_id: str
    term_sheets: list[dict]  # complete, snapped (complete_offer); empty for accept/walk
    accept_sheet_id: str | None
    claims: list[Claim]  # <= 3, never one already used in this case for this supplier
    questions: list[str]  # e.g. "cost breakdown", "earliest lead time"
    intent: str  # one line for the writer: "firm, appreciative, signal alternatives"


# --- Phase 2 (docs/PHASE2_SAFE_ARCHITECTURE.md): code generates safe candidates, ML ranks them ---


@dataclass
class CandidateAction:  # ANALYST (generator) -> SCOUT (shield) -> ANALYST (ranker)
    candidate_id: str  # e.g. "v0", "price_step:0.5", "cash_trade", "accept", "walk"
    kind: str  # send | accept | walk
    supplier_id: str
    term_sheets: list[dict]  # complete, snapped; empty for accept / walk
    claims: list[Claim]
    questions: list[str]
    intent: str
    buyer_cost: float | None  # C of the primary sheet (send), the standing offer (accept), the alternative (walk)
    saving_vs_open: float | None  # C_open - buyer_cost
    improvement_vs_alternative: float | None  # C_alternative - buyer_cost (> 0: beats it)
    supplier_value_estimate: float | None  # EUR per unit the deal is worth to the supplier (our estimate)
    features: dict[str, float | int | str | bool]
    valid: bool  # passed the SCOUT's shield
    rejection_reasons: list[str]
    accept_sheet_id: str | None = None  # accept only
    family: str = ""  # v0 | price_step | cash_trade | accept | walk


@dataclass
class PolicySelection:  # ANALYST -> OPERATOR (logged), DIPLOMAT gets only .decision
    decision: Decision
    policy_source: str  # v2_ml | v2_conservative | v0_fallback | v0_rule
    confidence: float  # 0..1; more uncertainty never raises it
    ood_reasons: list[str]
    ranked_candidates: list[dict]  # every candidate: id, family, kind, cost, value, valid, reasons
    reason: str = ""  # why this candidate was selected
