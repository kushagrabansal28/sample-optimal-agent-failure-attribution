/** Regression tests for the audited defects: blank pages after navigation, per-machine results, validation gating, stale parameters, threshold targets, zero-size graphs, accessibility, docs search. */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { GraphCanvas, groupEdges } from '../graph/GraphCanvas'
import { layoutLayered } from '../graph/layout'
import { stepGroups } from '../pages/Lab'
import { rangeOf } from '../pages/Docs'
import { ApiError, api } from '../lib/api'
import { BASE_ROUTES, GRAPH, MODELS, mockFetch, renderApp } from './helpers'

beforeEach(() => { window.localStorage.clear() })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

const info = (id: string, kind: string, examples: unknown[] = []) => ({ ...MODELS[1], id, name: id.toUpperCase(), kind, word: ['go'], examples, description: `${id} machine` })

describe('navigation never leaves a blank page', () => {
  it('shows the new page immediately (no opacity-0 start state), names it, and moves focus to its heading', async () => {
    mockFetch({ routes: BASE_ROUTES })
    const user = userEvent.setup()
    renderApp('/')
    await screen.findByRole('heading', { level: 1, name: /culprit identification/i })
    await user.click(screen.getByRole('link', { name: /Automata laboratory/i }))
    const h1 = await screen.findByRole('heading', { level: 1, name: /Automata laboratory/i })
    const main = document.getElementById('main-content') as HTMLElement
    expect(main.getAttribute('style') ?? '').not.toMatch(/opacity:\s*0/)
    expect(getComputedStyle(main).opacity).not.toBe('0')
    await waitFor(() => expect(document.title).toMatch(/Automata laboratory/))
    await waitFor(() => expect(document.activeElement).toBe(h1))
  })

  it('every page has exactly one h1 and one main landmark', { timeout: 40000 }, async () => {
    for (const path of ['/', '/related', '/lab', '/explorer', '/dashboard', '/studio', '/theory', '/reproducibility', '/docs']) {
      mockFetch({ routes: BASE_ROUTES })
      const { unmount } = renderApp(path)
      await screen.findAllByRole('heading', { level: 1 }, { timeout: 8000 })
      expect(screen.getAllByRole('heading', { level: 1 }), path).toHaveLength(1)
      expect(screen.getAllByRole('main'), path).toHaveLength(1)
      unmount()
    }
  })

  it('research metrics are exact on first render (no count-up frames)', async () => {
    mockFetch({ routes: { ...BASE_ROUTES, '/api/automata/graph': { ...GRAPH, count_logical_states: 48, groups: { PLAN: 8 } } } })
    renderApp('/')
    await waitFor(() => expect(document.querySelector('.kpis .stat .v')?.textContent).toBe('48'))
    expect([...document.querySelectorAll('.kpis .stat .v')].map((e) => e.textContent)[1]).toBe('3')
  })
})

describe('accessibility', () => {
  it('tabs follow the WAI-ARIA pattern: arrow keys move selection, tabs control panels', async () => {
    mockFetch({ routes: BASE_ROUTES })
    const user = userEvent.setup()
    renderApp('/lab?model=dfa')
    const first = await screen.findByRole('tab', { name: /Trace & playback/i })
    expect(first).toHaveAttribute('aria-selected', 'true')
    expect(first).toHaveAttribute('aria-controls')
    first.focus()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByRole('tab', { name: /Definition & semantics/i })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', screen.getByRole('tab', { name: /Definition & semantics/i }).id)
  })

  it('the mobile drawer takes focus and closes on Escape, returning focus to its button', async () => {
    mockFetch({ routes: BASE_ROUTES })
    const user = userEvent.setup()
    renderApp('/')
    const burger = await screen.findByRole('button', { name: /open menu/i })
    await user.click(burger)
    const side = document.querySelector('.sidebar') as HTMLElement
    expect(side).toHaveClass('open')
    expect(side.contains(document.activeElement)).toBe(true)
    await user.keyboard('{Escape}')
    expect(side).not.toHaveClass('open')
    expect(document.activeElement).toBe(screen.getByRole('button', { name: /open menu/i }))
  })

  it('related-work rows are keyboard operable', async () => {
    mockFetch({ routes: BASE_ROUTES })
    const user = userEvent.setup()
    renderApp('/related')
    const row = (await within(await screen.findByTestId('novelty-matrix')).findByText('Causal Agent Replay')).closest('tr') as HTMLElement
    expect(row).toHaveAttribute('tabindex', '0')
    row.focus()
    await user.keyboard('{Enter}')
    expect(row).toHaveAttribute('aria-selected', 'true')
  })
})

