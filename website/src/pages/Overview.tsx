import { motion } from 'framer-motion'
import { ArrowRight, Boxes, FileText, FlaskConical, Layers, Network, ShieldCheck, Target } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { HeroGraph } from '../ui/HeroGraph'
import { Badge, Callout, Card, Pending, Reveal, SkeletonBlock, Stat, Synthetic, TabPanel, Tabs, Tex, stagger, rise, Measured, Proved } from '../ui/kit'

const PIPELINE = [
  ['Parse task and failed trajectory', 'Read the task and a failed run (states, actions, observations).', 'replay.automaton_env · agents.toolagent', 'POST /api/trajectory'],
  ['Validate trajectory structure', 'Check ids, distributions, reachability, terminal states.', 'AgentModel.validate()', '—'],
  ['Convert to an automaton / LTS', 'Time-augmented states; DFA/NFA/ε-NFA/PA/LTS views.', 'automata.benchmark48', 'GET /api/automata/graph'],
  ['Identify eligible candidate steps', 'All steps, or decision states only (a prior).', 'AutomatonEnv(candidates=…)', '—'],
  ['Construct an intervention per candidate', 'Repair (force ρ(q)) or resample (redraw from π).', 'replay.*Env', 'POST /api/replay'],
  ['Define estimand and reference', 'μ_t = P(Y=1 | do(g_t)); common reference μ_ref.', 'paper §2', '—'],
  ['Initialise estimates and confidence procedure', 'Per-arm KL balls, x_n = ln(2Kn(n+1)/δ).', 'statistics.confidence.StackKL', '—'],
  ['Select the next candidate', 'LUCB: empirical best + strongest challenger.', 'attribution.algorithms.LUCB', '—'],
  ['Execute the counterfactual rollout', 'Re-simulate the continuation from the intervened state.', 'env.pull(arm, rng)', '—'],
  ['Record the result and prefix', 'Keep the visited (time, state, action) path.', 'PullResult.shared_arms', '—'],
  ['Update the candidate estimates', 'Own sample plus validly matched shared samples.', 'attribution.engine', '—'],
  ['Apply the stopping rule', 'Certify only when lo_h + ε ≥ max other hi.', 'attribution.targets', '—'],
  ['Return culprit, uncertainty or abstention', 'Budget exhaustion is an abstention, never a δ-PAC stop.', 'AttributionResult', 'POST /api/attribute'],
  ['Compare with the planted cause', 'Exact ground truth from dynamic programming.', 'ground_truth', '—'],
  ['Export traces, estimates and metrics', 'Raw rows (CSV/JSON) and aggregates.', 'experiments.suite', 'GET /api/results/export'],
] as const

type SecId = 'title' | 'gap' | 'problem' | 'methods' | 'input' | 'output' | 'steps'

function Pipeline() {
  const [i, setI] = useState(7)
  const s = PIPELINE[i]
  return (
    <div className="stack">
      <div className="pipeline" role="list">
        {PIPELINE.map((p, k) => (
          <button key={k} role="listitem" className={`pipe-step ${k === i ? 'on' : ''}`} onClick={() => setI(k)} onMouseEnter={() => setI(k)} aria-current={k === i}>
            <b>{p[0]}</b>
          </button>
        ))}
      </div>
      <motion.div key={i} initial={{ y: 8 }} animate={{ y: 0 }} className="callout info" style={{ alignItems: 'flex-start' }}>
        <Layers size={18} />
        <div>
          <b style={{ color: 'var(--text)' }}>Step {i + 1} · {s[0]}</b>
          <div>{s[1]}</div>
          <div className="small muted" style={{ marginTop: 4 }}>module <code>{s[2]}</code>{s[3] !== '—' && <> · endpoint <code>{s[3]}</code></>}</div>
        </div>
      </motion.div>
    </div>
  )
}

