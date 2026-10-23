# Page-by-page audit

Environment: headless Microsoft Edge driven over the DevTools protocol (`tools/*.mjs`) against `http://localhost:8000` (FastAPI serving `website/dist` built 2026-10-24 02:55). Viewports actually tested: 1440×900, 1280×800, 1024×768, 768×1024, 390×844 (mobile emulation). The embedded browser pane was also probed, but it was hidden (0×0, no animation frames) and is used only as evidence for AUTO-001.

Routing summary (all 9 routes + 404): direct load ✅, refresh on nested route with query (`/lab?model=pda`) ✅, sidebar click from home in order ✅, active nav state ✅, back/forward ✅, unknown route → "Page not found" ✅, 0 exceptions on every route. Focus after navigation stays on `<body>` and `document.title` never changes (A11Y-004). Every page except `/` uses `<h2>` as its title (A11Y-001).

---

## `/` Overview — `pages/Overview.tsx`, `ui/HeroGraph.tsx`

**Primary workflow:** understand the project; jump to dashboard / lab / theory.

| Element | Tested | Result |
|---|---|---|
| Hero CTAs (`/dashboard`, `/lab`, `/theory`) | links read and followed | ✅ |
| Hero graph (real API data, seed 5 trajectory) | rendered | ✅ — but 32 console errors per load (FE-001); "PLANTED FAULT" label overlaps a node |
| KPIs (states, tests, trials, real results) | sampled over time vs API | ⚠️ animated count-up shows transient values (DATA-001); final values correct: 48 · 146/146 · 6518 · 0 pending |
| "Seven required sections" tabs | 7 tabs listed | ✅ content; ⚠️ ARIA tabs incomplete (A11Y-002) |
| Pipeline (15 steps) | hover/click | ✅ |
| Architecture diagram | hover/focus | ✅ |
| Test module table | rendered from `/api/tests` | ✅ (no "last run" timestamp next to the KPI) |

Data dependencies: `/api/results/index`, `/api/tests`, `/api/automata/graph?model=agent48`, `/api/trajectory`.
Research claims: H1 "Sample-optimal…" vs Theory's "never call AFCR sample-optimal" (INT-001). "Fixed-confidence" ✅ (implemented and proved for the stopping rule). "48-state automaton" ✅ (verified). "Real-benchmark results 0 · pending" ✅ honest.

## `/related` Problem & related work — `pages/Related.tsx`

**Primary workflow:** inspect the evidence matrix and the novelty assessment.

| Element | Result |
|---|---|
| Outcome A/B/C cards | ✅ (B selected, provisional wording) |
| Timeline (20 points) | ⚠️ 2025–26 cluster: overlapping lines, clipped labels, CAR point indistinguishable (REL-001) |
| Evidence matrix (21 rows) | ✅ renders from `/api/research/novelty`; ⚠️ rows clickable by mouse only (A11Y-003) |
| Family filter + text filter | ✅ filtering works; ⚠️ "car" finds nothing, no empty-state text (REL-001) |
| Paper detail card / full records (14) | ✅ |

Claims vs source data: matrix cells come from `research/novelty_matrix.csv` ✅; the page states novelty is provisional ✅. No unsupported novelty claim found on the page.

## `/lab` Automata laboratory — `pages/Lab.tsx`, `graph/GraphCanvas.tsx`, `graph/layout.ts`

See [AUTOMATA_AUDIT.md](AUTOMATA_AUDIT.md) for the full investigation.

| Element | Result |
|---|---|
| Model picker (12 models) | ✅ all load; URL `?model=` updated and restored on refresh |
| 48-state views LTS/DFA/NFA/ε-NFA/PA | ✅ load; ⚠️ DFA view partial (AUTO-005) |
| Logical-state size 48/64/96 | ✅ |
| Graph pan/zoom/fit, minimap | ✅ zoom in changes transform, fit restores |
| Search | ✅ "memory" → 5 matches, 43 dimmed |
| State details (click / Enter) | ✅ |
| Trace & playback (step, play, speed, slider) | ✅ for all models; ⚠️ TM toast, PA/Mealy/Moore verdicts, PDA rejection, NFA current marker (AUTO-002…009) |
| Counterfactual branch | ✅ violet repair edges |
| Definition (KaTeX) / transition table / compare / test status | ✅ no KaTeX errors |
| Layout | ⚠️ graph below the fold (UX-001); nested `<main>` (A11Y-001); empty `<Tip>` (POL-001) |

## `/explorer` Trajectory explorer — `pages/Explorer.tsx`

**Primary workflow:** sample a failed run → choose a step → intervene → replay / estimate μ_t.

| Element | Tested | Result |
|---|---|---|
| Sample trajectory (automaton, seed 5) | ✅ 5 steps, planted step preselected, μ_t chart |
| Tool agent source | ✅ 8 steps |
| Step selection (cards, chart click) | ✅ |
| Intervention config (repair/resample, fault probability) | ⚠️ changes after loading are not reflected in the displayed data but are used by replay/estimate (EXPL-001) |
| Run one counterfactual replay | ✅ calls `POST /api/replay` (real re-simulation, not local state); ❌ uses current form seed (EXPL-001) |
| Estimate μ_t (n = 300) | ✅ μ̂ 0.607 [0.550, 0.660] vs exact 0.620; Wilson interval labelled "not anytime-valid" ✅ |
| Original vs counterfactual comparison | ✅ divergence highlighted |
| Empty state / loading / error | ✅ empty state; ✅ error banner (but replay 500s for out-of-range input, API-001) |

