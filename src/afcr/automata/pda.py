"""Nondeterministic pushdown automaton (stack = unbounded memory) for nested / structured tool invocation.

A transition  (q, a, X, q', γ)  reads input ``a`` (or ε), pops ``X`` from the stack (or does not inspect the stack when
X = ε), moves to q' and pushes the string γ (leftmost symbol ends up on top).  The stack operation is classified as
push / pop / noop by its net effect.

A finite-state machine cannot recognise arbitrarily deep nesting (pumping lemma); the PDA can.  The search below is
bounded (``max_stack``, ``max_steps``) purely for termination of the *simulator*; the model itself is unbounded.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

from .base import EPS, AutomatonError, State, Symbol, Trace, TraceStep, check_word


@dataclass(frozen=True)
class PDATransition:
    q: State
    a: Symbol          # input symbol or EPS
    X: Symbol          # popped stack symbol or EPS (= do not look at the stack)
    q2: State
    push: tuple[Symbol, ...]

    @property
    def op(self) -> str:
        net = len(self.push) - (0 if self.X == EPS else 1)
        return "push" if net > 0 else "pop" if net < 0 else "noop"


class PDA:
    kind = "PDA"

    def __init__(self, states: Iterable[State], inputs: Iterable[Symbol], stack_alphabet: Iterable[Symbol],
                 transitions: Iterable[PDATransition], start: State, bottom: Symbol, accepting: Iterable[State],
                 accept_by: str = "both"):
        self.states = set(states); self.inputs = frozenset(inputs); self.gamma = frozenset(stack_alphabet)
        self.transitions = list(transitions); self.start = start; self.bottom = bottom
        self.accepting = set(accepting); self.accept_by = accept_by
        if accept_by not in ("final", "empty", "both"):
            raise AutomatonError("accept_by must be 'final', 'empty' or 'both'")
        if start not in self.states or bottom not in self.gamma or not self.accepting <= self.states:
            raise AutomatonError("start/bottom/accepting must belong to Q / Γ")
        for t in self.transitions:
            if t.q not in self.states or t.q2 not in self.states:
                raise AutomatonError(f"transition {t} refers to an unknown state")
            if t.a != EPS and t.a not in self.inputs:
                raise AutomatonError(f"transition {t} reads unknown input {t.a!r}")
            if (t.X != EPS and t.X not in self.gamma) or not set(t.push) <= self.gamma:
                raise AutomatonError(f"transition {t} uses stack symbols outside Γ")
        self._by_state: dict[State, list[PDATransition]] = {}
        for t in self.transitions:
            self._by_state.setdefault(t.q, []).append(t)

    def _accepting_config(self, q: State, pos: int, stack: tuple, n: int) -> bool:
        if pos != n:
            return False
        fin = q in self.accepting
        emp = len(stack) == 0
        return {"final": fin, "empty": emp, "both": fin and emp}[self.accept_by]

    def run(self, word: Iterable[Symbol], *, max_stack: int = 64, max_steps: int = 20000) -> Trace:
        """Breadth-first search over configurations; returns the shortest accepting computation if one exists."""
        w = check_word(word, self.inputs)
        n = len(w)
        init = (self.start, 0, (self.bottom,))
        parent: dict[tuple, tuple[tuple, PDATransition] | None] = {init: None}
        depth: dict[tuple, int] = {init: 0}
        dq = deque([init]); expanded = 0; found = None
        best = init                                       # most input consumed (ties: fewest steps): explains a rejection
        while dq:
            cfg = dq.popleft()
            q, pos, stack = cfg
            if self._accepting_config(q, pos, stack, n):
                found = cfg; break
            if pos > best[1]:
                best = cfg
            expanded += 1
            if expanded > max_steps:
                break
            for t in self._by_state.get(q, []):
                if t.a != EPS and (pos >= n or w[pos] != t.a):
                    continue
                if t.X != EPS and (not stack or stack[0] != t.X):
                    continue
                rest = stack[1:] if t.X != EPS else stack
                nstack = tuple(t.push) + rest
                if len(nstack) > max_stack:
                    continue
                ncfg = (t.q2, pos + (0 if t.a == EPS else 1), nstack)
                if ncfg not in parent:
                    parent[ncfg] = (cfg, t)
                    depth[ncfg] = depth[cfg] + 1
                    dq.append(ncfg)
        exhausted = expanded > max_steps and found is None
        shown = found if found is not None else best     # a rejected run still shows how far the machine got
        steps: list[TraceStep] = []
        path = []
        cur = shown
        while parent[cur] is not None:
            prev, t = parent[cur]
            path.append((prev, t, cur)); cur = prev
        for i, (prev, t, cur) in enumerate(reversed(path)):
            steps.append(TraceStep(i, prev[0], t.a, cur[0],
                                   info={"stack_before": prev[2], "stack_after": cur[2], "op": t.op, "pos": cur[1]}))
        if found is not None:
            note, reason = "accepted", ""
        elif exhausted:
            note, reason = "search budget exhausted (not a rejection proof)", "search budget exhausted: the simulator cannot decide this word"
        else:
            note = "rejected: no accepting computation"
            reason = self._explain(shown, w)
        return Trace(self.kind, w, steps, accepted=found is not None, halted=not exhausted, note=note, reason=reason)

    def _explain(self, cfg: tuple, w: tuple) -> str:
        q, pos, stack = cfg
        top = stack[0] if stack else "(empty)"
        shown_stack = ",".join(stack) or "empty"
        if pos < len(w):
            return f"stuck before reading '{w[pos]}' (input position {pos + 1}): no transition from {q} with stack top {top} (stack: {shown_stack})"
        if stack != (self.bottom,) and stack:
            return f"input consumed but the stack still holds {shown_stack}: something was opened and never closed"
        return f"input consumed but {q} is not accepting (stack: {shown_stack})"

    def accepts(self, word: Iterable[Symbol], **kw) -> bool:
        return self.run(word, **kw).accepted


def nested_calls_pda() -> PDA:
    """Balanced call/return nesting of unbounded depth:  L = { w ∈ {call, ret}* : properly nested }."""
    T = [
        PDATransition("q", "call", EPS, "q", ("C",)),          # push (stack-insensitive)
        PDATransition("q", "ret", "C", "q", ()),               # pop
        PDATransition("q", EPS, "Z", "acc", ()),               # bottom reached -> accept with empty stack
    ]
    return PDA({"q", "acc"}, {"call", "ret"}, {"C", "Z"}, T, "q", "Z", {"acc"}, accept_by="both")


def typed_nested_tools_pda() -> PDA:
    """Structured tool invocation: a tool opened as search(...) must be closed by end_search, calc by end_calc."""
    T = [
        PDATransition("q", "open_search", EPS, "q", ("S",)),
        PDATransition("q", "open_calc", EPS, "q", ("K",)),
        PDATransition("q", "end_search", "S", "q", ()),
        PDATransition("q", "end_calc", "K", "q", ()),
        PDATransition("q", EPS, "Z", "acc", ()),
    ]
    return PDA({"q", "acc"}, {"open_search", "open_calc", "end_search", "end_calc"}, {"S", "K", "Z"}, T, "q", "Z", {"acc"})


def depth_bounded_dfa(max_depth: int):
    """A DFA that tracks nesting depth only up to ``max_depth`` (deeper words go to the sink): shows the finite-memory limit."""
    from .dfa import DFA
    states = [f"d{i}" for i in range(max_depth + 1)] + ["bad"]
    delta = {}
    for i in range(max_depth + 1):
        delta[(f"d{i}", "call")] = f"d{i+1}" if i < max_depth else "bad"
        delta[(f"d{i}", "ret")] = f"d{i-1}" if i > 0 else "bad"
    delta[("bad", "call")] = "bad"; delta[("bad", "ret")] = "bad"
    return DFA(states, {"call", "ret"}, delta, "d0", {"d0"})
