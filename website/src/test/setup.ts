import '@testing-library/jest-dom/vitest'

// jsdom lacks these browser APIs
class RO { observe() {} unobserve() {} disconnect() {} }
;(globalThis as unknown as { ResizeObserver: typeof RO }).ResizeObserver = RO
if (!window.matchMedia) {
  window.matchMedia = ((q: string) => ({ matches: false, media: q, onchange: null, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false })) as unknown as typeof window.matchMedia
}
window.scrollTo = (() => {}) as typeof window.scrollTo
class IO { observe() {} unobserve() {} disconnect() {} takeRecords() { return [] } }
;(globalThis as unknown as { IntersectionObserver: typeof IO }).IntersectionObserver = IO

// Pages are code-split (lazy): the first render of a page can take longer than the 1 s default on a busy machine.
import { configure } from '@testing-library/react'
configure({ asyncUtilTimeout: 6000 })
