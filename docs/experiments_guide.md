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
