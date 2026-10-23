"""Automaton-induced replay environment (Stage A, 'automaton model').

The arms are the steps of one *failed trajectory* of the 48-state agent automaton.  A pull performs the intervention at
that step (``repair``: force the reference action ρ(q); ``resample``: re-draw from π — CAR's null intervention) and
simulates the continuation under the same stochastic policy.  Ground-truth arm values are exact (backward induction).

Prefix reuse (Theorem 3).  Time-augmented states make the process Markov.  A rollout that, at time j-1, is in the
original state q_{j-1} and (for 'repair') takes ρ(q_{j-1}) is — conditionally on that event — distributed exactly as a
pull of arm j, so its outcome is a valid sample of arm j.  ``state_reconstruction_noise`` > 0 breaks this (the
replay context no longer equals the original context), so sharing is then declared invalid.
"""
from __future__ import annotations

import numpy as np

from ..automata.benchmark48 import AgentModel, OriginalTrajectory
from .base import PullResult, ReplayEnv


class AutomatonEnv(ReplayEnv):
    def __init__(self, model: AgentModel, traj: OriginalTrajectory, *, intervention: str = "repair",
                 candidates: str | list[int] = "all", state_reconstruction_noise: float = 0.0):
        if intervention not in ("repair", "resample"):
            raise ValueError("intervention must be 'repair' or 'resample'")
        if not 0.0 <= state_reconstruction_noise <= 1.0:
            raise ValueError("state_reconstruction_noise must lie in [0, 1]")
        self.model, self.traj, self.intervention = model, traj, intervention
        self.noise = state_reconstruction_noise
        T = traj.T
        all_steps = list(range(1, T + 1))
        if candidates == "all":
            self.steps = all_steps
        elif candidates == "decision":
            dec = set(model.decision_states())
            self.steps = [t for t in all_steps if model.ids[traj.states[t - 1]] in dec]
        elif isinstance(candidates, list):
            self.steps = [t for t in candidates if 1 <= t <= T]
        else:
            raise ValueError("candidates must be 'all', 'decision' or an explicit list of steps")
        if not self.steps:
            raise ValueError("no eligible candidate steps")
        self.n_arms = len(self.steps)
        self.arm_labels = [f"t={t}: {model.ids[traj.states[t - 1]]}" for t in self.steps]
        self.eligible = np.ones(self.n_arms, dtype=bool)
        self.sharing_valid = state_reconstruction_noise == 0.0
        self.name = f"automaton[{model.name}]"
        self._start_key = {(t - 1, traj.states[t - 1]): arm for arm, t in enumerate(self.steps)}
        self._ref = model.ref_idx
        self._noise_pool: dict[int, list[int]] = {}
        for q, sid in enumerate(model.ids):
            g = model.specs[sid].info.group
            self._noise_pool[q] = [j for j, s2 in enumerate(model.ids)
                                   if j != q and model.specs[s2].info.group == g and not model.terminal[j]]
        self._planted_arm: int | None = None
        pc = traj.planted_cause
        if pc is not None and pc in self.steps:
            self._planted_arm = self.steps.index(pc)

    # ------------------------------------------------------------------
    def _start_state(self, arm: int, rng: np.random.Generator) -> tuple[int, int]:
        t0 = self.steps[arm] - 1
        q = self.traj.states[t0]
        if self.noise > 0 and rng.random() < self.noise and self._noise_pool[q]:
            q = self._noise_pool[q][int(rng.integers(len(self._noise_pool[q])))]
        return t0, q

    def pull(self, arm: int, rng: np.random.Generator) -> PullResult:
        t0, q = self._start_state(arm, rng)
        forced = int(self._ref[q]) if self.intervention == "repair" else None
        roll = self.model.simulate(rng, q, t0, forced_action=forced, record=True)
        shared: list[int] = []
        if self.sharing_valid:
            for (t, qq, a) in roll.path[1:]:
                j = self._start_key.get((t, qq))
                if j is not None and j != arm and (self.intervention == "resample" or a == self._ref[qq]):
                    shared.append(j)
        naive = tuple(j for j in range(arm + 1, self.n_arms))
        return PullResult(int(roll.success), cost=max(roll.steps, 1), shared_arms=tuple(shared),
                          naive_shared_arms=naive, info={"timed_out": roll.timed_out})

    def replay_detail(self, arm: int, rng: np.random.Generator) -> dict:
        """One replay with the full counterfactual trace (for the trajectory explorer)."""
        t0, q = self._start_state(arm, rng)
        forced = int(self._ref[q]) if self.intervention == "repair" else None
        roll = self.model.simulate(rng, q, t0, forced_action=forced, record=True)
        m = self.model
        steps = [{"t": t + 1, "state": m.ids[qq], "action": m.sym_ids[qq][a],
                  "is_fault": bool(m.fault_mask[qq][a]), "forced": (i == 0 and forced is not None)}
                 for i, (t, qq, a) in enumerate(roll.path)]
        end = m.ids[roll.terminal] if roll.terminal is not None else None
        return {"arm": arm, "step": self.steps[arm], "intervention": self.intervention,
                "start_state": m.ids[q], "start_time": t0, "path": steps, "terminal": end,
                "success": roll.success, "timed_out": roll.timed_out}

    # ------------------------------------------------------------------ ground truth
    def _mu_state(self, q: int, t0: int) -> float:
        V = self.model.value_table()
        m = self.model
        if self.intervention == "resample":
            return float(V[t0, q])
        a = int(self._ref[q]); prev, e = 0.0, 0.0
        for r, c in zip(m.next_ids[q][a], m.next_cum[q][a]):
            e += (c - prev) * V[t0 + 1, r]; prev = c
        return e

    def noise_free_means(self) -> np.ndarray:
        return self.model.exact_mu(self.traj, self.intervention, self.steps)

    def true_means(self) -> np.ndarray:
        base = self.noise_free_means()
        if self.noise == 0.0:
            return base
        out = np.zeros(self.n_arms)
        for arm, t in enumerate(self.steps):
            t0, q = t - 1, self.traj.states[t - 1]
            pool = self._noise_pool[q]
            alt = float(np.mean([self._mu_state(j, t0) for j in pool])) if pool else base[arm]
            out[arm] = (1 - self.noise) * base[arm] + self.noise * alt
        return out

    def planted_arm(self) -> int | None:
        return self._planted_arm


def make_automaton_instance(model: AgentModel, rng: np.random.Generator, *, intervention: str = "repair",
                            candidates: str = "all", state_reconstruction_noise: float = 0.0,
                            require_fault: bool = True, min_len: int = 4) -> AutomatonEnv:
    traj = model.sample_failed(rng, min_len=min_len, require_fault=require_fault)
    return AutomatonEnv(model, traj, intervention=intervention, candidates=candidates,
                        state_reconstruction_noise=state_reconstruction_noise)