Uncertainty presentation is honest (fixed-n Wilson, explicit note). Δ̂ CI is computed as `[lo − baseline, hi − baseline]`, which treats the baseline as known — acceptable because the baseline is exact in the synthetic model; say so in the text.

## `/dashboard` Attribution dashboard — `pages/Dashboard.tsx`, `ui/charts.tsx`

**Primary workflow:** configure → run attribution → read certified culprit or abstention, intervals, stopping rule.

| Element | Result |
|---|---|
| Instance (automaton / tool agent / arms), seed, algorithm, sharing, target, ε/θ, δ, budget, confidence sequence, intervention, candidates, noise | ✅ all sent in `POST /api/attribute` |
| Run (autorun) | ✅ 6089 rollouts, certified `t=4: PLAN_SUBGOAL`, guarantee applies |
| Forest plot + round replay (history) | ✅ replay to round 600 etc. |
| Candidate ranking table | ✅ (shows final values even while replaying an earlier round — minor) |
| Stopping-rule panel | ✅ for argmax; ❌ for first/last-above (DASH-001) |
| Compare with uniform | ✅ runs `uniform_fc` (6089 vs 5829 on seed 5 — the page correctly says "no saving on this instance"); ❌ uses current form (DASH-002) |
| Invalid δ / budget | ❌ error text shown but run still sent with the previous value (FORM-001) |
| Abstention display | ✅ "Abstention, not a verdict" callout, candidate set |
| Guarantee display | ✅ `guarantee_applies` + note; empirical accuracy is not presented as δ-PAC |
| Labels | ❌ "CONFIDENCE Δ", "TOLERANCE Ε" (UI-001); "LUCB would pull next" for every algorithm (DASH-003) |
| Stop / cancel / export | ❌ missing (DASH-004) |

Bounds/stopping agreement: the panel's `lo_h + ε ≥ max hi` uses the API's `lo/hi` and the target's ε, consistent with `attribution/targets.py` for argmax.

## `/studio` Experiment studio — `pages/Studio.tsx`

| Element | Result |
|---|---|
| Saved results: 12 groups | ✅ every chart-based group renders bars/lines from `/api/results/group/*` (no empty chart); tool-agent and targets are table-only by design |
| Raw CSV download | ✅ `/api/results/export?fmt=csv` |
| Paired statistics | ✅ 4 rows, Holm-corrected, matches `results/processed/paired_stats.json` |
| Run simulation (bandit, 3 trials × 3 algorithms) | ✅ real `POST /api/experiment/run`; bars, strip plot, confusion matrix; CSV/JSON export buttons |
| Validation | ⚠️ same NumberField issue (FORM-001) |
| Automaton family in live mode | ⚠️ only δ/budget/trials/seed exposed; `n_states` and `eps_plan` silently default |
| Progress / cancel for long runs | ❌ synchronous request, spinner only (API-003) |

Charts are built from stored result files, not hard-coded (verified against the processed JSON).

## `/theory` Theory & guarantees — `pages/Theory.tsx`

| Element | Result |
|---|---|
| KaTeX rendering | ✅ no `.katex-error` |
| Theorem 1 (δ-correctness) | ✅ statement and proof consistent with the implementation (`x_n = ln(2Kn(n+1)/δ)`, union bound sums to δ) |
| Theorem 2 | ✅ restricted to successive elimination; LUCB bound explicitly "empirical" |
| Theorem 3 | ✅ matches `AutomatonEnv.pull` (repair requires ρ(q) match, resample any action, disabled under noise) |
| Claims ledger | ✅ proved / cited / empirical / hypothesis / not addressed |
| Reveal sections | ⚠️ invisible until scrolled (UX-002) |

No theorem claim found that is unproven or incompatible with the sampling assumptions.

## `/reproducibility` — `pages/Reproducibility.tsx`

| Element | Result |
|---|---|
| Install (PowerShell / bash) | ✅ matches README |
| Commands | ❌ `scripts/build_docs.py` no longer exists; "18 figures" (21) (DOC-001) |
| Spec example | ❌ JSON with `//` comments cannot be run (DOC-001) |
| Checklist / live test status | ✅ 123 passed (frontend 23/23 shown) |
| Artifacts (9 links) | ✅ all 200 |
| Figure gallery (21) + lightbox | ✅ |
| "Licensing notes" one-tab Tabs | ⚠️ inert control (POL-001) |

## `/docs` Documentation — `pages/Docs.tsx`

| Element | Result |
|---|---|
| Search | ⚠️ keyword lists only ("LUCB" → nothing) (DOC-003) |
| API reference from `/openapi.json` | ✅ 20 endpoints; ⚠️ ranges with minimum 0 dropped (DOC-002); error contract inaccurate (DOC-001) |
| Glossary, limitations, troubleshooting | ✅ |
| Internal links `/theory`, `/reproducibility` | ✅ work but are plain `<a>` (full reload instead of client navigation) |
