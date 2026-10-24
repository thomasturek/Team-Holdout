import json
import math
from pathlib import Path

from arena_kit.cost import must_haves_ok, score, total_cost

from ..policy.policy import Policy, ThreadState, alternative_cost
from .population import sample
from .supplier import SyntheticSupplier

KIT_CASES = Path(__file__).resolve().parents[3] / "starter-kit" / "arena_kit" / "sim_cases"
RUN_CASES = Path(__file__).resolve().parents[3] / "runs" / "cases"


def load_cases():
    cases = {}
    for folder in (KIT_CASES, RUN_CASES):
        for p in sorted(folder.glob("*.json")) if folder.is_dir() else []:
            data = json.loads(p.read_text())
            for c in data if isinstance(data, list) else [data]:
                if "buyer" in c and "unit_price" in c.get("negotiable", []):
                    cases[c["case_id"]] = c
    return list(cases.values())


def episode(case, policy: Policy, rng, ranges=None):
    suppliers, threads = {}, {}
    for sid in case["suppliers"]:
        params, profile = sample(case, rng, ranges)
        s = SyntheticSupplier(case, sid, params, rng)
        suppliers[sid] = s
        o = s.opening()
        threads[sid] = ThreadState(
            supplier_id=sid,
            standing_id=o["term_sheet_id"],
            standing_terms=o["terms"],
            status="open",
            standard=s.standard,
            rounds_left=case.get("round_limit", 10),
            profile=profile,
            their_prices=[o["terms"]["unit_price"]],
        )

    def cost(terms, std, sid):
        # scored like the arena: the relationship charge (stabilise / secure_supply) from the supplier's
        # real economics - the policy only has the Scout's estimate of them
        s = suppliers[sid]
        truth = {"full_cost": s.p.full_cost, "interest_rate": s.p.cash_rate, "standard": s.standard}
        return total_cost(case, terms, std, truth)

    opening = [cost(t.standing_terms, t.standard, t.supplier_id) for t in threads.values()
               if must_haves_ok(case, t.standing_terms, t.standard)]
    c_open = min(opening) if opening else math.inf
    c_alt = alternative_cost(case)
    c_best = min([s.best_package(lambda terms, std, sid=sid: cost(terms, std, sid)) for sid, s in suppliers.items()]
                 + [c_alt])

    rounds, decision = 0, None
    while True:
        live = [t for t in threads.values() if t.status not in ("walked_away", "no_bid")]
        if not live:
            break
        for t in live:
            rival = policy.rival_best(case, threads, t)  # the same eligibility rule as at run time
            decision = policy.decide(case, t, rival_best_c=rival)
            if decision.kind == "accept":
                c_deal = cost(t.standing_terms, t.standard, t.supplier_id)
                return result(c_open, c_deal, c_best, "deal", rounds)
            if decision.kind == "walk":
                t.status = "walked_away"
                continue
            rounds += 1
            t.rounds_left -= 1
            reply = suppliers[t.supplier_id].respond(decision.term_sheets)
            t.status, t.standing_id, t.standing_terms = reply["status"], reply["term_sheet_id"], reply["terms"]
            t.their_prices.append(reply["terms"]["unit_price"])
            if t.rounds_left <= 0 and t.status not in ("walked_away", "no_bid"):
                t.rounds_left = 1
    return result(c_open, c_alt, c_best, "no_deal", rounds)


def result(c_open, c_deal, c_best, outcome, rounds):
    s = 0.0 if c_deal == math.inf else score(c_open, c_deal, c_best)
    return {"score": s, "outcome": outcome, "rounds": rounds, "c_open": c_open, "c_deal": c_deal, "c_best": c_best}
