"""Decision rules ("targets"): WHAT is being identified, and when the confidence intervals certify it.

All rules consume simultaneous confidence intervals [lo_a, hi_a] for every eligible arm and are *correct on the
good event* E = {μ_a ∈ [lo_a, hi_a] for all arms and all times}; P(E) ≥ 1 - δ for the anytime-valid sequences, hence

    P(rule returns a wrong answer) ≤ δ                       (paper Theorem 1; any sampling rule).

ArgmaxEps(ε)      returns an ε-optimal arm: μ_h ≥ max_a μ_a - ε.   With ε = 0 it certifies the *unique* best arm and never
                  stops on instances with tied best arms (those end in abstention = budget exhaustion).
FirstAbove(θ)     returns the EARLIEST step whose repair value is ≥ θ   (AgenTracer's definition of the decisive step).
LastAbove(θ)      returns the LATEST step whose value is ≥ θ            (CAR's "point of commitment" with θ>0 as the margin).
Both threshold rules are exactly correct for the stated target on E and never need a unique-best-arm assumption.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Decision:
    status: str                          # "identified"
    selected: int | None                 # None => certified that no arm qualifies (threshold rules)
    certified_set: list[int] = field(default_factory=list)
    reason: str = ""


class Target(ABC):
    name = "target"

    @abstractmethod
    def decide(self, lo: np.ndarray, hi: np.ndarray, mean: np.ndarray, active: np.ndarray) -> Decision | None:
        """Return a Decision if the intervals certify an answer, else None.  ``active``: boolean mask of eligible arms."""

    @abstractmethod
    def suggest(self, lo: np.ndarray, hi: np.ndarray, mean: np.ndarray, n: np.ndarray, active: np.ndarray) -> list[int]:
        """LUCB-style arms to pull next (most informative for the stopping condition)."""

    @abstractmethod
    def provisional(self, lo: np.ndarray, hi: np.ndarray, mean: np.ndarray, active: np.ndarray) -> tuple[int | None, list[int]]:
        """(best guess, candidate set) to report when the budget is exhausted (NOT certified)."""

    def describe(self) -> dict:
        return {"name": self.name}


def _argmax_active(x: np.ndarray, active: np.ndarray, tie: np.ndarray | None = None) -> int:
    """argmax of x over active arms; ties broken by *smaller* ``tie`` value (e.g. fewer pulls), then lowest index."""
    idx = np.flatnonzero(active)
    xs = x[idx]
    best = xs.max()
    cand = idx[xs >= best - 1e-15]
    if tie is not None and len(cand) > 1:
        cand = cand[np.argsort(tie[cand], kind="stable")[:1]]
    return int(cand[0])


class ArgmaxEps(Target):
    name = "argmax"

    def __init__(self, eps: float = 0.0):
        if eps < 0:
            raise ValueError("eps must be >= 0")
        self.eps = float(eps)

    def describe(self):
        return {"name": self.name, "eps": self.eps}

    def decide(self, lo, hi, mean, active):
        idx = np.flatnonzero(active)
        if len(idx) == 0:
            return None
        if len(idx) == 1:
            return Decision("identified", int(idx[0]), [int(idx[0])], "single eligible candidate")
        h_act, l_act = hi[idx], lo[idx]
        order = np.argsort(-h_act)
        top1, top2 = h_act[order[0]], h_act[order[1]]
        other_max = np.where(np.arange(len(idx)) == order[0], top2, top1)
        ok = (l_act + self.eps >= other_max) if self.eps > 0 else (l_act > other_max)
        if not ok.any():
            return None
        cand = np.flatnonzero(ok)
        best = int(idx[cand[np.argmax(l_act[cand])]])
        cert = [int(a) for a in idx if hi[a] + self.eps >= lo[best] and a != best] if self.eps > 0 else []
        return Decision("identified", best, sorted([best] + (cert if self.eps > 0 else [])),
                        f"lo[{best}]+eps ≥ max other hi" if self.eps > 0 else f"lo[{best}] > max other hi")

    def suggest(self, lo, hi, mean, n, active):
        idx = np.flatnonzero(active)
        h = _argmax_active(mean, active, tie=n)
        rest = active.copy(); rest[h] = False
        if not rest.any():
            return [h]
        l = _argmax_active(hi, rest, tie=n)
        return [h, l]

    def provisional(self, lo, hi, mean, active):
        idx = np.flatnonzero(active)
        h = _argmax_active(mean, active)
        thresh = lo[idx].max()
        cand = [int(a) for a in idx if hi[a] >= thresh]
        return h, cand


class _Threshold(Target):
    def __init__(self, theta: float, strict: bool = False):
        if not 0.0 <= theta <= 1.0:
            raise ValueError("theta must lie in [0, 1]")
        self.theta, self.strict = float(theta), bool(strict)

    def describe(self):
        return {"name": self.name, "theta": self.theta, "strict": self.strict}

    def _above(self, lo):   # certified: μ ≥ θ  (or μ > θ if strict)
        return lo > self.theta if self.strict else lo >= self.theta

    def _below(self, hi):   # certified: μ < θ  (or μ ≤ θ if strict)
        return hi <= self.theta if self.strict else hi < self.theta

    def _scan(self, order: list[int], lo, hi):
        """First certified-above arm in ``order`` provided every earlier arm is certified-below; else the first uncertain arm."""
        for a in order:
            if self._above(lo[a]):
                return "above", a
            if not self._below(hi[a]):
                return "uncertain", a
        return "none", None

    def provisional(self, lo, hi, mean, active):
        idx = [int(a) for a in np.flatnonzero(active)]
        order = self._order(idx)
        for a in order:
            if mean[a] >= self.theta:
                return a, [int(x) for x in idx if not self._below(hi[x])]
        return None, [int(x) for x in idx if not self._below(hi[x])]

    def _order(self, idx):
        raise NotImplementedError

    def decide(self, lo, hi, mean, active):
        idx = [int(a) for a in np.flatnonzero(active)]
        kind, a = self._scan(self._order(idx), lo, hi)
        if kind == "above":
            return Decision("identified", a, [a], f"{self.name}: arm {a} certified ≥ θ, all earlier/later arms certified < θ")
        if kind == "none":
            return Decision("identified", None, [], f"{self.name}: every arm certified below θ — no arm qualifies")
        return None

    def suggest(self, lo, hi, mean, n, active):
        idx = [int(a) for a in np.flatnonzero(active)]
        kind, a = self._scan(self._order(idx), lo, hi)
        return [a] if a is not None else [idx[0]]


class FirstAbove(_Threshold):
    name = "first_above"

    def _order(self, idx):
        return sorted(idx)


class LastAbove(_Threshold):
    name = "last_above"

    def _order(self, idx):
        return sorted(idx, reverse=True)


def make_target(name: str, **kw) -> Target:
    table = {"argmax": ArgmaxEps, "first_above": FirstAbove, "last_above": LastAbove}
    if name not in table:
        raise ValueError(f"unknown target {name!r}; choose from {sorted(table)}")
    return table[name](**kw)
