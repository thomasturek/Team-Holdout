import dataclasses
import json
import os

import pytest

from buyer.interfaces import Signals
from buyer.llm.client import get_client, reset_clients
from buyer.llm.reader import build_prompt, coerce, normalise_ask, normalise_driver, parse_json, read, rule_signals
from buyer.llm.vocab import ASKS, DRIVERS, TONES

from .helpers import CLAIM_IDX, disabled_client, fake_client, load_fixtures

EMAILS = load_fixtures()


def mismatches(signals: Signals, case) -> list[str]:
    s = dataclasses.asdict(signals)
    errs = []
    for k, v in case["expected"].items():
        if isinstance(v, list):
            if [x for x in v if x not in s[k]] or (v == [] and s[k]):
                errs.append(f"{k}: want {v}, got {s[k]}")
        elif s[k] != v:
            errs.append(f"{k}: want {v}, got {s[k]}")
    for k, v in case.get("absent", {}).items():
        if any(x in s[k] for x in v):
            errs.append(f"{k}: must not hold {v}, got {s[k]}")
    return errs


def valid(signals: Signals):
    assert all(isinstance(getattr(signals, f), bool) for f in ("cash_pressure", "capacity_issue", "final_offer_language", "approval_pending"))  # noqa: E501
    assert signals.tone in TONES
    assert all(a in ASKS or a.startswith("other") for a in signals.asks)
    assert all(d in DRIVERS or "-" in d for d in signals.cost_drivers_claimed)


@pytest.mark.parametrize("case", EMAILS, ids=[e["id"] for e in EMAILS])
def test_keyword_rules_on_fixtures(case):
    s = rule_signals(case["message"], {"claims": case["last_claims"]})
    valid(s)
    assert not mismatches(s, case)


def test_twenty_fixtures():
    assert len(EMAILS) >= 20


def test_llm_answer_is_validated_and_normalised():
    answer = json.dumps({
        "cash_pressure": "yes", "capacity_issue": False, "final_offer_language": False, "approval_pending": 0,
        "cost_drivers_claimed": ["Energy", "LCI-C", "wages", "unknown thing"],
        "accepted_args": ["INDEX:PPI-D351"], "rejected_args": [],
        "asks": ["faster payment", "volume", "a visit to our plant"], "offered_variants": [], "tone": "Warm"})  # fmt: skip  # noqa: E501
    msg = {"from": "sales@1", "status": "final_offer", "body": "Some text.", "claim_results": []}
    r = read(msg, last_decision={"claims": [CLAIM_IDX]}, client=fake_client("```json\n" + answer + "\n```"))
    assert r.source == "llm" and r.error is None
    s = r.signals
    valid(s)
    assert s.cash_pressure is True and s.approval_pending is False
    assert s.final_offer_language is True  # the status says final_offer
    assert s.cost_drivers_claimed == ["energy", "LCI-C", "labour"]
    assert s.accepted_args == ["index:PPI-D351"]
    assert s.asks == ["faster_payment", "volume", "other: a visit to our plant"]
    assert s.tone == "warm"


def test_partial_or_invalid_answers_fall_back_to_rules():
    msg = EMAILS[2]["message"]  # final offer with a threat
    partial = read(msg, client=fake_client('{"tone": "neutral", "cash_pressure": "maybe"}'))
    assert partial.source == "llm+rules" and "cash_pressure" in partial.from_rules
    assert partial.signals.tone == "neutral" and partial.signals.final_offer_language is True
    for bad in ("not json at all", "[1, 2]", '{"unrelated": 1}'):
        r = read(msg, client=fake_client(bad))
        assert r.source == "rules" and r.error, bad
        assert r.signals == rule_signals(msg)

    def down(system, user):
        raise RuntimeError("down")

    assert read(msg, client=fake_client(down)).source == "rules"
    assert read(msg, client=disabled_client()).source == "rules"
    assert read(msg, use_llm=False, client=fake_client("{}")).error is None


def test_normalisers():
    assert normalise_ask("faster_payment") == "faster_payment" and normalise_ask("Longer contract") == "longer_contract"
    assert normalise_ask("other: on-site visit") == "other: on-site visit"
    assert normalise_driver("PPI-C2451") == "PPI-C2451" and normalise_driver("electricity costs") == "energy"
    assert normalise_driver("weather") is None and normalise_driver("NEW-SERIES1") == "NEW-SERIES1"
    assert coerce({"tone": "furious", "asks": "volume"}) == {"asks": ["volume"]}
    assert parse_json('Sure! {"a": {"b": 1}} trailing') == {"a": {"b": 1}}


def test_prompt_contains_claims_and_status():
    msg = {**EMAILS[0]["message"], "attachments": [{"name": "quote.pdf", "text": "Offered terms ..."}]}
    p = build_prompt(msg, {"claims": [CLAIM_IDX]})
    assert "STATUS: open" in p and "index:PPI-D351:" in p and "[quote.pdf]" in p and "Faster payment helps" in p


