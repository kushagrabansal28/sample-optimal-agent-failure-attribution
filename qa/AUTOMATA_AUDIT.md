# Automata investigation

Scope: `/lab` (Automata laboratory), the homepage automaton graphic, the `/api/automata/*` endpoints and `src/afcr/automata/*`. Everything below was executed against the running server (`http://localhost:8000`, PID 38972, serving this folder) unless marked *code review*.

## 1. Bottom line

* **In a normal, visible browser the laboratory works.** All 12 model entries (48-state agent automaton + DFA, NFA, ε-NFA, PA, LTS, Mealy, Moore, PDA, typed PDA, two Turing machines) load, render, accept a trace, play back step by step, zoom, search, select states and switch tabs, with **0 JavaScript exceptions and 0 failed requests** (headless Edge 1440×900, `evidence/02_lab.json`).
* **The reported symptom ("the automaton shows on the homepage but not in the other sections") is reproduced when the page is mounted in a viewport that has no size or does not paint** — which is exactly the state of the embedded browser pane when it is hidden. There, `innerWidth = innerHeight = 0`, `requestAnimationFrame` runs 0 frames/s, the lab graph is drawn at `scale(0)` (all 48 nodes and 89 edges are in the DOM but invisible), the KPI counters read `0`, and scroll-revealed sections stay at opacity 0. The homepage graphic survives because it is a different implementation (fixed `viewBox`, no measured fit). → **AUTO-001 (P1, highly likely)**.
* Independently of that, the lab has real **semantic and presentation defects** (P2/P3) listed in §5, plus a usability problem that makes the graph easy to miss (UX-001: the graph starts ≈650 px down the page).
* **The 47-vs-48 discrepancy is not a missing state.** The model has exactly 48 distinct logical states; the 47 is one frame of the KPI count-up animation (DATA-001). See §4.

## 2. Homepage graphic vs laboratory graph

| | Homepage (`ui/HeroGraph.tsx`) | Laboratory (`graph/GraphCanvas.tsx`) |
|---|---|---|
| Data | real: `GET /api/automata/graph?model=agent48` + `POST /api/trajectory {seed:5}` | real: same graph endpoint with `view`, `n_states` |
| Layout | `layoutGroups` → rescaled into a fixed `viewBox="0 0 620 500"` | `layoutGroups` / `layoutLayered` in world coordinates, then **fit to the measured container width** with d3-zoom |
| Sizing dependency | none (SVG scales with CSS width) | `wrapRef.clientWidth` via ResizeObserver; `fit()` with `w = 0` → `k = 0` |
| Animation dependency | decorative only (framer-motion keyframes) | none for drawing; fit tween uses rAF unless reduced motion |
| Interaction | none (decorative) | pan/zoom, select, search, trace, branch overlay, minimap |
| Shared code | `layoutGroups` only | — |

So the homepage graphic **is a real automaton rendered from the same API data**, but it is a **separate, non-interactive implementation**. It cannot be used as evidence that the lab works, and conversely the lab failing in a zero-size viewport does not affect it.

## 3. Route-to-render execution path (verified stage by stage)

| # | Stage | Code | Observed (visible browser) | Observed (hidden pane / 1×1 viewport) |
|---|---|---|---|---|
| 1 | Sidebar click | `ui/Shell.tsx` `NavLink to="/lab"` | URL → `/lab`, active item correct | same (navigation works without rAF) |
| 2 | Route resolution | `App.tsx` `<Route path="/lab" element={<Lab/>}>` (lazy) | chunk `Lab-*.js` loads | same |
| 3 | Mount | `AnimatePresence mode="wait"` + `motion.main` | one `main.page`, opacity 1 | same (style ends at opacity 1) |
| 4 | Data fetch init | `useAsync(api.models)`, `api.compare`, `api.tests`, `api.graph(model, {view, n_states})`, `api.trajectory` | all 200 | all 200 |
| 5 | Backend | `src/afcr/api/app.py graph()` | 48 nodes / 89 edges / `count_logical_states: 48` | same |
| 6 | Parse | `request()` → JSON | OK | OK |
| 7 | State update | `graph.data` | OK | OK |
| 8 | Normalisation | `layoutFor(nodes, edges, isAgent)` | 48 positioned nodes | same |
| 9 | Geometry | `buildGeometry` | 89 paths, no dangling edges | same |
| 10 | Render | SVG `<g transform>` | `translate(-20.9,80.6) scale(0.697)` | **`translate(0,310) scale(0)`** |
| 11 | Layout & sizing | ResizeObserver → `fit(false,{w,h})` | `svgW 746`, 48/48 nodes inside the viewport | `wrapW 0` → `k = min(0/bw, …) = 0`; d3 extent `[[0,0],[0,h]]` |
| 12 | Interaction | d3-zoom, node click/Enter, search | all work | wheel while collapsed → **`translate(Infinity,Infinity) scale(0.2)`** |
| 13 | Selection/trace | `selected`, `trail`, `trailIndex` | work | n/a |

