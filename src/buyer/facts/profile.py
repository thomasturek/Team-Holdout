"""Supplier profiles (SCOUT): who each supplier is, how far it can go, what moves it.

    from buyer.facts.profile import profile, profile_all
    profile(case)     # -> {supplier_id: profile dict} for the case's suppliers (first part; bundles
                      #    also get floor_by_part)
    profile_all()     # every detailed supplier x every part it supplies or quoted -> runs/profiles/all.json

The final only brings the 46 detailed suppliers of the package, so every profile is computed ahead:
``profile_all()`` writes them once, ``profile(case)`` reads that file and computes only what is
missing. Hand corrections live in ``overrides.json`` next to this file and are applied last, on
every read - edit it, no rebuild needed.

A profile carries the SupplierProfile fields (src/buyer/interfaces.py) as a dict, plus the reasons
behind its estimates (floor_source, cash_reasons, overrides).

Floor: the part's should-cost (supplier-specific, else the cheapest estimate x country factor);
without one, the market price (this supplier's latest price, else the lowest current price of any
source, else the part's standard price) x the cost-to-price ratio measured on the parts that have
both, by category - never above that price. Archetype: rules over supplier_intel, sourcing, news
and our payment record, corrected by hand in overrides.json.
"""

import json
import re
import sqlite3
import statistics
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

from .features import build_feature_vector
from .features.store import DEFAULT_DB

AS_OF = "2026-09-30"
COUNTRY_FACTOR = {"DE": 1.0, "AT": 1.05, "CH": 1.05, "CZ": 0.82, "PL": 0.82, "HU": 0.82, "TR": 0.75, "CN": 0.7}
BASE_RATE = 0.08
MARKET_CONFIDENCE = 0.15          # floor from a price, not a cost estimate
CASH_NEWS = {"credit_watch": 0.35, "credit_downgrade": 0.35, "short_time_work": 0.3, "restructuring": 0.3}
CAPACITY_NEWS = {"allocation", "full_order_book", "chip_shortage"}
BIG_TURNOVER = 50e6
NOTE_CHARS = 220
META_RE = re.compile(r"^[\w ]+ - \d{4}-\d{2}-\d{2} - ")

REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILES_FILE = REPO_ROOT / "runs" / "profiles" / "all.json"
OVERRIDES_FILE = Path(__file__).with_name("overrides.json")


