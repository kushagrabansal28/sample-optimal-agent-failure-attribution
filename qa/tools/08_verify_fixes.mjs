// End-to-end verification of the fixes (run after rebuilding the site and restarting the API).
//   node qa/tools/08_verify_fixes.mjs qa/evidence-after
import { launch } from './cdp.mjs'
import fs from 'node:fs'
const EV = process.argv[2]
fs.mkdirSync(EV, { recursive: true })
const results = []
const check = (name, ok, detail = '') => { results.push({ name, ok: !!ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`) }

const hiddenInside = `(()=>{const m=document.getElementById('main-content'); return [...m.querySelectorAll('*')].filter(e=>{const cs=getComputedStyle(e); return cs.opacity==='0' && cs.display!=='none' && !e.closest('[hidden]') && !e.classList.contains('halo') && !e.closest('svg')}).length})()`

// ------------------------------------------------------------------------------------------------ 1. navigation with NO animation frames (the "I must refresh" bug)
{
  const b = await launch({ port: 9351, noRaf: true })
  await b.viewport(1440, 900)
  await b.goto('/', 1500)
  const links = ['Problem & related work', 'Automata laboratory', 'Trajectory explorer', 'Attribution dashboard', 'Experiment studio', 'Theory & guarantees', 'Reproducibility', 'Documentation', 'Overview']
  for (const l of links) {
    await b.clickText('a.nav-item', l)
    await b.sleep(900)
    const s = await b.eval(`({path:location.pathname, h1:document.querySelector('h1')?.textContent.trim().slice(0,50), title:document.title, hidden:${hiddenInside}, mainOpacity:getComputedStyle(document.getElementById('main-content')).opacity, textLen:document.getElementById('main-content').innerText.length, focus:document.activeElement?.id, rafLive: false})`)
    check(`[no animation frames] clicking "${l}" shows the page without a refresh`, s.h1 && s.textLen > 200 && s.mainOpacity === '1' && s.hidden === 0, `${s.path} · h1 "${s.h1}" · ${s.textLen} chars · invisible elements ${s.hidden} · title "${s.title}" · focus #${s.focus}`)
  }
  await b.goto('/lab', 2500)
  const lab = await b.eval(`(()=>{const s=document.querySelector('.graph-svg'); const g=s.querySelector(':scope>g'); const r=s.getBoundingClientRect(); const vis=[...s.querySelectorAll('.g-node')].filter(n=>{const b=n.getBoundingClientRect(); return b.width>2 && b.left>=r.left-2 && b.right<=r.right+2 && b.top>=r.top-2 && b.bottom<=r.bottom+2}).length; return {tr:g.getAttribute('transform'), nodes:s.querySelectorAll('.g-node').length, vis, top:Math.round(r.top)}})()`)
  check('[no animation frames] lab graph is drawn at a finite, positive scale with all 48 states visible', !/NaN|Infinity|scale\(0\)/.test(lab.tr) && lab.vis === 48, JSON.stringify(lab))
  check('lab graph starts inside the first screen (top < 700 px at 1440x900)', lab.top < 700, `graph top at ${lab.top}px`)
  await b.shot(`${EV}/after_lab_no_raf.png`)
  const kpi = await (async () => { await b.goto('/', 1500); return b.eval(`[...document.querySelectorAll('.kpis .stat .v')].map(e=>e.textContent).join(' | ')`) })()
  check('[no animation frames] homepage KPIs show the exact final values (48 | 146+ | 6518 | 0)', /^48 \| \d+ \| 6518 \| 0$/.test(kpi), kpi)
  check('no JavaScript exceptions', b.log.exceptions.length === 0, JSON.stringify(b.log.exceptions).slice(0, 200))
  await b.close()
}

// ------------------------------------------------------------------------------------------------ 2. zero-size mount, then resize
{
  const b = await launch({ port: 9352 })
  await b.viewport(1, 1)
  await b.goto('/lab', 2500)
  await b.clickText('.seg button', 'Graph'); await b.sleep(800)               // tiny screens default to the table view
  const a = await b.eval(`document.querySelector('.graph-svg > g').getAttribute('transform')`)
  check('1x1 viewport: no degenerate graph transform', !/NaN|Infinity|scale\(0\)/.test(a || ''), a)
  await b.eval(`document.querySelector('.graph-svg').dispatchEvent(new WheelEvent('wheel',{deltaY:-200,bubbles:true,cancelable:true}))`)
  await b.sleep(300)
  const w = await b.eval(`document.querySelector('.graph-svg > g').getAttribute('transform')`)
  check('wheel while collapsed gives no Infinity/NaN', !/NaN|Infinity/.test(w || ''), w)
  await b.viewport(1440, 900); await b.sleep(1500)
  const r = await b.eval(`(()=>{const s=document.querySelector('.graph-svg'); const g=s.querySelector(':scope>g'); const rr=s.getBoundingClientRect(); return {tr:g.getAttribute('transform'), vis:[...s.querySelectorAll('.g-node')].filter(n=>{const b=n.getBoundingClientRect(); return b.width>2 && b.left>=rr.left-2 && b.right<=rr.right+2 && b.top>=rr.top-2 && b.bottom<=rr.bottom+2}).length}})()`)
  check('after growing to 1440x900 the graph fits (48/48 visible)', r.vis === 48, JSON.stringify(r))
  await b.close()
}

// ------------------------------------------------------------------------------------------------ 3. every model: q-ids, graph, example cases
{
  const b = await launch({ port: 9353 })
  await b.viewport(1440, 900)
  const models = ['dfa', 'nfa', 'enfa', 'pa', 'lts', 'mealy', 'moore', 'pda', 'pda_typed', 'tm', 'tm_pal', 'tm_loop']
  for (const m of models) {
    await b.goto(`/lab?model=${m}`, 1800)
    const g = await b.eval(`(()=>{const s=document.querySelector('.graph-svg'); const ids=[...s.querySelectorAll('.g-node text:first-of-type')].map(t=>t.textContent.trim()); const labels=[...s.querySelectorAll('.g-label')]; const bx=labels.map(l=>l.getBoundingClientRect()); let ov=0; for(let i=0;i<bx.length;i++)for(let j=i+1;j<bx.length;j++){const a=bx[i],c=bx[j]; if(a.width&&c.width&&a.left<c.right&&c.left<a.right&&a.top<c.bottom&&c.top<a.bottom) ov++}
      const r=s.getBoundingClientRect(); const clipped=[...s.querySelectorAll('.g-node')].filter(n=>{const b=n.getBoundingClientRect(); return b.left<r.left-2||b.right>r.right+2||b.top<r.top-2||b.bottom>r.bottom+2}).length; return {ids, ov, clipped, desc:document.querySelector('[data-testid=model-description]')?.textContent.slice(0,60)}})()`)
    const okIds = g.ids.length > 0 && g.ids.every((x) => /^q\d+$/.test(x)) && g.ids[0] === 'q0'
    check(`${m}: states are numbered q0, q1, …`, okIds, g.ids.join(' '))
    check(`${m}: no overlapping edge labels, no clipped states`, g.ov === 0 && g.clipped === 0, `overlaps ${g.ov}, clipped ${g.clipped}`)
    const n = await b.eval(`document.querySelectorAll('[data-testid=example-case]').length`)
    for (let i = 0; i < n; i++) {
      const label = await b.eval(`(()=>{const c=document.querySelectorAll('[data-testid=example-case]')[${i}]; const l=c.textContent; c.click(); return l+'|'+c.className})()`)
      await b.sleep(900)
      const [name, cls] = label.split('|')
      const expect = ['accept', 'reject', 'error', 'unknown', 'probability', 'output'].find((x) => cls.includes(x)) || ''
      const s = await b.eval(`(()=>{const p=document.querySelector('[data-testid=result-panel]'); return {badges:[...(p?.querySelectorAll('.badge')||[])].map(x=>x.textContent.trim()), panel:p?.innerText.replace(/\\s+/g,' ').slice(0,200)||null, err:document.querySelector('[data-testid=error-message]')?.textContent||null, steps:[...document.querySelectorAll('.mono.small.muted')].map(e=>e.textContent).find(t=>t.startsWith('step'))||null}})()`)
      let ok = false
      if (expect === 'accept') ok = /accepted/.test(s.panel || '') || /accept/.test(s.panel || '')
      else if (expect === 'reject') ok = /rejected|reject/.test(s.panel || '') && /Why|reason|blocked|dead|accepting/.test(s.panel || '')
      else if (expect === 'error') ok = !!s.err
      else if (expect === 'unknown') ok = /unknown/.test(s.panel || '') && !/\breject\b/.test((s.panel || '').split('Why')[0])
      else if (expect === 'probability') ok = /exact P\(accept\)/.test(s.panel || '') && !s.badges.some((x) => /^(accepted|rejected)$/.test(x))
      else if (expect === 'output') ok = /outputs|output/.test(s.panel || '') && !s.badges.some((x) => /^(accepted|rejected)$/.test(x))
      check(`${m} · case "${name}" (${expect}) behaves as stated`, ok, (s.err || s.panel || '').slice(0, 130))
    }
    if (m === 'moore') await b.shot(`${EV}/after_lab_moore.png`)
    if (m === 'pda') await b.shot(`${EV}/after_lab_pda_reject.png`)
  }
  // 48-state: q-ids, DFA view sink, table mode
  await b.goto('/lab', 2500)
  const a = await b.eval(`(()=>{const s=document.querySelector('.graph-svg'); return {ids:[...s.querySelectorAll('.g-node')].map(n=>n.getAttribute('aria-label')).slice(0,3), n:s.querySelectorAll('.g-node').length, badge:document.querySelector('.lab-toolbar .badge')?.textContent}})()`)
  check('48-state automaton: 48 nodes labelled q0 …', a.n === 48 && /State q0 /.test(a.ids[0]), `${a.n} nodes · ${a.ids[0]} · ${a.badge}`)
  await b.clickText('.seg button', 'DFA'); await b.sleep(1800)
  const d = await b.eval(`({nodes:document.querySelectorAll('.graph-svg .g-node').length, sink:[...document.querySelectorAll('.graph-svg .g-node')].some(n=>/sink/i.test(n.getAttribute('aria-label')||'')||n.querySelector('.sink-node')), badge:document.querySelector('.lab-toolbar .badge')?.textContent})`)
  check('48-state DFA view draws the sink (49 nodes) and still counts 48 logical states', d.nodes === 49 && d.sink && /48 distinct logical states/.test(d.badge), JSON.stringify(d))
  await b.clickText('.seg button', 'Table'); await b.sleep(500)
  const tb = await b.eval(`document.querySelectorAll('.lab-grid table tbody tr').length`)
  check('graph/table switch shows a table', tb > 40, `${tb} rows`)
  await b.goto('/lab?model=nfa', 1800)
  await b.clickText('.seg button', 'DFA (subset'); await b.sleep(1500)
  const sub = await b.eval(`[...document.querySelectorAll('.graph-svg .g-node')].length`)
  check('NFA → DFA (subset construction) view', sub >= 3, `${sub} DFA states`)
  check('lab: no JavaScript exceptions', b.log.exceptions.length === 0, JSON.stringify(b.log.exceptions).slice(0, 200))
  const errs = b.log.console.filter((c) => /error/i.test(c.type) && !/422/.test(c.text))
  check('lab: no console errors (the only network errors are the expected 422s of the invalid-symbol cases)', errs.length === 0, errs.map((e) => e.text).slice(0, 2).join(' | '))
  await b.close()
}

// ------------------------------------------------------------------------------------------------ 4. console, security, API
{
  const b = await launch({ port: 9354 })
  await b.viewport(1440, 900)
  await b.goto('/', 3000)
  check('homepage: no console errors', b.log.console.filter((c) => /error/i.test(c.type)).length === 0, b.log.console.filter((c) => /error/i.test(c.type)).map((c) => c.text).slice(0, 1).join(''))
  const sec = await b.eval(`(async()=>{const out=[]; for (const p of ['/../../pyproject.toml','/..%2F..%2Fpyproject.toml','/%2e%2e/%2e%2e/pyproject.toml']) { const r=await fetch(p); const t=await r.text(); out.push(!/setuptools|build-system/.test(t)) } const u=await fetch('/api/nope'); out.push(u.status===404 && (u.headers.get('content-type')||'').includes('json')); const rp=await fetch('/api/replay',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({seed:-1,arm:0})}); out.push(rp.status===422); return out})()`)
  check('path traversal blocked; unknown /api path is 404 JSON; replay with seed=-1 is 422', sec.every(Boolean), JSON.stringify(sec))
  for (const [w, h] of [[1440, 900], [1024, 768], [768, 1024], [390, 844]]) {
    await b.viewport(w, h, w < 768)
    for (const r of ['/', '/lab', '/dashboard', '/explorer', '/studio', '/theory', '/related', '/reproducibility', '/docs']) {
      await b.goto(r, 1200)
      const o = await b.eval(`document.documentElement.scrollWidth > document.documentElement.clientWidth`)
      if (o) check(`no horizontal overflow at ${w}x${h} on ${r}`, false)
    }
  }
  check('no horizontal overflow on any page at 1440, 1024, 768 and 390 px', !results.some((x) => x.name.startsWith('no horizontal overflow at')))
  await b.close()
}

fs.writeFileSync(`${EV}/08_verify_fixes.json`, JSON.stringify(results, null, 1))
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} checks passed`)
process.exit(failed.length ? 1 : 0)
