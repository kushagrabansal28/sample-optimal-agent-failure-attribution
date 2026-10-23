"""Nondeterministic finite automata: NFA and ε-NFA.

Nondeterminism here is a *formal* device (acceptance iff SOME path accepts).  It is NOT the same thing as
the randomness of an LLM's sampling; for probabilistic semantics see ``pa.ProbabilisticAutomaton``.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping

import networkx as nx

from .base import EPS, AutomatonError, State, Symbol, Trace, TraceStep, check_word
from .dfa import DFA


class ENFA:
    """ε-NFA  (Q, Σ, δ, q0, F)  with  δ: Q × (Σ ∪ {ε}) → 2^Q.  A plain NFA is an ENFA with no ε-moves."""

    kind = "ε-NFA"

    def __init__(self, states: Iterable[State], alphabet: Iterable[Symbol],
                 delta: Mapping[tuple[State, Symbol], Iterable[State]], start: State, accepting: Iterable[State]):
        self.states = set(states)
        self.alphabet = frozenset(alphabet)
        if EPS in self.alphabet:
            raise AutomatonError("ε must not be part of the input alphabet")
        self.delta = {k: frozenset(v) for k, v in delta.items()}
        self.start = start
        self.accepting = set(accepting)
        if start not in self.states or not self.accepting <= self.states:
            raise AutomatonError("start/accepting states must belong to Q")
        for (q, a), rs in self.delta.items():
            if q not in self.states or not set(rs) <= self.states:
                raise AutomatonError(f"transition from {q!r} on {a!r} refers to unknown states")
            if a != EPS and a not in self.alphabet:
                raise AutomatonError(f"transition on unknown symbol {a!r}")

    # ---- ε-closure ---------------------------------------------------------------------------
    def eps_closure(self, S: Iterable[State]) -> frozenset[State]:
        return frozenset(self.eps_closure_steps(S)[-1])

    def eps_closure_steps(self, S: Iterable[State]) -> list[frozenset[State]]:
        """The growing sets while computing the closure (for visualisation): [S, S∪{1-hop}, ..., closure]."""
        cur = set(S)
        out = [frozenset(cur)]
        while True:
            new = set(cur)
            for q in cur:
                new |= self.delta.get((q, EPS), frozenset())
            if new == cur:
                return out
            cur = new
            out.append(frozenset(cur))

    # ---- execution -------------------------------------------------------------------------------
    def step_set(self, S: frozenset[State], a: Symbol) -> frozenset[State]:
        moved: set[State] = set()
        for q in S:
            moved |= self.delta.get((q, a), frozenset())
        return self.eps_closure(moved)

    def run(self, word: Iterable[Symbol]) -> Trace:
        w = check_word(word, self.alphabet)
        steps: list[TraceStep] = []
        cur = self.eps_closure({self.start})
        for i, a in enumerate(w):
            moved = set()
            for q in cur:
                moved |= self.delta.get((q, a), frozenset())
            nxt = self.eps_closure(moved)
            steps.append(TraceStep(i, cur, a, nxt, info={"before_closure": frozenset(moved)}))
            cur = nxt
        return Trace(self.kind, w, steps, accepted=bool(cur & self.accepting),
                     note="accepted iff the active-state set contains an accepting state")

    def accepts(self, word: Iterable[Symbol]) -> bool:
        return self.run(word).accepted

    # ---- conversions ----------------------------------------------------------------------------------
    def to_nfa(self) -> "NFA":
        """Standard ε-removal: δ'(q,a) = ε-closure( δ( ε-closure(q), a ) ); F' adds states whose closure meets F."""
        delta: dict[tuple[State, Symbol], set[State]] = {}
        for q in self.states:
            cl = self.eps_closure({q})
            for a in self.alphabet:
                tgt: set[State] = set()
                for p in cl:
                    tgt |= self.delta.get((p, a), frozenset())
                tgt = set(self.eps_closure(tgt))
                if tgt:
                    delta[(q, a)] = tgt
        acc = {q for q in self.states if self.eps_closure({q}) & self.accepting}
        return NFA(self.states, self.alphabet, delta, self.start, acc)

    def to_dfa(self) -> DFA:
        """Subset construction on ε-closures; the empty set is the (explicit) dead state."""
        start = self.eps_closure({self.start})
        names: dict[frozenset[State], str] = {}

        def nm(S: frozenset[State]) -> str:
            if S not in names:
                names[S] = "{" + ",".join(sorted(map(str, S))) + "}" if S else "∅"
            return names[S]

        todo = deque([start])
        seen = {start}
        delta: dict[tuple[str, Symbol], str] = {}
        while todo:
            S = todo.popleft()
            for a in sorted(self.alphabet):
                T = self.step_set(S, a)
                delta[(nm(S), a)] = nm(T)
                if T not in seen:
                    seen.add(T)
                    todo.append(T)
        acc = {nm(S) for S in seen if S & self.accepting}
        return DFA({nm(S) for S in seen}, self.alphabet, delta, nm(start), acc)

    def to_networkx(self) -> nx.MultiDiGraph:
        g = nx.MultiDiGraph()
        for q in self.states:
            g.add_node(q, accepting=q in self.accepting, start=q == self.start)
        for (q, a), rs in self.delta.items():
            for r in rs:
                g.add_edge(q, r, label=a)
        return g

    def transition_table(self) -> dict[State, dict[Symbol, list[State]]]:
        syms = sorted(self.alphabet) + ([EPS] if any(a == EPS for (_, a) in self.delta) else [])
        return {q: {a: sorted(self.delta.get((q, a), frozenset())) for a in syms} for q in sorted(self.states)}

    def has_epsilon(self) -> bool:
        return any(a == EPS for (_, a) in self.delta)

    def is_nondeterministic(self) -> bool:
        return self.has_epsilon() or any(len(rs) > 1 for rs in self.delta.values())


class NFA(ENFA):
    """NFA: an ENFA without ε-transitions.  Execution tracks the active-state set; subset construction -> DFA."""

    kind = "NFA"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        if self.has_epsilon():
            raise AutomatonError("an NFA must not contain ε-transitions; use ENFA")

    def to_nfa(self) -> "NFA":
        return self
