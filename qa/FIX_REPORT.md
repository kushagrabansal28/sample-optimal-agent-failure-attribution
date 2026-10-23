# Fix report

All 39 issues of [BUG_REPORT.md](BUG_REPORT.md) are fixed and verified. After the fixes: **179/179 backend tests**, **46/46 frontend tests**, and `qa/tools/08_verify_fixes.mjs` **100/100 end-to-end checks** (evidence in `qa/evidence-after/`).

The user-reported symptom “I have to refresh to open the automata laboratory (or any other tab)” had one root cause: the page container was an `AnimatePresence mode="wait"` element that started at `opacity: 0`. After a click the old page had to finish an exit animation and the new page had to run an entrance animation before it became visible; a refresh skipped both. If the browser delays or never runs animation frames (hidden or background window, busy machine) the new page stayed invisible. Pages are now plain elements, nothing starts hidden, and `qa/tools/08_verify_fixes.mjs` clicks through all nine pages in a browser whose `requestAnimationFrame` never fires.

| ID | Severity | What changed | Files | Verified by |
|---|---|---|---|---|
| AUTO-001 | P1 | GraphCanvas never fits into a container without size, clamps the scale, ignores degenerate zoom transforms and refits when a size appears; Reveal/page transitions/count-ups no longer start hidden. | `website/src/graph/GraphCanvas.tsx, ui/kit.tsx, ui/Shell.tsx` | fixes.test.tsx 'never produces a degenerate transform…'; tools/08 (no animation frames, 1x1 → 1440x900) |
| EXPL-001 | P1 | The explorer stores the exact parameters of the loaded trajectory; replays and estimates use them, a notice shows when the form differs. | `website/src/pages/Explorer.tsx` | fixes.test.tsx 'replays with the parameters of the sampled trajectory' |
| SEC-001 | P1 | The static fallback resolves the path and serves only files inside website/dist; unknown /api and /files paths are 404. | `src/afcr/api/app.py (spa)` | tests/test_api_http.py (6 traversal variants) |
| API-001 | P2 | Bounds on every replay/estimate/trace field and a handler turning pydantic errors raised inside handlers into 422. | `src/afcr/api/app.py` | tests/test_api_http.py |
| AUTO-002 | P2 | PA results are a probability (exact + Monte-Carlo) and a description of the one sampled run; no accepted/rejected verdict. | `src/afcr/api/lab.py, pages/Lab.tsx (ResultPanel)` | test_api_automata.py; fixes.test.tsx; tools/08 |
| AUTO-003 | P2 | Transducers report their output word only; no acceptance. | `src/afcr/api/lab.py, pages/Lab.tsx` | test_api_automata.py; fixes.test.tsx |
| AUTO-004 | P2 | A rejected PDA run returns the furthest computation and a reason (underflow, mismatch, unclosed call); the UI keeps playback and the stack. | `src/afcr/automata/pda.py, api/lab.py` | test_api_automata.py; fixes.test.tsx; tools/08 |
| AUTO-005 | P2 | The 48-state DFA view draws the explicit sink with one aggregated default edge per state; the logical count stays 48. | `src/afcr/api/app.py, graph/GraphCanvas.tsx` | test_api_automata.py; tools/08 (49 nodes, 48 logical) |
| AUTO-006 | P2 | Every state is q0, q1, …; 13 machines with one-click example cases (accept, reject, dead state, empty word, invalid symbol, unknown); NFA→DFA and ε-removal views; a never-halting TM; a DFA with a dead state; a 2-symbol PA. | `src/afcr/api/lab.py, api/app.py, pages/Lab.tsx` | test_api_automata.py (every example executed); tools/08 (all example cases) |
| DASH-001 | P2 | Threshold targets get their own panel (above / below / undecided per step, θ line on the forest plot) and are judged against the threshold answer. | `website/src/pages/Dashboard.tsx, ui/charts.tsx` | fixes.test.tsx 'threshold targets…' |
| DASH-002 | P2 | A result is stored with the request that produced it; budget, comparison and summary use that request; a stale notice appears when the form changes. | `website/src/pages/Dashboard.tsx` | fixes.test.tsx 'a result stays tied…' |
| DATA-001 | P2 | Research numbers are rendered exactly (no count-up animation). | `website/src/ui/kit.tsx, pages/Overview.tsx` | fixes.test.tsx 'research metrics are exact'; tools/08 |
| FORM-001 | P2 | A form validity hook disables submit buttons while any number field is invalid, with a message. | `website/src/ui/kit.tsx and the four pages` | fixes.test.tsx 'δ = 0 disables Run' |
| UI-001 | P2 | Greek symbols in labels keep their case (.sym). | `website/src/styles.css, kit.tsx (Sym)` | visual (screenshots) |
| API-002 | P2 | Unknown /api and /files routes return 404 JSON; the client rejects non-JSON answers from JSON endpoints. | `src/afcr/api/app.py, website/src/lib/api.ts` | tests/test_api_http.py; fixes.test.tsx |
| UX-001 | P2 | A compact model toolbar puts the graph in the first screen (top ≈ 430 px at 1440×900); graph/table switch for small screens. | `website/src/pages/Lab.tsx, styles.css` | tools/08 (graph top < 700 px) |
| A11Y-001 | P3 | One h1 per page, one main landmark. | `ui/kit.tsx (PageHeader), pages/Lab.tsx, ui/Shell.tsx` | fixes.test.tsx 'every page has exactly one h1…' |
| A11Y-002 | P3 | ARIA tabs: ids, aria-controls, tabpanel, roving tabindex, arrow/Home/End keys. | `website/src/ui/kit.tsx and the pages` | fixes.test.tsx 'tabs follow the WAI-ARIA pattern' |
| A11Y-003 | P3 | Table rows, matrix rows, forest-plot rows and timeline points are keyboard operable; graph nodes show a focus halo. | `ui/kit.tsx, ui/charts.tsx, pages/Related.tsx, styles.css` | fixes.test.tsx 'related-work rows are keyboard operable' |
| A11Y-004 | P3 | The mobile menu takes focus, traps Tab, closes on Escape and returns focus; every route sets document.title and moves focus to the heading (without stealing focus from an input). | `website/src/ui/Shell.tsx` | fixes.test.tsx; tools/08 (title and focus) |
| A11Y-005 | P3 | The native cursor is no longer hidden; the ring is decoration and its animation loop stops when the pointer is idle. | `website/src/ui/Cursor.tsx, styles.css` | visual / code |
| API-003 | P3 | n_states bounded to 48–96 on trace and graph; experiment work is capped with an explanatory 422. | `src/afcr/api/app.py` | tests/test_api_http.py, test_api_automata.py |
| AUTO-007 | P3 | Trace responses always have a list `steps`; the TM response adds n_steps and tape configurations; the toast shows a number. | `src/afcr/api/lab.py, pages/Lab.tsx` | test_api_automata.py; fixes.test.tsx |
| AUTO-008 | P3 | Playback reveals the edges of each step; NFA/ε-NFA show the active set (including the initial ε-closure) and no single 'current' state. | `pages/Lab.tsx (stepGroups), graph/GraphCanvas.tsx` | fixes.test.tsx 'step groups…'; test_api_automata.py |
| AUTO-009 | P3 | A blocked LTS step is shown as 'blocked at q3 on plan' with the reason. | `src/afcr/api/lab.py, pages/Lab.tsx` | test_api_automata.py; tools/08 |
| CFG-001 | P3 | `preview.proxy` added to vite.config.ts. | `website/vite.config.ts` | executed: npm run preview → /api/health 200 via :4173 |
| DASH-003 | P3 | The caption names the algorithm that ran and is hidden when there is no suggestion. | `pages/Dashboard.tsx` | code |
| DASH-004 | P3 | Cancel (AbortController) while a run is in progress; Export JSON and ranking CSV. | `pages/Dashboard.tsx, lib/api.ts` | fixes.test.tsx 'exports the result and can cancel' |
| DOC-001 | P3 | The site lists the scripts that exist and a spec example that parses with run_one. | `pages/Reproducibility.tsx, pages/Docs.tsx` | code review |
| DOC-002 | P3 | The range column keeps bounds of 0 and nullable types. | `pages/Docs.tsx (rangeOf)` | fixes.test.tsx 'range column keeps bounds of zero' |
| DOC-003 | P3 | Documentation search indexes the rendered text of every section; glossary gained LUCB, successive elimination, stack-KL. | `pages/Docs.tsx` | fixes.test.tsx 'searching the documentation…' |
| FE-001 | P3 | The hero animation moves a group (transform) instead of animating circle attributes: no console errors. | `website/src/ui/HeroGraph.tsx` | tools/08 'homepage: no console errors' |
| INT-001 | P3 | The qualifier is a badge directly under the headline, linking to Theory. | `pages/Overview.tsx` | visual |
| REL-001 | P3 | Broken time axis (2006–2017 | 2024.9–2026.8), labels flip at the edge, acronym search, empty-state row. | `pages/Related.tsx` | fixes.test.tsx; screenshot |
| VIS-001 | P3 | Parallel edges merged into one arrow with one label; label de-collision; the fit includes label extents; self-loop room. | `graph/GraphCanvas.tsx, graph/layout.ts` | tools/08 (0 overlapping labels, 0 clipped states for every model) |
| UX-002 | P3 | Content is visible by default; entrance animations only move things. | `ui/kit.tsx (Reveal), styles.css` | tools/08 (no invisible elements) |
| POL-001 | P4 | Fake one-tab control and the empty tooltip removed; the lab grid is defined once. | `pages/Reproducibility.tsx, Lab.tsx, styles.css` | code |
| POL-002 | P4 | The tape window is computed once over the whole run. | `pages/Lab.tsx` | code / tools/08 |
| POL-003 | P4 | Markdown download routes have summaries. | `src/afcr/api/app.py` | tests/test_api_http.py 'openapi summaries are meaningful' |
