"""V1 (Policy V0) against V2 (safe candidate ranking) on the same synthetic suppliers.

    uv run python -m buyer.sim.compare --episodes 200

Same seeds for both, so every case meets the same supplier draws. Prints mean, 10th percentile and
zero-score rate per policy and case, and V2's policy sources (how often it fell back).
"""

import argparse
import collections
import random
import statistics

from ..policy.policy import Policy
from ..policy.v2 import PolicyV2
from .env import episode, load_cases


class Counting(PolicyV2):
    """PolicyV2 that counts where its decisions came from."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.sources = collections.Counter()

    def decide(self, case, t, rival_best_c=float("inf"), **kw):
        sel = self.select(case, t, rival_best_c, commit=True, **kw)
        self.sources[sel.policy_source] += 1
        return sel.decision


def p10(xs):
    xs = sorted(xs)
    return xs[max(0, int(len(xs) * 0.1) - 1)] if xs else 0.0


def compare(cases, episodes=100, seed=0, params=None):
    out = {}
    v2 = Counting(Policy(params))
    for name, make in (("v1", lambda: Policy(params)), ("v2", lambda: v2)):
        per_case = {}
        for case in cases:
            scores = []
            for i in range(episodes):
                rng = random.Random(seed * 100_003 + i)
                scores.append(episode(case, make(), rng)["score"])
            per_case[case["case_id"]] = scores
        out[name] = per_case
    return out, v2.sources


def summary(scores):
    return {"mean": round(statistics.mean(scores), 4), "p10": round(p10(scores), 4),
            "zeros": round(sum(s <= 0 for s in scores) / len(scores), 3)}  # fmt: skip


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    cases = load_cases()
    out, sources = compare(cases, a.episodes, a.seed)
    for cid in out["v1"]:
        print(f"{cid:14s} v1 {summary(out['v1'][cid])}  v2 {summary(out['v2'][cid])}")
    allv1 = [s for xs in out["v1"].values() for s in xs]
    allv2 = [s for xs in out["v2"].values() for s in xs]
    print(f"{'ALL':14s} v1 {summary(allv1)}  v2 {summary(allv2)}")
    print("v2 sources:", dict(sources))


if __name__ == "__main__":
    main()