Recovery: after the viewport grows (1×1 → 1440×900) the graph refits correctly in both the untouched case and after a wheel event (`evidence/03_hypotheses.json` A/B), because `fitSig` includes the width. While the pane stays hidden it stays invisible, and anything else that waits for animation frames (CountUp, Reveal, tweens) stays at its initial state.

Hypotheses checked and **ruled out** for a normal browser: route mismatch, missing import, lazy-chunk failure, error boundary swallowing (there is none; no exceptions were thrown), CORS (same origin), incorrect API path, schema mismatch for the agent graph, duplicate/missing node ids, zero-height container, stale cache.

Remaining hypotheses for the user's exact observation (need the user's URL, browser and a console log to distinguish): (a) hidden/not-painting embedded pane — reproduced; (b) API not running — produces the "Request failed" banner, observed in an earlier session; (c) `npm run preview` on :4173 (no `/api` proxy, CFG-001); (d) the page scrolled such that the graph is below the fold (UX-001).

## 4. The 48-state requirement and the 47 / 144 / 6413 discrepancy

Backend model (`build_agent_model(48)`, inspected directly):

| Check | Result |
|---|---|
| States / unique ids / unique labels | 48 / 48 / 48 |
| Groups | PLAN 8 · OBSERVE 8 · TOOL 8 · MEMORY 8 · VALIDATE 8 · TERMINAL 8 |
| Roles | benign 19, decision 7, fault_entry 7, corridor 3, recovery 4, terminal_success 2, terminal_failure 6 |
| Initial / accepting / rejecting | `PLAN_START` / `DONE_SUCCESS, DONE_PARTIAL` / 6 `FAIL_*` |
| Reachable from the initial state | 48 / 48 (no unreachable states) |
| Non-terminal states without actions | none |
| Dangling targets | none |
| Kernels and policies normalised | all |
| (state, action) pairs / (state, action, successor) triples | 48 / 89 |
| Planted-fault decision states | `PLAN_SUBGOAL, OBS_SEARCH, OBS_READ, TOOL_SELECT, MEM_WRITE, REASON_STEP, VAL_DIAGNOSE` |
| DFA (`to_dfa`) | 49 states incl. `⊥sink`, 2009 transitions = 49 × 41 (total) |
| NFA / ε-NFA | 48 keys, 89 edges / 8 ε-edges (heal moves) |
| 64 / 96 variants | 64 / 96 logical states, all validated |

Frontend: the API payload, the graph DOM (48 `.g-node`) and the "48 distinct logical states" callout all agree; the validation flag `state_count_validated` is a constant `True` in `app.py:155`, which is acceptable only because `build_agent_model` calls `model.validate()` (benchmark48.py:614) and `count_logical_states()` raises on duplicates.

**Source of 47 / 144 of 146 / 6413:** the Overview KPIs are rendered by `CountUp` (0 → value over 900 ms). Sampling the live page: 540 ms → `47 | 143 | 6401`, 720 ms → `48 | 146 | 6518`. The screenshot values are 47/48 = 0.979, 144/146 = 0.986, 6413/6518 = 0.984 — one animation frame. No state is missing, the test count is not stale (123/123 backend + 23/23 frontend), and 6518 equals the row total of the 12 raw CSVs. **Do not add a state.** Fix the display (DATA-001).

## 5. Model-by-model status

Legend — ✅ works · ⚠️ works with a defect · ❌ broken. "Trace" = default word; "Reject" = the rejecting/invalid word tested.

