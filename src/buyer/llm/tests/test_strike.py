"""The round-1 strike: the writer gets the supplier dossier and knows its first e-mail decides the deal;
a form letter and a summary of "what our data shows" never reach the supplier."""

from buyer.llm.compose import offers_block, questions_block
from buyer.llm.writer import build_prompt, write

from .helpers import CASE, CLAIM_IDX, PROFILE, SIGNALS, THREAD, decision, fake_client

DOSSIER = ("We deal with its owner, who decides alone. It cares about being repaid for its loyalty. "
           "Angle: Owner to owner: loyalty and reciprocity.")
CLAUSE = {"series": "CU-NOTATION", "material_share": 0.2, "deadband_pct": 5, "base_month": "2026-08"}


def prompt_for(profile=PROFILE, thread=THREAD, sheets=None):
    d = decision(sheets=sheets) if sheets else decision()
    return build_prompt(d, CASE, thread, profile, SIGNALS, [CLAIM_IDX], offers_block(d.term_sheets),
                        questions_block(d.questions))


def test_the_dossier_reaches_the_prompt():
    p = prompt_for({**PROFILE, "dossier": DOSSIER})
    assert "DOSSIER" in p and "repaid for its loyalty" in p and "never quote it" in p


def test_first_message_is_marked_as_decisive():
    supplier_only = [m for m in THREAD if m.get("from") != "buyer"]
    assert "MESSAGE: first" in prompt_for(thread=supplier_only)
    assert "MESSAGE: reply" in prompt_for(thread=[*supplier_only, {"from": "buyer", "body": "Dear ..."}])


def test_clause_in_the_options_is_flagged():
    plain = [{"unit_price": 129.9, "payment_days": 60}]
    with_clause = [{"unit_price": 129.9, "payment_days": 60, "index_clause": CLAUSE}]
    assert "CLAUSE IN OPTIONS: no" in prompt_for(sheets=plain)
    assert "CLAUSE IN OPTIONS: yes" in prompt_for(sheets=with_clause)


FORM_LETTER = """Dear colleagues at Gießerei Brandlhuber,

Thank you for your revised offer. We value our long-standing partnership.
You told us the owner kept supplying at the old price in a hard year, and we have not forgotten it.

Our data shows a more balanced picture:
[[CLAIM_1]]

The market is calm for castings.
[[OFFERS]]

Option A is the package we can approve: it reflects the cost picture above and keeps both family firms healthy.
If you confirm Option A as it stands, we can confirm the order straight away.

[[QUESTIONS]]

Best regards"""


def test_form_phrases_and_unbacked_evidence_are_dropped():
    e = write(decision(), CASE, THREAD, {**PROFILE, "dossier": DOSSIER}, SIGNALS, client=fake_client(FORM_LETTER))
    assert e.source == "llm", e.warnings
    for gone in ("Thank you for your revised offer", "value our long-standing partnership", "Our data shows",
                 "The market is calm"):
        assert gone not in e.body, gone
    for kept in ("Option A is the package we can approve", "confirm the order straight away",
                 "kept supplying at the old price"):
        assert kept in e.body, kept
    assert CLAIM_IDX.sentence in e.body  # the claim itself stays, verbatim, on its own line


def test_the_template_is_not_touched_by_the_style_rules():
    e = write(decision(), CASE, THREAD, PROFILE, SIGNALS, client=fake_client("not an e-mail"))
    assert e.source == "template" and e.body  # the fallback still goes out
