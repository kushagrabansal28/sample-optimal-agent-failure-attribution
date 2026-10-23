import numpy as np
import pytest

from afcr.agents import (OpenAICompatProvider, RecordingProvider, ScriptedProvider, ToolAgentWorld, make_tool_world, safe_calc)
from afcr.attribution import ArgmaxEps, make_strategy, run_attribution
from afcr.benchmarks import (ALFWorldGame, BenchmarkUnavailable, HotpotQAGame, LLMTextAgent, TextGameReplayEnv, exact_match, normalize,
                             toy_fixture)
from afcr.replay import make_toolagent_instance
from afcr.statistics import StackKL


def test_safe_calc_rejects_code_and_allows_arithmetic():
    assert safe_calc("3*4+5") == 17 and safe_calc("2*3+-1") == 5
    for bad in ("__import__('os')", "a+1", "2**3", "open('x')"):
        with pytest.raises((ValueError, SyntaxError)):
            safe_calc(bad)


def test_tool_world_dp_matches_monte_carlo():
    w = make_tool_world(1)
    rng = np.random.default_rng(0)
    n = 5000
    k = sum(w.success(w.simulate(rng, w.initial(), 0, record=False)[1]) for _ in range(n))
    p = w.success_probability()
    assert abs(k / n - p) < 4 * np.sqrt(p * (1 - p) / n)


def test_tool_world_kernels_are_distributions():
    w = make_tool_world(2)
    tr = w.sample_failed(np.random.default_rng(1))
    for s in tr.states[:-1]:
        acts = w.actions(s)
        assert abs(sum(p for p, _ in acts.values()) - 1) < 1e-9
        for _, kern in acts.values():
            assert abs(sum(p for p, _ in kern) - 1) < 1e-9


def test_deterministic_variant_has_unique_culprit_and_is_deterministic():
    w = ToolAgentWorld(deterministic=True, fault_phase=4)
    tr = w.sample_failed(np.random.default_rng(0))
    mu = w.exact_mu(tr)
    assert set(np.unique(mu)) <= {0.0, 1.0} and mu.sum() == 1 and int(np.argmax(mu)) + 1 == tr.planted_cause
    env = make_toolagent_instance(w, np.random.default_rng(0))
    r1 = env.pull(env.planted_arm(), np.random.default_rng(1)).outcome
    r2 = env.pull(env.planted_arm(), np.random.default_rng(2)).outcome
    assert r1 == r2 == 1


@pytest.mark.parametrize("phase", [0, 1, 4, 5])
def test_deterministic_planted_fault_each_type(phase):
    w = ToolAgentWorld(deterministic=True, fault_phase=phase)
    tr = w.sample_failed(np.random.default_rng(0))
    assert not tr.success and len(tr.faults) == 1
    assert int(np.argmax(w.exact_mu(tr))) + 1 == tr.planted_cause


def test_attribution_on_tool_agent_finds_good_culprit():
    w = make_tool_world(1)
    env = make_toolagent_instance(w, np.random.default_rng(3))
    mu = env.true_means()
    r = run_attribution(env, make_strategy("lucb"), ArgmaxEps(0.02), StackKL(), delta=0.1, budget=40000,
                        rng=np.random.default_rng(0), share="valid")
    assert r.status == "identified" and mu[r.selected] >= mu.max() - 0.02 and r.guarantee_applies


def _collect_shared(env, src, dst, n, seed=0):
    rng = np.random.default_rng(seed)
    vals, naive = [], []
    for _ in range(n):
        res = env.pull(src, rng)
        if dst in res.shared_arms:
            vals.append(res.outcome)
        if dst in res.naive_shared_arms:
            naive.append(res.outcome)
    return np.array(vals), np.array(naive)