| Model | Graph | States (start / accept / reject) | Trace & playback | Reject / invalid | Model-specific display | Issues |
|---|---|---|---|---|---|---|
| 48-state agent (LTS view) | ✅ 48 nodes, 89 edges | `PLAN_START` / 2 success / 6 failure | ✅ 5-step failed trajectory, culprit ring, edges highlighted | n/a | ✅ policy π(a\|q), ref action, branch overlay (2 violet edges), search (5 matches, 43 dimmed) | UX-001, VIS-001, AUTO-006 |
| 48-state — DFA view | ⚠️ 48 nodes, **48 edges** | — | — | — | ❌ claims total δ + explicit sink; sink not drawn | **AUTO-005** |
| 48-state — NFA / ε-NFA / PA views | ✅ 89 edges each; ε-edges dashed; PA kernel probabilities | — | — | — | ⚠️ views look nearly identical; no explanation of what changed | UI/UX §graph |
| 48-state — 64 / 96 states | ✅ 64/121, 96/185 | — | ✅ | — | ⚠️ 96 states fit at scale 0.45 | VIS-001 |
| DFA (even number of a's) | ✅ 2 states, 4 edges | `even` / `even` / — | ✅ 3 steps, one edge per step, current state correct | ✅ `a b b` → rejected; `c` → 422 shown | ✅ transition table | AUTO-006 (naming `even/odd`, no dead state) |
| NFA (ends in "ab") | ✅ 3 states | `q0` / `q2` | ✅ active sets `{q0,q1}`→`{q0,q1}`→`{q0,q2}` | ✅ `a b a` rejected | ⚠️ single "current" ring shown for a set run | AUTO-008 |
| ε-NFA (a*b) | ✅ 4 states, ε dashed | `q0` / `q3` | ✅ | ✅ `b b` rejected; `b` accepted | ⚠️ step 0 does not show ε-closure {q0,q1,q2}; closure animation separate | AUTO-008 |
| Probabilistic automaton | ✅ 3 states, probabilities on edges sum to 1 | `s` / `t` | ✅ exact P = 0.868, MC 0.875 [0.860, 0.889] | ⚠️ `go` → badge **"accepted"** with P = 0.70 | ❌ sampled path presented as a verdict | **AUTO-002** |
| LTS | ✅ 5 states | `idle` / `done` / `failed` | ✅ | ⚠️ `plan answer plan` → rejected, blocked step not shown | deadlocks returned by API but not displayed | AUTO-009 |
| Mealy | ✅ 3 states, outputs on edges (`a/out`) | `idle` / — | ✅ outputs `call_tool retry proceed` | ✅ `bogus` → 422 shown | ❌ badge **"accepted"** for a transducer | **AUTO-003** |
| Moore | ⚠️ 7 product states, 28 edges, **11 overlapping label pairs**, top self-loop clipped | `idle/start` | ✅ n+1 outputs `start call_tool retry proceed` | ⚠️ `ok ok` → "accepted" | outputs on states ✅ | AUTO-003, VIS-001, AUTO-006 |
| PDA (nested calls) | ✅ 2 states (`q`, `acc`) | `q` / `acc` | ✅ stack Z → Z,C → Z,C,C → … → accept | ❌ `call ret ret` → **0 steps**, playback hidden, initial hint shown | stack panel ✅ on accept only | **AUTO-004**, AUTO-006 |
| PDA (typed tools) | ✅ 2 states | `q` / `acc` | ✅ stack S/K typing | ❌ `open_search end_calc` → 0 steps | as above | AUTO-004 |
| TM (binary increment) | ✅ 5 states | `scan` / `acc` / `rej` | ✅ 9 steps, tape 1011 → 1100, output "1100" | ✅ `12` → 422 | ⚠️ toast "Trace computed (**undefined** steps)"; tape window shifts | **AUTO-007**, POL-002 |
| TM (palindromes) | ⚠️ 10 states, 2 overlapping label pairs | `q0` / `acc` / `rej` | ✅ 15 steps on `abba` | ✅ `ab` → reject (4 steps) | toast "undefined steps" | AUTO-007, VIS-001 |

Mathematical spot checks (all correct): DFA accepts words with an even number of `a` (`aba`, `aa`, ε accepted; `abb` rejected). NFA accepts words ending in `ab`. ε-NFA accepts `a*b` (`b` accepted, `a` rejected). PA: P(go) = 0.7 (one step to t), P(go³) = 0.7 + 0.2·0.7 + 0.04·0.7 = 0.868 ✓. TM: 1011₂ + 1 = 1100₂ ✓; ε input → "1" ✓. PDA: balanced `call/ret` accepted, unbalanced rejected ✓ (but invisible, AUTO-004). Palindromes: `abba`, `aba`, ε accepted; `ab` rejected ✓.

Execution-model faithfulness:

| Requirement | Status |
|---|---|
| DFA deterministic and total | toy DFA ✅ total; 48-state DFA view ❌ partial (AUTO-005) |
| NFA tracks active sets | ✅ (`steps[].state` are sets; amber active-set rings) |
| ε-NFA uses ε-closure | ✅ backend (`before_closure` + closure); ⚠️ initial closure not displayed |
| PA distributions valid | ✅ kernels sum to 1; ❌ acceptance shown as a verdict |
| LTS labels preserved | ✅ labels on edges; ⚠️ blocked step hidden |
| Mealy outputs on transitions | ✅ `in/out` labels; ❌ "accepted" badge |
| Moore outputs on states | ✅ `output` on nodes, n+1 outputs; ❌ "accepted" badge |
| PDA exposes stack | ✅ on accepting runs; ❌ nothing on rejecting runs |
| TM exposes tape and head | ✅ tape + head cell + state; ⚠️ moving window |

## 6. State naming and coverage requested by the user (AUTO-006)

Requested: states named `q0, q1, …` in every model, and "all cases" for each machine type.

Current ids: NFA/ε-NFA use `q0…`; everything else uses words (`even/odd`, `s/t/f`, `idle/thinking/…`, `idle/start` product states, `q/acc`, `scan/carry/done/acc/rej`, `PLAN_START … FAIL_TOOL`).

Required behaviour for the fix:

1. Every node gets a stable `qid` (`q0…q{n−1}`) from the backend; the 48-state model maps to `q0…q47` in a fixed, documented order (group, then position), so the logical-state count stays **48**.
2. The UI shows `q7 · Select subgoal` in nodes, tables, traces, the details panel and search (search matches both).
3. Coverage per type (keep the existing machines, add examples where missing):
   * **DFA:** accept, reject, empty word, invalid symbol, an explicit **dead/trap state**, total transition table.
   * **NFA:** nondeterministic branch, dead branch (∅), and the **subset construction** (NFA→DFA) view — the backend already implements and tests it (`test_nfa_to_dfa_equivalence`).
   * **ε-NFA:** ε-closure at step 0 and after each symbol, ε-removal equivalence.
   * **PA:** ≥ 2 input symbols, a rejecting absorbing state, exact vs Monte-Carlo probability.
   * **LTS:** reachability, deadlock, blocked label.
   * **Mealy / Moore:** the same input giving different outputs from the same state (already returned as `witness`), Mealy→Moore expansion explained.
   * **PDA:** push, pop, accept by final state with empty stack, and **reject** (underflow, mismatch, leftover stack) with the configuration where it fails.
   * **TM:** accept, reject, and **step-limit "unknown"** (the simulator supports it; no example exposes it).
4. Do **not** add arbitrary states to any model to reach a number.

## 7. Required fixes (automata), in order

1. AUTO-001 — robust fit (never fit at w ≤ 0, clamp k, guard the zoom extent), Reveal visible by default.
2. UX-001 — graph in the first viewport.
3. AUTO-002, AUTO-003, AUTO-004, AUTO-005 — truthful results per model (probability, outputs, rejection trace, total DFA view).
4. AUTO-007 — trace response schema per model kind (typed response models on the backend).
5. AUTO-008, AUTO-009 — set-semantics playback, blocked LTS steps.
6. AUTO-006 — `qid` naming and coverage examples.
7. VIS-001, POL-002 — readability.

## 8. Regression tests to add

* **Backend (pytest, `tests/test_api_automata.py` – new):** for every model id, `GET /api/automata/graph` returns unique node ids, a `qid` per node, exactly one start node, edges whose endpoints exist; `POST /api/automata/trace` validates against a per-kind response model (`steps` is always a list); PA has no `accepted` verdict; Mealy/Moore `accepted` is absent; PDA rejection returns ≥ 1 step and `reject_reason`; agent48 DFA view includes a sink and is total; `count_logical_states == 48` for `n_states=48`.
* **Frontend (vitest):** GraphCanvas with `clientWidth = 0` never yields `scale(0)`/`NaN`/`Infinity` and fits after a resize; TM toast shows a number; ε-NFA step 0 shows the closure; PDA rejection keeps playback and shows the reason; PA/Mealy/Moore show no accepted/rejected badge; node labels render `qN · name`.
* **End-to-end (CDP script `tools/02_lab.mjs`, already provided):** run after the fixes; expected: 0 exceptions, 0 failed requests, `overlappingLabelPairs == 0`, visible nodes == nodes for every model at 1440×900.
