import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from arena_kit.cost import complete_offer, must_haves_ok, total_cost

from buyer.facts.costing import c as relationship_c
from buyer.facts.costing import relationship_floor

PARAMS_FILE = Path(__file__).with_name("params.json")
STRUCTURAL = ("index_clause",)

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
}
DEEP_OPEN_TYPES = ("raw_material", "rfq")


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
    dropped: bool = False  # we walked away from this bidder while others played on (no longer a rival)
    their_costs: list = field(default_factory=list)  # C of each standing offer, in order (reciprocity)
    seen_ids: list = field(default_factory=list)
    holds: int = 0  # replies in a row in which the supplier did not move towards us
    holding: bool = False  # this move we hold our price and change the package instead
    asked_breakdown: bool = False


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
        close = t.our_costs and c_theirs <= t.our_costs[-1] * (1 + p["accept_gap_pct"] / 100)
        if close and acceptable and c_theirs < t.opening_cost:
            return self.close(case, t, acceptable, c_theirs, rival_best_c)
        if acceptable and self.at_target(case, t, c_theirs):
            return self.close(case, t, acceptable, c_theirs, rival_best_c)
        prev = t.last_sheet
        decision = self.offer(case, t, self.next_price(t, theirs, case=case), rival_best_c=rival_best_c)
        if prev is not None and decision.term_sheets[0] == prev and acceptable and not t.holding:
            return self.close(case, t, acceptable, c_theirs, rival_best_c)  # repeating ourselves makes them go final
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
        if case is not None:  # stabilise / secure_supply: below this price the relationship charge costs more
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
        return step

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
        sheets = [a]
        options = case.get("term_options", {}).get("payment_days") or []
        faster = [d for d in options if d < a.get("payment_days", 0)]
        rate, pressure = self.cash(t)
        cash_first = False
        if faster and self.p["cash_discount_pct"] > 0:
            days_b = min(faster) if pressure >= 0.5 else max(faster)
            gap = (a["payment_days"] - days_b) / 360
            ours = b["interest_rate"] * gap
            disc = self.p["cash_discount_pct"] / 100
            if rate > b["interest_rate"]:
                disc = max(disc, ours + 0.5 * (rate - b["interest_rate"]) * gap)
            sheet_b = complete_offer(case, {**a, "unit_price": a["unit_price"] * (1 - disc), "payment_days": days_b})
            if self.c(case, sheet_b, t) < self.c(case, a, t):
                sheets.append(sheet_b)
                cash_first = pressure >= 0.5
        slower = [d for d in options if d > a.get("payment_days", math.inf)]
        if "payment_days" in case["negotiable"] and slower and pressure < 0.5:
            days_c = max(slower)
            theirs_rate = rate if rate > 0 else 0.5 * b["interest_rate"]
            if theirs_rate < b["interest_rate"]:
                markup = (theirs_rate + b["interest_rate"]) / 2 * (days_c - a["payment_days"]) / 360
                sheet_c = complete_offer(
                    case, {**a, "unit_price": round(a["unit_price"] * (1 + markup), 2), "payment_days": days_c}
                )
                if self.c(case, sheet_c, t) < self.c(case, a, t):
                    sheets.insert(1, sheet_c)
        std_days = t.standard.get("payment_days") or t.opening_payment_days
        if "payment_days" in case["negotiable"] and std_days in options and std_days != a.get("payment_days"):
            sheet_s = self.same_cost(case, complete_offer(case, {**a, "payment_days": std_days}), a, t.standard)
            if sheet_s not in sheets:
                if self.p["lead_standard"] > 0.5:
                    sheets.insert(0, sheet_s)
                else:
                    sheets.append(sheet_s)
        if cash_first:
            sheets.insert(0, sheets.pop(sheets.index(sheet_b)))
        sheets = sheets[:3]
        questions = []
        if t.holding:  # same price: lead with another package, ask for its costs once
            k = t.holds % len(sheets)
            sheets = sheets[k:] + sheets[:k]
            intent = "firm on price, open on the other terms"
            if not t.asked_breakdown:
                questions, t.asked_breakdown = ["cost breakdown"], True
        t.last_sheet = a
        t.our_prices.append(a["unit_price"])
        t.our_costs.append(self.c(case, a, t))
        chosen = self.pick_claims(case, t)
        if any(c.key.startswith("rival:") for c in chosen):
            intent = f"{intent}, competition: another offer is on the table"
        return Decision("send", t.supplier_id, term_sheets=sheets, claims=chosen, questions=questions, intent=intent)

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
                t.our_prices.append(sheet["unit_price"])
                t.our_costs.append(self.c(case, sheet, t))
                return Decision("send", t.supplier_id, term_sheets=[sheet],
                                intent="appreciative: we accept your alternative proposal as offered")
        return self.accept(t) if acceptable else Decision("walk", t.supplier_id)

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
            if best and len(structures) > 1 and f in best[1]:
                continue
            insists = bool(t.offers) and all(terms.get(f) is not None for _, terms in t.offers)
            options = [v for v in t.struct_seen.get(f) or [] if v is not None]
            if f in case["negotiable"] and insists and options:
                out[f] = min(options, key=lambda v: self.c(case, {**out, f: v}, t))
        return out

    def pick_claims(self, case, t):
        limit = int(self.p["claims_per_msg"])
        if limit <= 0 or not case.get("case_id"):
            return []
        key = (case["case_id"], t.supplier_id)
        if key not in self.banks:
            try:
                from buyer.facts.claims import claims

                self.banks[key] = sorted(claims(case, t.supplier_id), key=lambda c: -c.strength)
            except Exception:
                self.banks[key] = []
        rejected = set((t.signals or {}).get("rejected_args") or [])
        bank = list(self.banks[key])
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
            and self.used_refs.isdisjoint(c.refs)
        ]
        chosen, seen = [], set()
        for c in pool:
            if seen.isdisjoint(c.refs):
                chosen.append(c)
                seen |= set(c.refs)
            if len(chosen) == limit:
                break
        for c in chosen:
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
                if theirs in ties:
                    out[f] = theirs
                elif isinstance(theirs, int | float) and all(isinstance(o, int | float) for o in ties):
                    out[f] = min(ties, key=lambda o: abs(o - theirs))
                else:
                    out[f] = ties[0]
        return out
