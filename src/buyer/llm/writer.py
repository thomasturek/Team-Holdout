"""The writer: Decision -> our e-mail (subject + body). The model writes prose only; code owns every
figure, every claim and every ID.

How it stays safe (DIPLOMAT.md rules, Definition of Done):
1. The model never writes a figure. It writes prose with placeholders - [[CLAIM_n]], [[OFFERS]],
   [[QUESTIONS]] - that code fills: the claim sentences verbatim, each on a line of its own and in
   the Decision's order (so `claim_results[i]` belongs to `Decision.claims[i]`), the term-sheet
   lines, the questions. Sloppy placeholders ([CLAIM_1], {{OFFERS}}) are understood; missing ones
   are injected; extra ones removed; text glued to a placeholder is dropped.
2. A sentence of the model is dropped if it holds a figure (any digit token not in the case title,
   the supplier's name or our questions; a number with a unit; a number in words with a unit), an
   ID of one of our claims (a reworded claim), a leak (urgency, budget, missing alternative, target,
   our C), a person's name the supplier never used, or talk of other suppliers / offers unless the
   Decision's intent asks to signal alternatives.
3. Data IDs that do not exist are removed (`known_id`; as the starter kit's agents/llm.py). The
   greeting never names an invented person; the sign-off is always ours, the model's is cut.
4. `verify_email` checks the result; on any problem - or when the model is off, late (client limits:
   20 s, one retry, 25 s in total), broken, or anything raises - the deterministic template is sent.

Entry points: `write(...) -> Email` and `to_message(...) -> (API message, Email | None)`.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from .client import ATTEMPT_TIMEOUT_S, RETRIES, TOTAL_S, LLMUnavailable, get_client
from .compose import attr, greeting, offers_block, questions_block, sheet_terms, sign_off, subject_for
from .guard import (
    EMPTY_PARENS,
    ID_RE,
    NAME_PAIR_RE,
    PLACEHOLDER_RE,
    TITLE_NAME_RE,
    allowed_tokens,
    canonical_placeholders,
    filter_sentences,
    foreign_numbers,
    isolate_placeholders,
    leaks,
    normalise_text,
    strip_unknown_ids,
    verify_email,
    word_count,
)
from .template import template_body
from .vocab import STYLE

log = logging.getLogger("buyer.llm")

SYSTEM = (Path(__file__).parent / "prompts" / "writer_system.md").read_text(encoding="utf-8")
MAX_TOKENS = 10000
MAX_OWN_WORDS = 160  # the prompt asks for <= 90; above this the model ignored the brief -> template
MIN_OWN_WORDS = 8
HISTORY = 4  # messages of the thread shown to the model
NOTES = 6  # profile notes shown to the model
REGARDS_RE = re.compile(
    r"^\s*(with\s+)?(best|kind|warm|warmest|many)?\s*(regards|wishes)\b"
    r"|^\s*(yours (sincerely|faithfully|truly)|sincerely|viele grüße|mit freundlichen|beste grüße|cheers)\b",
    re.I,
)
# a whole line that is only a closing word: "Thanks,", "Best,", "Cheers"
CLOSING_LINE_RE = re.compile(
    r"^\s*(thanks|many thanks|thank you|best|all the best|cheers|warmly|kind regards|regards|sincerely|"
    r"yours|grüße|gruß)\s*[,.!]?\s*$",
    re.I,
)
GREETING_RE = re.compile(
    r"^\s*(dear|hello|hallo|hi|greetings|good (morning|afternoon|day|evening)|guten tag|sehr geehrte\w*|liebe[rs]?)\b",
    re.I,
)
LEADING_HEADER_RE = re.compile(r"^\s*(re|aw|fwd?|wg|subject|betreff)\s*:.*\n", re.I)
# capitalised words that are no person's name (a pair of unknown capitalised words is taken for one)
COMMON_CAPS = {
    "hollerau", "pumpenwerke", "gmbh", "purchasing", "supplier", "suppliers", "quality", "department", "team",
    "option", "options", "incoterm", "incoterms", "lower", "bavaria", "germany", "german", "europe", "european",
    "dear", "best", "kind", "regards", "thank", "thanks", "we", "our", "your", "you", "the", "please", "as", "in",
    "on", "at", "for", "with", "this", "that", "it", "i", "a", "an", "and", "if", "to", "of", "by", "from", "after",
    "before", "since", "while", "when", "once", "given", "both", "all", "any", "each", "these", "those", "there",
    "here", "so", "but", "also", "however", "therefore", "meanwhile", "unfortunately", "fortunately", "together",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march",
    "april", "may", "june", "july", "august", "september", "october", "november", "december", "eur", "euro",
    "cost", "costs", "breakdown", "report", "delivery", "schedule", "index", "clause", "price", "prices", "unit",
    "order", "confirmation", "quote", "offer", "offers", "proposal", "contract", "framework", "agreement",
    "volute", "casing", "casings", "motor", "motors", "seal", "seals", "pump", "pumps", "series", "part", "parts",
}
GREETING_WORDS = {"dear", "hello", "hi", "good", "morning", "afternoon", "day", "guten", "tag", "mr", "mrs", "ms",
                  "dr", "sir", "madam", "or", "team", "colleagues", "all", "at", "the", "and", "of", "to", "everyone",
                  "partners", "friends", "sales", "purchasing", "hallo", "greetings", "evening", "sehr", "geehrte",
                  "geehrter", "damen", "herren", "liebe", "lieber", "liebes", "und"}  # fmt: skip
# Talk of other suppliers / offers is a negotiating move of the ANALYST: allowed only when the intent asks
# for it ("signal alternatives", "competition", "rival offer")
ALTERNATIVES_RE = re.compile(
    r"\balternatives?\b(?! (?:material|design|variant|grade))"
    r"|\b(?:an)?other (?:suppliers?|vendors?|manufacturers?|foundr(?:y|ies)|shops?|makers?|sources?|offers?|"
    r"quot\w*|bidders?|options on the market)\b"
    r"|\bcompetit\w*|\bsecond source|\brival\w*|\bmarket (?:offers?|quotes?)\b|\belsewhere\b"
    r"|\b(?:cheaper|better|lower) (?:quote|offer|price)s? from\b",
    re.I,
)
SIGNAL_ALT_RE = re.compile(r"alternativ|competit|rival|other (?:offer|supplier|quote|bidder)|second source", re.I)


@dataclass
class Email:
    subject: str
    body: str
    refs: list[str]
    source: str  # "llm" | "template"
    latency_s: float
    warnings: list[str] = field(default_factory=list)


# --- entry points --------------------------------------------------------------------------------------
def to_message(decision, case, thread=None, profile=None, signals=None, **kw):
    """The API message for a Decision: an e-mail for "send", the action for "accept" / "walk".
    Returns (message, Email or None). Keyword arguments go to `write`."""
    kind = attr(decision, "kind")
    if kind == "accept":
        sheet_id = attr(decision, "accept_sheet_id")
        if not sheet_id:
            raise ValueError("accept Decision without accept_sheet_id")
        return {"action": {"type": "accept", "term_sheet_id": sheet_id}}, None
    if kind == "walk":
        return {"action": {"type": "walk_away"}}, None
    email = write(decision, case, thread, profile, signals, **kw)
    sheets = [sheet_terms(s) for s in attr(decision, "term_sheets") or []]
    if len(sheets) > 3:
        log.warning("Decision with %d term sheets: sending the first 3", len(sheets))
    message = {
        "subject": email.subject,
        "body": email.body,
        "term_sheets": [{"terms": dict(t)} for t in sheets[:3]],
        "refs": email.refs,
    }
    return message, email


def write(
    decision, case, thread=None, profile=None, signals=None, *, client=None, known_id=None, deadline=None
) -> Email:
    """Our e-mail for a "send" Decision. Never raises for a "send" Decision: any failure -> template.

    decision  Decision (buyer.interfaces) or dict; kind must be "send"
    case      the case file (only its title and type reach the model)
    thread    this supplier's messages so far, both directions, kit format (oldest first)
    profile   SupplierProfile or dict (name, archetype, notes) - optional
    signals   Signals of the supplier's last e-mail (the reader) - optional
    client    LLMClient (default: the shared "writer" client from the environment)
    known_id  callable(id) -> bool: the ID exists (facts.json, Sunday release, case facts, offers of
              this session). Without it only the IDs of the Decision's claims count as known.
    deadline  optional time.monotonic() by which the model must have answered
    """
    t0 = time.monotonic()
    if attr(decision, "kind") != "send":
        raise ValueError(f"write() needs a 'send' Decision, got {attr(decision, 'kind')!r} - use to_message()")
    warnings: list[str] = []
    thread = [m for m in (thread or []) if isinstance(m, dict)]
    all_claims = list(attr(decision, "claims") or [])
    claims = [c for c in all_claims if isinstance(attr(c, "sentence"), str) and attr(c, "sentence").strip()]
    if len(claims) < len(all_claims):
        warnings.append(f"{len(all_claims) - len(claims)} claim(s) without a sentence skipped")
    if len(claims) > 3:
        warnings.append(f"{len(claims)} claims: only the first 3 are sent (the arena checks at most 3)")
        claims = claims[:3]
    sentences = [attr(c, "sentence").strip() for c in claims]
    claim_refs = list(dict.fromkeys(r for c in claims for r in _refs(c)))
    refs = claim_refs[:20]
    claim_ref_set = set(claim_refs)

    def known(i):
        return i in claim_ref_set or (known_id is not None and bool(known_id(i)))

    try:
        subject = subject_for(case, thread)
    except Exception:  # odd case or thread: a plain subject
        subject = "Re: your offer"
    offers = offers_block(attr(decision, "term_sheets"))
    questions = questions_block(attr(decision, "questions"))
    allowed = allowed_tokens(decision, case, profile)
    injected = [*sentences, offers, questions, sign_off()]
    thread_text = " ".join(str(m.get("body") or "") for m in thread if m.get("from") != "buyer")
    bad = prose_rules(allowed, claim_ref_set, attr(decision, "intent") or "", profile, thread_text, case)

    def fallback(reason):
        warnings.append(f"template: {reason}")
        try:
            body = template_body({**_as_dict(decision), "claims": claims}, case, thread, profile, signals)
            problems = verify_email(body, claims, injected, allowed, known, bad)
        except Exception as e:  # never lose the move
            body, problems = "", [f"template raised {type(e).__name__}: {e}"]
        if problems:  # cannot happen with sane inputs; never send a broken e-mail anyway
            warnings.append(f"template failed its check: {problems}")
            body = _minimal_body(profile, sentences, offers, questions)
        return Email(subject, body, refs, "template", round(time.monotonic() - t0, 3), warnings)

    try:
        client = client or get_client("writer")
        if not client.enabled:
            return fallback("LLM disabled")
        prompt = build_prompt(decision, case, thread, profile, signals, claims, offers, questions)
        text = client.complete(SYSTEM, prompt, timeout_s=ATTEMPT_TIMEOUT_S, retries=RETRIES, total_s=TOTAL_S,
                               max_tokens=MAX_TOKENS, deadline=deadline, tag="writer")  # fmt: skip
        body, why = postprocess(text, claims, offers, questions, profile, known, warnings, thread_text, bad, case)
        if body is None:
            return fallback(why)
        problems = verify_email(body, claims, injected, allowed, known, bad)
        if problems:
            return fallback(f"check failed: {problems}")
    except LLMUnavailable as e:
        return fallback(f"LLM unavailable ({str(e)[:120]})")
    except Exception as e:  # a bug or odd input must not cost the move
        log.exception("writer failed - template")
        return fallback(f"writer raised {type(e).__name__}: {str(e)[:120]}")
    return Email(subject, body, refs, "llm", round(time.monotonic() - t0, 3), warnings)


# --- prompt --------------------------------------------------------------------------------------------
def _as_dict(obj):
    if obj is None:
        return {}
    if dataclasses.is_dataclass(obj):
        return {f.name: getattr(obj, f.name) for f in dataclasses.fields(obj)}
    return dict(obj)


def _clean_note(note) -> str:
    """A profile note without its data IDs - background for the model, never something to cite."""
    note = ID_RE.sub("", str(note))
    note = re.sub(r"\b(?:sup|part|rfq|ctr|doc|news):[\w.:@#/-]*\w", "", note)
    note = EMPTY_PARENS.sub("", note)
    return re.sub(r"\s{2,}", " ", note).strip(" :;-")[:220]


def build_prompt(decision, case, thread, profile, signals, claims, offers, questions) -> str:
    archetype = attr(profile, "archetype") or "unknown"
    name = attr(profile, "name") or "the supplier"
    country = attr(profile, "country")
    lines = [
        f"SUPPLIER: {name}" + (f" ({country})" if country else "") + f" - type: {archetype}",
        f"STYLE: {STYLE.get(archetype, STYLE['unknown'])}",
        f"CASE: {attr(case, 'title') or ''} ({attr(case, 'type') or 'negotiation'})",
        f"INTENT: {attr(decision, 'intent') or 'polite, firm, constructive'}",
    ]
    if signals is not None:
        lines.append("SIGNALS FROM ITS LAST E-MAIL: " + json.dumps(_as_dict(signals), ensure_ascii=False, default=str))
    else:
        lines.append("SIGNALS FROM ITS LAST E-MAIL: none")
    notes = [n for n in (_clean_note(n) for n in (attr(profile, "notes") or [])) if n][:NOTES]
    if notes:
        lines.append("BACKGROUND NOTES (to choose your emphasis - never quote or reveal them):")
        lines += [f"- {n}" for n in notes]
    history = [m for m in (thread or []) if m.get("body")][-HISTORY:]
    if history:
        lines.append("THREAD SO FAR (oldest first, shortened):")
        for m in history:
            if m.get("from") == "buyer":
                lines.append(f"--- US:\n{str(m.get('body'))[:500]}")
            else:
                lines.append(f"--- SUPPLIER (status {m.get('status')}):\n{str(m.get('body'))[:900]}")
    if claims:
        lines.append("CLAIMS - insert each as its placeholder, in this order, each on its own line:")
        lines += [f"[[CLAIM_{i}]] = {attr(c, 'sentence').strip()}" for i, c in enumerate(claims, 1)]
    else:
        lines.append("CLAIMS: none - use no claim placeholder.")
    if offers:
        lines.append("OFFERS - inserted where you put [[OFFERS]]:\n" + offers)
    else:
        lines.append("OFFERS: none this time - use no [[OFFERS]] placeholder and do not propose terms.")
    if questions:
        lines.append("QUESTIONS - inserted where you put [[QUESTIONS]]:\n" + questions)
    else:
        lines.append("QUESTIONS: none - use no [[QUESTIONS]] placeholder.")
    lines.append("SIGN-OFF (end with exactly these lines):\n" + sign_off())
    return "\n".join(lines)


# --- after the model -----------------------------------------------------------------------------------
def _refs(claim) -> list[str]:
    refs = attr(claim, "refs") or []
    if isinstance(refs, str):
        refs = [refs]
    return [r for r in refs if isinstance(r, str)]


def _known_words(profile, thread_text, case=None):
    text = f"{attr(profile, 'name') or ''} {thread_text} {attr(case, 'title') or ''}"
    return {w.lower() for w in re.findall(r"[A-Za-zÄÖÜäöüßÀ-ž]+", text)}


def invented_name(line: str, profile, thread_text: str, case=None) -> bool:
    """True if a greeting line names someone who appears neither in the supplier's name nor in its
    e-mails - the model made the name up ("Dear Mr Huber", "Hallo Anna")."""
    if not GREETING_RE.match(line):
        return False
    known = _known_words(profile, thread_text, case)
    for word in re.findall(r"[A-Za-zÄÖÜäöüßÀ-ž]+", line):
        if word.lower() not in GREETING_WORDS and word[0].isupper() and word.lower() not in known:
            return True
    return False


def prose_rules(allowed, claim_refs, intent, profile, thread_text, case=None):
    """bad(text) -> True if the model's text breaks a writing rule (module docstring, point 2)."""
    may_signal_alternatives = bool(SIGNAL_ALT_RE.search(intent or ""))
    names_ok = _known_words(profile, thread_text, case)

    def unknown_pair(m):
        a, b = m.group(1).lower(), m.group(2).lower()
        return not ({a, b} & (names_ok | COMMON_CAPS))

    def bad(text):
        return (
            leaks(text)
            or bool(foreign_numbers(text, allowed))
            or any(r in text for r in claim_refs)  # a reworded claim: the arena would check it again
            or (not may_signal_alternatives and bool(ALTERNATIVES_RE.search(text)))
            or any(n.lower() not in names_ok for n in TITLE_NAME_RE.findall(text))
            or any(unknown_pair(m) for m in NAME_PAIR_RE.finditer(text))
        )

    return bad


