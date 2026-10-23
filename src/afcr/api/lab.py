"""Automata laboratory: model catalogue, graph views and trace results for the website.

Conventions
-----------
* Every state of every machine is exposed with a ``qid`` (``q0``, ``q1`` …): the initial state is ``q0``, the others
  follow in breadth-first order from it (the 48-state agent automaton uses its definition order).  The descriptive name
  of a state is kept as ``name`` / ``label`` so nothing is lost.
* A trace response always has ``kind``, a *list* ``steps`` and a model-specific result.  Only machines that really have
  an acceptance notion report ``accepted``: a probabilistic automaton reports a probability, transducers report their
  output word, a Turing machine reports a status (``unknown`` when a simulator bound was hit).
* Each machine comes with ``examples`` that cover the textbook cases (accept, reject, empty word, trap state, invalid
  input, unknown …); tests execute every example and check the stated expectation.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import numpy as np

from ..automata.base import EPS, AutomatonError
from ..automata.dfa import DFA
from ..automata.lts import LTS, Transition
from ..automata.nfa import ENFA, NFA
from ..automata.pa import ProbabilisticAutomaton
from ..automata.pda import nested_calls_pda, typed_nested_tools_pda
from ..automata.transducers import tool_call_controller_mealy
from ..automata.turing import TuringMachine, binary_increment_tm, palindrome_tm

# ---------------------------------------------------------------------------------------------- the machines


def _dfa() -> DFA:
    """Words over {a,b} that start with a and contain an even number of b's.  Has a dead (trap) state."""
    d = {("start", "a"): "ok_even", ("start", "b"): "dead",
         ("ok_even", "a"): "ok_even", ("ok_even", "b"): "ok_odd",
         ("ok_odd", "a"): "ok_odd", ("ok_odd", "b"): "ok_even",
         ("dead", "a"): "dead", ("dead", "b"): "dead"}
    return DFA({"start", "ok_even", "ok_odd", "dead"}, {"a", "b"}, d, "start", {"ok_even"})


def _nfa() -> NFA:
    """Words over {a,b} that end in 'ab' (guess where the suffix starts)."""
    return NFA({"q0", "q1", "q2"}, {"a", "b"}, {("q0", "a"): {"q0", "q1"}, ("q0", "b"): {"q0"}, ("q1", "b"): {"q2"}}, "q0", {"q2"})


def _enfa() -> ENFA:
    """a*b with silent (ε) moves q0 -> q1 -> q2."""
    return ENFA({"q0", "q1", "q2", "q3"}, {"a", "b"}, {("q0", EPS): {"q1"}, ("q1", EPS): {"q2"}, ("q1", "a"): {"q1"}, ("q2", "b"): {"q3"}}, "q0", {"q3"})


def _pa() -> ProbabilisticAutomaton:
    return ProbabilisticAutomaton(
        {"start", "goal", "fail"}, {"go", "retry"},
        {("start", "go"): {"goal": 0.7, "fail": 0.1, "start": 0.2}, ("start", "retry"): {"start": 0.5, "goal": 0.3, "fail": 0.2},
         ("goal", "go"): {"goal": 1.0}, ("goal", "retry"): {"goal": 0.9, "fail": 0.1},
         ("fail", "go"): {"fail": 1.0}, ("fail", "retry"): {"fail": 1.0}},
        "start", {"goal"})


def _lts() -> LTS:
    return LTS({"idle", "thinking", "calling", "done", "failed"},
               [Transition("idle", "plan", "thinking", category="reasoning"), Transition("thinking", "call_tool", "calling", category="tool_use"),
                Transition("calling", "observe_ok", "thinking", category="observation"), Transition("calling", "observe_err", "failed", category="failure"),
                Transition("thinking", "answer", "done", category="success"), Transition("thinking", "validate_fail", "idle", category="recovery")],
               "idle", accepting={"done"}, rejecting={"failed"})


def _tm_loop() -> TuringMachine:
    """Moves right forever: the simulator stops at its step limit and reports 'unknown', not 'reject'."""
    d = {("scan", "0"): ("scan", "0", "R"), ("scan", "1"): ("scan", "1", "R"), ("scan", "_"): ("scan", "_", "R")}
    return TuringMachine({"scan", "acc", "rej"}, {"0", "1"}, {"0", "1", "_"}, "_", d, "scan", "acc", "rej")


