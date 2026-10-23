"""Probabilistic finite automaton (Rabin-style): each (q, a) carries a probability distribution over successors.

Semantics (formally distinct from NFA nondeterminism)
-----------------------------------------------------
* NFA : a word is accepted iff SOME path accepts; no probabilities exist.
* PFA : a word has an acceptance *probability*  P(w) = e_{q0}^T M_{a1} ... M_{an} 1_F.
A missing (q, a) pair means the symbol is *not enabled* in q: the run is blocked (it can never accept).
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

import networkx as nx
import numpy as np

from .base import AutomatonError, State, Symbol, Trace, TraceStep, check_word


def wilson_interval(successes: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Wilson score interval (a *fixed-n* interval; not for adaptive stopping)."""
    from scipy.stats import norm
    if n == 0:
        return 0.0, 1.0
    z = float(norm.ppf(0.5 + level / 2))
    p = successes / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


class ProbabilisticAutomaton:
    def __init__(self, states: Iterable[State], alphabet: Iterable[Symbol],
                 trans: Mapping[tuple[State, Symbol], Mapping[State, float]], start: State,
                 accepting: Iterable[State], *, tol: float = 1e-9):
        self.states = sorted(set(states))
        self.index = {q: i for i, q in enumerate(self.states)}
        self.alphabet = frozenset(alphabet)
        self.start = start
        self.accepting = set(accepting)
        self.tol = tol
        self.trans: dict[tuple[State, Symbol], dict[State, float]] = {}
        if start not in self.index:
            raise AutomatonError("start state not in Q")
        for (q, a), dist in trans.items():
            if q not in self.index or a not in self.alphabet:
                raise AutomatonError(f"unknown state/symbol in transition ({q!r}, {a!r})")
            total = 0.0
            for r, p in dist.items():
                if r not in self.index:
                    raise AutomatonError(f"unknown successor {r!r}")
                if p < 0 or p > 1 + tol or math.isnan(p):
                    raise AutomatonError(f"invalid probability {p} for ({q!r},{a!r})->{r!r}")
                total += p
            if abs(total - 1.0) > tol:
                raise AutomatonError(f"distribution for ({q!r},{a!r}) sums to {total}, expected 1")
            self.trans[(q, a)] = {r: float(p) for r, p in dist.items() if p > 0}
        if not self.accepting <= set(self.states):
            raise AutomatonError("accepting states not in Q")

    # ---- exact semantics ------------------------------------------------------------------
    def matrix(self, a: Symbol) -> np.ndarray:
        n = len(self.states)
        M = np.zeros((n, n))
        for q in self.states:
            for r, p in self.trans.get((q, a), {}).items():
                M[self.index[q], self.index[r]] = p
        return M

    def acceptance_probability(self, word: Iterable[Symbol]) -> float:
        w = check_word(word, self.alphabet)
        v = np.zeros(len(self.states))
        v[self.index[self.start]] = 1.0
        for a in w:
            v = v @ self.matrix(a)
        return float(sum(v[self.index[q]] for q in self.accepting))

    def blocked_mass(self, word: Iterable[Symbol]) -> float:
        w = check_word(word, self.alphabet)
        v = np.zeros(len(self.states)); v[self.index[self.start]] = 1.0
        for a in w:
            v = v @ self.matrix(a)
        return float(1.0 - v.sum())

    # ---- sampling ---------------------------------------------------------------------------
    def sample_run(self, word: Iterable[Symbol], rng: np.random.Generator) -> Trace:
        w = check_word(word, self.alphabet)
        q = self.start
        steps: list[TraceStep] = []
        for i, a in enumerate(w):
            dist = self.trans.get((q, a))
            if not dist:
                steps.append(TraceStep(i, q, a, None, info={"blocked": True}))
                return Trace("PFA", w, steps, accepted=False, halted=True, note="run blocked: symbol not enabled")
            succ, probs = zip(*dist.items())
            nq = succ[int(rng.choice(len(succ), p=np.array(probs) / sum(probs)))]
            steps.append(TraceStep(i, q, a, nq, info={"p": dist[nq]}))
            q = nq
        return Trace("PFA", w, steps, accepted=q in self.accepting)

    def monte_carlo_acceptance(self, word: Iterable[Symbol], n: int, rng: np.random.Generator,
                               level: float = 0.95) -> dict:
        w = tuple(word)
        k = sum(self.sample_run(w, rng).accepted for _ in range(n))
        lo, hi = wilson_interval(k, n, level)
        return {"n": n, "successes": k, "p_hat": k / n, "ci_lo": lo, "ci_hi": hi, "level": level}

    def to_networkx(self) -> nx.MultiDiGraph:
        g = nx.MultiDiGraph()
        for q in self.states:
            g.add_node(q, accepting=q in self.accepting, start=q == self.start)
        for (q, a), dist in self.trans.items():
            for r, p in dist.items():
                g.add_edge(q, r, label=a, p=p)
        return g
