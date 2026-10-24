"""The reader: a supplier's e-mail -> `Signals` (AGENTS.md section 3) for the ANALYST.

The model (fast, <= 10 s, strict JSON) reads the prose; code validates every field and normalises
it to the fixed vocabularies in `vocab.py`. Fields the model got wrong or left out are taken from the
keyword rules; when the model is off, late or broken, the keyword rules give all of them.
`final_offer_language` is also true whenever the reply's status is `final_offer`.

The reader reads e-mail prose. Figures in attachments (quote PDF, cost breakdown ...) are the SCOUT's
(`update_profile`); the model sees a short excerpt of them for qualitative remarks only, the rules
never read them (their labels - "Payment terms", "Volume per year" - would look like asks).

Entry points: `read(...) -> Reading` (with source and latency, for the logs) and
`read_signals(...) -> Signals`.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from buyer.interfaces import Signals

from .client import READER_TIMEOUT_S, RETRIES, LLMUnavailable, get_client
from .compose import attr
from .vocab import ASK_WORDS, ASKS, DRIVER_WORDS, DRIVERS, LOOSE_SERIES_RE, SERIES_RE, TONES

log = logging.getLogger("buyer.llm")

SYSTEM = (Path(__file__).parent / "prompts" / "reader_system.md").read_text(encoding="utf-8")
MAX_TOKENS = 10000
FIELDS = [f.name for f in dataclasses.fields(Signals)]
BOOL_FIELDS = ("cash_pressure", "capacity_issue", "final_offer_language", "approval_pending")
LIST_FIELDS = ("cost_drivers_claimed", "accepted_args", "rejected_args", "asks", "offered_variants")
MAX_ITEMS = 8


@dataclass
class Reading:
    signals: Signals
    source: str  # "llm" | "llm+rules" | "rules"
    latency_s: float
    error: str | None = None
    from_rules: list[str] = field(default_factory=list)  # fields the rules filled in


def neutral_signals() -> Signals:
    return Signals(False, False, False, False, [], [], [], [], [], "neutral")


# --- keyword rules -----------------------------------------------------------------------------------
def _re(*alternatives):
    return re.compile("|".join(alternatives), re.I)


CASH_RE = _re(
    r"cash ?flow",
    r"liquidit",
    r"\bpay (?:us |our invoices |the invoices )?(?:earlier|faster|sooner|quicker)",
    r"\bpay (?:us |our invoices |the invoices )?within (?:[1-9]|1\d|ten|seven|five|fourteen) days",
    r"faster payment",
    r"earlier payment",
    r"quicker payment",
    r"prompt payment",
    r"prepayment",
    r"advance payment",
    r"cash discount",
    r"\bskonto",
    r"overdue",
    r"outstanding invoices",
    r"\b(?:our|the) bank\b(?! (?:details|account|holiday|transfer|code))",
    r"liquidität",
    r"pay (?:our invoices |the invoices |us )?late",
    r"late payments?",
    r"paid late",
    r"\bhausbank\b",
    r"kürzere(?:s|n)? zahlungsziel",
)
CAPACITY_RE = _re(
    r"fully booked",
    r"full order book",
    r"order (?:intake|book) is (?:very )?(?:strong|full)",
    r"\b(?:are|is|run(?:ning)?|operat\w*|work\w*) at (?:full )?capacity",
    r"capacity is (?:tight|limited|full|short|fully)",
    r"limited capacity",
    r"no (?:free|spare|additional) capacity",
    r"capacity (?:constraint|limit|bottleneck)",
    r"bottleneck",
    r"\b(?:on|under|delivery|capacity|customer) allocation",
    r"\ballocat(?:e|ing) (?:our |the )?(?:capacity|volumes?|quantities)",
    r"(?:material|component|supply|chip|semiconductor|steel|casting|raw material) shortages?",
    r"shortages? of (?:material|raw material|components?|parts|chips|semiconductors|steel|castings)",
    r"extended (?:our )?(?:lead|delivery) times?",
    r"longer (?:lead|delivery) times",
    r"(?:lead|delivery) times? (?:have|has) (?:been )?(?:extended|increased)",
    r"only against a binding",
    r"\bfully (?:loaded|utili[sz]ed|occupied)\b",
    r"ausgelastet",
    r"kapazitätsengpass",
    r"keine (?:freien )?kapazität",
)
FINAL_RE = _re(
    r"(?<!your )(?<!not our )(?<!not a )(?<!not the )(?<!not my )(?<!means our )\bfinal offer\b",
    r"\b(?:this|here|that) is (?:our|my) last offer\b",
    r"(?:the )?best we can do",
    r"(?:will|can) ?not go (?:any )?(?:lower|further)",
    r"won't go (?:any )?(?:lower|further)",
    r"(?<!not )\bour (?:final|last) (?:price|position|word|proposal)",
    r"best and final",
    r"cannot (?:go|move) (?:any )?(?:further|lower)",
    r"can't (?:go|move) (?:any )?(?:further|lower)",
    r"no further (?:room|movement|concession|reduction)",
    r"(?:this|that) is as far as",
    r"\bour last word",
    r"(?<!ihr )(?<!kein )letztes angebot",
    r"final position",
    r"absolute (?:limit|minimum)",
    r"take it or leave it",
    r"reached the (?:end|limit) of what we can",
    r"\bwould rather (?:decline|walk away|not (?:take|accept) (?:the|this) (?:order|business))",
    r"(?<!kein )(?<!nicht unser )\bunser letztes wort",
    r"weiter können wir (?:\w+ ){0,3}nicht",
)
# forward-looking only: "head office has frozen prices" is a fact, not a pending approval
APPROVAL_RE = _re(
    r"\b(?:needs?|requires?|subject to|waiting for|awaiting|seek|ask for|asked for|get) "
    r"(?:the |an? |their |our )?(?:management(?:'s)? |board(?:'s)? |internal |formal |final )?"
    r"(?:approval|sign-off|consent)",
    r"(?:check|discuss|clarify|align) (?:this |it |that )?with (?:our|my) (?:managing director|management|boss|"
    r"board|owner|head office|headquarters|sales director|director)",
    r"mit (?:der|unserer) geschäftsführung (?:abstimmen|besprechen|klären)",
    r"\bapprove (?:this|it|the|such|your)",
    r"(?:has|have|needs?) to approve",
    r"(?:pricing|price) committee",
    r"forward(?:ed)? (?:it|this|your \w+) to (?:our|the) "
    r"(?:management|managing director|board|committee|head office|owner|boss)",
    r"\b(?:our|the) (?:management|managing director|board|owner|boss|head office|headquarters) "
    r"(?:has to|must|needs to|will) (?:decide|approve|look|review|check)",
    r"(?:check|discuss|clarify|review) (?:this |it |your \w+ )?internally",
    r"exceeds my (?:authority|mandate)",
    r"beyond my (?:authority|mandate)",
    r"freigabe",
    r"decision is not (?:mine|ours|my own) alone",
    r"present (?:it|this|your \w+) to (?:him|her|our (?:owner|management|managing director|board|director|boss))",
)
APPROVED_RE = _re(
    r"(?:has|have) (?:now )?(?:been )?approved",
    r"approval (?:was|has been) (?:given|granted)",
    r"(?:management|committee|board) (?:has |have )?(?:agreed|approved|signed off)",
)
ACCEPT_RE = _re(
    r"fair point",
    r"did not know",
    r"didn't know",
    r"were not aware",
    r"\bit holds\b",
    r"\b(?:they|the figures?) holds?\b",
    r"took (?:it|this|that) into account",
    r"taken (?:it|this|that) into account",
    r"you are right",
    r"you're right",
    r"valid point",
    r"good point",
    r"we accept your (?:argument|point|figure)",
    r"we agree with your",
)
REJECT_RE = _re(
    r"not our reality",
    r"does(?:n't| not) reflect our",
    r"does(?:n't| not) apply to us",
    r"not relevant (?:to|for) us",
    r"bought (?:\w+ )?forward",
    r"\bhedged\b",
    r"covered at fixed prices",
    r"fixed prices until",
    r"\bour costs are different",
    r"does(?:n't| not) change (?:our|anything)",
    r"irrelevant (?:to|for) us",
    r"market (?:prices?|index|indices|figures?) (?:is|are) not (?:what|our)",
)
VARIANT_RE = _re(
    r"variant",
    r"alternative (?:material|design|grade|casting|alloy|version)",
    r"\binstead of\b",
    r"cheaper (?:version|design|material|option|alternative)",
    r"design change",
    r"value engineering",
    r"redesign",
    r"simplif",
    r"lower[- ]cost (?:version|design|material|option)",
)
IRRITATED_RE = _re(
    r"disappoint",
    r"frustrat",
    r"unacceptable",
    r"not acceptable",
    r"irritat",
    r"annoy",
    r"(?<!pleasantly )surprised (?:by|at|that)",
    r"we are surprised",
    r"\binsist",
    r"\bour patience",
    r"\bpatience is (?:running|wearing|at)",
    r"review our (?:conditions|cooperation|business)",
    r"reconsider (?:our|the) (?:business|relationship|cooperation)",
    r"end (?:our|the|these) (?:negotiation|talks|cooperation|discussion)",
    r"waste of time",
    r"not serious",
    r"offended",
    r"enttäuscht",
    r"ridiculous",
    r"tired of",
    r"fed up",
    r"absurd",
    r"insulting",
    r"outrageous",
    r"no longer willing",
    r"no basis for (?:further|any)",
    r"withdraw (?:our|the) (?:offer|quote)",
    r"with all due respect",
    r"for the (?:third|fourth|fifth|umpteenth) time",
    r"(?:third|fourth|fifth) time (?:that )?we (?:have to |must )?explain",
)
WARM_RE = _re(
    r"\bpleasure\b",
    r"happy to",
    r"glad to",
    r"delighted",
    r"appreciate",
    r"valued (?:customer|partner)",
    r"long(?:-standing| standing)? (?:partnership|cooperation|relationship)",
    r"thank you for your (?:trust|loyalty|kind)",
    r"we value",
    r"gerne",
    r"gern ",
    r"look forward to (?:continuing|our|working)",
    r"good (?:cooperation|collaboration|partnership)",
)
# Rules for asks: phrases only (bare words like "volume" or "payment terms" also appear when a
# supplier merely states its terms)
ASK_RULES = (
    ("faster_payment", _re(
        r"faster payment",
        r"earlier payment",
        r"quicker payment",
        r"pay (?:us |our invoices )?(?:earlier|faster|sooner|quicker)",
        r"pay (?:our invoices )?within (?:[1-9]|1\d|ten|seven|five|fourteen) days",
        r"prepayment",
        r"advance payment",
        r"cash discount",
        r"\bskonto",
        r"shorter payment (?:terms?|target)",
        r"payment helps our cash",
        r"kürzere(?:s|n)? zahlungsziel",
    )),
    ("volume", _re(
        r"(?:more|additional|higher|larger|extra) (?:volume|parts|quantities|business|work)",
        r"free (?:machine )?capacity",
        r"spare capacity",
        r"fill (?:our|the) capacity",
        r"volume (?:commitment|agreement|guarantee)",
        r"customers with volume",
        r"bigger (?:lots|orders)",
    )),
    ("longer_contract", _re(
        r"multi-?year",
        r"longer (?:contract|agreement|contract term)",
        r"longer[- ]term (?:contract|agreement|commitment|framework)",
        r"long-?term (?:agreement|contract|commitment)",
        r"binding (?:\d+|twelve|twenty-four)[- ]month",
        r"binding commitment",
        r"(?:two|three)-year",
        r"contract (?:length|duration|period) of",
    )),
    ("forecast", _re(
        r"forecast",
        r"planning security",
        r"call-?off (?:plan|schedule|visibility|flexibility)",
        r"(?:demand|volume) visibility",
    )),
    ("earlier_effective_date", _re(
        r"earlier (?:effective|start)",
        r"apply (?:sooner|earlier)",
        r"effective earlier",
        r"cannot postpone",
    )),
    ("index_clause", _re(
        r"index clause",
        r"price adjustment clause",
        r"escalation clause",
        r"indexation",
        r"index-?linked",
        r"price escalation",
    )),
    ("longer_lead_time", _re(
        r"longer lead time",
        r"more time to deliver",
        r"extend the lead time",
        r"lead time of at least",
    )),
    ("tooling_payment", _re(
        r"tooling (?:cost|payment|contribution|invoice)",
        r"pay (?:for )?the tooling",
        r"tooling (?:must|has to|needs to) be paid",
    )),
    ("incoterm", _re(
        r"ex works only",
        r"only (?:deliver |supply |ship )?ex works",
        r"(?:must|have to|need to|prefer to) (?:deliver|supply|ship) ex works",
        r"collect the goods",
        r"pick (?:them|the goods|the parts) up",
        r"freight (?:terms|costs? (?:must|have to|are on you))",
    )),
)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


# A signature or footer line ("Geschäftsführer: …", "Bank: Sparkasse …", "IBAN …") is no signal
FOOTER_RE = re.compile(
    r"^\s*(?:geschäftsführ\w*|managing directors?|bank|bankverbindung|iban|bic|swift|sitz|registergericht|"
    r"amtsgericht|hrb|hra|ust-?id\w*|vat(?: no| id)?|tel\.?|telefon|phone|fax|e-?mail|www\.|steuer\w*)\b\s*[:.]?",
    re.I,
)
NEGATION_BEFORE_RE = re.compile(
    r"(?:\b(?:no|not|without|never|nor|nothing|none|kein\w*|nicht)\b|n't)\W+(?:\w+\W+){0,3}$", re.I
)
NEGATION_AFTER_RE = re.compile(
    r"^\W*(?:\w+\W+){0,3}(?:would not|wouldn't|won't|will not|does not|doesn't|do not|don't|cannot|can't|"
    r"makes no|is not|isn't|are not|aren't|not possible|nicht|kein\w*|"
    r"(?:is|are) (?:excellent|solid|good|strong|healthy|fine|stable|sound))\b",
    re.I,
)
# a sentence that talks about costs or prices: only there does a material word blame a cost driver
COST_CONTEXT_RE = re.compile(
    r"cost|price|rose|rise|risen|rising|raised|increase|higher|expensive|surcharge|inflation|went up|gone up|"
    r"move with|driven by|due to|because of|gestiegen|teurer|kosten|preis",
    re.I,
)


def _prose(body: str) -> str:
    """The e-mail without signature and footer lines."""
    return "\n".join(ln for ln in (body or "").split("\n") if not FOOTER_RE.match(ln))


def _hit(rx, text: str, after: bool = False) -> bool:
    """A match of `rx` in `text` that is not negated: no "no / not / without ..." in the three words
    before it, and with `after` also no "would not / does not ..." in the two words after it
    ("Higher volume would not change our price")."""
    for m in rx.finditer(text):
        if NEGATION_BEFORE_RE.search(text[max(0, m.start() - 40):m.start()]):
            continue
        if after and NEGATION_AFTER_RE.search(text[m.end():m.end() + 40]):
            continue
        return True
    return False


def _drivers(text: str) -> list[str]:
    out = []
    for sentence in _sentences(text):
        if not COST_CONTEXT_RE.search(sentence):
            continue
        for code in SERIES_RE.findall(sentence):
            if code not in out:
                out.append(code)
        low = sentence.lower()
        for canon, words in DRIVER_WORDS:
            if canon not in out and any(re.search(r"\b" + re.escape(w), low) for w in words):
                out.append(canon)
    return out


def _claim_list(last_decision):
    return [c for c in (attr(last_decision, "claims") or []) if attr(c, "key")]


def _claims_in(sentence: str, claims) -> list[str]:
    """Claim keys a sentence refers to: the tail of the key ("PPI-D351" of "index:PPI-D351") or one of
    its refs appears in it."""
    low = sentence.lower()
    out = []
    for c in claims:
        key = attr(c, "key")
        tail = key.split(":", 1)[-1].lower()
        refs = [r.lower() for r in attr(c, "refs") or []]
        if (len(tail) >= 3 and tail in low) or any(r in low for r in refs):
            out.append(key)
    return out


def _verified_keys(message, claims) -> list[str]:
    results = message.get("claim_results") or []
    out = []
    for r in results:
        i = r.get("index")
        if r.get("result") == "verified" and isinstance(i, int) and 0 <= i < len(claims):
            out.append(attr(claims[i], "key"))
    return out


def rule_signals(message: dict, last_decision=None) -> Signals:
    """Signals from keyword rules over the e-mail body (no attachments, no signature or footer).
    Deterministic, instant."""
    body = _prose(str(message.get("body") or ""))
    claims = _claim_list(last_decision)
    sentences = _sentences(body)
    accepted, rejected = [], []
    acc_s = [s for s in sentences if ACCEPT_RE.search(s)]
    rej_s = [s for s in sentences if REJECT_RE.search(s)]
    for s in acc_s:
        accepted += _claims_in(s, claims)
    for s in rej_s:
        rejected += _claims_in(s, claims)
    verified = _verified_keys(message, claims)
    if acc_s and not accepted:
        accepted = verified if (verified and not rej_s) else ["accepted an argument"]
    if rej_s and not rejected:
        rejected = verified if (verified and not acc_s) else ["not our reality"]
    asks = [name for name, rx in ASK_RULES if _hit(rx, body, after=True)]
    variants = [s[:160] for s in sentences if VARIANT_RE.search(s)][:3]
    tone = "irritated" if _hit(IRRITATED_RE, body) else "warm" if _hit(WARM_RE, body) else "neutral"
    return Signals(
        cash_pressure=_hit(CASH_RE, body, after=True),
        capacity_issue=_hit(CAPACITY_RE, body),
        final_offer_language=bool(FINAL_RE.search(body)) or message.get("status") == "final_offer",
        approval_pending=_hit(APPROVAL_RE, body) and not APPROVED_RE.search(body),
        cost_drivers_claimed=_drivers(body),
        accepted_args=list(dict.fromkeys(accepted)),
        rejected_args=list(dict.fromkeys(rejected)),
        asks=asks,
        offered_variants=variants,
        tone=tone,
    )


# --- the model's answer -> validated fields ------------------------------------------------------------
def parse_json(text: str) -> dict:
    """The first JSON object in the model's answer (tolerates code fences and chatter, also a "{" in
    the chatter before it)."""
    t = re.sub(r"```(?:json)?", "", text or "")
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", t):
        try:
            obj, _ = decoder.raw_decode(t[m.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise ValueError(f"no JSON object in {(text or '')[:120]!r}")


def _bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, int | float) and v in (0, 1):
        return bool(v)
    if isinstance(v, str) and v.strip().lower() in ("true", "yes", "1", "false", "no", "0"):
        return v.strip().lower() in ("true", "yes", "1")
    raise ValueError(f"not a boolean: {v!r}")


def _strings(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list | tuple):
        raise ValueError(f"not a list: {v!r}")
    out = []
    for x in v:
        if isinstance(x, dict):  # {"key": ...} or {"name": ...}
            x = x.get("key") or x.get("name") or x.get("value") or ""
        s = re.sub(r"\s+", " ", str(x)).strip()
        if s and s not in out:
            out.append(s)
    return out[:MAX_ITEMS]


def normalise_ask(s: str) -> str:
    low = s.lower().strip()
    if low in ASKS:
        return low
    if low.replace(" ", "_") in ASKS:
        return low.replace(" ", "_")
    if low == "other" or low.startswith("other:"):
        rest = low.split(":", 1)[-1].strip() if ":" in low else low[5:].strip()
        return f"other: {rest[:60]}" if rest else "other"
    for canon, words in ASK_WORDS:
        if any(w in low for w in words):
            return canon
    return f"other: {low[:60]}"


def normalise_driver(s: str) -> str | None:
    s = s.strip()
    if SERIES_RE.fullmatch(s) or LOOSE_SERIES_RE.fullmatch(s):
        return s
    low = s.lower()
    if low in DRIVERS:
        return low
    if low.replace(" ", "_") in DRIVERS:
        return low.replace(" ", "_")
    for canon, words in DRIVER_WORDS:
        if any(re.search(r"\b" + re.escape(w), low) for w in words):
            return canon
    m = SERIES_RE.search(s)
    return m.group(0) if m else None


def normalise_arg(s: str, claims) -> str:
    keys = [attr(c, "key") for c in claims]
    if s in keys:
        return s
    for k in keys:
        if s.lower() == k.lower():
            return k
    found = _claims_in(s, claims)
    if len(found) == 1:
        return found[0]
    return s[:80]


def coerce(obj: dict, claims=()) -> dict:
    """The valid, normalised fields of the model's JSON; invalid or missing fields are left out."""
    out = {}
    for f in BOOL_FIELDS:
        if f in obj:
            try:
                out[f] = _bool(obj[f])
            except ValueError:
                pass
    for f in LIST_FIELDS:
        if f not in obj:
            continue
        try:
            items = _strings(obj[f])
        except ValueError:
            continue
        if f == "asks":
            items = list(dict.fromkeys(normalise_ask(x) for x in items))
        elif f == "cost_drivers_claimed":
            items = list(dict.fromkeys(d for d in (normalise_driver(x) for x in items) if d))
        elif f in ("accepted_args", "rejected_args"):
            items = list(dict.fromkeys(normalise_arg(x, claims) for x in items))
        else:
            items = [x[:200] for x in items]
        out[f] = items
    tone = obj.get("tone")
    if isinstance(tone, str) and tone.strip().lower() in TONES:
        out["tone"] = tone.strip().lower()
    return out