function Sections() {
  const [sec, setSec] = useState<SecId>('title')
  return (
    <Card title="The seven required sections" icon={<FileText size={18} />}>
      <Tabs<SecId> name="overview" label="The seven required sections" value={sec} onChange={setSec} tabs={[
        { id: 'title', label: '1 · Title' }, { id: 'gap', label: '2 · Research gap' }, { id: 'problem', label: '3 · Problem' }, { id: 'methods', label: '4 · Methods' },
        { id: 'input', label: '5 · Input' }, { id: 'output', label: '6 · Output' }, { id: 'steps', label: '7 · Steps' },
      ]} />
      <TabPanel id={sec} name="overview">
        {sec === 'title' && (
          <div className="stack">
            <h3 style={{ fontSize: 22 }}>Sample-Optimal Culprit Identification for Agent Failures: Fixed-Confidence Attribution with Automata-Aware Sequential Replay</h3>
            <p className="muted">Short title: <b>Sample-Optimal Agent Failure Attribution</b>. Working method name: <b>AFCR</b> (Automata-Aware Fixed-Confidence Replay).</p>
            <Callout kind="warn" title="About the word “optimal”">The title states the research <em>objective</em>. We prove δ-correctness and an elimination-based sample-complexity bound; we do <b>not</b> claim sample-optimality (Garivier &amp; Kaufmann caution against that word for constant-factor bounds).</Callout>
          </div>
        )}
        {sec === 'gap' && (
          <div className="stack">
            <p>After reading the supplied papers and about fifteen more, the novelty assessment is <Badge kind="info">outcome B</Badge>: the gap exists only in a <b>narrower formulation</b>.</p>
            <div className="grid cols-2">
              <Callout kind="ok" title="Already done by others">Replay for step attribution (AgenTracer, CAR, CausalFlow, REFLECT, DoVer); same-policy resampling with CIs (CAR); fixed-confidence best-arm identification, LUCB and KL bounds; side-observation bandits.</Callout>
              <Callout kind="info" title="Narrow claim of this work">Fixed-confidence stopping with explicit abstention under <em>stochastic</em> replay, a <em>proved</em> validity condition for sharing rollouts across candidate steps, on an automaton substrate with exact ground truth.</Callout>
            </div>
            <p className="small muted">Provisional: some neighbours were read at abstract level only. See the <Link to="/related">related-work page</Link> for the evidence table.</p>
          </div>
        )}
        {sec === 'problem' && (
          <div className="stack">
            <p>A failed agent trajectory <Tex>{'\\tau=(q_0,a_1,q_1,\\dots,a_T,q_T)'}</Tex> ends with <Tex>{'Y=0'}</Tex>. Which step was <em>decisive</em>, using as few expensive counterfactual rollouts as possible, with a valid error guarantee?</p>
            <Tex block>{'\\mu_t=\\Pr\\big(Y^{(t,g_t)}=1\\big),\\qquad t^\\star=\\arg\\max_t \\mu_t,\\qquad \\Pr(\\hat t\\neq t^\\star)\\le\\delta'}</Tex>
            <p className="small muted">Association, prediction, interventional effect, unique responsibility and joint causes are different notions; this work targets the <b>interventional effect of a repair</b>. Ties or near-ties return an abstention with a candidate set.</p>
          </div>
        )}
        {sec === 'methods' && (
          <ul className="stack" style={{ paddingLeft: 18, margin: 0 }}>
            <li><b>Confidence sequences</b> — per-arm KL balls with a union bound over arms and sample counts (Theorem 1).</li>
            <li><b>Adaptive allocation</b> — LUCB-style sampling; successive elimination for the proven bound; uniform/random as baselines.</li>
            <li><b>Automata substrate</b> — 48/64/96-state agent automaton, nine formal models, exact value tables by backward induction.</li>
            <li><b>Prefix-aware reuse</b> — one rollout may serve several candidates when it visits that candidate’s exact (time, state) and takes its intervention action (Theorem 3).</li>
          </ul>
        )}
        {sec === 'input' && (
          <ul className="stack" style={{ paddingLeft: 18, margin: 0 }}>
            <li>A failed trajectory with step-level actions and states; the task specification</li>
            <li>Candidate intervention locations and an intervention (repair / resample) per candidate</li>
            <li>A replay environment and an outcome evaluator</li>
            <li>Confidence parameter <Tex>{'\\delta'}</Tex>, rollout budget, optional seeds, automaton configuration</li>
          </ul>
        )}
        {sec === 'output' && (
          <ul className="stack" style={{ paddingLeft: 18, margin: 0 }}>
            <li>The culprit step <em>or</em> an abstention with the candidate set</li>
            <li>Per-candidate estimates, confidence intervals, rollouts, total replay cost</li>
            <li>Stopping status and whether the δ-guarantee applies (and why not)</li>
            <li>Original and counterfactual traces; a machine-readable run record</li>
          </ul>
        )}
        {sec === 'steps' && <Pipeline />}
      </TabPanel>
    </Card>
  )
}

