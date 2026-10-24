"""The runner: play practice, sandbox or the Live Final with our per-thread runtime.

    uv run buyer quota                                     # practice used / left / resets_at
    uv run buyer practice --agent naive --purpose baseline # every hosted practice case once
    uv run buyer practice --cases P01 P04 --repeat 2       # chosen cases ("P01" = "case:P01")
    uv run buyer sandbox --repeat 3                        # case:D01 and case:D02, no quota
    uv run buyer final                                     # the Live Final: every wave, until the last closes

Practice costs quota (200 sessions per rolling 24 h for the team). Before a practice run the runner
reads GET /v1/me and refuses to start if the run would leave fewer than --reserve sessions
(default 20: Sunday's pre-flight). While it runs, no new session starts once the arena reports the
reserve reached or the quota used up.

Final: polls the case list every few seconds, plays each wave's cases in parallel as they appear,
closes each case before its wave's cap (from `seconds_left`, re-read every poll so an extension is
followed). If the runner is restarted mid-wave, it picks up its running sessions (the arena's 409
names them) and plays on. It never reads the leaderboard, results, screen or events.

Every session is logged (runs/<set>/<case>/<session>.jsonl) and saved as one JSON file
(runs/<set>_sessions/); the runner's own log goes to runs/runner-<mode>-<time>.log as well.
"""

import argparse
import functools
import logging
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from arena_kit.client import ArenaClient, ArenaError
from arena_kit.play import hosted, quota_used_up

from . import env
from .agent import new_agent
from .log import SessionLog, summary
from .threads import play_case

log = logging.getLogger("buyer.runner")

FORBIDDEN = ("/events", "/screen", "/leaderboard", "/results")  # for people, never for the agent (api.md)
RESERVE = 20  # practice sessions kept for Sunday's pre-flight (AGENTS.md section 6)
POLL_S = 3.0


class SafeClient(ArenaClient):
    """The arena client, minus the endpoints the agent must never read during the Live Final."""

    def _call(self, method, path, *args, **kwargs):
        if path.startswith(FORBIDDEN):
            raise PermissionError(f"{path} is for people, not for the agent")
        return super()._call(method, path, *args, **kwargs)

    def leaderboard(self, set_="practice"):
        raise PermissionError("the leaderboard is for people, not for the agent")


class QuotaRefused(SystemExit):
    pass


def quota(client):
    """{"used", "left", "limit", "resets_at"} of the team's practice quota."""
    return client.me()["practice"]


def check_quota(client, sessions, reserve=RESERVE):
    """Refuse a practice run that would leave fewer than `reserve` sessions."""
    q = quota(client)
    if q["left"] - sessions < reserve:
        raise QuotaRefused(
            f"refused: {sessions} practice sessions would leave {q['left'] - sessions} of {q['limit']} "
            f"(keep {reserve}; resets_at {q['resets_at']}). Fewer cases, or --reserve to change it."
        )
    return q


def case_id(name):
    return name if name.startswith("case:") else f"case:{name}"


def play_set(client, set_, cases, *, agent="policy", params=None, parallel=8, repeat=1, run=None, reserve=None,
             root=env.RUNS):  # fmt: skip
    """Play `cases` (case files) `repeat` times, `parallel` at once. Practice: give `reserve` - no new
    session once the arena reports that many left (or the quota used up). Returns [(case_id, result
    or the exception that stopped it)]."""
    stop = threading.Event()
    archive = root / f"{set_}_sessions"

    def one(case, i):
        cid = case["case_id"]
        left = client.practice_remaining
        if stop.is_set() or (reserve is not None and left is not None and left <= reserve):
            stop.set()
            return cid, ArenaError(429, f"not started: keeping the reserve of {reserve} practice sessions")
        lg = SessionLog(set_, cid, root=root)
        info = {**(run or {}), "agent": agent, "params": params or {}, "repeat": i}
        try:
            result = play_case(client, cid, new_agent(agent, params), case=case, log=lg, run=info, archive=archive)
            log.info("%s", summary(lg.path))
        except ArenaError as e:
            lg("error", status=e.status, detail=e.detail, where="runner")
            if quota_used_up(e):
                stop.set()
                log.warning("practice quota used up: %s", e.detail)
            else:
                log.warning("%s: %s", cid, e)
            result = e
        except Exception as e:  # one broken case must not stop the others
            lg("error", detail=e, where="runner")
            log.exception("%s failed", cid)
            result = e
        finally:
            lg.close()
        return cid, result

    with ThreadPoolExecutor(
        max_workers=parallel, thread_name_prefix=set_
    ) as pool:  # every job reports, also the skipped
        return list(pool.map(lambda job: one(*job), [(c, i) for i in range(repeat) for c in cases]))


