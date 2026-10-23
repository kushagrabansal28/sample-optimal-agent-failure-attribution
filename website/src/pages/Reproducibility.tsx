import { AnimatePresence, motion } from 'framer-motion'
import { Check, Circle, X } from 'lucide-react'
import { useState } from 'react'
import { api, type FigureEntry } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { Badge, Callout, Card, CodeBlock, DataTable, Disclosure, ErrorBanner, Measured, PageHeader, Pending, Reveal, SkeletonBlock, type Col } from '../ui/kit'

const PS = `# from the project folder
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e ".[dev,docs]"
cd website; npm install; npm run build; cd ..
uvicorn afcr.api.app:app --port 8000      # website + API at http://localhost:8000`
const SH = `python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,docs]"
(cd website && npm install && npm run build)
uvicorn afcr.api.app:app --port 8000`
const RUN = `python -m pytest                                   # backend: unit + statistical tests (slow ones included)
cd website && npm test                              # frontend tests (vitest)
python scripts/run_tests_report.py                  # writes results/processed/test_report.json (shown on this site)
OPENBLAS_NUM_THREADS=1 python -m afcr.experiments.suite --trials 30 --workers 6      # all synthetic experiment groups
python -m afcr.experiments.suite --groups main,budget_curve --trials 10              # a subset
python scripts/make_figures.py                      # 21 figures + manifest, from real objects / result files
python scripts/build_paper.py                       # paper/main.md (numbers read from results/)
python scripts/build_appendices.py                  # paper/appendices/*.md
python scripts/build_report.py                      # report/*.md, RESEARCH_STATUS.md, DELIVERY_SUMMARY.md
python scripts/build_docs_folder.py                 # docs/*.md (API reference from the OpenAPI schema)
python scripts/build_deck.py                        # presentation/research_presentation.pptx + outline.md
python scripts/build_pdfs.py                        # PDF exports of paper and report
python scripts/build_demo_guide.py                  # the step-by-step demonstration guide (PDF)
python -m afcr.experiments.run_one configs/spec_automaton_prefix.json --seed 7   # ONE trial from a JSON spec`
const SPEC = `{
  "_comment": "keys starting with _ are comments; run: python -m afcr.experiments.run_one spec.json",
  "kind": "automaton", "n_states": 48, "eps_plan": 0.6,
  "method": "lucb_prefix",
  "delta": 0.1, "budget": 60000, "eps": 0.0,
  "target": "argmax", "conf": "stack_kl",
  "intervention": "repair", "recon_noise": 0.0, "seed": 20000
}
# method: lucb | lucb_prefix | successive_elim | uniform_fc | random_fc | ...
# target: argmax, or first_above / last_above with "theta"; the algorithm RNG uses seed + 7`

const ARTIFACTS: Array<[string, string, string]> = [
  ['Paper (Markdown + PDF)', '/files/paper/main.md', 'paper/main.md'], ['Technical report', '/files/report/technical_report.md', 'report/technical_report.md'], ['Experiments log', '/files/report/experiments.md', 'report/experiments.md'],
  ['Slides (editable)', '/files/presentation/research_presentation.pptx', 'presentation/research_presentation.pptx'], ['Related work (verification log)', '/files/research/related_work.md', 'research/related_work.md'],
  ['Novelty matrix (CSV)', '/files/research/novelty_matrix.csv', 'research/novelty_matrix.csv'], ['Related-work records (CSV)', '/files/research/related_work.csv', 'research/related_work.csv'],
  ['Research status', '/files/RESEARCH_STATUS.md', 'RESEARCH_STATUS.md'], ['Delivery summary', '/files/DELIVERY_SUMMARY.md', 'DELIVERY_SUMMARY.md'],
]

