"""One readable digest per practice case: every logged negotiation, ours and the EHL 2026 winners', move by move.

    uv run python scripts/case_digest.py            # runs/night/digest/<case>.md for every hosted case
"""

import glob
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINNERS = ROOT.parent / "ehl-final-procurecabana" / "exports" / "messages.jsonl"
OUT = ROOT / "runs" / "night" / "digest"
KEYS = ("unit_price", "payment_days", "contract_months", "volume_per_year", "lead_time_days", "effective_date",
        "ppm_commitment", "chargeback_eur_per_complaint", "index_clause")


def terms_text(t):
    out = []
    for k in KEYS:
        if k in (t or {}) and t[k] is not None:
            v = t[k]
            if k == "index_clause":
                v = f"{v.get('series')}/db{v.get('deadband_pct')}"
            out.append(f"{k.replace('_days', 'd').replace('unit_price', 'p')}={v}")
    return " ".join(out)


def ours(case_id):
    lines = []
    for f in sorted(glob.glob(str(ROOT / f"runs/practice/case_{case_id}/*.jsonl")), key=os.path.getmtime):
        ev = [json.loads(x) for x in open(f)]
        res = next((e["result"] for e in ev if e["kind"] == "result"), None) or {}
        tr = (next((e["data"] for e in ev if e["kind"] == "session"), {}).get("result") or {}).get("trace") or []
        if not tr:
            continue
        ts = Path(f).stat().st_mtime
        lines.append(f"\n### ours {Path(f).stem[:8]} (t={int(ts)}) score={res.get('score')} "
                     f"deal: {terms_text(res.get('terms'))} breakdown: "
                     + ", ".join(f"{k}={round(v)}" for k, v in (res.get('cost_breakdown') or {}).items() if abs(v) > 1))
        for x in tr:
            m = x.get("move") or {}
            if x.get("actor") == "buyer":
                sheets = " | ".join(terms_text(s.get("terms")) for s in m.get("term_sheets") or [])
                claims = [c.get("type") for c in (m.get("interpreted") or {}).get("claims") or []]
                kind = m.get("type") or "message"
                lines.append(f"r{x.get('round')} BUYER {kind}: {sheets} claims={claims}")
            else:
                lines.append(f"r{x.get('round')} {x.get('actor')} [{m.get('status')}] {terms_text(m.get('terms'))} :: "
                             + " | ".join(x.get("reasons") or [])[:600])
    return lines


def winners(case_id):
    if not WINNERS.is_file():
        return []
    rows = [json.loads(x) for x in WINNERS.read_text().splitlines() if x.strip()]
    rows = [r for r in rows if str(r.get("case_id", "")).endswith(case_id)]
    lines, last = [], None
    for r in rows:
        if r.get("session_id") != last:
            last = r.get("session_id")
            lines.append(f"\n### winners {str(last)[:8]}")
        sheets = " | ".join(terms_text(s.get("terms")) for s in r.get("sheets") or [])
        if r.get("actor") == "buyer":
            claims = [c.get("type") for c in r.get("claims_made") or []]
            note = f" ({r.get('probe_step')}: {r.get('probe_note')})" if r.get("probe_note") else ""
            lines.append(f"r{r.get('round')} BUYER {r.get('action') or 'message'}{note}: {sheets} claims={claims}")
        else:
            office = " / ".join(str(b.get("text", b))[:80] for b in r.get("backoffice") or [])
            lines.append(f"r{r.get('round')} {r.get('supplier_id')} [{r.get('status')}] {sheets} :: "
                         + " | ".join(r.get("reasons") or [])[:500] + (f" || office: {office}" if office else ""))
    return lines


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for cid in ("P01", "P02", "P03", "P04", "P05", "P07", "P08", "P10", "P11", "P18"):
        text = [f"# Case {cid}: every logged negotiation", "## Ours (oldest first)"] + ours(cid)
        text += ["", "## EHL 2026 winners (Codacabana probes)"] + winners(cid)
        (OUT / f"{cid}.md").write_text("\n".join(text), encoding="utf-8")
        print(cid, len("\n".join(text)) // 4, "tokens approx")


if __name__ == "__main__":
    main()
