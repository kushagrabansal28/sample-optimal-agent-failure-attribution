import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { GraphCanvas } from '../graph/GraphCanvas'
import { layoutLayered } from '../graph/layout'
import { ApiError, api } from '../lib/api'
import { toCsv } from '../lib/format'
import { BASE_ROUTES, GRAPH, mockFetch, renderApp } from './helpers'

beforeEach(() => { window.localStorage.clear() })
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('navigation', () => {
  it('navigates between pages from the sidebar', async () => {
    mockFetch({ routes: BASE_ROUTES })
    const user = userEvent.setup()
    renderApp('/')
    expect(await screen.findByRole('heading', { level: 1, name: /culprit identification/i })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: /Problem & related work/i }))
    expect(await screen.findByRole('heading', { name: /What is known, and where is the gap/i })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: /Theory & guarantees/i }))
    expect(await screen.findByRole('heading', { name: /Theory and what is actually proved/i })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: /Documentation/i }))
    expect((await screen.findAllByRole('heading', { name: /^Reference$/ })).length).toBeGreaterThan(0)
  })

  it('shows a not-found page for unknown routes', async () => {
    mockFetch({ routes: BASE_ROUTES })
    renderApp('/nope')
    expect(await screen.findByText(/Page not found/i)).toBeInTheDocument()
  })

  it('marks the active page and toggles the mobile menu', async () => {
    mockFetch({ routes: BASE_ROUTES })
    const user = userEvent.setup()
    renderApp('/')
    const home = await screen.findByRole('link', { name: /^Overview$/i })
    expect(home).toHaveClass('active')
    const burger = screen.getByRole('button', { name: /open menu/i })
    expect(burger).toHaveAttribute('aria-expanded', 'false')
    await user.click(burger)
    expect(screen.getByRole('button', { name: /close menu/i })).toHaveAttribute('aria-expanded', 'true')
    expect(document.querySelector('.sidebar')).toHaveClass('open')
  })
})

describe('overview data', () => {
  it('shows live test counts from the API, not hard-coded values', async () => {
    mockFetch({ routes: { ...BASE_ROUTES, '/api/tests': { available: true, total: 123, passed: 120, failed: 3, skipped: 0, modules: {}, command: 'x', ran_at: 'now' } } })
    renderApp('/')
    await waitFor(() => expect(screen.getByText(/of 123/)).toBeInTheDocument())
  })
})

describe('automata laboratory', () => {
  const routes = { ...BASE_ROUTES, '/api/automata/trace': { model: 'dfa', kind: 'dfa', accepted: true, steps: [{ index: 0, state: 'even', symbol: 'a', next_state: 'odd' }, { index: 1, state: 'odd', symbol: 'a', next_state: 'even' }] } }

  it('switches models and requests the matching graph', async () => {
    const { calls } = mockFetch({ routes })
    const user = userEvent.setup()
    renderApp('/lab')
    await user.click(await screen.findByTestId('model-nfa'))
    await waitFor(() => expect(calls.some((c) => c.url.includes('/api/automata/graph?model=nfa'))).toBe(true))
    expect(screen.getByTestId('model-nfa')).toHaveAttribute('aria-pressed', 'true')
  })

  it('runs a trace and reports acceptance', async () => {
    mockFetch({ routes })
    const user = userEvent.setup()
    renderApp('/lab?model=dfa')
    const btn = await screen.findByTestId('run-trace')
    await user.click(btn)
    expect(await screen.findByText(/accepted/i)).toBeInTheDocument()
  })

  it('surfaces a backend validation error in the UI', async () => {
    mockFetch({ routes, fail: { '/api/automata/trace': { status: 422, detail: "symbol 'z' is not in the alphabet ['a', 'b']" } } })
    const user = userEvent.setup()
    renderApp('/lab?model=dfa')
    await user.click(await screen.findByTestId('run-trace'))
    expect(await screen.findByTestId('error-message')).toHaveTextContent(/not in the alphabet/)
  })

  it('shows a loading skeleton and then an error with retry when the graph fails', async () => {
    mockFetch({ routes, fail: { '/api/automata/graph': { status: 500, detail: 'boom' } } })
    renderApp('/lab?model=dfa')
    expect(await screen.findByText('boom')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /retry/i }).length).toBeGreaterThan(0)
  })
})

describe('graph canvas', () => {
  const nodes = layoutLayered(GRAPH.nodes, GRAPH.edges)
  it('renders every node and selects on click and Enter', () => {
    const onSelect = vi.fn()
    render_graph(onSelect)
    const items = screen.getAllByRole('button', { name: /State/ })
    expect(items).toHaveLength(3)
    fireEvent.click(items[1])
    expect(onSelect).toHaveBeenLastCalledWith('odd')
    fireEvent.keyDown(items[0], { key: 'Enter' })
    expect(onSelect).toHaveBeenLastCalledWith('even')
  })
  it('dims non-matching states while searching', () => {
    render_graph(vi.fn(), 'odd')
    const odd = screen.getByRole('button', { name: /State odd/ })
    const even = screen.getByRole('button', { name: /State even/ })
    expect(Number(odd.getAttribute('opacity'))).toBeGreaterThan(Number(even.getAttribute('opacity')))
  })
  function render_graph(onSelect: (id: string | null) => void, query = '') {
    return renderGraph(nodes, onSelect, query)
  }
})

