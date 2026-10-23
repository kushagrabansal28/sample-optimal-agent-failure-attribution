// Workflow tests: explorer, dashboard, studio, docs, reproducibility — capturing request bodies to verify what is really sent.
import { launch } from './cdp.mjs'
import fs from 'node:fs'
const EV = process.argv[2]
const b = await launch({ port: 9345 })
await b.viewport(1440, 900)
const out = {}
const setInput = (sel, v, nth = 0) => b.eval(`(()=>{const i=document.querySelectorAll(${JSON.stringify(sel)})[${nth}]; if(!i) return 'NOT FOUND'; const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i, ${JSON.stringify(String(v))}); i.dispatchEvent(new Event('input',{bubbles:true})); return 'ok'})()`)
const setSelect = (label, v) => b.eval(`(()=>{const f=[...document.querySelectorAll('.field')].find(f=>f.querySelector('label')?.textContent.trim().startsWith(${JSON.stringify(label)})); const s=f?.querySelector('select'); if(!s) return 'NOT FOUND'; const set=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set; set.call(s, ${JSON.stringify(v)}); s.dispatchEvent(new Event('change',{bubbles:true})); return 'ok'})()`)
const inputOf = (label) => `[...document.querySelectorAll('.field')].find(f=>f.querySelector('label')?.textContent.trim().startsWith(${JSON.stringify(label)}))?.querySelector('input')`
// capture fetch bodies
const hook = `(()=>{ if(window.__hooked) return; window.__hooked=1; window.__reqs=[]; const of=window.fetch; window.fetch=async(u,i)=>{ window.__reqs.push({u:String(u), body:i?.body?JSON.parse(i.body):null}); return of(u,i) } })()`

// ---------------- Explorer
await b.goto('/explorer', 2000); await b.eval(hook)
await b.click('[data-testid=sample-traj]'); await b.sleep(2500)
out.explorer_loaded = await b.eval(`({steps:document.querySelectorAll('.steps-scroll .step-card').length, sel:document.querySelector('.step-card.sel .st')?.textContent, chart:!!document.querySelector('[data-testid=mu-chart] svg'), seq:[...document.querySelectorAll('.steps-scroll .step-card .st')].map(e=>e.textContent).join('>')})`)
// change seed WITHOUT resampling, then replay
await b.eval(`(()=>{const i=${inputOf('Seed')}; const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'11'); i.dispatchEvent(new Event('input',{bubbles:true}))})()`)
await b.sleep(300)
await b.click('[data-testid=run-replay]'); await b.sleep(2500)
out.explorer_stale = await b.eval(`({lastReq: window.__reqs.filter(r=>r.u.includes('/api/replay')).slice(-1)[0], shownTrajectory:[...document.querySelectorAll('.steps-scroll .step-card .st')].map(e=>e.textContent).join('>'), replayOriginal:[...document.querySelectorAll('.grid.cols-2 > div:first-child .stack .chip:not(:nth-child(3))')].map(e=>e.textContent).filter((_,i)=>i%2===0).join('>'), err:[...document.querySelectorAll('[data-testid=error-message]')].map(e=>e.textContent)})`)
await b.shot(`${EV}/explorer_stale_seed_replay.png`, true)
// estimate
await b.goto('/explorer?autoload=1', 3500); await b.eval(hook)
await b.click('[data-testid=run-estimate]'); await b.sleep(3500)
out.explorer_estimate = await b.eval(`(document.querySelector('.card .stack .small')?.parentElement?.innerText||'').slice(0,300)`)
// toolagent
await b.clickText('.seg button', 'Tool agent'); await b.sleep(300); await b.click('[data-testid=sample-traj]'); await b.sleep(2500)
out.explorer_tool = await b.eval(`({steps:document.querySelectorAll('.steps-scroll .step-card').length, err:[...document.querySelectorAll('[data-testid=error-message]')].map(e=>e.textContent)})`)
await b.shot(`${EV}/explorer_toolagent.png`)

