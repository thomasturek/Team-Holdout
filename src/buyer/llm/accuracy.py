"""How well the reader reads (V3, DIPLOMAT): precision and recall per Signals field on fixture e-mails.

    uv run python -m buyer.llm.accuracy                  # keyword rules, both fixture sets
    uv run python -m buyer.llm.accuracy --llm            # the reader model (needs the key; costs calls)

Scoring follows the fixtures' semantics: a boolean or tone in `expected` counts as one decision (a
true positive, false positive or false negative for booleans); every expected list item is a hit or
a miss; every `absent` item found is a false positive; `nonempty` fields must hold something.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "tests" / "fixtures"
SETS = ("supplier_emails.json", "adversarial_emails.json")  # development: tune rules and prompts on these
LOCKED = "adversarial_locked.json"  # held out: measure only (docs/V3_ROBUSTNESS_PLAN.md, dataset discipline)
BOOLS = ("cash_pressure", "capacity_issue", "final_offer_language", "approval_pending")


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["emails"]


def score(emails, read_fn) -> dict:
    """read_fn(message, last_decision) -> Signals. Returns per-field counts, metrics and misses."""
    counts = collections.defaultdict(lambda: collections.Counter())
    misses, right, by_cat = [], 0, collections.defaultdict(lambda: [0, 0])
    for e in emails:
        s = dataclasses.asdict(read_fn(e["message"], {"claims": e.get("last_claims", [])}))
        errs = []
        for field, want in e.get("expected", {}).items():
            got = s[field]
            if field in BOOLS:
                key = ("tp" if got else "fn") if want else ("fp" if got else "tn")
                counts[field][key] += 1
                if got != want:
                    errs.append(f"{field}: want {want}, got {got}")
            elif isinstance(want, list):
                for item in want:
                    counts[field]["tp" if item in got else "fn"] += 1
                if want == [] and got:
                    counts[field]["fp"] += len(got)
                missing = [x for x in want if x not in got]
                if missing or (want == [] and got):
                    errs.append(f"{field}: want {want}, got {got}")
            else:  # tone
                counts[field]["tp" if got == want else "fn"] += 1
                if got != want:
                    errs.append(f"{field}: want {want!r}, got {got!r}")
        for field, items in e.get("absent", {}).items():
            got = s[field] if isinstance(s[field], list) else [s[field]]
            found = [x for x in items if x in got]
            counts[field]["fp"] += len(found)
            if found:
                errs.append(f"{field}: must not hold {found}")
        for field in e.get("nonempty", []):
            counts[field]["tp" if s[field] else "fn"] += 1
            if not s[field]:
                errs.append(f"{field}: empty")
        cat = by_cat[e.get("category", "-")]
        cat[1] += 1
        if errs:
            misses.append((e["id"], errs))
        else:
            right += 1
            cat[0] += 1
    metrics = {}
    for field, c in sorted(counts.items()):
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        metrics[field] = {
            "precision": None if tp + fp == 0 else round(tp / (tp + fp), 3),
            "recall": None if tp + fn == 0 else round(tp / (tp + fn), 3),
            **{k: c[k] for k in ("tp", "fp", "fn", "tn")},
        }
    return {"emails": len(emails), "fully_right": right, "fields": metrics, "misses": misses,
            "categories": {k: f"{v[0]}/{v[1]}" for k, v in sorted(by_cat.items())}}  # fmt: skip


def rules_reader(message, last_decision):
    from .reader import rule_signals

    return rule_signals(message, last_decision)


def llm_reader(message, last_decision):
    from .reader import read

    return read(message, last_decision=last_decision).signals


def render(name, r) -> str:
    lines = [f"{name}: {r['fully_right']}/{r['emails']} fully right   categories {r['categories']}"]
    for field, m in r["fields"].items():
        lines.append(f"  {field:22s} precision {m['precision']}  recall {m['recall']}  "
                     f"(tp {m['tp']} fp {m['fp']} fn {m['fn']})")  # fmt: skip
    lines += [f"  MISS {i}: {'; '.join(errs)}" for i, errs in r["misses"]]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="the reader model instead of the keyword rules")
    ap.add_argument("--locked", action="store_true", help="also the locked set (never tune on it)")
    a = ap.parse_args(argv)
    fn = llm_reader if a.llm else rules_reader
    for name in SETS + ((LOCKED,) if a.locked else ()):
        print(render(name, score(load(name), fn)))


if __name__ == "__main__":
    main()
