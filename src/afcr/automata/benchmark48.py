"""The shared agent-execution automaton (48 logical states by default; 64 / 96 via filler states).

Formal model
------------
A *time-augmented Markov decision process under a fixed policy*:

    Q          finite set of logical states (>= 48), partitioned into six groups
    Σ          action symbols (e.g. ``select_good`` / ``select_wrong`` / ``search_good`` ...)
    P(q'|q,a)  environment kernel
    π(a|q)     the agent's (stochastic) policy;  ρ(q) ∈ A(q) the *reference* (repair) action
    H          horizon: a run that has not reached a terminal state after H steps is a failure (timeout)
    F ⊂ Q      accepting (success) terminals, everything else terminal = rejecting.

A *planted fault mechanism* is a decision state whose policy puts probability ε on a fault action that enters a
"corridor" of corrupted states which mostly lead to failure (with small heal / false-accept probabilities).

Exact quantities are available by backward induction (``value_table``), so every experiment has *exact* ground truth:

    V_t(q)  = P(success | state q at time t, policy π afterwards)
    μ_t^rep = Σ_q' P(q'|q_{t-1},ρ(q_{t-1})) V_t(q')        (repair value of step t)
    μ_t^res = V_{t-1}(q_{t-1})                              (resample value of step t = CAR's null intervention)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .base import AutomatonError, State, StateInfo, Symbol, Trace, TraceStep
from .dfa import DFA
from .lts import LTS, Transition
from .nfa import ENFA, NFA, EPS
from .pa import ProbabilisticAutomaton

GROUPS = ("PLAN", "OBSERVE", "TOOL", "MEMORY", "VALIDATE", "TERMINAL")


@dataclass
class ActionSpec:
    symbol: Symbol
    next: dict[State, float]
    category: str = "reasoning"
    is_fault: bool = False


@dataclass
class StateSpec:
    info: StateInfo
    actions: dict[Symbol, ActionSpec] = field(default_factory=dict)
    policy: dict[Symbol, float] = field(default_factory=dict)
    ref: Symbol | None = None


@dataclass
class Rollout:
    """One simulated continuation.  ``path`` holds (t, state_idx, action_idx) for every decision taken."""
    path: list[tuple[int, int, int]]
    terminal: int | None           # state index of terminal reached, None if timed out
    success: bool
    steps: int
    timed_out: bool = False


@dataclass
class OriginalTrajectory:
    """A (failed) trajectory  τ = (q_0, a_1, q_1, ..., a_T, q_T)  plus ground-truth bookkeeping."""
    states: list[int]              # q_0 .. q_T
    actions: list[int]             # a_1 .. a_T
    success: bool
    fault_steps: list[int]         # steps t (1-based) at which a planted fault action fired
    fault_symbols: list[str]

    @property
    def T(self) -> int:
        return len(self.actions)

    @property
    def planted_cause(self) -> int | None:
        """Planted culprit := the LAST fault that fired (earlier ones were healed before the failure)."""
        return self.fault_steps[-1] if self.fault_steps else None


class AgentModel:
    def __init__(self, specs: dict[State, StateSpec], init: State, horizon: int, name: str = "agent48"):
        self.name = name
        self.specs = specs
        self.init = init
        self.horizon = horizon
        self.ids: list[State] = list(specs)
        self.idx = {s: i for i, s in enumerate(self.ids)}
        self.heal_edges: dict[State, State] = {}
        self._compile()

    # ------------------------------------------------------------------ structure
    @property
    def accepting(self) -> set[State]:
        return {s for s, sp in self.specs.items() if sp.info.kind == "accepting"}

    @property
    def rejecting(self) -> set[State]:
        return {s for s, sp in self.specs.items() if sp.info.kind == "rejecting"}

    @property
    def alphabet(self) -> frozenset[Symbol]:
        return frozenset(a for sp in self.specs.values() for a in sp.actions)

    def count_logical_states(self) -> int:
        """Number of *distinct* logical states (unique ids AND unique labels; no sink / visualisation nodes)."""
        ids = {sp.info.id for sp in self.specs.values()}
        labels = {sp.info.label for sp in self.specs.values()}
        if len(ids) != len(self.specs) or len(labels) != len(self.specs):
            raise AutomatonError("duplicate state ids or labels")
        return len(ids)

    def group_counts(self) -> dict[str, int]:
        out = {g: 0 for g in GROUPS}
        for sp in self.specs.values():
            out[sp.info.group] += 1
        return out

    def decision_states(self) -> list[State]:
        return [s for s, sp in self.specs.items() if sp.info.role == "decision"]

    def fault_symbols(self) -> set[Symbol]:
        return {a for sp in self.specs.values() for a, spec in sp.actions.items() if spec.is_fault}

    # ------------------------------------------------------------------ validation
    def validate(self, *, min_states: int = 40, tol: float = 1e-9) -> None:
        n = self.count_logical_states()
        if n < min_states:
            raise AutomatonError(f"only {n} logical states, need >= {min_states}")
        if self.init not in self.specs:
            raise AutomatonError("init state missing")
        for s, sp in self.specs.items():
            terminal = sp.info.kind in ("accepting", "rejecting")
            if terminal:
                if sp.actions:
                    raise AutomatonError(f"terminal state {s} must not have outgoing actions")
                continue
            if not sp.actions:
                raise AutomatonError(f"non-terminal state {s} has no outgoing action (deadlock)")
            tot = sum(sp.policy.get(a, 0.0) for a in sp.actions)
            if abs(tot - 1.0) > tol or any(a not in sp.actions for a in sp.policy):
                raise AutomatonError(f"policy at {s} is not a distribution over its actions (sum={tot})")
            if sp.ref not in sp.actions:
                raise AutomatonError(f"reference action of {s} is not an action of the state")
            for a, spec in sp.actions.items():
                if abs(sum(spec.next.values()) - 1.0) > tol or any(p < 0 for p in spec.next.values()):
                    raise AutomatonError(f"kernel of ({s},{a}) is not a probability distribution")
                for r in spec.next:
                    if r not in self.specs:
                        raise AutomatonError(f"({s},{a}) -> unknown state {r}")
        reach = self.reachable_states()
        missing = set(self.specs) - reach
        if missing:
            raise AutomatonError(f"states unreachable from init: {sorted(missing)}")
        if not (reach & self.accepting):
            raise AutomatonError("no accepting state reachable")
        if not (reach & self.rejecting):
            raise AutomatonError("no rejecting state reachable")

    def reachable_states(self) -> set[State]:
        seen, st = {self.init}, [self.init]
        while st:
            s = st.pop()
            for spec in self.specs[s].actions.values():
                for r in spec.next:
                    if r not in seen:
                        seen.add(r); st.append(r)
        return seen

    # ------------------------------------------------------------------ compiled form for fast simulation
    def _compile(self) -> None:
        n = len(self.ids)
        self.terminal = np.zeros(n, dtype=bool)
        self.accepting_mask = np.zeros(n, dtype=bool)
        self.sym_ids: list[list[Symbol]] = []
        self.pol_cum: list[list[float]] = []
        self.next_ids: list[list[list[int]]] = []
        self.next_cum: list[list[list[float]]] = []
        self.ref_idx = np.full(n, -1, dtype=int)
        self.fault_mask: list[list[bool]] = []
        for i, s in enumerate(self.ids):
            sp = self.specs[s]
            self.terminal[i] = sp.info.kind in ("accepting", "rejecting")
            self.accepting_mask[i] = sp.info.kind == "accepting"
            syms = list(sp.actions)
            self.sym_ids.append(syms)
            cum, c = [], 0.0
            for a in syms:
                c += sp.policy.get(a, 0.0); cum.append(c)
            if cum:
                cum[-1] = 1.0
            self.pol_cum.append(cum)
            if sp.ref in syms:
                self.ref_idx[i] = syms.index(sp.ref)
            nn, nc, fm = [], [], []
            for a in syms:
                spec = sp.actions[a]
                tg = [self.idx[r] for r in spec.next]
                cc, c2 = [], 0.0
                for r in spec.next:
                    c2 += spec.next[r]; cc.append(c2)
                if cc:
                    cc[-1] = 1.0
                nn.append(tg); nc.append(cc); fm.append(spec.is_fault)
            self.next_ids.append(nn); self.next_cum.append(nc); self.fault_mask.append(fm)

    @staticmethod
    def _pick(cum: list[float], u: float) -> int:
        for i, c in enumerate(cum):
            if u < c:
                return i
        return len(cum) - 1

    # ------------------------------------------------------------------ simulation
    def simulate(self, rng: np.random.Generator, q: int, t: int, *, forced_action: int | None = None,
                 record: bool = True) -> Rollout:
        """Run from state ``q`` at time ``t`` (``t`` transitions already used) until a terminal state or the horizon.

        If ``forced_action`` is given it is used for the FIRST decision instead of sampling from π (a *do* intervention).
        """
        H = self.horizon
        draws = rng.random(2 * (H - t) + 2).tolist()
        k = 0
        path: list[tuple[int, int, int]] = []
        first = True
        while t < H:
            if self.terminal[q]:
                return Rollout(path, q, bool(self.accepting_mask[q]), len(path))
            if first and forced_action is not None:
                a = forced_action
            else:
                a = self._pick(self.pol_cum[q], draws[k])
            first = False
            k += 1
            if record:
                path.append((t, q, a))
            q = self.next_ids[q][a][self._pick(self.next_cum[q][a], draws[k])]
            k += 1
            t += 1
        if self.terminal[q]:
            return Rollout(path, q, bool(self.accepting_mask[q]), len(path))
        return Rollout(path, None, False, len(path), timed_out=True)

    def sample_original(self, rng: np.random.Generator) -> OriginalTrajectory:
        """Sample one full episode from the initial state under π, recording planted fault firings."""
        q, t = self.idx[self.init], 0
        states, actions, fs, fsym = [q], [], [], []
        H = self.horizon
        while t < H and not self.terminal[q]:
            a = self._pick(self.pol_cum[q], rng.random())
            if self.fault_mask[q][a]:
                fs.append(t + 1); fsym.append(self.sym_ids[q][a])
            q2 = self.next_ids[q][a][self._pick(self.next_cum[q][a], rng.random())]
            actions.append(a); states.append(q2); q = q2; t += 1
        success = bool(self.terminal[q] and self.accepting_mask[q])
        return OriginalTrajectory(states, actions, success, fs, fsym)

    def sample_failed(self, rng: np.random.Generator, *, min_len: int = 4, require_fault: bool = False,
                      max_tries: int = 100000) -> OriginalTrajectory:
        """Rejection-sample a *failed* trajectory (optionally one that contains a planted fault)."""
        for _ in range(max_tries):
            tr = self.sample_original(rng)
            if tr.success or tr.T < min_len:
                continue
            if require_fault and not tr.fault_steps:
                continue
            return tr
        raise AutomatonError("could not sample a failed trajectory; check the model parameters")

    # ------------------------------------------------------------------ exact ground truth
    def value_table(self) -> np.ndarray:
        """V[t, q] = P(success | q at time t) for t = 0..H, by backward induction (exact)."""
        if getattr(self, "_V", None) is not None:
            return self._V
        H, n = self.horizon, len(self.ids)
        V = np.zeros((H + 1, n))
        V[:, self.accepting_mask] = 1.0                 # a terminal accepting state stays accepting
        for t in range(H - 1, -1, -1):
            for q in range(n):
                if self.terminal[q]:
                    continue
                v = 0.0
                cum_prev = 0.0
                for a, (tg, cc) in enumerate(zip(self.next_ids[q], self.next_cum[q])):
                    pa = self.pol_cum[q][a] - cum_prev; cum_prev = self.pol_cum[q][a]
                    if pa <= 0:
                        continue
                    prev, e = 0.0, 0.0
                    for r, c in zip(tg, cc):
                        e += (c - prev) * V[t + 1, r]; prev = c
                    v += pa * e
                V[t, q] = v
        self._V = V
        return V

    def exact_mu(self, traj: OriginalTrajectory, intervention: str = "repair",
                 steps: list[int] | None = None, V: np.ndarray | None = None) -> np.ndarray:
        """Exact μ_t for the requested steps (1-based).  ``intervention`` ∈ {'repair', 'resample'}."""
        V = self.value_table() if V is None else V
        steps = list(range(1, traj.T + 1)) if steps is None else steps
        out = np.zeros(len(steps))
        for k, t in enumerate(steps):
            q = traj.states[t - 1]
            if intervention == "resample":
                out[k] = V[t - 1, q]
            else:
                a = int(self.ref_idx[q])
                prev, e = 0.0, 0.0
                for r, c in zip(self.next_ids[q][a], self.next_cum[q][a]):
                    e += (c - prev) * V[t, r]; prev = c
                out[k] = e
        return out

    def success_probability(self) -> float:
        return float(self.value_table()[0, self.idx[self.init]])

    # ------------------------------------------------------------------ formal views
    def to_pa(self) -> ProbabilisticAutomaton:
        """Probabilistic automaton over action symbols (policy is the *input*; kernel is the PA's randomness)."""
        trans = {}
        for s, sp in self.specs.items():
            for a, spec in sp.actions.items():
                trans[(s, a)] = dict(spec.next)
        return ProbabilisticAutomaton(self.ids, self.alphabet, trans, self.init, self.accepting)

    def to_lts(self) -> LTS:
        trs = []
        for s, sp in self.specs.items():
            for a, spec in sp.actions.items():
                for r, p in spec.next.items():
                    trs.append(Transition(s, a, r, sp.policy.get(a, 0.0) * p, spec.category))
        return LTS(self.ids, trs, self.init, self.accepting, self.rejecting)

    def to_dfa(self) -> DFA:
        """DFA skeleton: δ(q,a) = the MOST LIKELY successor of (q,a); missing pairs -> explicit sink; F = success terminals."""
        delta = {}
        for s, sp in self.specs.items():
            for a, spec in sp.actions.items():
                delta[(s, a)] = max(spec.next.items(), key=lambda kv: (kv[1], kv[0]))[0]
        return DFA(self.ids, self.alphabet, delta, self.init, self.accepting, complete_with_sink=True)

    def to_nfa(self) -> NFA:
        """NFA: δ(q,a) = every successor with positive probability (probabilities forgotten)."""
        delta = {(s, a): set(spec.next) for s, sp in self.specs.items() for a, spec in sp.actions.items()}
        return NFA(self.ids, self.alphabet, delta, self.init, self.accepting)

    def to_enfa(self) -> ENFA:
        """ε-NFA: silent self-correction ('heal') edges become ε-moves; everything else as in :meth:`to_nfa`."""
        delta: dict[tuple[State, Symbol], set[State]] = {}
        for s, sp in self.specs.items():
            for a, spec in sp.actions.items():
                h = self.heal_edges.get(s)
                tg = set(spec.next)
                if h is not None and h in tg and not spec.is_fault and sp.info.role in ("fault_entry", "corridor"):
                    tg.discard(h)
                    delta.setdefault((s, EPS), set()).add(h)
                if tg:
                    delta[(s, a)] = tg
        return ENFA(self.ids, self.alphabet, delta, self.init, self.accepting)

    def describe(self) -> dict[str, Any]:
        nodes = []
        for i, (s, sp) in enumerate(self.specs.items()):
            nodes.append({**sp.info.to_json(), "index": i, "ref_action": sp.ref,
                          "policy": sp.policy, "is_initial": s == self.init})
        edges = []
        for s, sp in self.specs.items():
            for a, spec in sp.actions.items():
                for r, p in spec.next.items():
                    edges.append({"source": s, "target": r, "label": a, "category": spec.category,
                                  "is_fault": spec.is_fault, "kernel_prob": p,
                                  "policy_prob": sp.policy.get(a, 0.0), "prob": sp.policy.get(a, 0.0) * p})
        return {"name": self.name, "n_states": len(self.specs), "horizon": self.horizon, "groups": self.group_counts(),
                "alphabet": sorted(self.alphabet), "nodes": nodes, "edges": edges,
                "fault_symbols": sorted(self.fault_symbols()), "success_probability": self.success_probability()}


# =============================================================================================================
#  builder
# =============================================================================================================

DEFAULT_EPS = {
    "PLAN_SUBGOAL": 0.25, "OBS_SEARCH": 0.15, "OBS_READ": 0.20, "TOOL_SELECT": 0.10,
    "MEM_WRITE": 0.15, "REASON_STEP": 0.10, "VAL_DIAGNOSE": 0.20,
}

_FILLER_GROUPS = ("PLAN", "OBSERVE", "TOOL", "MEMORY", "VALIDATE")


def build_agent_model(n_states: int = 48, *, eps: dict[str, float] | None = None, noise: float = 1.0,
                      heal: float = 0.08, leak: float = 0.06, false_accept: float = 0.10, horizon: int | None = None,
                      name: str | None = None) -> AgentModel:
    """Build the agent automaton.  ``n_states`` ≥ 48; surplus states are benign *filler* steps spread over the five
    non-terminal groups (they lengthen trajectories and add harmless candidate interventions).

    ``eps``   fault probability per decision state (planted mechanisms);  ``noise`` scales environment stochasticity;
    ``heal``  per-step probability that a corrupted state silently recovers;  ``leak``  immediate-failure leak per corridor
    state;  ``false_accept``  probability that the validator wrongly accepts a flawed draft.
    """
    if n_states < 48:
        raise AutomatonError("this builder defines the 48-state core; use n_states >= 48")
    e = {**DEFAULT_EPS, **(eps or {})}
    for k, v in e.items():
        if not 0.0 <= v < 1.0:
            raise AutomatonError(f"fault probability {k}={v} must lie in [0, 1)")
    nz = max(noise, 0.0)
    stall = min(0.03 * nz, 0.3)

    specs: dict[State, StateSpec] = {}

    def add(id_, label, group, kind, role, desc, note, actions, policy=None, ref=None):
        info = StateInfo(id_, label, group, kind, role, desc, note)
        pol = policy if policy is not None else ({next(iter(actions)): 1.0} if actions else {})
        specs[id_] = StateSpec(info, actions, pol, ref if ref is not None else (next(iter(actions)) if actions else None))

    def go(symbol, targets: dict[str, float], category="reasoning", fault=False, stall_self: str | None = None):
        t = dict(targets)
        if stall_self is not None and stall > 0:
            scale = 1.0 - stall
            t = {k: v * scale for k, v in t.items()}
            t[stall_self] = t.get(stall_self, 0.0) + stall
        return ActionSpec(symbol, t, category, fault)

    # ---- extra benign filler states per group --------------------------------------------------------
    extra = n_states - 48
    fill = {g: 0 for g in _FILLER_GROUPS}
    for i in range(extra):
        fill[_FILLER_GROUPS[i % len(_FILLER_GROUPS)]] += 1

    def chain(group: str, prefix: str, nxt: str, label_prefix: str, cat: str, desc: str) -> str:
        """Create ``fill[group]`` filler states in a chain ending at ``nxt``; return the id of the first one (or nxt)."""
        cur = nxt
        for k in range(fill[group], 0, -1):
            sid = f"{prefix}_{k}"
            add(sid, f"{label_prefix} {k}", group, "nonterminal", "benign", desc,
                "benign step: intervening here is expected to be harmless",
                {f"{prefix.lower()}_step": go(f"{prefix.lower()}_step", {cur: 1.0}, cat, stall_self=sid)})
            cur = sid
        return cur

    # ============================= PLAN =============================
    plan_subgoal_entry = "PLAN_SUBGOAL"
    plan_tools_entry = "PLAN_TOOLS"
    add("PLAN_START", "Start", "PLAN", "nonterminal", "benign", "Initial state: task received, nothing decided yet.", "never a culprit",
        {"start": go("start", {"PLAN_PARSE": 1.0}, "reasoning", stall_self="PLAN_START")})
    add("PLAN_PARSE", "Parse task", "PLAN", "nonterminal", "benign", "Read and normalise the task specification.", "",
        {"parse": go("parse", {"PLAN_DECOMP": 1.0}, "reasoning", stall_self="PLAN_PARSE")})
    decomp_next = chain("PLAN", "PLAN_REFINE", plan_subgoal_entry, "Refine plan", "reasoning", "Extra benign planning refinement.")
    add("PLAN_DECOMP", "Decompose task", "PLAN", "nonterminal", "benign", "Split the task into subgoals.", "",
        {"decompose": go("decompose", {decomp_next: 1.0}, "reasoning", stall_self="PLAN_DECOMP")})
    add("PLAN_SUBGOAL", "Select subgoal", "PLAN", "nonterminal", "decision",
        "Choose which subgoal to pursue next. DECISION POINT: choosing the wrong subgoal corrupts everything downstream.",
        "planted fault: incorrect planning decision",
        {"select_good": go("select_good", {"PLAN_TOOLS": 1.0}, "reasoning"),
         "select_wrong": go("select_wrong", {"PLAN_SUBGOAL_WRONG": 1.0}, "reasoning", fault=True)},
        {"select_good": 1 - e["PLAN_SUBGOAL"], "select_wrong": e["PLAN_SUBGOAL"]}, "select_good")
    add("PLAN_SUBGOAL_WRONG", "Wrong subgoal selected", "PLAN", "nonterminal", "fault_entry",
        "The agent committed to an irrelevant or incorrect subgoal.", "entry of the corrupted corridor (planning)", {})
    add("PLAN_TOOLS", "Plan tool use", "PLAN", "nonterminal", "benign", "Decide which tools will be needed.", "",
        {"plan_tools": go("plan_tools", {"PLAN_COMMIT": 1 - 0.10 * min(nz, 5), "PLAN_REVISE": 0.10 * min(nz, 5)}, "reasoning")})
    add("PLAN_REVISE", "Revise plan", "PLAN", "nonterminal", "benign", "Minor plan revision before committing.", "",
        {"revise": go("revise", {"PLAN_TOOLS": 1.0}, "reasoning", stall_self="PLAN_REVISE")})
    obs_first = "OBS_QUERY"
    add("PLAN_COMMIT", "Commit plan", "PLAN", "nonterminal", "benign", "Freeze the plan and start gathering information.", "",
        {"commit": go("commit", {obs_first: 1.0}, "reasoning", stall_self="PLAN_COMMIT")})

    # ============================= OBSERVE =============================
    add("OBS_QUERY", "Formulate query", "OBSERVE", "nonterminal", "benign", "Turn the current subgoal into a search query.", "",
        {"query": go("query", {"OBS_SEARCH": 1.0}, "observation", stall_self="OBS_QUERY")})
    add("OBS_SEARCH", "Choose resource", "OBSERVE", "nonterminal", "decision",
        "Choose where to search. DECISION POINT: a wrong resource yields misleading evidence.",
        "planted fault: wrong resource searched",
        {"search_good": go("search_good", {"OBS_RESULTS": 1.0}, "observation"),
         "search_wrong": go("search_wrong", {"OBS_WRONG_RESOURCE": 1.0}, "observation", fault=True)},
        {"search_good": 1 - e["OBS_SEARCH"], "search_wrong": e["OBS_SEARCH"]}, "search_good")
    add("OBS_WRONG_RESOURCE", "Wrong resource searched", "OBSERVE", "nonterminal", "fault_entry",
        "Evidence is being gathered from a resource that cannot contain the answer.", "corridor (observation)", {})
    browse_next = "OBS_READ"
    browse_first = chain("OBSERVE", "OBS_BROWSE", browse_next, "Browse page", "observation", "Extra benign browsing step.")
    add("OBS_RESULTS", "Search results", "OBSERVE", "nonterminal", "benign", "Results returned; may be empty (search again).", "",
        {"results": go("results", {"OBS_BROWSE": 1 - 0.12 * min(nz, 5), "OBS_SEARCH": 0.12 * min(nz, 5)}, "observation")})
    add("OBS_BROWSE", "Browse page", "OBSERVE", "nonterminal", "benign", "Open the most promising result.", "",
        {"browse": go("browse", {browse_first: 1.0}, "observation", stall_self="OBS_BROWSE")})
    add("OBS_READ", "Interpret document", "OBSERVE", "nonterminal", "decision",
        "Interpret the retrieved document. DECISION POINT: misreading corrupts the evidence the agent reasons over.",
        "planted fault: incorrect observation interpretation",
        {"read_good": go("read_good", {"OBS_EVIDENCE": 1.0}, "observation"),
         "misread": go("misread", {"OBS_MISREAD": 1.0}, "observation", fault=True)},
        {"read_good": 1 - e["OBS_READ"], "misread": e["OBS_READ"]}, "read_good")
    add("OBS_MISREAD", "Document misread", "OBSERVE", "nonterminal", "fault_entry",
        "The agent holds a wrong interpretation of the evidence.", "corridor (observation)", {})
    add("OBS_EVIDENCE", "Evidence ready", "OBSERVE", "nonterminal", "benign", "Evidence extracted; move to tool use.", "",
        {"extract": go("extract", {"TOOL_SELECT": 1.0}, "observation", stall_self="OBS_EVIDENCE")})

    # ============================= TOOL =============================
    tool_args_next = chain("TOOL", "TOOL_PRE", "TOOL_CALL", "Pre-check call", "tool_use", "Extra benign argument pre-check.")
    add("TOOL_SELECT", "Select tool", "TOOL", "nonterminal", "decision",
        "Pick a tool. DECISION POINT: an invalid tool choice produces garbage that is written to memory.",
        "planted fault: invalid tool choice",
        {"tool_valid": go("tool_valid", {"TOOL_ARGS": 1.0}, "tool_use"),
         "tool_invalid": go("tool_invalid", {"TOOL_INVALID": 1.0}, "tool_use", fault=True)},
        {"tool_valid": 1 - e["TOOL_SELECT"], "tool_invalid": e["TOOL_SELECT"]}, "tool_valid")
    add("TOOL_INVALID", "Invalid tool chosen", "TOOL", "nonterminal", "fault_entry",
        "A tool that cannot serve the subgoal was invoked.", "corridor (tool)", {})
    add("TOOL_ARGS", "Build arguments", "TOOL", "nonterminal", "benign", "Construct the tool-call arguments.", "",
        {"args": go("args", {tool_args_next: 1.0}, "tool_use", stall_self="TOOL_ARGS")})
    add("TOOL_CALL", "Call tool", "TOOL", "nonterminal", "benign", "Execute the tool call (may fail transiently).", "",
        {"call": go("call", {"TOOL_OK": 1 - 0.12 * min(nz, 5), "TOOL_ERROR": 0.12 * min(nz, 5)}, "tool_use")})
    add("TOOL_OK", "Tool succeeded", "TOOL", "nonterminal", "benign", "The tool returned a result.", "",
        {"ack": go("ack", {"TOOL_PARSED": 1.0}, "tool_use", stall_self="TOOL_OK")})
    add("TOOL_ERROR", "Tool error", "TOOL", "nonterminal", "benign", "The tool returned an error.", "",
        {"handle_error": go("handle_error", {"TOOL_RETRY": 1.0}, "tool_use")})
    add("TOOL_RETRY", "Retry tool", "TOOL", "nonterminal", "recovery", "Retry or re-select; retry budget may be exhausted.", "spontaneous (non-planted) failure source",
        {"retry": go("retry", {"TOOL_CALL": 0.70, "TOOL_SELECT": 0.20, "FAIL_TIMEOUT": 0.10}, "recovery")})
    add("TOOL_PARSED", "Parse tool result", "TOOL", "nonterminal", "benign", "Extract the useful content from the tool result.", "",
        {"parse_result": go("parse_result", {"MEM_READ": 1.0}, "state_update", stall_self="TOOL_PARSED")})

    # ============================= MEMORY / REASONING =============================
    mem_note_next = chain("MEMORY", "MEM_NOTE", "MEM_WRITE", "Take note", "state_update", "Extra benign memory note.")
    add("MEM_READ", "Read memory", "MEMORY", "nonterminal", "benign", "Recall relevant facts from memory.", "",
        {"recall": go("recall", {mem_note_next: 1.0}, "state_update", stall_self="MEM_READ")})
    add("MEM_WRITE", "Write memory", "MEMORY", "nonterminal", "decision",
        "Store the new fact. DECISION POINT: a corrupted write silently poisons later reasoning.",
        "planted fault: memory corruption",
        {"mem_write_ok": go("mem_write_ok", {"REASON_STEP": 1.0}, "state_update"),
         "mem_corrupt": go("mem_corrupt", {"MEM_CORRUPT": 1.0}, "state_update", fault=True)},
        {"mem_write_ok": 1 - e["MEM_WRITE"], "mem_corrupt": e["MEM_WRITE"]}, "mem_write_ok")
    add("MEM_CORRUPT", "Memory corrupted", "MEMORY", "nonterminal", "fault_entry",
        "A wrong value now sits in memory.", "corridor (memory)", {})
    add("REASON_STEP", "Reason over evidence", "MEMORY", "nonterminal", "decision",
        "Combine evidence into an answer. DECISION POINT: stopping too early skips needed verification.",
        "planted fault: premature stopping",
        {"reason_ok": go("reason_ok", {"DRAFT": 1.0}, "reasoning"),
         "stop_early": go("stop_early", {"EARLY_STOP": 1.0}, "reasoning", fault=True)},
        {"reason_ok": 1 - e["REASON_STEP"], "stop_early": e["REASON_STEP"]}, "reason_ok")
    add("REASON_FLAWED", "Reasoning flawed", "MEMORY", "nonterminal", "corridor",
        "Reasoning proceeds from corrupted inputs.", "downstream error propagation", {})
    pre_check = chain("VALIDATE", "VAL_RECHECK", "VAL_CHECK", "Recheck", "validation", "Extra benign validation step.")
    add("DRAFT", "Draft answer", "MEMORY", "nonterminal", "benign", "Write the candidate answer.", "",
        {"draft": go("draft", {pre_check: 1.0}, "reasoning", stall_self="DRAFT")})
    add("DRAFT_FLAWED", "Flawed draft", "MEMORY", "nonterminal", "corridor",
        "A candidate answer built on corrupted state.", "downstream error propagation", {})
    add("EARLY_STOP", "Stopped early", "MEMORY", "nonterminal", "fault_entry",
        "The agent stopped before gathering enough evidence.", "corridor (premature stop)", {})

    # ============================= VALIDATE / RECOVER =============================
    vf = 0.08 * min(nz, 5); vp = 0.05
    add("VAL_CHECK", "Validate answer", "VALIDATE", "nonterminal", "benign",
        "Check the draft against the task; may wrongly reject a good draft.", "validator false negatives are a non-planted failure source",
        {"validate": go("validate", {"DONE_SUCCESS": 1 - vf - vp, "VAL_FAIL": vf, "DONE_PARTIAL": vp}, "validation")})
    add("VAL_FAIL", "Validation failed", "VALIDATE", "nonterminal", "recovery", "The check reported a problem.", "",
        {"report_failure": go("report_failure", {"VAL_FEEDBACK": 1.0}, "validation")})
    add("VAL_FEEDBACK", "Collect feedback", "VALIDATE", "nonterminal", "benign", "Gather the validator's error report before choosing a recovery.", "",
        {"collect": go("collect", {"VAL_DIAGNOSE": 1.0}, "validation", stall_self="VAL_FEEDBACK")})
    r = e["VAL_DIAGNOSE"]
    add("VAL_DIAGNOSE", "Diagnose and choose recovery", "VALIDATE", "nonterminal", "decision",
        "Decide how to recover. DECISION POINT: an incorrect recovery wastes the last chance.",
        "planted fault: incorrect recovery",
        {"replan": go("replan", {"VAL_REPLAN": 1.0}, "recovery"),
         "retry_tool": go("retry_tool", {"VAL_RETRY_TOOL": 1.0}, "recovery"),
         "bad_recover": go("bad_recover", {"VAL_RECOVER_BAD": 1.0}, "recovery", fault=True)},
        {"replan": 0.55 * (1 - r), "retry_tool": 0.45 * (1 - r), "bad_recover": r}, "replan")
    add("VAL_REPLAN", "Replan", "VALIDATE", "nonterminal", "recovery", "Return to subgoal selection.", "",
        {"restart_plan": go("restart_plan", {"PLAN_SUBGOAL": 1.0}, "recovery")})
    add("VAL_RETRY_TOOL", "Retry with tool", "VALIDATE", "nonterminal", "recovery", "Return to tool selection.", "",
        {"restart_tool": go("restart_tool", {"TOOL_SELECT": 1.0}, "recovery")})
    add("VAL_RECOVER_BAD", "Bad recovery", "VALIDATE", "nonterminal", "fault_entry",
        "The chosen recovery is ineffective.", "corridor (recovery)", {})
    fa = min(max(false_accept, 0.0), 0.5)
    add("VAL_CHECK_FLAWED", "Validate flawed draft", "VALIDATE", "nonterminal", "corridor",
        "Validation of a draft built on corrupted state: usually fails, sometimes caught (diagnose), rarely wrongly accepted.",
        "validator may catch (recover) or miss (fail)",
        {"validate_flawed": go("validate_flawed", {"FAIL_EVIDENCE": 0.70 - fa, "VAL_DIAGNOSE": 0.30, "DONE_PARTIAL": fa}, "validation")})

    # ============================= TERMINAL =============================
    def terminal(id_, label, kind, desc, note):
        add(id_, label, "TERMINAL", kind, "terminal_success" if kind == "accepting" else "terminal_failure", desc, note, {})
    terminal("DONE_SUCCESS", "Success (exact)", "accepting", "Task solved and validated.", "accepting")
    terminal("DONE_PARTIAL", "Success (partial)", "accepting", "Accepted answer (possibly by validator error).", "accepting; may be spurious")
    terminal("FAIL_PLAN", "Failure: wrong plan", "rejecting", "Failure attributable to planning.", "rejecting")
    terminal("FAIL_EVIDENCE", "Failure: bad evidence", "rejecting", "Failure attributable to evidence gathering/interpretation.", "rejecting")
    terminal("FAIL_TOOL", "Failure: tool misuse", "rejecting", "Failure attributable to tool handling.", "rejecting")
    terminal("FAIL_MEMORY", "Failure: memory", "rejecting", "Failure attributable to memory corruption.", "rejecting")
    terminal("FAIL_EARLY_STOP", "Failure: premature stop", "rejecting", "The agent stopped before it should.", "rejecting")
    terminal("FAIL_TIMEOUT", "Failure: timeout", "rejecting", "Retry budget or horizon exhausted.", "rejecting")

    # ============================= corridor wiring (fault entries, corridor states) ==========================
    corr_next = {"PLAN_SUBGOAL_WRONG": "OBS_WRONG_RESOURCE", "OBS_WRONG_RESOURCE": "OBS_MISREAD", "OBS_MISREAD": "TOOL_INVALID",
                 "TOOL_INVALID": "MEM_CORRUPT", "MEM_CORRUPT": "REASON_FLAWED", "REASON_FLAWED": "DRAFT_FLAWED",
                 "DRAFT_FLAWED": "VAL_CHECK_FLAWED", "EARLY_STOP": "DRAFT_FLAWED"}
    heal_to = {"PLAN_SUBGOAL_WRONG": "PLAN_TOOLS", "OBS_WRONG_RESOURCE": "OBS_SEARCH", "OBS_MISREAD": "OBS_READ",
               "TOOL_INVALID": "TOOL_SELECT", "MEM_CORRUPT": "MEM_WRITE", "REASON_FLAWED": "REASON_STEP",
               "DRAFT_FLAWED": "REASON_STEP", "EARLY_STOP": "REASON_STEP"}
    leak_to = {"PLAN_SUBGOAL_WRONG": "FAIL_PLAN", "OBS_WRONG_RESOURCE": "FAIL_EVIDENCE", "OBS_MISREAD": "FAIL_EVIDENCE",
               "TOOL_INVALID": "FAIL_TOOL", "MEM_CORRUPT": "FAIL_MEMORY", "REASON_FLAWED": "FAIL_MEMORY",
               "DRAFT_FLAWED": "FAIL_EVIDENCE", "EARLY_STOP": "FAIL_EARLY_STOP"}
    hl = min(heal, 0.4)
    for s, nxt in corr_next.items():
        lk = 0.25 if s == "EARLY_STOP" else leak
        specs[s].actions = {"propagate": go("propagate", {nxt: 1.0 - hl - lk, heal_to[s]: hl, leak_to[s]: lk}, "state_update")}
        specs[s].policy = {"propagate": 1.0}
        specs[s].ref = "propagate"
    add_rb = {"FAIL_TOOL": 0.50, "VAL_DIAGNOSE": 0.35, "FAIL_PLAN": 0.15}
    specs["VAL_RECOVER_BAD"].actions = {"flounder": go("flounder", add_rb, "recovery")}
    specs["VAL_RECOVER_BAD"].policy = {"flounder": 1.0}
    specs["VAL_RECOVER_BAD"].ref = "flounder"

    H = horizon if horizon is not None else max(60, 2 * n_states)
    model = AgentModel(specs, "PLAN_START", H, name or f"agent{n_states}")
    model.heal_edges = {k: v for k, v in heal_to.items()}
    model.validate()
    return model