import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { PNode } from '../graph/layout'
function renderGraph(nodes: PNode[], onSelect: (id: string | null) => void, query: string) {
  return render(<MemoryRouter><GraphCanvas nodes={nodes} edges={GRAPH.edges} onSelect={onSelect} query={query} /></MemoryRouter>)
}

describe('input validation', () => {
  it('flags invalid δ and budget inputs on the dashboard', async () => {
    mockFetch({ routes: BASE_ROUTES })
    const user = userEvent.setup()
    renderApp('/dashboard')
    const delta = await screen.findByTestId('delta')
    await user.clear(delta); await user.type(delta, '1.5')
    expect(delta).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getAllByRole('alert').some((a) => /Must be </.test(a.textContent ?? ''))).toBe(true)
    await user.clear(delta); await user.type(delta, '0.05')
    expect(delta).not.toHaveAttribute('aria-invalid')
    const budget = screen.getByTestId('budget')
    await user.clear(budget); await user.type(budget, '12.5')
    expect(budget).toHaveAttribute('aria-invalid', 'true')
  })
})

describe('attribution dashboard', () => {
  const result = {
    status: 'identified', selected: 1, provisional: 1, answer: 1, candidate_set: [1], certified_none: false, guarantee_applies: true, guarantee_note: 'δ-correct under assumptions A1–A6 (paper Thm 1)',
    delta: 0.1, total_rollouts: 321, total_steps: 900, own_pulls: [100, 221], shared_obs: [0, 0], successes: [50, 180], counts: [100, 221], means: [0.5, 0.81], lo: [0.4, 0.74], hi: [0.6, 0.88],
    eligible: [true, true], rounds: 160, wall_seconds: 0.1, strategy: 'lucb', target: { name: 'argmax', eps: 0 }, confidence: 'stack_kl', share_mode: 'none', reason: '', history: [],
    labels: ['t=1: A', 't=2: B'], sharing_valid: true, ground_truth: { true_means: [0.5, 0.8], argmax_arm: 1, planted_arm: 1, labels: ['t=1: A', 't=2: B'], synthetic: true },
  }
  it('runs the algorithm via the API and renders its outputs', async () => {
    const { calls } = mockFetch({ routes: { ...BASE_ROUTES, '/api/attribute': result } })
    const user = userEvent.setup()
    renderApp('/dashboard')
    await user.click(await screen.findByTestId('run-attribution'))
    expect(await screen.findByText(/culprit certified/i)).toBeInTheDocument()
    expect(await screen.findByText('321', {}, { timeout: 4000 })).toBeInTheDocument()
    expect(screen.getByText(/δ-guarantee/i)).toBeInTheDocument()
    const post = calls.find((c) => c.url === '/api/attribute')
    expect(post?.init?.method).toBe('POST')
    expect(JSON.parse(String(post?.init?.body))).toMatchObject({ delta: 0.1, budget: 20000, algorithm: 'lucb' })
  })
  it('explains an abstention instead of presenting a verdict', async () => {
    mockFetch({ routes: { ...BASE_ROUTES, '/api/attribute': { ...result, status: 'budget_exhausted', selected: null, guarantee_applies: false, answer: 1 } } })
    const user = userEvent.setup()
    renderApp('/dashboard')
    await user.click(await screen.findByTestId('run-attribution'))
    expect(await screen.findByText(/Abstention, not a verdict/i)).toBeInTheDocument()
  })
  it('shows API errors', async () => {
    mockFetch({ routes: BASE_ROUTES, fail: { '/api/attribute': { status: 422, detail: 'delta must lie in (0, 1)' } } })
    const user = userEvent.setup()
    renderApp('/dashboard')
    await user.click(await screen.findByTestId('run-attribution'))
    expect(await screen.findByTestId('error-message')).toHaveTextContent(/delta must lie/)
  })
})

