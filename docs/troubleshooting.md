# Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The site shows **"Request failed"** / "Cannot reach the API" / the API pill is red | the backend is not running (the site only displays data served by it). Start it from the repository root: `uvicorn afcr.api.app:app --port 8000` and open <http://localhost:8000>. With `npm run dev` the proxy targets port 8000. |
| A page is blank until I refresh | fixed (pages no longer start invisible and wait for an animation). Rebuild the site (`cd website; npm run build`) and hard-refresh (Ctrl+F5) once to drop the old bundle |
| "Website not built" text at `/` | run `cd website && npm install && npm run build` |
| Studio says "no saved results" | run `python -m afcr.experiments.suite` (or copy `results/` from a full run) |
| Test-status panels are empty | run `python scripts/run_tests_report.py`; for the frontend `cd website && npx vitest run --reporter=json --outputFile=../results/processed/frontend_test_report.json` |
| `DLL load failed … paging file is too small` during experiments | too many parallel workers; use ≤ 6 and `OPENBLAS_NUM_THREADS=1` |
| `vite build` crashes with a native stack trace once | transient memory pressure on Windows; run it again |
| HTTP 422 from the API | the server validated your input (δ ∉ (0,1), budget not a positive integer, unknown algorithm …); the message names the field |
| PDF export fails | needs Node ≥ 18 and Edge/Chrome; `cd scripts/pdf && npm install` once, then `python scripts/build_pdfs.py` |
| The graph looks tiny | press the *fit to view* button; the graph auto-fits until you interact with it |
| Custom cursor missing | disabled on touch devices and with reduced-motion preferences (by design) |
| `ModuleNotFoundError: afcr` | the package is not installed: run `pip install -e .` once, or set `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH = "src"`). Tests set `pythonpath = src` themselves. |
