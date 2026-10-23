# UI/UX audit

Functional blockers are listed first; aesthetic refinements are in §8 and are optional. Bug IDs refer to [BUG_REPORT.md](BUG_REPORT.md).

## 1. Strengths worth preserving

* **Coherent visual system.** Dark research-tool palette with semantic tokens (`--blue`, `--cyan`, `--red`, `--amber`, per-group colours `--g-PLAN…`), consistent card/border/radius language, a working light theme (persisted in `localStorage`), Space Grotesk / Inter / JetBrains Mono pairing. Sampled text contrast ≥ 4.5:1 everywhere tested.
* **Honesty badges** (`synthetic`, `measured`, `pending`, `proved`) and explicit callouts ("Abstention, not a verdict", "Reading this chart honestly", "Wilson — not anytime-valid"). This is the project's best UX asset; keep it and extend it.
* **Everything is live data** from the API — no hard-coded charts were found.
* **Responsive basics work:** no horizontal page overflow at 1440/1280/1024/768/390; the sidebar collapses to a drawer below 960 px; tables and step lists scroll inside their containers.
* **Reduced motion is respected** for the cursor, count-ups (final values immediately) and charts.
* **Lab interactions are rich and correct for most models:** search with dimming, minimap, branch overlay, stack/tape panels, KaTeX definitions.

## 2. Functional blockers (fix before any visual work)

| Issue | Bug |
|---|---|
| Lab graph / sections blank when mounted without size or animation frames (embedded pane) | AUTO-001 |
| Explorer replays/estimates a different trajectory after a form change | EXPL-001 |
| Invalid inputs silently replaced by the previous value | FORM-001 |
| Threshold-target results contradict the stopping panel | DASH-001 |
| Result panels follow the live form instead of the run | DASH-002 |
| Lab graph below the fold | UX-001 |

## 3. Information architecture and navigation

* **Nine pages in three groups is reasonable**, but the core research loop (trajectory → intervention → attribution → experiments) is split across Explorer, Dashboard and Studio with no hand-off. Add cross-links that carry state: "Attribute this trajectory" (Explorer → Dashboard with the same source/seed/eps/intervention), "See this instance in the lab" (Dashboard → `/lab?seed=`), "Run 30 trials of this configuration" (Dashboard → Studio pre-filled).
* **Overview** answers "what is AFCR" well, but its "seven required sections" block reads like a course rubric; consider moving it lower and putting a 3-step "How to use this site" strip under the hero (Explore an automaton → Inspect a failed run → Run attribution).
* **Distinguish proposed vs verified** consistently: Overview already uses badges; the Lab and Dashboard should show the same `synthetic · exact ground truth` badge on the graph card and the result card.
* **Docs vs Reproducibility vs README** overlap; the website copies are stale (DOC-001). Generate the command list from one source.
* Page titles should be `<h1>` and the document title should include the page name (A11Y-001, A11Y-004).

## 4. Visual hierarchy, typography, spacing, layout

* **Hero:** H1 is 52 px over three lines; the "Sample-optimal" claim is the visually dominant phrase while its qualifier is 12–13 px grey text (INT-001). Shorten to two lines (`max-width ≈ 16ch` is too tight for the gradient phrase) and put the qualifier tag beside the eyebrow. The CTA row wraps at 1440 px ("Read the guarantees" alone on a second line) — make the third CTA a text link.
* **Lab:** page header (≈200 px) + three-row model picker (≈230 px) + view row push the graph to ≈650 px (UX-001). Proposed layout: compact header (title + one-line lead), a single toolbar row inside the graph card (model select grouped by family · view segmented · size select · search · zoom), graph `min-height: calc(100vh − 160px)`, details panel as a right drawer.
* **Dashboard:** strong two-column layout; the configuration card is long (14 controls). Group into "Instance", "Method", "Guarantee" sections with the Run button sticky at the bottom of the card; show a one-line summary of the active configuration above the results ("seed 5 · LUCB · δ 0.1 · budget 20 000").
* **Studio:** the group chips work but are 12 equal-weight buttons; group them (Main · Sweeps · Robustness · Stage B · Targets).
* **Typography:** uppercase labels change Greek symbols (UI-001). Smallest text is 9.5 px (graph node labels) and 10.5–11 px for many captions; raise captions to ≥ 12 px and graph labels to ≥ 11 px at scale 1.
* **CSS hygiene:** duplicate `.lab-grid` rules with `!important` overrides (POL-001).

## 5. Graph and scientific visualisation