def _unwrap(text: str) -> str:
    """Join the lines of each paragraph into one, so a sentence split by a line break is filtered as
    one sentence. Placeholder lines and intro lines ending in ":" stay lines of their own."""
    paras = []
    for para in re.split(r"\n\s*\n", text):
        out, buf = [], []
        for line in para.split("\n"):
            line = line.strip()
            if not line:
                continue
            if PLACEHOLDER_RE.fullmatch(line):
                if buf:
                    out.append(" ".join(buf))
                    buf = []
                out.append(line)
            elif line.endswith(":"):
                buf.append(line)
                out.append(" ".join(buf))
                buf = []
            else:
                buf.append(line)
        if buf:
            out.append(" ".join(buf))
        if out:
            paras.append("\n".join(out))
    return "\n\n".join(paras)


def postprocess(text, claims, offers, questions, profile, known, warnings, thread_text="", bad=None, case=None):
    """(body, None) or (None, why). Applies every rule of the module docstring."""
    bad = bad or (lambda s: False)
    t = normalise_text(text).strip()
    t = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", t).strip()
    while LEADING_HEADER_RE.match(t):
        t = LEADING_HEADER_RE.sub("", t, count=1).lstrip()
    t = re.sub(r"^\s*body\s*:\s*", "", t, flags=re.I)
    t = canonical_placeholders(t)
    # the model's own sign-off and everything after it: ours is appended at the end
    lines = t.split("\n")
    cut = next((i for i, ln in enumerate(lines) if i > 0 and (REGARDS_RE.match(ln) or CLOSING_LINE_RE.match(ln))), None)
    if cut is not None:
        t = "\n".join(lines[:cut])
    # greeting lines with an invented name: the first becomes ours, any other goes
    lines, seen_text = [], False
    for ln in t.split("\n"):
        short = len(ln) <= 80
        if short and GREETING_RE.match(ln) and invented_name(ln, profile, thread_text, case):
            warnings.append(f"replaced greeting with an invented name: {ln[:60]!r}")
            if not seen_text:
                lines.append(greeting(profile))
            seen_text = True
            continue
        seen_text = seen_text or bool(ln.strip())
        lines.append(ln)
    t = "\n".join(lines)
    # a claim the model copied: the placeholder carries it
    for c in claims:
        s = attr(c, "sentence").strip()
        if s in t:
            t = t.replace(s, "")
            warnings.append(f"model copied claim {attr(c, 'key')} - kept the placeholder only")
    t, glued = isolate_placeholders(t)
    if glued:
        warnings.append(f"dropped text glued to placeholders: {[g[:60] for g in glued]}")
    t = _unwrap(t)
    t, dropped_ids = strip_unknown_ids(t, known)
    if dropped_ids:
        warnings.append(f"removed unknown IDs {dropped_ids}")
    t, dropped = filter_sentences(t, bad)
    if dropped:
        warnings.append(f"dropped {len(dropped)} sentence(s): {[d[:80] for d in dropped]}")
    words = word_count(t)
    if words > MAX_OWN_WORDS:
        return None, f"model wrote {words} words"
    if words < MIN_OWN_WORDS:
        return None, f"model wrote only {words} words"

    # fill placeholders: claims in the Decision's order whatever their number; each block once
    nxt = 0
    used: set[str] = set()

    def fill(m):
        nonlocal nxt
        name = m.group(1)
        if name in ("CLAIM", "CLAIMS"):
            if nxt >= len(claims):
                warnings.append(f"removed placeholder {m.group(0)}")
                return ""
            if name == "CLAIMS":
                rest = [attr(c, "sentence").strip() for c in claims[nxt:]]
                nxt = len(claims)
                return "\n".join(rest)
            nxt += 1
            return attr(claims[nxt - 1], "sentence").strip()
        if name in used:
            return ""
        used.add(name)
        if name == "OFFERS" and offers:
            return offers
        if name == "QUESTIONS" and questions:
            return questions
        warnings.append(f"removed placeholder {m.group(0)}")
        return ""

    t = PLACEHOLDER_RE.sub(fill, t)

    paras = [p.strip() for p in re.split(r"\n\s*\n", t) if p.strip()]
    # inject what the model left out: claims next to the placed ones (or after the opening), offers
    # and questions before the closing line
    joined = "\n\n".join(paras)
    missing_claims = [attr(c, "sentence").strip() for c in claims[nxt:]]
    if missing_claims:
        warnings.append(f"injected {len(missing_claims)} claim(s)")
        placed = [i for i, p in enumerate(paras) if any(attr(c, "sentence").strip() in p for c in claims[:nxt])]
        if placed:
            paras[placed[-1]] = paras[placed[-1]] + "\n" + "\n".join(missing_claims)
        else:
            paras.insert(min(2, len(paras)), "\n".join(missing_claims))
    closing_at = len(paras) - 1 if len(paras) > 2 else len(paras)
    if offers and offers not in joined:
        warnings.append("injected the offers")
        paras.insert(closing_at, offers)
        closing_at += 1
    if questions and questions not in joined:
        warnings.append("injected the questions")
        paras.insert(closing_at, questions)
    if not paras:
        return None, "nothing left after the checks"
    if not GREETING_RE.match(paras[0]):
        warnings.append("added the greeting")
        paras.insert(0, greeting(profile))
    paras.append(sign_off())
    body = "\n\n".join(paras)
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body, None


def _minimal_body(profile, sentences, offers, questions) -> str:
    """Last resort: only code-made text, never over the arena's 8,000 characters (claims that do not
    fit are left out - a 422 would cost the whole move)."""
    head, tail = [greeting(profile), "Thank you for your message."], [sign_off()]
    blocks = [b for b in (offers, questions) if b]
    body = "\n\n".join(head + blocks + tail)
    fitting = []
    for s in sentences:
        if len(body) + len(s) + 2 + sum(len(f) + 1 for f in fitting) <= 8000:
            fitting.append(s)
    parts = head + (["\n".join(fitting)] if fitting else []) + blocks + tail
    return "\n\n".join(parts)[:8000]
