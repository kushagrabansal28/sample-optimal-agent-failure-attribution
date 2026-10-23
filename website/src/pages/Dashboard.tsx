import { motion } from 'framer-motion'
import { ChevronLeft, ChevronRight, Download, Gauge, Pause, Play, RotateCcw, Scale, XCircle } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type AttributeRequest, type AttributionResult } from '../lib/api'
import { downloadText, fmt, int, label, mcolor, toCsv } from '../lib/format'
import { useInterval } from '../lib/hooks'
import { useToast } from '../lib/toast'
import { Badge, Button, Callout, Card, CountUp, DataTable, Disclosure, ErrorBanner, NumberField, PageHeader, Segmented, SelectField, SkeletonBlock, SliderField, Stat, Switch, Sym, Synthetic, Tex, useFormValidity, type Col } from '../ui/kit'
import { ForestPlot, type ForestRow } from '../ui/charts'

const ALGS = [
  { value: 'lucb', label: 'LUCB (adaptive)' }, { value: 'successive_elim', label: 'Successive elimination' }, { value: 'uniform_fc', label: 'Uniform (same stopping rule)' },
  { value: 'random_fc', label: 'Random (same stopping rule)' }, { value: 'equal_budget', label: 'Equal budget (no stopping)' },
]
type Source = 'automaton' | 'toolagent' | 'bandit'
type ArmStatus = 'above' | 'below' | 'undecided'

