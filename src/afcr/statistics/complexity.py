"""Instance-dependent complexity quantities (used for analysis, plots and tests — never by the algorithms).

* ``gaps`` / ``hardness_H``  : Delta_a and H = sum_a 1 / max(Delta_a, eps/2)^2
* ``characteristic_time``    : T*(mu) of Garivier & Kaufmann (2016, Thm 1), Bernoulli arms, unique best arm
* ``gk_lower_bound``         : T*(mu) * kl(delta, 1-delta), a lower bound on E[tau] for ANY delta-PAC strategy
                               that samples independent arms one at a time (Thm 1 of that paper).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .bernoulli import kl_bernoulli


def gaps(mu) -> np.ndarray:
    """Delta_a = mu* - mu_a for a != best; Delta_best = mu* - second best."""
    mu = np.asarray(mu, dtype=float)
    order = np.argsort(-mu)
    out = mu[order[0]] - mu
    out[order[0]] = mu[order[0]] - mu[order[1]] if len(mu) > 1 else np.inf
    return out


def hardness_H(mu, eps: float = 0.0) -> float:
    d = np.maximum(gaps(mu), eps / 2.0)
    with np.errstate(divide="ignore"):
        return float(np.sum(1.0 / d ** 2))


def _I(alpha, x, y):
    """I_alpha(x, y) = alpha d(x, m) + (1-alpha) d(y, m), m = alpha x + (1-alpha) y."""
    m = alpha * x + (1.0 - alpha) * y
    return alpha * kl_bernoulli(x, m) + (1.0 - alpha) * kl_bernoulli(y, m)


def characteristic_time(mu, n_starts: int = 8, seed: int = 0) -> float:
    """T*(mu)^-1 = max_{w in simplex} min_{a != 1} (w_1 + w_a) I_{w_1/(w_1+w_a)}(mu_1, mu_a)."""
    mu = np.asarray(mu, dtype=float)
    K = len(mu)
    star = int(np.argmax(mu))
    if np.sum(mu == mu[star]) > 1:
        return float("inf")                       # no unique best arm: BAI is not identifiable
    others = [a for a in range(K) if a != star]

    def constraints_values(w):
        vals = []
        for a in others:
            tot = w[star] + w[a]
            if tot <= 1e-14:
                vals.append(0.0)
            else:
                vals.append(tot * float(_I(w[star] / tot, mu[star], mu[a])))
        return np.array(vals)

    rng = np.random.default_rng(seed)
    best = 0.0
    # variables: w (K) and t ; maximise t s.t. g_a(w) >= t, sum w = 1, w >= 0
    for i in range(n_starts):
        w0 = rng.dirichlet(np.ones(K)) if i else np.ones(K) / K
        t0 = constraints_values(w0).min()
        x0 = np.concatenate([w0, [t0]])
        cons = [
            {"type": "eq", "fun": lambda x: np.sum(x[:K]) - 1.0},
            {"type": "ineq", "fun": lambda x: constraints_values(np.clip(x[:K], 0, 1)) - x[K]},
        ]
        res = minimize(lambda x: -x[K], x0, constraints=cons, bounds=[(0, 1)] * K + [(0, None)],
                       method="SLSQP", options={"maxiter": 500, "ftol": 1e-12})
        w = np.clip(res.x[:K], 0, 1)
        w = w / w.sum()
        val = constraints_values(w).min()
        best = max(best, val)
    return float(1.0 / best) if best > 0 else float("inf")


def gk_lower_bound(mu, delta: float) -> float:
    """T*(mu) kl(delta, 1-delta): lower bound on E[tau_delta] for any delta-PAC strategy (G&K 2016, Thm 1)."""
    return characteristic_time(mu) * float(kl_bernoulli(delta, 1.0 - delta))
