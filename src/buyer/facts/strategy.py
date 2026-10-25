"""Negotiation strategies (SCOUT): which way to play a supplier, from what we know about it - and when
to switch, from what its replies reveal.

    from buyer.facts.strategy import choose
    s = choose(case, profile)                              # before the first e-mail
    s = choose(case, profile, signals, thread, current=s)  # after each reply
    s.name, s.reason, s.tone, s.params                     # params: overrides for the policy (Thomas)

Five strategies, each from something the practice logs showed (2026-10-24/25):

    aggressive   deep anchor, small steps, three claims - RFQs (P05: a rival's offer brought the biggest
                 first move of all), hungry suppliers, and once our arguments land
    cooperative  moderate anchor, lever trades, relationship tone - strategic cases, family firms with a
                 history of loyalty, irritated suppliers
    patient      reciprocal small steps, hold when it holds, trade instead of conceding - suppliers that
                 move in tiny steps (groups with an approval ladder)
    escalate     approver memo, ask to take Option A up - contacts with little authority (Inside Sales
                 at Leitner, Donautal, Werdenfels) or an approval pending
    secure       modest anchor, close near the target, never push - sole sources and short capacity,
                 where walking away scores 0 (P10's supplier goes final at once when pressed)

The facts layer chooses; the policy plays the numbers (``params`` are overrides of its parameters -
the values are starting points for Thomas to tune); the writer takes ``tone``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

LOW_AUTHORITY = ("inside sales", "sales assistant", "sales office", "customer service", "order desk")

TONES = {
    "aggressive": "firm and confident: the evidence and the competition speak; no softening, no apology",
    "cooperative": "warm and constructive: a fair deal for both sides, built on the options that give it what "
                   "it asked for",
    "patient": "calm and steady: we hold our line, move only when it moves, and offer other terms instead of price",
    "escalate": "respectful to our contact, and approver-ready: one paragraph its decision-maker can approve, and "
                "a clear request to take Option A up",
    "secure": "businesslike and reassuring: planning security and a reliable partnership; close, do not push",
}

# overrides of the policy's parameters (policy.DEFAULTS / params.json) - starting points to tune
PARAMS = {
    "aggressive": {"open_frac": 0.05, "min_open_discount_pct": 12.0, "concede": 0.08, "claims_per_msg": 3,
                   "lever_trades": 1.0},
    "cooperative": {"open_frac": 0.2, "min_open_discount_pct": 6.0, "concede": 0.15, "push_final": 0.0,
                    "lever_trades": 1.0},
    "patient": {"reciprocity": 1.0, "token_frac": 0.25, "stall_limit": 3, "concede": 0.1, "lever_trades": 1.0},
    "escalate": {"open_frac": 0.15, "min_open_discount_pct": 8.0, "concede": 0.12, "push_final": 0.0,
                 "lever_trades": 1.0},
    "secure": {"open_frac": 0.3, "min_open_discount_pct": 4.0, "concede": 0.2, "push_final": 0.0,
               "accept_target_pct": 3.0},
}


@dataclass
class Strategy:
    name: str
    reason: str
    tone: str = ""
    params: dict = field(default_factory=dict)


def _make(name: str, reason: str) -> Strategy:
    return Strategy(name, reason, TONES[name], dict(PARAMS[name]))


def _get(obj, key, default=None):
    if obj is None:
        return default
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _observed(profile) -> dict:
    sid = _get(profile, "supplier_id")
    if not sid:
        return {}
    try:
        from .dossier import observed

        return observed(sid)
    except Exception:
        return {}


def _holds(thread) -> int:
    """Replies in a row at the end of the thread in which the supplier's price did not move."""
    prices = [((m.get("term_sheets") or [{}])[0].get("terms") or {}).get("unit_price")
              for m in thread or [] if m.get("from") != "buyer" and m.get("term_sheets")]
    holds = 0
    for a, b in zip(prices[-2::-1], prices[::-1], strict=False):  # newest pair first
        if a is None or b is None or b < a - 1e-9:
            break
        holds += 1
    return holds


def initial(case: dict, profile: dict | None) -> Strategy:
    """The strategy for the first e-mail, from the case and what we know about the supplier."""
    goal = (case.get("buyer") or {}).get("category_goal")
    kind = _get(profile, "archetype") or "unknown"
    o = _observed(profile)
    role = (o.get("contact_role") or "").lower()
    said = set(o.get("said") or [])
    if len(case.get("suppliers") or []) > 1:
        return _make("aggressive", "several bidders compete: rival offers are our strongest lever")
    if goal == "secure_supply" or kind == "near_monopolist" or case.get("type") == "capacity" \
            or (o.get("replies_to_final") is not None and o["replies_to_final"] <= 1):
        return _make("secure", "a sole source or short capacity: walking away costs everything, so close safely")
    if any(w in role for w in LOW_AUTHORITY) or "committee" in said:
        return _make("escalate", f"our contact ({role or 'sales'}) does not decide alone: take Option A to who does")
    if (_get(profile, "cash_pressure") or 0) >= 0.5 or {"needs_cash", "free_capacity"} & said:
        return _make("aggressive", "a hungry supplier (cash or free capacity): it needs this business")
    if _get(profile, "approval_style") == "ladder" or kind == "group_ladder":
        return _make("patient", "a group with an approval ladder moves in small steps: hold and trade")
    if goal == "stabilise" or kind == "family_foundry":
        return _make("cooperative", "a strategic supply or a family firm: a fair, lasting deal pays most")
    return _make("cooperative", "no strong signal: constructive by default")


def choose(case: dict, profile: dict | None, signals=None, thread=None, current: Strategy | None = None) -> Strategy:
    """The strategy for our next e-mail: the initial one, switched by what the supplier's last reply
    revealed (signals from the reader, the thread so far)."""
    base = current or initial(case, profile)
    if signals is None and not thread:
        return base
    several = len(case.get("suppliers") or []) > 1
    if _get(signals, "tone") == "irritated":
        return _make("cooperative", "it is irritated: de-escalate before anything else")
    if _get(signals, "approval_pending"):
        return _make("escalate", "it waits for an approval: make Option A easy to approve")
    if _get(signals, "final_offer_language") and not several:
        return _make("secure", "it called its offer final and we have no other bidder: close safely")
    if _get(signals, "accepted_args") and base.name in ("cooperative", "patient"):
        return _make("aggressive", "our arguments land: keep the pressure on")
    if _holds(thread) >= 2 and base.name in ("aggressive", "cooperative"):
        return _make("patient", "it held twice: stop conceding, trade other terms instead")
    return base
