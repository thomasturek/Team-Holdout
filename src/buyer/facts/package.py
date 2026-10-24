"""The one front door to the data (SCOUT).

Three sources, checked in this order:
    1. ``case["facts"]``   facts that exist only in this case (hidden cases)
    2. Sunday release      ``<data>/release-sunday/`` once ``arena data`` has fetched it (new IDs only)
    3. data package v1     ``facts.json`` + ``world.sqlite`` + contract and correspondence texts

``citable(id)`` is the guardrail: only IDs in a facts.json (package, release) or in the case's facts
may be sent to a supplier. Table rows such as ``inv:`` or ``gr:`` can be looked up but not cited.

    from buyer.facts.package import CaseData
    data = CaseData(case)
    data.lookup("sc:70110@2026Q3")      # -> {"supplier": ..., "otd_pct": ..., "ppm": ...}
    data.citable("idx:PPI-C2451@2026-08")
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from arena_kit.data import DataPackage

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA = REPO_ROOT / "data"

_lock = threading.Lock()
_cache: dict[tuple[str, str | None], DataPackage] = {}
_release_ids: dict[int, frozenset[str]] = {}


def data_root(root: str | Path | None = None) -> Path:
    """``root``, else ARENA_DATA, else the repo's ``data/``. A relative path that does not exist
    from the working directory is taken relative to the repo root."""
    path = Path(root or os.environ.get("ARENA_DATA") or DEFAULT_DATA).expanduser()
    if not path.is_absolute() and not path.exists():
        path = REPO_ROOT / path
    return path.resolve()


def load_package(root: str | Path | None = None, release: str | Path | None = None,
                 refresh: bool = False) -> DataPackage:
    """The shared, read-only DataPackage for this process, loaded once (about a second) and cached.

    ``refresh=True`` reloads it, e.g. after downloading the Sunday release while running.
    """
    key = (str(data_root(root)), str(release) if release else None)
    with _lock:
        if refresh or key not in _cache:
            pkg = DataPackage(key[0], release=release)
            pkg.lookup("sup:__warm__")      # build the table ID index now, not inside a live round
            _release_ids[id(pkg)] = frozenset(
                json.loads((pkg.release / "facts.json").read_text(encoding="utf-8"))) if pkg.release else frozenset()
            _cache[key] = pkg
        return _cache[key]


class CaseData:
    """Data view for one case: the case's own facts in front of the shared package."""

    def __init__(self, case: dict | None = None, package: DataPackage | None = None):
        self.case = case or {}
        self.case_facts: dict = dict(self.case.get("facts") or {})
        self.package = package or load_package()

    # -------------------------------------------------------------- facts

    def lookup(self, ref: str) -> dict | None:
        """The fact behind an ID: case facts, then release + package facts.json, then the table row."""
        if ref in self.case_facts:
            return self.case_facts[ref]
        return self.package.lookup(ref)

    def citable(self, ref: str) -> bool:
        """True if the arena knows this ID: it is in the case's facts or in a facts.json."""
        return ref in self.case_facts or ref in self.package.facts

    def source(self, ref: str) -> str | None:
        """Where an ID comes from: 'case' | 'release' | 'package' (citable) | 'table' (lookup only) | None."""
        if ref in self.case_facts:
            return "case"
        if ref in _release_ids.get(id(self.package), ()):
            return "release"
        if ref in self.package.facts:
            return "package"
        return "table" if self.package.lookup(ref) is not None else None

    def require(self, ref: str) -> dict:
        """Like lookup, but raises KeyError for an ID that is not citable."""
        if not self.citable(ref):
            raise KeyError(f"not a citable ID: {ref}")
        return self.lookup(ref)

    def ids(self, prefix: str) -> list[str]:
        """All IDs starting with ``prefix`` (case facts included), sorted."""
        return sorted(set(self.package.ids(prefix)) | {i for i in self.case_facts if i.startswith(prefix)})

    # -------------------------------------------------------------- texts and tables

    def document(self, ref: str) -> str:
        """Text of a letter, note, contract or news item by ID (case facts first)."""
        fact = self.case_facts.get(ref)
        if fact:
            for col in ("body", "text", "content"):
                if fact.get(col):
                    return fact[col]
        return self.package.document(ref)

    def query(self, sql: str, params=(), limit: int = 200) -> list[dict]:
        """Read-only SQL over world.sqlite (SELECT / WITH only)."""
        return self.package.query(sql, params, limit)

    @property
    def has_release(self) -> bool:
        return self.package.release is not None


def lookup(ref: str, case: dict | None = None) -> dict | None:
    """Module-level shortcut: ``lookup("sup:70110")`` or ``lookup(ref, case)``."""
    return CaseData(case).lookup(ref)
