"""Write docs/*.md (architecture, I/O specification, glossary, API reference generated from OpenAPI, guides)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)


def w(name: str, text: str) -> None:
    (DOCS / name).write_text(text.strip() + "\n", encoding="utf-8")
    print("wrote docs/" + name)


def api_reference() -> str:
    from afcr.api.app import app
    spec = app.openapi()
    schemas = spec.get("components", {}).get("schemas", {})
    out = ["# API reference", "",
           "Generated from the FastAPI OpenAPI schema by `python scripts/build_docs_folder.py` (live version: `/api/docs`, raw schema: `/openapi.json`).",
           "All simulation endpoints are **synthetic**: ground truth is known by construction. Invalid input returns HTTP 422 with a readable `detail`; unknown models/groups return 404.", ""]
    for path, methods in sorted(spec["paths"].items()):
        for m, d in methods.items():
            out.append(f"## `{m.upper()} {path}`")
            out.append("")
            out.append((d.get("summary") or "").replace("_", " "))
            params = d.get("parameters") or []
            if params:
                out += ["", "| query parameter | required | type |", "|---|---|---|"]
                for p in params:
                    out.append(f"| `{p['name']}` | {'yes' if p.get('required') else 'no'} | {p.get('schema', {}).get('type', '')} |")
            ref = (((d.get("requestBody") or {}).get("content") or {}).get("application/json") or {}).get("schema", {}).get("$ref")
            if ref:
                sch = schemas.get(ref.split("/")[-1], {})
                out += ["", f"Request body `{ref.split('/')[-1]}`:", "", "| field | type | default | constraints |", "|---|---|---|---|"]
                for k, v in sch.get("properties", {}).items():
                    cons = []
                    for key, sym in (("minimum", "≥"), ("exclusiveMinimum", ">"), ("maximum", "≤"), ("exclusiveMaximum", "<")):
                        if key in v:
                            cons.append(f"{sym} {v[key]}")
                    if "pattern" in v:
                        cons.append(f"pattern `{v['pattern']}`")
                    t = v.get("type") or ("/".join(x.get("type", "") for x in v.get("anyOf", [])) or "")
                    out.append(f"| `{k}` | {t} | `{json.dumps(v.get('default'))}` | {', '.join(cons) or '—'} |")
            out.append("")
    return "\n".join(out)


w("README.md", """
# Documentation index

| Document | Contents |
|---|---|
| [architecture.md](architecture.md) | packages, data flow, design decisions |
| [io_specification.md](io_specification.md) | inputs and outputs of the attribution system, the result record |
| [automata_glossary.md](automata_glossary.md) | the nine formal models, semantics, limits, comparison matrix |
| [api.md](api.md) | every HTTP endpoint with request fields (generated) |
| [experiments_guide.md](experiments_guide.md) | experiment groups, configs, seeds, how to add an experiment |
| [website_guide.md](website_guide.md) | the nine pages and what each one shows |
| [troubleshooting.md](troubleshooting.md) | common problems and fixes |

The mathematical development is in [`paper/main.md`](../paper/main.md) (with PDF) and the implementation narrative in
[`report/technical_report.md`](../report/technical_report.md). The evidence for the literature claims is in [`research/`](../research/).
""")

w("architecture.md", """
# Architecture

```
failed trajectory ─┐
intervention g_t ──┼─► ReplayEnv ──pull(arm)──► outcome Y ∈ {0,1} (+ valid shared arms)
task / evaluator ──┘        ▲                              │
                            │ arm to pull                  ▼
                     Strategy (LUCB, …)  ◄────  engine: counts, KL intervals (running intersection)
                                                           │
                                                  Target.decide(lo, hi)
                                                           │
                        certified culprit  |  abstention (budget exhausted) + candidate set
```

## Packages (`src/afcr`)

