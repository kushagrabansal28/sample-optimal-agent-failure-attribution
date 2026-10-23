"""Build research/related_work.csv (one record per verified paper).

The data below was transcribed by hand from the papers' full texts on 2026-10-23
(see research/related_work.md for evidence levels). 'not verified' means the
field could not be established from the text we had.
"""
from __future__ import annotations

import csv
from pathlib import Path

FIELDS = [
    "id", "title", "authors", "first_publication", "versions", "venue", "evidence_level",
    "problem_definition", "causal_assumptions", "attribution_unit", "replay_or_intervention",
    "statistical_estimator", "allocation", "stopping_rule", "confidence_or_coverage_guarantee",
    "sample_complexity_results", "benchmarks", "baselines", "reported_limitations",
    "public_implementation", "overlap_with_proposal",
]

NV = "not verified"

ROWS = [
    dict(
        id="GK2016", title="Optimal Best Arm Identification with Fixed Confidence",
        authors="Aurélien Garivier; Emilie Kaufmann", first_publication="2016-02-15",
        versions="v1 2016-02-15; v2 2016-06-01", venue="COLT 2016", evidence_level="FULL-THM",
        problem_definition="Fixed-confidence best-arm identification, one-parameter bandit models with a unique best arm; delta-PAC strategies.",
        causal_assumptions="n/a (stochastic bandit; i.i.d. rewards per arm, independent arms)",
        attribution_unit="arm", replay_or_intervention="n/a",
        statistical_estimator="Empirical means; Chernoff generalized-likelihood-ratio statistic Z_{a,b}(t)",
        allocation="Adaptive: Track-and-Stop (C-/D-tracking of optimal proportions w*(mu))",
        stopping_rule="Chernoff stopping rule with threshold beta(t,delta)=log(r(t)/delta); Bernoulli: log(2(K-1)t/delta) is delta-PAC (Thm 10)",
        confidence_or_coverage_guarantee="delta-PAC for any sampling rule (Prop 12, exp. families, C=C(alpha,K))",
        sample_complexity_results="Thm 1: E[tau]>=T*(mu)kl(delta,1-delta). Thm 14: limsup E[tau]/log(1/delta)<=alpha T*(mu). Asymptotic (delta->0) optimality.",
        benchmarks="Synthetic bandit simulations", baselines="KL-LUCB, racing (per discussion section)",
        reported_limitations="Asymptotic optimality only; forced exploration needed when best arm not unique; unique-best-arm assumption.",
        public_implementation=NV,
        overlap_with_proposal="Statistical template for AFCR; our guarantee uses simpler union-bound bounds, NOT Track-and-Stop; we do not claim asymptotic optimality.",
    ),
    dict(
        id="WW2025", title="Which Agent Causes Task Failures and When? On Automated Failure Attribution of LLM Multi-Agent Systems",
        authors="Shaokun Zhang; Ming Yin; Jieyu Zhang; Jiale Liu; Zhiguang Han; Jingyang Zhang; Beibin Li; Chi Wang; Huazheng Wang; Yiran Chen; Qingyun Wu",
        first_publication="2025-04-30", versions="v1 2025-04-30; v2 2025-05-23; v3 2025-06-02", venue="ICML 2025 (per citation in arXiv:2606.08275)",
        evidence_level="KEY",
        problem_definition="Identify failure-responsible agent i* and decisive error step t* from a failure log.",
        causal_assumptions="Annotation-based notion of 'decisive error' (single decisive error); no formal causal model.",
        attribution_unit="agent and step", replay_or_intervention="None (LLM judges read the log)",
        statistical_estimator="None (LLM judgement)", allocation="Non-statistical: all-at-once, step-by-step, binary search over the log",
        stopping_rule="n/a", confidence_or_coverage_guarantee="None",
        sample_complexity_results="None", benchmarks="Who&When (127 multi-agent systems; algorithm-generated and hand-crafted)",
        baselines="Random; three LLM-judge methods; several LLMs incl. o1 and R1",
        reported_limitations="Best method ~53.5% agent-level, ~14.2% step-level accuracy; some methods below random.",
        public_implementation="github.com/mingyin1/Agents_Failure_Attribution (link on arXiv page; not inspected)",
        overlap_with_proposal="Defines the task and benchmark; no overlap in method. Does NOT use Shapley estimation (that is CAR).",
    ),
    dict(
        id="CAR2026", title="Causal Agent Replay: Counterfactual Attribution for LLM-Agent Failures",
        authors="Jaineet Shah", first_publication="2026-06-06", versions="v1 2026-06-06 (CC BY 4.0)", venue="arXiv preprint (cs.LG)",
        evidence_level="FULL",
        problem_definition="Which step caused the failure of an LLM-agent run; agent run as an SCM tau=(s0,(a1,o1),...,(an,on),y), y in [0,1].",
        causal_assumptions="Faithful replay of the exact state s_k; stochastic policy; outcome function user-supplied; total (not direct) effect through stochastic continuation; no common random numbers.",
        attribution_unit="step (and Shapley credit over steps)",
        replay_or_intervention="Five do-operations: do_resample (null), do_action, do_observation, do_context, do_policy; run forward K times from the intervened state.",
        statistical_estimator="Contrastive: P(bad|do_resample k) with Wilson interval on proportion and bootstrap interval on the difference; budget-bounded MC permutation Shapley with antithetic pairing and normal-approx CIs.",
        allocation="Fixed K per step (non-adaptive); Shapley budget-bounded with circuit breaker, on demand only",
        stopping_rule="None (fixed K); locus = latest step whose effect CI excludes zero",
        confidence_or_coverage_guarantee="Per-estimate CIs only; no delta-PAC or sequential guarantee stated",
        sample_complexity_results="None", benchmarks="Synthetic SCMs with planted ground truth only (pivotal step; two-step AND failure: phi0=0.44, phi1=0.45, efficiency sum 0.909 vs 0.91)",
        baselines="Single-step contrastive vs Shapley comparison; Who&When ~14% quoted from prior work",
        reported_limitations="Total effect; judge-based outcomes noisy; real tools with side effects out of scope; Shapley exponential worst case.",
        public_implementation="github.com/jaineet17/causal-agent-replay (link in paper; not inspected)",
        overlap_with_proposal="HIGH on estimand/replay (same-policy resampling, outcome distributions, run-forward confound); NONE on fixed-confidence stopping, adaptivity, prefix reuse, automata. Its no-cache rule motivates our validity conditions.",
    ),
    dict(
        id="AT2025", title="AgenTracer: Who Is Inducing Failure in the LLM Agentic Systems?",
        authors="Guibin Zhang; Junhao Wang; Junjie Chen; Wangchunshu Zhou; Kun Wang; Shuicheng Yan",
        first_publication="2025-09-03", versions="v1 2025-09-03; v2 2025-09-04", venue="ICLR 2026 (per citation in arXiv:2608.29228)",
        evidence_level="KEY",
        problem_definition="Failure attribution; decisive step = earliest step whose oracle rectification flips failure to success.",
        causal_assumptions="Oracle rectification operator R(tau,t,a'_t) replaces action by an oracle/analyzer-proposed corrected action and re-simulates; single decisive error.",
        attribution_unit="agent-step pair",
        replay_or_intervention="Counterfactual replay with analyzer-agent corrections (has access to ground truth) + programmatic fault injection on successful trajectories",
        statistical_estimator="Binary outcome of a single replay per step (no estimator)", allocation="Sequential scan over steps (non-statistical)",
        stopping_rule="Earliest flipping step", confidence_or_coverage_guarantee="None", sample_complexity_results="None",
        benchmarks="TracerTraj (~2k trajectories, six datasets); Who&When", baselines="Proprietary and open reasoning LLMs as judges (e.g. Gemini-2.5-Pro, DeepSeek-R1)",
        reported_limitations=NV, public_implementation="No code link found on arXiv page",
        overlap_with_proposal="Replay as annotation oracle; second culprit definition (earliest). AFCR's first_above rule formalises it under sampling noise.",
    ),
    dict(
        id="CP2026", title="Conformal Agent Error Attribution",
        authors="Naihe Feng; Yi Sui; Shiyi Hou; Ga Wu; Jesse C. Cresswell", first_publication="2026-05-07", versions="v1 2026-05-07", venue="arXiv preprint",
        evidence_level="KEY",
        problem_definition="Predict a contiguous set of steps containing the decisive error with finite-sample coverage.",
        causal_assumptions="Exchangeability of calibration and test trajectories; single decisive error; labelled calibration data.",
        attribution_unit="contiguous set of steps", replay_or_intervention="None (scoring functions: LLM judges, role prompting, fine-tuned Qwen3-1.7B)",
        statistical_estimator="Split conformal with left/right/two-way filtration scores", allocation="n/a (non-sequential)", stopping_rule="n/a",
        confidence_or_coverage_guarantee="Marginal coverage 1-alpha <= P[y* in C] < 1-alpha+1/(n+1) (Thm 3.4) over trajectories",
        sample_complexity_results="None (inference cost NFE per test point reported)", benchmarks="Who&When (184 examples); GSM8K/MATH controlled injection (DyLAN, MacNet)",
        baselines="VCP, CRSVP, top-1 step", reported_limitations="Exchangeability; match algorithm to data distribution; single decisive-error assumption.",
        public_implementation="github.com/layer6ai-labs/conformal-agent-error-attribution (link in paper; not inspected)",
        overlap_with_proposal="Orthogonal; marginal coverage vs per-trajectory identification; complementary (set -> replay).",
    ),
    dict(
        id="MA2025", title="Automatic Failure Attribution and Critical Step Prediction Method for Multi-Agent Systems Based on Causal Inference",
        authors="Guoqing Ma; Jia Zhu; Hanghui Guo; Weijie Shi; Jiawei Shen; Jingjiang Liu; Yidan Liang", first_publication="2025-09 (arXiv:2509.08682)", versions=NV, venue="arXiv preprint",
        evidence_level="KEY", problem_definition="Failure attribution via causal inversion + Shapley (agents) and CDC-MAS causal discovery (critical steps).",
        causal_assumptions="Non-stationary interaction data; latent confounders handled by CDC-MAS (per text).", attribution_unit="agent and step",
        replay_or_intervention="Counterfactual simulation used for optimisation suggestions", statistical_estimator="Shapley values; causal discovery", allocation="n/a", stopping_rule="n/a",
        confidence_or_coverage_guarantee="None found", sample_complexity_results="None", benchmarks="Who&When; TRAIL", baselines=NV,
        reported_limitations=NV, public_implementation=NV, overlap_with_proposal="Low (static-log causal discovery).",
    ),
    dict(
        id="REFLECT2026", title="REFLECT: Intervention-Supported Error Attribution for Silent Failures in LLM Agent Traces",
        authors="Xiaofeng Lin; Yunxi Wang; Tung Sum Thomas Kwok; Daniel Guo; Sahil Arun Nale; Charles Fleming; Guang Cheng", first_publication="2026-06-09", versions=NV, venue="ICML 2026 Workshop on Failure Modes in Agentic AI",
        evidence_level="KEY", problem_definition="Localize errors in silent-failure traces using intervention outcomes as evidence.", causal_assumptions="Deterministic verifier/string-match outcomes; patch quality.",
        attribution_unit="step", replay_or_intervention="Controlled replay with diagnosis-specific patch; multi-rollback", statistical_estimator="Outcome flip as contrastive evidence", allocation="Heuristic LLM-driven",
        stopping_rule="Heuristic", confidence_or_coverage_guarantee="None", sample_complexity_results="None", benchmarks="Four localisation benchmarks (e.g. WTQ, GAIA)", baselines="Same-auditor methods",
        reported_limitations=NV, public_implementation="Released code (err-loc package mentioned in appendix; not inspected)", overlap_with_proposal="Replay-based; no sequential statistics.",
    ),
    dict(
        id="CF2026", title="CausalFlow: Causal Attribution and Counterfactual Repair for LLM Agent Failures",
        authors="Akash Bonagiri; Devang Borkar; Gerard Janno Anderias; Setareh Rafatirad; Houman Homayoun", first_publication="2026-05 (arXiv:2605.25338)", versions=NV, venue="arXiv preprint",
        evidence_level="KEY", problem_definition="Causal Responsibility Scores via step-level counterfactual intervention, then minimal repairs.", causal_assumptions=NV, attribution_unit="step",
        replay_or_intervention="Step-level interventions and edited repairs validated by outcome flip", statistical_estimator="CRS (details not verified)", allocation=NV, stopping_rule=NV,
        confidence_or_coverage_guarantee="None found", sample_complexity_results="None", benchmarks="Four: math reasoning, code generation, QA, medical browsing", baselines="Heuristic refinement",
        reported_limitations=NV, public_implementation=NV, overlap_with_proposal="Replay-based; no sequential statistics.",
    ),
    dict(
        id="ZR2026", title="Knowledge-Based Zero-Replay Debugging of Multi-Agent LLM Traces",
        authors="Hyeonjeong Cha; Daein Weon; Dong Ho Kang", first_publication="2026-06 (arXiv:2606.14805)", versions="v2 2026-09-26", venue="arXiv preprint (cs.SE)",
        evidence_level="KEY", problem_definition="Predict which events a replay oracle would mark high-effect, without replaying (zero-replay counterfactual-effect prediction).", causal_assumptions="Deterministic replay oracle as reference.",
        attribution_unit="event", replay_or_intervention="Remove-event interventions in a deterministic oracle used only for calibration/evaluation", statistical_estimator="Learning-to-rank gradient-boosted predictor over 13 knowledge-graph features",
        allocation="Static top-K replay agenda under a budget", stopping_rule="n/a", confidence_or_coverage_guarantee="Calibration of predictor; no statistical stopping guarantee", sample_complexity_results="None",
        benchmarks="37 trace families (oracle-calibrated)", baselines="Graph-centrality heuristics, linear scorer", reported_limitations="Characterises when cheap centrality suffices vs learned evidence.",
        public_implementation="Reproducible artifacts claimed; not inspected", overlap_with_proposal="Same cost motivation, different mechanism (prediction vs adaptive stochastic replay).",
    ),
    dict(
        id="GCJR2026", title="Localizing Emergent Failures in Agentic AI: Recovering Minimal Repair Families via Counterfactual Replay",
        authors="Bingjie Li; Yumeng Song; Zhongming Yao; Tianyi Li", first_publication="2026-08 (arXiv:2608.29228)", versions="v2 2026-09-06", venue="arXiv preprint",
        evidence_level="KEY", problem_definition="Minimal Repair Family Recovery: all inclusion-minimal event sets whose replay restores success within a size bound.", causal_assumptions="Declared graph domain; fixed (deterministic) replay outcomes.",
        attribution_unit="set of events", replay_or_intervention="Graph-constrained singleton and pair candidates verified by replay with paired clean counterparts", statistical_estimator="None (deterministic verification)", allocation="Graph-constrained deterministic pruning",
        stopping_rule="Exhaustion of graph-feasible candidates", confidence_or_coverage_guarantee="Exact within declared graph domain for fixed replay outcomes (no probabilistic guarantee)", sample_complexity_results="Empirical: replay calls 56.3 -> 25.3 on 120-DAG benchmark; 21.0 -> 10.0 on 24-case LLM pilot",
        benchmarks="120-DAG controlled benchmark; 24-case four-agent LLM pilot", baselines="Exhaustive search; single-event replay", reported_limitations="Bounded set size; declared domain.",
        public_implementation=NV, overlap_with_proposal="Handles joint causes (we do not); different cost-reduction route.",
    ),
    dict(
        id="SYM2026", title="Repair or Resample? Rethinking Failure Debugging in LLM Multi-Agent Systems",
        authors="Zhongwen Luan; Xiaoyu Zhang; Yue Yang; Jiongchi Yu; Xiaohong Chen; Ming Hu", first_publication="2026-08 (arXiv:2608.25920)", versions=NV, venue="arXiv preprint",
        evidence_level="KEY", problem_definition="Do MAS repair methods causally repair or stochastically resample? SymTrace framework + SymFail dataset (536 annotated failures).", causal_assumptions="Faithful reconstruction of the prefix before an anchor from recorded logs.",
        attribution_unit="intervention anchor / suspicious node", replay_or_intervention="Snapshot + replay mode: reinject recorded results up to the anchor, regenerate downstream", statistical_estimator="Rates with Wilson CIs; paired bootstrap; McNemar; Holm (evaluation only)",
        allocation="Fixed attempts (e.g. three-attempt budget)", stopping_rule="n/a", confidence_or_coverage_guarantee="None for the debugger", sample_complexity_results="None",
        benchmarks="SymFail (AG2, CrewAI, Magentic-One)", baselines="Task-level rerun/regeneration, feedback-based methods", reported_limitations=NV, public_implementation=NV,
        overlap_with_proposal="Prefix reconstruction for replay FIDELITY; no cross-candidate reuse of rollouts found.",
    ),
    dict(
        id="DOVER2025", title="DoVer: Intervention-Driven Auto Debugging for LLM Multi-Agent Systems",
        authors="Ming Ma; Jue Zhang; Fangkai Yang; et al.", first_publication="2025-12-07", versions="v1 2025-12-07 ... v3 2026-01-31", venue="arXiv preprint",
        evidence_level="ABS", problem_definition="Validate or refute failure hypotheses by interventions.", causal_assumptions=NV, attribution_unit="step/agent hypotheses", replay_or_intervention="Interventions in Magentic-One and AG2",
        statistical_estimator=NV, allocation=NV, stopping_rule=NV, confidence_or_coverage_guarantee=NV, sample_complexity_results=NV, benchmarks="GAIA- and AssistantBench-derived datasets; GSMPlus", baselines=NV,
        reported_limitations="Evidence of feasibility, not universal guarantees (per abstract)", public_implementation="aka.ms/DoVer announced (not inspected)", overlap_with_proposal="Unclear; read full text before submission.",
    ),
    dict(
        id="KK2013", title="Information Complexity in Bandit Subset Selection",
        authors="Emilie Kaufmann; Shivaram Kalyanakrishnan", first_publication="2013", versions=NV, venue="COLT 2013, PMLR 30:228-251", evidence_level="THM",
        problem_definition="Explore-m (PAC/fixed-budget subset selection) with KL confidence regions.", causal_assumptions="Independent arms; bounded/Bernoulli rewards.", attribution_unit="arm",
        replay_or_intervention="n/a", statistical_estimator="u_a=max{q>=p_a: N_a d(p_a,q)<=beta}, l_a symmetric", allocation="KL-LUCB (sample lowest-LCB selected arm and highest-UCB non-selected arm) and KL-Racing",
        stopping_rule="Stop when L(selected) >= U(non-selected) - epsilon", confidence_or_coverage_guarantee="Thm 1: delta-PAC with beta=log(k1 K t^alpha/delta)+loglog(...), alpha>1, k1>2e+1+e/(alpha-1)+(e+1)/(alpha-1)^2",
        sample_complexity_results="Thm 3: P(tau<=C0(alpha)H*_{eps,c} log(k1 K (H*_{eps,c})^alpha/delta))>=1-2delta", benchmarks="Synthetic", baselines="Hoeffding LUCB/racing, others",
        reported_limitations=NV, public_implementation=NV, overlap_with_proposal="Source of the KL-LUCB baseline implemented in this repo.",
    ),
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "research" / "related_work.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in ROWS:
            missing = set(FIELDS) - set(r)
            assert not missing, (r["id"], missing)
            w.writerow(r)
    print(f"wrote {out} ({len(ROWS)} rows)")
