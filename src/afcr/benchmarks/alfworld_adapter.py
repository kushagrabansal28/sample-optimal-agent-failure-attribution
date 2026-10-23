"""ALFWorld adapter (Stage C) — INTERFACE ONLY.  No ALFWorld result exists in this repository.

Setup facts (from the package metadata / README as reported by secondary sources, NOT verified against the official repo):
MIT licence; text mode needs ``pip install alfworld`` (pulls TextWorld) and ``alfworld-download`` (data in ``~/.cache/alfworld``
or $ALFWORLD_DATA).  The agent needs an LLM (see ``afcr.agents.providers``); none is run here.

Usage once installed:
    game = ALFWorldGame(config_path)                      # wraps alfworld's text env
    agent = LLMTextAgent(OpenAICompatProvider("my-model"))
    ep = agent.run(game, seed=0, rng=rng)                 # record an episode
    env = TextGameReplayEnv(game, agent, ep)              # arms = steps of a FAILED episode
"""
from __future__ import annotations

from .textgame import BenchmarkUnavailable


class ALFWorldGame:
    def __init__(self, config_path: str, split: str = "eval_out_of_distribution"):
        try:
            import alfworld.agents.environment as env_mod                       # type: ignore  # pragma: no cover
            from alfworld.agents.environment import get_environment               # type: ignore  # pragma: no cover
            import yaml                                                           # pragma: no cover
        except ImportError as e:
            raise BenchmarkUnavailable("ALFWorld is not installed: `pip install alfworld` then `alfworld-download`") from e
        with open(config_path) as fh:                                              # pragma: no cover
            cfg = yaml.safe_load(fh)
        self._env = get_environment(cfg["env"]["type"])(cfg, train_eval=split).init_env(batch_size=1)   # pragma: no cover
        self._obs = ""                                                                                  # pragma: no cover

    def reset(self, seed: int) -> str:                                             # pragma: no cover
        self._env.seed(seed)
        obs, info = self._env.reset()
        self._info = info
        return obs[0]

    def step(self, action: str):                                                    # pragma: no cover
        obs, scores, dones, infos = self._env.step([action])
        return obs[0], bool(dones[0]), bool(infos.get("won", [False])[0])

    def admissible(self) -> list[str]:                                              # pragma: no cover
        return list(self._info.get("admissible_commands", [[]])[0])
