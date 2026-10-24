"""V3 harness (docs/V3_ROBUSTNESS_PLAN.md, OPERATOR): adversarial suites, property checks, calibration.

    uv run python -m buyer.sim.robust generate --split development --n 120
    uv run python -m buyer.sim.robust run --split development --episodes 3
    BUYER_LOCKED_EVAL=1 uv run python -m buyer.sim.robust run --split locked      # once per release candidate

Every adversarial case (sim/mutations.py) is played by V1 (Policy V0) and V2 (PolicyV2) on the same
synthetic supplier draws. Each episode is checked against the case's expected properties; the report
gives score statistics, property failures clustered by mutation, OOD fallback recall, false-fallback
rate, and V2's confidence calibration table.

Suites live in tests/generated/{train,development,locked}/suite.json and are reproducible from their
seeds (train 0-999, development 1000-1999, locked 2000-2999). The locked suite is read only with
BUYER_LOCKED_EVAL=1; training code never imports this module.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import math
import os
import random
import statistics
import time
from pathlib import Path

from arena_kit.cost import must_haves_ok, score, total_cost

from ..facts import shield
from ..interfaces import AdversarialCase
from ..policy import ood
from ..policy.policy import Policy, ThreadState, alternative_cost
from ..policy.v2 import PolicyV2
from .env import load_cases
from .mutations import adversarial
from .population import sample
from .supplier import SyntheticSupplier

ROOT = Path(__file__).resolve().parents[3]
SUITES = ROOT / "tests" / "generated"
SPLITS = {"train": range(0, 1000), "development": range(1000, 2000), "locked": range(2000, 3000)}
BANDS = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01))
WORSE_BY = 0.05  # V2 scoring this much below V1 on the same draw counts as an unsafe decision


class LockedSuite(PermissionError):
    pass


# --- suites ----------------------------------------------------------------------------------------------
def generate(split, n, parents=None) -> list[AdversarialCase]:
    parents = parents or load_cases()
    out, seeds = [], iter(SPLITS[split])
    while len(out) < n:
        seed = next(seeds)
        adv = adversarial(parents[seed % len(parents)], seed)
        if adv is not None:
            out.append(adv)
    return out


def save(split, suite):
    path = SUITES / split / "suite.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([dataclasses.asdict(a) for a in suite], indent=1, default=str), encoding="utf-8")
    return path


def load_suite(split) -> list[AdversarialCase]:
    if split == "locked" and os.environ.get("BUYER_LOCKED_EVAL") != "1":
        raise LockedSuite("the locked suite is for the release candidate's single evaluation: BUYER_LOCKED_EVAL=1")
    path = SUITES / split / "suite.json"
    return [AdversarialCase(**a) for a in json.loads(path.read_text(encoding="utf-8"))]


# --- one episode -----------------------------------------------------------------------------------------
class Recorder:
    """Wraps a policy: records every Decision, and V2's selections."""

    def __init__(self, policy):
        self.policy, self.decisions, self.selections = policy, [], []

    def cost(self, case, t):
        return self.policy.cost(case, t)

    def decide(self, case, t, rival_best_c=math.inf):
        if isinstance(self.policy, PolicyV2):
            sel = self.policy.select(case, t, rival_best_c, commit=True)
            self.selections.append(sel)
            d = sel.decision
        else:
            d = self.policy.decide(case, t, rival_best_c=rival_best_c)
        self.decisions.append((t.supplier_id, d))
        return d


def _profile(base, ov):
    if "profile_replace" in ov:
        return dict(ov["profile_replace"])
    p = {**base, "archetype": "family_foundry", "floor_confidence": 0.1, **ov.get("profile", {})}
    if ov.get("profile_floor_factor") and p.get("floor_estimate"):
        p["floor_estimate"] *= ov["profile_floor_factor"]
    return p