@lru_cache(maxsize=1)
def machines() -> dict[str, Any]:
    mealy = tool_call_controller_mealy()
    return dict(dfa=_dfa(), nfa=_nfa(), enfa=_enfa(), pa=_pa(), lts=_lts(), mealy=mealy, moore=mealy.to_moore("start"),
                pda=nested_calls_pda(), pda_typed=typed_nested_tools_pda(), tm=binary_increment_tm(), tm_pal=palindrome_tm(), tm_loop=_tm_loop())


# ---------------------------------------------------------------------------------------------- catalogue

def ex(label: str, word: list[str], expect: str, note: str = "") -> dict:
    return {"label": label, "word": word, "expect": expect, "note": note}


MODEL_INFO: dict[str, dict] = {
    "dfa": dict(name="DFA", definition="M = (Q, Σ, δ, q₀, F) with δ: Q×Σ→Q total", word=["a", "b", "b", "a"], accepts="accept iff the unique run ends in F",
                memory="finite (state only)", nondeterminism="none", probability="none", agent_fit="skeleton of an agent: one nominal execution per action word",
                limits="no branching, no uncertainty; cannot express stochastic replay", kind="dfa",
                description="Words over {a,b} that start with a and contain an even number of b's. q3 is a dead (trap) state: once entered, no accepting state is reachable.",
                examples=[ex("accepted", ["a", "b", "b", "a"], "accept"), ex("rejected (odd b's)", ["a", "b"], "reject"), ex("dead state", ["b", "a"], "reject", "starts with b → trap"),
                          ex("empty word", [], "reject", "q0 is not accepting"), ex("invalid symbol", ["a", "c"], "error", "c ∉ Σ")]),
    "nfa": dict(name="NFA", definition="δ: Q×Σ→2^Q ; accept iff some run accepts", word=["a", "a", "b"], accepts="active-state set contains an accepting state",
                memory="finite", nondeterminism="formal ('some path'); NOT LLM sampling randomness", probability="none",
                agent_fit="models possible environment outcomes without weights", limits="no likelihoods: cannot rank causes", kind="nfa",
                description="Words over {a,b} that end in ab. In q0 on 'a' the machine guesses: stay, or move to q1.",
                examples=[ex("accepted", ["a", "a", "b"], "accept"), ex("rejected", ["a", "b", "a"], "reject"), ex("empty word", [], "reject"),
                          ex("dead branch", ["b", "b"], "reject", "q1 has no 'a' move: that branch dies"), ex("invalid symbol", ["x"], "error")]),
    "enfa": dict(name="ε-NFA", definition="δ: Q×(Σ∪{ε})→2^Q", word=["a", "b"], accepts="ε-closure before/after each symbol",
                 memory="finite", nondeterminism="formal + silent moves", probability="none", agent_fit="silent self-correction ('heal') as ε-moves",
                 limits="same as NFA", kind="enfa",
                 description="The language a*b. The ε-moves q0→q1→q2 are silent: the machine starts in the ε-closure {q0,q1,q2}.",
                 examples=[ex("accepted", ["a", "b"], "accept"), ex("just b", ["b"], "accept", "closure already contains q2"), ex("rejected", ["a"], "reject"),
                           ex("empty word", [], "reject"), ex("too many b", ["b", "b"], "reject", "q3 has no outgoing move")]),
    "pa": dict(name="Probabilistic automaton", definition="each (q,a) → distribution over successors", word=["go", "go", "go"],
               accepts="word has an acceptance probability (exact via matrices); runs are sampled", memory="finite", nondeterminism="none (randomness is probabilistic)",
               probability="yes", agent_fit="natural model of a stochastic agent/environment", limits="finite memory; Markov", kind="pa",
               description="A stochastic tool: 'go' succeeds with probability 0.7; 'retry' is weaker. q2 (fail) is absorbing. There is no accept/reject verdict, only a probability.",
               examples=[ex("go go go", ["go", "go", "go"], "probability"), ex("retry then go", ["retry", "go"], "probability"), ex("empty word", [], "probability", "P = 0: q0 is not accepting"),
                         ex("invalid symbol", ["stop"], "error")]),
    "lts": dict(name="Labelled transition system", definition="s —a→ s' with action labels", word=["plan", "call_tool", "observe_ok", "answer"],
                accepts="reachability of accepting / rejecting states; deadlock detection", memory="finite", nondeterminism="allowed", probability="optional",
                agent_fit="execution as labelled actions: reasoning, tool use, observation, update, validation, recovery", limits="labels carry meaning only by convention", kind="lts",
                description="An agent loop: plan, call a tool, observe, answer. q3 (done) accepts and q4 (failed) rejects; both are terminal (no outgoing action). A deadlock would be a NON-terminal state with no action: there is none here.",
                examples=[ex("accepted", ["plan", "call_tool", "observe_ok", "answer"], "accept"), ex("failure", ["plan", "call_tool", "observe_err"], "reject", "ends in the rejecting state"),
                          ex("blocked action", ["plan", "answer", "plan"], "reject", "no 'plan' action from the terminal state done"), ex("empty word", [], "reject"),
                          ex("label never enabled", ["fly"], "reject", "blocked at q0: an LTS only says the action is not enabled")]),
    "mealy": dict(name="Mealy machine", definition="λ: Q×Σ→Γ — outputs on transitions", word=["task", "error", "ok"], accepts="transducer (outputs)",
                  memory="finite", nondeterminism="none", probability="none", agent_fit="controller reacting to observations", limits="no acceptance notion", kind="mealy",
                  description="A tool-call controller. The output depends on the state AND the input: from q1 'ok' gives proceed, 'error' gives retry.",
                  examples=[ex("normal run", ["task", "error", "ok"], "output"), ex("abort path", ["task", "error", "error"], "output"), ex("empty word", [], "output", "n inputs → n outputs (0)"),
                            ex("invalid symbol", ["bogus"], "error")]),
    "moore": dict(name="Moore machine", definition="λ: Q→Γ — outputs on states (Mealy→Moore needs state expansion)", word=["task", "error", "ok"],
                  accepts="transducer (n+1 outputs for n inputs)", memory="finite", nondeterminism="none", probability="none", agent_fit="state = action being executed",
                  limits="more states than the Mealy form", kind="moore",
                  description="The Moore form of the Mealy controller: states are (state, last output) pairs, so there are more states. n inputs produce n+1 outputs (the first is the start state's).",
                  examples=[ex("normal run", ["task", "error", "ok"], "output"), ex("empty word", [], "output", "one output: the start state's"), ex("invalid symbol", ["bogus"], "error")]),
    "pda": dict(name="Pushdown automaton", definition="finite control + stack", word=["call", "call", "ret", "ret"], accepts="final state and empty stack",
                memory="unbounded stack", nondeterminism="allowed", probability="none", agent_fit="nested / recursive tool invocation",
                limits="single stack; still no probabilities", kind="pda",
                description="Balanced call/ret nesting of any depth. Each call pushes C, each ret pops it; at the end only the bottom marker Z may remain.",
                examples=[ex("balanced", ["call", "call", "ret", "ret"], "accept"), ex("underflow", ["call", "ret", "ret"], "reject", "ret with an empty stack"),
                          ex("unclosed call", ["call"], "reject", "stack not empty at the end"), ex("empty word", [], "accept"), ex("invalid symbol", ["zzz"], "error")]),
    "pda_typed": dict(name="PDA (typed tools)", definition="stack records which tool was opened", word=["open_search", "open_calc", "end_calc", "end_search"],
                      accepts="properly nested typed calls", memory="unbounded stack", nondeterminism="allowed", probability="none", agent_fit="structured tool invocation",
                      limits="as PDA", kind="pda",
                      description="A tool opened as search must be closed by end_search, calc by end_calc: the stack remembers which tool is open.",
                      examples=[ex("well nested", ["open_search", "open_calc", "end_calc", "end_search"], "accept"), ex("type mismatch", ["open_search", "end_calc"], "reject", "S on top, end_calc needs K"),
                                ex("crossed", ["open_search", "open_calc", "end_search", "end_calc"], "reject"), ex("empty word", [], "accept")]),
    "tm": dict(name="Turing machine (bounded)", definition="tape + head + δ; step limit and tape bound", word=list("1011"), accepts="halts in accept state",
               memory="tape (bounded in this simulator)", nondeterminism="none", probability="none", agent_fit="general computation demo (binary increment)",
               limits="the bound is a simulator convenience, not a power claim; hitting it means 'unknown', not 'reject'", kind="tm",
               description="Binary increment, most significant bit first: 1011₂ + 1 = 1100₂. Scans right, then carries leftwards.",
               examples=[ex("1011 + 1", list("1011"), "output", "1100"), ex("all ones", list("111"), "output", "1000"), ex("empty tape", [], "output", "1"), ex("invalid symbol", ["1", "2"], "error")]),
    "tm_pal": dict(name="Turing machine (palindromes)", definition="decides palindromes over {a,b}", word=list("abba"), accepts="halts in accept", memory="tape (bounded)",
                   nondeterminism="none", probability="none", agent_fit="demo", limits="as above", kind="tm",
                   description="Erases matching end symbols from both sides; accepts palindromes, rejects the rest (q9 is the rejecting halt state).",
                   examples=[ex("palindrome", list("abba"), "accept"), ex("odd palindrome", list("aba"), "accept"), ex("not a palindrome", list("ab"), "reject"), ex("empty word", [], "accept"),
                             ex("invalid symbol", list("abc"), "error")]),
    "tm_loop": dict(name="Turing machine (never halts)", definition="a machine that loops: the simulator reports 'unknown'", word=list("01"), accepts="never halts",
                    memory="tape (bounded)", nondeterminism="none", probability="none", agent_fit="shows why a step limit is not a rejection",
                    limits="the halting problem is undecidable: a bound can only say 'unknown'", kind="tm",
                    description="Moves right forever. After the step limit the status is step_limit = unknown. It is NOT rejected.",
                    examples=[ex("loops", list("01"), "unknown", "step limit reached"), ex("empty tape", [], "unknown")]),
    "agent48": dict(name="48-state agent automaton", definition="time-augmented Markov chain with planted faults", word=[], accepts="success terminals",
                    memory="finite + time index", nondeterminism="views available", probability="yes", agent_fit="main benchmark (exact ground truth)",
                    limits="hand-designed; Markov", kind="agent",
                    description="Six groups of eight states (plan, observe, tool, memory, validate, terminal) with planted decision faults. States are q0 … q47 in definition order.",
                    examples=[]),
}
COMPARE_KEYS = ["dfa", "nfa", "enfa", "pa", "lts", "mealy", "moore", "pda", "tm"]
VIEWS = {"nfa": ["nfa", "dfa"], "enfa": ["enfa", "nfa", "dfa"]}
VIEW_NOTES = {
    ("nfa", "dfa"): "Subset construction: every DFA state is a set of NFA states; ∅ is the dead state.",
    ("enfa", "nfa"): "ε-removal: δ'(q,a) = ε-closure(δ(ε-closure(q), a)); a state becomes accepting if its closure meets F.",
    ("enfa", "dfa"): "Subset construction on ε-closures; ∅ is the dead state.",
}
STEP_LIMIT = {"tm_loop": 40}


