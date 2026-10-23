import math

import numpy as np
import pytest

from afcr.statistics import (
    KLLUCBRate, StackHoeffding, StackKL, WilsonFixed, characteristic_time, chernoff_information,
    gaps, gk_lower_bound, hardness_H, kl_bernoulli, kl_lower, kl_upper, make_confidence,
)
from afcr.statistics.confidence import KLLUCB_K1_MIN


def test_kl_basic_values():
    assert kl_bernoulli(0.5, 0.5) == pytest.approx(0.0, abs=1e-12)
    assert float(kl_bernoulli(0.0, 0.5)) == pytest.approx(math.log(2), rel=1e-9)
    assert float(kl_bernoulli(1.0, 0.25)) == pytest.approx(math.log(4), rel=1e-9)
    # Pinsker: d(p,q) >= 2 (p-q)^2
    p, q = np.meshgrid(np.linspace(0, 1, 21), np.linspace(0.01, 0.99, 21))
    assert np.all(kl_bernoulli(p, q) >= 2 * (p - q) ** 2 - 1e-12)


@pytest.mark.parametrize("p", [0.0, 0.2, 0.5, 0.97, 1.0])
@pytest.mark.parametrize("r", [0.01, 0.5, 3.0])
def test_kl_inversion_brackets_the_ball(p, r):
    lo, hi = float(kl_lower(p, r)[0]), float(kl_upper(p, r)[0])
    assert 0.0 <= lo <= p <= hi <= 1.0
    # conservative: the bracket end is at (or just beyond) the exact KL ball boundary
    if hi < 1.0:
        assert float(kl_bernoulli(p, hi)) >= r - 1e-9
    if lo > 0.0:
        assert float(kl_bernoulli(p, lo)) >= r - 1e-9


def test_kl_inversion_infinite_radius_is_trivial():
    assert kl_lower(0.3, np.inf)[0] == 0.0 and kl_upper(0.3, np.inf)[0] == 1.0


@pytest.mark.parametrize("cls", [StackKL, StackHoeffding])
def test_confidence_edge_cases(cls):
    c = cls()
    lo, hi = c.bounds([0, 0, 5, 10], [0, 10, 10, 10], K=4, delta=0.1)
    assert lo[0] == 0.0 and hi[0] == 1.0                       # no data -> trivial
    assert lo[1] == 0.0 and 0 < hi[1] < 1                      # all failures
    assert hi[3] == pytest.approx(1.0, abs=1e-9) and lo[3] > 0.2   # all successes
    assert np.all(lo <= hi)