def episode(adv: AdversarialCase, policy, seed) -> dict:
    """Play one adversarial case against fresh synthetic suppliers drawn from `seed`."""
    case = json.loads(json.dumps(adv.case))
    ov = (adv.scripted_responses or [{}])[0]
    rng = random.Random(seed)
    suppliers, threads = {}, {}
    for sid in case["suppliers"]:
        params, profile = sample(case, rng)
        params = dataclasses.replace(params, **ov.get("supplier", {}))
        s = SyntheticSupplier(case, sid, params, rng)
        suppliers[sid] = s
        o = s.opening()
        threads[sid] = ThreadState(sid, o["term_sheet_id"], o["terms"], "open", s.standard,
                                   case.get("round_limit", 10), profile=_profile(profile, ov),
                                   their_prices=[o["terms"]["unit_price"]])  # fmt: skip
    if "alt_vs_opening" in ov:  # the alternative relative to the cheapest opening quote
        t0 = min(threads.values(), key=lambda t: total_cost(case, t.standing_terms, t.standard))
        terms = {**t0.standard, **case.get("fixed_terms", {}), **t0.standing_terms}
        terms["unit_price"] = round(terms["unit_price"] * (1 + ov["alt_vs_opening"]), 4)
        case["buyer"]["alternative"] = {"kind": "quote", "terms": terms}

    def cost(t, std):
        return total_cost(case, t, std)

    opening = [cost(t.standing_terms, t.standard) for t in threads.values()
               if must_haves_ok(case, t.standing_terms, t.standard)]  # fmt: skip
    c_open = min(opening) if opening else math.inf
    c_alt = alternative_cost(case)
    c_best = min([s.best_package(cost) for s in suppliers.values()] + [c_alt])
    rec = Recorder(policy)
    out = {"violations": [], "deal": None, "rounds": 0, "error": None}
    t_start = time.monotonic()
    try:
        _play(case, rec, threads, suppliers, out)
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        out["violations"].append("no_exception")
    c_deal = out.pop("c_deal", c_alt)
    out.update(score=0.0 if c_deal == math.inf else score(c_open, c_deal, c_best), c_open=c_open, c_alt=c_alt,
               latency_s=time.monotonic() - t_start)  # fmt: skip
    out["violations"] += _check(adv, case, rec, threads, out)
    sel = rec.selections[0] if rec.selections else None
    out["first"] = None if sel is None else {"source": sel.policy_source, "confidence": sel.confidence,
                                             "reasons": sel.ood_reasons}  # fmt: skip
    out["kinds"] = collections.Counter(d.kind for _, d in rec.decisions)
    return out


def _play(case, rec, threads, suppliers, out):
    while True:
        live = [t for t in threads.values() if t.status not in ("walked_away", "no_bid")]
        if not live:
            return
        for t in live:
            rival = min((rec.cost(case, o) for o in live if o is not t and o.standing_id), default=math.inf)
            d = rec.decide(case, t, rival_best_c=rival)
            if d.kind == "accept":
                out.update(deal={"supplier_id": t.supplier_id, "sheet_id": d.accept_sheet_id,
                                 "terms": dict(t.standing_terms), "standard": dict(t.standard)},  # fmt: skip
                           c_deal=total_cost(case, t.standing_terms, t.standard))
                return
            if d.kind == "walk":
                t.status = "walked_away"
                continue
            out["rounds"] += 1
            t.rounds_left -= 1
            reply = suppliers[t.supplier_id].respond(d.term_sheets)
            t.status, t.standing_id, t.standing_terms = reply["status"], reply["term_sheet_id"], reply["terms"]
            t.their_prices.append(reply["terms"]["unit_price"])
            if t.rounds_left <= 0 and t.status not in ("walked_away", "no_bid"):
                t.rounds_left = 1
            if out["rounds"] > 200:
                raise RuntimeError("no end after 200 rounds")


