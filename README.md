# AFCR — Sample-Optimal Culprit Identification for Agent Failures

**Fixed-Confidence Attribution with Automata-Aware Sequential Replay**

Authors: **Kushagra Yogendra Bansal (25bde0080)** · **Kartik Kesharwani (25bde0053)** — Models of Computation research project.

When a long-horizon agent fails, *which step is responsible?* We treat each candidate step as an arm of a best-arm-identification problem: pulling an arm means restoring the failed run just before that step, applying an intervention (repair or resample), replaying to the end, and observing success or failure. AFCR samples adaptively, keeps anytime-valid confidence intervals, and **stops only when the culprit is certified at confidence 1 − δ — otherwise it abstains**. The agent is modelled as a 48-state automaton (plus 64/96-state variants and eight other formal models), so ground truth is known exactly.

> **Honesty box.** All reported experiments are **synthetic** (bandit-arm model, automaton, tool-agent world). ALFWorld and HotpotQA adapters exist and are unit-tested with a mock agent, but **those benchmarks have not been run**. We prove δ-correctness (Thm 1), a sample-complexity upper bound for successive elimination (Thm 2) and the validity of exact-match prefix reuse (Thm 3). We do **not** claim minimax/instance optimality — “sample-optimal” is the research objective in the title. Novelty is *provisional* (finite literature search). See [RESEARCH_STATUS.md](RESEARCH_STATUS.md).

## What is in the repository

| Path | Contents |
|---|---|
| `src/afcr/` | backend package: `automata`, `statistics`, `replay`, `attribution`, `agents`, `benchmarks`, `experiments`, `evaluation`, `api` |
| `website/` | React + TypeScript + Vite site (9 pages) served by the API |
| `tests/` · `website/src/test/` | 179 backend tests (pytest) · 46 frontend tests (vitest) |
| `configs/` | example single-trial specs and suite configs |
| `results/` | `raw/` (per-trial CSV), `processed/` (aggregated JSON, test reports), `figures/` (21 figures + manifest) |
| `paper/` | `main.md` / `main.pdf`, `references.bib`, `figures/` (+ captions), `appendices/` |
| `report/` | technical report (`technical_report.md` / `.pdf`), `experiments.md`, website screenshots |
| `presentation/` | 30-slide editable deck with speaker notes, `outline.md` |
| `research/` | verified related work (`related_work.md/.csv`, `novelty_matrix.csv`) |
| `report/demo_guide.pdf` | **step-by-step demonstration guide** for a reader new to the project, organised around the seven review items |
| `qa/` | quality audit of the website/API, the fix log and the end-to-end verification scripts |
| `docs/` | architecture, I/O specification, automata glossary, API reference, guides, troubleshooting |
| `scripts/` | figure, paper, report, deck, PDF, appendix, screenshot and test-report builders |

Start with [DELIVERY_SUMMARY.md](DELIVERY_SUMMARY.md) (what is done, what is not), then [docs/README.md](docs/README.md).

## Setup (Windows PowerShell; macOS/Linux: same commands with `source .venv/bin/activate`)

