import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from arena_kit.cost import complete_offer, must_haves_ok, total_cost

PARAMS_FILE = Path(__file__).with_name("params.json")
STRUCTURAL = ("index_clause",)

BOUNDS = {
    "open_frac": (0.0, 1.0),
    "concede": (0.05, 0.8),
    "floor_margin_pct": (0.0, 15.0),
    "accept_gap_pct": (0.0, 5.0),
    "cash_discount_pct": (0.0, 5.0),
    "push_final": (0.0, 1.0),
    "min_open_discount_pct": (1.0, 10.0),
    "rival_undercut_pct": (0.0, 5.0),
    "lead_standard": (0.0, 1.0),
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
    "claim_min_strength": 0.3,
}


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
        self.pick_offer(case, t)
        c_theirs = self.cost(case, t)
        if t.opening_cost is None:
            t.opening_cost = c_theirs
            t.opening_payment_days = t.standing_terms.get("payment_days")
        acceptable = self.acceptable(case, t, c_theirs, rival_best_c)

        if t.status == "agreed":
            return self.accept(t) if acceptable else Decision("walk", sid)
        if t.status == "final_offer":
            if p["push_final"] > 0.5 and not t.pushed_final and t.rounds_left > 1:
                t.pushed_final = True
                return self.offer(case, t, self.next_price(t, theirs, step=0.5), intent="final push")
            return self.close(case, t, acceptable, c_theirs, rival_best_c)
        if t.rounds_left <= 1:
            return self.accept(t) if acceptable else Decision("walk", sid)
        close = t.our_costs and c_theirs <= t.our_costs[-1] * (1 + p["accept_gap_pct"] / 100)
        if close and acceptable and c_theirs < t.opening_cost:
            return self.close(case, t, acceptable, c_theirs, rival_best_c)
        return self.offer(case, t, self.next_price(t, theirs), rival_best_c=rival_best_c)

    def closing(self, case, threads: dict) -> Decision:
        best = None
        for t in threads.values():
            if t.status in ("walked_away", "no_bid") or not t.standing_id:
                continue
            self.pick_offer(case, t)
            c = self.cost(case, t)
            if self.acceptable(case, t, c, math.inf) and (best is None or c < best[0]):
                best = (c, t)
        if best is None:
            return Decision("walk", next(iter(threads)))
        return self.accept(best[1])

    def cost(self, case, t):
        return total_cost(case, t.standing_terms, t.standard)

    def acceptable(self, case, t, c_theirs, rival_best_c):
        return (
            must_haves_ok(case, t.standing_terms, t.standard)
            and c_theirs < alternative_cost(case)
            and c_theirs <= rival_best_c
        )

    def accept(self, t):
        return Decision("accept", t.supplier_id, accept_sheet_id=t.standing_id)

    def floor_ask(self, t, theirs):
        floor = t.profile.get("floor_estimate") or theirs * 0.85
        return floor * (1 + self.p["floor_margin_pct"] / 100)

    def next_price(self, t, theirs, step=None):
        low = min(self.floor_ask(t, theirs), theirs * (1 - self.p["min_open_discount_pct"] / 100))
        if not t.our_prices:
            price = low + self.p["open_frac"] * (theirs - low)
        else:
            last = t.our_prices[-1]
            price = last + (step if step is not None else self.p["concede"]) * (theirs - last)
        return round(min(max(price, low), theirs), 2)

    def offer(self, case, t, price, intent="firm, appreciative", rival_best_c=math.inf):
        b = case["buyer"]
        base = {**t.standing_terms, "unit_price": price}
        if "payment_days" in case["negotiable"]:
            base["payment_days"] = b["reference_payment_days"]
        a = self.best_options(case, complete_offer(case, base), t.standard, skip={"payment_days"})
        a = self.adopt_structure(case, a, t)
        if rival_best_c < math.inf:
            c_a = total_cost(case, a, t.standard)
            target = rival_best_c * (1 - self.p["rival_undercut_pct"] / 100)
            if c_a > target:
                slope = total_cost(case, {**a, "unit_price": a["unit_price"] + 1}, t.standard) - c_a
                if slope > 0:
                    a = {**a, "unit_price": round(max(0.01, a["unit_price"] - (c_a - target) / slope), 2)}
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
            if total_cost(case, sheet_b, t.standard) < total_cost(case, a, t.standard):
                sheets.append(sheet_b)
                cash_first = pressure >= 0.5
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
        t.our_prices.append(a["unit_price"])
        t.our_costs.append(total_cost(case, a, t.standard))
        chosen = self.pick_claims(case, t)
        if any(c.key.startswith("rival:") for c in chosen):
            intent = f"{intent}, competition: another offer is on the table"
        return Decision("send", t.supplier_id, term_sheets=sheets, claims=chosen, intent=intent)

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
            c = total_cost(case, terms, t.standard)
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
                t.our_costs.append(total_cost(case, sheet, t.standard))
                return Decision("send", t.supplier_id, term_sheets=[sheet],
                                intent="appreciative: we accept your alternative proposal as offered")
        return self.accept(t) if acceptable else Decision("walk", t.supplier_id)

    def adopt_structure(self, case, sheet, t):
        out = dict(sheet)
        for f in STRUCTURAL:
            insists = bool(t.offers) and all(terms.get(f) is not None for _, terms in t.offers)
            options = [v for v in t.struct_seen.get(f) or [] if v is not None]
            if f in case["negotiable"] and insists and options:
                out[f] = min(options, key=lambda v: total_cost(case, {**out, f: v}, t.standard))
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
        for f, options in case.get("term_options", {}).items():
            if f == "unit_price" or f in skip or f not in case["negotiable"] or not options:
                continue
            costs = {i: total_cost(case, {**out, f: o}, standard) for i, o in enumerate(options)}
            low = min(costs.values())
            ties = [options[i] for i, c in costs.items() if c <= low + 1.0]
            theirs = terms.get(f)
            if theirs in ties:
                continue
            if isinstance(theirs, int | float) and all(isinstance(o, int | float) for o in ties):
                out[f] = min(ties, key=lambda o: abs(o - theirs))
            else:
                out[f] = ties[0]
        return out
