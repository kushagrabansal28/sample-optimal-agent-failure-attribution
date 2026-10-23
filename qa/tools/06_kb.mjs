import { launch } from './cdp.mjs'
const b = await launch({ port: 9347 })
await b.viewport(1440, 900)
await b.goto('/lab?model=dfa', 2500)
// Tab until a graph node is focused
let found = false
for (let i = 0; i < 80; i++) {
  await b.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 }); await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 })
  if (await b.eval(`!!document.activeElement?.classList?.contains('g-node')`)) { found = i + 1; break }
}
await b.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' }); await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 })
await b.sleep(500)
const sel = await b.eval(`(document.querySelector('.lab-grid aside .card')?.innerText||'').slice(0,80)`)
// focus ring visible on svg node?
const ring = await b.eval(`(()=>{const e=document.activeElement; const cs=getComputedStyle(e); return {tag:e.tagName, outline:cs.outlineStyle+' '+cs.outlineWidth, shadow:cs.boxShadow}})()`)
// arrow keys on the zoomable svg
console.log(JSON.stringify({ tabsToFirstNode: found, afterEnter: sel, ring }))
await b.close()
