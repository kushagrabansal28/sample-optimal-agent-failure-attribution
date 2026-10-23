"""Write paper/appendices/*.md.

  A  proof of Theorem 2 and B confidence-sequence notes  -> extracted from paper/main.md (single source of truth)
  C  complete specification of the 48-state agent automaton -> generated from the model
  D  complete result tables for every experiment group      -> generated from results/processed/*.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "paper" / "appendices"
OUT.mkdir(parents=True, exist_ok=True)
PROC = ROOT / "results" / "processed"
paper = (ROOT / "paper" / "main.md").read_text(encoding="utf-8").replace("\r\n", "\n")


def section(title_start: str) -> str:
    m = re.search(rf"^## {re.escape(title_start)}.*?(?=^## |\Z)", paper, re.S | re.M)
    return m.group(0).strip() if m else f"(section '{title_start}' not found in paper/main.md)"


def w(name, text):
    (OUT / name).write_text(text.strip() + "\n", encoding="utf-8")
    print("wrote paper/appendices/" + name)


NOTE = "*Extracted from `paper/main.md` by `scripts/build_appendices.py`; edit the paper, not this file.*\n\n"


def appendix(key):
    head, _, body = section(key).partition("\n")
    return head.replace("## ", "# ", 1) + "\n\n" + NOTE + body


w("A_proof_theorem2.md", appendix("Appendix A"))
w("B_confidence_sequences.md", appendix("Appendix B"))

# ---- C: automaton specification -------------------------------------------------------------------------------------
from afcr.automata.benchmark48 import build_agent_model  # noqa: E402

model = build_agent_model(48)
d = model.describe()
lines = ["# Appendix C. Specification of the 48-state agent automaton", "",
         f"Generated from `build_agent_model(48)`. {d['n_states']} logical states, horizon {d['horizon']}, alphabet size {len(d['alphabet'])}, "
         f"unconditional success probability {d['success_probability']:.4f}. Groups: " + ", ".join(f"{k} ({v})" for k, v in d["groups"].items()) + ".", "",
         "Roles: *benign*, *decision* (carries a planted fault action), *fault_entry*, *corridor* (corrupted state), *recovery*, *terminal_success*, *terminal_failure*.", "",
         "## States", "", "| # | id | label | group | role | reference action | policy over actions |", "|---|---|---|---|---|---|---|"]
for n in d["nodes"]:
    pol = ", ".join(f"{a}: {p:.2f}" for a, p in n["policy"].items()) or "—"
    lines.append(f"| {n['index']} | `{n['id']}` | {n['label']} | {n['group']} | {n['role']} | {n.get('ref_action') or '—'} | {pol} |")
lines += ["", "## Transitions (policy probability × kernel probability)", "", "| source | action | target | category | fault | kernel P | policy P | product |", "|---|---|---|---|---|---|---|---|"]
for e in d["edges"]:
    lines.append(f"| `{e['source']}` | {e['label']} | `{e['target']}` | {e['category']} | {'yes' if e['is_fault'] else ''} | {e['kernel_prob']:.2f} | {e['policy_prob']:.2f} | {e['prob']:.3f} |")
lines += ["", "Fault actions: " + ", ".join(f"`{s}`" for s in d["fault_symbols"]) + ".", "",
          "Exact quantities (see the paper, Section 5): $V_t(q)=P(\\text{success}\\mid q,t)$ by backward induction; "
          "$\\mu_t^{rep}=\\sum_{q'}P(q'\\mid q_{t-1},\\rho(q_{t-1}))V_t(q')$; $\\mu_t^{res}=V_{t-1}(q_{t-1})$."]
w("C_automaton_specification.md", "\n".join(lines))

# ---- D: complete result tables ---------------------------------------------------------------------------------------
GROUPS = ["main", "gap_sweep", "K_sweep", "delta_sweep", "stress", "size_sweep", "eps_sweep", "noise_sweep", "ablation", "budget_curve", "toolagent", "targets"]
KEYS = ["kind", "gap", "K", "delta", "n_states", "eps", "recon_noise", "factor", "level", "B", "variant", "target", "method", "n", "accuracy", "acc_ci_lo", "acc_ci_hi", "abstain_rate",
        "certified_rate", "identified_error_rate", "mean_rollouts", "median_rollouts", "p90_rollouts"]


def fmt(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.0f}" if abs(v) >= 100 else f"{v:.3f}"
    return str(v)


lines = ["# Appendix D. Complete result tables", "",
         "All numbers are **synthetic** (bandit-arm model, automata, Stage-B tool agent). Generated from `results/processed/<group>.json`, which `suite.aggregate` computes from "
         "`results/raw/<group>.csv`. Accuracy intervals (Wilson) are in the `acc_ci_*` columns. Rollout statistics of trials that hit the budget cap are censored.", ""]
meta = json.loads((PROC / "suite_meta.json").read_text(encoding="utf-8"))
lines += ["| group | rows | wall seconds |", "|---|---|---|"] + [f"| {g} | {v['rows']:,} | {v['wall_seconds']:.0f} |" for g, v in meta["groups"].items()] + [""]
for g in GROUPS:
    rows = json.loads((PROC / f"{g}.json").read_text(encoding="utf-8"))["summary"]
    cols = [k for k in KEYS if any(k in r for r in rows)]
    lines += [f"## {g}", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join(fmt(r.get(k)) for k in cols) + " |")
    lines.append("")
paired = json.loads((PROC / "paired_stats.json").read_text(encoding="utf-8"))
lines += ["## paired statistics (main, 48-state automaton)", "", "| A | B | n | mean A | mean B | mean diff | 95 % CI | ratio | p | p (Holm) | reject @ 0.05 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for p in paired:
    lines.append(f"| {p['a']} | {p['b']} | {p['n']} | {p['mean_a']:,.0f} | {p['mean_b']:,.0f} | {p['mean_diff']:,.0f} | [{p['ci'][0]:,.0f}, {p['ci'][1]:,.0f}] | {p['ratio']:.2f} | {p['p']:.1e} | {p['p_holm']:.1e} | {'yes' if p['reject_holm_0_05'] else 'no'} |")
w("D_full_result_tables.md", "\n".join(lines))

w("README.md", """
# Paper appendices

| File | Contents | Source |
|---|---|---|
| [A_proof_theorem2.md](A_proof_theorem2.md) | proof of Theorem 2 (successive elimination sample complexity) | `paper/main.md` |
| [B_confidence_sequences.md](B_confidence_sequences.md) | notes on the stack-KL / Hoeffding confidence sequences and the KL-LUCB rate | `paper/main.md` |
| [C_automaton_specification.md](C_automaton_specification.md) | every state, action and transition of the 48-state automaton | generated from the model |
| [D_full_result_tables.md](D_full_result_tables.md) | every experiment group's aggregated numbers and the paired statistics | generated from `results/processed` |

Regenerate with `python scripts/build_appendices.py`. Appendices C and D are generated, never typed by hand.
""")
