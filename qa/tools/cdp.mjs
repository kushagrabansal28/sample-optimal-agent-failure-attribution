// Minimal Chrome DevTools Protocol driver for headless Edge (audit tooling; not part of the project).
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const EDGE = ['C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Microsoft/Edge/Application/msedge.exe'].find((p) => fs.existsSync(p))
export const BASE = process.env.BASE || 'http://localhost:8000'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export async function launch({ port = 9333, reducedMotion = false, noRaf = false } = {}) {
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'afcr-audit-'))
  const args = ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`, `--user-data-dir=${prof}`, '--no-first-run', '--hide-scrollbars', '--window-size=1440,900']
  if (reducedMotion) args.push('--force-prefers-reduced-motion')
  const proc = spawn(EDGE, [...args, 'about:blank'], { stdio: 'ignore' })
  let ver
  for (let i = 0; i < 60; i++) { try { ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break } catch { await sleep(250) } }
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()
  const page = targets.find((t) => t.type === 'page')
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((r) => ws.addEventListener('open', r, { once: true }))
  let id = 0
  const pending = new Map()
  const log = { console: [], exceptions: [], network: [], requests: [] }
  const listeners = []
  ws.addEventListener('message', (m) => {
    const msg = JSON.parse(m.data)
    if (msg.id && pending.has(msg.id)) { const { res, rej } = pending.get(msg.id); pending.delete(msg.id); msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result); return }
    if (msg.method === 'Runtime.consoleAPICalled') log.console.push({ type: msg.params.type, text: msg.params.args.map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 400), url: page_url })
    if (msg.method === 'Runtime.exceptionThrown') log.exceptions.push({ text: (msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text || '').slice(0, 600), url: page_url })
    if (msg.method === 'Log.entryAdded') log.console.push({ type: 'log-' + msg.params.entry.level, text: (msg.params.entry.text || '').slice(0, 400) + ' ' + (msg.params.entry.url || ''), url: page_url })
    if (msg.method === 'Network.responseReceived') { const r = msg.params.response; if (r.url.includes('/api/') || r.url.includes('openapi')) log.requests.push({ url: r.url.replace(BASE, ''), status: r.status, page: page_url }); if (r.status >= 400) log.network.push({ url: r.url.replace(BASE, ''), status: r.status, page: page_url }) }
    if (msg.method === 'Network.loadingFailed') log.network.push({ failed: msg.params.errorText, id: msg.params.requestId, page: page_url })
    listeners.forEach((l) => l(msg))
  })
  let page_url = ''
  const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })) })
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable'); await send('Log.enable')
  // noRaf: simulate a window that never paints (hidden pane / background tab): animation frames never run
  if (noRaf) await send('Page.addScriptToEvaluateOnNewDocument', { source: 'window.requestAnimationFrame = () => 0; window.cancelAnimationFrame = () => {}' })
  const api = {
    send, log, sleep,
    async viewport(width, height, mobile = false) { await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile }); if (mobile) await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 }) },
    async goto(url, wait = 2500) {
      page_url = url
      const loaded = new Promise((r) => { const l = (m) => { if (m.method === 'Page.loadEventFired') { listeners.splice(listeners.indexOf(l), 1); r() } }; listeners.push(l) })
      await send('Page.navigate', { url: url.startsWith('http') ? url : BASE + url })
      await Promise.race([loaded, sleep(15000)])
      await sleep(wait)
    },
    async eval(expr, awaitPromise = true) {
      const r = await send('Runtime.evaluate', { expression: expr, awaitPromise, returnByValue: true })
      if (r.exceptionDetails) throw new Error('eval: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text))
      return r.result.value
    },
    async shot(file, full = false) {
      let clip
      if (full) { const m = await send('Page.getLayoutMetrics'); clip = { x: 0, y: 0, width: m.cssContentSize.width, height: Math.min(m.cssContentSize.height, 6000), scale: 1 } }
      const r = await send('Page.captureScreenshot', { format: 'png', ...(clip ? { clip, captureBeyondViewport: true } : {}) })
      fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, Buffer.from(r.data, 'base64'))
    },
    async click(selector) { return api.eval(`(()=>{const el=document.querySelector(${JSON.stringify(selector)}); if(!el) return 'NOT FOUND: ${selector.replace(/'/g, '')}'; el.scrollIntoView({block:'center'}); el.click(); return 'ok'})()`) },
    async clickText(sel, text) { return api.eval(`(()=>{const el=[...document.querySelectorAll(${JSON.stringify(sel)})].find(e=>e.textContent.trim().includes(${JSON.stringify(text)})); if(!el) return 'NOT FOUND'; el.scrollIntoView({block:'center'}); el.click(); return 'ok'})()`) },
    async close() { try { await send('Browser.close') } catch { /* ignore */ } proc.kill(); },
  }
  return api
}