// ---------------- Dashboard
await b.goto('/dashboard', 2000); await b.eval(hook)
// invalid delta then run: what is sent?
await b.eval(`(()=>{const i=document.querySelector('[data-testid=delta]'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'0'); i.dispatchEvent(new Event('input',{bubbles:true}))})()`)
await b.sleep(200)
out.dash_invalid_delta_ui = await b.eval(`({fieldError:document.querySelector('[data-testid=delta]').parentElement.querySelector('.err-text')?.textContent, runDisabled:document.querySelector('[data-testid=run-attribution]').disabled})`)
await b.click('[data-testid=run-attribution]'); await b.sleep(4000)
out.dash_invalid_delta_sent = await b.eval(`window.__reqs.filter(r=>r.u.includes('/api/attribute')).slice(-1)[0]?.body?.delta`)
// restore delta, run threshold target
await b.eval(`(()=>{const i=document.querySelector('[data-testid=delta]'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'0.1'); i.dispatchEvent(new Event('input',{bubbles:true}))})()`)
out.dash_target_set = await setSelect('Target', 'last_above'); await b.sleep(300)
await b.click('[data-testid=run-attribution]'); await b.sleep(6000)
out.dash_last_above = await b.eval(`(()=>{const cards=[...document.querySelectorAll('.card')]; const stop=cards.find(c=>c.querySelector('h3')?.textContent.includes('Stopping rule')); const kp=document.querySelector('.kpis'); return {kpis:(kp?.innerText||'').slice(0,400), stopping:(stop?.innerText||'').slice(0,400), suggestedLabel:[...document.querySelectorAll('p.mono.xs.muted')].map(e=>e.textContent).join(' ').slice(0,200)}})()`)
await b.shot(`${EV}/dashboard_last_above.png`, true)
// change budget after run: is the result display re-computed with the new budget?
await setSelect('Target', 'argmax'); await b.sleep(200)
await b.click('[data-testid=run-attribution]'); await b.sleep(6000)
const before = await b.eval(`[...document.querySelectorAll('.card')].find(c=>c.querySelector('h3')?.textContent.includes('Stopping rule'))?.innerText.match(/budget used\\s*(\\d+%)/)?.[1]`)
await b.eval(`(()=>{const i=document.querySelector('[data-testid=budget]'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'100000'); i.dispatchEvent(new Event('input',{bubbles:true}))})()`)
await b.sleep(1500)
const after = await b.eval(`[...document.querySelectorAll('.card')].find(c=>c.querySelector('h3')?.textContent.includes('Stopping rule'))?.innerText.match(/budget used\\s*(\\d+%)/)?.[1]`)
out.dash_budget_used_before_after_edit = { before, after, rolloutsSub: await b.eval(`[...document.querySelectorAll('.kpis .stat')][1]?.innerText`) }
// compare uniform + export availability
await b.click('[data-testid=compare-uniform]'); await b.sleep(8000)
out.dash_compare = await b.eval(`[...document.querySelectorAll('.card')].find(c=>c.querySelector('h3')?.textContent.includes('Compare with uniform'))?.innerText.slice(0,300)`)
out.dash_export_buttons = await b.eval(`[...document.querySelectorAll('button, a')].filter(e=>/export|download|csv|json/i.test(e.textContent)).map(e=>e.textContent)`)
out.dash_stop_cancel = await b.eval(`[...document.querySelectorAll('button')].filter(e=>/stop|cancel|reset/i.test(e.textContent+e.getAttribute('aria-label'))).map(e=>e.textContent||e.getAttribute('aria-label'))`)
// replay history playback
await b.clickText('button', 'Replay run'); await b.sleep(2500)
out.dash_playback = await b.eval(`[...document.querySelectorAll('.mono.small.muted')].map(e=>e.textContent).find(t=>t.startsWith('round'))`)
await b.shot(`${EV}/dashboard_run.png`, true)
// bandit source + uniform algorithm label "LUCB would pull next"
await b.clickText('.seg button', 'Arms'); await b.sleep(200); await setSelect('Algorithm', 'uniform_fc'); await b.sleep(200)
await b.click('[data-testid=run-attribution]'); await b.sleep(6000)
out.dash_uniform_label = await b.eval(`[...document.querySelectorAll('p.mono.xs.muted')].map(e=>e.textContent).join(' ').slice(0,220)`)

// ---------------- Studio
await b.goto('/studio', 2500); await b.eval(hook)
const groups = await b.eval(`[...document.querySelectorAll('main.page .row button.chip')].map(e=>e.textContent)`)
out.studio_groups = {}
for (const gname of groups) {
  await b.clickText('main.page .row button.chip', gname); await b.sleep(2200)
  out.studio_groups[gname] = await b.eval(`(()=>{const c=document.querySelector('main.page > div > .stack > .card') || document.querySelectorAll('main.page .card')[0]; return {bars:document.querySelectorAll('main.page .recharts-bar-rectangle').length, lines:document.querySelectorAll('main.page .recharts-line-curve').length, emptyCharts:[...document.querySelectorAll('main.page .recharts-wrapper')].filter(w=>!w.querySelector('.recharts-bar-rectangle, .recharts-line-curve, .recharts-scatter-symbol')).length, wrappers:document.querySelectorAll('main.page .recharts-wrapper').length, err:[...document.querySelectorAll('[data-testid=error-message]')].map(e=>e.textContent), rowsText:(document.querySelector('main.page p.small.muted')?.textContent||'').slice(-60)}})()`)
}
await b.clickText('.tabs [role=tab]', 'Run simulation'); await b.sleep(800)
await b.eval(`(()=>{const i=document.querySelector('[data-testid=trials]'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'3'); i.dispatchEvent(new Event('input',{bubbles:true}))})()`)
await b.click('[data-testid=run-experiment]'); await b.sleep(15000)
out.studio_live = await b.eval(`({rowsReq:window.__reqs.filter(r=>r.u.includes('/api/experiment')).slice(-1)[0]?.body, bars:document.querySelectorAll('main.page .recharts-bar-rectangle').length, scatter:document.querySelectorAll('main.page .recharts-scatter-symbol').length, exportCsv:!!document.querySelector('[data-testid=export-csv]'), exportJson:!!document.querySelector('[data-testid=export-json]'), heat:document.querySelectorAll('.heat-cell').length, err:[...document.querySelectorAll('[data-testid=error-message]')].map(e=>e.textContent)})`)
await b.shot(`${EV}/studio_live.png`, true)
// automaton source in studio live: does the UI expose n_states / eps_plan? (it sends defaults)
await setSelect('Instance family', 'automaton'); await b.sleep(400)
out.studio_live_automaton_fields = await b.eval(`[...document.querySelectorAll('main.page .field label')].map(l=>l.textContent)`)
await b.clickText('.tabs [role=tab]', 'Paired statistics'); await b.sleep(800)
out.studio_paired = await b.eval(`(document.querySelector('main.page .tbl')?.innerText||'').slice(0,500)`)

