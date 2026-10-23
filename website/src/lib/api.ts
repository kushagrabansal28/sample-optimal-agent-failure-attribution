// Typed client for the AFCR FastAPI backend. Every value shown in the UI comes from these calls.

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit, expect: 'json' | 'text' = 'json'): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, init)
  } catch (e) {
    if ((e as { name?: string })?.name === 'AbortError') throw new ApiError('Cancelled', -1)
    throw new ApiError('Cannot reach the API. Is the backend running on this origin (uvicorn afcr.api.app:app --port 8000)?', 0)
  }
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`
    try {
      const j = await res.json()
      if (typeof j.detail === 'string') msg = j.detail
      else if (Array.isArray(j.detail)) msg = j.detail.map((d: { loc?: string[]; msg: string }) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ')
    } catch { /* keep default message */ }
    throw new ApiError(msg, res.status)
  }
  const ct = res.headers.get('content-type') || ''
  if (expect === 'text') return res.text() as Promise<T>
  // A JSON endpoint that answers with something else (typically the web page for a mistyped route) is an error, not data.
  if (!ct.includes('json')) throw new ApiError(`Unexpected ${ct || 'non-JSON'} response from ${path.split('?')[0]} (is the endpoint path correct?)`, res.status)
  return res.json() as Promise<T>
}

const post = <T,>(path: string, body: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal })

// ---------------------------------------------------------------- types
export interface ExampleCase { label: string; word: string[]; expect: 'accept' | 'reject' | 'error' | 'unknown' | 'probability' | 'output'; note?: string }
export interface ModelInfo {
  id: string; name: string; definition: string; word: string[]; accepts: string; memory: string; nondeterminism: string
  probability: string; agent_fit: string; limits: string; kind?: string; description?: string; examples?: ExampleCase[]
}
export interface GNodeData {
  id: string; qid?: string; name?: string; sink?: boolean; dead?: boolean; label?: string; group?: string; kind?: string; role?: string; description?: string; attribution_note?: string
  start?: boolean; is_initial?: boolean; accepting?: boolean; rejecting?: boolean; output?: string; ref_action?: string
  policy?: Record<string, number>; [k: string]: unknown
}
export interface GEdgeData { source: string; target: string; label?: string; is_fault?: boolean; prob?: number | null; epsilon?: boolean; category?: string; op?: string; policy_prob?: number; kernel_prob?: number }
export interface GraphResponse {
  model?: string; name?: string; nodes: GNodeData[]; edges: GEdgeData[]; n_states: number; info?: ModelInfo
  groups?: Record<string, number>; horizon?: number; alphabet?: string[]; fault_symbols?: string[]; success_probability?: number
  count_logical_states?: number; state_count_validated?: boolean; view?: string
  transition_table?: Record<string, Record<string, string | string[]>>; closure_steps?: string[][]; witness?: string[][]; note?: string
  reachable?: string[]; deadlocks?: string[]; stack_bottom?: string; matrix_note?: string
  views?: string[]; view_note?: string; kind?: string
}
export interface TraceStepData { index: number; state: unknown; symbol: string | null; next_state: unknown; blocked?: boolean; stack_before?: string[]; stack_after?: string[]; op?: string; write?: string; move?: string; output?: string; p?: number; [k: string]: unknown }
export interface TapeConfig { step: number; state: string; head: number; tape: Record<string, string>; rendered?: string }
/** One response shape per machine kind. `steps` is always a list.  Only machines with an acceptance notion carry `accepted`. */
export interface TraceResponse {
  model: string; kind: string; word?: string[]; steps: TraceStepData[]
  accepted?: boolean | null; reason?: string; note?: string; halted?: boolean
  initial_active?: string[]; final_active?: string[]; final_state?: string
  blocked?: { state: string; label: string } | null; deadlocks?: string[]; end_states?: string[]
  outputs?: string[]
  sample_ended_accepting?: boolean; sample_blocked?: boolean; exact_acceptance_probability?: number
  monte_carlo?: { n: number; p_hat: number; ci_lo: number; ci_hi: number; successes?: number; level?: number }
  trace?: TapeConfig[]; n_steps?: number; status?: string; output?: string; unknown?: boolean
  success?: boolean; faults?: string[]; fault_steps?: number[]
}
export interface TrajStep {
  t: number; state: string; action: string; ref_action?: string; is_fault: boolean; group?: string; role?: string; note?: string
  next_state?: string; memory?: Record<string, number | null>
}
export interface TrajectoryResponse {
  steps: TrajStep[]; exact_mu: number[]; baseline_success: number; planted_arm: number | null; argmax_arm: number
  intervention: string; labels: string[]; outcome: string; synthetic: boolean
}
export interface ReplayPathStep { t: number; state: string; action: string; is_fault: boolean; forced: boolean; note?: string }
export interface ReplayResponse {
  original: TrajStep[]
  counterfactual: { arm: number; step: number; intervention: string; start_state: string; start_time: number; path: ReplayPathStep[]; terminal: string | null; success: boolean; timed_out: boolean; answer?: number | null; gold?: number }
  exact_mu: number; original_outcome: string; note: string
}
export interface EstimateResponse { arm: number; n: number; successes: number; mean: number; ci_lo: number; ci_hi: number; level: number; exact_mu: number; note: string }
export interface HistoryRound {
  round: number; pulls_before: number; arms: number[]; outcomes: number[]; shared: Record<string, number>
  mean?: number[]; lo?: number[]; hi?: number[]; counts?: number[]; suggested?: number[]; stop?: boolean
}
export interface AttributionResult {
  status: 'identified' | 'budget_exhausted' | 'fixed_budget_done' | 'oracle'
  selected: number | null; provisional: number | null; answer: number | null; candidate_set: number[]; certified_none: boolean
  guarantee_applies: boolean; guarantee_note: string; delta: number; total_rollouts: number; total_steps: number
  own_pulls: number[]; shared_obs: number[]; successes: number[]; counts: number[]; means: number[]; lo: number[]; hi: number[]
  eligible: boolean[]; rounds: number; wall_seconds: number; strategy: string; target: Record<string, unknown>; confidence: string
  share_mode: string; reason: string; history: HistoryRound[]; labels: string[]; sharing_valid: boolean
  ground_truth: { true_means: number[]; argmax_arm: number; planted_arm: number | null; labels: string[]; synthetic: boolean }
  trajectory?: TrajStep[]; steps?: number[]
}
export interface AttributeRequest {
  source: 'automaton' | 'bandit' | 'toolagent'; seed: number; n_states?: number; eps_plan?: number; gap?: number; K?: number; algorithm: string
  target?: string; eps?: number; theta?: number; delta: number; budget: number; share: string; confidence?: string
  intervention?: string; candidates?: string; reconstruct_noise?: number; deterministic?: boolean; history?: boolean
}
export interface ExpRow { method: string; seed: number; answer: number; truth: number; correct: number; correct_exact: number; identified: number; abstained: number; rollouts: number; shared: number; gap: number; n_arms: number }
export interface SummaryRow {
  n: number; accuracy: number; acc_ci_lo: number; acc_ci_hi: number; abstain_rate: number; identified_error_rate: number | null
  err_ci_lo: number | null; err_ci_hi: number | null; mean_rollouts: number; median_rollouts: number; p90_rollouts: number; rollouts_ci: [number, number]
  [k: string]: unknown
}
export interface GroupResult { group: string; n_trials_rows: number; summary: SummaryRow[] }
export interface PairedRow { a: string; b: string; n: number; mean_a?: number; mean_b?: number; mean_diff: number | null; ci: [number, number] | null; ratio: number | null; p: number | null; p_holm?: number | null; reject_holm_0_05?: boolean | null }
export interface FigureEntry { file: string; title: string; kind: 'conceptual' | 'experimental' | 'structural'; caption: string; source: string }
export interface ResultsIndex {
  available: boolean; groups: string[]; meta: { trials: number; groups: Record<string, { rows: number; wall_seconds: number }>; note: string } | null
  paired: PairedRow[] | null; figures: FigureEntry[] | null
}
export interface TestReport { available?: boolean; frontend?: { total: number; passed: number; failed: number; command: string }; total: number; passed: number; failed: number; skipped: number; modules: Record<string, { passed: number; failed: number; tests: Array<{ name: string; outcome: string }> }>; command: string; ran_at: string }
export interface OpenApi { paths: Record<string, Record<string, { summary?: string; description?: string; requestBody?: { content: Record<string, { schema: { $ref?: string } }> }; parameters?: Array<{ name: string; in: string; required?: boolean }> }>>; components?: { schemas?: Record<string, { properties?: Record<string, { type?: string; default?: unknown; description?: string; minimum?: number; maximum?: number; exclusiveMinimum?: number; exclusiveMaximum?: number }> }> } }

// ---------------------------------------------------------------- calls
export const api = {
  health: () => request<{ status: string; version: string }>('/api/health'),
  models: () => request<ModelInfo[]>('/api/automata/models'),
  graph: (model: string, opts: { view?: string; n_states?: number; eps_plan?: number } = {}) => {
    const q = new URLSearchParams({ model, ...(opts.view ? { view: opts.view } : {}), ...(opts.n_states ? { n_states: String(opts.n_states) } : {}), ...(opts.eps_plan != null ? { eps_plan: String(opts.eps_plan) } : {}) })
    return request<GraphResponse>(`/api/automata/graph?${q}`)
  },
  trace: (body: { model: string; word?: string[]; seed?: number; n_states?: number; view?: string }) => post<TraceResponse>('/api/automata/trace', body),
  compare: () => request<Array<{ id: string; name: string; definition: string; accepts: string; memory: string; nondeterminism: string; probability: string; agent_fit: string; limits: string }>>('/api/automata/compare'),
  trajectory: (body: { source: string; seed: number; eps_plan?: number; intervention?: string; deterministic?: boolean; n_states?: number }) => post<TrajectoryResponse>('/api/trajectory', body),
  replay: (body: { source: string; seed: number; arm: number; eps_plan?: number; intervention?: string; deterministic?: boolean; replay_seed?: number }) => post<ReplayResponse>('/api/replay', body),
  estimate: (body: { source: string; seed: number; arm: number; n: number; eps_plan?: number; intervention?: string; deterministic?: boolean }) => post<EstimateResponse>('/api/replay/estimate', body),
  attribute: (body: AttributeRequest, signal?: AbortSignal) => post<AttributionResult>('/api/attribute', body, signal),
  experiment: (body: Record<string, unknown>) => post<{ rows: ExpRow[]; summary: Array<SummaryRow & { method: string }>; synthetic: boolean; config: Record<string, unknown> }>('/api/experiment/run', body),
  resultsIndex: () => request<ResultsIndex>('/api/results/index'),
  group: (name: string) => request<GroupResult>(`/api/results/group/${name}`),
  rows: (group: string) => request<{ rows: Array<Record<string, string>> }>(`/api/results/export?fmt=json&group=${group}`),
  csvUrl: (group: string) => `/api/results/export?fmt=csv&group=${group}`,
  novelty: () => request<Array<Record<string, string>>>('/api/research/novelty'),
  related: () => request<Array<Record<string, string>>>('/api/research/related'),
  status: () => request<string>('/api/status', undefined, 'text'),
  tests: () => request<TestReport>('/api/tests'),
  openapi: () => request<OpenApi>('/openapi.json'),
}
