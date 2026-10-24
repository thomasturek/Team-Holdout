"""Phase 2 evidence from the run logs (docs/PHASE2_SAFE_ARCHITECTURE.md, O4 and the activation gate).

    uv run python -m buyer.policy.report                 # every set under runs/
    uv run python -m buyer.policy.report --set practice

Per policy mode: decisions, where V2's decisions came from (v2_ml / v2_conservative / v0_fallback /
v0_rule), how often the shadow V2 agreed with V1, the most frequent fallback reasons, V2 latency,
and the scores of the sessions. Read-only: it never touches a session.
"""

import argparse
import collections
import statistics

from ..runtime.env import RUNS
from ..runtime.log import iter_logs, read


def collect(paths):
    by_mode = collections.defaultdict(lambda: {
        "decisions": 0, "sources": collections.Counter(), "agree": [], "reasons": collections.Counter(),
        "latency": [], "errors": 0, "scores": [],
    })  # fmt: skip
    for path in paths:
        events = read(path)
        mode = None
        for e in events:
            if e.get("kind") != "decision":
                continue
            tr = e.get("trace") or {}
            mode = tr.get("policy_mode") or "v1"
            row = by_mode[mode]
            row["decisions"] += 1
            v2 = tr.get("v2") or tr.get("shadow")
            if not v2:
                continue
            if "error" in v2:
                row["errors"] += 1
            row["sources"][v2.get("policy_source", "?")] += 1
            if "agrees" in v2:
                row["agree"].append(bool(v2["agrees"]))
            row["reasons"].update(r.split(" 0.")[0] for r in v2.get("ood_reasons") or [])
            if v2.get("latency_s") is not None:
                row["latency"].append(v2["latency_s"])
        result = next((e.get("result") for e in reversed(events) if e.get("kind") == "result"), None) or {}
        if mode and result.get("score") is not None:
            by_mode[mode]["scores"].append(result["score"])
    return by_mode


def render(by_mode) -> str:
    lines = []
    for mode, r in sorted(by_mode.items()):
        lines.append(f"[{mode}] decisions {r['decisions']}  V2 errors {r['errors']}")
        if r["sources"]:
            total = sum(r["sources"].values())
            lines.append("  sources: " + ", ".join(f"{k} {v / total:.0%}" for k, v in r["sources"].most_common()))
        if r["agree"]:
            lines.append(f"  shadow agrees with V1: {sum(r['agree']) / len(r['agree']):.0%} of {len(r['agree'])}")
        if r["reasons"]:
            lines.append("  top reasons: " + ", ".join(f"{k} ({v})" for k, v in r["reasons"].most_common(5)))
        if r["latency"]:
            lat = sorted(r["latency"])
            lines.append(f"  V2 latency: p50 {lat[len(lat) // 2]:.4f}s  max {lat[-1]:.4f}s")
        if r["scores"]:
            s = r["scores"]
            lines.append(f"  sessions {len(s)}  mean score {statistics.mean(s):.3f}  zeros {sum(x <= 0 for x in s)}")
    return "\n".join(lines) or "no decisions logged"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default=None, help="practice | sandbox | final | sim (default: all)")
    a = ap.parse_args(argv)
    print(render(collect(iter_logs(a.set, root=RUNS))))


if __name__ == "__main__":
    main()