| Package | Responsibility | Key modules |
|---|---|---|
| `automata` | formal models and the agent benchmark | `dfa`, `nfa` (NFA + ε-NFA), `pa`, `lts`, `transducers` (Mealy/Moore), `pda`, `turing`, `benchmark48` |
| `statistics` | the only place bounds are defined | `bernoulli` (KL, inversion), `confidence` (stack-KL, stack-Hoeffding, KL-LUCB rate, Wilson), `complexity` (H, T*, lower bound) |
| `replay` | arms and exact ground truth | `bandit_env`, `automaton_env`, `toolagent_env`, `base` (PullResult) |
| `attribution` | what is identified and how | `targets` (argmax-ε, first/last-above), `algorithms` (strategies), `engine` |
| `agents` | agent worlds and model providers | `toolagent`, `providers` |
| `benchmarks` | adapters for real benchmarks | `textgame`, `alfworld_adapter`, `hotpotqa_adapter` |
| `experiments` · `evaluation` | experiments and analysis | `suite`, `core`, `run_one`; `metrics`, `stats` |
| `api` | HTTP interface for the website | `app` (endpoints, validation, static site), `lab` (automata laboratory: q-numbered graphs, per-machine traces, example cases) |

## Design decisions

1. **The stopping rule is separate from the sampling rule.** δ-correctness (Theorem 1) holds for any strategy, so no allocation heuristic can compromise it.
2. **Every result states whether the guarantee applies.** `guarantee_applies` plus a human-readable `guarantee_note`; fixed-budget strategies, non-anytime intervals and naive sharing switch it off.
3. **Abstention is a first-class outcome.** `budget_exhausted` returns the empirical best guess *and* the not-yet-eliminated candidates; it is never reported as a δ-PAC stop.
4. **Prefix sharing is opt-in and validated.** `share="valid"` requires a confidence sequence flagged `valid_under_sharing` and an environment whose `sharing_valid` is true (it is false under state-reconstruction noise).
5. **Exact ground truth.** Automaton and tool-agent environments expose `true_means()` computed by dynamic programming; algorithms never see it.
6. **Reproducibility.** Every trial is a plain dict (`afcr.experiments.core.run_spec`); seeds are explicit; raw and aggregated results are stored separately.
7. **No model SDK in the statistics.** Providers are behind an interface; a deterministic test mode needs no model.

## Data flow of an experiment

`suite.group_specs` → list of spec dicts → `core.run_spec` (build env, build strategy/target/confidence, `run_attribution`) → one row per trial → `results/raw/<group>.csv` → `suite.aggregate` (Wilson / bootstrap) → `results/processed/<group>.json` → figures, tables, website, slides.
""")

w("io_specification.md", """
# Input–output specification

## Input

| Item | Where it enters | Notes |
|---|---|---|
| Original failed trajectory (states, actions, observations, outcome) | `AutomatonEnv(model, traj)`, `ToolAgentEnv(world, traj)`, `TextGameReplayEnv(game, agent, episode)` | the trajectory must end in failure; candidate steps are `1..T` |
| Task specification | environment (automaton / tool-agent world / benchmark game) | |
| Candidate intervention locations | `candidates="all" \\| "decision" \\| [steps]`; `env.eligible` | eligibility is tracked per arm |
| Intervention protocol | `intervention="repair" \\| "resample"` | repair forces the reference action ρ(q); resample redraws from π |
| Replay environment and outcome evaluator | the environment's `pull(arm, rng)` | returns Y ∈ {0,1} |
| Confidence parameter δ | `delta ∈ (0,1)` | invalid values raise `ValueError` / HTTP 422 |
| Maximum rollout budget | `budget` (non-negative integer) | |
| Random seeds | instance seed; algorithm RNG = seed + 7 | |
| Automaton / transition-system configuration | `build_agent_model(n_states, eps=…, noise=…, heal=…, leak=…, false_accept=…)` | ≥ 48 logical states, validated |
| Target | `argmax` (ε), `first_above` (θ), `last_above` (θ) | |
| Sampling rule, confidence sequence, sharing mode | `strategy`, `conf`, `share ∈ {none, valid, naive}` | `naive` is a negative control |

