import json

import pytest

from buyer.facts.package import REPO_ROOT
from buyer.facts.profile import profile
from buyer.facts.strategy import PARAMS, TONES, choose, initial

CASES_FILE = REPO_ROOT / "runs" / "cases" / "practice.json"
CASES = {x["case_id"]: x for x in json.loads(CASES_FILE.read_text(encoding="utf-8"))} if CASES_FILE.is_file() else {}
pytestmark = pytest.mark.skipif(not CASES, reason="no runs/cases/practice.json")


def first(case_id):
    case = CASES[case_id]
    sid = case["suppliers"][0]
    return case, profile(case)[sid]


@pytest.mark.parametrize("case_id, expected", [
    ("case:P05", "aggressive"),   # several bidders: rival offers
    ("case:P10", "secure"),       # sole source, capacity: walking away scores 0
    ("case:P18", "escalate"),     # Inside Sales does not decide alone
    ("case:P08", "escalate"),
    ("case:P11", "aggressive"),   # cash-short: it needs the business
    ("case:P01", "cooperative"),  # strategic supply, family firm
])
def test_opening_strategy_follows_what_we_know(case_id, expected):
    case, p = first(case_id)
    assert initial(case, p).name == expected
    assert p["strategy"] == expected and p["strategy_params"] == PARAMS[expected]  # carried in the profile


def test_every_strategy_has_a_tone_and_params():
    assert set(TONES) == set(PARAMS) == {"aggressive", "cooperative", "patient", "escalate", "secure"}


def test_switches_on_what_the_reply_reveals():
    case, p = first("case:P01")
    start = initial(case, p)
    assert choose(case, p, {"tone": "irritated"}, [], start).name == "cooperative"
    assert choose(case, p, {"approval_pending": True}, [], start).name == "escalate"
    assert choose(case, p, {"final_offer_language": True}, [], start).name == "secure"
    assert choose(case, p, {"accepted_args": ["notice:sup:70110"]}, [], start).name == "aggressive"
    held = [{"from": "s", "term_sheets": [{"terms": {"unit_price": x}}]} for x in (140.0, 138.0, 138.0, 138.0)]
    assert choose(case, p, {}, held, initial(case, p)).name == "patient"  # held twice: trade, do not concede


def test_final_offer_in_an_rfq_does_not_force_secure():
    case = CASES["case:P05"]
    p = profile(case)[case["suppliers"][0]]
    assert choose(case, p, {"final_offer_language": True}, [], initial(case, p)).name == "aggressive"
