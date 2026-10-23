"""Generic text-environment replay (shared by the ALFWorld and HotpotQA adapters).

A *text game* is deterministic given its seed and the action history (true for ALFWorld/TextWorld and for a retrieval QA
tool-loop), so a prefix is reproduced EXACTLY by re-executing the first t-1 actions.  The agent is an LLM (any ModelProvider)
whose action distribution depends only on the history, so the time-augmented state is the action-history tuple and the
prefix-reuse proof (Thm 3) applies with exact history match.  With temperature 0 and a deterministic provider the replay is
deterministic (outcomes in {0,1}); with temperature > 0 outcomes are stochastic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from ..agents.providers import ModelProvider
from ..replay.base import PullResult, ReplayEnv


class BenchmarkUnavailable(RuntimeError):
    """Raised when an optional benchmark dependency or dataset is not installed."""


class TextGame(Protocol):
    def reset(self, seed: int) -> str: ...
    def step(self, action: str) -> tuple[str, bool, bool]: ...         # (observation, done, success)
    def admissible(self) -> list[str]: ...                                # may be empty


@dataclass
class Episode:
    seed: int
    observations: list[str]
    actions: list[str]
    success: bool


@dataclass
class LLMTextAgent:
    provider: ModelProvider
    prompt_template: str = "Observation: {obs}\nHistory: {hist}\nNext action:"
    temperature: float = 0.7
    max_steps: int = 30

    def act(self, obs: str, history: list[str], seed: int) -> str:
        p = self.prompt_template.format(obs=obs, hist=" | ".join(history[-6:]))
        return self.provider.complete(p, seed=seed, temperature=self.temperature).strip()

    def run(self, game: TextGame, seed: int, rng: np.random.Generator) -> Episode:
        obs = game.reset(seed)
        obss, acts, ok = [obs], [], False
        for _ in range(self.max_steps):
            a = self.act(obs, acts, int(rng.integers(2 ** 31)))
            obs, done, ok = game.step(a)
            acts.append(a); obss.append(obs)
            if done:
                break
        return Episode(seed, obss, acts, bool(ok))


class TextGameReplayEnv(ReplayEnv):
    """Arms = steps of one recorded failed episode.  ``repair_fn(obs, history, t)`` supplies the reference (repair) action
    (e.g. an expert/oracle policy or an alternative sampled from the model); with ``intervention='resample'`` the agent redraws."""

    def __init__(self, game: TextGame, agent: LLMTextAgent, episode: Episode, *, repair_fn=None, intervention: str = "resample"):
        if intervention == "repair" and repair_fn is None:
            raise ValueError("intervention='repair' needs a repair_fn")
        self.game, self.agent, self.ep, self.repair_fn, self.intervention = game, agent, episode, repair_fn, intervention
        T = len(episode.actions)
        self.n_arms = T
        self.arm_labels = [f"t={t + 1}: {episode.actions[t][:28]}" for t in range(T)]
        self.eligible = np.ones(T, dtype=bool)
        self.sharing_valid = True
        self.name = "textgame"
        self._keys = {tuple(episode.actions[:t]): t for t in range(T)}          # history before step t+1 -> arm

    def _prefix(self, t: int) -> tuple[str, list[str]]:
        obs = self.game.reset(self.ep.seed)
        hist: list[str] = []
        for a in self.ep.actions[:t]:
            obs, done, _ = self.game.step(a)
            hist.append(a)
        return obs, hist

    def pull(self, arm: int, rng: np.random.Generator) -> PullResult:
        obs, hist = self._prefix(arm)
        done, ok, steps = False, False, 0
        shared: list[int] = []
        first = True
        while not done and len(hist) < self.agent.max_steps:
            if first and self.intervention == "repair":
                a = self.repair_fn(obs, hist, arm + 1)
            else:
                a = self.agent.act(obs, hist, int(rng.integers(2 ** 31)))
            if not first:
                # the rollout is now at history `hist` taking action `a`; arm j matches if hist == original prefix and a == its action
                j = self._keys.get(tuple(hist))
                if j is not None and j > arm and (self.intervention == "resample" or a == self.ep.actions[j]):
                    shared.append(j)
            first = False
            obs, done, ok = self.game.step(a)
            hist.append(a); steps += 1
        return PullResult(int(bool(ok) and done), cost=max(steps, 1), shared_arms=tuple(shared),
                          naive_shared_arms=tuple(range(arm + 1, self.n_arms)))
