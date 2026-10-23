# Implementation plan

Work top to bottom. Each task lists the bug IDs, files, required behaviour, dependencies, acceptance criteria, regression tests and verification commands. Full reproduction details: [BUG_REPORT.md](BUG_REPORT.md) / [bugs.json](bugs.json). Do not change scientific results, add automaton states to reach a number, or remove honesty labels.

Common verification (run after every phase):

```powershell
python -m pytest -q
cd website; npx tsc --noEmit; npx vitest run; npm run build; cd ..
# restart the API so it serves the new build, then:
node qa/tools/01_routes.mjs qa/evidence-after
node qa/tools/02_lab.mjs qa/evidence-after
```

(Create `qa/evidence-after/` for post-fix evidence; keep the original `evidence/` untouched.)

---

## Phase 1 — P0/P1 application and integration blockers

### T1.1 Path traversal in the SPA fallback — SEC-001 (+ API-002)
* **Files:** `src/afcr/api/app.py` (`spa`, lines ~509-522).
* **Behaviour:** paths resolving outside `website/dist` never served; `api/…` and `files/…` paths that don't match a route → 404 JSON; everything else → index.html.
* **Acceptance:** `curl --path-as-is localhost:8000/../../pyproject.toml` ≠ 200 with file content (all four encodings in the bug); `GET /api/nope` → 404 `application/json`; `/lab`, `/assets/<file>` unchanged.
* **Tests:** new `tests/test_api_http.py` with FastAPI `TestClient` (httpx is in the dev extra): traversal cases, unknown API route, SPA route.
* **Also:** `website/src/lib/api.ts request()` — reject non-JSON bodies for JSON endpoints (vitest).

### T1.2 Explorer uses the loaded trajectory's parameters — EXPL-001
* **Files:** `website/src/pages/Explorer.tsx`.
* **Behaviour:** keep `loaded = { params, traj }`; replay/estimate use `loaded.params`; if the form differs, show "Parameters changed — resample to apply" and disable replay/estimate.
* **Acceptance:** load seed 5 → change seed to 11 → replay request body has seed 5 (or the button is disabled with the notice).
* **Tests:** vitest in `src/test/app.test.tsx` (mock fetch, assert POST body).

### T1.3 Lab and reveal content robust to zero-size / non-painting mounts — AUTO-001 (+ UX-002)
* **Files:** `website/src/graph/GraphCanvas.tsx` (`fit`, ResizeObserver effect, zoom extent, `fitSig`), `website/src/ui/kit.tsx` (`Reveal`, `CountUp`), `website/src/styles.css` (print rule).
* **Behaviour:** never fit when `w <= 0 || h <= 0`; clamp `k` to `[0.2, 4.5]`; zoom extent uses `max(1, w)`; refit on the first positive ResizeObserver size even if the user wheeled before; Reveal renders visible content when IntersectionObserver is missing / when printing (animate transform only, or start at opacity 1); CountUp handled in T3.1.
* **Acceptance:** CDP: mount `/lab` at 1×1 → transform never contains `scale(0)`, `NaN` or `Infinity`; resize to 1440×900 → 48/48 nodes visible. Full-page capture of `/theory` without scrolling shows all sections.
* **Tests:** vitest: GraphCanvas with mocked `clientWidth` 0 then 800 (ResizeObserver mock); Reveal visible without IntersectionObserver. Re-run `tools/03_zero.mjs`.
* **Depends on:** none.

## Phase 2 — Automata rendering and execution

### T2.1 Graph visible in the first viewport — UX-001
* **Files:** `website/src/pages/Lab.tsx`, `website/src/styles.css` (`.model-bar`, `.lab-grid`, remove duplicate `.lab-grid` rules → POL-001).
* **Behaviour:** compact header; model selection in one toolbar row inside the graph card (grouped select or compact segmented control); graph `min-height: calc(100vh - 160px)`.
* **Acceptance:** at 1440×900 ≥ 80 % of the 48 nodes are inside the initial viewport; at 390×844 the graph card's top is above 844 px.

### T2.2 Truthful per-model results — AUTO-002, AUTO-003, AUTO-004, AUTO-007
* **Files:** `src/afcr/api/app.py` (`trace`), `src/afcr/automata/pda.py` (run), `src/afcr/automata/turing.py` / transducers (`to_json`), `website/src/lib/api.ts` (TraceResponse → discriminated union by `kind`), `website/src/pages/Lab.tsx` (result panel per kind).
* **Behaviour:**
  * PA: no `accepted` verdict; show exact P(accept) and MC estimate as the result; sampled path labelled as a sample.
  * Mealy/Moore: no acceptance; result = output word.
  * PDA: rejecting runs return the explored configuration sequence and `reject_reason`; UI keeps playback and shows the reason.
  * TM: `steps` is always a list (configurations) or rename the count to `n_steps`; toast shows a number.
  * Add `kind` to every trace response and FastAPI `response_model`s.
