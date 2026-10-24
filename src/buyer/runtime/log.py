"""JSONL run logs, one file per session: runs/<set>/<case>/<session>.jsonl.

Every line is one event `{"t": unix time, "kind": ..., ...}`. The format is described for readers
in docs/LOGS.md; keep the kinds stable, the Analyst's calibration reads them.

    uv run python -m buyer.runtime.log backfill --set final    # after the final: add trace + back office
    uv run python -m buyer.runtime.log summary --set sandbox   # one line per logged session
"""

import argparse
import dataclasses
import json
import logging
import re
import threading
import time
from pathlib import Path

from .env import RUNS

log = logging.getLogger("buyer.log")

UNSAFE = re.compile(r"[^\w.@-]+")  # ':' is not allowed in Windows file names


def safe(name):
    return UNSAFE.sub("_", str(name))


def _default(o):
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return dataclasses.asdict(o)
    if isinstance(o, bytes | bytearray):
        return f"<{len(o)} bytes>"
    if isinstance(o, set | tuple):
        return list(o)
    if isinstance(o, BaseException):
        return f"{type(o).__name__}: {o}"
    return str(o)


class SessionLog:
    """Append-only, thread-safe. Opened before the session id is known; `bind` names the file."""

    def __init__(self, set_, case_id, root=RUNS):
        self.dir = Path(root) / safe(set_) / safe(case_id)
        self.path, self._lock, self._pending = None, threading.Lock(), []

    @classmethod
    def at(cls, path):
        """Append to an existing log file."""
        out = cls("-", "-")
        out.dir, out.path = Path(path).parent, Path(path)
        return out

    def bind(self, session_id):
        with self._lock:
            if self.path is not None:
                return
            self.dir.mkdir(parents=True, exist_ok=True)
            self.path = self.dir / f"{safe(session_id)}.jsonl"
            pending, self._pending = self._pending, []
            for line in pending:
                self._write(line)

    def __call__(self, kind, **fields):
        line = json.dumps({"t": round(time.time(), 3), "kind": kind, **fields}, default=_default, ensure_ascii=False)
        with self._lock:
            if self.path is None:
                self._pending.append(line)
            else:
                self._write(line)

    def _write(self, line):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def close(self, session_id=None):
        """Flush lines logged before the session existed (e.g. the open failed) into a file anyway."""
        if self.path is None and self._pending:
            self.bind(session_id or f"failed-{int(time.time() * 1000)}")


class NullLog:
    def bind(self, session_id):
        pass

    def __call__(self, kind, **fields):
        pass

    def close(self, session_id=None):
        pass


def read(path):
    """Every event of one session log. A line cut off by a crash is skipped."""
    events = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                if line.strip():
                    log.warning("%s: skipped a broken line", path)
    return events


def iter_logs(set_=None, root=RUNS):
    """Every session log, oldest first; `set_` = practice | sandbox | final | sim ... (None: all)."""
    pattern = f"{safe(set_)}/*/*.jsonl" if set_ else "*/*/*.jsonl"
    return sorted(Path(root).glob(pattern), key=lambda p: p.stat().st_mtime)


# -- one JSON file per ended session ------------------------------------------------------------
def archive_session(client, session_id, case, folder, run=None):
    """The whole session as one JSON file in `folder`, everything as the API returns it after the
    end: the case file, each supplier's thread (GET .../threads/{supplier}: every message, both
    directions, in order, plus the timeout answers) and the result (with the trace where the set
    shows it). File name: <ended at>_<case>_<session>.json, so the folder sorts by time."""
    state = client.session(session_id)
    suppliers = list(state.get("threads") or case.get("suppliers") or [])
    doc = {
        "session_id": session_id,
        "case_id": state.get("case_id") or case.get("case_id"),
        "set": state.get("set"),
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "run": run or {},
        "case": case,
        "threads": {sid: client.thread(session_id, sid) for sid in suppliers},
        "result": state.get("result"),
        "end_reason": state.get("end_reason"),
        "replay_url": state.get("replay_url"),
    }
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{time.strftime('%Y%m%d-%H%M%S')}_{safe(doc['case_id'])}_{safe(session_id)}.json"
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=_default), encoding="utf-8")
    return path


# -- after the end: trace and back office -----------------------------------------------------
def _session_id(events):
    return next((e.get("session_id") for e in events if e["kind"] == "case" and e.get("session_id")), None)


def _has(events):
    """(trace, back office): what this log already holds, each fetched without an error."""
    trace = any(e["kind"] == "session" and ((e.get("data") or {}).get("result") or {}).get("trace") for e in events)
    office = any(e["kind"] == "backoffice" and "data" in e for e in events)
    return trace, office


def _complete(events):
    return all(_has(events))


def backfill(client, set_="final", root=RUNS):
    """Add the trace and the back office to every log of `set_` that lacks them. In the final both
    stay closed until the whole final is over, so run this afterwards. Returns {path: what was added}."""
    added = {}
    for path in iter_logs(set_, root):
        events = read(path)
        sid, (trace, office) = _session_id(events), _has(events)
        if not sid or (trace and office):
            continue
        out, got = SessionLog.at(path), []
        if not trace:
            try:
                state = client.session(sid)
            except Exception as e:
                log.warning("%s: session %s: %s", path.name, sid, e)
                continue
            if (state.get("result") or {}).get("trace"):
                out("session", data=state, backfill=True)
                got.append("trace")
        if not office:
            try:
                out("backoffice", data=client.backoffice(sid), backfill=True)
                got.append("backoffice")
            except Exception as e:  # 403 while the final is still running
                log.info("%s: back office not available yet: %s", path.name, e)
        if got:
            added[path] = got
    return added


def summary(path):
    """One line about a session log: case, session, messages, timeouts, result."""
    events = read(path)
    case = next((e for e in events if e["kind"] == "case"), {})
    result = next((e.get("result") for e in reversed(events) if e["kind"] == "result"), None) or {}
    sent = sum(e["kind"] == "sent" for e in events)
    errors = [e.get("status") for e in events if e["kind"] == "error"]
    score = result.get("score")
    return (
        f"{case.get('case_id', '?')}  {case.get('session_id', path.stem)}  sent {sent}  "
        f"errors {len(errors)} {sorted(set(e for e in errors if e))}  deal {result.get('deal')}  "
        f"score {'-' if score is None else round(score, 3)}  {'complete' if _complete(events) else ''}"
    )


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m buyer.runtime.log")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backfill", help="add trace and back office to ended sessions (final: after the final)")
    b.add_argument("--set", default="final")
    s = sub.add_parser("summary", help="one line per logged session")
    s.add_argument("--set", default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.cmd == "summary":
        for path in iter_logs(args.set):
            print(summary(path))
        return
    from arena_kit import ArenaClient

    from . import env

    env.load()
    added = backfill(ArenaClient(), args.set)
    for path, got in added.items():
        print(path, "+", ", ".join(got))
    print(f"{len(added)} logs updated")


if __name__ == "__main__":
    main()
