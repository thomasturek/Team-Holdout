"""LLM latency under full parallel load (DIPLOMAT.md P2; Definition of Done: p95 under 15 s).

Plays the Live Final's worst case: 10 cases x 3 threads at once, each thread doing reader + writer
per move, back to back, with the models from `.env`. Uses the 20 fixture e-mails as supplier
replies and realistic Decisions; no arena, no quota - only LLM calls (about cases x threads x rounds x 2).

    uv run python -m buyer.llm.bench                        # 10 x 3, 2 rounds, real models
    uv run python -m buyer.llm.bench --cases 10 --threads 3 --rounds 3
    uv run python -m buyer.llm.bench --dry                  # the harness itself, fake models

Prints p50 / p95 / max per role and per move, how often each fell back, and PASS / FAIL against
the 15 s target. If it fails: set a faster model or lower effort for the role that is slow
(LLM_READER_MODEL, LLM_WRITER_MODEL, LLM_*_EFFORT) and run it again.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from buyer.interfaces import Claim, Decision

from .client import LLMClient, Settings, get_client, latency_summary
from .reader import read
from .writer import write

TARGET_P95_S = 15.0


def _fixtures():
    from pathlib import Path

    path = Path(__file__).parent / "tests" / "fixtures" / "supplier_emails.json"
    return json.loads(path.read_text(encoding="utf-8"))["emails"]


CASE = {"case_id": "case:BENCH", "type": "price_increase", "title": "HN volute casings: a price increase"}
PROFILE = {"name": "Gießerei Brandlhuber GmbH & Co. KG", "country": "DE", "archetype": "family_foundry",
           "notes": ["owner works from his own spreadsheet, last updated two years ago",
                     "asked twice whether we could pay earlier"]}  # fmt: skip
CLAIMS = [
    Claim("index:PPI-D351", "Electricity producer prices changed -3.7% from 2025-08 to 2026-08 "
          "(idx:PPI-D351@2025-08, idx:PPI-D351@2026-08).",
          ["idx:PPI-D351@2025-08", "idx:PPI-D351@2026-08"], "verified", 0.6),
    Claim("scorecard:70110", "Your rolling on-time delivery was 81.1% in 2026Q3 (sc:70110@2026Q3).",
          ["sc:70110@2026Q3"], "verified", 0.4),
]  # fmt: skip


def _decision(rnd):
    p = round(rnd.uniform(120, 135), 2)
    sheets = [{"unit_price": p, "effective_date": "2027-04-01", "payment_days": 60},
              {"unit_price": round(p - 1.4, 2), "effective_date": "2027-04-01", "payment_days": 14}]  # fmt: skip
    return Decision("send", "sup:70110", sheets, None, rnd.sample(CLAIMS, rnd.randint(0, 2)),
                    rnd.sample(["cost breakdown", "earliest lead time", "variants"], rnd.randint(0, 1)),
                    rnd.choice(["firm, appreciative", "concede a little, warm", "close, respectful"]))  # fmt: skip


def _dry_clients(rnd):
    def reader_fn(system, user, max_tokens, timeout_s):
        time.sleep(rnd.uniform(0.3, 2.0))
        return json.dumps({"cash_pressure": False, "capacity_issue": False, "final_offer_language": False,
                           "approval_pending": False, "cost_drivers_claimed": ["energy"], "accepted_args": [],
                           "rejected_args": [], "asks": [], "offered_variants": [], "tone": "neutral"})  # fmt: skip

    def writer_fn(system, user, max_tokens, timeout_s):
        time.sleep(rnd.uniform(0.5, 4.0))
        return ("Dear colleagues,\n\nthank you for your reply. We have looked at your points carefully.\n\n"
                "[[CLAIM_1]]\n\n[[OFFERS]]\n\n[[QUESTIONS]]\n\nWe look forward to your answer.")  # fmt: skip

    s = Settings("dry", "dry", None, None, None, False)
    return LLMClient(s, reader_fn, "dry-reader"), LLMClient(s, writer_fn, "dry-writer")


def run(cases=10, threads=3, rounds=2, dry=False, seed=1):
    rnd = random.Random(seed)
    emails = _fixtures()
    reader_client, writer_client = _dry_clients(rnd) if dry else (get_client("reader"), get_client("writer"))
    if not dry and not (reader_client.enabled and writer_client.enabled):
        print("LLM not configured (LLM_MODEL / API key) - use --dry to test the harness", file=sys.stderr)
        return None
    moves = []

    def one_thread(i):
        r = random.Random(seed * 1000 + i)
        for _ in range(rounds):
            case = r.choice(emails)
            t0 = time.monotonic()
            reading = read(case["message"], last_decision={"claims": case["last_claims"]}, client=reader_client)
            t1 = time.monotonic()
            email = write(_decision(r), CASE, [case["message"]], PROFILE, reading.signals, client=writer_client)
            t2 = time.monotonic()
            moves.append({"reader_s": t1 - t0, "writer_s": t2 - t1, "move_s": t2 - t0,
                          "reader_source": reading.source, "writer_source": email.source})  # fmt: skip

    n = cases * threads
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=n) as pool:
        list(pool.map(one_thread, range(n)))
    wall = time.monotonic() - t0

    def summary(key):
        return latency_summary([{"latency_s": round(m[key], 3), "ok": True} for m in moves])

    report = {
        "parallel_threads": n,
        "moves": len(moves),
        "wall_s": round(wall, 1),
        "reader": summary("reader_s"),
        "writer": summary("writer_s"),
        "move": summary("move_s"),
        "reader_fallback_pct": round(100 * sum(m["reader_source"] == "rules" for m in moves) / max(1, len(moves)), 1),
        "writer_fallback_pct": round(
            100 * sum(m["writer_source"] == "template" for m in moves) / max(1, len(moves)), 1
        ),
        "llm_calls": {
            "reader": latency_summary(list(reader_client.stats)),
            "writer": latency_summary(list(writer_client.stats)),
        },
        "models": {"reader": reader_client.settings.model, "writer": writer_client.settings.model},
    }
    report["pass"] = report["move"].get("p95", 0) <= TARGET_P95_S and report["writer_fallback_pct"] < 5
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m buyer.llm.bench", description=__doc__.split("\n\n")[0])
    ap.add_argument("--cases", type=int, default=10)
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--dry", action="store_true", help="fake models with random delays: tests the harness only")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    report = run(a.cases, a.threads, a.rounds, a.dry, a.seed)
    if report is None:
        return 2
    print(json.dumps(report, indent=2))
    verdict = "PASS" if report["pass"] else "FAIL"
    print(f"{verdict}: move p95 {report['move'].get('p95')} s (target <= {TARGET_P95_S} s), "
          f"writer fallbacks {report['writer_fallback_pct']} %")  # fmt: skip
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