describe('experiment studio', () => {
  const exp = {
    rows: [{ method: 'lucb', seed: 0, answer: 1, truth: 1, correct: 1, correct_exact: 1, identified: 1, abstained: 0, rollouts: 100, shared: 0, gap: 0.2, n_arms: 3 },
           { method: 'lucb', seed: 1, answer: 1, truth: 1, correct: 1, correct_exact: 1, identified: 1, abstained: 0, rollouts: 140, shared: 0, gap: 0.2, n_arms: 3 }],
    summary: [{ method: 'lucb', n: 2, accuracy: 1, acc_ci_lo: 0.34, acc_ci_hi: 1, abstain_rate: 0, certified_rate: 1, identified_error_rate: 0, err_ci_lo: 0, err_ci_hi: 0.6, mean_rollouts: 120, median_rollouts: 120, p90_rollouts: 140, rollouts_ci: [100, 140] }],
    synthetic: true, config: {},
  }
  it('runs a real simulation request and enables CSV/JSON export', async () => {
    const { calls } = mockFetch({ routes: { ...BASE_ROUTES, '/api/experiment/run': exp } })
    const user = userEvent.setup()
    renderApp('/studio')
    await user.click(await screen.findByRole('tab', { name: /Run simulation/i }))
    expect(screen.queryByTestId('export-csv')).not.toBeInTheDocument()
    await user.click(await screen.findByTestId('run-experiment'))
    const csv = await screen.findByTestId('export-csv')
    expect(screen.getByTestId('export-json')).toBeInTheDocument()
    const req = calls.find((c) => c.url === '/api/experiment/run')
    expect(JSON.parse(String(req?.init?.body))).toMatchObject({ source: 'bandit', delta: 0.1 })
    // export triggers a download
    const create = vi.fn(() => 'blob:x'); const revoke = vi.fn()
    ;(URL as unknown as { createObjectURL: unknown }).createObjectURL = create; (URL as unknown as { revokeObjectURL: unknown }).revokeObjectURL = revoke
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    await user.click(csv)
    expect(create).toHaveBeenCalledTimes(1)
    expect(click).toHaveBeenCalled()
  })
  it('validates the trial count before running', async () => {
    mockFetch({ routes: BASE_ROUTES })
    const user = userEvent.setup()
    renderApp('/studio')
    await user.click(await screen.findByRole('tab', { name: /Run simulation/i }))
    const trials = await screen.findByTestId('trials')
    await user.clear(trials); await user.type(trials, '500')
    expect(trials).toHaveAttribute('aria-invalid', 'true')
  })
  it('shows an empty state when no saved results exist', async () => {
    mockFetch({ routes: { ...BASE_ROUTES, '/api/results/index': { available: false, groups: [], meta: null, paired: null, figures: null } } })
    renderApp('/studio')
    expect(await screen.findByText(/No saved results/i)).toBeInTheDocument()
  })
  it('shows an error banner with retry when results cannot be loaded', async () => {
    mockFetch({ routes: BASE_ROUTES, fail: { '/api/results/index': { status: 500, detail: 'disk error' } } })
    renderApp('/studio')
    expect(await screen.findByText('disk error')).toBeInTheDocument()
    expect(within(document.body).getAllByRole('button', { name: /retry/i }).length).toBeGreaterThan(0)
  })
})

describe('related work', () => {
  it('renders the evidence matrix from the API and opens details', async () => {
    mockFetch({ routes: BASE_ROUTES })
    renderApp('/related')
    const matrix = await screen.findByTestId('novelty-matrix')
    expect(within(matrix).getByText('Causal Agent Replay')).toBeInTheDocument()
    expect(within(matrix).getAllByText('Yes').length).toBeGreaterThan(0)
  })
})

describe('documentation search', () => {
  it('filters sections by the search term and shows an empty state', async () => {
    mockFetch({ routes: { ...BASE_ROUTES, '/openapi.json': { paths: {}, components: { schemas: {} } } } })
    const user = userEvent.setup()
    renderApp('/docs')
    const box = await screen.findByTestId('docs-search')
    expect(screen.getByText(/Troubleshooting/)).toBeInTheDocument()
    await user.type(box, 'paging file')
    await waitFor(() => expect(screen.queryByText(/Input–output specification/)).not.toBeInTheDocument())
    expect(screen.getByText(/Troubleshooting/)).toBeInTheDocument()
    await user.clear(box); await user.type(box, 'zzzzqqq')
    expect(await screen.findByText(/No documentation matches/i)).toBeInTheDocument()
  })
})

describe('api client', () => {
  it('turns FastAPI validation details into readable messages', async () => {
    mockFetch({ routes: {}, fail: { '/api/attribute': { status: 422, detail: [{ loc: ['body', 'delta'], msg: 'Input should be less than 1' }] } } })
    await expect(api.attribute({ source: 'bandit', seed: 0, algorithm: 'lucb', delta: 2, budget: 10, share: 'none' })).rejects.toThrow(/delta: Input should be less than 1/)
  })
  it('reports an unreachable backend clearly', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('network') }))
    const e = await api.health().catch((x) => x)
    expect(e).toBeInstanceOf(ApiError)
    expect((e as ApiError).message).toMatch(/Cannot reach the API/)
    expect((e as ApiError).status).toBe(0)
  })
})

describe('export helpers', () => {
  it('serialises CSV with quoting', () => {
    expect(toCsv([{ a: 1, b: 'x,y' }, { a: 2, b: 'q"r' }])).toBe('a,b\n1,"x,y"\n2,"q""r"')
    expect(toCsv([])).toBe('')
  })
})
