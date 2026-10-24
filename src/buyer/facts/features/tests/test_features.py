import csv
import hashlib
import math
import sqlite3
from datetime import date, timedelta

import pytest

from buyer.facts.features import build as build_mod
from buyer.facts.features.extract import BELOW_COST_NOTE, build_feature_vector
from buyer.facts.features.spec import BY_NAME, FEATURE_COLUMNS, FEATURES, ID_COLUMNS, TARGET_COLUMNS
from buyer.facts.features.store import DEFAULT_DB, SNAPSHOT_DATE, FeatureStore, last_complete_month, month_index

SUP, PART = "sup:70110", "part:310010"


@pytest.fixture(scope="session")
def store():
    return FeatureStore.from_sqlite()


@pytest.fixture(scope="session")
def hist(store):
    return build_mod.historical_rows(store)


@pytest.fixture(scope="session")
def current(store):
    return build_mod.current_rows(store)


def fv(store, sid, pid, as_of, cc=None):
    return build_feature_vector(sid, pid, as_of, cc, store=store)


# ------------------------------------------------------------------ the reference example


def test_reference_pair_all_three_negotiations(store):
    f = fv(store, SUP, PART, "2025-12-03")          # day of the third renewal
    assert f["hist_pair_count"] == 3
    assert f["hist_level"] == "pair"
    assert f["hist_avg_concession_pp"] == pytest.approx((3.4 + 2.0 + 3.5) / 3)
    assert round(f["hist_avg_concession_pp"], 2) == 2.97
    assert f["hist_last_concession_pp"] == pytest.approx(3.5)


@pytest.mark.parametrize("as_of, n, mean, last", [
    ("2025-12-02", 2, (3.4 + 2.0) / 2, 2.0),
    ("2024-11-17", 2, (3.4 + 2.0) / 2, 2.0),
    ("2024-11-16", 1, 3.4, 3.4),
    ("2023-11-16", 1, 3.4, 3.4),
])
def test_reference_pair_excludes_later_outcomes(store, as_of, n, mean, last):
    f = fv(store, SUP, PART, as_of)
    assert f["hist_pair_count"] == n
    assert f["hist_avg_concession_pp"] == pytest.approx(mean)
    assert f["hist_last_concession_pp"] == pytest.approx(last)


def test_reference_pair_before_any_renewal(store):
    f = fv(store, SUP, PART, "2023-11-15")
    assert f["hist_pair_count"] == 0
    assert f["hist_level"] != "pair" and f["hist_is_fallback"] == 1
    assert f["hist_last_concession_pp"] is None


def test_reference_training_row_excludes_own_outcome(hist):
    row = next(r for r in hist if r["event_id"] == "EV-2026-70110-310010")
    assert row["as_of_date"] == "2025-12-02"
    assert row["hist_pair_count"] == 2
    assert row["hist_avg_concession_pp"] == pytest.approx(2.7)
    assert row["target_concession_pp"] == pytest.approx(3.5)
    assert row["cur_asked_pct"] == pytest.approx(2.1)


def test_reference_example_values_as_of_snapshot(store):
    f = fv(store, SUP, PART, "2026-09-30")
    expected = {
        "part_category": "castings", "material_group": "cast_iron", "previous_unit_price": 126.53,
        "hist_pair_count": 3, "hist_last_concession_pp": 3.5, "forecast_12m_volume": 8150,
        "supplier_otd_pct": 85.2, "supplier_ppm": 712, "estimated_unit_cost": 132.64,
        "equity_ratio_pct": 24.7, "active_supplier_count": 1, "qualified_supplier_count": 1,
    }
    for k, v in expected.items():
        assert f[k] == pytest.approx(v) if isinstance(v, float) else f[k] == v, k
    assert f["hist_avg_concession_pp"] == pytest.approx(2.9667, abs=1e-4)


# ------------------------------------------------------------------ joins and grain


def test_training_grain(hist, store):
    assert len(hist) == 225
    assert len({r["event_id"] for r in hist}) == 225
    assert len({(r["supplier_id"], r["part_id"], r["negotiation_date"]) for r in hist}) == 225
    assert all(r["target_settled_pct"] is not None and r["target_concession_pp"] is not None for r in hist)