def _check(adv, case, rec, threads, out) -> list[str]:
    v = []
    props = set(adv.expected_properties)
    if "no_invalid_sheet" in props:
        for _, d in rec.decisions:
            if d.kind == "send" and (not 1 <= len(d.term_sheets) <= 3
                                     or any(shield.check_terms(case, s) for s in d.term_sheets)):  # fmt: skip
                v.append("no_invalid_sheet")
                break
    deal = out["deal"]
    if deal:
        if "must_not_break_must_have" in props and not must_haves_ok(case, deal["terms"], deal["standard"]):
            v.append("must_not_break_must_have")
        if "must_not_accept_worse_than_alternative" in props and out.get("c_deal", 0) >= out["c_alt"]:
            if total_cost(case, deal["terms"], deal["standard"]) >= out["c_alt"]:
                v.append("must_not_accept_worse_than_alternative")
        if "must_not_accept_opening" in props and str(deal["sheet_id"]).endswith("-0"):
            v.append("must_not_accept_opening")
    if "must_close_within_round_limit" in props:
        limit = case.get("round_limit", 10)
        sends = collections.Counter(sid for sid, d in rec.decisions if d.kind == "send")
        if any(n > limit for n in sends.values()):
            v.append("must_close_within_round_limit")
    sel = rec.selections[0] if rec.selections else None
    if sel is not None:
        if "must_fallback" in props and sel.policy_source not in ("v0_fallback", "v0_rule"):
            v.append("must_fallback")
        if "must_fallback_or_conservative" in props and sel.policy_source == "v2_ml":
            v.append("must_fallback_or_conservative")
    return v


# --- novelty ---------------------------------------------------------------------------------------------
def novelty(adv: AdversarialCase, train_cases=None) -> tuple[str, float, list[str]]:
    """Measured distribution (gate 4): far_ood for an unseen type / field / goal, no supplier profile, or a
    case beyond ood.FAR_DISTANCE from every training case; near_ood for missing or wrong beliefs about
    the supplier, a supplier that differs from them, or beyond ood.NEAR_DISTANCE; else in_distribution."""
    types, fields, goals = ood.familiar()
    far, near = [], []
    c = adv.case
    if c.get("type") not in types:
        far.append("unseen type")
    if set(c.get("negotiable") or []) - fields:
        far.append("unseen field")
    if (c.get("buyer") or {}).get("category_goal") not in goals:
        far.append("unseen goal")
    ov = (adv.scripted_responses or [{}])[0]
    if "profile_replace" in ov:
        far.append("no supplier profile")
    dist = ood.distance_to_training(c)
    if dist > ood.FAR_DISTANCE:
        far.append(f"distance {dist:.2f}")
    if ov.get("supplier") or ov.get("profile_floor_factor") or ov.get("alt_vs_opening"):
        near.append("supplier differs from belief")
    if ov.get("profile"):
        near.append("belief changed: " + ", ".join(sorted(ov["profile"])))
    if c.get("round_limit", 10) != 10:
        near.append("round limit")
    if ood.NEAR_DISTANCE < dist <= ood.FAR_DISTANCE:
        near.append(f"distance {dist:.2f}")
    label = "far_ood" if far else "near_ood" if near else "in_distribution"
    return label, round(dist, 3), far + near


# --- the run ---------------------------------------------------------------------------------------------
def run(suite, episodes=3, seed=0) -> dict:
    train_cases = load_cases()
    rows = []
    for adv in suite:
        measured, dist, why = novelty(adv, train_cases)
        if "must_fallback" in adv.expected_properties and measured != "far_ood":
            # intended far, measured nearer (gate 4): listed for review, judged by what was measured
            props = ["must_fallback_or_conservative" if p == "must_fallback" else p for p in adv.expected_properties]
            adv = dataclasses.replace(adv, expected_properties=props)
        for i in range(episodes):
            s = seed * 7919 + adv.seed * 31 + i
            r1 = episode(adv, Policy(), s)
            r2 = episode(adv, PolicyV2(), s)
            parent_conf = None
            if "confidence_must_not_rise" in adv.expected_properties:
                parent = dataclasses.replace(adv, scripted_responses=[{}])
                p = episode(parent, PolicyV2(), s)["first"]
                parent_conf = p and p["confidence"]
                if r2["first"] and parent_conf is not None and r2["first"]["confidence"] > parent_conf + 1e-9:
                    r2["violations"].append("confidence_must_not_rise")
            rows.append({"id": adv.case_id, "mutation": adv.mutations[0], "intended": adv.distribution,
                         "measured": measured, "distance": dist, "why": why, "expected_policy": adv.expected_policy,
                         "v1": r1, "v2": r2})  # fmt: skip
    return summarize(rows)


