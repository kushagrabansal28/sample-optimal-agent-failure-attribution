# Executive summary — AFCR application audit (2026-10-24)

> **Status update:** every issue listed here has been fixed and verified; see [FIX_REPORT.md](FIX_REPORT.md). This document describes the application as it was audited, before the fixes.

## Overall health

**Functional in a normal browser, with integrity and robustness defects.** All 9 routes render, refresh, navigate and go back/forward without a single JavaScript exception or failed request; all 12 automata models load and execute; the attribution, replay and experiment workflows call the real backend. Existing suites pass: **pytest 123/123, vitest 23/23, `tsc` clean**. The audit found **39 issues: 0 P0, 3 P1, 13 P2, 20 P3, 3 P4** ([BUG_REPORT.md](BUG_REPORT.md)).

## Highest-severity issues

| ID | Sev | Issue |
|---|---|---|
| AUTO-001 | P1 | Lab graph drawn at `scale(0)` and scroll-revealed sections stay invisible when the page is mounted in a zero-size / non-painting viewport (the hidden embedded browser pane) — explains "automata work on the homepage but not elsewhere" |
| SEC-001 | P1 | Path traversal: `GET /../../pyproject.toml` serves files outside `website/dist` |
| EXPL-001 | P1 | Trajectory explorer replays/estimates a *different* trajectory after a form change (uses live form values) |
| API-001 | P2 | `/api/replay` and `/api/replay/estimate` return 500 for out-of-range input |
| AUTO-002/003/004/005 | P2 | PA and transducers shown as "accepted"; PDA rejections have no trace; 48-state "DFA" view is not total and hides its sink |
| DASH-001/002, FORM-001 | P2 | Threshold-target results contradict the stopping panel; result panels follow the live form; invalid inputs silently replaced by the last valid value |
| DATA-001, UI-001 | P2 | KPI count-up animation displays wrong transient numbers; uppercase CSS turns δ→Δ, ε→Ε |

## Why the automata may "not work outside the homepage"

In a visible browser the lab works (verified for every model). It fails when the page is mounted without a size or animation frames — the state of the embedded browser pane when hidden: `innerWidth = 0`, 0 animation frames/s, graph transform `scale(0)` (48 nodes in the DOM, invisible), KPIs `0`, Reveal sections opacity 0. The homepage graphic is a separate fixed-viewBox SVG and is unaffected. Contributing factor: the lab graph starts ≈650 px down the page (UX-001), so at 1440×900 only one row of states is visible. Other possible causes to rule out with the user: API not running ("Request failed"), `npm run preview` (no `/api` proxy, CFG-001).

## Homepage inconsistencies

* **47 vs 48 states, 144 of 146 tests, 6413 trials:** not data errors. The live values are 48 · 146/146 · 6518. The screenshot values are each ≈98.4 % of the true values — a single frame of the 900 ms count-up animation (sampled: 540 ms → `47 | 143 | 6401`). The model has exactly 48 unique, reachable logical states; **do not add a state**.
* **"Sample-optimal" H1** conflicts with the Theory page ("never call AFCR sample-optimal"); the qualifier is small grey text (INT-001).
* 32 SVG console errors on every homepage load (FE-001).

## Most important UI/UX problems

Graph below the fold and hard to read for larger models (UX-001, VIS-001); results not tied to the configuration that produced them (EXPL-001, DASH-002); validation that does not block submission (FORM-001); misleading model-specific badges (AUTO-002/003); no cancel/export on the Dashboard (DASH-004); weak keyboard/ARIA support for tabs, rows, drawer and route changes (A11Y-001…005). User requirement: **q0, q1, … state names and full case coverage for every machine type** (AUTO-006).

## Recommended fix order

1. SEC-001 → EXPL-001 → AUTO-001 (P1).
2. API-001, API-002, then automata truthfulness (AUTO-002…005, AUTO-007) and UX-001.
3. DATA-001, DASH-001, DASH-002, FORM-001, UI-001, INT-001.
4. AUTO-006 (qN naming + coverage), AUTO-008/009, VIS-001.
5. Remaining P3/P4, accessibility, docs.

Detailed tasks with acceptance criteria: [FIX_PLAN.md](FIX_PLAN.md).

## Limitations

Headless Edge only (no Firefox/Safari, no real screen reader, mobile emulation only). The embedded pane was hidden during the audit, so the user's exact screen state was inferred, not observed; no screenshot was attached to the request. Build, report-generation and experiment commands were not run because they overwrite served or result files. Load behaviour of large inputs (API-003) was reviewed in code, not stress-tested.
