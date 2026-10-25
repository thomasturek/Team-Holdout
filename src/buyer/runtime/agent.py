"""Agents the runtime can play, by name: `new_agent(name, params)` gives one agent per case.

The runtime asks an agent for one supplier's next move at a time (see `threads.py`):
  decide(case, threads, supplier_id) -> {"supplier_id", "message"[, "trace"]}
  closing(case, threads) -> {"supplier_id", "message"}            (optional)

  naive   the kit's NaiveAgent, per thread: the baseline to beat
  llm     the kit's LLMAgent, per thread (needs ANTHROPIC_API_KEY)
  policy  the Analyst's Policy (src/buyer/policy) with the Scout's profiles and the Diplomat
          (src/buyer/llm): every supplier reply is read into Signals (thread state), every Decision
          goes out as an e-mail written around it. What the harvester plays, with the parameter sets
          from explore.json. Without an LLM (LLM_DISABLED=1, no LLM_MODEL or no key) the Diplomat
          uses its keyword rules and its template e-mail - the cheap mode for harvesting.

One move of the policy agent, inside MOVE_BUDGET_S from the call (threads.py allows 25 s from the
supplier's reply): read the reply with the keyword rules (milliseconds) -> policy (plain code, under
the agent's lock) -> write the e-mail (LLM, the rest of the budget; else the template). The LLM
reader runs in the background at the same time as the writer (at most READER_BUDGET_S): its Signals
replace the rules' for this reply as soon as they arrive and go into the run log. The policy does not
wait for it - a move costs the writer's time, not reader + writer. BUYER_READER=blocking restores the
old order (LLM reader first, then policy and writer). The LLM calls run outside the lock, so the
threads of an RFQ never wait for each other.
"""

import dataclasses
import json
import logging
import os
import threading
import time

from arena_kit.docs import standard_terms
from arena_kit.play import closing_move, latest, moves_left, standing

from .env import ROOT

log = logging.getLogger("buyer.agent")
EXPLORE = ROOT / "src" / "buyer" / "policy" / "explore.json"
MOVE_BUDGET_S = 23.0  # reader + policy + writer, from the call; threads.DECIDE_BUDGET_S (25) runs from the reply
READER_BUDGET_S = 10.0  # DIPLOMAT.md: the reader answers in < 10 s, else its keyword rules
CLOSING_BUDGET_S = 8.0  # near the wave's cap: accept / walk need no LLM; a rare closing e-mail must be quick


class PerThread:
    """A kit agent (`decide(case, threads)` picks any supplier) asked about one thread at a time:
    it sees only that thread, so its move is for that supplier."""

    def __init__(self, kit_agent):
        self.kit_agent, self._lock = kit_agent, threading.Lock()

    def decide(self, case, threads, supplier_id):
        with self._lock:  # the kit agents keep no state, but are not written for threads either
            return self.kit_agent.decide(case, {supplier_id: threads[supplier_id]})


