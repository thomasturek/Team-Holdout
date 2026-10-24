import time

import pytest
from facts_cases import kit_cases, practice_cases

from buyer.facts.claims import check, claims, compatible, session_offers, supplier_claims
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
    assert {"index", "notice", "otd", "ppm", "po"} <= keys
    assert "po_rival" not in keys  # the arena rates other suppliers' orders irrelevant


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


# ------------------------------------------------------------------ RFQ: rival offers and quotes

RFQ = {"case_id": "case:T", "parts": ["part:310020"], "suppliers": ["sup:70140", "sup:70190"],
       "refs": ["quote:7200011"], "buyer": {"alternative": {"kind": "none", "ref": None}}}


def _offer(sid, n, price):
    return {"from": f"sales@{sid[4:]}", "term_sheets": [{"term_sheet_id": f"offer:{sid[4:]}-{n}",
                                                         "terms": {"unit_price": price}}]}


THREADS = {"sup:70140": [_offer("sup:70140", 0, 49.90)],
           "sup:70190": [_offer("sup:70190", 0, 55.00), {"from": "buyer"}, _offer("sup:70190", 1, 48.20)]}


def test_rival_offer_is_cited_to_the_dearer_bidder_only():
    bank = {c.key: c for c in claims(RFQ, threads=THREADS)}
    c = bank["rival:sup:70140:offer:70190-1"]  # the latest offer stands, not the opening 55.00
    assert "EUR 48.20" in c.sentence and c.refs == ["offer:70190-1"]
    assert not any(k.startswith("rival:sup:70190") for k in bank)  # nothing cheaper than its 48.20
    assert check(RFQ, "sup:70140", c.sentence, offers=session_offers(THREADS)) == "verified"


def test_case_quote_is_cited_when_cheaper():
    threads = {**THREADS, "sup:70140": [_offer("sup:70140", 0, 60.00)]}
    bank = {c.key: c for c in claims(RFQ, "sup:70140", threads=threads)}
    assert "EUR 53.56" in bank["rival:sup:70140:quote:7200011"].sentence  # sup:70190's quote of this case


def test_rival_checks():
    offers = session_offers(THREADS)
    s = "Another supplier has offered EUR 48.20 for this part (offer:70190-1)."
    assert check(RFQ, "sup:70140", s.replace("48.20", "45.00"), offers=offers) == "contradicted"
    assert check(RFQ, "sup:70140", s) == "contradicted"  # no such offer outside the session
    assert check(RFQ, "sup:70190", s, offers=offers) == "irrelevant"  # its own offer
    assert check(RFQ, "sup:70140", "A quote at EUR 49.20 (quote:7100007).") == "irrelevant"  # not a quote of the case
    assert not any(c.key.startswith("rival") for c in claims(RFQ))  # no threads, no rival claims


def test_supplier_claims_for_the_review():
    bank = {c.key for c in supplier_claims("sup:70110", "part:310010")}
    assert {"notice:sup:70110", "otd:sup:70110", "index:PPI-D351"} <= bank


def test_dropped_claims_never_come_back(monkeypatch):
    import buyer.facts.claims as cl

    monkeypatch.setattr(cl, "_dropped", lambda sid: {"otd:sup:70110"})
    keys = {c.key for c in claims(P01, "sup:70110")}
    assert "otd:sup:70110" not in keys and "ppm:sup:70110" in keys


def test_other_suppliers_orders_are_irrelevant():
    """P18 replay: "The price history data you cite does not concern this part or our company"."""
    s = ("We also buy it at EUR 128.42 on 2024-10-04 (po:4500011493-10) and EUR 126.53 on 2026-09-21 "
         "(po:4500014428-10).")  # sup:70110's orders
    assert check(P01, "sup:70110", s) == "verified"
    assert check(P01, "sup:70140", s) == "irrelevant"
