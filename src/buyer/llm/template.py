"""The template writer: a deterministic e-mail from a Decision, no LLM. Used when the model is off,
late or broken - so it must be good enough to negotiate on its own.

Every sentence is fixed text without digits; figures come only from the claim sentences and the
term-sheet lines (`compose`). Same inputs, same e-mail.
"""

from __future__ import annotations

import re

from .compose import attr, greeting, offers_block, questions_block, sheet_terms, sign_off, subject_for
from .vocab import ASK_SENTENCES, CLOSING, CONCERN_SENTENCES, DRIVER_PHRASES, DRIVERS

MAX_CONCERNS = 3
# the intent marks a closing move: "final", "closing move", "best and final", "last offer / round"
FINAL_INTENT_RE = re.compile(r"\b(?:final|closing|best and final|last (?:offer|round|move|push))\b", re.I)


def _has_previous_buyer_message(thread) -> bool:
    return any(m.get("from") == "buyer" for m in thread or [])


def concern_sentences(signals, decision=None) -> list[str]:
    """Up to three sentences that show we read the supplier's last e-mail."""
    if signals is None:
        return []
    out = []
    if attr(signals, "final_offer_language"):
        out.append(CONCERN_SENTENCES["final_offer_language"])
    if attr(signals, "tone") == "irritated":
        out.append(CONCERN_SENTENCES["irritated"])
    if attr(signals, "rejected_args"):
        out.append(CONCERN_SENTENCES["rejected_args"])
    elif attr(signals, "accepted_args"):
        out.append(CONCERN_SENTENCES["accepted_args"])
    if attr(signals, "approval_pending"):
        out.append(CONCERN_SENTENCES["approval_pending"])
    if attr(signals, "capacity_issue"):
        out.append(CONCERN_SENTENCES["capacity_issue"])
    sheets = attr(decision, "term_sheets") or []
    offers_payment = any("payment_days" in sheet_terms(s) for s in sheets)
    if attr(signals, "cash_pressure") and offers_payment:
        out.append(CONCERN_SENTENCES["cash_pressure"])
    drivers = [d for d in attr(signals, "cost_drivers_claimed") or [] if d]
    if drivers:
        words = [DRIVER_PHRASES[d] for d in dict.fromkeys(drivers) if d in DRIVERS]
        if words:
            listed = words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]
            out.append(f"We have read your remarks on {listed} carefully.")
        else:
            out.append("We have read your remarks on the cost indices carefully.")
    for ask in attr(signals, "asks") or []:
        if ask in ASK_SENTENCES and not (ask == "faster_payment" and CONCERN_SENTENCES["cash_pressure"] in out):
            out.append(ASK_SENTENCES[ask])
    return list(dict.fromkeys(out))[:MAX_CONCERNS]


def closing_sentence(profile=None, decision=None) -> str:
    archetype = attr(profile, "archetype") or "unknown"
    text = CLOSING.get(archetype, CLOSING["unknown"])
    if FINAL_INTENT_RE.search(str(attr(decision, "intent") or "")):
        text = "This is our best proposal at this stage. " + text
    return text


def template_body(decision, case=None, thread=None, profile=None, signals=None) -> str:
    parts = [greeting(profile)]
    opener = "Thank you for your reply." if _has_previous_buyer_message(thread) else "Thank you for your quote."
    parts.append(" ".join([opener, *concern_sentences(signals, decision)]))
    claims = [s.strip() for s in (attr(c, "sentence") for c in attr(decision, "claims") or [])
              if isinstance(s, str) and s.strip()][:3]  # fmt: skip
    if claims:
        parts.append("\n".join(claims))
    offers = offers_block(attr(decision, "term_sheets"))
    if offers:
        parts.append(offers)
    questions = questions_block(attr(decision, "questions"))
    if questions:
        parts.append(questions)
    parts.append(closing_sentence(profile, decision))
    parts.append(sign_off())
    return "\n\n".join(parts)


def template_email(decision, case=None, thread=None, profile=None, signals=None) -> tuple[str, str]:
    """(subject, body)"""
    return subject_for(case, thread), template_body(decision, case, thread, profile, signals)
