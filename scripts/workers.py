"""Night workers: Claude Opus 5.5 tasks through the team's Anthropic key, in parallel, with a hard spend cap.

    uv run python scripts/workers.py tasks.json [--parallel 6]

tasks.json: [{"id", "prompt", "files": [paths], "context": "name of a shared context file list", "max_tokens"}]
Shared contexts ({"contexts": {name: [paths]}} at the top level) are sent as a cached system block, so many
tasks over the same repo pay the big input once. Answers land in runs/night/out/<id>.md; every call's
usage and cost in runs/night/api_spend.jsonl. No call starts once the logged spend reaches CAP_USD.
"""

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from buyer.runtime import env  # noqa: E402

env.load()

import anthropic  # noqa: E402

MODEL = "claude-opus-5-5"
CAP_USD = 90.0
PRICE = {"input": 4.0, "output": 20.0, "cache_write": 5.0, "cache_read": 0.20}  # USD per million tokens
OUT = ROOT / "runs" / "night" / "out"
SPEND = ROOT / "runs" / "night" / "api_spend.jsonl"
SYSTEM = (
    "You are a senior engineer and negotiation strategist on a hackathon team. Our AI buyer agent negotiates "
    "by e-mail with deterministic supplier bots in the Tacto Negotiation Arena; score per case is "
    "(c_open - c_deal) / (c_open - c_best). Be concrete and evidence-based: cite file:line, session ids and "
    "figures. Separate what the evidence shows from what you infer. Prefer general rules over rules keyed to a "
    "case id. Every proposed code change must be a minimal unified diff against the files shown."
)
_lock = threading.Lock()


def spent() -> float:
    if not SPEND.is_file():
        return 0.0
    return sum(json.loads(line)["usd"] for line in SPEND.read_text().splitlines() if line.strip())


def cost(usage) -> float:
    u = {k: getattr(usage, k, 0) or 0 for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                                                 "cache_read_input_tokens")}
    return (u["input_tokens"] * PRICE["input"] + u["output_tokens"] * PRICE["output"]
            + u["cache_creation_input_tokens"] * PRICE["cache_write"]
            + u["cache_read_input_tokens"] * PRICE["cache_read"]) / 1e6


def read_files(paths) -> str:
    parts = []
    for p in paths:
        path = (ROOT / p) if not Path(p).is_absolute() else Path(p)
        if path.is_file():
            parts.append(f"===== FILE {p} =====\n{path.read_text(encoding='utf-8', errors='replace')}")
        else:
            parts.append(f"===== FILE {p} (missing) =====")
    return "\n\n".join(parts)


def run_task(client, task, contexts):
    out = OUT / f"{task['id']}.md"
    if out.is_file() and out.stat().st_size > 0:
        return task["id"], "cached"
    with _lock:
        if spent() >= CAP_USD:
            return task["id"], "skipped: cap reached"
    system = [{"type": "text", "text": SYSTEM}]
    if task.get("context"):
        system.append({"type": "text", "text": read_files(contexts[task["context"]]),
                       "cache_control": {"type": "ephemeral", "ttl": "1h"}})
    user = task["prompt"]
    if task.get("files"):
        user = f"{user}\n\n{read_files(task['files'])}"
    t0 = time.time()
    for attempt in range(3):
        try:
            with client.messages.stream(
                model=MODEL, max_tokens=task.get("max_tokens", 16000), system=system,
                messages=[{"role": "user", "content": user}],
                extra_body={"output_config": {"effort": task.get("effort", "high")}},
            ) as stream:
                msg = stream.get_final_message()
            break
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError) as e:
            if attempt == 2:
                return task["id"], f"failed: {type(e).__name__}"
            time.sleep(20 * (attempt + 1))
    usd = cost(msg.usage)
    with _lock:
        SPEND.parent.mkdir(parents=True, exist_ok=True)
        with SPEND.open("a") as f:
            f.write(json.dumps({"id": task["id"], "usd": round(usd, 4), "s": round(time.time() - t0, 1),
                                "stop": msg.stop_reason, **{k: getattr(msg.usage, k, 0) or 0 for k in (
                                    "input_tokens", "output_tokens", "cache_creation_input_tokens",
                                    "cache_read_input_tokens")}}) + "\n")
    text = "".join(b.text for b in msg.content if b.type == "text")
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return task["id"], f"done ({msg.stop_reason}, ${usd:.2f})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tasks")
    ap.add_argument("--parallel", type=int, default=6)
    args = ap.parse_args()
    spec = json.loads(Path(args.tasks).read_text())
    contexts, tasks = spec.get("contexts", {}), spec["tasks"]
    client = anthropic.Anthropic(max_retries=2, timeout=900)
    with ThreadPoolExecutor(args.parallel) as pool:
        for tid, status in pool.map(lambda t: run_task(client, t, contexts), tasks):
            print(f"{tid}: {status}", flush=True)
    print(f"total spend so far: ${spent():.2f} of ${CAP_USD:.0f}")


if __name__ == "__main__":
    main()
