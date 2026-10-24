import argparse
import json
import math
import random
import statistics
from collections import defaultdict

from ..policy.policy import Policy, load_params
from ..runtime.agent import explore_params
from ..runtime.harvest import version
from ..runtime.log import iter_logs, read
from .calibrate import from_events, sheets
from .env import episode
from .population import load_ranges, sample
from .supplier import SyntheticSupplier


def anchored(case, sid, opening, ranges, rng):
    p, _ = sample(case, rng, ranges)
    p.full_cost = opening["unit_price"] / (1 + p.open_margin)
    if opening.get("payment_days") is not None:
        p.std_payment_days = opening["payment_days"]
    p.std_incoterm = opening.get("incoterm") or p.std_incoterm
    p.std_lead_time = opening.get("lead_time_days") or p.std_lead_time
    return SyntheticSupplier(case, sid, p, rng)


def replay_thread(case, sid, messages, ranges, draws, rng):
    supplier = [m for m in messages if m.get("from") != "buyer"]
    if not supplier or not sheets(supplier[0]) or sheets(supplier[0])[0].get("unit_price") is None:
        return []
    opening = sheets(supplier[0])[0]
    first = opening["unit_price"]
    fakes = [anchored(case, sid, opening, ranges, rng) for _ in range(draws)]
    alive = [True] * draws
    out, ours = [], None
    for m in messages[1:]:
        if m.get("from") == "buyer":
            ours = [s for s in sheets(m) if s.get("unit_price") is not None]
            continue
        real = sheets(m)
        if not ours or not real or real[0].get("unit_price") is None:
            continue
        preds, statuses = [], []
        for i, f in enumerate(fakes):
            if not alive[i]:
                continue
            rep = f.respond([dict(s) for s in ours])
            statuses.append(rep["status"])
            if rep["status"] == "walked_away":
                alive[i] = False
                continue
            preds.append(rep["terms"]["unit_price"])
        if preds:
            err = (statistics.mean(preds) - real[0]["unit_price"]) / first * 100
            hit = statistics.mean(1.0 if s == m.get("status") else 0.0 for s in statuses)
            out.append((err, hit))
        ours = None
    return out


def replay_error(recs, ranges=None, draws=8, seed=0):
    ranges = ranges or load_ranges()
    rng = random.Random(seed)
    rows = [r for rec in recs for sid, msgs in rec["threads"].items()
            for r in replay_thread(rec["case"], sid, msgs, ranges, draws, rng)]
    if not rows:
        return None
    errs = [e for e, _ in rows]
    return {
        "replies": len(rows),
        "mae_pct": round(statistics.mean(abs(e) for e in errs), 3),
        "rmse_pct": round(math.sqrt(statistics.mean(e * e for e in errs)), 3),
        "bias_pct": round(statistics.mean(errs), 3),
        "status_accuracy": round(statistics.mean(h for _, h in rows), 3),
    }


def transfer_error(logs, episodes=60, seed=0):
    real = defaultdict(list)
    cases, overrides = {}, {}
    for events in logs:
        head = next((e for e in events if e.get("kind") == "case"), None)
        result = next((e["result"] for e in events if e.get("kind") == "result"), None)
        if not head or result is None or head.get("run", {}).get("probe"):
            continue
        params = head.get("run", {}).get("params") or {}
        key = (head["case_id"], json.dumps(params, sort_keys=True))
        real[key].append(result.get("score") or 0.0)
        cases[head["case_id"]], overrides[key] = head["case"], params
    base = load_params()
    rows = []
    for key, scores in real.items():
        rng = random.Random(seed)
        policy = Policy({**base, **overrides[key]})
        sim = statistics.mean(episode(cases[key[0]], policy, rng)["score"] for _ in range(episodes))
        rows.append((key[0], statistics.mean(scores), sim))
    if not rows:
        return None
    errs = [s - r for _, r, s in rows]
    by_case = defaultdict(list)
    for c, r, s in rows:
        by_case[c].append((r, s))
    rank = {}
    for c, pairs in by_case.items():
        if len(pairs) > 2:
            rank[c] = round(spearman([r for r, _ in pairs], [s for _, s in pairs]), 3)
    return {
        "param_sets": len(rows),
        "mae": round(statistics.mean(abs(e) for e in errs), 3),
        "rmse": round(math.sqrt(statistics.mean(e * e for e in errs)), 3),
        "bias": round(statistics.mean(errs), 3),
        "rank_corr_by_case": rank,
    }


def spearman(a, b):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r

    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=["sandbox"])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--draws", type=int, default=8)
    ap.add_argument("--episodes", type=int, default=60)
    a = ap.parse_args()
    explore = None if a.all else version(explore_params())
    logs = []
    for s in a.sets:
        for p in iter_logs(s):
            events = read(p)
            head = next((e for e in events if e.get("kind") == "case"), {})
            if explore is None or head.get("run", {}).get("explore") == explore:
                logs.append(events)
    recs = [r for r in (from_events(e) for e in logs) if r]
    print("simulator vs real replies:", json.dumps(replay_error(recs, draws=a.draws)))
    print("simulated vs real score:  ", json.dumps(transfer_error(logs, a.episodes)))


if __name__ == "__main__":
    main()