# ---------------------------------------------------------------------------------------------- q numbering
class QMap:
    """Initial state -> q0, then breadth-first order, then any unreachable states (sorted)."""

    def __init__(self, states, start, edges):
        adj: dict[str, list[str]] = {}
        for s, d in edges:
            adj.setdefault(s, []).append(d)
        order, seen, dq = [start], {start}, deque([start])
        while dq:
            u = dq.popleft()
            for v in adj.get(u, []):
                if v not in seen:
                    seen.add(v); order.append(v); dq.append(v)
        order += sorted(set(states) - seen)
        self.q = {s: f"q{i}" for i, s in enumerate(order)}

    def __call__(self, s):
        if isinstance(s, (set, frozenset, list, tuple)):
            return sorted((self.q.get(x, x) for x in s), key=lambda t: (len(t), t))
        return self.q.get(s, s) if s is not None else None


@dataclass
class Graph:
    nodes: list[dict]
    edges: list[dict]
    qm: QMap
    extra: dict = field(default_factory=dict)


def _node(qm: QMap, s: str, **kw) -> dict:
    q = qm(s)
    return {"id": q, "qid": q, "name": s, "label": s if s != q else "", **kw}


def _edge(qm: QMap, s, t, label, **kw) -> dict:
    return {"source": qm(s), "target": qm(t), "label": label, **kw}