function Gallery({ figs }: { figs: FigureEntry[] }) {
  const [open, setOpen] = useState<FigureEntry | null>(null)
  return (
    <>
      <div className="grid cols-3">
        {figs.map((f) => (
          <motion.button key={f.file} className="card hover fig-card" onClick={() => setOpen(f)} whileTap={{ scale: 0.98 }} aria-label={`Open ${f.title}`}>
            <img src={`/files/results/figures/${f.file}`} alt={f.title} loading="lazy" />
            <div className="row" style={{ marginTop: 8, justifyContent: 'space-between' }}><b className="small" style={{ textAlign: 'left' }}>{f.title}</b><Badge kind={f.kind === 'experimental' ? 'ok' : f.kind === 'structural' ? 'info' : 'vio'}>{f.kind}</Badge></div>
          </motion.button>
        ))}
      </div>
      <AnimatePresence>
        {open && (
          <motion.div className="lightbox" initial={false} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setOpen(null)} role="dialog" aria-modal="true" aria-label={open.title}>
            <motion.div className="card" initial={{ scale: 0.94, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.96, opacity: 0 }} onClick={(e) => e.stopPropagation()} style={{ maxWidth: 1100, width: '94vw', maxHeight: '92vh', overflow: 'auto' }}>
              <div className="row" style={{ justifyContent: 'space-between' }}><h3>{open.title}</h3><button className="btn icon ghost sm" aria-label="Close" onClick={() => setOpen(null)}><X size={16} /></button></div>
              <img src={`/files/results/figures/${open.file}`} alt={open.title} style={{ width: '100%', borderRadius: 10, background: '#fff', margin: '10px 0' }} />
              <p className="small">{open.caption}</p>
              <p className="xs muted">Kind: <b>{open.kind}</b> · source: <code>{open.source}</code> · file: <code>results/figures/{open.file}</code></p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

export default function Reproducibility() {
  const [shell, setShell] = useState<'ps' | 'sh'>('ps')
  const tests = useAsync(() => api.tests(), [])
  const idx = useAsync(() => api.resultsIndex(), [])
  const t = tests.data
  const meta = idx.data?.meta
  const checks: Array<[string, boolean | null, string]> = [
    ['Backend tests pass', t ? (t.total ? t.failed === 0 : null) : null, t?.total ? `${t.passed}/${t.total} passed` : 'no test report'],
    ['Raw and aggregate results stored separately', idx.data ? idx.data.available : null, 'results/raw/*.csv vs results/processed/*.json'],
    ['Seeds fixed and documented', true, 'instance seed = base + trial index; algorithm RNG = seed + 7'],
    ['All figures traced to code or result files', idx.data ? !!idx.data.figures?.length : null, 'results/figures/manifest.json'],
    ['Synthetic and real results kept apart', true, 'every chart labelled synthetic; real-benchmark count = 0'],
    ['ALFWorld / HotpotQA executed', false, 'adapters + mock-tested only (pending)'],
    ['Dataset licences verified from official sources', false, 'read from secondary sources only'],
    ['Baselines reproduced from original code', false, 'CAR rule re-implemented from the paper text; others not reproduced'],
  ]
  return (
    <div className="stack" style={{ gap: 22 }}>
      <PageHeader eyebrow="Reproducibility" title="Run it yourself" lead="Everything on this site can be regenerated from the repository with the commands below. No paid API is needed for the synthetic mode." />

      <Reveal><div className="grid cols-2">
        <Card title="Install" right={<div className="seg" role="group" aria-label="Shell">{(['ps', 'sh'] as const).map((s) => <button key={s} aria-pressed={shell === s} onClick={() => setShell(s)}>{shell === s && <motion.span layoutId="shell" className="seg-pill" />}{s === 'ps' ? 'PowerShell' : 'bash'}</button>)}</div>}>
          <CodeBlock code={shell === 'ps' ? PS : SH} lang={shell} />
          <p className="small muted" style={{ marginBottom: 0 }}>Python ≥ 3.10, Node ≥ 18. Development was done on Windows 11 / Python 3.13 / Node 24.</p>
        </Card>
        <Card title="Reproducibility checklist">
          <div className="stack" style={{ gap: 8 }}>
            {checks.map(([k, v, d]) => (
              <div key={k} className="row" style={{ alignItems: 'flex-start', flexWrap: 'nowrap' }}>
                {v === true ? <Check size={17} color="var(--green)" style={{ flex: 'none', marginTop: 2 }} /> : v === false ? <X size={17} color="var(--red)" style={{ flex: 'none', marginTop: 2 }} /> : <Circle size={17} color="var(--muted)" style={{ flex: 'none', marginTop: 2 }} />}
                <div><div className="small" style={{ fontWeight: 600 }}>{k}</div><div className="xs muted">{d}</div></div>
              </div>
            ))}
          </div>
        </Card>
      </div></Reveal>

      <Reveal><Card title="Commands"><CodeBlock code={RUN} lang="bash" />
        <Callout kind="warn" title="Windows note">Many parallel workers can exhaust the paging file (“DLL load failed … paging file is too small”). Use ≤ 6 workers and <code>OPENBLAS_NUM_THREADS=1</code>.</Callout></Card></Reveal>

      <Reveal><div className="grid cols-2">
        <Card title="Test status (live)" right={t?.ran_at ? <Measured /> : undefined}>
          {tests.loading ? <SkeletonBlock rows={4} /> : tests.error ? <ErrorBanner error={tests.error} onRetry={tests.reload} /> : !t?.total ? <Callout kind="info">No report yet — run <code>python scripts/run_tests_report.py</code>.</Callout> : (
            <div className="stack">
              <div className="row"><Badge kind={t.failed ? 'pend' : 'ok'}>{t.passed} passed</Badge>{t.failed > 0 && <Badge kind="pend">{t.failed} failed</Badge>}{t.skipped > 0 && <Badge kind="plain">{t.skipped} skipped</Badge>}<span className="xs muted">{t.ran_at}</span></div>
              <div className="small muted"><code>{t.command}</code></div>
              {t.frontend && <div className="row"><Badge kind={t.frontend.failed ? 'pend' : 'ok'}>{t.frontend.passed}/{t.frontend.total} frontend tests</Badge><span className="small muted"><code>{t.frontend.command}</code></span></div>}
              {Object.entries(t.modules).map(([m, v]) => <Disclosure key={m} title={<span className="mono">{m}</span>} right={<Badge kind={v.failed ? 'pend' : 'ok'}>{v.passed}/{v.passed + v.failed}</Badge>}><div className="chips">{v.tests.map((x) => <span key={x.name} className={`chip ${x.outcome === 'passed' ? 'ok' : 'fault'}`}>{x.outcome === 'passed' ? '✓' : '✗'} {x.name.replace('test_', '')}</span>)}</div></Disclosure>)}
            </div>
          )}
        </Card>
        <Card title="Seed policy & configuration">
          <ul className="small stack" style={{ paddingLeft: 18, margin: '0 0 12px' }}>
            <li>Every trial is a plain-dict <i>spec</i>; the same spec reproduces the same row.</li>
            <li>Instance seed <code>s</code> = group base + trial index (base seeds: main 20000, size 40000, ablation 43000, budget 44000, …).</li>
            <li>Algorithm RNG = <code>s + 7</code>; replays draw fresh streams from it.</li>
            <li>Methods share seeds, so comparisons are <b>paired</b> on the same failed trajectory.</li>
          </ul>
          <CodeBlock code={SPEC} lang="json" />
        </Card>
      </div></Reveal>

      <Reveal><Card title="Models and datasets">
        <div className="grid cols-2">
          <div className="stack"><b>Model providers</b>
            <p className="small muted" style={{ margin: 0 }}>The statistics never import a model SDK. <code>ScriptedProvider</code> (deterministic, used by tests), <code>RecordingProvider</code> (exact prefix replay of recorded completions) and <code>OpenAICompatProvider</code> (hosted / vLLM / Ollama; reads <code>OPENAI_API_KEY</code>, <code>OPENAI_BASE_URL</code>; <b>never exercised by the tests</b>). Keys live in the environment only, never in the frontend bundle.</p>
            <CodeBlock code={'# .env (see .env.example) — optional, unused in synthetic mode\nOPENAI_API_KEY=\nOPENAI_BASE_URL='} lang="env" /></div>
          <div className="stack"><b>Benchmarks</b>
            <div className="row"><Badge kind="plain">ALFWorld</Badge><Pending /></div>
            <p className="small muted" style={{ margin: 0 }}>MIT licence per package metadata; needs <code>pip install alfworld</code> (TextWorld) and <code>alfworld-download</code>. Adapter: <code>afcr.benchmarks.ALFWorldGame</code> — raises <code>BenchmarkUnavailable</code> when not installed.</p>
            <div className="row"><Badge kind="plain">HotpotQA</Badge><Pending /></div>
            <p className="small muted" style={{ margin: 0 }}>CC BY-SA 4.0 per secondary sources. Adapter loads a <em>local</em> distractor-setting JSON you provide; normalised exact match as evaluator. Nothing is downloaded or bundled. Licences were <b>not</b> verified against the official repositories.</p>
            <Callout kind="info">The generic replay environment (<code>TextGameReplayEnv</code>) is tested only with a scripted mock agent — that test is an interface check, <b>not a benchmark result</b>.</Callout></div>
        </div>
      </Card></Reveal>

      <Reveal><Card title="Result artifacts">
        <DataTable cols={[{ key: 'n', label: 'artifact' }, { key: 'p', label: 'path', render: (r: [string, string, string]) => <code>{r[2]}</code> }, { key: 'l', label: '', render: (r: [string, string, string]) => <a href={r[1]} target="_blank" rel="noreferrer">open ↗</a> }] as Array<Col<[string, string, string]>>} rows={ARTIFACTS.map((a) => a)} />
        {meta && <p className="small muted">Last full suite: {meta.trials} trials per cell; groups: {Object.entries(meta.groups).map(([g, v]) => `${g} (${v.rows} rows, ${v.wall_seconds}s)`).join(' · ')}.</p>}
        <div className="small muted">Hardware: results were produced on a shared 24-logical-core Windows machine; memory use is small (under 200 MB per worker). The full suite runs in roughly 15–25 minutes with 6 workers.</div>
      </Card></Reveal>

      <Reveal><Card title="Figures and their sources" right={<span className="xs muted">click to enlarge</span>}>
        {idx.loading ? <SkeletonBlock rows={5} /> : idx.data?.figures?.length ? <Gallery figs={idx.data.figures} /> : <Callout kind="info">No figure manifest yet — run <code>python scripts/make_figures.py</code>.</Callout>}
      </Card></Reveal>

      <Callout kind="info" title="Benchmark licensing notes">Who&amp;When is MIT-licensed (per the conformal-attribution paper that uses it). ALFWorld: MIT (PyPI metadata). HotpotQA: CC BY-SA 4.0 (secondary sources). Verify all three against the official repositories before redistributing data.</Callout>
    </div>
  )
}
