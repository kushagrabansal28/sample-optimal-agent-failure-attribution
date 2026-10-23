import { motion } from 'framer-motion'
import { ANIMATE } from '../lib/hooks'
import { FlaskConical, Play, Shuffle, Sigma } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Area, CartesianGrid, ComposedChart, Line, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip as RTip, XAxis, YAxis } from 'recharts'
import { api, type EstimateResponse, type ReplayResponse, type TrajectoryResponse } from '../lib/api'
import { fmt } from '../lib/format'
import { useToast } from '../lib/toast'
import { Badge, Button, Callout, Card, Disclosure, ErrorBanner, NumberField, PageHeader, Segmented, SkeletonBlock, SliderField, Switch, Synthetic, Tex, useFormValidity } from '../ui/kit'
import { CIBar } from '../ui/charts'

type Source = 'automaton' | 'toolagent'
interface ReplayBody { source: Source; seed: number; eps_plan: number; intervention: 'repair' | 'resample'; deterministic: boolean }

function ReplayCompare({ r, arm }: { r: ReplayResponse; arm: number }) {
  const cf = r.counterfactual
  const diverge = r.original.slice(arm).findIndex((s, i) => cf.path[i] && (cf.path[i].action !== s.action || cf.path[i].state !== s.state))
  return (
    <div className="grid cols-2">
      <div>
        <div className="row" style={{ marginBottom: 8 }}><b>Original run</b><Badge kind="pend">failure</Badge></div>
        <div className="stack" style={{ gap: 5 }}>
          {r.original.map((s, i) => (
            <div key={i} className="row" style={{ opacity: i < arm ? 0.4 : 1, gap: 6 }}>
              <span className="mono xs muted" style={{ width: 28 }}>t={s.t}</span>
              <span className={`chip ${s.is_fault ? 'fault' : ''}`} style={{ outline: i === arm ? '2px solid var(--blue)' : undefined }}>{s.state}</span><span className="chip">{s.action}</span>
            </div>
          ))}
        </div>
      </div>
      <div>
        <div className="row" style={{ marginBottom: 8 }}><b>Counterfactual replay</b><Badge kind={cf.success ? 'ok' : 'pend'}>{cf.success ? 'success' : 'failure'}</Badge>{cf.timed_out && <Badge kind="syn">timed out</Badge>}</div>
        <div className="stack" style={{ gap: 5 }}>
          <div className="small muted">prefix t=1…{arm} is reproduced exactly, then:</div>
          {cf.path.map((s, i) => {
            const diff = diverge >= 0 && i >= diverge
            return (
              <motion.div key={i} initial={{ x: 10 }} animate={{ x: 0 }} transition={{ delay: Math.min(i * 0.04, 0.8) }} className="row" style={{ gap: 6 }}>
                <span className="mono xs muted" style={{ width: 28 }}>t={s.t}</span>
                <span className={`chip ${s.is_fault ? 'fault' : ''}`} style={{ borderColor: diff ? 'var(--violet)' : undefined }}>{s.state}</span>
                <span className={`chip ${s.forced ? 'forced' : ''}`}>{s.action}{s.forced ? ' · forced' : ''}</span>
                {s.note && <span className="xs muted">{s.note}</span>}
              </motion.div>
            )
          })}
          <div className="small">→ terminal <b>{cf.terminal ?? 'timeout'}</b>{cf.answer !== undefined && cf.gold !== undefined && <> · answer {String(cf.answer)} vs gold {cf.gold}</>}</div>
        </div>
      </div>
    </div>
  )
}

