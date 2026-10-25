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


def test_no_promise_to_confirm_at_once_with_several_bidders():
    from buyer.llm.writer import CONFIRM_RE, confirm_at_once

    assert confirm_at_once({"suppliers": ["sup:1"]})
    assert not confirm_at_once({"suppliers": ["sup:1", "sup:2"]})
    assert CONFIRM_RE.search("If you confirm Option A as it stands, we can confirm the order straight away.")


def test_what_we_know_about_the_supplier_stays_private():
    from buyer.llm.writer import REVEAL_RE

    assert REVEAL_RE.search("As we know that a decision on price sits above your desk, here is a note.")
    assert REVEAL_RE.search("We have heard that your bank is watching.")
    assert not REVEAL_RE.search("We understand that energy and wages weigh on your costs.")
    assert not REVEAL_RE.search("Since price changes of this size go through your pricing committee, here it is.")


def test_a_dropped_sentence_leaves_no_open_quote():
    from buyer.llm.writer import balance_quotes

    assert '"' not in balance_quotes('Forward this: "Hollerau offers Option A.')
    assert balance_quotes('a "b" c') == 'a "b" c'


def test_the_volume_is_stated_in_figures_when_asked_or_in_a_bundle():
    from buyer.llm.writer import volume_line

    class D:
        term_sheets = [{"unit_price": 5.2, "payment_days": 60}]

    bundle = {"type": "bundling", "fixed_terms": {"volume_per_year": 30000, "contract_months": 24}}
    plain = {"type": "price_increase", "fixed_terms": {"volume_per_year": 6110, "contract_months": 12}}
    assert volume_line(bundle, D(), None, []) == "Binding volume in every option: 30,000 units a year over 24 months."
    assert "6,110" in volume_line(plain, D(), None, [{"from": "sup", "body": "Which volume can you commit to?"}])
    assert volume_line(plain, D(), None, [{"from": "sup", "body": "Our price stands."}]) == ""


def test_a_complaint_about_late_payment_is_recognised():
    from buyer.llm.writer import complains_of_late_payment

    assert complains_of_late_payment([{"from": "sup", "body": "Since your payments are often late, we cannot."}])
    assert complains_of_late_payment([{"from": "sup", "body": "Several invoices are overdue."}])
    assert not complains_of_late_payment([{"from": "sup", "body": "Faster payment is welcome."}])
    assert not complains_of_late_payment([{"from": "buyer", "body": "We never pay late."}])


def test_the_strategy_reaches_the_prompt():
    p = prompt_for({**PROFILE, "supplier_id": "sup:70110"})
    assert "STRATEGY:" in p and "why:" in p
