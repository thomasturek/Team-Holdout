"""Supplier memory (SCOUT): what our own sessions taught us about a supplier's real floor.

Every ended session reports ``c_best``, the cost of the best deal the case allows. At the terms we
closed on, that is a unit price: the lowest price this supplier would have agreed to - its
observed floor, much tighter than any estimate from the data package. The final only brings the
46 detailed suppliers, so a supplier met in practice is met again.

    uv run python -m buyer.facts.memory           # rebuild memory.json from runs/practice_sessions
    uv run python -m buyer.facts.memory --check   # our floors against every logged best price

``memory.json`` sits next to this file and is committed (``runs/`` is not), so the final machine
has it. ``apply_memory(profile, supplier, parts)`` is called by ``profile(case)``:
    same supplier, same parts   floor = the observed best price (confidence 3 %); a relationship charge
                                we paid gives its full cost exactly (``full_cost_observed``)
    same supplier, other parts  floor x (observed best / our estimate) of its logged cases
    RFQ                         the best price of the case caps every bidder's floor for that part
"""

from __future__ import annotations

import argparse
import json
import statistics
from functools import lru_cache
from pathlib import Path

from arena_kit.cost import relationship_cost, total_cost
from arena_kit.docs import standard_terms

REPO_ROOT = Path(__file__).resolve().parents[3]
SESSIONS = REPO_ROOT / "runs" / "practice_sessions"
MEMORY_FILE = Path(__file__).with_name("memory.json")
OBSERVED_CONFIDENCE = 0.03
BIAS_RANGE = (0.7, 1.15)  # how far one supplier's logged cases may move its other floors


def key(supplier_id: str, parts) -> str:
    return f"{supplier_id}|{'+'.join(parts or [])}"


def best_price(case: dict, terms: dict, c_best: float) -> float:
    """The unit price at ``terms`` whose total cost is ``c_best`` (bisection over total_cost)."""
    lo, hi = 0.0, max(terms["unit_price"], 0.01) * 4
    for _ in range(60):
        mid = (lo + hi) / 2
        if total_cost(case, {**terms, "unit_price": mid}) < c_best:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 4)


def observation(doc: dict) -> dict | None:
    """One ended session with a deal -> what it shows about the winning supplier, else None."""
    case, r = doc.get("case") or {}, doc.get("result") or {}
    if not (r.get("deal") and r.get("c_best") and r.get("terms", {}).get("unit_price") and case.get("buyer")):
        return None
    sid = r["supplier_id"]
    thread = (doc.get("threads") or {}).get(sid) or {}
    theirs = [ts["terms"].get("unit_price") for m in thread.get("messages") or []
              if m.get("from") != "buyer" for ts in (m.get("term_sheets") or [])[:1]]
    return {
        "case_id": case.get("case_id"),
        "session_id": doc.get("session_id"),
        "type": case.get("type"),
        "supplier_id": sid,
        "parts": case.get("parts") or [],
        "bidders": case.get("suppliers") or [sid],
        "opening_price": theirs[0] if theirs else None,
        "deal_price": r["terms"]["unit_price"],
        "best_price": best_price(case, r["terms"], r["c_best"]),
        "score": r.get("score"),
        "terms": r["terms"],
        "standard": standard_terms(thread.get("messages") or []) or {},
        "relationship": (r.get("cost_breakdown") or {}).get("relationship") or 0.0,
        "case": case,
    }


def implied_full_cost(o: dict, profile: dict, rate: float | None = None) -> float | None:
    """The supplier full cost at which the arena's relationship charge for this deal is what we paid
    (bisection; our estimate of its cash rate and standard terms). None without a charge."""
    from .costing import relationship_case, supplier_estimate

    if o["relationship"] <= 1.0 or not relationship_case(o["case"]):
        return None
    base = supplier_estimate(o["case"], {**profile, "full_cost_observed": 1.0}, o["standard"])
    if base is None:
        return None
    if rate is not None:
        base["interest_rate"] = rate

    def charge(full_cost):
        return relationship_cost(o["case"], o["terms"], o["standard"], {**base, "full_cost": full_cost})

    lo, hi = 0.3 * o["deal_price"], 1.5 * o["deal_price"]  # the charge rises with the full cost
    for _ in range(80):
        mid = (lo + hi) / 2
        if charge(mid) < o["relationship"]:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 4)


