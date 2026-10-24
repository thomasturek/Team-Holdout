"""The claim bank (SCOUT): sentences with data IDs that the arena checks as ``verified``.

    from buyer.facts.claims import claims, check
    bank = claims(case)                       # every claim for every supplier of the case
    bank = claims(case, "sup:70110")          # only those that are about this supplier
    check(case, "sup:70110", bank[0].sentence)   # -> "verified" (our own copy of the arena's rules)

Kinds (``Claim.key``):
    index:<series>                  12-month change of a cost driver of the part (any supplier)
    notice:<supplier>               the price letter gives less notice than the contract requires
    otd:<supplier> / ppm:<supplier> latest rolling scorecard: on-time delivery / defect rate
    po:<supplier>:<part>            our order prices with this supplier: stable or falling
    po_rival:<supplier>:<part>:<rival>  what we pay another source for the same part (below this supplier)

Rules (brief/api.md "What counts"): each ID counts once per case - across suppliers too, so an
index claim or a PO line cited to one bidder is spent for the others - and at most 3 checked claims
per message. Claims that share a ref are alternatives: pass every ID already cited in the case as
``used`` to ``compatible()`` and it returns a set the arena will not mark ``duplicate``. Each
sentence is one line and carries its own figure; the Diplomat pastes it verbatim.
``Claim.strength`` is a prior only (how much the fact speaks for us); the Analyst chooses.
"""

from __future__ import annotations

import re
import threading
from collections import defaultdict
from datetime import date

from buyer.interfaces import Claim

from .package import CaseData

PCT_TOL = 0.5           # percentage points
REL_TOL = 0.005         # 0.5 % of the value, at least 0.01
PO_LOOKBACK_DAYS = 730  # order history worth citing
MAX_PO = 4

ID_RE = re.compile(r"\b(?:idx|quote|offer|sc|qn|po|fc|cost|news|doc|ctr):[\w.:@#/-]*\w")
NUM = r"[-+−]?\d+(?:[.,]\d+)?"

# Series names in words, without digits that could be read as the figure.
SERIES_WORDS = {
    "AS-14301": "The alloy surcharge for stainless grade 304",
    "AS-14404": "The alloy surcharge for stainless grade 316L",
    "CU-NOTATION": "The copper notation",
    "LCI-C": "German labour costs in manufacturing",
    "PPI-C2219": "German producer prices for rubber products",
    "PPI-C241": "German producer prices for basic iron and steel",
    "PPI-C2431": "German producer prices for cold-drawn bars",
    "PPI-C2451": "German producer prices for iron castings",
    "PPI-C2452": "German producer prices for steel castings",
    "PPI-C2594": "German producer prices for fasteners",
    "PPI-C2611": "German producer prices for electronic components",
    "PPI-C2815": "German producer prices for bearings and gears",
    "PPI-D351": "German electricity producer prices",
}


# ------------------------------------------------------------------ indices over the facts


class _Index:
    """facts.json grouped the way the claim builders need it. Built once per package."""

    def __init__(self, facts: dict):
        self.series: dict[str, dict[str, tuple[str, float]]] = defaultdict(dict)  # series -> month -> (id, value)
        self.po: dict[tuple[str, str], list[tuple[str, dict]]] = defaultdict(list)  # (supplier, part) -> [(id, row)]
        self.po_part: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        self.sc: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        self.letters: dict[str, list[tuple[str, dict]]] = defaultdict(list)  # docs with notice days
        self.contracts: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        self.add(facts)

    def add(self, facts: dict):
        for ref, f in facts.items():
            kind = ref.split(":", 1)[0]
            if kind == "idx":
                self.series[f["series"]][f["month"]] = (ref, f["value"])
            elif kind == "po":
                self.po[(f["supplier"], f["part"])].append((ref, f))
                self.po_part[f["part"]].append((ref, f))
            elif kind == "sc":
                self.sc[f["supplier"]].append((ref, f))
            elif kind == "doc" and f.get("days") is not None:
                self.letters[f["supplier"]].append((ref, f))
            elif kind == "ctr" and "#" not in ref and f.get("days") is not None:
                self.contracts[f["supplier"]].append((ref, f))

    @property
    def last_month(self) -> str:
        return max(m for months in self.series.values() for m in months)


_lock = threading.Lock()
_indices: dict[int, _Index] = {}


