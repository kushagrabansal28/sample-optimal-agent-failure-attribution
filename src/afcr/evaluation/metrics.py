"""Metrics computed ONLY from raw per-trial rows (dicts) - never from hard-coded numbers."""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from ..automata.pa import wilson_interval


def bootstrap_ci(x, stat=np.mean, n=1000, level=0.95, seed=0):
    x = np.asarray(x, float)
    if len(x) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), (n, len(x)))
    v = np.array([stat(x[i]) for i in idx])
    a = (1 - level) / 2
    return float(np.quantile(v, a)), float(np.quantile(v, 1 - a))


def summarize(rows, by=("method",)):
    g = defaultdict(list)
    for r in rows:
        g[tuple(r[k] for k in by)].append(r)
    out = []
    for key, rs in g.items():
        n = len(rs)
        c = sum(r["correct"] for r in rs)
        idn = [r for r in rs if r["identified"]]
        wrong = sum(1 for r in idn if not r["correct"])
        ro = np.array([r["rollouts"] for r in rs], float)
        lo, hi = wilson_interval(c, n)
        wl, wh = wilson_interval(wrong, len(idn)) if idn else (float("nan"), float("nan"))
        d = dict(zip(by, key))
        has_ab = all("abstained" in r for r in rs)
        ab = (sum(int(r["abstained"]) for r in rs) / n) if has_ab else 1 - len(idn) / n    # abstention = budget exhausted without certification
        d.update(n=n, accuracy=c / n, acc_ci_lo=lo, acc_ci_hi=hi, abstain_rate=ab, certified_rate=len(idn) / n,
                 identified_error_rate=(wrong / len(idn)) if idn else float("nan"), err_ci_lo=wl, err_ci_hi=wh,
                 mean_rollouts=float(ro.mean()), median_rollouts=float(np.median(ro)),
                 p90_rollouts=float(np.quantile(ro, 0.9)), rollouts_ci=bootstrap_ci(ro))
        d = {k: (None if isinstance(v, float) and v != v else v) for k, v in d.items()}
        out.append(d)
    return out
