# Final handoff

## Files generated (all new, under `qa/`)

| File | Content |
|---|---|
| `EXECUTIVE_SUMMARY.md` | one-page status, top issues, fix order, limitations |
| `BUG_REPORT.md` | 39 reproducible records (template: ID, severity, category, route, steps, expected/actual, evidence, root cause, sources, fix, tests, dependencies, confidence) |
| `bugs.json` | the same 39 records, machine-readable (generated from the same source as BUG_REPORT.md) |
| `PAGE_AUDIT.md` | route-by-route workflows, interactions, data dependencies, defects |
| `AUTOMATA_AUDIT.md` | render pipeline trace, homepage vs lab, 48-state validation, 47/48 explanation, model-by-model table, q-naming/coverage requirement |
| `API_BACKEND_AUDIT.md` | endpoint inventory, schema mismatches, error handling, security, reproduction commands |
| `UI_UX_AUDIT.md` | strengths, blockers, IA, hierarchy, visualisation, forms, a11y, responsive, component recommendations |
| `TEST_REPORT.md` | commands, exit codes, counts, coverage gaps, verification level, side effects |
| `FIX_PLAN.md` | ordered implementation tasks with acceptance criteria and verification commands |
| `HANDOFF.md` | this file |
| `evidence/` | JSON outputs of the audit scripts, 90+ screenshots, pytest/vitest/tsc output |
| `tools/` | `cdp.mjs` (headless-Edge DevTools driver), `01_routes.mjs` … `06_kb.mjs`, `bugs_src.py` |

## Audit scope

Repository inspection (frontend React 18.3 / TypeScript 5.6 / Vite 5.4 / react-router 6 / d3-zoom / recharts / framer-motion / KaTeX; backend FastAPI + pydantic 2, Python 3.13), all 9 routes and the 404 route, all 12 automata models, Explorer/Dashboard/Studio workflows, 20 API routes, the 48-state model internals, 5 viewports, keyboard/ARIA checks, existing test suites. No git repository exists in this folder (no `git status` possible). No source, configuration, dependency or data file was modified.

## Confirmed root causes

* **SEC-001** unchecked `DIST / full_path` in the SPA fallback.
* **EXPL-001 / DASH-002** request bodies and displays derived from live form state instead of the stored run.
* **AUTO-001** fit computed from a 0-px container (`k = 0`, zoom extent 0 → `Infinity`); Reveal/CountUp require animation frames + IntersectionObserver (mechanism established; link to the user's report highly likely).
* **DATA-001** KPI count-up animation — the 47/144/6413 values are animation frames; the data are 48/146/6518.
* **API-001** inner `AttribReq(...)` validation error escaping as 500.
* **AUTO-005** `_agent_view` filters out sink transitions.
* **AUTO-007** TM trace `steps` is an integer.
* **DOC-002** operator precedence in the range expression.
* **UI-001** `text-transform: uppercase` on Greek letters.

## Unresolved questions (for the user)

1. Where exactly did you see the lab "not working": in the embedded browser pane, in Chrome/Edge at `http://localhost:8000`, or via `npm run dev` / `npm run preview`? A screenshot and the browser console would confirm AUTO-001 vs CFG-001 vs the API being down.
2. Was the homepage screenshot (47 / 144 / 6413) taken right after the page loaded? (That would confirm DATA-001.)
3. For the `q0, q1, …` naming: should the semantic names (e.g. `PLAN_SUBGOAL`) disappear entirely, or stay as secondary labels? The plan assumes secondary labels, so figures, paper and results that use the names stay valid.
4. Which additional textbook cases matter most for the course (dead state, subset construction, ε-removal, PDA rejection, TM step limit, minimisation, regex↔NFA)? The plan includes all but minimisation and regex.

## Highest-priority fixes

SEC-001 → EXPL-001 → AUTO-001 → API-001/API-002 → AUTO-002…005, AUTO-007 → UX-001 → DATA-001, DASH-001, DASH-002, FORM-001, UI-001 → AUTO-006.

## Recommended implementation sequence

Phases 1–7 in [FIX_PLAN.md](FIX_PLAN.md): blockers → automata → statistical/data integrity → page defects → UX → accessibility/responsive → docs and full regression. Update `bugs.json` `status` per ID as fixes land; do not delete records.

## Commands the implementer should run after implementing changes

```powershell
# backend
python -m pytest -q
# frontend
cd website
npx tsc --noEmit
npx vitest run
npm run build
cd ..
# restart the server so it serves the new build
uvicorn afcr.api.app:app --port 8000
# end-to-end evidence (new folder; keep the original evidence/ untouched)
node qa/tools/01_routes.mjs qa/evidence-after
node qa/tools/02_lab.mjs qa/evidence-after
node qa/tools/03_zero.mjs qa/evidence-after
node qa/tools/04_workflows.mjs qa/evidence-after
node qa/tools/05_responsive_a11y.mjs qa/evidence-after
# API spot checks
curl -s --path-as-is -o /dev/null -w "%{http_code}\n" "localhost:8000/../../pyproject.toml"
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" localhost:8000/api/nope
curl -s -X POST localhost:8000/api/replay -H "Content-Type: application/json" -d "{\"seed\":-1,\"arm\":0}"
# refresh the stored test reports shown on the website (only after everything passes)
python scripts/run_tests_report.py
cd website; npx vitest run --reporter=json --outputFile=../results/processed/frontend_test_report.json; cd ..
```