## Output (`AttributionResult`, JSON via `/api/attribute`)

| Field | Meaning |
|---|---|
| `status` | `identified`, `budget_exhausted` (abstention), `fixed_budget_done`, `oracle` |
| `selected` / `provisional` / `answer` | certified step; empirical best guess; forced-choice answer |
| `candidate_set`, `certified_none` | arms not eliminated; threshold rules: no step qualifies |
| `means`, `lo`, `hi`, `counts`, `own_pulls`, `shared_obs`, `successes` | per-arm estimates, intervals, observations (own / shared) |
| `total_rollouts`, `total_steps`, `rounds`, `wall_seconds` | cost accounting |
| `guarantee_applies`, `guarantee_note` | whether the δ-guarantee applies and why / why not |
| `history` | optional per-round snapshots (arms pulled, outcomes, shared credits, intervals, suggested next arms, stop flag) |
| `ground_truth` | synthetic only: exact means, exact argmax, planted arm |
| `trajectory`, `labels` | the original failed trajectory and arm labels |

The experiment suite adds, per trial: `truth`, `correct_exact`, `correct` (ε-aware), `gap`, `mu_ans`, `mu_max`, `identified`, `abstained`, `shared`, `guarantee`, `traj_len`, and the full spec fields.

## Automata laboratory (`/api/automata/*`)

Every state of every machine is exposed with a `qid` (`q0`, `q1`, …): the initial state is `q0`, the others follow in breadth-first order (the 48-state agent automaton uses its definition order, `q0 … q47`). The descriptive name stays available as `name` / `label`.

`POST /api/automata/trace` returns `kind`, a *list* `steps`, and a result that depends on the machine — only machines that really have an acceptance notion report `accepted`:

| kind | machines | result fields |
|---|---|---|
| `dfa`, `nfa`, `enfa`, `lts`, `pda` | DFA, NFA, ε-NFA, LTS, both PDAs | `accepted`, `reason` (why a word is rejected), `final_state` / `initial_active` / `final_active` / `blocked` / stack in every step |
| `pa` | probabilistic automaton | `exact_acceptance_probability`, `monte_carlo`, `sample_ended_accepting` — **no** accepted/rejected verdict |
| `mealy`, `moore` | transducers | `outputs` — **no** acceptance |
| `tm` | the three Turing machines | `status`, `output`, `n_steps`, `trace` (tape configurations), `unknown` (true when a simulator bound was reached: the answer is *unknown*, never *reject*) |

Each machine lists `examples` (accept, reject, empty word, trap/dead state, invalid symbol, unknown …) that the website offers as one-click cases; the test-suite executes every one of them.

## Statuses and what they license

| Status | May be called δ-correct? |
|---|---|
| `identified` with `guarantee_applies = true` | yes, under assumptions A1–A6 |
| `identified` with `guarantee_applies = false` | no (e.g. Wilson intervals, naive sharing) |
| `budget_exhausted` | no — it is an abstention |
| `fixed_budget_done` | no |
""")

w("automata_glossary.md", """
# Automata glossary and semantics

