import random
import re

import pytest

from buyer.llm.compose import offers_block, questions_block, sign_off
from buyer.llm.guard import ID_RE, RESIDUE_RE, allowed_tokens, foreign_numbers, leaks, verify_email
from buyer.llm.writer import to_message, write

from .helpers import (
    CASE,
    CLAIM_IDX,
    CLAIM_PO,
    CLAIM_SC,
    GOOD_LLM_BODY,
    PROFILE,
    SIGNALS,
    THREAD,
    decision,
    disabled_client,
    fake_client,
)


def check_dod(email, d, profile=PROFILE):
    """The Definition of Done for one e-mail: every claim verbatim, no foreign number."""
    lines = [ln.strip() for ln in email.body.split("\n")]
    for c in d.claims[:3]:
        assert c.sentence.strip() in lines  # verbatim, on a line of its own
    rest = email.body
    blocks = [c.sentence for c in d.claims[:3]] + [offers_block(d.term_sheets), questions_block(d.questions), sign_off()]  # noqa: E501
    for b in sorted((b for b in blocks if b), key=len, reverse=True):
        rest = rest.replace(b, " ")
    assert not foreign_numbers(rest, allowed_tokens(d, CASE, profile)), rest
    assert not RESIDUE_RE.search(rest) and len(email.body) <= 8000


def test_good_llm_output():
    d = decision()
    e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(GOOD_LLM_BODY))
    assert e.source == "llm", e.warnings
    check_dod(e, d)
    assert e.refs == CLAIM_IDX.refs
    assert e.subject == "Re: Price adjustment from 01 November 2026"
    assert "Option A: unit price EUR 129.90" in e.body and "Option B: unit price EUR 128.50" in e.body
    assert "Could you send us a cost breakdown for this part?" in e.body
    assert e.body.endswith(sign_off()) and e.body.count("Best regards") == 1


def test_foreign_numbers_and_leaks_are_dropped():
    body = GOOD_LLM_BODY.replace(
        "We understand that energy and wages weigh on your costs.",
        "We understand that energy and wages weigh on your costs. Our target is EUR 120.00. "
        "We need this urgently as the line stops otherwise. We have no other supplier for this part. "
        "Since your letter of 11 September we have thought hard.",
    )
    d = decision()
    e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    assert e.source == "llm"
    check_dod(e, d)
    for gone in ("target", "urgently", "no other supplier", "11 September"):
        assert gone not in e.body
    assert "energy and wages" in e.body


def test_alternatives_only_when_the_intent_says_so():
    body = GOOD_LLM_BODY.replace("[[OFFERS]]", "We have other offers on the table.\n[[OFFERS]]")
    plain = write(decision(intent="firm"), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    signal = write(decision(intent="firm, signal alternatives"), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))  # noqa: E501
    assert "other offers" not in plain.body and "other offers" in signal.body


def test_unknown_ids_removed_known_kept():
    body = GOOD_LLM_BODY.replace("[[OFFERS]]", "See also doc:NOPE-1 and sc:70110@2026Q2 for context.\n\n[[OFFERS]]")
    d = decision()
    e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body), known_id=lambda i: i == "sc:70110@2026Q2")
    assert "doc:NOPE-1" not in e.body and "sc:70110@2026Q2" in e.body
    # without known_id only the Decision's claim IDs count as known
    e2 = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    assert "sc:70110@2026Q2" not in e2.body
    assert set(ID_RE.findall(e2.body)) <= set(CLAIM_IDX.refs)


def test_missing_placeholders_are_injected():
    body = "Dear colleagues,\n\nthank you for your quote. We would like to find a fair solution with you.\n\nWe look forward to your reply."  # noqa: E501
    d = decision(claims=(CLAIM_IDX, CLAIM_SC))
    e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    assert e.source == "llm"
    check_dod(e, d)
    assert any("injected" in w for w in e.warnings)
    # order: claims before the offers, the offers and the questions before the closing line
    assert e.body.index(CLAIM_SC.sentence) < e.body.index("Option A") < e.body.index("cost breakdown") < e.body.index("We look forward")  # noqa: E501


