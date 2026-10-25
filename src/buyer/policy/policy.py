import itertools
import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

from arena_kit.cost import complete_offer, must_haves_ok, supplier_value, total_cost

from buyer.facts.costing import asked as lever_asked
from buyer.facts.costing import c as relationship_c
from buyer.facts.costing import clause_wanted, lever_values, relationship_case, relationship_floor

log = logging.getLogger("buyer.policy")
PARAMS_FILE = Path(__file__).with_name("params.json")
STRUCTURAL = ("index_clause",)
CASH_LEVERS = ("payment_days", "incoterm", "tooling_eur")  # where our estimate of the supplier's gain holds
MAX_TRADE_DROP = 0.05  # a lever costing us more than 5 % of the price is no trade the supplier would take

BOUNDS = {
    "open_frac": (0.0, 1.0),
    "concede": (0.05, 0.8),
    "floor_margin_pct": (0.0, 15.0),
    "accept_gap_pct": (0.0, 5.0),
    "cash_discount_pct": (0.0, 5.0),
    "push_final": (0.0, 1.0),
    "min_open_discount_pct": (1.0, 30.0),
    "rival_undercut_pct": (0.0, 5.0),
    "lead_standard": (0.0, 1.0),
    "reciprocity": (0.0, 1.5),
    "token_frac": (0.0, 0.6),
    "stall_limit": (1.0, 5.0),
    "endgame_moves": (0.0, 3.0),
    "endgame_frac": (0.0, 0.8),
    "accept_target_pct": (0.0, 10.0),
    "lever_trades": (0.0, 1.0),
}
DEFAULTS = {
    "open_frac": 0.3,
    "concede": 0.35,
    "floor_margin_pct": 4.0,
    "accept_gap_pct": 1.0,
    "cash_discount_pct": 1.5,
    "push_final": 0.0,
    "min_open_discount_pct": 4.0,
    "rival_undercut_pct": 1.0,
    "lead_standard": 0.0,
    "claims_per_msg": 2,
    "claim_min_strength": 0.2,
    "deep_open_pct": 20.0,
    # reciprocal concessions: our step follows the supplier's last step (in EUR of C), not the gap.
    # Practice 2026-10-24: suppliers held still in 51 % of their replies; we kept moving anyway.
    # Off by default (0 = the old fixed `concede` step): it only paid off in the simulator when the whole
    # set was retrained with it (sim/train.py tunes these keys) - switch on via params.json.
    "reciprocity": 0.0,  # our step per step of theirs (trained: about 1.1)
    "token_frac": 0.25,  # first round it holds: a token step (share of the old step) to keep it talking
    "stall_limit": 3,  # holds of theirs during which we hold too (and change the package instead)
    "endgame_moves": 1,  # moves left at which one bigger step is allowed
    "endgame_frac": 0.5,  # that step: share of the remaining gap
    "accept_target_pct": 0.0,  # accept at or below a sure floor x (1 + this); 0 = off (trained: about 2.3)
    # lever trades: when the supplier holds or asks for a term, offer that term at equal cost to us.
    # Practice 2026-10-25: every losing deal closed at the supplier's holding price; our sheets only ever
    # varied the payment days, while suppliers asked for volume, longer contracts, index clauses.
    "lever_trades": 1.0,  # > 0.5 = on
    "min_step_pct": 0.0,
}
DEEP_OPEN_TYPES = ("raw_material", "rfq")
ARCHETYPE_LEAD_EFFORT = {"near_monopolist": 0.005}
ARCHETYPE_RATE = {"cash_short_jobshop": 0.18, "group_ladder": 0.07, "near_monopolist": 0.07}
MENU_SPREAD = 0.003
MENU_COMBOS = 300
HOLD_JUMP = 0.5
MIN_STEP_GAP = 0.4
LONG_CONTRACT_TYPES = ("bundling", "capacity")
NEGOTIATES_DOWN = ("family_foundry",)
CLAUSE_WORTH = 0.04
FIRST_MESSAGE_CLAIMS = 3
WEAK_CLAIM = 0.2
CLAIM_WEIGHT = {"notice": 1.0, "ppm": 0.75, "rival": 0.7, "cost": 0.6, "news": 0.55, "index": 0.5, "fc": 0.45,
                "po": 0.3, "otd": 0.15}
OWN_PRICE_SLACK = 0.005
CASH_HUNGRY_RATE = 0.15


