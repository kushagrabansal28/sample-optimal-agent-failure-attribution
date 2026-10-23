import { useEffect, useRef } from 'react'

const HOVER = 'a,button,[role="button"],[role="tab"],label,summary,select,.g-node,.step-card,.pipe-step,[data-cursor="hover"]'
const TEXT = 'input[type="text"],input[type="number"],input[type="search"],textarea'

/** Dot + spring ring cursor with hover / press / drag / text states. Disabled on touch and for reduced motion. Also drives the spotlight. */
export function Cursor() {
  const dot = useRef<HTMLDivElement>(null)
  const ring = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fine = typeof window.matchMedia === 'function' && window.matchMedia('(pointer: fine)').matches
    const reduce = typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const root = document.documentElement
    let x = window.innerWidth / 2, y = window.innerHeight / 2, rx = x, ry = y, raf = 0, active = false

    const setSpot = () => { root.style.setProperty('--mx', `${x}px`); root.style.setProperty('--my', `${y}px`) }
    let running = false
    const loop = () => {
      rx += (x - rx) * 0.2; ry += (y - ry) * 0.2
      if (ring.current) ring.current.style.transform = `translate3d(${rx}px,${ry}px,0)`
      if (Math.abs(x - rx) > 0.15 || Math.abs(y - ry) > 0.15) raf = requestAnimationFrame(loop)
      else running = false                                    // idle: no work until the pointer moves again
    }
    const kick = () => { if (!running) { running = true; raf = requestAnimationFrame(loop) } }
    const move = (e: PointerEvent) => {
      x = e.clientX; y = e.clientY
      if (dot.current) dot.current.style.transform = `translate3d(${x}px,${y}px,0)`
      setSpot()
      if (!active) { active = true; root.classList.add('cursor-on'); rx = x; ry = y }
      kick()
    }
    const over = (e: Event) => {
      const t = e.target as Element | null
      if (!t || !t.closest) return
      root.classList.toggle('cursor-text', !!t.closest(TEXT))
      root.classList.toggle('cursor-hover', !!t.closest(HOVER) && !t.closest(TEXT))
    }
    const down = (e: PointerEvent) => {
      root.classList.add('cursor-down')
      if ((e.target as Element).closest?.('.graph-svg')) root.classList.add('cursor-drag')
    }
    const up = () => root.classList.remove('cursor-down', 'cursor-drag')
    const leave = () => { root.classList.remove('cursor-on'); active = false }
    window.addEventListener('pointermove', move, { passive: true })
    if (!fine || reduce) {
      return () => window.removeEventListener('pointermove', move)
    }
    document.addEventListener('pointerover', over)
    window.addEventListener('pointerdown', down)
    window.addEventListener('pointerup', up)
    document.documentElement.addEventListener('mouseleave', leave)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('pointermove', move)
      document.removeEventListener('pointerover', over)
      window.removeEventListener('pointerdown', down)
      window.removeEventListener('pointerup', up)
      document.documentElement.removeEventListener('mouseleave', leave)
      root.classList.remove('cursor-on', 'cursor-hover', 'cursor-text', 'cursor-down', 'cursor-drag')
    }
  }, [])

  return (
    <>
      <div ref={ring} className="cursor-ring" aria-hidden="true" />
      <div ref={dot} className="cursor-dot" aria-hidden="true" />
    </>
  )
}

export function Background() {
  return (
    <div className="bg-layer" aria-hidden="true">
      <div className="bg-aurora" />
      <div className="bg-grid" />
      <div className="bg-spot" />
    </div>
  )
}
