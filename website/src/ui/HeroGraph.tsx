import { motion } from 'framer-motion'
import { useMemo } from 'react'
import { layoutGroups } from '../graph/layout'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'

/** Decorative-but-real: the 48-state automaton from the API with one failed trajectory travelling over it. */
export function HeroGraph() {
  const g = useAsync(() => api.graph('agent48'), [])
  const t = useAsync(() => api.trajectory({ source: 'automaton', seed: 5 }), [])
  const data = useMemo(() => {
    if (!g.data) return null
    const ns = layoutGroups(g.data.nodes)
    const W = 620, H = 500
    const sx = (x: number) => 36 + ((x - 90) / (190 * 5)) * (W - 72)
    const maxY = Math.max(...ns.map((n) => n.y))
    const sy = (y: number) => 34 + ((y - 70) / (maxY - 70)) * (H - 80)
    const pos = new Map(ns.map((n) => [n.id, { x: sx(n.x), y: sy(n.y), g: String(n.group) }]))
    return { pos, W, H, edges: g.data.edges }
  }, [g.data])
  if (!data) return <div className="skeleton" style={{ height: 420, borderRadius: 16 }} aria-hidden />
  const steps = t.data?.steps ?? []
  const pts = steps.length ? [steps[0].state, ...steps.map((s) => s.next_state as string)].map((id) => data.pos.get(id)).filter(Boolean) as Array<{ x: number; y: number }> : []
  const dur = Math.max(4, pts.length * 0.75)
  const fault = t.data?.planted_arm != null ? data.pos.get(steps[t.data.planted_arm].state) : null
  return (
    <figure className="hero-graph" aria-label="Animated failed trajectory over the 48-state automaton" style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${data.W} ${data.H}`} width="100%" role="img" aria-hidden={false}>
        <defs><filter id="hg" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="4" /></filter></defs>
        {data.edges.map((e, i) => { const a = data.pos.get(e.source), b = data.pos.get(e.target); if (!a || !b) return null
          return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={e.is_fault ? 'var(--red)' : 'var(--text-2)'} strokeOpacity={e.is_fault ? 0.55 : 0.1} strokeWidth={e.is_fault ? 1.3 : 0.8} /> })}
        {Array.from(data.pos.entries()).map(([id, p]) => <circle key={id} cx={p.x} cy={p.y} r={4.4} fill={`var(--g-${p.g})`} fillOpacity={0.85} />)}
        {pts.length > 1 && (
          <>
            <motion.polyline points={pts.map((p) => `${p.x},${p.y}`).join(' ')} fill="none" stroke="var(--cyan)" strokeWidth={2.4} strokeLinejoin="round" strokeLinecap="round"
              initial={{ pathLength: 0 }} animate={{ pathLength: [0, 1, 1], opacity: [0.9, 0.9, 0] }} transition={{ duration: dur + 1.6, repeat: Infinity, times: [0, 0.85, 1], ease: 'linear' }} />
            <motion.g initial={{ x: pts[0].x, y: pts[0].y }} animate={{ x: pts.map((p) => p.x), y: pts.map((p) => p.y) }} transition={{ duration: dur, repeat: Infinity, repeatDelay: 1.6, ease: 'linear' }}>
              <circle r={7} fill="var(--cyan)" filter="url(#hg)" />
              <circle r={4} fill="#fff" />
            </motion.g>
          </>
        )}
        {fault && <><circle className="pulse" cx={fault.x} cy={fault.y} r={11} fill="none" stroke="var(--red)" strokeWidth={2.4} /><text x={fault.x - 15} y={fault.y - 12} textAnchor="start" style={{ fill: 'var(--red)', font: '700 11px var(--font-sans)', letterSpacing: '0.08em' }}>PLANTED FAULT</text></>}
      </svg>
      <figcaption className="xs muted" style={{ textAlign: 'center', marginTop: 4 }}>Live: one failed trajectory on the 48-state automaton · columns = plan · observe · tool · memory · validate · terminal</figcaption>
    </figure>
  )
}