def env_params() -> dict:
    """Policy parameter overrides for test batches: environment BUYER_PARAMS as a JSON object, e.g.
    BUYER_PARAMS='{"concede": 0.25}'. Unset or invalid: none (the policy's own parameters)."""
    raw = os.environ.get("BUYER_PARAMS", "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        log.warning("BUYER_PARAMS is not valid JSON - ignored")
        return {}
    return {k: v for k, v in value.items() if isinstance(k, str) and isinstance(v, int | float)}         if isinstance(value, dict) else {}


class PolicyAgent:
    """The Analyst's Policy over the runtime's threads: keeps one ThreadState per supplier, updated
    from the messages before every decision (the Diplomat's Signals included); turns its Decision
    into an e-mail with the Diplomat's writer."""

    def __init__(self, params=None):
        from buyer.policy.policy import Policy, load_params

        # a partial set changes only what it names; BUYER_PARAMS: overrides for test batches
        self.policy = Policy({**load_params(), **env_params(), **(params or {})})
        self.base_p = dict(self.policy.p)  # the policy's own parameters; a strategy only overrides them per move
        self.states, self._lock = {}, threading.Lock()  # the policy is fast plain code: one at a time
        self.profiles = None  # the Scout's supplier profiles, built once per case
        self.readings = {}  # supplier -> (messages in the thread when read, Reading of its latest reply)
        self.llm_readings = {}  # supplier -> [messages when read, LLM Reading, already in a trace?]
        self.last_sent = {}  # supplier -> our last "send" Decision (the reader maps claim results to its claims)
        self.blocking_reader = os.environ.get("BUYER_READER", "parallel").strip().lower() == "blocking"
        self._data, self._data_tried = None, False  # the Scout's CaseData: which IDs exist (writer's known_id)
        self._init_lock = threading.Lock()  # loading profiles and data once per case, outside the policy's lock

    def _state(self, case, sid, events):
        from buyer.policy.policy import ThreadState

        try:
            sheet_id, terms = standing(events)
        except Exception:
            log.exception("%s: standing offer unreadable", sid)
            sheet_id, terms = None, {}
        terms = terms or {}
        t = self.states.get(sid)
        if t is None:
            if self.profiles is None:
                self.profiles = scout_profiles(case)
            profile = self.profiles.get(sid) or {}
            t = self.states[sid] = ThreadState(sid, sheet_id, terms, "open", {}, 0, profile=profile)
        t.standing_id, t.standing_terms = sheet_id, terms
        t.offers = [(ts["term_sheet_id"], ts["terms"]) for ts in latest(events).get("term_sheets") or [] if ts.get("term_sheet_id")]
        t.status = latest(events).get("status") or "open"
        try:
            t.standard = standard_terms(events) or t.standard
        except Exception:
            log.exception("%s: standard terms unreadable - keeping the earlier ones", sid)
        t.rounds_left = moves_left(case, events)
        t.their_prices = [
            m["term_sheets"][0]["terms"].get("unit_price")
            for m in events
            if m.get("from") != "buyer" and m.get("term_sheets")
        ]
        reading = self.readings.get(sid)
        if reading:  # the Diplomat's reading of this supplier's latest reply
            t.signals = dataclasses.asdict(reading[1].signals)
        return t

    def decide(self, case, threads, supplier_id):
        start = time.monotonic()
        deadline = start + MOVE_BUDGET_S
        reading = self._read(supplier_id, threads[supplier_id], min(start + READER_BUDGET_S, deadline))
        self._warm(case)  # first move of a case: profiles and data (a few seconds, once), outside the lock
        with self._lock:
            states = {sid: self._state(case, sid, ev) for sid, ev in threads.items()}
            for st in states.values():
                st.case_threads = threads
            t = states[supplier_id]
            strategy = self._strategy(case, t, threads[supplier_id])
            learned = self._learned(case, t)
            self.policy.p = {**self.base_p, **learned, **(strategy.params if strategy else {})}
            try:
                rival = self.policy.rival_best(case, states, t)  # eligible offers only (Policy.eligible_cost)
                decision = self.policy.decide(case, t, rival_best_c=rival)
            finally:
                self.policy.p = dict(self.base_p)
            if decision.kind == "walk":  # the runtime stops this thread (or ends the case): no longer a rival
                t.dropped = True
            profile = self._writer_profile(case, decision.supplier_id)
        move, email = self._message(case, threads, decision, profile, reading, deadline)
        diplomat = diplomat_trace(reading, email)
        diplomat.update(self._llm_reading_trace(supplier_id, len(threads[supplier_id])))
        trace = {"decision": decision, "rival_best_c": rival, "diplomat": diplomat,
                 "strategy": {"name": strategy.name, "reason": strategy.reason} if strategy else None}
        return {**move, "trace": trace}

    @staticmethod
    def _learned(case, t):
        """Policy parameters learned per case type and supplier type from practice runs
        (buyer.facts.strategy.learned_params), per environment BUYER_LEARNED: on (default; validated in
        practice 2026-10-25: 0.772 -> 0.796 on the ten hosted cases) / off."""
        if os.environ.get("BUYER_LEARNED", "on").strip().lower() in ("0", "off", "no", "false"):
            return {}
        try:
            from buyer.facts.strategy import learned_params

            label, params = learned_params(case, t.profile)
            t.learned = label
            return params
        except Exception:
            log.exception("learned params failed - the policy's own parameters")
            return {}

    @staticmethod
    def _strategy(case, t, events):
        """The Scout's strategy for this move (buyer.facts.strategy), per environment BUYER_STRATEGY:
        off (default: the policy's own parameters), auto (chosen from the profile, switched by the
        replies), or a strategy's name to force it on every supplier (for A/B tests)."""
        mode = os.environ.get("BUYER_STRATEGY", "off").strip().lower()
        if mode in ("", "off"):
            return None
        try:
            from buyer.facts.strategy import PARAMS, _make, choose

            if mode in PARAMS:
                s = _make(mode, f"forced by BUYER_STRATEGY={mode}")
            else:
                s = choose(case, t.profile, t.signals, list(events or []), current=getattr(t, "strategy", None))
            t.strategy = s
            return s
        except Exception:
            log.exception("strategy failed - the policy's own parameters")
            return None

    def closing(self, case, threads):
        start = time.monotonic()
        self._warm(case)
        with self._lock:
            states = {sid: self._state(case, sid, ev) for sid, ev in threads.items()}
            for st in states.values():
                st.case_threads = threads
            decision = self.policy.closing(case, states)
            profile = self._writer_profile(case, decision.supplier_id)
        move, _ = self._message(case, threads, decision, profile, None, start + CLOSING_BUDGET_S)
        return move

    # -- the Diplomat ---------------------------------------------------------------------------
    def _read(self, sid, events, deadline):
        """The Reading of this supplier's latest reply - read once per reply, outside the lock. In
        parallel mode: the keyword rules now, the LLM in the background (`_read_in_background`).
        None if the reader fails: the policy then plays on the Signals it had."""
        from buyer.llm import get_client, read

        n = len(events)
        with self._lock:
            done = self.readings.get(sid)
            if done and done[0] == n:
                return done[1]
            last = self.last_sent.get(sid)
        try:
            if self.blocking_reader:
                reading = read(latest(events), last_decision=last, deadline=deadline)
            else:
                reading = read(latest(events), last_decision=last, use_llm=False)
        except Exception:
            log.exception("%s: reading the reply failed - playing on the earlier signals", sid)
            return None
        with self._lock:
            self.readings[sid] = (n, reading)
        if not self.blocking_reader and get_client("reader").enabled:
            threading.Thread(
                target=self._read_in_background, args=(sid, latest(events), n, last, deadline),
                daemon=True, name=f"reader-{sid}",
            ).start()  # fmt: skip
        return reading

    def _read_in_background(self, sid, message, n, last, deadline):
        """The LLM's Reading of one reply: replaces the rules' Reading of that reply (if the thread has
        not moved on) and waits for the next trace. Never raises - the rules' Reading stays."""
        from buyer.llm import read

        try:
            reading = read(message, last_decision=last, deadline=deadline)
        except Exception:
            log.exception("%s: the background reader failed - the keyword rules stand", sid)
            return
        with self._lock:
            current = self.readings.get(sid)
            if current and current[0] == n and reading.source != "rules":  # an LLM answer, same reply
                self.readings[sid] = (n, reading)
            self.llm_readings[sid] = [n, reading, False]

    def _llm_reading_trace(self, sid, n):
        """The background reader's result for the run log, once: this reply's if it has arrived,
        else a note that it is still running (it is logged with the next move)."""
        with self._lock:
            entry = self.llm_readings.get(sid)
            if entry and not entry[2]:
                entry[2] = True
                key = "reader_llm" if entry[0] == n else "reader_llm_previous"
                r = entry[1]
                return {key: {"source": r.source, "latency_s": r.latency_s, "error": r.error,
                              "from_rules": r.from_rules, "signals": r.signals}}  # fmt: skip
        from buyer.llm import get_client

        if self.blocking_reader or not get_client("reader").enabled:
            return {}
        return {"reader_llm": {"pending": True}}

    def _message(self, case, threads, decision, profile, reading, deadline):
        move, email = message_for(
            decision,
            case,
            threads.get(decision.supplier_id) or [],
            profile,
            reading.signals if reading else None,
            known_id=self._known_id(case, threads),
            deadline=deadline,
        )
        if decision.kind == "send":
            with self._lock:
                self.last_sent[decision.supplier_id] = decision
        return move, email

    def _warm(self, case):
        """The Scout's profiles and CaseData, loaded once per case by the first thread that gets here;
        the others wait for it (instead of playing a move without them)."""
        with self._init_lock:
            if self.profiles is None:
                profiles = scout_profiles(case)
                with self._lock:
                    if self.profiles is None:
                        self.profiles = profiles
            self._case_data(case)

    def _case_data(self, case):
        """The Scout's CaseData for this case (case facts, Sunday release, package), or None."""
        if not self._data_tried:
            self._data_tried = True
            try:
                from buyer.facts.package import CaseData

                self._data = CaseData(case)
            except Exception:
                log.exception("case data failed - the writer keeps only the IDs of its claims")
        return self._data

    def _known_id(self, case, threads):
        """known_id for the writer: an ID the arena knows - citable data, or an offer of this session."""
        offers = {ts.get("term_sheet_id") for ev in threads.values() for m in ev for ts in m.get("term_sheets") or []}
        data = self._case_data(case)

        def known(ref):
            return ref in offers or (data is not None and data.citable(ref))

        return known

    def _writer_profile(self, case, sid):
        """The Scout's profile of this supplier, with its name for the greeting."""
        p = dict((self.profiles or {}).get(sid) or {})
        p.setdefault("supplier_id", sid)
        if not p.get("name") and self._data is not None:
            try:
                p["name"] = (self._data.lookup(sid) or {}).get("name")
            except Exception:
                pass
        return p


class PaymentProbe:
    """Harvest probe: every term sheet the agent sends proposes `payment_days` (one of the case's
    options) instead of what the agent chose - how do suppliers price other payment terms?"""

    def __init__(self, agent, payment_days):
        self.agent, self.days = agent, payment_days

    def decide(self, case, threads, supplier_id):
        d = self.agent.decide(case, threads, supplier_id)
        msg = d["message"]
        if not msg.get("term_sheets") or "payment_days" not in case["negotiable"]:
            return d
        sheets = []
        for ts in msg["term_sheets"]:
            terms = {**ts["terms"], "payment_days": self.days}
            if terms not in [s["terms"] for s in sheets]:  # sheets that differed only in payment days
                sheets.append({**ts, "terms": terms})
        trace = {**(d.get("trace") or {}), "probe": {"payment_days": self.days, "agent_sheets": msg["term_sheets"]}}
        return {**d, "message": {**msg, "term_sheets": sheets}, "trace": trace}

    def closing(self, case, threads):
        if hasattr(self.agent, "closing"):
            return self.agent.closing(case, threads)
        return closing_move(case, threads)


def probes(case):
    """The probe variants for a case: push past a final offer; propose each payment term the case
    allows; both together."""
    days = case.get("term_options", {}).get("payment_days") or [] if "payment_days" in case["negotiable"] else []
    return [
        {"push_final": True},
        *({"payment_days": d} for d in days),
        *({"push_final": True, "payment_days": d} for d in days),
    ]


def probe_agent(name, params, probe):
    """An agent for a probe variant: push_final through the policy's own parameter, payment days
    through PaymentProbe."""
    if probe.get("push_final"):
        params = {**(params or {}), "push_final": 1.0}  # the policy pushes once after a final offer
    agent = new_agent(name, params)
    return PaymentProbe(agent, probe["payment_days"]) if "payment_days" in probe else agent


def scout_profiles(case):
    """The Scout's profile per supplier (floor estimate, cash rate); {} if the facts layer fails."""
    try:
        from buyer.facts.profile import profile

        return profile(case)
    except Exception:
        log.exception("supplier profiles failed - playing without them")
        return {}


def message_for(decision, case, events, profile=None, signals=None, known_id=None, deadline=None):
    """A Decision as the runtime sends it: ({"supplier_id", "message"}, Email or None). The e-mail is
    the Diplomat's (`buyer.llm.to_message`): the LLM's words around the Decision's figures, else its
    template; accept and walk-away are actions without an e-mail."""
    from buyer.llm import to_message

    try:
        message, email = to_message(decision, case, events, profile, signals, known_id=known_id, deadline=deadline)
    except Exception:
        if decision.kind != "send":
            raise
        log.exception("%s: the writer raised - sending a bare e-mail", decision.supplier_id)
        subject = next((m.get("subject") for m in events or [] if m.get("subject")), "your offer")
        subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        sentences = [c.sentence for c in decision.claims or [] if getattr(c, "sentence", None)][:3]
        body = "\n\n".join(["Dear colleagues,", "Thank you for your message. Our options are in the term sheets.",
                             *sentences, "Best regards\nHollerau Pumpenwerke, Purchasing"])
        sheets = [{"terms": dict(x)} for x in decision.term_sheets[:3] if isinstance(x, dict)]
        message, email = {"subject": subject, "body": body, "term_sheets": sheets, "refs": []}, None
    return {"supplier_id": decision.supplier_id, "message": message}, email


def diplomat_trace(reading, email):
    """What the Diplomat did in a move, for the run log (the Analyst calibrates on it)."""
    out = {}
    if reading is not None:
        out["reader"] = {"source": reading.source, "latency_s": reading.latency_s, "error": reading.error,
                         "from_rules": reading.from_rules, "signals": reading.signals}  # fmt: skip
    if email is not None:
        out["writer"] = {"source": email.source, "latency_s": email.latency_s, "warnings": email.warnings}
    return out


def new_agent(name="naive", params=None):
    if name == "naive":
        from arena_kit.agents import NaiveAgent

        keep = {k: v for k, v in (params or {}).items() if k in ("anchor", "close_gap")}
        return PerThread(NaiveAgent(**keep))
    if name == "llm":
        from arena_kit.agents import LLMAgent, llm_from_env
        from arena_kit.data import DataPackage

        data = os.environ.get("ARENA_DATA")
        package = DataPackage(data) if data else None
        return PerThread(LLMAgent(llm_from_env(), package))
    if name == "policy":
        return PolicyAgent(params)
    raise ValueError(f"unknown agent {name!r}: naive, llm or policy")


def explore_params(path=None):
    """The parameter sets the Analyst wants harvested (a JSON list of dicts). Without the file: one
    empty set, i.e. the policy's params.json. The Operator runs and logs them; it never picks them."""
    try:
        sets = json.loads((path or EXPLORE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [{}]
    if isinstance(sets, dict):  # {"sets": [...]} is fine too
        sets = sets.get("sets", [sets])
    return sets or [{}]