* **Acceptance:** for every model the result panel matches the table in AUTOMATA_AUDIT §5 "expected"; no "undefined" in toasts; `tools/02_lab.mjs` shows `afterReject.stepLabel` non-null for PDA.
* **Tests:** new `tests/test_api_automata.py` (shape per model, PDA reject ≥ 1 step, TM steps list, PA/Mealy/Moore no verdict); vitest for each panel.

### T2.3 Total DFA view for the 48-state model — AUTO-005
* **Files:** `src/afcr/api/app.py` (`_agent_view`), `website/src/pages/Lab.tsx` (callout), `GraphCanvas` (render a `sink` node style).
* **Behaviour:** include `⊥sink` (flag `sink: true`, excluded from `count_logical_states`) and one aggregated default edge per state ("other → ⊥").
* **Acceptance:** DFA view shows 49 nodes (48 logical + sink), callout accurate, `count_logical_states` still 48.
* **Tests:** pytest on the view payload.

### T2.4 Set-semantics playback and LTS blocking — AUTO-008, AUTO-009
* **Files:** `website/src/pages/Lab.tsx` (`trailFromTrace`, `trailIndex`, `countUpTo`, trace panel), `website/src/graph/GraphCanvas.tsx` (`current`).
* **Behaviour:** per-step edge groups; reveal exactly the edges of steps < idx; step 0 active set = ε-closure(q0); no single current marker for NFA/ε-NFA; LTS blocked step shown as a badge and highlighted state; show `deadlocks` from the payload.
* **Tests:** vitest with a synthetic NFA trace whose steps contribute 1, 3 and 2 edges.

### T2.5 `qN` state naming and coverage examples — AUTO-006 (user requirement)
* **Files:** `src/afcr/api/app.py` (`small_models`, graph payloads), `src/afcr/automata/benchmark48.py` (stable qid order), `src/afcr/automata/{dfa,nfa,pa,pda,turing,transducers}.py` (example machines), `website/src/pages/Lab.tsx`, `GraphCanvas.tsx` (label `qN · name`), search matches both.
* **Behaviour:** every node has `qid` `q0…`; 48-state model `q0…q47` (documented order: group, then position); examples cover accept/reject/empty/invalid/dead state; add NFA→DFA subset-construction view, ε-removal view, PA with ≥ 2 symbols and a rejecting sink, PDA reject example, TM step-limit example.
* **Constraints:** keep the 48 logical states; keep existing ids available (e.g. `name`) so results/figures referring to `PLAN_SUBGOAL` stay valid; update the tests in `tests/test_automata.py` only by adding cases.
* **Tests:** pytest: unique `^q\d+$` per model, agent48 q0..q47; example coverage; vitest rendering.

### T2.6 Graph readability — VIS-001, POL-002
* **Files:** `website/src/graph/GraphCanvas.tsx`, `website/src/graph/layout.ts`, `Lab.tsx` (Tape).
* **Behaviour:** merge parallel edges (one path, combined label); include self-loop extents in `bbox`; label background/halo and offset; agent48 edge labels on hover only; mobile list/table mode; TM tape window fixed over the whole trace with indices.
* **Acceptance:** `tools/02_lab.mjs` → `overlappingLabelPairs == 0` for all models; Moore self-loop inside the viewport.

## Phase 3 — Statistical correctness and data integrity

### T3.1 Static research metrics — DATA-001
* **Files:** `website/src/ui/kit.tsx` (`Stat`, `CountUp`), `website/src/pages/Overview.tsx`.
* **Behaviour:** KPIs show final numbers immediately; tests KPI shows "last run <ran_at>".
* **Acceptance:** CDP sample at 100 ms after data arrives = `48 | 146 | 6518 | 0`.

### T3.2 Threshold targets on the Dashboard — DASH-001
* **Files:** `website/src/pages/Dashboard.tsx`.
* **Behaviour:** branch on `res.target.name`; threshold panel with per-arm certified-above / certified-below / undecided; θ line on the forest plot; correctness against the true first/last ≥ θ index.
* **Tests:** vitest with a last_above result fixture.

### T3.3 Results bound to their configuration — DASH-002, FORM-001
* **Files:** `Dashboard.tsx`, `Explorer.tsx`, `Studio.tsx`, `ui/kit.tsx` (`NumberField`).
* **Behaviour:** store `{req, res}`; displays and "compare with uniform" use `req`; stale marker when the form changes; NumberField reports validity and submit buttons are disabled while any field is invalid.
* **Tests:** vitest: δ = 0 disables Run (no POST); budget edit after run doesn't change "budget used"; compare posts the original seed.