def _sorted_nodes(nodes):
    return sorted(nodes, key=lambda n: int(n["qid"][1:]))


def _finite_graph(obj, view: str | None) -> Graph:
    """DFA / NFA / ε-NFA (and the derived views)."""
    if isinstance(obj, DFA):
        edges_raw = [(q, r, a) for (q, a), r in sorted(obj.delta.items())]
        start, accepting, states = obj.start, obj.accepting, obj.states
        table_syms = sorted(obj.alphabet)
        qm = QMap(states, start, [(q, r) for q, r, _ in edges_raw])
        nodes = [_node(qm, s, start=s == start, accepting=s in accepting) for s in states]
        edges = [_edge(qm, q, r, a) for q, r, a in edges_raw]
        table = {qm(q): {a: qm(obj.delta[(q, a)]) for a in table_syms} for q in sorted(states, key=lambda s: int(qm(s)[1:]))}
        return Graph(_sorted_nodes(nodes), edges, qm, {"transition_table": table, "alphabet": table_syms})
    edges_raw = [(q, r, a) for (q, a), rs in sorted(obj.delta.items()) for r in sorted(rs)]
    qm = QMap(obj.states, obj.start, [(q, r) for q, r, _ in edges_raw])
    nodes = [_node(qm, s, start=s == obj.start, accepting=s in obj.accepting) for s in obj.states]
    edges = [_edge(qm, q, r, a, epsilon=a == EPS) for q, r, a in edges_raw]
    table = {qm(q): {a: qm(rs) for a, rs in row.items()} for q, row in obj.transition_table().items()}
    return Graph(_sorted_nodes(nodes), edges, qm, {"transition_table": table, "alphabet": sorted(obj.alphabet)})


