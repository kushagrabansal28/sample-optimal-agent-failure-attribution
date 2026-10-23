import { Search } from 'lucide-react'
import { useMemo, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api, type OpenApi } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { Badge, Callout, Card, DataTable, Disclosure, Empty, ErrorBanner, PageHeader, SkeletonBlock, useDebounced, type Col } from '../ui/kit'

interface Sec { id: string; title: string; text: string; body: ReactNode }

function Hl({ text, q }: { text: string; q: string }) {
  if (!q) return <>{text}</>
  const i = text.toLowerCase().indexOf(q.toLowerCase())
  return i < 0 ? <>{text}</> : <>{text.slice(0, i)}<mark>{text.slice(i, i + q.length)}</mark>{text.slice(i + q.length)}</>
}

interface Prop { type?: string; anyOf?: Array<{ type?: string }>; minimum?: number; maximum?: number; exclusiveMinimum?: number; exclusiveMaximum?: number }
/** "≥ 0, < 1": a bound of 0 is a bound (explicit null checks, not truthiness). */
export function rangeOf(v: Prop): string {
  const lower = v.exclusiveMinimum != null ? `> ${v.exclusiveMinimum}` : v.minimum != null ? `≥ ${v.minimum}` : ''
  const upper = v.exclusiveMaximum != null ? `< ${v.exclusiveMaximum}` : v.maximum != null ? `≤ ${v.maximum}` : ''
  return [lower, upper].filter(Boolean).join(', ') || '—'
}
const typeOf = (v: Prop) => v.type ?? (v.anyOf ? v.anyOf.map((a) => a.type).filter((x) => x && x !== 'null').join(' | ') + (v.anyOf.some((a) => a.type === 'null') ? ' (optional)' : '') : '—')

function resolve(api_: OpenApi, ref?: string) { const name = ref?.split('/').pop(); return name ? api_.components?.schemas?.[name] : undefined }

function ApiReference() {
  const spec = useAsync(() => api.openapi(), [])
  const [q, setQ] = useState('')
  if (spec.loading) return <SkeletonBlock rows={6} />
  if (spec.error || !spec.data) return <ErrorBanner error={spec.error ?? new Error('no spec')} onRetry={spec.reload} />
  const eps = Object.entries(spec.data.paths).flatMap(([p, ms]) => Object.entries(ms).map(([m, d]) => ({ p, m: m.toUpperCase(), d })))
  const rows = eps.filter((e) => `${e.p} ${e.d.summary ?? ''}`.toLowerCase().includes(q.toLowerCase()))
  return (
    <div className="stack">
      <label className="row" style={{ position: 'relative', maxWidth: 360 }}><Search size={14} style={{ position: 'absolute', left: 11, color: 'var(--muted)' }} /><input className="input" type="search" style={{ paddingLeft: 32 }} placeholder="Filter endpoints" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filter endpoints" /></label>
      <div className="stack" style={{ gap: 6 }}>
        {rows.map((e) => {
          const schema = resolve(spec.data!, e.d.requestBody?.content?.['application/json']?.schema?.$ref)
          return (
            <Disclosure key={e.m + e.p} title={<span className="row" style={{ gap: 10 }}><Badge kind={e.m === 'GET' ? 'info' : 'vio'}>{e.m}</Badge><code style={{ background: 'none', border: 0 }}>{e.p}</code></span>}>
              <div className="stack" style={{ gap: 8 }}>
                {e.d.summary && <div className="small">{e.d.summary.replaceAll('_', ' ')}</div>}
                {e.d.parameters?.length ? <div className="small"><b>Query parameters:</b> {e.d.parameters.map((p) => <code key={p.name} style={{ marginRight: 6 }}>{p.name}{p.required ? '*' : ''}</code>)}</div> : null}
                {schema?.properties && <div className="tbl-wrap"><table className="tbl"><thead><tr><th>field</th><th>type</th><th>default</th><th>range</th></tr></thead><tbody>
                  {Object.entries(schema.properties).map(([k, v]) => <tr key={k}><td className="mono">{k}</td><td>{typeOf(v as Prop)}</td><td className="mono">{v.default === undefined ? '—' : JSON.stringify(v.default)}</td><td className="mono">{rangeOf(v)}</td></tr>)}</tbody></table></div>}
                <div className="xs muted">Errors (JSON <code>detail</code>): <code>422</code> for invalid input (out-of-range numbers, δ outside (0,1), unknown algorithm, oversized experiment); <code>404</code> for unknown models, groups and unknown <code>/api/…</code> paths.</div>
              </div>
            </Disclosure>
          )
        })}
        {!rows.length && <Empty title="No endpoint matches" />}
      </div>
      <p className="small muted">Generated live from <a href="/openapi.json" target="_blank" rel="noreferrer">/openapi.json</a>; interactive explorer at <a href="/api/docs" target="_blank" rel="noreferrer">/api/docs</a>.</p>
    </div>
  )
}

