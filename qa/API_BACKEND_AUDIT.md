# API and backend audit

Server: `python -m uvicorn afcr.api.app:app --port 8000` (PID 38972, bound to 127.0.0.1), FastAPI app `src/afcr/api/app.py` v0.2.0. Probes were read-only GETs or POSTs to computation endpoints; none modifies project data. **Side effect:** the server process writes its stderr to `results/processed/api_err.txt`, so the HTTP 500 probes below appended tracebacks to that log file.

## Endpoint inventory (from `/openapi.json`, then probed)

| Method & path | Purpose | Observed | Status |
|---|---|---|---|
| GET `/api/health` | liveness + version | 200 `{"status":"ok","version":"0.2.0"}` | ✅ |
| GET `/api/automata/models` | model catalogue | 200, 12 models | ✅ |
| GET `/api/automata/graph?model=&view=&n_states=&eps_plan=` | graph payload | 200 for all 12 models and 5 views; 422 bad view, 422 n_states<48, 404 unknown model | ⚠️ DFA view drops sink (AUTO-005); n_states unbounded (API-003); no `qid` (AUTO-006) |
| POST `/api/automata/trace` | run a word | 200 for all models; 422 invalid symbol; 404 unknown model | ⚠️ per-model schema differs (TM `steps` int, AUTO-007); PA/Mealy/Moore `accepted` (AUTO-002/003); PDA reject → no steps (AUTO-004) |
| GET `/api/automata/compare` | comparison table | 200, 9 rows | ✅ (pda_typed, tm_pal, agent48 omitted by design) |
| POST `/api/attribute` | run the attribution engine | 200; 422 for unknown algorithm/confidence/target, δ ∉ (0,1) | ✅ |
| POST `/api/replay` | one counterfactual replay | 200; 422 arm out of range; **500** for seed<0, n_states 10/500, eps_plan 1.5 | ❌ API-001 |
| POST `/api/trajectory` | sample a failed trajectory | 200; 422 seed<0, n_states<48 | ✅ |
| POST `/api/replay/estimate` | n replays + Wilson CI | 200; **500** for seed<0 | ❌ API-001 |
| GET `/api/tests` | stored test report (+ frontend) | 200: 123/123, frontend 23/23, ran_at 2026-10-24 03:09 | ✅ (stored, not live) |
| POST `/api/experiment/run` | live simulation | 200; 422 unknown algorithm; negative seed accepted (works) | ⚠️ synchronous, no progress/cancel (API-003) |
| GET `/api/results/index` | groups + meta + paired + figures | 200, 12 groups, 6518 rows | ✅ |
| GET `/api/results/group/{name}` | aggregated group | 200; 404 unknown | ✅ |
| GET `/api/results/summary` | legacy alias | 200 | ✅ (unused by UI) |
| GET `/api/results/export?fmt=&group=` | raw rows CSV/JSON | 200; 422 bad fmt; 404 unknown group | ✅ |
| GET `/api/research/{novelty,related}` | CSV → JSON | 200 | ✅ |
| GET `/api/status` | RESEARCH_STATUS.md | 200 text | ✅ (unused by UI) |
| GET `/files/{README,RESEARCH_STATUS,DELIVERY_SUMMARY}.md` | documents | 200; OpenAPI summary " F" | ⚠️ POL-003 |
| GET `/files/{results,paper,report,presentation,research}/…` | static mounts (StaticFiles) | 200 for all 9 linked artifacts | ✅ (StaticFiles rejects traversal) |
| GET `/assets/*` | built JS/CSS | 200 | ✅ |
| GET `/{full_path:path}` | SPA fallback | 200 index.html — **also for `/api/*` typos** and **for `../` paths outside dist** | ❌ SEC-001, API-002 |
| OPTIONS (CORS) | — | 405, no CORS headers | ✅ intended (same origin) |

Endpoints the frontend calls that **do not** exist: none (every `api.*` call in `website/src/lib/api.ts` maps to a route above).

## Schema / contract findings

| Contract | Frontend expectation (`lib/api.ts`) | Backend reality | Effect |
|---|---|---|---|
| `TraceResponse.steps` | `TraceStepData[]` | TM: `int` (count) + `trace[]` | toast "undefined steps" (AUTO-007) |
| `TraceResponse.accepted` | verdict | PA: sampled path; Mealy/Moore: always true | misleading badges (AUTO-002/003) |
| PDA rejection | steps for playback | `steps: []` | nothing to show (AUTO-004) |
| Non-JSON success | — | SPA HTML with 200 for unknown `/api/*` | client returns HTML as data (API-002) |
| Validation errors | 422 + `detail` | 500 text on replay endpoints | generic "500 Internal Server Error" message (API-001) |

Recommendation: declare `response_model=` per endpoint (discriminated union per trace kind) so the OpenAPI schema documents the payloads and tests can validate them.

## Backend defects (beyond the table)

* **SEC-001 Path traversal** (`app.py:513-518`): `GET /../../pyproject.toml` (and `%2F`, `%2e%2e`, `%5C` variants) returns the file. Fix: resolve and require the path to stay inside `website/dist`.
* **Exception handling:** only `AutomatonError`/`ValueError` are mapped to 422 in `trace`/`attribute`; pydantic `ValidationError` raised while building an inner request model escapes as 500 (API-001). Add a global handler for `ValidationError → 422`.
* **Long-running work:** `/api/experiment/run` can execute up to 60 trials × 12 methods × 100 000 rollouts synchronously; no job id, progress or cancel (API-003).
* **Caching:** `agent()` is `lru_cache(16)` keyed by `(n_states, eps_plan)`; with unbounded `n_states` on `/api/automata/graph` and `/api/automata/trace` arbitrary large models can be built and retained (API-003).
* **Reproducibility:** fixed seeds — `attribute` uses `seed + 7`, `replay` `seed + 99` (or `replay_seed`), `estimate` `seed + 1234`. Re-running the same request returns the same result (observed for attribute: 6089 rollouts twice). Note that `estimate` is therefore deterministic per (seed, arm, n) — repeated presses give identical numbers; document this in the UI.
* **Logging:** tracebacks go to stderr only (here redirected into `results/processed/api_err.txt`, i.e. inside the results folder that the website serves under `/files/results/`). Move logs out of `results/`.
* **Numerical checks (spot):** DP ground truth vs Monte Carlo agree (existing tests); PA exact probability 0.868 for `go go go` ✓; Wilson intervals ✓; Monte-Carlo CI lower bound printed as `1.08e-19` for p̂ = 0 (cosmetic: clamp to 0).
* **Semantics:** `state_count_validated` is a constant `True` (acceptable because the builder validates, but compute it from `validate()` to keep the flag honest).

## Reproduction commands

```bash
curl -s localhost:8000/api/health
curl -s --path-as-is -o /dev/null -w "%{http_code}\n" "localhost:8000/../../pyproject.toml"      # expect 404 after SEC-001
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" localhost:8000/api/nope                   # expect 404 JSON after API-002
curl -s -X POST localhost:8000/api/replay -H "Content-Type: application/json" -d '{"seed":-1,"arm":0}'   # expect 422 after API-001
curl -s -X POST localhost:8000/api/automata/trace -H "Content-Type: application/json" -d '{"model":"tm","word":["1","0","1","1"]}'   # steps must be a list after AUTO-007
curl -s -X POST localhost:8000/api/automata/trace -H "Content-Type: application/json" -d '{"model":"pda","word":["call","ret","ret"]}' # ≥1 step + reject_reason after AUTO-004
```
