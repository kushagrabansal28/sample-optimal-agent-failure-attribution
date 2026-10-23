import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, Check, ChevronRight, Copy, Info, Inbox, CheckCircle2 } from 'lucide-react'
import { useCallback, useEffect, useId, useMemo, useState, type ButtonHTMLAttributes, type KeyboardEvent, type ReactNode } from 'react'
import katex from 'katex'

// ------------------------------------------------------------------ Button / Badge / Card
interface BtnProps extends ButtonHTMLAttributes<HTMLButtonElement> { variant?: 'primary' | 'ghost' | 'default'; size?: 'sm' | 'md'; loading?: boolean; icon?: ReactNode }
export function Button({ variant = 'default', size = 'md', loading, icon, children, className = '', disabled, ...rest }: BtnProps) {
  return (
    <button className={`btn ${variant === 'primary' ? 'primary' : variant === 'ghost' ? 'ghost' : ''} ${size === 'sm' ? 'sm' : ''} ${!children ? 'icon' : ''} ${className}`} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? <span className="spinner" aria-hidden /> : icon}
      {children}
    </button>
  )
}

export type BadgeKind = 'syn' | 'ok' | 'pend' | 'info' | 'vio' | 'plain'
export function Badge({ kind = 'plain', children, title }: { kind?: BadgeKind; children: ReactNode; title?: string }) {
  return <span className={`badge ${kind}`} title={title}>{children}</span>
}
export const Synthetic = () => <Badge kind="syn" title="Produced by simulation with known ground truth - not a real-benchmark result">synthetic</Badge>
export const Measured = () => <Badge kind="ok" title="Computed from raw result files in results/">measured</Badge>
export const Pending = () => <Badge kind="pend" title="Not executed in this repository">pending</Badge>
export const Proved = () => <Badge kind="ok" title="A proof is given in the paper">proved</Badge>

export function Card({ title, icon, right, children, hover, className = '', style }: { title?: ReactNode; icon?: ReactNode; right?: ReactNode; children: ReactNode; hover?: boolean; className?: string; style?: React.CSSProperties }) {
  return (
    <section className={`card ${hover ? 'hover' : ''} ${className}`} style={style}>
      {(title || right) && (
        <div className="card-head">
          <h3>{icon}{title}</h3>
          {right}
        </div>
      )}
      {children}
    </section>
  )
}

/** Page title: the one <h1> of a page. The shell moves focus here after every navigation. */
export function PageHeader({ eyebrow, title, lead, right, compact }: { eyebrow?: string; title: ReactNode; lead?: ReactNode; right?: ReactNode; compact?: boolean }) {
  return (
    <header className={`page-head ${compact ? 'compact' : ''}`}>
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          <h1 id="page-title" tabIndex={-1} className="page-title">{title}</h1>
        </div>
        {right}
      </div>
      {lead && <p className="lead">{lead}</p>}
    </header>
  )
}

/** Greek letters and math symbols must keep their case inside upper-cased labels (δ is not Δ). */
export const Sym = ({ children }: { children: ReactNode }) => <span className="sym">{children}</span>

// ------------------------------------------------------------------ Form validity
/** Collects the validity of the number fields of one form so that submit buttons can be disabled while any field is invalid. */
export interface FormValidity { set: (id: string, invalid: boolean) => void; anyInvalid: boolean; messages: string[]; setMessage: (id: string, msg: string | null) => void }
export function useFormValidity(): FormValidity {
  const [bad, setBad] = useState<Record<string, string>>({})
  const setMessage = useCallback((id: string, msg: string | null) => setBad((b) => {
    if (msg == null) { if (!(id in b)) return b; const n = { ...b }; delete n[id]; return n }
    return b[id] === msg ? b : { ...b, [id]: msg }
  }), [])
  const set = useCallback((id: string, invalid: boolean) => setMessage(id, invalid ? 'invalid' : null), [setMessage])
  return useMemo(() => ({ set, setMessage, anyInvalid: Object.keys(bad).length > 0, messages: Object.values(bad) }), [bad, set, setMessage])
}

// ------------------------------------------------------------------ Form controls
export function Field({ label, hint, error, children, right }: { label: string; hint?: string; error?: string | null; children: ReactNode; right?: ReactNode }) {
  const id = useId()
  return (
    <div className="field">
      <label htmlFor={id}><span>{label}</span>{right}</label>
      {typeof children === 'function' ? null : (
        <div id={id} style={{ display: 'contents' }}>{children}</div>
      )}
      {error ? <span className="err-text" role="alert">{error}</span> : hint ? <span className="hint">{hint}</span> : null}
    </div>
  )
}

