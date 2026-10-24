"""Build the ML feature datasets.

    PYTHONPATH=src uv run --no-project --python 3.12 python -m buyer.facts.features.build [--out runs/features]

Writes (never touches data/world.sqlite):
    <out>/historical_negotiation_features.csv   one row per renewal with asked and settled change
    <out>/current_supplier_features.csv         one row per source-list supplier-part pair as of 2026-09-30
    <out>/negotiation_features.sqlite           both tables + feature_dictionary + missing_report
    src/buyer/facts/features/FEATURES.md        data dictionary (from spec.py)
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from .extract import build_feature_vector
from .spec import BY_NAME, FEATURE_COLUMNS, FEATURES, ID_COLUMNS, IDS, TARGET_COLUMNS, TARGETS
from .store import REPO_ROOT, SNAPSHOT_DATE, FeatureStore, canonical_supplier

DEFAULT_OUT = REPO_ROOT / "runs" / "features"
DOC_PATH = Path(__file__).with_name("FEATURES.md")
HIST_COLUMNS = ID_COLUMNS + TARGET_COLUMNS + FEATURE_COLUMNS
CURRENT_COLUMNS = ["as_of_date", "supplier_id", "part_id"] + FEATURE_COLUMNS
SQL_TYPES = {"float": "REAL", "int": "INTEGER", "bool": "INTEGER", "category": "TEXT", "id": "TEXT", "date": "TEXT"}


def historical_rows(store: FeatureStore) -> list[dict]:
    """One row per renewal; features as of the day before the negotiation."""
    rows = []
    for r in store.renewals:
        as_of = r.date - timedelta(days=1)
        feats = build_feature_vector(r.supplier_id, r.part_id, as_of, {"asked_pct": r.asked_pct}, store=store)
        rows.append({
            "event_id": r.event_id,
            "negotiation_date": r.date.isoformat(),
            "as_of_date": as_of.isoformat(),
            "supplier_id": r.supplier_id,
            "part_id": r.part_id,
            "target_settled_pct": r.settled_pct,
            "target_concession_pp": round(r.asked_pct - r.settled_pct, 6),
            "target_settled_unit_price": store.condition_by_event[r.event_id]["price"],
            **feats,
        })
    return rows


def current_rows(store: FeatureStore, as_of: date = SNAPSHOT_DATE) -> list[dict]:
    pairs = sorted({(canonical_supplier(r["supplier_id"]), r["part_id"]) for r in store.tables["sourcing"]})
    return [{"as_of_date": as_of.isoformat(), "supplier_id": s, "part_id": p,
             **build_feature_vector(s, p, as_of, store=store)} for s, p in pairs]


def missing_report(rows: list[dict], columns: list[str]) -> list[dict]:
    n = len(rows)
    return [{"feature": c, "missing_pct": round(100 * sum(r[c] is None for r in rows) / n, 1) if n else None}
            for c in columns]


def _clean(v):
    return round(v, 6) if isinstance(v, float) else v


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columns)
        for r in rows:
            w.writerow(["" if r[c] is None else _clean(r[c]) for c in columns])


def write_sqlite(path: Path, tables: dict[str, tuple[list[str], list[dict]]]) -> None:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    try:
        for name, (columns, rows) in tables.items():
            decl = ", ".join(f'"{c}" {SQL_TYPES.get(BY_NAME[c].dtype, "TEXT") if c in BY_NAME else "TEXT"}'
                             for c in columns)
            con.execute(f'CREATE TABLE "{name}" ({decl})')
            con.executemany(f'INSERT INTO "{name}" VALUES ({", ".join("?" * len(columns))})',
                            [[_clean(r[c]) for c in columns] for r in rows])
        con.commit()
    finally:
        con.close()


def dictionary_rows() -> list[dict]:
    return [{"feature": f.name, "role": "id" if f in IDS else "target" if f in TARGETS else "feature",
             "dtype": f.dtype, "group": f.group, "source_table": f.source, "source_columns": f.columns,
             "join_keys": f.join, "formula": f.formula, "cutoff": f.cutoff, "missing": f.missing,
             "interpretation": f.meaning} for f in IDS + TARGETS + FEATURES]


DICT_COLUMNS = ["feature", "role", "dtype", "group", "source_table", "source_columns", "join_keys", "formula",
                "cutoff", "missing", "interpretation"]


def render_doc(hist_missing: dict[str, float], cur_missing: dict[str, float], n_hist: int, n_cur: int) -> str:
    def esc(s: str) -> str:
        return str(s).replace("|", "\\|")

    out = [DOC_HEADER.format(n_hist=n_hist, n_cur=n_cur, n_feat=len(FEATURES))]
    for title, items in (("Identifiers (never use as features)", IDS), ("Targets", TARGETS)):
        out.append(f"\n## {title}\n")
        out.append("| Name | Type | Source | Formula | Notes |\n|---|---|---|---|---|")
        out += [f"| `{f.name}` | {f.dtype} | `{esc(f.source)}`.{esc(f.columns)} | {esc(f.formula)} | {esc(f.meaning)} |"
                for f in items]
    groups: dict[str, list] = {}
    for f in FEATURES:
        groups.setdefault(f.group, []).append(f)
    out.append("\n## Features\n")
    for g, items in groups.items():
        out.append(f"\n### {g}\n")
        for f in items:
            out.append(f"#### `{f.name}`\n")
            out.append(f"- **Type:** {f.dtype}\n- **Source:** `{f.source}` - columns: {f.columns}"
                       f"\n- **Join keys:** {f.join}\n- **Calculation:** {f.formula}\n- **Cutoff:** {f.cutoff}"
                       f"\n- **Missing values:** {f.missing}"
                       f" (missing in training: {hist_missing.get(f.name, 0)} %,"
                       f" current: {cur_missing.get(f.name, 0)} %)"
                       f"\n- **Interpretation:** {f.meaning}\n")
    return "\n".join(out)


DOC_HEADER = """# Feature data dictionary

