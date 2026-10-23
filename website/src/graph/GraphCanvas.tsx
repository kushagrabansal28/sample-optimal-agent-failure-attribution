import { select } from 'd3-selection'
import { zoom as d3zoom, zoomIdentity, type ZoomBehavior, type ZoomTransform } from 'd3-zoom'
import { Maximize2, Minus, Plus } from 'lucide-react'
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { GEdgeData } from '../lib/api'
import { bbox, GROUP_ORDER, type PNode } from './layout'

export interface TrailEdge { source: string; target: string; label?: string }
interface Props {
  nodes: PNode[]; edges: GEdgeData[]; height?: number
  selectedId?: string | null; onSelect?: (id: string | null) => void
  query?: string
  trail?: TrailEdge[]; trailIndex?: number; startId?: string | null
  activeSet?: string[]
  /** false for set semantics (NFA / ε-NFA): there is no single "current" state, only an active set. */
  showCurrent?: boolean
  branch?: TrailEdge[]
  culprit?: string | null
  grouped?: boolean
  edgeLabels?: 'auto' | 'all' | 'none'
  fitKey?: string
  minimap?: boolean
  legend?: Array<{ color: string; label: string }>
  ariaLabel?: string
}

const K_MIN = 0.2, K_MAX = 4.5
const groupColor = (g?: string) => (g ? `var(--g-${g})` : 'var(--blue)')
function nodeFill(n: PNode, grouped?: boolean): string {
  if (n.sink) return 'var(--surface-3)'
  if (grouped) return groupColor(n.group)
  if (n.accepting) return 'var(--green)'
  if (n.rejecting) return 'var(--red)'
  if (n.dead) return 'var(--surface-3)'
  return 'var(--surface-3)'
}
function wrap(text: string, w = 15): string[] {
  const words = text.split(/[\s_]+/).filter(Boolean)
  const lines: string[] = []
  let cur = ''
  for (const wd of words) {
    if ((cur + ' ' + wd).trim().length > w && cur) { lines.push(cur); cur = wd } else cur = (cur + ' ' + wd).trim()
  }
  if (cur) lines.push(cur)
  return lines.slice(0, 3)
}

/** Parallel edges between the same ordered pair are drawn as ONE arrow with a combined label (no overlapping labels). */
export interface EdgeGroup { source: string; target: string; members: GEdgeData[]; label: string; is_fault: boolean; epsilon: boolean }
export function groupEdges(edges: GEdgeData[]): EdgeGroup[] {
  const m = new Map<string, GEdgeData[]>()
  edges.forEach((e) => { const k = `${e.source}\u0000${e.target}`; (m.get(k) ?? m.set(k, []).get(k)!).push(e) })
  return [...m.values()].map((members) => {
    const parts = members.map((e) => `${e.label ?? ''}${e.prob != null && e.prob < 1 ? ` ${e.prob.toFixed(2)}` : ''}`.trim()).filter(Boolean)
    const uniq = Array.from(new Set(parts))
    return { source: members[0].source, target: members[0].target, members, label: uniq.join(', '), is_fault: members.some((e) => e.is_fault), epsilon: members.every((e) => e.epsilon) }
  })
}
const shortLabel = (s: string, n = 34) => (s.length > n ? `${s.slice(0, n - 1)}…` : s)

export interface Geo { g: EdgeGroup; i: number; d: string; lx: number; ly: number; self: boolean }

