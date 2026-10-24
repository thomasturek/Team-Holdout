import re

from buyer.interfaces import Signals
from buyer.llm.compose import offer_line, offers_block, question_text, subject_for, term_phrase
from buyer.llm.template import concern_sentences, template_email
from buyer.llm.vocab import ASK_SENTENCES, CLOSING, CONCERN_SENTENCES, LEAK_RE, QUESTIONS, STYLE

from .helpers import CASE, CLAIM_IDX, CLAIM_SC, PROFILE, SIGNALS, THREAD, decision


def test_template_is_deterministic_and_complete():
    d = decision(claims=(CLAIM_IDX, CLAIM_SC))
    a = template_email(d, CASE, THREAD, PROFILE, SIGNALS)
    assert a == template_email(d, CASE, THREAD, PROFILE, SIGNALS)
    subject, body = a
    assert subject == "Re: Price adjustment from 01 November 2026"
    assert CLAIM_IDX.sentence in body and CLAIM_SC.sentence in body
    assert "Option A: unit price EUR 129.90; new price valid from 2027-04-01; payment 60 days net." in body
    assert "Could you send us a cost breakdown for this part?" in body
    assert body.startswith("Dear colleagues at Gießerei Brandlhuber GmbH & Co. KG,")
    assert CLOSING["family_foundry"] in body
    assert body.endswith("Best regards\nPurchasing\nHollerau Pumpenwerke GmbH")


def test_fixed_texts_have_no_digits_and_no_leaks():
    texts = list(CONCERN_SENTENCES.values()) + list(ASK_SENTENCES.values()) + list(CLOSING.values())
    texts += [q[2] for q in QUESTIONS] + list(STYLE.values())
    for t in texts:
        assert not re.search(r"\d", t.replace("8D", "")), t  # "8D" is the report's name, not a figure
        assert not LEAK_RE.search(t), t


def test_concerns_follow_signals():
    s = Signals(False, True, True, True, ["energy", "PPI-C241"], [], ["not our reality"], ["volume"], [], "irritated")
    out = concern_sentences(s, decision())
    assert len(out) == 3
    assert out[0] == CONCERN_SENTENCES["final_offer_language"] and out[1] == CONCERN_SENTENCES["irritated"]
    assert concern_sentences(None) == []
    only_series = Signals(False, False, False, False, ["PPI-C241"], [], [], [], [], "neutral")
    assert concern_sentences(only_series) == ["We have read your remarks on the cost indices carefully."]
    # cash: only when an option actually carries payment terms
    cash = Signals(True, False, False, False, [], [], [], [], [], "neutral")
    assert concern_sentences(cash, decision()) == [CONCERN_SENTENCES["cash_pressure"]]
    assert concern_sentences(cash, decision(sheets=[{"unit_price": 5.0}])) == []


def test_first_reply_vs_later():
    d = decision()
    first = template_email(d, CASE, THREAD, PROFILE, None)[1]
    later = template_email(d, CASE, THREAD + [{"from": "buyer", "body": "x"}, {"from": "sales@70110", "subject": "Re: x", "body": "y"}], PROFILE, None)[1]  # noqa: E501
    assert "Thank you for your quote." in first and "Thank you for your reply." in later


def test_final_intent_adds_best_proposal_line():
    body = template_email(decision(intent="closing move, final"), CASE, THREAD, PROFILE, None)[1]
    assert "This is our best proposal at this stage." in body


def test_term_phrases():
    assert term_phrase("unit_price", 1234.5) == "unit price EUR 1,234.50"
    assert term_phrase("contract_months", 0) == "single order"
    assert term_phrase("contract_months", 24) == "contract term 24 months"
    assert term_phrase("volume_per_year", 4000) == "binding volume 4,000 units per year"
    assert term_phrase("index_clause", None) == "no index clause"
    clause = {"series": "PPI-C241", "material_share": 0.35, "deadband_pct": 3, "base_month": "2026-09"}
    assert term_phrase("index_clause", clause) == "index clause on PPI-C241 (35 % material share, deadband 3 %, base 2026-09)"  # noqa: E501
    assert term_phrase("chargeback_eur_per_complaint", 150) == "chargeback EUR 150.00 per complaint"
    assert offer_line({"unit_price": 10, "incoterm": "DAP"}) == "unit price EUR 10.00; Incoterm DAP."
    assert offers_block([]) == ""
    assert offers_block([{"terms": {"unit_price": 10}}]) == "Our proposal: unit price EUR 10.00."


def test_questions_and_subject():
    assert question_text("earliest lead time") == "What is the earliest lead time you can commit to?"
    assert question_text("8D report") == "Could you send us your 8D report and a binding improvement plan?"
    assert question_text("Do you plan a second shift?") == "Do you plan a second shift?"
    assert question_text("warranty terms") == "Could you also tell us about the following: Warranty terms?"
    assert subject_for(CASE, [{"from": "sales@1", "subject": "RE: AW: Re: Offer"}]) == "Re: Offer"
    assert subject_for(CASE, []) == "Re: HN volute casings: a price increase"