Generated by `python -m buyer.facts.features.build` from `spec.py` - edit `spec.py`, not this file.
Owner: SCOUT (`src/buyer/facts/features/`).

## Datasets

| Dataset | Rows | Grain |
|---|---|---|
| `historical_negotiation_features` | {n_hist} | one past renewal (asked and settled change known) |
| `current_supplier_features` | {n_cur} | one source-list supplier-part pair as of 2026-09-30 |

{n_feat} features; columns are identifiers, then targets (training only), then features.

## How to use

```bash
# rebuild everything (reads data/world.sqlite read-only, writes runs/features/ and this file)
PYTHONPATH=src uv run --no-project --python 3.12 python -m buyer.facts.features.build
PYTHONPATH=src uv run --no-project --python 3.12 --with pytest python -m pytest src/buyer/facts/features/tests
```

```python
import pandas as pd
from buyer.facts.features import FEATURE_COLUMNS, TARGET_COLUMNS, CATEGORICAL, build_feature_vector

df = pd.read_csv("runs/features/historical_negotiation_features.csv", parse_dates=["negotiation_date"])
X, y = df[FEATURE_COLUMNS], df["target_concession_pp"]       # ids and targets stay out of X
X = X.astype({{c: "category" for c in CATEGORICAL}})
# split by time (negotiation_date), never randomly: the rows are a time series

# live: one vector for a case, also for a supplier never seen before
v = build_feature_vector(None, "part:310010", "2026-09-30",
                         {{"supplier_country": "PL", "asked_pct": 6.0}})
```

The same tables are in `runs/features/negotiation_features.sqlite`, with `feature_dictionary`
(this document as a table) and `missing_report`.

## Rules that hold for every feature

- **Cutoff.** A row "as of D" uses only what was known at the end of day D. A training row for a
  negotiation on day N is built as of **N - 1 day**: its own outcome, its own note and anything dated
  N or later never enter its features (tested by rebuilding features on a database truncated at D).