def play_final(client, *, agent="policy", params=None, waves=5, parallel=10, poll=POLL_S, root=env.RUNS):
    """The Live Final: wait for each wave, play its cases in parallel within the wave's cap, until
    `waves` waves have closed and every case has finished. Returns {case_id: result or exception}."""
    started, closed, caps = {}, set(), {}  # caps: wave -> its cap as time.time()
    archive = root / "final_sessions"

    def one(case, deadline):
        cid = case["case_id"]
        lg = SessionLog("final", cid, root=root)
        info = {"mode": "final", "agent": agent, "params": params or {}, "wave": case.get("wave")}
        try:
            result = play_case(
                client, cid, new_agent(agent, params), case=case, deadline=deadline, log=lg, run=info, archive=archive
            )
            log.warning("wave %s %s", case.get("wave"), summary(lg.path))
            return result
        except Exception as e:  # one broken case must not stop the others
            lg("error", detail=e, where="runner")
            log.exception("%s failed", cid)
            return e
        finally:
            lg.close()

    with ThreadPoolExecutor(max_workers=parallel, thread_name_prefix="final") as pool:
        while len(closed) < waves or not all(f.done() for f in started.values()):
            try:
                cases = client.cases("final")
            except ArenaError as e:
                if e.status != 403:  # 403: no wave has started yet
                    log.warning("case list: %s", e)
                cases = []
            except Exception as e:  # the network: keep polling
                log.warning("case list: %s", e)
                cases = []
            for case in cases:
                wave, cid = case.get("wave"), case["case_id"]
                if not case.get("open"):
                    if wave not in closed:
                        log.warning("wave %s closed (%d of %d)", wave, len(closed) + 1, waves)
                    closed.add(wave)
                    continue
                if case.get("seconds_left") is not None:  # each wave has its own cap; follow an extension
                    caps[wave] = time.time() + case["seconds_left"]
                if cid not in started and case.get("seconds_left"):
                    if wave not in {c.get("wave") for c in cases if c["case_id"] in started}:
                        log.warning("wave %s started: %s (%s s)", wave, case.get("theme"), case["seconds_left"])
                    started[cid] = pool.submit(one, case, functools.partial(caps.get, wave))
            time.sleep(poll)
    return {cid: f.result() for cid, f in started.items()}


def report(out):
    lines, scores = [], []
    for cid, r in out:
        if isinstance(r, BaseException):
            lines.append(f"{cid}  {type(r).__name__}: {r}")
            continue
        scores.append(r.get("score") or 0.0)
        lines.append(f"{cid}  deal {r.get('deal')}  score {r.get('score')}")
    if scores:
        lines.append(f"mean score {100 * statistics.mean(scores):.1f} over {len(scores)} sessions")
    return lines


def setup_logging(mode, verbose=False):
    env.RUNS.mkdir(parents=True, exist_ok=True)
    path = env.RUNS / f"runner-{mode}-{time.strftime('%Y%m%d-%H%M%S')}.log"
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s", "%H:%M:%S")
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
    file = logging.FileHandler(path, encoding="utf-8")
    file.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=[console, file])
    if not verbose:
        for noisy in ("httpx", "buyer.threads", "arena"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="buyer", description="Team Holdout runner: practice, sandbox, final")
    sub = ap.add_subparsers(dest="mode", required=True)
    sub.add_parser("quota", help="the team's practice quota")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--agent", default="policy", choices=["policy", "naive", "llm"])
    common.add_argument("-v", "--verbose", action="store_true")
    for mode in ("practice", "sandbox"):
        p = sub.add_parser(mode, parents=[common], help=f"play {mode} cases")
        p.add_argument("--cases", nargs="*", help="case ids, e.g. P01 or case:P01 (default: every playable case)")
        p.add_argument("--repeat", type=int, default=1)
        p.add_argument("--parallel", type=int, default=8, help="sessions at once (the key allows 10 for the team)")
        p.add_argument("--purpose", default="", help="logged with each session: baseline, calibration, ...")
        if mode == "practice":
            p.add_argument("--reserve", type=int, default=RESERVE, help="practice sessions to keep")
    f = sub.add_parser("final", parents=[common], help="the Live Final, wave by wave")
    f.add_argument("--waves", type=int, default=5, help="stop after this many waves have closed (rehearsal: 2)")
    f.add_argument("--parallel", type=int, default=10)
    args = ap.parse_args(argv)
    env.load()
    client = SafeClient()
    if args.mode == "quota":
        q = quota(client)
        print(f"practice: used {q['used']}, left {q['left']} of {q['limit']}, next frees up {q['resets_at']}")
        return
    print(f"log: {setup_logging(args.mode, args.verbose)}")
    if args.mode == "final":
        out = play_final(client, agent=args.agent, waves=args.waves, parallel=min(args.parallel, 10))
        for line in report(list(out.items())):
            print(line)
        return
    listed = client.cases(args.mode)
    playable = hosted(listed) if args.mode == "practice" else listed
    if args.cases:
        wanted = {case_id(c) for c in args.cases}
        unknown = wanted - {c["case_id"] for c in playable}
        if unknown:
            raise SystemExit(f"not playable in {args.mode}: {sorted(unknown)}")
        playable = [c for c in playable if c["case_id"] in wanted]
    reserve = None
    if args.mode == "practice":
        q = check_quota(client, len(playable) * args.repeat, args.reserve)
        reserve = args.reserve
        log.warning(
            "practice: %d sessions; %d left before, keeping %d", len(playable) * args.repeat, q["left"], reserve
        )
    out = play_set(
        client,
        args.mode,
        playable,
        agent=args.agent,
        parallel=min(args.parallel, 10),
        repeat=args.repeat,
        run={"mode": args.mode, "purpose": args.purpose},
        reserve=reserve,
    )
    for line in report(out):
        print(line)
    if client.practice_remaining is not None:
        print(f"practice sessions left: {client.practice_remaining}")


if __name__ == "__main__":
    main()
