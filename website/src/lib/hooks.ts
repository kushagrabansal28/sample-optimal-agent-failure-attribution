import { useCallback, useEffect, useRef, useState } from 'react'

/** Chart animations are skipped when the OS asks for reduced motion (also keeps screenshots deterministic). */
export const ANIMATE = typeof window === 'undefined' || !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

export interface AsyncState<T> { data: T | null; error: Error | null; loading: boolean; reload: () => void }

/** Run an async function on mount / when deps change; ignores stale responses. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const id = useRef(0)
  useEffect(() => {
    const my = ++id.current
    setLoading(true); setError(null)
    fn().then(
      (d) => { if (my === id.current) { setData(d); setLoading(false) } },
      (e: Error) => { if (my === id.current) { setError(e); setLoading(false) } },
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])
  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, error, loading, reload }
}

export function useLocalStorage<T>(key: string, initial: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => {
    try { const raw = localStorage.getItem(key); return raw ? (JSON.parse(raw) as T) : initial } catch { return initial }
  })
  const set = useCallback((n: T) => { setV(n); try { localStorage.setItem(key, JSON.stringify(n)) } catch { /* private mode */ } }, [key])
  return [v, set]
}

export function useMedia(query: string): boolean {
  const get = () => (typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(query).matches : false)
  const [m, setM] = useState(get)
  useEffect(() => {
    if (!window.matchMedia) return
    const mq = window.matchMedia(query)
    const h = () => setM(mq.matches)
    mq.addEventListener('change', h)
    return () => mq.removeEventListener('change', h)
  }, [query])
  return m
}

export function useInterval(fn: () => void, ms: number | null) {
  const saved = useRef(fn)
  useEffect(() => { saved.current = fn }, [fn])
  useEffect(() => {
    if (ms == null) return
    const id = setInterval(() => saved.current(), ms)
    return () => clearInterval(id)
  }, [ms])
}
