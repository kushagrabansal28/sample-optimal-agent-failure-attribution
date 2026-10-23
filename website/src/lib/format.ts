export const fmt = (x: number | null | undefined, d = 2): string => (x == null || Number.isNaN(x) ? '—' : x.toFixed(d))
export const pct = (x: number | null | undefined, d = 0): string => (x == null || Number.isNaN(x) ? '—' : `${(x * 100).toFixed(d)}%`)
export const int = (x: number | null | undefined): string => (x == null || Number.isNaN(x) ? '—' : Math.round(x).toLocaleString('en-US'))
export const compact = (x: number): string => (Math.abs(x) >= 1000 ? `${(x / 1000).toFixed(x >= 10000 ? 0 : 1)}k` : String(Math.round(x)))
export const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x))

export const GROUP_COLORS: Record<string, string> = {
  PLAN: 'var(--g-PLAN)', OBSERVE: 'var(--g-OBSERVE)', TOOL: 'var(--g-TOOL)', MEMORY: 'var(--g-MEMORY)', VALIDATE: 'var(--g-VALIDATE)', TERMINAL: 'var(--g-TERMINAL)',
}
export const METHOD_LABEL: Record<string, string> = {
  lucb: 'LUCB', lucb_prefix: 'LUCB + prefix reuse', lucb_naive_share: 'LUCB + naive sharing (invalid)', successive_elim: 'Successive elimination',
  uniform_fc: 'Uniform (same stop)', random_fc: 'Random (same stop)', equal_budget: 'Equal budget', random_budget: 'Random budget',
  car_fixed_k: 'CAR-style K=100', car_fixed_k500: 'CAR-style K=500', oracle: 'Oracle', successive_elim_prefix: 'SE + prefix reuse',
}
export const METHOD_COLOR: Record<string, string> = {
  lucb: '#5b9dff', lucb_prefix: '#35d6e0', lucb_naive_share: '#ff6b7a', successive_elim: '#9b8cff', uniform_fc: '#f5b84a', random_fc: '#c98a5b',
  equal_budget: '#8794b0', random_budget: '#6b7691', car_fixed_k: '#ff9ec4', car_fixed_k500: '#ff7aa8', oracle: '#4ade9a',
}
export const SHORT_LABEL: Record<string, string> = {
  lucb: 'LUCB', lucb_prefix: 'LUCB+prefix', lucb_naive_share: 'LUCB+naive*', successive_elim: 'Succ. elim.', uniform_fc: 'Uniform', random_fc: 'Random',
  equal_budget: 'Equal budget', random_budget: 'Random budget', car_fixed_k: 'CAR-style', car_fixed_k500: 'CAR-style 500', oracle: 'Oracle',
}
export const short = (m: string) => SHORT_LABEL[m] ?? m
export const label = (m: string) => METHOD_LABEL[m] ?? m
export const mcolor = (m: string) => METHOD_COLOR[m] ?? '#5b9dff'

export function downloadText(text: string, filename: string, mime = 'text/plain') {
  const url = URL.createObjectURL(new Blob([text], { type: mime }))
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function toCsv(rows: Array<Record<string, unknown>>): string {
  if (!rows.length) return ''
  const keys = Array.from(new Set(rows.flatMap((r) => Object.keys(r))))
  const esc = (v: unknown) => { const s = v == null ? '' : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s }
  return [keys.join(','), ...rows.map((r) => keys.map((k) => esc(r[k])).join(','))].join('\n')
}
