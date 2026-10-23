import { motion } from 'framer-motion'
import { BookMarked, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { Badge, Callout, Card, Disclosure, ErrorBanner, PageHeader, Reveal, SkeletonBlock, Tex } from '../ui/kit'

const DATES: Record<string, [number, string]> = {
  LUCB2012: [2012.5, 'LUCB'], KK2013: [2013.5, 'KL-LUCB'], LIL2014: [2013.99, "lil' UCB"], ED2006: [2006.5, 'Action elim.'], GK2016: [2016.12, 'Track-and-Stop'], RSP2025: [2025.2, 'Feedback graphs'],
  WW2025: [2025.33, 'Who&When'], AT2025: [2025.67, 'AgenTracer'], MA2025: [2025.69, 'Ma et al.'], DOVER2025: [2025.93, 'DoVer'],
  CP2026: [2026.35, 'Conformal'], CF2026: [2026.4, 'CausalFlow'], CAR2026: [2026.43, 'CAR'], REFLECT2026: [2026.44, 'REFLECT'], ZR2026: [2026.45, 'Zero-Replay'], AL2026: [2026.52, 'AgentLocate'],
  GCJR2026: [2026.62, 'GCJR'], SYM2026: [2026.65, 'SymTrace'], TE2026: [2026.3, 'TraceElephant'], ARFP2026: [2026.64, 'AgenticRAG-FP'],
}
const FEATS: Array<[string, string]> = [
  ['step_level_attribution', 'Step-level'], ['counterfactual_replay', 'CF replay'], ['adaptive_allocation', 'Adaptive'], ['fixed_confidence_stopping', 'Fixed-conf. stop'],
  ['delta_pac_guarantee', 'δ-PAC'], ['prefix_aware_information_reuse', 'Prefix reuse'], ['formal_automata_representation', 'Automata'], ['proven_sample_complexity_bound', 'Sample-compl. bound'], ['real_agent_benchmarks', 'Real benchmarks'],
]
const isBandit = (id: string) => ['GK2016', 'KK2013', 'LUCB2012', 'LIL2014', 'ED2006', 'RSP2025'].includes(id)

function Cell({ v }: { v: string }) {
  const k = v.toLowerCase()
  return <span className={`cell-${k === 'yes' ? 'yes' : k === 'partial' ? 'partial' : k === 'unclear' ? 'unclear' : 'no'}`}>{v}</span>
}

/** Broken time axis: 2006–2017 is compressed, 2024–2027 (where almost all agent-attribution papers appear) gets most of the width. */
const SEG: Array<[number, number, number, number]> = [[2006, 2017, 40, 300], [2024.9, 2026.8, 372, 960]]
const xOf = (t: number, W = 1000) => {
  const s = SEG.find(([a, b]) => t >= a && t <= b) ?? (t < SEG[0][0] ? SEG[0] : SEG[1])
  const k = Math.min(1, Math.max(0, (t - s[0]) / (s[1] - s[0])))
  return (s[2] + k * (s[3] - s[2])) * (W / 1000)
}

function Timeline({ rows, onPick, picked }: { rows: Array<Record<string, string>>; onPick: (id: string) => void; picked: string | null }) {
  const pts = rows.map((r) => ({ r, d: DATES[r.paper_id] })).filter((p) => p.d).sort((a, b) => a.d![0] - b.d![0])
  const W = 1000, H = 330
  const lanes: number[] = []
  const placed = pts.map((p) => {
    const px = xOf(p.d![0], W); let lane = 0
    const label = DATES[p.r.paper_id][1]
    const w = label.length * 6.4 + 22
    const flip = px + w > W - 8                                   // near the right edge: put the label on the left of the dot
    const lo = flip ? px - w : px - 6, hi = flip ? px + 8 : px + w
    while ((lanes[lane] ?? -999) > lo) lane++
    lanes[lane] = hi
    return { ...p, px, lane, flip }
  })
  const ticks = [2006, 2010, 2014, 2017, 2025, 2026]
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" className="timeline-svg" role="group" aria-label="Related-work timeline (the axis is broken between 2017 and 2025)">
      <line x1={30} x2={W - 20} y1={H - 40} y2={H - 40} stroke="var(--border-strong)" />
      <text x={(xOf(2017) + xOf(2025)) / 2} y={H - 36} textAnchor="middle" style={{ fill: 'var(--muted)' }}>// no papers read here //</text>
      {ticks.map((t) => <g key={t}><line x1={xOf(t)} x2={xOf(t)} y1={H - 44} y2={H - 36} stroke="var(--border-strong)" /><text x={xOf(t)} y={H - 20} textAnchor="middle">{t}</text></g>)}
      {placed.map(({ r, px, lane, flip }) => {
        const bandit = isBandit(r.paper_id), y = H - 52 - lane * 24
        const col = r.paper_id === 'CAR2026' ? 'var(--red)' : bandit ? 'var(--violet)' : 'var(--cyan)'
        return (
          <g key={r.paper_id} onClick={() => onPick(r.paper_id)} style={{ cursor: 'pointer' }} tabIndex={0} role="button" aria-label={`${DATES[r.paper_id][1]} (${r.short_name})`} aria-pressed={picked === r.paper_id} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(r.paper_id) } }}>
            <line x1={px} x2={px} y1={y + 6} y2={H - 40} stroke={col} strokeOpacity={0.35} />
            <circle cx={px} cy={y} r={picked === r.paper_id ? 7.5 : r.paper_id === 'CAR2026' ? 7 : 5.5} fill={col} stroke="var(--bg)" strokeWidth={2} />
            <text x={flip ? px - 10 : px + 10} y={y + 4} textAnchor={flip ? 'end' : 'start'} style={{ fontWeight: picked === r.paper_id || r.paper_id === 'CAR2026' ? 700 : 500, fill: picked === r.paper_id ? 'var(--text)' : undefined }}>{DATES[r.paper_id][1]}</text>
          </g>
        )
      })}
    </svg>
  )
}

