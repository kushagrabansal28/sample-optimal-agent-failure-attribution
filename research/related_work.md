# Related work — verification log and novelty analysis

*Last verified: 2026-10-23. All statements below come from reading (or keyword-scanning) the actual paper
PDFs fetched from arXiv / PMLR on that date, not from search snippets, unless the "Evidence level" says
otherwise. Prose is original; quotations are avoided.*

## 0. How to read the evidence levels

| Level | Meaning |
|---|---|
| **FULL** | The whole text was read (CAR: all 5 pages). |
| **KEY** | The full PDF text was downloaded and searched for the features in the matrix (bandit / best-arm / UCB / fixed-confidence / PAC / adaptive / budget / prefix / cache / replay), and the abstract, problem definition and method sections were read. Not every appendix was read. |
| **THM** | The specific theorem statements cited below were read in the source. |
| **ABS** | Only the abstract / search-result metadata was seen. Matrix cells for such papers are "Unclear" unless the abstract is explicit. |

## 1. The five supplied references

### 1.1 Garivier & Kaufmann — *Optimal Best Arm Identification with Fixed Confidence* (arXiv:1602.04589) — FULL-THM
* **Authors / dates.** Aurélien Garivier, Emilie Kaufmann. v1: 15 Feb 2016; v2: 1 Jun 2016. Published at COLT 2016.
* **Problem.** Fixed-confidence best-arm identification (BAI) in one-parameter bandit models with a unique best arm.
  A strategy is δ-PAC if it stops almost surely and returns a wrong arm with probability ≤ δ for every model in the class.
* **Verified results used here.**
  * *Theorem 1 (lower bound).* For any δ-PAC strategy and any model μ in the class, E[τ_δ] ≥ T\*(μ)·kl(δ,1−δ), with
    T\*(μ)⁻¹ = sup_w inf_{λ∈Alt(μ)} Σ_a w_a d(μ_a, λ_a). Asymptotically liminf E[τ_δ]/log(1/δ) ≥ T\*(μ).
  * *Track-and-Stop.* Tracking sampling rule + Chernoff stopping rule; Proposition 12 gives an exploration rate
    log(C t^α/δ) that is δ-PAC for any sampling rule in exponential families; Theorem 14 gives
    limsup_{δ→0} E[τ_δ]/log(1/δ) ≤ α T\*(μ). For Bernoulli arms they note β(t,δ)=log(2(K−1)t/δ) is δ-PAC (their Thm 10).
  * They explicitly caution that "optimal" should not be used for bounds that match a lower bound only up to a multiplicative constant.
    **We therefore never call AFCR "sample-optimal"; see §6 and `RESEARCH_STATUS.md`.**
* **Agent-related?** No. Not an agent paper; no replay, no automata, synthetic bandit experiments.

### 1.2 Zhang et al. — *Which Agent Causes Task Failures and When?* (arXiv:2505.00212) — KEY
* **Authors.** Shaokun Zhang, Ming Yin, Jieyu Zhang, Jiale Liu, Zhiguang Han, Jingyang Zhang, Beibin Li, Chi Wang, Huazheng Wang, Yiran Chen, Qingyun Wu.
  v1 30 Apr 2025, v2 23 May 2025, v3 2 Jun 2025 (camera-ready; ICML 2025 per the later citations in 2606.08275).
* **Contribution.** Defines automated failure attribution (find the responsible agent *i\** and decisive error step *t\**) and the **Who&When** dataset
  (failure logs from 127 multi-agent systems, algorithm-generated + hand-crafted). Three LLM-judge methods: all-at-once, step-by-step, binary search.
  Best reported: ≈53.5 % agent-level, ≈14.2 % step-level accuracy; some methods below a random baseline.
* **Attribution unit.** Agent and step. **No counterfactual replay and no statistical estimator**: all methods are LLM judgments over the log.
  Binary search is an LLM-driven halving of the log, *not* statistical adaptive sampling.
* **Correction to the project brief.** The brief suggests "existing failure attribution may use budget-limited Monte Carlo Shapley estimation". That is **not** Who&When; the Shapley estimator is in CAR (§1.3).

