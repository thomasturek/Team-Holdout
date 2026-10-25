"""Compare two practice batches (their run `purpose`) per case and per supplier type.

    uv run python scripts/compare_batches.py angle-A angle-B
    uv run python scripts/compare_batches.py ab-A-off,ab-A-on ab-B-off,ab-B-on   # pooled: a main effect

For each side: score per case (mean over its runs), the supplier's first-reply concession in % of C
(where 88 % of all movement happens), grouped by the supplier's archetype - so the better variant can
be kept per type, not just overall. A side may pool several batches ("a,b").
"""

import glob
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from arena_kit.cost import total_cost

from buyer.facts.profile import lookup_profile

ROOT = Path(__file__).resolve().parents[1]


def runs(purpose):
    """Sessions of one batch, or of several pooled ("a,b": comma-separated run purposes)."""
    wanted = set(purpose.split(","))
    out = defaultdict(list)
    for f in sorted(glob.glob(str(ROOT / "runs" / "practice_sessions" / "*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        if (d.get("run") or {}).get("purpose") not in wanted:
            continue
        r, case = d.get("result") or {}, d["case"]
        sid = r.get("supplier_id") or case["suppliers"][0]
        sup = [m for m in d["threads"][sid]["messages"] if m.get("from") != "buyer" and m.get("term_sheets")]
        first = None
        if len(sup) >= 2:
            c0, c1 = (total_cost(case, m["term_sheets"][0]["terms"]) for m in sup[:2])
            first = (c0 - c1) / c0 * 100
        score = r.get("score") if r.get("deal") else 0.0
        part = (case.get("parts") or [None])[0]
        arch = (lookup_profile(sid, part) or {}).get("archetype", "unknown") if part else "unknown"
        out[case["case_id"][5:]].append({"score": score, "first": first, "arch": arch})
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def fmt(x, pct=False):
    return "   -  " if x is None else (f"{x:6.2f}" + ("%" if pct else ""))


def main(a, b):
    ra, rb = runs(a), runs(b)
    if not ra or not rb:
        sys.exit(f"no sessions for {a!r} ({len(ra)} cases) or {b!r} ({len(rb)} cases)")
    print(f"A = {a}\nB = {b}\n")
    print(f"{'case':5} {'type':18} {'A score':>8} {'B score':>8} {'diff':>6}   first reply A / B")
    by_type = defaultdict(lambda: {"a": [], "b": [], "fa": [], "fb": []})
    for cid in sorted(set(ra) | set(rb)):
        sa, sb = mean(x["score"] for x in ra.get(cid, [])), mean(x["score"] for x in rb.get(cid, []))
        fa, fb = mean(x["first"] for x in ra.get(cid, [])), mean(x["first"] for x in rb.get(cid, []))
        arch = (ra.get(cid) or rb.get(cid))[0]["arch"]
        diff = sb - sa if sa is not None and sb is not None else None
        n = f"(runs {len(ra.get(cid, []))}/{len(rb.get(cid, []))})"
        print(f"{cid:5} {arch:18} {fmt(sa):>8} {fmt(sb):>8} {fmt(diff):>6}   {fmt(fa, True)} / {fmt(fb, True)}   {n}")
        t = by_type[arch]
        t["a"] += [x["score"] for x in ra.get(cid, [])]
        t["b"] += [x["score"] for x in rb.get(cid, [])]
        t["fa"] += [x["first"] for x in ra.get(cid, [])]
        t["fb"] += [x["first"] for x in rb.get(cid, [])]
    print(f"\n{'per supplier type':22} {'A':>7} {'B':>7}   first reply A / B     -> keep (B needs +0.05)")
    for arch, t in sorted(by_type.items()):
        ma, mb = mean(t["a"]), mean(t["b"])
        keep = "-" if ma is None or mb is None else "B" if mb >= ma + 0.05 else "A"
        print(f"{arch:22} {fmt(ma):>7} {fmt(mb):>7}   {fmt(mean(t['fa']), True)} / {fmt(mean(t['fb']), True)}   -> {keep}")
    all_a = [x["score"] for v in ra.values() for x in v]
    all_b = [x["score"] for v in rb.values() for x in v]
    print(f"\noverall: A {mean(all_a):.3f} (n={len(all_a)})   B {mean(all_b):.3f} (n={len(all_b)})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
