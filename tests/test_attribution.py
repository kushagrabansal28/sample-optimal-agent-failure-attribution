import numpy as np
import pytest

from afcr.attribution import ArgmaxEps, FirstAbove, LastAbove, make_strategy, run_attribution
from afcr.automata.benchmark48 import build_agent_model
from afcr.evaluation.metrics import summarize
from afcr.replay import BanditEnv, make_automaton_instance, make_gap_instance
from afcr.statistics import KLLUCBRate, StackKL


def run(env, strat="lucb", target=None, conf=None, delta=0.1, budget=100000, seed=0, share="none", **kw):
    return run_attribution(env, make_strategy(strat, **kw), target or ArgmaxEps(0), conf or StackKL(), delta=delta,
                           budget=budget, rng=np.random.default_rng(seed), share=share)


def test_deterministic_planted_culprit():
    r = run(BanditEnv([0, 0, 1, 0, 0]), budget=5000)
    assert r.status == "identified" and r.selected == 2 and r.guarantee_applies


def test_ranking_with_different_probabilities():
    r = run(BanditEnv([0.2, 0.5, 0.8, 0.35]))
    assert r.selected == 2 and r.means[2] > r.means[1]


def test_tied_best_abstains_not_fabricates():
    r = run(BanditEnv([0.7, 0.7, 0.2]), budget=3000)
    assert r.status == "budget_exhausted" and r.selected is None and not r.guarantee_applies
    assert {0, 1} <= set(r.candidate_set)


def test_epsilon_resolves_ties():
    r = run(BanditEnv([0.7, 0.7, 0.2]), target=ArgmaxEps(0.1), budget=20000)
    assert r.status == "identified" and r.selected in (0, 1)


def test_budget_exhaustion_accounting():
    r = run(BanditEnv([0.5, 0.51, 0.5]), budget=137)
    assert r.total_rollouts == 137 == sum(r.own_pulls) and r.status == "budget_exhausted"


def test_validation_errors():
    env = BanditEnv([0.2, 0.9])
    for d in (0, 1, -1, 2):
        with pytest.raises(ValueError):
            run(env, delta=d)
    with pytest.raises(ValueError):
        run(env, budget=-1)
    with pytest.raises(ValueError):
        run(env, share="bogus")
    with pytest.raises(ValueError):
        run(env, conf=KLLUCBRate(), share="valid")
    with pytest.raises(ValueError):
        make_strategy("nope")


def test_reproducible_with_seed():
    env = make_gap_instance(5, 0.2, best=0.8)
    a, b, c = run(env, seed=3), run(env, seed=3), run(env, seed=4)
    assert a.counts == b.counts and a.total_rollouts == b.total_rollouts and a.counts != c.counts


def test_rollout_accounting_and_stopping_rule_consistency():
    r = run(make_gap_instance(6, 0.25, best=0.8))
    assert r.total_rollouts == sum(r.own_pulls) == sum(r.counts) and r.shared_obs == [0] * 6
    h = r.selected
    assert r.lo[h] > max(r.hi[a] for a in range(6) if a != h)


def test_adaptive_beats_uniform_on_average():
    env = make_gap_instance(8, 0.2, best=0.8)
    l = np.mean([run(env, "lucb", seed=s).total_rollouts for s in range(8)])
    u = np.mean([run(env, "uniform_fc", seed=s).total_rollouts for s in range(8)])
    assert l < u


def test_threshold_targets_exact():
    env = BanditEnv([0.05, 0.1, 0.9, 0.85, 0.1])
    assert run(env, target=FirstAbove(0.5), budget=20000).selected == 2
    assert run(env, target=LastAbove(0.5), budget=20000).selected == 3
    assert run(BanditEnv([0.1, 0.2]), target=FirstAbove(0.5), budget=20000).certified_none


def test_fixed_budget_car_and_oracle():
    env = BanditEnv([0.2, 0.8, 0.3])
    r = run(env, "equal_budget", budget=300)
    assert r.status == "fixed_budget_done" and r.total_rollouts == 300 and not r.guarantee_applies
    assert max(r.own_pulls) - min(r.own_pulls) <= 1
    car = run(env, "car_fixed_k", budget=10 ** 6, k_per_arm=20)
    assert car.total_rollouts == 60 and not car.guarantee_applies
    o = run(env, "oracle")
    assert o.selected == 1 and o.total_rollouts == 0


def test_prefix_sharing_valid_and_no_invalid_sharing():
    m = build_agent_model(48, eps={"PLAN_SUBGOAL": 0.6})
    env = make_automaton_instance(m, np.random.default_rng(5))
    a, b = run(env, budget=40000, share="none"), run(env, budget=40000, share="valid")
    assert a.selected == b.selected == int(np.argmax(env.true_means())) and sum(b.shared_obs) > 0
    assert b.total_rollouts < a.total_rollouts and b.guarantee_applies
    rng = np.random.default_rng(0)
    for arm in range(env.n_arms):
        for _ in range(20):
            assert all(j > arm for j in env.pull(arm, rng).shared_arms)
    assert not run(env, budget=2000, share="naive").guarantee_applies


def test_sharing_disabled_under_reconstruction_noise():
    m = build_agent_model(48)
    env = make_automaton_instance(m, np.random.default_rng(1), state_reconstruction_noise=0.2)
    assert not env.sharing_valid
    r = run(env, budget=500, share="valid")
    assert sum(r.shared_obs) == 0 and "disabled" in r.guarantee_note


def test_prefix_reachability_last_step_shares_nothing():
    m = build_agent_model(48)
    env = make_automaton_instance(m, np.random.default_rng(2))
    assert env.pull(env.n_arms - 1, np.random.default_rng(0)).shared_arms == ()


@pytest.mark.slow
def test_empirical_error_rate_below_delta():
    delta, trials, wrong = 0.1, 150, 0
    env = make_gap_instance(5, 0.15, best=0.7)
    for s in range(trials):
        r = run(env, delta=delta, seed=1000 + s, budget=200000)
        wrong += r.status == "identified" and r.selected != env.planted_arm()
    assert wrong / trials <= delta + 3 * np.sqrt(delta * 0.9 / trials)


def test_metrics_computed_from_raw_results():
    rows = [dict(method="a", correct=1, identified=1, rollouts=10), dict(method="a", correct=0, identified=1, rollouts=30)]
    s = summarize(rows)[0]
    assert s["accuracy"] == 0.5 and s["mean_rollouts"] == 20
