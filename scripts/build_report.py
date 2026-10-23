"""Write report/technical_report.md, report/experiments.md, RESEARCH_STATUS.md, DELIVERY_SUMMARY.md.
Reuses the verified sections of the paper and docdata tables; every number is computed from the result files."""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import build_paper as BP  # noqa: E402
import docdata as D  # noqa: E402

ROOT = D.ROOT
H, T, FT = BP.H, BP.T, BP.FT
AUTH = BP.AUTH
PAPER = BP.PAPER

# ---------------------------------------------------------------------------------------- paper section extraction
_parts = re.split(r"\n(?=## )", PAPER)
SEC = {}
for part in _parts:
    m = re.match(r"## (\d+|Appendix [A-D])[.\s]", part)
    if m:
        SEC[m.group(1)] = part


def P(key: str, demote: bool = True) -> str:
    body = SEC[key].split("\n", 1)[1]
    body = re.sub(r"^### \d+(\.\d+)*\.? ", "### ", body, flags=re.M)
    return body.replace("](figures/", "](../results/figures/").strip() + "\n"


def fig(n, cap, name):
    return f"![Figure {n}. {cap}](../results/figures/{name}.png)\n"


def csv_rows(name):
    with (ROOT / "research" / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def novelty_table() -> str:
    feats = [("step_level_attribution", "Step"), ("counterfactual_replay", "Replay"), ("adaptive_allocation", "Adaptive"), ("fixed_confidence_stopping", "Fixed-conf."),
             ("delta_pac_guarantee", "δ-PAC"), ("prefix_aware_information_reuse", "Prefix reuse"), ("formal_automata_representation", "Automata"),
             ("proven_sample_complexity_bound", "Compl. bound"), ("real_agent_benchmarks", "Real bench.")]
    h = "| Paper | Read | " + " | ".join(l for _, l in feats) + " |\n|---|---|" + "---|" * len(feats) + "\n"
    for r in csv_rows("novelty_matrix.csv"):
        h += f"| {r['short_name']} | {r['read_depth']} | " + " | ".join(r[k] for k, _ in feats) + " |\n"
    return h


def literature_table() -> str:
    h = "| Id | Title | Authors | First publication | Venue / status | Evidence |\n|---|---|---|---|---|---|\n"
    for r in csv_rows("related_work.csv"):
        a = r["authors"].split(";")
        auth = a[0].strip() + (" et al." if len(a) > 1 else "")
        h += f"| {r['id']} | {r['title']} | {auth} | {r['first_publication']} | {r['venue']} | {r['evidence_level']} |\n"
    return h


def test_inventory() -> str:
    h = "| Test module | Passed | Failed | Tests |\n|---|---|---|---|\n"
    for m, v in T.get("modules", {}).items():
        names = ", ".join(t["name"].replace("test_", "") for t in v["tests"])
        h += f"| `{m}` | {v['passed']} | {v['failed']} | {names} |\n"
    return h


def api_table() -> str:
    from afcr.api.app import app
    spec = app.openapi()
    h = "| Method | Path | Purpose |\n|---|---|---|\n"
    for p, ms in sorted(spec["paths"].items()):
        for m, d in ms.items():
            h += f"| {m.upper()} | `{p}` | {d.get('summary', '').replace('_', ' ')} |\n"
    return h


REPORT = f"""---
title: "Technical Report: Sample-Optimal Culprit Identification for Agent Failures"
authors: "{AUTH}"
---

# Technical Report — Sample-Optimal Culprit Identification for Agent Failures: Fixed-Confidence Attribution with Automata-Aware Sequential Replay

**{AUTH}**

*Reading guide.* This report describes the implemented system, the verified literature review, the formal development and every experiment. Sections marked "(from the paper)" reproduce the corresponding material of `paper/main.md`; **section references of the form §x.y inside such material refer to the paper**. All measured numbers are computed from `results/raw` and `results/processed`; all results are **synthetic**. ALFWorld and HotpotQA were **not** run. The title states a research objective; no optimality is claimed.

## 1. Executive summary

{BP.abstract}

**What exists.** (i) A verified literature review with an evidence-level record per paper. (ii) Nine formal models and a 48/64/96-state agent automaton, all unit-tested. (iii) A fixed-confidence replay engine with three decision rules, an abstention outcome and an exact-match prefix-reuse extension. (iv) A controlled tool-using agent with exact ground truth. (v) A reproducible synthetic experiment suite (about 6,500 trials) with paired statistics. (vi) A FastAPI backend and a React + TypeScript website that runs the real algorithm. (vii) {T['total']} backend tests and {FT['total']} frontend tests, all passing. **What does not exist:** benchmark runs on real LLM agents, a proof of sample-complexity for LUCB with the stack bound, any optimality result, joint-cause handling.

## 2. Research motivation

Modern agents carry out long sequences of reasoning, planning, tool calls, browser operations, memory updates and external actions. A task can fail at its conclusion because of a decision made much earlier: the agent selects an incorrect subgoal, searches the wrong resource, misreads a tool response, writes a wrong value into memory and then reasons correctly from corrupted state. The *last* action is the symptom, not the cause. Practitioners need the **decisive failure-inducing intervention**, and distinguishing it from correlated, downstream or merely symptomatic steps requires intervention rather than observation.

Naive causal attribution intervenes at every candidate step and re-runs the agent. With $T$ candidate steps and a stochastic agent this is $T\\times$(number of replays per step) full executions. Uniform allocation spends a predetermined number of replays on every step, ignoring that some steps are clearly harmless, some are decisive and some are ambiguous. This project investigates whether *adaptive statistical allocation*, stopped by a valid statistical condition and combined with the structure of the execution history, can reduce attribution cost without sacrificing the reliability of the result. The hypothesis is **not assumed true**: the experiments were designed to be able to support, qualify or reject it, and they include conditions (ties, small gaps, reconstruction noise, invalid sharing) in which it fails.

## 3. Problem statement

{P('3')}
## 4. Literature review

Each of the five supplied references was fetched and read (not only the abstract). The first-publication dates and version histories were taken from the arXiv records on 2026-10-23; findings below were taken from the full texts. Reading depth is recorded per paper: FULL (read in full), THM (theorem statements checked), KEY (full text downloaded and searched for bandit / best-arm / UCB / fixed-confidence / PAC / adaptive / budget / prefix / cache / replay terms, with abstract, problem definition and method sections read), ABS (abstract only).

{literature_table()}
**Supplied references — key verified findings.**

* *Garivier and Kaufmann (2016).* Fixed-confidence BAI; Theorem 1 gives $\\mathbb E[\\tau_\\delta]\\ge T^\\star(\\mu)\\,\\mathrm{{kl}}(\\delta,1-\\delta)$ for every δ-PAC strategy; Track-and-Stop with a Chernoff stopping rule is asymptotically optimal ($\\limsup_{{\\delta\\to0}}\\mathbb E[\\tau_\\delta]/\\log(1/\\delta)\\le\\alpha T^\\star$). The authors warn that "optimal" should not be used for bounds that match only up to a constant factor.
* *Who&When (Zhang et al., 2025).* Defines the task and benchmark (127 systems). Three LLM-judge methods (all-at-once, step-by-step, binary search); best step-level accuracy about 14.2 %. **No replay and no Shapley estimator** — the brief's attribution of Monte-Carlo Shapley to this paper is a mis-attribution (the estimator is CAR's).
* *CAR (Shah, 2026).* Five do-operations (`do_resample`, `do_action`, `do_observation`, `do_context`, `do_policy`); contrastive estimator with a fixed number K of rollouts per step, Wilson and bootstrap intervals, a *point-of-commitment* locus rule (latest step whose effect CI excludes zero), a budget-bounded Monte-Carlo Shapley estimator that deliberately avoids caching, validated only on synthetic structural causal models. No stopping rule, no δ-PAC statement, no sample-complexity result, no prefix reuse.
* *AgenTracer (Zhang et al., 2025).* Counterfactual replay as an *annotation oracle*: an analyzer agent with access to the ground truth proposes a corrected action at each step; the decisive step is the **earliest** step whose rectification flips the outcome. Sequential scan; no confidence control.
* *Conformal Agent Error Attribution (Feng et al., 2026).* Filtration-based split-conformal prediction of **contiguous sets** of steps with marginal coverage under exchangeability (Theorem 3.4: $1-\\alpha\\le\\Pr[y^\\star\\in C]<1-\\alpha+1/(n+1)$); no replay or rollouts.

**Additional literature found and examined:** Ma et al. 2025 (causal discovery and Shapley over static logs), REFLECT, CausalFlow, Knowledge-Based Zero-Replay (explicitly names replay cost as the bottleneck and answers it by *prediction*), GCJR (set-valued repair families; deterministic pruning of replay calls), SymTrace ("Repair or Resample?": prefix *reconstruction for replay fidelity*, Wilson/bootstrap/Holm in the *evaluation*), DoVer (abstract-level), AgentLocate, TraceElephant, AgenticRAG-FP; and, on the statistics side, Kalyanakrishnan et al. 2012 (LUCB), Kaufmann and Kalyanakrishnan 2013 (KL-LUCB, Theorems 1 and 3 read), Jamieson et al. 2014 (lil'UCB), Even-Dar et al. 2006 (action elimination) and Russo, Song and Pacchiano 2025 (pure exploration with feedback graphs).

## 5. Research gap analysis

The following comparison matrix was filled from the evidence above (full text where possible; "No" is used only where the full text was searched; "Unclear" where only an abstract was available).

{novelty_table()}
**Three possible outcomes.** (A) The intended gap is supported. (B) The gap exists only in a narrower formulation. (C) Existing work already substantially addresses the gap. **Our assessment is B.** Replay for attribution (AgenTracer, CAR, CausalFlow, REFLECT, DoVer, SymTrace), same-policy resampling with confidence intervals and the run-forward confound (CAR), fixed-confidence best-arm identification with LUCB and KL bounds, and pure exploration with side observations are all established. What we did not find is a method that treats each candidate step as an arm under **stochastic** replay, certifies with a **per-trajectory δ-correctness statement and an explicit abstention outcome**, and shares rollouts across candidates under a **proved** validity condition on a substrate with **exactly computable ground truth**. This is a statement about our search, not a proof of absence; DoVer, the LUCB and lil'UCB originals and Russo et al. were read at abstract level only, and the field is moving quickly, so the search must be repeated before submission.

**Design consequences of the review.** (1) Three culprit definitions exist (argmax-repair, *earliest* sufficient repair, *latest* significant step), so the engine implements all three as decision rules over the same confidence sequences. (2) CAR's run-forward confound is reproduced and visible in exact numbers (Figure 2). (3) CAR's refusal to cache coalition values motivates the strict match condition and the negative control for prefix reuse. (4) Joint causes (GCJR, CAR-Shapley) are out of scope. (5) Only CAR's *estimator rule* is re-implemented (from the paper's text, not its code); no other related-method results are reported.

{fig(12, "The 48-state automaton.", "fig12_automaton_48_states")}

## 6. Mathematical formulation (from the paper)

{P('3')}
{P('4')}
## 7. Models of Computation: overview

{P('5')}
## 8. DFA implementation

`afcr.automata.dfa.DFA` implements $M=(Q,\\Sigma,\\delta,q_0,F)$ with a **total** transition function. Construction validates that the start and accepting states belong to $Q$ and that every transition refers to known states and symbols; a missing pair raises an error unless `complete_with_sink=True`, in which case an explicit non-accepting sink state is added and flagged so that it is *not* counted as a logical state of the modelled system. The class provides step-wise execution with a full trace (state, symbol, next state per step), acceptance, final-state queries, forward and backward reachability (`reachable`, `can_reach`), a transition-table export, enumeration of all words up to a length, and a bounded equivalence check. For the agent benchmark, `AgentModel.to_dfa()` builds the DFA skeleton from the specification by keeping, for every (state, action) pair, the **most likely** successor; the result has 48 logical states plus the sink and a total transition function.

**Tests** (`tests/test_automata.py`): determinism and totality are asserted on a hand-built parity automaton; acceptance on accepted/rejected words; missing transitions raise; the sink completion makes δ total while `logical_states()` still returns the original set; unknown symbols raise `AutomatonError`; the 48-state DFA view is total, has an explicit sink, has 48 logical states and can reach both accepting and rejecting terminals.

{fig(6, "A DFA recognising an even number of a's.", "fig06_dfa")}

## 9. NFA and ε-NFA implementation

`ENFA` stores $\\delta:Q\\times(\\Sigma\\cup\\{{\\varepsilon\\}})\\to2^Q$; `NFA` is the ε-free subclass (constructing an `NFA` with an ε-transition raises). Execution maintains the **active-state set**; `eps_closure` and `eps_closure_steps` return the closure and the growing sets for visualisation; `to_nfa()` performs standard ε-removal (and adds states whose closure meets $F$ to the accepting set); `to_dfa()` is the subset construction over ε-closures with the empty set as an explicit dead state. A word is accepted iff the final active set meets $F$.

The agent specification yields an NFA (all positive-probability successors, probabilities forgotten) and an ε-NFA in which the **silent self-correction ("heal") edges** of corrupted states are ε-moves; in the website's laboratory the ε-closure of a corrupted state shows which clean states can be reached silently. *Nondeterminism of an NFA is a formal device (some path accepts); it is not the randomness of LLM sampling*, which is modelled by probabilities in the probabilistic automaton.

**Tests:** active-set transitions, acceptance (`ends in ab`), equivalence of NFA, its subset-construction DFA and (for the ε-NFA) the ε-free NFA over **all** words up to length 6–7, ε-closure on a chain of ε-moves, rejection of ε in the input alphabet.

{fig(7, "NFA active-state sets on the word aab.", "fig07_nfa_active_sets")}
{fig(8, "ε-NFA closure.", "fig08_enfa_closure")}

## 10. Probabilistic automata

`ProbabilisticAutomaton` stores a distribution over successors for every enabled (state, symbol) pair. Construction **validates normalisation** (probabilities in $[0,1]$, row sums within $10^{{-9}}$ of 1, known states); an unenabled pair means the symbol is *blocked* (the run cannot accept). The exact semantics is $P(w)=e_{{q_0}}^\\top M_{{a_1}}\\cdots M_{{a_n}}\\mathbf 1_F$ (`acceptance_probability`, `blocked_mass`); runs can be sampled with a seeded generator (reproducible: identical seeds give identical traces) and `monte_carlo_acceptance` returns the estimate with a Wilson interval and the sample size. This formalism is clearly distinct from NFA nondeterminism: an NFA asks *whether* a path accepts, a PA asks *how likely* acceptance is.

In the agent benchmark the policy is the *input* of the PA (action symbols) and the environment kernel is its randomness; the full agent (policy ⊗ kernel) is a time-augmented Markov chain whose success probability is computed exactly by backward induction and was validated against Monte Carlo ({T['total']} tests include a statistical check at 4σ).

{fig(9, "A probabilistic automaton.", "fig09_probabilistic_automaton")}

## 11. Labelled transition systems

`LTS` represents execution as labelled transitions $s\\xrightarrow{{a}}s'$ with an optional probability and a *category* drawn from {{reasoning, tool_use, observation, state_update, validation, recovery, success, failure}}. It supports trace enumeration, label-sequence execution (set of reachable states), forward and backward **reachability**, **deadlock detection** (reachable non-terminal states without successors), reachability of accepting and rejecting states and the extraction of a **counterfactual branch** (the alternative transitions out of a state on a path). `AgentModel.to_lts()` exports the 48-state model with transition weights $\\pi(a|q)P(q'|q,a)$; the tests assert that it has no deadlocks and that both outcomes are reachable.

## 12. Mealy and Moore machines

`Mealy` attaches outputs to transitions, `Moore` to states; both are total. A small tool-call controller demonstrates the Mealy-specific behaviour that **the same state emits different outputs for different inputs** (state `calling` emits `proceed` on `ok` and `retry` on `error`). `Mealy.to_moore` performs the required **state expansion** — Moore states are (state, last output) pairs reachable from the start, at most $|Q||\\Gamma|+1$ — with a designated initial output; `Moore.to_mealy` needs no expansion. By convention a Moore machine emits $n+1$ outputs for $n$ inputs; the tests check that the Moore output sequence minus the initial output equals the Mealy output sequence on a test word, and that a Moore machine missing an output is rejected.

## 13. PDA and Turing-machine demonstrations

**PDA.** `PDA` is a nondeterministic pushdown automaton whose transitions $(q,a,X,q',\\gamma)$ are classified as push, pop or no-op by their net stack effect; execution is a breadth-first search over configurations with bounds on the stack height and the number of expanded configurations (a *simulator* bound; the model itself is unbounded) and returns the shortest accepting computation with the stack before and after every step. Two machines are provided: balanced call/return nesting and **typed** tool nesting (`open_search … end_search`, `open_calc … end_calc`). The test that *requires stack information* builds a DFA that tracks nesting depth only up to 3 and shows that it rejects the depth-5 word the PDA accepts — a finite-state machine cannot capture unbounded recursion.

**Turing machine.** `TuringMachine` simulates a bounded tape (`max_cells`) with a step limit (`max_steps`); the result status is one of accept, reject, `step_limit`, `tape_bound` or `halt_no_transition`, and a full configuration trace is kept. Demonstrations: binary increment (read/write/move) and a palindrome decider. **The bounds are implementation conveniences, not a claim that a bounded simulator reproduces the power of an unbounded machine; a run that hits a bound means "unknown", not "rejected".**

## 14. Agent environments

**The 48-state automaton** (Stage A). Eight states in each of six groups. The groups and their decision/fault states:

| Group | States (8 each) | Planted fault at the decision state |
|---|---|---|
| PLAN | start, parse, decompose, **select subgoal**, wrong subgoal, plan tools, revise, commit | `select_wrong` (default ε = 0.25) |
| OBSERVE | query, **choose resource**, wrong resource, results, browse, **interpret document**, misread, evidence | `search_wrong` (0.15), `misread` (0.20) |
| TOOL | **select tool**, invalid tool, args, call, ok, error, retry, parsed | `tool_invalid` (0.10) |
| MEMORY | read, **write**, corrupt, **reason**, flawed reasoning, draft, flawed draft, stopped early | `mem_corrupt` (0.15), `stop_early` (0.10) |
| VALIDATE | check, fail, feedback, **diagnose**, replan, retry tool, bad recovery, validate flawed | `bad_recover` (0.20) |
| TERMINAL | success (exact), success (partial), fail: plan / evidence / tool / memory / early stop / timeout | — |

Every state carries a unique id, a human-readable label, a semantic description, a kind (non-terminal / accepting / rejecting), a role (benign, decision, fault entry, corridor, recovery, terminal) and a note on its relation to attribution. `build_agent_model(n)` validates: at least 40 logical states (unique ids and labels), policies and kernels are probability distributions, the reference action of every state exists, no deadlocks, every state reachable, accepting and rejecting states reachable, terminal states absorbing. Corrupted states heal with probability 0.08 per step, leak to a failure terminal with probability 0.06 and are wrongly accepted by the validator with probability 0.10; environment noise and the horizon (twice the state count) are configurable. Exact quantities: the value table $V_t(q)$ by backward induction; $\\mu^{{\\mathrm{{rep}}}}_t$ and $\\mu^{{\\mathrm{{res}}}}_t$ for any trajectory.

**The tool-using agent** (Stage B). A controlled *order-total* task: look up price, quantity and shipping, write to memory, compute with a restricted arithmetic `calc` tool (integers with +, −, ×; no names, calls or attributes — tested), validate and recover. Six planted failure types:

| Failure type | Fault action | Effect |
|---|---|---|
| incorrect planning decision | `plan_bad` | later lookups hit a decoy record (downstream propagation) |
| invalid tool choice | `wrong_tool` | the call returns garbage |
| incorrect observation interpretation | `misread` | a value is stored wrongly |
| memory corruption | `mem_corrupt` | stored quantity corrupted |
| premature stopping | `stop_early` | shipping skipped |
| incorrect recovery | `bad_recover` | recovery fails, wrong answer submitted |

States are hashable snapshots (so a replay restores any prefix exactly), the stochastic kernel is explicit (so ground truth is exact by memoised backward induction) and a **deterministic variant** schedules one fault with probability 1 and removes noise and recovery, giving $\\mu_t\\in\\{{0,1\\}}$ and a unique culprit (tested for four fault phases).

## 15. Counterfactual replay design

**Protocols.** *Repair* forces the reference action $\\rho(q)$ at the chosen step; *resample* redraws the action from the agent's policy (CAR's null intervention). After the intervention the agent continues under its own stochastic policy; the outcome is the evaluator's $Y\\in\\{{0,1\\}}$ of the terminal state. A genuine intervention differs from relabelling a trace: the continuation is **re-executed** from the restored state; the website's trajectory explorer displays original and counterfactual traces side by side and shows that repeated replays of the same step can end differently.

**Interfaces.** `ReplayEnv.pull(arm, rng)` returns a `PullResult` (outcome, simulated steps, arms for which the rollout is a *valid* extra observation, the arms that *naive* sharing would credit — used only as a negative control). Implementations: `BanditEnv` (prescribed arm means; the statistical core), `AutomatonEnv` (arms are the steps of a failed trajectory; optional state-reconstruction noise, which disables sharing), `ToolAgentEnv` (snapshot restoration), and `TextGameReplayEnv` (action-history prefix replay for LLM agents on deterministic text environments such as ALFWorld/TextWorld and a retrieval QA loop). Eligibility can be restricted to decision states (a domain prior) and is tracked per arm. **Model providers** are behind an interface (`ScriptedProvider`, `RecordingProvider`, `OpenAICompatProvider`), so the statistical algorithm never imports a model SDK and a deterministic test mode needs no model. The OpenAI-compatible provider is **untested** (no key, no network in the test-suite).

**State reconstruction.** `state_reconstruction_noise` replaces the start state, with the given probability, by another non-terminal state of the same group, modelling an imperfect reproduction of the prefix (A1 violated). The estimand becomes the *noisy replay context*; the exact value of that context is computed and used as ground truth in §22.

## 16. The AFCR algorithm (from the paper)

{P('6')}
## 17. The prefix-aware extension (from the paper)

{P('7')}
## 18. Theoretical analysis (from the paper)

{P('8')}
## 19. Software architecture

{fig(13, "Package boundaries.", "fig13_software_architecture")}

| Package | Responsibility |
|---|---|
| `afcr.automata` | the nine formal models; `benchmark48` (48/64/96-state agent automaton, exact DP, DFA/NFA/ε-NFA/PA/LTS views) |
| `afcr.statistics` | Bernoulli KL and its inversion, four confidence sequences (with `anytime_valid` / `valid_under_sharing` flags), complexity quantities ($H$, $T^\\star$, the Garivier–Kaufmann bound) |
| `afcr.replay` | replay environments: bandit arms, automaton, tool agent |
| `afcr.attribution` | targets (decision rules), allocation strategies, the engine with abstention and accounting |
| `afcr.agents` · `afcr.benchmarks` | tool-agent world, model providers; ALFWorld / HotpotQA / text-game adapters |
| `afcr.experiments` · `afcr.evaluation` | spec execution, the experiment suite, metrics (Wilson, bootstrap), paired statistics (Wilcoxon, Holm) |
| `afcr.api` | FastAPI application consumed by the website |

**Design decisions.** (1) The *stopping rule* lives in the target and the confidence sequence, never in the sampling strategy, so no allocation rule can compromise δ-correctness. (2) The engine reports `guarantee_applies` and a human-readable reason on every result; fixed-budget strategies, non-anytime intervals and naive sharing switch it off. (3) Invalid input raises readable errors (δ outside (0,1), negative budgets, unknown strategies, combining the KL-LUCB rate with sharing). (4) Seeds are explicit everywhere. (5) Performance: a pure-Python scalar bisection path for per-pull interval updates made the full suite run in minutes.

**Test inventory ({T['passed']}/{T['total']} backend tests pass; `python -m pytest`).**

{test_inventory()}
## 20. Website architecture

The website is a React 18 + TypeScript + Vite single-page application served by the FastAPI backend (and proxied by `npm run dev`). Nothing it displays is hard-coded: every graph, trace, estimate, interval and table comes from an endpoint, and every simulated number is labelled *synthetic*. Libraries: React Router (nine routes, code-split), Framer Motion (page transitions, layout animations, reduced-motion aware), Recharts (charts with error bars), d3-zoom/d3-selection (graph pan/zoom), KaTeX (mathematics), Lucide (icons), and the Inter, Space Grotesk and JetBrains Mono variable fonts bundled locally.

**Design system.** Deep graphite/navy surfaces with restrained blue, cyan and violet accents; design tokens as CSS variables with a light theme; hairline borders and soft depth; a custom **dot-and-ring cursor** (spring-follow, hover/press/drag/text states) and a pointer-following **spotlight** on the background — both disabled on touch and for reduced motion; staggered reveals, animated counters, skeleton loaders, toasts and animated tabs/segmented controls; full keyboard access (focus rings, roving buttons, `aria` labels), responsive layouts (breakpoints at 1280, 1100, 960, 860 and 720 px; the sidebar becomes a drawer) and no horizontal overflow at phone width (verified).

**Pages.** *Overview* (live KPIs, the seven required sections as tabs, interactive 15-step pipeline, architecture diagram); *Problem and related work* (timeline, filterable evidence matrix with per-paper drill-down, outcome A/B/C, unresolved questions); *Automata laboratory* (an interactive 48-state graph with search + fly-to, zoom/pan, minimap, state details, trace playback with a travelling token, planted-culprit highlight, counterfactual-branch overlay, formalism views LTS/DFA/NFA/ε-NFA/PA, 48/64/96 states, and the other eight models with model-specific views — active sets, ε-closure steps, stack, tape, outputs, exact and Monte-Carlo acceptance probability, definitions, transition tables, comparison matrix and live test status); *Trajectory explorer* (failed trajectory, exact μ<sub>t</sub> chart, step selection, prefix state, intervention configuration, one counterfactual replay or an n-replay estimate with a Wilson interval, original vs counterfactual side by side); *Attribution dashboard* (the real algorithm with a round-by-round replayable forest plot, stopping-rule panel, ranking, uniform comparison on the same instance); *Experiment studio* (live simulations, saved results for all twelve groups, paired statistics, CSV/JSON export); *Theory* (KaTeX with expandable proofs and a claims ledger); *Reproducibility* (commands, seed policy, live test status, artifact links, checklist, figure gallery with lightbox); *Documentation* (searchable specification, generated API reference, glossary, troubleshooting).

![Overview page.](screens/overview.png)

![Automata laboratory.](screens/lab.png)

![Trajectory explorer.](screens/explorer.png)

![Attribution dashboard.](screens/dashboard.png)

![Experiment studio.](screens/studio.png)

**Frontend tests** ({FT['passed']}/{FT['total']} pass; vitest + Testing Library): navigation and the mobile menu, live test counts from the API, model switching and graph requests, trace execution, backend validation errors surfaced in the UI, loading/error/retry states, graph selection by click and keyboard and search dimming, number-field validation (δ, budget, trial count), dashboard execution and the abstention message, simulation execution and CSV/JSON export, empty states, the novelty matrix, documentation search, API-client error mapping (FastAPI validation details; unreachable backend) and CSV serialisation. No browser end-to-end tests were written.

**API.**

{api_table()}
## 21. Experimental methodology (from the paper)

{P('9')}
## 22. Synthetic experiments (from the paper)

{P('10')}
## 23. Benchmark experiments (ALFWorld, HotpotQA)

{P('11')}
## 24. Results and statistical analysis

The primary comparisons are paired by instance and corrected together (Table 2 of §22). With {H['n_pairs']} pairs per comparison all four primary differences are significant after Holm correction (largest adjusted p = {H['p_holm_max']:.4f}); effect sizes are ratios of *censored* means, so they are conservative; no other significance claim is made. Accuracy intervals are Wilson intervals, rollout intervals are bootstrap intervals, and the sample size of every cell is reported. There are no missing runs: every spec in `suite.py` produced a row (`results/processed/suite_meta.json` records the row count and wall time of every group). Sensitivity analyses: gap, number of candidates, automaton size, fault probability, δ, reconstruction noise and five ablation factors.

## 25. Ablation studies

{D.table_ablation()}
Reading: the confidence sequence matters moderately (stack-KL < KL-LUCB rate < stack-Hoeffding in cost); the allocation rule matters most (uniform and random roughly double the cost and certify far less often); valid prefix reuse reduces cost while naive sharing destroys certification; restricting candidates to decision states (a domain prior) is a different, easier problem; ε > 0 trades exactness for cost.

## 26. Error analysis

{fig(18, "Error analysis.", "fig18_error_analysis")}
1. **Abstentions are not failures of the method.** The abstaining LUCB trials are instances in which the best arm is (almost exactly) tied with another — gaps below $10^{{-4}}$ — so there is nothing to certify; the engine reports the candidate set instead of guessing. With ε > 0 these trials are certified (Table 8).
2. **Cost and the gap.** Cost rises steeply as the best–second gap shrinks (Table 4); on automaton instances with a small planted-fault probability the planted step is only slightly better than a pure re-roll (Table: fault probability), and certification needs tens of thousands of rollouts.
3. **Invalid sharing.** Naive credit is biased for every candidate whose value differs from the re-roll baseline (|z| ≈ 20–30 in the numerical check) and consequently almost never certifies and sometimes certifies wrongly.
4. **CAR-style rule.** The fixed-K "CI excludes zero" rule returns a late corridor step because corrupted states heal with probability 0.08 and any success among K rollouts is enough; this reflects *its estimand* (latest step that can still be rescued) on *our* model. It is not an error of the original method.
5. **Assumption violations.** Reconstruction noise reduces certification (Table 9); the target changes to the noisy context, so accuracy against the *original* argmax is not the right metric.

## 27. Limitations

{P('12')}
## 28. Reproducibility

**Environment.** Python ≥ 3.10 (developed on 3.13), Node ≥ 18 (developed on 24); Windows 11. **Commands.**

```
pip install -e ".[dev,docs]"
python -m pytest                                              # backend tests
python scripts/run_tests_report.py                            # also writes results/processed/test_report.json
cd website && npm install && npm test && npm run build        # frontend tests and production build
OPENBLAS_NUM_THREADS=1 python -m afcr.experiments.suite --trials 30 --workers 6
python -m afcr.experiments.suite --aggregate-only             # recompute aggregates from raw rows
python scripts/make_figures.py && python scripts/build_paper.py && python scripts/build_report.py
python scripts/build_deck.py && python scripts/build_pdfs.py
uvicorn afcr.api.app:app --port 8000                          # website + API at http://localhost:8000
```

**Seeds.** Instance seed = group base + trial index (main 20 000, gap sweep 30 000, K sweep 31 000, δ sweep 32 000, stress 33 000, size 40 000, fault probability 41 000, noise 42 000, ablation 43 000, budget curve 44 000, tool agent 50 000, targets 60 000/61 000); algorithm RNG = seed + 7. **Windows note.** Many parallel workers can exhaust the paging file; use at most six workers and `OPENBLAS_NUM_THREADS=1`. **Hardware.** A shared 24-logical-core machine; the full suite took {sum(g['wall_seconds'] for g in D.meta()['groups'].values()) / 60:.0f} minutes of wall time with six workers (wall-clock numbers are not performance claims). No paid model API is needed. Raw rows and aggregates are stored separately (`results/raw`, `results/processed`).

## 29. Conclusion and future work

{P('13')}
## 30. References

{P('13').split('## References')[0] if False else ''}See the reference list of the paper (§References of `paper/main.md`) and `paper/references.bib` for the full list. Verified neighbours: Zhang et al. 2025 (arXiv:2505.00212); Shah 2026 (arXiv:2606.08275); Zhang et al. 2025 (arXiv:2509.03312); Feng et al. 2026 (arXiv:2605.06788); Garivier and Kaufmann 2016 (arXiv:1602.04589); Kaufmann and Kalyanakrishnan 2013 (COLT, PMLR 30); Ma et al. 2025 (arXiv:2509.08682); Lin et al. 2026 (arXiv:2606.09071); Bonagiri et al. 2026 (arXiv:2605.25338); Cha et al. 2026 (arXiv:2606.14805); Li et al. 2026 (arXiv:2608.29228); Luan et al. 2026 (arXiv:2608.25920); Ma et al. 2025 (arXiv:2512.06749).

## 31. Appendices

### Appendix A. Proof of Theorem 2 (from the paper)

{P('Appendix A')}
### Appendix B. Confidence-sequence notes (from the paper)

{P('Appendix B')}
### Appendix C. Figure index

All 21 figures are produced by `scripts/make_figures.py`; kind, caption and source of each are in `results/figures/manifest.json` and `paper/figures/CAPTIONS.md`. Each is saved as PNG (200 dpi) and SVG. *Conceptual:* 1, 3, 4, 6, 7, 8, 9, 14. *Structural (drawn from the real model objects):* 12, 13. *Experimental (drawn only from result files, or from a real run stated in the caption):* 2, 5, 10, 11, 15–21.

{fig(1, "System architecture.", "fig01_system_architecture")}
{fig(3, "Counterfactual replay mechanism.", "fig03_counterfactual_replay")}
{fig(4, "Adaptive selection flowchart.", "fig04_adaptive_selection_flowchart")}
{fig(5, "Confidence bounds and stopping.", "fig05_confidence_stopping")}
{fig(10, "Prefix tree of replays.", "fig10_prefix_tree")}
{fig(11, "Prefix-aware replay comparison.", "fig11_prefix_aware_comparison")}
{fig(14, "Evaluation pipeline.", "fig14_evaluation_pipeline")}
{fig(15, "Rollouts versus accuracy.", "fig15_rollouts_vs_accuracy")}
{fig(16, "Cost versus attribution quality.", "fig16_cost_vs_quality")}
{fig(17, "Ablations.", "fig17_ablations")}
{fig(19, "Cost versus the lower bound.", "fig19_gap_sweep_lower_bound")}
{fig(20, "Empirical error versus δ.", "fig20_error_vs_delta")}
{fig(21, "Number of candidates.", "fig21_candidates_sweep")}
"""

EXPS = f"""# Experiments log

* **Command:** `OPENBLAS_NUM_THREADS=1 python -m afcr.experiments.suite --trials {D.meta()['trials']} --workers 6`; re-aggregation: `python -m afcr.experiments.suite --aggregate-only`.
* **Scope:** {D.meta()['note']}
* **Raw rows:** `results/raw/<group>.csv`; **aggregates:** `results/processed/<group>.json`; paired statistics: `results/processed/paired_stats.json`.
* **Wall time per group:** {', '.join(f"{g} ({v['rows']} rows, {v['wall_seconds']:.0f}s)" for g, v in D.meta()['groups'].items())}.
* **Censoring:** trials that hit the rollout cap contribute the cap to rollout statistics; means and medians are therefore lower bounds, most severely for uniform and random allocation.

## Main comparison — 48-state automaton

{D.table_main_auto()}
## Paired statistics (Holm-corrected)

{D.table_paired()}
## Bandit-arm model

{D.table_main_bandit()}
## Gap sweep and the Garivier–Kaufmann lower bound

{D.table_gap_sweep()}
## Number of candidates

{D.table_K()}
## Automaton size

{D.table_size()}
## Planted-fault probability

{D.table_eps()}
## δ calibration

{D.table_delta()}
Stress test (two arms, gap 0.06): {H['stress_per']} wrong certified answers per δ (total {H['stress_wrong']}/{H['stress_cert']}).

## Accuracy versus budget (and the 90 % target)

{D.table_budget()}
## Ablations

{D.table_ablation()}
## State-reconstruction noise

{D.table_noise()}
## Stage B: tool-using agent

{D.table_tool()}
## Targets

{D.table_targets()}
## Pending (not executed)

* **ALFWorld** (Stage C) and **HotpotQA** (Stage D): adapters exist and are mock-tested only; no model, no data and no result in this repository.
* Baselines other than the re-implemented CAR-style rule (Who&When judges, AgenTracer, conformal, REFLECT, …): not reproduced.
* Browser end-to-end tests.
"""

STATUS = f"""# RESEARCH_STATUS

_Authors: {AUTH}. Last generated from the result files; all numbers below are computed, not typed._

## Verified facts
* The five supplied papers exist; their metadata and (for CAR in full, others by full-text search and theorem reading) contents were verified on 2026-10-23 — see `research/related_work.md` (evidence level per paper).
* CAR: fixed K rollouts per step, Wilson + bootstrap intervals, point-of-commitment rule, budget-bounded MC-Shapley, **no** stopping rule / δ-PAC / sample-complexity result, synthetic SCMs only.
* Who&When uses LLM judges (no replay, no Shapley). AgenTracer: decisive step = earliest oracle-flip. Conformal paper: marginal coverage, no replay.
* KL-LUCB exploration rate β(t,δ)=ln(k₁Ktᵅ/δ)+ln ln(·) with k₁>2e+1+e/(α−1)+(e+1)/(α−1)² (Kaufmann & Kalyanakrishnan 2013, Thm 1) was read in the source.
* Tests: **{T['passed']}/{T['total']} backend** and **{FT['passed']}/{FT['total']} frontend** pass. The exact DP values agree with Monte Carlo; matched prefix-reuse observations are unbiased and naive-credited observations are biased (tested and reported in §10.8 of the paper).
* Experiments: {sum(v['rows'] for v in D.meta()['groups'].values()):,} synthetic trials in 12 groups; {H['cert_wrong']} wrong answers among {H['cert_total']:,} certified guaranteed trials; LUCB cost is {H['lb_lo']:.0f}–{H['lb_hi']:.0f}× the Garivier–Kaufmann lower bound.

## Unverified assumptions
* Novelty (outcome B) is provisional: DoVer, the LUCB / lil'UCB originals and Russo et al. were read at abstract level; later arXiv postings are unknown.
* ALFWorld (MIT) and HotpotQA (CC BY-SA 4.0) licences were read from secondary sources, not the official repositories.
* The OpenAI-compatible model provider has never been exercised.

## Proposed contributions
Fixed-confidence replay with abstention and three decision rules; a proved exact-match prefix-reuse condition with an unbiasedness test and a negative control; a 48/64/96-state automaton benchmark and a tool-agent world with exact ground truth.

## Implemented components
Nine formal models and the 48/64/96-state agent automaton; statistics (KL bounds, four confidence sequences, T* and H); replay environments (bandit, automaton, tool agent, text game); targets (argmax-ε, first/last-above-θ); strategies (LUCB, uniform, random, successive elimination, equal/random budget, CAR-style, oracle); the engine with abstention; valid and naive prefix sharing; model providers; ALFWorld/HotpotQA adapters; experiment suite with paired statistics; FastAPI backend; React + TypeScript website; 21 figures; paper, report, experiments log and slides.

## Experiments completed
All twelve synthetic groups (main, gap/K/δ sweeps, stress, size, fault probability, reconstruction noise, ablations, budget curve, tool agent, targets) at {D.meta()['trials']} trials per cell (60 for bandit cells).

## Experiments pending
ALFWorld; HotpotQA; any run with a real LLM agent; reproduction of related-work baselines other than the CAR-style rule; browser end-to-end tests; larger trial counts; 64/96-state sweeps beyond the size group.

## Known theoretical limitations
Theorem 1 holds under A1–A6 (a statement about the replay model); the sample-complexity bound is proved for successive elimination only (LUCB + stack bound: empirical); no lower-bound match and no optimality claim; the stack bound is conservative (0 errors observed even on stress instances); joint causes and non-Markov LLM state are out of scope.

## Remaining work before publication
Run Stages C and D with a fixed open model; verify DoVer / Russo et al. full texts and repeat the literature search; reproduce at least one more published baseline; add confidence sequences with LIL-type growth and measure the gap to the lower bound; handle joint causes; independent review of the proofs; larger-scale experiments; browser end-to-end tests.
"""

DELIVERY = f"""# DELIVERY_SUMMARY

Authors: {AUTH}

## Artifacts and exact paths
| Artifact | Path |
|---|---|
| Related work, evidence log; machine-readable records; novelty matrix | `research/related_work.md`, `research/related_work.csv`, `research/novelty_matrix.csv` |
| Research paper (source, PDF, bibliography, captions) | `paper/main.md`, `paper/main.pdf`, `paper/references.bib`, `paper/figures/` (+ `CAPTIONS.md`) |
| Technical report (source, PDF); experiments log | `report/technical_report.md`, `report/technical_report.pdf`, `report/experiments.md`, `report/screens/` |
| Slides (editable, 30 slides, speaker notes on every slide), outline and generator | `presentation/research_presentation.pptx`, `presentation/outline.md`, `scripts/build_deck.py` |
| Documentation (architecture, I/O spec, automata glossary, API reference, guides, troubleshooting) | `docs/` (generated: `scripts/build_docs_folder.py`) |
| Paper appendices (proof of Thm 2, confidence sequences, 48-state specification, complete result tables) | `paper/appendices/` |
| Experiment configurations (single trials and whole suites) | `configs/`, `src/afcr/experiments/run_one.py` |
| Backend | `src/afcr/**` (FastAPI app: `src/afcr/api/app.py`) |
| Website (source and build) | `website/` (React + TypeScript + Vite), `website/dist/` |
| Tests | backend `tests/`; frontend `website/src/test/` |
| Experiments | `src/afcr/experiments/suite.py` (+ `core.py`); raw `results/raw/*.csv`; processed `results/processed/*.json` |
| Figures (PNG + SVG), manifest | `results/figures/` |
| Status | `RESEARCH_STATUS.md`, this file, `README.md` |

## How to run
```
pip install -e ".[dev,docs]"
cd website && npm install && npm run build && cd ..
uvicorn afcr.api.app:app --port 8000          # open http://localhost:8000   (API explorer: /api/docs)
```
All commands (tests, suite, figures, documents, deck, PDFs): `README.md` and the Reproducibility page.

## Tests completed
* Backend: `python -m pytest` → **{T['passed']}/{T['total']} passed** (automata, statistics incl. empirical coverage under adaptive sampling, attribution, tool agent, adapters, prefix-reuse unbiasedness).
* Frontend: `cd website && npm test` → **{FT['passed']}/{FT['total']} passed** (navigation, model switching, graph interaction, validation, API errors, loading/error/empty states, export, simulation execution, responsive menu).
* Manual: every page loaded in a browser pane; no horizontal overflow at 390 px width.

## Experiments completed
Twelve synthetic groups, {sum(v['rows'] for v in D.meta()['groups'].values()):,} trials (see `report/experiments.md`).

## Experiments not completed
ALFWorld; HotpotQA; real LLM agents; baselines other than the CAR-style re-implementation; browser end-to-end tests.

## Status of the theoretical guarantee
Theorem 1 (δ-correctness for any sampling rule) and Theorem 3 (prefix-reuse validity) are **proved** under assumptions A1–A6; Theorem 2 (sample complexity) is proved for **successive elimination only**; LUCB's sample complexity with the stack bound is **empirical**; no optimality is claimed. Observed: {H['cert_wrong']} wrong answers among {H['cert_total']:,} certified guaranteed trials.

## Remaining publication risks
Novelty is provisional (abstract-level reading of some neighbours; fast-moving field); all results are synthetic; the automaton is hand-designed; the stack bound is conservative; real-agent assumptions (A1–A4) are likely violated; licences not verified at source; the OpenAI-compatible provider is untested.
"""

if __name__ == "__main__":
    (ROOT / "report" / "technical_report.md").write_text(REPORT, encoding="utf-8")
    (ROOT / "report" / "experiments.md").write_text(EXPS, encoding="utf-8")
    (ROOT / "RESEARCH_STATUS.md").write_text(STATUS, encoding="utf-8")
    (ROOT / "DELIVERY_SUMMARY.md").write_text(DELIVERY, encoding="utf-8")
    print("report words:", len(REPORT.split()), "| exps:", len(EXPS.split()))
