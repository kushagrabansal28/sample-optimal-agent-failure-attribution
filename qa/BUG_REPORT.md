# Bug report — AFCR application audit

39 records, sorted by severity, then dependency order. Machine-readable copy: [`bugs.json`](bugs.json) (generated from the same source).

Severity: **P0** unusable / critical integrity or security · **P1** major feature or primary workflow broken · **P2** important functionality degraded · **P3** minor defect / usability · **P4** polish.

| ID | Sev | Category | Title | Confidence |
|---|---|---|---|---|
| [AUTO-001](#auto-001) | P1 | visualization | Lab graph and scroll-revealed sections render blank when the page is mounted in a zero-size or non-painting viewport (e.g. the hidden embedded browser pane) | highly likely |
| [EXPL-001](#expl-001) | P1 | frontend | Replay and μ̂ estimate are computed for the current form values, not for the trajectory on screen | confirmed |
| [SEC-001](#sec-001) | P1 | backend | Path traversal: the SPA catch-all serves any file outside website/dist | confirmed |
| [API-001](#api-001) | P2 | backend | Replay endpoints return HTTP 500 for out-of-range input instead of 422 | confirmed |
| [AUTO-002](#auto-002) | P2 | automata semantics | Probabilistic automaton shows 'accepted'/'rejected' from one sampled run | confirmed |
| [AUTO-003](#auto-003) | P2 | automata semantics | Mealy and Moore transducers are reported as 'accepted' | confirmed |
| [AUTO-004](#auto-004) | P2 | automata semantics | PDA rejections return an empty trace, so the user cannot see where the run failed | confirmed |
| [AUTO-005](#auto-005) | P2 | automata semantics | The 48-state 'DFA' view is not total and hides the sink it claims to add | confirmed |
| [AUTO-006](#auto-006) | P2 | automata semantics | Requirement: states must use q0, q1, … naming and every model must demonstrate all relevant cases | confirmed |
| [DASH-001](#dash-001) | P2 | statistics | For threshold targets the stopping-rule panel and the correctness badge use the argmax rule | confirmed |
| [DASH-002](#dash-002) | P2 | frontend | Result panels read the live form instead of the run that produced them | confirmed |
| [DATA-001](#data-001) | P2 | research integrity | Homepage metrics are animated count-ups: screenshots and throttled windows show wrong values (the reported 47 / 144 of 146 / 6413) | confirmed |
| [FORM-001](#form-001) | P2 | frontend | Invalid numeric input is flagged but the run silently uses the previous valid value | confirmed |
| [UI-001](#ui-001) | P2 | research integrity | CSS uppercase turns δ into Δ and ε into Ε in form labels | confirmed |
| [API-002](#api-002) | P2 | API integration | Unknown /api/* paths return 200 index.html, and the client accepts HTML as data | confirmed |
| [UX-001](#ux-001) | P2 | UX | The automaton graph starts below the fold (≈650 px of header and model picker first) | confirmed |
| [A11Y-001](#a11y-001) | P3 | accessibility | No <h1> outside the homepage; nested <main> landmark in the lab | confirmed |
| [A11Y-002](#a11y-002) | P3 | accessibility | Tabs lack tabpanel wiring and arrow-key navigation | confirmed |
| [A11Y-003](#a11y-003) | P3 | accessibility | Clickable rows and plot rows are not keyboard operable; SVG node focus ring is invisible | highly likely |
| [A11Y-004](#a11y-004) | P3 | accessibility | Mobile menu does not take focus or close on Escape; route changes do not move focus or update the title | confirmed |
| [A11Y-005](#a11y-005) | P3 | accessibility | Custom cursor hides the native pointer site-wide and runs a permanent rAF loop | confirmed |
| [API-003](#api-003) | P3 | backend | Unbounded n_states on trace/graph and synchronous long experiment runs | confirmed (code), not load-tested |
| [AUTO-007](#auto-007) | P3 | API integration | TM trace returns `steps` as a number; UI toasts 'Trace computed (undefined steps)' | confirmed |
| [AUTO-008](#auto-008) | P3 | visualization | NFA/ε-NFA playback marks a single 'current' state, omits the initial ε-closure and maps steps to edges proportionally | confirmed |
| [AUTO-009](#auto-009) | P3 | automata semantics | LTS deadlock / blocked step is not shown | confirmed |
| [CFG-001](#cfg-001) | P3 | documentation | `npm run preview` has no /api proxy, so the previewed site cannot reach the backend | highly likely |
| [DASH-003](#dash-003) | P3 | frontend | Caption says 'LUCB would pull next' for every algorithm | confirmed |
| [DASH-004](#dash-004) | P3 | frontend | No result export and no way to cancel a long attribution run | confirmed |
| [DOC-001](#doc-001) | P3 | documentation | Stale and non-runnable instructions on the site | confirmed |
| [DOC-002](#doc-002) | P3 | documentation | API reference drops bounds of 0 (operator precedence) and nullable types | confirmed |
| [DOC-003](#doc-003) | P3 | documentation | Documentation search only matches hand-written keyword strings | confirmed |
| [FE-001](#fe-001) | P3 | frontend | Homepage logs 32 SVG errors per load: <circle> cx/cy 'undefined' | confirmed (errors), highly likely (cause) |
| [INT-001](#int-001) | P3 | research integrity | Homepage headline says 'Sample-optimal' while Theory says the project never calls AFCR sample-optimal | confirmed |
| [REL-001](#rel-001) | P3 | visualization | Related-work timeline clusters 2025–26 papers into clipped, overlapping labels; 'CAR' search finds nothing | confirmed |
| [VIS-001](#vis-001) | P3 | visualization | Graph readability: overlapping edge labels, clipped self-loops, edge labels over node labels, tiny scale for 96 states / mobile | confirmed |
| [UX-002](#ux-002) | P3 | UX | Content below the fold is invisible until scrolled (print, full-page capture, find-in-page) | confirmed |
| [POL-001](#pol-001) | P4 | frontend | Dead UI and conflicting CSS | confirmed |
| [POL-002](#pol-002) | P4 | visualization | Turing-machine tape window shifts as the head moves; blank symbol differs between backend and UI | confirmed |
| [POL-003](#pol-003) | P4 | backend | Markdown file routes appear in OpenAPI with summary ' F' | confirmed |

## AUTO-001

**Lab graph and scroll-revealed sections render blank when the page is mounted in a zero-size or non-painting viewport (e.g. the hidden embedded browser pane)**

- **Severity:** P1  ·  **Category:** visualization  ·  **Confidence:** highly likely  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab (also /theory, /related, /reproducibility, / KPIs)` — graph/GraphCanvas.tsx (fit, ResizeObserver, d3-zoom extent); ui/kit.tsx (Reveal, CountUp)
- **Preconditions:** API running on :8000. Page loaded while its viewport has no size or does not paint (embedded browser pane hidden/minimised; background tab; a collapsed iframe).

**Steps to reproduce**

1. Open http://localhost:8000/lab in the embedded browser pane while the pane is hidden (or emulate a 1x1 viewport over CDP).
2. Inspect `.graph-svg > g` and the page sections.
3. Navigate to /theory and inspect the opacity of the <Reveal> sections below the first two.
4. On /, read the four KPI values.

**Expected.** The 48 states are drawn at a readable scale as soon as the graph is visible; content does not depend on animation frames or scroll position to become visible; KPIs show their real values.

**Actual.** In the hidden pane: innerWidth=innerHeight=0, requestAnimationFrame fires 0 times/s, the graph group transform is `translate(0,310) scale(0)` (all 48 nodes and 89 edges exist in the DOM but are drawn at zero size), KPIs read `0 | 0 | 0 | 0`. A wheel event while collapsed produces `translate(Infinity,Infinity) scale(0.2)`. On /theory, 5 of 7 <Reveal> sections stay at opacity 0 until scrolled into view. The homepage hero graph is unaffected because it is a viewBox-scaled SVG with no measured fit — which matches the report that the automaton 'shows on the homepage but not in other sections'.

**Evidence**

- embedded pane probe: {innerWidth:0, rafFramesIn1s:0, gTransform:'translate(0,310) scale(0)', nodes:48, edges:89}
- qa/evidence/03_hypotheses.json (A_mount_1px, B_after_wheel_collapsed, C_theory_reveal)
- qa/evidence/hyp_C_theory_fullpage_noscroll.png
- In a visible 1440x900 headless Edge the same page renders correctly (qa/evidence/02_lab.json) and recovers after a resize (A_after_resize).

**Root cause (highly likely).** Established for the mechanism, highly likely for the user's report: GraphCanvas computes the fit from the container's clientWidth (0 → k=0) and d3-zoom's extent [[0,0],[w,h]] with w=0 (→ Infinity); Reveal/CountUp/page transitions need IntersectionObserver + requestAnimationFrame to reach their final state. The homepage graph uses a fixed viewBox instead.

**Source locations**

- `website/src/graph/GraphCanvas.tsx:118-124 (fit with w=0)`
- `website/src/graph/GraphCanvas.tsx:139-149 (ResizeObserver; initial setSize with clientWidth 0)`
- `website/src/graph/GraphCanvas.tsx:154 (zoom extent uses sizeRef w)`
- `website/src/graph/GraphCanvas.tsx:166-167 (fitSig effect fits at w=0)`
- `website/src/ui/kit.tsx:265-267 (Reveal initial opacity 0)`
- `website/src/ui/kit.tsx:234-251 (CountUp)`

**Recommended fix direction.** Never fit when w<=0 or h<=0 (skip and retry on the next ResizeObserver tick); clamp k to the zoom scaleExtent; guard the zoom extent against zero size; render the SVG with a viewBox fallback so it is visible before measurement. Make Reveal render visible content by default (animate only an enhancement; no opacity:0 initial state when IntersectionObserver is unavailable or when printing). Render scientific KPI values as final numbers (see DATA-001).

**Regression tests**

- vitest: GraphCanvas mounted with clientWidth 0 never produces scale(0)/NaN/Infinity and fits once a width appears.
- vitest: Reveal children are visible (opacity 1) when IntersectionObserver is undefined.
- CDP/Playwright: load /lab at 1x1, resize to 1440x900, assert ≥48 visible nodes; wheel at 1x1 then resize, assert finite transform.

**Dependencies:** none

## EXPL-001

**Replay and μ̂ estimate are computed for the current form values, not for the trajectory on screen**

- **Severity:** P1  ·  **Category:** frontend  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/explorer` — website/src/pages/Explorer.tsx (body, doReplay, doEstimate)
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /explorer, keep seed 5, press 'Sample failed trajectory' (5 steps: PLAN_START>…>PLAN_SUBGOAL_WRONG).
2. Change Seed to 11 but do NOT resample.
3. With step 4 selected press 'Run one counterfactual replay' (same for 'Estimate μt', or after changing Intervention / Fault probability).

**Expected.** The replay uses the parameters of the loaded trajectory (seed 5, its eps_plan and intervention), or the stale form is clearly flagged and the action disabled until resampling.

**Actual.** Request body is {seed: 11, arm: 3, ...}. The 'Original run' column of the replay shows a different 13-step trajectory (PLAN_START>PLAN_DECOMP>…>MEM_CORRUPT) while the chart and step list still show the seed-5 trajectory; the arm index is applied to the wrong trajectory (and can be out of range → 422).

**Evidence**

- qa/evidence/04_workflows.json explorer_stale
- qa/evidence/explorer_stale_seed_replay.png

**Root cause (established).** `const body = { source, seed, eps_plan: eps, intervention: interv, deterministic: det }` is rebuilt on every render from the live form state and reused by doReplay/doEstimate.

**Source locations**

- `website/src/pages/Explorer.tsx:70-87`

**Recommended fix direction.** Store the request parameters together with the loaded trajectory (e.g. `loaded = {params, traj}`) and use `loaded.params` for replay/estimate. When the form differs from `loaded.params`, show a 'parameters changed — resample' notice and disable replay/estimate (or resample automatically).

**Regression tests**

- vitest: load seed 5, change seed to 11, click replay → POST /api/replay body has seed 5 (or the button is disabled with a notice).
- vitest: same for estimate and for intervention / eps changes.

**Dependencies:** none

## SEC-001

**Path traversal: the SPA catch-all serves any file outside website/dist**

- **Severity:** P1  ·  **Category:** backend  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `GET /{full_path:path} (SPA fallback)` — src/afcr/api/app.py spa()
- **Preconditions:** Built website (website/dist exists); server running.

**Steps to reproduce**

1. curl --path-as-is http://localhost:8000/../../pyproject.toml
2. Repeat with /..%2F..%2Fpyproject.toml, /%2e%2e/%2e%2e/pyproject.toml, /..%5C..%5Cpyproject.toml

**Expected.** 404 (or index.html) for every path that resolves outside website/dist.

**Actual.** HTTP 200, application/octet-stream, 926 B: the project's pyproject.toml. Any readable file on the machine reachable by relative path can be served (the auditor read only pyproject.toml).

**Evidence**

- /..%2F..%2Fpyproject.toml -> 200 application/octet-stream 926B, body starts '[build-system]' (all four encodings)

**Root cause (established).** `f = DIST / full_path; if f.is_file(): return FileResponse(f)` with no check that f.resolve() is inside DIST.

**Source locations**

- `src/afcr/api/app.py:513-518`

**Recommended fix direction.** Resolve the candidate and require `f.resolve().is_relative_to(DIST.resolve())`; otherwise fall back to index.html (or 404). Do not serve dotfiles. Keep the server bound to 127.0.0.1.

**Regression tests**

- pytest (TestClient): GET '/../../pyproject.toml', '/..%2F..%2Fpyproject.toml', '/%2e%2e/%2e%2e/pyproject.toml', '/..%5C..%5Cpyproject.toml' never return pyproject content.
- pytest: GET '/assets/<real file>' and '/lab' still work.

**Dependencies:** none

## API-001

**Replay endpoints return HTTP 500 for out-of-range input instead of 422**

- **Severity:** P2  ·  **Category:** backend  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `POST /api/replay, POST /api/replay/estimate` — src/afcr/api/app.py ReplayReq/EstReq, replay(), replay_estimate()
- **Preconditions:** Server running.

**Steps to reproduce**

1. POST /api/replay {"seed":-1,"arm":0}
2. POST /api/replay {"seed":0,"arm":0,"n_states":500}  (also n_states 10, eps_plan 1.5)
3. POST /api/replay/estimate {"seed":-3,"arm":0,"n":10}

**Expected.** 422 with a readable field message (as /api/trajectory does for the same values).

**Actual.** 500 Internal Server Error (text/plain). Traceback in results/processed/api_err.txt: pydantic ValidationError for AttribReq.seed.

**Evidence**

- 5 probes → 500; /api/trajectory {seed:-1} → 422 'Input should be greater than or equal to 0'

**Root cause (established).** ReplayReq has unconstrained seed/n_states/eps_plan; the handler builds AttribReq(...) inside the request, whose ValidationError is not converted to an HTTP error.

**Source locations**

- `src/afcr/api/app.py:314-341`
- `src/afcr/api/app.py:379-394`

**Recommended fix direction.** Give ReplayReq the same Field constraints as TrajReq/AttribReq (seed ge=0, n_states 48..96, eps_plan [0,1)); additionally catch pydantic.ValidationError/ValueError around build_env and return 422.

**Regression tests**

- pytest: each of the 5 bodies above returns 422 with a field name in detail.
- pytest: no endpoint returns 500 for a sweep of invalid bodies (property test over fields).

**Dependencies:** none

## AUTO-002

**Probabilistic automaton shows 'accepted'/'rejected' from one sampled run**

- **Severity:** P2  ·  **Category:** automata semantics  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab?model=pa` — src/afcr/api/app.py trace() (pa); website/src/pages/Lab.tsx result badges
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /lab?model=pa, word 'go', press Run trace.

**Expected.** Acceptance is reported as a probability (exact P(accept), Monte-Carlo estimate); the sampled path is labelled 'one sampled run ended in t (accepting)', not 'accepted'.

**Actual.** Badges: 'accepted' + 'exact P(accept) = 0.7000' + 'Monte-Carlo 0.705 [0.685, 0.725]'. Re-running can flip the badge to 'rejected' for the same word.

**Evidence**

- qa/evidence/02_lab.json pa.afterReject
- qa/evidence/lab_pa_reject.png

**Root cause (established).** trace() returns sample_run(...).to_json() whose `accepted` field is the sampled path's outcome; Lab renders any `accepted` field as an acceptance verdict.

**Source locations**

- `src/afcr/api/app.py:218-222`
- `website/src/pages/Lab.tsx:298`

**Recommended fix direction.** Rename the field for PA to `sample_ended_accepting` (keep exact/MC probabilities as the verdict) and render a model-specific result panel.

**Regression tests**

- pytest: PA trace JSON has exact_acceptance_probability and no `accepted` verdict key.
- vitest: PA result shows probability badges and no 'accepted' badge.

**Dependencies:** none

## AUTO-003

**Mealy and Moore transducers are reported as 'accepted'**

- **Severity:** P2  ·  **Category:** automata semantics  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab?model=mealy, /lab?model=moore` — src/afcr/api/app.py trace(); automata/transducers.py; Lab.tsx
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /lab?model=mealy (or moore), press Run trace; try 'ok ok' on Moore.

**Expected.** No acceptance notion for transducers: show the output word only.

**Actual.** Badge 'accepted' next to the note 'transducer: no acceptance, see outputs'; Moore 'ok ok' also 'accepted'. Backend JSON has accepted: true.

**Evidence**

- qa/evidence/02_lab.json mealy/moore
- qa/evidence/lab_moore_trace_end.png

**Root cause (established).** The transducer trace object serialises a generic `accepted=True`; the UI shows it.

**Source locations**

- `src/afcr/api/app.py:216-217`
- `src/afcr/automata/transducers.py`
- `website/src/pages/Lab.tsx:298`

**Recommended fix direction.** Omit `accepted` for transducers (or set null) and render the output tape/word as the result.

**Regression tests**

- pytest: mealy/moore trace JSON has outputs and accepted is None/absent.
- vitest: no accepted/rejected badge for mealy/moore.

**Dependencies:** none

## AUTO-004

**PDA rejections return an empty trace, so the user cannot see where the run failed**

- **Severity:** P2  ·  **Category:** automata semantics  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab?model=pda, /lab?model=pda_typed` — src/afcr/automata/pda.py run(); Lab.tsx
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /lab?model=pda, enter 'call ret ret' (or 'call'), press Run trace.
2. Open pda_typed, enter 'open_search end_calc'.

**Expected.** Steps up to the failing configuration (stack underflow / type mismatch / non-empty stack at end) with the stack shown, plus the reason for rejection.

**Actual.** Response {accepted:false, steps:[]}. UI shows only a 'rejected' badge, playback controls disappear and the hint 'Press Run trace to execute the model…' reappears as if nothing ran.

**Evidence**

- POST /api/automata/trace {model:'pda', word:['call','ret','ret']} → nsteps 0
- qa/evidence/02_lab.json pda.afterReject
- qa/evidence/lab_pda_reject.png

**Root cause (suspected).** Suspected: PDA run returns the accepting path only (search over configurations) and an empty list when no path accepts.

**Source locations**

- `src/afcr/automata/pda.py`
- `src/afcr/api/app.py:232`
- `website/src/pages/Lab.tsx:271-313`

**Recommended fix direction.** Return the longest explored configuration sequence (or the deterministic prefix) with a `reject_reason` (no transition / stack mismatch / stack not empty); show it in the stack panel. Show a 'run finished: rejected' state instead of the initial hint.

**Regression tests**

- pytest: pda trace for ['call','ret','ret'] has ≥2 steps and reject_reason.
- vitest: rejected PDA run keeps playback and shows the reason.

**Dependencies:** none

## AUTO-005

**The 48-state 'DFA' view is not total and hides the sink it claims to add**

- **Severity:** P2  ·  **Category:** automata semantics  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab (48-state, DFA view)` — src/afcr/api/app.py _agent_view(view='dfa'); Lab.tsx callout
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /lab, Formalism view = DFA.
2. Compare with m.to_dfa(): 49 states (incl. ⊥sink), 2009 transitions over 41 symbols.

**Expected.** A DFA view consistent with the definition shown (δ total): either draw the sink (collapsed, e.g. 'all other symbols → ⊥') or label the view 'partial deterministic skeleton (sink omitted)'.

**Actual.** Graph shows 48 nodes and 48 edges (one per (state, action)); the callout says 'The DFA view adds an explicit sink that is not counted' but no sink is drawn; the definition says δ is total.

**Evidence**

- to_dfa(): states 49, delta 2009, alphabet 41, total=True; API dfa view: nodes 48, edges 48
- qa/evidence/lab_agent48_view_DFA.png

**Root cause (established).** _agent_view filters `if q in m.specs and r in m.specs`, dropping every transition into ⊥sink.

**Source locations**

- `src/afcr/api/app.py:126-130`
- `website/src/pages/Lab.tsx:180`

**Recommended fix direction.** Return the sink node (flag `sink: true`, excluded from the logical count) and one aggregated edge per state 'Σ∖{a} → ⊥'; update the callout to match.

**Regression tests**

- pytest: dfa view has a sink node and every non-sink state has an explicit default edge; count_logical_states stays 48.
- vitest: DFA view legend/callout mention the drawn sink.

**Dependencies:** none

## AUTO-006

**Requirement: states must use q0, q1, … naming and every model must demonstrate all relevant cases**

- **Severity:** P2  ·  **Category:** automata semantics  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab (all models)` — src/afcr/api/app.py small_models(); automata/benchmark48.py ids; Lab.tsx
- **Preconditions:** User requirement (stated in this audit request).

**Steps to reproduce**

1. Open each model in /lab and read the state ids.

**Expected.** Every model uses q-indexed state ids (q0, q1, …; 48-state model q0…q47) with the descriptive name as a secondary label, and each model shows its full set of cases (accept, reject, dead/trap state, empty word, invalid symbol; NFA active sets; ε-closure; PDA push/pop/reject; TM accept/reject/step-limit).

**Actual.** Only NFA and ε-NFA use q0…; DFA uses even/odd, PA s/t/f, LTS idle/thinking…, Mealy idle/calling/retrying, Moore product names 'idle/start', PDA q/acc, TM scan/carry/done/acc/rej, TM_pal has_a/go_a…, 48-state model PLAN_START…FAIL_TOOL. Toy models are minimal (DFA 2 states without a dead state; PA single-letter alphabet; PDA 2 states; no NFA→DFA subset-construction view although the backend implements and tests it; no TM step-limit demo).

**Evidence**

- qa/evidence/02_lab.json initial ids per model
- GET /api/automata/graph?model=<m> payloads (audit log)

**Root cause (established).** Design choice; not a defect in execution.

**Source locations**

- `src/afcr/api/app.py:53-65`
- `src/afcr/automata/benchmark48.py (state ids)`
- `src/afcr/automata/*.py (example machines)`
- `website/src/pages/Lab.tsx`

**Recommended fix direction.** Add a stable `qid` (q0…) to every node in the API (keep `id` semantic for back-compat or switch id→qid and move names to `label`), display 'q3 · Select subgoal' in nodes and tables; extend examples: DFA with a dead state (e.g. 3–4 states), NFA→DFA subset construction view, ε-NFA→NFA conversion, PA with ≥2 symbols and a rejecting sink, PDA with an explicit reject path, TM with a step-limit 'unknown' example. Keep the 48 logical-state count unchanged (do not add states to reach a number).

**Regression tests**

- pytest: every graph payload node has qid matching ^q\d+$, unique per model; agent48 qids are q0..q47.
- pytest: example machines cover accept/reject/empty/invalid cases.
- vitest: node labels render 'qN · name'.

**Dependencies:** none

## DASH-001

**For threshold targets the stopping-rule panel and the correctness badge use the argmax rule**

- **Severity:** P2  ·  **Category:** statistics  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/dashboard` — website/src/pages/Dashboard.tsx stats, correct, Stopping-rule card
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /dashboard, Target = 'Latest step ≥ θ (CAR locus)', θ = 0.5, Run attribution.

**Expected.** Panel shows the threshold rule state (which steps are certified above/below θ) and correctness against the threshold target's true answer.

**Actual.** Outcome 'culprit certified' with badge 'matches exact argmax', while the stopping card says 'best t=1: lo = 0.005 · strongest challenger t=2: hi = 1.000 · separation margin −0.995 · negative margin: intervals still overlap' — contradicting the certified outcome.

**Evidence**

- qa/evidence/04_workflows.json dash_last_above
- qa/evidence/dashboard_last_above.png

**Root cause (established).** `stats` (h, ℓ, margin) and `correct` are computed with argmax-ε logic regardless of res.target.name.

**Source locations**

- `website/src/pages/Dashboard.tsx:79-87`
- `website/src/pages/Dashboard.tsx:102-103`
- `website/src/pages/Dashboard.tsx:170-181`

**Recommended fix direction.** Branch on res.target.name: for first/last_above compute per-arm status (lo ≥ θ certified above, hi < θ certified below, undecided) and compare the answer with the true first/last index ≥ θ from ground_truth; hide the argmax margin.

**Regression tests**

- vitest: last_above result renders threshold status and no 'separation margin'; badge compares with the threshold truth.

**Dependencies:** none

## DASH-002

**Result panels read the live form instead of the run that produced them**

- **Severity:** P2  ·  **Category:** frontend  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/dashboard` — website/src/pages/Dashboard.tsx (req, compare, budget displays)
- **Preconditions:** A run has completed.

**Steps to reproduce**

1. Run attribution with budget 20000 (6089 rollouts → 'budget used 30%').
2. Change Rollout budget to 100000 without re-running.
3. Change seed and press 'Run uniform on this instance'.

**Expected.** Budget used, budget text and the uniform comparison refer to the completed run's configuration ('identical instance and seed').

**Actual.** 'Budget used' changes to 6% and the Rollouts card says 'budget 100,000' for a 20,000-budget run; compare() calls api.attribute(req(...)) with the current form, so after a seed change the 'identical instance' comparison runs on a different instance.

**Evidence**

- qa/evidence/04_workflows.json dash_budget_used_before_after_edit {before:'30%', after:'6%'}
- code: Dashboard.tsx:49-52, 62-65, 140, 178

**Root cause (established).** Displays and compare() use component state (budget, seed, …) rather than parameters stored with `res`.

**Source locations**

- `website/src/pages/Dashboard.tsx:49-66`
- `website/src/pages/Dashboard.tsx:140`
- `website/src/pages/Dashboard.tsx:178`
- `website/src/pages/Dashboard.tsx:182-191`

**Recommended fix direction.** Store the request with the result (`run = {req, res}`), compute displays from run.req and build the uniform comparison from run.req; mark results 'stale' when the form changes.

**Regression tests**

- vitest: changing budget after a run does not change 'budget used'.
- vitest: compare after a seed change posts the original seed.

**Dependencies:** none

## DATA-001

**Homepage metrics are animated count-ups: screenshots and throttled windows show wrong values (the reported 47 / 144 of 146 / 6413)**

- **Severity:** P2  ·  **Category:** research integrity  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/` — website/src/ui/kit.tsx CountUp/Stat; pages/Overview.tsx KPIs
- **Preconditions:** Any.

**Steps to reproduce**

1. Load / and sample `.kpis .stat .v` every 60 ms for 0.8 s.
2. Load / in a hidden pane / background tab.

**Expected.** Scientific metrics show their exact values (48 · 146 of 146 · 6518 · 0) at all times.

**Actual.** Timeline at 540 ms: '47 | 143 | 6401 | 0'; final at 720 ms: '48 | 146 | 6518 | 0'. The supplied screenshot's 47 / 144 / 6413 are all ≈98.4 % of the true values (47/48, 144/146, 6413/6518), i.e. one frame of the ease-out animation. In a non-painting pane the values stay at 0. Data sources are correct: API returns count_logical_states=48 (48 unique ids/labels, all reachable), tests 123/123 + 23/23, 6518 rows = sum of the 12 raw CSVs.

**Evidence**

- qa/evidence/01_routes.json kpiTimeline
- GET /api/automata/graph?model=agent48 → n_states 48, count_logical_states 48
- GET /api/tests → 123/123, frontend 23/23
- raw CSV row total 6518 == suite_meta sum 6518
- reduced-motion run: '48 | 146 | 6518 | 0' immediately (qa/evidence/03_hypotheses.json E_*)

**Root cause (established).** Stat renders values through CountUp (0→value over 900 ms via requestAnimationFrame). No state is missing: the 47 is a transient animation frame, not a model defect.

**Source locations**

- `website/src/ui/kit.tsx:234-261`
- `website/src/pages/Overview.tsx:176-179`

**Recommended fix direction.** Render research metrics as static final values (keep animation, if any, purely decorative and never changing the digits), or snap to the final value on mount and when the document is hidden. Add the test-report timestamp to the tests KPI ('last run 2026-10-24 03:09') because it is read from a stored report, not run live.

**Regression tests**

- vitest: Overview KPI text equals the API values on first render after data arrives (no intermediate numbers).
- CDP: screenshot at 300 ms shows 48 / 146 / 6518.

**Dependencies:** none

## FORM-001

**Invalid numeric input is flagged but the run silently uses the previous valid value**

- **Severity:** P2  ·  **Category:** frontend  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/dashboard, /explorer, /studio` — website/src/ui/kit.tsx NumberField; pages using it
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /dashboard, set Confidence δ to 0 (field shows 'Must be > 0').
2. Press Run attribution.

**Expected.** Run is disabled (or blocked with a message) while any field is invalid.

**Actual.** Run button enabled; request is sent with delta: 0.1 (the last valid value). Same pattern for budget, seed, trials, n.

**Evidence**

- qa/evidence/04_workflows.json dash_invalid_delta_ui {fieldError:'Must be > 0', runDisabled:false}, dash_invalid_delta_sent 0.1

**Root cause (established).** NumberField only calls onChange for valid values and keeps its error local; parents never learn that a field is invalid.

**Source locations**

- `website/src/ui/kit.tsx:70-90`
- `website/src/pages/Dashboard.tsx:121,125`
- `website/src/pages/Explorer.tsx:101,159-160`
- `website/src/pages/Studio.tsx:149-153,158`

**Recommended fix direction.** Expose validity (onValidityChange or a form-level error map) and disable submit buttons while invalid; show a summary next to the button.

**Regression tests**

- vitest: δ=0 disables Run attribution and no POST is made.
- vitest: same for Studio trials and Explorer n.

**Dependencies:** none

## UI-001

**CSS uppercase turns δ into Δ and ε into Ε in form labels**

- **Severity:** P2  ·  **Category:** research integrity  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/dashboard, /studio, /explorer (all uppercase labels)` — website/src/styles.css (.field label / .lbl text-transform: uppercase)
- **Preconditions:** Any.

**Steps to reproduce**

1. Open /dashboard and read the labels 'Confidence δ' and 'Tolerance ε'.

**Expected.** 'CONFIDENCE δ', 'TOLERANCE ε' (Greek symbols keep their case).

**Actual.** 'CONFIDENCE Δ' and 'TOLERANCE Ε'. Δ is the paper's symbol for the gap Δ_t = μ_t − μ_ref, so the label now names a different quantity; 'Ε' reads as Latin E.

**Evidence**

- qa/evidence/resp_1024x768_dashboard.png
- report/screens/dashboard.png

**Root cause (established).** text-transform: uppercase applies Unicode case mapping to Greek letters.

**Source locations**

- `website/src/styles.css (field label / .lbl rules)`
- `website/src/pages/Dashboard.tsx:120-121`
- `website/src/pages/Studio.tsx:150`

**Recommended fix direction.** Wrap symbols in <span class='sym'> with text-transform:none (or use font-variant small-caps for labels), or drop uppercase for labels containing math.

**Regression tests**

- vitest/DOM: computed text-transform of .sym is none.
- visual: label renders lowercase δ.

**Dependencies:** none

## API-002

**Unknown /api/* paths return 200 index.html, and the client accepts HTML as data**

- **Severity:** P2  ·  **Category:** API integration  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `GET /api/<anything unknown>` — src/afcr/api/app.py spa(); website/src/lib/api.ts request()
- **Preconditions:** Built website.

**Steps to reproduce**

1. curl -i http://localhost:8000/api/models (also /api/nope, /api/results/groups, /api/figures)

**Expected.** 404 JSON {detail: 'Not Found'} for any /api/* route that does not exist; the client rejects non-JSON for JSON endpoints.

**Actual.** 200 text/html (the SPA shell). `request()` returns the HTML string typed as T, so a typo in an endpoint fails later with confusing errors. (The previous session's 'all API endpoints return 200' check used these paths and was therefore a false positive.)

**Evidence**

- /api/models -> 200 text/html; charset=utf-8, body '<!doctype html>'

**Root cause (established).** The catch-all route `/{full_path:path}` also matches /api/... and /files/...; request() falls back to res.text() for non-JSON.

**Source locations**

- `src/afcr/api/app.py:513-518`
- `website/src/lib/api.ts:28-29`

**Recommended fix direction.** In spa(): if full_path starts with 'api/' or 'files/' raise HTTPException(404). In request(): for JSON endpoints throw ApiError when content-type is not JSON.

**Regression tests**

- pytest: GET /api/does-not-exist → 404 JSON.
- vitest: request() with an HTML 200 response rejects with ApiError.

**Dependencies:** SEC-001

## UX-001

**The automaton graph starts below the fold (≈650 px of header and model picker first)**

- **Severity:** P2  ·  **Category:** UX  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab` — website/src/pages/Lab.tsx layout (PageHeader, model-bar card, lab-grid)
- **Preconditions:** 1440×900 or smaller.

**Steps to reproduce**

1. Open /lab at 1440×900; at 390×844.

**Expected.** The selected model's graph is visible in the first viewport (with the model picker compact).

**Actual.** At 1440×900 only the first row of nodes is visible; at 390×844 the whole first screen is the model picker. Users can reasonably conclude that the lab 'shows nothing'.

**Evidence**

- qa/evidence/lab_agent48_view_DFA.png
- qa/evidence/resp_390x844_lab.png
- qa/evidence/route_lab_1440.png

**Root cause (established).** Large page header + three-row model picker + views row precede the graph.

**Source locations**

- `website/src/pages/Lab.tsx:156-197`
- `website/src/styles.css (.model-bar, .page-head)`

**Recommended fix direction.** Collapse the model picker into one row (segmented/select with grouped options), shorten the lead, put the view/size controls in the graph card header, and give the graph min-height: calc(100vh - header).

**Regression tests**

- CDP: at 1440×900 ≥80 % of graph nodes are inside the initial viewport.
- CDP: at 390×844 the graph card top is < 844 px.

**Dependencies:** AUTO-001

## A11Y-001

**No <h1> outside the homepage; nested <main> landmark in the lab**

- **Severity:** P3  ·  **Category:** accessibility  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `all non-home routes; /lab` — ui/kit.tsx PageHeader; pages/Lab.tsx
- **Preconditions:** Any.

**Steps to reproduce**

1. Inspect headings and landmarks on /lab, /dashboard, …

**Expected.** One h1 per page (the page title); one main landmark.

**Actual.** Page titles are <h2> (h1 count 0); /lab contains <main class='page'> > <main class='stack'> (2 main landmarks).

**Evidence**

- qa/evidence/05_responsive_a11y.json a11y

**Root cause (established).** PageHeader renders h2; Lab uses <main> for its column.

**Source locations**

- `website/src/ui/kit.tsx:47`
- `website/src/pages/Lab.tsx:185`

**Recommended fix direction.** PageHeader → h1; Lab column → <div> or <section>.

**Regression tests**

- vitest: each page renders exactly one h1 and one main.

**Dependencies:** none

## A11Y-002

**Tabs lack tabpanel wiring and arrow-key navigation**

- **Severity:** P3  ·  **Category:** accessibility  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/, /lab, /studio, /reproducibility` — ui/kit.tsx Tabs
- **Preconditions:** Any.

**Steps to reproduce**

1. Focus a tab and press ArrowRight.

**Expected.** WAI-ARIA tabs: aria-controls/aria-labelledby, roving tabindex, arrow keys move selection.

**Actual.** ArrowRight does nothing; 0 of 17 tabs have aria-controls; panels have no role=tabpanel.

**Evidence**

- qa/evidence/05_responsive_a11y.json tabArrow, tabsWithoutPanels

**Root cause (established).** Minimal Tabs component.

**Source locations**

- `website/src/ui/kit.tsx:196-208`

**Recommended fix direction.** Implement the ARIA tabs pattern (ids, aria-controls, tabindex −1 on inactive tabs, Arrow/Home/End).

**Regression tests**

- vitest: ArrowRight moves focus and selection; panel has role tabpanel.

**Dependencies:** none

## A11Y-003

**Clickable rows and plot rows are not keyboard operable; SVG node focus ring is invisible**

- **Severity:** P3  ·  **Category:** accessibility  ·  **Confidence:** highly likely  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/related, /dashboard, /lab` — Related matrix rows; DataTable onRowClick; ForestPlot rows; GraphCanvas nodes
- **Preconditions:** Any.

**Steps to reproduce**

1. Tab through /related's evidence matrix; tab to a graph node on /lab.

**Expected.** Rows reachable and activatable with Enter/Space; visible focus on graph nodes.

**Actual.** 21 clickable matrix rows are not focusable (same for DataTable rows with onRowClick and ForestPlot rows); graph nodes are focusable (28 Tabs to the first node) and Enter selects, but the focus style is a CSS box-shadow on an SVG <g>, which browsers do not paint.

**Evidence**

- qa/evidence/05_responsive_a11y.json clickableNonFocusable
- 06_kb result {tabsToFirstNode:28, ring:{tag:'g', shadow:'… 0 0 0 3px'}}

**Root cause (established (rows), highly likely (invisible ring)).** onClick on <tr>/<g> without tabIndex/key handlers; :focus-visible uses box-shadow.

**Source locations**

- `website/src/pages/Related.tsx:114`
- `website/src/ui/kit.tsx:290`
- `website/src/ui/charts.tsx:20`
- `website/src/styles.css:67`
- `website/src/graph/GraphCanvas.tsx:247-250`

**Recommended fix direction.** Use buttons inside rows (or tabIndex=0 + Enter/Space handlers); for SVG nodes draw a focus halo via :focus-visible > .halo stroke; add a 'skip to graph' link.

**Regression tests**

- vitest: Enter on a focused matrix row opens its details.
- visual: focused node shows a halo.

**Dependencies:** none

## A11Y-004

**Mobile menu does not take focus or close on Escape; route changes do not move focus or update the title**

- **Severity:** P3  ·  **Category:** accessibility  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `all (mobile ≤960 px) and route changes` — ui/Shell.tsx
- **Preconditions:** 390×844.

**Steps to reproduce**

1. Open the menu with the hamburger; press Escape.
2. Navigate between pages with the keyboard.

**Expected.** Focus moves into the drawer and is trapped; Escape closes and returns focus; after navigation focus moves to the page h1 and document.title names the page.

**Actual.** focusInside:false; Escape leaves the drawer open; after navigation focus stays on BODY; document.title is always 'AFCR · Agent Failure Attribution'.

**Evidence**

- qa/evidence/05_responsive_a11y.json menu, escapeClosesMenu:false
- qa/evidence/01_routes.json sidebar[].focused 'BODY.'

**Root cause (established).** Not implemented.

**Source locations**

- `website/src/ui/Shell.tsx:31-95`

**Recommended fix direction.** Add focus trap + Escape handler; on location change focus the page h1 (tabIndex −1) and set document.title per route.

**Regression tests**

- vitest: Escape closes the drawer.
- vitest: after navigation document.activeElement is the h1 and title includes the page name.

**Dependencies:** none

## A11Y-005

**Custom cursor hides the native pointer site-wide and runs a permanent rAF loop**

- **Severity:** P3  ·  **Category:** accessibility  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `all (pointer: fine)` — ui/Cursor.tsx; styles.css .cursor-on
- **Preconditions:** Desktop with a mouse, motion allowed.

**Steps to reproduce**

1. Move the mouse; observe styles.css .cursor-on { cursor: none } on the root.

**Expected.** Native cursor kept (custom ring as decoration) or an opt-out; no work when idle.

**Actual.** `cursor: none` on html/a/button/label/select/.graph-svg; the ring follows via a requestAnimationFrame loop that never stops. If the loop stalls (throttled/hidden window, heavy main thread) the user sees no pointer.

**Evidence**

- code: styles.css:97, Cursor.tsx:40-45

**Root cause (established).** Design choice.

**Source locations**

- `website/src/ui/Cursor.tsx:11-59`
- `website/src/styles.css:89-99`

**Recommended fix direction.** Keep the native cursor (cursor:auto) and use the ring only as a hover accent, or add a toggle in the sidebar footer; pause the loop when the pointer is idle or the document is hidden.

**Regression tests**

- DOM: html computed cursor is not 'none'.
- unit: loop stops after N idle frames.

**Dependencies:** none

## API-003

**Unbounded n_states on trace/graph and synchronous long experiment runs**

- **Severity:** P3  ·  **Category:** backend  ·  **Confidence:** confirmed (code), not load-tested  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `POST /api/automata/trace, GET /api/automata/graph, POST /api/experiment/run` — src/afcr/api/app.py TraceReq, graph(), ExpReq
- **Preconditions:** Server running.

**Steps to reproduce**

1. Inspect TraceReq.n_states and graph(n_states) (no upper bound, lru_cache keeps the model).
2. POST /api/experiment/run with trials 60, all 12 algorithms, automaton, budget 100000.

**Expected.** Bounded inputs (48..96 like TrajReq); long experiments run as jobs with progress and cancellation, or are capped.

**Actual.** Any n_states ≥ 48 is accepted and cached (memory growth); experiment runs synchronously in a worker thread with no progress, timeout or cancel.

**Evidence**

- code review (not load-tested to avoid disturbing the running server)

**Root cause (established).** Missing Field bounds; no job model.

**Source locations**

- `src/afcr/api/app.py:105-110`
- `src/afcr/api/app.py:147-152`
- `src/afcr/api/app.py:410-441`
- `src/afcr/api/app.py:38-43`

**Recommended fix direction.** Add Field(ge=48, le=96) to TraceReq.n_states and the graph query; cap work (trials×algorithms×budget) or move to a background job with polling.

**Regression tests**

- pytest: n_states=1000 → 422 on trace and graph.
- pytest: oversized experiment → 422 with an explanation.

**Dependencies:** none

## AUTO-007

**TM trace returns `steps` as a number; UI toasts 'Trace computed (undefined steps)'**

- **Severity:** P3  ·  **Category:** API integration  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab?model=tm, /lab?model=tm_pal` — src/afcr/api/app.py trace() TM branch; automata/turing.py to_json; Lab.tsx runTrace
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /lab?model=tm, press Run trace.

**Expected.** Consistent schema (steps: array, or n_steps: int) and toast 'Trace computed (9 steps)'.

**Actual.** Response {steps: 9 (int), trace: [...]} while TraceResponse types steps as an array; toast reads 'Trace computed (undefined steps)'. Playback works only because `trace.steps?.length` is undefined and falls back to trace.trace.length − 1.

**Evidence**

- qa/evidence/02_lab.json tm.afterRun / tm_pal.afterRun
- POST /api/automata/trace {model:'tm'} → steps: int

**Root cause (established).** Schema mismatch between turing.Trace.to_json() and website/src/lib/api.ts TraceResponse.

**Source locations**

- `src/afcr/api/app.py:214-215`
- `src/afcr/automata/turing.py (to_json)`
- `website/src/lib/api.ts:54-58`
- `website/src/pages/Lab.tsx:123,131`

**Recommended fix direction.** Rename the TM field to n_steps (or return configurations under steps); add a response model per trace kind; compute the toast count per model.

**Regression tests**

- pytest: TM trace JSON validates against a TraceResponse schema.
- vitest: TM run toast shows a number.

**Dependencies:** none

## AUTO-008

**NFA/ε-NFA playback marks a single 'current' state, omits the initial ε-closure and maps steps to edges proportionally**

- **Severity:** P3  ·  **Category:** visualization  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab?model=nfa|enfa` — website/src/pages/Lab.tsx trailFromTrace, trailIndex/countUpTo; GraphCanvas current marker
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /lab?model=enfa, Run trace 'a b', step through; observe step 0 and the cyan 'current' ring.

**Expected.** At step 0 the active set is ε-closure(q0) = {q0,q1,q2}; each step highlights exactly the edges taken in that step; there is no single 'current' state for set-based runs.

**Actual.** Step 0 shows no active set; a cyan pulse marks one state (the last edge's target) as 'current'; edges revealed per step are approximated by ceil(trail.length·idx/steps), which is only correct when every step contributes the same number of edges.

**Evidence**

- qa/evidence/02_lab.json enfa.playback / nfa.playback
- code: Lab.tsx:132,133,348-352

**Root cause (established).** Trail indexing is not per step; GraphCanvas derives `current` from the last revealed edge.

**Source locations**

- `website/src/pages/Lab.tsx:38-60`
- `website/src/pages/Lab.tsx:131-133`
- `website/src/pages/Lab.tsx:348-352`
- `website/src/graph/GraphCanvas.tsx:185`

**Recommended fix direction.** Build trail as an array of per-step edge groups; reveal groups[0..idx); pass activeSet (including the initial closure at idx 0) and suppress the single current marker for set semantics.

**Regression tests**

- vitest: ε-NFA idx 0 active set equals closure_steps' last set.
- vitest: unequal per-step edge counts highlight exactly the edges of steps ≤ idx.

**Dependencies:** none

## AUTO-009

**LTS deadlock / blocked step is not shown**

- **Severity:** P3  ·  **Category:** automata semantics  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab?model=lts` — Lab.tsx trace panel
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /lab?model=lts, word 'plan answer plan', Run trace.

**Expected.** The third step is shown as blocked at 'done' (no 'plan' transition) — a deadlock for that label.

**Actual.** Only 'rejected'; the step with blocked:true and next_state:null is silently skipped in playback.

**Evidence**

- POST trace lts → steps[2] = {state:'done', symbol:'plan', next_state:null, blocked:true}

**Root cause (established).** trailFromTrace ignores steps whose next_state is not a string; the UI never reads `blocked`.

**Source locations**

- `website/src/pages/Lab.tsx:54-57`
- `website/src/pages/Lab.tsx:295-310`

**Recommended fix direction.** Render a 'blocked at <state> on <label>' badge and highlight the state; list LTS deadlocks from the graph payload (already returned as `deadlocks`).

**Regression tests**

- vitest: blocked LTS step renders a blocked badge.

**Dependencies:** none

## CFG-001

**`npm run preview` has no /api proxy, so the previewed site cannot reach the backend**

- **Severity:** P3  ·  **Category:** documentation  ·  **Confidence:** highly likely  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `vite preview (:4173)` — website/vite.config.ts
- **Preconditions:** Built site, API on :8000.

**Steps to reproduce**

1. cd website; npm run preview; open http://localhost:4173/lab.

**Expected.** Same behaviour as npm run dev (proxy to :8000) or docs saying preview is unsupported.

**Actual.** Only `server.proxy` is configured; `preview.proxy` is missing (not executed in this audit — derived from the config).

**Evidence**

- website/vite.config.ts: server: { proxy: {...} } only

**Root cause (established (config); not run).** Missing preview config.

**Source locations**

- `website/vite.config.ts:7`

**Recommended fix direction.** Add `preview: { proxy: { '/api': 'http://localhost:8000', '/files': 'http://localhost:8000' } }`.

**Regression tests**

- manual/CI: npm run preview then GET /api/health through :4173 returns JSON.

**Dependencies:** none

## DASH-003

**Caption says 'LUCB would pull next' for every algorithm**

- **Severity:** P3  ·  **Category:** frontend  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/dashboard` — Dashboard.tsx history caption
- **Preconditions:** API running.

**Steps to reproduce**

1. Choose 'Uniform (same stopping rule)' and Run attribution; read the caption under the forest plot.

**Expected.** '<algorithm> would pull next' (or hide for non-LUCB).

**Actual.** '… · LUCB would pull next ["step 8","step 1"]' for uniform_fc.

**Evidence**

- qa/evidence/04_workflows.json dash_uniform_label

**Root cause (established).** Hard-coded string.

**Source locations**

- `website/src/pages/Dashboard.tsx:166`

**Recommended fix direction.** Use label(res.strategy) and only show `suggested` when the backend's strategy produced it.

**Regression tests**

- vitest: uniform run caption names Uniform.

**Dependencies:** none

## DASH-004

**No result export and no way to cancel a long attribution run**

- **Severity:** P3  ·  **Category:** frontend  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/dashboard` — Dashboard.tsx; api.ts attribute()
- **Preconditions:** API running.

**Steps to reproduce**

1. Run attribution with budget 300000; look for stop/cancel/export.

**Expected.** Cancel (AbortController) while running; export the result (JSON incl. config, history, intervals; CSV of the ranking).

**Actual.** No stop/cancel/reset or export control on the page (only Experiment studio exports).

**Evidence**

- qa/evidence/04_workflows.json dash_export_buttons [], dash_stop_cancel []

**Root cause (established).** Not implemented.

**Source locations**

- `website/src/pages/Dashboard.tsx`
- `website/src/lib/api.ts:12-33`

**Recommended fix direction.** Pass an AbortSignal through request(); add Cancel while busy; add 'Export JSON' / 'Export ranking CSV' buttons using downloadText.

**Regression tests**

- vitest: Cancel aborts the fetch and restores the idle state.
- vitest: Export JSON contains req + result.

**Dependencies:** none

## DOC-001

**Stale and non-runnable instructions on the site**

- **Severity:** P3  ·  **Category:** documentation  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/reproducibility, /docs` — pages/Reproducibility.tsx RUN/SPEC; pages/Docs.tsx API reference note
- **Preconditions:** Any.

**Steps to reproduce**

1. Open /reproducibility → Commands; copy the spec block into a file and run `python -m afcr.experiments.run_one spec.json`.
2. Open /docs → API reference footer.

**Expected.** Commands that exist; a spec that runs; accurate error contract.

**Actual.** Lists `python scripts/build_docs.py` (script removed; current: build_paper.py, build_report.py, build_appendices.py, build_docs_folder.py, take_screenshots.py) and '18 figures' (21 exist); the JSON spec uses // comments, which run_one's json.loads rejects; Docs says invalid input returns 422 although the replay endpoints return 500 (API-001) and unknown routes 200 (API-002). README (repo) is current; the website copy is not.

**Evidence**

- qa/evidence/04_workflows.json repro_commands
- scripts/ listing (no build_docs.py)
- configs/*.json use '_comment' keys instead

**Root cause (established).** Hard-coded strings in the page were not updated with the scripts.

**Source locations**

- `website/src/pages/Reproducibility.tsx:18-33`
- `website/src/pages/Docs.tsx:37`

**Recommended fix direction.** Serve the command list from the repository (README section or a JSON written by the build) or update the strings; use the `_comment` key convention from configs/ in the example spec.

**Regression tests**

- pytest: every `python scripts/X.py` mentioned in website/src exists.
- pytest: the spec example in Reproducibility parses with run_one.load_spec.

**Dependencies:** none

## DOC-002

**API reference drops bounds of 0 (operator precedence) and nullable types**

- **Severity:** P3  ·  **Category:** documentation  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/docs` — pages/Docs.tsx ApiReference range column
- **Preconditions:** Any.

**Steps to reproduce**

1. Open /docs → API reference → POST /api/attribute.

**Expected.** seed '≥ 0', eps_plan '≥ 0, < 1', eps '≥ 0, ≤ 0.5', reconstruct_noise '≥ 0, ≤ 1'.

**Actual.** seed '—', eps_plan '< 1', eps '≤ 0.5', reconstruct_noise '≤ 1'; nullable fields (anyOf) show type '—'.

**Evidence**

- qa/evidence/04_workflows.json docs_attribute_ranges

**Root cause (established).** `v.minimum ?? v.exclusiveMinimum != null ? … : ''` parses as `(v.minimum ?? (v.exclusiveMinimum != null)) ? …`; a minimum of 0 is falsy.

**Source locations**

- `website/src/pages/Docs.tsx:36`

**Recommended fix direction.** Compute lower = v.exclusiveMinimum ?? v.minimum with explicit `!= null` checks; render anyOf types.

**Regression tests**

- vitest: schema {minimum:0} renders '≥ 0'.

**Dependencies:** none

## DOC-003

**Documentation search only matches hand-written keyword strings**

- **Severity:** P3  ·  **Category:** documentation  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/docs` — pages/Docs.tsx search
- **Preconditions:** Any.

**Steps to reproduce**

1. Search 'LUCB' (described in the glossary/API sections).

**Expected.** Sections that mention LUCB.

**Actual.** No results (empty state).

**Evidence**

- qa/evidence/04_workflows.json docs_search_LUCB []

**Root cause (established).** Filtering uses `s.text` keyword lists, not the rendered content.

**Source locations**

- `website/src/pages/Docs.tsx:71-83`

**Recommended fix direction.** Index the rendered text (ref.innerText) or the glossary/API data used to build the sections.

**Regression tests**

- vitest: searching 'LUCB' shows the glossary/API sections.

**Dependencies:** none

## FE-001

**Homepage logs 32 SVG errors per load: <circle> cx/cy 'undefined'**

- **Severity:** P3  ·  **Category:** frontend  ·  **Confidence:** confirmed (errors), highly likely (cause)  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/` — website/src/ui/HeroGraph.tsx motion.circle
- **Preconditions:** Any.

**Steps to reproduce**

1. Load / with DevTools console open.

**Expected.** No console errors.

**Actual.** 16 × 'Error: <circle> attribute cx: Expected length, "undefined"' and 16 × cy.

**Evidence**

- qa/evidence/01_routes.json allConsole

**Root cause (highly likely).** motion.circle is animated with keyframe arrays for cx/cy but has no initial cx/cy attribute.

**Source locations**

- `website/src/ui/HeroGraph.tsx:37-38`

**Recommended fix direction.** Set cx={pts[0].x} cy={pts[0].y} (and initial) on both circles, or animate a transform instead.

**Regression tests**

- CDP: zero console errors on /.

**Dependencies:** none

## INT-001

**Homepage headline says 'Sample-optimal' while Theory says the project never calls AFCR sample-optimal**

- **Severity:** P3  ·  **Category:** research integrity  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/ vs /theory` — pages/Overview.tsx hero h1; pages/Theory.tsx §6
- **Preconditions:** Any.

**Steps to reproduce**

1. Read the H1 on / and Theory §6.

**Expected.** The qualifier is part of the headline (e.g. 'Towards sample-optimal…' or a visible 'objective' tag), consistent with Theory.

**Actual.** H1 'Sample-optimal culprit identification for agent failures'; qualifier only in small grey text below the CTAs; Theory: 'We do not claim to match it and therefore never call AFCR “sample-optimal”'.

**Evidence**

- qa/evidence/route_home_1440.png
- Theory.tsx:79

**Root cause (established).** Title kept from the project outline.

**Source locations**

- `website/src/pages/Overview.tsx:162,169`
- `website/src/pages/Theory.tsx:79`

**Recommended fix direction.** Keep the official project title but attach an 'objective, not a proven property' tag directly to the H1 (same line/size as eyebrow) and link to Theory §6.

**Regression tests**

- vitest: hero contains the qualifier within the header element.

**Dependencies:** none

## REL-001

**Related-work timeline clusters 2025–26 papers into clipped, overlapping labels; 'CAR' search finds nothing**

- **Severity:** P3  ·  **Category:** visualization  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/related` — pages/Related.tsx Timeline, filter
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /related, look at the right end of the timeline.
2. Type 'car' in 'Filter papers'.

**Expected.** All points labelled and readable; CAR (highlighted in the legend as closest) visible; searching the acronym finds the paper; empty filter shows an empty state.

**Actual.** Labels such as 'TraceEleph…' are clipped at the SVG edge and stacked lines overlap; CAR's red point is not distinguishable in the cluster; 'car' returns zero rows (short_name is 'Causal Agent Replay'); the table shows only a header with no empty-state text.

**Evidence**

- qa/evidence/related_timeline.png
- qa/evidence/04_workflows.json related_filter_car []

**Root cause (established).** Linear 2006–2027 axis with 20 points, 14 of them within ~1.5 years; filter matches short_name/venue only.

**Source locations**

- `website/src/pages/Related.tsx:25-51`
- `website/src/pages/Related.tsx:59`

**Recommended fix direction.** Use a broken/zoomed axis (2006–2016 | 2025–2026) or a list for the recent cluster; match the DATES acronym and paper_id in the filter; show an empty row message.

**Regression tests**

- vitest: filter 'CAR' returns the CAR row.
- CDP: no timeline label extends beyond the SVG.

**Dependencies:** none

## VIS-001

**Graph readability: overlapping edge labels, clipped self-loops, edge labels over node labels, tiny scale for 96 states / mobile**

- **Severity:** P3  ·  **Category:** visualization  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab (moore, tm_pal, agent48 64/96, mobile)` — website/src/graph/GraphCanvas.tsx buildGeometry/labels; graph/layout.ts
- **Preconditions:** API running.

**Steps to reproduce**

1. Open /lab?model=moore and Run trace; open tm_pal; open the 48-state model; select 96 states; open /lab at 390×844.

**Expected.** No overlapping labels; self-loops inside the viewport; readable labels.

**Actual.** Moore: 11 overlapping edge-label pairs (28 parallel/self edges), self-loop at the top clipped; tm_pal: 2 overlapping pairs; agent graph: edge label 'tool_invalid 0.10' over the node label 'Select tool'; 96 states fit at scale 0.45; at 390 px the 48 nodes are drawn in 318 px.

**Evidence**

- qa/evidence/02_lab.json overlappingLabelPairs
- qa/evidence/lab_moore_trace_end.png
- qa/evidence/lab_agent48_96states.png
- qa/evidence/resp_390x844_lab.png

**Root cause (established).** Layered layout with fixed spacing; parallel edges between the same pair get separate labels; no label collision handling; bbox ignores self-loop height.

**Source locations**

- `website/src/graph/GraphCanvas.tsx:45-75,229-235`
- `website/src/graph/layout.ts:18-38,44-47`

**Recommended fix direction.** Merge parallel edges into one edge with a combined label ('task, ok / noop'); include self-loop extents in bbox; offset labels away from nodes / add a label background; for agent48 show labels on hover only and offer a 'columns compact' layout; on mobile default to a list/table view with the graph behind a toggle.

**Regression tests**

- unit (layout): no two label boxes overlap for the bundled models.
- CDP: overlappingLabelPairs == 0 for every model.

**Dependencies:** none

## UX-002

**Content below the fold is invisible until scrolled (print, full-page capture, find-in-page)**

- **Severity:** P3  ·  **Category:** UX  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/theory, /related, /reproducibility, /` — ui/kit.tsx Reveal
- **Preconditions:** Any.

**Steps to reproduce**

1. Open /theory and take a full-page screenshot without scrolling (or print).

**Expected.** All content visible.

**Actual.** Sections 3–8 are at opacity 0 in the capture.

**Evidence**

- qa/evidence/hyp_C_theory_fullpage_noscroll.png
- qa/evidence/03_hypotheses.json C_theory_reveal

**Root cause (established).** Reveal starts at opacity 0 and relies on whileInView.

**Source locations**

- `website/src/ui/kit.tsx:265-267`

**Recommended fix direction.** See AUTO-001: visible by default; add @media print { opacity:1 !important }.

**Regression tests**

- CDP: full-page capture of /theory has no element with opacity 0 inside main.

**Dependencies:** AUTO-001

## POL-001

**Dead UI and conflicting CSS**

- **Severity:** P4  ·  **Category:** frontend  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/reproducibility, /lab, styles` — Reproducibility.tsx Tabs; Lab.tsx Tip; styles.css .lab-grid
- **Preconditions:** Any.

**Steps to reproduce**

1. See /reproducibility 'Licensing notes' tab; Lab aside empty Tip; styles.css .lab-grid.

**Expected.** No inert controls; one grid definition.

**Actual.** A one-tab <Tabs onChange={() => {}}> acts as a heading; <Tip><span /></Tip> renders an empty hover target; .lab-grid is defined at lines ~365–367 (3 columns) and overridden with !important at ~387–388 (2 columns).

**Evidence**

- code

**Root cause (established).** Leftovers.

**Source locations**

- `website/src/pages/Reproducibility.tsx:156`
- `website/src/pages/Lab.tsx:341`
- `website/src/styles.css:365-367,387-388`

**Recommended fix direction.** Replace the fake tab with a heading; remove the empty Tip; delete the superseded .lab-grid rules.

**Regression tests**

- none (cleanup)

**Dependencies:** none

## POL-002

**Turing-machine tape window shifts as the head moves; blank symbol differs between backend and UI**

- **Severity:** P4  ·  **Category:** visualization  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `/lab?model=tm|tm_pal` — Lab.tsx Tape
- **Preconditions:** API running.

**Steps to reproduce**

1. Run the TM trace and step through.

**Expected.** Fixed tape window with cell indices; one blank symbol.

**Actual.** Visible tape changes between '␣␣1011␣␣␣' and '1011␣␣␣' as the window is recomputed from the head position; backend uses '_' while the UI shows '␣'.

**Evidence**

- qa/evidence/02_lab.json tm.playback

**Root cause (established).** Tape window = [min(0, head−2, keys), max(head+2, keys, 6)] per step.

**Source locations**

- `website/src/pages/Lab.tsx:70-76`

**Recommended fix direction.** Compute the window once over the whole trace; show indices; use one blank glyph and explain it.

**Regression tests**

- vitest: tape window constant across steps.

**Dependencies:** none

## POL-003

**Markdown file routes appear in OpenAPI with summary ' F'**

- **Severity:** P4  ·  **Category:** backend  ·  **Confidence:** confirmed  ·  **Status:** fixed (see FIX_REPORT.md)
- **Affected page / component:** `GET /openapi.json` — src/afcr/api/app.py _mk()
- **Preconditions:** Any.

**Steps to reproduce**

1. GET /openapi.json; see /files/README.md etc.

**Expected.** Meaningful summaries or include_in_schema=False.

**Actual.** summary ' F' (from the inner function name _f).

**Evidence**

- openapi listing

**Root cause (established).** Generated handler name.

**Source locations**

- `src/afcr/api/app.py:502-507`

**Recommended fix direction.** Add summary='Download <file>' or include_in_schema=False.

**Regression tests**

- pytest: no OpenAPI summary shorter than 3 characters.

**Dependencies:** none
