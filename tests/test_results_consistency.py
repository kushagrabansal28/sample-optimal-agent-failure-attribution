"""Reported metrics must be computed from raw results, and the stored experiments must behave as the theory predicts.

These tests read results/raw/*.csv and results/processed/*.json (produced by `python -m afcr.experiments.suite`).
They are skipped when the results have not been generated.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from afcr.experiments.suite import ALL, BY, aggregate, load_rows, paired_block
from afcr.evaluation.metrics import summarize

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "results" / "raw", ROOT / "results" / "processed"
pytestmark = pytest.mark.skipif(not (RAW / "main.csv").exists(), reason="run the experiment suite first")


def _stored(g):
    return json.loads((PROC / f"{g}.json").read_text(encoding="utf-8"))["summary"]


def _close(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (list, tuple)):
        return all(_close(x, y) for x, y in zip(a, b)) and len(a) == len(b)
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
    return a == b


@pytest.mark.parametrize("group", ALL)
def test_processed_summaries_are_recomputable_from_raw_rows(group):
    rows = load_rows(RAW / f"{group}.csv")
    fresh = aggregate(group, rows)
    stored = _stored(group)
    assert len(fresh) == len(stored)
    for f, s in zip(fresh, stored):
        for k, v in s.items():
            fv = f.get(k)
            if isinstance(fv, float) and fv != fv:
                fv = None
            if isinstance(fv, tuple):
                fv = list(fv)
            assert _close(fv, v), (group, k, fv, v)


def test_paired_statistics_are_recomputable_from_raw_rows():
    fresh = paired_block(load_rows(RAW / "main.csv"))
    stored = json.loads((PROC / "paired_stats.json").read_text(encoding="utf-8"))
    assert len(fresh) == len(stored) == 4
    for f, s in zip(fresh, stored):
        assert (f["a"], f["b"], f["n"]) == (s["a"], s["b"], s["n"])
        assert _close(f["ratio"], s["ratio"]) and _close(f["p"], s["p"]) and _close(f["p_holm"], s["p_holm"])


@pytest.mark.parametrize("group", ALL)
def test_raw_rows_are_internally_consistent(group):
    rows = load_rows(RAW / f"{group}.csv")
    assert rows, group
    for r in rows:
        assert r["rollouts"] >= 0
        assert r["identified"] in (0, 1) and r["abstained"] in (0, 1)
        assert not (r["identified"] and r["abstained"])                    # a trial cannot be both certified and abstained
        if r["abstained"]:
            assert r["status"] == "budget_exhausted"
        if r["identified"] and r["guarantee"]:
            assert r["status"] == "identified"


def test_no_wrong_certified_answer_in_guaranteed_runs():
    """Empirical consistency with Theorem 1 (a bug detector, not a proof)."""
    wrong = total = 0
    for g in ("main", "gap_sweep", "K_sweep", "delta_sweep", "stress", "size_sweep", "eps_sweep", "ablation", "toolagent", "targets"):
        for r in load_rows(RAW / f"{g}.csv"):
            if r["guarantee"] and r["identified"] and r.get("share_override") != "naive" and r["method"] != "oracle":
                total += 1
                wrong += 0 if (r["correct_exact"] or (r.get("eps") and r["correct"])) else 1
    assert total > 1000
    assert wrong == 0


def test_sample_complexity_scales_with_the_gap():
    """Smaller best-vs-runner-up gap => more rollouts, for every method (stored gap sweep)."""
    S = _stored("gap_sweep")
    for m in ("lucb", "successive_elim", "uniform_fc"):
        pts = sorted([s for s in S if s["method"] == m], key=lambda s: s["gap"])
        cost = [s["mean_rollouts"] for s in pts]
        assert all(a > b for a, b in zip(cost, cost[1:])), (m, cost)


def test_cost_grows_roughly_like_inverse_gap_squared_for_uniform():
    S = {s["gap"]: s["mean_rollouts"] for s in _stored("gap_sweep") if s["method"] == "uniform_fc"}
    slope = np.polyfit(np.log(list(S.keys())), np.log(list(S.values())), 1)[0]
    assert -3.2 < slope < -1.3                                              # theory: ~ gap^-2 up to log factors


def test_every_method_respects_the_lower_bound_on_average():
    rows = [r for r in load_rows(RAW / "gap_sweep.csv") if r["identified"] and r.get("gk_lower_bound")]
    by = {}
    for r in rows:
        by.setdefault((r["method"], r["gap"]), []).append(r)
    for (m, gap), rs in by.items():
        assert np.mean([r["rollouts"] for r in rs]) > np.mean([r["gk_lower_bound"] for r in rs]), (m, gap)


def test_adaptive_beats_uniform_in_every_gap_and_k_setting():
    for g, key in (("gap_sweep", "gap"), ("K_sweep", "K")):
        S = _stored(g)
        for v in {s[key] for s in S}:
            d = {s["method"]: s["mean_rollouts"] for s in S if s[key] == v}
            assert d["lucb"] < d["uniform_fc"], (g, v, d)


def test_summarize_matches_manual_computation_on_raw_rows():
    rows = [r for r in load_rows(RAW / "main.csv") if r["kind"] == "automaton"]
    s = {x["method"]: x for x in summarize(rows)}["lucb"]
    mine = [r for r in rows if r["method"] == "lucb"]
    assert s["n"] == len(mine)
    assert s["accuracy"] == pytest.approx(sum(r["correct"] for r in mine) / len(mine))
    assert s["mean_rollouts"] == pytest.approx(np.mean([r["rollouts"] for r in mine]))
    assert s["abstain_rate"] == pytest.approx(sum(r["abstained"] for r in mine) / len(mine))
