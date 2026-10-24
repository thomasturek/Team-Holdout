import re

from buyer.facts.dossier import dossier, observed
from buyer.facts.profile import lookup_profile, pairs, profile

ID_RE = re.compile(r"\b(?:idx|sc|po|qn|doc|ctr|quote|offer|news|sup|part|cost|fc):\S+")


def first_part_per_supplier():
    seen = {}
    for sid, part in pairs():
        seen.setdefault(sid, part)
    return seen


def test_every_final_supplier_gets_a_clean_dossier():
    suppliers = first_part_per_supplier()
    assert len(suppliers) == 46
    for sid, part in suppliers.items():
        text = dossier(lookup_profile(sid, part))
        assert text and "Angle:" in text, sid
        assert not re.search(r"\d", text), (sid, text)  # never a figure the writer could repeat
        assert not ID_RE.search(text), (sid, text)
        assert not re.search(r"credit|equity|bank|insolven|liquidity", text, re.I), (sid, text)


def test_what_practice_showed_is_in_it():
    nordmark = dossier(lookup_profile("sup:70510", "part:350011"))
    assert "copper" in nordmark and "pricing committee" in nordmark and "Approver memo" in nordmark
    werdenfels = dossier(lookup_profile("sup:70740", "part:370010"))
    assert "inside sales" in werdenfels and "escalate" in werdenfels
    brandlhuber = dossier(lookup_profile("sup:70110", "part:310010"))
    assert "owner" in brandlhuber and "loyalty" in brandlhuber


def test_unknown_supplier_still_gets_an_angle():
    text = dossier({"supplier_id": "sup:99999", "archetype": "unknown"}, obs={})
    assert "Angle:" in text and not re.search(r"\d", text)


def test_the_case_profile_carries_the_dossier():
    p = profile({"suppliers": ["sup:70510"], "parts": ["part:350011"]})["sup:70510"]
    assert p["dossier"] and "copper" in p["dossier"]


def test_observations_are_committed():
    assert observed("sup:70510").get("contact_role") == "Key Account Manager"