describe('forms cannot submit invalid values', () => {
  const result = { status: 'identified', selected: 1, provisional: 1, answer: 1, candidate_set: [1], certified_none: false, guarantee_applies: true, guarantee_note: 'ok', delta: 0.1, total_rollouts: 321, total_steps: 900,
    own_pulls: [100, 221], shared_obs: [0, 0], successes: [50, 180], counts: [100, 221], means: [0.5, 0.81], lo: [0.4, 0.74], hi: [0.6, 0.88], eligible: [true, true], rounds: 160, wall_seconds: 0.1, strategy: 'lucb',
    target: { name: 'argmax', eps: 0 }, confidence: 'stack_kl', share_mode: 'none', reason: '', history: [], labels: ['t=1: A', 't=2: B'], sharing_valid: true,
    ground_truth: { true_means: [0.5, 0.8], argmax_arm: 1, planted_arm: 1, labels: ['t=1: A', 't=2: B'], synthetic: true } }

  it('δ = 0 disables Run attribution and nothing is sent', async () => {
    const { calls } = mockFetch({ routes: { ...BASE_ROUTES, '/api/attribute': result } })
    const user = userEvent.setup()
    renderApp('/dashboard')
    const delta = await screen.findByTestId('delta')
    await user.clear(delta); await user.type(delta, '0')
    expect(delta).toHaveAttribute('aria-invalid', 'true')
    const run = screen.getByTestId('run-attribution')
    expect(run).toBeDisabled()
    expect(screen.getByTestId('form-invalid')).toBeInTheDocument()
    await user.click(run)
    expect(calls.filter((c) => c.url === '/api/attribute')).toHaveLength(0)
    await user.clear(delta); await user.type(delta, '0.05')
    expect(run).toBeEnabled()
  })

  it('a result stays tied to the configuration that produced it', async () => {
    const { calls } = mockFetch({ routes: { ...BASE_ROUTES, '/api/attribute': result } })
    const user = userEvent.setup()
    renderApp('/dashboard')
    await user.click(await screen.findByTestId('run-attribution'))
    await screen.findByText(/culprit certified/i)
    expect(screen.getByTestId('run-summary')).toHaveTextContent(/seed 5.*budget 20,000/)
    const budget = screen.getByTestId('budget')
    await user.clear(budget); await user.type(budget, '100000')
    expect(screen.getByText(/configuration on the left has changed/i)).toBeInTheDocument()
    expect(screen.getAllByText(/budget 20,000/).length).toBeGreaterThan(0)
    expect(screen.queryAllByText(/budget 100,000/)).toHaveLength(0)
    const seed = screen.getByLabelText('Seed')
    await user.clear(seed); await user.type(seed, '9')
    await user.click(screen.getByTestId('compare-uniform'))
    await waitFor(() => expect(calls.filter((c) => c.url === '/api/attribute')).toHaveLength(2))
    const cmp = JSON.parse(String(calls.filter((c) => c.url === '/api/attribute')[1].init?.body))
    expect(cmp).toMatchObject({ algorithm: 'uniform_fc', seed: 5, budget: 20000 })      // the identical instance, not the edited form
  })

  it('threshold targets show the threshold panel and are judged against the threshold answer', async () => {
    const thr = { ...result, target: { name: 'last_above', theta: 0.5, strict: false }, certified_none: false, answer: 1, selected: 1 }
    mockFetch({ routes: { ...BASE_ROUTES, '/api/attribute': thr } })
    const user = userEvent.setup()
    renderApp('/dashboard')
    await user.selectOptions(await screen.findByLabelText('Target'), 'last_above')
    await user.click(screen.getByTestId('run-attribution'))
    expect(await screen.findByTestId('threshold-panel')).toBeInTheDocument()
    expect(screen.getByText(/matches exact last step/i)).toBeInTheDocument()
    expect(screen.queryByText(/separation margin/i)).not.toBeInTheDocument()
  })

  it('exports the result and can cancel a running request', async () => {
    mockFetch({ routes: { ...BASE_ROUTES, '/api/attribute': result } })
    const user = userEvent.setup()
    renderApp('/dashboard')
    await user.click(await screen.findByTestId('run-attribution'))
    expect(await screen.findByTestId('export-attribution-json')).toBeInTheDocument()
    expect(screen.getByTestId('export-attribution-csv')).toBeInTheDocument()
    // cancel: a pending request that rejects with AbortError when aborted
    vi.stubGlobal('fetch', vi.fn((_: unknown, init?: RequestInit) => new Promise((_res, rej) => { init?.signal?.addEventListener('abort', () => rej(Object.assign(new Error('x'), { name: 'AbortError' }))) })))
    await user.click(screen.getByTestId('run-attribution'))
    await user.click(await screen.findByTestId('cancel-attribution'))
    await waitFor(() => expect(screen.getByTestId('run-attribution')).toBeEnabled())
    expect(screen.queryByTestId('error-message')).not.toBeInTheDocument()
  })
})

