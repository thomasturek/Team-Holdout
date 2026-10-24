import argparse
import json
import random
import statistics
from pathlib import Path

from ..policy.policy import Policy, ThreadState
from ..runtime.env import RUNS
from ..runtime.log import iter_logs, read
from .env import load_cases
from .population import RANGES_FILE, load_ranges, sample
from .supplier import SyntheticSupplier

FIT = {
    "concede": (0.02, 0.9),
    "max_concession": (0.0, 0.15),
    "open_margin": (-0.05, 0.35),
    "cash_rate": (0.0, 0.4),
    "walk_after_final": (0.0, 1.0),
}
WIDTH = {"concede": 0.1, "max_concession": 0.02, "open_margin": 0.06, "cash_rate": 0.04, "walk_after_final": 0.2}


def from_events(events):
    head = next((e for e in events if e.get("kind") == "case"), None)
    opening = next((e for e in events if e.get("kind") == "opening"), None)
    if not head or not opening:
        return None
    threads = {sid: list(msgs) for sid, msgs in opening["threads"].items()}
    for e in events:
        if e.get("kind") == "sent" and "action" not in (e.get("message") or {}):
            threads.setdefault(e["supplier_id"], []).append({**e["message"], "from": "buyer"})
        elif e.get("kind") == "reply":
            threads.setdefault(e["supplier_id"], []).append(e["message"])
    result = next((e["result"] for e in events if e.get("kind") == "result"), {})
    return {"case": head["case"], "threads": threads, "result": result}


def sessions(root=RUNS, sets=("sandbox", "practice")):
    for s in sets:
        for p in iter_logs(s, root):
            rec = from_events(read(p))
            if rec:
                yield rec


def sheets(m):
    return [s.get("terms", s) for s in m.get("term_sheets") or []]


def thread_stats(case, messages):
    out = {"step": [], "faster": [], "open_over_current": None, "total_drop": None, "final_round": None,
           "walked": False, "pushed_after_final": False}
    current = case["buyer"].get("current_unit_price") or case["buyer"].get("fallback_unit_price")
    supplier = [m for m in messages if m.get("from") != "buyer"]
    if not supplier or not sheets(supplier[0]) or sheets(supplier[0])[0].get("unit_price") is None:
        return out
    first = sheets(supplier[0])[0]["unit_price"]
    if current:
        out["open_over_current"] = first / current
    last, ours, final_seen, rnd = first, [], False, 0
    for m in messages[1:]:
        if m.get("from") == "buyer":
            ours = sheets(m)
            if final_seen:
                out["pushed_after_final"] = True
            continue
        rnd += 1
        if m.get("status") == "walked_away":
            out["walked"] = True
            break
        cur = sheets(m)
        if not cur or cur[0].get("unit_price") is None:
            continue
        price, terms = cur[0]["unit_price"], cur[0]
        out["step"].append((last - price) / first)
        days = [s.get("payment_days") for s in ours if s.get("payment_days") is not None]
        if len(set(days)) > 1 and terms.get("payment_days") is not None:
            out["faster"].append(1.0 if terms["payment_days"] == min(days) else 0.0)
        if m.get("status") == "final_offer" and out["final_round"] is None:
            out["final_round"] = rnd
            final_seen = True
        last = price
    out["total_drop"] = (first - last) / first
    return out


def summary(recs):
    stats = [thread_stats(r["case"], msgs) for r in recs for msgs in r["threads"].values()]
    def pick(k):
        return [s[k] for s in stats if s[k] is not None]

    def flat(k):
        return [x for s in stats for x in s[k]]

    def med(v):
        return statistics.median(v) if v else None

    pushed = [s for s in stats if s["pushed_after_final"]]
    return {
        "threads": len(stats),
        "open_over_current": med(pick("open_over_current")),
        "step": med([x for x in flat("step") if x > 0]),
        "total_drop": med(pick("total_drop")),
        "final_round": med(pick("final_round")),
        "faster_share": statistics.mean(flat("faster")) if flat("faster") else None,
        "walk_after_push": statistics.mean(s["walked"] for s in pushed) if pushed else None,
    }


