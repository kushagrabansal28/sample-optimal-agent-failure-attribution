"""Sampling strategies (allocation rules).  The stopping rule is NOT here — it lives in the Target + confidence sequence,
which is why a strategy can never compromise δ-correctness (Theorem 1 holds for any strategy).

lucb                 sample the empirical best arm and its strongest challenger (Kalyanakrishnan et al. 2012; KL version K&K 2013)
uniform_fc           round-robin over arms, with the SAME stopping rule  (matched confidence target)
random_fc            uniformly random arm each pull, SAME stopping rule
successive_elim      round-robin over arms that have not been eliminated (Even-Dar et al. 2006 style)  [argmax target only]
equal_budget         spend the whole budget evenly, never stop early, return the empirical argmax  (matched budget; no guarantee)
random_budget        spend the whole budget on uniformly random arms, return the empirical argmax     (no guarantee)
car_fixed_k          CAR-style (re-implemented from the paper's text): K rollouts per arm, Wilson CIs, latest step whose CI excludes 0
oracle               knows the exact means; 0 rollouts (reference upper bound, synthetic only)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .targets import Target, _argmax_active


@dataclass
class View:
    K: int
    active: np.ndarray
    n: np.ndarray
    s: np.ndarray
    mean: np.ndarray
    lo: np.ndarray
    hi: np.ndarray
    rounds: int
    pulls: int
    rng: np.random.Generator
    target: Target


class Strategy:
    name = "strategy"
    fixed_budget = False          # True: never stops early; always spends the budget (or its own quota)
    is_oracle = False
    needs_wilson = False          # use non-sequential Wilson intervals (CAR-style)

    def select(self, v: View) -> list[int]:
        raise NotImplementedError

    def final(self, v: View) -> tuple[int | None, list[int]]:
        """Answer reported when the run ends without a certified decision."""
        idx = np.flatnonzero(v.active)
        best = v.mean[idx].max()
        cand = idx[v.mean[idx] >= best - 1e-12]
        pick = int(v.rng.choice(cand))
        return pick, [int(a) for a in cand]

    def quota(self, v: View) -> int | None:
        """Optional hard cap on pulls for fixed-budget strategies (None = engine budget)."""
        return None


def _least_pulled(v: View, mask: np.ndarray | None = None) -> int:
    act = v.active if mask is None else (v.active & mask)
    idx = np.flatnonzero(act)
    return int(idx[np.argmin(v.n[idx])])


class LUCB(Strategy):
    name = "lucb"

    def select(self, v):
        unseen = [int(a) for a in np.flatnonzero(v.active & (v.n == 0))]
        if unseen:
            return unseen
        return v.target.suggest(v.lo, v.hi, v.mean, v.n, v.active)


class UniformFC(Strategy):
    name = "uniform_fc"

    def select(self, v):
        return [_least_pulled(v)]


class RandomFC(Strategy):
    name = "random_fc"

    def select(self, v):
        return [int(v.rng.choice(np.flatnonzero(v.active)))]


class SuccessiveElimination(Strategy):
    name = "successive_elim"

    def select(self, v):
        idx = np.flatnonzero(v.active)
        survivors = v.active & (v.hi >= v.lo[idx].max() - 1e-15)
        unseen = np.flatnonzero(v.active & (v.n == 0))
        if len(unseen):
            return [int(a) for a in unseen]
        return [_least_pulled(v, survivors)]


class EqualBudget(Strategy):
    name = "equal_budget"
    fixed_budget = True

    def select(self, v):
        return [_least_pulled(v)]


class RandomBudget(Strategy):
    name = "random_budget"
    fixed_budget = True

    def select(self, v):
        return [int(v.rng.choice(np.flatnonzero(v.active)))]


class CARFixedK(Strategy):
    """CAR-style contrastive rule, re-implemented from the paper's description (NOT from its code):
    K rollouts per candidate; Wilson 95% interval per arm; the culprit is the LATEST step whose interval excludes zero
    (here: lower bound > 0, i.e. at least one observed success).  Uses 'resample' interventions in the experiments."""
    name = "car_fixed_k"
    fixed_budget = True
    needs_wilson = True

    def __init__(self, k_per_arm: int = 50):
        if k_per_arm < 1:
            raise ValueError("k_per_arm must be >= 1")
        self.k = int(k_per_arm)

    def select(self, v):
        return [_least_pulled(v)]

    def quota(self, v):
        return self.k * int(v.active.sum())

    def final(self, v):
        idx = [int(a) for a in np.flatnonzero(v.active)]
        above = [a for a in idx if v.lo[a] > 0.0]
        return (max(above) if above else None), above


class OracleStrategy(Strategy):
    name = "oracle"
    is_oracle = True
    fixed_budget = True

    def select(self, v):
        return []


def make_strategy(name: str, **kw) -> Strategy:
    table = {
        "lucb": LUCB, "uniform_fc": UniformFC, "random_fc": RandomFC, "successive_elim": SuccessiveElimination,
        "equal_budget": EqualBudget, "random_budget": RandomBudget, "car_fixed_k": CARFixedK, "oracle": OracleStrategy,
    }
    if name not in table:
        raise ValueError(f"unknown strategy {name!r}; choose from {sorted(table)}")
    return table[name](**kw)
