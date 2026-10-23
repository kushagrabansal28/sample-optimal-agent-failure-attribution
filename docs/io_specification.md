# Input–output specification

## Input

| Item | Where it enters | Notes |
|---|---|---|
| Original failed trajectory (states, actions, observations, outcome) | `AutomatonEnv(model, traj)`, `ToolAgentEnv(world, traj)`, `TextGameReplayEnv(game, agent, episode)` | the trajectory must end in failure; candidate steps are `1..T` |
| Task specification | environment (automaton / tool-agent world / benchmark game) | |
| Candidate intervention locations | `candidates="all" \| "decision" \| [steps]`; `env.eligible` | eligibility is tracked per arm |
| Intervention protocol | `intervention="repair" \| "resample"` | repair forces the reference action ρ(q); resample redraws from π |
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
