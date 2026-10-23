"""Labelled transition systems  s --a--> s'  for agent execution (reasoning, tool use, observation, update, ...)."""
from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass

import networkx as nx

from .base import AutomatonError, State, Symbol

# canonical action-label categories (documented in docs/automata_glossary.md)
LABEL_CATEGORIES = ("reasoning", "tool_use", "observation", "state_update", "validation", "recovery", "success", "failure")


@dataclass(frozen=True)
class Transition:
    source: State
    label: Symbol
    target: State
    prob: float | None = None
    category: str | None = None


class LTS:
    def __init__(self, states: Iterable[State], transitions: Iterable[Transition], initial: State,
                 accepting: Iterable[State] = (), rejecting: Iterable[State] = ()):
        self.states = set(states)
        self.transitions = list(transitions)
        self.initial = initial
        self.accepting = set(accepting)
        self.rejecting = set(rejecting)
        if initial not in self.states:
            raise AutomatonError("initial state not in S")
        for t in self.transitions:
            if t.source not in self.states or t.target not in self.states:
                raise AutomatonError(f"transition {t} refers to unknown state")
            if t.category is not None and t.category not in LABEL_CATEGORIES:
                raise AutomatonError(f"unknown label category {t.category!r}")
        self._out: dict[State, list[Transition]] = defaultdict(list)
        for t in self.transitions:
            self._out[t.source].append(t)

    def successors(self, s: State) -> list[Transition]:
        return list(self._out.get(s, []))

    def reachable(self, frm: State | None = None) -> set[State]:
        start = self.initial if frm is None else frm
        seen, dq = {start}, deque([start])
        while dq:
            s = dq.popleft()
            for t in self._out.get(s, []):
                if t.target not in seen:
                    seen.add(t.target)
                    dq.append(t.target)
        return seen

    def can_reach(self, targets: Iterable[State]) -> set[State]:
        rev: dict[State, set[State]] = defaultdict(set)
        for t in self.transitions:
            rev[t.target].add(t.source)
        seen = set(targets)
        dq = deque(seen)
        while dq:
            s = dq.popleft()
            for p in rev[s]:
                if p not in seen:
                    seen.add(p)
                    dq.append(p)
        return seen

    def deadlocks(self) -> set[State]:
        """Reachable non-terminal states with no outgoing transition."""
        terminal = self.accepting | self.rejecting
        return {s for s in self.reachable() if s not in terminal and not self._out.get(s)}

    def accepting_reachable(self) -> bool:
        return bool(self.reachable() & self.accepting)

    def rejecting_reachable(self) -> bool:
        return bool(self.reachable() & self.rejecting)

    def run_labels(self, labels: Iterable[Symbol]) -> set[State]:
        cur = {self.initial}
        for a in labels:
            cur = {t.target for s in cur for t in self._out.get(s, []) if t.label == a}
            if not cur:
                return set()
        return cur

    def traces(self, max_len: int) -> list[tuple[Symbol, ...]]:
        out: list[tuple[Symbol, ...]] = []

        def rec(s: State, pref: tuple[Symbol, ...]):
            out.append(pref)
            if len(pref) == max_len:
                return
            for t in self._out.get(s, []):
                rec(t.target, pref + (t.label,))
        rec(self.initial, ())
        return out

    def counterfactual_branch(self, path_states: list[State], t: int, label: Symbol) -> list[Transition]:
        """Alternative transition out of path_states[t] with a different label (a *branch*, for visualisation)."""
        if not 0 <= t < len(path_states):
            raise AutomatonError("branch index out of range")
        return [x for x in self._out.get(path_states[t], []) if x.label == label]

    def to_networkx(self) -> nx.MultiDiGraph:
        g = nx.MultiDiGraph()
        for s in self.states:
            g.add_node(s, accepting=s in self.accepting, rejecting=s in self.rejecting, initial=s == self.initial)
        for t in self.transitions:
            g.add_edge(t.source, t.target, label=t.label, prob=t.prob, category=t.category)
        return g