def _stats(scores):
    s = sorted(scores)
    return {"mean": round(statistics.mean(s), 4), "median": round(statistics.median(s), 4),
            "p10": round(s[max(0, int(len(s) * 0.1) - 1)], 4), "worst": round(s[0], 4),
            "zeros": round(sum(x <= 0 for x in s) / len(s), 3)}  # fmt: skip


def summarize(rows) -> dict:
    out = {"episodes": len(rows)}
    for pol in ("v1", "v2"):
        out[pol] = _stats([r[pol]["score"] for r in rows])
        viol = collections.Counter(v for r in rows for v in r[pol]["violations"])
        out[f"{pol}_violations"] = dict(viol)
        by_mut = collections.Counter(r["mutation"] for r in rows if r[pol]["violations"])
        out[f"{pol}_failures_by_mutation"] = dict(by_mut)
    firsts = [r for r in rows if r["v2"]["first"]]
    fb = lambda r: r["v2"]["first"]["source"] in ("v0_fallback", "v0_rule")  # noqa: E731
    far = [r for r in firsts if r["measured"] == "far_ood"]
    ind = [r for r in firsts if r["measured"] == "in_distribution"]
    out["far_ood_fallback_recall"] = None if not far else round(sum(map(fb, far)) / len(far), 3)
    out["in_distribution_false_fallback"] = None if not ind else round(sum(map(fb, ind)) / len(ind), 3)
    out["novelty_mismatch"] = sorted({r["mutation"] for r in rows if r["intended"] != r["measured"]})
    out["disagreement"] = round(sum(r["v1"]["kinds"] != r["v2"]["kinds"] for r in rows) / len(rows), 3)
    table = []
    for lo, hi in BANDS:
        band = [r for r in firsts if lo <= r["v2"]["first"]["confidence"] < hi]
        unsafe = [r for r in band if r["v2"]["violations"] or r["v2"]["score"] < r["v1"]["score"] - WORSE_BY]
        table.append({"band": f"{lo:.1f}-{min(hi, 1.0):.1f}", "count": len(band), "unsafe": len(unsafe),
                      "safe": len(band) - len(unsafe), "fallback_rate": None if not band else
                      round(sum(map(fb, band)) / len(band), 3)})  # fmt: skip
    out["calibration"] = table
    out["v2_latency_p95_s"] = round(sorted(r["v2"]["latency_s"] for r in rows)[int(0.95 * (len(rows) - 1))], 4)
    out["errors"] = sorted({r[p]["error"] for r in rows for p in ("v1", "v2") if r[p]["error"]})
    return out


def render(s) -> str:
    lines = [f"episodes {s['episodes']}   V1 {s['v1']}", f"{'':14s}V2 {s['v2']}"]
    lines.append(f"violations  V1 {s['v1_violations'] or '-'}   V2 {s['v2_violations'] or '-'}")
    lines.append(f"failures by mutation  V1 {s['v1_failures_by_mutation'] or '-'}   "
                 f"V2 {s['v2_failures_by_mutation'] or '-'}")  # fmt: skip
    lines.append(f"far-OOD fallback recall {s['far_ood_fallback_recall']}   in-distribution false fallback "
                 f"{s['in_distribution_false_fallback']}   V1/V2 disagreement {s['disagreement']}")  # fmt: skip
    lines.append(f"intended != measured novelty: {s['novelty_mismatch'] or '-'}")
    lines.append("confidence band  count  safe  unsafe  fallback")
    lines += [f"  {b['band']:12s}  {b['count']:5d}  {b['safe']:4d}  {b['unsafe']:6d}  {b['fallback_rate']}"
              for b in s["calibration"]]  # fmt: skip
    lines.append(f"V2 episode latency p95 {s['v2_latency_p95_s']} s   errors {s['errors'] or '-'}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--split", choices=SPLITS, required=True)
    g.add_argument("--n", type=int, default=120)
    r = sub.add_parser("run")
    r.add_argument("--split", choices=SPLITS, required=True)
    r.add_argument("--episodes", type=int, default=3)
    a = ap.parse_args(argv)
    if a.cmd == "generate":
        print(save(a.split, generate(a.split, a.n)))
    else:
        suite = load_suite(a.split) if (SUITES / a.split / "suite.json").is_file() else generate(a.split, 120)
        print(render(run(suite, a.episodes)))


if __name__ == "__main__":
    main()
