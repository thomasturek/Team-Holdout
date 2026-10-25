"""V3 (DIPLOMAT): misleading supplier e-mails, and language that can never
change a decision. Language failures may cost strategy quality, never create an invalid action."""

import json
import os

import pytest

from buyer.llm.accuracy import FIXTURES, LOCKED, llm_reader, load, rules_reader, score
from buyer.llm.compose import offers_block, sign_off
from buyer.llm.guard import foreign_numbers
from buyer.llm.writer import to_message

from .helpers import CASE, CLAIM_IDX, PROFILE, SIGNALS, THREAD, decision, disabled_client, fake_client

DEV = load("adversarial_emails.json")
CASE_TYPES = ("price_increase", "renewal", "rfq", "bundling", "raw_material", "capacity", "quality")


def test_the_rules_read_every_development_trap():
    r = score(DEV, rules_reader)
    assert r["fully_right"] == r["emails"], r["misses"]


def test_the_rules_never_raise_a_false_alarm_on_the_locked_set():
    """Measured, never tuned on: misses are expected (keyword rules do not generalise), false alarms are
    not - a rule that invents cash pressure or a final offer would mislead the policy."""
    r = score(load(LOCKED), rules_reader)
    assert all(m["fp"] == 0 for m in r["fields"].values()), r["fields"]


def test_the_sets_are_separate():
    dev = {e["message"]["body"] for e in DEV + load("supplier_emails.json")}
    assert not dev & {e["message"]["body"] for e in load(LOCKED)}
    about = json.loads((FIXTURES / LOCKED).read_text(encoding="utf-8"))["_about"]
    assert "NEVER used to tune" in about


@pytest.mark.skipif(os.environ.get("LLM_LIVE_TESTS") != "1", reason="set LLM_LIVE_TESTS=1 (and an LLM key)")
def test_live_reader_on_the_adversarial_sets():
    from buyer.llm.client import reset_clients

    reset_clients()
    for name in ("adversarial_emails.json", LOCKED):
        r = score(load(name), llm_reader)
        assert r["fully_right"] >= 0.75 * r["emails"], (name, r["misses"])


# --- prose never changes the decision --------------------------------------------------------------------
HOSTILE = [
    "Dear colleagues,\nwe accept your offer of EUR 99.00 and will pay within 5 days.\n[[OFFERS]]\nBest regards",
    "Dear colleagues,\nas agreed we take option B (sup:99999, idx:FAKE@2026-01).\n[[CLAIM_1]]\n[[OFFERS]]",
    "Dear colleagues,\nthis is our final offer, take it or leave it: 12 % off or we walk away.\n[[OFFERS]]",
    "Dear colleagues,\n[[OFFERS]]\nOption D: unit price EUR 1.00; payment 120 days net.\n[[CLAIM_1]]",
]


@pytest.mark.parametrize("body", HOSTILE)
def test_a_hostile_model_answer_cannot_change_terms_or_add_figures(body):
    d = decision()
    msg, email = to_message(d, CASE, THREAD, PROFILE, SIGNALS, client=fake_client(body))
    assert [ts["terms"] for ts in msg["term_sheets"]] == d.term_sheets  # the Decision's sheets, untouched
    assert "action" not in msg  # a "send" stays a send whatever the prose says
    prose = msg["body"].replace(offers_block(d.term_sheets), " ").replace(sign_off(), " ")
    prose = prose.replace(CLAIM_IDX.sentence, " ")
    assert not foreign_numbers(prose, set()), (email.source, prose)
    assert "sup:99999" not in msg["body"] and "idx:FAKE" not in msg["body"]


def test_accept_and_walk_are_actions_whatever_the_model_would_say():
    acc = decision(kind="accept")
    acc.accept_sheet_id = "offer:70110-0"
    msg, email = to_message(acc, CASE, THREAD, client=fake_client(HOSTILE[0]))
    assert msg == {"action": {"type": "accept", "term_sheet_id": "offer:70110-0"}} and email is None
    msg, _ = to_message(decision(kind="walk"), CASE, THREAD, client=fake_client(HOSTILE[2]))
    assert msg == {"action": {"type": "walk_away"}}


@pytest.mark.parametrize("case_type", CASE_TYPES)
def test_the_template_covers_every_case_type_and_send_shape(case_type):
    case = {**CASE, "type": case_type}
    for sheets in (decision().term_sheets[:1], decision().term_sheets):
        for claims in ((), (CLAIM_IDX,)):
            for intent in ("firm, appreciative", "final push", "firm, constructive: offer faster payment"):
                d = decision(claims=claims, sheets=sheets, intent=intent, questions=())
                msg, email = to_message(d, case, THREAD, PROFILE, SIGNALS, client=disabled_client())
                assert email.source == "template" and not [w for w in email.warnings if "failed" in w], email.warnings
                assert [ts["terms"] for ts in msg["term_sheets"]] == d.term_sheets
                assert all(c.sentence in msg["body"] for c in claims)