_QMS: dict[str, QMap] = {}          # q numbering of each model's default graph (traces use it)


def graph_payload(model: str, view: str | None = None) -> dict:
    if model not in machines():
        raise KeyError(model)
    obj, info = machines()[model], MODEL_INFO[model]
    base: dict[str, Any] = {"model": model, "kind": info["kind"], "info": info}
    if model in ("dfa", "nfa", "enfa"):
        views = VIEWS.get(model, [])
        view = view or (views[0] if views else model)
        if view != model and view not in views:
            raise AutomatonError(f"view must be one of {views}")
        shown = obj
        if view == "dfa" and model != "dfa":
            shown = obj.to_dfa()
        elif view == "nfa" and model == "enfa":
            shown = obj.to_nfa()
        g = _finite_graph(shown, view)
        if isinstance(shown, DFA) and model != "dfa":
            for n in g.nodes:                                           # derived DFA: ∅ is the dead state
                n["dead"] = n["name"] == "∅"
        extra = dict(g.extra)
        if model == "enfa":
            extra["closure_steps"] = [g.qm(sorted(s)) for s in obj.eps_closure_steps({obj.start})] if view == "enfa" else []
        if views:
            extra["views"] = views
            extra["view_note"] = VIEW_NOTES.get((model, view), "")
        if view == (views[0] if views else model):
            _QMS[model] = g.qm
        return {**base, "view": view, "nodes": g.nodes, "edges": g.edges, "n_states": len(g.nodes), **extra}
    if model == "pa":
        edges_raw = [(q, r, a, p) for (q, a), dist in sorted(obj.trans.items()) for r, p in sorted(dist.items())]
        qm = QMap(obj.states, obj.start, [(q, r) for q, r, _, _ in edges_raw])
        nodes = _sorted_nodes([_node(qm, s, start=s == obj.start, accepting=s in obj.accepting) for s in obj.states])
        _QMS[model] = qm
        return {**base, "nodes": nodes, "edges": [_edge(qm, q, r, a, prob=p) for q, r, a, p in edges_raw], "n_states": len(nodes),
                "matrix_note": "P(word) = e_{q0}^T M_a1 ... M_an 1_F"}
    if model == "lts":
        qm = QMap(obj.states, obj.initial, [(t.source, t.target) for t in obj.transitions])
        nodes = _sorted_nodes([_node(qm, s, start=s == obj.initial, accepting=s in obj.accepting, rejecting=s in obj.rejecting) for s in obj.states])
        edges = [_edge(qm, t.source, t.target, t.label, category=t.category) for t in obj.transitions]
        _QMS[model] = qm
        return {**base, "nodes": nodes, "edges": edges, "n_states": len(nodes), "reachable": qm(sorted(obj.reachable())), "deadlocks": qm(sorted(obj.deadlocks()))}
    if model == "mealy":
        raw = [(q, obj.delta[(q, a)], f"{a}/{obj.lam[(q, a)]}") for q in sorted(obj.states) for a in sorted(obj.inputs)]
        qm = QMap(obj.states, obj.start, [(q, r) for q, r, _ in raw])
        nodes = _sorted_nodes([_node(qm, s, start=s == obj.start) for s in obj.states])
        _QMS[model] = qm
        return {**base, "nodes": nodes, "edges": [_edge(qm, q, r, lab) for q, r, lab in raw], "n_states": len(nodes),
                "witness": [[qm(w[0]), *w[1:]] for w in obj.same_state_different_outputs()[:4]]}
    if model == "moore":
        raw = [(q, obj.delta[(q, a)], a) for q in sorted(obj.states) for a in sorted(obj.inputs)]
        qm = QMap(obj.states, obj.start, [(q, r) for q, r, _ in raw])
        nodes = _sorted_nodes([_node(qm, s, start=s == obj.start, output=obj.out[s]) for s in obj.states])
        _QMS[model] = qm
        return {**base, "nodes": nodes, "edges": [_edge(qm, q, r, a) for q, r, a in raw], "n_states": len(nodes),
                "note": "Mealy→Moore expansion: states are (q, last output) pairs"}
    if model in ("pda", "pda_typed"):
        qm = QMap(obj.states, obj.start, [(t.q, t.q2) for t in obj.transitions])
        nodes = _sorted_nodes([_node(qm, s, start=s == obj.start, accepting=s in obj.accepting) for s in obj.states])
        edges = [_edge(qm, t.q, t.q2, f"{t.a}, {t.X}→{''.join(t.push) or 'ε'}", op=t.op) for t in obj.transitions]
        _QMS[model] = qm
        return {**base, "nodes": nodes, "edges": edges, "n_states": len(nodes), "stack_bottom": obj.bottom}
    raw = [(q, v[0], f"{a}/{v[1]},{v[2]}") for (q, a), v in sorted(obj.delta.items())]
    qm = QMap(obj.states, obj.start, [(q, r) for q, r, _ in raw])
    nodes = _sorted_nodes([_node(qm, s, start=s == obj.start, accepting=s == obj.accept, rejecting=s == obj.reject) for s in obj.states])
    _QMS[model] = qm
    return {**base, "nodes": nodes, "edges": [_edge(qm, q, r, lab) for q, r, lab in raw], "n_states": len(nodes)}


