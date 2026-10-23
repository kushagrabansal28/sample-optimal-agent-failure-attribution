# Test report

Machine: Windows 11, Python 3.13, Node 24.19.0, Microsoft Edge (headless, DevTools protocol). Date: 2026-10-24. No packages were installed, upgraded or removed. No source file was modified.

## 1. Existing automated suites

| # | Command | Working directory | Exit | Pass | Fail | Skip | Duration | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | `python -m pytest -q -p no:cacheprovider` | repo root | 0 | 123 | 0 | 0 | 106 s | `addopts = -q` plus `-q` suppresses the summary line; 123 = dot count (72 + 51) and matches `--collect-only`. Output: `evidence/pytest_output.txt` |
| 2 | `npx vitest run` | `website/` | 0 | 23 | 0 | 0 | 32 s | 2 React Router v7 future-flag warnings, no `act()` warnings. Output: `evidence/vitest_output.txt` |
| 3 | `npx tsc --noEmit` | `website/` | 0 | — | — | — | 8 s | no type errors. Output: `evidence/tsc_output.txt` |

Not run: `npm run build` (would overwrite `website/dist`, which the running server serves); `python scripts/run_tests_report.py` and the frontend JSON reporter (would overwrite `results/processed/*report*.json`); the experiment suite (long, writes `results/`).

Stored reports served by the site (`/api/tests`): backend 123/123 at 2026-10-24 03:09, frontend 23/23 — consistent with the runs above.

### Coverage gaps in the existing suites

* Frontend: no tests for Explorer, Theory or Reproducibility; the validation test checks the error text but not that submission is blocked (FORM-001); no test for threshold targets on the Dashboard; GraphCanvas tests run in jsdom where `clientWidth = 0`, so the zero-width fit path (AUTO-001) is exercised but never asserted.
* Backend: no tests for the HTTP layer of `/api/replay`, `/api/replay/estimate`, `/api/automata/trace` response shapes, the SPA fallback (SEC-001/API-002).

## 2. Audit scripts (new, in `qa/tools/`)

All scripts drive a fresh headless Edge profile in a temp directory; they only read from the running server (plus the computation POSTs that the UI itself makes).

| Script | Command | Result | Evidence |
|---|---|---|---|
| `01_routes.mjs` | `node qa/tools/01_routes.mjs qa/evidence` | completed: 10 routes direct + refresh, sidebar sequence, back/forward, KPI timeline; 0 exceptions; 32 console errors on `/` (FE-001) | `01_routes.json`, `route_*.png` |
| `02_lab.mjs` | same pattern | completed: 12 models × (graph, trace, step-through, reject/invalid word, node click, zoom); 0 exceptions; 2 expected 422s (invalid words) | `02_lab.json`, `lab_*.png` |
| `03_zero.mjs` | same pattern | completed: zero-size mount, wheel while collapsed, Reveal opacity, theme toggle, reduced motion | `03_hypotheses.json`, `hyp_*.png` |
| `04_workflows.mjs` | same pattern | completed: Explorer, Dashboard, Studio (12 groups + live run), Docs, Reproducibility links, Related filters; request bodies captured | `04_workflows.json`, `explorer_*`, `dashboard_*`, `studio_*` |
| `05_responsive_a11y.mjs` | same pattern | completed: 9 routes × 5 viewports; landmarks, headings, labels, contrast sample, tabs, mobile drawer | `05_responsive_a11y.json`, `resp_*.png` |
| `06_kb.mjs` | `node qa/tools/06_kb.mjs` | completed: keyboard reach and Enter on a graph node | console output (quoted in A11Y-003) |
| `bugs_src.py` | `python qa/tools/bugs_src.py qa` | regenerates `bugs.json` + `BUG_REPORT.md` | — |

The scripts default to `BASE=http://localhost:8000`; set `BASE` to target another origin.

## 3. Manual / probe checks

| Check | Method | Result |
|---|---|---|
| API inventory and error handling | curl / urllib (see API_BACKEND_AUDIT.md) | 20 documented routes; 500s on replay endpoints; traversal confirmed with `pyproject.toml` only |
| 48-state model integrity | Python import of `build_agent_model` | 48/48 unique, all reachable, normalised (AUTOMATA_AUDIT §4) |
| Trial count | sum of rows in `results/raw/*.csv` | 6518 = `suite_meta` sum |
| embedded browser pane | `the embedded browser pane tools` | pane hidden: viewport 0×0, rAF 0 fps → used only as evidence for AUTO-001; **no visual verification was done in that pane** |
| Listening servers | `Get-NetTCPConnection` (read-only) | only :8000 (this project) and :8080 (Oracle TNS listener, unrelated, untouched) |

## 4. Degree of verification

* **Verified in a browser (headless Edge):** all routes, all lab models, Explorer/Dashboard/Studio workflows, responsive layouts at 5 viewports, keyboard reach on the lab, theme toggle, reduced motion.
* **Verified by API probes only:** schema mismatches, 500s, traversal, unknown-route behaviour.
* **Code review only (not executed):** `npm run preview` proxy gap (CFG-001), long-running experiment behaviour and unbounded `n_states` memory growth (API-003, not load-tested to avoid disturbing the running server), screen-reader output.
* **Not tested:** real assistive technology (NVDA/JAWS/VoiceOver), Firefox/Safari, touch devices (only mobile emulation), the OpenAI provider, ALFWorld/HotpotQA (not run in the project either).

## 5. Correction of an earlier claim

At the end of the previous build session the build session reported "API endpoints return 200" after probing `/api/models`, `/api/results/groups`, `/api/results/paired`, `/api/tests`, `/api/figures`. Three of those paths do not exist; they returned the SPA's `index.html` with status 200 (API-002). That check was a false positive.

## 6. Side effects of the audit

* New files only under `qa/`.
* The running server appended tracebacks for the deliberately invalid replay requests to `results/processed/api_err.txt` (its stderr log). No other project file changed.
* Temporary Edge profiles were created in the system temp directory and are disposable.