### 1.3 Shah — *Causal Agent Replay: Counterfactual Attribution for LLM-Agent Failures* (arXiv:2606.08275) — FULL
* **Author / dates.** Jaineet Shah. v1 only: 6 Jun 2026. CC BY 4.0. Code link in paper: github.com/jaineet17/causal-agent-replay (**repository not inspected by us**).
* **Problem / unit.** Which *step* caused the failure; trajectory modelled as an SCM τ=(s₀,(a₁,o₁),…,(a_n,o_n),y), y∈[0,1].
* **Interventions.** Five do-operations: `do_resample` (re-draw a_k from the *same* policy — the "null intervention"), `do_action`, `do_observation`, `do_context`, `do_policy`.
* **Estimator.** Contrastive single-step: hold steps [0,k) at factual actions, `do_resample(k)`, run forward **K times (fixed per step)**; Wilson interval on the proportion, bootstrap interval on the difference.
  Culprit = **latest step whose effect CI still excludes zero** ("point-of-commitment" rule), to cope with the run-forward confound (resampling an early step re-rolls the genuinely pivotal later step).
* **Shapley.** Monte-Carlo permutation Shapley with antithetic pairing, "budget-bounded with a circuit breaker", normal-approximation CIs; v(S) deliberately **not cached** across permutations (caching would collapse variance and report false confidence); truncated MC-Shapley deliberately avoided.
* **Allocation / stopping / guarantee.** Fixed K; **no adaptive allocation, no sequential stopping rule, no δ-PAC statement, no sample-complexity theorem** (none appear in the text).
* **Evaluation.** Synthetic SCMs with planted truth only (3-step pivotal SCM; two-step AND-failure with Shapley φ₀=0.44, φ₁=0.45, efficiency sum 0.909 vs analytic 0.91). No real benchmark results; the Who&When ≈14 % figure is quoted from prior work.
* **Limitations stated.** Contrastive effect is a *total* effect through a stochastic continuation (common random numbers across branches left as future work); judge-based outcome functions add noise; real tools with side effects out of scope; Shapley exponential in worst case.
* **Overlap with this proposal.** **High on the replay/estimand side** (same-policy resampling interventions, outcome distributions with CIs, the run-forward confound, a "locus" target different from argmax).
  **None on** fixed-confidence stopping, adaptivity, prefix-level information reuse or automata. Its explicit "do not cache" stance is a direct warning for our prefix-reuse extension (see §5).

### 1.4 Zhang et al. — *AgenTracer: Who Is Inducing Failure in the LLM Agentic Systems?* (arXiv:2509.03312) — KEY
* **Authors.** Guibin Zhang, Junhao Wang, Junjie Chen, Wangchunshu Zhou, Kun Wang, Shuicheng Yan. v1 3 Sep 2025; v2 4 Sep 2025.
* **Method.** Annotation pipeline: **counterfactual replay with oracle-guided correction** (an analyzer agent, given the ground-truth solution, proposes a minimally invasive corrected action a′_t for each step t, then the rest is re-simulated) + programmatic fault injection; TracerTraj (~2k trajectories); AgenTracer-8B trained with multi-granular RL.
* **Culprit definition.** The decisive step is the **earliest** step t whose oracle rectification flips failure to success: argmin_{t∈C(τ)} t.
* **Allocation / guarantee.** Sequential scan over all steps; **no statistical allocation, no confidence statement, no budget accounting** (0 hits for bandit/confidence/budget/prefix).
* **Evaluation.** Who&When + TracerTraj; reports gains up to 18.18 % over proprietary LLM judges (abstract). Code: no repository link found on the arXiv page.
* **Overlap.** Replay as an *annotation oracle*; second distinct culprit definition (earliest sufficient repair). AFCR's threshold targets (`first_above`) formalise this definition under sampling noise.