describe('trajectory explorer uses the loaded trajectory', () => {
  const traj = { steps: [{ t: 1, state: 'S0', action: 'a', ref_action: 'a', is_fault: false, group: 'PLAN', role: 'benign', next_state: 'S1' }, { t: 2, state: 'S1', action: 'b', ref_action: 'c', is_fault: true, group: 'PLAN', role: 'decision', next_state: 'S2' }],
    exact_mu: [0.4, 0.6], baseline_success: 0.4, planted_arm: 1, argmax_arm: 1, intervention: 'repair', labels: ['t=1: S0', 't=2: S1'], outcome: 'failure', synthetic: true }
  const replay = { original: [], counterfactual: { arm: 1, step: 2, intervention: 'repair', start_state: 'S1', start_time: 1, path: [], terminal: 'DONE', success: true, timed_out: false }, exact_mu: 0.6, original_outcome: 'failure', note: 'n' }
  it('replays with the parameters of the sampled trajectory, flags the stale form, and links to the dashboard', async () => {
    const { calls } = mockFetch({ routes: { ...BASE_ROUTES, '/api/trajectory': traj, '/api/replay': replay } })
    const user = userEvent.setup()
    renderApp('/explorer')
    await user.click(await screen.findByTestId('sample-traj'))
    await screen.findByText(/Exact intervention value/i)
    const seed = screen.getByLabelText('Seed')
    await user.clear(seed); await user.type(seed, '11')
    expect(await screen.findByTestId('stale-notice')).toBeInTheDocument()
    await user.click(screen.getByTestId('run-replay'))
    await waitFor(() => expect(calls.some((c) => c.url === '/api/replay')).toBe(true))
    expect(JSON.parse(String(calls.find((c) => c.url === '/api/replay')?.init?.body))).toMatchObject({ seed: 5, arm: 1 })
    expect(screen.getByTestId('attribute-this')).toHaveAttribute('href', expect.stringContaining('seed=5'))
  })
})

