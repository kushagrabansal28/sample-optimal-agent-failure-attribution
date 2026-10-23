import { motion } from 'framer-motion'

export interface ForestRow { label: string; mean: number; lo: number; hi: number; n: number; truth?: number | null; own?: number; shared?: number; tag?: 'best' | 'challenger' | 'planted' | null; dim?: boolean }

/** Animated forest plot: one row per arm; interval bar, mean dot, optional ground-truth diamond, pull counts. */
export function ForestPlot({ rows, showTruth, selected, onSelect, height = 30, threshold }: { rows: ForestRow[]; showTruth?: boolean; selected?: number | null; onSelect?: (i: number) => void; height?: number; threshold?: number }) {
  const L = 185, R = 110, W = 800, pw = W - L - R, H = rows.length * height + 34
  const x = (v: number) => L + Math.min(1, Math.max(0, v)) * pw
  const maxN = Math.max(1, ...rows.map((r) => r.n))
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="group" aria-label="Confidence intervals per candidate step" className="forest">
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <g key={t}><line x1={x(t)} x2={x(t)} y1={6} y2={H - 26} stroke="var(--border)" /><text x={x(t)} y={H - 10} textAnchor="middle" style={{ fill: 'var(--muted)', font: '500 10.5px var(--font-mono)' }}>{t.toFixed(2)}</text></g>
      ))}
      {threshold != null && <g><line x1={x(threshold)} x2={x(threshold)} y1={4} y2={H - 26} stroke="var(--amber)" strokeDasharray="5 4" strokeWidth={1.6} /><text x={x(threshold)} y={H - 1} textAnchor="middle" style={{ fill: 'var(--amber)', font: '600 10.5px var(--font-sans)' }}>θ = {threshold}</text></g>}
      {rows.map((r, i) => {
        const y = 18 + i * height
        const col = r.tag === 'best' ? 'var(--cyan)' : r.tag === 'challenger' ? 'var(--amber)' : r.tag === 'planted' ? 'var(--red)' : 'var(--blue)'
        const sel = selected === i
        return (
          <g key={i} opacity={r.dim ? 0.35 : 1} onClick={() => onSelect?.(i)} style={{ cursor: onSelect ? 'pointer' : undefined }}
            tabIndex={onSelect ? 0 : undefined} role={onSelect ? 'button' : undefined} aria-pressed={onSelect ? sel : undefined}
            aria-label={onSelect ? `${r.label}: mean ${r.mean.toFixed(2)}, interval ${r.lo.toFixed(2)} to ${r.hi.toFixed(2)}, ${r.n} observations` : undefined}
            onKeyDown={onSelect ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(i) } } : undefined}>
            {sel && <rect x={0} y={y - height / 2 + 2} width={W} height={height - 4} rx={8} fill="color-mix(in srgb, var(--blue) 9%, transparent)" />}
            <text x={L - 12} y={y + 4} textAnchor="end" style={{ fill: sel ? 'var(--text)' : 'var(--text-2)', font: '500 11.5px var(--font-sans)' }}>{r.label.length > 30 ? r.label.slice(0, 29) + '…' : r.label}</text>
            <motion.line animate={{ x1: x(r.lo), x2: x(r.hi) }} initial={false} transition={{ type: 'spring', stiffness: 160, damping: 24 }} y1={y} y2={y} stroke={col} strokeWidth={5} strokeLinecap="round" opacity={0.35} />
            <motion.line animate={{ x1: x(r.lo), x2: x(r.lo) }} initial={false} y1={y - 6} y2={y + 6} stroke={col} strokeWidth={2} />
            <motion.line animate={{ x1: x(r.hi), x2: x(r.hi) }} initial={false} y1={y - 6} y2={y + 6} stroke={col} strokeWidth={2} />
            <motion.circle animate={{ cx: x(r.mean) }} initial={false} transition={{ type: 'spring', stiffness: 200, damping: 26 }} cy={y} r={5} fill={col} />
            {showTruth && r.truth != null && <motion.path d={`M 0 -6 L 6 0 L 0 6 L -6 0 Z`} animate={{ x: x(r.truth), y }} initial={false} fill="#fff" stroke="var(--bg)" strokeWidth={1.5}><title>true μ = {r.truth.toFixed(3)} (synthetic ground truth)</title></motion.path>}
            <rect x={W - R + 10} y={y - 4} width={70} height={8} rx={4} fill="var(--surface-3)" />
            <motion.rect x={W - R + 10} y={y - 4} height={8} rx={4} fill={col} opacity={0.8} animate={{ width: (r.n / maxN) * 70 }} initial={false} />
            <text x={W - 6} y={y + 4} textAnchor="end" style={{ fill: 'var(--muted)', font: '500 10.5px var(--font-mono)' }}>{r.n}</text>
          </g>
        )
      })}
    </svg>
  )
}

