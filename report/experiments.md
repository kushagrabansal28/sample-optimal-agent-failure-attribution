# Experiments log

* **Command:** `OPENBLAS_NUM_THREADS=1 python -m afcr.experiments.suite --trials 30 --workers 6`; re-aggregation: `python -m afcr.experiments.suite --aggregate-only`.
* **Scope:** SYNTHETIC only (bandit-arm, automaton, tool-agent). NOT ALFWorld/HotpotQA.
* **Raw rows:** `results/raw/<group>.csv`; **aggregates:** `results/processed/<group>.json`; paired statistics: `results/processed/paired_stats.json`.
* **Wall time per group:** main (990 rows, 164s), gap_sweep (450 rows, 109s), K_sweep (450 rows, 194s), delta_sweep (300 rows, 10s), stress (900 rows, 225s), size_sweep (270 rows, 151s), eps_sweep (360 rows, 152s), noise_sweep (120 rows, 56s), ablation (450 rows, 200s), budget_curve (1920 rows, 134s), toolagent (158 rows, 60s), targets (150 rows, 78s).
* **Censoring:** trials that hit the rollout cap contribute the cap to rollout statistics; means and medians are therefore lower bounds, most severely for uniform and random allocation.

## Main comparison — 48-state automaton

| Method | n | Accuracy [Wilson 95%] | Certified | Abstained | Error among certified | Mean rollouts [95% CI] | Median |
|---|---|---|---|---|---|---|---|
| Oracle (exact means) | 30 | 100% [89%, 100%] | 100% | 0% | 0.0% | 0 [0–0] | 0 |
| LUCB + valid prefix reuse | 30 | 93% [79%, 98%] | 90% | 10% | 0.0% | 14,530 [8,646–21,704] | 4,281 |
| LUCB | 30 | 93% [79%, 98%] | 83% | 17% | 0.0% | 20,637 [14,124–28,126] | 8,328 |
| Successive elimination | 30 | 93% [79%, 98%] | 80% | 20% | 0.0% | 24,528 [17,691–31,998] | 12,320 |
| Uniform (same stopping rule) | 30 | 93% [79%, 98%] | 57% | 43% | 0.0% | 36,929 [29,737–44,830] | 34,274 |
| Random (same stopping rule) | 30 | 97% [83%, 99%] | 50% | 50% | 0.0% | 37,911 [30,554–46,150] | 46,100 |
| Equal budget (no stopping) | 30 | 80% [63%, 90%] | 0% | 0% | — | 3,000 [3,000–3,000] | 3,000 |
| LUCB + naive sharing (invalid) | 30 | 47% [30%, 64%] | 13% | 87% | 25.0% | 5,396 [4,747–5,880] | 6,000 |
| CAR-style fixed K=100 | 30 | 0% [0%, 11%] | 0% | 0% | — | 1,607 [1,283–1,957] | 1,300 |

## Paired statistics (Holm-corrected)

| Comparison (second vs first) | Pairs | Ratio of mean rollouts | Mean difference [95% bootstrap CI] | p (Wilcoxon) | p (Holm) | Significant at 0.05 |
|---|---|---|---|---|---|---|
| Uniform (same stopping rule) vs LUCB | 30 | 1.79× | 16,292 [11,060, 22,096] | <0.001 | <0.001 | yes |
| Random (same stopping rule) vs LUCB | 30 | 1.84× | 17,275 [11,536, 23,887] | <0.001 | <0.001 | yes |
| Successive elimination vs LUCB | 30 | 1.19× | 3,891 [1,908, 6,404] | <0.001 | <0.001 | yes |
| LUCB vs LUCB + valid prefix reuse | 30 | 1.42× | 6,106 [4,185, 8,177] | <0.001 | <0.001 | yes |

## Bandit-arm model

| Gap | Method | n | Accuracy | Certified | Error among certified | Mean rollouts [95% CI] |
|---|---|---|---|---|---|---|
| 0.1 | LUCB | 60 | 100% | 100% | 0.0% | 6,709 [6,296–7,188] |
| 0.1 | Successive elimination | 60 | 100% | 100% | 0.0% | 7,876 [7,504–8,264] |
| 0.1 | Uniform (same stopping rule) | 60 | 100% | 100% | 0.0% | 23,467 [21,890–25,044] |
| 0.1 | Random (same stopping rule) | 60 | 100% | 100% | 0.0% | 23,192 [21,947–24,561] |
| 0.1 | Equal budget (no stopping) | 60 | 100% | 0% | — | 3,000 [3,000–3,000] |
| 0.1 | Oracle (exact means) | 60 | 100% | 100% | 0.0% | 0 [0–0] |
| 0.2 | LUCB | 60 | 100% | 100% | 0.0% | 1,503 [1,413–1,600] |
| 0.2 | Successive elimination | 60 | 100% | 100% | 0.0% | 1,736 [1,621–1,857] |
| 0.2 | Uniform (same stopping rule) | 60 | 100% | 100% | 0.0% | 5,783 [5,501–6,083] |
| 0.2 | Random (same stopping rule) | 60 | 100% | 100% | 0.0% | 5,766 [5,394–6,169] |
| 0.2 | Equal budget (no stopping) | 60 | 100% | 0% | — | 3,000 [3,000–3,000] |
| 0.2 | Oracle (exact means) | 60 | 100% | 100% | 0.0% | 0 [0–0] |

