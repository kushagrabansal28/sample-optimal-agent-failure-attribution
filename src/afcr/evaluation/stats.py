"""Paired comparisons and multiple-comparison correction (used on raw trial rows; nothing is hard-coded)."""
from __future__ import annotations

import numpy as np
from scipy.stats import wilcoxon

from .metrics import bootstrap_ci


def paired_compare(rows: list[dict], a: str, b: str, metric: str = "rollouts", key: str = "seed", n_boot: int = 2000) -> dict:
    """Paired by trial seed (same instance). Reports mean(b - a), bootstrap CI, ratio of means and a Wilcoxon signed-rank p-value.
    NOTE: ``rollouts`` is censored at the budget cap for abstained trials, so these differences are conservative."""
    ra = {r[key]: r[metric] for r in rows if r["method"] == a}
    rb = {r[key]: r[metric] for r in rows if r["method"] == b}
    ids = sorted(set(ra) & set(rb))
    if len(ids) < 3:
        return dict(a=a, b=b, n=len(ids), mean_diff=None, ci=None, ratio=None, p=None)
    x = np.array([ra[i] for i in ids], float)
    y = np.array([rb[i] for i in ids], float)
    d = y - x
    ci = bootstrap_ci(d, n=n_boot)
    try:
        p = float(wilcoxon(d, zero_method="wilcox", alternative="two-sided").pvalue) if np.any(d != 0) else 1.0
    except ValueError:
        p = 1.0
    return dict(a=a, b=b, n=len(ids), mean_a=float(x.mean()), mean_b=float(y.mean()), mean_diff=float(d.mean()), ci=list(ci),
                ratio=float(y.mean() / x.mean()) if x.mean() > 0 else None, p=p)


def holm(pvals: list[float | None], alpha: float = 0.05) -> list[dict]:
    """Holm-Bonferroni step-down. Returns adjusted p-values and rejection flags in the input order (None stays None)."""
    idx = [i for i, p in enumerate(pvals) if p is not None]
    order = sorted(idx, key=lambda i: pvals[i])
    m = len(order)
    adj = {}
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return [dict(p=pvals[i], p_holm=adj.get(i), reject=(adj[i] < alpha) if i in adj else None) for i in range(len(pvals))]
