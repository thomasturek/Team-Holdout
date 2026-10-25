import json

import pytest
from arena_kit.cost import total_cost
from arena_kit.docs import standard_terms

from buyer.facts import memory as mem
from buyer.facts.costing import FULL_COST_FACTOR, c, relationship_case, relationship_floor, supplier_estimate
from buyer.facts.package import REPO_ROOT
from buyer.facts.profile import profile

CASES_FILE = REPO_ROOT / "runs" / "cases" / "practice.json"
CASES = {x["case_id"]: x for x in json.loads(CASES_FILE.read_text(encoding="utf-8"))} if CASES_FILE.is_file() else {}
needs_cases = pytest.mark.skipif(not CASES, reason="no runs/cases/practice.json")


def _session(case_id):
    """The last logged practice session of a case with a deal, or None."""
    for path in sorted((REPO_ROOT / "runs" / "practice_sessions").glob(f"*_{case_id.replace(':', '_')}_*.json"),
                       reverse=True):
        doc = json.loads(path.read_text(encoding="utf-8"))
        purpose = str((doc.get("run") or {}).get("purpose") or "")
        if purpose.startswith(("strat-", "bet-")):  # forced-strategy experiments end at unusual terms
            continue
        if (doc.get("result") or {}).get("deal") and (doc.get("result") or {}).get("score"):
            return doc
    return None


@needs_cases
def test_only_stabilise_and_secure_supply_carry_the_charge():
    assert relationship_case(CASES["case:P01"]) and relationship_case(CASES["case:P10"])
    assert not relationship_case(CASES["case:P04"]) and not relationship_case(CASES["case:P08"])


@needs_cases
def test_outside_those_cases_c_is_plain_total_cost():
    case = CASES["case:P04"]
    terms = {"unit_price": 4.5, "payment_days": 60, "contract_months": 24}
    assert c(case, terms, {}, {"floor_estimate": 4.0}) == total_cost(case, terms, {})


@needs_cases
def test_estimate_rules():
    case = CASES["case:P01"]
    assert supplier_estimate(case, {}) is None  # no full cost, no charge
    sure = {"floor_computed": 100.0, "floor_computed_source": "should_cost", "cash_rate_estimate": 0.12}
    e = supplier_estimate(case, {**sure, "floor_estimate": 90.0})
    assert e["full_cost"] == pytest.approx(FULL_COST_FACTOR * 100.0) and e["interest_rate"] == 0.12
    assert supplier_estimate(case, {"floor_computed": 100.0, "full_cost_observed": 95.0})["full_cost"] == 95.0
    for rough in ("own_price", "market_price", "should_cost_country", "bundle_current_price", None):
        assert supplier_estimate(case, {"floor_estimate": 100.0, "floor_source": rough}) is None  # too rough
    e = supplier_estimate(case, {"floor_estimate": 100.0, "floor_source": "should_cost",
                                 "vendor_terms": {"incoterm": "XYZ"}})
    assert e["standard"]["incoterm"] in case["buyer"]["freight_eur_per_unit"]  # never an unknown Incoterm
    assert e["standard"]["payment_days"] == case["buyer"]["reference_payment_days"]


def _strategic_sessions():
    out = []
    for path in sorted((REPO_ROOT / "runs" / "practice_sessions").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        r = doc.get("result") or {}
        if r.get("deal") and relationship_case(doc["case"]):
            out.append(doc)
    return out


STRATEGIC = _strategic_sessions()


@pytest.mark.skipif(not STRATEGIC, reason="no logged stabilise / secure_supply deals")
@pytest.mark.parametrize("doc", STRATEGIC, ids=lambda d: d["session_id"])
def test_logged_charges_are_reproduced(doc):
    """Every logged relationship charge: exact for a supplier the memory knows (one charge fixes its
    full cost - P01's EUR 615 reproduces its EUR 6,071 and EUR 10,848 sessions), the right size from the
    data estimate alone."""
    r = doc["result"]
    sid, case = r["supplier_id"], doc["case"]
    std = standard_terms(doc["threads"][sid]["messages"]) or {}
    logged = r["cost_breakdown"].get("relationship") or 0.0
    p = profile(case)[sid]
    charge = c(case, r["terms"], std, p) - total_cost(case, r["terms"], std)
    if p.get("full_cost_observed"):
        assert charge == pytest.approx(logged, rel=0.05, abs=50)
    data_only = {k: v for k, v in p.items() if k != "full_cost_observed"}
    charge = c(case, r["terms"], std, data_only) - total_cost(case, r["terms"], std)
    assert 0.5 * logged - 100 <= charge <= 2.0 * logged + 100  # steep and quadratic: the right size


@needs_cases
def test_relationship_floor_sits_between_full_cost_and_the_best_price():
    for case_id in ("case:P01", "case:P03"):
        doc = _session(case_id)
        if doc is None:
            continue
        r = doc["result"]
        sid, case = r["supplier_id"], doc["case"]
        std = standard_terms(doc["threads"][sid]["messages"]) or {}
        p = profile(case)[sid]
        floor = relationship_floor(case, r["terms"], std, p)
        best = mem.observation(doc)["best_price"]
        full = supplier_estimate(case, p, std)["full_cost"]
        assert full * 0.995 < floor <= best * 1.01, (case_id, floor, best)  # the knee can sit at the full cost


@needs_cases
def test_no_relationship_floor_outside_strategic_cases():
    case = CASES["case:P08"]
    assert relationship_floor(case, {"unit_price": 5.0}, {}, {"floor_estimate": 4.5}) is None


def test_memory_stores_the_full_cost_a_charge_implies():
    m = json.loads(mem.MEMORY_FILE.read_text(encoding="utf-8"))
    observed = {k: e["full_cost_observed"] for k, e in m["entries"].items() if e.get("full_cost_observed")}
    assert observed, "no relationship charge in the logged sessions"
    for k, value in observed.items():
        assert value > 0 and m["entries"][k]["estimate"] is None or value < m["entries"][k]["estimate"] * 1.1


def test_policy_never_asks_below_the_relationship_floor():
    from buyer.policy.policy import Policy, ThreadState

    if not CASES:
        pytest.skip("no runs/cases/practice.json")
    case = CASES["case:P03"]
    prof = {"floor_estimate": 300.0, "floor_computed": 403.21, "floor_computed_source": "should_cost",
            "cash_rate_estimate": 0.08,
            "vendor_terms": {"payment_days": 30, "incoterm": "DAP", "lead_time_days": 49}}
    terms = {"unit_price": 438.21, "payment_days": 30, "contract_months": 24, "volume_per_year": 4580}
    t = ThreadState(case["suppliers"][0], "offer:x-0", terms, "open", {"payment_days": 30}, 10, profile=prof)
    d = Policy().decide(case, t)
    floor = relationship_floor(case, terms, t.standard, prof)
    assert d.kind == "send" and floor is not None
    assert t.our_prices[-1] >= floor - 0.01  # the low floor estimate (300) would have let it ask far lower