## Gap sweep and the Garivier–Kaufmann lower bound

| Gap | LUCB | Successive elim. | Uniform | Lower bound T*·kl(δ,1−δ) | LUCB / lower bound |
|---|---|---|---|---|---|
| 0.050000000000000044 | 27,515 | 36,381 | 100,600 | 1,165 | 23.6× |
| 0.09999999999999998 | 6,609 | 7,837 | 25,481 | 313 | 21.1× |
| 0.15000000000000002 | 2,769 | 3,384 | 10,660 | 147 | 18.8× |
| 0.19999999999999996 | 1,537 | 1,867 | 5,781 | 86 | 17.8× |
| 0.30000000000000004 | 648 | 765 | 2,471 | 42 | 15.3× |

## Number of candidates

| K | LUCB | Successive elim. | Uniform | Uniform / LUCB |
|---|---|---|---|---|
| 4 | 1,416 | 1,441 | 2,808 | 2.0× |
| 8 | 1,565 | 1,890 | 5,526 | 3.5× |
| 16 | 1,812 | 2,612 | 11,676 | 6.4× |
| 32 | 2,391 | 3,953 | 22,869 | 9.6× |
| 64 | 3,362 | 6,249 | 49,713 | 14.8× |

## Automaton size

| Logical states | Method | n | Certified | Mean rollouts [95% CI] |
|---|---|---|---|---|
| 48 | LUCB | 30 | 87% | 22,634 [15,340–29,860] |
| 48 | LUCB + valid prefix reuse | 30 | 97% | 14,282 [8,970–20,184] |
| 48 | Uniform (same stopping rule) | 30 | 57% | 40,204 [33,447–47,048] |
| 64 | LUCB | 30 | 80% | 28,140 [21,150–34,961] |
| 64 | LUCB + valid prefix reuse | 30 | 90% | 14,416 [8,578–21,172] |
| 64 | Uniform (same stopping rule) | 30 | 47% | 44,908 [38,194–50,621] |
| 96 | LUCB | 30 | 77% | 35,263 [28,064–41,893] |
| 96 | LUCB + valid prefix reuse | 30 | 90% | 13,860 [7,697–20,360] |
| 96 | Uniform (same stopping rule) | 30 | 50% | 50,354 [46,284–54,020] |

## Planted-fault probability

| Fault prob. | mean true gap | Method | Certified | Mean rollouts [95% CI] |
|---|---|---|---|---|
| 0.3 | 0.068 | LUCB | 73% | 31,470 [24,627–38,586] |
| 0.3 | 0.068 | LUCB + valid prefix reuse | 90% | 19,044 [13,101–25,453] |
| 0.3 | 0.068 | Uniform (same stopping rule) | 20% | 57,140 [53,369–59,601] |
| 0.45 | 0.084 | LUCB | 70% | 26,281 [18,521–34,085] |
| 0.45 | 0.084 | LUCB + valid prefix reuse | 80% | 19,619 [11,903–27,193] |
| 0.45 | 0.084 | Uniform (same stopping rule) | 53% | 47,749 [42,209–52,954] |
| 0.6 | 0.119 | LUCB | 77% | 19,717 [12,335–27,998] |
| 0.6 | 0.119 | LUCB + valid prefix reuse | 90% | 14,803 [8,008–22,739] |
| 0.6 | 0.119 | Uniform (same stopping rule) | 73% | 31,439 [24,637–38,561] |
| 0.8 | 0.159 | LUCB | 80% | 16,652 [9,332–24,791] |
| 0.8 | 0.159 | LUCB + valid prefix reuse | 93% | 13,600 [6,488–21,477] |
| 0.8 | 0.159 | Uniform (same stopping rule) | 77% | 22,807 [14,397–30,968] |

## δ calibration

| δ | n | Observed error among certified | Certified | Mean rollouts |
|---|---|---|---|---|
| 0.01 | 60 | 0.0% | 100% | 3,221 |
| 0.05 | 60 | 0.0% | 100% | 2,935 |
| 0.1 | 60 | 0.0% | 100% | 2,784 |
| 0.2 | 60 | 0.0% | 100% | 2,688 |
| 0.4 | 60 | 0.0% | 100% | 2,531 |

Stress test (two arms, gap 0.06): δ=0.1: 0/300; δ=0.3: 0/300; δ=0.5: 0/300 wrong certified answers per δ (total 0/900).

## Accuracy versus budget (and the 90 % target)

| Method | B=100 | B=200 | B=500 | B=1,000 | B=2,000 | B=5,000 | B=10,000 | B=20,000 |
|---|---|---|---|---|---|---|---|---|
| LUCB + valid prefix reuse | 87% | 93% | 95% | 93% | 97% | 97% | 98% | 97% |
| LUCB | 53% | 63% | 80% | 88% | 90% | 98% | 97% | 97% |
| Equal budget (no stopping) | 45% | 62% | 72% | 80% | 90% | 95% | 98% | 98% |
| Random budget | 35% | 58% | 70% | 78% | 95% | 98% | 97% | 95% |

