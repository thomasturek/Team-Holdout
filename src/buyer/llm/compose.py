"""Deterministic pieces of our e-mails, written by code - never by the model: the term-sheet lines,
the questions, the subject, greeting and sign-off. Every figure in an e-mail comes from here or from
a claim sentence.

Objects may be the dataclasses of `buyer.interfaces` or plain dicts with the same field names.
"""

from __future__ import annotations

import os
import re

from .vocab import QUESTIONS

SIGNATURE = os.environ.get("BUYER_SIGNATURE", "Purchasing\nHollerau Pumpenwerke GmbH")
SIGN_OFF = "Best regards"
LETTERS = "ABC"


def attr(obj, name, default=None):
    """`obj.name` or `obj[name]` - dataclasses and dicts alike."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def sheet_terms(sheet) -> dict:
    """A Decision term sheet: the terms dict itself, or {"terms": {...}, ...} as the API wraps it
    (no negotiable field is called "terms")."""
    if isinstance(sheet, dict) and isinstance(sheet.get("terms"), dict):
        return sheet["terms"]
    return sheet if isinstance(sheet, dict) else {}


def _money(v):
    return f"EUR {float(v):,.2f}"


def _int(v):
    return f"{int(round(float(v))):,}"


def term_phrase(field, value) -> str:
    """One negotiable field in words, with its exact value. Never raises: an odd value is shown as is."""
    try:
        return _term_phrase(field, value)
    except (TypeError, ValueError, AttributeError):
        return f"{str(field).replace('_', ' ')} {value}"


def _term_phrase(field, value) -> str:
    if value is None and field != "index_clause":
        return f"{field.replace('_', ' ')} as per your standard terms"
    if field == "unit_price":
        return f"unit price {_money(value)}"
    if field == "payment_days":
        return f"payment {int(value)} days net"
    if field == "lead_time_days":
        return f"lead time {int(value)} days"
    if field == "volume_per_year":
        return f"binding volume {_int(value)} units per year"
    if field == "contract_months":
        return "single order" if int(value) == 0 else f"contract term {int(value)} months"
    if field == "effective_date":
        return f"new price valid from {value}"
    if field == "index_clause":
        if not value:
            return "no index clause"
        if not isinstance(value, dict):
            return f"index clause {value}"
        share = float(value.get("material_share", 0)) * 100
        share_txt = f"{share:.0f}" if abs(share - round(share)) < 1e-9 else f"{share:g}"
        return (f"index clause on {value.get('series')} ({share_txt} % material share, "
                f"deadband {float(value.get('deadband_pct', 0)):g} %, base {value.get('base_month')})")  # fmt: skip
    if field == "incoterm":
        return f"Incoterm {value}"
    if field == "tooling_eur":
        return f"tooling {_money(value)}"
    if field == "ppm_commitment":
        return f"quality commitment {_int(value)} ppm"
    if field == "chargeback_eur_per_complaint":
        return f"chargeback {_money(value)} per complaint"
    return f"{field.replace('_', ' ')} {value}"


def offer_line(terms: dict) -> str:
    return "; ".join(term_phrase(f, v) for f, v in terms.items()) + "."


def offers_block(term_sheets) -> str:
    """The term sheets in words, with their own one-line introduction. Empty without sheets."""
    sheets = [t for t in (sheet_terms(s) for s in (term_sheets or [])) if t][:3]
    if not sheets:
        return ""
    if len(sheets) == 1:
        return "Our proposal: " + offer_line(sheets[0])
    lines = ["We can offer you the following options:"]
    lines += [f"Option {LETTERS[i]}: {offer_line(t)}" for i, t in enumerate(sheets)]
    return "\n".join(lines)


def question_text(q: str) -> str:
    """A Decision question ("cost breakdown", "earliest lead time" ...) as one polite question."""
    q = str(q or "").strip()
    low = q.lower()
    for _key, words, text in QUESTIONS:
        if any(w in low for w in words):
            return text
    if not q:
        return ""
    q = q[0].upper() + q[1:]
    if q.endswith("?"):
        return q
    return f"Could you also tell us about the following: {q.rstrip('.')}?"


def questions_block(questions) -> str:
    out = []
    for q in questions or []:
        t = question_text(q)
        if t and t not in out:
            out.append(t)
    return " ".join(out)


def subject_for(case, thread=None) -> str:
    """Re: the supplier's latest subject (one "Re:"), else Re: the case title; at most 300 chars."""
    subject = None
    for m in reversed(thread or []):
        if m.get("from") != "buyer" and m.get("subject"):
            subject = m["subject"]
            break
    subject = subject or attr(case, "title") or "Your offer"
    subject = re.sub(r"^\s*((re|aw|fwd?|wg)\s*:\s*)+", "", str(subject), flags=re.I).strip()
    return ("Re: " + subject)[:300]


def greeting(profile=None) -> str:
    name = attr(profile, "name")
    return f"Dear colleagues at {name}," if name else "Dear Sir or Madam,"


def sign_off() -> str:
    return f"{SIGN_OFF}\n{SIGNATURE}"
