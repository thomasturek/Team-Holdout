import argparse
import json
import random
import statistics

from ..policy.policy import BOUNDS, DEFAULTS, PARAMS_FILE, Policy, load_params
from .env import episode, load_cases


def evaluate(params, cases, episodes, seed):
    rng = random.Random(seed)
    policy = Policy(params)
    scores = [episode(rng.choice(cases), policy, rng)["score"] for _ in range(episodes)]
    scores.sort()
    return statistics.mean(scores), scores[len(scores) // 10], sum(x == 0 for x in scores) / len(scores)


def train(iters, pop, episodes, elite_frac=0.25, seed=0, start=None):
    cases = load_cases()
    if not cases:
        raise SystemExit("no case files: put practice case files into runs/cases/")
    rng = random.Random(seed)
    start = start or load_params()
    mean = {k: start.get(k, DEFAULTS[k]) for k in BOUNDS}
    std = {k: (hi - lo) / 4 for k, (lo, hi) in BOUNDS.items()}
    best = (evaluate(mean, cases, episodes, seed), mean)
    print(f"start  mean {best[0][0]:.3f}  p10 {best[0][1]:.3f}  ({len(cases)} cases)")
    for it in range(iters):
        candidates = []
        for _ in range(pop):
            cand = {k: min(hi, max(lo, rng.gauss(mean[k], std[k]))) for k, (lo, hi) in BOUNDS.items()}
            candidates.append((evaluate(cand, cases, episodes, seed + it + 1), cand))
        candidates.sort(key=lambda x: x[0][0], reverse=True)
        elite = [c for _, c in candidates[: max(2, int(pop * elite_frac))]]
        for k in BOUNDS:
            vals = [e[k] for e in elite]
            mean[k], std[k] = statistics.mean(vals), max(statistics.pstdev(vals), 1e-3)
        if candidates[0][0][0] > best[0][0]:
            best = candidates[0]
        print(f"iter {it + 1:2d}  best {candidates[0][0][0]:.3f}  p10 {candidates[0][0][1]:.3f}  overall {best[0][0]:.3f}")
    check = evaluate(best[1], cases, episodes * 2, seed + 10_000)
    print(f"holdout  mean {check[0]:.3f}  p10 {check[1]:.3f}  zeros {check[2]:.1%}")
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=15)
    ap.add_argument("--pop", type=int, default=32)
    ap.add_argument("--episodes", type=int, default=80)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--save", action="store_true", help=f"write the result to {PARAMS_FILE}")
    a = ap.parse_args()
    params = train(a.iters, a.pop, a.episodes, seed=a.seed)
    print(json.dumps({k: round(v, 4) for k, v in params.items()}, indent=2))
    if a.save:
        PARAMS_FILE.write_text(json.dumps({k: round(v, 4) for k, v in params.items()}, indent=2) + "\n")
        print(f"saved {PARAMS_FILE}")


if __name__ == "__main__":
    main()
