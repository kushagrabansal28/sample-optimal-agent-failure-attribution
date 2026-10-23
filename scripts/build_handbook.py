"""Write report/handbook.md and report/AFCR_Complete_Handbook.pdf: the long, beginner-level handbook and demonstration manual.

Every number in it comes from a real run of the code in this repository (results/processed, a live engine run, real traces of every machine).
    python scripts/build_handbook.py            # needs report/screens/demo/*.png (node scripts/demo_screens.mjs and demo_screens2.mjs)
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
P = ROOT / "results" / "processed"
J = lambda n: json.loads((P / f"{n}.json").read_text(encoding="utf-8"))
main, paired, gap, kswp, dsw, szs, abl, bud, noise, tool, tgt = (J(n)["summary"] if n not in ("paired_stats",) else J(n) for n in
    ("main", "paired_stats", "gap_sweep", "K_sweep", "delta_sweep", "size_sweep", "ablation", "budget_curve", "noise_sweep", "toolagent", "targets"))
meta, tests, fe = J("suite_meta"), J("test_report"), J("frontend_test_report")
A = {s["method"]: s for s in main if s["kind"] == "automaton"}
AB = {(s["factor"], str(s["level"])): s for s in abl}
rows_total = sum(v["rows"] for v in meta["groups"].values())
pc = lambda x: f"{100 * x:.0f} %"
man = {m["file"]: m for m in json.loads((ROOT / "results" / "figures" / "manifest.json").read_text(encoding="utf-8"))}

# ------------------------------------------------------------------------------------------------ real computations
from afcr.api import lab
from afcr.attribution.algorithms import LUCB, UniformFC
from afcr.attribution.engine import run_attribution
from afcr.attribution.targets import ArgmaxEps
from afcr.automata.benchmark48 import build_agent_model
from afcr.replay.automaton_env import make_automaton_instance
from afcr.statistics.bernoulli import kl_bernoulli
from afcr.statistics.confidence import StackKL

model = build_agent_model(48, eps={"PLAN_SUBGOAL": 0.6})
env = make_automaton_instance(model, np.random.default_rng(5))
runk = lambda **kw: run_attribution(env, kw.pop("s", LUCB()), ArgmaxEps(0.0), StackKL(), delta=0.1, budget=20000, rng=np.random.default_rng(12), **kw)
res = runk(history=True, history_stride=1)
res_valid, res_naive, res_uni = runk(share="valid"), runk(share="naive"), runk(s=UniformFC())
mu, labs, T = env.true_means(), env.arm_labels, env.n_arms
H = res.history
tr = env.traj
traj_rows = "\n".join(f"| {i + 1} | `{model.ids[tr.states[i]]}` | `{model.sym_ids[tr.states[i]][tr.actions[i]]}` | {'**fault action**' if model.fault_mask[tr.states[i]][tr.actions[i]] else ''} |" for i in range(tr.T))
est_rows = "\n".join(f"| {labs[i]} | {mu[i]:.3f} | {res.means[i]:.3f} | [{res.lo[i]:.3f}, {res.hi[i]:.3f}] | {int(res.counts[i]):,} |" for i in range(T))
pick = [0, 1, 2, 9, 99, 499, 1999, len(H) - 1]
hist_rows = "\n".join(f"| {H[i]['round']} | {H[i]['pulls_before']:,} | {', '.join(str(int(c)) for c in H[i]['counts'])} | {', '.join(f'{x:.2f}' for x in H[i]['mean'])} | [{H[i]['lo'][3]:.2f}, {H[i]['hi'][3]:.2f}] | {max(H[i]['hi'][j] for j in range(T) if j != 3):.2f} | {'**stop**' if H[i]['stop'] else 'continue'} |" for i in pick)
V = model.value_table()
sub = model.ids.index("PLAN_SUBGOAL")

# worked confidence interval and the "peeking" simulation
n0, s0 = 30, 18
lo, hi = StackKL().bounds(np.array([s0]), np.array([n0]), K=1, delta=0.1)
hoeff = (s0 / n0 - np.sqrt(np.log(2 / 0.1) / (2 * n0)), s0 / n0 + np.sqrt(np.log(2 / 0.1) / (2 * n0)))
rng = np.random.default_rng(3)
flips = rng.random((4000, 400)) < 0.5
cs = np.cumsum(flips, axis=1)
n = np.arange(1, 401)
phat = cs / n
naive_wrong = (np.abs(phat - 0.5) > 1.645 * np.sqrt(0.25 / n))[:, 9:].any(axis=1).mean()
xn = np.log(2 * 1 * n * (n + 1) / 0.1)
stack_wrong = (np.abs(phat - 0.5) > np.sqrt(xn / (2 * n)))[:, 9:].any(axis=1).mean()

# real transcripts of the machines
def steps_table(m, w):
    d = lab.trace_payload(m, w)
    rows = []
    for s in d["steps"]:
        extra = ""
        if "stack_after" in s: extra = f" stack {''.join(s['stack_after'])}"
        if "output" in s: extra = f" out {s['output']}"
        if "p" in s: extra = f" p={s['p']}"
        rows.append(f"| {s['index'] + 1} | {s['state']} | `{s['symbol']}` | {s['next_state'] if s['next_state'] is not None else '— (blocked)'}{extra} |")
    head = "| step | from | reads | to |\n|---|---|---|---|\n"
    return head + "\n".join(rows), d
tt = {k: steps_table(*a) for k, a in {"dfa_ok": ("dfa", ["a", "b", "b", "a"]), "dfa_dead": ("dfa", ["b", "a"]), "nfa": ("nfa", ["a", "a", "b"]), "enfa": ("enfa", ["a", "b"]), "pa": ("pa", ["go", "go", "go"]),
                                           "lts": ("lts", ["plan", "answer", "plan"]), "mealy": ("mealy", ["task", "error", "ok"]), "pda": ("pda", ["call", "call", "ret", "ret"]), "pda_bad": ("pda", ["call", "ret", "ret"]),
                                           "tm": ("tm", list("1011"))}.items()}
tm = tt["tm"][1]
states_tbl = "\n".join(f"| q{n['index']} | `{n['id']}` | {n['group']} | {n['role'].replace('_', ' ')} | {n['description'][:150].rstrip()} |" for n in model.describe()["nodes"])
roles = {}
for n_ in model.describe()["nodes"]:
    roles[n_["role"]] = roles.get(n_["role"], 0) + 1

rel = list(csv.DictReader(open(ROOT / "research" / "related_work.csv", encoding="utf-8")))
cut = lambda s, k=330: (s if len(s) <= k else s[:k].rsplit(" ", 1)[0] + " …")
rel_md = "\n\n".join(f"""### {r['id']} — {r['title']}

