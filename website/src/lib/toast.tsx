import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

type Kind = 'ok' | 'err' | 'info'
interface Toast { id: number; kind: Kind; text: string }
const Ctx = createContext<{ push: (kind: Kind, text: string) => void }>({ push: () => {} })
export const useToast = () => useContext(Ctx)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([])
  const push = useCallback((kind: Kind, text: string) => {
    const id = Date.now() + Math.random()
    setItems((s) => [...s.slice(-3), { id, kind, text }])
    setTimeout(() => setItems((s) => s.filter((t) => t.id !== id)), kind === 'err' ? 7000 : 3800)
  }, [])
  const value = useMemo(() => ({ push }), [push])
  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        <AnimatePresence>
          {items.map((t) => (
            <motion.div key={t.id} className={`toast ${t.kind}`} initial={{ y: 16 }} animate={{ y: 0 }} exit={{ opacity: 0, x: 40 }} transition={{ type: 'spring', stiffness: 380, damping: 30 }}>
              {t.kind === 'err' ? <AlertTriangle size={18} color="var(--red)" /> : t.kind === 'ok' ? <CheckCircle2 size={18} color="var(--green)" /> : <Info size={18} color="var(--blue)" />}
              <span>{t.text}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  )
}