def test_confidence_shrinks_with_n_and_grows_with_confidence():
    c = StackKL()
    w = []
    for n in (10, 100, 1000, 10000):
        lo, hi = c.bounds([n // 2], [n], K=5, delta=0.05)
        w.append(hi[0] - lo[0])
    assert w == sorted(w, reverse=True)
    lo1, hi1 = c.bounds([50], [100], K=5, delta=0.5)
    lo2, hi2 = c.bounds([50], [100], K=5, delta=0.001)
    assert (hi2 - lo2) > (hi1 - lo1)


def test_stack_kl_never_wider_than_hoeffding():
    kl, ho = StackKL(), StackHoeffding()
    for n in (5, 50, 500):
        for s in (0, n // 4, n // 2, n):
            a = kl.bounds([s], [n], K=8, delta=0.05)
            b = ho.bounds([s], [n], K=8, delta=0.05)
            assert a[1][0] <= b[1][0] + 1e-6 and a[0][0] >= b[0][0] - 1e-6


@pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5])
def test_delta_validation(bad):
    with pytest.raises(ValueError):
        StackKL().bounds([1], [2], K=2, delta=bad)


def test_input_validation():
    with pytest.raises(ValueError):
        StackKL().bounds([3], [2], K=2, delta=0.1)
    with pytest.raises(ValueError):
        StackKL().bounds([1, 2], [2], K=2, delta=0.1)
    with pytest.raises(ValueError):
        make_confidence("nope")


def test_kl_lucb_rate_matches_published_constants():
    # K&K 2013 Thm 1: alpha=1.1 requires k1 > 2e+1+e/0.1+(e+1)/0.01  (~ 405.4)
    assert KLLUCB_K1_MIN(1.1) == pytest.approx(2 * math.e + 1 + math.e / 0.1 + (math.e + 1) / 0.01)
    assert 405.0 < KLLUCB_K1_MIN(1.1) < 406.0
    with pytest.raises(ValueError):
        KLLUCBRate(alpha=1.1, k1=100.0)                       # below the admissible threshold
    with pytest.raises(ValueError):
        KLLUCBRate(alpha=1.0)
    c = KLLUCBRate()
    b1, b2 = c.beta(10, 5, 0.1), c.beta(1000, 5, 0.1)
    assert b2 > b1 > 0
    with pytest.raises(ValueError):
        c.bounds([1], [2], K=2, delta=0.1)                    # needs rounds


def test_wilson_is_flagged_non_sequential():
    w = WilsonFixed(0.95)
    assert not w.anytime_valid
    lo, hi = w.bounds([5, 0, 10], [10, 10, 10], K=3, delta=0.1)
    assert lo[0] < 0.5 < hi[0] and lo[1] == 0.0 and hi[2] == pytest.approx(1.0)


def test_flags_for_sharing_validity():
    assert StackKL().valid_under_sharing and StackHoeffding().valid_under_sharing
    assert not KLLUCBRate().valid_under_sharing and not WilsonFixed().valid_under_sharing


def test_gaps_and_hardness():
    mu = [0.9, 0.7, 0.5]
    g = gaps(mu)
    assert g == pytest.approx([0.2, 0.2, 0.4])
    assert hardness_H(mu) == pytest.approx(1 / 0.04 + 1 / 0.04 + 1 / 0.16)
    assert hardness_H(mu, eps=1.0) == pytest.approx(3 / 0.25)


def test_characteristic_time_two_arms_is_inverse_chernoff():
    for p, q in [(0.9, 0.5), (0.6, 0.4), (0.3, 0.1)]:
        t = characteristic_time([p, q])
        assert t == pytest.approx(1.0 / chernoff_information(p, q), rel=2e-3)


def test_characteristic_time_monotone_in_gap_and_inf_for_ties():
    easy = characteristic_time([0.9, 0.3, 0.3])
    hard = characteristic_time([0.9, 0.8, 0.3])
    assert hard > easy > 0
    assert characteristic_time([0.5, 0.5, 0.2]) == float("inf")
    assert gk_lower_bound([0.9, 0.5, 0.4], 0.05) > gk_lower_bound([0.9, 0.5, 0.4], 0.2) > 0


@pytest.mark.slow
@pytest.mark.parametrize("cls", [StackKL, StackHoeffding])
def test_confidence_sequence_coverage_under_adaptive_sampling(cls):
    """Empirical check (NOT a proof): an adversarially adaptive sampler must not push the
    simultaneous miscoverage above delta.  The sampler concentrates pulls on whichever arm
    currently looks *worst covered* (smallest interval-width ratio), a stress case for naive bounds."""
    rng = np.random.default_rng(123)
    K, delta, horizon, trials = 4, 0.1, 400, 400
    mu = np.array([0.5, 0.5, 0.52, 0.1])
    c = cls()
    misses = 0
    for _ in range(trials):
        s = np.zeros(K); n = np.zeros(K)
        bad = False
        for t in range(horizon):
            lo, hi = c.bounds(s, n, K=K, delta=delta)
            if np.any(mu < lo - 1e-12) or np.any(mu > hi + 1e-12):
                bad = True
                break
            # adaptive rule: pull the arm with the widest interval among those whose mean looks extreme
            a = int(np.argmax(np.where(n == 0, 9, (hi - lo))))
            if n.sum() > 20 and rng.random() < 0.5:
                a = int(np.argmax(s / np.maximum(n, 1)))
            s[a] += rng.random() < mu[a]
            n[a] += 1
        misses += bad
    rate = misses / trials
    assert rate <= delta + 3 * math.sqrt(delta * (1 - delta) / trials)