| Model | Definition | Acceptance / halting | Memory | Nondeterminism | Probability | Fit for agent traces | Limits for causal attribution |
|---|---|---|---|---|---|---|---|
| **DFA** | M = (Q, Σ, δ, q₀, F), δ: Q×Σ→Q **total** | final state ∈ F | finite | none | none | nominal skeleton of an agent | no uncertainty; cannot express stochastic replay |
| **NFA** | δ: Q×Σ→2^Q | some path accepts (active-state set meets F) | finite | formal, not randomness | none | possible environment outcomes | no likelihoods; cannot rank causes |
| **ε-NFA** | δ: Q×(Σ∪{ε})→2^Q | ε-closure before/after each symbol | finite | formal + silent moves | none | silent self-correction ("heal") as ε-moves | as NFA |
| **Probabilistic automaton** | each (q,a) → distribution over successors | P(w) = e_{q₀}ᵀ M_{a₁}…M_{aₙ} 1_F | finite | none | **yes** | natural model of a stochastic agent | finite memory; Markov |
| **LTS** | s —a→ s′ with labels (reasoning, tool use, observation, update, validation, recovery, success, failure) | reachability of accepting/rejecting states; deadlocks | finite | allowed | optional | execution as labelled actions | labels carry meaning only by convention |
| **Mealy** | λ: Q×Σ→Γ | transducer | finite | none | none | controller reacting to observations | no acceptance notion |
| **Moore** | λ: Q→Γ | transducer (n+1 outputs for n inputs) | finite | none | none | state = action being executed | Mealy→Moore needs state expansion |
| **PDA** | finite control + stack; transitions (q,a,X,q′,γ) | final state and/or empty stack | unbounded stack | allowed | none | nested / recursive tool invocation | single stack, no probabilities |
| **Turing machine (bounded)** | tape + head + δ; step limit and tape bound | accept / reject / step_limit / tape_bound | tape (bounded in this simulator) | none | none | general-computation demonstration | bound is a simulator convenience; hitting it means *unknown*, not *reject* |

**State numbering.** In the laboratory every machine is drawn with states `q0, q1, …`; the initial state is always `q0`. The meaning of a state (e.g. `idle`, `dead`, `PLAN_SUBGOAL`) is shown beside it.

**Cases each machine demonstrates.**

| Machine | Cases (one-click examples on the website) |
|---|---|
| DFA (starts with `a`, even number of `b`) | accepted · rejected · **dead (trap) state** · empty word · invalid symbol |
| NFA (ends in `ab`) | accepted · rejected · empty word · a dead branch · invalid symbol; *Show as → DFA* = subset construction |
| ε-NFA (`a*b`) | accepted · only `b` (closure already contains `q2`) · rejected · empty word · too many `b`; *Show as → NFA / DFA* = ε-removal / subset construction |
| Probabilistic automaton | a probability for each word, never a verdict; empty word = probability 0; invalid symbol |
| LTS | accepted · failure · **blocked action** · empty word · label that is never enabled |
| Mealy / Moore | outputs for a run (n resp. n+1 outputs) · empty word · invalid symbol |
| PDA (nested calls) and typed PDA | balanced · **stack underflow** · **unclosed call** · type mismatch · empty word · invalid symbol — a rejection shows how far the machine got and why it stopped |
| Turing machines | increment (output) · palindromes (accept / reject) · a machine that never halts → **unknown** (step limit), not reject |

**Important distinctions.**
* NFA nondeterminism ("does some path accept?") is a formal device. LLM sampling randomness is *probabilistic*: it belongs in the probabilistic automaton / the policy π of the agent model.
* A probabilistic automaton or an LTS is the natural model of a stochastic agent; DFA, NFA, PDA and Turing machines are used for formal-language demonstrations and as structural views of the same 48-state specification. They are **not** forced into the same causal interpretation.
* A finite-state machine cannot recognise arbitrarily deep nesting; the PDA can (the tests show a depth-3-bounded DFA failing on a depth-5 word).

## The 48-state agent automaton

Six groups of eight states (PLAN, OBSERVE, TOOL, MEMORY, VALIDATE, TERMINAL). Roles: *benign*, *decision* (carries a planted fault), *fault entry*, *corridor* (corrupted state), *recovery*, *terminal_success*, *terminal_failure*. Views: LTS (policy × kernel probabilities), DFA (most-likely successor, explicit sink), NFA (all successors), ε-NFA (heal edges are ε), probabilistic automaton (environment kernel). The state count is validated programmatically (unique ids and labels; the DFA sink is not counted).

