from buyer.llm.guard import (
    allowed_tokens,
    canonical_placeholders,
    digit_tokens,
    filter_sentences,
    foreign_numbers,
    isolate_placeholders,
    leaks,
    strip_unknown_ids,
    verify_email,
)

from .helpers import CASE, CLAIM_IDX, PROFILE, decision


def test_digit_tokens():
    assert digit_tokens("from 2027-04-01 for HN 50-200, IE3 motors.") == ["2027-04-01", "50-200", "IE3"]
    assert digit_tokens("see idx:PPI-D351@2025-08 and [[CLAIM_1]]") == []  # data IDs, placeholders
    # only checkable data IDs are exempt: "part:10 euros" must not hide a figure
    assert digit_tokens("sup:70110 and part:10") == ["70110", "10"]


def test_prose_may_hold_no_figure():
    d = decision(questions=("8D report",))
    case = {**CASE, "title": "Motor IE3 7.5 kW, 4-pole: a price increase"}
    allowed = allowed_tokens(d, case, PROFILE)
    assert allowed == {"IE3", "7.5", "4-pole", "8D"}
    for ok in ("Your IE3 motors are important to us.", "Please send the 8D report.", "We see two options."):
        assert not foreign_numbers(ok, allowed), ok
    for bad in ("We propose EUR 129.90.", "Prices fell 3.7% last year.", "That is 8% too much.", "EUR 2,027 is fair.",
                "We buy 60.000 units.", "About 14k pieces.", "We expect ten percent less.",
                "One hundred twenty euros is our view.", "We think eur:118.50 is right.", "Since 2026 we work together.",  # noqa: E501
                "Prices fell 7.5 % this year."):  # fmt: skip
        assert foreign_numbers(bad, allowed), bad


def test_strip_unknown_ids():
    text = "As shown (doc:FAKE-1), prices fell (idx:PPI-D351@2026-08, quote:1)."
    out, dropped = strip_unknown_ids(text, lambda i: i.startswith("idx:"))
    assert dropped == ["doc:FAKE-1", "quote:1"]
    assert out == "As shown, prices fell (idx:PPI-D351@2026-08)."
    assert strip_unknown_ids("Prices fell (doc:A-1, quote:1) as shown.", lambda i: False)[0] == "Prices fell as shown."
    out = strip_unknown_ids("A (quote:1, idx:X@2026-01) b.", lambda i: i.startswith("idx"))[0]
    assert out == "A (idx:X@2026-01) b."


def test_placeholders_are_normalised_and_isolated():
    assert canonical_placeholders("[CLAIM_1] [[claim 2]] [[CLAIM-3]] {{OFFERS}} [[Claim4]] [[question]] [[CLAIMS]]") == (  # noqa: E501
        "[[CLAIM_1]] [[CLAIM_2]] [[CLAIM_3]] [[OFFERS]] [[CLAIM_4]] [[QUESTIONS]] [[CLAIMS]]")  # fmt: skip
    text, dropped = isolate_placeholders("Our data shows: [[CLAIM_1]]\nWe do not believe that [[CLAIM_2]] at all.\n1[[CLAIM_3]]")  # noqa: E501
    assert text.split("\n") == ["Our data shows:", "[[CLAIM_1]]", "[[CLAIM_2]]", "[[CLAIM_3]]"]
    assert dropped == ["We do not believe that", "at all.", "1"]


def test_filter_sentences_keeps_placeholders_and_paragraphs():
    text = "Dear all,\n\nGood. Bad 7 here. Fine.\n[[CLAIM_1]]\n\nAll bad 9.\n\nEnd."
    out, dropped = filter_sentences(text, lambda s: bool(foreign_numbers(s, set())))
    assert out == "Dear all,\n\nGood. Fine.\n[[CLAIM_1]]\n\nEnd."
    assert dropped == ["Bad 7 here.", "All bad 9."]


def test_leaks():
    for s in ("This is urgent.", "Our budget is tight.", "We have no alternative.", "Our target price is lower.",
              "We must close this week.", "As an AI I think so.", "We know your bank is worried."):  # fmt: skip
        assert leaks(s), s
    for s in ("Thank you for your offer.", "We value the cooperation.", "Option B pays faster."):
        assert not leaks(s), s


def test_verify_email():
    d = decision()
    allowed = allowed_tokens(d, CASE, PROFILE)
    good = f"Dear all,\n{CLAIM_IDX.sentence}\nThanks."
    assert verify_email(good, d.claims, [CLAIM_IDX.sentence], allowed) == []
    assert verify_email("Dear all, thanks.", d.claims, [], allowed)[0].startswith("claim missing")
    glued = f"Dear all,\nWe doubt that {CLAIM_IDX.sentence}\nThanks."
    assert verify_email(glued, d.claims, [CLAIM_IDX.sentence], allowed)[0].startswith("claim missing")
    assert any("foreign" in p for p in verify_email(good + " Pay 77.", d.claims, [CLAIM_IDX.sentence], allowed))
    for residue in (" [[OFFERS]]", " [CLAIM_2]", " {{QUESTIONS}}", " OFFERS"):
        assert any("placeholder" in p for p in verify_email(good + residue, d.claims, [CLAIM_IDX.sentence], allowed))
    assert not verify_email(good + " Thank you for your offers and questions.", d.claims, [CLAIM_IDX.sentence], allowed)
    unknown = verify_email(good + " doc:X-1", d.claims, [CLAIM_IDX.sentence], allowed, lambda i: False)
    assert any("unknown IDs" in p for p in unknown)