def test_copied_claim_and_repeated_placeholder():
    body = GOOD_LLM_BODY.replace("[[CLAIM_1]]", CLAIM_IDX.sentence + "\n[[CLAIM_1]]\n[[CLAIM_1]]\n[[CLAIM_7]]")
    d = decision()
    e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    check_dod(e, d)
    assert e.body.count(CLAIM_IDX.sentence) == 1


def test_placeholder_variants_are_understood():
    body = GOOD_LLM_BODY.replace("[[CLAIM_1]]", "[[ claim_1 ]]").replace("[[OFFERS]]", "[[offers]]")
    d = decision()
    e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    check_dod(e, d)
    assert e.body.count("Option A") == 1


def test_invented_name_in_greeting_is_replaced():
    d = decision()
    e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(GOOD_LLM_BODY.replace(
        "Dear colleagues at Gießerei Brandlhuber,", "Dear Mr Huber,")))  # fmt: skip
    assert "Huber," not in e.body.splitlines()[0] and e.body.startswith("Dear colleagues at Gießerei Brandlhuber GmbH")
    # a name the supplier used itself is fine
    e2 = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(GOOD_LLM_BODY.replace(
        "Dear colleagues at Gießerei Brandlhuber,", "Dear Mr Brandlhuber, dear Josef,")))  # fmt: skip
    assert e2.body.startswith("Dear Mr Brandlhuber, dear Josef,")


def test_model_sign_off_replaced_by_ours():
    body = GOOD_LLM_BODY.replace("Best regards\nPurchasing\nHollerau Pumpenwerke GmbH", "Kind regards,\nAnna Weber\nBuyer")  # noqa: E501
    e = write(decision(), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    assert "Anna Weber" not in e.body and e.body.endswith(sign_off())


def test_fallbacks_to_template():
    d = decision(claims=(CLAIM_IDX, CLAIM_SC, CLAIM_PO))

    def broken(system, user):
        raise RuntimeError("API down")

    for c in (disabled_client(), fake_client(broken), fake_client("[[CLAIM_1]]"), fake_client("word " * 400)):
        e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=c)
        assert e.source == "template", e.warnings
        check_dod(e, d)
        assert e.refs == CLAIM_IDX.refs + CLAIM_SC.refs + CLAIM_PO.refs


def test_more_than_three_claims_are_cut():
    extra = type(CLAIM_PO)("x:y", "A fourth argument (cost:310010).", ["cost:310010"], "verified", 0.1)
    d = decision(claims=(CLAIM_IDX, CLAIM_SC, CLAIM_PO, extra))
    e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=disabled_client())
    assert extra.sentence not in e.body and "cost:310010" not in e.refs and e.warnings


def test_prompt_hides_private_data():
    seen = {}

    def capture(system, user):
        seen["user"] = user
        return GOOD_LLM_BODY

    case = {**CASE, "briefing": "SECRET we have no alternative", "buyer": {"fallback_unit_price": 999.99}}
    write(decision(), case, THREAD, PROFILE, SIGNALS, client=fake_client(capture))
    u = seen["user"]
    assert "SECRET" not in u and "999.99" not in u and "fallback" not in u
    assert "doc:20260210" not in u and "news:" not in u and "sup:70110" not in u  # notes without IDs
    assert "owner works from his own spreadsheet" in u and "[[CLAIM_1]] = " in u


def test_to_message_shapes():
    d = decision()
    msg, email = to_message(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(GOOD_LLM_BODY))
    assert set(msg) == {"subject", "body", "term_sheets", "refs"}
    assert msg["term_sheets"] == [{"terms": t} for t in d.term_sheets] and email.body == msg["body"]
    acc = decision(kind="accept", sheets=())
    acc.accept_sheet_id = "offer:70110-3"
    assert to_message(acc, CASE) == ({"action": {"type": "accept", "term_sheet_id": "offer:70110-3"}}, None)
    assert to_message(decision(kind="walk", sheets=()), CASE) == ({"action": {"type": "walk_away"}}, None)
    with pytest.raises(ValueError):
        to_message(decision(kind="accept", sheets=()), CASE)
    with pytest.raises(ValueError):
        write(decision(kind="walk"), CASE)