export default function Explorer() {
  const toast = useToast()
  const [sp] = useSearchParams()
  const [source, setSource] = useState<Source>('automaton')
  const [seed, setSeed] = useState(5)
  const [eps, setEps] = useState(0.6)
  const [interv, setInterv] = useState<'repair' | 'resample'>('repair')
  const [det, setDet] = useState(false)
  const form = useFormValidity()
  // The trajectory on screen is tied to the exact parameters that produced it: replays and estimates use THESE, not the form.
  const [loaded, setLoaded] = useState<{ body: ReplayBody; traj: TrajectoryResponse } | null>(null)
  const traj = loaded?.traj ?? null
  const [sel, setSel] = useState<number | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [err, setErr] = useState<Error | null>(null)
  const [replay, setReplay] = useState<ReplayResponse | null>(null)
  const [est, setEst] = useState<EstimateResponse | null>(null)
  const [n, setN] = useState(300)
  const [replaySeed, setReplaySeed] = useState(0)

  const body: ReplayBody = { source, seed, eps_plan: eps, intervention: interv, deterministic: det }
  const stale = !!loaded && JSON.stringify(loaded.body) !== JSON.stringify(body)
  async function load() {
    if (form.anyInvalid) return
    setBusy('load'); setErr(null); setReplay(null); setEst(null)
    try { const b = body; const t = await api.trajectory(b); setLoaded({ body: b, traj: t }); setSel(t.planted_arm ?? t.argmax_arm); toast.push('ok', `Sampled a failed trajectory with ${t.steps.length} steps`) }
    catch (e) { setErr(e as Error); setLoaded(null); toast.push('err', (e as Error).message) } finally { setBusy(null) }
  }
  async function doReplay() {
    if (sel == null || !loaded) return
    setBusy('replay'); setErr(null)
    try { setReplay(await api.replay({ ...loaded.body, arm: sel, replay_seed: replaySeed })); setReplaySeed((s) => s + 1) }
    catch (e) { setErr(e as Error); toast.push('err', (e as Error).message) } finally { setBusy(null) }
  }
  async function doEstimate() {
    if (sel == null || !loaded || form.anyInvalid) return
    setBusy('est'); setErr(null)
    try { setEst(await api.estimate({ ...loaded.body, arm: sel, n })) }
    catch (e) { setErr(e as Error); toast.push('err', (e as Error).message) } finally { setBusy(null) }
  }

  useEffect(() => { if (sp.get('autoload')) void load() /* eslint-disable-next-line */ }, [])
  const data = useMemo(() => traj?.steps.map((s, i) => ({ t: s.t, mu: traj.exact_mu[i], state: s.state, action: s.action, fault: s.is_fault })) ?? [], [traj])
  const step = sel != null && traj ? traj.steps[sel] : null

  return (
    <div className="stack" style={{ gap: 20 }}>
      <PageHeader eyebrow="Counterfactual replay" title="Trajectory explorer"
        lead="Sample a failed run, pick a step, intervene on it and re-simulate the continuation. A replay is a real intervention under the same stochastic policy — not an edited label." right={<Synthetic />} />
      <div className="grid" style={{ gridTemplateColumns: 'minmax(250px, 300px) minmax(0, 1fr)', alignItems: 'start' }}>
        <Card title="Instance" className="sticky-card">
          <div className="stack">
            <div className="field"><span className="lbl">Agent</span><Segmented<Source> value={source} onChange={(v) => { setSource(v); setLoaded(null); setReplay(null); setEst(null) }} ariaLabel="Agent" options={[{ value: 'automaton', label: '48-state automaton' }, { value: 'toolagent', label: 'Tool agent' }]} /></div>
            <NumberField label="Seed" value={seed} onChange={setSeed} min={0} int hint="Deterministic: same seed, same trajectory" form={form} />
            {source === 'automaton' && <SliderField label="Fault probability (planning)" value={eps} onChange={setEps} min={0.1} max={0.9} step={0.05} format={(v) => v.toFixed(2)} />}
            {source === 'toolagent' && <Switch checked={det} onChange={setDet} label="Deterministic variant" />}
            <div className="field"><span className="lbl">Intervention</span><Segmented value={interv} onChange={setInterv} ariaLabel="Intervention" options={[{ value: 'repair', label: 'Repair' }, { value: 'resample', label: 'Resample' }]} /></div>
            <p className="xs muted" style={{ margin: 0 }}>{interv === 'repair' ? 'Repair forces the reference action ρ(q) at the chosen step, then the agent continues on its own.' : 'Resample redraws the action from the agent’s own policy (CAR’s null intervention).'}</p>
            <Button variant="primary" onClick={load} loading={busy === 'load'} disabled={form.anyInvalid} icon={<Shuffle size={15} />} data-testid="sample-traj">Sample failed trajectory</Button>
            {form.anyInvalid && <span className="err-text" role="alert">Fix the highlighted field first.</span>}
          </div>
        </Card>

        <div className="stack" style={{ minWidth: 0 }}>
          {err && <ErrorBanner error={err} />}
          {stale && <Callout kind="warn" title="The form has changed"><span data-testid="stale-notice">The trajectory below was sampled with different settings (seed {loaded?.body.seed}, {loaded?.body.intervention}). Replays and estimates keep using <b>that</b> trajectory; press “Sample failed trajectory” to apply the new settings.</span></Callout>}
          {!traj && !busy && <Card><div className="empty"><Sigma size={28} /><b style={{ color: 'var(--text-2)' }}>No trajectory yet</b><span className="small">Choose an agent and press “Sample failed trajectory”.</span></div></Card>}
          {busy === 'load' && <Card><SkeletonBlock rows={6} /></Card>}
          {traj && (
            <>
              <Card title="Exact intervention value of each step" right={<div className="row"><Badge kind="vio">dynamic programming</Badge><Badge kind="syn">synthetic</Badge></div>}>
                <div className="chart-box" style={{ height: 260 }} data-testid="mu-chart">
                  <ResponsiveContainer>
                    <ComposedChart data={data} margin={{ left: -10, right: 12, top: 10 }} onClick={(e) => { const p = (e as { activeTooltipIndex?: number } | null)?.activeTooltipIndex; if (typeof p === 'number') setSel(p) }}>
                      <defs><linearGradient id="gmu" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#5b9dff" stopOpacity={0.4} /><stop offset="100%" stopColor="#5b9dff" stopOpacity={0} /></linearGradient></defs>
                      <CartesianGrid vertical={false} />
                      <XAxis dataKey="t" tickLine={false} axisLine={false} label={{ value: 'step t', position: 'insideBottom', offset: -2, fill: 'var(--muted)', fontSize: 11 }} />
                      <YAxis domain={[0, 1]} tickLine={false} axisLine={false} />
                      <RTip content={({ active, payload }) => active && payload?.length ? <div className="rc-tip"><b>t = {payload[0].payload.t}</b><div className="mono">{payload[0].payload.state}</div><div className="mono muted">{payload[0].payload.action}</div><div>μ<sub>t</sub> = {fmt(payload[0].payload.mu, 3)}</div></div> : null} />
                      <ReferenceLine y={traj.baseline_success} stroke="var(--amber)" strokeDasharray="5 4" label={{ value: `baseline ${fmt(traj.baseline_success, 2)}`, fill: 'var(--amber)', fontSize: 11, position: 'insideTopRight' }} />
                      <Area dataKey="mu" stroke="none" fill="url(#gmu)" isAnimationActive={ANIMATE} />
                      <Line isAnimationActive={ANIMATE} dataKey="mu" stroke="var(--blue)" strokeWidth={2.4} dot={{ r: 3.5, fill: 'var(--blue)' }} activeDot={{ r: 6 }} />
                      {traj.planted_arm != null && <ReferenceDot x={traj.planted_arm + 1} y={traj.exact_mu[traj.planted_arm]} r={9} fill="none" stroke="var(--red)" strokeWidth={2.5} label={{ value: 'planted cause', position: 'top', fill: 'var(--red)', fontSize: 11 }} />}
                      {sel != null && <ReferenceDot x={sel + 1} y={traj.exact_mu[sel]} r={6} fill="var(--cyan)" stroke="var(--bg)" strokeWidth={2} />}
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <p className="small muted" style={{ marginBottom: 0 }}>μ<sub>t</sub> is the probability of success if step <i>t</i> is intervened and the agent continues. Steps before the planted cause score only slightly above the baseline: re-running re-rolls the fault (CAR’s “run-forward confound”). The exact argmax is step <b>{traj.argmax_arm + 1}</b>{traj.planted_arm != null && <> and the planted cause is step <b>{traj.planted_arm + 1}</b></>}.</p>
              </Card>

              <Card title="Failed trajectory — choose a step">
                <div className="steps-scroll" role="listbox" aria-label="Trajectory steps">
                  {traj.steps.map((s, i) => (
                    <button key={i} role="option" aria-selected={sel === i} className={`step-card ${sel === i ? 'sel' : ''} ${s.is_fault ? 'fault' : ''}`} onClick={() => { setSel(i); setReplay(null); setEst(null) }}>
                      <div className="t"><span>t={s.t}</span><span>{traj.planted_arm === i ? '★ planted' : s.is_fault ? 'FAULT' : ''}</span></div>
                      <div className="st">{s.state}</div><div className="ac">{s.action}</div>
                      <div className="mubar"><i style={{ width: `${traj.exact_mu[i] * 100}%` }} /></div>
                    </button>
                  ))}
                </div>
              </Card>

              {step && sel != null && (
                <Card title={<>Intervene at step {step.t}</>} icon={<FlaskConical size={18} />}>
                  <div className="grid cols-2">
                    <div className="stack">
                      <div><div className="xs muted">PREFIX STATE (restored exactly)</div><div className="mono" style={{ fontSize: 16, fontWeight: 700 }}>{step.state}</div>{step.group && <Badge kind="info">{step.group.toLowerCase()}</Badge>}{step.memory && <div className="chips" style={{ marginTop: 6 }}>{Object.entries(step.memory).map(([k, v]) => <span key={k} className="chip">{k}={v == null ? '∅' : v}</span>)}</div>}</div>
                      <div className="row"><div><div className="xs muted">ORIGINAL ACTION</div><span className={`chip ${step.is_fault ? 'fault' : ''}`}>{step.action}</span></div><div><div className="xs muted">{interv === 'repair' ? 'INTERVENTION (forced)' : 'INTERVENTION'}</div><span className="chip forced">{interv === 'repair' ? step.ref_action : 'redraw from π'}</span></div></div>
                      {step.note && <p className="small muted" style={{ margin: 0 }}>{step.note}</p>}
                      <div className="row">
                        <Button onClick={doReplay} loading={busy === 'replay'} icon={<Play size={15} />} data-testid="run-replay">Run one counterfactual replay</Button>
                      </div>
                      <div className="row" style={{ alignItems: 'flex-end' }}>
                        <div style={{ width: 130 }}><NumberField label="Replays n" value={n} onChange={setN} min={1} max={5000} int form={form} /></div>
                        <Button variant="primary" onClick={doEstimate} loading={busy === 'est'} disabled={form.anyInvalid} data-testid="run-estimate">Estimate μ<sub>t</sub></Button>
                      </div>
                    </div>
                    <div className="stack">
                      {est ? (
                        <div className="stack">
                          <div className="row"><b>Estimate from {est.n} replays</b><Badge kind="syn">synthetic</Badge></div>
                          <CIBar mean={est.mean} lo={est.ci_lo} hi={est.ci_hi} exact={est.exact_mu} baseline={traj.baseline_success} />
                          <div className="small">μ̂ = <b>{fmt(est.mean, 3)}</b> · 95 % Wilson [{fmt(est.ci_lo, 3)}, {fmt(est.ci_hi, 3)}] · exact μ = <b>{fmt(est.exact_mu, 3)}</b></div>
                          <div className="small">Effect vs baseline: Δ̂ = <b style={{ color: est.mean - traj.baseline_success > 0 ? 'var(--green)' : 'var(--red)' }}>{est.mean - traj.baseline_success >= 0 ? '+' : ''}{fmt(est.mean - traj.baseline_success, 3)}</b> (CI [{fmt(est.ci_lo - traj.baseline_success, 3)}, {fmt(est.ci_hi - traj.baseline_success, 3)}])</div>
                          <p className="xs muted" style={{ margin: 0 }}>{est.note}</p>
                        </div>
                      ) : <Callout kind="info" title="One replay is one sample">A single replay shows what <em>can</em> happen. To compare steps you need an estimate with uncertainty — or let the adaptive algorithm decide how many replays each step needs (Attribution dashboard).</Callout>}
                    </div>
                  </div>
                  {replay && <><div className="divider" /><ReplayCompare r={replay} arm={sel} /></>}
                </Card>
              )}
              {loaded && <div className="row"><Link to={`/dashboard?autorun=1&seed=${loaded.body.seed}&source=${loaded.body.source}&eps_plan=${loaded.body.eps_plan}&intervention=${loaded.body.intervention}`} className="btn" style={{ textDecoration: 'none' }} data-testid="attribute-this">Attribute this trajectory adaptively →</Link><span className="small muted">opens the Attribution dashboard with these exact settings</span></div>}
              <Disclosure title="Genuine intervention vs relabelling a trace">
                <p>Editing the label of a step in the log changes nothing about what the agent would do. Here the continuation is <b>re-executed</b> from the restored prefix state under the same stochastic policy (<Tex>{'\\pi'}</Tex>) after forcing or redrawing one action. That is why different replays of the same step can end differently, and why μ<sub>t</sub> has to be <em>estimated</em>.</p>
              </Disclosure>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
