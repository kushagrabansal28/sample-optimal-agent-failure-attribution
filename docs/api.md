# API reference

Generated from the FastAPI OpenAPI schema by `python scripts/build_docs_folder.py` (live version: `/api/docs`, raw schema: `/openapi.json`).
All simulation endpoints are **synthetic**: ground truth is known by construction. Invalid input returns HTTP 422 with a readable `detail`; unknown models/groups return 404.

## `POST /api/attribute`

Attribute

Request body `AttribReq`:

| field | type | default | constraints |
|---|---|---|---|
| `source` | string | `"automaton"` | pattern `^(automaton|bandit|toolagent)$` |
| `seed` | integer | `0` | ≥ 0.0 |
| `n_states` | integer | `48` | ≥ 48.0, ≤ 200.0 |
| `eps_plan` | number | `0.6` | ≥ 0.0, < 1.0 |
| `gap` | number | `0.2` | > 0.0, < 0.7 |
| `K` | integer | `8` | ≥ 2.0, ≤ 60.0 |
| `algorithm` | string | `"lucb"` | — |
| `target` | string | `"argmax"` | — |
| `eps` | number | `0.0` | ≥ 0.0, ≤ 0.5 |
| `theta` | number | `0.5` | ≥ 0.0, ≤ 1.0 |
| `delta` | number | `0.1` | > 0.0, < 1.0 |
| `budget` | integer | `20000` | ≥ 1.0, ≤ 300000.0 |
| `share` | string | `"none"` | pattern `^(none|valid|naive)$` |
| `confidence` | string | `"stack_kl"` | — |
| `intervention` | string | `"repair"` | pattern `^(repair|resample)$` |
| `candidates` | string | `"all"` | pattern `^(all|decision)$` |
| `reconstruct_noise` | number | `0.0` | ≥ 0.0, ≤ 1.0 |
| `deterministic` | boolean | `false` | — |
| `history` | boolean | `true` | — |

## `GET /api/automata/compare`

Compare

## `GET /api/automata/graph`

Graph

| query parameter | required | type |
|---|---|---|
| `model` | yes | string |
| `n_states` | no | integer |
| `view` | no |  |
| `eps_plan` | no | number |

## `GET /api/automata/models`

List Models

## `POST /api/automata/trace`

Trace

Request body `TraceReq`:

| field | type | default | constraints |
|---|---|---|---|
| `model` | string | `null` | — |
| `word` | array | `null` | — |
| `n_states` | integer | `48` | ≥ 48.0, ≤ 96.0 |
| `seed` | integer | `0` | ≥ 0.0 |
| `view` | string | `"lts"` | — |

## `POST /api/experiment/run`

Run Experiment

Request body `ExpReq`:

| field | type | default | constraints |
|---|---|---|---|
| `source` | string | `"bandit"` | pattern `^(bandit|automaton|toolagent)$` |
| `algorithms` | array | `["lucb", "uniform_fc", "successive_elim"]` | — |
| `trials` | integer | `10` | ≥ 1.0, ≤ 60.0 |
| `K` | integer | `8` | ≥ 2.0, ≤ 40.0 |
| `gap` | number | `0.2` | > 0.0, < 0.7 |
| `delta` | number | `0.1` | > 0.0, < 1.0 |
| `budget` | integer | `20000` | ≥ 100.0, ≤ 100000.0 |
| `seed` | integer | `0` | ≥ 0.0 |
| `eps_plan` | number | `0.6` | ≥ 0.0, < 1.0 |
| `n_states` | integer | `48` | ≥ 48.0, ≤ 96.0 |

## `GET /api/health`

Health

## `POST /api/replay`

Replay

Request body `ReplayReq`:

| field | type | default | constraints |
|---|---|---|---|
| `source` | string | `"automaton"` | pattern `^(automaton|toolagent)$` |
| `seed` | integer | `0` | ≥ 0.0 |
| `arm` | integer | `0` | ≥ 0.0 |
| `eps_plan` | number | `0.6` | ≥ 0.0, < 1.0 |
| `intervention` | string | `"repair"` | pattern `^(repair|resample)$` |
| `n_states` | integer | `48` | ≥ 48.0, ≤ 96.0 |
| `deterministic` | boolean | `false` | — |
| `replay_seed` | integer/null | `null` | — |

## `POST /api/replay/estimate`

Replay Estimate

Request body `EstReq`:

| field | type | default | constraints |
|---|---|---|---|
| `source` | string | `"automaton"` | pattern `^(automaton|toolagent)$` |
| `seed` | integer | `0` | ≥ 0.0 |
| `arm` | integer | `0` | ≥ 0.0 |
| `eps_plan` | number | `0.6` | ≥ 0.0, < 1.0 |
| `intervention` | string | `"repair"` | pattern `^(repair|resample)$` |
| `n_states` | integer | `48` | ≥ 48.0, ≤ 96.0 |
| `deterministic` | boolean | `false` | — |
| `replay_seed` | integer/null | `null` | — |
| `n` | integer | `200` | ≥ 1.0, ≤ 5000.0 |

## `GET /api/research/{what}`

Research

| query parameter | required | type |
|---|---|---|
| `what` | yes | string |

## `GET /api/results/export`

Results Export

| query parameter | required | type |
|---|---|---|
| `fmt` | no | string |
| `group` | no | string |

## `GET /api/results/group/{name}`

Results Group

| query parameter | required | type |
|---|---|---|
| `name` | yes | string |

## `GET /api/results/index`

Results Index

## `GET /api/results/summary`

Results Summary

## `GET /api/status`

Status

## `GET /api/tests`

Tests Report

## `POST /api/trajectory`

Trajectory

Request body `TrajReq`:

| field | type | default | constraints |
|---|---|---|---|
| `source` | string | `"automaton"` | pattern `^(automaton|toolagent)$` |
| `seed` | integer | `0` | ≥ 0.0 |
| `eps_plan` | number | `0.6` | ≥ 0.0, < 1.0 |
| `n_states` | integer | `48` | ≥ 48.0, ≤ 96.0 |
| `intervention` | string | `"repair"` | pattern `^(repair|resample)$` |
| `deterministic` | boolean | `false` | — |

## `GET /files/DELIVERY_SUMMARY.md`

Download DELIVERY SUMMARY.md

## `GET /files/README.md`

Download README.md

## `GET /files/RESEARCH_STATUS.md`

Download RESEARCH STATUS.md