@dataclass
class Decision:

    kind: str
    supplier_id: str
    term_sheets: list = field(default_factory=list)
    accept_sheet_id: str | None = None
    claims: list = field(default_factory=list)
    questions: list = field(default_factory=list)
    intent: str = ""


@dataclass
class ThreadState:

    supplier_id: str
    standing_id: str | None
    standing_terms: dict
    status: str
    standard: dict
    rounds_left: int
    profile: dict = field(default_factory=dict)
    signals: dict = field(default_factory=dict)
    our_prices: list = field(default_factory=list)
    their_prices: list = field(default_factory=list)
    pushed_final: bool = False
    opening_cost: float | None = None
    opening_payment_days: int | None = None
    offers: list = field(default_factory=list)
    our_costs: list = field(default_factory=list)
    case_threads: dict | None = None
    alt: tuple | None = None
    mirrored: bool = False
    struct_seen: dict = field(default_factory=dict)
    last_sheet: dict | None = None
    case_type: str | None = None
    jumped: bool = False
    sent_prices: dict = field(default_factory=dict)
    dropped: bool = False  # we walked away from this bidder while others played on (no longer a rival)
    their_costs: list = field(default_factory=list)  # C of each standing offer, in order (reciprocity)
    seen_ids: list = field(default_factory=list)
    holds: int = 0  # replies in a row in which the supplier did not move towards us
    holding: bool = False  # this move we hold our price and change the package instead
    asked_breakdown: bool = False
    clause_countered: bool = False  # we offered its package with a wider index deadband once before closing


def floor_binds(t):
    return (t.profile or {}).get("archetype") not in NEGOTIATES_DOWN


def load_params(path=PARAMS_FILE):
    p = dict(DEFAULTS)
    if Path(path).is_file():
        p.update(json.loads(Path(path).read_text()))
    return p


def alternative_cost(case):
    alt = case["buyer"].get("alternative") or {}
    if alt.get("kind") in (None, "none") or not alt.get("terms", {}).get("unit_price"):
        return math.inf
    return total_cost(case, alt["terms"])


