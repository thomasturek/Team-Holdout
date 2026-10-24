"""THE ANALYST, Phase 2 (A2): rank safe candidates. The ranker never builds terms or prices.

Model: an ensemble of small linear value functions over the candidate features
(`candidates.features`). Each member scores every valid candidate; the ensemble's ranking is the
mean, and how often members disagree on the winner feeds the uncertainty check (`ood.py`).

`ranker.json` (next to this file) holds trained weights: {"members": [{feature: weight, ...}, ...]}.
Without it the ranker uses PRIOR - hand-set weights that reproduce V0's preferences (keep V0's move
unless another safe candidate saves clearly more). That is a placeholder until the Analyst trains
real weights on the simulator and the shadow logs; with it V2 behaves like V0 plus the shield.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

RANKER_FILE = Path(__file__).with_name("ranker.json")

PRIOR = {
    "bias:v0": 0.02,  # V0's own move, unless another candidate is clearly better
    "bias:price_step": 0.0,
    "bias:cash_trade": 0.0,
    "bias:accept": 0.0,
    "bias:walk": -0.02,
    "saving_vs_standing": 1.0,  # EUR the candidate would save vs the standing offer, / C_open
    "price_vs_floor": 0.0,
    "accept_x_rounds_left_frac": -0.02,  # accepting early leaves rounds unused
    "send_x_status_final": -0.03,  # pushing after a final offer risks the walk
    "send_x_floor_gap": -0.5,  # asking below the floor estimate rarely lands: (floor - price) / floor if > 0
}
MEMBERS = 5
NOISE = 0.25  # relative weight noise of the prior ensemble members


def _x(f: dict) -> dict:
    """Feature vector incl. the interactions the weights refer to."""
    kind, fam = f.get("kind"), f.get("family")
    x = {k: float(v) for k, v in f.items() if isinstance(v, int | float) and not isinstance(v, bool)}
    x.update({k: float(v) for k, v in f.items() if isinstance(v, bool)})
    x[f"bias:{fam}"] = 1.0
    x["accept_x_rounds_left_frac"] = float(kind == "accept") * x.get("rounds_left_frac", 0.0)
    x["send_x_status_final"] = float(kind == "send") * x.get("status_final", 0.0)
    gap = -x.get("price_vs_floor", 0.0) if f.get("floor_known") else 0.0
    x["send_x_floor_gap"] = float(kind == "send") * max(0.0, gap)
    return x


class Ranker:
    def __init__(self, members=None, seed=0):
        if members is None:
            members = load_members()
        if not members:
            rng = random.Random(seed)
            members = [PRIOR] + [
                {k: w * (1 + rng.uniform(-NOISE, NOISE)) for k, w in PRIOR.items()} for _ in range(MEMBERS - 1)
            ]
        self.members = members
        self.trained = RANKER_FILE.is_file()

    def scores(self, cand) -> list[float]:
        x = _x(cand.features)
        return [sum(w * x.get(k, 0.0) for k, w in m.items()) for m in self.members]

    def rank(self, cands):
        """Valid candidates best first: [(candidate, mean value, member values)], and the share of
        members whose own winner differs from the ensemble's (0 = all agree)."""
        valid = [c for c in cands if c.valid]
        if not valid:
            return [], 1.0
        rows = [(c, s) for c in valid for s in [self.scores(c)]]
        ranked = sorted(((c, sum(s) / len(s), s) for c, s in rows), key=lambda r: -r[1])
        top = ranked[0][0]
        winners = [max(rows, key=lambda r, i=i: r[1][i])[0] for i in range(len(self.members))]
        disagreement = sum(w is not top for w in winners) / len(winners)
        return ranked, disagreement


def load_members(path=RANKER_FILE):
    p = Path(path)
    if not p.is_file():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("members") or None