RATE_GRID = [round(0.005 * i, 4) for i in range(0, 81)]  # 0 % .. 40 % a year


def fit_relationship(obs: list[dict], profile: dict) -> tuple[float, float] | None:
    """(full cost, interest rate) of the supplier that reproduce the relationship charges the arena
    billed in our sessions with it - each session at its own payment term. The charge depends on what
    money is worth to the supplier once the payment term differs from its standard (P01/P03 at 14, 45
    and 90 days, 2026-10-25), so one charge fixes the full cost, several fix the rate as well.
    Sessions without a charge count too: the fit must not bill them. None without any charge."""
    from .costing import relationship_case, supplier_estimate

    charged = [o for o in obs if o["relationship"] > 1.0 and relationship_case(o["case"])]
    if not charged:
        return None
    usable = [o for o in obs if relationship_case(o["case"])]
    best = None
    for rate in RATE_GRID:
        prof = {**profile, "full_cost_observed": 1.0, "cash_rate_estimate": rate}
        full = implied_full_cost(charged[0], prof, rate=rate)
        if full is None:
            continue
        err = 0.0
        for o in usable:
            base = supplier_estimate(o["case"], {**prof, "full_cost_observed": full}, o["standard"])
            if base is None:
                continue
            base["interest_rate"] = rate
            pred = relationship_cost(o["case"], o["terms"], o["standard"], base)
            err += ((pred - o["relationship"]) / max(o["relationship"], 200.0)) ** 2
        if best is None or err < best[0] - 1e-12:
            best = (err, full, rate)
    return (best[1], best[2]) if best else None


