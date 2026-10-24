"""THE ANALYST, Phase 2 (A4): safe candidate ranking with a deterministic fallback.

    sel = PolicyV2(policy).select(case, t, rival_best_c)    # PolicySelection, t unchanged
    PolicyV2(policy).decide(case, t, rival_best_c)          # Decision, t updated (like Policy.decide)

Routing, in this order:
  1. agreed / final offer / last round / no price  -> V0's rules        ("v0_rule")
  2. any error, no valid candidate                  -> V0's move         ("v0_fallback")
  3. confidence >= HIGH                             -> the ranker's best ("v2_ml")
  4. confidence >= MEDIUM                           -> best conservative ("v2_conservative")
  5. otherwise                                      -> V0's move         ("v0_fallback")
Accept and walk only ever come from V0's rules or a shield-checked candidate. Deadline closing stays
with the runtime (threads.py -> agent.closing -> Policy.closing), which never asks V2.
"""

from __future__ import annotations

import copy
import logging
import math
import time

from ..interfaces import PolicySelection
from . import candidates as gen
from . import ood
from .policy import Policy, ThreadState
from .ranker import Ranker

log = logging.getLogger("buyer.policy.v2")
STATE_FIELDS = ("our_prices", "pushed_final", "opening_cost", "opening_payment_days")


class PolicyV2:
    def __init__(self, policy: Policy | None = None, ranker: Ranker | None = None):
        self.v0 = policy or Policy()
        self.ranker = ranker or Ranker()

    # the interface the simulator and the agent use for V0 as well
    def cost(self, case, t):
        return self.v0.cost(case, t)

    def closing(self, case, threads):
        return self.v0.closing(case, threads)

    def decide(self, case, t: ThreadState, rival_best_c=math.inf, **kw):
        sel = self.select(case, t, rival_best_c, commit=True, **kw)
        return sel.decision

    def select(self, case, t: ThreadState, rival_best_c=math.inf, *, claims=(), ctx=None, commit=False):
        """The move for this thread. `t` changes only with commit=True (then exactly as if the selected
        Decision had come from V0: opening cost, our prices, final push)."""
        t0 = time.monotonic()
        work = copy.deepcopy(t)
        v0 = self.v0.decide(case, work, rival_best_c=rival_best_c)  # V0 on a copy; `work` holds its state
        try:
            sel, chosen = self._route(case, copy.deepcopy(t), work, v0, rival_best_c, claims, ctx or {})
        except Exception as e:  # never lose the move: V0's
            log.exception("%s: V2 failed - V0's move", t.supplier_id)
            sel, chosen = PolicySelection(v0, "v0_fallback", 0.0, [f"v2 error: {type(e).__name__}: {e}"], [],
                                          "V2 raised"), None  # fmt: skip
        if commit:
            self._commit(t, work, sel.decision, chosen)
        sel.ranked_candidates.append({"latency_s": round(time.monotonic() - t0, 4)})
        return sel

    def _route(self, case, pre, work, v0, rival_best_c, claims, ctx):
        """`pre`: the thread before this move (candidates start from it); `work`: after V0's move."""
        if v0.kind != "send" or work.status != "open" or work.rounds_left <= 1:
            return PolicySelection(v0, "v0_rule", 1.0, [], [], f"V0's rules: {v0.kind} ({work.status})"), None
        pre.opening_cost, pre.opening_payment_days = work.opening_cost, work.opening_payment_days
        cands = gen.generate(case, pre, self.v0, v0, rival_best_c, claims=claims, ctx=ctx)
        ranked, disagreement = self.ranker.rank(cands)
        confidence, reasons, cap = ood.assess(case, pre, ranked, disagreement, v0)
        table = [row(c, ranked) for c in cands]
        v0_cand = next(c for c in cands if c.candidate_id == "v0")
        if not ranked:
            return PolicySelection(v0, "v0_fallback", 0.0, reasons + ["no valid candidate"], table,
                                   "no valid candidate"), None  # fmt: skip
        level = "ml" if confidence >= ood.HIGH else "conservative" if confidence >= ood.MEDIUM else "fallback"
        level = max(level, cap, key=("ml", "conservative", "fallback").index)  # the more cautious of the two
        if level == "ml":
            best, source = ranked[0][0], "v2_ml"
        elif level == "conservative":
            safe = [r for r in ranked if r[0].family in gen.CONSERVATIVE]
            best, source = (safe[0][0] if safe else v0_cand), "v2_conservative"
        else:
            why = f"confidence {confidence} < {ood.MEDIUM}" if confidence < ood.MEDIUM else "the model's doubts"
            return PolicySelection(v0, "v0_fallback", confidence, reasons, table, why), None
        if best is v0_cand or not best.valid:
            decision, chosen = self._with_claims(v0, v0_cand), None
        else:
            decision, chosen = self._decision(v0, best), best
        value = next((r[1] for r in ranked if r[0] is best), None)  # V0's candidate may be unranked (invalid)
        why = f"{best.candidate_id}: value {'-' if value is None else f'{value:.4f}'}, confidence {confidence}"
        return PolicySelection(decision, source, confidence, reasons, table, why), chosen

    @staticmethod
    def _with_claims(v0, cand):
        if cand.claims and not v0.claims and cand.valid:
            v0 = copy.copy(v0)
            v0.claims = list(cand.claims)
        return v0

    @staticmethod
    def _decision(v0, cand):
        d = type(v0)(cand.kind, cand.supplier_id)
        d.term_sheets, d.accept_sheet_id = list(cand.term_sheets), cand.accept_sheet_id
        d.claims, d.questions, d.intent = list(cand.claims), list(cand.questions), cand.intent or v0.intent
        return d

    @staticmethod
    def _commit(t, work, decision, chosen):
        for f in STATE_FIELDS:
            setattr(t, f, copy.deepcopy(getattr(work, f)))
        if chosen is not None and decision.kind == "send" and decision.term_sheets:
            # V0 recorded its own price for this move; the move sent is the chosen candidate's
            prices = list(t.our_prices)
            if prices:
                prices[-1] = decision.term_sheets[0]["unit_price"]
            t.our_prices = prices
        elif chosen is not None and decision.kind != "send" and t.our_prices:
            t.our_prices = t.our_prices[:-1]  # V0 offered; V2 accepted or walked instead


def row(c, ranked) -> dict:
    value = next((r[1] for r in ranked if r[0] is c), None)
    return {
        "id": c.candidate_id, "family": c.family, "kind": c.kind, "valid": c.valid,
        "reasons": c.rejection_reasons, "buyer_cost": c.buyer_cost, "saving_vs_open": c.saving_vs_open,
        "value": None if value is None else round(value, 5),
        "price": c.term_sheets[0].get("unit_price") if c.term_sheets else None,
        "features": c.features,
    }  # fmt: skip


def selection_trace(sel: PolicySelection) -> dict:
    """A PolicySelection for the run log (the Decision itself is logged next to it)."""
    rows = [r for r in sel.ranked_candidates if "id" in r]
    latency = next((r["latency_s"] for r in sel.ranked_candidates if "latency_s" in r), None)
    return {
        "policy_source": sel.policy_source, "confidence": sel.confidence, "ood_reasons": sel.ood_reasons,
        "reason": sel.reason, "kind": sel.decision.kind,
        "price": sel.decision.term_sheets[0].get("unit_price") if sel.decision.term_sheets else None,
        "candidates": rows, "latency_s": latency,
    }  # fmt: skip
