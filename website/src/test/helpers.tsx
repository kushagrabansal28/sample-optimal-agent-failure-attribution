import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import App from '../App'

type Handler = unknown | ((url: string, init?: RequestInit) => unknown)
export interface MockOpts { routes: Record<string, Handler>; fail?: Record<string, { status: number; detail?: unknown }> }

/** Install a fetch mock. Keys are matched as URL prefixes (longest first); a function value is called with (url, init). */
export function mockFetch({ routes, fail = {} }: MockOpts) {
  const calls: Array<{ url: string; init?: RequestInit }> = []
  const f = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString()
    calls.push({ url, init })
    const failKey = Object.keys(fail).sort((a, b) => b.length - a.length).find((k) => url.startsWith(k))
    if (failKey) {
      const { status, detail } = fail[failKey]
      return new Response(JSON.stringify({ detail }), { status, headers: { 'content-type': 'application/json' } })
    }
    const key = Object.keys(routes).sort((a, b) => b.length - a.length).find((k) => url.startsWith(k))
    if (!key) return new Response(JSON.stringify({ detail: `no mock for ${url}` }), { status: 404, headers: { 'content-type': 'application/json' } })
    const h = routes[key]
    const body = typeof h === 'function' ? (h as (u: string, i?: RequestInit) => unknown)(url, init) : h
    return new Response(typeof body === 'string' ? body : JSON.stringify(body), { status: 200, headers: { 'content-type': typeof body === 'string' ? 'text/plain' : 'application/json' } })
  })
  vi.stubGlobal('fetch', f)
  return { f, calls }
}

export const GRAPH = {
  model: 'dfa', n_states: 3, info: { id: 'dfa', name: 'DFA', definition: 'd', word: ['a'], accepts: 'x', memory: 'finite', nondeterminism: 'none', probability: 'none', agent_fit: 'f', limits: 'l' },
  nodes: [{ id: 'even', label: 'even', start: true, accepting: true }, { id: 'odd', label: 'odd' }, { id: 'sink', label: 'sink' }],
  edges: [{ source: 'even', target: 'odd', label: 'a' }, { source: 'odd', target: 'even', label: 'a' }, { source: 'even', target: 'even', label: 'b' }],
  transition_table: { even: { a: 'odd', b: 'even' }, odd: { a: 'even', b: 'odd' } },
}
export const MODELS = [
  { id: 'agent48', name: '48-state agent automaton', definition: 'd', word: [], accepts: 'a', memory: 'm', nondeterminism: 'n', probability: 'p', agent_fit: 'f', limits: 'l' },
  { id: 'dfa', name: 'DFA', definition: 'd', word: ['a', 'b'], accepts: 'a', memory: 'm', nondeterminism: 'n', probability: 'p', agent_fit: 'f', limits: 'l' },
  { id: 'nfa', name: 'NFA', definition: 'd', word: ['a'], accepts: 'a', memory: 'm', nondeterminism: 'n', probability: 'p', agent_fit: 'f', limits: 'l' },
]
export const BASE_ROUTES: Record<string, Handler> = {
  '/api/health': { status: 'ok', version: '0.2.0' },
  '/api/tests': { available: true, total: 3, passed: 3, failed: 0, skipped: 0, modules: { test_x: { passed: 3, failed: 0, tests: [{ name: 'test_dfa_a', outcome: 'passed' }] } }, command: 'pytest', ran_at: 't' },
  '/api/results/index': { available: true, groups: ['main'], meta: { trials: 2, groups: { main: { rows: 4, wall_seconds: 1 } }, note: 'n' }, paired: null, figures: [] },
  '/api/automata/models': MODELS,
  '/api/automata/compare': [],
  '/api/automata/graph': GRAPH,
  '/api/research/novelty': [{ paper_id: 'CAR2026', short_name: 'Causal Agent Replay', arxiv_or_venue: 'arXiv:2606.08275', read_depth: 'FULL', step_level_attribution: 'Yes', counterfactual_replay: 'Yes', adaptive_allocation: 'No', fixed_confidence_stopping: 'No', delta_pac_guarantee: 'No', prefix_aware_information_reuse: 'No', formal_automata_representation: 'No', proven_sample_complexity_bound: 'No', real_agent_benchmarks: 'No', evidence_notes: 'notes' }],
  '/api/research/related': [],
}

export function renderApp(path = '/') {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}
