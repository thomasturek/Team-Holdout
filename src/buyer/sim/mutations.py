"""THE ANALYST, V3 (docs/V3_ROBUSTNESS_PLAN.md, mutation catalog): programmatic adversarial cases.

    adversarial(parent_case, seed) -> AdversarialCase      one mutation, chosen and parameterised by seed
    MUTATIONS                                              name -> (family, distribution, operator)

An operator returns (case, overrides, properties, expected_policy). `overrides` change the synthetic
supplier ({"supplier": {SupplierParams field: value}}) or what we believe about it ({"profile":
{...}}), or ask the harness to set the alternative relative to the supplier's opening quote
({"alt_vs_opening": 0.0001} = 0.01 % above it). Everything is reproducible from (parent, seed).
"""

from __future__ import annotations

import copy
import random

from ..facts.case_check import check
from ..interfaces import AdversarialCase

VERSION = "v3.0"
UNSEEN_TYPE = "spot_buy"  # a case type no training case has: must fall back

ALWAYS = ["no_exception", "no_invalid_sheet", "must_not_break_must_have", "must_not_accept_worse_than_alternative"]


def _buyer(case):
    return case["buyer"]


# --- boundary --------------------------------------------------------------------------------------------
def alt_just_above(case, rng):
    """The alternative costs 0.01 % more than the supplier's opening: accepting the opening is barely ok."""
    return case, {"alt_vs_opening": 0.0001}, [], None


def alt_just_below(case, rng):
    """The alternative costs 0.01 % less than the opening: the opening must never be accepted as is."""
    return case, {"alt_vs_opening": -0.0001}, ["must_not_accept_opening"], None


def must_have_at_boundary(case, rng):
    """A must-have exactly at one of the allowed payment terms."""
    days = (case.get("term_options") or {}).get("payment_days")
    if not days or "payment_days" not in case["negotiable"]:
        return None
    c = copy.deepcopy(case)
    _buyer(c)["must_haves"] = [*_buyer(c).get("must_haves", []),
                               {"field": "payment_days", "op": ">=", "value": rng.choice(days)}]  # fmt: skip
    return c, {}, [], None


def reference_payment_shift(case, rng):
    """reference_payment_days one day off a term option (59 / 61 when 60 is the option)."""
    c = copy.deepcopy(case)
    _buyer(c)["reference_payment_days"] = _buyer(c)["reference_payment_days"] + rng.choice((-1, 1))
    return c, {}, [], None


def last_rounds_only(case, rng):
    """Two or three rounds: no long probing."""
    c = copy.deepcopy(case)
    c["round_limit"] = rng.choice((2, 3))
    return c, {}, ["must_close_within_round_limit"], None


# --- preference reversals (the supplier differs from what we believe) -----------------------------------
def cash_stressed_rejects_early_payment(case, rng):
    return case, {"profile": {"cash_pressure": 0.9, "cash_rate_estimate": 0.25},
                  "supplier": {"cash_rate": 0.0, "insist_payment": True}}, [], None  # fmt: skip


def strong_supplier_values_cash(case, rng):
    return case, {"profile": {"cash_pressure": 0.0, "cash_rate_estimate": 0.04},
                  "supplier": {"cash_rate": 0.35}}, [], None  # fmt: skip


def impatient_supplier(case, rng):
    return case, {"supplier": {"patience": 0, "walk_after_final": 1.0}}, [], None


def stubborn_ladder(case, rng):
    return case, {"supplier": {"concede": 0.02, "approval_step_pct": 0.3}}, [], None


# --- familiar-looking traps ------------------------------------------------------------------------------
def walk_away_optimal(case, rng):
    """The alternative beats anything the supplier can reach: no deal is the right answer."""
    return case, {"alt_vs_opening": -0.35}, ["must_not_accept_worse_than_alternative"], None


def floor_overestimated(case, rng):
    """Our floor estimate is 30 % too high: we would concede too early."""
    return case, {"profile_floor_factor": 1.3}, [], None


def floor_underestimated(case, rng):
    """Our floor estimate is 30 % too low: we would ask for the impossible."""
    return case, {"profile_floor_factor": 0.7}, [], None


