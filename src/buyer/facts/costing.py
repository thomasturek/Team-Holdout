"""Costing with the relationship term (SCOUT): what a deal costs us when the supplier's health counts.

In `stabilise` and `secure_supply` cases the arena charges `relationship_eur_per_point` for every
margin point a deal leaves the supplier below `sustainable_margin_pct` (arena_kit.cost). That term
needs an estimate of the supplier - without one `total_cost` counts it as 0, and a policy squeezing
a strategic supplier never sees the bill (P01 paid EUR 615, P03 EUR 630 on 2026-10-24).

    from buyer.facts.costing import c, relationship_floor, supplier_estimate
    c(case, terms, standard, profile)                    # C in EUR, relationship term included
    relationship_floor(case, terms, standard, profile)   # unit price below which C rises again, or None

The estimate: full cost = the full cost implied by a charge we paid this supplier (supplier memory,
`full_cost_observed`), else FULL_COST_FACTOR x the profile's data estimate (`floor_computed`, else
`floor_estimate`) - never the observed best price, which already has the charge priced in.

The charge is steep and quadratic in the margin gap: 2 % too much full cost is about 2 margin points,
and turned P01's logged EUR 615 into EUR 10,316. FULL_COST_FACTOR comes from the logged charges
(2026-10-24): the arena's full cost was 98.0 % of our estimate in P01, 98.5 % in P03, and P02's
zero charge needs at most 98.6 %.

Only a sure full cost counts: one a charge revealed, or a supplier-specific should-cost (+-5 %; 1.5-2 %
off in practice). The knee is so steep that a rough one does harm - in the simulator, seeing the
charge raised the score with a full cost off by 0-2 % (0.650 -> 0.663) and cut it with 8 % (-> 0.570).
Market-price and country-factor estimates (+-10-15 %) are left out: the charge counts 0, as before.
"""

from __future__ import annotations

from arena_kit.cost import RELATIONSHIP_GOALS, total_cost

DEFAULT_RATE = 0.08
FULL_COST_FACTOR = 0.98  # arena full cost / our data estimate, from the logged charges (P01, P02, P03)
SURE_SOURCES = ("should_cost",)  # data estimates good enough to price the charge (supplier-specific)


def relationship_case(case: dict) -> bool:
    b = case.get("buyer") or {}
    return b.get("category_goal") in RELATIONSHIP_GOALS and bool(b.get("relationship_eur_per_point")) \
        and bool(b.get("sustainable_margin_pct"))


def supplier_estimate(case: dict, profile: dict | None, standard: dict | None = None) -> dict | None:
    """What arena_kit.cost needs to price the relationship term, or None without a sure full cost.
    ``standard``: the supplier's standard terms from its quote PDF once the session has them; before
    that its master-data terms (``vendor_terms``), then the buyer's plan."""
    profile = profile or {}
    full_cost = profile.get("full_cost_observed")
    if not full_cost:
        estimate = profile.get("floor_computed") or profile.get("floor_estimate")
        source = profile.get("floor_computed_source") or profile.get("floor_source")
        if not estimate or source not in SURE_SOURCES:
            return None
        full_cost = FULL_COST_FACTOR * estimate
    b = case["buyer"]
    freight = b.get("freight_eur_per_unit") or {}
    vendor = {k: v for k, v in (profile.get("vendor_terms") or {}).items() if v is not None}
    std = {**vendor, **{k: v for k, v in (standard or {}).items() if v is not None}}
    std.setdefault("payment_days", b["reference_payment_days"])
    if std.get("incoterm") not in freight:  # an unknown Incoterm: the case's fixed one, else the dearest
        std["incoterm"] = (case.get("fixed_terms") or {}).get("incoterm") or max(freight, key=freight.get)
    return {"full_cost": full_cost, "interest_rate": profile.get("cash_rate_estimate") or DEFAULT_RATE,
            "standard": std}


def c(case: dict, terms: dict, standard: dict | None = None, profile: dict | None = None) -> float:
    """C in EUR (arena_kit.cost.total_cost) with the relationship term priced from our estimate of
    the supplier; outside stabilise / secure_supply, or without an estimate, plain total_cost."""
    supplier = supplier_estimate(case, profile, standard) if relationship_case(case) else None
    return total_cost(case, terms, standard, supplier)


def relationship_floor(case: dict, terms: dict, standard: dict | None = None,
                       profile: dict | None = None) -> float | None:
    """The unit price (at ``terms``' other terms) that minimises C: below it every euro off the price
    costs more in relationship charge than it saves. None outside stabilise / secure_supply, without
    an estimate, or when the charge never binds above half the full cost."""
    if not relationship_case(case):
        return None
    supplier = supplier_estimate(case, profile, standard)
    if supplier is None:
        return None

    def cost(price):
        return total_cost(case, {**terms, "unit_price": price}, standard, supplier)

    lo, hi = 0.5 * supplier["full_cost"], 2.0 * supplier["full_cost"]
    for _ in range(100):  # C is convex in the price: linear spend plus a convex charge below the margin
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if cost(m1) < cost(m2):
            hi = m2
        else:
            lo = m1
    best = round((lo + hi) / 2, 2)
    return None if best <= 0.5 * supplier["full_cost"] + 0.01 else best