const GLOSSARY: Array<[string, string]> = [
  ['DFA', 'Deterministic finite automaton: a total transition function; exactly one run per word.'], ['NFA', 'Nondeterministic finite automaton: a word is accepted if some path accepts. Formal nondeterminism ≠ sampling randomness.'],
  ['ε-NFA', 'NFA with silent ε-moves; the ε-closure is applied before and after each symbol.'], ['Probabilistic automaton', 'Each (state, symbol) has a distribution over successors; a word has an acceptance probability.'],
  ['LTS', 'Labelled transition system: s —a→ s′; supports reachability and deadlock analysis.'], ['Mealy / Moore', 'Transducers: output on transitions (Mealy) or on states (Moore).'], ['PDA', 'Finite control plus a stack: models unbounded nesting of tool calls.'],
  ['Turing machine (bounded)', 'Tape + head; the simulator bounds steps and tape so it always terminates.'], ['LUCB', 'Lower-Upper Confidence Bound sampling: replay the empirically best step and its strongest challenger. The default adaptive allocation of AFCR.'], ['Successive elimination', 'Replay every surviving step equally and drop a step once its upper bound is below the best lower bound; the rule for which a sample-complexity bound is proved (Theorem 2).'], ['Stack-KL', 'The anytime-valid KL confidence sequence used by the stopping rule (Theorem 1).'], ['Arm', 'A candidate intervention point (a step of the failed trajectory).'], ['Pull', 'One real replay of an arm; returns a binary outcome.'],
  ['Repair', 'Force the reference action ρ(q) at the step, then continue under the agent’s policy.'], ['Resample', 'Redraw the action at the step from the agent’s policy (null intervention).'],
  ['μ_t', 'Probability of success after intervening at step t.'], ['δ-PAC', 'Stops almost surely and returns a wrong answer with probability ≤ δ.'], ['Abstention', 'Budget exhausted without certification; reported with the not-yet-eliminated candidates.'],
  ['Prefix reuse', 'Using one rollout as a valid sample for several arms (Theorem 3) — only with an exact (time,state,action) match.'], ['Censoring', 'Rollout counts of abstained trials stop at the cap, so means are lower bounds.'],
]
const TROUBLE: Array<[string, string]> = [
  ['The site says “API offline”.', 'Start the backend: uvicorn afcr.api.app:app --port 8000, and open the site from the same origin (or use npm run dev, which proxies /api).'],
  ['“DLL load failed … paging file is too small”.', 'Too many parallel Python workers. Use --workers 6 or fewer and set OPENBLAS_NUM_THREADS=1.'],
  ['Studio says “no saved results”.', 'Run python -m afcr.experiments.suite (about 15–25 minutes) to create results/raw and results/processed.'],
  ['The graph is empty or tiny.', 'Press the “fit to view” button, or switch the graph card to “Table”; if the model failed to load, the error banner shows the API message.'],
  ['A page is blank until I refresh.', 'Fixed: pages no longer wait for an animation to become visible. If it ever happens again, hard-refresh (Ctrl+F5) after rebuilding the site (npm run build).'],
  ['Request failed: 422.', 'The server validated your input (e.g. δ must be in (0,1), budget a positive integer). The message names the field.'],
  ['Test status shows nothing.', 'Run python scripts/run_tests_report.py to generate results/processed/test_report.json.'],
  ['The custom cursor is missing.', 'It is disabled on touch devices and when the OS asks for reduced motion — by design.'],
]

