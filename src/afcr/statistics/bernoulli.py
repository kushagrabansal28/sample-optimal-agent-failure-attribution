"""Bernoulli Kullback-Leibler divergence and the KL confidence-region inversion.

Notation: d(p, q) = p ln(p/q) + (1-p) ln((1-p)/(1-q)).

``kl_upper(p, r)`` is  max{q in [p, 1] : d(p, q) <= r}   (upper end of a KL ball)
``kl_lower(p, r)`` is  min{q in [0, p] : d(p, q) <= r}   (lower end)

Both are computed by bisection and return the *conservative* end of the final
bracket (the side where d > r), so the returned interval always contains the
exact KL ball.  ``r = +inf`` yields the trivial interval [0, 1].
"""
from __future__ import annotations

import numpy as np
from scipy.special import xlogy

_EPS = 1e-15
_ITERS = 50


def kl_bernoulli(p, q):
    """Elementwise Bernoulli KL divergence d(p, q); broadcasts like numpy."""
    p = np.asarray(p, dtype=float)
    q = np.clip(np.asarray(q, dtype=float), _EPS, 1.0 - _EPS)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = xlogy(p, p / q) + xlogy(1.0 - p, (1.0 - p) / (1.0 - q))
    return out


def kl_upper(p, r):
    """Largest q >= p with d(p, q) <= r (conservative bracket end)."""
    p = np.atleast_1d(np.asarray(p, dtype=float))
    r = np.broadcast_to(np.asarray(r, dtype=float), p.shape)
    lo = p.copy()
    hi = np.ones_like(p)
    for _ in range(_ITERS):
        mid = 0.5 * (lo + hi)
        too_far = kl_bernoulli(p, mid) > r
        hi = np.where(too_far, mid, hi)
        lo = np.where(too_far, lo, mid)
    out = np.where(np.isinf(r), 1.0, hi)
    return out


def kl_lower(p, r):
    """Smallest q <= p with d(p, q) <= r (conservative bracket end)."""
    p = np.atleast_1d(np.asarray(p, dtype=float))
    r = np.broadcast_to(np.asarray(r, dtype=float), p.shape)
    lo = np.zeros_like(p)
    hi = p.copy()
    for _ in range(_ITERS):
        mid = 0.5 * (lo + hi)
        too_far = kl_bernoulli(p, mid) > r
        lo = np.where(too_far, mid, lo)
        hi = np.where(too_far, hi, mid)
    out = np.where(np.isinf(r), 0.0, lo)
    return out


def chernoff_information(p: float, q: float) -> float:
    """Chernoff information C(p,q) = max_{a in [0,1]} [ a d(p,m_a) + (1-a) d(q,m_a) ] with m_a = a p + (1-a) q."""
    from scipy.optimize import minimize_scalar

    def neg(a: float) -> float:
        m = a * p + (1 - a) * q
        return -(a * float(kl_bernoulli(p, m)) + (1 - a) * float(kl_bernoulli(q, m)))

    res = minimize_scalar(neg, bounds=(0.0, 1.0), method="bounded", options={"xatol": 1e-12})
    return float(-res.fun)