class Policy:
    def __init__(self, params=None):
        self.p = {**DEFAULTS, **(params if params is not None else load_params())}
        self.banks, self.used_refs, self.used_keys = {}, set(), set()

    def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
        p, sid = self.p, t.supplier_id
        theirs = t.standing_terms.get("unit_price")
        if t.status in ("walked_away", "no_bid") or theirs is None:
            return Decision("walk", sid)
        t.case_type = case.get("type")
        self.pick_offer(case, t)
        c_theirs = self.cost(case, t)
        if t.standing_id not in t.seen_ids:
            t.seen_ids.append(t.standing_id)
            t.their_costs.append(c_theirs)
        if t.opening_cost is None:
            t.opening_cost = c_theirs
            t.opening_payment_days = t.standing_terms.get("payment_days")
        acceptable = self.acceptable(case, t, c_theirs, rival_best_c)

        if t.status == "agreed":
            if acceptable:
                return self.accept(t)
            if self.eligible_cost(case, t, include_dropped=True) is not None and t.rounds_left > 1:
                # it agrees, but an eligible rival is cheaper: keep this bidder in play with a counter priced
                # against that rival instead of walking away from a valid fallback
                return self.offer(case, t, self.next_price(t, theirs, case=case), rival_best_c=rival_best_c)
            return Decision("walk", sid)
        if t.status == "final_offer":
            if p["push_final"] > 0.5 and not t.pushed_final and t.rounds_left > 1:
                t.pushed_final = True
                return self.offer(case, t, self.next_price(t, theirs, step=0.5, case=case), intent="final push")
            return self.close(case, t, acceptable, c_theirs, rival_best_c)
        if t.rounds_left <= 1:
            return self.accept(t) if acceptable else Decision("walk", sid)
        gap = 1 + p["accept_gap_pct"] / 100
        close = t.our_costs and self.c_track(case, t.standing_terms, t) <= t.our_costs[-1] * gap
        if close and acceptable and c_theirs < t.opening_cost:
            return self.close(case, t, acceptable, c_theirs, rival_best_c)
        if acceptable and self.at_target(case, t, c_theirs):
            return self.close(case, t, acceptable, c_theirs, rival_best_c)
        prev = t.last_sheet
        decision = self.offer(case, t, self.next_price(t, theirs, case=case), rival_best_c=rival_best_c)
        if prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding:
            return self.close(case, t, acceptable, c_theirs, rival_best_c)
        return decision

    def closing(self, case, threads: dict) -> Decision:
        best = None
        for t in threads.values():
            if t.status in ("walked_away", "no_bid") or not t.standing_id:
                continue
            self.pick_offer(case, t)
            c = self.eligible_cost(case, t, include_dropped=True)  # at the cap any live eligible offer beats none
            if c is not None and (best is None or c < best[0]):
                best = (c, t)
        if best is None:
            return Decision("walk", next(iter(threads)))
        return self.accept(best[1])

    def cost(self, case, t):
        return self.c(case, t.standing_terms, t)

    @staticmethod
    def c(case, terms, t):
        """C of ``terms`` in t's thread, with the relationship charge in stabilise / secure_supply cases
        (priced from the Scout's estimate of the supplier; 0 without one, as before)."""
        return relationship_c(case, terms, t.standard, t.profile)

    def eligible_cost(self, case, t, include_dropped=False):
        """C of t's standing offer if it could be accepted now, else None - the one rule for rivals,
        acceptance and the closing move: the thread is live (and, as a rival, not dropped by us), it has a
        standing offer with a price, the must-haves hold on its terms with the supplier's standard terms,
        and it beats the alternative."""
        if t.status in ("walked_away", "no_bid") or (t.dropped and not include_dropped):
            return None
        if not t.standing_id or t.standing_terms.get("unit_price") is None:
            return None
        if not must_haves_ok(case, t.standing_terms, t.standard):
            return None
        c = self.cost(case, t)
        return c if c < alternative_cost(case) else None

    def rival_best(self, case, threads, t):
        """The cheapest eligible standing offer among the other bidders (inf if none)."""
        costs = (self.eligible_cost(case, o) for o in threads.values() if o is not t)
        return min((c for c in costs if c is not None), default=math.inf)

    def acceptable(self, case, t, c_theirs, rival_best_c):
        return self.eligible_cost(case, t, include_dropped=True) is not None and c_theirs <= rival_best_c

    def accept(self, t):
        return Decision("accept", t.supplier_id, accept_sheet_id=t.standing_id)

    def floor_ask(self, t, theirs):
        floor = t.profile.get("floor_estimate") or theirs * 0.85
        return floor * (1 + self.p["floor_margin_pct"] / 100)

    def next_price(self, t, theirs, step=None, case=None):
        discount = self.p["min_open_discount_pct"]
        if t.case_type in DEEP_OPEN_TYPES:
            discount = max(discount, self.p["deep_open_pct"])
        low = min(self.floor_ask(t, theirs), theirs * (1 - discount / 100))
        if case is not None and floor_binds(t):  # stabilise / secure_supply: below it the charge costs more
            rel = relationship_floor(case, t.standing_terms, t.standard, t.profile)
            if rel is not None:
                low = min(max(low, rel), theirs)
        t.holding = False
        if not t.our_prices:
            price = low + self.p["open_frac"] * (theirs - low)
        else:
            last = t.our_prices[-1]
            price = last + (step * (theirs - last) if step is not None else self.concession(case, t, theirs, last))
        return round(min(max(price, low), theirs), 2)

    def concession(self, case, t, theirs, last):
        """Our step in unit price: as large as the supplier's last step towards us (x `reciprocity`,
        measured in EUR of C so a changed term counts), a token step the first time it holds, nothing
        while it keeps holding or steps back (we change the package instead), and one bigger step in
        the endgame. Without a case or with reciprocity 0: the old fixed share of the gap."""
        p, gap = self.p, theirs - last
        default = p["concede"] * gap
        if case is None or p["reciprocity"] <= 0 or len(t.their_costs) < 2:
            step = default
        else:
            slope = self.c(case, {**t.standing_terms, "unit_price": theirs + 1}, t) - t.their_costs[-1]
            move = (t.their_costs[-2] - t.their_costs[-1]) / slope if slope > 0 else 0.0  # their step, in price
            tol = 0.0005 * theirs
            if move > tol:
                t.holds = 0
                step = min(p["reciprocity"] * move, 0.5 * gap)
            else:
                t.holds += 1
                if move < -tol or 1 < t.holds <= round(p["stall_limit"]):
                    step, t.holding = 0.0, True
                else:
                    step = p["token_frac"] * default  # first hold, or a hold past the stall limit
            if t.rounds_left <= round(p["endgame_moves"]) + 1:
                step, t.holding = max(step, p["endgame_frac"] * gap), False
        if case is not None and not t.jumped and self.cash(t)[1] >= 0.5 and self.flat_replies(t) >= 2:
            step, t.holding, t.jumped = max(step, HOLD_JUMP * gap), False, True
        if not t.holding and gap > 0 and p["reciprocity"] <= 0:
            step = max(step, min(p["min_step_pct"] / 100 * theirs, MIN_STEP_GAP * gap))
        return step

    @staticmethod
    def flat_replies(t, tol=1.0):
        n = 0
        for prev, cur in zip(reversed(t.their_costs[:-1]), reversed(t.their_costs[1:]), strict=True):
            if cur < prev - tol:
                break
            n += 1
        return n

    def at_target(self, case, t, c_theirs):
        """Accept without haggling on when the offer is at or below a sure floor (observed, or a
        supplier-specific should-cost) x (1 + accept_target_pct). An unsure floor never decides."""
        prof = t.profile or {}
        floor = prof.get("floor_estimate")
        if not floor or (prof.get("floor_confidence") or 1.0) > 0.05 or self.p["accept_target_pct"] <= 0:
            return False
        target = {**t.standing_terms, "unit_price": floor * (1 + self.p["accept_target_pct"] / 100)}
        return c_theirs <= self.c(case, target, t)

    def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
        b = case["buyer"]
        base = {**t.standing_terms, "unit_price": price}
        if "payment_days" in case["negotiable"]:
            base["payment_days"] = b["reference_payment_days"]
        a = self.best_options(case, complete_offer(case, base), t.standard, skip={"payment_days"})
        a = self.adopt_structure(case, a, t)
        if rival_best_c < math.inf:
            c_a = self.c(case, a, t)
            target = rival_best_c * (1 - self.p["rival_undercut_pct"] / 100)
            if c_a > target:
                slope = self.c(case, {**a, "unit_price": a["unit_price"] + 1}, t) - c_a
                if slope > 0:
                    a = {**a, "unit_price": round(max(0.01, a["unit_price"] - (c_a - target) / slope), 2)}
        if t.standing_terms.get("unit_price") is not None:
            c_theirs = self.c(case, t.standing_terms, t)
            if self.c(case, a, t) > c_theirs:  # never ask for more than they already give us
                a = self.same_cost(case, a, t.standing_terms, t.standard)
        c_cap = self.c(case, t.standing_terms, t) if t.standing_terms.get("unit_price") is not None else math.inf
        sheets = self.menu(case, t, a, c_cap) or [a]
        if t.last_sheet is not None and sheets[0] == t.last_sheet:
            t.holding = True
        asks = list((t.signals or {}).get("asks") or [])
        if clause_wanted(case, t.signals) and "index_clause" not in asks and self.clause_worth(case, t) >= CLAUSE_WORTH:
            asks.append("index_clause")  # it blames the driver a clause would follow: offer the clause
        if self.p["lever_trades"] > 0.5 and (t.holding or asks):
            trades = [x for x in self.lever_trades(case, t, a, asks) if x not in sheets]
            if trades:
                sheets = [sheets[0], *trades[:2], *sheets[1:]]
                intent = f"{intent}; we can meet you on other terms"
        sheets = sheets[:3]
        questions = []
        notes = " ".join(str(n) for n in (t.profile or {}).get("notes") or []).lower()
        if not t.asked_breakdown and not t.our_prices and "calculation" in notes:
            questions, t.asked_breakdown = ["cost breakdown"], True
        if t.holding:  # same price: lead with another package, ask for its costs once
            k = t.holds % len(sheets)
            sheets = sheets[k:] + sheets[:k]
            intent = "firm on price, open on the other terms"
            if not t.asked_breakdown:
                questions, t.asked_breakdown = ["cost breakdown"], True
        sheets = [self.no_step_back(t, s) for s in sheets]
        t.last_sheet = sheets[0]
        t.our_prices.append(a["unit_price"])
        t.our_costs.append(min(self.c_track(case, s, t) for s in sheets))
        chosen = self.pick_claims(case, t)
        if any(c.key.startswith("rival:") for c in chosen):
            intent = f"{intent}, competition: another offer is on the table"
        return Decision("send", t.supplier_id, term_sheets=sheets, claims=chosen, questions=questions, intent=intent)

    def supplier_model(self, case, t):
        b = case["buyer"]
        std = {k: v for k, v in (t.standard or {}).items() if v is not None}
        std.setdefault("payment_days", t.opening_payment_days or b["reference_payment_days"])
        freight = b.get("freight_eur_per_unit") or {}
        if std.get("incoterm") not in freight:
            std["incoterm"] = (case.get("fixed_terms") or {}).get("incoterm") or next(iter(freight), "EXW")
        rate, pressure = self.cash(t)
        rate = ARCHETYPE_RATE.get((t.profile or {}).get("archetype"), rate or 0.08)
        if pressure >= 0.5:
            rate = max(rate, ARCHETYPE_RATE["cash_short_jobshop"])
        ref = t.standing_terms.get("unit_price") or 0.0
        offered = t.standing_terms.get("ppm_commitment")
        if offered is not None and std.get("ppm_commitment") is None:
            std["ppm_commitment"] = offered
        ppm = max(std.get("ppm_commitment") or 0, offered or 0, (t.profile or {}).get("ppm_actual") or 0)
        lead = ARCHETYPE_LEAD_EFFORT.get((t.profile or {}).get("archetype"), 0.001)
        return {"standard": std, "interest_rate": rate, "usual_rate": 0.07, "ref_price": ref, "ppm": ppm,
                "lead_effort": lead}

    @staticmethod
    def effort(terms, model):
        std, ref = model["standard"], model["ref_price"]
        days = max(0, (std.get("lead_time_days") or 0) - (terms.get("lead_time_days") or 0)) \
            if std.get("lead_time_days") is not None and terms.get("lead_time_days") is not None else 0
        ppm = max(0, (std.get("ppm_commitment") or 0) - (terms.get("ppm_commitment") or 0)) \
            if std.get("ppm_commitment") is not None and terms.get("ppm_commitment") is not None else 0
        return ref * (model.get("lead_effort", 0.001) * days + 0.00001 * ppm)

    def worth(self, case, terms, model):
        try:
            return supplier_value(case, terms, model) - self.effort(terms, model)
        except (KeyError, TypeError, ZeroDivisionError):
            return None

    def menu(self, case, t, a, c_cap):
        model = self.supplier_model(case, t)
        target = self.worth(case, a, model)
        if target is None:
            return []
        domains = {}
        for f in case["negotiable"]:
            options = list((case.get("term_options") or {}).get(f) or [])
            if f == "unit_price" or f in STRUCTURAL or not options:
                continue
            if a.get(f) not in options:
                options.append(a.get(f))
            domains[f] = options
        while domains and math.prod(len(v) for v in domains.values()) > MENU_COMBOS:
            f = max(domains, key=lambda k: len(domains[k]))
            v = domains[f]
            keep = [a.get(f), v[0], v[-1], v[len(v) // 2]]
            domains[f] = list(dict.fromkeys(x for x in keep if x in v))
            if len(domains[f]) == len(v):
                break
        theirs = t.standing_terms.get("unit_price")
        at_theirs = self.c(case, {**a, "unit_price": theirs}, t) if theirs else math.inf
        rel_case, rel_floors = relationship_case(case) and floor_binds(t), {}
        cash_hungry = model["interest_rate"] >= CASH_HUNGRY_RATE
        found = []
        for combo in itertools.product(*domains.values()):
            levers = {**a, **dict(zip(domains, combo, strict=True))}
            v0 = self.worth(case, {**levers, "unit_price": 0.0}, model)
            v1 = self.worth(case, {**levers, "unit_price": 1.0}, model)
            if v0 is None or v1 is None or v1 - v0 <= 1e-9:
                continue
            price = round((target - v0) / (v1 - v0), 2)
            if price <= 0:
                continue
            terms = complete_offer(case, {**levers, "unit_price": price})
            if not must_haves_ok(case, terms, t.standard):
                continue
            if rel_case:
                key = tuple(sorted((k, str(v)) for k, v in levers.items() if k != "unit_price"))
                if key not in rel_floors:
                    rel_floors[key] = relationship_floor(case, terms, t.standard, t.profile)
                if rel_floors[key] and terms["unit_price"] < rel_floors[key]:
                    terms = {**terms, "unit_price": rel_floors[key]}
            cost = self.c(case, terms, t)
            if cost >= c_cap - 0.5:
                continue
            if (theirs and not cash_hungry
                    and self.c(case, {**terms, "unit_price": theirs}, t) > at_theirs * (1 + OWN_PRICE_SLACK) + 1.0):
                continue
            changes = sum(terms.get(f) != a.get(f) for f in domains)
            found.append((cost, changes, terms))
        if not found:
            return []
        found.sort(key=lambda x: (x[0], x[1]))
        best = found[0][0]
        picked, seen = [], set()
        for cost, _, terms in found:
            if cost > best * (1 + MENU_SPREAD):
                break
            levers = tuple((f, str(terms.get(f))) for f in domains)
            if levers in seen or (picked and not set(levers) - {p for s in picked for p in s[1]}):
                continue
            if any(terms["unit_price"] == q["unit_price"] and abs(cost - qc) < 1.0 for q, _, qc in picked):
                continue
            seen.add(levers)
            picked.append((terms, levers, cost))
            if len(picked) == 3:
                break
        return [terms for terms, _, _ in picked]

    @staticmethod
    def no_step_back(t, sheet):
        key = tuple(sorted((k, str(v)) for k, v in sheet.items() if k != "unit_price"))
        last = t.sent_prices.get(key)
        theirs = t.standing_terms.get("unit_price")
        if (last is not None and sheet.get("unit_price") is not None and sheet["unit_price"] < last
                and (theirs is None or last < theirs)):
            sheet = {**sheet, "unit_price": last}
        if sheet.get("unit_price") is not None:
            t.sent_prices[key] = sheet["unit_price"]
        return sheet

    def c_track(self, case, terms, t):
        return self.c(case, terms, t) if floor_binds(t) else total_cost(case, terms, t.standard)

    @staticmethod
    def above_floor(case, t, terms):
        if not relationship_case(case) or not floor_binds(t):
            return terms
        floor = relationship_floor(case, terms, t.standard, t.profile)
        return {**terms, "unit_price": floor} if floor and terms["unit_price"] < floor else terms

    def lever_trades(self, case, t, a, asks=()):
        """Packages that give the supplier a term it values at equal cost to us (costing.lever_values):
        first the terms it asked for (the cheapest version of each for us - e.g. a 5 % deadband, the
        smallest volume step, a contract beyond the horizon that costs nothing), then cash terms our
        estimate says it gains on. None that would cut the price by more than MAX_TRADE_DROP."""
        picks = {}
        theirs = t.standing_terms.get("unit_price")
        hungry = self.supplier_model(case, t)["interest_rate"] >= CASH_HUNGRY_RATE
        at_theirs = self.c(case, {**a, "unit_price": theirs}, t) if theirs else math.inf
        for v in lever_values(case, a, t.standard, t.profile):
            if not v["must_haves_ok"]:
                continue
            sheet = self.above_floor(case, t, complete_offer(case, v["sheet"]))
            if sheet == a or (a["unit_price"] - sheet["unit_price"]) > MAX_TRADE_DROP * a["unit_price"]:
                continue
            if v["field"] == "index_clause" and self.clause_worth(case, t) < CLAUSE_WORTH:
                continue
            if v["field"] == "index_clause" and v["sheet"]:
                sheet = self.cheap_money_term(case, t, sheet)
            if (theirs and not hungry and v["field"] == "payment_days"
                    and self.c(case, {**sheet, "unit_price": theirs}, t) > at_theirs * (1 + OWN_PRICE_SLACK) + 1.0):
                continue
            gain = v["supplier_gain"] or 0.0
            if lever_asked(v, a, asks):
                rank = (0, v["delta_c"])  # asked for: the version that costs us least
            elif v["field"] in CASH_LEVERS and gain > 0.002 * a["unit_price"]:
                rank = (1, -gain)  # worth more to it than to us
            else:
                continue
            if v["field"] not in picks or rank < picks[v["field"]][0]:
                picks[v["field"]] = (rank, sheet)
        return [sheet for _, sheet in sorted(picks.values(), key=lambda x: x[0])]

    def pick_offer(self, case, t):
        t.alt = None
        for sheet_id, terms in t.offers or []:
            for f in STRUCTURAL:
                if f in terms:
                    seen = t.struct_seen.setdefault(f, [])
                    if terms[f] not in seen:
                        seen.append(terms[f])
            if sheet_id == t.standing_id or terms.get("unit_price") is None:
                continue
            if not must_haves_ok(case, terms, t.standard):
                continue
            c = self.c(case, terms, t)
            if t.alt is None or c < t.alt[0]:
                t.alt = (c, sheet_id, terms)

    @staticmethod
    def cash(t):
        prof, sig = t.profile or {}, t.signals or {}
        rate = prof.get("cash_rate_estimate") or 0.0
        pressure = prof.get("cash_pressure") or 0.0
        if sig.get("cash_pressure") or "faster_payment" in (sig.get("asks") or []):
            rate, pressure = max(rate, 0.2), max(pressure, 0.6)
        return rate, pressure

    def close(self, case, t, acceptable, c_theirs, rival_best_c):
        alt = t.alt
        if alt and alt[0] < c_theirs and t.rounds_left > 1 and not t.mirrored:
            if alt[0] < alternative_cost(case) and alt[0] <= rival_best_c:
                t.mirrored = True
                sheet = complete_offer(case, dict(alt[2]))
                variants = self.clause_variants(case, t, sheet)  # its package, but our cheapest deadband first
                t.clause_countered = t.clause_countered or bool(variants)
                t.our_prices.append(sheet["unit_price"])
                t.our_costs.append(self.c(case, sheet, t))
                intent = "appreciative: we accept your alternative proposal as offered"
                if variants:
                    intent += "; we would prefer the same with a wider index deadband"
                return Decision("send", t.supplier_id, term_sheets=[*variants, sheet][:3], intent=intent)
        if acceptable and t.status == "open" and t.rounds_left > 1 and not t.clause_countered:
            variants = self.clause_variants(case, t, complete_offer(case, dict(t.standing_terms)))
            if variants:  # one more message before closing: its own package stays on the table as the last sheet
                t.clause_countered = True
                own = complete_offer(case, dict(t.standing_terms))
                t.our_prices.append(own["unit_price"])
                t.our_costs.append(self.c(case, own, t))
                return Decision("send", t.supplier_id, term_sheets=[*variants, own][:3],
                                intent="appreciative: we can agree to your offer; we would prefer it with a wider "
                                       "index deadband")
        return self.accept(t) if acceptable else Decision("walk", t.supplier_id)

    def clause_variants(self, case, t, sheet):
        """``sheet`` with the index clause cheapest for us (e.g. a 5 % instead of a 0 % deadband): once at
        the same price, once priced so that our C equals ``sheet``'s. [] when its clause is already the
        cheapest or it has none. The supplier keeps ``sheet`` as an option - this can only gain."""
        out = []
        for f in STRUCTURAL:
            if f not in case["negotiable"] or sheet.get(f) is None:
                continue
            options = [v for v in (case.get("term_options") or {}).get(f) or [] if v is not None]
            if not options:
                continue
            c_sheet = self.c(case, sheet, t)
            cheapest = min(options, key=lambda v: self.c(case, {**sheet, f: v}, t))
            same_price = complete_offer(case, {**sheet, f: cheapest})
            c_same = self.c(case, same_price, t)
            if cheapest == sheet[f] or c_same >= c_sheet:
                continue
            slope = self.c(case, {**same_price, "unit_price": same_price["unit_price"] + 1}, t) - c_same
            out.append(same_price)
            if slope > 0:
                price = round(same_price["unit_price"] + (c_sheet - c_same) / slope, 2)
                equal_cost = complete_offer(case, {**same_price, "unit_price": price})
                if equal_cost not in out and equal_cost != sheet:
                    out.append(equal_cost)
        return out

    def adopt_structure(self, case, sheet, t):
        out = dict(sheet)
        best = None
        for _, terms in t.offers or []:
            if terms.get("unit_price") is None or not must_haves_ok(case, terms, t.standard):
                continue
            c = self.c(case, terms, t)
            if best is None or c < best[0]:
                best = (c, terms)
        structures = {tuple(sorted((k, str(v)) for k, v in terms.items() if k not in ("unit_price", "payment_days")))
                      for _, terms in t.offers or []}
        if best and len(structures) > 1:
            for f in case["negotiable"]:
                if f not in ("unit_price", "payment_days") and f in best[1]:
                    out[f] = best[1][f]
            if out != sheet and not must_haves_ok(case, out, t.standard):
                out = dict(sheet)
        for f in STRUCTURAL:
            insists = bool(t.offers) and all(terms.get(f) is not None for _, terms in t.offers)
            if best and len(structures) > 1 and f in best[1] and not insists:
                continue
            # it insists on a clause: counter with the one cheapest for us the case allows (a 5 % deadband),
            # not the one it proposed (0 % cost EUR 31k in P08 on 2026-10-24)
            options = [v for v in (case.get("term_options") or {}).get(f) or [] if v is not None] \
                or [v for v in t.struct_seen.get(f) or [] if v is not None]
            if f in case["negotiable"] and insists and options:
                out[f] = min(options, key=lambda v: self.c(case, {**out, f: v}, t))
        if "index_clause" in out and self.clause_worth(case, t) < CLAUSE_WORTH:
            out["index_clause"] = sheet.get("index_clause")
        return out

    @staticmethod
    def clause_worth(case, t):
        drivers = {d.get("series"): d.get("change_12m_pct") or 0.0 for d in (t.profile or {}).get("cost_drivers") or []}
        options = [o for o in (case.get("term_options") or {}).get("index_clause") or [] if o]
        return max((o.get("material_share", 0) * (drivers.get(o.get("series"), 0.0) - o.get("deadband_pct", 0)) / 100
                    for o in options), default=0.0)

    def cheap_money_term(self, case, t, sheet):
        options = (case.get("term_options") or {}).get("payment_days") or []
        if "payment_days" not in case["negotiable"] or not options:
            return sheet
        if self.supplier_model(case, t)["interest_rate"] >= case["buyer"]["interest_rate"]:
            return sheet
        longest = complete_offer(case, {**sheet, "payment_days": max(options)})
        if longest == sheet:
            return sheet
        return self.above_floor(case, t, self.same_cost(case, longest, sheet, t.standard))

    def pick_claims(self, case, t):
        limit = int(self.p["claims_per_msg"])
        if limit <= 0 or not case.get("case_id"):
            return []
        if len(t.our_prices) <= 1:
            limit = max(limit, FIRST_MESSAGE_CLAIMS)
        key = (case["case_id"], t.supplier_id)
        if key not in self.banks:
            from buyer.facts.claims import claims

            for attempt in range(2):
                try:
                    self.banks[key] = sorted(claims(case, t.supplier_id), key=lambda c: -c.strength)
                    break
                except Exception:  # a transient failure must not cost the whole thread its arguments
                    log.warning("claim bank for %s %s failed (attempt %d)", *key, attempt + 1, exc_info=True)
        rejected = set((t.signals or {}).get("rejected_args") or [])
        bank = list(self.banks.get(key) or [])
        if t.case_threads and len(case.get("suppliers") or []) > 1:
            try:
                from buyer.facts.claims import rival_claims

                bank = sorted(bank + rival_claims(case, t.case_threads, t.supplier_id), key=lambda c: -c.strength)
            except Exception:
                pass
        pool = [
            c for c in bank
            if c.strength >= self.p["claim_min_strength"]
            and (t.supplier_id, c.key) not in self.used_keys
            and c.key not in rejected
            and (c.key.startswith("rival:") or self.used_refs.isdisjoint(c.refs))
        ]
        pool.sort(key=lambda c: -c.strength * CLAIM_WEIGHT.get(c.key.split(":", 1)[0], 0.3))
        strong = [c for c in pool if CLAIM_WEIGHT.get(c.key.split(":", 1)[0], 0.3) >= WEAK_CLAIM]
        pool = strong or pool
        chosen, seen = [], set()
        for c in pool:
            if seen.isdisjoint(c.refs):
                chosen.append(c)
                seen |= set(c.refs)
            if len(chosen) == limit:
                break
        for c in chosen:
            if not c.key.startswith("rival:"):  # a rival's offer may be cited to every other bidder (api.md)
                self.used_refs |= set(c.refs)
            self.used_keys.add((t.supplier_id, c.key))
        return chosen

    @staticmethod
    def same_cost(case, sheet, ref, standard):
        c_ref, c = total_cost(case, ref, standard), total_cost(case, sheet, standard)
        slope = total_cost(case, {**sheet, "unit_price": sheet["unit_price"] + 1}, standard) - c
        if slope <= 0:
            return sheet
        return {**sheet, "unit_price": round(max(0.01, sheet["unit_price"] - (c - c_ref) / slope), 2)}

    @staticmethod
    def best_options(case, terms, standard, skip=()):
        out = dict(terms)
        for _ in range(2):
            for f, options in case.get("term_options", {}).items():
                if f == "unit_price" or f in skip or f not in case["negotiable"] or not options:
                    continue
                options = [o for o in options if must_haves_ok(case, {**out, f: o}, standard)] or options
                costs = {i: total_cost(case, {**out, f: o}, standard) for i, o in enumerate(options)}
                low = min(costs.values())
                ties = [options[i] for i, c in costs.items() if c <= low + 1.0]
                theirs = terms.get(f)
                if f == "contract_months" and case.get("type") in LONG_CONTRACT_TYPES:
                    out[f] = max(ties)
                elif theirs in ties:
                    out[f] = theirs
                elif isinstance(theirs, int | float) and all(isinstance(o, int | float) for o in ties):
                    out[f] = min(ties, key=lambda o: abs(o - theirs))
                else:
                    out[f] = ties[0]
        return out
