"""Fixed vocabularies of the DIPLOMAT: what the reader may put into `Signals`, how the writer and the
template phrase questions and concerns, and which words leak.

`Signals` keeps the `list[str]` types of AGENTS.md; these vocabularies only fix the values, so the
ANALYST can act on them with plain `in` checks:

- `Signals.asks`                 one of ASKS, or "other: <few words>"
- `Signals.cost_drivers_claimed` an index series code as the supplier wrote it ("LCI-C", "PPI-C241"),
                                 or one of DRIVERS
- `Signals.accepted_args` / `rejected_args`
                                 the `Claim.key` of our argument when the reader can tell which one,
                                 else a few words
- `Signals.tone`                 one of TONES
"""

import re

# --- Signals values ------------------------------------------------------------------------------

TONES = ("warm", "neutral", "irritated")

ASKS = (
    "faster_payment",  # pay earlier, cash discount, prepayment
    "volume",  # more volume, more parts, fill free capacity
    "longer_contract",  # multi-year agreement, binding commitment
    "forecast",  # planning security, call-off visibility, delivery schedule
    "earlier_effective_date",  # the new price should apply sooner
    "index_clause",  # price follows an index / adjustment clause
    "longer_lead_time",  # more time to deliver
    "tooling_payment",  # tooling paid by us / up front
    "incoterm",  # a different freight split (e.g. EXW instead of DAP)
)

DRIVERS = (
    "energy",
    "labour",
    "raw_material",
    "steel",
    "copper",
    "aluminium",
    "nickel",
    "electronics",
    "polymers",
    "logistics",
    "financing",
)

# An index series code of the data package (index_series.csv): PPI-C241, LCI-C, WB-CU, CU-NOTATION,
# AS-14404, ECB-USD, SMARD-DA ... Known prefixes only, so material grades (GJS-400, GJL-250) and
# norms (ISO-9001) are not taken for series. Used by the keyword rules.
SERIES_RE = re.compile(r"\b(?:PPI|LCI|WB|ECB|SMARD|CU|AS|GP\d{0,2}|CPI|HICP)-[A-Z0-9]{1,12}(?:-[A-Z0-9]{1,12})*\b")
# Any code that looks like a series - to accept a series the model names that is not known yet
# (e.g. from the Sunday release)
LOOSE_SERIES_RE = re.compile(r"\b(?!(?:ISO|EN|DIN|VDA|IATF|GJS|GJL|GS|DAP|FCA|EXW|EUR|HN|HB|HI|HX)-)"
                             r"[A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]{1,12})+\b")  # fmt: skip

# words -> canonical driver (checked in this order; first hit wins per word)
DRIVER_WORDS = (
    ("energy", ("energy", "electricity", "power price", "gas price", "natural gas", "strom", "energie")),
    ("labour", ("wage", "labour", "labor", "personnel cost", "staff cost", "salar", "collective agreement",
                "lohn", "löhne", "tarifvertrag", "tariflohn")),
    ("copper", ("copper", "kupfer")),
    ("aluminium", ("aluminium", "aluminum")),
    ("nickel", ("nickel", "alloy surcharge", "alloys", "stainless", "legierung")),
    ("steel", ("steel", "iron", "scrap", "pig iron", "stahl", "schrott")),
    ("electronics", ("electronic", "semiconductor", "chip", "component prices")),
    ("polymers", ("rubber", "elastomer", "polymer", "resin", "plastic", "ptfe", "epdm")),
    ("logistics", ("logistics", "freight", "transport", "shipping", "fuel")),
    ("financing", ("interest rate", "financing cost", "cost of capital")),
    ("raw_material", ("raw material", "material cost", "material price", "materials", "rohstoff")),
)

# words -> canonical ask
ASK_WORDS = (
    ("faster_payment", ("faster payment", "pay earlier", "earlier payment", "shorter payment", "within 10 days",
                        "within ten days", "prepayment", "advance payment", "cash discount", "skonto",
                        "pay our invoices", "payment term", "zahlungsziel", "quicker payment", "pay faster")),
    ("volume", ("more volume", "additional volume", "higher volume", "larger volume", "additional parts",
                "more parts", "larger quantities", "bigger lots", "free capacity", "spare capacity",
                "fill our capacity", "volume")),
    ("longer_contract", ("multi-year", "multiyear", "longer contract", "long-term agreement", "longer term",
                         "binding 12-month", "binding commitment", "framework agreement", "contract length",
                         "longer agreement", "two-year", "three-year")),
    ("forecast", ("forecast", "planning security", "call-off", "call off", "delivery schedule", "visibility")),
    ("earlier_effective_date", ("earlier effective", "earlier start", "apply sooner", "from an earlier date",
                                "effective earlier", "as early as")),
    ("index_clause", ("index clause", "price adjustment clause", "escalation clause", "indexation",
                      "price escalation", "index-linked", "index linked")),
    ("longer_lead_time", ("longer lead time", "more time to deliver", "extend the lead time", "extended lead time")),
    ("tooling_payment", ("tooling",)),
    ("incoterm", ("incoterm", "ex works", "exw", "pick up", "pickup", "collect the goods", "freight terms")),
)

# --- Writer and template ---------------------------------------------------------------------------