function buildGeometry(nodes: PNode[], groups: EdgeGroup[], R: number): Geo[] {
  const pos = new Map(nodes.map((n) => [n.id, n]))
  const pairCount: Record<string, number> = {}
  const pairIdx: Record<string, number> = {}
  const key = (a: string, b: string) => (a < b ? `${a}|${b}` : `${b}|${a}`)
  groups.forEach((e) => { const k = key(e.source, e.target); pairCount[k] = (pairCount[k] ?? 0) + 1 })
  const out: Geo[] = []
  groups.forEach((g, i) => {
    const a = pos.get(g.source), b = pos.get(g.target)
    if (!a || !b) return
    const k = key(g.source, g.target)
    const idx = (pairIdx[k] = (pairIdx[k] ?? -1) + 1)
    const n = pairCount[k]
    if (a === b) {
      const o = 14 + idx * 12
      out.push({ g, i, d: `M ${a.x - 8} ${a.y - R} C ${a.x - 8 - o} ${a.y - R - o * 1.8}, ${a.x + 8 + o} ${a.y - R - o * 1.8}, ${a.x + 8} ${a.y - R}`, lx: a.x, ly: a.y - R - o * 1.45, self: true })
      return
    }
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1
    const nx = -dy / len, ny = dx / len
    const forward = g.source < g.target ? 1 : -1
    const off = (idx - (n - 1) / 2) * 26 * forward + (Math.min(len, 400) / 400) * 10 * forward
    const cx = (a.x + b.x) / 2 + nx * off, cy = (a.y + b.y) / 2 + ny * off
    const u1x = cx - a.x, u1y = cy - a.y, l1 = Math.hypot(u1x, u1y) || 1
    const u2x = cx - b.x, u2y = cy - b.y, l2 = Math.hypot(u2x, u2y) || 1
    const sx = a.x + (u1x / l1) * R, sy = a.y + (u1y / l1) * R
    const ex = b.x + (u2x / l2) * (R + 4), ey = b.y + (u2y / l2) * (R + 4)
    out.push({ g, i, d: `M ${sx} ${sy} Q ${cx} ${cy} ${ex} ${ey}`, lx: 0.25 * sx + 0.5 * cx + 0.25 * ex, ly: 0.25 * sy + 0.5 * cy + 0.25 * ey, self: false })
  })
  return out
}

/** Greedy label de-collision: a label that would overlap an already placed one is nudged along the vertical axis until it is free. */
export function spreadLabels(geo: Geo[]): Geo[] {
  const placed: Array<{ x0: number; x1: number; y0: number; y1: number }> = []
  const offsets = [0, 13, -13, 26, -26, 39, -39, 52, -52, 65, -65]
  const out = geo.map((g) => ({ ...g }))
  const order = out.filter((g) => g.g.label).sort((a, b) => a.ly - b.ly || a.lx - b.lx)
  for (const g of order) {
    const w = shortLabel(g.g.label).length * 6 + 8
    let chosen = offsets[offsets.length - 1]
    for (const dy of offsets) {
      const box = { x0: g.lx - w / 2, x1: g.lx + w / 2, y0: g.ly + dy - 10, y1: g.ly + dy + 3 }
      if (!placed.some((p) => box.x0 < p.x1 && p.x0 < box.x1 && box.y0 < p.y1 && p.y0 < box.y1)) { chosen = dy; break }
    }
    g.ly += chosen
    placed.push({ x0: g.lx - w / 2, x1: g.lx + w / 2, y0: g.ly - 10, y1: g.ly + 3 })
  }
  return out
}