- **Snapshot data** (supplier_intel, should_cost, sourcing status) exists only as of 2026-09-30 and is
  used only from the date it became true: should-cost from 2026-07-15, filed accounts from 31 Dec of
  the year after the fiscal year, credit index values from the dates they were measured. Sourcing
  status is never used; competition is rebuilt from PO lines.
- **Prices** are per the part's `price_unit` (1, 100 or 1,000 pieces, kg or m), as in the cases.
  `previous_price_per_uom` divides by it. PO values are `qty x price / price_unit`.
- **Unknown suppliers** (`supplier_id` None or not in the vendor master) get `is_known_supplier = 0`,
  supplier-level features null, history from category / global aggregates (`hist_level`), and
  part-level features (forecast, competition, part reference price, should-cost of another plant).
- **Nulls mean unknown, never zero.** Zero means "known to be zero". Indicators: `is_known_supplier`,
  `hist_level`, `hist_level_count`, `hist_is_fallback`, `po_window_complete`, `has_financials`,
  `has_should_cost`, `has_scorecard`.
- **Identifiers** (`event_id`, dates, `supplier_id`, `part_id`) are for tracking and joins only.

## Targets are not the supplier's floor

`target_settled_pct` is what Hollerau agreed, not the lowest the supplier would have accepted. A
settlement is an upper bound on the supplier's walk-away price; the concession is a lower bound on
what it could have given. 5 of the 75 supplier-part pairs carry the note "accepted below full cost to
keep the volume": some settlements sit below the supplier's own cost and say little about its floor.

## Limitations (not reconstructible historically)

- `has_financials = 0`, `has_should_cost = 0` for all 225 training rows; `credit_index` only for the 75
  renewals of Nov-Dec 2025 (`credit_index_change` for none). A model trained on history cannot learn
  from these; use them at run time as rules or priors, or train on the current snapshot.
- Scorecards start at 2024Q3: the 2023 renewals have none. PO, QN and invoice data start 2023-10: the
  2023 renewals (`po_window_complete = 0`) have no 12-month sums.
- Cost-driver weights are an estimate of 2026-06, used for every date (part property).
- `approved_supplier_count` assumes no supplier was removed from the source list.
- `supplier_age_years`, `owner_type`, `group_parent` are assumed constant over time.
"""


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=None, help="source database (read-only); default data/world.sqlite")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--as-of", default=SNAPSHOT_DATE.isoformat(), help="date of the current feature dataset")
    args = ap.parse_args(argv)

    store = FeatureStore.from_sqlite(args.db) if args.db else FeatureStore.from_sqlite()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    hist = historical_rows(store)
    cur = current_rows(store, date.fromisoformat(args.as_of))
    hist_missing = missing_report(hist, HIST_COLUMNS)
    cur_missing = missing_report(cur, CURRENT_COLUMNS)

    write_csv(out / "historical_negotiation_features.csv", hist, HIST_COLUMNS)
    write_csv(out / "current_supplier_features.csv", cur, CURRENT_COLUMNS)
    report = [{"dataset": "historical", **m} for m in hist_missing] + [{"dataset": "current", **m} for m in cur_missing]
    write_sqlite(out / "negotiation_features.sqlite", {
        "historical_negotiation_features": (HIST_COLUMNS, hist),
        "current_supplier_features": (CURRENT_COLUMNS, cur),
        "feature_dictionary": (DICT_COLUMNS, dictionary_rows()),
        "missing_report": (["dataset", "feature", "missing_pct"], report),
    })
    DOC_PATH.write_text(render_doc({m["feature"]: m["missing_pct"] for m in hist_missing},
                                   {m["feature"]: m["missing_pct"] for m in cur_missing}, len(hist), len(cur)),
                        encoding="utf-8")
    print(f"historical: {len(hist)} rows x {len(HIST_COLUMNS)} columns ({len(FEATURE_COLUMNS)} features)")
    print(f"current:    {len(cur)} rows x {len(CURRENT_COLUMNS)} columns")
    print(f"written to {out} and {DOC_PATH}")


if __name__ == "__main__":
    main()
