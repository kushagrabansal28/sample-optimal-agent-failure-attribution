"""Deterministic finite automaton  M = (Q, Σ, δ, q0, F)  with a *total* transition function."""
from __future__ import annotations

import itertools
from collections.abc import Iterable, Mapping

import networkx as nx

from .base import AutomatonError, State, Symbol, Trace, TraceStep, check_word

SINK = "⊥sink"


class DFA:
    """DFA with an explicit total δ: Q × Σ → Q.

    Parameters
    ----------
    states, alphabet, delta, start, accepting :
        the usual 5-tuple. ``delta`` maps ``(q, a)`` to ``q'``.
    complete_with_sink :
        if True, every missing ``(q, a)`` is routed to an explicit non-accepting sink state
        (named ``⊥sink``); otherwise a missing transition raises :class:`AutomatonError`.
        The sink is a *completion artefact*, not a logical state of the modelled system
        (see :meth:`logical_states`).
    """

    def __init__(self, states: Iterable[State], alphabet: Iterable[Symbol],
                 delta: Mapping[tuple[State, Symbol], State], start: State,
                 accepting: Iterable[State], *, complete_with_sink: bool = False,
                 labels: Mapping[State, str] | None = None):
        self.states = set(states)
        self.alphabet = frozenset(alphabet)
        self.delta = dict(delta)
        self.start = start
        self.accepting = set(accepting)
        self.labels = dict(labels or {})
        self.sink_added = False
        self._check_structure()
        if complete_with_sink:
            self._complete()
        self.validate_total()

    # ---- validation -----------------------------------------------------------------------
    def _check_structure(self) -> None:
        if self.start not in self.states:
            raise AutomatonError(f"start state {self.start!r} not in Q")
        if not self.accepting <= self.states:
            raise AutomatonError(f"accepting states not in Q: {sorted(self.accepting - self.states)}")
        for (q, a), r in self.delta.items():
            if q not in self.states or r not in self.states:
                raise AutomatonError(f"transition ({q!r},{a!r})->{r!r} refers to an unknown state")
            if a not in self.alphabet:
                raise AutomatonError(f"transition on unknown symbol {a!r}")

    def _complete(self) -> None:
        missing = [(q, a) for q in self.states for a in self.alphabet if (q, a) not in self.delta]
        if not missing:
            return
        self.states.add(SINK)
        self.sink_added = True
        for q in list(self.states):
            for a in self.alphabet:
                self.delta.setdefault((q, a), SINK)

    def missing_transitions(self) -> list[tuple[State, Symbol]]:
        return sorted((q, a) for q in self.states for a in self.alphabet if (q, a) not in self.delta)

    def validate_total(self) -> None:
        miss = self.missing_transitions()
        if miss:
            raise AutomatonError(f"δ is not total; {len(miss)} missing transitions, e.g. {miss[:3]}")

    def is_total(self) -> bool:
        return not self.missing_transitions()

    def is_deterministic(self) -> bool:
        # a dict keyed by (q, a) is deterministic by construction; kept as an explicit, testable property
        return len(self.delta) == len(set(self.delta))

    def logical_states(self) -> set[State]:
        return self.states - ({SINK} if self.sink_added else set())

    # ---- execution --------------------------------------------------------------------------
    def step(self, q: State, a: Symbol) -> State:
        if a not in self.alphabet:
            raise AutomatonError(f"symbol {a!r} not in alphabet")
        return self.delta[(q, a)]

    def run(self, word: Iterable[Symbol]) -> Trace:
        w = check_word(word, self.alphabet)
        q = self.start
        steps: list[TraceStep] = []
        for i, a in enumerate(w):
            nq = self.step(q, a)
            steps.append(TraceStep(i, q, a, nq))
            q = nq
        return Trace("DFA", w, steps, accepted=q in self.accepting)

    def accepts(self, word: Iterable[Symbol]) -> bool:
        return self.run(word).accepted

    def final_state(self, word: Iterable[Symbol]) -> State:
        t = self.run(word)
        return t.steps[-1].next_state if t.steps else self.start

    # ---- analysis ---------------------------------------------------------------------------
    def to_networkx(self) -> nx.MultiDiGraph:
        g = nx.MultiDiGraph()
        for q in self.states:
            g.add_node(q, accepting=q in self.accepting, start=q == self.start)
        for (q, a), r in self.delta.items():
            g.add_edge(q, r, label=a)
        return g

    def reachable(self) -> set[State]:
        seen, stack = {self.start}, [self.start]
        while stack:
            q = stack.pop()
            for a in self.alphabet:
                r = self.delta[(q, a)]
                if r not in seen:
                    seen.add(r)
                    stack.append(r)
        return seen

    def can_reach(self, targets: Iterable[State]) -> set[State]:
        """States from which some target is reachable (reverse reachability)."""
        rev: dict[State, set[State]] = {q: set() for q in self.states}
        for (q, _a), r in self.delta.items():
            rev[r].add(q)
        seen = set(targets)
        stack = list(seen)
        while stack:
            r = stack.pop()
            for q in rev[r]:
                if q not in seen:
                    seen.add(q)
                    stack.append(q)
        return seen

    def transition_table(self) -> dict[State, dict[Symbol, State]]:
        return {q: {a: self.delta[(q, a)] for a in sorted(self.alphabet)} for q in sorted(self.states)}

    def words_up_to(self, max_len: int) -> Iterable[tuple[Symbol, ...]]:
        syms = sorted(self.alphabet)
        for n in range(max_len + 1):
            yield from itertools.product(syms, repeat=n)

    def equivalent_up_to(self, other, max_len: int) -> bool:
        """Bounded equivalence: same acceptance on every word of length <= max_len (a test aid, not a proof)."""
        if self.alphabet != other.alphabet:
            return False
        return all(self.accepts(w) == other.accepts(w) for w in self.words_up_to(max_len))