### 1.5 Feng, Sui, Hou, Wu, Cresswell — *Conformal Agent Error Attribution* (arXiv:2605.06788) — KEY
* v1 only: 7 May 2026, 10 pages main text (20 incl. appendices). Code: github.com/layer6ai-labs/conformal-agent-error-attribution (**not inspected**).
* **Method.** Filtration-based split-conformal prediction (left/right/two-way filtration) producing **contiguous sets of steps** that contain the decisive error with marginal coverage ≥ 1−α under exchangeability of calibration and test trajectories; Theorem 3.4 gives 1−α ≤ P[y\*∈C] < 1−α+1/(n+1).
* **No replay, no rollouts, no bandits** (0 hits). Needs labelled calibration trajectories and a scoring function g (LLM judges / fine-tuned Qwen3-1.7B).
* **Evaluation.** Who&When (184 real examples, MIT licence per the paper) + controlled error-injection datasets on GSM8K/MATH with DyLAN and MacNet trajectories; also uses sets for rollback.
* **Overlap.** Orthogonal. Its guarantee is *marginal coverage over trajectories* (needs exchangeability and calibration data); ours is a *per-trajectory identification guarantee* conditional on the replay model. They answer different questions and could be combined (conformal localisation → AFCR replay on the set).

## 2. Additional literature found and examined

| Paper | Evidence | One-line finding relevant to the gap |
|---|---|---|
| Ma et al., *Automatic Failure Attribution and Critical Step Prediction … Causal Inference* (arXiv:2509.08682) | KEY | Shapley + causal discovery (CDC-MAS) over *static* logs; reports up to 36.2 % step-level accuracy on Who&When/TRAIL (abstract-level number). Counterfactual *simulation* only for optimisation suggestions. No sequential statistics. |
| Lin et al., **REFLECT** (arXiv:2606.09071; ICML 2026 FAGEN workshop) | KEY | Diagnose → controlled replay with a targeted patch → outcome flip used as evidence to refine attribution. Heuristic, LLM-driven feedback loop; no bandit/PAC terms (0 hits). |
| Bonagiri et al., **CausalFlow** (arXiv:2605.25338) | KEY | Causal Responsibility Scores via step-level intervention + minimal counterfactual repairs; no sequential/bandit machinery (0 hits). |
| Cha, Weon, Kang, **Knowledge-Based Zero-Replay Debugging** (arXiv:2606.14805 v2) | KEY | Explicitly names the cost problem: replay cost grows linearly with candidates. Their answer is *prediction without replay* (learned ranker over a trace knowledge graph, budget-bounded agenda, calibrated against a deterministic oracle on 37 trace families). It does **not** run adaptive stochastic replay or give a statistical stopping rule. |
| Li, Song, Yao, Li, **GCJR / Minimal Repair Family Recovery** (arXiv:2608.29228 v2) | KEY | Set-valued target (jointly necessary vs alternative singleton repairs); graph-constrained candidate enumeration cuts replay calls 56.3→25.3 on a 120-DAG benchmark (deterministic outcomes, "exact for fixed replay outcomes"). A different route to lower replay cost; no confidence sequences. Handles *joint causes*, which we do not. |
| Luan et al., **SymTrace** "Repair or Resample?" (arXiv:2608.25920) | KEY (abstract + keyword scan) | Snapshot/replay infrastructure that reconstructs the execution *prefix* from logs to isolate repair from stochastic resampling; uses Wilson CIs, bootstrap and Holm correction **for evaluation**, not for sampling control. Its "prefix" is about replay *fidelity*, not about sharing rollouts across candidates. |
| Ma et al., **DoVer** (arXiv:2512.06749) | ABS | Intervention-driven debugging, hypothesis validation by interventions in Magentic-One/AG2 — details of allocation not verified. |
| Xia et al., **AgentLocate** (arXiv:2607.07989, COLM 2026) | KEY | LLM hypothesis + multi-perspective verification; no bandit terms. |
| Chen et al., **TraceElephant** benchmark (arXiv:2604.22708) | KEY | Benchmark for failure attribution; no replay-allocation content. |
| Pothuru, **AgenticRAG-FP** (arXiv:2608.20627) | KEY | Fault-injection benchmark with a fixed small probe budget (4); no sequential statistics. |

