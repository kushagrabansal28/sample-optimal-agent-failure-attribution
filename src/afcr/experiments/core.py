"""Single-trial execution for every experiment group. A *spec* (plain dict) fully determines a trial (instance, method, seed)."""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from ..agents.toolagent import ToolAgentWorld, make_tool_world
from ..attribution import ArgmaxEps, FirstAbove, LastAbove, make_strategy, run_attribution
from ..automata.benchmark48 import build_agent_model
from ..replay import make_automaton_instance, make_gap_instance, make_toolagent_instance
from ..statistics import make_confidence
from ..statistics.complexity import gk_lower_bound

# method -> (strategy name, share mode, strategy kwargs)
METHODS = {
    "lucb": ("lucb", "none", {}),
    "lucb_prefix": ("lucb", "valid", {}),
    "lucb_naive_share": ("lucb", "naive", {}),
    "successive_elim": ("successive_elim", "none", {}),
    "successive_elim_prefix": ("successive_elim", "valid", {}),
    "uniform_fc": ("uniform_fc", "none", {}),
    "random_fc": ("random_fc", "none", {}),
    "equal_budget": ("equal_budget", "none", {}),
    "random_budget": ("random_budget", "none", {}),
    "car_fixed_k": ("car_fixed_k", "none", {"k_per_arm": 100}),
    "car_fixed_k500": ("car_fixed_k", "none", {"k_per_arm": 500}),
    "oracle": ("oracle", "none", {}),
}


@lru_cache(maxsize=64)
def _model(n_states: int, eps_plan: float, noise: float):
    return build_agent_model(n_states, eps={"PLAN_SUBGOAL": eps_plan}, noise=noise)


def build_env(sp: dict):
    kind, seed = sp["kind"], sp["seed"]
    if kind == "bandit":
        return make_gap_instance(sp.get("K", 8), sp.get("gap", 0.2), best=sp.get("best", 0.8), n_near=sp.get("n_near", 1))
    if kind == "automaton":
        m = _model(sp.get("n_states", 48), sp.get("eps_plan", 0.6), sp.get("env_noise", 1.0))
        return make_automaton_instance(m, np.random.default_rng(seed), intervention=sp.get("intervention", "repair"),
                                       candidates=sp.get("candidates", "all"), state_reconstruction_noise=sp.get("recon_noise", 0.0))
    if kind == "toolagent":
        det = sp.get("deterministic", False)
        w = (ToolAgentWorld(deterministic=True, fault_phase=sp.get("fault_phase", 4)) if det
             else make_tool_world(seed, **sp.get("world", {})))
        return make_toolagent_instance(w, np.random.default_rng(seed), intervention=sp.get("intervention", "repair"))
    raise ValueError(f"unknown env kind {kind!r}")


def _target(sp: dict):
    t = sp.get("target", "argmax")
    if t == "argmax":
        return ArgmaxEps(sp.get("eps", 0.0))
    if t == "first_above":
        return FirstAbove(sp["theta"])
    if t == "last_above":
        return LastAbove(sp["theta"])
    raise ValueError(t)


def _truth(mu: np.ndarray, sp: dict) -> int:
    t = sp.get("target", "argmax")
    if t == "argmax":
        return int(np.argmax(mu))
    th = sp["theta"]
    idx = np.flatnonzero(mu >= th)
    if len(idx) == 0:
        return -1
    return int(idx[0] if t == "first_above" else idx[-1])


def run_spec(sp: dict) -> dict:
    env = build_env(sp)
    mu = env.true_means()
    method = sp["method"]
    strat, share, kw = METHODS[method]
    tgt = _target(sp)
    conf = make_confidence(sp.get("conf", "stack_kl"))
    if sp.get("share_override"):
        share = sp["share_override"]
    res = run_attribution(env, make_strategy(strat, **kw), tgt, conf, delta=sp.get("delta", 0.1), budget=sp.get("budget", 40000),
                          rng=np.random.default_rng(sp["seed"] + 7), share=share)
    truth = _truth(mu, sp)
    ans = res.answer if res.answer is not None else -1
    if res.certified_none:
        ans = -1
    eps_c = sp.get("eps", 0.0) if sp.get("target", "argmax") == "argmax" else 0.0
    srt = np.sort(mu)[::-1]
    gap = float(srt[0] - srt[1]) if len(srt) > 1 else float("nan")
    mu_ans = float(mu[ans]) if ans >= 0 else float("nan")
    correct_exact = int(ans == truth)
    correct_eps = int(ans >= 0 and mu[ans] >= srt[0] - eps_c - 1e-12) if sp.get("target", "argmax") == "argmax" else correct_exact
    row = dict(sp.get("tags", {}))
    row.update({k: v for k, v in sp.items() if k not in ("tags", "world")})
    row.update(method=method, n_arms=env.n_arms, status=res.status, identified=int(res.status in ("identified", "oracle")),
               abstained=int(res.status == "budget_exhausted"), answer=int(ans), truth=int(truth), gap=gap, mu_max=float(srt[0]), mu_ans=mu_ans,
               correct_exact=correct_exact, correct=correct_eps, rollouts=res.total_rollouts, steps=res.total_steps,
               shared=int(sum(res.shared_obs)), wall=round(res.wall_seconds, 4), guarantee=int(res.guarantee_applies),
               planted_is_argmax=int(env.planted_arm() == int(np.argmax(mu))) if env.planted_arm() is not None else -1,
               traj_len=getattr(getattr(env, "traj", None), "T", env.n_arms))
    if sp["kind"] == "bandit" and sp.get("with_lb"):
        row["gk_lower_bound"] = float(gk_lower_bound(mu, sp.get("delta", 0.1)))
    return row
