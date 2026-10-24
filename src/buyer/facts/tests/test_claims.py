import time

import pytest
from facts_cases import kit_cases, practice_cases

from buyer.facts.claims import check, claims, compatible
from buyer.facts.package import CaseData

PRACTICE = practice_cases()
P01 = next(c for c in PRACTICE if c["case_id"] == "case:P01")


def test_there_are_19_practice_cases():
    assert [c["case_id"] for c in PRACTICE] == [f"case:P{i:02d}" for i in range(1, 20)]


@pytest.mark.parametrize("case", PRACTICE + kit_cases(), ids=lambda c: c["case_id"])
def test_every_claim_verifies(case):
    data = CaseData(case)
    bank = claims(case, data=data)
    assert bank, "no claims at all"
    for sid in case["suppliers"]:
        for c in claims(case, sid, data=data):
            assert check(case, sid, c.sentence, data=data) == "verified", c.sentence
            assert c.expected == "verified" and 0 <= c.strength <= 1
            assert "\n" not in c.sentence
            assert all(data.citable(r) for r in c.refs), c.refs
            assert all(r in c.sentence for r in c.refs), c.sentence


def test_build_is_fast():
    t = time.perf_counter()
    for case in PRACTICE:
        claims(case)
    assert time.perf_counter() - t < 2.0


def test_p01_matches_the_brief_example():
    """api.md: the PPI-D351 sentence from practice case P01 came back verified."""
    bank = {c.key: c for c in claims(P01, "sup:70110")}
    s = bank["index:PPI-D351"].sentence
    assert "-3.7%" in s and "idx:PPI-D351@2025-08" in s and "idx:PPI-D351@2026-08" in s
    notice = bank["notice:sup:70110"]
    assert "51 days" in notice.sentence and "90 days" in notice.sentence
    assert notice.refs == ["doc:20260911-70110-P01", "ctr:4600070110"]


def test_notice_only_when_the_letter_gives_less_than_the_contract():
    keys = {c["case_id"]: {k.key for k in claims(c)} for c in PRACTICE}
    assert "notice:sup:70230" in keys["case:P13"]            # 35 < 90 days
    assert not any(k.startswith("notice:") for k in keys["case:P02"])  # 109 >= 90 days
    assert not any(k.startswith("notice:") for k in keys["case:P17"])  # 104 >= 90 days


def test_kinds_present():
    keys = {k.key.split(":")[0] for c in PRACTICE for k in claims(c)}
    assert {"index", "notice", "otd", "ppm", "po", "po_rival"} <= keys


def test_wrong_figure_is_contradicted():
    s = ("German electricity producer prices changed -2.0% from 2025-08 to 2026-08 "
         "(idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).")
    assert check(P01, "sup:70110", s) == "contradicted"
    assert check(P01, "sup:70110", s.replace("-2.0%", "-3.4%")) == "verified"  # within 0.5 pp
    assert check(P01, "sup:70110", "Your on-time delivery was 70.0% (sc:70110@2026Q3).") == "contradicted"
    assert check(P01, "sup:70110", "Your letter (doc:20260911-70110-P01) gives 60 days' notice, our contract "
                                   "(ctr:4600070110) 90 days.") == "contradicted"


def test_unknown_id_is_contradicted():
    assert check(P01, "sup:70110", "Prices fell 3% (idx:PPI-D351@1999-01, idx:PPI-D351@2026-08).") == "contradicted"


def test_irrelevant_claims():
    old = "Electricity changed +1.0% from 2023-08 to 2024-08 (idx:PPI-D351@2023-08, idx:PPI-D351@2024-08)."
    assert check(P01, "sup:70110", old) == "irrelevant"  # window too old
    long = "Electricity changed +1.0% (idx:PPI-D351@2024-08, idx:PPI-D351@2026-08)."
    assert check(P01, "sup:70110", long) == "irrelevant"  # window longer than 12 months
    assert check(P01, "sup:70110", "Copper changed +47.7% (idx:CU-NOTATION@2025-09, idx:CU-NOTATION@2026-09).") \
        == "irrelevant"  # not a cost driver of a volute casing
    assert check(P01, "sup:70110", "Their on-time delivery was 63.5% (sc:70140@2026Q3).") == "irrelevant"


def test_duplicate_and_compatible():
    bank = claims(P01, "sup:70110")
    first = bank[0]
    assert check(P01, "sup:70110", first.sentence, used=set(first.refs)) == "duplicate"
    picked = compatible(bank)
    assert len(picked) == 3
    refs = [r for c in picked for r in c.refs]
    assert len(refs) == len(set(refs))
    otd_ppm = [c for c in bank if c.key in ("otd:sup:70110", "ppm:sup:70110")]
    assert len(compatible(otd_ppm, limit=3)) == 1  # same scorecard row: only one of the two
    assert all(set(c.refs).isdisjoint(first.refs) for c in compatible(bank, used=set(first.refs)))


def test_case_facts_letter_gives_a_notice_claim():
    letter = {"supplier": "sup:70110", "date": "2026-10-01", "days": 30, "asked_pct": 5.0, "asked_price": None,
              "effective_date": "2026-11-01", "title": "Price", "type": "letter"}
    case = {"case_id": "case:X", "parts": ["part:310010"], "suppliers": ["sup:70110"], "trigger_doc": "doc:new",
            "facts": {"doc:new": letter}}
    bank = {c.key: c for c in claims(case)}
    assert "doc:new" in bank["notice:sup:70110"].refs
    assert check(case, "sup:70110", bank["notice:sup:70110"].sentence) == "verified"