interface NumProps { label: ReactNode; value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number; int?: boolean; hint?: string; excludeMin?: boolean; excludeMax?: boolean; testId?: string; form?: FormValidity }
/** Validated number input: shows an inline error, reports valid values only and (with `form`) blocks submission while invalid. */
export function NumberField({ label, value, onChange, min, max, step, int, hint, excludeMin, excludeMax, testId, form }: NumProps) {
  const [text, setText] = useState(String(value))
  useEffect(() => { if (Number(text) !== value) setText(String(value)) /* eslint-disable-next-line */ }, [value])
  const n = Number(text)
  let error: string | null = null
  if (text.trim() === '' || Number.isNaN(n)) error = 'Enter a number'
  else if (int && !Number.isInteger(n)) error = 'Must be an integer'
  else if (min != null && (excludeMin ? n <= min : n < min)) error = `Must be ${excludeMin ? '>' : '≥'} ${min}`
  else if (max != null && (excludeMax ? n >= max : n > max)) error = `Must be ${excludeMax ? '<' : '≤'} ${max}`
  const id = useId()
  const report = form?.setMessage
  useEffect(() => {
    report?.(id, error)
    return () => report?.(id, null)
  }, [error, id, report])
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} data-testid={testId} className="input" type="text" inputMode="decimal" value={text} aria-invalid={error ? true : undefined} aria-describedby={`${id}-m`}
        onChange={(e) => { setText(e.target.value); const v = Number(e.target.value); if (e.target.value.trim() !== '' && !Number.isNaN(v)) { const bad = (int && !Number.isInteger(v)) || (min != null && (excludeMin ? v <= min : v < min)) || (max != null && (excludeMax ? v >= max : v > max)); if (!bad) onChange(v) } }} />
      <span id={`${id}-m`} className={error ? 'err-text' : 'hint'} role={error ? 'alert' : undefined}>{error ?? hint ?? (step ? '' : '')}</span>
    </div>
  )
}

export function SelectField({ label, value, onChange, options, hint }: { label: ReactNode; value: string; onChange: (v: string) => void; options: Array<{ value: string; label: string }>; hint?: string }) {
  const id = useId()
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} className="select" value={value} onChange={(e) => onChange(e.target.value)}>{options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
      {hint && <span className="hint">{hint}</span>}
    </div>
  )
}

export function SliderField({ label, value, onChange, min, max, step = 1, format }: { label: ReactNode; value: number; onChange: (v: number) => void; min: number; max: number; step?: number; format?: (v: number) => string }) {
  const id = useId()
  const p = ((value - min) / (max - min)) * 100
  return (
    <div className="field">
      <label htmlFor={id}><span>{label}</span><span className="mono" style={{ color: 'var(--text)' }}>{format ? format(value) : value}</span></label>
      <input id={id} className="range" type="range" min={min} max={max} step={step} value={value} style={{ ['--p' as string]: `${p}%` }} onChange={(e) => onChange(Number(e.target.value))} />
    </div>
  )
}

export function Segmented<T extends string>({ value, onChange, options, ariaLabel }: { value: T; onChange: (v: T) => void; options: Array<{ value: T; label: ReactNode }>; ariaLabel?: string }) {
  const gid = useId()
  return (
    <div className="seg" role="group" aria-label={ariaLabel}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={value === o.value} onClick={() => onChange(o.value)}>
          {value === o.value && <motion.span layoutId={`seg-${gid}`} className="seg-pill" transition={{ type: 'spring', stiffness: 500, damping: 36 }} />}
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <div className="switch">
      <button type="button" role="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)} />
      <span>{label}</span>
    </div>
  )
}

// ------------------------------------------------------------------ Tooltip, Skeleton, Callout, Empty
export function Tip({ text, children }: { text: ReactNode; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <span className="tip" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
      {children}
      <AnimatePresence>
        {open && <motion.span role="tooltip" className="tip-bubble" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>{text}</motion.span>}
      </AnimatePresence>
    </span>
  )
}

export function Skeleton({ h = 16, w = '100%', r }: { h?: number; w?: number | string; r?: number }) {
  return <div className="skeleton" style={{ height: h, width: w, borderRadius: r }} aria-hidden="true" />
}
export function SkeletonBlock({ rows = 4 }: { rows?: number }) {
  return <div className="stack" role="status" aria-label="Loading">{Array.from({ length: rows }, (_, i) => <Skeleton key={i} h={i === 0 ? 22 : 14} w={i === 0 ? '40%' : `${92 - i * 9}%`} />)}</div>
}

