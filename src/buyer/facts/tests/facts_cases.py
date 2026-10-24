"""Case files for the facts tests."""

import json

from buyer.facts import package as pk


def practice_cases():
    """Stand-ins for the 19 practice cases, built from their trigger documents (doc:...-P01 ...):
    trigger, parts, the addressed supplier plus every supplier that quoted the part this month."""
    pkg = pk.load_package(pk.DEFAULT_DATA)
    docs = pkg.query("SELECT id, supplier_id, part_ids FROM documents WHERE id LIKE '%-P__' ORDER BY id")
    cases = []
    for d in docs:
        parts = d["part_ids"].split(";")
        others = pkg.query("SELECT DISTINCT supplier_id FROM quotes WHERE part_id = ? AND quote_date >= '2026-09-01' "
                           "AND supplier_id != ?", (parts[0], d["supplier_id"]))
        cases.append({"case_id": f"case:{d['id'][-3:]}", "trigger_doc": d["id"], "parts": parts,
                      "suppliers": [d["supplier_id"]] + [r["supplier_id"] for r in others]})
    return sorted(cases, key=lambda c: c["case_id"])


def kit_cases():
    folder = pk.REPO_ROOT / "starter-kit" / "arena_kit" / "sim_cases"
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]
