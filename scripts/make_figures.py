"""Generate all figures + results/figures/manifest.json (+ paper/figures/CAPTIONS.md).

kind = "conceptual"   schematic, no measured data
       "structural"   drawn from the real model objects (graphs, architecture)
       "experimental" drawn ONLY from results/raw|processed (or from a real run, stated in the caption)
Every figure is written as PNG (200 dpi) and SVG.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from afcr.attribution import ArgmaxEps, make_strategy, run_attribution
from afcr.automata.benchmark48 import GROUPS, build_agent_model
from afcr.automata.dfa import DFA
from afcr.automata.nfa import EPS, ENFA, NFA
from afcr.automata.pa import ProbabilisticAutomaton
from afcr.replay import make_automaton_instance
from afcr.statistics import StackKL

OUT = ROOT / "results" / "figures"
PAPER = ROOT / "paper" / "figures"
PROC, RAW = ROOT / "results" / "processed", ROOT / "results" / "raw"
OUT.mkdir(parents=True, exist_ok=True); PAPER.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": 0.25, "figure.dpi": 100, "axes.titleweight": "bold", "axes.titlesize": 11})
GCOL = {"PLAN": "#4C78A8", "OBSERVE": "#54A24B", "TOOL": "#F58518", "MEMORY": "#B279A2", "VALIDATE": "#2AA5B0", "TERMINAL": "#8794B0"}
MCOL = {"lucb": "#2563EB", "lucb_prefix": "#0891B2", "lucb_naive_share": "#E11D48", "successive_elim": "#7C3AED", "uniform_fc": "#D97706", "random_fc": "#A16207",
        "equal_budget": "#64748B", "random_budget": "#94A3B8", "car_fixed_k": "#DB2777", "oracle": "#16A34A"}
LAB = {"lucb": "LUCB", "lucb_prefix": "LUCB + prefix reuse", "lucb_naive_share": "LUCB + naive sharing (invalid)", "successive_elim": "Successive elimination",
       "uniform_fc": "Uniform (same stop)", "random_fc": "Random (same stop)", "equal_budget": "Equal budget", "random_budget": "Random budget", "car_fixed_k": "CAR-style (K=100)", "oracle": "Oracle"}
MANIFEST: list[dict] = []



def _ntests():
    """(backend, frontend) test counts from the stored reports; '?' when the reports have not been generated."""
    import json as _j
    try:
        b = _j.loads((ROOT / "results" / "processed" / "test_report.json").read_text(encoding="utf-8"))["total"]
        f = _j.loads((ROOT / "results" / "processed" / "frontend_test_report.json").read_text(encoding="utf-8"))["numTotalTests"]
        return b, f
    except Exception:
        return "?", "?"


def summ(g):
    return json.loads((PROC / f"{g}.json").read_text())["summary"]


def rows(g):
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


def save(fig, name, title, kind, caption, source):
    for d in (OUT, PAPER):
        fig.savefig(d / f"{name}.png", dpi=200, bbox_inches="tight", facecolor="white")
        fig.savefig(d / f"{name}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    MANIFEST.append(dict(file=f"{name}.png", title=title, kind=kind, caption=caption, source=source))
    print("saved", name)


def box(ax, x, y, w, h, text, fc="#EEF2FF", ec="#4F46E5", fs=9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, p, q, text=None, color="#475569", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=13, lw=1.3, color=color, connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.06, text, fontsize=8, ha="center", color=color)


def blank(w, h, xlim, ylim):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off"); ax.grid(False)
    return fig, ax


# ------------------------------------------------------------------------------------------------ 1, 13, 14 diagrams
def fig01():
    fig, ax = blank(11.5, 5.6, (0, 11.5), (0, 5.6))
    box(ax, 0.2, 4.1, 2.3, 1.0, "Failed trajectory\n(states, actions,\noutcome Y = 0)", "#FEF3C7", "#D97706", fs=8.6)
    box(ax, 3.0, 4.1, 2.5, 1.0, "Intervention protocol\nrepair | resample\nper candidate step", "#E0F2FE", "#0284C7", fs=8.6)
    box(ax, 6.0, 4.1, 2.6, 1.0, "Replay environment\nautomaton · tool agent\n· text game", "#E0F2FE", "#0284C7", fs=8.6)
    box(ax, 9.1, 4.1, 2.2, 1.0, "Outcome evaluator\nY ∈ {0, 1}", "#E0F2FE", "#0284C7", fs=8.6)
    box(ax, 6.0, 2.2, 2.6, 1.0, "Allocation (LUCB)\nbest + strongest\nchallenger", "#EDE9FE", "#7C3AED", fs=8.6)
    box(ax, 9.1, 2.2, 2.2, 1.0, "Prefix reuse\n(exact match only)", "#DCFCE7", "#16A34A", fs=8.6)
    box(ax, 3.0, 2.2, 2.5, 1.0, "Confidence sequences\nKL balls, union bound", "#EDE9FE", "#7C3AED", fs=8.6)
    box(ax, 0.2, 2.2, 2.3, 1.0, "Stopping rule\ncertify | abstain", "#EDE9FE", "#7C3AED", fs=8.6)
    box(ax, 0.2, 0.3, 5.3, 1.0, "Result: culprit or abstention + candidate set, CIs, rollouts,\ntraces, guarantee flag", "#FEE2E2", "#E11D48", fs=8.6, bold=True)
    box(ax, 6.0, 0.3, 5.3, 1.0, "Ground truth (synthetic only): exact dynamic programming —\nplanted cause, exact mu_t, comparison with the answer", "#F1F5F9", "#64748B", fs=8.6)
    arrow(ax, (2.5, 4.6), (3.0, 4.6)); arrow(ax, (5.5, 4.6), (6.0, 4.6)); arrow(ax, (8.6, 4.6), (9.1, 4.6))
    arrow(ax, (7.3, 3.2), (7.3, 4.1), "pull arm", color="#7C3AED")
    arrow(ax, (10.2, 4.1), (10.2, 3.2), "outcome y", color="#0284C7")
    arrow(ax, (9.1, 2.7), (8.6, 2.7), color="#16A34A")
    arrow(ax, (6.0, 2.45), (5.5, 2.45), "counts", color="#7C3AED")
    arrow(ax, (5.5, 2.95), (6.0, 2.95), "intervals", color="#7C3AED")
    arrow(ax, (3.0, 2.7), (2.5, 2.7), color="#7C3AED")
    arrow(ax, (1.35, 2.2), (1.35, 1.3), color="#E11D48")
    ax.text(5.75, 5.4, "AFCR loop: pull → outcome → update → stop?", fontsize=8.5, color="#475569", ha="center")
    ax.set_title("AFCR: end-to-end system architecture", loc="left")
    save(fig, "fig01_system_architecture", "End-to-end system architecture", "conceptual",
         "A failed trajectory and an intervention protocol define candidate arms; each pull replays the agent from the intervened state and returns an outcome. Confidence sequences and the stopping rule decide when to certify or abstain, the allocation rule chooses the next arm, and valid prefix reuse supplies extra observations.",
         "scripts/make_figures.py (schematic)")


def fig13():
    fig, ax = blank(11.5, 5.2, (0, 11.5), (0, 5.2))
    cols = [("afcr.automata", ["DFA · NFA\nε-NFA", "Probabilistic\nautomaton", "LTS · Mealy\nMoore", "PDA · Turing\nmachine", "benchmark48\n(48/64/96)"], "#DBEAFE", "#2563EB"),
            ("afcr.statistics", ["Bernoulli KL", "confidence\n(4 sequences)", "complexity\n(H, T*)"], "#EDE9FE", "#7C3AED"),
            ("afcr.replay\nafcr.agents", ["BanditEnv", "AutomatonEnv", "ToolAgentEnv", "providers"], "#DCFCE7", "#16A34A"),
            ("afcr.attribution", ["targets", "strategies", "engine\n(abstention)"], "#FEF3C7", "#D97706"),
            ("afcr.experiments\nafcr.evaluation", ["suite / core", "metrics,\nstats (Holm)"], "#FCE7F3", "#DB2777"),
            ("afcr.api\nwebsite", ["FastAPI\nendpoints", "React + TypeScript\nUI"], "#FEE2E2", "#E11D48")]
    for i, (t, items, fc, ec) in enumerate(cols):
        x = 0.1 + i * 1.87
        box(ax, x, 4.0, 1.65, 0.85, t, fc, ec, fs=8, bold=True)
        for j, it in enumerate(items):
            box(ax, x, 3.1 - j * 0.66, 1.65, 0.56, it, "white", ec, fs=7.4)
    for i in range(5):
        arrow(ax, (1.75 + i * 1.87, 4.42), (1.97 + i * 1.87, 4.42))
    ax.text(0.1, 0.25, f"tests/ ({_ntests()[0]} pytest cases) · website/src/test ({_ntests()[1]} vitest cases) · scripts/ (figures, documents, deck, PDFs) · results/{{raw, processed, figures}}", fontsize=8.6, color="#475569")
    ax.set_title("Software architecture (package boundaries)", loc="left")
    save(fig, "fig13_software_architecture", "Software architecture", "structural",
         "Clear boundaries between automata, statistics, replay environments, attribution logic, experiments/evaluation and the API/website; the statistical algorithm never imports a model SDK.", "src/afcr package layout")


def fig14():
    fig, ax = blank(11, 3.6, (0, 11), (0, 3.6))
    steps = ["instance specs\n(seeded dicts)", "run_spec()\nreal replays", "raw rows\nresults/raw/*.csv", "aggregate\nWilson / bootstrap", "processed JSON\nresults/processed", "paired stats\nWilcoxon + Holm", "figures, tables,\nwebsite, deck"]
    for i, t in enumerate(steps):
        box(ax, 0.1 + i * 1.55, 1.3, 1.35, 1.0, t, "#F0F9FF" if i % 2 == 0 else "#F5F3FF", "#0284C7" if i % 2 == 0 else "#7C3AED", fs=8)
        if i:
            arrow(ax, (0.1 + i * 1.55 - 0.2, 1.8), (0.1 + i * 1.55, 1.8))
    ax.text(0.1, 0.55, "Charts are rendered from the stored files only; nothing is typed in. --aggregate-only recomputes the processed layer from the raw rows.", fontsize=9, color="#475569")
    ax.set_title("Experimental evaluation pipeline", loc="left")
    save(fig, "fig14_evaluation_pipeline", "Experimental evaluation pipeline", "conceptual",
         "Trials are plain-dict specs; every number in the paper, report, website and slides is computed from the raw CSV rows by the aggregation layer.", "src/afcr/experiments/suite.py")


def fig04():
    fig, ax = blank(8.6, 7.6, (0, 8.6), (0, 7.6))
    nodes = [(2.6, 6.5, 3.4, 0.7, "Update confidence intervals\n(running intersection)", "#EDE9FE", "#7C3AED"), (2.6, 5.3, 3.4, 0.7, "Stopping rule satisfied?\nlo_h + ε ≥ max other hi", "#FEF3C7", "#D97706"),
             (6.2, 5.3, 2.2, 0.7, "Return certified\nculprit (δ-correct)", "#DCFCE7", "#16A34A"), (2.6, 4.1, 3.4, 0.7, "Budget exhausted?", "#FEF3C7", "#D97706"),
             (6.2, 4.1, 2.2, 0.7, "ABSTAIN: best guess +\ncandidate set", "#FEE2E2", "#E11D48"), (2.6, 2.9, 3.4, 0.7, "Pick arms: unseen first, else\nempirical best h + challenger ℓ", "#EDE9FE", "#7C3AED"),
             (2.6, 1.7, 3.4, 0.7, "Replay each arm (real intervention)\n→ outcome Y ∈ {0,1}", "#E0F2FE", "#0284C7"), (2.6, 0.5, 3.4, 0.7, "Credit Y to the arm (+ exact-match\nprefix-reuse arms, if enabled)", "#DCFCE7", "#16A34A")]
    for x, y, w, h, t, fc, ec in nodes:
        box(ax, x, y, w, h, t, fc, ec, fs=8.6)
    for p, q in [((4.3, 6.5), (4.3, 6.0)), ((4.3, 5.3), (4.3, 4.8)), ((4.3, 4.1), (4.3, 3.6)), ((4.3, 2.9), (4.3, 2.4)), ((4.3, 1.7), (4.3, 1.2))]:
        arrow(ax, p, q)
    arrow(ax, (6.0, 5.65), (6.2, 5.65)); arrow(ax, (6.0, 4.45), (6.2, 4.45)); ax.text(6.02, 5.78, "yes", fontsize=8, color="#475569"); ax.text(6.02, 4.58, "yes", fontsize=8, color="#475569")
    ax.text(4.45, 4.95, "no", fontsize=8, color="#475569"); ax.text(4.45, 3.75, "no", fontsize=8, color="#475569")
    arrow(ax, (2.6, 0.85), (1.6, 0.85)); arrow(ax, (1.6, 0.85), (1.6, 6.85)); arrow(ax, (1.6, 6.85), (2.6, 6.85))
    ax.set_title("Adaptive candidate selection and stopping", loc="left")
    save(fig, "fig04_adaptive_selection_flowchart", "Adaptive candidate-selection flowchart", "conceptual",
         "One round of AFCR. The sampling rule is interchangeable: δ-correctness depends only on the confidence sequence and the stopping rule. Budget exhaustion is an abstention, never a certified answer.", "src/afcr/attribution/engine.py")


# ------------------------------------------------------------------------------------------------ 2 trajectory, 3 replay, 5 stopping
def sample_env(seed=5, eps=0.6):
    m = build_agent_model(48, eps={"PLAN_SUBGOAL": eps})
    return m, make_automaton_instance(m, np.random.default_rng(seed))


def fig02():
    m, env = sample_env()
    mu = env.true_means(); tr = env.traj; base = m.success_probability()
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    x = np.arange(1, env.n_arms + 1)
    ax.plot(x, mu, "-o", color="#2563EB", lw=2)
    ax.axhline(base, color="#D97706", ls="--", lw=1.4, label=f"baseline success {base:.2f}")
    p = env.planted_arm()
    if p is not None:
        ax.scatter([p + 1], [mu[p]], s=240, facecolors="none", edgecolors="#E11D48", lw=2.4, label="planted cause", zorder=5)
    ax.set_xticks(x); ax.set_xticklabels([f"{m.ids[tr.states[i]].replace('_', chr(10), 1)}\n→{m.sym_ids[tr.states[i]][tr.actions[i]]}" for i in range(env.n_arms)], fontsize=7)
    ax.set_ylim(0, 1); ax.set_ylabel("μ_t = P(success | repair at step t)"); ax.legend(loc="upper right")
    ax.set_title("Exact value of intervening at each step of one failed trajectory", fontsize=10.5)
    save(fig, "fig02_failed_trajectory", "Example failed agent trajectory", "experimental",
         "Exact μ_t (dynamic programming, no sampling) for one failed trajectory (seed 5, fault probability 0.6). Steps before the planted fault only exceed the baseline slightly: re-running re-rolls the fault. After the fault the state is corrupted and μ_t falls.", "AgentModel.exact_mu; seed 5")


def fig03():
    m, env = sample_env()
    arm = env.planted_arm() or 0
    det = env.replay_detail(arm, np.random.default_rng(1))
    fig, ax = blank(11, 4.6, (0, 11), (0, 4.6))
    tr = env.traj
    n = min(env.n_arms, 7)
    for i in range(n):
        s = m.ids[tr.states[i]]; a = m.sym_ids[tr.states[i]][tr.actions[i]]
        fault = bool(m.fault_mask[tr.states[i]][tr.actions[i]])
        box(ax, 0.2 + i * 1.5, 3.1, 1.35, 0.9, f"t={i + 1}\n{s.replace('_', chr(10), 1)[:20]}\n{a}", "#FEE2E2" if fault else "#F1F5F9", "#E11D48" if fault else "#64748B", fs=6.8)
        if i: arrow(ax, (0.2 + i * 1.5 - 0.15, 3.55), (0.2 + i * 1.5, 3.55))
    ax.text(0.2, 4.25, "Original run (failed)", fontsize=10, fontweight="bold", color="#E11D48")
    ax.text(0.2 + arm * 1.5, 2.75, "▲ intervene here", fontsize=8, color="#7C3AED")
    path = det["path"][:6]
    ax.text(0.2 + arm * 1.5, 2.35, f"Counterfactual replay ({'success' if det['success'] else 'failure'})", fontsize=10, fontweight="bold", color="#16A34A" if det["success"] else "#E11D48")
    for j, s in enumerate(path):
        x = 0.2 + (arm + j) * 1.5
        if x > 9.7: break
        box(ax, x, 1.2, 1.35, 0.9, f"t={s['t']}\n{s['state'].replace('_', chr(10), 1)[:20]}\n{s['action']}{' (forced)' if s['forced'] else ''}", "#EDE9FE" if s["forced"] else "#DCFCE7", "#7C3AED" if s["forced"] else "#16A34A", fs=6.8)
        if j: arrow(ax, (x - 0.15, 1.65), (x, 1.65))
    arrow(ax, (0.2 + arm * 1.5 + 0.67, 3.1), (0.2 + arm * 1.5 + 0.67, 2.1), color="#7C3AED")
    ax.text(0.2, 0.4, "Prefix t < intervention is restored exactly; the continuation is re-simulated under the same stochastic policy (a different run can end differently).", fontsize=8.5, color="#475569")
    ax.set_title("Counterfactual replay mechanism", loc="left")
    save(fig, "fig03_counterfactual_replay", "Counterfactual replay mechanism", "conceptual",
         "Illustrated with a real sampled trajectory: the original run (top) is restored up to the chosen step, one action is forced to the reference action, and the continuation (bottom) is re-simulated. One replay is one sample of the outcome distribution.", "AutomatonEnv.replay_detail; seed 5")


def fig05():
    m, env = sample_env()
    res = run_attribution(env, make_strategy("lucb"), ArgmaxEps(0.0), StackKL(), delta=0.1, budget=60000, rng=np.random.default_rng(12), history=True, history_stride=1)
    H = [h for h in res.history if "lo" in h]
    t = np.array([h["pulls_before"] for h in H]); lo = np.array([h["lo"] for h in H]); hi = np.array([h["hi"] for h in H]); mean = np.array([h["mean"] for h in H])
    h_arm = res.selected if res.selected is not None else int(np.argmax(res.means))
    others = [i for i in range(env.n_arms) if i != h_arm]
    chall = np.max(hi[:, others], axis=1)
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.plot(t, mean[:, h_arm], color="#2563EB", lw=1.2, label="mean of best arm")
    ax.fill_between(t, lo[:, h_arm], hi[:, h_arm], color="#2563EB", alpha=0.18, label="best arm interval [lo, hi]")
    ax.plot(t, lo[:, h_arm], color="#2563EB", lw=1.8, label="lo(best)")
    ax.plot(t, chall, color="#D97706", lw=1.8, label="max hi over other arms")
    ax.axvline(res.total_rollouts, color="#16A34A", ls="--", label=f"stop: separation after {res.total_rollouts} rollouts")
    ax.set_xlabel("rollouts so far"); ax.set_ylabel("probability of success"); ax.set_ylim(0.2, 0.9); ax.legend(loc="lower right", fontsize=8.5)
    ax.set_title("Confidence bounds and the stopping rule on one real run (δ = 0.1, ε = 0)")
    save(fig, "fig05_confidence_stopping", "Confidence-bound and stopping-rule illustration", "experimental",
         f"One LUCB run (seed 5, status: {res.status}). The run stops the first time the lower bound of the best arm exceeds the largest upper bound of all other arms (running-intersection intervals, x_n = ln(2Kn(n+1)/δ)).", "run_attribution(history=True); seed 5, algorithm seed 12")


# ------------------------------------------------------------------------------------------------ 6-9 automata
def draw_small(g, name, title, caption, source, pos=None, figsize=(8, 4.2), loop_dy=0.7):
    fig, ax = plt.subplots(figsize=figsize); ax.axis("off"); ax.grid(False)
    pos = pos or nx.spring_layout(g, seed=3, k=1.6)
    xs = [q[0] for q in pos.values()]; ys = [q[1] for q in pos.values()]
    nx.draw_networkx_nodes(g, pos, node_color=["#BBF7D0" if g.nodes[n].get("accepting") else "#DBEAFE" for n in g.nodes], node_size=1500,
                           edgecolors=["#111" if g.nodes[n].get("start") else "#64748B" for n in g.nodes], linewidths=[3 if g.nodes[n].get("start") else 1 for n in g.nodes], ax=ax)
    nx.draw_networkx_labels(g, pos, font_size=9, ax=ax)
    lab = {}
    for u, v, d in g.edges(data=True):
        t = str(d.get("label", "")) + (f" ({d['p']:.2f})" if "p" in d else "")
        lab[(u, v)] = (lab.get((u, v), "") + ", " + t).strip(", ")
    loops = [(u, v) for (u, v) in lab if u == v]
    plain = [(u, v) for (u, v) in lab if u != v]
    nx.draw_networkx_edges(g, pos, edgelist=plain, ax=ax, node_size=1500, arrows=True, arrowstyle="-|>", arrowsize=16, width=1.3, connectionstyle="arc3,rad=0.18")
    for (u, _v) in loops:
        x0, y0 = pos[u]
        ax.annotate("", xy=(x0 + 0.11, y0 + 0.2), xytext=(x0 - 0.11, y0 + 0.2), arrowprops=dict(arrowstyle="-|>", mutation_scale=16, lw=1.3, connectionstyle="arc3,rad=-2.4", shrinkA=0, shrinkB=0, color="black"))
    for (u, v) in lab:
        if u == v:
            ax.text(pos[u][0], pos[u][1] + loop_dy, lab[(u, v)], fontsize=8.5, color="#B91C1C", ha="center")
        else:
            ax.text((pos[u][0] + pos[v][0]) / 2, (pos[u][1] + pos[v][1]) / 2 + (0.34 if u < v else -0.34), lab[(u, v)], fontsize=8.5, color="#B91C1C", ha="center")
    ax.set_xlim(min(xs) - 0.7, max(xs) + 0.7); ax.set_ylim(min(ys) - 0.8, max(ys) + 1.35)
    ax.set_title(title, loc="left")
    save(fig, name, title, "conceptual", caption, source)


def fig06():
    d = DFA({"e", "o"}, {"a", "b"}, {("e", "a"): "o", ("o", "a"): "e", ("e", "b"): "e", ("o", "b"): "o"}, "e", {"e"})
    draw_small(d.to_networkx(), "fig06_dfa", "DFA: even number of a’s", "A total deterministic automaton (states e = even, o = odd); bold outline = start state, green = accepting. The agent model’s DFA view is the same kind of object built from the 48-state spec (most-likely successors, explicit sink).", "afcr.automata.dfa.DFA",
               pos={"e": (0.0, 0.0), "o": (2.2, 0.0)}, figsize=(7.2, 3.0))


def fig07():
    n = NFA({0, 1, 2}, {"a", "b"}, {(0, "a"): {0, 1}, (0, "b"): {0}, (1, "b"): {2}}, 0, {2})
    tr = n.run("aab")
    fig, axes = plt.subplots(1, 4, figsize=(11, 2.8))
    sets = [frozenset({0})] + [s.next_state for s in tr.steps]
    syms = ["start"] + [s.symbol for s in tr.steps]
    for ax, S, a in zip(axes, sets, syms):
        ax.axis("off"); ax.grid(False)
        for i, q in enumerate([0, 1, 2]):
            ax.add_patch(plt.Circle((i, 0), 0.38, fc="#FCD34D" if q in S else "#F1F5F9", ec="#111" if q == 2 else "#64748B", lw=3 if q == 2 else 1))
            ax.text(i, 0, f"q{q}", ha="center", va="center", fontsize=11, fontweight="bold" if q in S else "normal")
        ax.set_xlim(-0.7, 2.7); ax.set_ylim(-0.9, 0.9); ax.set_aspect("equal")
        ax.set_title(f"after “{a}”: {{{', '.join('q' + str(q) for q in sorted(S))}}}", fontsize=9)
    fig.suptitle(f"NFA active-state sets on the word aab — accepted: {tr.accepted} (ends in ab)", fontsize=11, fontweight="bold")
    save(fig, "fig07_nfa_active_sets", "NFA active-state-set example", "conceptual",
         "The NFA of words ending in “ab” run on “aab”: yellow = active states. The word is accepted because the final active set contains the accepting state q2 (thick outline). Nondeterminism here is formal, not LLM sampling.", "afcr.automata.nfa.NFA.run")


def fig08():
    e = ENFA({0, 1, 2, 3}, {"a", "b"}, {(0, EPS): {1}, (1, EPS): {2}, (1, "a"): {1}, (2, "b"): {3}}, 0, {3})
    steps = e.eps_closure_steps({0})
    g = e.to_networkx()
    fig, axes = plt.subplots(1, len(steps), figsize=(3.4 * len(steps), 2.8))
    pos = {0: (0, 0), 1: (1.4, 0), 2: (2.8, 0), 3: (4.2, 0)}
    for ax, S, k in zip(np.atleast_1d(axes), steps, range(len(steps))):
        ax.axis("off"); ax.grid(False)
        for u, v, d in g.edges(data=True):
            if u != v:
                ax.annotate("", xy=pos[v], xytext=pos[u], arrowprops=dict(arrowstyle="-|>", lw=1.1, color="#F59E0B" if d["label"] == EPS else "#64748B", ls="--" if d["label"] == EPS else "-", shrinkA=16, shrinkB=16))
                ax.text((pos[u][0] + pos[v][0]) / 2, 0.22, d["label"], ha="center", fontsize=9, color="#B45309" if d["label"] == EPS else "#334155")
        for q, (x, y) in pos.items():
            ax.add_patch(plt.Circle((x, y), 0.34, fc="#FCD34D" if q in S else "#F1F5F9", ec="#111" if q == 3 else "#64748B", lw=3 if q == 3 else 1))
            ax.text(x, y, f"q{q}", ha="center", va="center")
        ax.set_xlim(-0.6, 4.8); ax.set_ylim(-0.7, 0.7); ax.set_aspect("equal")
        ax.set_title(f"iteration {k}: {{{', '.join('q' + str(q) for q in sorted(S))}}}", fontsize=9)
    save(fig, "fig08_enfa_closure", "ε-NFA closure illustration", "conceptual",
         "Computing the ε-closure of {q0} (dashed amber = ε-moves): the set grows until a fixed point, here {q0, q1, q2}. The agent model’s heal edges are ε-moves in its ε-NFA view.", "afcr.automata.nfa.ENFA.eps_closure_steps")


def fig09():
    pa = ProbabilisticAutomaton({"s", "t", "f"}, {"go"}, {("s", "go"): {"t": 0.7, "f": 0.1, "s": 0.2}, ("t", "go"): {"t": 1.0}, ("f", "go"): {"f": 1.0}}, "s", {"t"})
    pos = {"s": (0.0, 0.0), "t": (2.4, 0.9), "f": (2.4, -0.9)}
    draw_small(pa.to_networkx(), "fig09_probabilistic_automaton", "Probabilistic automaton", "Each (state, symbol) carries a distribution over successors (edge labels). P(accept after n steps) is exact by matrix products; runs can be sampled. This is the natural formalism for a stochastic agent.", "afcr.automata.pa.ProbabilisticAutomaton", pos=pos, figsize=(7.2, 3.6), loop_dy=1.1)


def fig12():
    m = build_agent_model(48)
    pos = {}
    for gi, g in enumerate(GROUPS):
        for k, s in enumerate([s for s, sp in m.specs.items() if sp.info.group == g]):
            pos[s] = (gi * 3.0, -k * 1.2)
    fig, ax = plt.subplots(figsize=(17, 11)); ax.axis("off"); ax.grid(False)
    for s, sp in m.specs.items():
        for a, spec in sp.actions.items():
            for r, p in spec.next.items():
                (x1, y1), (x2, y2) = pos[s], pos[r]
                col = "#D62728" if spec.is_fault else ("#E8A0A0" if sp.info.role in ("fault_entry", "corridor") else "#BBBBBB")
                ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", color=col, lw=1.6 if spec.is_fault else 0.6, alpha=0.9 if spec.is_fault else 0.55, connectionstyle="arc3,rad=0.12"))
    for s, sp in m.specs.items():
        x, y = pos[s]
        ec = {"decision": "#D62728", "fault_entry": "#8B0000", "corridor": "#E57373"}.get(sp.info.role, "black")
        ax.scatter([x], [y], s=1400, c=GCOL[sp.info.group], edgecolors=ec, linewidths=3 if sp.info.role in ("decision", "fault_entry") else 1, marker="s" if sp.info.kind != "nonterminal" else "o", zorder=3)
        ax.text(x, y, s.replace("_", "\n", 1), ha="center", va="center", fontsize=5.6, zorder=4)
    for gi, g in enumerate(GROUPS):
        ax.text(gi * 3.0, 1.2, g, ha="center", fontsize=12, fontweight="bold", color=GCOL[g])
    ax.set_xlim(-1.5, 16.5); ax.set_ylim(-9.5, 2)
    ax.set_title("48-state agent-execution automaton: 8 states × 6 groups. Red = planted fault actions; red outline = decision / fault-entry states; squares = terminal (DONE_* accepting, FAIL_* rejecting)", fontsize=10, loc="left")
    save(fig, "fig12_automaton_48_states", "48-state automaton overview", "structural",
         "All 48 logical states grouped into plan / observe / tool / memory / validate / terminal; edges are all positive-probability transitions of the model, fault actions in red. Drawn from build_agent_model(48), so state count and structure are those of the tested object.", "afcr.automata.benchmark48.build_agent_model(48)")


def fig10():
    m, env = sample_env()
    rng = np.random.default_rng(3)
    arm = 0
    t0 = env.steps[arm] - 1; q0 = env.traj.states[t0]
    G = nx.DiGraph(); counts = {}
    root = (t0, q0)
    G.add_node(root); counts[root] = 0
    N = 60
    for _ in range(N):
        roll = m.simulate(rng, q0, t0, forced_action=int(m.ref_idx[q0]), record=True)
        prev = root; counts[root] += 1
        for (t, q, a) in roll.path[1:]:
            node = (t, q)
            G.add_edge(prev, node); counts[node] = counts.get(node, 0) + 1; prev = node
    orig = {(env.steps[j] - 1, env.traj.states[env.steps[j] - 1]): j for j in range(env.n_arms)}
    levels = {}
    for n in G.nodes: levels.setdefault(n[0], []).append(n)
    pos = {}
    for t, ns in levels.items():
        ns.sort(key=lambda n: (m.specs[m.ids[n[1]]].info.group, n[1]))
        for i, n in enumerate(ns): pos[n] = (t - t0, (i - (len(ns) - 1) / 2) * 1.0)
    fig, ax = plt.subplots(figsize=(11, 5.6)); ax.axis("off"); ax.grid(False)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#CBD5E1", arrows=True, arrowsize=7, width=0.8, node_size=0)
    cols = []
    for n in G.nodes:
        j = orig.get(n)
        cols.append("#16A34A" if j is not None and j != arm else "#2563EB" if n == root else GCOL[m.specs[m.ids[n[1]]].info.group])
    nx.draw_networkx_nodes(G, pos, node_size=[40 + 14 * counts[n] for n in G.nodes], node_color=cols, ax=ax, edgecolors="white", linewidths=0.8)
    ax.set_title(f"Prefix tree of {N} replays from arm 1 (step {env.steps[arm]}): green = state coincides with another candidate’s original (time, state) → potential valid reuse", loc="left", fontsize=10)
    save(fig, "fig10_prefix_tree", "Prefix-tree representation of replays", "experimental",
         f"Union of {N} real replays started at the first candidate step (node size = visit count; x = time since the intervention). Green nodes are exactly the (time, state) pairs at which another candidate would start; a rollout through a green node that also takes that candidate’s reference action is a valid sample for it (Theorem 3).", "AgentModel.simulate; seed 5, rng 3")


# ------------------------------------------------------------------------------------------------ experimental
def ci_bars(ax, x, vals, los, his, colors, width=0.7):
    ax.bar(x, vals, width, color=colors, alpha=0.9)
    ax.errorbar(x, vals, yerr=[np.array(vals) - np.array(los), np.array(his) - np.array(vals)], fmt="none", ecolor="#334155", capsize=3, lw=1.2)


def fig11():
    main = [r for r in summ("main") if r.get("kind") == "automaton"]
    order = ["lucb_prefix", "lucb", "successive_elim", "uniform_fc", "random_fc"]
    d = {r["method"]: r for r in main}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    x = np.arange(len(order))
    ci_bars(axes[0], x, [d[m]["mean_rollouts"] for m in order], [d[m]["rollouts_ci"][0] for m in order], [d[m]["rollouts_ci"][1] for m in order], [MCOL[m] for m in order])
    SL = {"lucb_prefix": "LUCB\n+ prefix", "lucb": "LUCB", "successive_elim": "Succ.\nelim.", "uniform_fc": "Uniform", "random_fc": "Random"}
    axes[0].set_xticks(x); axes[0].set_xticklabels([SL[m] for m in order], fontsize=8.5); axes[0].set_ylabel("mean rollouts (95% bootstrap CI)")
    axes[0].set_title("Rollouts (censored at the 60 000 cap)")
    axes[1].bar(x, [d[m]["certified_rate"] for m in order], color=[MCOL[m] for m in order], alpha=0.9)
    axes[1].set_xticks(x); axes[1].set_xticklabels([SL[m] for m in order], fontsize=8.5); axes[1].set_ylim(0, 1); axes[1].set_ylabel("fraction certified within budget")
    axes[1].set_title("Certification rate")
    n = d["lucb"]["n"]
    fig.suptitle(f"Uniform vs standard adaptive vs prefix-aware adaptive replay (48-state automaton, δ=0.1, n={n} paired instances)", fontsize=10.5, fontweight="bold")
    save(fig, "fig11_prefix_aware_comparison", "Prefix-aware replay comparison", "experimental",
         "Same instances, same stopping rule and δ. Means include trials that stopped at the budget cap (censored), so the gaps between methods are conservative; the right panel shows how often each method certified at all.", "results/processed/main.json (group main)")


def fig15():
    S = summ("budget_curve")
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    for m in ["lucb_prefix", "lucb", "equal_budget", "random_budget"]:
        pts = sorted([r for r in S if r["method"] == m], key=lambda r: r["B"])
        B = [r["B"] for r in pts]; a = np.array([r["accuracy"] for r in pts])
        ax.plot(B, a, "-o", color=MCOL[m], label=LAB[m], lw=2, ms=4)
        ax.fill_between(B, [r["acc_ci_lo"] for r in pts], [r["acc_ci_hi"] for r in pts], color=MCOL[m], alpha=0.12)
    ax.axhline(0.9, color="#16A34A", ls="--", lw=1.3, label="90% target"); ax.set_xscale("log"); ax.set_ylim(0.3, 1.02)
    ax.set_xlabel("rollout budget B"); ax.set_ylabel("accuracy (exact argmax)"); ax.legend(fontsize=8.5, loc="lower right")
    ax.set_title("Rollouts versus attribution accuracy (48-state automaton; Wilson 95% bands)")
    save(fig, "fig15_rollouts_vs_accuracy", "Rollouts-versus-accuracy plot", "experimental",
         "Forced-choice accuracy when only B rollouts are available (adaptive methods return their best guess if they cannot certify). The dashed 90% line is an empirical target, not the (1−δ) guarantee.", "results/processed/budget_curve.json")


def fig16():
    from matplotlib.ticker import FuncFormatter
    A = [r for r in summ("main") if r.get("kind") == "automaton" and r["method"] not in ("oracle",)]
    mk = {"lucb": "o", "lucb_prefix": "s", "successive_elim": "^", "uniform_fc": "D", "random_fc": "v", "equal_budget": "P", "lucb_naive_share": "X", "car_fixed_k": "*"}
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    for r in A:
        m = r["method"]
        ax.errorbar(max(r["mean_rollouts"], 1), r["accuracy"], xerr=[[max(r["mean_rollouts"] - r["rollouts_ci"][0], 0)], [max(r["rollouts_ci"][1] - r["mean_rollouts"], 0)]],
                    yerr=[[max(r["accuracy"] - r["acc_ci_lo"], 0)], [max(r["acc_ci_hi"] - r["accuracy"], 0)]], fmt=mk.get(m, "o"), color=MCOL[m], ms=9, capsize=3, lw=1.1, label=LAB[m], alpha=0.95)
    ax.set_xscale("log"); ax.set_xlim(1000, 80000); ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}")); ax.set_xticks([1000, 2000, 5000, 10000, 20000, 50000]); ax.minorticks_off()
    ax.set_xlabel("mean rollouts per trial (censored at the cap)"); ax.set_ylabel("accuracy (Wilson 95%)"); ax.set_ylim(-0.05, 1.08)
    ax.legend(fontsize=8, loc="lower right", frameon=True, title="method", title_fontsize=8)
    ax.set_title("Cost versus attribution quality (48-state automaton, δ = 0.1)")
    save(fig, "fig16_cost_vs_quality", "Cost-versus-attribution-quality plot", "experimental",
         "Each marker is one method (mean rollouts with 95% bootstrap CI vs accuracy with Wilson CI). The certifying adaptive methods and the uniform/random baselines overlap in accuracy, so the separation is along the cost axis. Fixed-budget methods (equal budget, CAR-style) never certify; the CAR-style point scores against the planted step with resample arms (a different target) and is not comparable.", "results/processed/main.json")


def fig17():
    S = summ("ablation")
    facs = ["confidence", "allocation", "sharing", "candidates", "epsilon"]
    fig, axes = plt.subplots(1, 5, figsize=(16, 4.4))
    for ax, f in zip(axes, facs):
        rs = [r for r in S if r["factor"] == f]
        x = np.arange(len(rs))
        ci_bars(ax, x, [r["mean_rollouts"] for r in rs], [r["rollouts_ci"][0] for r in rs], [r["rollouts_ci"][1] for r in rs], ["#E11D48" if r["level"] == "naive" else "#2563EB" for r in rs])
        ax.set_xticks(x); ax.set_xticklabels([str(r["level"]).replace("successive_elim", "SE").replace("stack_", "").replace("uniform_fc", "uniform").replace("random_fc", "random") for r in rs], fontsize=8, rotation=20)
        ax.set_title(f.capitalize(), fontsize=11)
        for xi, r in zip(x, rs):
            ax.text(xi, ax.get_ylim()[1] * 0.03, f"abst {r['abstain_rate']:.0%}", ha="center", fontsize=8, color="white", rotation=90, va="bottom")
    axes[0].set_ylabel("mean rollouts")
    fig.suptitle("Ablations on the 48-state automaton (one factor varied; 30 paired instances; labels inside bars = abstention rate)", fontsize=10.5, fontweight="bold")
    save(fig, "fig17_ablations", "Ablation comparison", "experimental",
         "Confidence sequence (stack-KL vs stack-Hoeffding vs the KL-LUCB rate), allocation rule, prefix sharing (valid vs invalid naive), candidate set (all steps vs decision states only — a domain prior) and tolerance ε. Naive sharing is shown in red: it is invalid and rarely certifies.", "results/processed/ablation.json")


def fig18():
    R = rows("main"); auto = [r for r in R if r["kind"] == "automaton"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), gridspec_kw={"wspace": 0.32})
    ms = ["lucb", "lucb_prefix", "uniform_fc", "random_fc", "lucb_naive_share"]
    cats = ["certified & correct", "certified & wrong", "abstained, guess correct", "abstained, guess wrong"]
    cc = ["#16A34A", "#E11D48", "#F59E0B", "#94A3B8"]
    bottom = np.zeros(len(ms))
    for ci_, cat in enumerate(cats):
        vals = []
        for m in ms:
            rs = [r for r in auto if r["method"] == m]
            if cat == cats[0]: vals.append(sum(1 for r in rs if r["identified"] and r["correct_exact"]))
            elif cat == cats[1]: vals.append(sum(1 for r in rs if r["identified"] and not r["correct_exact"]))
            elif cat == cats[2]: vals.append(sum(1 for r in rs if not r["identified"] and r["correct_exact"]))
            else: vals.append(sum(1 for r in rs if not r["identified"] and not r["correct_exact"]))
        axes[0].bar(range(len(ms)), vals, bottom=bottom, color=cc[ci_], label=cat); bottom += np.array(vals)
    axes[0].set_xticks(range(len(ms))); axes[0].set_xticklabels([LAB[m].replace(" (same stop)", "").replace(" + ", "\n+ ").replace(" (invalid)", "\n(invalid)") for m in ms], fontsize=7.5)
    axes[0].set_title("Outcome per method", fontsize=10); axes[0].legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False); axes[0].set_ylabel("trials")
    lu = [r for r in auto if r["method"] == "lucb"]
    g = np.maximum(np.array([r["gap"] for r in lu]), 1e-4); ab = np.array([r["abstained"] for r in lu]); rl = np.array([r["rollouts"] for r in lu])
    axes[1].scatter(g[ab == 0], rl[ab == 0], c="#2563EB", s=36, label="certified"); axes[1].scatter(g[ab == 1], rl[ab == 1], c="#F59E0B", s=46, marker="x", label="abstained (cap)")
    axes[1].set_xscale("log"); axes[1].set_yscale("log"); axes[1].set_xlabel("true gap μ* − μ(2nd)  (ties drawn at 1e-4)", fontsize=9); axes[1].set_ylabel("rollouts"); axes[1].legend(fontsize=8)
    axes[1].set_title("LUCB cost vs best–second gap", fontsize=10)
    nv = [r for r in auto if r["method"] == "lucb_naive_share"]; va = [r for r in auto if r["method"] == "lucb_prefix"]
    labs = ["valid reuse", "naive sharing"]; err = [np.mean([not r["correct_exact"] for r in va if r["identified"]]) if any(r["identified"] for r in va) else 0, np.mean([not r["correct_exact"] for r in nv if r["identified"]]) if any(r["identified"] for r in nv) else 0]
    axes[2].bar(labs, err, color=["#0891B2", "#E11D48"]); axes[2].axhline(0.1, color="#16A34A", ls="--", label="δ = 0.1"); axes[2].set_ylabel("error rate among certified trials"); axes[2].legend()
    axes[2].set_title("Why naive sharing is invalid", fontsize=10)
    fig.suptitle("Error analysis (48-state automaton, main experiment)", fontsize=11, fontweight="bold", y=1.02)
    save(fig, "fig18_error_analysis", "Error-analysis visualisation", "experimental",
         "Left: what happened in every trial. Middle: abstentions occur on instances whose best arm is (almost) exactly tied with another — there is nothing to certify, so abstaining is the correct behaviour — and cost rises as the gap shrinks. Right: sharing every rollout with all later candidates produces wrong certified answers; exact-match reuse does not.", "results/raw/main.csv")


def fig19():
    S = [r for r in summ("gap_sweep")]
    R = rows("gap_sweep")
    lb = {}
    for r in R:
        if r["method"] == "lucb" and r.get("gk_lower_bound"):
            lb.setdefault(r["gap"], []).append(r["gk_lower_bound"])
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    for m in ["lucb", "successive_elim", "uniform_fc"]:
        pts = sorted([r for r in S if r["method"] == m], key=lambda r: r["gap"])
        ax.errorbar([r["gap"] for r in pts], [r["mean_rollouts"] for r in pts], yerr=[[r["mean_rollouts"] - r["rollouts_ci"][0] for r in pts], [r["rollouts_ci"][1] - r["mean_rollouts"] for r in pts]], fmt="-o", color=MCOL[m], label=LAB[m], capsize=3)
    gs = sorted(lb); ax.plot(gs, [np.mean(lb[g]) for g in gs], "--", color="#16A34A", lw=2, label="Garivier–Kaufmann lower bound (any δ-PAC)")
    ax.set_yscale("log"); ax.set_xlabel("best − runner-up gap (bandit-arm model, K=8, δ=0.1)"); ax.set_ylabel("mean rollouts to certify"); ax.legend(fontsize=8.5)
    ax.set_title("Sample cost versus the instance-dependent lower bound")
    save(fig, "fig19_gap_sweep_lower_bound", "Sample cost vs gap and the Garivier–Kaufmann lower bound", "experimental",
         "Every measured method lies above the lower bound T*(μ)·kl(δ,1−δ) (necessarily, for δ-PAC methods); the vertical distance shows that our algorithms are far from asymptotically optimal — which is why the word ‘optimal’ is not claimed.", "results/processed/gap_sweep.json; results/raw/gap_sweep.csv (gk_lower_bound)")


def fig20():
    S = summ("stress") + [dict(r, group="delta_sweep") for r in summ("delta_sweep")]
    st = sorted(summ("stress"), key=lambda r: r["delta"])
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    d = [r["delta"] for r in st]; e = [(r["identified_error_rate"] or 0) for r in st]
    ax.plot([0, 0.55], [0, 0.55], "--", color="#D97706", label="allowed: error = δ")
    ax.errorbar(d, e, yerr=[[max(0.0, (r["identified_error_rate"] or 0) - (r["err_ci_lo"] or 0)) for r in st], [max(0.0, (r["err_ci_hi"] or 0) - (r["identified_error_rate"] or 0)) for r in st]], fmt="o", color="#E11D48", capsize=4, ms=8, label="observed (hard 2-arm instances)")
    for r in st: ax.annotate(f"n={r['n']}", (r["delta"], (r["identified_error_rate"] or 0)), textcoords="offset points", xytext=(6, 8), fontsize=8)
    ax.set_xlabel("δ"); ax.set_ylabel("error rate among certified trials"); ax.legend(fontsize=8.5); ax.set_xlim(0, 0.55); ax.set_ylim(-0.02, 0.55)
    ax.set_title("Empirical error versus δ (stress test, gap 0.06)")
    save(fig, "fig20_error_vs_delta", "Empirical error versus δ", "experimental",
         "Observed errors among certified trials on very hard 2-arm instances, with Wilson 95% intervals. Zero errors in all trials is consistent with Theorem 1 but also shows the stack bound is conservative; this is a bug-detector, not a proof.", "results/processed/stress.json")


def fig21():
    S = summ("K_sweep")
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for m in ["lucb", "successive_elim", "uniform_fc"]:
        pts = sorted([r for r in S if r["method"] == m], key=lambda r: r["K"])
        ax.errorbar([r["K"] for r in pts], [r["mean_rollouts"] for r in pts], yerr=[[r["mean_rollouts"] - r["rollouts_ci"][0] for r in pts], [r["rollouts_ci"][1] - r["mean_rollouts"] for r in pts]], fmt="-o", color=MCOL[m], label=LAB[m], capsize=3)
    from matplotlib.ticker import FuncFormatter, NullFormatter
    ax.set_xscale("log", base=2); ax.set_yscale("log"); ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}")); ax.set_xticks([4, 8, 16, 32, 64]); ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}")); ax.yaxis.set_minor_formatter(NullFormatter()); ax.set_xlabel("number of candidate steps K (gap 0.2)"); ax.set_ylabel("mean rollouts"); ax.legend(fontsize=8.5)
    ax.set_title("Effect of the number of candidates")
    save(fig, "fig21_candidates_sweep", "Effect of the number of candidate steps", "experimental",
         "Cost grows with K for every method; adaptive allocation spends its budget on the few ambiguous arms while uniform spends it on all of them.", "results/processed/K_sweep.json")


if __name__ == "__main__":
    fig01(); fig02(); fig03(); fig04(); fig05(); fig06(); fig07(); fig08(); fig09(); fig10(); fig11(); fig12(); fig13(); fig14()
    fig15(); fig16(); fig17(); fig18(); fig19(); fig20(); fig21()
    MANIFEST.sort(key=lambda m: m["file"])
    (OUT / "manifest.json").write_text(json.dumps(MANIFEST, indent=1), encoding="utf-8")
    cap = ["# Figure captions\n"] + [f"**{m['file']}** ({m['kind']}) — {m['title']}. {m['caption']} *Source:* `{m['source']}`\n" for m in MANIFEST]
    (PAPER / "CAPTIONS.md").write_text("\n".join(cap), encoding="utf-8")
    print(len(MANIFEST), "figures")
