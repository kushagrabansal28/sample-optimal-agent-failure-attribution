# DELIVERY_SUMMARY

Authors: Kushagra Yogendra Bansal (25bde0080) and Kartik Kesharwani (25bde0053)

## Artifacts and exact paths
| Artifact | Path |
|---|---|
| Related work, evidence log; machine-readable records; novelty matrix | `research/related_work.md`, `research/related_work.csv`, `research/novelty_matrix.csv` |
| Research paper (source, PDF, bibliography, captions) | `paper/main.md`, `paper/main.pdf`, `paper/references.bib`, `paper/figures/` (+ `CAPTIONS.md`) |
| Technical report (source, PDF); experiments log | `report/technical_report.md`, `report/technical_report.pdf`, `report/experiments.md`, `report/screens/` |
| Slides (editable, 30 slides, speaker notes on every slide), outline and generator | `presentation/research_presentation.pptx`, `presentation/outline.md`, `scripts/build_deck.py` |
| Documentation (architecture, I/O spec, automata glossary, API reference, guides, troubleshooting) | `docs/` (generated: `scripts/build_docs_folder.py`) |
| Paper appendices (proof of Thm 2, confidence sequences, 48-state specification, complete result tables) | `paper/appendices/` |
| Experiment configurations (single trials and whole suites) | `configs/`, `src/afcr/experiments/run_one.py` |
| Backend | `src/afcr/**` (FastAPI app: `src/afcr/api/app.py`) |
| Website (source and build) | `website/` (React + TypeScript + Vite), `website/dist/` |
| Tests | backend `tests/`; frontend `website/src/test/` |
| Experiments | `src/afcr/experiments/suite.py` (+ `core.py`); raw `results/raw/*.csv`; processed `results/processed/*.json` |
| Figures (PNG + SVG), manifest | `results/figures/` |
| Status | `RESEARCH_STATUS.md`, this file, `README.md` |

## How to run
```
pip install -e ".[dev,docs]"
cd website && npm install && npm run build && cd ..
uvicorn afcr.api.app:app --port 8000          # open http://localhost:8000   (API explorer: /api/docs)
```
All commands (tests, suite, figures, documents, deck, PDFs): `README.md` and the Reproducibility page.

## Tests completed
* Backend: `python -m pytest` → **179/179 passed** (automata, statistics incl. empirical coverage under adaptive sampling, attribution, tool agent, adapters, prefix-reuse unbiasedness).
* Frontend: `cd website && npm test` → **46/46 passed** (navigation, model switching, graph interaction, validation, API errors, loading/error/empty states, export, simulation execution, responsive menu).
* Manual: every page loaded in a browser pane; no horizontal overflow at 390 px width.

## Experiments completed
Twelve synthetic groups, 6,518 trials (see `report/experiments.md`).

## Experiments not completed
ALFWorld; HotpotQA; real LLM agents; baselines other than the CAR-style re-implementation; browser end-to-end tests.

## Status of the theoretical guarantee
Theorem 1 (δ-correctness for any sampling rule) and Theorem 3 (prefix-reuse validity) are **proved** under assumptions A1–A6; Theorem 2 (sample complexity) is proved for **successive elimination only**; LUCB's sample complexity with the stack bound is **empirical**; no optimality is claimed. Observed: 0 wrong answers among 3,620 certified guaranteed trials.

## Remaining publication risks
Novelty is provisional (abstract-level reading of some neighbours; fast-moving field); all results are synthetic; the automaton is hand-designed; the stack bound is conservative; real-agent assumptions (A1–A4) are likely violated; licences not verified at source; the OpenAI-compatible provider is untested.
