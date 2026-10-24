"""Safety of what we send. Code, not the model, guarantees the Definition of Done:

- every claim sentence of the Decision is in the e-mail verbatim, on a line of its own (placeholders
  filled by code, missing ones injected; nothing glued to it);
- the model's prose holds no figure at all: a sentence with a digit token that is not in the case
  title, the supplier's name or our questions ("HN 50-200", "IE3", "8D"), a number with a unit
  ("8%", "EUR 120") or a number in words with a unit ("ten percent") is dropped. Every figure comes
  from code (claim sentences, term-sheet lines);
- data IDs that do not exist are removed (`strip_unknown_ids`, as `agents/llm.py` does);
- sentences that leak (urgency, budget, missing alternative, target, our C) are dropped.
"""

from __future__ import annotations

import re
import unicodedata

from .compose import attr
from .vocab import LEAK_RE

CHECKABLE = "idx|quote|offer|sc|qn|po|cost|fc|news|doc|ctr"
# Checkable data IDs - the same types as the starter kit's agents/llm.py. Their digits are not
# "numbers" in prose (unknown ones are stripped before); any other "word:123" token's digits are.
ID_RE = re.compile(rf"\b(?:{CHECKABLE}):[\w.:@#/-]*\w")
# The canonical placeholders the model is asked to write: [[CLAIM_1]], [[OFFERS]], [[QUESTIONS]]
PLACEHOLDER_RE = re.compile(r"\[\[([A-Z]+)(?:_(\d+))?\]\]")
# What models write instead: [CLAIM_1], [[claim 1]], {{OFFERS}}, [[Claim1]], <<claim_1>>, ⟦OFFERS⟧ ...
LOOSE_PLACEHOLDER_RE = re.compile(
    r"[\[{<⟦［【]{1,2}\s*(claims?|offers?|questions?)[\s_-]*(\d*)\s*[\]}>⟧］】]{1,2}", re.I
)
# Anything placeholder-like left in a finished body (brackets in any case; the bare words only in
# capitals - "your offers" in prose is fine)
RESIDUE_RE = re.compile(
    r"\[\[|\]\]|\{\{|\}\}|<<|>>|\{%|%\}|[⟦⟧［］【】]"
    r"|[\[{(<]\s*(?i:claim|offer|question|insert|placeholder)"
    r"|\b(?:CLAIMS?|OFFERS|QUESTIONS)(?:_\d+)?\b"
)
DIGIT_TOKEN_RE = re.compile(r"[^\s()\[\]{}<>\"',;:!?]*\d[^\s()\[\]{}<>\"',;:!?]*")
UNITS = (
    r"%|％|percent(?:age)?(?:\s+points?)?\b|per ?cent\b|prozent\w*|eur\b|euros?\b|€|\$|dollars?\b|usd\b|cents?\b|"
    r"units?\b|pcs\b|pieces?\b|parts\b|stück\b|per (?:piece|part|unit)\b|days?\b|tage\w*|weeks?\b|wochen\b|"
    r"months?\b|monate\w*|years?\b|jahre\w*|hours?\b|minutes?\b|k\b|ppm\b|tons?\b|tonnes?\b|kg\b|times\b"
)
NUMBER_UNIT_RE = re.compile(rf"\d[\d.,]*\s*(?:{UNITS})|(?:\beur\b|\beuro\b|€|\$|\busd\b)\s*\d", re.I)
_NW = (
    r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
    r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|"
    r"thousand|million|half|double|twice|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|"
    r"zwanzig|dreißig|vierzig|fünfzig|sechzig|siebzig|achtzig|neunzig|hundert|tausend"
)
NUMBER_WORD_RE = re.compile(
    rf"\b(?:{_NW})(?:[\s-]+(?:{_NW}|and|point|a|und))*[\s-]*(?:{UNITS})"
    rf"|(?:\beur\b|\beuro\b|€|\$|\busd\b)\s*(?:{_NW})\b",
    re.I,
)
# a sentence ends at . ! ? - but not after "Mr." / "Dr." / "e.g." ...
SENTENCE_SPLIT = re.compile(
    r"(?<!\bMr\.)(?<!\bMrs\.)(?<!\bMs\.)(?<!\bDr\.)(?<!\bSt\.)(?<!\be\.g\.)(?<!\bi\.e\.)(?<!\bNo\.)(?<=[.!?])\s+"
)
EMPTY_PARENS = re.compile(r"\s*\(\s*[,;\s]*\)")
TITLE_NAME_RE = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Herr|Frau)\.?\s+([A-ZÄÖÜ][\w'-]+)")
NAME_PAIR_RE = re.compile(r"\b([A-ZÄÖÜ][a-zäöüß]+)\s+([A-ZÄÖÜ][a-zäöüß]{2,})\b")
SPACES_RE = re.compile(r"[ \t\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]+")
INVISIBLE_RE = re.compile(r"[\u200b-\u200d\u2060\ufeff\u00ad]")
MARKDOWN_RE = re.compile(r"\*\*|__|^#{1,6}\s+|^\s*[-*•]\s+", re.M)


def normalise_text(text: str) -> str:
    """One kind of space, one kind of line break, no invisible characters, no markdown emphasis -
    so no word-filter can be dodged by odd whitespace."""
    t = INVISIBLE_RE.sub("", text or "")
    t = t.replace("\r\n", "\n").replace("\r", "\n").replace("\u2028", "\n").replace("\u2029", "\n\n")
    t = SPACES_RE.sub(" ", t)
    return MARKDOWN_RE.sub("", t)


# --- numbers -----------------------------------------------------------------------------------------
def _numerals_as_digits(text: str) -> str:
    """Superscripts, circled numbers, roman numeral signs, fractions (Unicode No / Nl) count as digits."""
    if text.isascii():
        return text
    return "".join("0" if unicodedata.category(c) in ("No", "Nl") else c for c in text)


def _clean(text: str) -> str:
    """Text without placeholders and checkable IDs: what is left is prose."""
    return _numerals_as_digits(ID_RE.sub(" ", PLACEHOLDER_RE.sub(" ", text or "")))


def digit_tokens(text: str) -> list[str]:
    """Every word with a digit in it ("50-200", "IE3", "8%", "2027-04-01"), IDs and placeholders left out."""
    return [t.rstrip(".") for t in DIGIT_TOKEN_RE.findall(_clean(text))]


def allowed_tokens(decision=None, case=None, profile=None) -> set[str]:
    """Digit tokens the model's prose may contain: those of the case title (part names such as
    "HN 50-200"), the supplier's name and our questions ("8D"). Never a figure of the Decision: those
    reach the e-mail through code only."""
    out = set()
    texts = [str(attr(case, "title", "") or ""), str(attr(profile, "name", "") or "")]
    texts += [str(q) for q in attr(decision, "questions") or []]
    for t in texts:
        out.update(digit_tokens(t))
    return out


def foreign_numbers(text: str, allowed: set[str]) -> list[str]:
    """Why a text holds a figure it must not: foreign digit tokens, numbers with units, numbers in words."""
    prose = _clean(text)
    found = [t for t in digit_tokens(text) if t not in allowed]
    found += [m.group(0) for m in NUMBER_UNIT_RE.finditer(prose)]
    found += [m.group(0) for m in NUMBER_WORD_RE.finditer(prose)]
    return found


# --- IDs ---------------------------------------------------------------------------------------------
def strip_unknown_ids(text: str, known) -> tuple[str, list[str]]:
    """Remove checkable IDs for which `known(id)` is false. Returns (text, removed IDs)."""
    dropped = []

    def keep(m):
        if known(m.group(0)):
            return m.group(0)
        dropped.append(m.group(0))
        return ""

    out = ID_RE.sub(keep, text or "")
    if dropped:
        out = re.sub(r"[,;]\s*(?=[,;)])", "", out)  # "(idx:A, )" -> "(idx:A)"
        out = re.sub(r"\(\s*[,;]\s*", "(", out)  # "(, idx:A)" -> "(idx:A)"
        out = EMPTY_PARENS.sub("", out)
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"[ \t]+([.,;:])", r"\1", out)
    return out, dropped


# --- placeholders ------------------------------------------------------------------------------------
def canonical_placeholders(text: str) -> str:
    """[CLAIM_1], [[claim 1]], {{OFFERS}}, [[Claim1]] ... -> [[CLAIM_1]], [[OFFERS]]."""

    def fix(m):
        word, n = m.group(1).upper(), m.group(2)
        if word.startswith("CLAIM"):
            return f"[[CLAIM_{n}]]" if n else ("[[CLAIMS]]" if word == "CLAIMS" else "[[CLAIM]]")
        return "[[OFFERS]]" if word.startswith("OFFER") else "[[QUESTIONS]]"

    return LOOSE_PLACEHOLDER_RE.sub(fix, text or "")


def isolate_placeholders(text: str) -> tuple[str, list[str]]:
    """Every placeholder on a line of its own, nothing glued to it: a claim must reach the arena as
    the exact sentence the SCOUT verified. Text before a placeholder stays (as its own line) only if
    it ends with ":" ("Our data shows:"); other text on that line is dropped."""
    dropped, out = [], []
    for line in text.split("\n"):
        parts = re.split(r"(\[\[[A-Z]+(?:_\d+)?\]\])", line)
        if len(parts) == 1:
            out.append(line)
            continue
        for i, part in enumerate(parts):
            if PLACEHOLDER_RE.fullmatch(part):
                out.append(part)
            elif part.strip():
                if i == 0 and part.strip().endswith(":"):
                    out.append(part.strip())
                else:
                    dropped.append(part.strip())
    return "\n".join(out), dropped


# --- sentences ---------------------------------------------------------------------------------------
def filter_sentences(text: str, bad) -> tuple[str, list[str]]:
    """Drop every sentence for which `bad(sentence)` is true; placeholder-only lines stay. Line breaks
    and paragraphs are kept. Returns (text, dropped sentences)."""
    dropped, lines = [], []
    for line in (text or "").split("\n"):
        if PLACEHOLDER_RE.fullmatch(line.strip() or "x"):
            lines.append(line.strip())
            continue
        keep = []
        for s in SENTENCE_SPLIT.split(line.strip()):
            if not s:
                continue
            if bad(s):
                dropped.append(s)
            else:
                keep.append(s)
        if keep or not line.strip():
            lines.append(" ".join(keep))
        # a line whose sentences were all dropped disappears
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out, dropped


def leaks(sentence: str) -> bool:
    return bool(LEAK_RE.search(PLACEHOLDER_RE.sub(" ", sentence)))


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-zÄÖÜäöüß']+", PLACEHOLDER_RE.sub(" ", text or "")))


# --- final check -------------------------------------------------------------------------------------
def verify_email(body: str, claims, injected, allowed: set[str], known=None, bad=None) -> list[str]:
    """Problems of a finished e-mail body; empty means it may be sent.

    - each claim sentence present verbatim as a line of its own;
    - outside the code-made blocks (`injected`: claim sentences, offers, questions, sign-off) no
      figure the prose may not hold (`foreign_numbers`);
    - no checkable ID that `known` rejects (outside the claim sentences);
    - nothing placeholder-like left; at most 8,000 characters; not empty;
    - `bad(text) -> bool` (the writer's sentence rules), run once more on all prose as one line - a
      backstop against sentence splits and line breaks that hid a phrase from the sentence filter."""
    problems = []
    lines = {ln.strip() for ln in body.split("\n")}
    for c in claims or []:
        s = (attr(c, "sentence") or "").strip()
        if s and s not in lines:
            problems.append(f"claim missing, changed or not on its own line: {attr(c, 'key')}")
    rest = body
    for block in sorted((b for b in injected if b), key=len, reverse=True):
        rest = rest.replace(block, " ")
    figures = foreign_numbers(rest, allowed)
    if figures:
        problems.append(f"foreign numbers: {figures}")
    if known is not None:
        unknown = [i for i in ID_RE.findall(rest) if not known(i)]
        if unknown:
            problems.append(f"unknown IDs: {unknown}")
    if bad is not None and bad(" ".join(rest.split())):
        problems.append("the prose as a whole breaks a writing rule")
    if RESIDUE_RE.search(rest):
        problems.append("placeholder residue in body")
    if len(body) > 8000:
        problems.append("body longer than 8,000 characters")
    if not body.strip():
        problems.append("empty body")
    return problems