Exact quantities: V_t(q) = P(success | q, t) by backward induction;
μ_t^rep = Σ_{q′} P(q′ | q_{t−1}, ρ(q_{t−1})) V_t(q′); μ_t^res = V_{t−1}(q_{t−1}).
""")

w("api.md", api_reference())

w("experiments_guide.md", """
# Experiments guide

All experiments are **synthetic** (bandit-arm model, 48/64/96-state automaton, Stage-B tool agent). ALFWorld and HotpotQA have not been run.

## Groups (`python -m afcr.experiments.suite --groups …`)

| Group | What varies | Key question |
|---|---|---|
| `main` | all methods on the 48-state automaton; bandit cells at gap 0.1 / 0.2 | adaptive vs uniform at matched confidence; paired statistics |
| `gap_sweep` | best–runner-up gap 0.05–0.3 | cost vs the Garivier–Kaufmann lower bound |
| `K_sweep` | number of candidates 4–64 | growth of cost with K |
| `delta_sweep` | δ 0.01–0.4 | cost and error vs δ |
| `stress` | two-arm instances, gap 0.06, δ up to 0.5 | can the stopping rule be made to err? |
| `size_sweep` | 48 / 64 / 96 states | trajectory length and harmless candidates |
| `eps_sweep` | planted-fault probability | true gap of the planted step |
| `noise_sweep` | state-reconstruction noise (A1 violated) | effect of assumption violation |
| `ablation` | confidence sequence, allocation, sharing, candidates, ε | one factor at a time |
| `budget_curve` | rollout budget 100–20 000 | forced-choice accuracy, 90 % target |
| `toolagent` | Stage-B agent, stochastic and deterministic | non-automaton environment |
| `targets` | first/last-above-θ, CAR-style rule | alternative culprit definitions |

## Running

```
OPENBLAS_NUM_THREADS=1 python -m afcr.experiments.suite --config configs/suite_default.json     # everything (≈ 20 min, 6 workers)
python -m afcr.experiments.suite --groups main,gap_sweep --trials 10 --workers 4                 # a subset
python -m afcr.experiments.suite --aggregate-only                                                # re-aggregate raw → processed
python -m afcr.experiments.run_one configs/spec_automaton_prefix.json --seed 7 --budget 20000    # ONE trial
```

On Windows, more than about six workers can exhaust the paging file; keep `OPENBLAS_NUM_THREADS=1`.

## Seeds

Instance seed = group base + trial index (main 20 000, gap 30 000, K 31 000, δ 32 000, stress 33 000, size 40 000, ε 41 000, noise 42 000, ablation 43 000, budget 44 000, tool agent 50 000, targets 60 000/61 000). Algorithm RNG = seed + 7. All methods in a group share seeds, so comparisons are **paired**.

## Adding an experiment

1. Add a branch to `group_specs` in `src/afcr/experiments/suite.py` returning a list of spec dicts; add the group to `ALL` and `BY`.
2. Run it; inspect `results/raw/<group>.csv`.
3. Add a view in `website/src/pages/Studio.tsx` (title/blurb in `GROUP_INFO`) and a figure in `scripts/make_figures.py`.
4. `tests/test_results_consistency.py` automatically checks the new group's aggregates against its raw rows.

## Reading the numbers

* Rollout counts of trials that hit the budget cap are **censored**: means and medians are lower bounds on the true cost.
* *Abstained* = budget exhausted without certification; fixed-budget methods never certify and are not counted as abstaining.
* Accuracy intervals are Wilson; rollout intervals are bootstrap; paired tests are Wilcoxon signed-rank with Holm correction over the four primary comparisons.
""")

w("website_guide.md", """
# Website guide

Start: `uvicorn afcr.api.app:app --port 8000` and open <http://localhost:8000> (build once with `cd website && npm install && npm run build`;
for development run `npm run dev` — port 5173 proxies `/api` to the backend).

