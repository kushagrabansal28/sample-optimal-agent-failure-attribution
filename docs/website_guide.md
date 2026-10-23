# Website guide

Start: `uvicorn afcr.api.app:app --port 8000` and open <http://localhost:8000> (build once with `cd website && npm install && npm run build`;
for development run `npm run dev` — port 5173 proxies `/api` to the backend).

| Page | Route | What it shows (all from the API) |
|---|---|---|
| Overview | `/` | live KPIs, the seven required sections as tabs, the 15-step pipeline, architecture diagram, δ-PAC explainer, test status |
| Problem & related work | `/related` | timeline, filterable evidence matrix, per-paper records, outcome A/B/C |
| Automata laboratory | `/lab` | 13 machines with q0, q1, … states: pick a machine, press an **example case** (accept / reject / dead state / invalid input / unknown …) and play the run on the graph; per-machine result panel (probability, outputs, stack, tape, reason for rejection); graph ⇄ table switch; NFA/ε-NFA *Show as* views (subset construction, ε-removal); the 48-state automaton in LTS/DFA/NFA/ε-NFA/PA views (DFA view draws the sink); search, zoom/pan, minimap, state details, counterfactual-branch overlay, definitions, comparison matrix, test status |
| Trajectory explorer | `/explorer` | sample a failed run, exact μ_t chart, intervene on a step, one replay or an n-replay estimate, original vs counterfactual |
| Attribution dashboard | `/dashboard` | run the real algorithm; replayable forest plot of intervals; stopping-rule panel; ranking; comparison with uniform |
| Experiment studio | `/studio` | live simulations, all saved result groups, paired statistics, CSV/JSON export |
| Theory & guarantees | `/theory` | estimand, assumptions, theorems with expandable proofs, claims ledger |
| Reproducibility | `/reproducibility` | install, commands, seed policy, live test status, artifacts, checklist, figure gallery |
| Documentation | `/docs` | searchable specification, generated API reference, glossary, troubleshooting |

Deep links: `/lab?model=pda`, `/dashboard?autorun=1`, `/dashboard?seed=5&source=automaton&autorun=1`, `/explorer?autoload=1`.

Keyboard: Tab / Shift-Tab, Enter on states and table rows, arrow keys in tab lists, Escape closes the mobile menu; a *Skip to content* link and one `h1` per page.

**Honesty conventions.** Simulated results carry a *synthetic* badge; pending work carries a *pending* badge; nothing on the site is a real-benchmark result. The custom cursor and background spotlight are disabled on touch devices and when the system requests reduced motion.
