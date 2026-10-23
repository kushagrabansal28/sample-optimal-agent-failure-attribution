// Automata laboratory: every model — graph geometry, start/accept marks, trace execution, playback, overlays, toasts.
import { launch } from './cdp.mjs'
import fs from 'node:fs'
const EV = process.argv[2]
const b = await launch({ port: 9342 })
await b.viewport(1440, 900)
const MODELS = ['agent48', 'dfa', 'nfa', 'enfa', 'pa', 'lts', 'mealy', 'moore', 'pda', 'pda_typed', 'tm', 'tm_pal']
const probe = `(()=>{const s=document.querySelector('.graph-svg'); const g=s?.querySelector(':scope>g'); const r=s?.getBoundingClientRect();
  const nodes=[...(s?.querySelectorAll('.g-node')||[])]; const vis=nodes.filter(n=>{const b=n.getBoundingClientRect(); return b.width>2 && b.right>r.left && b.left<r.right && b.bottom>r.top && b.top<r.bottom}).length;
  const labels=[...(s?.querySelectorAll('.g-label')||[])]; let overl=0; const bx=labels.map(l=>l.getBoundingClientRect()); for(let i=0;i<bx.length;i++)for(let j=i+1;j<bx.length;j++){const a=bx[i],c=bx[j]; if(a.width&&c.width&&a.left<c.right&&c.left<a.right&&a.top<c.bottom&&c.top<a.bottom) overl++}
  return {svgW:Math.round(r?.width||0), transform:g?.getAttribute('transform'), nodes:nodes.length, visibleNodes:vis, edges:s?.querySelectorAll('.g-edge').length, labels:labels.length, overlappingLabelPairs:overl,
   startMarker: !!s?.querySelector('path[marker-end="url(#m-p)"]'), title:document.querySelector('.lab-grid .card-head h3')?.textContent, word:document.querySelector('[data-testid=word-input]')?.value ?? null,
   tabs:[...document.querySelectorAll('.tabs [role=tab]')].map(t=>t.textContent), badges:[...document.querySelectorAll('.lab-grid .badge')].map(b=>b.textContent).slice(0,8), callout:document.querySelector('.model-bar ~ .row .callout b, .card .callout.ok b')?.textContent||null}})()`
