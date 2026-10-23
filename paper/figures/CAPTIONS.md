# Figure captions

**fig01_system_architecture.png** (conceptual) — End-to-end system architecture. A failed trajectory and an intervention protocol define candidate arms; each pull replays the agent from the intervened state and returns an outcome. Confidence sequences and the stopping rule decide when to certify or abstain, the allocation rule chooses the next arm, and valid prefix reuse supplies extra observations. *Source:* `scripts/make_figures.py (schematic)`

**fig02_failed_trajectory.png** (experimental) — Example failed agent trajectory. Exact μ_t (dynamic programming, no sampling) for one failed trajectory (seed 5, fault probability 0.6). Steps before the planted fault only exceed the baseline slightly: re-running re-rolls the fault. After the fault the state is corrupted and μ_t falls. *Source:* `AgentModel.exact_mu; seed 5`

**fig03_counterfactual_replay.png** (conceptual) — Counterfactual replay mechanism. Illustrated with a real sampled trajectory: the original run (top) is restored up to the chosen step, one action is forced to the reference action, and the continuation (bottom) is re-simulated. One replay is one sample of the outcome distribution. *Source:* `AutomatonEnv.replay_detail; seed 5`

**fig04_adaptive_selection_flowchart.png** (conceptual) — Adaptive candidate-selection flowchart. One round of AFCR. The sampling rule is interchangeable: δ-correctness depends only on the confidence sequence and the stopping rule. Budget exhaustion is an abstention, never a certified answer. *Source:* `src/afcr/attribution/engine.py`

**fig05_confidence_stopping.png** (experimental) — Confidence-bound and stopping-rule illustration. One LUCB run (seed 5, status: identified). The run stops the first time the lower bound of the best arm exceeds the largest upper bound of all other arms (running-intersection intervals, x_n = ln(2Kn(n+1)/δ)). *Source:* `run_attribution(history=True); seed 5, algorithm seed 12`

**fig06_dfa.png** (conceptual) — DFA: even number of a’s. A total deterministic automaton (states e = even, o = odd); bold outline = start state, green = accepting. The agent model’s DFA view is the same kind of object built from the 48-state spec (most-likely successors, explicit sink). *Source:* `afcr.automata.dfa.DFA`

**fig07_nfa_active_sets.png** (conceptual) — NFA active-state-set example. The NFA of words ending in “ab” run on “aab”: yellow = active states. The word is accepted because the final active set contains the accepting state q2 (thick outline). Nondeterminism here is formal, not LLM sampling. *Source:* `afcr.automata.nfa.NFA.run`

**fig08_enfa_closure.png** (conceptual) — ε-NFA closure illustration. Computing the ε-closure of {q0} (dashed amber = ε-moves): the set grows until a fixed point, here {q0, q1, q2}. The agent model’s heal edges are ε-moves in its ε-NFA view. *Source:* `afcr.automata.nfa.ENFA.eps_closure_steps`

**fig09_probabilistic_automaton.png** (conceptual) — Probabilistic automaton. Each (state, symbol) carries a distribution over successors (edge labels). P(accept after n steps) is exact by matrix products; runs can be sampled. This is the natural formalism for a stochastic agent. *Source:* `afcr.automata.pa.ProbabilisticAutomaton`

**fig10_prefix_tree.png** (experimental) — Prefix-tree representation of replays. Union of 60 real replays started at the first candidate step (node size = visit count; x = time since the intervention). Green nodes are exactly the (time, state) pairs at which another candidate would start; a rollout through a green node that also takes that candidate’s reference action is a valid sample for it (Theorem 3). *Source:* `AgentModel.simulate; seed 5, rng 3`

**fig11_prefix_aware_comparison.png** (experimental) — Prefix-aware replay comparison. Same instances, same stopping rule and δ. Means include trials that stopped at the budget cap (censored), so the gaps between methods are conservative; the right panel shows how often each method certified at all. *Source:* `results/processed/main.json (group main)`

**fig12_automaton_48_states.png** (structural) — 48-state automaton overview. All 48 logical states grouped into plan / observe / tool / memory / validate / terminal; edges are all positive-probability transitions of the model, fault actions in red. Drawn from build_agent_model(48), so state count and structure are those of the tested object. *Source:* `afcr.automata.benchmark48.build_agent_model(48)`

**fig13_software_architecture.png** (structural) — Software architecture. Clear boundaries between automata, statistics, replay environments, attribution logic, experiments/evaluation and the API/website; the statistical algorithm never imports a model SDK. *Source:* `src/afcr package layout`

**fig14_evaluation_pipeline.png** (conceptual) — Experimental evaluation pipeline. Trials are plain-dict specs; every number in the paper, report, website and slides is computed from the raw CSV rows by the aggregation layer. *Source:* `src/afcr/experiments/suite.py`

**fig15_rollouts_vs_accuracy.png** (experimental) — Rollouts-versus-accuracy plot. Forced-choice accuracy when only B rollouts are available (adaptive methods return their best guess if they cannot certify). The dashed 90% line is an empirical target, not the (1−δ) guarantee. *Source:* `results/processed/budget_curve.json`

**fig16_cost_vs_quality.png** (experimental) — Cost-versus-attribution-quality plot. Each marker is one method (mean rollouts with 95% bootstrap CI vs accuracy with Wilson CI). The certifying adaptive methods and the uniform/random baselines overlap in accuracy, so the separation is along the cost axis. Fixed-budget methods (equal budget, CAR-style) never certify; the CAR-style point scores against the planted step with resample arms (a different target) and is not comparable. *Source:* `results/processed/main.json`

**fig17_ablations.png** (experimental) — Ablation comparison. Confidence sequence (stack-KL vs stack-Hoeffding vs the KL-LUCB rate), allocation rule, prefix sharing (valid vs invalid naive), candidate set (all steps vs decision states only — a domain prior) and tolerance ε. Naive sharing is shown in red: it is invalid and rarely certifies. *Source:* `results/processed/ablation.json`

**fig18_error_analysis.png** (experimental) — Error-analysis visualisation. Left: what happened in every trial. Middle: abstentions occur on instances whose best arm is (almost) exactly tied with another — there is nothing to certify, so abstaining is the correct behaviour — and cost rises as the gap shrinks. Right: sharing every rollout with all later candidates produces wrong certified answers; exact-match reuse does not. *Source:* `results/raw/main.csv`

**fig19_gap_sweep_lower_bound.png** (experimental) — Sample cost vs gap and the Garivier–Kaufmann lower bound. Every measured method lies above the lower bound T*(μ)·kl(δ,1−δ) (necessarily, for δ-PAC methods); the vertical distance shows that our algorithms are far from asymptotically optimal — which is why the word ‘optimal’ is not claimed. *Source:* `results/processed/gap_sweep.json; results/raw/gap_sweep.csv (gk_lower_bound)`

**fig20_error_vs_delta.png** (experimental) — Empirical error versus δ. Observed errors among certified trials on very hard 2-arm instances, with Wilson 95% intervals. Zero errors in all trials is consistent with Theorem 1 but also shows the stack bound is conservative; this is a bug-detector, not a proof. *Source:* `results/processed/stress.json`

**fig21_candidates_sweep.png** (experimental) — Effect of the number of candidate steps. Cost grows with K for every method; adaptive allocation spends its budget on the few ambiguous arms while uniform spends it on all of them. *Source:* `results/processed/K_sweep.json`