### 2.1 Fixed-confidence pure-exploration methods we build on
| Source | Evidence | What we use |
|---|---|---|
| Kaufmann & Kalyanakrishnan, *Information Complexity in Bandit Subset Selection* (COLT 2013, PMLR 30) | THM | **KL-LUCB** and its exploration rate: β(t,δ)=log(k₁Ktᵅ/δ)+log log(k₁Ktᵅ/δ) with α>1, k₁>2e+1+e/(α−1)+(e+1)/(α−1)² (their Theorem 1); KL-confidence bounds u_a, l_a from N_a·d(p̂_a,q)≤β; Theorem 3 gives a high-probability sample-complexity bound C₀(α)H\*_{ε,c} log(k₁K(H\*_{ε,c})ᵅ/δ). α=1.1 ⇒ k₁≈405.5. |
| Kalyanakrishnan, Tewari, Auer, Stone, *PAC Subset Selection in Stochastic Multi-armed Bandits* (ICML 2012) | ABS | Original LUCB (sample the empirical best and the strongest challenger). |
| Jamieson, Malloy, Nowak, Bubeck, *lil' UCB* (COLT 2014, arXiv:1312.7308) | ABS | LIL-based confidence bounds; matches an LIL lower bound up to constants. Not implemented. |
| Even-Dar, Mannor, Mansour, *Action Elimination and Stopping Conditions …* (JMLR 7, 2006) | ABS | Confidence-interval elimination, (n/ε²)log(1/δ) for ε-optimal arm, matching Mannor–Tsitsiklis (2004) up to constants. We implement an elimination variant (AFCR-SE) because its sample-complexity proof is short enough to include in full. |
| Russo, Song, Pacchiano, *Pure Exploration with Feedback Graphs* (AISTATS 2025, arXiv:2503.07824) | ABS | Fixed-confidence BAI where one pull can reveal side observations of other arms (graph feedback) — the closest *generic* statistical template for Prefix-Aware AFCR. Our reuse mechanism is a concrete, state-dependent instance, so we claim no generic novelty there. |

## 3. Comparison matrix (summary; full evidence in `novelty_matrix.csv`)

Legend: Y = Yes, P = Partial, N = No, U = Unclear (could not establish). "N" is only used where the full text was searched (KEY/FULL/THM).

| Paper | Step-level | CF replay | Adaptive alloc. | Fixed-conf. stop | δ-PAC | Prefix-aware reuse | Automata | Proven sample-compl. | Real agent benchmarks |
|---|---|---|---|---|---|---|---|---|---|
| Garivier–Kaufmann 2016 | N (not agent) | N | **Y** | **Y** | **Y** | N | N | **Y** | N |
| Who&When 2025 | **Y** | N | N | N | N | N | N | N | **Y** |
| CAR 2026 | **Y** | **Y** | N | N | N | N | N | N | N (synthetic SCMs) |
| AgenTracer 2025 | **Y** | **Y** (oracle) | N | N | N | N | N | N | **Y** |
| Conformal 2026 | P (step *sets*) | N | N | N | P (coverage, not δ-PAC) | N | N | N | **Y** |
| Ma et al. 2025 | **Y** | P | N | N | N | N | N | N | **Y** |
| REFLECT 2026 | **Y** | **Y** | P (heuristic) | N | N | N | N | N | **Y** |
| CausalFlow 2026 | **Y** | **Y** | N | N | N | N | N | N | **Y** |
| Zero-Replay 2026 | **Y** (event) | P (oracle for calibration) | P (static budgeted agenda) | N | N | N | P (event graph) | N | U |
| GCJR 2026 | P (event sets) | **Y** | P (deterministic pruning) | N | N (deterministic exactness) | N | P (dependency DAG) | N | P (24-case pilot) |
| SymTrace 2026 | P | **Y** | N | N | N | P (prefix *fidelity*) | N | N | **Y** |
| DoVer 2025 | **Y** | **Y** | U | U | U | U | U | U | **Y** |
| **AFCR (this work, proposed)** | **Y** | **Y** | **Y** | **Y** | **Y** (core; assumptions stated) | **P** (valid under Markov + exact match; proof in paper) | **Y** | **P** (SE proven; LUCB cited; ours empirical) | **N so far** (pending ALFWorld/HotpotQA) |