# How we write to each SCOUT archetype (AGENTS.md: SupplierProfile.archetype).
STYLE = {
    "family_foundry": (
        "Family-owned firm: personal, warm and long-term. Show respect for the owner and the years of "
        "reliable cooperation; speak of partnership and of a fair solution for both family companies."
    ),
    "group_ladder": (
        "Part of a group with an approval ladder: structured, clear and approval-friendly. Present the "
        "options so they are easy to take to a pricing committee; offer to provide what their approval needs."
    ),
    "cash_short_jobshop": (
        "Job shop where cash and steady work matter: emphasise reliable, punctual payment and steady "
        "call-offs; point to the payment timing in the options. Never mention its finances."
    ),
    "near_monopolist": (
        "Near-monopolist that barely moves on price: calm and businesslike; emphasise planning security, "
        "volume and contract security in the options; no pressure, no threats."
    ),
    "unknown": "Professional, friendly and to the point.",
}

CLOSING = {
    "family_foundry": "We value our long cooperation and are confident we will find a fair solution together.",
    "group_ladder": "If your approval process needs anything further from us, we are glad to provide it.",
    "cash_short_jobshop": "You can count on us as a reliable customer with steady orders and punctual payment.",
    "near_monopolist": (
        "We are interested in a stable, long-term supply relationship with planning security for both sides."
    ),
    "unknown": "We look forward to your reply.",
}

# Decision.questions -> one polite question. Matched by keywords; unknown questions are used as written.
QUESTIONS = (
    ("cost_breakdown", ("breakdown", "calculation", "cost structure", "cost split"),
     "Could you send us a cost breakdown for this part?"),
    ("8d_report", ("8d", "corrective", "root cause", "quality plan", "improvement plan"),
     "Could you send us your 8D report and a binding improvement plan?"),
    ("delivery_schedule", ("schedule", "delivery plan", "call-off plan"),
     "Could you share your delivery schedule for the coming months?"),
    ("lead_time", ("lead time", "leadtime", "delivery time", "earliest delivery"),
     "What is the earliest lead time you can commit to?"),
    ("variants", ("variant", "alternative material", "alternative design", "cheaper option", "engineering"),
     "Are there cheaper engineering or material variants you would suggest?"),
    ("capacity", ("capacity",),
     "How much capacity can you reserve for us?"),
    ("payment", ("payment",),
     "Which payment terms would help you most?"),
    ("contract_volume", ("volume", "contract length", "longer contract", "commitment"),
     "Would a longer contract or a firm annual volume change your price?"),
    ("index", ("index",),
     "Would an index clause be an option for you instead of a fixed increase?"),
    ("approval", ("approval", "decision", "who decides"),
     "Who on your side approves this, and when can we expect an answer?"),
)

# Supplier concerns (from Signals) -> one acknowledging sentence for the template. No digits.
CONCERN_SENTENCES = {
    "final_offer_language": (
        "Thank you for your offer; we have looked at it carefully and would like to make one more proposal."
    ),
    "approval_pending": (
        "We understand this needs approval on your side, and we have tried to make the options easy to decide on."
    ),
    "capacity_issue": "We understand that capacity is tight at the moment and that planning security matters to you.",
    "cash_pressure": "We have taken your wishes on payment timing into account in our proposal.",
    "irritated": "We appreciate your patience and would like to find a fair solution together.",
    "rejected_args": "We understand that market figures are not the whole picture for your company.",
    "accepted_args": "Thank you for taking our figures into account.",
}

ASK_SENTENCES = {
    "faster_payment": "We have noted your wish for faster payment.",
    "volume": "We have noted that volume matters to you.",
    "longer_contract": "We have noted your interest in a longer-term agreement.",
    "forecast": "We have noted that planning security is important to you.",
    "earlier_effective_date": "We have noted your view on the effective date.",
    "index_clause": "We have noted your interest in an index clause.",
    "longer_lead_time": "We have noted your request on lead time.",
    "tooling_payment": "We have noted your point on tooling.",
    "incoterm": "We have noted your point on the delivery terms.",
}

DRIVER_PHRASES = {
    "energy": "energy costs",
    "labour": "wage costs",
    "raw_material": "raw material costs",
    "steel": "steel and scrap prices",
    "copper": "copper prices",
    "aluminium": "aluminium prices",
    "nickel": "alloy surcharges",
    "electronics": "electronic component prices",
    "polymers": "elastomer and polymer prices",
    "logistics": "logistics costs",
    "financing": "financing costs",
}

# --- Leaks ------------------------------------------------------------------------------------------

# A sentence of the model's prose matching one of these is dropped: never reveal urgency, budget, a
# missing alternative, our target or our C; never talk about the model or its instructions.
LEAK_RE = re.compile(
    r"\b(?:urgen\w*|asap|as soon as possible|immediately|time pressure|pressed for time|running out|"
    r"deadline|last chance|no alternatives?|no other (?:supplier|source|option|offer)s?|"
    r"only (?:supplier|source|option)|single source|depend(?:ent|ing)? on you|cannot do without|"
    r"budget\w*|target(?:ed)? price|our target|price target|maximum we|we can pay up to|"
    r"walk[- ]?away|fallback|total cost|our cost model|our calculation|our (?:internal )?model|"
    r"desperate|must (?:close|sign|conclude)|need (?:this|the) deal|line (?:stop|standstill)|"
    r"credit (?:index|rating|score)|equity ratio|your bank|liquidity problem|"
    r"financial (?:difficult|trouble|problem)\w*|"
    r"insolven\w*|as an ai|language model|placeholder|the instructions?|"
    r"nobody else|no one else|sole (?:supplier|source)|only one who|(?:cannot|can't|unable to) switch|"
    r"(?:price )?ceiling|stock (?:runs?|is running) out|run(?:s|ning)? out of|out of stock|our stock|"
    r"inventory is low|production (?:stop|standstill|halt)|stand ?still|we need (?:the|these) parts by)\b",
    re.I,
)