def test_joins_supplier_and_part(hist, current, store):
    for r in hist + current:
        assert r["supplier_id"] in store.suppliers
        assert r["part_id"] in store.parts
        assert r["part_category"] == store.parts[r["part_id"]]["category"]
        assert r["price_unit"] == store.parts[r["part_id"]]["price_unit"]
        assert r["supplier_country"] == store.suppliers[r["supplier_id"]]["country"]
        assert r["is_known_supplier"] == 1


def test_target_price_matches_settled_pct(hist):
    # the settled price is the previous price moved by settled_pct (rounded to cents)
    for r in hist:
        if r["previous_price_basis"] != "index_adjustment":
            expected = r["previous_unit_price"] * (1 + r["target_settled_pct"] / 100)
            assert r["target_settled_unit_price"] == pytest.approx(expected, rel=2e-3), r["event_id"]


def test_columns_match_registry(hist, current, store):
    assert list(fv(store, SUP, PART, "2026-09-30")) == FEATURE_COLUMNS
    assert list(hist[0]) == ID_COLUMNS + TARGET_COLUMNS + FEATURE_COLUMNS
    assert len(set(FEATURE_COLUMNS)) == len(FEATURE_COLUMNS)
    assert not set(FEATURE_COLUMNS) & set(ID_COLUMNS + TARGET_COLUMNS)
    for f in FEATURES:
        assert all([f.dtype, f.source, f.formula, f.cutoff, f.missing, f.meaning]), f.name


# ------------------------------------------------------------------ leakage


def truncate(store: FeatureStore, as_of: date) -> FeatureStore:
    """Independent re-implementation of 'what the database looked like at the end of as_of'."""
    t = store.tables
    d = as_of.isoformat()
    cap = last_complete_month(as_of)
    lag = store.index_lag

    def nulled(rows, col):
        return [{**r, col: None} if r[col] is not None and r[col] > d else r for r in rows]

    tables = dict(t)
    tables["negotiation_history"] = [r for r in t["negotiation_history"] if r["date"] <= d]
    tables["price_conditions"] = [r for r in t["price_conditions"] if r["valid_from"] <= d]
    tables["po_lines"] = [r for r in t["po_lines"] if r["order_date"] <= d]
    tables["invoices"] = nulled([r for r in t["invoices"] if r["invoice_date"] <= d], "paid_date")
    tables["quality_notifications"] = nulled([r for r in t["quality_notifications"] if r["qn_date"] <= d], "d8_date")
    tables["scorecards"] = [r for r in t["scorecards"] if r["period_end"] <= d]
    tables["forecasts"] = [r for r in t["forecasts"] if month_index(r["snapshot_month"]) <= cap]
    tables["should_cost"] = [r for r in t["should_cost"] if r["estimate_date"] <= d]
    tables["index_values"] = [r for r in t["index_values"] if month_index(r["month"]) <= cap - lag[r["series_id"]]]
    return FeatureStore(tables)


