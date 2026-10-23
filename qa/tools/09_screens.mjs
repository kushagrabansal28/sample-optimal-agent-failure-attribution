// Screenshots of the fixed pages (after).   node qa/tools/09_screens.mjs qa/evidence-after
import { launch } from './cdp.mjs'
const EV = process.argv[2]
const b = await launch({ port: 9355 })
await b.viewport(1440, 900)
const shots = [['/', 'home'], ['/lab', 'lab_agent48'], ['/lab?model=mealy', 'lab_mealy'], ['/lab?model=nfa', 'lab_nfa'], ['/lab?model=pda', 'lab_pda'], ['/related', 'related']]
for (const [u, n] of shots) { await b.goto(u, 2500); await b.shot(`${EV}/shot_${n}.png`) }
// mealy: run an example then shoot
await b.goto('/lab?model=pda', 2000); await b.eval(`document.querySelectorAll('[data-testid=example-case]')[1].click()`); await b.sleep(1200); await b.eval(`document.querySelector('[role=tabpanel]').scrollIntoView({block:'center'})`); await b.sleep(300); await b.shot(`${EV}/shot_lab_pda_reject.png`)
await b.goto('/related', 2500); await b.eval(`document.querySelector('.timeline-svg').scrollIntoView({block:'center'})`); await b.sleep(400); await b.shot(`${EV}/shot_related_timeline.png`)
await b.close()