# --- missing and corrupted context ----------------------------------------------------------------------
def no_floor(case, rng):
    props = ["confidence_must_not_rise", "must_fallback_or_conservative"]
    return case, {"profile": {"floor_estimate": None}}, props, None


def no_profile(case, rng):
    return case, {"profile_replace": {}}, ["confidence_must_not_rise", "must_fallback"], "fallback"


def rough_floor(case, rng):
    return case, {"profile": {"floor_confidence": 0.4}}, ["confidence_must_not_rise"], None


# --- far OOD ---------------------------------------------------------------------------------------------
def unseen_case_type(case, rng):
    c = copy.deepcopy(case)
    c["type"] = UNSEEN_TYPE
    c["case_id"] = c["case_id"]  # the validators reject undocumented types; kept on purpose (far_ood)
    return c, {}, ["must_fallback"], "fallback"


def extreme_volume(case, rng):
    """Need x50: far outside every training case."""
    c = copy.deepcopy(case)
    _buyer(c)["need_per_year"] = _buyer(c)["need_per_year"] * 50
    return c, {"profile": {"floor_estimate": None}}, ["must_fallback"], "fallback"


MUTATIONS = {
    "alt_just_above": ("boundary", "near_ood", alt_just_above),
    "alt_just_below": ("boundary", "near_ood", alt_just_below),
    "must_have_at_boundary": ("boundary", "in_distribution", must_have_at_boundary),
    "reference_payment_shift": ("boundary", "in_distribution", reference_payment_shift),
    "last_rounds_only": ("boundary", "far_ood", last_rounds_only),  # every training case has 10 rounds
    "cash_stressed_rejects_early_payment": ("conflicting", "near_ood", cash_stressed_rejects_early_payment),
    "strong_supplier_values_cash": ("conflicting", "near_ood", strong_supplier_values_cash),
    "impatient_supplier": ("sequence", "near_ood", impatient_supplier),
    "stubborn_ladder": ("sequence", "near_ood", stubborn_ladder),
    "walk_away_optimal": ("trap", "near_ood", walk_away_optimal),
    "floor_overestimated": ("trap", "near_ood", floor_overestimated),
    "floor_underestimated": ("trap", "near_ood", floor_underestimated),
    "no_floor": ("missing", "near_ood", no_floor),
    "no_profile": ("missing", "far_ood", no_profile),
    "rough_floor": ("missing", "near_ood", rough_floor),
    "unseen_case_type": ("extreme", "far_ood", unseen_case_type),
    "extreme_volume": ("extreme", "far_ood", extreme_volume),
}
# the portfolio of the plan: property/boundary 40 %, near-OOD 30 %, conflicting 15 %, missing 10 %, extreme 5 %
WEIGHTS = {"boundary": 0.40, "trap": 0.15, "sequence": 0.15, "conflicting": 0.15, "missing": 0.10, "extreme": 0.05}


def pick(rng) -> str:
    family = rng.choices(list(WEIGHTS), list(WEIGHTS.values()))[0]
    return rng.choice([n for n, (f, _, _) in MUTATIONS.items() if f == family])


def adversarial(parent, seed, name=None) -> AdversarialCase | None:
    """One adversarial case from `parent`, reproducible from (parent, seed[, name]); None if the
    mutation does not apply to this parent."""
    rng = random.Random(seed)
    name = name or pick(rng)
    family, dist, op = MUTATIONS[name]
    out = op(copy.deepcopy(parent), rng)
    if out is None:
        return None
    case, overrides, props, expected_policy = out
    case = {**case, "case_id": f"{parent['case_id']}~{name}#{seed}"}
    validation = check(case)
    if dist != "far_ood" and (validation["schema"] or validation["economic"]):
        return None  # gate 1 / 2: only far-OOD tests may break the documented schema
    return AdversarialCase(
        case_id=case["case_id"], parent_case_id=parent["case_id"], generator="programmatic",
        generator_version=VERSION, seed=seed, mutations=[name], distribution=dist, case=case,
        scripted_responses=[overrides], expected_properties=list(dict.fromkeys(ALWAYS + props)),
        expected_policy=expected_policy, validation=validation,
    )  # fmt: skip