def _same(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def test_no_leakage_against_truncated_database(hist, store):
    sample = hist[::9] + [r for r in hist if r["supplier_id"] == SUP]
    for row in sample:
        as_of = date.fromisoformat(row["as_of_date"])
        past = truncate(store, as_of)
        f = build_feature_vector(row["supplier_id"], row["part_id"], as_of, {"asked_pct": row["cur_asked_pct"]},
                                 store=past)
        diff = {k: (row[k], f[k]) for k in FEATURE_COLUMNS if not _same(row[k], f[k])}
        assert not diff, (row["event_id"], diff)


def test_own_outcome_does_not_move_features(store):
    row_event = "EV-2025-70110-310010"
    tables = dict(store.tables)
    tables["negotiation_history"] = [{**r, "settled_pct": -99.0, "note": BELOW_COST_NOTE}
                                     if r["event_id"] == row_event else r for r in store.tables["negotiation_history"]]
    tampered = FeatureStore(tables)
    as_of = date(2024, 11, 16)
    assert fv(store, SUP, PART, as_of) == fv(tampered, SUP, PART, as_of)
    assert fv(store, SUP, PART, as_of + timedelta(days=1)) != fv(tampered, SUP, PART, as_of + timedelta(days=1))


# ------------------------------------------------------------------ date cutoffs


def test_snapshot_only_data_absent_from_history(hist):
    assert all(r["has_should_cost"] == 0 and r["estimated_unit_cost"] is None for r in hist)
    assert all(r["has_financials"] == 0 and r["equity_ratio_pct"] is None for r in hist)
    assert all(r["credit_index_change"] is None for r in hist)
    for r in hist:
        assert (r["credit_index"] is not None) == (r["as_of_date"] >= "2025-09-30")


def test_should_cost_appears_on_its_estimate_date(store):
    assert fv(store, SUP, PART, "2026-07-14")["estimated_unit_cost"] is None
    assert fv(store, SUP, PART, "2026-07-15")["estimated_unit_cost"] == pytest.approx(132.64)


def test_forecast_snapshot_known_at_month_end(store):
    assert fv(store, SUP, PART, "2026-09-29")["forecast_12m_volume"] == 8200    # fc:310010@2026-06
    assert fv(store, SUP, PART, "2026-09-30")["forecast_12m_volume"] == 8150    # fc:310010@2026-09


def test_scorecards_and_windows_respect_data_start(hist):
    for r in hist:
        if r["as_of_date"] < "2024-09-30":
            assert r["has_scorecard"] == 0 and r["supplier_otd_pct"] is None
        if r["po_window_complete"] == 0:
            assert r["po_12m_volume"] is None and r["quality_cost_12m"] is None and r["active_supplier_count"] is None
    assert {r["po_window_complete"] for r in hist if r["negotiation_date"] < "2024-01-01"} == {0}


def test_index_respects_publication_lag(store):
    # LCI-C ends 2026-06 at the snapshot: lag 3 months. On 2026-08-31 the latest month is 2026-05.
    from buyer.facts.features.extract import latest_index_month
    assert latest_index_month(store, "LCI-C", date(2026, 9, 30)) == month_index("2026-06")
    assert latest_index_month(store, "LCI-C", date(2026, 8, 31)) == month_index("2026-05")
    assert latest_index_month(store, "PPI-C241", date(2026, 9, 30)) == month_index("2026-08")


# ------------------------------------------------------------------ calculations


def test_price_unit_normalisation(store):
    part = next(p for p, r in store.parts.items() if r["price_unit"] == 100 and store.po_by_part.get(p))
    sid = store.po_by_part[part][0]["supplier_id"]
    as_of = SNAPSHOT_DATE
    f = fv(store, sid, part, as_of)
    lines = [r for r in store.po_by_pair[(sid, part)] if r["order_date"] >= (as_of - timedelta(days=364)).isoformat()]
    assert f["price_unit"] == 100
    assert f["po_12m_spend"] == pytest.approx(sum(r["qty"] * r["price"] / 100 for r in lines))
    assert f["previous_price_per_uom"] == pytest.approx(f["previous_unit_price"] / 100)
    fresh = [r["price"] for r in lines if r["price_note"] != "stale_condition"]
    assert min(fresh) <= f["po_12m_avg_unit_price"] <= max(fresh)   # per price_unit, not per piece


def test_stale_conditions_excluded_from_average_price(store):
    pair = next(k for k, rows in store.po_by_pair.items() if any(r["price_note"] == "stale_condition" for r in rows))
    stale = next(r for r in store.po_by_pair[pair] if r["price_note"] == "stale_condition")
    f = fv(store, *pair, stale["order_date"])
    lines = [r for r in store.po_by_pair[pair]
             if date.fromisoformat(stale["order_date"]) - timedelta(days=364) <= date.fromisoformat(r["order_date"])
             <= date.fromisoformat(stale["order_date"])]
    fresh = [r for r in lines if r["price_note"] != "stale_condition"]
    if fresh:
        assert f["po_12m_avg_unit_price"] == pytest.approx(sum(r["qty"] * r["price"] for r in fresh)
                                                           / sum(r["qty"] for r in fresh))
    assert f["po_stale_condition_share"] > 0


def test_category_and_global_aggregates_match_sql(store):
    as_of = "2025-06-30"
    con = sqlite3.connect(f"file:{DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    cat, = con.execute("""SELECT AVG(n.asked_pct - n.settled_pct) FROM negotiation_history n
                          JOIN parts p ON p.id = n.part_id
                          WHERE p.category = 'castings' AND n.settled_pct IS NOT NULL
                          AND n.date <= ?""", (as_of,)).fetchone()
    glob, cnt = con.execute("""SELECT AVG(asked_pct - settled_pct), COUNT(*) FROM negotiation_history
                               WHERE settled_pct IS NOT NULL AND date <= ?""", (as_of,)).fetchone()
    con.close()
    f = fv(store, SUP, PART, as_of)
    assert f["category_avg_concession_pp"] == pytest.approx(cat)
    assert f["global_avg_concession_pp"] == pytest.approx(glob)
    assert f["global_negotiation_count"] == cnt


def test_weighted_and_std(store):
    f = fv(store, SUP, PART, "2025-12-03")
    c = [3.4, 2.0, 3.5]
    ages = [(date(2025, 12, 3) - date.fromisoformat(d)).days for d in ("2023-11-16", "2024-11-17", "2025-12-03")]
    w = [0.5 ** (a / 365) for a in ages]
    assert f["hist_weighted_concession_pp"] == pytest.approx(sum(x * y for x, y in zip(w, c, strict=True)) / sum(w))
    m = sum(c) / 3
    assert f["hist_concession_std"] == pytest.approx(math.sqrt(sum((x - m) ** 2 for x in c) / 2))


def test_competition_matches_sourcing_status_at_snapshot(store):
    for part, rows in store.sourcing_by_part.items():
        f = fv(store, None, part, SNAPSHOT_DATE)
        assert f["active_supplier_count"] == sum(r["status"] == "active" for r in rows), part
        assert f["qualified_supplier_count"] == sum(r["status"] == "qualified" for r in rows), part


def test_open_8d_overdue_matches_scorecards(store):
    for rows in store.scorecards_by_supplier.values():
        for sc in rows:
            f = fv(store, sc["supplier_id"], PART, sc["period_end"])
            assert f["open_8d_overdue"] == sc["open_8d_overdue"], sc["id"]


def test_payment_delay_matches_readme_query(store):
    sid = "sup:70210"
    as_of = SNAPSHOT_DATE
    con = sqlite3.connect(f"file:{DEFAULT_DB.as_posix()}?mode=ro", uri=True)
    expected, = con.execute("""SELECT AVG(julianday(paid_date) - julianday(due_date)) FROM invoices
                               WHERE supplier_id = ? AND discount_taken = 0 AND paid_date IS NOT NULL
                               AND due_date BETWEEN ? AND ?""",
                            (sid, (as_of - timedelta(days=364)).isoformat(), as_of.isoformat())).fetchone()
    con.close()
    assert fv(store, sid, "part:320010", as_of)["avg_payment_delay_days"] == pytest.approx(expected)


# ------------------------------------------------------------------ missing values and unseen suppliers


SUPPLIER_LEVEL = ["previous_unit_price", "po_12m_volume", "po_12m_spend", "owner_type", "equity_ratio_pct",
                  "credit_index", "supplier_otd_pct", "supplier_ppm", "open_8d_overdue", "quality_cost_12m",
                  "avg_payment_delay_days", "late_payment_rate", "hist_last_concession_pp",
                  "supplier_avg_concession_pp", "supplier_country"]


@pytest.mark.parametrize("sid", [None, "sup:99999"])
def test_unseen_supplier(store, sid):
    f = fv(store, sid, PART, SNAPSHOT_DATE)
    assert f["is_known_supplier"] == 0
    assert all(f[k] is None for k in SUPPLIER_LEVEL)
    assert f["hist_pair_count"] == 0 and f["hist_negotiation_count"] == 0
    assert f["hist_level"] == "category" and f["hist_avg_concession_pp"] == f["category_avg_concession_pp"]
    # part-level information still flows
    assert f["forecast_12m_volume"] == 8150 and f["part_ref_unit_price"] == pytest.approx(126.53)
    assert f["estimated_unit_cost"] == pytest.approx(132.64) and f["should_cost_supplier_specific"] == 0
    assert f["active_supplier_count"] == 1


def test_unseen_supplier_fill_ins_and_context(store):
    cc = {"supplier_country": "PL", "owner_type": "family", "equity_ratio_pct": 18.0, "quoted_unit_price": 120.0}
    f = fv(store, None, PART, SNAPSHOT_DATE, cc)
    assert f["supplier_country"] == "PL" and f["owner_type"] == "family" and f["equity_ratio_pct"] == 18.0
    assert f["has_group_parent"] == 0
    assert f["cur_quote_to_cost_ratio"] == pytest.approx(120.0 / 132.64)


def test_fill_ins_never_override_database(store):
    f = fv(store, SUP, PART, SNAPSHOT_DATE, {"supplier_country": "PL", "equity_ratio_pct": 99.0})
    assert f["supplier_country"] == "DE" and f["equity_ratio_pct"] == 24.7


def test_unknown_part_with_fill_ins(store):
    f = fv(store, None, "part:999999", SNAPSHOT_DATE, {"part_category": "seals", "price_unit": 1})
    assert f["part_category"] == "seals" and f["hist_level"] == "category"
    assert f["previous_unit_price"] is None and f["active_supplier_count"] is None


def test_unknown_current_condition_key_rejected(store):
    with pytest.raises(ValueError):
        fv(store, SUP, PART, SNAPSHOT_DATE, {"asked_pc": 3.0})


def test_alias_supplier_maps_to_current_record(store):
    assert fv(store, "sup:71999", PART, SNAPSHOT_DATE) == fv(store, "sup:70210", PART, SNAPSHOT_DATE)


def test_known_supplier_zero_is_not_null(store):
    f = fv(store, "sup:70140", PART, SNAPSHOT_DATE)        # qualified, never ordered this part
    assert f["po_12m_volume"] == 0 and f["po_12m_order_count"] == 0
    assert f["previous_unit_price"] is None


# ------------------------------------------------------------------ types


@pytest.mark.parametrize("rows", ["hist", "current"])
def test_types_follow_registry(rows, request, store):
    data = request.getfixturevalue(rows)
    data = data + [fv(store, None, PART, SNAPSHOT_DATE)]
    for name in FEATURE_COLUMNS:
        kind = BY_NAME[name].dtype
        for r in data:
            v = r[name]
            if v is None:
                continue
            if kind == "float":
                assert isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v), name
            elif kind == "int":
                assert isinstance(v, int) and not isinstance(v, bool), (name, v)
            elif kind == "bool":
                assert v in (0, 1) and not isinstance(v, bool), (name, v)
            elif kind == "category":
                assert isinstance(v, str), (name, v)


# ------------------------------------------------------------------ outputs


def test_build_writes_outputs_and_leaves_source_untouched(tmp_path, monkeypatch):
    before = hashlib.sha256(DEFAULT_DB.read_bytes()).hexdigest()
    monkeypatch.setattr(build_mod, "DOC_PATH", tmp_path / "FEATURES.md")
    build_mod.main(["--out", str(tmp_path)])
    assert hashlib.sha256(DEFAULT_DB.read_bytes()).hexdigest() == before

    with (tmp_path / "historical_negotiation_features.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 225 and list(rows[0]) == build_mod.HIST_COLUMNS
    con = sqlite3.connect(tmp_path / "negotiation_features.sqlite")
    counts = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
              for t in ("historical_negotiation_features", "current_supplier_features", "feature_dictionary")}
    con.close()
    assert counts == {"historical_negotiation_features": 225, "current_supplier_features": 90,
                      "feature_dictionary": len(ID_COLUMNS) + len(TARGET_COLUMNS) + len(FEATURE_COLUMNS)}
    doc = (tmp_path / "FEATURES.md").read_text(encoding="utf-8")
    assert all(f"`{name}`" in doc for name in FEATURE_COLUMNS)