def _rows(sql, params=()):
    con = sqlite3.connect(f"file:{DEFAULT_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, params)]
    finally:
        con.close()


# ------------------------------------------------------------------ cached tables


@lru_cache(maxsize=1)
def _skonto():
    rows = _rows("SELECT id, payment_days, skonto_days, skonto_pct FROM suppliers WHERE skonto_pct > 0")
    return {r["id"]: (r["payment_days"], r["skonto_days"], r["skonto_pct"]) for r in rows}


@lru_cache(maxsize=1)
def _suppliers():
    return {r["id"]: r for r in _rows("SELECT id, name, country, category, payment_days, incoterm, "
                                      "standard_lead_time_days FROM suppliers")}


@lru_cache(maxsize=1)
def _news():
    out = {}
    for r in _rows("SELECT id, date, supplier_id, topic, headline FROM news "
                   "WHERE supplier_id IS NOT NULL ORDER BY date"):
        out.setdefault(r["supplier_id"], []).append(r)
    return out


@lru_cache(maxsize=1)
def _overdue_letters():
    """Suppliers that wrote to us about overdue invoices in the last 12 months: {supplier: [doc ids]}."""
    out = {}
    for r in _rows("SELECT id, supplier_id FROM documents "
                   "WHERE subject LIKE 'Overdue invoice%' AND date > date(?, '-12 months')", (AS_OF,)):
        out.setdefault(r["supplier_id"], []).append(r["id"])
    return out


@lru_cache(maxsize=1)
def _meeting_notes():
    """Meeting and call notes, e-mails and letters about a supplier from the last 12 months (the
    ``-M`` documents; ``-N`` are boilerplate, ``-P`` belong to cases): {supplier: [note]}."""
    out = {}
    root = DEFAULT_DB.parent
    for r in _rows("SELECT id, date, supplier_id, subject, file FROM documents "
                   "WHERE id LIKE '%-M_' AND date > date(?, '-12 months') ORDER BY date", (AS_OF,)):
        try:
            lines = (root / r["file"]).read_text(encoding="utf-8").splitlines()
        except (OSError, TypeError):
            continue
        # "# Subject", "<kind> - <date> - <author>", then the text
        body = " ".join(ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")
                        and not META_RE.match(ln.strip()))
        text = body if len(body) <= NOTE_CHARS else body[:NOTE_CHARS].rsplit(" ", 1)[0] + " ..."
        out.setdefault(r["supplier_id"], []).append(f"{r['date']} {r['subject']}: {text} ({r['id']})")
    return out


@lru_cache(maxsize=1)
def _history():
    out = {}
    for r in _rows("SELECT event_id, date, supplier_id, part_id, type, asked_pct, settled_pct, note "
                   "FROM negotiation_history ORDER BY date"):
        out.setdefault(r["supplier_id"], []).append(r)
    return out


@lru_cache(maxsize=1)
def _scorecards():
    out = {}
    for r in _rows("SELECT id, supplier_id, quarter, otd_pct, ppm, colour FROM scorecards ORDER BY quarter"):
        out[r["supplier_id"]] = r  # the latest quarter wins
    return out


@lru_cache(maxsize=1)
def _cost_to_price():
    """Median of should-cost / that supplier's latest price, by part category (and 'all')."""
    rows = _rows("""
        SELECT p.category, s.unit_cost,
               (SELECT price FROM price_conditions c WHERE c.part_id = s.part_id AND c.supplier_id = s.supplier_id
                ORDER BY valid_from DESC LIMIT 1) AS price
        FROM should_cost s JOIN parts p ON p.id = s.part_id WHERE s.supplier_id IS NOT NULL""")
    ratios = {}
    for r in rows:
        if r["price"]:
            ratios.setdefault(r["category"], []).append(r["unit_cost"] / r["price"])
    out = {cat: statistics.median(v) for cat, v in ratios.items() if len(v) >= 3}
    out["all"] = statistics.median([x for v in ratios.values() for x in v])
    return out


# ------------------------------------------------------------------ estimates


def market_price(supplier_id, part_id):
    """(price per price_unit, source) for the part: this supplier's latest condition, else the
    lowest latest condition among its sources, else the standard price."""
    rows = _rows("""SELECT supplier_id, price FROM price_conditions c WHERE part_id = ? AND valid_from =
                    (SELECT max(valid_from) FROM price_conditions d WHERE d.part_id = c.part_id
                     AND d.supplier_id = c.supplier_id)""", (part_id,))
    own = [r["price"] for r in rows if r["supplier_id"] == supplier_id]
    if own:
        return own[0], "own_price"
    if rows:
        return min(r["price"] for r in rows), "market_price"
    std = _rows("SELECT standard_price FROM parts WHERE id = ?", (part_id,))
    if std and std[0]["standard_price"]:
        return std[0]["standard_price"], "standard_price"
    return None, None


def floor(v, supplier_id=None, part_id=None):
    """(floor_estimate, floor_confidence, source) in EUR per price_unit."""
    cost = v.get("estimated_unit_cost")
    if cost is not None:
        if v.get("should_cost_supplier_specific"):
            return cost, (v.get("should_cost_confidence_pct") or 5) / 100, "should_cost"
        factor = COUNTRY_FACTOR.get(v.get("supplier_country") or "DE", 1.0)
        return cost * factor, max(0.10, (v.get("should_cost_confidence_pct") or 10) / 100), "should_cost_country"
    price, source = market_price(supplier_id, part_id) if part_id else (None, None)
    if price is None:
        return None, None, None
    ratios = _cost_to_price()
    ratio = min(1.0, ratios.get(v.get("part_category"), ratios["all"]))  # never above today's price
    return round(price * ratio, 4), MARKET_CONFIDENCE, source


def cash_pressure(supplier_id, v):
    """0..1 and the reasons: weak or worsening credit, thin equity, distress news, letters about
    our overdue invoices, a cash discount on offer."""
    score, why = 0.0, []
    credit, change = v.get("credit_index"), v.get("credit_index_change")
    if credit is not None and credit >= 300:  # German style: higher is worse, 300+ is weak
        score += 0.35
        why.append(f"credit index {credit:g}")
    if change is not None and change >= 30:
        score += 0.25
        why.append(f"credit index +{change:g} in 12 months")
    equity = v.get("equity_ratio_pct")
    if equity is not None and equity < 22:
        score += 0.15
        why.append(f"equity ratio {equity:g} %")
    for n in _news().get(supplier_id, []):
        if n["topic"] in CASH_NEWS:
            score += CASH_NEWS[n["topic"]]
            why.append(f"{n['headline']} ({n['id']})")
    overdue = _overdue_letters().get(supplier_id)
    if overdue:
        score += 0.15
        why.append(f"complains about our overdue invoices ({', '.join(overdue)})")
    if supplier_id in _skonto():
        score += 0.1
        why.append("offers a cash discount")
    return round(min(1.0, score), 3), why


def cash_rate(supplier_id, v, pressure=None):
    """What money is worth to the supplier per year: the rate its cash discount implies, else the
    base rate plus up to 16 points for cash pressure."""
    if pressure is None:
        pressure, _ = cash_pressure(supplier_id, v)
    rate = BASE_RATE + 0.16 * pressure
    s = _skonto().get(supplier_id)
    if s and s[0] and s[0] > (s[1] or 0):
        rate = max(rate, s[2] / 100 * 360 / (s[0] - (s[1] or 0)))
    return round(rate, 4)


def archetype(supplier_id, v, pressure):
    """family_foundry | group_ladder | cash_short_jobshop | near_monopolist | unknown, and the
    approval style that goes with it (flat | ladder)."""
    owner = v.get("owner_type")
    group = owner == "group" or bool(v.get("group_parent"))
    turnover = v.get("turnover_eur") or 0
    sources = v.get("approved_supplier_count")
    capacity = any(n["topic"] in CAPACITY_NEWS for n in _news().get(supplier_id, []))
    style = "ladder" if group else "flat"
    if pressure >= 0.5 and not group:
        return "cash_short_jobshop", style
    if sources is not None and sources <= 1 and (group or turnover >= BIG_TURNOVER or capacity):
        return "near_monopolist", style
    if group:
        return "group_ladder", style
    if owner in ("family", "founder"):
        return "family_foundry", style
    return "unknown", style


def history(supplier_id, part_id=None):
    """Past renewals with this supplier: how much it asked and settled, on average and per event."""
    rows = _history().get(supplier_id, [])
    asked = [r for r in rows if r["asked_pct"] is not None and r["settled_pct"] is not None]
    return {
        "events": len(rows),
        "events_this_part": sum(1 for r in rows if r["part_id"] == part_id),
        "avg_asked_pct": round(statistics.fmean(r["asked_pct"] for r in asked), 2) if asked else None,
        "avg_settled_pct": round(statistics.fmean(r["settled_pct"] for r in asked), 2) if asked else None,
        "avg_given_up_pp": round(statistics.fmean(r["asked_pct"] - r["settled_pct"] for r in asked), 2)
        if asked else None,
        "notes": sorted({r["note"] for r in rows if r["note"]}),
        "last": [{k: r[k] for k in ("event_id", "date", "part_id", "type", "asked_pct", "settled_pct")}
                 for r in rows[-3:]],
    }


def quality(supplier_id):
    sc = _scorecards().get(supplier_id)
    if not sc:
        return {}
    return {"otd_pct": sc["otd_pct"], "ppm": sc["ppm"], "colour": sc["colour"], "quarter": sc["quarter"],
            "ids": [sc["id"]]}


def notes(supplier_id):
    out = [f"{n['date']} {n['headline']} ({n['id']})" for n in _news().get(supplier_id, []) if n["topic"] != "noise"]
    out += [f"wrote about overdue invoices ({d})" for d in _overdue_letters().get(supplier_id, [])]
    return out + _meeting_notes().get(supplier_id, [])


# ------------------------------------------------------------------ overrides


@lru_cache(maxsize=4)
def _overrides_at(path, mtime):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _overrides(path=OVERRIDES_FILE):
    path = Path(path)
    return _overrides_at(str(path), path.stat().st_mtime) if path.is_file() else {}


def apply_overrides(p, supplier_id, part_id=None, overrides=None):
    """Hand corrections, supplier-wide (``"sup:..."``) then per pair (``"sup:...|part:..."``).
    Fields replace the computed value; ``notes`` are added; keys starting with ``_`` are comments
    (``_why`` is kept in ``p["overrides"]``)."""
    overrides = _overrides() if overrides is None else overrides
    for key in (supplier_id, f"{supplier_id}|{part_id}"):
        o = overrides.get(key)
        if not o:
            continue
        for k, v in o.items():
            if k == "notes":
                p["notes"] = list(dict.fromkeys([*p.get("notes", []), *v]))
            elif not k.startswith("_"):
                p[k] = v
        if "cash_pressure" in o and "cash_rate_estimate" not in o:
            rate = max(p.get("cash_rate_estimate") or 0, BASE_RATE + 0.16 * o["cash_pressure"])
            p["cash_rate_estimate"] = round(rate, 4)
        if "archetype" in o and "approval_style" not in o:
            p["approval_style"] = "ladder" if o["archetype"] == "group_ladder" else p.get("approval_style", "flat")
        why = o.get("_why")
        if why and why not in p.setdefault("overrides", []):
            p["overrides"].append(why)
    return p


# ------------------------------------------------------------------ profiles


def computed_profile(supplier_id, part_id):
    """The profile from the data alone, without overrides; {} for a supplier we cannot read."""
    try:
        v = build_feature_vector(supplier_id, part_id, AS_OF)
    except Exception:
        return {}
    from .claims import driver_changes  # claims imports package only; keep the import local

    est, conf, source = floor(v, supplier_id, part_id)
    pressure, why = cash_pressure(supplier_id, v)
    kind, style = archetype(supplier_id, v, pressure)
    sup = _suppliers().get(supplier_id, {})
    return {
        "supplier_id": supplier_id,
        "part_id": part_id,
        "name": sup.get("name") or supplier_id,
        "country": v.get("supplier_country") or sup.get("country"),
        "owner_type": v.get("owner_type"),
        "archetype": kind,
        "floor_estimate": est,
        "floor_confidence": conf,
        "floor_source": source,
        "cash_rate_estimate": cash_rate(supplier_id, v, pressure),
        "cash_pressure": pressure,
        "cash_reasons": why,
        "approval_style": style,
        "cost_drivers": driver_changes(part_id) if part_id else [],
        "history": history(supplier_id, part_id),
        "quality": quality(supplier_id),
        "notes": notes(supplier_id),
        "standard_terms": {},  # from the quote PDF once the session is open
        "vendor_terms": {"payment_days": sup.get("payment_days"), "incoterm": sup.get("incoterm"),
                         "lead_time_days": sup.get("standard_lead_time_days")},  # master data, not binding
    }


def supplier_profile(supplier_id, part_id):
    """Computed profile with the hand corrections applied."""
    p = computed_profile(supplier_id, part_id)
    return apply_overrides(p, supplier_id, part_id) if p else p


def pairs():
    """Every detailed supplier with every part it supplies (sourcing) or quoted (quotes)."""
    rows = _rows("""SELECT supplier_id, part_id FROM sourcing
                    WHERE supplier_id IN (SELECT supplier_id FROM supplier_intel)
                    UNION SELECT supplier_id, part_id FROM quotes
                    WHERE supplier_id IN (SELECT supplier_id FROM supplier_intel)
                    ORDER BY 1, 2""")
    return [(r["supplier_id"], r["part_id"]) for r in rows]


def profile_all(path=PROFILES_FILE, write=True):
    """Profiles of every detailed supplier x part: {"as_of", "profiles": {supplier: {part: profile}}}.
    The Analyst's input for its training population; the agent's lookup table at run time."""
    from .claims import supplier_claims
    from .memory import apply_memory

    out = {"as_of": AS_OF, "profiles": {}}
    for sid, part in pairs():
        p = apply_memory(supplier_profile(sid, part), sid, [part])
        if p:
            p["claims"] = [asdict(c) for c in supplier_claims(sid, part)]  # for the review; cases build their own
            out["profiles"].setdefault(sid, {})[part] = p
    if write:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        path.with_name("review.md").write_text(review(out["profiles"]), encoding="utf-8")
    return out


def review(profiles):
    """The hand-review sheet: per supplier its estimates, the evidence and every claim, as Markdown.
    Corrections go into overrides.json (fields, notes, drop_claims)."""
    lines = ["# Supplier review", "",
             f"{len(profiles)} suppliers. Correct anything in `src/buyer/facts/overrides.json` "
             "(with `_why`); drop a claim with `\"drop_claims\": [\"<key>\"]`.", ""]
    for sid, parts in sorted(profiles.items()):
        first = next(iter(parts.values()))
        lines += [f"## {first['name']} ({sid})", "",
                  f"- {first['country']}, {first['owner_type']}; **{first['archetype']}**, approval "
                  f"{first['approval_style']}; cash pressure {first['cash_pressure']} "
                  f"(rate {first['cash_rate_estimate']:.0%})"]
        for why in first.get("cash_reasons") or []:
            lines.append(f"  - cash: {why}")
        for why in first.get("overrides") or []:
            lines.append(f"  - override: {why}")
        h = first.get("history") or {}
        if h.get("events"):
            lines.append(f"- history: {h['events']} renewals, asked {h['avg_asked_pct']} % on average, settled "
                         f"{h['avg_settled_pct']} %")
        q = first.get("quality") or {}
        if q:
            lines.append(f"- quality {q['quarter']}: OTD {q['otd_pct']} %, {q['ppm']} ppm, {q['colour']}")
        for part, p in sorted(parts.items()):
            floor_ = f"{p['floor_estimate']:.2f}" if p["floor_estimate"] is not None else "-"
            lines.append(f"- {part}: floor {floor_} ({p['floor_source']}, +-{p['floor_confidence']:.0%})")
        lines += ["", "Notes:"] + [f"- {n}" for n in first.get("notes") or ["(none)"]]
        claim_lines = {}
        for p in parts.values():
            for c in p.get("claims") or []:
                claim_lines.setdefault(c["key"], f"- `{c['key']}` ({c['strength']:.2f}) {c['sentence']}")
        lines += ["", "Claims:"] + (list(claim_lines.values()) or ["- (none)"]) + [""]
    return "\n".join(lines)


@lru_cache(maxsize=4)
def _stored_at(path, mtime):
    return json.loads(Path(path).read_text(encoding="utf-8")).get("profiles", {})


def stored(path=PROFILES_FILE):
    """The precomputed profiles, {} if the file is not there (or unreadable)."""
    path = Path(path)
    try:
        return _stored_at(str(path), path.stat().st_mtime)
    except (OSError, ValueError):
        return {}


def lookup_profile(supplier_id, part_id, path=PROFILES_FILE):
    """One profile: precomputed if there, else computed now; overrides applied either way."""
    p = stored(path).get(supplier_id, {}).get(part_id)
    if p is None:
        return supplier_profile(supplier_id, part_id)
    return apply_overrides(json.loads(json.dumps(p)), supplier_id, part_id)  # a copy: the cache stays clean


def bundle_floor(case, part_id):
    """(floor, confidence, source) for a bundle: its unit_price is per kit, so the floor comes from
    today's kit price (the case's current_unit_price) x the cost-to-price ratio, never above it."""
    price = (case.get("buyer") or {}).get("current_unit_price")
    if not price:
        return None, None, None
    category = (_rows("SELECT category FROM parts WHERE id = ?", (part_id,)) or [{}])[0].get("category")
    ratios = _cost_to_price()
    return round(price * min(1.0, ratios.get(category, ratios["all"])), 4), MARKET_CONFIDENCE, "bundle_current_price"


def profile(case, path=PROFILES_FILE):
    """Profile per supplier for the case: the first part's profile with the case's floor - the kit
    price for bundles (``floor_by_part`` keeps the parts' own floors) - and the supplier memory."""
    from .memory import apply_memory

    parts = case.get("parts") or [None]
    out = {}
    for sid in case.get("suppliers", []):
        p = lookup_profile(sid, parts[0], path)
        if p and len(parts) > 1:
            p["floor_by_part"] = {part: (lookup_profile(sid, part, path) or {}).get("floor_estimate") for part in parts}
            for k in ("floor_computed", "floor_computed_source", "memory"):  # the first part's, not the kit's
                p.pop(k, None)
            est, conf, source = bundle_floor(case, parts[0])
            p.update(floor_estimate=est, floor_confidence=conf, floor_source=source)
        out[sid] = apply_memory(p, sid, parts) if p else p
        if p:
            try:  # the writer's brief on this supplier; never worth losing a move over
                from .dossier import dossier

                p["dossier"] = dossier(p)
                from .strategy import initial

                s0 = initial(case, p)  # the opening strategy; the policy re-chooses after each reply
                p["strategy"], p["strategy_reason"], p["strategy_params"] = s0.name, s0.reason, s0.params
            except Exception:
                p["dossier"] = ""
    return out


if __name__ == "__main__":
    import time

    t = time.perf_counter()
    result = profile_all()
    n = sum(len(v) for v in result["profiles"].values())
    print(f"{len(result['profiles'])} suppliers, {n} profiles -> {PROFILES_FILE} in {time.perf_counter() - t:.1f}s")