def _qm_for(model: str) -> QMap:
    if model not in _QMS:
        graph_payload(model)
    return _QMS[model]


# ---------------------------------------------------------------------------------------------- traces
def _steps(t, qm: QMap) -> list[dict]:
    out = []
    for s in t.steps:
        j = s.to_json()
        j["state"], j["next_state"] = qm(j["state"]), qm(j["next_state"])
        if "before_closure" in j:
            j["before_closure"] = qm(j["before_closure"])
        out.append(j)
    return out


def _dead_states(obj: DFA) -> set[str]:
    return obj.states - obj.can_reach(obj.accepting)


def trace_payload(model: str, word: list[str], seed: int = 0) -> dict:
    if model not in machines():
        raise KeyError(model)
    obj, info = machines()[model], MODEL_INFO[model]
    qm = _qm_for(model)
    out: dict[str, Any] = {"model": model, "kind": info["kind"], "word": list(word)}
    if model == "dfa":
        t = obj.run(word)
        steps = _steps(t, qm)
        final = qm(t.steps[-1].next_state if t.steps else obj.start)
        out |= {"steps": steps, "accepted": t.accepted, "final_state": final}
        if not t.accepted:
            end = t.steps[-1].next_state if t.steps else obj.start
            out["reason"] = (f"ended in {final}, a dead (trap) state: no accepting state is reachable from it" if end in _dead_states(obj)
                             else f"ended in {final}, which is not an accepting state")
        return out
    if model in ("nfa", "enfa"):
        t = obj.run(word)
        init = obj.eps_closure({obj.start})
        out |= {"steps": _steps(t, qm), "accepted": t.accepted, "initial_active": qm(init), "note": t.note}
        last = t.steps[-1].next_state if t.steps else init
        out["final_active"] = qm(last)
        if not t.accepted:
            out["reason"] = "every branch died: the active-state set is empty (∅)" if not last else f"the active set {{{', '.join(qm(last))}}} contains no accepting state"
        return out
    if model == "pa":
        t = obj.sample_run(word, np.random.default_rng(seed))
        out |= {"steps": _steps(t, qm), "sample_ended_accepting": t.accepted, "sample_blocked": bool(t.steps and t.steps[-1].info.get("blocked")),
                "exact_acceptance_probability": obj.acceptance_probability(word),
                "monte_carlo": obj.monte_carlo_acceptance(word, 2000, np.random.default_rng(seed + 1)),
                "note": "One sampled run is shown. The verdict of a probabilistic automaton is the probability, not accepted/rejected."}
        out["monte_carlo"]["ci_lo"] = max(0.0, round(out["monte_carlo"]["ci_lo"], 12))
        return out
    if model == "lts":
        end = obj.run_labels(word)
        cur, steps = obj.initial, []
        blocked = None
        for i, a in enumerate(word):
            nxt = [t for t in obj.successors(cur) if t.label == a]
            if not nxt:
                steps.append({"index": i, "state": qm(cur), "symbol": a, "next_state": None, "blocked": True})
                blocked = {"state": qm(cur), "label": a}
                break
            steps.append({"index": i, "state": qm(cur), "symbol": a, "next_state": qm(nxt[0].target)}); cur = nxt[0].target
        out |= {"steps": steps, "accepted": bool(end & obj.accepting), "end_states": qm(sorted(end)), "blocked": blocked, "deadlocks": qm(sorted(obj.deadlocks()))}
        if not out["accepted"]:
            out["reason"] = (f"blocked: no '{blocked['label']}' action is enabled in {blocked['state']}" if blocked
                             else "the run ended in a state that is not accepting" if end else "no run exists for this word")
        return out
    if model in ("mealy", "moore"):
        outs, t = obj.run(word)
        out |= {"steps": _steps(t, qm), "outputs": outs, "note": t.note}
        return out
    if model in ("pda", "pda_typed"):
        t = obj.run(word)
        out |= {"steps": _steps(t, qm), "accepted": t.accepted, "note": t.note, "halted": t.halted}
        if not t.accepted:
            out["reason"] = t.reason
        return out
    # Turing machines
    kw = {"max_steps": STEP_LIMIT[model]} if model in STEP_LIMIT else {}
    r = obj.run("".join(word), **kw)
    cfgs = [c.to_json() for c in r.trace]
    for c in cfgs:
        c["state"] = qm(c["state"])
    steps = []
    for i in range(len(r.trace) - 1):
        a, b = r.trace[i], r.trace[i + 1]
        steps.append({"index": i, "state": qm(a.state), "symbol": a.tape.get(a.head, a.blank), "next_state": qm(b.state),
                      "write": b.tape.get(a.head, a.blank), "move": {-1: "L", 0: "S", 1: "R"}.get(b.head - a.head, "?")})
    unknown = r.status in ("step_limit", "tape_bound")
    out |= {"steps": steps, "trace": cfgs, "n_steps": r.steps, "status": r.status, "halted": r.halted, "output": r.final.contents(), "unknown": unknown,
            "accepted": r.accepted if not unknown else None}
    if unknown:
        out["reason"] = f"simulator bound reached ({r.status}): the machine did not halt — the answer is unknown, not 'reject'"
    elif not r.accepted:
        out["reason"] = f"halted in the rejecting state ({r.status})"
    return out


def compare_rows() -> list[dict]:
    return [{"id": k, **{f: MODEL_INFO[k][f] for f in ("name", "definition", "accepts", "memory", "nondeterminism", "probability", "agent_fit", "limits")}} for k in COMPARE_KEYS]
