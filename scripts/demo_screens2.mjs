// Additional screenshots for the handbook (API on :8000, site built).   node scripts/demo_screens2.mjs
import { launch } from '../qa/tools/cdp.mjs'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const OUT = path.join(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..'), 'report', 'screens', 'demo')
const b = await launch({ port: 9361 })
await b.viewport(1440, 900)
const done = []
async function shotEl(name, sel, pad = 10) {
  const r = await b.eval(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(!e) return null; e.scrollIntoView({block:'start'}); const r=e.getBoundingClientRect(); return {x:Math.max(0,r.left-${pad}), y:Math.max(0,r.top+scrollY-${pad}), w:r.width+${2 * pad}, h:r.height+${2 * pad}}})()`)
  if (!r) { console.log('MISSING', name, sel); return }
  await b.sleep(300)
  const res = await b.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: r.x, y: r.y, width: Math.min(r.w, 1440), height: Math.min(r.h, 2600), scale: 1 } })
  fs.writeFileSync(path.join(OUT, name + '.png'), Buffer.from(res.data, 'base64')); done.push(name)
}
const tab = async (t) => { await b.clickText('.tabs [role=tab]', t); await b.sleep(700) }
await b.goto('/lab', 3000)
await b.eval(`(()=>{const n=[...document.querySelectorAll('.g-node')].find(n=>/State q3 /.test(n.getAttribute('aria-label'))); n.dispatchEvent(new MouseEvent('click',{bubbles:true}))})()`); await b.sleep(700)
await shotEl('14_lab_state_details', '.lab-grid')
await b.goto('/lab?model=dfa', 2500); await tab('Definition & semantics'); await shotEl('15_lab_definition_tab', '.lab-grid > .stack > .card:nth-of-type(2)')
await tab('Transition table'); await shotEl('16_lab_table_tab', '.lab-grid > .stack > .card:nth-of-type(2)')
await tab('Compare models'); await shotEl('17_lab_compare_tab', '.lab-grid > .stack > .card:nth-of-type(2)')
await b.goto('/lab', 2800); await b.clickText('.seg button', 'PA'); await b.sleep(1800); await shotEl('18_lab_agent_pa_view', '.lab-grid')
await b.goto('/dashboard', 2500); await shotEl('43_dashboard_config', '.sticky-card')
await b.goto('/dashboard?autorun=1', 6500); await b.eval(`[...document.querySelectorAll('.card .card-head h3')].find(h=>h.textContent.includes('Candidate ranking')).closest('.card').setAttribute('data-shot','rk')`); await shotEl('44_dashboard_ranking', '[data-shot=rk]')
await b.goto('/studio', 3000); await b.clickText('main .row button.chip', 'Ablations'); await b.sleep(2500); await shotEl('45_studio_ablation', 'main.page')
await b.clickText('main .row button.chip', 'Accuracy vs rollout'); await b.sleep(2500); await shotEl('46_studio_budget', 'main.page')
await b.clickText('main .row button.chip', 'Stage B'); await b.sleep(2000); await shotEl('47_studio_toolagent', 'main.page')
await b.goto('/explorer', 2500); await shotEl('48_explorer_config', '.sticky-card')
await b.goto('/related', 2500); await b.eval(`document.querySelector('input[aria-label="Filter papers"]').scrollIntoView({block:'center'})`)
await b.eval(`(()=>{const i=document.querySelector('input[aria-label="Filter papers"]'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'car'); i.dispatchEvent(new Event('input',{bubbles:true}))})()`); await b.sleep(800)
await b.eval(`[...document.querySelectorAll('.card .card-head h3')].find(h=>h.textContent.includes('Evidence matrix')).closest('.card').setAttribute('data-shot','em')`); await shotEl('07_related_filter_car', '[data-shot=em]')
await b.eval(`document.querySelector('[data-testid=novelty-matrix] tbody tr').click()`); await b.sleep(600); await shotEl('08_related_paper_detail', '.page > .stack > div:nth-of-type(7)')
await b.close()
console.log(done.length, 'extra screenshots')