def observations(folder: Path = SESSIONS) -> list[dict]:
    out = []
    for path in sorted(Path(folder).glob("*.json")):
        try:
            obs = observation(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if obs:
            out.append(obs)
    return out


def build(folder: Path = SESSIONS, path: Path = MEMORY_FILE, write: bool = True) -> dict:
    """Memory per supplier and parts (the median over its sessions) and the RFQ caps per part."""
    from .profile import lookup_profile  # the estimate we would use without memory

    grouped: dict[str, list[dict]] = {}
    for o in observations(folder):
        grouped.setdefault(key(o["supplier_id"], o["parts"]), []).append(o)
    entries, caps = {}, {}
    for k, obs in sorted(grouped.items()):
        o = obs[-1]
        best = round(statistics.median(x["best_price"] for x in obs), 4)
        rfq = len(o["bidders"]) > 1
        estimate, p = None, {}
        if len(o["parts"]) == 1:  # the data-only estimate, before any memory
            p = lookup_profile(o["supplier_id"], o["parts"][0]) or {}
            estimate = p.get("floor_computed") or p.get("floor_estimate")
        fitted = None if rfq else fit_relationship(obs, p)
        entries[k] = {
            "supplier_id": o["supplier_id"], "parts": o["parts"], "type": o["type"], "rfq": rfq,
            "best_price": best, "deal_price": o["deal_price"], "opening_price": o["opening_price"],
            "estimate": estimate, "sessions": [x["session_id"] for x in obs],
            "cases": sorted({x["case_id"] for x in obs}), "scores": [x["score"] for x in obs],
            "full_cost_observed": round(fitted[0], 4) if fitted else None,
            "interest_rate_observed": fitted[1] if fitted else None,
        }
        if rfq:
            part = "+".join(o["parts"])
            caps[part] = min(caps.get(part, best), best)
    memory = {"built_from": sum(len(v) for v in grouped.values()), "entries": entries, "rfq_caps": caps}
    if write:
        Path(path).write_text(json.dumps(memory, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        _load.cache_clear()
    return memory


@lru_cache(maxsize=2)
def _load(path: str, mtime: float) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load(path: Path = MEMORY_FILE) -> dict:
    path = Path(path)
    try:
        return _load(str(path), path.stat().st_mtime)
    except (OSError, ValueError):
        return {"entries": {}, "rfq_caps": {}}


def supplier_bias(supplier_id: str, memory: dict) -> float | None:
    """Observed best / our estimate over the supplier's single-part, single-bidder sessions."""
    ratios = [e["best_price"] / e["estimate"] for e in memory.get("entries", {}).values()
              if e["supplier_id"] == supplier_id and not e["rfq"] and e.get("estimate")]
    if not ratios:
        return None
    return min(BIAS_RANGE[1], max(BIAS_RANGE[0], statistics.median(ratios)))


def apply_memory(p: dict, supplier_id: str, parts, memory: dict | None = None) -> dict:
    """Put what the sessions showed into a profile; repeatable (always starts from the estimate)."""
    if not p:
        return p
    memory = load() if memory is None else memory
    if "floor_computed" not in p:
        p["floor_computed"] = p.get("floor_estimate")
        p["floor_computed_source"] = p.get("floor_source")
    floor, conf, source = p["floor_computed"], p.get("floor_confidence"), p["floor_computed_source"]
    seen = memory.get("entries", {}).get(key(supplier_id, parts))
    if seen and not seen["rfq"]:
        floor, conf, source = seen["best_price"], OBSERVED_CONFIDENCE, "observed_best"
        p["memory"] = {k: seen[k] for k in ("best_price", "deal_price", "opening_price", "cases", "scores")}
        if seen.get("full_cost_observed"):
            p["full_cost_observed"] = seen["full_cost_observed"]
        if seen.get("interest_rate_observed") is not None:
            p["interest_rate_observed"] = seen["interest_rate_observed"]
    else:
        bias = supplier_bias(supplier_id, memory)
        if bias is not None and floor is not None:
            floor, source = round(floor * bias, 4), f"{source}+observed_bias"
        cap = memory.get("rfq_caps", {}).get("+".join(parts or []))
        if cap is not None and (floor is None or cap < floor):
            floor, conf, source = cap, 0.1, "rfq_observed_best"
    p.update(floor_estimate=floor, floor_confidence=conf, floor_source=source)
    return p


def check(folder: Path = SESSIONS) -> list[dict]:
    """Per logged session: the floor profile(case) gives now, the data-only estimate, and the
    best price - a floor above the best price keeps the policy from ever asking low enough."""
    from .profile import profile

    rows = []
    for path in sorted(Path(folder).glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        o = observation(doc)
        if not o:
            continue
        p = profile(doc["case"]).get(o["supplier_id"]) or {}
        rows.append({**o, "floor": p.get("floor_estimate"), "source": p.get("floor_source"),
                     "estimate": p.get("floor_computed")})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sessions", type=Path, default=SESSIONS)
    ap.add_argument("--check", action="store_true", help="compare floors with the logged best prices")
    a = ap.parse_args(argv)
    if a.check:
        print(f"{'case':9} {'supplier':10} {'best':>9} {'floor':>9} {'estimate':>9}  source")
        for r in check(a.sessions):
            est = f"{r['estimate']:9.2f}" if r["estimate"] else "        -"
            flag = "  <- floor above best" if r["floor"] and r["floor"] > r["best_price"] * 1.02 else ""
            print(f"{r['case_id']:9} {r['supplier_id']:10} {r['best_price']:9.2f} {r['floor'] or 0:9.2f} {est}  "
                  f"{r['source']}{flag}")
        return
    m = build(a.sessions)
    print(f"{m['built_from']} sessions -> {len(m['entries'])} entries, {len(m['rfq_caps'])} RFQ caps -> {MEMORY_FILE}")


if __name__ == "__main__":
    main()
