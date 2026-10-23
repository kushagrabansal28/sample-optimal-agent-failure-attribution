"""Bounded-tape Turing machine simulator.

The bound (``max_cells`` of used tape, ``max_steps``) is an *implementation convenience* guaranteeing that the
simulator terminates.  A bounded simulator does NOT have the computational power of an unbounded Turing machine:
a run that hits a bound ends with status 'step_limit' or 'tape_bound' — which means "unknown", not "rejects".
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from .base import AutomatonError, State, Symbol


@dataclass
class TMConfig:
    step: int
    state: State
    head: int
    tape: dict[int, Symbol] = field(default_factory=dict)
    blank: Symbol = "_"

    def render(self, window: int | None = None) -> str:
        lo = min(list(self.tape) + [self.head]); hi = max(list(self.tape) + [self.head])
        if window is not None:
            lo, hi = min(lo, self.head - window), max(hi, self.head + window)
        return "".join(f"[{self.tape.get(i, self.blank)}]" if i == self.head else f" {self.tape.get(i, self.blank)} " for i in range(lo, hi + 1))

    def contents(self) -> str:
        if not self.tape:
            return ""
        lo, hi = min(self.tape), max(self.tape)
        return "".join(self.tape.get(i, self.blank) for i in range(lo, hi + 1)).strip(self.blank)

    def to_json(self) -> dict:
        return {"step": self.step, "state": self.state, "head": self.head,
                "tape": {str(k): v for k, v in sorted(self.tape.items())}, "rendered": self.render()}


@dataclass
class TMResult:
    status: str                 # accept | reject | step_limit | tape_bound | halt_no_transition
    steps: int
    trace: list[TMConfig]
    final: TMConfig

    @property
    def accepted(self) -> bool:
        return self.status == "accept"

    @property
    def halted(self) -> bool:
        return self.status in ("accept", "reject", "halt_no_transition")

    def to_json(self) -> dict:
        return {"status": self.status, "steps": self.steps, "accepted": self.accepted, "halted": self.halted,
                "output": self.final.contents(), "trace": [c.to_json() for c in self.trace]}


class TuringMachine:
    kind = "Turing machine (bounded simulation)"

    def __init__(self, states: Iterable[State], input_alphabet: Iterable[Symbol], tape_alphabet: Iterable[Symbol],
                 blank: Symbol, delta: Mapping[tuple[State, Symbol], tuple[State, Symbol, str]],
                 start: State, accept: State, reject: State):
        self.states = set(states); self.sigma = frozenset(input_alphabet); self.gamma = frozenset(tape_alphabet)
        self.blank = blank; self.delta = dict(delta); self.start = start; self.accept = accept; self.reject = reject
        if blank not in self.gamma or blank in self.sigma or not self.sigma <= self.gamma:
            raise AutomatonError("need Σ ⊆ Γ and blank ∈ Γ \\ Σ")
        if not {start, accept, reject} <= self.states or accept == reject:
            raise AutomatonError("start/accept/reject must be distinct members of Q" if accept == reject else "start/accept/reject must belong to Q")
        for (q, a), (q2, b, m) in self.delta.items():
            if q in (accept, reject):
                raise AutomatonError("halting states must have no outgoing transitions")
            if q not in self.states or q2 not in self.states or a not in self.gamma or b not in self.gamma or m not in ("L", "R", "S"):
                raise AutomatonError(f"invalid transition ({q!r},{a!r})->({q2!r},{b!r},{m!r})")

    def run(self, word: Iterable[Symbol], *, max_steps: int = 10000, max_cells: int = 256, keep_trace: bool = True) -> TMResult:
        w = list(word)
        for c in w:
            if c not in self.sigma:
                raise AutomatonError(f"input symbol {c!r} not in Σ")
        if len(w) > max_cells:
            raise AutomatonError("input longer than the tape bound")
        tape = {i: c for i, c in enumerate(w)}
        cfg = TMConfig(0, self.start, 0, dict(tape), self.blank)
        trace = [TMConfig(0, self.start, 0, dict(tape), self.blank)] if keep_trace else []
        lo, hi = 0, max(len(w) - 1, 0)
        q, head, steps = self.start, 0, 0
        while True:
            if q == self.accept or q == self.reject:
                status = "accept" if q == self.accept else "reject"
                break
            if steps >= max_steps:
                status = "step_limit"; break
            sym = tape.get(head, self.blank)
            key = (q, sym)
            if key not in self.delta:
                status = "halt_no_transition"; break
            q2, b, m = self.delta[key]
            if b == self.blank:
                tape.pop(head, None)
            else:
                tape[head] = b
            head += {"L": -1, "R": 1, "S": 0}[m]
            lo, hi = min(lo, head), max(hi, head)
            if hi - lo + 1 > max_cells:
                status = "tape_bound"; q = q2; steps += 1; break
            q = q2; steps += 1
            if keep_trace:
                trace.append(TMConfig(steps, q, head, dict(tape), self.blank))
        final = TMConfig(steps, q, head, dict(tape), self.blank)
        return TMResult(status, steps, trace, final)

    def accepts(self, word, **kw) -> bool:
        return self.run(word, **kw).accepted


def binary_increment_tm() -> TuringMachine:
    """Increment a binary number (MSB first): output = input + 1.  Demonstration of read/write/move."""
    d = {
        ("scan", "0"): ("scan", "0", "R"), ("scan", "1"): ("scan", "1", "R"), ("scan", "_"): ("carry", "_", "L"),
        ("carry", "1"): ("carry", "0", "L"), ("carry", "0"): ("done", "1", "S"), ("carry", "_"): ("done", "1", "S"),
        ("done", "0"): ("acc", "0", "S"), ("done", "1"): ("acc", "1", "S"), ("done", "_"): ("acc", "_", "S"),
    }
    return TuringMachine({"scan", "carry", "done", "acc", "rej"}, {"0", "1"}, {"0", "1", "_"}, "_", d, "scan", "acc", "rej")


def palindrome_tm() -> TuringMachine:
    """Decide { w ∈ {a,b}* : w is a palindrome } by erasing matching end symbols."""
    d = {}
    for s in ("a", "b"):
        d[("q0", s)] = (f"has_{s}", "_", "R")
        d[(f"has_{s}", "a")] = (f"go_{s}", "a", "R")
        d[(f"has_{s}", "b")] = (f"go_{s}", "b", "R")
        d[(f"has_{s}", "_")] = ("acc", "_", "S")                  # single middle symbol
        d[(f"go_{s}", "a")] = (f"go_{s}", "a", "R"); d[(f"go_{s}", "b")] = (f"go_{s}", "b", "R")
        d[(f"go_{s}", "_")] = (f"end_{s}", "_", "L")
        d[(f"end_{s}", s)] = ("back", "_", "L")
        d[(f"end_{s}", "b" if s == "a" else "a")] = ("rej", "_", "S")
        d[(f"end_{s}", "_")] = ("acc", "_", "S")                  # nothing left
    d[("q0", "_")] = ("acc", "_", "S")
    d[("back", "a")] = ("back", "a", "L"); d[("back", "b")] = ("back", "b", "L"); d[("back", "_")] = ("q0", "_", "R")
    states = {"q0", "back", "acc", "rej"} | {f"{p}_{s}" for p in ("has", "go", "end") for s in ("a", "b")}
    return TuringMachine(states, {"a", "b"}, {"a", "b", "_"}, "_", d, "q0", "acc", "rej")