const ARCH = [
  { id: 'a', x: 20, y: 20, w: 150, h: 54, t: 'Failed trajectory', d: 'Original run: states, actions, outcome' },
  { id: 'b', x: 210, y: 20, w: 170, h: 54, t: 'Intervention protocol', d: 'Repair (force ρ) or resample (redraw from π) per candidate step' },
  { id: 'c', x: 420, y: 20, w: 170, h: 54, t: 'Replay environment', d: 'Automaton / tool agent / text game; exact snapshots' },
  { id: 'd', x: 210, y: 130, w: 170, h: 54, t: 'Confidence sequences', d: 'KL balls; union bound over arms and n' },
  { id: 'e', x: 420, y: 130, w: 170, h: 54, t: 'Allocation (LUCB)', d: 'Pull the empirical best and its strongest challenger' },
  { id: 'f', x: 20, y: 130, w: 150, h: 54, t: 'Stopping rule', d: 'Certify, or abstain at the budget' },
  { id: 'g', x: 420, y: 240, w: 170, h: 54, t: 'Prefix reuse', d: 'Valid only with exact (time,state,action) match' },
  { id: 'h', x: 20, y: 240, w: 150, h: 54, t: 'Result + record', d: 'Culprit / abstention, CIs, traces, flags' },
] as const

function Architecture() {
  const [h, setH] = useState<string>('d')
  const cur = ARCH.find((a) => a.id === h)!
  const arrows: Array<[string, string]> = [['a', 'b'], ['b', 'c'], ['c', 'e'], ['e', 'd'], ['d', 'f'], ['f', 'h'], ['c', 'g'], ['g', 'd']]
  const pos = (id: string) => { const a = ARCH.find((x) => x.id === id)!; return { x: a.x + a.w / 2, y: a.y + a.h / 2 } }
  return (
    <Card title="System architecture" icon={<Boxes size={18} />}>
      <svg viewBox="0 0 610 316" width="100%" role="img" aria-label="System architecture diagram">
        <defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--muted)" /></marker></defs>
        {arrows.map(([a, b], i) => { const p = pos(a), q = pos(b); return <line key={i} x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke="var(--muted)" strokeOpacity={0.6} strokeWidth={1.3} markerEnd="url(#ar)" /> })}
        {ARCH.map((a) => (
          <g key={a.id} onMouseEnter={() => setH(a.id)} onClick={() => setH(a.id)} style={{ cursor: 'pointer' }} tabIndex={0} role="button" aria-label={a.t} onFocus={() => setH(a.id)}>
            <rect x={a.x} y={a.y} width={a.w} height={a.h} rx={12} fill={h === a.id ? 'color-mix(in srgb, var(--blue) 16%, var(--surface-2))' : 'var(--surface-2)'} stroke={h === a.id ? 'var(--blue)' : 'var(--border-strong)'} strokeWidth={h === a.id ? 2 : 1} />
            <text x={a.x + a.w / 2} y={a.y + a.h / 2 + 4} textAnchor="middle" style={{ fill: 'var(--text)', font: '600 12.5px var(--font-sans)' }}>{a.t}</text>
          </g>
        ))}
      </svg>
      <motion.div key={h} initial={{ y: 6 }} animate={{ y: 0 }} className="small" style={{ marginTop: 6 }}><b>{cur.t}.</b> <span className="muted">{cur.d}</span></motion.div>
    </Card>
  )
}