def simulate(ranges, n, seed, cases, policy):
    rng = random.Random(seed)
    recs = []
    for _ in range(n):
        case = rng.choice(cases)
        threads = {}
        for sid in case["suppliers"]:
            p, prof = sample(case, rng, ranges)
            s = SyntheticSupplier(case, sid, p, rng)
            o = s.opening()
            msgs = [{"from": "supplier", "status": "open", "term_sheets": [o]}]
            t = ThreadState(sid, o["term_sheet_id"], o["terms"], "open", s.standard,
                            case.get("round_limit", 10), prof, their_prices=[o["terms"]["unit_price"]])
            while t.rounds_left > 0 and t.status not in ("walked_away", "agreed"):
                d = policy.decide(case, t)
                if d.kind != "send":
                    break
                msgs.append({"from": "buyer", "term_sheets": [{"terms": x} for x in d.term_sheets]})
                rep = s.respond(d.term_sheets)
                t.rounds_left -= 1
                t.status, t.standing_id, t.standing_terms = rep["status"], rep["term_sheet_id"], rep["terms"]
                t.their_prices.append(rep["terms"]["unit_price"])
                msgs.append({"from": "supplier", "status": rep["status"], "term_sheets": [rep]})
            threads[sid] = msgs
        recs.append({"case": case, "threads": threads})
    return recs


def distance(a, b):
    scale = {"open_over_current": 0.05, "step": 0.01, "total_drop": 0.02, "final_round": 2.0,
             "faster_share": 0.2, "walk_after_push": 0.2}
    return sum(((a[k] - b[k]) / s) ** 2 for k, s in scale.items() if a.get(k) is not None and b.get(k) is not None)


def ranges_from(centers, base):
    r = dict(base)
    for k, c in centers.items():
        lo, hi = FIT[k]
        r[k] = (max(lo, c - WIDTH[k]), min(hi, c + WIDTH[k]))
    return r


def fit(target, iters=12, pop=24, n=120, seed=0):
    base, cases, policy = load_ranges(), load_cases(), Policy()
    rng = random.Random(seed)
    mean = {k: statistics.mean(base[k]) if isinstance(base.get(k), tuple) else statistics.mean(FIT[k]) for k in FIT}
    std = {k: (hi - lo) / 8 for k, (lo, hi) in FIT.items()}

    def score(c):
        return distance(summary(simulate(ranges_from(c, base), n, seed, cases, policy)), target)

    best = (score(mean), dict(mean))
    for _ in range(iters):
        cands = []
        for _ in range(pop):
            c = {k: min(FIT[k][1], max(FIT[k][0], rng.gauss(mean[k], std[k]))) for k in FIT}
            cands.append((score(c), c))
        cands.sort(key=lambda x: x[0])
        elite = [c for _, c in cands[: max(2, pop // 4)]]
        for k in FIT:
            vals = [e[k] for e in elite]
            mean[k], std[k] = statistics.mean(vals), max(statistics.pstdev(vals), 1e-3)
        if cands[0][0] < best[0]:
            best = cands[0]
        print(f"distance {best[0]:.3f}")
    fitted = ranges_from(best[1], base)
    return {k: [round(v, 4) for v in fitted[k]] for k in FIT}, summary(simulate(fitted, n, seed + 1, cases, policy))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, default=RUNS)
    ap.add_argument("--sets", nargs="+", default=["sandbox", "practice"])
    ap.add_argument("--iters", type=int, default=12)
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    recs = list(sessions(a.runs, a.sets))
    if not recs:
        raise SystemExit(f"no session logs under {a.runs}/{{{','.join(a.sets)}}}")
    target = summary(recs)
    print("real ", json.dumps(target))
    new, check = fit(target, iters=a.iters)
    print("sim  ", json.dumps(check))
    print(json.dumps(new, indent=2))
    if a.save:
        current = json.loads(RANGES_FILE.read_text()) if RANGES_FILE.is_file() else {}
        RANGES_FILE.write_text(json.dumps({**current, **new}, indent=2) + "\n")
        print(f"saved {RANGES_FILE}")


if __name__ == "__main__":
    main()
