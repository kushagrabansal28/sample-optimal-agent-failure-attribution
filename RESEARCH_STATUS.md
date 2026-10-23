# RESEARCH_STATUS

_Authors: Kushagra Yogendra Bansal (25bde0080) and Kartik Kesharwani (25bde0053). Last generated from the result files; all numbers below are computed, not typed._

## Verified facts
* The five supplied papers exist; their metadata and (for CAR in full, others by full-text search and theorem reading) contents were verified on 2026-10-23 — see `research/related_work.md` (evidence level per paper).
* CAR: fixed K rollouts per step, Wilson + bootstrap intervals, point-of-commitment rule, budget-bounded MC-Shapley, **no** stopping rule / δ-PAC / sample-complexity result, synthetic SCMs only.
* Who&When uses LLM judges (no replay, no Shapley). AgenTracer: decisive step = earliest oracle-flip. Conformal paper: marginal coverage, no replay.
* KL-LUCB exploration rate β(t,δ)=ln(k₁Ktᵅ/δ)+ln ln(·) with k₁>2e+1+e/(α−1)+(e+1)/(α−1)² (Kaufmann & Kalyanakrishnan 2013, Thm 1) was read in the source.
* Tests: **179/179 backend** and **46/46 frontend** pass. The exact DP values agree with Monte Carlo; matched prefix-reuse observations are unbiased and naive-credited observations are biased (tested and reported in §10.8 of the paper).
* Experiments: 6,518 synthetic trials in 12 groups; 0 wrong answers among 3,620 certified guaranteed trials; LUCB cost is 15–24× the Garivier–Kaufmann lower bound.

## Unverified assumptions
* Novelty (outcome B) is provisional: DoVer, the LUCB / lil'UCB originals and Russo et al. were read at abstract level; later arXiv postings are unknown.
* ALFWorld (MIT) and HotpotQA (CC BY-SA 4.0) licences were read from secondary sources, not the official repositories.
* The OpenAI-compatible model provider has never been exercised.

## Proposed contributions
Fixed-confidence replay with abstention and three decision rules; a proved exact-match prefix-reuse condition with an unbiasedness test and a negative control; a 48/64/96-state automaton benchmark and a tool-agent world with exact ground truth.

## Implemented components
Nine formal models and the 48/64/96-state agent automaton; statistics (KL bounds, four confidence sequences, T* and H); replay environments (bandit, automaton, tool agent, text game); targets (argmax-ε, first/last-above-θ); strategies (LUCB, uniform, random, successive elimination, equal/random budget, CAR-style, oracle); the engine with abstention; valid and naive prefix sharing; model providers; ALFWorld/HotpotQA adapters; experiment suite with paired statistics; FastAPI backend; React + TypeScript website; 21 figures; paper, report, experiments log and slides.

## Experiments completed
All twelve synthetic groups (main, gap/K/δ sweeps, stress, size, fault probability, reconstruction noise, ablations, budget curve, tool agent, targets) at 30 trials per cell (60 for bandit cells).

## Experiments pending
ALFWorld; HotpotQA; any run with a real LLM agent; reproduction of related-work baselines other than the CAR-style rule; browser end-to-end tests; larger trial counts; 64/96-state sweeps beyond the size group.

## Known theoretical limitations
Theorem 1 holds under A1–A6 (a statement about the replay model); the sample-complexity bound is proved for successive elimination only (LUCB + stack bound: empirical); no lower-bound match and no optimality claim; the stack bound is conservative (0 errors observed even on stress instances); joint causes and non-Markov LLM state are out of scope.

## Remaining work before publication
Run Stages C and D with a fixed open model; verify DoVer / Russo et al. full texts and repeat the literature search; reproduce at least one more published baseline; add confidence sequences with LIL-type growth and measure the gap to the lower bound; handle joint causes; independent review of the proofs; larger-scale experiments; browser end-to-end tests.
