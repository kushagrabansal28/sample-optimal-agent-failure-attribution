// Hypothesis tests: zero-size mount, resize recovery, interaction-before-visible, Reveal visibility, reduced motion.
import { launch } from './cdp.mjs'
import fs from 'node:fs'
const EV = process.argv[2]
const out = {}
const g = `(()=>{const s=document.querySelector('.graph-svg'); const gg=s?.querySelector(':scope>g'); return {w:Math.round(s?.getBoundingClientRect().width||0), t:gg?.getAttribute('transform'), inner:[innerWidth,innerHeight]}})()`
{
  const b = await launch({ port: 9343 })
  // A: mount with a 1px-wide viewport (stand-in for a hidden / collapsed pane), then grow it
  await b.viewport(1, 1)
  await b.goto('/lab', 3000)
  out.A_mount_1px = await b.eval(g)
  await b.viewport(1440, 900); await b.sleep(1500)
  out.A_after_resize = await b.eval(g)
  await b.shot(`${EV}/hyp_A_after_resize.png`)
  // B: mount at 1px, user wheel-scrolls over the graph while collapsed, then grows
  await b.viewport(1, 1)
  await b.goto('/lab?model=dfa', 3000)
  await b.eval(`(()=>{const s=document.querySelector('.graph-svg'); s.dispatchEvent(new WheelEvent('wheel',{deltaY:-200,bubbles:true,cancelable:true,clientX:0,clientY:0}));})()`)
  await b.sleep(400)
  out.B_after_wheel_collapsed = await b.eval(g)
  await b.viewport(1440, 900); await b.sleep(1500)
  out.B_after_resize = await b.eval(g)
  await b.shot(`${EV}/hyp_B_wheel_then_resize.png`)
  // C: Reveal sections below the fold on long pages: opacity before scrolling
  await b.goto('/theory', 2500)
  out.C_theory_reveal = await b.eval(`[...document.querySelectorAll('main.page > div > div[style]')].map(e=>({op:getComputedStyle(e).opacity, top:Math.round(e.getBoundingClientRect().top)})).slice(0,10)`)
  await b.shot(`${EV}/hyp_C_theory_fullpage_noscroll.png`, true)
  // D: theme toggle persists and light theme renders
  await b.goto('/lab', 2500)
  await b.click('.side-foot button.btn.icon'); await b.sleep(800)
  out.D_theme = await b.eval(`({theme:document.documentElement.dataset.theme, stored:localStorage.getItem('afcr-theme'), bg:getComputedStyle(document.body).backgroundColor})`)
  await b.shot(`${EV}/lab_light_theme.png`)
  await b.click('.side-foot button.btn.icon'); await b.sleep(400)
  out.exceptions = b.log.exceptions
  await b.close()
}
{
  // E: reduced motion: counters show final values immediately; cursor disabled
  const b = await launch({ port: 9344, reducedMotion: true })
  await b.viewport(1440, 900)
  await b.goto('/', 300)
  out.E_reduced_kpi_300ms = await b.eval(`[...document.querySelectorAll('.kpis .stat .v')].map(e=>e.textContent).join(' | ')`)
  await b.sleep(1500)
  out.E_reduced_kpi_1800ms = await b.eval(`[...document.querySelectorAll('.kpis .stat .v')].map(e=>e.textContent).join(' | ')`)
  out.E_cursor = await b.eval(`({cls:document.documentElement.className, ring:getComputedStyle(document.querySelector('.cursor-ring')).display})`)
  await b.close()
}
fs.writeFileSync(`${EV}/03_hypotheses.json`, JSON.stringify(out, null, 1))
console.log(JSON.stringify(out, null, 1))