// ---------------- Docs API reference ranges
await b.goto('/docs', 2500)
await b.eval(`[...document.querySelectorAll('.disc-trigger')].find(t=>t.textContent.includes('/api/attribute'))?.click()`); await b.sleep(800)
out.docs_attribute_ranges = await b.eval(`[...document.querySelectorAll('.disc-body tbody tr')].map(r=>[...r.children].map(c=>c.textContent).join(' | ')).slice(0,22)`)
out.docs_internal_links = await b.eval(`[...document.querySelectorAll('main.page a')].map(a=>a.getAttribute('href'))`)
// search for something that exists only inside a section body
await setInput('[data-testid=docs-search]', 'abstention'); await b.sleep(600)
out.docs_search_abstention = await b.eval(`[...document.querySelectorAll('main.page .card h3')].map(h=>h.textContent)`)
await setInput('[data-testid=docs-search]', 'LUCB'); await b.sleep(600)
out.docs_search_LUCB = await b.eval(`[...document.querySelectorAll('main.page .card h3')].map(h=>h.textContent)`)

// ---------------- Reproducibility commands & artifact links
await b.goto('/reproducibility', 2500)
out.repro_commands = await b.eval(`[...document.querySelectorAll('pre.code')].map(p=>p.textContent).join('\\n---\\n').slice(0,2500)`)
const links = await b.eval(`[...document.querySelectorAll('main.page a[href^="/files"]')].map(a=>a.getAttribute('href'))`)
out.repro_links = []
for (const l of links) out.repro_links.push([l, await b.eval(`fetch(${JSON.stringify(l)}).then(r=>r.status+' '+r.headers.get('content-type'))`)])
out.repro_fig_imgs = await b.eval(`(async()=>{const imgs=[...document.querySelectorAll('.fig-card img')]; return {n:imgs.length}})()`)

// ---------------- Related
await b.goto('/related', 2500)
out.related = await b.eval(`({rows:document.querySelectorAll('[data-testid=novelty-matrix] tbody tr').length, timelinePts:document.querySelectorAll('.timeline-svg g[role=button]').length, records:document.querySelectorAll('.disc').length})`)
await setInput('input[aria-label="Filter papers"]', 'car'); await b.sleep(400)
out.related_filter_car = await b.eval(`[...document.querySelectorAll('[data-testid=novelty-matrix] tbody tr td:first-child b')].map(e=>e.textContent)`)
await b.clickText('.seg button', 'Bandit papers'); await b.sleep(400)
out.related_filter_car_bandit = await b.eval(`[...document.querySelectorAll('[data-testid=novelty-matrix] tbody tr td:first-child b')].map(e=>e.textContent)`)
await b.shot(`${EV}/related_timeline.png`)
// Overview: pipeline + section tabs + buttons
await b.goto('/', 2500)
out.overview_links = await b.eval(`[...document.querySelectorAll('.hero a')].map(a=>a.getAttribute('href')+' '+a.textContent.trim())`)
out.overview_tabs = await b.eval(`[...document.querySelectorAll('.tabs [role=tab]')].map(t=>t.textContent)`)

out.exceptions = b.log.exceptions
out.consoleErrors = [...new Set(b.log.console.filter((c) => /error|warn/i.test(c.type)).map((c) => c.text.slice(0, 200)))]
out.network = b.log.network
fs.writeFileSync(`${EV}/04_workflows.json`, JSON.stringify(out, null, 1))
console.log(JSON.stringify(out, null, 1).slice(0, 14000))
await b.close()