export function Callout({ kind = 'info', title, children }: { kind?: 'info' | 'warn' | 'err' | 'ok'; title?: string; children: ReactNode }) {
  const Icon = kind === 'warn' ? AlertTriangle : kind === 'err' ? AlertTriangle : kind === 'ok' ? CheckCircle2 : Info
  return (
    <div className={`callout ${kind}`} role={kind === 'err' ? 'alert' : undefined}>
      <Icon size={18} />
      <div>{title && <b style={{ color: 'var(--text)', display: 'block', marginBottom: 2 }}>{title}</b>}{children}</div>
    </div>
  )
}
export const ErrorBanner = ({ error, onRetry }: { error: Error; onRetry?: () => void }) => (
  <Callout kind="err" title="Request failed">
    <span data-testid="error-message">{error.message}</span>
    {onRetry && <div style={{ marginTop: 8 }}><Button size="sm" onClick={onRetry}>Retry</Button></div>}
  </Callout>
)
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="empty"><Inbox size={28} /><b style={{ color: 'var(--text-2)' }}>{title}</b><span className="small">{children}</span></div>
}

// ------------------------------------------------------------------ Disclosure / Tabs / CodeBlock
/** Content is rendered as soon as it is opened (no height/opacity animation that could leave it hidden). */
export function Disclosure({ title, children, defaultOpen = false, right }: { title: ReactNode; children: ReactNode; defaultOpen?: boolean; right?: ReactNode }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="disc">
      <button className="disc-trigger" aria-expanded={open} onClick={() => setOpen(!open)}>
        <ChevronRight size={16} className={`disc-chev ${open ? 'open' : ''}`} /> <span style={{ flex: 1 }}>{title}</span>{right}
      </button>
      {open && <div className="disc-body">{children}</div>}
    </div>
  )
}

/** WAI-ARIA tabs: arrow keys / Home / End move between tabs; pair with <TabPanel name=… id=…>. */
export function Tabs<T extends string>({ value, onChange, tabs, name = 'tabs', label }: { value: T; onChange: (v: T) => void; tabs: Array<{ id: T; label: ReactNode }>; name?: string; label?: string }) {
  const gid = useId()
  const onKey = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const k = e.key
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(k)) return
    e.preventDefault()
    const j = k === 'Home' ? 0 : k === 'End' ? tabs.length - 1 : (i + (k === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length
    onChange(tabs[j].id)
    document.getElementById(`${name}-tab-${tabs[j].id}`)?.focus()
  }
  return (
    <>
      <div className="tabs" role="tablist" aria-label={label}>
        {tabs.map((t, i) => (
          <button key={t.id} id={`${name}-tab-${t.id}`} role="tab" aria-selected={value === t.id} aria-controls={`${name}-panel-${t.id}`} tabIndex={value === t.id ? 0 : -1}
            onClick={() => onChange(t.id)} onKeyDown={(e) => onKey(e, i)}>
            {t.label}
            {value === t.id && <motion.span layoutId={`tab-${gid}`} className="tab-line" transition={{ type: 'spring', stiffness: 500, damping: 38 }} />}
          </button>
        ))}
      </div>
    </>
  )
}
export function TabPanel({ id, name, children, className, style }: { id: string; name: string; children: ReactNode; className?: string; style?: React.CSSProperties }) {
  return <div role="tabpanel" id={`${name}-panel-${id}`} aria-labelledby={`${name}-tab-${id}`} tabIndex={0} className={className} style={style}>{children}</div>
}

export function CopyButton({ text }: { text: string }) {
  const [ok, setOk] = useState(false)
  return (
    <Button size="sm" variant="ghost" className="copy" aria-label="Copy to clipboard" onClick={async () => { try { await navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 1400) } catch { /* ignore */ } }}>
      {ok ? <Check size={14} /> : <Copy size={14} />}
    </Button>
  )
}
export function CodeBlock({ code, lang }: { code: string; lang?: string }) {
  return (
    <div style={{ position: 'relative' }}>
      <pre className="code" data-lang={lang}><code style={{ background: 'none', border: 0, padding: 0 }}>{code}</code></pre>
      <CopyButton text={code} />
    </div>
  )
}

// ------------------------------------------------------------------ Math
export function Tex({ children, block }: { children: string; block?: boolean }) {
  const html = useMemo(() => katex.renderToString(children, { displayMode: !!block, throwOnError: false, strict: 'ignore' }), [children, block])
  return <span className={block ? 'katex-block' : undefined} dangerouslySetInnerHTML={{ __html: html }} />
}