export default function Dashboard() {
  const toast = useToast()
  const [sp] = useSearchParams()
  const form = useFormValidity()
  const [source, setSource] = useState<Source>(() => (['automaton', 'toolagent', 'bandit'].includes(sp.get('source') ?? '') ? (sp.get('source') as Source) : 'automaton'))
  const [seed, setSeed] = useState(() => (sp.get('seed') !== null && Number.isInteger(Number(sp.get('seed'))) && Number(sp.get('seed')) >= 0 ? Number(sp.get('seed')) : 5))
  const [alg, setAlg] = useState('lucb')
  const [share, setShare] = useState('none')
  const [target, setTarget] = useState('argmax')
  const [eps, setEps] = useState(0)
  const [theta, setTheta] = useState(0.5)
  const [delta, setDelta] = useState(0.1)
  const [budget, setBudget] = useState(20000)
  const [conf, setConf] = useState('stack_kl')
  const [interv, setInterv] = useState(() => (sp.get('intervention') === 'resample' ? 'resample' : 'repair'))
  const [cand, setCand] = useState('all')
  const [noise, setNoise] = useState(0)
  const [epsPlan, setEpsPlan] = useState(() => (Number(sp.get('eps_plan')) >= 0.2 && Number(sp.get('eps_plan')) <= 0.9 ? Number(sp.get('eps_plan')) : 0.6))
  const [K, setK] = useState(8)
  const [gap, setGap] = useState(0.2)
  const [det, setDet] = useState(false)
  const [reveal, setReveal] = useState(true)

  // A result always stays tied to the exact request that produced it (the form may change afterwards).
  const [run, setRun] = useState<{ req: AttributeRequest; res: AttributionResult } | null>(null)
  const res = run?.res ?? null
  const lastReq = run?.req ?? null
  const [uni, setUni] = useState<AttributionResult | null>(null)
  const [busy, setBusy] = useState<'run' | 'cmp' | null>(null)
  const [err, setErr] = useState<Error | null>(null)
  const [pos, setPos] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<'1' | '4' | '16'>('4')
  const [selArm, setSelArm] = useState<number | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const req = (over: Partial<AttributeRequest> = {}): AttributeRequest => ({
    source, seed, algorithm: alg, share, target, eps, theta, delta, budget, confidence: conf, intervention: interv, candidates: cand,
    reconstruct_noise: noise, eps_plan: epsPlan, K, gap, deterministic: det, history: true, ...over,
  })
  const formKey = JSON.stringify(req())
  const stale = !!lastReq && JSON.stringify({ ...lastReq }) !== formKey

  async function execute(kind: 'run' | 'cmp') {
    if (form.anyInvalid) return
    abortRef.current?.abort()
    const ctl = new AbortController(); abortRef.current = ctl
    setBusy(kind); setErr(null)
    try {
      if (kind === 'run') {
        const r0 = req()
        setUni(null)
        const r = await api.attribute(r0, ctl.signal)
        setRun({ req: r0, res: r }); setPos(Math.max(0, r.history.length - 1)); setPlaying(false); setSelArm(null)
        toast.push(r.status === 'identified' ? 'ok' : 'info', r.status === 'identified' ? `Identified after ${int(r.total_rollouts)} rollouts` : `Budget exhausted after ${int(r.total_rollouts)} rollouts — abstaining`)
      } else if (lastReq) {
        // the identical instance and seed of the run on screen, not whatever the form says now
        setUni(await api.attribute({ ...lastReq, algorithm: 'uniform_fc', share: 'none', history: false }, ctl.signal))
      }
    } catch (e) {
      if ((e as { status?: number }).status === -1) toast.push('info', 'Run cancelled')
      else { setErr(e as Error); toast.push('err', (e as Error).message) }
    } finally { if (abortRef.current === ctl) { setBusy(null); abortRef.current = null } }
  }
  const doRun = () => void execute('run')
  const doCompare = () => void execute('cmp')
  const cancel = () => abortRef.current?.abort()
  useEffect(() => { if (sp.get('autorun')) void execute('run') /* eslint-disable-next-line */ }, [])
  useInterval(() => setPos((p) => { const m = (res?.history.length ?? 1) - 1; if (p >= m) { setPlaying(false); return p } return Math.min(m, p + 1) }), playing ? 700 / Number(speed) : null)

  const H = res?.history ?? []
  const hasHist = H.length > 0 && !!H[Math.min(pos, H.length - 1)].mean
  const cur = hasHist ? H[Math.min(pos, H.length - 1)] : null
  const atEnd = !cur || pos >= H.length - 1
  const mean = (atEnd || !cur ? res?.means : cur.mean) ?? []
  const lo = (atEnd || !cur ? res?.lo : cur.lo) ?? []
  const hi = (atEnd || !cur ? res?.hi : cur.hi) ?? []
  const counts = (atEnd || !cur ? res?.counts : cur.counts) ?? []

  const tname = String(res?.target.name ?? 'argmax')
  const isThreshold = tname === 'first_above' || tname === 'last_above'
  const th = Number(res?.target.theta ?? NaN)
  const tEps = Number(res?.target.eps ?? 0) || 0
  const truth = res?.ground_truth.true_means ?? []

  const stats = useMemo(() => {
    if (!res || !mean.length || isThreshold) return null
    const idx = mean.map((_, i) => i).filter((i) => res.eligible[i])
    if (!idx.length) return null
    const h = idx.reduce((a, b) => (mean[b] > mean[a] ? b : a), idx[0])
    const rest = idx.filter((i) => i !== h)
    const l = rest.length ? rest.reduce((a, b) => (hi[b] > hi[a] ? b : a), rest[0]) : null
    return { h, l, margin: l == null ? 1 : lo[h] + tEps - hi[l] }
  }, [res, mean, lo, hi, isThreshold, tEps])

  /** Threshold targets: every step is certified above θ, certified below θ, or still undecided. */
  const armStatus: ArmStatus[] = useMemo(() => (res && isThreshold ? mean.map((_, i) => (lo[i] >= th ? 'above' : hi[i] < th ? 'below' : 'undecided')) : []), [res, mean, lo, hi, isThreshold, th])
  const trueThresholdAnswer = useMemo(() => {
    if (!isThreshold) return null
    const idx = truth.map((v, i) => (v >= th ? i : -1)).filter((i) => i >= 0)
    return idx.length ? (tname === 'first_above' ? idx[0] : idx[idx.length - 1]) : -1
  }, [isThreshold, truth, th, tname])

  const rows: ForestRow[] = res ? res.labels.map((lab, i) => ({
    label: lab, mean: mean[i] ?? 0, lo: lo[i] ?? 0, hi: hi[i] ?? 1, n: counts[i] ?? 0, truth: truth[i],
    tag: res.selected === i && atEnd ? 'best' : stats?.h === i && !atEnd ? 'best' : stats?.l === i ? 'challenger' : res.ground_truth.planted_arm === i ? 'planted' : null,
    dim: !res.eligible[i],
  })) : []

  const ranking = res ? res.labels.map((lab, i) => ({ i, lab, n: res.counts[i], own: res.own_pulls[i], shr: res.shared_obs[i], mean: res.means[i], lo: res.lo[i], hi: res.hi[i], truth: truth[i] })) : []
  type RankRow = (typeof ranking)[number]
  const cols: Array<Col<RankRow>> = [
    { key: 'lab', label: 'candidate step' }, { key: 'n', label: 'observations', num: true }, { key: 'own', label: 'own pulls', num: true }, { key: 'shr', label: 'shared', num: true },
    { key: 'mean', label: 'mean', num: true, render: (r) => fmt(r.mean, 3) }, { key: 'ci', label: '95/δ interval', render: (r) => `[${fmt(r.lo, 3)}, ${fmt(r.hi, 3)}]`, sortValue: (r) => r.lo },
    ...(reveal ? [{ key: 'truth', label: 'true μ', num: true, render: (r: RankRow) => fmt(r.truth, 3) }, { key: 'in', label: 'truth in CI', render: (r: RankRow) => (r.truth >= r.lo - 1e-9 && r.truth <= r.hi + 1e-9 ? <Badge kind="ok">yes</Badge> : <Badge kind="pend">no</Badge>), sortValue: (r: RankRow) => (r.truth >= r.lo - 1e-9 && r.truth <= r.hi + 1e-9 ? 1 : 0) }] : []),
  ]
  const answer = res?.answer ?? null
  const correct = res && !isThreshold && answer != null ? truth[answer] >= Math.max(...truth) - tEps - 1e-12
    : res && isThreshold ? (res.certified_none ? trueThresholdAnswer === -1 : answer != null ? answer === trueThresholdAnswer : null) : null
  const budgetUsed = res && lastReq ? (res.total_rollouts / lastReq.budget) * 100 : 0
  const strategyLabel = res ? label(res.strategy === 'lucb' && res.share_mode === 'valid' ? 'lucb_prefix' : res.strategy) : ''

  const exportJson = () => res && lastReq && downloadText(JSON.stringify({ request: lastReq, result: res }, null, 1), 'afcr_attribution.json', 'application/json')
  const exportCsv = () => res && downloadText(toCsv(ranking.map((r) => ({ step: r.lab, observations: r.n, own_pulls: r.own, shared: r.shr, mean: r.mean, lo: r.lo, hi: r.hi, true_mu: r.truth }))), 'afcr_ranking.csv', 'text/csv')

  return (
    <div className="stack" style={{ gap: 20 }}>
      <PageHeader eyebrow="Adaptive fixed-confidence replay" title="Attribution dashboard"
        lead="Run the actual algorithm on a failed trajectory, watch the confidence intervals tighten round by round, and see exactly why it stopped — or why it refused to." right={<Synthetic />} />
      <div className="dash-grid">
        <Card title="Configuration" className="sticky-card">
          <div className="stack" style={{ gap: 13 }}>
            <div className="field"><span className="lbl">Instance</span><Segmented<Source> value={source} onChange={setSource} ariaLabel="Instance source" options={[{ value: 'automaton', label: 'Automaton' }, { value: 'toolagent', label: 'Tool agent' }, { value: 'bandit', label: 'Arms' }]} /></div>
            <NumberField label="Seed" value={seed} onChange={setSeed} min={0} int form={form} />
            {source === 'automaton' && <SliderField label="Planted fault probability" value={epsPlan} onChange={setEpsPlan} min={0.2} max={0.9} step={0.05} format={(v) => v.toFixed(2)} />}
            {source === 'bandit' && <div className="grid cols-2"><NumberField label="Arms K" value={K} onChange={setK} min={2} max={60} int form={form} /><NumberField label="Gap" value={gap} onChange={setGap} min={0} max={0.7} excludeMin excludeMax step={0.05} form={form} /></div>}
            {source === 'toolagent' && <Switch checked={det} onChange={setDet} label="Deterministic variant" />}
            <SelectField label="Algorithm" value={alg} onChange={setAlg} options={ALGS} />
            <SelectField label="Prefix sharing" value={share} onChange={setShare} options={[{ value: 'none', label: 'Off' }, { value: 'valid', label: 'Valid reuse (Theorem 3)' }, { value: 'naive', label: 'Naive (invalid — negative control)' }]} hint={share === 'naive' ? 'Credits every later arm with the outcome: statistically invalid.' : share === 'valid' ? 'Only exact (time,state,action) matches are shared.' : undefined} />
            <SelectField label="Target" value={target} onChange={setTarget} options={[{ value: 'argmax', label: 'Best repair step (argmax-ε)' }, { value: 'first_above', label: 'Earliest step ≥ θ (AgenTracer)' }, { value: 'last_above', label: 'Latest step ≥ θ (CAR locus)' }]} />
            {target === 'argmax' ? <NumberField label={<>Tolerance <Sym>ε</Sym></>} value={eps} onChange={setEps} min={0} max={0.5} hint="ε = 0 certifies a unique best step" form={form} /> : <NumberField label={<>Threshold <Sym>θ</Sym></>} value={theta} onChange={setTheta} min={0} max={1} form={form} />}
            <div className="grid cols-2"><NumberField label={<>Confidence <Sym>δ</Sym></>} value={delta} onChange={setDelta} min={0} max={1} excludeMin excludeMax testId="delta" form={form} /><NumberField label="Rollout budget" value={budget} onChange={setBudget} min={1} max={300000} int testId="budget" form={form} /></div>
            <SelectField label="Confidence sequence" value={conf} onChange={setConf} options={[{ value: 'stack_kl', label: 'Stack-KL (ours, proved)' }, { value: 'stack_hoeffding', label: 'Stack-Hoeffding' }, { value: 'kl_lucb_rate', label: 'KL-LUCB rate (K&K 2013)' }, { value: 'wilson_fixed', label: 'Wilson (non-sequential!)' }]} hint={conf === 'wilson_fixed' ? 'Not anytime-valid: the δ-guarantee will be reported as not applying.' : conf === 'kl_lucb_rate' ? 'Proven for independent arms only; combine with sharing off.' : undefined} />
            {source === 'automaton' && <><div className="grid cols-2"><SelectField label="Intervention" value={interv} onChange={setInterv} options={[{ value: 'repair', label: 'Repair' }, { value: 'resample', label: 'Resample' }]} /><SelectField label="Candidates" value={cand} onChange={setCand} options={[{ value: 'all', label: 'All steps' }, { value: 'decision', label: 'Decision states' }]} /></div>
              <SliderField label="State-reconstruction noise" value={noise} onChange={setNoise} min={0} max={0.6} step={0.05} format={(v) => v.toFixed(2)} /></>}
            <div className="row">
              <Button variant="primary" onClick={doRun} loading={busy === 'run'} disabled={form.anyInvalid} icon={<Gauge size={16} />} data-testid="run-attribution">Run attribution</Button>
              {busy === 'run' && <Button onClick={cancel} icon={<XCircle size={15} />} data-testid="cancel-attribution">Cancel</Button>}
            </div>
            {form.anyInvalid && <span className="err-text" role="alert" data-testid="form-invalid">Fix the highlighted fields before running.</span>}
          </div>
        </Card>

        <div className="stack" style={{ minWidth: 0 }}>
          {err && <ErrorBanner error={err} onRetry={doRun} />}
          {!res && busy !== 'run' && !err && (
            <Card><div className="empty"><Gauge size={30} /><b style={{ color: 'var(--text-2)' }}>No run yet</b><span className="small">Configure on the left and press <b>Run attribution</b>. Values come straight from the algorithm.</span></div></Card>
          )}
          {busy === 'run' && <Card><SkeletonBlock rows={8} /></Card>}
          {res && lastReq && busy !== 'run' && (
            <>
              <p className="mono xs muted" style={{ margin: 0 }} data-testid="run-summary">
                this run: {lastReq.source} · seed {lastReq.seed} · {label(res.strategy)} · {tname}{isThreshold ? ` θ=${th}` : tEps ? ` ε=${tEps}` : ''} · δ {lastReq.delta} · budget {int(lastReq.budget)}
              </p>
              {stale && <Callout kind="warn">The configuration on the left has changed since this run. The results below still show the earlier run; press <b>Run attribution</b> to update them.</Callout>}
              <div className="kpis">
                <Card><div className="stat"><span className="l">Outcome</span><span className="v" style={{ fontSize: 22 }}>{res.status === 'identified' ? (res.certified_none ? 'none qualifies' : 'culprit certified') : res.status === 'budget_exhausted' ? 'abstained' : res.status.replaceAll('_', ' ')}</span>
                  <span className="s">{answer != null ? <>answer: <b>{res.labels[answer]}</b> {correct != null && reveal && <Badge kind={correct ? 'ok' : 'pend'}>{correct ? (isThreshold ? `matches exact ${tname === 'first_above' ? 'first' : 'last'} step ≥ θ` : 'matches exact argmax') : (isThreshold ? 'differs from exact threshold answer' : 'differs from exact argmax')}</Badge>}</> : res.certified_none && reveal && correct != null ? <>no step qualifies <Badge kind={correct ? 'ok' : 'pend'}>{correct ? 'matches the exact answer' : 'differs from the exact answer'}</Badge></> : 'no answer'}</span></div></Card>
                <Card><Stat label="Rollouts" value={res.total_rollouts} sub={`${int(res.total_steps)} simulated steps · budget ${int(lastReq.budget)}`} /></Card>
                <Card><Stat label="Shared observations" value={res.shared_obs.reduce((a, b) => a + b, 0)} sub={res.share_mode === 'valid' ? 'valid prefix reuse' : res.share_mode === 'naive' ? 'INVALID naive sharing' : 'sharing off'} /></Card>
                <Card><div className="stat"><span className="l">δ-guarantee</span><span className="v" style={{ fontSize: 22, color: res.guarantee_applies ? 'var(--green)' : 'var(--amber)' }}>{res.guarantee_applies ? 'applies' : 'does not apply'}</span><span className="s xs">{res.guarantee_note}</span></div></Card>
              </div>
              {res.status === 'budget_exhausted' && <Callout kind="warn" title="Abstention, not a verdict">The budget ran out before the stopping rule fired. The provisional best guess is <b>{res.provisional != null ? res.labels[res.provisional] : '—'}</b>; candidates not yet eliminated: {res.candidate_set.map((c) => res.labels[c]).join(', ') || '—'}. A timeout is not a δ-PAC event.</Callout>}
              {res.share_mode === 'naive' && <Callout kind="err" title="Naive sharing is statistically invalid">Each rollout was credited to every later step regardless of whether it visited that step’s state. The guarantee is off and the estimates are biased — this mode exists only as a negative control.</Callout>}
              {!res.sharing_valid && res.share_mode === 'none' && lastReq.share === 'valid' && <Callout kind="warn">Valid sharing was requested but the environment does not satisfy its conditions (e.g. state-reconstruction noise), so sharing was disabled.</Callout>}

              <Card title="Candidate steps and their confidence intervals" right={<div className="row"><Switch checked={reveal} onChange={setReveal} label="Reveal ground truth" /><Synthetic />
                <Button size="sm" icon={<Download size={14} />} onClick={exportJson} data-testid="export-attribution-json">Export JSON</Button>
                <Button size="sm" icon={<Download size={14} />} onClick={exportCsv} data-testid="export-attribution-csv">Ranking CSV</Button></div>}>
                {hasHist ? (
                  <div className="stack" style={{ gap: 8 }}>
                    <div className="row">
                      <Button size="sm" icon={<RotateCcw size={14} />} aria-label="Restart" onClick={() => { setPos(0); setPlaying(false) }} />
                      <Button size="sm" icon={<ChevronLeft size={14} />} aria-label="Previous round" onClick={() => setPos((p) => Math.max(0, p - 1))} />
                      <Button size="sm" variant="primary" icon={playing ? <Pause size={14} /> : <Play size={14} />} onClick={() => { if (pos >= H.length - 1) setPos(0); setPlaying(!playing) }}>{playing ? 'Pause' : 'Replay run'}</Button>
                      <Button size="sm" icon={<ChevronRight size={14} />} aria-label="Next round" onClick={() => setPos((p) => Math.min(H.length - 1, p + 1))} />
                      <Segmented value={speed} onChange={setSpeed} ariaLabel="Speed" options={[{ value: '1', label: '1×' }, { value: '4', label: '4×' }, { value: '16', label: '16×' }]} />
                      <span className="mono small muted">round {cur?.round ?? res.rounds} · {int(cur ? cur.pulls_before : res.total_rollouts)} rollouts so far</span>
                    </div>
                    <input className="range" type="range" min={0} max={H.length - 1} value={pos} aria-label="History position" style={{ ['--p' as string]: `${(pos / Math.max(1, H.length - 1)) * 100}%` }} onChange={(e) => { setPos(Number(e.target.value)); setPlaying(false) }} />
                  </div>
                ) : <p className="small muted">No per-round history was recorded (too few rounds).</p>}
                <ForestPlot rows={rows} showTruth={reveal} selected={selArm} onSelect={setSelArm} threshold={isThreshold && Number.isFinite(th) ? th : undefined} />
                <div className="legend" style={{ marginTop: 6 }}>
                  <span><i style={{ background: 'var(--cyan)' }} />best</span><span><i style={{ background: 'var(--amber)' }} />{isThreshold ? 'threshold θ' : 'strongest challenger'}</span><span><i style={{ background: 'var(--red)' }} />planted cause</span><span><i style={{ background: '#fff' }} />true μ (diamond)</span><span>bars at right: observations</span>
                </div>
                {cur && <p className="mono xs muted" style={{ marginBottom: 0 }}>pulled {JSON.stringify(cur.arms.map((a) => res.labels[a]?.split(':')[0]))} → outcomes {JSON.stringify(cur.outcomes)}{Object.keys(cur.shared).length ? ` · shared to ${Object.keys(cur.shared).length} other arms` : ''}{(cur.suggested ?? []).length ? ` · ${strategyLabel} would pull next ${JSON.stringify((cur.suggested ?? []).map((a) => res.labels[a]?.split(':')[0]))}` : ''}</p>}
              </Card>

              <div className="grid cols-2">
                <Card title="Stopping rule" icon={<Scale size={18} />}>
                  {isThreshold ? (
                    <div className="stack" data-testid="threshold-panel">
                      <Tex block>{tname === 'first_above' ? '\\text{earliest } t \\text{ with } \\mu_t\\ge\\theta,\\ \\text{stop when every step is certified above or below }\\theta' : '\\text{latest } t \\text{ with } \\mu_t\\ge\\theta,\\ \\text{stop when every step is certified above or below }\\theta'}</Tex>
                      <div className="chips">
                        {armStatus.map((s, i) => <span key={i} className={`chip ${s === 'above' ? 'ok' : s === 'below' ? '' : 'fault'}`} title={`${res.labels[i]}: ${s}`}>{res.labels[i].split(':')[0]} {s === 'above' ? '≥ θ ✓' : s === 'below' ? '< θ ✓' : '?'}</span>)}
                      </div>
                      <div className="small muted">{armStatus.filter((s) => s === 'undecided').length} of {armStatus.length} steps still undecided. θ = {th}.</div>
                      <div><div className="row small" style={{ justifyContent: 'space-between' }}><span>budget used</span><b className="mono"><CountUp value={budgetUsed} decimals={0} suffix="%" /></b></div><div className="progress"><i style={{ width: `${Math.min(100, budgetUsed)}%` }} /></div></div>
                    </div>
                  ) : stats ? (
                    <div className="stack">
                      <Tex block>{'\\text{stop when}\\ \\ \\mathrm{lo}_h+\\varepsilon\\;\\ge\\;\\max_{a\\neq h}\\mathrm{hi}_a'}</Tex>
                      <div className="small">best <b>{res.labels[stats.h].split(':')[0]}</b>: lo = <b>{fmt(lo[stats.h], 3)}</b>{stats.l != null && <> · strongest challenger <b>{res.labels[stats.l].split(':')[0]}</b>: hi = <b>{fmt(hi[stats.l], 3)}</b></>}</div>
                      <div><div className="row small" style={{ justifyContent: 'space-between' }}><span>separation margin lo<sub>h</sub> + ε − hi<sub>ℓ</sub></span><b className="mono" style={{ color: stats.margin >= 0 ? 'var(--green)' : 'var(--amber)' }}>{fmt(stats.margin, 3)}</b></div>
                        <div className="progress"><i style={{ width: `${Math.max(2, Math.min(100, (1 + stats.margin) * 50))}%`, background: stats.margin >= 0 ? 'var(--green)' : undefined }} /></div>
                        <div className="xs muted">{stats.margin >= 0 ? 'positive margin: the rule is satisfied' : 'negative margin: intervals still overlap'}</div></div>
                      <div><div className="row small" style={{ justifyContent: 'space-between' }}><span>budget used</span><b className="mono"><CountUp value={budgetUsed} decimals={0} suffix="%" /></b></div><div className="progress"><i style={{ width: `${Math.min(100, budgetUsed)}%` }} /></div></div>
                    </div>
                  ) : <p className="muted small">—</p>}
                </Card>
                <Card title="Compare with uniform allocation" right={<Button size="sm" onClick={doCompare} loading={busy === 'cmp'} data-testid="compare-uniform">Run uniform on this instance</Button>}>
                  {!uni ? <p className="small muted">Runs <b>uniform_fc</b> (round-robin, <em>same</em> stopping rule and δ) on the identical instance and seed of the run above, so the rollout counts are directly comparable.</p> : (
                    <div className="stack">
                      {[{ n: strategyLabel, v: res.total_rollouts, st: res.status }, { n: label('uniform_fc'), v: uni.total_rollouts, st: uni.status }].map((x, i) => (
                        <div key={i}><div className="row small" style={{ justifyContent: 'space-between' }}><span>{x.n} <span className="muted">({x.st.replace('_', ' ')})</span></span><b className="mono">{int(x.v)}</b></div>
                          <div className="progress"><motion.i initial={false} animate={{ width: `${(x.v / Math.max(res.total_rollouts, uni.total_rollouts, 1)) * 100}%` }} style={{ background: mcolor(i ? 'uniform_fc' : 'lucb') }} /></div></div>
                      ))}
                      <p className="small muted" style={{ margin: 0 }}>{uni.total_rollouts > res.total_rollouts ? `Uniform used ${(uni.total_rollouts / Math.max(res.total_rollouts, 1)).toFixed(2)}× as many rollouts` : 'No saving on this instance'}{uni.status === 'budget_exhausted' ? ' (uniform hit the budget cap: its count is a lower bound)' : ''}. One instance is an anecdote; see the Experiment studio for distributions.</p>
                    </div>
                  )}
                </Card>
              </div>

              <Card title="Candidate ranking">
                <DataTable cols={cols} rows={ranking} rowKey={(r) => String(r.i)} onRowClick={(r) => setSelArm(r.i)} selected={(r) => r.i === selArm} />
              </Card>
              {res.trajectory && (
                <Disclosure title={`Original failed trajectory (${res.trajectory.length} steps)`}>
                  <div className="chips">{res.trajectory.map((s) => <span key={s.t} className={`chip ${s.is_fault ? 'fault' : ''}`}>{s.t}:{s.state}·{s.action}</span>)}</div>
                </Disclosure>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