## 4. Outcome of the novelty assessment

> **Outcome B — the intended gap exists only in a narrower formulation.**

*What is NOT novel:* counterfactual replay for step attribution (AgenTracer, CAR, CausalFlow, REFLECT, DoVer, SymTrace); same-policy resampling interventions and outcome distributions with CIs (CAR); naming replay cost as a bottleneck (Zero-Replay, GCJR); fixed-confidence BAI, LUCB-style sampling and KL confidence bounds (the 2012–2016 bandit literature); side-observation pure exploration (Russo et al. 2025).

*What the review did not find* (a statement about *our search*, not a proof of absence — the literature on this topic is moving at roughly weekly pace): a method that (i) treats each candidate step as an arm under **stochastic** replay, (ii) attributes with a **sequential stopping rule carrying a per-trajectory δ-correctness statement and an explicit abstention outcome**, and (iii) shares rollouts across candidates under a **proved validity condition** (strong Markov property + exact (state, action) match), together with (iv) a **formally specified automaton substrate with exactly computable ground truth** for validating such guarantees.

*Narrowed claim used throughout the project:* "We study fixed-confidence step attribution under stochastic replay. The δ-correctness statement is conditional on the replay model (Assumptions A1–A6); we do not claim it transfers to real LLM agents unless those assumptions are checked."

*Why not outcome C:* none of the 14 agent-attribution papers examined (13 of them at KEY/FULL level; DoVer at ABS level) reports sequential, confidence-controlled allocation of replays. *Why the risk remains:* ABS-level papers (DoVer, LUCB/lil'UCB originals, Russo et al.) were not read in full, and 2026 arXiv postings after 2026-10-23 cannot be excluded. Treat "novelty" as **provisional** until a final search is repeated before submission.

## 5. Consequences for the design (decisions taken because of the review)

1. **Estimand.** Three culprit definitions exist in the literature: argmax-repair (this proposal), *earliest* sufficient repair (AgenTracer), *latest* step with a significant effect (CAR). AFCR therefore implements a **target-agnostic confidence-sequence engine** with three decision rules (`argmax_eps`, `first_above(θ)`, `last_above(θ)`), instead of hard-wiring argmax.
2. **Resampling confound.** CAR's observation that an early irrelevant step re-rolls the pivotal one is reproduced exactly in our automaton substrate (μ_t for t<c is lifted by the chance of avoiding the fault again). The paper reports μ_t profiles from exact dynamic programming so the effect is visible.
3. **Caching warning.** CAR avoids caching coalition values because it would give false confidence. Our prefix-reuse extension therefore (a) is allowed only through an explicit match condition derived from the strong Markov property, (b) is validated by a *naive-sharing negative control* that is shown to be biased, and (c) is disabled in the guaranteed algorithm if the Markov/exact-match assumptions fail.
4. **Joint causes** (GCJR, CAR-Shapley) are out of scope; they are listed under limitations and future work.
5. **Baselines to reproduce.** Only CAR's *estimator rule* is re-implemented (from the paper's text; **not** from the authors' code) as the `car_fixed_k` baseline, clearly labelled as such. AgenTracer, Who&When judges, conformal methods, REFLECT etc. need LLMs and labelled data and are **not reproduced**; no comparative numbers from them are reported.

## 6. Naming discipline

"Sample-optimal" is **not** used as a claim. Garivier & Kaufmann (§1.1) define asymptotic optimality (limsup E[τ_δ]/log(1/δ) = T\*(μ)). Our algorithms are (i) δ-correct (proved), (ii) *H-efficient up to logarithmic factors* for the elimination variant (proved), and (iii) empirically compared with uniform allocation. The title keeps the proposal's wording ("Sample-Optimal …") only because the user specified it; the manuscript and website carry a visible note that the title states the *research objective*, not a theorem.
