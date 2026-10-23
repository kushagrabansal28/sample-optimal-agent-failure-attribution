import { motion } from 'framer-motion'
import { BookOpen, FileText, FlaskConical, Gauge, Home, Menu, Moon, Network, Package, Route, Sigma, Sun, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync, useLocalStorage } from '../lib/hooks'
import { Background, Cursor } from './Cursor'

export const NAV = [
  { to: '/', label: 'Overview', icon: Home, group: 'Project' },
  { to: '/related', label: 'Problem & related work', icon: BookOpen, group: 'Project' },
  { to: '/lab', label: 'Automata laboratory', icon: Network, group: 'Instruments' },
  { to: '/explorer', label: 'Trajectory explorer', icon: Route, group: 'Instruments' },
  { to: '/dashboard', label: 'Attribution dashboard', icon: Gauge, group: 'Instruments' },
  { to: '/studio', label: 'Experiment studio', icon: FlaskConical, group: 'Instruments' },
  { to: '/theory', label: 'Theory & guarantees', icon: Sigma, group: 'Reference' },
  { to: '/reproducibility', label: 'Reproducibility', icon: Package, group: 'Reference' },
  { to: '/docs', label: 'Documentation', icon: FileText, group: 'Reference' },
] as const

function Logo() {
  return (
    <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
      <defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#5b9dff" /><stop offset="1" stopColor="#9b8cff" /></linearGradient></defs>
      <path d="M9 10 L16 23 M23 9 L16 23 M9 10 L23 9" stroke="#8a97b4" strokeWidth="1.5" fill="none" />
      <circle cx="9" cy="10" r="3.2" fill="url(#lg)" /><circle cx="23" cy="9" r="3.2" fill="#35d6e0" /><circle cx="16" cy="23" r="4" fill="#ff6b7a" />
    </svg>
  )
}

const APP = 'AFCR'

export function Shell({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useLocalStorage<'dark' | 'light'>('afcr-theme', 'dark')
  const [open, setOpen] = useState(false)
  const loc = useLocation()
  const health = useAsync(() => api.health(), [])
  const toggleRef = useRef<HTMLButtonElement>(null)
  const sideRef = useRef<HTMLElement>(null)
  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])

  // Route change: close the drawer, scroll to the top, name the page in the tab title and move focus to the page heading.
  const first = useRef(true)
  useEffect(() => {
    const item = NAV.find((n) => (n.to === '/' ? loc.pathname === '/' : loc.pathname.startsWith(n.to)))
    document.title = item ? `${item.label} · ${APP}` : `Page not found · ${APP}`
    if (first.current) { first.current = false; return }           // the first load needs no announcement
    setOpen(false)
    window.scrollTo({ top: 0 })
    // Focus goes to the new page's heading only if the user has not put it somewhere else themselves (e.g. an input they started typing in).
    const focusTitle = (fromNav: boolean) => {
      const a = document.activeElement
      const parked = !a || a === document.body || a.id === 'main-content' || a.id === 'page-title' || (fromNav && !!a.closest('.sidebar, .topbar'))
      const el = document.getElementById('page-title') ?? document.getElementById('main-content')
      if (parked && el && a !== el) el.focus({ preventScroll: true })
    }
    const t1 = setTimeout(() => focusTitle(true), 40)
    const t2 = setTimeout(() => focusTitle(false), 500)            // lazy pages may mount their heading a moment later
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [loc.pathname])

  // Mobile drawer: focus moves in, Tab is trapped, Escape closes and returns focus to the menu button.
  const close = useCallback(() => { setOpen(false); toggleRef.current?.focus() }, [])
  useEffect(() => {
    if (open) sideRef.current?.querySelector<HTMLElement>('a, button')?.focus()
  }, [open])
  const onSideKey = (e: KeyboardEvent<HTMLElement>) => {
    if (!open) return
    if (e.key === 'Escape') { e.preventDefault(); close(); return }
    if (e.key !== 'Tab') return
    const f = Array.from(sideRef.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])') ?? [])
    if (!f.length) return
    const first = f[0], last = f[f.length - 1]
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
  }
  const groups = Array.from(new Set(NAV.map((n) => n.group)))

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <Background />
      <Cursor />
      <div className="app">
        <aside ref={sideRef} className={`sidebar ${open ? 'open' : ''}`} aria-label="Primary" onKeyDown={onSideKey}>
          <NavLink to="/" className="brand" aria-label="AFCR home">
            <span className="brand-mark"><Logo /></span>
            <span><b>AFCR</b><span>Agent failure attribution</span></span>
          </NavLink>
          <nav className="nav" aria-label="Pages">
            {groups.map((g) => (
              <div key={g}>
                <div className="nav-sep">{g}</div>
                {NAV.filter((n) => n.group === g).map((n) => (
                  <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    {({ isActive }) => (
                      <>
                        {isActive && <motion.span layoutId="nav-pill" className="nav-pill" transition={{ type: 'spring', stiffness: 520, damping: 40 }} />}
                        <n.icon size={17} />
                        <span>{n.label}</span>
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
          <div className="side-foot">
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <span className="row" style={{ gap: 7 }} title={health.error ? health.error.message : 'API reachable'}>
                <span style={{ width: 8, height: 8, borderRadius: 99, background: health.loading ? 'var(--amber)' : health.error ? 'var(--red)' : 'var(--green)', boxShadow: `0 0 10px ${health.error ? 'var(--red)' : 'var(--green)'}` }} />
                {health.loading ? 'connecting…' : health.error ? 'API offline' : `API v${health.data?.version}`}
              </span>
              <button className="btn icon ghost sm" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
                {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
              </button>
            </div>
            <div style={{ lineHeight: 1.45 }}>Kushagra Yogendra Bansal <span className="mono">25bde0080</span><br />Kartik Kesharwani <span className="mono">25bde0053</span></div>
          </div>
        </aside>
        {open && <div className="scrim" onClick={close} aria-hidden />}
        <div className="main">
          <div className="topbar">
            <button ref={toggleRef} className="btn icon ghost" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} onClick={() => (open ? close() : setOpen(true))}>{open ? <X size={18} /> : <Menu size={18} />}</button>
            <b style={{ fontFamily: 'var(--font-display)' }}>AFCR</b>
          </div>
          {/* Plain element, no exit animation and no hidden initial state: the new page is visible the moment the route changes. */}
          <main key={loc.pathname} id="main-content" tabIndex={-1} className="page">
            {children}
          </main>
        </div>
      </div>
    </>
  )
}
