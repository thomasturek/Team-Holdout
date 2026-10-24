"""Shared test inputs: a case, a profile, claims, Decisions and a fake LLM. No network, no keys."""

import json
from pathlib import Path

from buyer.interfaces import Claim, Decision, Signals
from buyer.llm.client import LLMClient, Settings

FIXTURES = Path(__file__).parent / "fixtures"

CASE = {
    "case_id": "case:P01",
    "type": "price_increase",
    "title": "HN volute casings: a price increase",
    "negotiable": ["unit_price", "effective_date", "payment_days"],
    "buyer": {"need_per_year": 4000, "current_unit_price": 126.53},
}

PROFILE = {
    "supplier_id": "sup:70110",
    "name": "Gießerei Brandlhuber GmbH & Co. KG",
    "country": "DE",
    "archetype": "family_foundry",
    "notes": [
        "doc:20260210-70110-M1: owner works from his own spreadsheet, last updated two years ago",
        "news:20260302-01 (sup:70110) energy contract renewed",
    ],
}

CLAIM_IDX = Claim(
    key="index:PPI-D351",
    sentence="Electricity producer prices changed -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).",  # noqa: E501
    refs=["idx:PPI-D351@2025-08", "idx:PPI-D351@2026-08"],
    expected="verified",
    strength=0.6,
)
CLAIM_SC = Claim(
    key="scorecard:70110",
    sentence="Your rolling on-time delivery was 81.1% in 2026Q3 (sc:70110@2026Q3).",
    refs=["sc:70110@2026Q3"],
    expected="verified",
    strength=0.4,
)
CLAIM_PO = Claim(
    key="po_history:310010",
    sentence="We paid EUR 126.53 on our last two orders (po:4500010001-10, po:4500010002-10).",
    refs=["po:4500010001-10", "po:4500010002-10"],
    expected="verified",
    strength=0.3,
)

SHEETS = [
    {"unit_price": 129.9, "effective_date": "2027-04-01", "payment_days": 60},
    {"unit_price": 128.5, "effective_date": "2027-04-01", "payment_days": 14},
]

THREAD = [
    {
        "from": "sales@70110",
        "subject": "Price adjustment from 01 November 2026",
        "status": "open",
        "body": "Dear Sir or Madam, please find our quote attached. Josef Brandlhuber",
        "term_sheets": [{"term_sheet_id": "offer:70110-0", "terms": {"unit_price": 138.55}}],
    }
]

SIGNALS = Signals(True, False, False, False, ["energy", "labour"], [], [], ["faster_payment"], [], "neutral")


def decision(claims=(CLAIM_IDX,), sheets=SHEETS, questions=("cost breakdown",), intent="firm, appreciative", kind="send"):  # noqa: E501
    return Decision(kind, "sup:70110", [dict(s) for s in sheets], None, list(claims), list(questions), intent)


def fake_client(answer, settings=None):
    """An LLMClient whose model answers `answer` (a string, or a callable(system, user) -> str or raise)."""

    def fn(system, user, max_tokens, timeout_s):
        return answer(system, user) if callable(answer) else answer

    return LLMClient(settings or Settings("anthropic", "test-model", "low", None, "key", False), complete_fn=fn)


def disabled_client():
    return LLMClient(Settings("anthropic", None, None, None, None, True))


GOOD_LLM_BODY = """Dear colleagues at Gießerei Brandlhuber,

thank you for your quote and for the many years of reliable supply.
We understand that energy and wages weigh on your costs.

Our data shows a different picture:
[[CLAIM_1]]

[[OFFERS]]

The second option pays you much faster, which may help with your cash flow.

[[QUESTIONS]]

We value our long cooperation and are confident we will find a fair solution together.

Best regards
Purchasing
Hollerau Pumpenwerke GmbH"""


def load_fixtures():
    return json.loads((FIXTURES / "supplier_emails.json").read_text(encoding="utf-8"))["emails"]
