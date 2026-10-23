"""Replay environment over the Stage-B tool agent (explicit snapshots, exact ground truth, exact-match prefix reuse)."""
from __future__ import annotations

import numpy as np

from ..agents.toolagent import PHASES, ToolAgentWorld, ToolTrajectory
from .base import PullResult, ReplayEnv


class ToolAgentEnv(ReplayEnv):
    def __init__(self, world: ToolAgentWorld, traj: ToolTrajectory, *, intervention: str = "repair"):
        if intervention not in ("repair", "resample"):
            raise ValueError("intervention must be 'repair' or 'resample'")
        self.world, self.traj, self.intervention = world, traj, intervention
        self.steps = list(range(1, traj.T + 1))
        self.n_arms = len(self.steps)
        self.arm_labels = [f"t={t}: {PHASES[traj.states[t - 1].phase]}" for t in self.steps]
        self.eligible = np.ones(self.n_arms, dtype=bool)
        self.sharing_valid = True                     # snapshots are exact, so A1 holds by construction
        self.name = f"toolagent[{world.name}]"
        self._start_key = {(t - 1, traj.states[t - 1]): arm for arm, t in enumerate(self.steps)}
        pc = traj.planted_cause
        self._planted = (self.steps.index(pc) if pc in self.steps else None)

    def pull(self, arm: int, rng: np.random.Generator) -> PullResult:
        t0 = self.steps[arm] - 1
        s = self.traj.states[t0]
        forced = self.world.ref_action(s) if self.intervention == "repair" else None
        path, final, timed_out = self.world.simulate(rng, s, t0, forced=forced, record=True)
        shared = []
        for (t, st, a) in path[1:]:
            j = self._start_key.get((t, st))
            if j is not None and j != arm and (self.intervention == "resample" or a == self.world.ref_action(st)):
                shared.append(j)
        return PullResult(int(self.world.success(final)), cost=max(len(path), 1), shared_arms=tuple(shared),
                          naive_shared_arms=tuple(range(arm + 1, self.n_arms)), info={"timed_out": timed_out})

    def replay_detail(self, arm: int, rng: np.random.Generator) -> dict:
        t0 = self.steps[arm] - 1
        s = self.traj.states[t0]
        forced = self.world.ref_action(s) if self.intervention == "repair" else None
        path, final, timed_out = self.world.simulate(rng, s, t0, forced=forced, record=True)
        steps = [{"t": t + 1, "state": PHASES[st.phase], "action": a, "is_fault": a in self.world.fault_actions,
                  "forced": i == 0 and forced is not None, "note": self.world.narrate(st, a)} for i, (t, st, a) in enumerate(path)]
        return {"arm": arm, "step": self.steps[arm], "intervention": self.intervention, "start_state": PHASES[s.phase], "start_time": t0,
                "path": steps, "terminal": "ANSWER", "success": self.world.success(final), "timed_out": timed_out,
                "answer": final.answer, "gold": self.world.gold}

    def true_means(self) -> np.ndarray:
        return self.world.exact_mu(self.traj, self.intervention, self.steps)

    def planted_arm(self):
        return self._planted


def make_toolagent_instance(world: ToolAgentWorld, rng: np.random.Generator, *, intervention: str = "repair",
                            require_fault: bool = True) -> ToolAgentEnv:
    return ToolAgentEnv(world, world.sample_failed(rng, require_fault=require_fault), intervention=intervention)
