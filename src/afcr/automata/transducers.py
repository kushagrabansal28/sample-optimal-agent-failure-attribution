"""Mealy (output on transitions) and Moore (output on states) machines, with conversions.

Convention: a Moore machine emits the output of its current state *before* reading input, so for an input of
length n it produces n+1 outputs (the first is the start-state output).  The Mealy machine produces n outputs.
Mealy -> Moore therefore needs (i) a designated initial output and (ii) state expansion:
|Q_moore| <= |Q| * |Γ| + 1 (states are (q, last_output) pairs reachable from the start).
"""
from __future__ import annotations

import itertools
from collections.abc import Iterable, Mapping

from .base import AutomatonError, State, Symbol, Trace, TraceStep, check_word


class Mealy:
    kind = "Mealy"

    def __init__(self, states: Iterable[State], inputs: Iterable[Symbol], outputs: Iterable[Symbol],
                 delta: Mapping[tuple[State, Symbol], State], lam: Mapping[tuple[State, Symbol], Symbol], start: State):
        self.states = set(states); self.inputs = frozenset(inputs); self.outputs = frozenset(outputs)
        self.delta = dict(delta); self.lam = dict(lam); self.start = start
        if start not in self.states:
            raise AutomatonError("start not in Q")
        for q in self.states:
            for a in self.inputs:
                if (q, a) not in self.delta or (q, a) not in self.lam:
                    raise AutomatonError(f"Mealy machine must be total: missing ({q!r},{a!r})")
                if self.delta[(q, a)] not in self.states or self.lam[(q, a)] not in self.outputs:
                    raise AutomatonError(f"bad target/output at ({q!r},{a!r})")

    def run(self, word: Iterable[Symbol]) -> tuple[list[Symbol], Trace]:
        w = check_word(word, self.inputs)
        q, outs, steps = self.start, [], []
        for i, a in enumerate(w):
            o = self.lam[(q, a)]; nq = self.delta[(q, a)]
            steps.append(TraceStep(i, q, a, nq, info={"output": o}))
            outs.append(o); q = nq
        return outs, Trace(self.kind, w, steps, accepted=True, note="transducer: no acceptance, see outputs")

    def outputs_for(self, word) -> list[Symbol]:
        return self.run(word)[0]

    def same_state_different_outputs(self) -> list[tuple[State, Symbol, Symbol, Symbol, Symbol]]:
        """(q, a, a', out, out') witnesses where one state outputs differently for different inputs (Mealy-only behaviour)."""
        wit = []
        for q in sorted(self.states):
            for a, b in itertools.combinations(sorted(self.inputs), 2):
                if self.lam[(q, a)] != self.lam[(q, b)]:
                    wit.append((q, a, b, self.lam[(q, a)], self.lam[(q, b)]))
        return wit

    def to_moore(self, init_output: Symbol) -> "Moore":
        start = (self.start, init_output)
        seen, todo = {start}, [start]
        delta, out = {}, {start: init_output}
        while todo:
            q, o = todo.pop()
            for a in self.inputs:
                nq, no = self.delta[(q, a)], self.lam[(q, a)]
                tgt = (nq, no)
                delta[((q, o), a)] = tgt
                out[tgt] = no
                if tgt not in seen:
                    seen.add(tgt); todo.append(tgt)
        name = lambda s: f"{s[0]}/{s[1]}"
        return Moore({name(s) for s in seen}, self.inputs, self.outputs | {init_output},
                     {(name(s), a): name(t) for (s, a), t in delta.items()},
                     {name(s): o for s, o in out.items()}, name(start))


class Moore:
    kind = "Moore"

    def __init__(self, states: Iterable[State], inputs: Iterable[Symbol], outputs: Iterable[Symbol],
                 delta: Mapping[tuple[State, Symbol], State], out: Mapping[State, Symbol], start: State):
        self.states = set(states); self.inputs = frozenset(inputs); self.outputs = frozenset(outputs)
        self.delta = dict(delta); self.out = dict(out); self.start = start
        if start not in self.states:
            raise AutomatonError("start not in Q")
        for q in self.states:
            if q not in self.out or self.out[q] not in self.outputs:
                raise AutomatonError(f"Moore machine needs an output for every state; missing/invalid at {q!r}")
            for a in self.inputs:
                if (q, a) not in self.delta or self.delta[(q, a)] not in self.states:
                    raise AutomatonError(f"Moore machine must be total: missing ({q!r},{a!r})")

    def run(self, word: Iterable[Symbol]) -> tuple[list[Symbol], Trace]:
        w = check_word(word, self.inputs)
        q = self.start
        outs = [self.out[q]]
        steps = []
        for i, a in enumerate(w):
            nq = self.delta[(q, a)]
            steps.append(TraceStep(i, q, a, nq, info={"output_of_next_state": self.out[nq]}))
            outs.append(self.out[nq]); q = nq
        return outs, Trace(self.kind, w, steps, accepted=True, note="outputs are attached to states; n+1 outputs for n inputs")

    def outputs_for(self, word) -> list[Symbol]:
        return self.run(word)[0]

    def to_mealy(self) -> Mealy:
        """λ(q, a) = out(δ(q, a)); no state expansion is needed in this direction."""
        lam = {(q, a): self.out[self.delta[(q, a)]] for q in self.states for a in self.inputs}
        return Mealy(self.states, self.inputs, self.outputs, self.delta, lam, self.start)


def tool_call_controller_mealy() -> Mealy:
    """Small agent-flavoured Mealy machine: outputs depend on the *input observed in a state*, not only on the state."""
    S = {"idle", "calling", "retrying"}
    I = {"task", "ok", "error", "timeout"}
    O = {"noop", "call_tool", "proceed", "retry", "abort"}
    d, l = {}, {}
    def put(q, a, nq, o):
        d[(q, a)] = nq; l[(q, a)] = o
    for a in I: put("idle", a, "idle", "noop")
    put("idle", "task", "calling", "call_tool")
    put("calling", "ok", "idle", "proceed"); put("calling", "error", "retrying", "retry"); put("calling", "timeout", "retrying", "retry")
    put("calling", "task", "calling", "noop")
    for a in I: put("retrying", a, "retrying", "noop")
    put("retrying", "ok", "idle", "proceed"); put("retrying", "error", "idle", "abort"); put("retrying", "timeout", "idle", "abort")
    put("retrying", "task", "calling", "call_tool")
    return Mealy(S, I, O, d, l, "idle")