describe('automata laboratory results are specific to the machine', () => {
  const models = (...m: unknown[]) => [MODELS[0], ...m]
  const cfg = (step: number, state: string, head: number, tape: Record<string, string>) => ({ step, state, head, tape })

  it('probabilistic automaton: probability, no accepted/rejected verdict; an example case runs with its word', async () => {
    const ex = [{ label: 'go go go', word: ['go', 'go', 'go'], expect: 'probability' }]
    const trace = { model: 'pa', kind: 'pa', steps: [{ index: 0, state: 'q0', symbol: 'go', next_state: 'q1' }], sample_ended_accepting: true, exact_acceptance_probability: 0.868, monte_carlo: { n: 2000, p_hat: 0.87, ci_lo: 0.85, ci_hi: 0.88 } }
    const { calls } = mockFetch({ routes: { ...BASE_ROUTES, '/api/automata/models': models(info('pa', 'pa', ex)), '/api/automata/trace': trace } })
    const user = userEvent.setup()
    renderApp('/lab?model=pa')
    await user.click(await screen.findByTestId('example-case'))
    const panel = await screen.findByTestId('result-panel')
    expect(within(panel).getByText(/exact P\(accept\) = 0\.8680/)).toBeInTheDocument()
    expect(within(panel).queryByText(/^accepted$/)).not.toBeInTheDocument()
    expect(within(panel).queryByText(/^rejected$/)).not.toBeInTheDocument()
    expect(JSON.parse(String(calls.find((c) => c.url === '/api/automata/trace')?.init?.body)).word).toEqual(['go', 'go', 'go'])
  })

  it('transducers show outputs and no acceptance verdict', async () => {
    const trace = { model: 'mealy', kind: 'mealy', steps: [{ index: 0, state: 'q0', symbol: 'task', next_state: 'q1', output: 'call_tool' }], outputs: ['call_tool'] }
    mockFetch({ routes: { ...BASE_ROUTES, '/api/automata/models': models(info('mealy', 'mealy')), '/api/automata/trace': trace } })
    const user = userEvent.setup()
    renderApp('/lab?model=mealy')
    await user.click(await screen.findByTestId('run-trace'))
    const panel = await screen.findByTestId('result-panel')
    expect(within(panel).getByText(/no accepted\/rejected/i)).toBeInTheDocument()
    expect(within(panel).queryByText(/^accepted$/)).not.toBeInTheDocument()
  })

  it('a rejected PDA run still has steps to play back and says why it was rejected', async () => {
    const trace = { model: 'pda', kind: 'pda', accepted: false, reason: "stuck before reading 'ret' (input position 3): no transition from q0 with stack top Z",
      steps: [{ index: 0, state: 'q0', symbol: 'call', next_state: 'q0', stack_before: ['Z'], stack_after: ['C', 'Z'], op: 'push' }] }
    mockFetch({ routes: { ...BASE_ROUTES, '/api/automata/models': models(info('pda', 'pda')), '/api/automata/trace': trace } })
    const user = userEvent.setup()
    renderApp('/lab?model=pda')
    await user.click(await screen.findByTestId('run-trace'))
    expect(await screen.findByText(/^rejected$/)).toBeInTheDocument()
    expect(screen.getByTestId('reject-reason')).toHaveTextContent(/stuck before reading 'ret'/)
    expect(screen.getByText(/step 1\/1/)).toBeInTheDocument()
  })

  it('a Turing machine that hits its step limit is "unknown", never "reject"', async () => {
    const trace = { model: 'tm_loop', kind: 'tm', status: 'step_limit', unknown: true, accepted: null, halted: false, n_steps: 1, output: '', reason: 'simulator bound reached (step_limit): the machine did not halt — the answer is unknown, not \'reject\'',
      steps: [{ index: 0, state: 'q0', symbol: '0', next_state: 'q0', write: '0', move: 'R' }], trace: [cfg(0, 'q0', 0, { 0: '0' }), cfg(1, 'q0', 1, { 0: '0' })] }
    mockFetch({ routes: { ...BASE_ROUTES, '/api/automata/models': models(info('tm_loop', 'tm')), '/api/automata/trace': trace } })
    const user = userEvent.setup()
    renderApp('/lab?model=tm_loop')
    await user.click(await screen.findByTestId('run-trace'))
    const panel = await screen.findByTestId('result-panel')
    expect(within(panel).getByText(/unknown \(step_limit\)/)).toBeInTheDocument()
    expect(within(panel).queryByText(/^reject$/)).not.toBeInTheDocument()
    expect(await screen.findByText(/Trace computed \(1 step\)/)).toBeInTheDocument()       // a number, not "undefined steps"
  })

  it('step groups reveal exactly the edges of the steps taken (NFA sets contribute several edges, blocked steps none)', () => {
    const edges = [{ source: 'q0', target: 'q0', label: 'a' }, { source: 'q0', target: 'q1', label: 'a' }, { source: 'q1', target: 'q2', label: 'b' }, { source: 'q2', target: 'q3', label: 'ε', epsilon: true }]
    const g = stepGroups('nfa', [{ index: 0, state: ['q0'], symbol: 'a', next_state: ['q0', 'q1'] }, { index: 1, state: ['q0', 'q1'], symbol: 'b', next_state: ['q2', 'q3'] }], edges)
    expect(g.map((x) => x.length)).toEqual([2, 2])
    const lts = stepGroups('lts', [{ index: 0, state: 'q0', symbol: 'plan', next_state: 'q1' }, { index: 1, state: 'q1', symbol: 'x', next_state: null, blocked: true }], [])
    expect(lts[1]).toEqual([])
  })

  it('every state shows its q-number', async () => {
    const g = { ...GRAPH, nodes: [{ id: 'q0', qid: 'q0', name: 'start', label: 'start', start: true }, { id: 'q1', qid: 'q1', name: 'ok', label: 'ok', accepting: true }], edges: [{ source: 'q0', target: 'q1', label: 'a' }] }
    mockFetch({ routes: { ...BASE_ROUTES, '/api/automata/graph': g } })
    renderApp('/lab?model=dfa')
    expect(await screen.findByRole('button', { name: /State q0 start, initial/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /State q1 ok, accepting/ })).toBeInTheDocument()
  })
})