@pytest.mark.slow
def test_theorem3_matched_observations_unbiased_and_naive_biased_automaton():
    from afcr.automata.benchmark48 import build_agent_model
    from afcr.replay import make_automaton_instance
    m = build_agent_model(48, eps={"PLAN_SUBGOAL": 0.6})
    env = make_automaton_instance(m, np.random.default_rng(5))
    mu = env.true_means()
    dst = env.planted_arm()
    vals, _ = _collect_shared(env, 0, dst, 6000)
    assert len(vals) > 500
    se = np.sqrt(mu[dst] * (1 - mu[dst]) / len(vals))
    assert abs(vals.mean() - mu[dst]) < 4.5 * se
    biased = []
    for j in range(1, env.n_arms):
        _, nv = _collect_shared(env, 0, j, 1500, seed=j)
        if len(nv):
            biased.append(abs(nv.mean() - mu[j]) > 4 * np.sqrt(0.25 / len(nv)))
    assert any(biased)


@pytest.mark.slow
def test_theorem3_unbiased_on_tool_agent():
    w = make_tool_world(1)
    env = make_toolagent_instance(w, np.random.default_rng(3))
    mu = env.true_means()
    checked = 0
    for dst in range(1, env.n_arms):
        vals, _ = _collect_shared(env, 0, dst, 3000, seed=dst)
        if len(vals) >= 300:
            se = np.sqrt(max(mu[dst] * (1 - mu[dst]), 1e-4) / len(vals))
            assert abs(vals.mean() - mu[dst]) < 4.5 * se + 1e-9
            checked += 1
    assert checked >= 1


def test_providers():
    p = ScriptedProvider(lambda prompt, seed, temp: f"echo:{seed}")
    rec = RecordingProvider(p)
    assert rec.complete("x", seed=3) == "echo:3" and rec.complete("x", seed=3) == "echo:3" and len(rec.log) == 1
    with pytest.raises(RuntimeError):
        OpenAICompatProvider("m", api_key_env="DEFINITELY_UNSET_KEY_VAR").complete("hi")


def test_hotpot_game_and_evaluator():
    assert normalize("The  Paris!") == "paris" and exact_match("paris.", "Paris")
    g = HotpotQAGame(toy_fixture())
    assert "Eiffel" in g.reset(0)
    o, done, ok = g.step("search: capital of France")
    assert not done and "France" in o
    _, done, ok = g.step("finish: paris")
    assert done and ok
    g.reset(1)
    assert g.step("finish: Frank Herbert")[2] is False
    g.reset(0)
    assert "invalid" in g.step("dance")[0]
    with pytest.raises(BenchmarkUnavailable):
        HotpotQAGame.from_file("no_such_file.json")


def test_alfworld_unavailable_is_reported_cleanly():
    with pytest.raises(BenchmarkUnavailable):
        ALFWorldGame("config.yaml")


def _scripted_agent():
    def fn(prompt, seed, temp):
        if "search:" not in prompt.split("History:")[1]:
            return "search: capital France Eiffel"
        return "finish: Paris" if np.random.default_rng(seed).random() < 0.5 else "finish: Berlin"
    return LLMTextAgent(ScriptedProvider(fn), temperature=0.7, max_steps=6)


def test_text_game_replay_env_with_mock_agent_is_not_a_benchmark_result():
    game, agent = HotpotQAGame(toy_fixture()), _scripted_agent()
    ep = None
    for s in range(60):
        e = agent.run(game, 0, np.random.default_rng(s))
        if not e.success and len(e.actions) >= 2:
            ep = e
            break
    assert ep is not None
    env = TextGameReplayEnv(game, agent, ep, intervention="resample")
    assert env.n_arms == len(ep.actions) and env.sharing_valid
    out = [env.pull(1, np.random.default_rng(i)).outcome for i in range(300)]
    assert 0.3 < np.mean(out) < 0.7                       # step 2 re-draws the 50/50 answer
    r = run_attribution(env, make_strategy("lucb"), ArgmaxEps(0.05), StackKL(), delta=0.2, budget=3000,
                        rng=np.random.default_rng(0), share="valid")
    assert r.total_rollouts <= 3000
    with pytest.raises(ValueError):
        TextGameReplayEnv(game, agent, ep, intervention="repair")