def _index(data: CaseData) -> _Index:
    key = id(data.package)
    with _lock:
        if key not in _indices:
            _indices[key] = _Index(data.package.facts)
    if not data.case_facts:
        return _indices[key]
    idx = _Index({})  # case facts on top: copy the shared index shallowly, then add
    for name in ("series", "po", "po_part", "sc", "letters", "contracts"):
        shared = getattr(_indices[key], name)
        getattr(idx, name).update({k: (dict(v) if isinstance(v, dict) else list(v)) for k, v in shared.items()})
    idx.add(data.case_facts)
    return idx


# ------------------------------------------------------------------ helpers


def _months_between(a: str, b: str) -> int:
    ya, ma = map(int, a.split("-"))
    yb, mb = map(int, b.split("-"))
    return (yb - ya) * 12 + (mb - ma)


def _shift(month: str, n: int) -> str:
    y, m = map(int, month.split("-"))
    y, m = divmod(y * 12 + m - 1 + n, 12)
    return f"{y:04d}-{m + 1:02d}"


def _pct_ok(stated: float, actual: float) -> bool:
    return abs(stated - actual) <= PCT_TOL


def _rel_ok(stated: float, actual: float) -> bool:
    return abs(stated - actual) <= max(0.01, abs(actual) * REL_TOL)


def _num(s: str) -> float:
    return float(s.replace("−", "-").replace(",", "."))


def _eur(value: float, price_unit) -> str:
    unit = f" per {int(price_unit):,} units" if price_unit and price_unit != 1 else ""
    return f"EUR {value:.2f}{unit}"


def _long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B')} {d.year}"


AS_OF = date(2026, 9, 30)  # the data's 'today' (snapshot date of the package)


def _drivers(data: CaseData, parts: list[str]) -> dict[str, float]:
    """series -> highest weight among the case's parts."""
    out: dict[str, float] = {}
    for part in parts:
        for r in data.query("SELECT series_id, weight FROM cost_drivers WHERE part_id = ?", (part,)):
            out[r["series_id"]] = max(out.get(r["series_id"], 0.0), r["weight"] or 0.0)
    return out


def _series_words(data: CaseData, series: str) -> str:
    if series in SERIES_WORDS:
        return SERIES_WORDS[series]
    rows = data.query("SELECT name FROM index_series WHERE id = ?", (series,))
    name = re.split(r"\s*[(,]", rows[0]["name"])[0] if rows else series
    return re.sub(r"\s*\d[\d.]*", "", name).strip() or series


def _part_words(data: CaseData, part: str) -> str:
    rows = data.query("SELECT description FROM parts WHERE id = ?", (part,))
    return rows[0]["description"] if rows else part


def _asked_pct(data: CaseData) -> float | None:
    doc = data.case.get("trigger_doc")
    fact = data.lookup(doc) if doc else None
    return (fact or {}).get("asked_pct")


# ------------------------------------------------------------------ builders


def index_claims(data: CaseData, idx: _Index) -> list[Claim]:
    """One claim per cost-driver series: the 12-month change ending at the series' latest month."""
    out = []
    asked = _asked_pct(data)
    for series, weight in sorted(_drivers(data, data.case.get("parts") or []).items(), key=lambda x: -x[1]):
        months = idx.series.get(series)
        if not months:
            continue
        end = max(months)
        start = _shift(end, -12)
        if start not in months or _months_between(end, idx.last_month) >= 12:
            continue
        (id0, v0), (id1, v1) = months[start], months[end]
        change = (v1 / v0 - 1) * 100
        sentence = f"{_series_words(data, series)} changed {change:+.1f}% from {start} to {end} ({id0}, {id1})."
        bar = asked if asked else 5.0  # a change well below what is asked speaks for us
        strength = min(1.0, 2 * weight) * max(0.0, min(1.0, (bar - change) / bar))
        out.append(Claim(f"index:{series}", sentence, [id0, id1], "verified", round(strength, 3)))
    return out


def notice_claims(data: CaseData, idx: _Index, sid: str) -> list[Claim]:
    """A price letter that gives less notice than the supplier's contract requires."""
    trigger = data.case.get("trigger_doc")
    # only this case's letter: its trigger document, or a letter among the case's own facts
    letters = [x for x in idx.letters.get(sid, []) if x[0] == trigger or x[0] in data.case_facts]
    contracts = idx.contracts.get(sid, [])
    out = []
    for doc_id, doc in letters:
        valid = [c for c in contracts if (c[1].get("valid_from") or "") <= (doc.get("date") or "9999")
                 <= (c[1].get("valid_to") or "9999")] or contracts
        for ctr_id, ctr in valid[:1]:
            if doc["days"] < ctr["days"]:
                when = f" of {_long_date(doc['date'])}" if doc.get("date") else ""
                sentence = (f"Your letter{when} ({doc_id}) gives {doc['days']} days' notice, "
                            f"while our contract ({ctr_id}) requires {ctr['days']} days.")
                strength = min(1.0, 0.6 + (ctr["days"] - doc["days"]) / 100)
                out.append(Claim(f"notice:{sid}", sentence, [doc_id, ctr_id], "verified", round(strength, 3)))
    return out


