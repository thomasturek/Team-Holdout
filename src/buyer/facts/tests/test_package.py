import json
import time
from pathlib import Path

import pytest

from buyer.facts import package as pk
from buyer.facts.package import CaseData, load_package, lookup

SIM_CASES = pk.REPO_ROOT / "starter-kit" / "arena_kit" / "sim_cases"


@pytest.fixture(scope="module")
def data():
    return CaseData(package=load_package(pk.DEFAULT_DATA))  # module scope: before the env fixture


def test_known_ids_found_and_citable(data):
    for ref in ("idx:PPI-C2451@2026-08", "sc:70110@2026Q3", "cost:310010", "ctr:4600070110", "po:4500010001-10"):
        assert data.lookup(ref) is not None, ref
        assert data.citable(ref), ref
        assert data.source(ref) == "package", ref
    assert data.lookup("cost:310010")["unit_cost"] == 132.64


def test_master_data_ids_are_not_evidence(data):
    # facts.json lists evidence (po, idx, qn, fc, sc, ctr, doc, quote, rfq, news, cost), not master data
    for ref in ("sup:70110", "part:310010"):
        assert data.lookup(ref) is not None and not data.citable(ref), ref
        assert data.source(ref) == "table"


def test_unknown_id(data):
    assert data.lookup("sup:00000") is None
    assert not data.citable("sup:00000")
    assert data.source("sup:00000") is None
    with pytest.raises(KeyError):
        data.require("sup:00000")


def test_table_rows_are_lookup_only(data):
    # IDs that sit in world.sqlite but not in facts.json: readable, never citable
    table_only = next(i for i in data.ids("inv:") if i not in data.package.facts)
    assert data.lookup(table_only)["table"] == "invoices"
    assert not data.citable(table_only)
    assert data.source(table_only) == "table"


def test_case_facts_come_first():
    case = {"case_id": "case:T", "facts": {
        "doc:new-letter": {"supplier": "sup:70110", "date": "2026-10-01", "days": 30, "body": "New prices."},
        "cost:310010": {"part": "part:310010", "unit_cost": 1.0},
    }}
    data = CaseData(case)
    assert data.citable("doc:new-letter") and data.source("doc:new-letter") == "case"
    assert data.document("doc:new-letter") == "New prices."
    assert data.lookup("cost:310010")["unit_cost"] == 1.0          # the case overrides the package
    assert "doc:new-letter" in data.ids("doc:")
    assert not CaseData().citable("doc:new-letter")                 # and only inside that case
    assert lookup("doc:new-letter", case)["days"] == 30


def test_kit_sample_case_facts_are_citable():
    case = json.loads((SIM_CASES / "S01.json").read_text(encoding="utf-8"))
    data = CaseData(case)
    for ref in case["refs"] + list(case["facts"]):
        assert data.citable(ref), ref


def test_documents_and_query(data):
    doc_id = data.ids("doc:")[0]
    assert len(data.document(doc_id)) > 0
    assert data.query("SELECT COUNT(*) AS n FROM parts")[0]["n"] == 60
    with pytest.raises(ValueError):
        data.query("DELETE FROM parts")


def test_package_is_cached_and_fast():
    t = time.perf_counter()
    a, b = load_package(), load_package()
    assert a is b
    data = CaseData({"facts": {}})
    t = time.perf_counter()
    for _ in range(1000):
        data.lookup("sc:70110@2026Q3")
        data.citable("idx:PPI-C2451@2026-08")
    assert time.perf_counter() - t < 0.5


def _fake_package(root: Path, with_release: bool) -> Path:
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "facts.json").write_text(json.dumps({"sup:1": {"name": "Old Supplier"}}), encoding="utf-8")
    if with_release:
        rel = pkg / "release-sunday"
        (rel / "data").mkdir(parents=True)
        (rel / "facts.json").write_text(json.dumps({"news:900": {"supplier": "sup:1"}}), encoding="utf-8")
        (rel / "data" / "news.csv").write_text("id,headline,body\nnews:900,Strike,Plant on strike.\n",
                                                encoding="utf-8")
    return pkg


def test_without_release(tmp_path):
    data = CaseData(package=load_package(_fake_package(tmp_path, False), refresh=True))
    assert not data.has_release
    assert data.citable("sup:1") and not data.citable("news:900")


def test_with_release(tmp_path):
    data = CaseData(package=load_package(_fake_package(tmp_path, True), refresh=True))
    assert data.has_release
    assert data.citable("news:900") and data.source("news:900") == "release"
    assert data.source("sup:1") == "package"
    assert data.document("news:900") == "Plant on strike."


def test_data_root_resolution(monkeypatch, tmp_path):
    monkeypatch.delenv("ARENA_DATA", raising=False)
    assert pk.data_root() == pk.DEFAULT_DATA.resolve()
    monkeypatch.setenv("ARENA_DATA", "data")                      # .env.example: relative to the repo
    monkeypatch.chdir(tmp_path)
    assert pk.data_root() == pk.DEFAULT_DATA.resolve()
    assert pk.data_root(tmp_path) == tmp_path.resolve()