def test_dict_inputs_work_too():
    d = {"kind": "send", "supplier_id": "sup:70110", "term_sheets": [{"terms": {"unit_price": 10.0, "payment_days": 30}}],  # noqa: E501
         "accept_sheet_id": None, "claims": [{"key": "k", "sentence": CLAIM_SC.sentence, "refs": CLAIM_SC.refs}],
         "questions": [], "intent": ""}  # fmt: skip
    msg, email = to_message(d, CASE, THREAD, None, None, client=disabled_client())
    assert CLAIM_SC.sentence in msg["body"] and msg["term_sheets"] == [{"terms": {"unit_price": 10.0, "payment_days": 30}}]  # noqa: E501
    assert msg["body"].startswith("Dear Sir or Madam,")


# --- the Definition of Done under adversarial model output ---------------------------------------------
NOISE = [
    "We can pay EUR 99.99 if you agree today.",
    "Our budget is limited this year.",
    "As discussed on 12 March, we expect a reply.",
    "Please see idx:PPI-C241@2026-08 and quote:7100002 for details.",
    "We could order 5,000 units next year.",
    "Your price is 7 % above the market.",
    "Thank you for the constructive discussion.",
    "[[CLAIM_9]] [[OFFERS]] [[QUESTIONS]]",
    "We have alternatives.",
    "Kind regards, Max",
]


def test_dod_holds_for_random_decisions_and_noisy_models():
    rnd = random.Random(7)
    claims_pool = [CLAIM_IDX, CLAIM_SC, CLAIM_PO]
    for _ in range(300):
        claims = rnd.sample(claims_pool, rnd.randint(0, 3))
        sheets = [{"unit_price": round(rnd.uniform(1, 500), rnd.choice([0, 1, 2])),
                   "payment_days": rnd.choice([14, 30, 45, 60, 90]),
                   "contract_months": rnd.choice([0, 12, 24]),
                   "index_clause": rnd.choice([None, {"series": "PPI-C241", "material_share": 0.35, "deadband_pct": 3, "base_month": "2026-09"}])}  # noqa: E501
                  for _ in range(rnd.randint(0, 3))]  # fmt: skip
        d = decision(claims=claims, sheets=sheets, questions=rnd.sample(["cost breakdown", "lead time", "8D report", "variants"], rnd.randint(0, 2)))  # noqa: E501
        lines = GOOD_LLM_BODY.split("\n")
        for _ in range(rnd.randint(0, 4)):
            lines.insert(rnd.randint(1, len(lines) - 1), rnd.choice(NOISE))
        if rnd.random() < 0.3:
            lines = [ln for ln in lines if "[[" not in ln]
        e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client("\n".join(lines)))
        check_dod(e, d)
        assert not verify_email(e.body, d.claims, [c.sentence for c in d.claims] + [offers_block(d.term_sheets),
                                questions_block(d.questions), sign_off()], allowed_tokens(d, CASE, PROFILE))  # fmt: skip  # noqa: E501
        assert not re.search(r"budget|today|alternatives", e.body.replace(sign_off(), ""), re.I) or e.source == "template"  # noqa: E501


# --- regressions from the independent review ------------------------------------------------------------
def body_with(replacement_for_claim_line):
    return GOOD_LLM_BODY.replace("[[CLAIM_1]]", replacement_for_claim_line)


def test_reworded_claim_with_its_ids_is_dropped():
    reworded = ("Electricity producer prices rose 3.7% from 2025-08 to 2026-08 "
                "(idx:PPI-D351@2025-08, idx:PPI-D351@2026-08), so we see less room.\n[[CLAIM_1]]")
    e = write(decision(), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body_with(reworded)))
    check_dod(e, decision())
    assert "rose 3.7%" not in e.body and e.body.count("idx:PPI-D351@2025-08") == 1