def scorecard_claims(data: CaseData, idx: _Index, sid: str) -> list[Claim]:
    """Latest rolling scorecard: on-time delivery and defect rate. Same ref: use one of the two."""
    rows = sorted(idx.sc.get(sid, []), key=lambda x: x[1].get("quarter") or "")
    if not rows:
        return []
    sc_id, sc = rows[-1]
    q = sc.get("quarter") or ""
    out = []
    if sc.get("otd_pct") is not None:
        otd = sc["otd_pct"]
        sentence = f"Your on-time delivery was {otd:.1f}% in the four quarters to {q} ({sc_id})."
        out.append(Claim(f"otd:{sid}", sentence, [sc_id], "verified", round(max(0.0, min(1.0, (95 - otd) / 20)), 3)))
    if sc.get("ppm") is not None:
        ppm = sc["ppm"]
        sentence = f"Your quality was {ppm:g} ppm defective parts in the four quarters to {q} ({sc_id})."
        out.append(Claim(f"ppm:{sid}", sentence, [sc_id], "verified", round(max(0.0, min(1.0, ppm / 1000)), 3)))
    return out


def _recent(rows, as_of: date):
    return sorted((r for r in rows if r[1].get("date") and (as_of - date.fromisoformat(r[1]["date"])).days
                   <= PO_LOOKBACK_DAYS), key=lambda r: r[1]["date"])


def _spread(rows, n: int):
    """Up to n rows spread over the period, first and last included."""
    if len(rows) <= n:
        return rows
    step = (len(rows) - 1) / (n - 1)
    return [rows[round(i * step)] for i in range(n)]


def _po_sentence(lines) -> str:
    parts = [f"{_eur(f['unit_price'], f.get('price_unit'))} on {f['date']} ({ref})" for ref, f in lines]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def po_claims(data: CaseData, idx: _Index, sid: str) -> list[Claim]:
    """Our order prices with this supplier (stable or falling) and with other sources (cheaper)."""
    as_of = AS_OF
    out = []
    for part in data.case.get("parts") or []:
        words = _part_words(data, part)
        own = _recent(idx.po.get((sid, part), []), as_of)
        if len(own) >= 2:  # 2-8 lines of one part, spread over the period
            lines = _spread(own, MAX_PO)
            first, last = lines[0][1]["unit_price"], lines[-1][1]["unit_price"]
            if last <= first:
                flat = len({f["unit_price"] for _, f in lines}) == 1
                trend = "has been unchanged" if flat else "has not risen"
                sentence = f"Our orders of {words} with you were placed at {_po_sentence(lines)}: the price {trend}."
                strength = 0.5 if flat else 0.5 + min(0.3, (first - last) / first * 10)
                out.append(Claim(f"po:{sid}:{part}", sentence, [r for r, _ in lines], "verified", strength))
        current = own[-1][1]["unit_price"] if own else None
        rivals = [r for r in _recent(idx.po_part.get(part, []), as_of) if r[1]["supplier"] != sid]
        by_sup = defaultdict(list)
        for r in rivals:
            by_sup[r[1]["supplier"]].append(r)
        for rival, rows in sorted(by_sup.items()):
            lines = _spread(rows, 2) if len(rows) >= 2 else []
            if not lines:
                continue
            price = lines[-1][1]["unit_price"]
            if current is not None and price >= current:
                continue
            sentence = f"We also buy {words} from another source, at {_po_sentence(lines)}."
            gap = (current - price) / current if current else 0.05
            out.append(Claim(f"po_rival:{sid}:{part}:{rival}", sentence, [r for r, _ in lines], "verified",
                             round(min(1.0, 0.3 + 5 * gap), 3)))
    return out


# ------------------------------------------------------------------ public API


