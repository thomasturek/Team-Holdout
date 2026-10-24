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
    insist_payment: bool = False
    reciprocity: float = 0.0
    insult_pct: float = 100.0
    first_drop: float = 0.0
    lead_premium_pct_week: float = 0.0
    std_incoterm: str | None = None
    std_lead_time: int | None = None


class SyntheticSupplier:
    def __init__(self, case, supplier_id, params: SupplierParams, rng):
        self.case, self.sid, self.p, self.rng = case, supplier_id, params, rng
        b, fixed = case["buyer"], case.get("fixed_terms", {})
        self.standard = {
            "payment_days": params.std_payment_days,
            "incoterm": fixed.get("incoterm") or params.std_incoterm or "FCA",
            "lead_time_days": fixed.get("lead_time_days") or params.std_lead_time or b["need_lead_time_days"],
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
        self.angry = False
        self.n = 0
        self.terms = self.price_terms({**self.standard, **fixed}, self.ask)

    def value(self, terms):
        v = supplier_value(self.case, terms, self.me)
        lead = terms.get("lead_time_days")
        if lead is not None and self.p.lead_premium_pct_week:
            faster = max(0, self.standard["lead_time_days"] - lead) / 7
            v -= self.p.full_cost * self.p.lead_premium_pct_week / 100 * faster
        return v

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
        best = sheets[0]
        if self.p.insist_payment and "payment_days" in best:
            best = {**best, "payment_days": self.standard["payment_days"]}
        v = self.value(best)
        if v >= self.ask - 0.005:
            return self.reply("agreed", best)
        last_v = self.value(self.best_seen) if self.best_seen is not None else None
        if last_v is None and v < self.p.full_cost * (1 - self.p.insult_pct / 100):
            self.angry = True
        moved = last_v is None or v > last_v + 1e-6
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
        if self.round == 1 and self.p.first_drop:
            self.ask = max(self.floor, self.ask * (1 - self.p.first_drop))
        if moved:
            step = self.p.concede * (self.ask - max(v, self.floor))
            if last_v is not None:
                step += self.p.reciprocity * (v - last_v)
            if self.angry:
                step *= 0.5
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
