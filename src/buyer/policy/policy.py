import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from arena_kit.cost import complete_offer, must_haves_ok, total_cost

PARAMS_FILE = Path(__file__).with_name("params.json")

BOUNDS = {
    "open_frac": (0.0, 1.0),
    "concede": (0.05, 0.8),
    "floor_margin_pct": (0.0, 15.0),
    "accept_gap_pct": (0.0, 5.0),
    "cash_discount_pct": (0.0, 5.0),
    "push_final": (0.0, 1.0),
    "min_open_discount_pct": (1.0, 10.0),
}
DEFAULTS = {
    "open_frac": 0.3,
    "concede": 0.35,
    "floor_margin_pct": 4.0,
    "accept_gap_pct": 1.0,
    "cash_discount_pct": 1.5,
    "push_final": 0.0,
    "min_open_discount_pct": 4.0,
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

    def decide(self, case, t: ThreadState, rival_best_c=math.inf) -> Decision:
        p, sid = self.p, t.supplier_id
        theirs = t.standing_terms.get("unit_price")
        if t.status in ("walked_away", "no_bid") or theirs is None:
            return Decision("walk", sid)
        c_theirs = self.cost(case, t)
        if t.opening_cost is None:
            t.opening_cost = c_theirs
        acceptable = self.acceptable(case, t, c_theirs, rival_best_c)

        if t.status == "agreed":
            return self.accept(t) if acceptable else Decision("walk", sid)
        if t.status == "final_offer":
            if p["push_final"] > 0.5 and not t.pushed_final and t.rounds_left > 1:
                t.pushed_final = True
                return self.offer(case, t, self.next_price(t, theirs, step=0.5), intent="final push")
            return self.accept(t) if acceptable else Decision("walk", sid)
        if t.rounds_left <= 1:
            return self.accept(t) if acceptable else Decision("walk", sid)
        close = t.our_prices and theirs <= t.our_prices[-1] * (1 + p["accept_gap_pct"] / 100)
        if close and acceptable and c_theirs < t.opening_cost:
            return self.accept(t)
        return self.offer(case, t, self.next_price(t, theirs))

    def closing(self, case, threads: dict) -> Decision:
        best = None
        for t in threads.values():
            if t.status in ("walked_away", "no_bid") or not t.standing_id:
                continue
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

    def offer(self, case, t, price, intent="firm, appreciative"):
        b = case["buyer"]
        base = {**t.standing_terms, "unit_price": price}
        if "payment_days" in case["negotiable"]:
            base["payment_days"] = b["reference_payment_days"]
        a = self.best_options(case, complete_offer(case, base), t.standard, skip={"payment_days"})
        sheets = [a]
        options = case.get("term_options", {}).get("payment_days") or []
        faster = [d for d in options if d < a.get("payment_days", 0)]
        if faster and self.p["cash_discount_pct"] > 0:
            sheet_b = complete_offer(
                case,
                {**a, "unit_price": price * (1 - self.p["cash_discount_pct"] / 100), "payment_days": max(faster)},
            )
            if total_cost(case, sheet_b, t.standard) < total_cost(case, a, t.standard):
                sheets.append(sheet_b)
        std_days = t.standard.get("payment_days")
        if "payment_days" in case["negotiable"] and std_days in options and len(sheets) < 3:
            sheet_s = complete_offer(case, {**a, "payment_days": std_days})
            if sheet_s not in sheets:
                sheets.append(sheet_s)
        t.our_prices.append(a["unit_price"])
        return Decision("send", t.supplier_id, term_sheets=sheets, intent=intent)

    @staticmethod
    def best_options(case, terms, standard, skip=()):
        out = dict(terms)
        for f, options in case.get("term_options", {}).items():
            if f == "unit_price" or f in skip or f not in case["negotiable"] or not options:
                continue
            out[f] = min(options, key=lambda o: total_cost(case, {**out, f: o}, standard))
        return out