*{r['authors']} · first posted {r['first_publication']} · {r['venue']} · how closely we read it: **{r['evidence_level']}***

* **Problem:** {cut(r['problem_definition'])}
* **Replay / intervention:** {cut(r['replay_or_intervention'])}
* **How it decides / stops:** {cut(r['stopping_rule'])}
* **Guarantee:** {cut(r['confidence_or_coverage_guarantee'])}
* **Overlap with our work:** {cut(r['overlap_with_proposal'])}""" for r in rel)

gap_rows = "\n".join(f"| {g:.2f} | {next(s for s in gap if s['method'] == 'lucb' and abs(s['gap'] - g) < 1e-9)['mean_rollouts']:,.0f} | {next(s for s in gap if s['method'] == 'successive_elim' and abs(s['gap'] - g) < 1e-9)['mean_rollouts']:,.0f} | {next(s for s in gap if s['method'] == 'uniform_fc' and abs(s['gap'] - g) < 1e-9)['mean_rollouts']:,.0f} |" for g in sorted({s['gap'] for s in gap}))
k_rows = "\n".join(f"| {k} | {next(s for s in kswp if s['method'] == 'lucb' and s['K'] == k)['mean_rollouts']:,.0f} | {next(s for s in kswp if s['method'] == 'uniform_fc' and s['K'] == k)['mean_rollouts']:,.0f} |" for k in sorted({s['K'] for s in kswp}))
d_rows = "\n".join(f"| {s['delta']} | {s['mean_rollouts']:,.0f} | {pc(s['accuracy'])} | {pc(s['identified_error_rate'])} |" for s in sorted(dsw, key=lambda s: s['delta']))
sz_rows = "\n".join(f"| {s['n_states']} | {s['method'].replace('_', ' ')} | {s['mean_rollouts']:,.0f} | {pc(s['accuracy'])} | {pc(s['abstain_rate'])} |" for s in sorted(szs, key=lambda s: (s['n_states'], s['method'])))
nz_rows = "\n".join(f"| {s['recon_noise']:.2f} | {s['mean_rollouts']:,.0f} | {pc(s['abstain_rate'])} | {pc(s['accuracy'])} |" for s in sorted(noise, key=lambda s: s['recon_noise']))
ab_rows = "\n".join(f"| {s['factor']} = {s['level']} | {s['mean_rollouts']:,.0f} | {pc(s['accuracy'])} | {pc(s['abstain_rate'])} |" for s in abl)
b90 = {}
for s in sorted(bud, key=lambda s: s['B']):
    if s['accuracy'] >= 0.9 and s['method'] not in b90: b90[s['method']] = s['B']
b_rows = "\n".join(f"| {m.replace('_', ' ')} | {b90.get(m, 'not reached')} |" for m in ("lucb_prefix", "lucb", "equal_budget", "random_budget"))
tool_rows = "\n".join(f"| {s['variant']} | {s['method'].replace('_', ' ')} | {s['mean_rollouts']:,.0f} | {pc(s['accuracy'])} | {pc(s['abstain_rate'])} |" for s in tool)
tgt_rows = "\n".join(f"| {s['target']} | {s['method'].replace('_', ' ')} | {s['mean_rollouts']:,.0f} | {pc(s['accuracy'])} | {pc(s['abstain_rate'])} |" for s in tgt)
main_rows = "\n".join(f"| {n} | {pc(A[k]['accuracy'])} | {pc(A[k]['abstain_rate'])} | {A[k]['mean_rollouts']:,.0f} | {A[k]['median_rollouts']:,.0f} |" for k, n in
                      [("lucb_prefix", "LUCB + valid prefix reuse"), ("lucb", "LUCB"), ("successive_elim", "Successive elimination"), ("uniform_fc", "Uniform (same stopping rule)"), ("random_fc", "Random (same stopping rule)"),
                       ("equal_budget", "Equal budget (never stops early)"), ("lucb_naive_share", "LUCB + naive sharing (invalid, negative control)"), ("car_fixed_k", "CAR-style fixed K (different question)")])
pair_rows = "\n".join(f"| {p['a'].replace('_', ' ')} vs {p['b'].replace('_', ' ')} | {p['mean_a']:,.0f} vs {p['mean_b']:,.0f} | {p['ratio']:.2f}× | [{p['ci'][0]:,.0f}, {p['ci'][1]:,.0f}] | {p['p_holm']:.1e} |" for p in paired)
nov = {r["paper_id"]: r for r in csv.DictReader(open(ROOT / "research" / "novelty_matrix.csv", encoding="utf-8"))}
yn = lambda r, k: {"Yes": "●", "Partial": "◐", "No": "–"}.get(nov[r][k], nov[r][k])
nov_rows = "\n".join(f"| {nov[r]['short_name']} | {nov[r]['read_depth']} | " + " | ".join(yn(r, k) for k in ("step_level_attribution", "counterfactual_replay", "adaptive_allocation", "fixed_confidence_stopping", "delta_pac_guarantee", "prefix_aware_information_reuse", "formal_automata_representation", "real_agent_benchmarks")) + " |"
                     for r in ("GK2016", "WW2025", "CAR2026", "AT2025", "CP2026", "MA2025"))

V_ = {
    "N_ARMS": T, "RES_STATUS": res.status, "RES_GUAR": f"{res.guarantee_applies} — {res.guarantee_note}", "RES_ROLL": f"{res.total_rollouts:,}", "RES_ROUNDS": f"{res.rounds:,}", "RES_LAB": labs[res.selected], "PLANTED": labs[env.planted_arm()], "TRAJ_ROWS": traj_rows, "EST_ROWS": est_rows, "HIST_ROWS": hist_rows,
    "VALID_ROLL": f"{res_valid.total_rollouts:,}", "VALID_SHARED": f"{int(sum(res_valid.shared_obs)):,}", "NAIVE_ROLL": f"{res_naive.total_rollouts:,}", "NAIVE_ANS": labs[res_naive.answer] if res_naive.answer is not None else "none",
    "NAIVE_STATUS": res_naive.status, "UNI_ROLL": f"{res_uni.total_rollouts:,}", "STEPS_SIM": f"{res.total_steps:,}", "SUCC_P": f"{model.success_probability():.3f}", "VSUB": f"{V[0, sub]:.3f}",
    "N0": n0, "S0": s0, "PHAT": f"{s0 / n0:.2f}", "KL_LO": f"{lo[0]:.3f}", "KL_HI": f"{hi[0]:.3f}", "H_LO": f"{hoeff[0]:.3f}", "H_HI": f"{hoeff[1]:.3f}", "NAIVE_WRONG": pc(naive_wrong), "STACK_WRONG": f"{100 * stack_wrong:.1f} %",
    "KLEX": f"{kl_bernoulli(0.6, 0.45):.4f}", "ROWS_TOTAL": f"{rows_total:,}", "TRIALS": meta["trials"], "BT": tests["total"], "FT": fe["numTotalTests"], "TT": tests["total"] + fe["numTotalTests"],
    "STATES_TBL": states_tbl, "REL_MD": rel_md, "NOV_ROWS": nov_rows, "GAP_ROWS": gap_rows, "K_ROWS": k_rows, "D_ROWS": d_rows, "SZ_ROWS": sz_rows, "NZ_ROWS": nz_rows, "AB_ROWS": ab_rows, "B_ROWS": b_rows,
    "TOOL_ROWS": tool_rows, "TGT_ROWS": tgt_rows, "MAIN_ROWS": main_rows, "PAIR_ROWS": pair_rows, "P0": f"{paired[0]['ratio']:.2f}", "P3": f"{paired[3]['ratio']:.2f}",
    "SH_NONE": f"{AB[('sharing', 'none')]['mean_rollouts']:,.0f}", "SH_VALID": f"{AB[('sharing', 'valid')]['mean_rollouts']:,.0f}", "SH_NAIVE": f"{AB[('sharing', 'naive')]['mean_rollouts']:,.0f}",
    "AC_NONE": pc(AB[('sharing', 'none')]['accuracy']), "AC_VALID": pc(AB[('sharing', 'valid')]['accuracy']), "AC_NAIVE": pc(AB[('sharing', 'naive')]['accuracy']),
    "TM_OUT": tm["output"], "TM_STEPS": tm["n_steps"], "PA_P": f"{tt['pa'][1]['exact_acceptance_probability']:.3f}", "ROLES": ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in roles.items()),
}
for k, (tbl, _) in tt.items():
    V_["TT_" + k.upper()] = tbl


def fig(f, cap=None, w=96):
    cap = cap or (man.get(f"{f}.png", {}).get("caption", ""))
    return f'<figure><img src="../results/figures/{f}.png" style="width:{w}%"/><figcaption>{cap}</figcaption></figure>'


def shot(f, cap, w=96):
    return f'<figure><img src="screens/demo/{f}.png" style="width:{w}%"/><figcaption><b>Screenshot.</b> {cap}</figcaption></figure>'


V_["FIG_ARCH"] = fig("fig01_system_architecture"); V_["FIG_TRAJ"] = fig("fig02_failed_trajectory"); V_["FIG_REPLAY"] = fig("fig03_counterfactual_replay"); V_["FIG_FLOW"] = fig("fig04_adaptive_selection_flowchart", w=70)
V_["FIG_STOP"] = fig("fig05_confidence_stopping"); V_["FIG_DFA"] = fig("fig06_dfa", w=75); V_["FIG_NFA"] = fig("fig07_nfa_active_sets"); V_["FIG_ENFA"] = fig("fig08_enfa_closure"); V_["FIG_PA"] = fig("fig09_probabilistic_automaton", w=70)
V_["FIG_PREFIX"] = fig("fig10_prefix_tree"); V_["FIG_PREFIXC"] = fig("fig11_prefix_aware_comparison"); V_["FIG_A48"] = fig("fig12_automaton_48_states"); V_["FIG_SW"] = fig("fig13_software_architecture"); V_["FIG_PIPE"] = fig("fig14_evaluation_pipeline")
V_["FIG_ACC"] = fig("fig15_rollouts_vs_accuracy"); V_["FIG_COST"] = fig("fig16_cost_vs_quality"); V_["FIG_ABL"] = fig("fig17_ablations"); V_["FIG_ERR"] = fig("fig18_error_analysis"); V_["FIG_GAP"] = fig("fig19_gap_sweep_lower_bound")
V_["FIG_DELTA"] = fig("fig20_error_vs_delta"); V_["FIG_K"] = fig("fig21_candidates_sweep")
for f in sorted((ROOT / "report" / "screens" / "demo").glob("*.png")):
    pass

PARTS = []
T_ = lambda s: PARTS.append(s)
exec((ROOT / "scripts" / "handbook_text.py").read_text(encoding="utf-8"))   # defines the chapters as plain strings with @TOKEN@ placeholders and appends them to PARTS

md = "\n\n".join(PARTS)
for k, v in V_.items():
    md = md.replace(f"@{k}@", str(v))
import re
left = set(re.findall(r"@[A-Z0-9_]+@", md))
assert not left, left
# screenshots by name:  [[shot:file|caption|width]]
md = re.sub(r"\[\[shot:([^|\]]+)\|([^|\]]+)(?:\|(\d+))?\]\]", lambda m: shot(m.group(1), m.group(2), int(m.group(3) or 96)), md)
out = ROOT / "report" / "handbook.md"
out.write_text(md, encoding="utf-8")
print("wrote", out.relative_to(ROOT), f"({len(md.split()):,} words)")
if "--no-pdf" not in sys.argv:
    from build_pdfs import build
    tmp = ROOT / "report" / "_handbook_pdf.md"
    tmp.write_text(md.replace('src="../results/', 'src="' + ROOT.as_uri() + '/results/').replace('src="screens/', 'src="' + ROOT.as_uri() + '/report/screens/'), encoding="utf-8")
    try:
        build(tmp, ROOT / "report" / "AFCR_Complete_Handbook.pdf")
    finally:
        tmp.unlink(missing_ok=True)
