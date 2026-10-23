// Responsive layout at 5 viewports + accessibility probes.
import { launch } from './cdp.mjs'
import fs from 'node:fs'
const EV = process.argv[2]
const b = await launch({ port: 9346 })
const VPS = [[1440, 900], [1280, 800], [1024, 768], [768, 1024], [390, 844]]
const ROUTES = ['/', '/lab', '/explorer?autoload=1', '/dashboard?autorun=1', '/studio', '/theory', '/related', '/reproducibility', '/docs']
const probe = `(()=>{const W=innerWidth; const over=[...document.querySelectorAll('main.page *')].filter(e=>{const r=e.getBoundingClientRect(); return r.width>0 && r.right>W+2 && getComputedStyle(e).position!=='fixed' && !e.closest('.tbl-wrap,.steps-scroll,.graph-wrap,pre,.pipeline,.tabs,.seg,.heat')}).map(e=>e.tagName.toLowerCase()+'.'+String(e.className).split(' ')[0]).slice(0,6);
 const sb=document.querySelector('.sidebar'); const sbr=sb.getBoundingClientRect(); const s=document.querySelector('.graph-svg');
 return {hOverflow:document.documentElement.scrollWidth>W, scrollW:document.documentElement.scrollWidth, overflowing:over, sidebarVisible: sbr.right>0 && sbr.left>=-1, topbar:getComputedStyle(document.querySelector('.topbar')).display!=='none', graphW:s?Math.round(s.getBoundingClientRect().width):null,
  graphVisibleNodes: s? [...s.querySelectorAll('.g-node')].filter(n=>{const r=n.getBoundingClientRect(), g=s.getBoundingClientRect(); return r.width>1 && r.left>=g.left-2 && r.right<=g.right+2 && r.top>=g.top-2 && r.bottom<=g.bottom+2}).length : null, graphNodes:s? s.querySelectorAll('.g-node').length:null,
  h1Size: getComputedStyle(document.querySelector('main.page h1, main.page h2')).fontSize, smallestText: Math.min(...[...document.querySelectorAll('main.page *')].filter(e=>e.childNodes.length && [...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())).map(e=>parseFloat(getComputedStyle(e).fontSize)))}})()`
const resp = {}
for (const [w, h] of VPS) {
  await b.viewport(w, h, w < 768)
  for (const r of ROUTES) {
    await b.goto(r, r.includes('auto') ? 5000 : 2600)
    resp[`${w}x${h} ${r}`] = await b.eval(probe)
    if (['/', '/lab', '/dashboard?autorun=1', '/explorer?autoload=1', '/studio'].includes(r)) await b.shot(`${EV}/resp_${w}x${h}_${r === '/' ? 'home' : r.slice(1).split('?')[0]}.png`)
  }
}
// mobile nav menu
await b.viewport(390, 844, true)
await b.goto('/lab', 2500)
await b.click('.topbar button'); await b.sleep(700)
const menu = await b.eval(`({open:document.querySelector('.sidebar').classList.contains('open'), scrim:!!document.querySelector('.scrim'), focusInside:document.querySelector('.sidebar').contains(document.activeElement)})`)
await b.shot(`${EV}/resp_390_menu_open.png`)
await b.clickText('a.nav-item', 'Theory'); await b.sleep(1200)
const menuAfter = await b.eval(`({open:document.querySelector('.sidebar').classList.contains('open'), path:location.pathname})`)
// Escape closes?
await b.click('.topbar button'); await b.sleep(500)
await b.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }); await b.sleep(500)
const escClose = await b.eval(`document.querySelector('.sidebar').classList.contains('open')`)

