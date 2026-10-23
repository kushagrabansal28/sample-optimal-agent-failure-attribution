import { Suspense, lazy } from 'react'
import { Route, Routes } from 'react-router-dom'
import { ToastProvider } from './lib/toast'
import { Shell } from './ui/Shell'
import { Callout, SkeletonBlock, Button } from './ui/kit'
import { Link } from 'react-router-dom'
import Overview from './pages/Overview'

const Related = lazy(() => import('./pages/Related'))
const Lab = lazy(() => import('./pages/Lab'))
const Explorer = lazy(() => import('./pages/Explorer'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Studio = lazy(() => import('./pages/Studio'))
const Theory = lazy(() => import('./pages/Theory'))
const Reproducibility = lazy(() => import('./pages/Reproducibility'))
const Docs = lazy(() => import('./pages/Docs'))

function NotFound() {
  return (
    <div className="stack" style={{ maxWidth: 560 }}>
      <h2>Page not found</h2>
      <Callout kind="warn">That route does not exist. Use the navigation to pick a page.</Callout>
      <Link to="/" style={{ textDecoration: 'none' }}><Button variant="primary">Back to overview</Button></Link>
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <Shell>
        <Suspense fallback={<div className="card"><SkeletonBlock rows={6} /></div>}>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/related" element={<Related />} />
            <Route path="/lab" element={<Lab />} />
            <Route path="/explorer" element={<Explorer />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/studio" element={<Studio />} />
            <Route path="/theory" element={<Theory />} />
            <Route path="/reproducibility" element={<Reproducibility />} />
            <Route path="/docs" element={<Docs />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </Shell>
    </ToastProvider>
  )
}
