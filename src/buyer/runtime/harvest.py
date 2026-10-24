"""The sandbox harvester: plays the sandbox cases (case:D01, case:D02) non-stop, several sessions at
once, with each parameter set the Analyst puts in src/buyer/policy/explore.json - his free training
and calibration data. Sandbox sessions do not count against the practice quota.

    uv run python -m buyer.runtime.harvest                      # until Ctrl+C
    uv run python -m buyer.runtime.harvest --sessions 40        # stop after 40 sessions
    uv run python -m buyer.runtime.harvest --hours 8 --parallel 6

Episode n plays case n % len(cases) with parameter set (n // len(cases)) % len(sets), so every set
meets every case in turn. explore.json is read again before each session: edit it while the
harvester runs. Each session is logged in runs/sandbox/<case>/<session>.jsonl (docs/LOGS.md) with
the agent and parameter set on its `case` line. Before it starts, the harvester also saves the
sandbox and practice case files to runs/cases/<set>.json (listing cases costs no quota).

The key allows 10 open sessions for the whole team: keep --parallel below that (default 8) while
someone else plays practice. Ctrl+C stops starting new sessions and lets the running ones finish;
a second Ctrl+C quits at once.
"""

import argparse
import hashlib
import itertools
import json
import logging
import statistics
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from arena_kit.client import ArenaClient, ArenaError

from . import env
from .agent import explore_params, new_agent
from .log import SessionLog, summary
from .threads import play_case

log = logging.getLogger("buyer.harvest")

BUSY_WAIT_S = 10  # 429 open sessions: someone else is playing; wait
ERROR_WAIT_S = 2


def save_cases(client, root=env.RUNS, sets=("sandbox", "practice")):
    """The case files of each set as runs/cases/<set>.json - what the Analyst's simulator loads."""
    out = root / "cases"
    out.mkdir(parents=True, exist_ok=True)
    saved = {}
    for set_ in sets:
        try:
            cases = client.cases(set_)
        except ArenaError as e:
            log.warning("case list %s: %s", set_, e)
            continue
        (out / f"{set_}.json").write_text(json.dumps(cases, indent=1, ensure_ascii=False), encoding="utf-8")
        saved[set_] = len(cases)
    return saved


def version(sets):
    """A short fingerprint of the parameter sets, so logs say which explore.json they ran with."""
    return hashlib.sha1(json.dumps(sets, sort_keys=True).encode()).hexdigest()[:8]


class Harvester:
    def __init__(self, client, *, agent="policy", parallel=8, set_="sandbox", case_ids=None, root=env.RUNS):
        self.client, self.agent, self.parallel, self.set, self.root = client, agent, parallel, set_, root
        cases = client.cases(set_)
        self.cases = [c for c in cases if case_ids is None or c["case_id"] in case_ids]
        if not self.cases:
            raise SystemExit(f"no cases to harvest in {set_}")
        self.id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        self.stop = threading.Event()
        self._n, self._lock = itertools.count(), threading.Lock()
        self.results = []  # (params_index, case_id, score or None, deal)

    def run(self, sessions=None, until=None):
        """Play until `sessions` have started, `until` (time.time()) has passed, or stop is set."""

        def slot():
            while not self.stop.is_set():
                with self._lock:
                    n = next(self._n)
                if (sessions is not None and n >= sessions) or (until and time.time() > until):
                    return
                self.episode(n)

        with ThreadPoolExecutor(max_workers=self.parallel, thread_name_prefix="harvest") as pool:
            futures = [pool.submit(slot) for _ in range(self.parallel)]
            try:
                while not all(f.done() for f in futures):
                    time.sleep(0.5)
            except KeyboardInterrupt:
                log.warning("stopping: the running sessions finish first (Ctrl+C again to quit now)")
                self.stop.set()
                for f in futures:
                    f.result()
        return self.results

    def episode(self, n):
        sets = explore_params()
        case = self.cases[n % len(self.cases)]
        index = (n // len(self.cases)) % len(sets)
        params = sets[index]
        run = {
            "agent": self.agent,
            "params": params,
            "params_index": index,
            "explore": version(sets),
            "harvest": self.id,
            "episode": n,
        }
        lg = SessionLog(self.set, case["case_id"], root=self.root)
        try:
            result = play_case(self.client, case["case_id"], new_agent(self.agent, params), case=case, log=lg, run=run)
        except ArenaError as e:
            lg("error", status=e.status, detail=e.detail, where="harvest")
            wait = BUSY_WAIT_S if e.status == 429 else ERROR_WAIT_S
            log.warning("episode %d %s: %s - waiting %ss", n, case["case_id"], e, wait)
            self.stop.wait(wait)
            return
        except Exception as e:  # never let one broken session stop the night
            lg("error", detail=e, where="harvest")
            log.exception("episode %d %s failed", n, case["case_id"])
            self.stop.wait(ERROR_WAIT_S)
            return
        finally:
            lg.close()
        with self._lock:
            self.results.append((index, case["case_id"], result.get("score"), result.get("deal")))
        log.info("#%d set %d  %s", n, index, summary(lg.path))


def report(results):
    """Mean score per parameter set and case."""
    by = {}
    for index, case_id, score, _ in results:
        by.setdefault((index, case_id), []).append(score or 0.0)
    return [(i, c, len(v), round(statistics.mean(v), 3)) for (i, c), v in sorted(by.items())]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m buyer.runtime.harvest", description=__doc__.split("\n\n")[0])
    ap.add_argument("--agent", default="policy", choices=["policy", "naive", "llm"])
    ap.add_argument("--parallel", type=int, default=8, help="sessions at once (the key allows 10 for the team)")
    ap.add_argument("--sessions", type=int, help="stop after this many sessions")
    ap.add_argument("--hours", type=float, help="stop after this many hours")
    ap.add_argument("--cases", nargs="*", help="only these case ids (default: every sandbox case)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    if not args.verbose:
        for noisy in ("httpx", "buyer.threads"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
    env.load()
    client = ArenaClient()
    saved = save_cases(client)
    log.info("case files saved to %s: %s", env.RUNS / "cases", saved)
    h = Harvester(client, agent=args.agent, parallel=min(args.parallel, 10), case_ids=args.cases)
    until = time.time() + args.hours * 3600 if args.hours else None
    log.info("harvest %s: %s, %d parameter set(s), %d at once", h.id, [c["case_id"] for c in h.cases],
             len(explore_params()), h.parallel)  # fmt: skip
    results = h.run(args.sessions, until)
    print(f"\n{len(results)} sessions")
    for index, case_id, n, mean in report(results):
        print(f"set {index:3d}  {case_id}  sessions {n:4d}  mean score {mean}")


if __name__ == "__main__":
    main()
