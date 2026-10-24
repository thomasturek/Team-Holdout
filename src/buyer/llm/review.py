"""Replay review for the DIPLOMAT (P2): where did suppliers react badly to our wording?

Reads our finished sessions from the arena (GET /v1/sessions, /v1/sessions/{sid}, the threads) -
never the leaderboard, the screen, the results or the event feed - and writes a markdown draft:
per session every exchange (our e-mail -> the supplier's reply, status, claim results, the reader's
signals), flags where it went badly (irritated, "not our reality", final offer, walked away, a
contradicted claim) and the supplier's reasons from the trace. Read it, then write the findings into
docs/LEARNINGS.md (replay link + supplier, as AGENTS.md asks) and tune prompts/ and vocab.py.

    uv run python -m buyer.llm.review report --set practice --limit 25 --out runs/review/practice.md
    uv run python -m buyer.llm.review fixtures --set practice --limit 30 \
        --out src/buyer/llm/tests/fixtures/recorded_emails.json

`fixtures` exports every supplier reply with the keyword rules' signals as a draft `expected`:
correct each by hand - then they are the "recorded supplier e-mails -> expected Signals" of the
reader's prompt tests (`test_reader.py` reads supplier_emails.json; add the file's emails there).
Needs ARENA_URL and ARENA_API_KEY (the kit's client); costs no practice quota.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path

from .reader import REJECT_RE, rule_signals

BAD_STATUS = {"final_offer", "walked_away", "no_bid"}


def _client():
    from arena_kit import ArenaClient

    return ArenaClient()


def _sessions(client, set_, limit):
    rows = [s for s in client.sessions(set_) if s.get("status") == "ended"]
    rows.sort(key=lambda s: str(s.get("created_at")), reverse=True)
    return rows[:limit]


def _threads(client, sid, state):
    return {sup: client.thread(sid, sup).get("messages", []) for sup in (state.get("threads") or {})}


def _reasons(trace, supplier_id):
    key = supplier_id.split(":", 1)[-1]
    out = []
    for t in trace or []:
        actor = str(t.get("actor", ""))
        if "buyer" in actor or key not in actor:
            continue
        reasons = t.get("reasons") or []
        if isinstance(reasons, str):
            reasons = [reasons]
        out.append((t.get("round"), [str(r) for r in reasons]))
    return out


def flags_of(reply, signals) -> list[str]:
    out = []
    if reply.get("status") in BAD_STATUS:
        out.append(reply["status"])
    if signals.tone == "irritated":
        out.append("irritated")
    if REJECT_RE.search(str(reply.get("body") or "")):
        out.append("not_our_reality")
    for r in reply.get("claim_results") or []:
        if r.get("result") in ("contradicted", "irrelevant", "duplicate"):
            out.append(f"claim_{r['result']}")
    return out


def _short(text, n):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _sheets(msg):
    return "; ".join(json.dumps(s.get("terms", s), ensure_ascii=False) for s in msg.get("term_sheets") or [])


def report(set_="practice", limit=25, client=None) -> str:
    client = client or _client()
    lines = [f"# Replay review ({set_}, last {limit} ended sessions)", ""]
    totals, bad_wording = Counter(), []
    for row in _sessions(client, set_, limit):
        sid = row["session_id"]
        state = client.session(sid)
        result = state.get("result") or {}
        lines += [f"## {row.get('case_id')} - session {sid}",
                  f"score {result.get('score')} - deal {result.get('deal')} with {result.get('supplier_id')} - "
                  f"end {state.get('end_reason')} - replay {state.get('replay_url')}", ""]  # fmt: skip
        for sup, messages in _threads(client, sid, state).items():
            lines.append(f"### {sup}")
            ours = None
            for m in messages:
                if m.get("from") == "buyer":
                    ours = m
                    if m.get("action"):
                        lines.append(f"- **us**: action {json.dumps(m['action'])}")
                    else:
                        lines.append(f"- **us**: {_short(m.get('body'), 400)}  \n  sheets: {_sheets(m)}")
                    continue
                s = rule_signals(m)
                f = flags_of(m, s)
                totals.update(f or ["ok"])
                lines.append(f"- **{m.get('from')}** [{m.get('status')}] claims {m.get('claim_results') or []} "
                             f"signals tone={s.tone} asks={s.asks} drivers={s.cost_drivers_claimed}"
                             + (f" **FLAGS {f}**" if f else "") + f"  \n  {_short(m.get('body'), 600)}")  # fmt: skip
                if f and ours and ours.get("body"):
                    excerpt = _short(ours.get("body"), 300)
                    bad_wording.append((row.get("case_id"), sup, f, excerpt, state.get("replay_url")))
            for rnd, reasons in _reasons(result.get("trace"), sup):
                lines.append(f"  - reasons round {rnd}: " + " | ".join(_short(r, 200) for r in reasons))
            lines.append("")
    lines += ["## Summary", "", "| flag | replies |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in totals.most_common()]
    lines += ["", "## Our e-mails that preceded a bad reaction", ""]
    lines += [f"- {c} {s} {f}: \"{b}\" ({u})" for c, s, f, b, u in bad_wording] or ["- none"]
    return "\n".join(lines) + "\n"


def fixtures(set_="practice", limit=30, client=None) -> dict:
    client = client or _client()
    out = []
    for row in _sessions(client, set_, limit):
        sid = row["session_id"]
        state = client.session(sid)
        for sup, messages in _threads(client, sid, state).items():
            ours = None
            for n, m in enumerate(messages):
                if m.get("from") == "buyer":
                    ours = m
                    continue
                if not m.get("body"):
                    continue
                refs = list((ours or {}).get("refs") or [])
                last_claims = [{"key": r, "refs": [r], "sentence": ""} for r in refs]
                msg = {k: m.get(k) for k in ("from", "subject", "status", "claim_results", "body")}
                expected = dataclasses.asdict(rule_signals(msg, {"claims": last_claims}))
                out.append({
                    "id": f"{row.get('case_id')}-{sid}-{sup}-{n}",
                    "message": msg,
                    "last_claims": last_claims,
                    "expected": expected,
                    "_todo": "check `expected` by hand before using it as a test",
                })
    return {"_about": f"Recorded supplier replies from {set_} sessions; `expected` is the keyword rules' draft.",
            "emails": out}  # fmt: skip


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m buyer.llm.review", description=__doc__.split("\n\n")[0])
    ap.add_argument("command", choices=["report", "fixtures"])
    ap.add_argument("--set", default="practice", choices=["practice", "sandbox", "final"])
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--out", help="file to write (default: stdout)")
    a = ap.parse_args(argv)
    if a.command == "report":
        text = report(a.set, a.limit)
    else:
        text = json.dumps(fixtures(a.set, a.limit), indent=2, ensure_ascii=False)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