export default function Docs() {
  const [q, setQ] = useState('')
  const dq = useDebounced(q, 150).trim()
  const secs: Sec[] = useMemo(() => [
    { id: 'io', title: 'Input–output specification', text: 'input failed trajectory task specification candidate interventions replay environment evaluator delta budget seed automaton output culprit abstention confidence intervals rollouts cost stopping status guarantee traces record',
      body: <div className="grid cols-2"><div><b>Input</b><ul className="small stack" style={{ paddingLeft: 18 }}><li>Failed trajectory (states, actions, observations) and task</li><li>Candidate intervention locations and protocol (repair / resample)</li><li>Replay environment and outcome evaluator</li><li>Confidence δ ∈ (0,1), rollout budget, optional seeds, automaton configuration</li></ul></div>
        <div><b>Output</b><ul className="small stack" style={{ paddingLeft: 18 }}><li>Culprit step <i>or</i> abstention with candidate set</li><li>Per-step estimate, interval, pulls (own / shared), total rollouts and simulated steps</li><li>Stopping status; <code>guarantee_applies</code> and why not</li><li>Original and counterfactual traces; history; machine-readable record</li></ul></div></div> },
    { id: 'arch', title: 'System architecture', text: 'architecture packages automata statistics replay attribution experiments evaluation api agents benchmarks website',
      body: <div className="tbl-wrap"><table className="tbl"><thead><tr><th>package</th><th className="wrap">responsibility</th></tr></thead><tbody>{[['afcr.automata', 'DFA, NFA, ε-NFA, PA, LTS, Mealy, Moore, PDA, TM; 48/64/96-state agent automaton'], ['afcr.statistics', 'Bernoulli KL, confidence sequences (single source of bounds), complexity quantities'], ['afcr.replay', 'Replay environments (bandit arms, automaton, tool agent): pull + exact ground truth'], ['afcr.attribution', 'Targets (decision rules), allocation strategies, engine with abstention'], ['afcr.agents', 'Tool-using agent world, model-provider abstraction'], ['afcr.benchmarks', 'ALFWorld / HotpotQA adapters (interfaces; mock-tested)'], ['afcr.experiments / evaluation', 'Suite, aggregation, Wilson / bootstrap / Wilcoxon / Holm'], ['afcr.api · website', 'FastAPI endpoints · React + TypeScript single-page app']].map((r) => <tr key={r[0]}><td className="mono">{r[0]}</td><td className="wrap">{r[1]}</td></tr>)}</tbody></table></div> },
    { id: 'api', title: 'API reference', text: 'api endpoints reference openapi attribute replay trajectory experiment results export automata graph trace', body: <ApiReference /> },
    { id: 'glossary', title: 'Automata and statistics glossary', text: GLOSSARY.map((g) => g.join(' ')).join(' '), body: <DataTable cols={[{ key: 't', label: 'term', render: (r: [string, string]) => <b>{r[0]}</b> }, { key: 'd', label: 'meaning', wrap: true, render: (r: [string, string]) => r[1] }] as Array<Col<[string, string]>>} rows={GLOSSARY} /> },
    { id: 'limits', title: 'Research limitations', text: 'limitations joint causes nonstationary replay cost stochasticity reconstruction dependence benchmark generalisation finite-state abstraction',
      body: <ul className="small stack" style={{ paddingLeft: 18, margin: 0 }}><li>Single decisive cause; joint causes are out of scope.</li><li>Nonstationary policies, provider non-determinism and hidden context break A2–A4.</li><li>Exact prefix reconstruction (A1); reconstruction errors disable sharing.</li><li>Results are synthetic; ALFWorld and HotpotQA are pending.</li><li>Finite-state abstractions may miss unbounded state of real agents.</li><li>The automaton is hand-designed by the authors.</li></ul> },
    { id: 'trouble', title: 'Troubleshooting', text: TROUBLE.map((t) => t.join(' ')).join(' '), body: <div className="stack" style={{ gap: 6 }}>{TROUBLE.map(([a, b]) => <Disclosure key={a} title={a}><p style={{ margin: 0 }}>{b}</p></Disclosure>)}</div> },
  ], [])
  const texts = useRef<Record<string, string>>({})
  const [, bump] = useState(0)
  const shown = secs.filter((s) => !dq || `${s.title} ${s.text} ${texts.current[s.id] ?? ''}`.toLowerCase().includes(dq.toLowerCase()))
  return (
    <div className="stack" style={{ gap: 20 }}>
      <PageHeader eyebrow="Documentation" title="Reference" lead="Specification, architecture, API, glossary, limitations and troubleshooting. Use the search to filter sections." />
      <label className="row" style={{ position: 'relative', maxWidth: 480 }}><Search size={15} style={{ position: 'absolute', left: 12, color: 'var(--muted)' }} /><input className="input" type="search" style={{ paddingLeft: 36, height: 44, fontSize: 15 }} placeholder="Search the documentation (e.g. stopping, prefix, 422)" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search documentation" data-testid="docs-search" /></label>
      {!shown.length && <Empty title="No documentation matches your search">Try a different term.</Empty>}
      {shown.map((s) => <Card key={s.id} title={<Hl text={s.title} q={dq} />}>{dq && <p className="xs muted" style={{ marginTop: 0 }}>matches “{dq}”</p>}{s.body}</Card>)}
      {/* hidden copy of every section: its rendered text is what the search indexes (so 'LUCB' finds the API reference and glossary) */}
      <div hidden aria-hidden>{secs.map((s) => <div key={s.id} ref={(el) => { if (el && texts.current[s.id] !== el.textContent) { texts.current[s.id] = el.textContent ?? ''; bump((n) => n + 1) } }}>{s.body}</div>)}</div>
      <Callout kind="info">The mathematical statements live on the <Link to="/theory">Theory</Link> page; run instructions on <Link to="/reproducibility">Reproducibility</Link>.</Callout>
    </div>
  )
}