/** One estimate with its interval, the exact value (diamond) and a reference line. */
export function CIBar({ mean, lo, hi, exact, baseline, label = 'success probability' }: { mean: number; lo: number; hi: number; exact?: number; baseline?: number; label?: string }) {
  const W = 520, P = 14, x = (v: number) => P + v * (W - 2 * P)
  return (
    <svg viewBox={`0 0 ${W} 74`} width="100%" role="img" aria-label={`${label} estimate with confidence interval`}>
      <line x1={P} x2={W - P} y1={34} y2={34} stroke="var(--border-strong)" />
      {[0, 0.25, 0.5, 0.75, 1].map((t) => <g key={t}><line x1={x(t)} x2={x(t)} y1={30} y2={38} stroke="var(--border-strong)" /><text x={x(t)} y={58} textAnchor="middle" style={{ fill: 'var(--muted)', font: '500 10px var(--font-mono)' }}>{t}</text></g>)}
      {baseline != null && <g><line x1={x(baseline)} x2={x(baseline)} y1={14} y2={54} stroke="var(--amber)" strokeDasharray="4 3" /><text x={x(baseline)} y={10} textAnchor="middle" style={{ fill: 'var(--amber)', font: '600 10px var(--font-sans)' }}>baseline {baseline.toFixed(2)}</text></g>}
      <motion.rect initial={{ width: 0 }} animate={{ x: x(lo), width: Math.max(2, x(hi) - x(lo)) }} y={29} height={10} rx={5} fill="var(--blue)" opacity={0.45} />
      <motion.circle initial={{ cx: P }} animate={{ cx: x(mean) }} transition={{ type: 'spring', stiffness: 140, damping: 20 }} cy={34} r={6.5} fill="var(--blue)" stroke="var(--bg)" strokeWidth={2} />
      {exact != null && <path d={`M ${x(exact)} 24 L ${x(exact) + 7} 34 L ${x(exact)} 44 L ${x(exact) - 7} 34 Z`} fill="#fff" stroke="var(--bg)" strokeWidth={1.5}><title>exact μ = {exact.toFixed(3)}</title></path>}
    </svg>
  )
}

/** Heatmap (confusion matrix): rows = truth, columns = answer. */
export function Heatmap({ labels, matrix, colLabels, rowTitle = 'truth', colTitle = 'answer' }: { labels: string[]; matrix: number[][]; colLabels?: string[]; rowTitle?: string; colTitle?: string }) {
  const max = Math.max(1, ...matrix.flat())
  const cols = colLabels ?? labels
  return (
    <div>
      <div className="xs muted" style={{ marginBottom: 6 }}>rows: {rowTitle} · columns: {colTitle}</div>
      <div className="heat" style={{ gridTemplateColumns: `64px repeat(${cols.length}, minmax(34px, 1fr))` }} role="table" aria-label="Confusion matrix">
        <div />
        {cols.map((c) => <div key={c} className="xs muted" style={{ textAlign: 'center' }}>{c}</div>)}
        {matrix.map((row, i) => (
          <div key={i} style={{ display: 'contents' }}>
            <div className="xs muted" style={{ alignSelf: 'center' }}>{labels[i]}</div>
            {row.map((v, j) => <div key={j} className="heat-cell" title={`${rowTitle} ${labels[i]} → ${cols[j]}: ${v}`} style={{ background: v ? `color-mix(in srgb, ${i === j ? 'var(--green)' : 'var(--red)'} ${Math.round(18 + (v / max) * 70)}%, var(--surface-2))` : 'var(--surface-2)', color: v ? '#fff' : 'var(--muted)' }}>{v || '·'}</div>)}
          </div>
        ))}
      </div>
    </div>
  )
}
