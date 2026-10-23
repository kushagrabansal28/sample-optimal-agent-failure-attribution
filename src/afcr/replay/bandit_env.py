"""Direct Bernoulli-arm environment: the statistical-core test bed (Stage A, 'arm model').

Each arm's success probability is prescribed, so the gap structure, ties and the number of near-best arms are
controlled exactly.  There is no trajectory and no sharing.  Results on this environment are *synthetic bandit
simulations* and are labelled as such everywhere.
"""
from __future__ import annotations

import numpy as np

from .base import PullResult, ReplayEnv


class BanditEnv(ReplayEnv):
    sharing_valid = False

    def __init__(self, mu, *, planted: int | None = None, eligible=None, labels=None, name="bandit"):
        self.mu = np.asarray(mu, dtype=float)
        if self.mu.ndim != 1 or len(self.mu) < 1 or np.any(self.mu < 0) or np.any(self.mu > 1):
            raise ValueError("mu must be a 1-D vector of probabilities")
        self.n_arms = len(self.mu)
        self.arm_labels = list(labels) if labels is not None else [f"step {i + 1}" for i in range(self.n_arms)]
        self.eligible = np.ones(self.n_arms, dtype=bool) if eligible is None else np.asarray(eligible, dtype=bool)
        self._planted = planted if planted is not None else int(np.argmax(self.mu))
        self.name = name

    def pull(self, arm: int, rng: np.random.Generator) -> PullResult:
        return PullResult(int(rng.random() < self.mu[arm]), cost=1)

    def true_means(self) -> np.ndarray:
        return self.mu.copy()

    def planted_arm(self) -> int:
        return self._planted


def make_gap_instance(K: int, gap: float, *, best: float = 0.7, n_near: int = 1, rest: float | None = None,
                      best_index: int | None = None) -> BanditEnv:
    """One best arm at ``best``; ``n_near`` runner-up arms at ``best - gap``; all others at ``rest``
    (default ``best - 3*gap`` clipped to [0.02, best - gap]).  ``best_index`` defaults to the last arm."""
    if K < 2:
        raise ValueError("need K >= 2")
    if not 0 < gap < best <= 1:
        raise ValueError("need 0 < gap < best <= 1")
    rest_v = rest if rest is not None else float(np.clip(best - 3 * gap, 0.02, best - gap))
    others = np.full(K - 1, rest_v)
    others[: min(max(n_near, 1), K - 1)] = best - gap
    bi = K - 1 if best_index is None else best_index
    if not 0 <= bi < K:
        raise ValueError("best_index out of range")
    return BanditEnv(np.insert(others, bi, best), planted=bi, name=f"gap{gap:g}_K{K}")