| Method | Smallest B with accuracy ≥ 90% (point estimate) | … with Wilson lower bound ≥ 90% |
|---|---|---|
| LUCB + valid prefix reuse | 200 | 10000 |
| LUCB | 2000 | 5000 |
| Equal budget (no stopping) | 2000 | 10000 |
| Random budget | 2000 | 5000 |

## Ablations

| Factor | Level | Accuracy | Certified | Error among certified | Mean rollouts [95% CI] |
|---|---|---|---|---|---|
| confidence | stack_kl | 93% | 83% | 0.0% | 18,448 [12,059–26,396] |
| confidence | stack_hoeffding | 93% | 83% | 0.0% | 22,764 [16,069–30,633] |
| confidence | kl_lucb_rate | 93% | 83% | 0.0% | 19,831 [13,554–27,394] |
| allocation | lucb | 93% | 83% | 0.0% | 18,448 [12,059–26,396] |
| allocation | successive_elim | 93% | 83% | 0.0% | 20,944 [14,662–28,386] |
| allocation | uniform_fc | 97% | 67% | 0.0% | 36,493 [30,004–43,330] |
| allocation | random_fc | 100% | 63% | 0.0% | 36,397 [29,789–43,632] |
| sharing | none | 93% | 83% | 0.0% | 18,448 [12,059–26,396] |
| sharing | valid | 97% | 87% | 0.0% | 12,693 [6,193–20,749] |
| sharing | naive | 47% | 20% | 16.7% | 5,355 [4,781–5,848] |
| candidates | all | 93% | 83% | 0.0% | 18,448 [12,059–26,396] |
| candidates | decision | 100% | 97% | 0.0% | 6,578 [2,125–12,883] |
| epsilon | 0.0 | 93% | 83% | 0.0% | 18,448 [12,059–26,396] |
| epsilon | 0.02 | 100% | 97% | 0.0% | 14,222 [8,936–21,317] |
| epsilon | 0.05 | 100% | 100% | 0.0% | 7,203 [4,860–10,929] |

## State-reconstruction noise

| Reconstruction noise | n | Accuracy vs noisy-context argmax | Certified | Mean rollouts |
|---|---|---|---|---|
| 0.0 | 30 | 97% [83%, 99%] | 97% | 11,908 |
| 0.1 | 30 | 97% [83%, 99%] | 77% | 23,514 |
| 0.25 | 30 | 100% [89%, 100%] | 70% | 31,055 |
| 0.5 | 30 | 80% [63%, 90%] | 30% | 54,780 |

## Stage B: tool-using agent

| Variant | Method | n | Accuracy (ε-optimal) | Certified | Mean rollouts [95% CI] |
|---|---|---|---|---|---|
| stochastic | LUCB | 30 | 100% | 83% | 6,623 [4,845–8,591] |
| stochastic | LUCB + valid prefix reuse | 30 | 100% | 83% | 5,578 [3,938–7,451] |
| stochastic | Uniform (same stopping rule) | 30 | 100% | 47% | 11,612 [9,936–13,189] |
| stochastic | Equal budget (no stopping) | 30 | 97% | 0% | 3,000 [3,000–3,000] |
| stochastic | Oracle (exact means) | 30 | 100% | 100% | 0 [0–0] |
| deterministic_phase0 | LUCB | 1 | 100% | 100% | 92 [92–92] |
| deterministic_phase0 | Uniform (same stopping rule) | 1 | 100% | 100% | 121 [121–121] |
| deterministic_phase1 | LUCB | 1 | 100% | 100% | 92 [92–92] |
| deterministic_phase1 | Uniform (same stopping rule) | 1 | 100% | 100% | 122 [122–122] |
| deterministic_phase4 | LUCB | 1 | 100% | 100% | 92 [92–92] |
| deterministic_phase4 | Uniform (same stopping rule) | 1 | 100% | 100% | 125 [125–125] |
| deterministic_phase5 | LUCB | 1 | 100% | 100% | 92 [92–92] |
| deterministic_phase5 | Uniform (same stopping rule) | 1 | 100% | 100% | 126 [126–126] |

## Targets

| Target | Method | n | Agreement with exact target | Certified | Mean rollouts |
|---|---|---|---|---|---|
| last_above | LUCB | 30 | 100% | 47% | 34,333 |
| last_above | CAR-style fixed K=100 | 30 | 3% | 0% | 1,320 |
| last_above | CAR-style fixed K=500 | 30 | 3% | 0% | 6,600 |
| first_above | LUCB | 30 | 100% | 100% | 32,362 |
| first_above | Uniform (same stopping rule) | 30 | 100% | 0% | 60,000 |

## Pending (not executed)

* **ALFWorld** (Stage C) and **HotpotQA** (Stage D): adapters exist and are mock-tested only; no model, no data and no result in this repository.
* Baselines other than the re-implemented CAR-style rule (Who&When judges, AgenTracer, conformal, REFLECT, …): not reproduced.
* Browser end-to-end tests.
