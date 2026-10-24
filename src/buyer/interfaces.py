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
