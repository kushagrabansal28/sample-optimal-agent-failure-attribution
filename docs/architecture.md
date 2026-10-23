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
