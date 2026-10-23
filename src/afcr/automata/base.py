"""Shared types for all formal models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

State = str
Symbol = str

EPS: Symbol = "ε"          # epsilon label for eps-NFA / PDA transitions


class AutomatonError(ValueError):
    """Raised on structurally invalid automata or illegal inputs (unknown symbol, missing transition, ...)."""


@dataclass(frozen=True)
class StateInfo:
    """Metadata attached to a logical state of the agent benchmark automaton."""

    id: State
    label: str
    group: str                     # e.g. "PLAN", "OBSERVE", "TOOL", "MEMORY", "VALIDATE", "TERMINAL"
    kind: str                      # "nonterminal" | "accepting" | "rejecting"
    role: str                      # benign | decision | fault_entry | corridor | recovery | terminal_success | terminal_failure
    description: str
    attribution_note: str = ""

    def to_json(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class TraceStep:
    index: int
    state: Any                     # state, or frozenset of states for NFAs, or configuration for PDA/TM
    symbol: Symbol | None
    next_state: Any
    info: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        def enc(x):
            if isinstance(x, (set, frozenset)):
                return sorted(x)
            return x
        return {"index": self.index, "state": enc(self.state), "symbol": self.symbol,
                "next_state": enc(self.next_state), **{k: enc(v) for k, v in self.info.items()}}


@dataclass
class Trace:
    model: str
    word: tuple[Symbol, ...]
    steps: list[TraceStep]
    accepted: bool
    halted: bool = True
    note: str = ""
    reason: str = ""                  # why a run was rejected / blocked (empty when accepted)

    def to_json(self) -> dict[str, Any]:
        return {"model": self.model, "word": list(self.word), "accepted": self.accepted,
                "halted": self.halted, "note": self.note, "reason": self.reason, "steps": [s.to_json() for s in self.steps]}


def check_word(word, alphabet: frozenset[Symbol]) -> tuple[Symbol, ...]:
    w = tuple(word)
    for a in w:
        if a not in alphabet:
            raise AutomatonError(f"symbol {a!r} is not in the alphabet {sorted(alphabet)}")
    return w