def test_nothing_glued_to_a_claim():
    for glued in ("We do not believe that [[CLAIM_1]]", "1[[CLAIM_1]]",
                  "Contrary to idx:PPI-C241@2026-08 and sc:70110@2026Q3, [[CLAIM_1]]"):
        e = write(decision(), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body_with(glued)), known_id=lambda i: True)  # noqa: E501
        check_dod(e, decision())
        assert "do not believe" not in e.body and "1Electricity" not in e.body and "Contrary" not in e.body, e.body


def test_figures_in_any_form_are_dropped():
    for figure in ("That is 8% too much.", "EUR 2,027 would be fair.", "We plan 60.000 units.", "About 14k pieces.",
                   "We expect ten percent less.", "One hundred twenty euros is our view.", "We think eur:118.50 fits."):
        e = write(decision(), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body_with(figure + "\n[[CLAIM_1]]")))
        check_dod(e, decision())
        assert figure not in e.body, figure


def test_sloppy_placeholders_are_filled():
    body = (GOOD_LLM_BODY.replace("[[CLAIM_1]]", "[CLAIM_1]").replace("[[OFFERS]]", "{{OFFERS}}")
            .replace("[[QUESTIONS]]", "[[question]]"))
    e = write(decision(), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    assert e.source == "llm", e.warnings
    check_dod(e, decision())
    assert e.body.count("Option A") == 1 and e.body.count("cost breakdown") == 1


def test_model_sign_off_inside_a_paragraph_is_cut():
    body = GOOD_LLM_BODY.split("Best regards")[0].rstrip() + "\nBest regards\nMaria Huber, Head of Purchasing"
    e = write(decision(), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    assert "Maria" not in e.body and e.body.endswith(sign_off()) and e.body.count("regards") == 1


def test_claims_go_out_in_decision_order():
    body = GOOD_LLM_BODY.replace("[[CLAIM_1]]", "[[CLAIM_2]]\n[[CLAIM_1]]")
    d = decision(claims=(CLAIM_IDX, CLAIM_SC))
    e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    check_dod(e, d)
    assert e.body.index(CLAIM_IDX.sentence) < e.body.index(CLAIM_SC.sentence)
    assert e.refs == CLAIM_IDX.refs + CLAIM_SC.refs


def test_invented_person_in_prose_is_dropped():
    body = body_with("I spoke with Mr Huber about this last week.\n[[CLAIM_1]]")
    e = write(decision(), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    assert "Huber about" not in e.body
    ok = body_with("As Mr Brandlhuber wrote, we take this seriously.\n[[CLAIM_1]]")
    assert "Mr Brandlhuber wrote" in write(decision(), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(ok)).body


def test_odd_inputs_never_crash():
    odd_sheets = [{"unit_price": 10.0, "payment_days": None, "index_clause": "PPI-C241"}, {"terms": {"unit_price": 9.0}, "x": 1}]  # noqa: E501
    claims = [type(CLAIM_IDX)("k", None, ["idx:A"], "verified", 0.1), CLAIM_SC]
    d = decision(claims=claims, sheets=odd_sheets, questions=(None, 7))
    for client in (fake_client(GOOD_LLM_BODY), disabled_client()):
        msg, e = to_message(d, CASE, [{"from": "sales@1", "body": None, "subject": None}], None, None, client=client)
        assert CLAIM_SC.sentence in msg["body"] and "idx:A" not in msg["refs"]
        assert msg["term_sheets"][1] == {"terms": {"unit_price": 9.0}}


def test_trailing_whitespace_in_a_claim_still_counts_as_verbatim():
    c = type(CLAIM_SC)(CLAIM_SC.key, CLAIM_SC.sentence + "  ", CLAIM_SC.refs, "verified", 0.4)
    e = write(decision(claims=(c,)), CASE, THREAD, PROFILE, SIGNALS, client=fake_client(GOOD_LLM_BODY))
    assert e.source == "llm", e.warnings
    assert CLAIM_SC.sentence in e.body.split("\n")


# --- regressions from the second review ------------------------------------------------------------------
def sent(body, intent="firm, appreciative", **kw):
    d = decision(intent=intent)
    e = write(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body), **kw)
    check_dod(e, d)
    return e


def test_whitespace_tricks_do_not_hide_leaks():
    for trick in ("We have no  alternative here.", "We need this as soon as possible.", "There is time\tpressure.",
                  "We depend\non you.", "There is no other\nsource for us."):
        e = sent(body_with(trick + "\n[[CLAIM_1]]"), intent="signal alternatives, firm")
        flat = " ".join(e.body.split())
        assert not leaks(flat.replace(sign_off().replace("\n", " "), "")), (trick, e.body)


def test_more_leaks_and_rival_talk_are_dropped():
    for text in ("Nobody else can make this casting for us.", "You are our sole supplier and we cannot switch.",
                 "Our price ceiling for this part is reached.", "We have a cheaper quote from another foundry.",
                 "Other vendors have offered us better terms.", "We are comparing other quotations."):
        e = sent(body_with(text + "\n[[CLAIM_1]]"))
        assert text not in e.body, text


def test_more_invented_names_are_dropped():
    for text in ("Please give our regards to Dr. Huber.", "As agreed with Mr. Weber, we write again.",
                 "Our colleague Thomas Weber will call you."):
        e = sent(body_with(text + "\n[[CLAIM_1]]"))
        assert "Huber." not in e.body and "Weber" not in e.body, text


def test_informal_sign_offs_are_cut():
    for closing in ("Thanks,\nMaria Schneider\nHead of Purchasing", "Best,\nAnna Weber\nSenior Buyer"):
        body = GOOD_LLM_BODY.split("Best regards")[0].rstrip() + "\n\n" + closing
        e = sent(body)
        assert "Maria" not in e.body and "Anna" not in e.body and e.body.endswith(sign_off())


def test_odd_greetings_with_invented_names_are_replaced():
    for first in ("Hallo Anna,", "**Dear Anna,**", "﻿Dear Anna,", "Re: your offer\nDear Anna,"):
        e = sent(GOOD_LLM_BODY.replace("Dear colleagues at Gießerei Brandlhuber,", first))
        assert "Anna" not in e.body and e.body.startswith("Dear colleagues at Gießerei Brandlhuber GmbH & Co. KG,"), e.body  # noqa: E501


def test_exotic_placeholders_never_reach_the_supplier():
    for ph in ("<<claim>>", "⟦claim⟧", "{% claim %}", "(claim one)", "<insert claim here>",
               "［［offers］］", "<<offers>>", "<<claim_1>>"):
        sent(GOOD_LLM_BODY.replace("[[CLAIM_1]]", ph))  # check_dod: no residue, claims verbatim


def test_exotic_figures_are_dropped():
    for text in ("A price of EUR one hundred twenty would be fine.", "That is ten dollars too much.",
                 "Wir bitten um zehn Prozent Nachlass.", "Prices rose ⁵% this year.", "We need forty-eight hours."):
        assert text not in sent(body_with(text + "\n[[CLAIM_1]]")).body, text


def test_bad_caller_input_never_raises():
    long_claim = type(CLAIM_SC)("long", "Long argument " + "x" * 3000 + " (sc:70110@2026Q3).", ["sc:70110@2026Q3"], "verified", 0.1)  # noqa: E501
    odd_refs = type(CLAIM_SC)("odd", CLAIM_SC.sentence, "sc:70110@2026Q3", "verified", 0.1)
    for case, thread, claims in (({"title": 12345}, ["not a dict", None], [CLAIM_IDX]),
                                 (CASE, THREAD, [odd_refs]),
                                 (CASE, THREAD, [long_claim, long_claim, long_claim])):
        for client in (fake_client(GOOD_LLM_BODY), disabled_client()):
            msg, e = to_message(decision(claims=claims), case, thread, PROFILE, SIGNALS, client=client)
            assert len(msg["body"]) <= 8000 and msg["subject"]
    assert to_message(decision(claims=[odd_refs]), CASE, THREAD, client=disabled_client())[0]["refs"] == ["sc:70110@2026Q3"]  # noqa: E501
