import { Download, FlaskConical } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ComposedChart, ErrorBar, Legend as RLegend, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip as RTip, XAxis, YAxis, ZAxis, Cell } from 'recharts'
import { api, type ExpRow, type GroupResult, type PairedRow, type SummaryRow } from '../lib/api'
import { downloadText, fmt, int, label, mcolor, pct, short, toCsv } from '../lib/format'
import { useAsync, ANIMATE } from '../lib/hooks'
import { useToast } from '../lib/toast'
import { Badge, Button, Callout, Card, DataTable, Empty, ErrorBanner, Measured, NumberField, PageHeader, Segmented, SelectField, SkeletonBlock, Sym, Synthetic, TabPanel, Tabs, useFormValidity, type Col } from '../ui/kit'
import { Heatmap } from '../ui/charts'

type SR = SummaryRow & { method?: string; [k: string]: unknown }
const METHODS = ['lucb', 'lucb_prefix', 'successive_elim', 'uniform_fc', 'random_fc', 'equal_budget']
const GROUP_INFO: Record<string, { title: string; blurb: string; x?: string; xlabel?: string }> = {
  main: { title: 'Main comparison', blurb: 'Matched-confidence comparison of all strategies on the 48-state automaton and on the bandit-arm model.' },
  gap_sweep: { title: 'Gap sweep (bandit, K=8)', blurb: 'Rollouts needed as the best-vs-second gap shrinks, against the Garivier–Kaufmann lower bound.', x: 'gap', xlabel: 'best − runner-up gap' },
  K_sweep: { title: 'Number of candidates', blurb: 'Cost as the number of candidate steps K grows (gap fixed at 0.2).', x: 'K', xlabel: 'K candidate steps' },
  delta_sweep: { title: 'Confidence parameter δ', blurb: 'Rollouts and observed error among certified trials as δ varies.', x: 'delta', xlabel: 'δ' },
  stress: { title: 'Guarantee stress test', blurb: 'Very hard 2-arm instances (gap 0.06) where wrong answers are possible: is the empirical error ≤ δ?', x: 'delta', xlabel: 'δ' },
  size_sweep: { title: 'Automaton size', blurb: '48 vs 64 vs 96 logical states (longer trajectories, more harmless candidates).', x: 'n_states', xlabel: 'logical states' },
  eps_sweep: { title: 'Planted-fault probability', blurb: 'A smaller fault probability makes the planted step closer to the re-roll baseline: a harder instance.', x: 'eps_plan', xlabel: 'fault probability' },
  noise_sweep: { title: 'State-reconstruction noise (assumption A1 violated)', blurb: 'The replay context drifts from the original; prefix sharing is disabled automatically.', x: 'recon_noise', xlabel: 'reconstruction noise' },
  ablation: { title: 'Ablations', blurb: 'One factor at a time on the automaton: confidence sequence, allocation rule, sharing, candidate set, tolerance ε.' },
  budget_curve: { title: 'Accuracy vs rollout budget', blurb: 'Forced-choice accuracy when a budget B is all you have; the 90 % target is marked.', x: 'B', xlabel: 'rollout budget B' },
  toolagent: { title: 'Stage B: tool-using agent', blurb: 'Controlled agent with planted failure types; stochastic and deterministic variants.' },
  targets: { title: 'Targets: threshold rules vs the CAR-style fixed-K rule', blurb: 'AFCR with last/first-above-θ targets vs a re-implementation of the CAR locus rule (from its paper’s text, not its code).' },
}

function Tip2({ active, payload, label: lab }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string | number }) {
  if (!active || !payload?.length) return null
  return <div className="rc-tip"><b>{String(lab)}</b>{payload.filter((p) => !String(p.name).endsWith('__e')).map((p) => <div key={p.name} style={{ color: p.color }}>{label(p.name)}: <span className="mono">{typeof p.value === 'number' ? p.value.toFixed(p.value < 5 ? 3 : 0) : p.value}</span></div>)}</div>
}

/** Pivot summary rows into {x, <method>: y, <method>__e: [dlo, dhi]} for a line chart with error bars. */
function pivot(rows: SR[], x: string, y: 'mean_rollouts' | 'accuracy' | 'abstain_rate' | 'identified_error_rate', series = 'method') {
  const xs = Array.from(new Set(rows.map((r) => r[x] as number))).sort((a, b) => a - b)
  const names = Array.from(new Set(rows.map((r) => String(r[series]))))
  const data = xs.map((xv) => {
    const o: Record<string, unknown> = { x: xv }
    names.forEach((n) => {
      const r = rows.find((q) => q[x] === xv && String(q[series]) === n)
      if (!r) return
      const v = r[y] as number | null
      if (v == null) return
      o[n] = v
      if (y === 'mean_rollouts') o[`${n}__e`] = [v - r.rollouts_ci[0], r.rollouts_ci[1] - v]
      else if (y === 'accuracy') o[`${n}__e`] = [v - r.acc_ci_lo, r.acc_ci_hi - v]
      else if (y === 'identified_error_rate' && r.err_ci_lo != null && r.err_ci_hi != null) o[`${n}__e`] = [v - r.err_ci_lo, r.err_ci_hi - v]
    })
    return o
  })
  return { data, names }
}

