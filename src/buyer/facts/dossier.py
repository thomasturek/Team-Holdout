"""Supplier dossier (SCOUT): a short brief per supplier for the writer - who decides, what it cares
about, what it argued with us before, how it moves, and the angle to take.

    uv run python -m buyer.facts.dossier     # rebuild dossiers.json from runs/practice_sessions + runs/practice

    from buyer.facts.dossier import dossier
    dossier(profile)   # -> a few plain sentences, no digits, no data IDs

The final only brings the 46 detailed suppliers of the package, so what a supplier showed in practice
is worth telling the writer: Nordmark's key account manager argued copper in every reply and needs
its pricing committee; Werdenfels, Donautal and Leitner negotiate through Inside Sales, the role with
the least authority. ``dossiers.json`` (committed, next to this file) keeps what the sessions showed;
``dossier(profile)`` joins it with the profile (archetype, meeting notes, cash signals) at run time.

The dossier is background for the writer: it chooses the angle, it is never quoted. It holds no
figures and no IDs, and nothing about a supplier's finances that the writer could repeat.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
from functools import lru_cache
from pathlib import Path

from .package import REPO_ROOT

SESSIONS = REPO_ROOT / "runs" / "practice_sessions"
EVENTS = REPO_ROOT / "runs" / "practice"
DOSSIER_FILE = Path(__file__).with_name("dossiers.json")

LOW_AUTHORITY = ("inside sales", "sales assistant", "sales office", "customer service", "order desk")
SERIES_WORDS = {"CU-": "copper", "AS-": "alloy surcharges", "PPI-C24": "steel", "LCI-": "labour",
                "PPI-D35": "energy", "PPI-C26": "electronic components", "PPI-C22": "rubber"}
PHRASES = {  # what a supplier said, as a short note in words
    "needs_cash": r"need (?:the )?cash|cash flow|faster payment would help|pay (?:us )?(?:faster|earlier|on time)",
    "prefers_standard_payment": r"standard and preferred payment term|preferred payment term",
    "committee": r"pricing committee|committee|approval|head office|management board|our board",
    "free_capacity": r"free capacity|looking for new customers|take additional parts",
    "full_capacity": r"fully booked|allocat|capacity is (?:limited|tight)",
    "wants_volume": r"higher (?:annual )?volume|binding (?:higher )?volume|which volume can you commit",
    "wants_clause": r"index clause|preisgleitklausel|alloy surcharge index|surcharge clause",
    "asks_for_proof": r"which figures|send us the data|provide (?:this|the) documentation",
}
ANGLES = {
    "family_foundry": "Owner to owner: loyalty and reciprocity. Acknowledge what it has done for us and present "
                      "Option A as fair for both family companies.",
    "group_ladder": "Approver memo: give our contact one short paragraph it can forward unchanged to its pricing "
                    "committee, and ask it to take Option A to the approver.",
    "cash_short_jobshop": "Cash first: lead with the faster-payment option as the reason Option A works for it - "
                          "never mention its finances.",
    "near_monopolist": "Security, not pressure: planning security, steady volume and a reliable partner; firm, "
                       "never adversarial.",
    "unknown": "Plain and businesslike: its concern first, then the options.",
    "escalate": "Make it easy to escalate: respectful to our contact, with one short paragraph its decision-maker "
                "can approve as it stands, and a clear request to take Option A to that person.",
}
# Angle B per profile, for A/B test batches (BUYER_ANGLE=B; default A). Hypotheses from the practice logs
# (2026-10-25, across suppliers, so confounded - hence the test): planning-security language went with
# bigger first moves at groups (+5.8 pp), form letters with smaller ones at family firms (-4.7 pp);
# Kalwisz's payment term was not negotiable; Inside Sales contacts rarely decide alone.
ANGLES_B = {
    "family_foundry": "Steady work and fair numbers: lead with what keeps its shop busy - the contract length and "
                      "steady call-offs in our options - and let the claim lines show why Option A is fair; "
                      "less sentiment, more business.",
    "group_ladder": "Planning security first: lead with the commitment our options give - contract length, volume, "
                    "planning certainty - as the reason its committee can approve Option A.",
    "cash_short_jobshop": "Quality as the trade: lead with what the quality commitment in our options is worth to "
                          "both sides; speak of payment only if an option changes it.",
    "near_monopolist": "Escalate respectfully: one short paragraph its management can approve, framing Option A as "
                       "securing the full volume and long-term planning with us.",
    "unknown": "Evidence first: the claim lines, then Option A as the fair consequence.",
    "escalate": "One simple yes: make Option A the obvious choice our contact can confirm on its own - short and "
                "clear, no paragraph for anyone else.",
}
GENERIC_DRIVERS = ("raw material", "raw_material")


def angle_variant() -> str:
    """'A' (default) or 'B' - which angle set a test batch plays (environment BUYER_ANGLE)."""
    return "B" if os.environ.get("BUYER_ANGLE", "A").strip().upper() == "B" else "A"


def angle(kind: str, low_authority: bool = False) -> str:
    key = "escalate" if low_authority else kind if kind in ANGLES else "unknown"
    return (ANGLES_B if angle_variant() == "B" else ANGLES)[key]


def _driver_words(drivers) -> list[str]:
    out = []
    specific = [d for d in drivers if str(d) not in GENERIC_DRIVERS]
    for d in specific or drivers:  # copper beats "raw material"
        word = next((w for pre, w in SERIES_WORDS.items() if str(d).startswith(pre)), str(d).replace("_", " "))
        if word not in out:
            out.append(word)
    return out


def observe(sessions: Path = SESSIONS, events: Path = EVENTS) -> dict:
    """Per supplier, what our practice sessions showed: roles, arguments, asks, phrases, how it moved."""
    from arena_kit.cost import total_cost

    obs: dict = collections.defaultdict(lambda: {"roles": collections.Counter(), "drivers": collections.Counter(),
                                                 "asks": collections.Counter(), "said": collections.Counter(),
                                                 "first_moves": [], "later_moves": [], "replies_to_final": [],
                                                 "sessions": 0})
    for path in sorted(Path(sessions).glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        case = doc.get("case") or {}
        for sid, th in (doc.get("threads") or {}).items():
            o = obs[sid]
            o["sessions"] += 1
            sup = [m for m in th.get("messages") or [] if m.get("from") != "buyer"]
            for m in sup:
                body = m.get("body") or ""
                for key, rx in PHRASES.items():
                    if re.search(rx, body, re.I):
                        o["said"][key] += 1
            costs = []
            for m in sup:
                if m.get("term_sheets"):
                    try:
                        costs.append(total_cost(case, m["term_sheets"][0]["terms"]))
                    except Exception:
                        pass
            moves = [(a - b) / a for a, b in zip(costs, costs[1:], strict=False) if a]
            if moves:
                o["first_moves"].append(moves[0])
                o["later_moves"] += moves[1:]
            finals = [i for i, m in enumerate(sup) if m.get("status") == "final_offer"]
            if finals:
                o["replies_to_final"].append(finals[0])
        events_file = Path(events) / str(case.get("case_id", "")).replace(":", "_") / f"{doc.get('session_id')}.jsonl"
        if events_file.is_file():
            for line in events_file.read_text(encoding="utf-8").splitlines():
                e = json.loads(line)
                if e.get("kind") == "backoffice" and isinstance(e.get("data"), list):
                    for x in e["data"]:
                        if x.get("supplier_id") and x.get("from") and x.get("from") != "team":
                            obs[x["supplier_id"]]["roles"][x["from"]] += 1
                elif e.get("kind") == "decision":
                    sid = e.get("supplier_id")
                    sig = ((e.get("trace") or {}).get("diplomat") or {}).get("reader", {}).get("signals") or {}
                    if sid:
                        obs[sid]["drivers"].update(sig.get("cost_drivers_claimed") or [])
                        obs[sid]["asks"].update(sig.get("asks") or [])
    return obs


def summarise(o: dict) -> dict:
    """The observations of one supplier as stable fields (what dossiers.json keeps)."""
    def median(v):
        v = sorted(v)
        return v[len(v) // 2] if v else None

    role = o["roles"].most_common(1)[0][0] if o["roles"] else None
    n = max(1, o["sessions"])
    return {
        "sessions": o["sessions"],
        "contact_role": role,
        "drivers": [d for d, _ in o["drivers"].most_common(3)],
        "asks": [a for a, k in o["asks"].most_common(3) if k >= 1],
        "said": sorted(k for k, c in o["said"].items() if c >= max(1, n // 2)),
        "first_move": median(o["first_moves"]),
        "later_move": median(o["later_moves"]),
        "replies_to_final": median(o["replies_to_final"]),
    }


def build(sessions: Path = SESSIONS, events: Path = EVENTS, path: Path = DOSSIER_FILE, write: bool = True) -> dict:
    data = {"suppliers": {sid: summarise(o) for sid, o in sorted(observe(sessions, events).items()) if sid}}
    if write:
        Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        _load.cache_clear()
    return data


@lru_cache(maxsize=2)
def _load(path: str, mtime: float) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8")).get("suppliers", {})


def observed(supplier_id: str, path: Path = DOSSIER_FILE) -> dict:
    path = Path(path)
    try:
        return _load(str(path), path.stat().st_mtime).get(supplier_id) or {}
    except (OSError, ValueError):
        return {}


def _movement(o: dict) -> str | None:
    first, later, finals = o.get("first_move"), o.get("later_move"), o.get("replies_to_final")
    if first is None:
        return None
    step = "a big first step" if first >= 0.03 else "a small first step" if first > 0.002 else "no first step"
    then = ("then it barely moves" if (later or 0) < 0.002 else "then smaller steps")
    final = " and it calls its offer final after a few replies" if finals is not None and finals <= 4 else ""
    return f"It moves with {step}, {then}{final} - the first message decides most of the deal."


def dossier(profile: dict | None, obs: dict | None = None) -> str:
    """A few plain sentences about the supplier for the writer (no digits, no IDs)."""
    p = profile or {}
    sid = p.get("supplier_id") or ""
    o = observed(sid) if obs is None else obs
    kind = p.get("archetype") or "unknown"
    notes = " ".join(str(n) for n in p.get("notes") or [])
    lines = []

    role = o.get("contact_role")
    who = f"We deal with its {role.lower()}" if role else "We deal with its sales side"
    low_authority = bool(role) and any(w in role.lower() for w in LOW_AUTHORITY)
    if low_authority:
        who += ", who has little authority of its own: ask it to take Option A to the person who decides"
    elif p.get("approval_style") == "ladder" or re.search(r"pricing committee|head office|approval", notes, re.I) \
            or "committee" in (o.get("said") or []):
        who += "; bigger steps need its pricing committee or head office"
    elif role and role.lower() == "owner":
        who += ", who decides alone"
    lines.append(who + ".")

    cares = []
    said = set(o.get("said") or [])
    asks_cash = re.search(r"pay our invoices within|pay earlier", notes, re.I)
    if (p.get("cash_pressure") or 0) >= 0.5 or "needs_cash" in said or asks_cash:
        cares.append("being paid faster")
    if "prefers_standard_payment" in said:
        cares.append("keeping its standard payment term")
    if "free_capacity" in said or re.search(r"free capacity|second shift|additional parts", notes, re.I):
        cares.append("filling free capacity")
    if "full_capacity" in said or re.search(r"fully booked|allocat", notes, re.I):
        cares.append("its tight capacity")
    wants_calloffs = re.search(r"firm call-offs", notes, re.I)
    if "wants_volume" in said or "volume" in (o.get("asks") or []) or wants_calloffs:
        cares.append("a binding volume")
    if re.search(r"partnership in return|kept supplying at the old price", notes, re.I):
        cares.append("being repaid for its loyalty (it held the old price for us in a hard year)")
    if re.search(r"successor", notes, re.I):
        cares.append("continuity, as the owner looks for a successor")
    if cares:
        lines.append("It cares about " + ", ".join(cares) + ".")

    drivers = _driver_words(o.get("drivers") or [])
    if drivers:
        lines.append(f"Its argument with us is {', '.join(drivers[:2])}" +
                     (" - and it wants an index clause for that" if "wants_clause" in said else "") + ".")
    if re.search(r"bought forward", notes, re.I):
        lines.append("It wrote to us itself that its material for next year is bought forward at fixed prices: "
                     "a rising material index is no reason for a higher price or an index clause, and we may "
                     "remind it of its letter.")
    if "asks_for_proof" in said:
        lines.append("It asks for the figures behind every statement: say nothing the claim lines do not show.")
    move = _movement(o)
    if move:
        lines.append(move)
    lines.append("Angle: " + angle(kind, low_authority))
    text = " ".join(lines)
    return re.sub(r"\s*\d[\d.,%]*\s*", " ", text).strip()  # never a figure, even from a note


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.parse_args(argv)
    data = build()
    print(f"{len(data['suppliers'])} suppliers observed -> {DOSSIER_FILE}")


if __name__ == "__main__":
    main()
