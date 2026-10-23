// Screenshots for the demonstration guide (the API must be running on :8000 and the site built).
//   node scripts/demo_screens.mjs            -> report/screens/demo/*.png
import { launch } from '../qa/tools/cdp.mjs'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const OUT = path.join(ROOT, 'report', 'screens', 'demo')
fs.mkdirSync(OUT, { recursive: true })
const b = await launch({ port: 9360 })
await b.viewport(1440, 900)
const done = []

async function rect(sel, pad = 12) {
  return b.eval(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(!e) return null; e.scrollIntoView({block:'start'}); const r=e.getBoundingClientRect(); return {x:Math.max(0,r.left-${pad}), y:Math.max(0,r.top+scrollY-${pad}), w:r.width+${2 * pad}, h:r.height+${2 * pad}}})()`)
}
async function shotEl(name, sel, pad = 12) {
  const r = await rect(sel, pad)
  if (!r) { console.log('MISSING', name, sel); return }
  await b.sleep(250)
  const res = await b.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: r.x, y: r.y, width: Math.min(r.w, 1440), height: Math.min(r.h, 2400), scale: 1 } })
  fs.writeFileSync(path.join(OUT, name + '.png'), Buffer.from(res.data, 'base64')); done.push(name)
}
async function shotView(name) { await b.sleep(300); await b.shot(path.join(OUT, name + '.png')); done.push(name) }
const setInput = (sel, v) => b.eval(`(()=>{const i=document.querySelector(${JSON.stringify(sel)}); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i, ${JSON.stringify(String(v))}); i.dispatchEvent(new Event('input',{bubbles:true}))})()`)
const example = async (i) => { await b.eval(`document.querySelectorAll('[data-testid=example-case]')[${i}].click()`); await b.sleep(1100) }
const cardOf = (title) => `(()=>{const h=[...document.querySelectorAll('.card .card-head h3')].find(h=>h.textContent.includes(${JSON.stringify(title)})); return h?.closest('.card')})()`
async function shotCard(name, title, pad = 8) {
  const ok = await b.eval(`(()=>{const c=${cardOf(title)}; if(!c) return false; c.setAttribute('data-shot', ${JSON.stringify(name)}); return true})()`)
  if (!ok) { console.log('MISSING card', title); return }
  await shotEl(name, `[data-shot="${name}"]`, pad)
}

// ---------------- home
await b.goto('/', 3000); await shotView('01_home')
await shotEl('01b_home_kpis', '.kpis')
await b.eval(`document.querySelectorAll('.tabs [role=tab]')[1].click()`); await b.sleep(400); await shotCard('02_research_gap_tab', 'seven required')
await b.eval(`document.querySelectorAll('.tabs [role=tab]')[6].click()`); await b.sleep(400); await shotCard('03_steps_tab', 'seven required')
// ---------------- related work
await b.goto('/related', 2500); await shotView('04_related_top')
await shotCard('05_related_timeline', 'Timeline')
await shotCard('06_related_matrix', 'Evidence matrix')
// ---------------- lab: agent automaton
await b.goto('/lab', 3000); await shotView('10_lab_agent_lts')
await b.clickText('.seg button', 'DFA'); await b.sleep(1800); await shotView('11_lab_agent_dfa_sink')
await b.clickText('.seg button', 'LTS'); await b.sleep(1500)
for (let i = 0; i < 3; i++) { await b.click('button[aria-label="Step forward"]'); await b.sleep(250) }
await shotView('12_lab_agent_trace_step3')
await b.clickText('.tabs [role=tab]', 'Counterfactual branch'); await b.sleep(500); await b.eval(`document.querySelectorAll('.steps-scroll .step-card')[3].click()`); await b.sleep(700); await shotView('13_lab_agent_branch')
// ---------------- lab: small machines (example cases)
const L = async (model, idx, name) => { await b.goto(`/lab?model=${model}`, 2200); await example(idx); await shotEl(name, '.page > .stack', 6) }
await L('dfa', 0, '20_dfa_accepted'); await L('dfa', 2, '21_dfa_dead_state'); await L('dfa', 4, '22_dfa_invalid_symbol')
await L('nfa', 0, '23_nfa_accepted_active_sets')
await b.clickText('.seg button', 'DFA (subset'); await b.sleep(1500); await shotEl('24_nfa_subset_construction', '.page > .stack', 6)
await L('enfa', 0, '25_enfa_closure')
await L('pa', 0, '26_pa_probability')
await L('lts', 2, '27_lts_blocked')
await L('mealy', 0, '28_mealy_outputs'); await L('moore', 0, '29_moore_outputs')
await L('pda', 0, '30_pda_balanced'); await L('pda', 1, '31_pda_underflow_reject'); await L('pda_typed', 1, '32_pda_typed_mismatch')
await L('tm', 0, '33_tm_increment'); await L('tm_pal', 2, '34_tm_palindrome_reject'); await L('tm_loop', 0, '35_tm_unknown')
await b.goto('/lab?model=dfa', 2000); await b.clickText('.seg button', 'Table'); await b.sleep(500); await shotEl('36_dfa_table_view', '.page > .stack', 6)
// ---------------- trajectory explorer
await b.goto('/explorer?autoload=1', 3500); await shotView('40_explorer_loaded')
await b.click('[data-testid=run-estimate]'); await b.sleep(2500); await shotCard('41_explorer_estimate', 'Intervene at step')
await b.click('[data-testid=run-replay]'); await b.sleep(1500); await shotCard('42_explorer_replay', 'Intervene at step')
// ---------------- dashboard
await b.goto('/dashboard?autorun=1', 6500); await shotView('50_dashboard_result')
await shotCard('51_dashboard_forest', 'Candidate steps and their confidence')
await shotCard('52_dashboard_stopping', 'Stopping rule')
await b.click('[data-testid=compare-uniform]'); await b.sleep(7000); await shotCard('53_dashboard_compare', 'Compare with uniform')
await b.eval(`(()=>{const s=[...document.querySelectorAll('.field')].find(f=>f.querySelector('label')?.textContent.startsWith('Target')).querySelector('select'); const set=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set; set.call(s,'last_above'); s.dispatchEvent(new Event('change',{bubbles:true}))})()`)
await b.sleep(300); await b.click('[data-testid=run-attribution]'); await b.sleep(5500); await shotCard('54_dashboard_threshold', 'Stopping rule')
await b.goto('/dashboard', 2000); await setInput('[data-testid=delta]', '0'); await b.sleep(400); await shotEl('55_dashboard_invalid_blocks_run', '.sticky-card')
await b.goto('/dashboard?autorun=1', 5500)
await setInput('[data-testid=budget]', '2000'); await b.click('[data-testid=run-attribution]'); await b.sleep(4500); await shotView('56_dashboard_abstention')
// ---------------- studio
await b.goto('/studio', 3000); await shotView('60_studio_main')
await b.clickText('main .row button.chip', 'Gap sweep'); await b.sleep(2500); await shotView('61_studio_gap_sweep')
await b.clickText('.tabs [role=tab]', 'Paired statistics'); await b.sleep(1000); await shotView('62_studio_paired')
await b.clickText('.tabs [role=tab]', 'Run simulation'); await b.sleep(500); await setInput('[data-testid=trials]', '6'); await b.click('[data-testid=run-experiment]'); await b.sleep(9000); await shotView('63_studio_live')
// ---------------- reference pages
await b.goto('/theory', 2500); await shotView('70_theory')
await b.goto('/reproducibility', 2500); await shotView('71_reproducibility')
await b.goto('/docs', 2500); await shotView('72_docs')
// ---------------- responsive
await b.viewport(390, 844, true); await b.goto('/lab', 2500); await shotView('80_mobile_lab')
await b.close()
console.log(done.length, 'screenshots in', OUT)
