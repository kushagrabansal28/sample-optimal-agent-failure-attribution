// Route audit: direct navigation + refresh, sidebar click navigation, back/forward, active state, console errors, KPI timing.
import { launch } from './cdp.mjs'
import fs from 'node:fs'
const EV = process.argv[2]
const b = await launch({ port: 9341 })
await b.viewport(1440, 900)
const ROUTES = ['/', '/related', '/lab', '/explorer', '/dashboard', '/studio', '/theory', '/reproducibility', '/docs', '/does-not-exist']
const out = { direct: [], kpiTimeline: [], sidebar: [], history: [] }
for (const r of ROUTES) {
  const c0 = b.log.console.length, e0 = b.log.exceptions.length, n0 = b.log.network.length
  await b.goto(r, 3500)
  const info = await b.eval(`(()=>{const m=document.querySelector('main.page'); return {path:location.pathname, title:document.title, h:[...document.querySelectorAll('main.page h1, main.page h2')].slice(0,2).map(e=>e.textContent.trim().slice(0,60)), textLen:(m?.innerText||'').length, active:document.querySelector('a.nav-item.active')?.textContent?.trim()||null, skeletons:document.querySelectorAll('.skeleton').length, errors:[...document.querySelectorAll('.callout.err, .error-banner, [role=alert]')].map(e=>e.textContent.trim().slice(0,120)), hOverflow: document.documentElement.scrollWidth>document.documentElement.clientWidth, h1count:document.querySelectorAll('h1').length}})()`)
  info.route = r
  info.console = b.log.console.slice(c0).filter((c) => /error|warn/i.test(c.type))
  info.exceptions = b.log.exceptions.slice(e0)
  info.network = b.log.network.slice(n0)
  out.direct.push(info)
  await b.shot(`${EV}/route_${r === '/' ? 'home' : r.slice(1)}_1440.png`)
}
// KPI timeline right after load
await b.goto('/', 0)
for (let i = 0; i < 30; i++) { await b.sleep(60); out.kpiTimeline.push([i * 60, await b.eval(`[...document.querySelectorAll('.kpis .stat .v')].map(e=>e.textContent).join(' | ')`)]) }
out.kpiTimeline = out.kpiTimeline.filter((s, i, a) => i === 0 || s[1] !== a[i - 1][1])
// Sidebar click navigation from home, in order
await b.goto('/', 2000)
for (const label of ['Problem & related work', 'Automata laboratory', 'Trajectory explorer', 'Attribution dashboard', 'Experiment studio', 'Theory & guarantees', 'Reproducibility', 'Documentation', 'Overview']) {
  const r = await b.clickText('a.nav-item', label)
  await b.sleep(2200)
  out.sidebar.push(await b.eval(`(()=>({clicked:${JSON.stringify(label)}, path:location.pathname, active:document.querySelector('a.nav-item.active')?.textContent?.trim(), mains:document.querySelectorAll('main.page').length, h:document.querySelector('main.page h1, main.page h2')?.textContent?.trim().slice(0,60), scrollY:scrollY, focused:document.activeElement?.tagName+'.'+(document.activeElement?.className||'')}))()`))
  out.sidebar[out.sidebar.length - 1].result = r
}
// Lab graph after client-side navigation
await b.clickText('a.nav-item', 'Automata laboratory'); await b.sleep(3000)
out.labAfterClientNav = await b.eval(`(()=>{const s=document.querySelector('.graph-svg'); const g=s?.querySelector(':scope>g'); return {w:s?.getBoundingClientRect().width, transform:g?.getAttribute('transform'), nodes:s?.querySelectorAll('.g-node').length}})()`)
// back / forward
await b.eval('history.back()'); await b.sleep(1500); out.history.push(await b.eval(`location.pathname + ' | ' + document.querySelector('main.page h1, main.page h2')?.textContent?.trim().slice(0,40) + ' | active=' + document.querySelector('a.nav-item.active')?.textContent?.trim()`))
await b.eval('history.back()'); await b.sleep(1500); out.history.push(await b.eval(`location.pathname + ' | ' + document.querySelector('main.page h1, main.page h2')?.textContent?.trim().slice(0,40)`))
await b.eval('history.forward()'); await b.sleep(1500); out.history.push(await b.eval(`location.pathname + ' | ' + document.querySelector('main.page h1, main.page h2')?.textContent?.trim().slice(0,40)`))
// refresh on nested route with query
await b.goto('/lab?model=pda', 3500)
out.refreshNested = await b.eval(`({path:location.pathname+location.search, pressed:[...document.querySelectorAll('.model-item[aria-pressed=true]')].map(e=>e.textContent), nodes:document.querySelectorAll('.g-node').length})`)
out.allConsole = b.log.console.filter((c) => /error|warn/i.test(c.type))
out.allExceptions = b.log.exceptions
out.apiRequests = [...new Set(b.log.requests.map((r) => `${r.status} ${r.url.split('?')[0]}`))]
fs.writeFileSync(`${EV}/01_routes.json`, JSON.stringify(out, null, 1))
console.log(JSON.stringify(out, null, 1).slice(0, 9000))
await b.close()