// ------------------------------------------------------------------ Motion helpers
/** A research number is always shown exactly: no count-up animation (a half-finished animation frame once displayed 47 instead of 48). */
export function CountUp({ value, decimals = 0, suffix = '' }: { value: number; decimals?: number; suffix?: string; duration?: number }) {
  return <span className="num">{value.toFixed(decimals)}{suffix}</span>
}

export function Stat({ label, value, sub, decimals = 0, suffix = '', text }: { label: string; value?: number; sub?: ReactNode; decimals?: number; suffix?: string; text?: string }) {
  return (
    <div className="stat">
      <span className="l">{label}</span>
      <span className="v">{text ?? (value == null ? '—' : <CountUp value={value} decimals={decimals} suffix={suffix} />)}</span>
      {sub && <span className="s">{sub}</span>}
    </div>
  )
}

/** Entrance animations only ever move things (transform); content is never opacity:0, so a page can't stay blank if animation frames don't run. */
export const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.06 } } }
export const rise = { hidden: { y: 14 }, show: { y: 0, transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } } }
export function Reveal({ children, delay = 0, className, style }: { children: ReactNode; delay?: number; className?: string; style?: React.CSSProperties }) {
  return <div className={`reveal ${className ?? ''}`} style={{ ...style, animationDelay: delay ? `${delay}s` : undefined }}>{children}</div>
}

// ------------------------------------------------------------------ DataTable
export interface Col<R> { key: string; label: string; render?: (r: R) => ReactNode; num?: boolean; wrap?: boolean; sortValue?: (r: R) => number | string }
export function DataTable<R>({ cols, rows, onRowClick, empty = 'No rows', rowKey, selected }: { cols: Array<Col<R>>; rows: R[]; onRowClick?: (r: R) => void; empty?: string; rowKey?: (r: R, i: number) => string; selected?: (r: R) => boolean }) {
  const [sort, setSort] = useState<{ k: string; dir: 1 | -1 } | null>(null)
  const sorted = useMemo(() => {
    if (!sort) return rows
    const c = cols.find((x) => x.key === sort.k)
    if (!c) return rows
    const val = (r: R) => (c.sortValue ? c.sortValue(r) : ((r as Record<string, unknown>)[c.key] as number | string))
    return [...rows].sort((a, b) => { const x = val(a), y = val(b); return (x < y ? -1 : x > y ? 1 : 0) * sort.dir })
  }, [rows, sort, cols])
  if (!rows.length) return <Empty title={empty} />
  return (
    <div className="tbl-wrap">
      <table className="tbl">
        <thead><tr>{cols.map((c) => (
          <th key={c.key} className={c.wrap ? 'wrap' : ''} aria-sort={sort?.k === c.key ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'} onClick={() => setSort((s) => (s?.k === c.key ? { k: c.key, dir: (s.dir * -1) as 1 | -1 } : { k: c.key, dir: 1 }))} style={c.num ? { textAlign: 'right' } : undefined}>
            {c.label}{sort?.k === c.key ? (sort.dir === 1 ? ' ↑' : ' ↓') : ''}
          </th>))}</tr></thead>
        <tbody>
          {sorted.map((r, i) => (
            <tr key={rowKey ? rowKey(r, i) : i} onClick={onRowClick ? () => onRowClick(r) : undefined}
              tabIndex={onRowClick ? 0 : undefined} aria-selected={onRowClick ? !!selected?.(r) : undefined}
              onKeyDown={onRowClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onRowClick(r) } } : undefined}
              style={{ cursor: onRowClick ? 'pointer' : undefined, background: selected?.(r) ? 'color-mix(in srgb, var(--blue) 10%, transparent)' : undefined }}>
              {cols.map((c) => <td key={c.key} className={`${c.num ? 'n' : ''} ${c.wrap ? 'wrap' : ''}`}>{c.render ? c.render(r) : String((r as Record<string, unknown>)[c.key] ?? '')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function useDebounced<T>(v: T, ms = 200): T {
  const [d, setD] = useState(v)
  useEffect(() => { const t = setTimeout(() => setD(v), ms); return () => clearTimeout(t) }, [v, ms])
  return d
}
export const Legend = ({ items }: { items: Array<{ color: string; label: string }> }) => (
  <div className="legend">{items.map((i) => <span key={i.label}><i style={{ background: i.color }} />{i.label}</span>)}</div>
)
