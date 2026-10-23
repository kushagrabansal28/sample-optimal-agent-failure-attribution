"""Replay-environment protocol.

An *arm* is a candidate intervention point.  ``pull(arm, rng)`` performs the pre-specified intervention at that
point, replays the continuation and returns one binary outcome (Y = 1: task success).

Prefix sharing (paper §6.4 / Theorem 3).  A pull may also report ``shared_arms``: other arms for which the *same*
rollout is a **valid** sample, by the strong Markov property, because the rollout visited exactly that arm's start
state at that arm's start time and (for 'repair' protocols) took exactly that arm's intervention action.
``naive_shared_arms`` lists what a *naive* heuristic ("a shared prefix means interchangeable outcomes") would credit;
it exists only to run the negative control and is never used by the guaranteed algorithm.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class PullResult:
    outcome: int
    cost: int = 1                                   # simulated environment steps consumed by this rollout
    shared_arms: tuple[int, ...] = ()
    naive_shared_arms: tuple[int, ...] = ()
    info: dict[str, Any] = field(default_factory=dict)


class ReplayEnv(ABC):
    n_arms: int
    arm_labels: list[str]
    eligible: np.ndarray                            # bool mask of eligible candidates
    sharing_valid: bool = False                     # does the environment satisfy the conditions of Theorem 3?
    name: str = "env"

    @abstractmethod
    def pull(self, arm: int, rng: np.random.Generator) -> PullResult: ...

    def true_means(self) -> np.ndarray | None:
        """Exact (or reference) arm means — for EVALUATION only; algorithms never see them."""
        return None

    def planted_arm(self) -> int | None:
        """Index of the planted cause among the arms, if the instance has one."""
        return None

    def describe_arm(self, arm: int) -> dict[str, Any]:
        return {"arm": arm, "label": self.arm_labels[arm]}