function GraphCanvasInner({ nodes, edges, height = 560, selectedId, onSelect, query = '', trail = [], trailIndex = 0, startId, activeSet, showCurrent = true, branch = [], culprit, grouped, edgeLabels = 'auto', fitKey, minimap, legend, ariaLabel }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const gRef = useRef<SVGGElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const tRef = useRef<ZoomTransform>(zoomIdentity)
  const [k, setK] = useState(1)
  const [tr, setTr] = useState<ZoomTransform>(zoomIdentity)
  const [size, setSize] = useState({ w: 800, h: height })
  const [hover, setHover] = useState<string | null>(null)
  const interacted = useRef(false)
  const sizeRef = useRef({ w: 800, h: height })
  const fitRef = useRef<(animate: boolean, dims?: { w: number; h: number }) => void>(() => {})
  const R = grouped ? 19 : 27

  const groups = useMemo(() => groupEdges(edges), [edges])
  const geo = useMemo(() => spreadLabels(buildGeometry(nodes, groups, R)), [nodes, groups, R])
  // the fit box covers the nodes AND their (possibly wide) edge labels, so nothing is cut off at the border
  const box = useMemo(() => {
    const b = bbox(nodes, 60)
    if (edgeLabels === 'none') return b
    geo.forEach((g) => {
      if (!g.g.label || (edgeLabels === 'auto' && grouped)) return
      const half = (shortLabel(g.g.label).length * 6 + 8) / 2
      b.x0 = Math.min(b.x0, g.lx - half - 8); b.x1 = Math.max(b.x1, g.lx + half + 8); b.y0 = Math.min(b.y0, g.ly - 18); b.y1 = Math.max(b.y1, g.ly + 10)
    })
    return b
  }, [nodes, geo, edgeLabels, grouped])
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes])
  const q = query.trim().toLowerCase()
  const matches = useMemo(() => (q ? new Set(nodes.filter((n) => `${n.id} ${n.qid ?? ''} ${n.name ?? ''} ${n.label ?? ''} ${n.description ?? ''}`.toLowerCase().includes(q)).map((n) => n.id)) : null), [q, nodes])
  const neighbors = useMemo(() => {
    const m = new Map<string, Set<string>>()
    edges.forEach((e) => { (m.get(e.source) ?? m.set(e.source, new Set()).get(e.source)!).add(e.target); (m.get(e.target) ?? m.set(e.target, new Set()).get(e.target)!).add(e.source) })
    return m
  }, [edges])

  const tween = useCallback((to: ZoomTransform, ms = 650) => {
    const svg = svgRef.current, z = zoomRef.current
    if (!svg || !z) return
    const from = tRef.current, t0 = performance.now()
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reduce || document.hidden) { select(svg).call(z.transform, to); return }
    const step = (t: number) => {
      const p = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - p, 3)
      const k2 = from.k + (to.k - from.k) * e
      select(svg).call(z.transform, zoomIdentity.translate(from.x + (to.x - from.x) * e, from.y + (to.y - from.y) * e).scale(k2))
      if (p < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [])

  /** Fit the whole graph into the container.  Never fits into a container that has no size yet (a hidden pane, a collapsed tab): k would be 0. */
  const fit = useCallback((animate = true, dims?: { w: number; h: number }) => {
    const w = dims?.w ?? size.w, h = dims?.h ?? size.h
    if (!(w > 0) || !(h > 0)) return
    const bw = Math.max(1, box.x1 - box.x0), bh = Math.max(1, box.y1 - box.y0)
    const kk = Math.min(K_MAX, Math.max(K_MIN, Math.min(w / bw, h / bh, 1.6)))
    const t = zoomIdentity.translate(w / 2 - ((box.x0 + box.x1) / 2) * kk, h / 2 - ((box.y0 + box.y1) / 2) * kk).scale(kk)
    if (animate) tween(t); else if (svgRef.current && zoomRef.current) select(svgRef.current).call(zoomRef.current.transform, t)
  }, [box, size, tween])

  const zoomBy = useCallback((f: number) => {
    const t = tRef.current, cx = size.w / 2, cy = size.h / 2
    const k2 = Math.min(K_MAX, Math.max(K_MIN, t.k * f)), r = k2 / t.k
    tween(zoomIdentity.translate(cx - (cx - t.x) * r, cy - (cy - t.y) * r).scale(k2), 250)
  }, [size, tween])

  fitRef.current = fit
  sizeRef.current = size

  const flyTo = useCallback((x: number, y: number, kk: number) => {
    if (!(size.w > 0)) return
    tween(zoomIdentity.translate(size.w / 2 - x * kk, size.h / 2 - y * kk).scale(kk))
  }, [size, tween])

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const apply = () => {
      const w = el.clientWidth
      if (w > 0) setSize({ w, h: height })
      // a positive size after a zero size always refits, even if the user touched the graph while it was collapsed
      if (w > 0 && (!interacted.current || !(tRef.current.k > 0) || !Number.isFinite(tRef.current.x))) fitRef.current(false, { w, h: height })
    }
    const ro = new ResizeObserver(apply)
    ro.observe(el); apply()
    return () => ro.disconnect()
  }, [height])

  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    const z = d3zoom<SVGSVGElement, unknown>().scaleExtent([K_MIN, K_MAX]).extent(() => [[0, 0], [Math.max(1, sizeRef.current.w), Math.max(1, sizeRef.current.h)]]).on('zoom', (ev) => {
      const t = ev.transform as ZoomTransform
      if (!(t.k > 0) || !Number.isFinite(t.x) || !Number.isFinite(t.y)) return               // ignore degenerate transforms
      if (ev.sourceEvent) interacted.current = true
      tRef.current = t
      gRef.current?.setAttribute('transform', t.toString())
      setK(t.k); setTr(t)
    })
    zoomRef.current = z
    select(svg).call(z).on('dblclick.zoom', null)
    return () => { select(svg).on('.zoom', null) }
  }, [])

  useEffect(() => { interacted.current = false }, [fitKey])
  const fitSig = `${fitKey}|${nodes.length}|${Math.round(size.w / 40)}`
  useEffect(() => { if (nodes.length) fit(false) /* eslint-disable-next-line */ }, [fitSig])

  useEffect(() => {
    if (matches && matches.size) {
      const first = nodes.find((n) => matches.has(n.id))
      if (first) flyTo(first.x, first.y, Math.max(tRef.current.k, 1.25))
    }
    /* eslint-disable-next-line */
  }, [q])
  useEffect(() => {
    if (selectedId) { const n = byId.get(selectedId); if (n && (n.x * tRef.current.k + tRef.current.x < 40 || n.x * tRef.current.k + tRef.current.x > size.w - 40 || n.y * tRef.current.k + tRef.current.y < 40 || n.y * tRef.current.k + tRef.current.y > size.h - 40)) flyTo(n.x, n.y, tRef.current.k) }
    /* eslint-disable-next-line */
  }, [selectedId])

  const revealed = trail.slice(0, trailIndex)
  const trailKeys = new Set(revealed.filter((t) => t.label !== undefined).map((t) => `${t.source}>${t.target}>${t.label}`))
  const trailPairs = new Set(revealed.filter((t) => t.label === undefined).map((t) => `${t.source}>${t.target}`))
  const trailNodes = new Set(revealed.flatMap((t) => [t.source, t.target]))
  const current = !showCurrent ? null : revealed.length ? revealed[revealed.length - 1].target : startId ?? null
  const branchKeys = new Set(branch.filter((t) => t.label !== undefined).map((t) => `${t.source}>${t.target}>${t.label}`))
  const branchPairs = new Set(branch.filter((t) => t.label === undefined).map((t) => `${t.source}>${t.target}`))
  const active = new Set(activeSet ?? [])
  const focus = hover ?? selectedId ?? null
  const focusN = focus ? neighbors.get(focus) : null

  const dimNode = (id: string) => {
    if (matches) return !matches.has(id)
    if (hover) return id !== hover && !focusN?.has(id)
    return false
  }

  const markerFor = (c: string) => `url(#m-${c})`
  const groupsMaxY = Math.max(0, ...nodes.map((n) => n.y))
  return (
    <div className="graph-wrap" ref={wrapRef} style={{ height }}>
      <div className="graph-hint">drag to pan · scroll to zoom · click a state</div>
      <div className="graph-tools">
        <button className="btn icon sm" aria-label="Zoom in" onClick={() => zoomBy(1.4)}><Plus size={14} /></button>
        <button className="btn icon sm" aria-label="Zoom out" onClick={() => zoomBy(1 / 1.4)}><Minus size={14} /></button>
        <button className="btn icon sm" aria-label="Fit to view" onClick={() => fit(true)}><Maximize2 size={14} /></button>
      </div>
      <svg ref={svgRef} className="graph-svg" width="100%" height={height} role="group" aria-label={ariaLabel ?? 'State graph'} onClick={(e) => { if (e.target === svgRef.current) onSelect?.(null) }}>
        <defs>
          {[['d', '#5d6a88'], ['f', '#ff6b7a'], ['p', '#35d6e0'], ['b', '#9b8cff'], ['e', '#f5b84a'], ['s', '#5b9dff']].map(([id, c]) => (
            <marker key={id} id={`m-${id}`} viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill={c} /></marker>
          ))}
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3.2" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <g ref={gRef}>
          {grouped && GROUP_ORDER.map((g, i) => (
            <g key={g}>
              <rect x={90 + i * 190 - 78} y={18} width={156} height={groupsMaxY + 62} rx={16} fill={groupColor(g)} opacity={0.045} />
              <text x={90 + i * 190} y={36} textAnchor="middle" style={{ fill: groupColor(g), font: '700 11px var(--font-sans)', letterSpacing: '0.14em' }}>{g}</text>
            </g>
          ))}
          {geo.map(({ g, d, lx, ly, i }) => {
            const keyOf = (e: GEdgeData) => `${e.source}>${e.target}>${e.label ?? ''}`
            const pair = `${g.source}>${g.target}`
            const inTrail = g.members.some((e) => trailKeys.has(keyOf(e))) || trailPairs.has(pair)
            const inBranch = g.members.some((e) => branchKeys.has(keyOf(e))) || branchPairs.has(pair)
            const touching = focus && (g.source === focus || g.target === focus)
            const dim = (matches && !(matches.has(g.source) || matches.has(g.target))) || (hover && !touching)
            const color = inBranch ? 'b' : inTrail ? 'p' : g.is_fault ? 'f' : g.epsilon ? 'e' : touching ? 's' : 'd'
            const stroke = { b: '#9b8cff', p: '#35d6e0', f: '#ff6b7a', e: '#f5b84a', s: '#5b9dff', d: '#5d6a88' }[color]
            const showLabel = edgeLabels === 'all' ? k > 0.55 : edgeLabels === 'none' ? false : (g.is_fault || inTrail || inBranch || touching || !grouped || k > 1.9)
            return (
              <g key={i} opacity={dim ? 0.1 : inTrail || inBranch ? 1 : touching || g.is_fault ? 0.95 : grouped ? 0.5 : 0.85}>
                <title>{`${g.source} → ${g.target}: ${g.label}`}</title>
                <path className={`g-edge ${inTrail || inBranch ? 'dash-flow' : ''}`} d={d} stroke={stroke} strokeWidth={inTrail || inBranch ? 2.6 : g.is_fault ? 1.8 : touching ? 1.7 : 1.1} strokeDasharray={inBranch ? '5 4' : g.epsilon ? '2 4' : undefined} markerEnd={markerFor(color)} />
                {showLabel && g.label && <text className="g-label" x={lx} y={ly} textAnchor="middle">{shortLabel(g.label)}</text>}
              </g>
            )
          })}
          {nodes.map((n) => {
            const sel = selectedId === n.id, isStart = !!(n.start || n.is_initial), dim = dimNode(n.id)
            const term = n.kind === 'accepting' || n.kind === 'rejecting' || n.accepting || n.rejecting
            const hit = matches?.has(n.id)
            const visited = trailNodes.has(n.id)
            const hasQ = !!n.qid
            const below = hasQ ? (n.label && n.label !== n.qid ? wrap(String(n.label), grouped ? 16 : 18) : []) : []
            const lines = hasQ ? [n.qid as string] : wrap(String(n.label ?? n.id), grouped ? 16 : 20)
            const isCurrent = current === n.id
            const aria = `State ${n.qid ? `${n.qid}${n.label ? ` ${n.label}` : ''}` : (n.label ?? n.id)}${isStart ? ', initial' : ''}${n.accepting ? ', accepting' : ''}${n.rejecting ? ', rejecting' : ''}`
            return (
              <g key={n.id} className={`g-node ${sel ? 'sel' : ''}`} transform={`translate(${n.x},${n.y})`} opacity={dim ? 0.18 : 1} role="button" tabIndex={0} aria-label={aria} aria-pressed={sel}
                onClick={(ev) => { ev.stopPropagation(); onSelect?.(sel ? null : n.id) }} onKeyDown={(ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); onSelect?.(sel ? null : n.id) } }}
                onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}>
                <circle className="halo" r={R + 9} fill="none" stroke={sel ? 'var(--blue)' : 'var(--text-2)'} strokeWidth={2} opacity={0.5} />
                {(culprit === n.id) && <circle className="pulse" r={R + 8} fill="none" stroke="var(--red)" strokeWidth={2.5} />}
                {(isCurrent) && <circle className="pulse" r={R + 6} fill="none" stroke="var(--cyan)" strokeWidth={2.5} />}
                {active.has(n.id) && <circle r={R + 5} fill="none" stroke="var(--amber)" strokeWidth={3} filter="url(#glow)" />}
                {term ? <rect x={-R} y={-R * 0.78} width={R * 2} height={R * 1.56} rx={8} fill={nodeFill(n, grouped)} fillOpacity={grouped ? 0.9 : 0.85} stroke={hit ? '#fff' : visited ? 'var(--cyan)' : 'color-mix(in srgb, var(--bg) 60%, transparent)'} strokeWidth={hit || visited ? 3 : 1.5} />
                  : <circle className={n.sink || n.dead ? 'sink-node' : undefined} r={R} fill={nodeFill(n, grouped)} fillOpacity={grouped ? 0.88 : 1} stroke={hit ? '#fff' : n.role === 'decision' || n.role === 'fault_entry' ? 'var(--red)' : isStart ? 'var(--cyan)' : visited ? 'var(--cyan)' : 'var(--border-strong)'} strokeWidth={hit ? 4 : n.role === 'decision' || n.role === 'fault_entry' || isStart || visited ? 3 : 1.4} />}
                {n.accepting && !n.kind && !term && <circle r={R - 5} fill="none" stroke="var(--green)" strokeWidth={1.6} />}
                {n.accepting && !n.kind && term && <rect x={-R + 4} y={-R * 0.78 + 4} width={R * 2 - 8} height={R * 1.56 - 8} rx={5} fill="none" stroke="#06101f" strokeOpacity={0.55} strokeWidth={1.4} />}
                {isStart && !grouped && <path d={`M ${-R - 28} 0 L ${-R - 5} 0`} stroke="var(--cyan)" strokeWidth={2} markerEnd="url(#m-p)" />}
                {culprit === n.id && <text y={-R - 12} textAnchor="middle" style={{ fill: 'var(--red)', font: '700 10px var(--font-sans)', letterSpacing: '0.1em' }}>CULPRIT</text>}
                <text textAnchor="middle" y={grouped ? 3.5 : 5} style={{ fontSize: grouped ? 9.5 : hasQ ? 14 : 12, fontWeight: 700 }}>{lines.map((l, i) => <tspan key={i} x={0} dy={i === 0 ? (lines.length > 1 ? -4 : 0) : 12}>{l}</tspan>)}</text>
                {below.length > 0 && <text textAnchor="middle" y={R + 14} style={{ fontSize: grouped ? 9.5 : 11, fontWeight: 500 }}>{below.map((l, i) => <tspan key={i} x={0} dy={i === 0 ? 0 : 11}>{l}</tspan>)}</text>}
              </g>
            )
          })}
        </g>
      </svg>
      {legend && <div className="graph-legend">{legend.map((l) => <span key={l.label}><i style={{ background: l.color }} />{l.label}</span>)}</div>}
      {minimap && nodes.length > 12 && (
        <div className="minimap" aria-hidden>
          <svg width="150" height="104" viewBox={`${box.x0} ${box.y0} ${box.x1 - box.x0} ${box.y1 - box.y0}`} preserveAspectRatio="xMidYMid meet"
            onClick={(ev) => { const r = (ev.currentTarget as SVGSVGElement).getBoundingClientRect(); const px = (ev.clientX - r.left) / r.width, py = (ev.clientY - r.top) / r.height; flyTo(box.x0 + px * (box.x1 - box.x0), box.y0 + py * (box.y1 - box.y0), tRef.current.k) }}>
            {nodes.map((n) => <circle key={n.id} cx={n.x} cy={n.y} r={14} fill={nodeFill(n, grouped)} opacity={0.85} />)}
            <rect x={(-tr.x) / tr.k} y={(-tr.y) / tr.k} width={size.w / tr.k} height={size.h / tr.k} fill="rgba(91,157,255,0.12)" stroke="var(--blue)" strokeWidth={10} />
          </svg>
        </div>
      )}
    </div>
  )
}
export const GraphCanvas = memo(GraphCanvasInner)
