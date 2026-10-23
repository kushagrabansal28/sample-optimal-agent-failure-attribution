import { ChevronLeft, ChevronRight, Pause, Play, RotateCcw, Search, Shuffle } from 'lucide-react'
import { Fragment, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { GraphCanvas, type TrailEdge } from '../graph/GraphCanvas'
import { layoutFor, type PNode } from '../graph/layout'
import { api, type ExampleCase, type GEdgeData, type GNodeData, type GraphResponse, type ModelInfo, type TapeConfig, type TraceResponse, type TraceStepData, type TrajectoryResponse } from '../lib/api'
import { fmt } from '../lib/format'
import { useAsync, useInterval, useMedia } from '../lib/hooks'
import { useToast } from '../lib/toast'
import { Badge, Button, Callout, Card, DataTable, Disclosure, ErrorBanner, PageHeader, Segmented, SelectField, SkeletonBlock, TabPanel, Tabs, Tex, Measured } from '../ui/kit'

const FAMILY: Array<{ title: string; ids: string[] }> = [
  { title: 'Main benchmark', ids: ['agent48'] },
  { title: 'Finite-state', ids: ['dfa', 'nfa', 'enfa', 'pa', 'lts'] },
  { title: 'Transducers', ids: ['mealy', 'moore'] },
  { title: 'Beyond finite-state', ids: ['pda', 'pda_typed', 'tm', 'tm_pal', 'tm_loop'] },
]
const DEFS: Record<string, string> = {
  dfa: 'M=(Q,\\Sigma,\\delta,q_0,F),\\ \\delta:Q\\times\\Sigma\\to Q\\ \\text{total}',
  nfa: '\\delta:Q\\times\\Sigma\\to 2^{Q},\\quad w\\in L\\iff \\exists\\text{ accepting path}',
  enfa: '\\delta:Q\\times(\\Sigma\\cup\\{\\varepsilon\\})\\to 2^{Q},\\quad \\mathrm{cl}(S)=\\text{states reachable by }\\varepsilon^{*}',
  pa: 'P(w)=e_{q_0}^{\\top}M_{a_1}\\cdots M_{a_n}\\mathbf 1_F,\\quad \\textstyle\\sum_{q\'}M_a[q,q\']=1',
  lts: 's\\xrightarrow{a}s\',\\quad \\text{reachability, deadlocks, accepting/rejecting states}',
  mealy: '\\lambda:Q\\times\\Sigma\\to\\Gamma\\quad(\\text{output on the transition})',
  moore: '\\lambda:Q\\to\\Gamma\\quad(\\text{output on the state; } n+1\\text{ outputs for }n\\text{ inputs})',
  pda: '(Q,\\Sigma,\\Gamma,\\delta,q_0,Z_0,F),\\ \\delta:Q\\times(\\Sigma\\cup\\{\\varepsilon\\})\\times\\Gamma\\to 2^{Q\\times\\Gamma^*}',
  pda_typed: '\\text{stack records which tool was opened; only matching } end\\_x \\text{ may pop}',
  tm: '(Q,\\Sigma,\\Gamma,\\sqcup,\\delta,q_0,q_{acc},q_{rej}),\\ \\delta:Q\\times\\Gamma\\to Q\\times\\Gamma\\times\\{L,R,S\\}',
  tm_pal: '\\{w\\in\\{a,b\\}^*: w=w^R\\}\\ \\text{decided by erasing matching ends}',
  tm_loop: '\\text{no halting state is reached: the bounded simulator reports } \\textit{unknown}, \\text{ never } \\textit{reject}',
  agent48: '\\mathcal M=(Q,\\Sigma,P,\\pi,\\rho,H),\\quad V_t(q)=\\sum_a\\pi(a|q)\\sum_{q\'}P(q\'|q,a)V_{t+1}(q\')',
}
const TEST_KEYS: Record<string, string[]> = {
  dfa: ['dfa'], nfa: ['nfa'], enfa: ['enfa'], pa: ['pa_'], lts: ['lts'], mealy: ['mealy'], moore: ['mealy'], pda: ['pda'], pda_typed: ['pda'], tm: ['turing'], tm_pal: ['turing'], tm_loop: ['turing'], agent48: ['agent48', 'exact_mu'],
}
const LEGEND_GROUPS = ['PLAN', 'OBSERVE', 'TOOL', 'MEMORY', 'VALIDATE', 'TERMINAL'].map((g) => ({ color: `var(--g-${g})`, label: g.toLowerCase() }))
const SET_MODELS = ['nfa', 'enfa']
const VIEW_LABEL: Record<string, string> = { nfa: 'NFA', enfa: 'ε-NFA', dfa: 'DFA (subset construction)' }

/** One group of highlighted edges per trace step (so step i reveals exactly the edges of steps < i). */
export function stepGroups(model: string, steps: TraceStepData[], edges: GEdgeData[]): TrailEdge[][] {
  return steps.map((s) => {
    if (s.blocked || s.next_state == null) return []
    if (Array.isArray(s.state)) {                                   // set semantics: every edge that moved the active set
      const before = s.state as string[], after = (s.next_state as string[]) ?? []
      const moved = edges.filter((e) => e.label === s.symbol && before.includes(e.source) && after.includes(e.target))
      const eps = edges.filter((e) => e.epsilon && (before.includes(e.source) || after.includes(e.source)) && after.includes(e.target))
      return [...moved, ...eps].map((e) => ({ source: e.source, target: e.target, label: e.label }))
    }
    if (typeof s.state === 'string' && typeof s.next_state === 'string') {
      let label: string | undefined = s.symbol ?? undefined
      if (model === 'mealy') label = edges.find((e) => e.source === s.state && e.target === s.next_state && String(e.label).startsWith(`${s.symbol}/`))?.label
      else if (model.startsWith('tm')) label = edges.find((e) => e.source === s.state && e.target === s.next_state && String(e.label).startsWith(`${s.symbol}/`))?.label
      else if (model.startsWith('pda')) label = undefined
      return [{ source: s.state, target: s.next_state, label }]
    }
    return []
  })
}

function StackVis({ stack }: { stack: string[] }) {
  return (
    <div className="stack-vis" aria-label={`Stack contents, top first: ${stack.join(', ') || 'empty'}`}>
      {[...stack].reverse().map((c, i) => <div key={`${i}-${c}`} className="stack-cell">{c}</div>)}
      {!stack.length && <span className="small muted">empty</span>}
    </div>
  )
}
/** The tape window is computed once for the whole run, so cells do not jump while stepping. */
function Tape({ cfg, window: win }: { cfg: TapeConfig; window: [number, number] }) {
  const cells: number[] = []
  for (let i = win[0]; i <= win[1]; i++) cells.push(i)
  return (
    <div className="tape" role="img" aria-label={`Turing machine tape: ${cells.map((i) => cfg.tape[String(i)] ?? 'blank').join(' ')}; head at cell ${cfg.head}`}>
      {cells.map((i) => <div key={i} className={`tape-cell ${i === cfg.head ? 'head' : ''}`} title={`cell ${i}`}>{cfg.tape[String(i)] ?? '_'}</div>)}
    </div>
  )
}
const tapeWindow = (cfgs: TapeConfig[]): [number, number] => {
  let lo = 0, hi = 6
  cfgs.forEach((c) => { lo = Math.min(lo, c.head - 1, ...Object.keys(c.tape).map(Number)); hi = Math.max(hi, c.head + 1, ...Object.keys(c.tape).map(Number)) })
  return [lo, hi]
}

function TransitionTable({ g }: { g: GraphResponse }) {
  if (g.transition_table) {
    const cols = Object.keys(Object.values(g.transition_table)[0] ?? {})
    return (
      <div className="tbl-wrap"><table className="tbl"><caption className="sr-only">Transition table</caption><thead><tr><th>state</th>{cols.map((a) => <th key={a}>{a}</th>)}</tr></thead>
        <tbody>{Object.entries(g.transition_table).map(([q, row]) => <tr key={q}><td className="mono">{q}{g.nodes.find((n) => n.id === q)?.label ? ` · ${g.nodes.find((n) => n.id === q)?.label}` : ''}</td>{cols.map((a) => { const v = row[a]; return <td key={a} className="mono">{Array.isArray(v) ? (v.length ? `{${v.join(', ')}}` : '∅') : String(v ?? '—')}</td> })}</tr>)}</tbody></table></div>
    )
  }
  return <DataTable cols={[{ key: 'source', label: 'from' }, { key: 'label', label: 'label' }, { key: 'target', label: 'to' }, { key: 'prob', label: 'probability', num: true, render: (e: GEdgeData) => (e.prob != null ? fmt(e.prob, 3) : '—'), sortValue: (e: GEdgeData) => e.prob ?? -1 }]} rows={g.edges} />
}

/** The result of one run, specific to the kind of machine: only machines with an acceptance notion show accepted/rejected. */
function ResultPanel({ t, idx, tapeWin, bottom }: { t: TraceResponse; idx: number; tapeWin: [number, number]; bottom: string }) {
  const k = t.kind
  const cfg = t.trace && t.trace.length ? t.trace[Math.min(idx, t.trace.length - 1)] : null
  const stack = k === 'pda' ? (idx > 0 && t.steps.length ? ((t.steps[Math.min(idx, t.steps.length) - 1].stack_after as string[]) ?? []) : [bottom]) : []
  const activeNow = SET_MODELS.includes(t.model) ? (idx === 0 ? t.initial_active : (t.steps[Math.min(idx, t.steps.length) - 1]?.next_state as string[] | undefined)) : undefined
  return (
    <div className="stack" data-testid="result-panel">
      <div className="row">
        {(k === 'dfa' || k === 'nfa' || k === 'enfa' || k === 'lts' || k === 'pda') && <Badge kind={t.accepted ? 'ok' : 'pend'}>{t.accepted ? 'accepted' : 'rejected'}</Badge>}
        {k === 'pa' && <>
          <Badge kind="vio">exact P(accept) = {fmt(t.exact_acceptance_probability ?? 0, 4)}</Badge>
          {t.monte_carlo && <Badge kind="info">Monte-Carlo {fmt(t.monte_carlo.p_hat, 3)} [{fmt(t.monte_carlo.ci_lo, 3)}, {fmt(t.monte_carlo.ci_hi, 3)}] n={t.monte_carlo.n}</Badge>}
          <Badge kind="plain">this sampled run {t.sample_blocked ? 'was blocked' : t.sample_ended_accepting ? 'ended in an accepting state' : 'ended in a non-accepting state'}</Badge>
        </>}
        {k === 'tm' && <>
          <Badge kind={t.unknown ? 'syn' : t.accepted ? 'ok' : 'pend'}>{t.unknown ? `unknown (${t.status})` : t.accepted ? 'accept' : 'reject'}</Badge>
          {!t.unknown && <Badge kind="ok">output “{t.output ?? ''}”</Badge>}
          <Badge kind="plain">{t.n_steps} steps</Badge>
        </>}
        {(k === 'mealy' || k === 'moore') && <Badge kind="plain">{t.outputs?.length ?? 0} outputs · no accepted/rejected: a transducer only produces output</Badge>}
        {t.blocked && <Badge kind="pend">blocked at {t.blocked.state} on “{t.blocked.label}”</Badge>}
      </div>
      {t.reason && <p className="small" style={{ margin: 0 }} data-testid="reject-reason"><b>Why:</b> {t.reason}</p>}
      {t.outputs && <div className="chips" aria-label="Output word">{t.outputs.slice(0, k === 'moore' ? idx + 1 : idx).map((o, i) => <span key={i} className="chip">{o}</span>)}</div>}
      {activeNow && <div className="chips"><span className="xs muted">active states:</span>{activeNow.map((a) => <span key={a} className="chip" style={{ borderColor: 'var(--amber)' }}>{a}</span>)}{!activeNow.length && <span className="chip fault">∅ (all branches dead)</span>}</div>}
      {k === 'pda' && <div><div className="xs muted" style={{ marginBottom: 6 }}>STACK (top ↑)</div><StackVis stack={stack} /></div>}
      {cfg && <div><div className="xs muted">TAPE · state <b className="mono" style={{ color: 'var(--text)' }}>{cfg.state}</b> · head at {cfg.head}</div><Tape cfg={cfg} window={tapeWin} /></div>}
      {t.note && <p className="small muted" style={{ margin: 0 }}>{t.note}</p>}
    </div>
  )
}

export default function Lab() {
  const toast = useToast()
  const [sp, setSp] = useSearchParams()
  const models = useAsync(() => api.models(), [])
  const compare = useAsync(() => api.compare(), [])
  const tests = useAsync(() => api.tests(), [])
  const small = useMedia('(max-width: 640px)')
  const model = sp.get('model') ?? 'agent48'
  const setModel = (m: string) => { const n = new URLSearchParams(sp); n.set('model', m); setSp(n, { replace: true }) }
  const [view, setView] = useState<'lts' | 'dfa' | 'nfa' | 'enfa' | 'pa'>('lts')
  const [sview, setSview] = useState<string | null>(null)
  const [nStates, setNStates] = useState('48')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<string | null>(null)
  const [tab, setTab] = useState<'def' | 'table' | 'trace' | 'branch' | 'compare' | 'tests'>('trace')
  const [mode, setMode] = useState<'graph' | 'table'>(() => (typeof window !== 'undefined' && window.matchMedia?.('(max-width: 640px)').matches ? 'table' : 'graph'))
  const [word, setWord] = useState('')
  const [trace, setTrace] = useState<TraceResponse | null>(null)
  const [traj, setTraj] = useState<TrajectoryResponse | null>(null)
  const [seed, setSeed] = useState(5)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<Error | null>(null)
  const [idx, setIdx] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<'0.5' | '1' | '2'>('1')
  const [branchAt, setBranchAt] = useState<number | null>(null)

  const info: ModelInfo | undefined = models.data?.find((m) => m.id === model)
  const isAgent = model === 'agent48'
  const isTm = model.startsWith('tm')
  const isSet = SET_MODELS.includes(model)
  const graph = useAsync<GraphResponse>(() => api.graph(model, isAgent ? { view, n_states: Number(nStates) } : sview ? { view: sview } : {}), [model, view, nStates, sview])
  const g = graph.data
  const nodes: PNode[] = useMemo(() => (g ? layoutFor(g.nodes as GNodeData[], g.edges, isAgent) : []), [g, isAgent])

  useEffect(() => { setSelected(null); setTrace(null); setTraj(null); setIdx(0); setPlaying(false); setErr(null); setBranchAt(null); setQuery('') }, [model, nStates])
  useEffect(() => { setSview(null) }, [model])
  useEffect(() => { if (info && !isAgent) setWord(info.word.join(isTm ? '' : ' ')) }, [info, model, isAgent, isTm])
  useEffect(() => { if (isAgent) void loadAgentTrace() /* eslint-disable-next-line */ }, [isAgent, nStates])

  async function loadAgentTrace(s = seed) {
    setBusy(true); setErr(null)
    try { const t = await api.trajectory({ source: 'automaton', seed: s, n_states: Number(nStates) }); setTraj(t); setIdx(0); setPlaying(false); setBranchAt(null) }
    catch (e) { setErr(e as Error); toast.push('err', (e as Error).message) } finally { setBusy(false) }
  }
  async function runTrace(w: string[] | null = null) {
    setBusy(true); setErr(null)
    try {
      const sym = w ?? (isTm ? word.replace(/\s+/g, '').split('') : word.trim().split(/\s+/).filter(Boolean))
      const t = await api.trace({ model, word: sym, seed: Date.now() % 1000 })
      setTrace(t); setIdx(t.steps.length); setPlaying(false)           // show the finished run; Play (or Restart) replays it from the start
      toast.push('ok', `Trace computed (${t.steps.length} step${t.steps.length === 1 ? '' : 's'})`)
    } catch (e) { setErr(e as Error); setTrace(null); toast.push('err', (e as Error).message) } finally { setBusy(false) }
  }
  function useExample(ex: ExampleCase) {
    setWord(ex.word.join(isTm ? '' : ' '))
    void runTrace(ex.word)
  }

  // ---- derived trail: one group of edges per step
  const agentTrail: TrailEdge[] = useMemo(() => (traj ? traj.steps.map((s) => ({ source: s.state, target: s.next_state as string, label: s.action })) : []), [traj])
  const groups = useMemo(() => (trace && g && !isAgent ? stepGroups(model, trace.steps, g.edges) : []), [trace, g, model, isAgent])
  const smallTrail = useMemo(() => groups.flat(), [groups])
  const trail = isAgent ? agentTrail : smallTrail
  const total = isAgent ? agentTrail.length : (trace?.steps.length ?? 0)
  const trailIndex = isAgent ? idx : groups.slice(0, idx).reduce((a, x) => a + x.length, 0)
  const activeSet = !isAgent && isSet && trace ? (idx === 0 ? trace.initial_active : (trace.steps[Math.min(idx, trace.steps.length) - 1]?.next_state as string[] | undefined)) : undefined
  const culprit = isAgent && traj && traj.planted_arm != null ? traj.steps[traj.planted_arm].state : null
  const branch: TrailEdge[] = useMemo(() => {
    if (!isAgent || !traj || branchAt == null || !g) return []
    const st = traj.steps[branchAt]
    return g.edges.filter((e) => e.source === st.state && e.label === st.ref_action).map((e) => ({ source: e.source, target: e.target, label: e.label }))
  }, [isAgent, traj, branchAt, g])
  const startId = g?.nodes.find((n) => n.start || n.is_initial)?.id ?? null
  const tapeWin = useMemo(() => tapeWindow(trace?.trace ?? []), [trace])

  useInterval(() => { setIdx((i) => { if (i >= total) { setPlaying(false); return i } return i + 1 }) }, playing ? 950 / Number(speed) : null)

  const selNode = g?.nodes.find((n) => n.id === selected)
  const out = g?.edges.filter((e) => e.source === selected) ?? []
  const inc = g?.edges.filter((e) => e.target === selected) ?? []
  const matches = query.trim() ? nodes.filter((n) => `${n.id} ${n.qid ?? ''} ${n.name ?? ''} ${n.label ?? ''} ${n.description ?? ''}`.toLowerCase().includes(query.trim().toLowerCase())).length : null
  const modTests = tests.data?.modules ? Object.values(tests.data.modules).flatMap((m) => m.tests).filter((t) => (TEST_KEYS[model] ?? []).some((k) => t.name.toLowerCase().includes(k))) : []

  const hasAcc = nodes.some((n) => n.accepting || n.kind === 'accepting'), hasRej = nodes.some((n) => n.rejecting || n.kind === 'rejecting')
  const legend = isAgent
    ? [...LEGEND_GROUPS, { color: 'var(--red)', label: 'fault action / decision' }, { color: 'var(--cyan)', label: 'trace' }, { color: 'var(--violet)', label: 'counterfactual branch' }, ...(view === 'dfa' ? [{ color: 'var(--surface-3)', label: 'sink (not a logical state)' }] : [])]
    : [...(hasAcc ? [{ color: 'var(--green)', label: 'accepting' }] : []), ...(hasRej ? [{ color: 'var(--red)', label: 'rejecting' }] : []), { color: 'var(--cyan)', label: isSet ? 'initial state' : 'initial / current state' },
       ...(isSet ? [{ color: 'var(--amber)', label: 'active set' }] : []), ...(nodes.some((n) => n.dead) ? [{ color: 'var(--surface-3)', label: 'dead state ∅' }] : [])]
  const viewList = g?.views ?? []

  return (
    <div className="stack" style={{ gap: 14 }}>
      <PageHeader compact eyebrow="Models of computation" title="Automata laboratory"
        lead="Pick a machine, press an example case, and watch it run on the graph. States are q0, q1, … with their meaning beside them." />
      <Card>
        {models.loading ? <SkeletonBlock rows={2} /> : models.error ? <ErrorBanner error={models.error} onRetry={models.reload} /> : (
          <div className="model-bar" role="group" aria-label="Choose a model">
            {FAMILY.map((f, fi) => (
              <Fragment key={f.title}>
                {fi > 0 && <span className="model-sep" aria-hidden />}
                {f.ids.map((id) => { const m = models.data?.find((x) => x.id === id); if (!m) return null; return (
                  <button key={id} className={`model-item ${model === id ? 'on' : ''}`} onClick={() => setModel(id)} aria-pressed={model === id} data-testid={`model-${id}`} title={f.title}>{m.name}</button>
                ) })}
              </Fragment>
            ))}
          </div>
        )}
        <div className="lab-toolbar">
          {isAgent && <>
            <div className="field"><span className="lbl">Formalism view</span>
              <Segmented value={view} onChange={setView} ariaLabel="Formalism view" options={[{ value: 'lts', label: 'LTS' }, { value: 'dfa', label: 'DFA' }, { value: 'nfa', label: 'NFA' }, { value: 'enfa', label: 'ε-NFA' }, { value: 'pa', label: 'PA' }]} /></div>
            <div style={{ width: 210 }}><SelectField label="Logical states" value={nStates} onChange={setNStates} options={[{ value: '48', label: '48 (6 groups × 8)' }, { value: '64', label: '64 (+16 benign steps)' }, { value: '96', label: '96 (+48 benign steps)' }]} /></div>
            {g?.count_logical_states != null && <Badge kind="ok">{g.count_logical_states} distinct logical states{view === 'dfa' ? ' · sink not counted' : ''}</Badge>}
          </>}
          {viewList.length > 0 && (
            <div className="field"><span className="lbl">Show as</span>
              <Segmented value={(sview ?? viewList[0]) as string} onChange={(v) => setSview(v)} ariaLabel="Machine view" options={viewList.map((v) => ({ value: v, label: VIEW_LABEL[v] ?? v }))} /></div>
          )}
          {info?.description && <p className="small muted" style={{ margin: 0, flex: 1, minWidth: 240 }} data-testid="model-description">{info.description}</p>}
        </div>
        {g?.view_note && <p className="xs muted" style={{ margin: '8px 0 0' }}>{g.view_note}</p>}
      </Card>

      <div className="lab-grid">
        <div className="stack" style={{ minWidth: 0 }}>
          <Card title={<>{info?.name ?? model}{g ? <Badge kind="info">{g.n_states} states</Badge> : null}</>} right={
            <div className="row">
              <Segmented value={mode} onChange={setMode} ariaLabel="Graph or table" options={[{ value: 'graph', label: 'Graph' }, { value: 'table', label: 'Table' }]} />
              <label className="row" style={{ position: 'relative' }}>
                <Search size={15} style={{ position: 'absolute', left: 11, color: 'var(--muted)' }} />
                <input className="input" style={{ paddingLeft: 32, width: 200 }} type="search" placeholder={isAgent ? 'Search states (q7, memory…)' : 'Search states'} value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search states" data-testid="state-search" />
                {matches != null && <span className="xs muted" style={{ marginLeft: 8 }} role="status">{matches} match{matches === 1 ? '' : 'es'}</span>}
              </label>
            </div>}>
            {graph.error ? <ErrorBanner error={graph.error} onRetry={graph.reload} /> : graph.loading || !g ? <div className="skeleton" style={{ height: small ? 300 : 560 }} /> : mode === 'table' ? (
              <TransitionTable g={g} />
            ) : (
              <GraphCanvas nodes={nodes} edges={g.edges} grouped={isAgent} selectedId={selected} onSelect={setSelected} query={query} trail={trail} trailIndex={trailIndex}
                startId={startId} activeSet={activeSet} showCurrent={!isSet} branch={branch} culprit={culprit} fitKey={`${model}-${view}-${nStates}-${sview}`} minimap legend={legend} height={small ? 380 : isAgent ? 620 : 520}
                edgeLabels={isAgent ? 'auto' : 'all'} ariaLabel={`${info?.name ?? model} state graph`} />
            )}
          </Card>

          <Card>
            <Tabs name="lab" label="Laboratory sections" value={tab} onChange={setTab} tabs={[
              { id: 'trace', label: 'Trace & playback' }, { id: 'def', label: 'Definition & semantics' }, { id: 'table', label: 'Transition table' },
              ...(isAgent ? [{ id: 'branch' as const, label: 'Counterfactual branch' }] : []), { id: 'compare', label: 'Compare models' }, { id: 'tests', label: `Test status${modTests.length ? ` (${modTests.length})` : ''}` },
            ]} />
            {tab === 'def' && info && (
              <TabPanel name="lab" id="def" className="stack">
                <Tex block>{DEFS[model] ?? ''}</Tex>
                <div className="grid cols-2">
                  {([['Acceptance / halting', info.accepts], ['Memory', info.memory], ['Nondeterminism', info.nondeterminism], ['Probability', info.probability], ['Fit for agent trajectories', info.agent_fit], ['Limits for causal attribution', info.limits]] as const).map(([k, v]) => (
                    <div key={k}><div className="xs muted" style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>{k}</div><div>{v}</div></div>
                  ))}
                </div>
                {model === 'nfa' && <Callout kind="info">Nondeterminism here is a <em>formal</em> device (“some path accepts”). It is not the sampling randomness of an LLM; for that use the probabilistic view. Use “Show as → DFA” to see the subset construction.</Callout>}
                {isTm && <Callout kind="warn">The tape and step bounds are simulator conveniences. A run that hits a bound ends “unknown”, not “rejected”, and a bounded simulator does not have the power of an unbounded machine.</Callout>}
                {isAgent && <Callout kind="info">Views: <b>LTS</b> (policy×kernel probabilities), <b>DFA</b> (most-likely successor; every other symbol goes to the drawn sink), <b>NFA</b> (all successors), <b>ε-NFA</b> (silent “heal” edges are ε-moves), <b>PA</b> (environment kernel). States are numbered q0 … q{(g?.n_states ?? 48) - 1} in definition order.</Callout>}
              </TabPanel>
            )}
            {tab === 'table' && g && <TabPanel name="lab" id="table"><TransitionTable g={g} /></TabPanel>}
            {tab === 'compare' && (
              <TabPanel name="lab" id="compare">{compare.loading ? <SkeletonBlock rows={6} /> : compare.error ? <ErrorBanner error={compare.error} onRetry={compare.reload} /> : (
                <div className="tbl-wrap"><table className="tbl"><thead><tr><th>model</th><th className="wrap">acceptance</th><th>memory</th><th className="wrap">nondeterminism</th><th>probability</th><th className="wrap">fit for agent traces</th><th className="wrap">limits for causal attribution</th></tr></thead>
                  <tbody>{compare.data?.map((c) => <tr key={c.id} style={{ background: c.id === model ? 'color-mix(in srgb, var(--blue) 10%, transparent)' : undefined }}><td><b>{c.name}</b></td><td className="wrap">{c.accepts}</td><td className="wrap">{c.memory}</td><td className="wrap">{c.nondeterminism}</td><td>{c.probability}</td><td className="wrap">{c.agent_fit}</td><td className="wrap">{c.limits}</td></tr>)}</tbody></table></div>
              )}</TabPanel>
            )}
            {tab === 'tests' && (
              <TabPanel name="lab" id="tests" className="stack">
                {tests.data && !tests.data.total ? <Callout kind="info">No test report available.</Callout> : modTests.length ? (
                  <>
                    <div className="row"><Measured /><span className="small muted">from <code>results/processed/test_report.json</code> · {tests.data?.ran_at}</span></div>
                    <div className="chips">{modTests.map((t) => <span key={t.name} className={`chip ${t.outcome === 'passed' ? 'ok' : 'fault'}`}>{t.outcome === 'passed' ? '✓' : '✗'} {t.name.replace('test_', '')}</span>)}</div>
                  </>
                ) : <Callout kind="info">No tests are mapped to this model name.</Callout>}
              </TabPanel>
            )}
            {tab === 'branch' && isAgent && (
              <TabPanel name="lab" id="branch" className="stack">
                <p className="small muted">Pick a step of the failed trajectory: the violet edge shows the <b>reference (repair) action</b> that an intervention at that step would force. Replaying from there is what the attribution engine does for every candidate.</p>
                {!traj ? <SkeletonBlock rows={3} /> : (
                  <div className="steps-scroll">
                    {traj.steps.map((s, i) => (
                      <button key={i} className={`step-card ${branchAt === i ? 'sel' : ''} ${s.is_fault ? 'fault' : ''}`} onClick={() => { setBranchAt(i); setSelected(s.state) }}>
                        <div className="t"><span>t={s.t}</span><span>μ {fmt(traj.exact_mu[i], 3)}</span></div>
                        <div className="st">{s.state}</div>
                        <div className="ac">{s.action} {s.is_fault ? '⚠' : ''}</div>
                        {s.ref_action !== s.action && <div className="ac" style={{ color: 'var(--violet)' }}>repair → {s.ref_action}</div>}
                      </button>
                    ))}
                  </div>
                )}
              </TabPanel>
            )}
            {tab === 'trace' && (
              <TabPanel name="lab" id="trace" className="stack">
                {isAgent ? (
                  <div className="row">
                    <Button onClick={() => { const s = Math.floor(Math.random() * 9999); setSeed(s); void loadAgentTrace(s) }} loading={busy} icon={<Shuffle size={15} />}>Sample another failed trajectory</Button>
                    {traj && <span className="small muted">seed {seed} · {traj.steps.length} steps · planted fault at step {traj.planted_arm != null ? traj.planted_arm + 1 : '—'} · exact baseline success {fmt(traj.baseline_success, 3)}</span>}
                  </div>
                ) : (
                  <>
                    {!!info?.examples?.length && (
                      <div>
                        <div className="xs muted" style={{ marginBottom: 6 }}>EXAMPLE CASES — press one to run it</div>
                        <div className="case-chips" role="group" aria-label="Example cases">
                          {info.examples.map((ex) => <button key={ex.label} className={`case-chip ${ex.expect}`} onClick={() => useExample(ex)} title={ex.note || undefined} data-testid="example-case">{ex.label}</button>)}
                        </div>
                      </div>
                    )}
                    <div className="row" style={{ alignItems: 'flex-end' }}>
                      <div className="field" style={{ flex: 1, minWidth: 220 }}><label htmlFor="word">Input word {isTm ? '(characters)' : '(space-separated symbols)'}</label>
                        <input id="word" className="input mono" type="text" value={word} onChange={(e) => setWord(e.target.value)} data-testid="word-input" onKeyDown={(e) => { if (e.key === 'Enter') void runTrace() }} /></div>
                      <Button variant="primary" onClick={() => runTrace()} loading={busy} data-testid="run-trace">Run trace</Button>
                    </div>
                  </>
                )}
                {err && <ErrorBanner error={err} />}
                {total > 0 && (
                  <>
                    <div className="row">
                      <Button size="sm" icon={<RotateCcw size={14} />} aria-label="Restart" onClick={() => { setIdx(0); setPlaying(false) }} />
                      <Button size="sm" icon={<ChevronLeft size={14} />} aria-label="Step back" onClick={() => setIdx((i) => Math.max(0, i - 1))} />
                      <Button size="sm" variant="primary" icon={playing ? <Pause size={14} /> : <Play size={14} />} onClick={() => { if (idx >= total) setIdx(0); setPlaying(!playing) }}>{playing ? 'Pause' : 'Play'}</Button>
                      <Button size="sm" icon={<ChevronRight size={14} />} aria-label="Step forward" onClick={() => setIdx((i) => Math.min(total, i + 1))} />
                      <Segmented value={speed} onChange={setSpeed} ariaLabel="Speed" options={[{ value: '0.5', label: '0.5×' }, { value: '1', label: '1×' }, { value: '2', label: '2×' }]} />
                      <span className="mono small muted" role="status">step {idx}/{total}</span>
                    </div>
                    <input className="range" type="range" min={0} max={total} value={idx} aria-label="Trace position" style={{ ['--p' as string]: `${(idx / total) * 100}%` }} onChange={(e) => { setIdx(Number(e.target.value)); setPlaying(false) }} />
                  </>
                )}
                {isAgent && traj && (
                  <div className="steps-scroll" aria-label="Trajectory steps">
                    {traj.steps.map((s, i) => (
                      <button key={i} className={`step-card ${i === idx - 1 ? 'sel' : ''} ${s.is_fault ? 'fault' : ''}`} onClick={() => { setIdx(i + 1); setPlaying(false); setSelected(s.state) }} style={{ opacity: i < idx ? 1 : 0.55 }}>
                        <div className="t"><span>t={s.t}</span>{s.is_fault && <span style={{ color: 'var(--red)' }}>FAULT</span>}</div>
                        <div className="st">{s.state}</div><div className="ac">{s.action}</div>
                        <div className="mubar"><i style={{ width: `${traj.exact_mu[i] * 100}%` }} /></div>
                      </button>
                    ))}
                  </div>
                )}
                {!isAgent && trace && <ResultPanel t={{ ...trace, kind: trace.kind ?? info?.kind ?? model, model: trace.model ?? model }} idx={idx} tapeWin={tapeWin} bottom={g?.stack_bottom ?? 'Z'} />}
                {model === 'enfa' && (sview ?? 'enfa') === 'enfa' && g?.closure_steps && g.closure_steps.length > 0 && <Closure steps={g.closure_steps} />}
                {model === 'mealy' && g?.witness && g.witness.length > 0 && <Callout kind="info" title="Same state, different outputs">{g.witness.slice(0, 2).map((w, i) => <div key={i} className="mono small">state <b>{w[0]}</b>: input <b>{w[1]}</b> → <b>{w[3]}</b>, input <b>{w[2]}</b> → <b>{w[4]}</b></div>)}</Callout>}
                {model === 'lts' && g?.deadlocks && <p className="xs muted" style={{ margin: 0 }}>Deadlocks (non-terminal states with no action): {g.deadlocks.length ? g.deadlocks.join(', ') : 'none'}.</p>}
                {!total && !isAgent && !err && !trace && <p className="small muted">Press an example case or <b>Run trace</b> to execute the model on the word above and animate the run on the graph.</p>}
                {!total && !isAgent && !err && trace && <p className="small muted">The empty word has no steps.</p>}
              </TabPanel>
            )}
          </Card>
        </div>

        <aside className="stack" aria-label="State details">
          <Card title="State details">
            {!selNode ? <p className="small muted">Select a state in the graph. {isAgent && 'Nodes outlined in red are decision points with planted faults.'}</p> : (
              <div className="stack" style={{ gap: 10 }} key={selNode.id}>
                <div><div className="mono" style={{ fontWeight: 700, fontSize: 15 }}>{selNode.qid ?? selNode.id}{selNode.name && selNode.name !== selNode.qid ? ` · ${selNode.name}` : ''}</div><div className="small">{selNode.label}</div></div>
                <div className="row">{selNode.group && <Badge kind="info">{String(selNode.group).toLowerCase()}</Badge>}{selNode.role && <Badge kind={selNode.role === 'decision' || selNode.role === 'fault_entry' ? 'pend' : 'plain'}>{String(selNode.role).replace('_', ' ')}</Badge>}{selNode.kind && selNode.kind !== 'nonterminal' && <Badge kind={selNode.kind === 'accepting' ? 'ok' : 'pend'}>{selNode.kind}</Badge>}{(selNode.start || selNode.is_initial) && <Badge kind="vio">initial</Badge>}{selNode.accepting && <Badge kind="ok">accepting</Badge>}{selNode.rejecting && <Badge kind="pend">rejecting</Badge>}{selNode.dead && <Badge kind="plain">dead state</Badge>}{selNode.sink && <Badge kind="plain">sink</Badge>}</div>
                {selNode.description && <p className="small" style={{ margin: 0 }}>{String(selNode.description)}</p>}
                {selNode.attribution_note && <p className="small muted" style={{ margin: 0 }}>Attribution: {String(selNode.attribution_note)}</p>}
                {selNode.ref_action && <div className="small">Reference (repair) action: <span className="chip forced">{String(selNode.ref_action)}</span></div>}
                {selNode.policy && Object.keys(selNode.policy).length > 0 && (
                  <div><div className="xs muted" style={{ marginBottom: 4 }}>POLICY π(a | q)</div>{Object.entries(selNode.policy).map(([a, p]) => <div key={a} className="small" style={{ marginBottom: 4 }}><div className="row" style={{ justifyContent: 'space-between' }}><span className="mono">{a}</span><span className="mono">{fmt(p, 2)}</span></div><div className="progress"><i style={{ width: `${p * 100}%`, background: g?.fault_symbols?.includes(a) ? 'var(--red)' : undefined }} /></div></div>)}</div>
                )}
                {selNode.output && <div className="small">Output: <span className="chip">{selNode.output}</span></div>}
                <Disclosure title={`Outgoing (${out.length}) · incoming (${inc.length})`}>
                  <div className="stack" style={{ gap: 4 }}>
                    {out.slice(0, 14).map((e, i) => <div key={i} className="mono xs">→ <b>{nameOf(g, e.target)}</b> <span className="muted">via {e.label}{e.prob != null ? ` (${fmt(e.prob, 2)})` : ''}</span></div>)}
                    {inc.slice(0, 8).map((e, i) => <div key={i} className="mono xs">← <b>{nameOf(g, e.source)}</b> <span className="muted">via {e.label}</span></div>)}
                  </div>
                </Disclosure>
              </div>
            )}
          </Card>
        </aside>
      </div>
    </div>
  )
}

function nameOf(g: GraphResponse | null | undefined, id: string) {
  const n = g?.nodes.find((x) => x.id === id)
  return n?.qid && n.qid !== id ? `${n.qid} (${id})` : id
}

function Closure({ steps }: { steps: string[][] }) {
  const [i, setI] = useState(0)
  useInterval(() => setI((x) => (x + 1) % (steps.length + 1)), 1100)
  const cur = steps[Math.min(i, steps.length - 1)]
  return (
    <Callout kind="info" title="ε-closure of q0, computed step by step">
      <div className="chips" style={{ marginTop: 6 }}>{cur.map((s) => <span key={s} className="chip" style={{ borderColor: 'var(--amber)' }}>{s}</span>)}</div>
      <div className="xs muted" style={{ marginTop: 6 }}>iteration {Math.min(i, steps.length - 1)} of {steps.length - 1}</div>
    </Callout>
  )
}

