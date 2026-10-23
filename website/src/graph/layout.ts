import type { GEdgeData, GNodeData } from '../lib/api'

export interface PNode extends GNodeData { x: number; y: number }
export const GROUP_ORDER = ['PLAN', 'OBSERVE', 'TOOL', 'MEMORY', 'VALIDATE', 'TERMINAL']

/** Group columns (used for the 48/64/96-state agent automaton): one column per group, ordered by role then id. */
export function layoutGroups(nodes: GNodeData[], colW = 190, rowH = 74): PNode[] {
  const cnt: Record<string, number> = {}
  return nodes.map((n) => {
    const g = GROUP_ORDER.indexOf(String(n.group))
    const k = g < 0 ? GROUP_ORDER.length : g
    const i = (cnt[k] = (cnt[k] ?? -1) + 1)
    return { ...n, x: 90 + k * colW, y: 70 + i * rowH }
  })
}

/** Layered (BFS from the start state) left-to-right layout for small automata. Unreachable nodes go to an extra layer. */
export function layoutLayered(nodes: GNodeData[], edges: GEdgeData[], colW = 210, rowH = 120): PNode[] {
  const start = nodes.find((n) => n.start || n.is_initial) ?? nodes[0]
  const adj: Record<string, string[]> = {}
  edges.forEach((e) => { (adj[e.source] ||= []).push(e.target) })
  const depth: Record<string, number> = { [start.id]: 0 }
  const q = [start.id]
  while (q.length) {
    const u = q.shift() as string
    for (const v of adj[u] ?? []) if (!(v in depth)) { depth[v] = depth[u] + 1; q.push(v) }
  }
  const maxD = Math.max(0, ...Object.values(depth))
  nodes.forEach((n) => { if (!(n.id in depth)) depth[n.id] = maxD + 1 })
  const layers: Record<number, GNodeData[]> = {}
  nodes.forEach((n) => (layers[depth[n.id]] ||= []).push(n))
  const maxRows = Math.max(...Object.values(layers).map((l) => l.length))
  const out: PNode[] = []
  Object.entries(layers).forEach(([d, ns]) => {
    ns.forEach((n, i) => out.push({ ...n, x: 90 + Number(d) * colW, y: 90 + ((maxRows - ns.length) / 2 + i) * rowH }))
  })
  return nodes.map((n) => out.find((o) => o.id === n.id) as PNode)
}

export function layoutFor(nodes: GNodeData[], edges: GEdgeData[], grouped: boolean): PNode[] {
  return grouped ? layoutGroups(nodes) : layoutLayered(nodes, edges)
}

export function bbox(ns: PNode[], pad = 70) {
  if (!ns.length) return { x0: 0, y0: 0, x1: 600, y1: 400 }
  // extra room above (self-loops) and below (state names) the outermost nodes
  return { x0: Math.min(...ns.map((n) => n.x)) - pad, y0: Math.min(...ns.map((n) => n.y)) - pad - 34, x1: Math.max(...ns.map((n) => n.x)) + pad, y1: Math.max(...ns.map((n) => n.y)) + pad + 20 }
}