@pytest.mark.skipif(os.environ.get("LLM_LIVE_TESTS") != "1", reason="set LLM_LIVE_TESTS=1 (and an LLM key) to call the model")  # noqa: E501
def test_live_model_on_fixtures():
    """The real reader model on the 20 fixtures: at least 80 % of them fully right, each < 10 s."""
    reset_clients()
    client = get_client("reader")
    assert client.enabled, "LLM not configured"
    good, report = 0, []
    for case in EMAILS:
        r = read(case["message"], last_decision={"claims": case["last_claims"]}, client=client)
        errs = mismatches(r.signals, case)
        good += not errs
        report.append(f"{case['id']}: {r.source} {r.latency_s:.1f}s {errs}")
        assert r.latency_s < 10.5
    print("\n".join(report))
    assert good >= 0.8 * len(EMAILS), "\n".join(report)


# --- regressions from the independent review ------------------------------------------------------------
def rules(body, status="open", claims=(), results=None):
    return rule_signals({"body": body, "status": status, "claim_results": results or []}, {"claims": list(claims)})


def test_signature_and_footer_are_no_signals():
    s = rules("Thank you for your order.\nGeschäftsführer: Max Muster\nBank: Sparkasse Passau\nIBAN DE12 3456")
    assert not s.approval_pending and not s.cash_pressure


def test_polite_phrases_are_not_misread():
    assert rules("Thank you once again for your order.").tone != "irritated"
    assert not rules("We will get back to you shortly.").approval_pending
    assert not rules("Thank you for your last offer.").final_offer_language
    assert not rules("This is not our final offer.").final_offer_language
    assert rules("This is our final offer.").final_offer_language


def test_negations():
    assert not rules("There is no capacity bottleneck and no shortage on our side.").capacity_issue
    assert "volume" not in rules("Higher volume would not change our price.").asks
    assert not rules("We have no cash flow problems.").cash_pressure
    assert rules("We are fully booked and cannot take more orders.").capacity_issue


def test_stated_terms_are_not_asks():
    assert "incoterm" not in rules("Our prices are ex works, delivery terms unchanged.").asks
    assert "longer_contract" not in rules("In the longer term we see stable prices.").asks
    assert "earlier_effective_date" not in rules("Please reply not later than Friday.").asks
    assert "incoterm" in rules("We can deliver ex works only.").asks


def test_material_words_are_drivers_only_when_costs_are_blamed():
    assert rules("The housing is made of stainless steel.").cost_drivers_claimed == []
    assert rules("Stainless steel surcharges rose sharply.").cost_drivers_claimed == ["nickel", "steel"]


def test_accepted_without_claim_results_is_not_mapped_to_all_claims():
    s = rules("Fair point.", claims=[CLAIM_IDX])
    assert s.accepted_args == ["accepted an argument"]
    assert rules("Fair point.", claims=[CLAIM_IDX], results=[{"index": 0, "result": "verified"}]).accepted_args == [
        "index:PPI-D351"]  # fmt: skip


def test_parser_and_ask_normaliser_edge_cases():
    assert normalise_ask("otherwise more volume") == "volume"
    assert parse_json('I think {this} is it: {"tone": "warm"}') == {"tone": "warm"}


def test_second_review_cases():
    s = rules
    assert not s("As agreed, you pay within 30 days net.").cash_pressure
    assert "faster_payment" not in s("As agreed, you pay within 30 days net.").asks
    assert not s("Unfortunately a cash discount is not possible for us.").cash_pressure
    assert not s("Skonto können wir leider nicht gewähren.").cash_pressure
    assert not s("Our liquidity is excellent and our cash flow is solid.").cash_pressure
    assert not s("Nothing is overdue on your side.").cash_pressure
    assert not s("Our overhead allocation follows our standard calculation.").capacity_issue
    assert not s("Looking at capacity, we have plenty of room.").capacity_issue
    assert not s("The shortage of skilled workers has pushed up our wages.").capacity_issue
    assert s("Wir haben derzeit keine freien Kapazitäten.").capacity_issue
    assert not s("As in our last offer, payment remains 30 days net.").final_offer_language
    assert not s("The bottom line is that our energy costs have doubled.").final_offer_language
    assert not s("This is by no means our final offer.").final_offer_language
    assert s("This is the best we can do; we will not go any lower.").final_offer_language
    assert not s("We need your approval for the new material grade.").approval_pending
    assert s("I have to check this with our managing director first.").approval_pending
    assert s("Das muss ich mit der Geschäftsführung abstimmen.").approval_pending
    for warm in ("We were pleasantly surprised that your volumes grew.", "We have repeatedly invested in this line.",
                 "Thank you yet again for your trust."):
        assert s(warm).tone != "irritated", warm
    assert s("This proposal is ridiculous and we are tired of these discussions.").tone == "irritated"
