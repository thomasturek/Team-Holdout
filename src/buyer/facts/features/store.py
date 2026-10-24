"""In-memory, read-only view of the procurement database used by the feature extractors.

The database (``data/world.sqlite``) is opened read-only and every table needed for features is
loaded once into plain dicts with lookup indices. The store can also be built from a dict of
tables, which the tests use to build point-in-time truncated copies.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DB = REPO_ROOT / "data" / "world.sqlite"

# The whole data package is a snapshot taken at this date (data/README.md).
SNAPSHOT_DATE = date(2026, 9, 30)

# KNOWN_ISSUES.md #5: old vendor record -> current record.
SUPPLIER_ALIASES = {"sup:71999": "sup:70210"}

# Annual accounts become public at the latest 12 months after the fiscal year end (HGB par. 325).
FILING_LAG_MONTHS = 12

TABLES = (
    "parts",
    "suppliers",
    "supplier_intel",
    "sourcing",
    "negotiation_history",
    "price_conditions",
    "po_lines",
    "forecasts",
    "invoices",
    "quality_notifications",
    "scorecards",
    "should_cost",
    "cost_drivers",
    "index_series",
    "index_values",
)


def to_date(value: str | date | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


def month_index(value: str | date) -> int:
    """'2026-09' or a date -> y*12 + (m-1), so months can be subtracted."""
    if isinstance(value, date):
        return value.year * 12 + value.month - 1
    y, m = value[:7].split("-")
    return int(y) * 12 + int(m) - 1


def last_complete_month(as_of: date) -> int:
    """Month index of the last month that has ended by the end of ``as_of``."""
    return month_index(as_of + timedelta(days=1)) - 1


def canonical_supplier(supplier_id: str | None) -> str | None:
    if supplier_id is None:
        return None
    return SUPPLIER_ALIASES.get(supplier_id, supplier_id)


@dataclass(frozen=True)
class Renewal:
    """One negotiation_history row with both asked and settled change."""

    event_id: str
    date: date
    supplier_id: str
    part_id: str
    asked_pct: float
    settled_pct: float

    @property
    def concession_pp(self) -> float:
        return self.asked_pct - self.settled_pct


class FeatureStore:
    def __init__(self, tables: dict[str, list[dict]]):
        self.tables = tables
        t = tables
        self.parts = {r["id"]: r for r in t["parts"]}
        self.suppliers = {r["id"]: r for r in t["suppliers"]}
        self.intel = {r["supplier_id"]: r for r in t["supplier_intel"]}

        self.sourcing_by_part = _group(t["sourcing"], "part_id")

        self.events = sorted(
            ({**r, "supplier_id": canonical_supplier(r["supplier_id"]), "_date": to_date(r["date"])}
             for r in t["negotiation_history"]),
            key=lambda r: (r["_date"], r["event_id"]),
        )
        self.renewals = [
            Renewal(r["event_id"], r["_date"], r["supplier_id"], r["part_id"], r["asked_pct"], r["settled_pct"])
            for r in self.events
            if r["asked_pct"] is not None and r["settled_pct"] is not None
        ]

        conds = sorted(t["price_conditions"], key=lambda r: r["valid_from"])
        self.conditions_by_pair = _group(conds, "supplier_id", "part_id")
        self.conditions_by_part = _group(conds, "part_id")
        self.condition_by_event = {r["event_id"]: r for r in conds}

        self.po_by_pair = _group(t["po_lines"], "supplier_id", "part_id")
        self.po_by_part = _group(t["po_lines"], "part_id")
        dates = [r["order_date"] for r in t["po_lines"]]
        # Transaction tables (PO lines, receipts, invoices, QNs) start at the first PO order date.
        self.activity_start = to_date(min(dates)) if dates else SNAPSHOT_DATE

        self.forecasts_by_part = _group(sorted(t["forecasts"], key=lambda r: r["snapshot_month"]), "part_id")
        self.invoices_by_supplier = _group(t["invoices"], "supplier_id")
        self.qn_by_supplier = _group(t["quality_notifications"], "supplier_id")
        self.scorecards_by_supplier = _group(sorted(t["scorecards"], key=lambda r: r["period_end"]), "supplier_id")
        self.should_cost_by_part = _group(t["should_cost"], "part_id")
        self.cost_drivers_by_part = _group(t["cost_drivers"], "part_id")

        self.index_values: dict[str, dict[int, float]] = defaultdict(dict)
        for r in t["index_values"]:
            self.index_values[r["series_id"]][month_index(r["month"])] = r["value"]
        # Publication lag per series, as observed at the snapshot (KNOWN_ISSUES.md #12).
        self.index_lag = {
            r["id"]: max(0, month_index(SNAPSHOT_DATE) - month_index(r["last_month"])) for r in t["index_series"]
        }

    @classmethod
    def from_sqlite(cls, path: str | Path = DEFAULT_DB) -> FeatureStore:
        uri = f"file:{Path(path).as_posix()}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        con.row_factory = sqlite3.Row
        try:
            tables = {name: [dict(r) for r in con.execute(f"SELECT * FROM {name}")] for name in TABLES}
        finally:
            con.close()
        return cls(tables)

    def is_known_supplier(self, supplier_id: str | None) -> bool:
        return supplier_id is not None and supplier_id in self.suppliers


def _group(rows, *keys) -> dict:
    out: dict = defaultdict(list)
    for r in rows:
        k = tuple(canonical_supplier(r[c]) if c == "supplier_id" else r[c] for c in keys)
        out[k[0] if len(k) == 1 else k].append(r)
    return out


_DEFAULT_STORE: FeatureStore | None = None


def default_store() -> FeatureStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = FeatureStore.from_sqlite(DEFAULT_DB)
    return _DEFAULT_STORE
