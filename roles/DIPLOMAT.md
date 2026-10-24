# THE DIPLOMAT (LLM reading and writing)

**Owner: Halichem**

> Read [`../AGENTS.md`](../AGENTS.md) first: the idea, hard constraints, architecture, interfaces
> (`SupplierProfile`, `Claim`, `Signals`, `Decision`), timeline and guardrails. This file is your job.
> Start every task by saying "Acting as DIPLOMAT".

**Mission:** suppliers read our e-mails as coming from a sharp, polite, well-informed buyer; we read
theirs better than anyone. Fast and safe.

**Owns:** `src/buyer/llm/`, prompts.

**Tasks, in priority order**

P0 - Saturday evening
- [ ] `client.py`: provider from `.env` (Anthropic default, `LLM_EFFORT=low`), hard timeout 20 s,
      one retry, then fallback to templates. Never blocks a move past 25 s.
- [ ] `writer.py`: input = Decision + case + short thread history + profile notes. Output =
      subject + body (max ~150 words). Rules:
  - claim sentences pasted **verbatim** (code checks they are present unchanged; if not, inject).
  - no numbers, prices or terms that are not in the Decision; code strips unknown IDs
    (`ID_RE` like `agents/llm.py`).
  - never reveal urgency, budget, missing alternative, our target or our C.
  - polite, specific, appreciative of the relationship; reflect the supplier's stated concerns
    (from Signals) and answer them; ask the Decision's questions (cost breakdown, lead time,
    variants).
  - match archetype: personal and long-term to family firms, structured and approval-friendly to
    groups, cash-and-reliability to cash-short shops, volume/contract security to monopolists.
- [ ] Template fallback writer (no LLM): deterministic e-mail from Decision. Used on timeout.

P1 - Saturday night
- [ ] `reader.py`: supplier e-mail + attachments text -> `Signals` JSON (schema above), strict
      JSON, validated. Fast model, < 10 s. Fallback: keyword rules.
- [ ] Prompt tests: 20 recorded supplier e-mails from logs -> expected Signals.

P2 - Sunday morning
- [ ] Read 20+ real replays; tune wording where suppliers reacted badly (irritated, "not our
      reality", walked). Write findings into `docs/LEARNINGS.md`.
- [ ] Measure LLM latency under 10 parallel cases x 3 threads; switch model / effort if p95 > 15 s.

**Definition of done:** 100 % of sent e-mails contain the Decision's claims verbatim and no foreign
number; p95 latency under 15 s with full parallel load.