| Page | Route | What it shows (all from the API) |
|---|---|---|
| Overview | `/` | live KPIs, the seven required sections as tabs, the 15-step pipeline, architecture diagram, δ-PAC explainer, test status |
| Problem & related work | `/related` | timeline, filterable evidence matrix, per-paper records, outcome A/B/C |
| Automata laboratory | `/lab` | 13 machines with q0, q1, … states: pick a machine, press an **example case** (accept / reject / dead state / invalid input / unknown …) and play the run on the graph; per-machine result panel (probability, outputs, stack, tape, reason for rejection); graph ⇄ table switch; NFA/ε-NFA *Show as* views (subset construction, ε-removal); the 48-state automaton in LTS/DFA/NFA/ε-NFA/PA views (DFA view draws the sink); search, zoom/pan, minimap, state details, counterfactual-branch overlay, definitions, comparison matrix, test status |
| Trajectory explorer | `/explorer` | sample a failed run, exact μ_t chart, intervene on a step, one replay or an n-replay estimate, original vs counterfactual |
| Attribution dashboard | `/dashboard` | run the real algorithm; replayable forest plot of intervals; stopping-rule panel; ranking; comparison with uniform |
| Experiment studio | `/studio` | live simulations, all saved result groups, paired statistics, CSV/JSON export |
| Theory & guarantees | `/theory` | estimand, assumptions, theorems with expandable proofs, claims ledger |
| Reproducibility | `/reproducibility` | install, commands, seed policy, live test status, artifacts, checklist, figure gallery |
| Documentation | `/docs` | searchable specification, generated API reference, glossary, troubleshooting |

Deep links: `/lab?model=pda`, `/dashboard?autorun=1`, `/dashboard?seed=5&source=automaton&autorun=1`, `/explorer?autoload=1`.

Keyboard: Tab / Shift-Tab, Enter on states and table rows, arrow keys in tab lists, Escape closes the mobile menu; a *Skip to content* link and one `h1` per page.

**Honesty conventions.** Simulated results carry a *synthetic* badge; pending work carries a *pending* badge; nothing on the site is a real-benchmark result. The custom cursor and background spotlight are disabled on touch devices and when the system requests reduced motion.
""")

w("troubleshooting.md", """
# Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The site shows **"Request failed"** / "Cannot reach the API" / the API pill is red | the backend is not running (the site only displays data served by it). Start it from the repository root: `uvicorn afcr.api.app:app --port 8000` and open <http://localhost:8000>. With `npm run dev` the proxy targets port 8000. |
| A page is blank until I refresh | fixed (pages no longer start invisible and wait for an animation). Rebuild the site (`cd website; npm run build`) and hard-refresh (Ctrl+F5) once to drop the old bundle |
| "Website not built" text at `/` | run `cd website && npm install && npm run build` |
| Studio says "no saved results" | run `python -m afcr.experiments.suite` (or copy `results/` from a full run) |
| Test-status panels are empty | run `python scripts/run_tests_report.py`; for the frontend `cd website && npx vitest run --reporter=json --outputFile=../results/processed/frontend_test_report.json` |
| `DLL load failed … paging file is too small` during experiments | too many parallel workers; use ≤ 6 and `OPENBLAS_NUM_THREADS=1` |
| `vite build` crashes with a native stack trace once | transient memory pressure on Windows; run it again |
| HTTP 422 from the API | the server validated your input (δ ∉ (0,1), budget not a positive integer, unknown algorithm …); the message names the field |
| PDF export fails | needs Node ≥ 18 and Edge/Chrome; `cd scripts/pdf && npm install` once, then `python scripts/build_pdfs.py` |
| The graph looks tiny | press the *fit to view* button; the graph auto-fits until you interact with it |
| Custom cursor missing | disabled on touch devices and with reduced-motion preferences (by design) |
| `ModuleNotFoundError: afcr` | the package is not installed: run `pip install -e .` once, or set `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH = "src"`). Tests set `pythonpath = src` themselves. |
""")