const out = {}
for (const m of MODELS) {
  await b.goto(`/lab?model=${m}`, 2500)
  const rec = { initial: await b.eval(probe) }
  await b.shot(`${EV}/lab_${m}_initial.png`)
  if (m !== 'agent48') {
    // run the default trace
    const t0 = Date.now()
    rec.run = await b.click('[data-testid=run-trace]'); await b.sleep(1800)
    rec.afterRun = await b.eval(`(()=>({toast:[...document.querySelectorAll('.toast, [role=status]')].map(e=>e.textContent.trim()).filter(Boolean).slice(-3), badges:[...document.querySelectorAll('.lab-grid main .badge')].map(b=>b.textContent), stepLabel:[...document.querySelectorAll('.lab-grid .mono.small.muted')].map(e=>e.textContent).find(t=>t.startsWith('step'))||null, err:[...document.querySelectorAll('[data-testid=error-message]')].map(e=>e.textContent), stack:[...document.querySelectorAll('.stack-cell')].map(e=>e.textContent), tape:[...document.querySelectorAll('.tape-cell')].map(e=>e.textContent).join(''), active:[...document.querySelectorAll('.chips .chip')].map(e=>e.textContent).slice(0,12), note:[...document.querySelectorAll('.lab-grid main p.small.muted')].map(e=>e.textContent).slice(-1)[0]||null}))()`)
    // step forward through the whole trace, recording highlighted edges per step
    const total = await b.eval(`(()=>{const t=[...document.querySelectorAll('.lab-grid .mono.small.muted')].map(e=>e.textContent).find(t=>t.startsWith('step')); return t?Number(t.split('/')[1]):0})()`)
    rec.total = total
    rec.playback = []
    for (let i = 0; i < Math.min(total, 30); i++) {
      await b.click('button[aria-label="Step forward"]'); await b.sleep(250)
      rec.playback.push(await b.eval(`(()=>{const s=document.querySelector('.graph-svg'); const hi=[...s.querySelectorAll('.g-edge.dash-flow')].length; const cur=[...s.querySelectorAll('.g-node')].filter(n=>n.querySelector('circle.pulse[stroke="var(--cyan)"]')).map(n=>n.getAttribute('aria-label')); const amber=[...s.querySelectorAll('.g-node')].filter(n=>n.querySelector('circle[stroke="var(--amber)"]')).map(n=>n.getAttribute('aria-label')); const step=[...document.querySelectorAll('.lab-grid .mono.small.muted')].map(e=>e.textContent).find(t=>t.startsWith('step')); return {step, highlightedEdges:hi, current:cur, activeSet:amber, stack:[...document.querySelectorAll('.stack-cell')].map(e=>e.textContent).join(','), tape:[...document.querySelectorAll('.tape-cell')].map(e=>e.textContent).join(''), outputs:[...document.querySelectorAll('.lab-grid main .chips .chip')].map(e=>e.textContent).join(' ')}})()`))
    }
    await b.shot(`${EV}/lab_${m}_trace_end.png`)
    // a rejecting / invalid word
    const bad = { dfa: 'a b b', nfa: 'a b a', enfa: 'b b', pa: 'go', lts: 'plan answer plan', mealy: 'task bogus', moore: 'ok ok', pda: 'call ret ret', pda_typed: 'open_search end_calc', tm: '12', tm_pal: 'ab' }[m]
    await b.eval(`(()=>{const i=document.querySelector('[data-testid=word-input]'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i, ${JSON.stringify(bad)}); i.dispatchEvent(new Event('input',{bubbles:true}));})()`)
    await b.sleep(200)
    await b.click('[data-testid=run-trace]'); await b.sleep(1800)
    rec.rejectWord = bad
    rec.afterReject = await b.eval(`(()=>({badges:[...document.querySelectorAll('.lab-grid main .badge')].map(b=>b.textContent), err:[...document.querySelectorAll('[data-testid=error-message]')].map(e=>e.textContent), stepLabel:[...document.querySelectorAll('.lab-grid .mono.small.muted')].map(e=>e.textContent).find(t=>t.startsWith('step'))||null, prompt:[...document.querySelectorAll('.lab-grid main p.small.muted')].map(e=>e.textContent).slice(-1)[0]||null}))()`)
    await b.shot(`${EV}/lab_${m}_reject.png`)
  } else {
    // agent48: views, sizes, trace playback, branch tab, search, select node
    rec.views = {}
    for (const v of ['DFA', 'NFA', 'ε-NFA', 'PA', 'LTS']) {
      await b.clickText('.seg button', v); await b.sleep(1800)
      rec.views[v] = await b.eval(probe)
      if (v !== 'LTS') await b.shot(`${EV}/lab_agent48_view_${v.replace('ε-', 'e')}.png`)
    }
    for (const n of ['64', '96', '48']) {
      await b.eval(`(()=>{const s=[...document.querySelectorAll('select')].find(x=>[...x.options].some(o=>o.value==='96')); const set=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set; set.call(s,'${n}'); s.dispatchEvent(new Event('change',{bubbles:true}))})()`)
      await b.sleep(2500)
      rec['size_' + n] = await b.eval(probe)
      if (n !== '48') await b.shot(`${EV}/lab_agent48_${n}states.png`)
    }
    rec.traceTotal = await b.eval(`[...document.querySelectorAll('.lab-grid .mono.small.muted')].map(e=>e.textContent).find(t=>t.startsWith('step'))||null`)
    await b.click('button[aria-label="Step forward"]'); await b.sleep(300); await b.click('button[aria-label="Step forward"]'); await b.sleep(300)
    rec.afterTwoSteps = await b.eval(`(()=>{const s=document.querySelector('.graph-svg'); return {hi:s.querySelectorAll('.g-edge.dash-flow').length, culprit:[...s.querySelectorAll('text')].filter(t=>t.textContent==='CULPRIT').length}})()`)
    await b.clickText('.tabs [role=tab]', 'Counterfactual branch'); await b.sleep(600)
    await b.eval(`document.querySelectorAll('.steps-scroll .step-card')[0]?.click()`); await b.sleep(600)
    rec.branch = await b.eval(`(()=>{const s=document.querySelector('.graph-svg'); return {violetEdges:[...s.querySelectorAll('path.g-edge')].filter(p=>p.getAttribute('stroke')==='#9b8cff').length, selected: document.querySelector('.lab-grid aside .mono')?.textContent}})()`)
    await b.shot(`${EV}/lab_agent48_branch.png`)
    // search
    await b.eval(`(()=>{const i=document.querySelector('[data-testid=state-search]'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'memory'); i.dispatchEvent(new Event('input',{bubbles:true}))})()`)
    await b.sleep(1200)
    rec.search = await b.eval(`(()=>({matchesText:document.querySelector('[data-testid=state-search]')?.nextElementSibling?.textContent, dimmed:[...document.querySelectorAll('.g-node')].filter(n=>n.getAttribute('opacity')==='0.18').length}))()`)
    // tabs
    for (const t of ['Definition & semantics', 'Transition table', 'Compare models', 'Test status']) {
      await b.clickText('.tabs [role=tab]', t); await b.sleep(700)
      rec['tab_' + t] = await b.eval(`(()=>{const c=document.querySelectorAll('.lab-grid main > .card')[1]; return {text:(c?.innerText||'').slice(0,300), rows:c?.querySelectorAll('tbody tr').length, katex:c?.querySelectorAll('.katex').length, katexErr:c?.querySelectorAll('.katex-error').length}})()`)
    }
  }
  // click a node, inspect details
  await b.eval(`document.querySelectorAll('.g-node')[0]?.dispatchEvent(new MouseEvent('click',{bubbles:true}))`); await b.sleep(500)
  rec.nodeDetails = await b.eval(`(document.querySelector('.lab-grid aside .card')?.innerText||'').slice(0,240)`)
  // zoom buttons
  const before = await b.eval(`document.querySelector('.graph-svg > g').getAttribute('transform')`)
  await b.click('button[aria-label="Zoom in"]'); await b.sleep(500)
  const after = await b.eval(`document.querySelector('.graph-svg > g').getAttribute('transform')`)
  await b.click('button[aria-label="Fit to view"]'); await b.sleep(900)
  rec.zoom = { before, after, afterFit: await b.eval(`document.querySelector('.graph-svg > g').getAttribute('transform')`) }
  out[m] = rec
  console.log('done', m)
}
out.exceptions = b.log.exceptions
out.consoleErrors = b.log.console.filter((c) => /error/i.test(c.type)).map((c) => c.text).filter((t, i, a) => a.indexOf(t) === i)
out.network = b.log.network
fs.writeFileSync(`${EV}/02_lab.json`, JSON.stringify(out, null, 1))
await b.close()