* **Lab graph:** semantics are mostly correct (initial arrow, accepting double ring / green, rejecting red, ε dashed amber, fault red, trace cyan, branch violet). Problems: overlapping labels and clipped self-loops (VIS-001), single "current" marker for set semantics (AUTO-008), partial DFA view (AUTO-005), no `qN` ids (AUTO-006). For the 48-state model, the five "views" look almost identical — add a one-line caption per view saying what changed ("DFA: most-likely successor per action, sink collapsed", "ε-NFA: 8 heal edges shown dashed", "PA: kernel probabilities, policy removed").
* **Legend accuracy:** the small-model legend lists "accepting / rejecting / trace / active set" for every model, including transducers that have neither accepting nor rejecting states; make the legend model-specific.
* **Forest plot (Dashboard):** clear and honest (interval, mean, truth diamond, counts). Add the x-axis meaning ("success probability μ") and mark the threshold θ line for threshold targets (DASH-001).
* **Explorer μ_t chart:** good; the "planted cause" ring and baseline line are informative. Clicking the chart to select a step is undiscoverable — add a hint.
* **Studio charts:** error bars present, log scales labelled. The "ratio of means" explanation ("A value above 1 means the first-named method (the one on the right of 'vs') is cheaper") is confusing — rename the column "× rollouts of the cheaper method" or show "LUCB needs 1.79× fewer rollouts than Uniform".
* **Timeline (Related):** recent-paper cluster unreadable (REL-001).
* **Count-up numbers** should not be used for research metrics (DATA-001).

## 6. Forms, controls, feedback

* Validation must gate submission (FORM-001); show which field blocks the run next to the button.
* Long operations (attribution with large budgets, live experiments) need progress, elapsed time and **Cancel** (DASH-004, API-003).
* Results must be tied to the configuration that produced them, and marked stale when the form changes (DASH-002, EXPL-001).
* Missing exports on the Dashboard (DASH-004); Explorer could export the replay trace (JSON).
* Toasts duplicate information already shown inline; keep toasts for errors and long-running completions only. "Trace computed (undefined steps)" must go (AUTO-007).
* Disabled states: buttons show a spinner while loading ✅; inputs remain editable during a run, which silently diverges from the running request — disable or mark stale.
* Inert controls: one-tab `<Tabs>` on Reproducibility, empty `<Tip>` in the Lab (POL-001).

## 7. Accessibility and responsive behaviour

Confirmed (see bug IDs):
* No `<h1>` on 8 of 9 pages; nested `<main>` in the Lab (A11Y-001).
* Tabs: no `aria-controls`/`tabpanel`, no arrow keys (A11Y-002).
* Clickable `<tr>`/`<g>` rows not focusable; SVG node focus ring not painted (A11Y-003).
* Mobile drawer: focus not moved, Escape does not close; route changes don't move focus or change the title (A11Y-004).
* Native cursor hidden site-wide (A11Y-005).
* Content hidden until scrolled (UX-002).

Potential concerns (not confirmed): screen-reader output of the graph (each node is a `role="button"` with `aria-label="State …"`, but edges/transitions are not exposed — provide the transition table as the accessible alternative and link it with `aria-describedby`); toast region is `aria-live="polite"` ✅ but trace results and attribution outcomes are not announced.

Responsive (tested at 1440×900, 1280×800, 1024×768, 768×1024, 390×844): no page overflow; drawer works; at 390 px the lab's first screen is only the model picker and the graph is 318 px wide with all 48 nodes (unreadable) — offer a list/table mode on small screens; dashboard and explorer stack correctly (config first, results below — add a "jump to results" after Run).

## 8. Component-level recommendations (aesthetic / polish, after the above)

| Component | Recommendation |
|---|---|
| `PageHeader` | `<h1>`, optional compact variant for tool pages (Lab, Dashboard, Explorer) |
| `Stat` / `CountUp` | static numbers for metrics; optional subtle fade-in only |
| `Reveal` | visible by default; animate transform only |
| `Tabs`, `Segmented` | full ARIA patterns; keyboard support |
| `NumberField` | report validity to the parent; `inputMode` numeric for integers; show units |
| `GraphCanvas` | robust fit; merged parallel edges; label halos; focus halo; legend per model; optional dagre/elk layout for small models |
| `Cursor` | keep native cursor; ring as accent; pause when idle/hidden; user toggle |
| `HeroGraph` | fix cx/cy initialisation; label offset so "PLANTED FAULT" doesn't cover a node |
| Labels with math | `<span class="sym">` with `text-transform:none` |
