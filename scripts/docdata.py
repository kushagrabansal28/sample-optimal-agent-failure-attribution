"""Single place that turns results/raw + results/processed into the numbers and markdown tables used by the documents.
Nothing here is typed-in: every figure is computed from the stored result files."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "results" / "raw", ROOT / "results" / "processed"
LABEL = {"lucb": "LUCB", "lucb_prefix": "LUCB + valid prefix reuse", "lucb_naive_share": "LUCB + naive sharing (invalid)", "successive_elim": "Successive elimination",
         "uniform_fc": "Uniform (same stopping rule)", "random_fc": "Random (same stopping rule)", "equal_budget": "Equal budget (no stopping)",
         "random_budget": "Random budget", "car_fixed_k": "CAR-style fixed K=100", "car_fixed_k500": "CAR-style fixed K=500", "oracle": "Oracle (exact means)"}


def L(m: str) -> str:
    return LABEL.get(m, m)


def load_rows(g: str) -> list[dict]:
    def conv(v):
        if v == "":
            return None
        for f in (int, float):
            try:
                return f(v)
            except ValueError:
                pass
        return v
    with (RAW / f"{g}.csv").open(newline="", encoding="utf-8") as f:
        return [{k: conv(v) for k, v in r.items()} for r in csv.DictReader(f)]


def summary(g: str) -> list[dict]:
    return json.loads((PROC / f"{g}.json").read_text(encoding="utf-8"))["summary"]


def meta() -> dict:
    return json.loads((PROC / "suite_meta.json").read_text(encoding="utf-8"))


def paired() -> list[dict]:
    return json.loads((PROC / "paired_stats.json").read_text(encoding="utf-8"))


def tests() -> dict:
    p = PROC / "test_report.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"total": 0, "passed": 0, "failed": 0}


def frontend_tests() -> dict:
    p = PROC / "frontend_test_report.json"
    if not p.exists():
        return {"total": 0, "passed": 0}
    d = json.loads(p.read_text(encoding="utf-8"))
    return {"total": d.get("numTotalTests", 0), "passed": d.get("numPassedTests", 0)}


def f(x, d=2):
    return "—" if x is None else f"{x:.{d}f}"


def pct(x, d=0):
    return "—" if x is None else f"{100 * x:.{d}f}%"


def n0(x):
    return "—" if x is None else f"{x:,.0f}"


def ci_txt(s):
    return f"{s['rollouts_ci'][0]:,.0f}–{s['rollouts_ci'][1]:,.0f}"


# ----------------------------------------------------------------------------------------- tables
def table_main_auto() -> str:
    S = {r["method"]: r for r in summary("main") if r.get("kind") == "automaton"}
    h = "| Method | n | Accuracy [Wilson 95%] | Certified | Abstained | Error among certified | Mean rollouts [95% CI] | Median |\n|---|---|---|---|---|---|---|---|\n"
    for m in ["oracle", "lucb_prefix", "lucb", "successive_elim", "uniform_fc", "random_fc", "equal_budget", "lucb_naive_share", "car_fixed_k"]:
        if m in S:
            s = S[m]
            h += f"| {L(m)} | {s['n']} | {pct(s['accuracy'])} [{pct(s['acc_ci_lo'])}, {pct(s['acc_ci_hi'])}] | {pct(s['certified_rate'])} | {pct(s['abstain_rate'])} | {pct(s['identified_error_rate'], 1)} | {n0(s['mean_rollouts'])} [{ci_txt(s)}] | {n0(s['median_rollouts'])} |\n"
    return h


def table_main_bandit() -> str:
    S = [r for r in summary("main") if r.get("kind") == "bandit"]
    h = "| Gap | Method | n | Accuracy | Certified | Error among certified | Mean rollouts [95% CI] |\n|---|---|---|---|---|---|---|\n"
    for gap in (0.1, 0.2):
        for m in ["lucb", "successive_elim", "uniform_fc", "random_fc", "equal_budget", "oracle"]:
            for s in S:
                if s["method"] == m and abs(s["gap"] - gap) < 1e-9:
                    h += f"| {gap} | {L(m)} | {s['n']} | {pct(s['accuracy'])} | {pct(s['certified_rate'])} | {pct(s['identified_error_rate'], 1)} | {n0(s['mean_rollouts'])} [{ci_txt(s)}] |\n"
    return h


def table_paired() -> str:
    h = "| Comparison (second vs first) | Pairs | Ratio of mean rollouts | Mean difference [95% bootstrap CI] | p (Wilcoxon) | p (Holm) | Significant at 0.05 |\n|---|---|---|---|---|---|---|\n"
    for r in paired():
        diff = "—" if r["mean_diff"] is None else f"{n0(r['mean_diff'])} [{n0(r['ci'][0])}, {n0(r['ci'][1])}]"
        pv = lambda p: "—" if p is None else ("<0.001" if p < 0.001 else f"{p:.3f}")
        h += f"| {L(r['b'])} vs {L(r['a'])} | {r['n']} | {f(r['ratio'])}× | {diff} | {pv(r['p'])} | {pv(r.get('p_holm'))} | {'yes' if r.get('reject_holm_0_05') else 'no'} |\n"
    return h


def table_gap_sweep() -> str:
    S, R = summary("gap_sweep"), load_rows("gap_sweep")
    lb: dict[float, list[float]] = {}
    for r in R:
        if r["method"] == "lucb" and r.get("gk_lower_bound") is not None:
            lb.setdefault(r["gap"], []).append(r["gk_lower_bound"])
    h = "| Gap | LUCB | Successive elim. | Uniform | Lower bound T*·kl(δ,1−δ) | LUCB / lower bound |\n|---|---|---|---|---|---|\n"
    for gap in sorted({s["gap"] for s in S}):
        g = {s["method"]: s for s in S if s["gap"] == gap}
        low = float(np.mean(lb[gap]))
        h += f"| {gap} | {n0(g['lucb']['mean_rollouts'])} | {n0(g['successive_elim']['mean_rollouts'])} | {n0(g['uniform_fc']['mean_rollouts'])} | {n0(low)} | {g['lucb']['mean_rollouts'] / low:.1f}× |\n"
    return h


def lb_ratio_range() -> tuple[float, float]:
    S, R = summary("gap_sweep"), load_rows("gap_sweep")
    lb: dict[float, list[float]] = {}
    for r in R:
        if r["method"] == "lucb" and r.get("gk_lower_bound") is not None:
            lb.setdefault(r["gap"], []).append(r["gk_lower_bound"])
    rat = [s["mean_rollouts"] / float(np.mean(lb[s["gap"]])) for s in S if s["method"] == "lucb"]
    return min(rat), max(rat)


def table_K() -> str:
    S = summary("K_sweep")
    h = "| K | LUCB | Successive elim. | Uniform | Uniform / LUCB |\n|---|---|---|---|---|\n"
    for K in sorted({s["K"] for s in S}):
        g = {s["method"]: s for s in S if s["K"] == K}
        h += f"| {K} | {n0(g['lucb']['mean_rollouts'])} | {n0(g['successive_elim']['mean_rollouts'])} | {n0(g['uniform_fc']['mean_rollouts'])} | {g['uniform_fc']['mean_rollouts'] / g['lucb']['mean_rollouts']:.1f}× |\n"
    return h


def table_delta() -> str:
    S = sorted(summary("delta_sweep"), key=lambda r: r["delta"])
    h = "| δ | n | Observed error among certified | Certified | Mean rollouts |\n|---|---|---|---|---|\n"
    for s in S:
        h += f"| {s['delta']} | {s['n']} | {pct(s['identified_error_rate'], 1)} | {pct(s['certified_rate'])} | {n0(s['mean_rollouts'])} |\n"
    return h


def stress_counts() -> tuple[int, int, str]:
    R = load_rows("stress")
    cert = [r for r in R if r["identified"]]
    wrong = [r for r in cert if not r["correct_exact"]]
    per = {}
    for d in sorted({r["delta"] for r in R}):
        c = [r for r in cert if r["delta"] == d]
        per[d] = (len(c), sum(1 for r in c if not r["correct_exact"]))
    return len(cert), len(wrong), "; ".join(f"δ={d}: {w}/{c}" for d, (c, w) in per.items())


def main_counts(method: str) -> tuple[int, int, int]:
    R = [r for r in load_rows("main") if r["kind"] == "automaton" and r["method"] == method]
    cert = [r for r in R if r["identified"]]
    return len(R), len(cert), sum(1 for r in cert if not r["correct_exact"])


def all_certified_counts() -> tuple[int, int]:
    """Certified trials and certified-wrong trials over all VALID guaranteed runs in every group (excludes naive sharing, fixed-budget)."""
    tot = wrong = 0
    for g in ("main", "gap_sweep", "K_sweep", "delta_sweep", "stress", "size_sweep", "eps_sweep", "ablation", "toolagent", "targets"):
        for r in load_rows(g):
            if r["guarantee"] and r["identified"] and r.get("share_override") != "naive" and r["method"] != "oracle":
                tot += 1
                wrong += 0 if r["correct_exact"] or (r.get("eps") and r["correct"]) else 1
    return tot, wrong


def table_size() -> str:
    S = summary("size_sweep")
    h = "| Logical states | Method | n | Certified | Mean rollouts [95% CI] |\n|---|---|---|---|---|\n"
    for n in sorted({s["n_states"] for s in S}):
        for m in ("lucb", "lucb_prefix", "uniform_fc"):
            for s in S:
                if s["n_states"] == n and s["method"] == m:
                    h += f"| {n} | {L(m)} | {s['n']} | {pct(s['certified_rate'])} | {n0(s['mean_rollouts'])} [{ci_txt(s)}] |\n"
    return h


def table_eps() -> str:
    S, R = summary("eps_sweep"), load_rows("eps_sweep")
    h = "| Fault prob. | mean true gap | Method | Certified | Mean rollouts [95% CI] |\n|---|---|---|---|---|\n"
    for e in sorted({s["eps_plan"] for s in S}):
        gap = float(np.mean([r["gap"] for r in R if r["eps_plan"] == e and r["method"] == "lucb"]))
        for m in ("lucb", "lucb_prefix", "uniform_fc"):
            for s in S:
                if s["eps_plan"] == e and s["method"] == m:
                    h += f"| {e} | {gap:.3f} | {L(m)} | {pct(s['certified_rate'])} | {n0(s['mean_rollouts'])} [{ci_txt(s)}] |\n"
    return h


def table_noise() -> str:
    S = sorted(summary("noise_sweep"), key=lambda r: r["recon_noise"])
    h = "| Reconstruction noise | n | Accuracy vs noisy-context argmax | Certified | Mean rollouts |\n|---|---|---|---|---|\n"
    for s in S:
        h += f"| {s['recon_noise']} | {s['n']} | {pct(s['accuracy'])} [{pct(s['acc_ci_lo'])}, {pct(s['acc_ci_hi'])}] | {pct(s['certified_rate'])} | {n0(s['mean_rollouts'])} |\n"
    return h


def table_ablation() -> str:
    S = summary("ablation")
    h = "| Factor | Level | Accuracy | Certified | Error among certified | Mean rollouts [95% CI] |\n|---|---|---|---|---|---|\n"
    for s in S:
        h += f"| {s['factor']} | {s['level']} | {pct(s['accuracy'])} | {pct(s['certified_rate'])} | {pct(s['identified_error_rate'], 1)} | {n0(s['mean_rollouts'])} [{ci_txt(s)}] |\n"
    return h


def budget_to90() -> list[dict]:
    S = summary("budget_curve")
    out = []
    for m in ("lucb_prefix", "lucb", "equal_budget", "random_budget"):
        pts = sorted([r for r in S if r["method"] == m], key=lambda r: r["B"])
        a = next((r["B"] for r in pts if r["accuracy"] >= 0.9), None)
        b = next((r["B"] for r in pts if r["acc_ci_lo"] >= 0.9), None)
        out.append(dict(method=m, b90=a, b90_lo=b))
    return out


def table_budget() -> str:
    S = summary("budget_curve")
    Bs = sorted({s["B"] for s in S})
    h = "| Method | " + " | ".join(f"B={b:,}" for b in Bs) + " |\n|---|" + "---|" * len(Bs) + "\n"
    for m in ("lucb_prefix", "lucb", "equal_budget", "random_budget"):
        d = {s["B"]: s for s in S if s["method"] == m}
        h += f"| {L(m)} | " + " | ".join(pct(d[b]["accuracy"]) for b in Bs) + " |\n"
    h += "\n| Method | Smallest B with accuracy ≥ 90% (point estimate) | … with Wilson lower bound ≥ 90% |\n|---|---|---|\n"
    for r in budget_to90():
        h += f"| {L(r['method'])} | {r['b90'] if r['b90'] else 'not reached'} | {r['b90_lo'] if r['b90_lo'] else 'not reached'} |\n"
    return h


def table_tool() -> str:
    S = summary("toolagent")
    h = "| Variant | Method | n | Accuracy (ε-optimal) | Certified | Mean rollouts [95% CI] |\n|---|---|---|---|---|---|\n"
    for s in S:
        h += f"| {s['variant']} | {L(s['method'])} | {s['n']} | {pct(s['accuracy'])} | {pct(s['certified_rate'])} | {n0(s['mean_rollouts'])} [{ci_txt(s)}] |\n"
    return h


def table_targets() -> str:
    S = summary("targets")
    h = "| Target | Method | n | Agreement with exact target | Certified | Mean rollouts |\n|---|---|---|---|---|---|\n"
    for s in S:
        h += f"| {s['target']} | {L(s['method'])} | {s['n']} | {pct(s['accuracy'])} | {pct(s['certified_rate'])} | {n0(s['mean_rollouts'])} |\n"
    return h


def headline() -> dict:
    """Numbers quoted in the abstract / summary."""
    P = {(r["a"], r["b"]): r for r in paired()}
    n_cert, n_wrong = all_certified_counts()
    sc, sw, per = stress_counts()
    nv = main_counts("lucb_naive_share")
    S = {r["method"]: r for r in summary("main") if r.get("kind") == "automaton"}
    lo, hi = lb_ratio_range()
    b = {r["method"]: r for r in budget_to90()}
    return dict(
        uni_over_lucb=P[("lucb", "uniform_fc")]["ratio"], rand_over_lucb=P[("lucb", "random_fc")]["ratio"], se_over_lucb=P[("lucb", "successive_elim")]["ratio"],
        lucb_over_prefix=P[("lucb_prefix", "lucb")]["ratio"], p_holm_max=max(r["p_holm"] for r in paired() if r.get("p_holm") is not None),
        n_pairs=P[("lucb", "uniform_fc")]["n"], cert_total=n_cert, cert_wrong=n_wrong, stress_cert=sc, stress_wrong=sw, stress_per=per,
        naive_cert=nv[1], naive_wrong=nv[2], naive_n=nv[0], lucb_cert=S["lucb"]["certified_rate"], prefix_cert=S["lucb_prefix"]["certified_rate"],
        uni_cert=S["uniform_fc"]["certified_rate"], lb_lo=lo, lb_hi=hi, b90=b, trials=meta()["trials"],
    )


if __name__ == "__main__":
    import pprint
    pprint.pprint(headline())
    print(table_main_auto()); print(table_paired()); print(table_budget()); print(table_gap_sweep())