export default function Overview() {
  const idx = useAsync(() => api.resultsIndex(), [])
  const tests = useAsync(() => api.tests(), [])
  const g = useAsync(() => api.graph('agent48'), [])
  const rows = idx.data?.meta ? Object.values(idx.data.meta.groups).reduce((a, b) => a + b.rows, 0) : null
  const modules = tests.data && tests.data.total ? Object.entries(tests.data.modules) : []

  return (
    <div className="stack" style={{ gap: 28 }}>
      <section className="hero hero-grid">
        <motion.div initial="hidden" animate="show" variants={stagger}>
          <motion.div variants={rise} className="eyebrow"><Target size={14} /> Agentic AI · Sequential statistics · Models of computation</motion.div>
          <motion.h1 variants={rise} id="page-title" tabIndex={-1} style={{ outline: 'none' }}>Sample-optimal <span className="grad-text">culprit identification</span> for agent failures</motion.h1>
          <motion.div variants={rise} className="row" style={{ marginTop: 10 }}><Badge kind="syn">“sample-optimal” = the research objective, not a proven property</Badge><Link to="/theory" className="small">what is actually proved →</Link></motion.div>
          <motion.p variants={rise} className="sub">Fixed-confidence attribution with automata-aware sequential replay. Find the decisive step of a failed agent run with few counterfactual rollouts — and say so honestly when the data cannot decide.</motion.p>
          <motion.div variants={rise} className="row" style={{ marginBottom: 14 }}>
            <Link to="/dashboard" className="btn primary" style={{ textDecoration: 'none' }}>Run an attribution <ArrowRight size={16} /></Link>
            <Link to="/lab" className="btn" style={{ textDecoration: 'none' }}><Network size={16} /> Explore the 48-state automaton</Link>
            <Link to="/theory" className="btn ghost" style={{ textDecoration: 'none' }}>Read the guarantees</Link>
          </motion.div>
          <motion.p variants={rise} className="hero-title-note">“Sample-optimal” names the research objective, not a proven property. Every number on this site is computed from the repository’s code and result files; simulated data is labelled <Synthetic />.</motion.p>
        </motion.div>
        <div className="hero-visual"><HeroGraph /></div>
      </section>

      <Reveal>
        <div className="kpis">
          <Card><Stat label="Logical states (validated)" value={g.data?.count_logical_states} sub={g.data ? Object.values(g.data.groups ?? {}).join(' · ') + ' per group' : <SkeletonBlock rows={1} />} /></Card>
          <Card><Stat label="Unit & statistical tests passing" value={tests.data ? tests.data.passed + (tests.data.frontend?.passed ?? 0) : undefined} text={tests.data && !tests.data.total ? 'run tests' : undefined} sub={tests.data?.total ? `of ${tests.data.total + (tests.data.frontend?.total ?? 0)} · backend ${tests.data.passed}/${tests.data.total}${tests.data.frontend ? ` · frontend ${tests.data.frontend.passed}/${tests.data.frontend.total}` : ''} · ${tests.data.failed + (tests.data.frontend?.failed ?? 0)} failed · stored report, last run ${tests.data.ran_at}` : undefined} /></Card>
          <Card><Stat label="Synthetic trials recorded" value={rows ?? undefined} text={!idx.loading && !rows ? 'none yet' : undefined} sub={idx.data?.groups.length ? `${idx.data.groups.length} experiment groups` : undefined} /></Card>
          <Card><Stat label="Real-benchmark results" text="0" sub={<Pending />} /></Card>
        </div>
      </Reveal>

      <Reveal><Sections /></Reveal>

      <Reveal>
        <div className="grid cols-2">
          <Architecture />
          <Card title="The δ-PAC objective, compactly" icon={<ShieldCheck size={18} />}>
            <Tex block>{'\\Pr\\big(\\text{certified culprit is wrong}\\big)\\le\\delta \\quad\\text{under assumptions A1–A6}'}</Tex>
            <ul className="small stack" style={{ paddingLeft: 18, margin: 0, color: 'var(--text-2)' }}>
              <li>It holds for <b>any</b> sampling rule, because the bounds are anytime-valid. <Proved /></li>
              <li>A budget timeout is an <b>abstention</b>, not a δ-PAC stop.</li>
              <li>An empirical “90 % accuracy” target is a different object from a (1−δ) guarantee.</li>
              <li>The guarantee is about the <em>replay model</em>; it transfers to a real LLM agent only if A1–A6 are checked.</li>
            </ul>
          </Card>
        </div>
      </Reveal>

      <Reveal>
        <Card title="What is implemented, and how it is verified" icon={<FlaskConical size={18} />} right={tests.data?.ran_at ? <span className="xs muted">tests run {tests.data.ran_at}</span> : undefined}>
          {tests.loading ? <SkeletonBlock rows={5} /> : modules.length ? (
            <div className="tbl-wrap"><table className="tbl"><thead><tr><th>Test module</th><th style={{ textAlign: 'right' }}>passed</th><th style={{ textAlign: 'right' }}>failed</th><th>status</th></tr></thead>
              <tbody>{modules.map(([m, v]) => <tr key={m}><td className="mono">{m}</td><td className="n">{v.passed}</td><td className="n">{v.failed}</td><td>{v.failed ? <Badge kind="pend">failing</Badge> : <Measured />}</td></tr>)}</tbody></table></div>
          ) : <Callout kind="info">No test report found. Run <code>python scripts/run_tests_report.py</code>.</Callout>}
        </Card>
      </Reveal>
    </div>
  )
}
