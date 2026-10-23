"""Confidence sequences for Bernoulli arms.  THE single source of truth for every bound used by AFCR.

All sequences expose ``bounds(successes, counts, K, delta, rounds)`` -> (lower, upper) arrays and the flags

* ``anytime_valid``      the bound holds *simultaneously for all n and all arms* w.p. >= 1 - delta
                         (needed for a valid stopping rule under adaptive sampling);
* ``valid_under_sharing``the correctness proof does not rely on one-pull-per-observation, so the
                         sequence may be used when an arm receives extra (matched) observations
                         from other arms' rollouts (paper Thm 3).

Provided sequences
------------------
StackKL (primary, "ours")
    Per-arm KL ball with radius x_n / n where x_n = ln(2 K n (n+1) / delta).
    Proof sketch (full proof: paper Thm 1): reward-stack model + Chernoff
    P(n d(mu_hat_n, mu) >= x, mu_hat_n on one side of mu) <= e^{-x} for each side, then
    sum_{a<=K} sum_{n>=1} 2 e^{-x_n} = delta * sum_n 1/(n(n+1)) = delta.
StackHoeffding
    Same union bound with Hoeffding radius sqrt(x_n / (2 n)); looser than StackKL (Pinsker).
KLLUCBRate (literature baseline)
    Exploration rate beta(t, delta) = ln(k1 K t^alpha / delta) + ln ln(k1 K t^alpha / delta),
    alpha > 1, k1 > 2e + 1 + e/(alpha-1) + (e+1)/(alpha-1)^2, from Kaufmann & Kalyanakrishnan,
    COLT 2013, Theorem 1; KL balls  N_a d(p_a, q) <= beta.  Proven for *independent arms with one
    observation per pull* and t = round index of KL-LUCB, so it is NOT used with prefix sharing.
WilsonFixed (non-sequential; CAR-style baseline)
    Wilson score interval at a fixed level.  Valid for a *single, pre-specified* sample size only.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from .bernoulli import kl_lower, kl_upper

__all__ = [
    "ConfidenceSequence", "StackKL", "StackHoeffding", "KLLUCBRate", "WilsonFixed",
    "make_confidence", "KLLUCB_K1_MIN",
]


def KLLUCB_K1_MIN(alpha: float) -> float:
    """Smallest admissible k1 (strict inequality) from K&K 2013 Thm 1 for KL-LUCB."""
    if alpha <= 1.0:
        raise ValueError("alpha must be > 1")
    return 2 * math.e + 1 + math.e / (alpha - 1) + (math.e + 1) / (alpha - 1) ** 2


class ConfidenceSequence(ABC):
    name: str = "abstract"
    anytime_valid: bool = False
    valid_under_sharing: bool = False
    uses_rounds: bool = False        # True if the bound depends on the global round index (all arms must be refreshed each round)

    @abstractmethod
    def bounds(self, successes, counts, *, K: int, delta: float, rounds: int | None = None):
        """Return (lower, upper) arrays; arms with zero observations get [0, 1]."""

    @staticmethod
    def _validate(delta: float, K: int) -> None:
        if not (0.0 < delta < 1.0):
            raise ValueError(f"delta must lie in (0, 1), got {delta!r}")
        if K < 1:
            raise ValueError("K must be >= 1")


def _prep(successes, counts):
    s = np.atleast_1d(np.asarray(successes, dtype=float))
    n = np.atleast_1d(np.asarray(counts, dtype=float))
    if s.shape != n.shape:
        raise ValueError("successes and counts must have the same shape")
    if np.any(n < 0) or np.any(s < 0) or np.any(s > n):
        raise ValueError("require 0 <= successes <= counts")
    return s, n


def _kl_s(p, q):
    q = min(max(q, 1e-15), 1 - 1e-15)
    a = p * math.log(p / q) if p > 0 else 0.0
    b = (1 - p) * math.log((1 - p) / (1 - q)) if p < 1 else 0.0
    return a + b


def _scalar_ball(p, r, iters=34):
    """Conservative KL ball [lo, hi] around p with radius r (pure-python fast path; same bracket logic as kl_lower/kl_upper)."""
    lo_, hi_ = p, 1.0
    for _ in range(iters):
        mid = 0.5 * (lo_ + hi_)
        if _kl_s(p, mid) > r:
            hi_ = mid
        else:
            lo_ = mid
    up = hi_
    lo_, hi_ = 0.0, p
    for _ in range(iters):
        mid = 0.5 * (lo_ + hi_)
        if _kl_s(p, mid) > r:
            lo_ = mid
        else:
            hi_ = mid
    return lo_, up


class StackKL(ConfidenceSequence):
    name = "stack_kl"
    anytime_valid = True
    valid_under_sharing = True

    def bounds(self, successes, counts, *, K, delta, rounds=None):
        self._validate(delta, K)
        s, n = _prep(successes, counts)
        if len(n) <= 24:                                   # fast scalar path (identical semantics)
            lo = np.zeros(len(n)); hi = np.ones(len(n))
            for i in range(len(n)):
                ni = n[i]
                if ni > 0:
                    r = math.log(2.0 * K * ni * (ni + 1.0) / delta) / ni
                    lo[i], hi[i] = _scalar_ball(s[i] / ni, r)
            return lo, hi
        with np.errstate(divide="ignore", invalid="ignore"):
            p = np.where(n > 0, s / np.maximum(n, 1), 0.0)
            x = np.log(2.0 * K * n * (n + 1.0) / delta)
            r = np.where(n > 0, x / np.maximum(n, 1), np.inf)
        lo = kl_lower(p, r)
        hi = kl_upper(p, r)
        lo = np.where(n > 0, lo, 0.0)
        hi = np.where(n > 0, hi, 1.0)
        return lo, hi


class StackHoeffding(ConfidenceSequence):
    name = "stack_hoeffding"
    anytime_valid = True
    valid_under_sharing = True

    def bounds(self, successes, counts, *, K, delta, rounds=None):
        self._validate(delta, K)
        s, n = _prep(successes, counts)
        with np.errstate(divide="ignore", invalid="ignore"):
            p = np.where(n > 0, s / np.maximum(n, 1), 0.0)
            x = np.log(2.0 * K * n * (n + 1.0) / delta)
            rad = np.where(n > 0, np.sqrt(x / (2.0 * np.maximum(n, 1))), np.inf)
        lo = np.where(n > 0, np.clip(p - rad, 0.0, 1.0), 0.0)
        hi = np.where(n > 0, np.clip(p + rad, 0.0, 1.0), 1.0)
        return lo, hi


@dataclass
class KLLUCBRate(ConfidenceSequence):
    """KL confidence regions with the KL-LUCB exploration rate (K&K 2013, Thm 1)."""

    alpha: float = 1.1
    k1: float | None = None
    name: str = "kl_lucb_rate"
    anytime_valid: bool = True        # as a function of the round index t, for KL-LUCB's sampling scheme
    valid_under_sharing: bool = False
    uses_rounds: bool = True

    def __post_init__(self):
        kmin = KLLUCB_K1_MIN(self.alpha)
        if self.k1 is None:
            self.k1 = math.ceil(kmin * 10) / 10 + 0.1       # strictly above the threshold
        if self.k1 <= kmin:
            raise ValueError(f"k1 must exceed {kmin:.4f} for alpha={self.alpha}")

    def beta(self, t: int, K: int, delta: float) -> float:
        t = max(int(t), 1)
        inner = math.log(self.k1 * K * t ** self.alpha / delta)
        return inner + math.log(max(inner, 1e-12))

    def bounds(self, successes, counts, *, K, delta, rounds=None):
        self._validate(delta, K)
        if rounds is None:
            raise ValueError("KLLUCBRate needs the round index t (rounds=...)")
        s, n = _prep(successes, counts)
        beta = self.beta(rounds, K, delta)
        with np.errstate(divide="ignore", invalid="ignore"):
            p = np.where(n > 0, s / np.maximum(n, 1), 0.0)
            r = np.where(n > 0, beta / np.maximum(n, 1), np.inf)
        lo = np.where(n > 0, kl_lower(p, r), 0.0)
        hi = np.where(n > 0, kl_upper(p, r), 1.0)
        return lo, hi


@dataclass
class WilsonFixed(ConfidenceSequence):
    """Wilson score interval at a fixed two-sided level (NOT anytime-valid)."""

    level: float = 0.95
    name: str = "wilson_fixed"
    anytime_valid: bool = False
    valid_under_sharing: bool = False

    def bounds(self, successes, counts, *, K, delta, rounds=None):
        s, n = _prep(successes, counts)
        z = float(norm.ppf(0.5 + self.level / 2.0))
        with np.errstate(divide="ignore", invalid="ignore"):
            nn = np.maximum(n, 1)
            p = s / nn
            denom = 1.0 + z * z / nn
            centre = (p + z * z / (2 * nn)) / denom
            half = z * np.sqrt(p * (1 - p) / nn + z * z / (4 * nn * nn)) / denom
        lo = np.where(n > 0, np.clip(centre - half, 0.0, 1.0), 0.0)
        hi = np.where(n > 0, np.clip(centre + half, 0.0, 1.0), 1.0)
        return lo, hi


def make_confidence(name: str, **kw) -> ConfidenceSequence:
    table = {
        "stack_kl": StackKL, "stack_hoeffding": StackHoeffding,
        "kl_lucb_rate": KLLUCBRate, "wilson_fixed": WilsonFixed,
    }
    if name not in table:
        raise ValueError(f"unknown confidence sequence {name!r}; choose from {sorted(table)}")
    return table[name](**kw)