def claims(case: dict, supplier_id: str | None = None, data: CaseData | None = None) -> list[Claim]:
    """Every claim of the case that checks as ``verified`` (strongest first), for one supplier or
    for all of them. Claims that our own checker does not verify are dropped, never returned."""
    data = data or CaseData(case)
    idx = _index(data)
    suppliers = [supplier_id] if supplier_id else list(case.get("suppliers") or [])
    shared = index_claims(data, idx)
    out = []
    for sid in suppliers:
        bank = shared + notice_claims(data, idx, sid) + scorecard_claims(data, idx, sid) + po_claims(data, idx, sid)
        out += [c for c in bank if check(case, sid, c.sentence, data=data) == "verified"]
    unique = list({c.key: c for c in out}.values())  # index claims appear once
    return sorted(unique, key=lambda c: -c.strength)


def compatible(bank: list[Claim], used: set[str] = frozenset(), limit: int = 3) -> list[Claim]:
    """Up to ``limit`` claims in order that share no ref with each other or with ``used`` (IDs
    already cited in this case) - a message the arena will not mark ``duplicate``."""
    out, seen = [], set(used)
    for c in bank:
        if seen.isdisjoint(c.refs):
            out.append(c)
            seen |= set(c.refs)
            if len(out) == limit:
                break
    return out


def check(case: dict, supplier_id: str, sentence: str, used: set[str] = frozenset(),
          data: CaseData | None = None) -> str:
    """Our copy of the arena's check for one sentence: verified | irrelevant | contradicted |
    duplicate. Stricter than the arena where the brief is vague (we would rather drop a claim)."""
    data = data or CaseData(case)
    ids = ID_RE.findall(sentence)
    if not ids:
        return "irrelevant"
    if any(not data.citable(i) for i in ids):
        return "contradicted"
    if any(i in used for i in ids):
        return "duplicate"
    facts = {i: data.lookup(i) for i in ids}
    kinds = {i.split(":", 1)[0] for i in ids}
    parts = set(case.get("parts") or [])

    if kinds == {"idx"}:
        if len(ids) != 2:
            return "irrelevant"
        a, b = sorted((facts[i] for i in ids), key=lambda f: f["month"])
        if a["series"] != b["series"]:
            return "irrelevant"
        last = _index(data).last_month
        if _months_between(a["month"], b["month"]) > 12 or _months_between(b["month"], last) >= 12:
            return "irrelevant"
        if a["series"] not in _drivers(data, list(parts)):
            return "irrelevant"
        stated = re.findall(rf"({NUM})\s*%", sentence)
        change = (b["value"] / a["value"] - 1) * 100
        return "verified" if stated and all(_pct_ok(_num(s), change) for s in stated) else "contradicted"

    if kinds == {"sc"}:
        rows = list(facts.values())
        if any(f["supplier"] != supplier_id for f in rows):
            return "irrelevant"
        if re.search(r"ppm|quality|defect", sentence, re.I):
            stated = re.findall(rf"({NUM})\s*ppm", sentence)
            mean = sum(f["ppm"] for f in rows) / len(rows)
            return "verified" if stated and all(_rel_ok(_num(s), mean) for s in stated) else "contradicted"
        stated = re.findall(rf"({NUM})\s*%", sentence)
        mean = sum(f["otd_pct"] for f in rows) / len(rows)
        return "verified" if stated and all(_pct_ok(_num(s), mean) for s in stated) else "contradicted"

    if kinds == {"po"}:
        rows = list(facts.values())
        if not 2 <= len(rows) <= 8 or len({f["part"] for f in rows}) != 1:
            return "irrelevant"
        if rows[0]["part"] not in parts:
            return "irrelevant"
        stated = re.findall(rf"EUR\s*({NUM})", sentence)
        prices = [f["unit_price"] for f in rows]
        ok = len(stated) == len(prices) and all(any(_rel_ok(_num(s), p) for p in prices) for s in stated)
        return "verified" if ok else "contradicted"

    if kinds == {"doc", "ctr"} and len(ids) == 2:
        doc = next(facts[i] for i in ids if i.startswith("doc:"))
        ctr = next(facts[i] for i in ids if i.startswith("ctr:"))
        if doc.get("supplier") != supplier_id or ctr.get("supplier") != supplier_id:
            return "irrelevant"
        if doc.get("days") is None or ctr.get("days") is None:
            return "irrelevant"
        stated = sorted(int(_num(s)) for s in re.findall(rf"({NUM})\s*days", sentence))
        return "verified" if stated == sorted([doc["days"], ctr["days"]]) else "contradicted"

    return "irrelevant"  # a kind we do not build (yet): never claim it
