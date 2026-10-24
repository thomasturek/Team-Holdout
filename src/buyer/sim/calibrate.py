import argparse
import json
import random
import statistics
from pathlib import Path

from ..policy.policy import Policy, ThreadState
from ..runtime.env import RUNS
from ..runtime.agent import explore_params
from ..runtime.harvest import version
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
    "insist_share": (0.0, 1.0),
    "reciprocity": (0.0, 1.5),
    "insult_pct": (0.0, 30.0),
    "first_drop": (0.0, 0.12),
    "lead_premium_pct_week": (0.0, 5.0),
}
WIDTH = {"concede": 0.1, "max_concession": 0.02, "open_margin": 0.06, "cash_rate": 0.04, "walk_after_final": 0.2, "insist_share": 0.15, "reciprocity": 0.2, "insult_pct": 4.0, "first_drop": 0.015, "lead_premium_pct_week": 0.5}


def replay_error(*args, **kwargs):
    from .metrics import replay_error as run

    return run(*args, **kwargs)


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


def sessions(root=RUNS, sets=("sandbox", "practice"), explore=None):
    for s in sets:
        for p in iter_logs(s, root):
            events = read(p)
            rec = from_events(events)
            head = next((e for e in events if e.get("kind") == "case"), {})
            if rec and (explore is None or head.get("run", {}).get("explore") == explore):
                yield rec


def sheets(m):
    return [s.get("terms", s) for s in m.get("term_sheets") or []]


def thread_stats(case, messages):
    out = {"step": [], "revert": [], "pairs": [], "open_discount": None, "open_over_current": None, "total_drop": None, "final_round": None,
           "walked": False, "pushed_after_final": False}
    current = case["buyer"].get("current_unit_price") or case["buyer"].get("fallback_unit_price")
    supplier = [m for m in messages if m.get("from") != "buyer"]
    if not supplier or not sheets(supplier[0]) or sheets(supplier[0])[0].get("unit_price") is None:
        return out
    first = sheets(supplier[0])[0]["unit_price"]
    std = sheets(supplier[0])[0].get("payment_days")
    if current:
        out["open_over_current"] = first / current
    last, ours, final_seen, rnd = first, [], False, 0
    our_prev, our_step = None, None
    for m in messages[1:]:
        if m.get("from") == "buyer":
            ours = sheets(m)
            p0 = ours[0].get("unit_price") if ours else None
            if p0 is not None:
                if our_prev is None:
                    out["open_discount"] = (first - p0) / first
                else:
                    our_step = (p0 - our_prev) / first
                our_prev = p0
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
        if our_step is not None:
            out["pairs"].append((our_step, (last - price) / first))
            our_step = None
        days = [s.get("payment_days") for s in ours if s.get("payment_days") is not None]
        if std is not None and days and days[0] != std and terms.get("payment_days") is not None:
            out["revert"].append(1.0 if terms["payment_days"] == std else 0.0)
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
    pairs = flat("pairs")
    sxx = sum(x * x for x, _ in pairs)
    lows = [(s["open_discount"], s["total_drop"]) for s in stats if s["open_discount"] is not None and s["total_drop"] is not None]
    lowball = None
    if len(lows) > 2:
        mx, my = statistics.mean(x for x, _ in lows), statistics.mean(y for _, y in lows)
        vx = sum((x - mx) ** 2 for x, _ in lows)
        lowball = sum((x - mx) * (y - my) for x, y in lows) / vx if vx > 0 else None
    return {
        "recip_slope": sum(x * y for x, y in pairs) / sxx if sxx > 0 else None,
        "lowball_slope": lowball,
        "threads": len(stats),
        "open_over_current": med(pick("open_over_current")),
        "step": med([x for x in flat("step") if x > 0]),
        "total_drop": med(pick("total_drop")),
        "final_round": med(pick("final_round")),
        "revert_share": statistics.mean(flat("revert")) if flat("revert") else None,
        "walk_after_push": statistics.mean(s["walked"] for s in pushed) if pushed else None,
    }


def simulate(ranges, n, seed, cases, policy):
    rng = random.Random(seed)
    recs = []
    players = [Policy({**policy.p, **x}) for x in explore_params()]
    for i in range(n):
        case = rng.choice(cases)
        player = players[i % len(players)]
        threads = {}
        for sid in case["suppliers"]:
            p, prof = sample(case, rng, ranges)
            s = SyntheticSupplier(case, sid, p, rng)
            o = s.opening()
            msgs = [{"from": "supplier", "status": "open", "term_sheets": [o]}]
            t = ThreadState(sid, o["term_sheet_id"], o["terms"], "open", s.standard,
                            case.get("round_limit", 10), prof, their_prices=[o["terms"]["unit_price"]])
            while t.rounds_left > 0 and t.status not in ("walked_away", "agreed"):
                d = player.decide(case, t)
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
    scale = {"recip_slope": 0.1, "lowball_slope": 0.1, "open_over_current": 0.05, "step": 0.01, "total_drop": 0.02, "final_round": 2.0,
             "revert_share": 0.1, "walk_after_push": 0.2}
    return sum(((a[k] - b[k]) / s) ** 2 for k, s in scale.items() if a.get(k) is not None and b.get(k) is not None)


def ranges_from(centers, base):
    r = dict(base)
    for k, c in centers.items():
        lo, hi = FIT[k]
        r[k] = (max(lo, c - WIDTH[k]), min(hi, c + WIDTH[k]))
    return r


def fit(target, iters=12, pop=24, n=120, seed=0, recs=None):
    base, cases, policy = load_ranges(), load_cases(), Policy()
    rng = random.Random(seed)
    mean = {k: statistics.mean(base[k]) if isinstance(base.get(k), tuple) else statistics.mean(FIT[k]) for k in FIT}
    std = {k: (hi - lo) / 8 for k, (lo, hi) in FIT.items()}

    def score(c):
        r = ranges_from(c, base)
        d = distance(summary(simulate(r, n, seed, cases, policy)), target)
        if recs:
            e = replay_error(recs, r, draws=4, seed=seed)
            if e:
                d += (e["mae_pct"] / 1.0) ** 2 + ((1 - e["status_accuracy"]) / 0.1) ** 2
        return d

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
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    recs = list(sessions(a.runs, a.sets, None if a.all else version(explore_params())))
    if not recs:
        raise SystemExit(f"no session logs under {a.runs}/{{{','.join(a.sets)}}}")
    target = summary(recs)
    print("real ", json.dumps(target))
    new, check = fit(target, iters=a.iters, recs=recs)
    print("sim  ", json.dumps(check))
    print("replay", json.dumps(replay_error(recs, ranges_from({k: statistics.mean(v) for k, v in new.items()}, load_ranges()))))
    print(json.dumps(new, indent=2))
    if a.save:
        current = json.loads(RANGES_FILE.read_text()) if RANGES_FILE.is_file() else {}
        RANGES_FILE.write_text(json.dumps({**current, **new}, indent=2) + "\n")
        print(f"saved {RANGES_FILE}")


if __name__ == "__main__":
    main()
