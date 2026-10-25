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

from arena_kit.cost import RELATIONSHIP_GOALS, must_haves_ok, supplier_value, total_cost

DEFAULT_RATE = 0.08
FULL_COST_FACTOR = 0.98  # arena full cost / our data estimate, from the logged charges (P01, P02, P03)
SURE_SOURCES = ("should_cost",)  # data estimates good enough to price the charge (supplier-specific)

# what a supplier asks for (the reader's `asks`, src/buyer/llm/README.md) as a term and a direction
ASK_LEVERS = {
    "faster_payment": ("payment_days", "down"),
    "volume": ("volume_per_year", "up"),
    "longer_contract": ("contract_months", "up"),
    "earlier_effective_date": ("effective_date", "down"),
    "index_clause": ("index_clause", "on"),
    "longer_lead_time": ("lead_time_days", "up"),
    "incoterm": ("incoterm", "any"),
}

# a cost driver the supplier blames (reader `cost_drivers_claimed`) and the index series a clause on it follows
DRIVER_SERIES = {
    "copper": ("CU-",),
    "nickel": ("AS-",),
    "alloy": ("AS-",),
    "stainless": ("AS-",),
    "steel": ("PPI-C24",),
    "raw_material": ("CU-", "AS-", "PPI-C24"),
}


def relationship_case(case: dict) -> bool:
    b = case.get("buyer") or {}
    return b.get("category_goal") in RELATIONSHIP_GOALS and bool(b.get("relationship_eur_per_point")) \
        and bool(b.get("sustainable_margin_pct"))


def supplier_estimate(case: dict, profile: dict | None, standard: dict | None = None,
                      sure_only: bool = True) -> dict | None:
    """What arena_kit.cost needs to price the relationship term, or None without a sure full cost.
    ``standard``: the supplier's standard terms from its quote PDF once the session has them; before
    that its master-data terms (``vendor_terms``), then the buyer's plan. ``sure_only=False`` takes
    any estimate - good enough to rank what a term is worth to the supplier, not to price the charge."""
    profile = profile or {}
    full_cost = profile.get("full_cost_observed")
    if not full_cost:
        estimate = profile.get("floor_computed") or profile.get("floor_estimate")
        source = profile.get("floor_computed_source") or profile.get("floor_source")
        if not estimate or (sure_only and source not in SURE_SOURCES):
            return None
        full_cost = FULL_COST_FACTOR * estimate
    b = case["buyer"]
    freight = b.get("freight_eur_per_unit") or {}
    vendor = {k: v for k, v in (profile.get("vendor_terms") or {}).items() if v is not None}
    std = {**vendor, **{k: v for k, v in (standard or {}).items() if v is not None}}
    std.setdefault("payment_days", b["reference_payment_days"])
    if std.get("incoterm") not in freight:  # an unknown Incoterm: the case's fixed one, else the dearest
        std["incoterm"] = (case.get("fixed_terms") or {}).get("incoterm") or max(freight, key=freight.get)
    rate = profile.get("interest_rate_observed")  # fitted from the charges we paid (supplier memory)
    if rate is None:
        rate = profile.get("cash_rate_estimate") or DEFAULT_RATE
    return {"full_cost": full_cost, "interest_rate": rate,
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


def asked(lever: dict, terms: dict, asks) -> bool:
    """Does switching ``lever`` (an item of lever_values) give the supplier something it asked for?"""
    for ask in asks or ():
        field, direction = ASK_LEVERS.get(ask, (None, None))
        if field != lever["field"]:
            continue
        old, new = terms.get(field), lever["option"]
        if direction == "on":
            return new is not None
        if direction == "any":
            return True
        if old is None or new is None:
            continue
        if (direction == "up" and new > old) or (direction == "down" and new < old):
            return True
    return False


def lever_values(case: dict, terms: dict, standard: dict | None = None, profile: dict | None = None) -> list[dict]:
    """Every other allowed value of every negotiable term (case `term_options`) next to ``terms``:

        field, option   the switch
        delta_c         what it costs us in EUR of C at the same price (< 0: it saves us money)
        sheet           ``terms`` with the switch, priced so that our C stays the same (the price change from
                        the plain cost slope; the relationship charge only enters ``delta_c``)
        supplier_gain   what that equal-cost sheet is worth to the supplier per unit, in cash
                        (arena_kit.cost.supplier_value: payment days, freight, tooling, chargeback;
                        contract length, volume and an index clause are security, not cash: 0)
        must_haves_ok   the equal-cost sheet keeps the case's must-haves

    A switch with ``supplier_gain`` > 0 costs us nothing and is worth something to the supplier: the
    trade to offer when it holds. One it asked for (``asked``) is worth offering at equal cost too."""
    base = c(case, terms, standard, profile)
    est = supplier_estimate(case, profile, standard, sure_only=False)
    worth = supplier_value(case, terms, est) if est else None
    out = []
    for field, options in (case.get("term_options") or {}).items():
        if field == "unit_price" or field not in case.get("negotiable", ()) or not options:
            continue
        for option in options:
            if option == terms.get(field):
                continue
            switched = {**terms, field: option}
            c_switched = c(case, switched, standard, profile)
            delta = c_switched - base
            # EUR of C per EUR of price at the switched terms (a volume switch changes it) - the plain cost:
            # near the relationship knee the charge distorts the slope (P02: EUR 722 instead of 6,110 per EUR)
            up = {**switched, "unit_price": terms["unit_price"] + 1}
            slope = total_cost(case, up, standard) - total_cost(case, switched, standard)
            sheet = None
            if slope > 0:
                price = round(terms["unit_price"] - delta / slope, 2)
                sheet = {**switched, "unit_price": price} if price > 0 else None
            gain = supplier_value(case, sheet, est) - worth if est and sheet else None
            out.append({"field": field, "option": option, "delta_c": round(delta, 2), "sheet": sheet,
                        "supplier_gain": None if gain is None else round(gain, 4),
                        "must_haves_ok": bool(sheet) and must_haves_ok(case, sheet, standard)})
    return out


def clause_wanted(case: dict, signals: dict | None) -> bool:
    """The supplier blames a cost driver that an index clause allowed in this case would follow - its
    risk is the clause's subject, so offering the clause answers it (P02 2026-10-24: Nordmark argued
    copper in every reply, CU-NOTATION clauses were negotiable, we never offered one)."""
    claimed = [str(x) for x in (signals or {}).get("cost_drivers_claimed") or []]
    series = {o["series"] for o in (case.get("term_options") or {}).get("index_clause") or [] if o}
    if "index_clause" not in case.get("negotiable", ()) or not series or not claimed:
        return False
    for word in claimed:
        if word in series:
            return True
        prefixes = DRIVER_SERIES.get(word.lower(), ())
        if any(sr.startswith(pre) for sr in series for pre in prefixes):
            return True
    return False