Requirements: Python ≥ 3.10 (developed on 3.13), Node ≥ 18 (website and PDF export), Microsoft Edge or Chrome (PDF export, screenshots).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,docs]"          # numpy, scipy, networkx, matplotlib, pydantic, fastapi, uvicorn + pytest, httpx, python-pptx, pillow
cd website; npm install; npm run build; cd ..
```

The model-provider layer is optional: `pip install -e ".[llm]"` and set `OPENAI_API_KEY` (see `.env.example`) to use an OpenAI-compatible model. **Synthetic mode needs no key, and the OpenAI path is implemented but untested.**

## Run the website

```powershell
uvicorn afcr.api.app:app --port 8000
```

Open <http://localhost:8000>. The API documentation is at `/api/docs`. If a page says *“Request failed”* or the API pill is red, the backend is not running — see [docs/troubleshooting.md](docs/troubleshooting.md). For frontend development, run the API as above and `cd website; npm run dev` (port 5173, `/api` is proxied to 8000).

## Run the tests

```powershell
python -m pytest -q                                   # 179 backend tests (≈ 2 min); results-consistency tests need results/ to exist
cd website; npm test; cd ..                           # 46 frontend tests
python scripts/run_tests_report.py                    # writes results/processed/test_report.json (shown on the website)
cd website; npx vitest run --reporter=json --outputFile=../results/processed/frontend_test_report.json; cd ..
```

## Reproduce the experiments

```powershell
$env:OPENBLAS_NUM_THREADS = "1"                       # important on Windows: avoids paging-file errors with many workers
python -m afcr.experiments.suite --config configs/suite_default.json     # all 12 groups, 30 paired trials per method, ≈ 20 min with 6 workers
python -m afcr.experiments.suite --config configs/suite_quick.json       # smoke run (a few minutes)
python -m afcr.experiments.suite --groups main,gap_sweep --trials 10 --workers 4
python -m afcr.experiments.suite --aggregate-only                        # recompute results/processed from results/raw
python -m afcr.experiments.run_one configs/spec_automaton_prefix.json --seed 7 --budget 20000     # ONE trial, printed as JSON
```

Use **at most ~6 workers** on Windows. Every method in a group shares seeds, so comparisons are paired. Details and the group list: [docs/experiments_guide.md](docs/experiments_guide.md).

## Rebuild the deliverables

```powershell
python scripts/make_figures.py          # 21 figures -> results/figures (+ paper/figures, captions, manifest)
python scripts/build_paper.py           # paper/main.md from the template + results
python scripts/build_appendices.py      # paper/appendices/*.md
python scripts/build_report.py          # report/*.md, RESEARCH_STATUS.md, DELIVERY_SUMMARY.md
python scripts/build_docs_folder.py     # docs/*.md (API reference from the OpenAPI schema)
python scripts/take_screenshots.py      # report/screens/*.png (API must be running on :8000)
python scripts/build_pdfs.py            # paper/main.pdf and report/technical_report.pdf (needs Node + Edge)
python scripts/build_deck.py            # presentation/research_presentation.pptx + outline.md
node scripts/demo_screens.mjs           # screenshots for the guide -> report/screens/demo
python scripts/build_demo_guide.py      # report/demo_guide.md + demo_guide.pdf: step-by-step demonstration guide
python scripts/build_related_work_csv.py
```

First time only for the PDFs: `cd scripts/pdf; npm install; cd ../..`.

## The core API in five lines

```python
import numpy as np
from afcr.automata.benchmark48 import build_agent_model
from afcr.replay.automaton_env import make_automaton_instance
from afcr.attribution.engine import run_attribution
from afcr.attribution.algorithms import LUCB
from afcr.attribution.targets import ArgmaxEps
from afcr.statistics.confidence import StackKL

model = build_agent_model(48, eps={"PLAN_SUBGOAL": 0.6})                 # planted fault at PLAN_SUBGOAL with probability 0.6
env = make_automaton_instance(model, np.random.default_rng(5))          # samples a failed trajectory and wraps it as a replay environment
res = run_attribution(env, LUCB(), ArgmaxEps(0.0), StackKL(), delta=0.1, budget=20000, rng=np.random.default_rng(12))
print(res.status, env.arm_labels[res.selected], res.total_rollouts, res.guarantee_applies)
```

`res.status` is `identified` (certified, δ-correct under A1–A6), `budget_exhausted` (**abstention** — never a certified answer), or a fixed-budget/oracle status. The same call, driven by a JSON spec, is `python -m afcr.experiments.run_one configs/spec_automaton_prefix.json`.

## Reading the results honestly

* Rollout counts of trials that hit the budget cap are **censored**: means are lower bounds on the true cost.
* *Abstained* means “budget exhausted without certification”. Fixed-budget methods never certify and are not counted as abstaining.
* The **CAR-style fixed-K** baseline targets a different estimand (latest step whose effect excludes zero); its low “accuracy” against the argmax-repair target is not a statement that CAR is wrong.
* **LUCB + naive sharing** is a deliberately invalid negative control.
* No experiment here says anything about real LLM agents.

## Windows notes

* `python -m pytest` with the whole suite needs the `results/` folder; to run only unit tests: `python -m pytest tests/test_statistics.py tests/test_automata.py tests/test_attribution.py tests/test_toolagent_and_benchmarks.py tests/test_configs.py`.
* If a build prints `DLL load failed … paging file`, lower `--workers` and keep `OPENBLAS_NUM_THREADS=1`.
* Files written by scripts are UTF-8; the Markdown→HTML step normalises CRLF.

## Licence and citation

Course project; no licence granted beyond evaluation. Cite as: Bansal, K. Y. and Kesharwani, K., *Sample-Optimal Culprit Identification for Agent Failures: Fixed-Confidence Attribution with Automata-Aware Sequential Replay* (course project, 2026). Prior work used and its limits are listed in [research/related_work.md](research/related_work.md).