export default function Related() {
  const nov = useAsync(() => api.novelty(), [])
  const rel = useAsync(() => api.related(), [])
  const [pick, setPick] = useState<string | null>('CAR2026')
  const [q, setQ] = useState('')
  const [fam, setFam] = useState<'all' | 'agent' | 'bandit'>('all')
  const rows = useMemo(() => (nov.data ?? []).filter((r) => (fam === 'all' || (fam === 'bandit') === isBandit(r.paper_id) || r.paper_id === 'AFCR') && `${r.short_name} ${r.arxiv_or_venue} ${r.paper_id} ${DATES[r.paper_id]?.[1] ?? ''}`.toLowerCase().includes(q.trim().toLowerCase())), [nov.data, q, fam])
  const picked = nov.data?.find((r) => r.paper_id === pick)
  const rec = rel.data?.find((r) => r.id === pick)

  return (
    <div className="stack" style={{ gap: 22 }}>
      <PageHeader eyebrow="Problem & related work" title="What is known, and where is the gap?"
        lead="Every row comes from reading the paper’s text (not a search snippet); the depth of reading is recorded per paper. The conclusion is deliberately narrow." />
      <Reveal>
        <div className="grid cols-3">
          {[{ k: 'A', t: 'The gap is supported', d: 'No substantial prior work on the intended combination.', on: false }, { k: 'B', t: 'The gap exists only in a narrower formulation', d: 'Replay and fixed-confidence BAI each exist; the combination under stochastic replay, with abstention and proved prefix reuse, was not found.', on: true }, { k: 'C', t: 'Existing work already addresses it', d: 'Would require redesigning the contribution.', on: false }].map((o) => (
            <motion.div key={o.k} whileHover={{ y: -3 }} className="card" style={{ borderColor: o.on ? 'var(--blue)' : undefined, opacity: o.on ? 1 : 0.55, boxShadow: o.on ? '0 0 0 1px var(--blue), var(--shadow)' : undefined }}>
              <div className="row"><span className="mono" style={{ fontSize: 22, fontWeight: 700, color: o.on ? 'var(--blue)' : 'var(--muted)' }}>{o.k}</span>{o.on && <Badge kind="info">our assessment</Badge>}</div>
              <b>{o.t}</b><p className="small muted" style={{ margin: '4px 0 0' }}>{o.d}</p>
            </motion.div>
          ))}
        </div>
        <p className="small muted">Provisional: some neighbours (DoVer, LUCB/lil’UCB originals, Russo et al.) were read at abstract level only; later postings cannot be excluded.</p>
      </Reveal>

      <Reveal>
        <Card title="Why attribution is hard" icon={<BookMarked size={18} />}>
          <svg viewBox="0 0 900 130" width="100%" role="img" aria-label="Failure propagation from an early decisive step to a late symptom">
            <defs><marker id="ra" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--muted)" /></marker></defs>
            {['receive task', 'wrong subgoal', 'wrong resource', 'misread result', 'update memory', 'bad reasoning', 'final answer ✗'].map((t, i) => {
              const bad = i >= 1, dec = i === 1, last = i === 6
              return <g key={i}><line x1={30 + i * 138 + 100} x2={30 + (i + 1) * 138} y1={55} y2={55} stroke="var(--muted)" markerEnd={i < 6 ? 'url(#ra)' : undefined} />
                <rect x={30 + i * 138} y={32} width={100} height={46} rx={11} fill={dec ? 'color-mix(in srgb, var(--red) 18%, var(--surface-2))' : bad ? 'color-mix(in srgb, var(--amber) 10%, var(--surface-2))' : 'var(--surface-2)'} stroke={dec ? 'var(--red)' : last ? 'var(--amber)' : 'var(--border-strong)'} strokeWidth={dec || last ? 2 : 1} />
                <text x={30 + i * 138 + 50} y={59} textAnchor="middle" style={{ fill: 'var(--text)', font: '600 11.5px var(--font-sans)' }}>{t}</text>
                {dec && <text x={30 + i * 138 + 50} y={100} textAnchor="middle" style={{ fill: 'var(--red)', font: '700 11px var(--font-sans)' }}>decisive error</text>}
                {last && <text x={30 + i * 138 + 50} y={100} textAnchor="middle" style={{ fill: 'var(--amber)', font: '700 11px var(--font-sans)' }}>last action = symptom</text>}</g>
            })}
          </svg>
          <p className="small muted" style={{ marginBottom: 0 }}>Debugging the last action finds the symptom. To find the decisive step you have to <em>intervene</em> and ask what would have happened — and because the agent is stochastic, the answer is a probability that must be estimated with replays.</p>
        </Card>
      </Reveal>

      <Reveal>
        <Card title="Timeline" right={<div className="legend"><span><i style={{ background: 'var(--cyan)' }} />agent attribution</span><span><i style={{ background: 'var(--red)' }} />CAR (closest)</span><span><i style={{ background: 'var(--violet)' }} />bandits / pure exploration</span></div>}>
          {nov.loading ? <SkeletonBlock rows={4} /> : nov.error ? <ErrorBanner error={nov.error} onRetry={nov.reload} /> : <Timeline rows={nov.data ?? []} onPick={setPick} picked={pick} />}
        </Card>
      </Reveal>

      <Reveal>
        <Card title="Evidence matrix" right={
          <div className="row">
            <div className="seg" role="group" aria-label="Family">{(['all', 'agent', 'bandit'] as const).map((f) => <button key={f} aria-pressed={fam === f} onClick={() => setFam(f)}>{fam === f && <motion.span layoutId="fam" className="seg-pill" />}{f === 'all' ? 'All' : f === 'agent' ? 'Agent papers' : 'Bandit papers'}</button>)}</div>
            <label className="row" style={{ position: 'relative' }}><Search size={14} style={{ position: 'absolute', left: 10, color: 'var(--muted)' }} /><input className="input" type="search" style={{ paddingLeft: 30, width: 190 }} placeholder="Filter papers" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filter papers" /></label>
          </div>}>
          {nov.loading ? <SkeletonBlock rows={8} /> : nov.error ? <ErrorBanner error={nov.error} onRetry={nov.reload} /> : (
            <div className="tbl-wrap">
              <table className="tbl" data-testid="novelty-matrix">
                <thead><tr><th>Paper</th><th>Read</th>{FEATS.map(([, l]) => <th key={l}>{l}</th>)}</tr></thead>
                <tbody>
                  {!rows.length && <tr><td colSpan={FEATS.length + 2} className="muted" style={{ padding: 18 }}>No paper matches “{q}”.</td></tr>}
                  {rows.map((r) => (
                    <tr key={r.paper_id} tabIndex={0} onClick={() => setPick(r.paper_id)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setPick(r.paper_id) } }} aria-selected={r.paper_id === pick} style={{ cursor: 'pointer', background: r.paper_id === pick ? 'color-mix(in srgb, var(--blue) 10%, transparent)' : r.paper_id === 'AFCR' ? 'color-mix(in srgb, var(--violet) 8%, transparent)' : undefined }}>
                      <td><b>{r.short_name}</b><div className="xs muted">{r.arxiv_or_venue}</div></td>
                      <td><Badge kind={r.read_depth.startsWith('FULL') || r.read_depth === 'THM' ? 'ok' : r.read_depth === 'KEY' ? 'info' : r.read_depth === 'ABS' ? 'syn' : 'vio'} title="FULL: read in full · THM: theorems checked · KEY: full text keyword-scanned · ABS: abstract only">{r.read_depth}</Badge></td>
                      {FEATS.map(([k]) => <td key={k}><Cell v={r[k]} /></td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="xs muted" style={{ marginBottom: 0 }}>“No” is used only where the full text was searched. The AFCR row describes <em>this</em> work: <b>Partial</b> prefix reuse = valid under stated assumptions; <b>Partial</b> sample complexity = proved for elimination, empirical for LUCB.</p>
        </Card>
      </Reveal>

      {picked && (
        <motion.div key={picked.paper_id} initial={{ y: 10 }} animate={{ y: 0 }}>
          <Card title={<>{picked.short_name} <Badge kind="plain">{picked.arxiv_or_venue}</Badge></>}>
            <p style={{ marginTop: 0 }}>{picked.evidence_notes}</p>
            {rec && (
              <div className="grid cols-2">
                {([['Title', rec.title], ['Authors', rec.authors], ['First publication', `${rec.first_publication}${rec.versions && rec.versions !== 'not verified' ? ' · ' + rec.versions : ''}`], ['Problem', rec.problem_definition], ['Attribution unit', rec.attribution_unit], ['Intervention / replay', rec.replay_or_intervention], ['Estimator', rec.statistical_estimator], ['Allocation', rec.allocation], ['Stopping rule', rec.stopping_rule], ['Guarantee', rec.confidence_or_coverage_guarantee], ['Sample complexity', rec.sample_complexity_results], ['Benchmarks', rec.benchmarks], ['Stated limitations', rec.reported_limitations], ['Public implementation', rec.public_implementation], ['Overlap with this proposal', rec.overlap_with_proposal]] as const).map(([k, v]) => (
                  <div key={k}><div className="xs muted" style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>{k}</div><div className="small">{v}</div></div>
                ))}
              </div>
            )}
          </Card>
        </motion.div>
      )}

      <Reveal>
        <div className="grid cols-2">
          <Card title="What is not novel">
            <ul className="small stack" style={{ paddingLeft: 18, margin: 0 }}>
              <li>Counterfactual replay for step attribution (AgenTracer, CAR, CausalFlow, REFLECT, DoVer, SymTrace).</li>
              <li>Same-policy resampling with outcome distributions and CIs, and the run-forward confound (CAR).</li>
              <li>Fixed-confidence best-arm identification, LUCB, KL confidence bounds, tracking-based optimality (2012–2016).</li>
              <li>Pure exploration with side observations (Russo et al., 2025) — the generic template for sharing.</li>
              <li>Naming replay cost as the bottleneck (Zero-Replay, GCJR).</li>
            </ul>
          </Card>
          <Card title="The narrowed claim">
            <p className="small" style={{ marginTop: 0 }}>Fixed-confidence step attribution under <b>stochastic</b> replay, where (i) stopping carries a per-trajectory δ-correctness statement and an explicit abstention outcome, (ii) rollouts are shared across candidates only under a <b>proved</b> validity condition, and (iii) the substrate is a formal automaton with exactly computable ground truth.</p>
            <Callout kind="warn">The guarantee is conditional on the replay model (A1–A6). It does not transfer to a production LLM agent unless those assumptions are checked.</Callout>
          </Card>
        </div>
      </Reveal>

      <Reveal>
        <div className="grid cols-2">
          <Card title="Unresolved research questions"><ul className="small stack" style={{ paddingLeft: 18, margin: 0 }}>
            <li>Does adaptive allocation help on real LLM agents (ALFWorld, HotpotQA)? — <Badge kind="pend">pending</Badge></li>
            <li>How large is the gap between the elimination bound and LUCB with the stack bound, and the Garivier–Kaufmann lower bound?</li>
            <li>How should joint causes (AND-failures) be handled with fixed confidence (GCJR/CAR-Shapley)?</li>
            <li>Can common random numbers reduce the variance of the total effect through divergent LLM contexts?</li>
            <li>Which Markov abstraction of a real agent keeps A2 approximately true?</li></ul></Card>
          <Card title="Known limitations"><ul className="small stack" style={{ paddingLeft: 18, margin: 0 }}>
            <li>Single decisive cause; nonstationary policies and provider non-determinism are out of scope.</li>
            <li>Exact prefix reproduction (A1); state-reconstruction errors void sharing.</li>
            <li>Hand-designed automaton; results are synthetic.</li>
            <li>Novelty is provisional (see above).</li></ul>
            <Disclosure title="Why not just resample?"><p>Resampling an early step re-rolls everything after it, so an irrelevant early step can look effective. With <Tex>{'\\mu_t'}</Tex> measured under a <em>repair</em> intervention the decisive step stands out because only there is the fault avoided with certainty.</p></Disclosure></Card>
        </div>
      </Reveal>

      <Reveal>
        <Card title="Full paper records (verified fields)">
          {rel.loading ? <SkeletonBlock rows={5} /> : rel.error ? <ErrorBanner error={rel.error} onRetry={rel.reload} /> : (
            <div className="stack" style={{ gap: 6 }}>{rel.data?.map((r) => (
              <Disclosure key={r.id} title={<><b>{r.id}</b> · {r.title}</>} right={<Badge kind="plain">{r.evidence_level}</Badge>}>
                <div className="small stack" style={{ gap: 6 }}><div><b>Authors:</b> {r.authors}</div><div><b>Problem:</b> {r.problem_definition}</div><div><b>Replay / intervention:</b> {r.replay_or_intervention}</div><div><b>Allocation & stopping:</b> {r.allocation}; {r.stopping_rule}</div><div><b>Guarantee:</b> {r.confidence_or_coverage_guarantee}</div><div><b>Benchmarks:</b> {r.benchmarks}</div><div><b>Overlap:</b> {r.overlap_with_proposal}</div></div>
              </Disclosure>))}</div>
          )}
        </Card>
      </Reveal>
    </div>
  )
}
