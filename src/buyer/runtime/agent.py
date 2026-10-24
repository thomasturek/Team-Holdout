"""Agents the runtime can play, by name: `new_agent(name, params)` gives one agent per case.

The runtime asks an agent for one supplier's next move at a time (see `threads.py`):
  decide(case, threads, supplier_id) -> {"supplier_id", "message"[, "trace"]}
  closing(case, threads) -> {"supplier_id", "message"}            (optional)

  naive   the kit's NaiveAgent, per thread: the baseline to beat
  llm     the kit's LLMAgent, per thread (needs ANTHROPIC_API_KEY)
  policy  the Analyst's Policy (src/buyer/policy) with a plain template e-mail - no Scout facts,
          no Diplomat yet. What the harvester plays, with the parameter sets from explore.json.
"""

import json
import math
import os
import threading

from arena_kit.docs import standard_terms
from arena_kit.play import closing_move, latest, moves_left, standing

from .env import ROOT

EXPLORE = ROOT / "src" / "buyer" / "policy" / "explore.json"
SIGNATURE = "Best regards\nHollerau Pumpenwerke, Purchasing"


class PerThread:
    """A kit agent (`decide(case, threads)` picks any supplier) asked about one thread at a time:
    it sees only that thread, so its move is for that supplier."""

    def __init__(self, kit_agent):
        self.kit_agent, self._lock = kit_agent, threading.Lock()

    def decide(self, case, threads, supplier_id):
        with self._lock:  # the kit agents keep no state, but are not written for threads either
            return self.kit_agent.decide(case, {supplier_id: threads[supplier_id]})


class PolicyAgent:
    """The Analyst's Policy over the runtime's threads: keeps one ThreadState per supplier, updated
    from the messages before every decision; turns its Decision into a message."""

    def __init__(self, params=None):
        from buyer.policy.policy import Policy, load_params

        self.policy = Policy({**load_params(), **(params or {})})  # a partial set changes only what it names
        self.states, self._lock = {}, threading.Lock()  # the policy is fast plain code: one at a time

    def _state(self, case, sid, events):
        from buyer.policy.policy import ThreadState

        sheet_id, terms = standing(events)
        t = self.states.get(sid)
        if t is None:
            t = self.states[sid] = ThreadState(sid, sheet_id, terms, "open", {}, 0)
        t.standing_id, t.standing_terms = sheet_id, terms
        t.status = latest(events).get("status") or "open"
        t.standard = standard_terms(events) or t.standard
        t.rounds_left = moves_left(case, events)
        t.their_prices = [
            m["term_sheets"][0]["terms"].get("unit_price")
            for m in events
            if m.get("from") != "buyer" and m.get("term_sheets")
        ]
        return t

    def decide(self, case, threads, supplier_id):
        with self._lock:
            states = {sid: self._state(case, sid, ev) for sid, ev in threads.items()}
            t = states[supplier_id]
            live = [
                o for o in states.values() if o is not t and o.standing_id and o.status not in ("walked_away", "no_bid")
            ]
            rival = min((self.policy.cost(case, o) for o in live), default=math.inf)
            decision = self.policy.decide(case, t, rival_best_c=rival)
        return {**to_message(decision, threads[supplier_id]), "trace": {"decision": decision, "rival_best_c": rival}}

    def closing(self, case, threads):
        with self._lock:
            states = {sid: self._state(case, sid, ev) for sid, ev in threads.items()}
            decision = self.policy.closing(case, states)
        return to_message(decision, threads[decision.supplier_id])


class PaymentProbe:
    """Harvest probe: every term sheet the agent sends proposes `payment_days` (one of the case's
    options) instead of what the agent chose - how do suppliers price other payment terms?"""

    def __init__(self, agent, payment_days):
        self.agent, self.days = agent, payment_days

    def decide(self, case, threads, supplier_id):
        d = self.agent.decide(case, threads, supplier_id)
        msg = d["message"]
        if not msg.get("term_sheets") or "payment_days" not in case["negotiable"]:
            return d
        sheets = []
        for ts in msg["term_sheets"]:
            terms = {**ts["terms"], "payment_days": self.days}
            if terms not in [s["terms"] for s in sheets]:  # sheets that differed only in payment days
                sheets.append({**ts, "terms": terms})
        trace = {**(d.get("trace") or {}), "probe": {"payment_days": self.days, "agent_sheets": msg["term_sheets"]}}
        return {**d, "message": {**msg, "term_sheets": sheets}, "trace": trace}

    def closing(self, case, threads):
        if hasattr(self.agent, "closing"):
            return self.agent.closing(case, threads)
        return closing_move(case, threads)


def probes(case):
    """The probe variants for a case: push past a final offer; propose each payment term the case
    allows; both together."""
    days = case.get("term_options", {}).get("payment_days") or [] if "payment_days" in case["negotiable"] else []
    return [
        {"push_final": True},
        *({"payment_days": d} for d in days),
        *({"push_final": True, "payment_days": d} for d in days),
    ]


def probe_agent(name, params, probe):
    """An agent for a probe variant: push_final through the policy's own parameter, payment days
    through PaymentProbe."""
    if probe.get("push_final"):
        params = {**(params or {}), "push_final": 1.0}  # the policy pushes once after a final offer
    agent = new_agent(name, params)
    return PaymentProbe(agent, probe["payment_days"]) if "payment_days" in probe else agent


def to_message(decision, events):
    """A Decision as the runtime sends it. Until the Diplomat's writer exists: a plain template."""
    sid = decision.supplier_id
    if decision.kind == "accept":
        return {
            "supplier_id": sid,
            "message": {"action": {"type": "accept", "term_sheet_id": decision.accept_sheet_id}},
        }
    if decision.kind == "walk":
        return {"supplier_id": sid, "message": {"action": {"type": "walk_away"}}}
    subject = next((m.get("subject") for m in events if m.get("subject")), "Your offer")
    sheets = [{"terms": ts} for ts in decision.term_sheets]
    options = "the term sheet" if len(sheets) == 1 else "the alternative term sheets"
    body = (
        "Dear Sir or Madam,\n\nthank you for your offer. Please find our proposal in "
        f"{options} attached; we would be glad to agree on one of them.\n\n{SIGNATURE}"
    )
    return {
        "supplier_id": sid,
        "message": {
            "subject": subject if subject.startswith("Re:") else f"Re: {subject}",
            "body": body,
            "term_sheets": sheets,
        },
    }


def new_agent(name="naive", params=None):
    if name == "naive":
        from arena_kit.agents import NaiveAgent

        keep = {k: v for k, v in (params or {}).items() if k in ("anchor", "close_gap")}
        return PerThread(NaiveAgent(**keep))
    if name == "llm":
        from arena_kit.agents import LLMAgent, llm_from_env
        from arena_kit.data import DataPackage

        data = os.environ.get("ARENA_DATA")
        package = DataPackage(data) if data else None
        return PerThread(LLMAgent(llm_from_env(), package))
    if name == "policy":
        return PolicyAgent(params)
    raise ValueError(f"unknown agent {name!r}: naive, llm or policy")


def explore_params(path=None):
    """The parameter sets the Analyst wants harvested (a JSON list of dicts). Without the file: one
    empty set, i.e. the policy's params.json. The Operator runs and logs them; it never picks them."""
    try:
        sets = json.loads((path or EXPLORE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [{}]
    if isinstance(sets, dict):  # {"sets": [...]} is fine too
        sets = sets.get("sets", [sets])
    return sets or [{}]
