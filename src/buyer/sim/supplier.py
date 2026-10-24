from dataclasses import dataclass

from arena_kit.cost import complete_offer, supplier_value


@dataclass
class SupplierParams:
    full_cost: float
    open_margin: float
    min_margin: float
    cash_rate: float
    concede: float
    approval_step_pct: float
    patience: int
    walk_after_final: float
    std_payment_days: int


class SyntheticSupplier:
    def __init__(self, case, supplier_id, params: SupplierParams, rng):
        self.case, self.sid, self.p, self.rng = case, supplier_id, params, rng
        b, fixed = case["buyer"], case.get("fixed_terms", {})
        self.standard = {
            "payment_days": params.std_payment_days,
            "incoterm": fixed.get("incoterm") or "FCA",
            "lead_time_days": b["need_lead_time_days"],
            "volume_per_year": b["need_per_year"],
            "contract_months": round(12 * b["horizon_years"]),
            "tooling_eur": 0,
            "ppm_commitment": 0,
            "chargeback_eur_per_complaint": 0,
        }
        self.me = {"standard": self.standard, "interest_rate": params.cash_rate}
        self.floor = params.full_cost * (1 + params.min_margin)
        self.ask = params.full_cost * (1 + params.open_margin)
        self.best_seen = None
        self.idle = 0
        self.round = 0
        self.final_sent = False
        self.n = 0
        self.terms = self.price_terms({**self.standard, **fixed}, self.ask)

    def value(self, terms):
        return supplier_value(self.case, terms, self.me)

    def price_for(self, terms, value):
        v0 = self.value({**terms, "unit_price": 0.0})
        v1 = self.value({**terms, "unit_price": 1.0})
        return round((value - v0) / (v1 - v0), 2)

    def price_terms(self, terms, value):
        t = complete_offer(self.case, {**terms, "unit_price": 0.0})
        return {**t, "unit_price": self.price_for(t, value)}

    def reply(self, status, terms):
        self.n += 1
        self.terms = terms
        return {"status": status, "term_sheet_id": f"offer:{self.sid}-{self.n}", "terms": terms}

    def opening(self):
        return {"status": "open", "term_sheet_id": f"offer:{self.sid}-0", "terms": self.terms}

    def respond(self, sheets):
        self.round += 1
        best = max(sheets, key=self.value)
        v = self.value(best)
        if v >= self.ask - 0.005:
            return self.reply("agreed", best)
        moved = self.best_seen is None or v > self.value(self.best_seen) + 1e-6
        if moved:
            self.best_seen, self.idle = best, 0
        else:
            self.idle += 1
            if self.idle > self.p.patience:
                return self.reply("walked_away", self.terms)
        if self.final_sent:
            if self.rng.random() < self.p.walk_after_final:
                return self.reply("walked_away", self.terms)
            return self.reply("final_offer", self.price_terms(best, self.ask))
        if moved:
            step = self.p.concede * (self.ask - max(v, self.floor))
            cap = self.ask * self.p.approval_step_pct / 100
            if step > cap and self.round % 2:
                step = cap
            self.ask = max(self.floor, self.ask - step)
        status = "open"
        if self.ask - self.floor < 0.01 * self.floor:
            status, self.final_sent = "final_offer", True
        return self.reply(status, self.price_terms(best, self.ask))

    def best_package(self, case_cost):
        best = None
        options = {f: o for f, o in self.case.get("term_options", {}).items() if f in self.case["negotiable"]}
        combos = [{}]
        for f, opts in options.items():
            combos = [{**c, f: o} for c in combos for o in opts]
        for combo in combos:
            t = self.price_terms({**self.terms, **combo}, self.floor)
            c = case_cost(t, self.standard)
            best = c if best is None else min(best, c)
        return best
