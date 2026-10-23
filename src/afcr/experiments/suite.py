"""The full synthetic experiment suite.  python -m afcr.experiments.suite [--groups main,gap_sweep,...] [--trials 30] [--workers 6]

Writes   results/raw/<group>.csv           raw per-trial rows
         results/processed/<group>.json    aggregates (Wilson / bootstrap CIs) computed from the raw rows
         results/processed/paired_stats.json  paired comparisons with Holm correction
Everything is SYNTHETIC (bandit-arm model, 48/64/96-state automaton, Stage-B tool agent). No ALFWorld / HotpotQA results.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ..evaluation.metrics import summarize
from ..evaluation.stats import holm, paired_compare
from .core import run_spec

ROOT = Path(__file__).resolve().parents[3]
RAW, PROC = ROOT / "results" / "raw", ROOT / "results" / "processed"

MAIN_AUTO_METHODS = ["lucb", "lucb_prefix", "successive_elim", "uniform_fc", "random_fc", "equal_budget", "lucb_naive_share", "car_fixed_k", "oracle"]


def seeds(base, n):
    return range(base, base + n)


def group_specs(name: str, n: int) -> list[dict]:
    S: list[dict] = []
    add = S.append
    if name == "main":
        for m in MAIN_AUTO_METHODS:
            for s in seeds(20_000, n):
                b = 3000 if m == "equal_budget" else 6000 if m == "lucb_naive_share" else 60000
                add(dict(kind="automaton", n_states=48, eps_plan=0.6, method=m, seed=s, budget=b,
                         intervention="resample" if m == "car_fixed_k" else "repair", tags={"group": name}))
        for gap in (0.1, 0.2):
            for m in ("lucb", "successive_elim", "uniform_fc", "random_fc", "equal_budget", "oracle"):
                for s in seeds(10_000, 2 * n):
                    add(dict(kind="bandit", K=8, gap=gap, method=m, seed=s, budget=3000 if m == "equal_budget" else 60000, with_lb=True, tags={"group": name}))
    elif name == "gap_sweep":
        for gap in (0.05, 0.1, 0.15, 0.2, 0.3):
            for m in ("lucb", "successive_elim", "uniform_fc"):
                for s in seeds(30_000, n):
                    add(dict(kind="bandit", K=8, gap=gap, method=m, seed=s, budget=150000, with_lb=True, tags={"group": name}))
    elif name == "K_sweep":
        for K in (4, 8, 16, 32, 64):
            for m in ("lucb", "successive_elim", "uniform_fc"):
                for s in seeds(31_000, n):
                    add(dict(kind="bandit", K=K, gap=0.2, method=m, seed=s, budget=150000, with_lb=True, tags={"group": name}))
    elif name == "delta_sweep":
        for d in (0.01, 0.05, 0.1, 0.2, 0.4):
            for s in seeds(32_000, 2 * n):
                add(dict(kind="bandit", K=8, gap=0.15, method="lucb", delta=d, seed=s, budget=150000, tags={"group": name}))
    elif name == "stress":                       # hard 2-arm instances where errors are possible: tests the guarantee itself
        for d in (0.1, 0.3, 0.5):
            for s in seeds(33_000, 10 * n):
                add(dict(kind="bandit", K=2, gap=0.06, best=0.55, method="lucb", delta=d, seed=s, budget=200000, tags={"group": name}))
    elif name == "size_sweep":
        for ns in (48, 64, 96):
            for m in ("lucb", "lucb_prefix", "uniform_fc"):
                for s in seeds(40_000, n):
                    add(dict(kind="automaton", n_states=ns, eps_plan=0.6, method=m, seed=s, budget=60000, tags={"group": name}))
    elif name == "eps_sweep":
        for e in (0.3, 0.45, 0.6, 0.8):
            for m in ("lucb", "lucb_prefix", "uniform_fc"):
                for s in seeds(41_000, n):
                    add(dict(kind="automaton", n_states=48, eps_plan=e, method=m, seed=s, budget=60000, tags={"group": name}))
    elif name == "noise_sweep":
        for r in (0.0, 0.1, 0.25, 0.5):
            for s in seeds(42_000, n):
                add(dict(kind="automaton", n_states=48, eps_plan=0.6, method="lucb_prefix", recon_noise=r, seed=s, budget=60000, tags={"group": name}))
    elif name == "ablation":
        for conf in ("stack_kl", "stack_hoeffding", "kl_lucb_rate"):
            for s in seeds(43_000, n):
                add(dict(kind="automaton", eps_plan=0.6, method="lucb", conf=conf, seed=s, budget=60000, tags={"group": name, "factor": "confidence", "level": conf}))
        for m in ("lucb", "successive_elim", "uniform_fc", "random_fc"):
            for s in seeds(43_000, n):
                add(dict(kind="automaton", eps_plan=0.6, method=m, seed=s, budget=60000, tags={"group": name, "factor": "allocation", "level": m}))
        for share in ("none", "valid", "naive"):
            for s in seeds(43_000, n):
                add(dict(kind="automaton", eps_plan=0.6, method="lucb", share_override=share, seed=s, budget=6000 if share == "naive" else 60000,
                         tags={"group": name, "factor": "sharing", "level": share}))
        for cand in ("all", "decision"):
            for s in seeds(43_000, n):
                add(dict(kind="automaton", eps_plan=0.6, method="lucb", candidates=cand, seed=s, budget=60000, tags={"group": name, "factor": "candidates", "level": cand}))
        for eps in (0.0, 0.02, 0.05):
            for s in seeds(43_000, n):
                add(dict(kind="automaton", eps_plan=0.6, method="lucb", eps=eps, seed=s, budget=60000, tags={"group": name, "factor": "epsilon", "level": str(eps)}))
    elif name == "budget_curve":
        for B in (100, 200, 500, 1000, 2000, 5000, 10000, 20000):
            for m in ("lucb", "lucb_prefix", "equal_budget", "random_budget"):
                for s in seeds(44_000, 2 * n):
                    add(dict(kind="automaton", eps_plan=0.6, method=m, seed=s, budget=B, tags={"group": name, "B": B}))
    elif name == "toolagent":
        for m in ("lucb", "lucb_prefix", "uniform_fc", "equal_budget", "oracle"):
            for s in seeds(50_000, n):
                add(dict(kind="toolagent", method=m, seed=s, eps=0.03, budget=3000 if m == "equal_budget" else 15000, tags={"group": name, "variant": "stochastic"}))
        for fp in (0, 1, 4, 5):
            for m in ("lucb", "uniform_fc"):
                add(dict(kind="toolagent", deterministic=True, fault_phase=fp, method=m, seed=0, budget=2000, tags={"group": name, "variant": f"deterministic_phase{fp}"}))
    elif name == "targets":
        for m, tgt in (("lucb", "last_above"), ("car_fixed_k", "last_above"), ("car_fixed_k500", "last_above")):
            for s in seeds(60_000, n):
                add(dict(kind="automaton", eps_plan=0.6, intervention="resample", target=tgt, theta=0.45, method=m, seed=s, budget=60000, tags={"group": name, "target": "last_above(0.45), resample arms"}))
        for m in ("lucb", "uniform_fc"):
            for s in seeds(61_000, n):
                add(dict(kind="automaton", eps_plan=0.6, intervention="repair", target="first_above", theta=0.6, method=m, seed=s, budget=60000, tags={"group": name, "target": "first_above(0.60), repair arms"}))
    else:
        raise ValueError(name)
    return S


ALL = ["main", "gap_sweep", "K_sweep", "delta_sweep", "stress", "size_sweep", "eps_sweep", "noise_sweep", "ablation", "budget_curve", "toolagent", "targets"]
BY = {"main": None, "gap_sweep": ("kind", "gap", "method"), "K_sweep": ("K", "method"), "delta_sweep": ("delta",), "stress": ("delta",),
      "size_sweep": ("n_states", "method"), "eps_sweep": ("eps_plan", "method"), "noise_sweep": ("recon_noise",),
      "ablation": ("factor", "level"), "budget_curve": ("B", "method"), "toolagent": ("variant", "method"), "targets": ("target", "method")}


def write_csv(path: Path, rows: list[dict]):
    keys = sorted({k for r in rows for k in r})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)


def load_rows(path: Path) -> list[dict]:
    def conv(v: str):
        if v == "":
            return None
        for f in (int, float):
            try:
                return f(v)
            except ValueError:
                pass
        return v
    with path.open(newline="", encoding="utf-8") as f:
        return [{k: conv(v) for k, v in r.items()} for r in csv.DictReader(f)]


def clean(x):
    if isinstance(x, tuple):
        return [clean(i) for i in x]
    if isinstance(x, float) and x != x:
        return None
    return x


def aggregate(group: str, rows: list[dict]):
    by = BY[group]
    if group == "main":
        out = []
        for kind, b in (("automaton", ("method",)), ("bandit", ("method", "gap"))):
            sub = [r for r in rows if r["kind"] == kind]
            for s in summarize(sub, b):
                s["kind"] = kind; out.append(s)
        return out
    return summarize(rows, by)


def paired_block(rows: list[dict]) -> list[dict]:
    auto = [r for r in rows if r["kind"] == "automaton"]
    pairs = [("lucb", "uniform_fc"), ("lucb", "random_fc"), ("lucb", "successive_elim"), ("lucb_prefix", "lucb")]
    res = [paired_compare(auto, a, b) for a, b in pairs]
    adj = holm([r["p"] for r in res])
    for r, a in zip(res, adj):
        r.update(p_holm=a["p_holm"], reject_holm_0_05=a["reject"])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", default=",".join(ALL))
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--workers", type=int, default=min(6, (os.cpu_count() or 2) - 1))
    ap.add_argument("--aggregate-only", action="store_true", help="recompute results/processed from results/raw without running trials")
    ap.add_argument("--config", help="JSON file with {trials, workers, groups} (see configs/suite_default.json); CLI flags still override it")
    a = ap.parse_args()
    if a.config:
        cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
        defaults = {"trials": 30, "workers": min(6, (os.cpu_count() or 2) - 1), "groups": ",".join(ALL)}
        if a.trials == defaults["trials"] and "trials" in cfg:
            a.trials = int(cfg["trials"])
        if a.workers == defaults["workers"] and "workers" in cfg:
            a.workers = int(cfg["workers"])
        if a.groups == defaults["groups"] and "groups" in cfg:
            a.groups = ",".join(cfg["groups"])
    if a.aggregate_only:
        for g in a.groups.split(","):
            rows = load_rows(RAW / f"{g}.csv")
            agg = [{k: clean(v) for k, v in s.items()} for s in aggregate(g, rows)]
            (PROC / f"{g}.json").write_text(json.dumps({"group": g, "n_trials_rows": len(rows), "summary": agg}, indent=1))
            if g == "main":
                (PROC / "paired_stats.json").write_text(json.dumps(paired_block(rows), indent=1))
            print(f"[{g}] re-aggregated {len(rows)} rows")
        return
    RAW.mkdir(parents=True, exist_ok=True); PROC.mkdir(parents=True, exist_ok=True)
    meta = dict(trials=a.trials, groups={}, note="SYNTHETIC only (bandit-arm, automaton, tool-agent). NOT ALFWorld/HotpotQA.")
    with ProcessPoolExecutor(a.workers) as ex:
        for g in a.groups.split(","):
            specs = group_specs(g, a.trials)
            t0 = time.time()
            rows = list(ex.map(run_spec, specs, chunksize=2))
            write_csv(RAW / f"{g}.csv", rows)
            agg = [{k: clean(v) for k, v in s.items()} for s in aggregate(g, rows)]
            (PROC / f"{g}.json").write_text(json.dumps({"group": g, "n_trials_rows": len(rows), "summary": agg}, indent=1))
            if g == "main":
                (PROC / "paired_stats.json").write_text(json.dumps(paired_block(rows), indent=1))
            meta["groups"][g] = dict(rows=len(rows), wall_seconds=round(time.time() - t0, 1))
            print(f"[{g}] {len(rows)} rows in {time.time() - t0:.0f}s", flush=True)
    meta["delta_default"] = 0.1
    (PROC / "suite_meta.json").write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