# --- prompt and entry points ---------------------------------------------------------------------------
def build_prompt(message: dict, last_decision=None) -> str:
    claims = _claim_list(last_decision)
    lines = [
        f"STATUS: {message.get('status')}",
        f"CLAIM RESULTS (index = our argument in order): {json.dumps(message.get('claim_results') or [])}",
    ]
    if claims:
        lines.append("OUR CLAIMS in our last e-mail (key: sentence):")
        lines += [f"- {attr(c, 'key')}: {attr(c, 'sentence')}" for c in claims]
    else:
        lines.append("OUR CLAIMS in our last e-mail: none")
    lines.append(f"SUPPLIER E-MAIL from {message.get('from')}, subject {message.get('subject')!r}:")
    lines.append(str(message.get("body") or "")[:4000])
    atts = [a for a in message.get("attachments") or [] if a.get("text")][:2]
    if atts:
        lines.append("ATTACHMENTS (their figures are read elsewhere - use them only for qualitative remarks):")
        lines += [f"[{a.get('name')}]\n{str(a['text'])[:600]}" for a in atts]
    return "\n".join(lines)


def read(message: dict, *, last_decision=None, client=None, deadline=None, use_llm=True) -> Reading:
    """Signals of one supplier e-mail.

    message        the supplier's message as the API returns it (kit format: body, status,
                   claim_results, attachments with "text")
    last_decision  our Decision this e-mail answers (to map accepted / rejected arguments to claim keys)
    client         LLMClient (default: the shared "reader" client from the environment)
    deadline       optional time.monotonic() by which the model must have answered
    use_llm        False = keyword rules only
    """
    t0 = time.monotonic()
    rules = rule_signals(message, last_decision)

    def done(signals, source, error=None, from_rules=()):
        return Reading(signals, source, round(time.monotonic() - t0, 3), error, list(from_rules))

    client = client or get_client("reader")
    if not use_llm or not client.enabled:
        return done(rules, "rules", None if not use_llm else "LLM disabled", FIELDS)
    try:
        text = client.complete(SYSTEM, build_prompt(message, last_decision), timeout_s=READER_TIMEOUT_S,
                               retries=RETRIES, total_s=READER_TIMEOUT_S, max_tokens=MAX_TOKENS,
                               deadline=deadline, tag="reader")  # fmt: skip
    except LLMUnavailable as e:
        return done(rules, "rules", f"LLM unavailable: {str(e)[:160]}", FIELDS)
    try:
        fields = coerce(parse_json(text), _claim_list(last_decision))
    except (ValueError, json.JSONDecodeError) as e:
        log.warning("reader: invalid JSON from the model (%s) - keyword rules", e)
        return done(rules, "rules", f"invalid JSON: {str(e)[:120]}", FIELDS)
    if not fields:
        return done(rules, "rules", "no valid field in the model's JSON", FIELDS)
    merged = {**dataclasses.asdict(rules), **fields}
    merged["final_offer_language"] = bool(merged["final_offer_language"]) or message.get("status") == "final_offer"
    missing = [f for f in FIELDS if f not in fields]
    return done(Signals(**merged), "llm+rules" if missing else "llm", None, missing)


def read_signals(message: dict, **kw) -> Signals:
    return read(message, **kw).signals