describe('graph canvas', () => {
  it('parallel edges are drawn once with a combined label', () => {
    const groups = groupEdges([{ source: 'a', target: 'b', label: 'x' }, { source: 'a', target: 'b', label: 'y' }, { source: 'b', target: 'a', label: 'z' }])
    expect(groups).toHaveLength(2)
    expect(groups[0].label).toBe('x, y')
  })

  it('never produces a degenerate transform for a container without size, and fits once it has one', () => {
    const observers: Array<() => void> = []
    class RO { constructor(cb: () => void) { observers.push(cb) } observe() {} unobserve() {} disconnect() {} }
    vi.stubGlobal('ResizeObserver', RO)
    let width = 0
    const spy = vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockImplementation(() => width)
    const nodes = layoutLayered(GRAPH.nodes, GRAPH.edges)
    const { container } = render(<MemoryRouter><GraphCanvas nodes={nodes} edges={GRAPH.edges} fitKey="k" /></MemoryRouter>)
    const g = () => container.querySelector('svg > g') as SVGGElement
    const ok = () => { const tr = g().getAttribute('transform') ?? ''; expect(tr).not.toMatch(/NaN|Infinity/); expect(tr).not.toMatch(/scale\(0\)/) }
    ok()
    fireEvent.wheel(container.querySelector('svg') as SVGSVGElement, { deltaY: -200 })        // user scrolls while the graph has no size
    ok()
    width = 500
    observers.forEach((cb) => cb())
    ok()
    expect(g().getAttribute('transform')).toMatch(/scale\(/)
    spy.mockRestore()
  })
})

describe('docs, related work and the API client', () => {
  it('range column keeps bounds of zero', () => {
    expect(rangeOf({ minimum: 0, exclusiveMaximum: 1 })).toBe('≥ 0, < 1')
    expect(rangeOf({ exclusiveMinimum: 0, maximum: 0.5 })).toBe('> 0, ≤ 0.5')
    expect(rangeOf({ type: 'integer' })).toBe('—')
  })

  it('searching the documentation finds terms inside sections (LUCB is defined in the glossary)', async () => {
    mockFetch({ routes: { ...BASE_ROUTES, '/openapi.json': { paths: {}, components: { schemas: {} } } } })
    const user = userEvent.setup()
    renderApp('/docs')
    await user.type(await screen.findByTestId('docs-search'), 'LUCB')
    expect(await screen.findByText(/Automata and statistics glossary/)).toBeInTheDocument()
    expect(screen.queryByText(/No documentation matches/i)).not.toBeInTheDocument()
  })

  it('the related-work filter finds a paper by acronym and explains an empty result', async () => {
    mockFetch({ routes: BASE_ROUTES })
    const user = userEvent.setup()
    renderApp('/related')
    const box = await screen.findByLabelText('Filter papers')
    await user.type(box, 'car')
    expect(within(screen.getByTestId('novelty-matrix')).getByText('Causal Agent Replay')).toBeInTheDocument()
    await user.clear(box); await user.type(box, 'zzzz')
    expect(await screen.findByText(/No paper matches/)).toBeInTheDocument()
  })

  it('a JSON endpoint that answers with the web page is an error, not data', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<!doctype html><title>x</title>', { status: 200, headers: { 'content-type': 'text/html; charset=utf-8' } })))
    const e = await api.models().catch((x) => x)
    expect(e).toBeInstanceOf(ApiError)
    expect((e as ApiError).message).toMatch(/Unexpected text\/html/)
  })
})