### T3.4 Greek symbols in labels — UI-001
* **Files:** `website/src/styles.css`, label strings in Dashboard/Studio/Explorer.
* **Acceptance:** labels read "CONFIDENCE δ", "TOLERANCE ε".

### T3.5 Headline claim — INT-001
* **Files:** `website/src/pages/Overview.tsx`.
* **Acceptance:** the "objective, not a proven property" qualifier is inside the hero heading block and links to Theory §6.

## Phase 4 — Page-specific functional defects

| Task | Bugs | Files | Acceptance | Tests |
|---|---|---|---|---|
| T4.1 Replay endpoint validation | API-001 | `src/afcr/api/app.py` (ReplayReq/EstReq bounds; global `ValidationError → 422` handler) | 5 bodies in the bug → 422 | pytest HTTP tests |
| T4.2 Bounds and long runs | API-003 | `app.py` (TraceReq/graph `n_states` 48..96; experiment work cap or job endpoint) | n_states 1000 → 422; oversized experiment → 422 | pytest |
| T4.3 Dashboard caption, export, cancel | DASH-003, DASH-004 | `Dashboard.tsx`, `lib/api.ts` (AbortSignal) | caption names the algorithm; Export JSON/CSV; Cancel aborts | vitest |
| T4.4 Hero console errors | FE-001 | `ui/HeroGraph.tsx` | 0 console errors on `/` | CDP `01_routes.mjs` |
| T4.5 Related timeline & filter | REL-001 | `pages/Related.tsx` | no clipped labels; "CAR" finds CAR; empty state row | vitest + screenshot |
| T4.6 Docs reference & search | DOC-002, DOC-003 | `pages/Docs.tsx` | seed shows "≥ 0"; "LUCB" finds sections | vitest |
| T4.7 Stale instructions | DOC-001 | `pages/Reproducibility.tsx`, `pages/Docs.tsx` | only existing scripts listed; spec example parses with `run_one.load_spec` | pytest: grep `scripts/*.py` mentioned in `website/src` exist |
| T4.8 Vite preview proxy | CFG-001 | `website/vite.config.ts` | `npm run preview` → `/api/health` JSON via :4173 | manual |
| T4.9 OpenAPI summaries | POL-003 | `app.py` `_mk` | no summary < 3 chars | pytest |

## Phase 5 — UI/UX improvements

Follow [UI_UX_AUDIT.md](UI_UX_AUDIT.md) §3–§5 and §8: cross-links that carry configuration (Explorer → Dashboard → Studio), "How to use this site" strip, per-view captions in the lab, model-specific legends, compact tool-page headers, grouped Studio chips, caption sizes ≥ 12 px. Remove dead UI (POL-001). No change to colours/tokens is required.

## Phase 6 — Accessibility and responsive behaviour

| Task | Bugs | Acceptance |
|---|---|---|
| T6.1 Headings & landmarks | A11Y-001 | one `<h1>`, one `<main>` per page |
| T6.2 ARIA tabs | A11Y-002 | arrow keys + `aria-controls`/`tabpanel` |
| T6.3 Keyboard rows & focus halo | A11Y-003 | Enter on matrix/ranking/forest rows; visible focus on graph nodes |
| T6.4 Drawer & route focus | A11Y-004 | focus trap + Escape; focus h1 on navigation; per-page `document.title` |
| T6.5 Cursor | A11Y-005 | native cursor visible; loop paused when idle/hidden |
| T6.6 Responsive lab | UX-001, VIS-001 | 390 px list/table mode; re-run `tools/05_responsive_a11y.mjs` (no new overflow) |

## Phase 7 — Documentation and final regression

1. Update README / docs only where behaviour changed (trace response kinds, qid naming, new endpoints/limits).
2. Re-generate project artefacts that display test counts (`python scripts/run_tests_report.py`; frontend JSON report) **after** all tests pass.
3. Re-run all audit scripts into `qa/evidence-after/` and compare with `evidence/`:
   * 0 exceptions, 0 console errors on every route;
   * all P1/P2 acceptance criteria above;
   * `bugs.json`: set `status` to `fixed` / `wont_fix` per ID with a one-line note (do not delete records).
4. Final commands:

```powershell
python -m pytest -q
cd website; npx tsc --noEmit; npx vitest run; npm run build; cd ..
uvicorn afcr.api.app:app --port 8000      # restart to serve the new build
node qa/tools/01_routes.mjs qa/evidence-after
node qa/tools/02_lab.mjs qa/evidence-after
node qa/tools/03_zero.mjs qa/evidence-after
node qa/tools/04_workflows.mjs qa/evidence-after
node qa/tools/05_responsive_a11y.mjs qa/evidence-after
```