// ---------------- a11y
await b.viewport(1440, 900)
const a11y = {}
for (const r of ROUTES.map((x) => x.split('?')[0])) {
  await b.goto(r, 2600)
  a11y[r] = await b.eval(`(()=>{const name=e=>(e.getAttribute('aria-label')||e.getAttribute('aria-labelledby')||e.textContent||e.getAttribute('title')||'').trim();
   const lum=c=>{const m=c.match(/[\\d.]+/g); if(!m) return null; const [r,g,b]=m.slice(0,3).map(Number).map(v=>{v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)}); return 0.2126*r+0.7152*g+0.0722*b};
   const bgOf=e=>{let x=e; while(x){const c=getComputedStyle(x).backgroundColor; if(c && !c.includes('rgba(0, 0, 0, 0)') && !/rgba\\([^)]*, 0\\)/.test(c)) return c; x=x.parentElement} return getComputedStyle(document.body).backgroundColor};
   const lowContrast=[...document.querySelectorAll('main.page .muted, main.page .xs, main.page .hint, main.page .g-label, .nav-sep, main.page th')].slice(0,400).map(e=>{const f=lum(getComputedStyle(e).color), g=lum(bgOf(e)); if(f==null||g==null) return null; const cr=(Math.max(f,g)+0.05)/(Math.min(f,g)+0.05); return {cr:+cr.toFixed(2), fs:parseFloat(getComputedStyle(e).fontSize), cls:e.className&&String(e.className).slice(0,30), text:e.textContent.trim().slice(0,30)}}).filter(x=>x && x.cr<4.5);
   return {landmarks:{main:document.querySelectorAll('main').length, nav:document.querySelectorAll('nav').length, aside:document.querySelectorAll('aside').length, header:document.querySelectorAll('header').length},
    headings:[...document.querySelectorAll('h1,h2,h3,h4')].map(h=>h.tagName).join(''), h1:document.querySelectorAll('h1').length,
    unnamedButtons:[...document.querySelectorAll('button,[role=button]')].filter(e=>!name(e)).map(e=>e.outerHTML.slice(0,90)).slice(0,6),
    unlabeledInputs:[...document.querySelectorAll('input,select,textarea')].filter(e=>!(e.labels&&e.labels.length) && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby')).map(e=>e.outerHTML.slice(0,90)),
    imgsNoAlt:[...document.querySelectorAll('img')].filter(i=>!i.alt).length, nestedMain: document.querySelectorAll('main main').length,
    svgNoName:[...document.querySelectorAll('main.page svg[role=img]')].filter(s=>!s.getAttribute('aria-label')).length,
    lowContrastCount:lowContrast.length, lowContrastSample:lowContrast.slice(0,5), tabsWithoutPanels:[...document.querySelectorAll('[role=tab]')].filter(t=>!t.getAttribute('aria-controls')).length,
    clickableNonFocusable:[...document.querySelectorAll('main.page tr[style*=pointer], main.page g[style*=pointer]')].filter(e=>e.tabIndex<0).length}})()`)
}
// keyboard: tab from top — first focusable and whether focus ring visible; skip link?
await b.goto('/', 2000)
const tabSeq = []
for (let i = 0; i < 6; i++) {
  await b.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 }); await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 }); await b.sleep(150)
  tabSeq.push(await b.eval(`(()=>{const e=document.activeElement; const cs=getComputedStyle(e); return (e.tagName+' '+(e.textContent||e.getAttribute('aria-label')||'').trim().slice(0,30)+' | ring:'+(cs.boxShadow!=='none'||cs.outlineStyle!=='none'))})()`))
}
// keyboard on lab graph node and tabs arrow keys
await b.goto('/lab?model=dfa', 2500)
const nodeKb = await b.eval(`(()=>{const n=document.querySelector('.g-node'); n.focus(); n.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true})); return document.querySelector('.lab-grid aside .mono')?.textContent||null})()`)
await b.eval(`document.querySelector('.tabs [role=tab]').focus()`)
await b.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 }); await b.sleep(300)
const tabArrow = await b.eval(`({focused:document.activeElement.textContent, selected:document.querySelector('.tabs [role=tab][aria-selected=true]')?.textContent})`)
// live region for toasts / status announcements; route-change focus
const live = await b.eval(`({toastsLive:document.querySelector('.toasts')?.getAttribute('aria-live'), docTitleChangesPerRoute:document.title})`)
const out = { resp, menu, menuAfter, escapeClosesMenu: !escClose, a11y, tabSeq, nodeKb, tabArrow, live, exceptions: b.log.exceptions }
fs.writeFileSync(`${EV}/05_responsive_a11y.json`, JSON.stringify(out, null, 1))
await b.close()
console.log('ok')