function LineSeries({ rows, x, y, xlabel, ylabel, log, extra, yMax, refY }: { rows: SR[]; x: string; y: 'mean_rollouts' | 'accuracy' | 'abstain_rate' | 'identified_error_rate'; xlabel: string; ylabel: string; log?: boolean; extra?: Array<{ name: string; data: Array<{ x: number; v: number }>; color: string }>; yMax?: number; refY?: number }) {
  const { data, names } = useMemo(() => pivot(rows, x, y), [rows, x, y])
  const merged = useMemo(() => data.map((d) => { const o = { ...d } as Record<string, unknown>; (extra ?? []).forEach((e) => { const f = e.data.find((q) => q.x === d.x); if (f) o[e.name] = f.v }); return o }), [data, extra])
  const logX = x === 'B'
  return (
    <div style={{ height: 320 }}>
      <ResponsiveContainer>
        <LineChart data={merged} margin={{ left: 4, right: 18, top: 10, bottom: 18 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="x" type={logX ? 'number' : 'number'} scale={logX ? 'log' : 'linear'} domain={logX ? ['dataMin', 'dataMax'] : ['dataMin', 'dataMax']} ticks={Array.from(new Set(rows.map((r) => r[x] as number))).sort((a, b) => a - b)} tickLine={false} label={{ value: xlabel, position: 'insideBottom', offset: -8, fill: 'var(--muted)', fontSize: 11.5 }} />
          <YAxis scale={log ? 'log' : 'linear'} domain={log ? ['auto', 'auto'] : [0, yMax ?? 'auto']} allowDataOverflow={log} tickLine={false} axisLine={false} label={{ value: ylabel, angle: -90, position: 'insideLeft', fill: 'var(--muted)', fontSize: 11.5 }} width={58} />
          <RTip content={<Tip2 />} />
          <RLegend formatter={(v: string) => label(v)} />
          {refY != null && <ReferenceLine y={refY} stroke="var(--amber)" strokeDasharray="5 4" label={{ value: String(refY), fill: 'var(--amber)', fontSize: 11 }} />}
          {names.map((n) => <Line key={n} dataKey={n} name={n} stroke={mcolor(n)} strokeWidth={2.3} dot={{ r: 3.5 }} connectNulls isAnimationActive={ANIMATE}><ErrorBar dataKey={`${n}__e`} width={5} stroke={mcolor(n)} strokeOpacity={0.55} /></Line>)}
          {(extra ?? []).map((e) => <Line isAnimationActive={ANIMATE} key={e.name} dataKey={e.name} name={e.name} stroke={e.color} strokeDasharray="6 4" strokeWidth={2} dot={false} connectNulls />)}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function Bars({ rows, nameKey, valueKey, color, ci, fmtV, domain, ariaLabel }: { rows: SR[]; nameKey: string; valueKey: 'mean_rollouts' | 'accuracy' | 'abstain_rate'; color?: (r: SR) => string; ci?: 'rollouts' | 'acc'; fmtV?: (v: number) => string; domain?: [number, number]; ariaLabel?: string }) {
  const data = rows.map((r) => ({ name: String(r[nameKey]), v: r[valueKey] as number, e: ci === 'rollouts' ? [(r[valueKey] as number) - r.rollouts_ci[0], r.rollouts_ci[1] - (r[valueKey] as number)] : ci === 'acc' ? [r.accuracy - r.acc_ci_lo, r.acc_ci_hi - r.accuracy] : undefined, r }))
  return (
    <div style={{ height: 290 }} role="img" aria-label={ariaLabel}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: 8, right: 12, top: 10, bottom: 36 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="name" interval={0} tickFormatter={(v: string) => short(v)} tickLine={false} angle={-25} textAnchor="end" height={64} />
          <YAxis tickLine={false} axisLine={false} domain={domain} width={56} tickFormatter={fmtV} />
          <RTip content={({ active, payload }) => active && payload?.length ? <div className="rc-tip"><b>{label(String(payload[0].payload.name))}</b><div className="mono">{fmtV ? fmtV(payload[0].payload.v) : fmt(payload[0].payload.v, 2)}</div><div className="xs muted">n = {payload[0].payload.r.n}</div></div> : null} cursor={{ fill: 'rgba(148,163,184,0.08)' }} />
          <Bar dataKey="v" radius={[7, 7, 0, 0]} isAnimationActive={ANIMATE}>
            {data.map((d, i) => <Cell key={i} fill={color ? color(d.r) : mcolor(d.name)} />)}
            {ci && <ErrorBar dataKey="e" width={6} stroke="var(--text-2)" strokeOpacity={0.7} />}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function Strip({ rows, methods }: { rows: ExpRow[]; methods: string[] }) {
  const data = rows.map((r) => ({ x: methods.indexOf(r.method) + 1 + ((r.seed * 9301) % 100) / 260 - 0.19, y: Math.max(1, r.rollouts), m: r.method, ok: r.correct, a: r.abstained }))
  return (
    <div style={{ height: 290 }} role="img" aria-label="Distribution of rollouts per trial">
      <ResponsiveContainer>
        <ScatterChart margin={{ left: 0, right: 12, top: 10, bottom: 36 }}>
          <CartesianGrid vertical={false} />
          <XAxis type="number" dataKey="x" domain={[0.4, methods.length + 0.6]} ticks={methods.map((_, i) => i + 1)} tickFormatter={(v) => short(methods[Math.round(v) - 1] ?? '')} interval={0} tickLine={false} angle={-25} textAnchor="end" height={64} />
          <YAxis type="number" dataKey="y" scale="log" domain={['auto', 'auto']} tickLine={false} axisLine={false} width={56} allowDataOverflow />
          <ZAxis range={[36, 36]} />
          <RTip cursor={false} content={({ active, payload }) => active && payload?.length ? <div className="rc-tip"><b>{label(payload[0].payload.m)}</b><div className="mono">{payload[0].payload.y} rollouts</div><div className="xs muted">{payload[0].payload.a ? 'abstained' : payload[0].payload.ok ? 'correct' : 'incorrect'}</div></div> : null} />
          <Scatter data={data}>{data.map((d, i) => <Cell key={i} fill={mcolor(d.m)} fillOpacity={d.a ? 0.35 : 0.8} stroke={d.ok ? 'none' : 'var(--red)'} />)}</Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

// ================================================================== live simulation
function Live() {
  const toast = useToast()
  const [source, setSource] = useState<'bandit' | 'automaton' | 'toolagent'>('bandit')
  const [algs, setAlgs] = useState<string[]>(['lucb', 'uniform_fc', 'successive_elim'])
  const [trials, setTrials] = useState(8)
  const [K, setK] = useState(8)
  const [gap, setGap] = useState(0.2)
  const [delta, setDelta] = useState(0.1)
  const [budget, setBudget] = useState(20000)
  const [seed, setSeed] = useState(0)
  const [nStates, setNStates] = useState(48)
  const [epsPlan, setEpsPlan] = useState(0.6)
  const form = useFormValidity()
  const [out, setOut] = useState<{ rows: ExpRow[]; summary: SR[] } | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<Error | null>(null)

  async function run() {
    if (form.anyInvalid) return
    if (!algs.length) { setErr(new Error('Select at least one algorithm')); return }
    setBusy(true); setErr(null)
    try { const r = await api.experiment({ source, algorithms: algs, trials, K, gap, delta, budget, seed, n_states: nStates, eps_plan: epsPlan }); setOut({ rows: r.rows, summary: r.summary as SR[] }); toast.push('ok', `Ran ${r.rows.length} simulated trials`) }
    catch (e) { setErr(e as Error); setOut(null); toast.push('err', (e as Error).message) } finally { setBusy(false) }
  }
  const toggle = (a: string) => setAlgs((s) => (s.includes(a) ? s.filter((x) => x !== a) : [...s, a]))
  const rows = out?.rows ?? []
  const conf = useMemo(() => {
    const arms = Array.from(new Set(rows.flatMap((r) => [r.answer, r.truth]).filter((v) => v >= 0))).sort((a, b) => a - b)
    const labels = arms.map(String)
    const m = arms.map(() => arms.map(() => 0))
    rows.forEach((r) => { const i = arms.indexOf(r.truth), j = arms.indexOf(r.answer); if (i >= 0 && j >= 0) m[i][j]++ })
    return { labels, m }
  }, [rows])
  return (
    <div className="stack">
      <Card title="Configure" right={<Synthetic />}>
        <div className="grid cols-4">
          <SelectField label="Instance family" value={source} onChange={(v) => setSource(v as typeof source)} options={[{ value: 'bandit', label: 'Bandit-arm model' }, { value: 'automaton', label: '48-state automaton' }, { value: 'toolagent', label: 'Tool agent' }]} />
          <NumberField label="Trials per algorithm" value={trials} onChange={setTrials} min={1} max={60} int testId="trials" form={form} />
          <NumberField label={<>Confidence <Sym>δ</Sym></>} value={delta} onChange={setDelta} min={0} max={1} excludeMin excludeMax form={form} />
          <NumberField label="Rollout budget" value={budget} onChange={setBudget} min={100} max={100000} int form={form} />
          {source === 'bandit' && <><NumberField label="Arms K" value={K} onChange={setK} min={2} max={40} int form={form} /><NumberField label="Best−runner-up gap" value={gap} onChange={setGap} min={0} max={0.7} excludeMin excludeMax form={form} /></>}
          {source === 'automaton' && <><NumberField label="Logical states" value={nStates} onChange={setNStates} min={48} max={96} int hint="48, 64 or 96 are the built-in sizes" form={form} /><NumberField label="Fault probability" value={epsPlan} onChange={setEpsPlan} min={0} max={1} excludeMax form={form} /></>}
          <NumberField label="Base seed" value={seed} onChange={setSeed} min={0} int form={form} />
        </div>
        <div className="field" style={{ marginTop: 14 }}><span className="lbl">Algorithms</span>
          <div className="chips">{[...METHODS, 'random_budget', 'car_fixed_k', 'oracle'].map((a) => <button key={a} className={`chip ${algs.includes(a) ? 'ok' : ''}`} aria-pressed={algs.includes(a)} style={{ cursor: 'pointer', height: 30, borderColor: algs.includes(a) ? mcolor(a) : undefined }} onClick={() => toggle(a)}>{algs.includes(a) ? '✓ ' : ''}{label(a)}</button>)}</div></div>
        <div className="row" style={{ marginTop: 14 }}>
          <Button variant="primary" onClick={run} loading={busy} disabled={form.anyInvalid} icon={<FlaskConical size={16} />} data-testid="run-experiment">Run simulation</Button>
          {form.anyInvalid && <span className="err-text" role="alert">Fix the highlighted fields first.</span>}
          {out && <>
            <Button icon={<Download size={15} />} onClick={() => downloadText(toCsv(out.rows as unknown as Array<Record<string, unknown>>), 'afcr_simulation.csv', 'text/csv')} data-testid="export-csv">Export CSV</Button>
            <Button icon={<Download size={15} />} onClick={() => downloadText(JSON.stringify({ config: { source, algs, trials, K, gap, delta, budget, seed }, rows: out.rows, summary: out.summary }, null, 1), 'afcr_simulation.json', 'application/json')} data-testid="export-json">Export JSON</Button>
          </>}
        </div>
      </Card>
      {err && <ErrorBanner error={err} />}
      {busy && <Card><SkeletonBlock rows={7} /></Card>}
      {!out && !busy && !err && <Empty title="No simulation yet">Pick algorithms and press <b>Run simulation</b>. Runs happen on the server with real code; nothing here is pre-baked.</Empty>}
      {out && !busy && (
        <>
          <div className="grid cols-2">
            <Card title="Mean rollouts (95 % bootstrap CI)"><Bars rows={out.summary} nameKey="method" valueKey="mean_rollouts" ci="rollouts" fmtV={(v) => int(v)} ariaLabel="Mean rollouts per method" /></Card>
            <Card title="Accuracy (Wilson 95 %)"><Bars rows={out.summary} nameKey="method" valueKey="accuracy" ci="acc" domain={[0, 1]} fmtV={(v) => pct(v)} ariaLabel="Accuracy per method" /></Card>
          </div>
          <div className="grid cols-2">
            <Card title="Distribution of rollouts per trial" right={<span className="xs muted">hollow = abstained · red ring = wrong</span>}><Strip rows={rows} methods={algs} /></Card>
            <Card title="Attribution confusion matrix (all methods pooled)"><Heatmap labels={conf.labels} matrix={conf.m} rowTitle="true best arm" colTitle="returned arm" /></Card>
          </div>
          <Card title="Summary table">
            <DataTable cols={[{ key: 'method', label: 'method', render: (r: SR) => label(String(r.method)) }, { key: 'n', label: 'trials', num: true }, { key: 'accuracy', label: 'accuracy', num: true, render: (r: SR) => pct(r.accuracy) }, { key: 'abstain_rate', label: 'abstain', num: true, render: (r: SR) => pct(r.abstain_rate) },
              { key: 'identified_error_rate', label: 'error | certified', num: true, render: (r: SR) => (r.identified_error_rate == null ? '—' : pct(r.identified_error_rate, 1)) }, { key: 'mean_rollouts', label: 'mean rollouts', num: true, render: (r: SR) => int(r.mean_rollouts) }, { key: 'median_rollouts', label: 'median', num: true, render: (r: SR) => int(r.median_rollouts) }, { key: 'p90_rollouts', label: 'p90', num: true, render: (r: SR) => int(r.p90_rollouts) }] as Array<Col<SR>>} rows={out.summary} />
          </Card>
        </>
      )}
    </div>
  )
}

// ================================================================== saved results
function Saved({ idxGroups }: { idxGroups: string[] }) {
  const [g, setG] = useState(idxGroups.includes('main') ? 'main' : idxGroups[0])
  const sum = useAsync<GroupResult>(() => api.group(g), [g])
  const raw = useAsync(() => api.rows(g), [g])
  const rows = (sum.data?.summary ?? []) as SR[]
  const info = GROUP_INFO[g] ?? { title: g, blurb: '' }
  const num = (v: unknown) => Number(v)
  // lower bound from raw rows (gap/K sweeps)
  const lb = useMemo(() => {
    if (!raw.data || !info.x) return undefined
    const byX: Record<string, number[]> = {}
    raw.data.rows.forEach((r) => { if (r.gk_lower_bound && r.method === 'lucb') (byX[r[info.x!]] ||= []).push(Number(r.gk_lower_bound)) })
    const d = Object.entries(byX).map(([x, v]) => ({ x: Number(x), v: v.reduce((a, b) => a + b, 0) / v.length }))
    return d.length ? [{ name: 'GK lower bound (any δ-PAC)', data: d, color: '#4ade9a' }] : undefined
  }, [raw.data, info.x])
  // rollouts-to-90% for the budget curve
  const to90 = useMemo(() => {
    if (g !== 'budget_curve') return []
    return METHODS.concat(['random_budget']).filter((m) => rows.some((r) => r.method === m)).map((m) => {
      const pts = rows.filter((r) => r.method === m).sort((a, b) => num(a.B) - num(b.B))
      const hit = pts.find((r) => r.accuracy >= 0.9)
      const hitLo = pts.find((r) => r.acc_ci_lo >= 0.9)
      return { method: m, b90: hit ? num(hit.B) : null, b90lo: hitLo ? num(hitLo.B) : null }
    })
  }, [g, rows])

  return (
    <div className="stack">
      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
        {idxGroups.map((x) => <button key={x} className={`chip ${x === g ? 'ok' : ''}`} style={{ cursor: 'pointer', height: 30, borderColor: x === g ? 'var(--blue)' : undefined }} onClick={() => setG(x)} aria-pressed={x === g}>{GROUP_INFO[x]?.title ?? x}</button>)}
      </div>
      <Card title={info.title} right={<div className="row"><Measured /><Synthetic />
        <a className="btn sm" href={api.csvUrl(g)} download={`${g}.csv`} style={{ textDecoration: 'none' }}><Download size={14} /> raw CSV</a></div>}>
        <p className="small muted" style={{ marginTop: 0 }}>{info.blurb} <span className="mono">({sum.data?.n_trials_rows ?? '…'} trials in <code>results/raw/{g}.csv</code>)</span></p>
        {sum.error ? <ErrorBanner error={sum.error} onRetry={sum.reload} /> : sum.loading ? <SkeletonBlock rows={7} /> : (
          <div className="stack">
            {g === 'main' && <MainView rows={rows} />}
            {['gap_sweep', 'K_sweep', 'size_sweep', 'eps_sweep'].includes(g) && info.x && (
              <div className="grid cols-2">
                <div><div className="small muted">Mean rollouts to certify (log scale; bars: 95 % bootstrap CI)</div><LineSeries rows={rows} x={info.x} y="mean_rollouts" xlabel={info.xlabel!} ylabel="rollouts" log extra={lb} /></div>
                <div><div className="small muted">Abstention rate (budget exhausted)</div><LineSeries rows={rows} x={info.x} y="abstain_rate" xlabel={info.xlabel!} ylabel="abstain" yMax={1} /></div>
              </div>
            )}
            {['delta_sweep', 'stress'].includes(g) && <DeltaView rows={rows} />}
            {g === 'noise_sweep' && <NoiseView rows={rows} />}
            {g === 'budget_curve' && (
              <div className="stack">
                <LineSeries rows={rows} x="B" y="accuracy" xlabel="rollout budget B (log)" ylabel="accuracy" yMax={1} refY={0.9} />
                <div className="tbl-wrap"><table className="tbl"><thead><tr><th>method</th><th style={{ textAlign: 'right' }}>smallest B with accuracy ≥ 90 % (point estimate)</th><th style={{ textAlign: 'right' }}>…with Wilson lower bound ≥ 90 %</th></tr></thead>
                  <tbody>{to90.map((r) => <tr key={r.method}><td>{label(r.method)}</td><td className="n">{r.b90 ?? 'not reached'}</td><td className="n">{r.b90lo ?? 'not reached'}</td></tr>)}</tbody></table></div>
                <Callout kind="info">“90 % average attribution accuracy” is an <b>empirical target</b> on this grid of budgets; it is not the (1−δ) guarantee of the stopping rule, and the two are not interchangeable.</Callout>
              </div>
            )}
            {g === 'ablation' && <AblationView rows={rows} />}
            {['toolagent', 'targets'].includes(g) && <GenericView rows={rows} keys={g === 'toolagent' ? ['variant'] : ['target']} />}
            <details className="disc"><summary className="disc-trigger" style={{ cursor: 'pointer' }}>Full summary table</summary>
              <div style={{ padding: 12 }}>
                <DataTable cols={[...Object.keys(rows[0] ?? {}).filter((k) => !['n', 'accuracy', 'acc_ci_lo', 'acc_ci_hi', 'abstain_rate', 'identified_error_rate', 'err_ci_lo', 'err_ci_hi', 'mean_rollouts', 'median_rollouts', 'p90_rollouts', 'rollouts_ci'].includes(k)).map((k) => ({ key: k, label: k })),
                  { key: 'n', label: 'n', num: true }, { key: 'accuracy', label: 'accuracy', num: true, render: (r: SR) => fmt(r.accuracy, 3) }, { key: 'abstain_rate', label: 'abstain', num: true, render: (r: SR) => fmt(r.abstain_rate, 3) },
                  { key: 'identified_error_rate', label: 'err|cert', num: true, render: (r: SR) => fmt(r.identified_error_rate, 3) }, { key: 'mean_rollouts', label: 'mean', num: true, render: (r: SR) => int(r.mean_rollouts) }, { key: 'median_rollouts', label: 'median', num: true, render: (r: SR) => int(r.median_rollouts) }] as Array<Col<SR>>} rows={rows} />
              </div>
            </details>
          </div>
        )}
      </Card>
    </div>
  )
}

function MainView({ rows }: { rows: SR[] }) {
  const auto = rows.filter((r) => r.kind === 'automaton')
  const order = ['oracle', 'lucb_prefix', 'lucb', 'successive_elim', 'uniform_fc', 'random_fc', 'equal_budget', 'lucb_naive_share', 'car_fixed_k']
  const A = order.map((m) => auto.find((r) => r.method === m)).filter(Boolean) as SR[]
  const B = rows.filter((r) => r.kind === 'bandit')
  return (
    <div className="stack">
      <h4 style={{ fontFamily: 'var(--font-display)' }}>48-state automaton</h4>
      <div className="grid cols-2">
        <div><div className="small muted">Mean rollouts (censored at the budget cap for abstained trials)</div><Bars rows={A.filter((r) => r.method !== 'oracle')} nameKey="method" valueKey="mean_rollouts" ci="rollouts" fmtV={(v) => int(v)} ariaLabel="Mean rollouts, automaton" /></div>
        <div><div className="small muted">Share of trials that ended in abstention</div><Bars rows={A.filter((r) => r.method !== 'oracle')} nameKey="method" valueKey="abstain_rate" domain={[0, 1]} fmtV={(v) => pct(v)} ariaLabel="Abstention rate" /></div>
      </div>
      <Callout kind="warn" title="Reading this chart honestly">Means include trials that stopped at the budget cap, so uniform/random numbers understate their true cost. <b>LUCB + naive sharing</b> is the invalid negative control (and equal_budget never stops early by design).</Callout>
      <DataTable cols={[{ key: 'method', label: 'method', render: (r: SR) => label(String(r.method)) }, { key: 'n', label: 'n', num: true }, { key: 'accuracy', label: 'accuracy [Wilson 95%]', render: (r: SR) => `${pct(r.accuracy)} [${pct(r.acc_ci_lo)}, ${pct(r.acc_ci_hi)}]` }, { key: 'abstain_rate', label: 'abstain', num: true, render: (r: SR) => pct(r.abstain_rate) },
        { key: 'identified_error_rate', label: 'error | certified', num: true, render: (r: SR) => (r.identified_error_rate == null ? '—' : pct(r.identified_error_rate, 1)) }, { key: 'mean_rollouts', label: 'mean rollouts', num: true, render: (r: SR) => int(r.mean_rollouts) }, { key: 'median_rollouts', label: 'median', num: true, render: (r: SR) => int(r.median_rollouts) }] as Array<Col<SR>>} rows={A} />
      <h4 style={{ fontFamily: 'var(--font-display)' }}>Bandit-arm model (K = 8)</h4>
      <div className="grid cols-2">
        {[0.1, 0.2].map((gp) => <div key={gp}><div className="small muted">gap = {gp}</div><Bars rows={B.filter((r) => Math.abs(num(r.gap) - gp) < 1e-9 && !['oracle', 'equal_budget'].includes(String(r.method)))} nameKey="method" valueKey="mean_rollouts" ci="rollouts" fmtV={(v) => int(v)} /></div>)}
      </div>
    </div>
  )
}
const num = (v: unknown) => Number(v)

function DeltaView({ rows }: { rows: SR[] }) {
  const data = rows.map((r) => ({ delta: num(r.delta), err: r.identified_error_rate ?? 0, e: r.err_ci_lo != null && r.err_ci_hi != null && r.identified_error_rate != null ? [r.identified_error_rate - r.err_ci_lo, r.err_ci_hi - r.identified_error_rate] : [0, 0], rollouts: r.mean_rollouts, n: r.n, abst: r.abstain_rate })).sort((a, b) => a.delta - b.delta)
  return (
    <div className="grid cols-2">
      <div><div className="small muted">Observed error among certified trials vs the allowed δ</div>
        <div style={{ height: 300 }}><ResponsiveContainer><ComposedChart data={data} margin={{ left: 0, right: 16, top: 10, bottom: 18 }}><CartesianGrid vertical={false} /><XAxis dataKey="delta" type="number" domain={[0, 'dataMax']} tickLine={false} label={{ value: 'δ', position: 'insideBottom', offset: -8, fill: 'var(--muted)' }} /><YAxis domain={[0, 'auto']} tickLine={false} axisLine={false} width={50} />
          <RTip content={({ active, payload }) => active && payload?.length ? <div className="rc-tip"><b>δ = {payload[0].payload.delta}</b><div>observed error {pct(payload[0].payload.err, 2)} (n={payload[0].payload.n})</div></div> : null} />
          <ReferenceLine segment={[{ x: 0, y: 0 }, { x: Math.max(...data.map((d) => d.delta)), y: Math.max(...data.map((d) => d.delta)) }]} stroke="var(--amber)" strokeDasharray="5 4" label={{ value: 'error = δ', fill: 'var(--amber)', fontSize: 11, position: 'insideTopLeft' }} />
          <Line isAnimationActive={ANIMATE} dataKey="err" stroke="var(--red)" strokeWidth={2.4} dot={{ r: 4, fill: 'var(--red)' }}><ErrorBar dataKey="e" width={5} stroke="var(--red)" strokeOpacity={0.55} /></Line></ComposedChart></ResponsiveContainer></div></div>
      <div><div className="small muted">Mean rollouts (log)</div>
        <div style={{ height: 300 }}><ResponsiveContainer><LineChart data={data} margin={{ left: 0, right: 16, top: 10, bottom: 18 }}><CartesianGrid vertical={false} /><XAxis dataKey="delta" type="number" domain={[0, 'dataMax']} tickLine={false} /><YAxis scale="log" domain={['auto', 'auto']} tickLine={false} axisLine={false} width={56} /><RTip content={<Tip2 />} /><Line isAnimationActive={ANIMATE} dataKey="rollouts" name="mean rollouts" stroke="var(--blue)" strokeWidth={2.4} dot={{ r: 4 }} /></LineChart></ResponsiveContainer></div></div>
      <div style={{ gridColumn: '1 / -1' }}><Callout kind="info">Points <b>below</b> the dashed line are consistent with Theorem 1. This is a check for implementation errors, not a proof: the stack bound is conservative, so errors are typically far below δ — which is why the stress instances (2 arms, gap 0.06) are included.</Callout></div>
    </div>
  )
}

function NoiseView({ rows }: { rows: SR[] }) {
  return (
    <div className="grid cols-2">
      <div><div className="small muted">Accuracy against the <b>noisy replay-context</b> argmax (the estimand actually being sampled)</div><LineSeries rows={rows.map((r) => ({ ...r, method: 'lucb_prefix' }))} x="recon_noise" y="accuracy" xlabel="reconstruction noise" ylabel="accuracy" yMax={1} /></div>
      <div><div className="small muted">Abstention rate</div><LineSeries rows={rows.map((r) => ({ ...r, method: 'lucb_prefix' }))} x="recon_noise" y="abstain_rate" xlabel="reconstruction noise" ylabel="abstain" yMax={1} /></div>
      <div style={{ gridColumn: '1 / -1' }}><Callout kind="warn" title="Assumption A1 is violated here">With noise the replay starts from a perturbed state, so the target changes (the replay-context μ′ differs from the true μ) and prefix sharing is disabled. Accuracy is measured against μ′ — the guarantee concerns the replay model, not the original run.</Callout></div>
    </div>
  )
}

function AblationView({ rows }: { rows: SR[] }) {
  const factors = Array.from(new Set(rows.map((r) => String(r.factor))))
  return (
    <div className="stack">
      {factors.map((f) => {
        const rs = rows.filter((r) => r.factor === f)
        return (
          <div key={f}>
            <h4 style={{ fontFamily: 'var(--font-display)', textTransform: 'capitalize' }}>{f}</h4>
            <div className="grid cols-2">
              <Bars rows={rs.map((r) => ({ ...r, method: String(r.level) }))} nameKey="method" valueKey="mean_rollouts" ci="rollouts" fmtV={(v) => int(v)} color={(r) => ({ naive: '#ff6b7a', valid: '#35d6e0', none: '#5b9dff' } as Record<string, string>)[String(r.level)] ?? mcolor(String(r.level))} />
              <Bars rows={rs.map((r) => ({ ...r, method: String(r.level) }))} nameKey="method" valueKey="abstain_rate" domain={[0, 1]} fmtV={(v) => pct(v)} color={() => 'var(--violet)'} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function GenericView({ rows, keys }: { rows: SR[]; keys: string[] }) {
  return (
    <DataTable cols={[...keys.map((k) => ({ key: k, label: k, wrap: true })), { key: 'method', label: 'method', render: (r: SR) => label(String(r.method)) }, { key: 'n', label: 'n', num: true }, { key: 'accuracy', label: 'accuracy [Wilson 95%]', render: (r: SR) => `${pct(r.accuracy)} [${pct(r.acc_ci_lo)}, ${pct(r.acc_ci_hi)}]` }, { key: 'abstain_rate', label: 'abstain', num: true, render: (r: SR) => pct(r.abstain_rate) }, { key: 'mean_rollouts', label: 'mean rollouts', num: true, render: (r: SR) => int(r.mean_rollouts) }] as Array<Col<SR>>} rows={rows} />
  )
}

function Stats({ paired }: { paired: PairedRow[] | null }) {
  if (!paired) return <Empty title="No paired statistics">Run the suite first.</Empty>
  return (
    <div className="stack">
      <Callout kind="info" title="How these are computed">Trials are paired by instance (same seed, same failed trajectory). For each pair: mean difference in rollouts with a 2000-resample bootstrap CI, ratio of means, and a two-sided Wilcoxon signed-rank test. The four p-values are corrected together with <b>Holm–Bonferroni</b>. Rollouts are censored at the budget cap for abstained trials, so differences are conservative.</Callout>
      <DataTable cols={[{ key: 'cmp', label: 'comparison', render: (r: PairedRow) => <><b>{label(r.b)}</b> vs <b>{label(r.a)}</b></> }, { key: 'n', label: 'pairs', num: true }, { key: 'ratio', label: 'times fewer rollouts', num: true, render: (r: PairedRow) => (r.ratio == null ? '—' : `${r.ratio.toFixed(2)}×`) },
        { key: 'mean_diff', label: 'mean diff [95% CI]', render: (r: PairedRow) => (r.mean_diff == null || !r.ci ? '—' : `${int(r.mean_diff)} [${int(r.ci[0])}, ${int(r.ci[1])}]`) },
        { key: 'p', label: 'p (Wilcoxon)', num: true, render: (r: PairedRow) => (r.p == null ? '—' : r.p < 0.001 ? '<0.001' : r.p.toFixed(3)) }, { key: 'p_holm', label: 'p (Holm)', num: true, render: (r: PairedRow) => (r.p_holm == null ? '—' : r.p_holm < 0.001 ? '<0.001' : r.p_holm.toFixed(3)) },
        { key: 'reject', label: 'significant @ 0.05', render: (r: PairedRow) => (r.reject_holm_0_05 == null ? '—' : r.reject_holm_0_05 ? <Badge kind="ok">yes</Badge> : <Badge kind="plain">no</Badge>) }] as Array<Col<PairedRow>>} rows={paired} />
      <p className="small muted">“times fewer rollouts” = (rollouts of the method after “vs”) ÷ (rollouts of the method before it). For example 1.79× on “Uniform vs LUCB” means LUCB needed 1.79 times fewer rollouts than Uniform on the same trajectories.</p>
    </div>
  )
}

export default function Studio() {
  const [tab, setTab] = useState<'live' | 'saved' | 'stats'>('saved')
  const idx = useAsync(() => api.resultsIndex(), [])
  const groups = (idx.data?.groups ?? []).slice().sort((a, b) => Object.keys(GROUP_INFO).indexOf(a) - Object.keys(GROUP_INFO).indexOf(b))
  return (
    <div className="stack" style={{ gap: 20 }}>
      <PageHeader eyebrow="Reproducible experiments" title="Experiment studio" lead="Run fresh simulations or explore the saved experiment suite. Charts are drawn from raw result files; accuracy intervals are Wilson, rollout intervals are bootstrap." right={<Synthetic />} />
      <Tabs name="studio" label="Experiment studio sections" value={tab} onChange={setTab} tabs={[{ id: 'saved', label: 'Saved results' }, { id: 'live', label: 'Run simulation' }, { id: 'stats', label: 'Paired statistics' }]} />
      {tab === 'live' && <TabPanel name="studio" id="live"><Live /></TabPanel>}
      {tab === 'saved' && <TabPanel name="studio" id="saved">{idx.loading ? <SkeletonBlock rows={8} /> : idx.error ? <ErrorBanner error={idx.error} onRetry={idx.reload} /> : groups.length ? <Saved idxGroups={groups} /> : <Empty title="No saved results">Run <code>python -m afcr.experiments.suite</code> to create them.</Empty>}</TabPanel>}
      {tab === 'stats' && <TabPanel name="studio" id="stats">{idx.loading ? <SkeletonBlock rows={5} /> : <Stats paired={idx.data?.paired ?? null} />}</TabPanel>}
    </div>
  )
}
