// node md2html.mjs <input.md> <output.html>   -- Markdown (+ KaTeX math, tables, images) to a print-styled HTML page.
import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import MarkdownIt from 'markdown-it'
import mk from '@vscode/markdown-it-katex'
import anchor from 'markdown-it-anchor'

const [, , inp, out] = process.argv
const src = fs.readFileSync(inp, 'utf8').replace(/\r\n/g, '\n')
const dir = path.dirname(path.resolve(inp))
const m = src.match(/^---\n([\s\S]*?)\n---\n/)
let body = m ? src.slice(m[0].length) : src
let title = 'Document', authors = ''
if (m) {
  const t = m[1].match(/title:\s*"(.*)"/); if (t) title = t[1]
  const a = m[1].match(/authors:\s*"(.*)"/); if (a) authors = a[1]
}
const md = new MarkdownIt({ html: true, linkify: true, typographer: false }).use(mk.default ?? mk, { throwOnError: false }).use(anchor.default ?? anchor, { permalink: false })
// resolve images to absolute file URLs
const defaultImage = md.renderer.rules.image
md.renderer.rules.image = (tokens, idx, options, env, self) => {
  const t = tokens[idx]; const s = t.attrGet('src')
  if (s && !/^(https?:|data:|file:)/.test(s)) t.attrSet('src', pathToFileURL(path.resolve(dir, s)).href)
  return defaultImage ? defaultImage(tokens, idx, options, env, self) : self.renderToken(tokens, idx, options)
}
// figures: wrap image paragraphs as <figure> with caption
let html = md.render(body)
const authorsHtml = authors ? `<p class="authors">${authors}</p>` : ''
html = html.replace(/<p><img src="([^"]+)" alt="([^"]*)"[^>]*><\/p>/g, (_, s, a) => `<figure><img src="${s}" alt="${a}"><figcaption>${a}</figcaption></figure>`)
const katexCss = pathToFileURL(path.resolve('node_modules/katex/dist/katex.min.css')).href
const doc = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${title}</title>
<link rel="stylesheet" href="${katexCss}">
<style>
@page { size: A4; margin: 20mm 17mm 22mm 17mm; @bottom-center { content: counter(page); font: 9pt "Segoe UI", Arial, sans-serif; color: #555 } }
html { font-size: 10.4pt } body { font-family: "Cambria", "Georgia", "Times New Roman", serif; line-height: 1.5; color: #111; max-width: 100%; }
h1 { font: 700 20pt "Segoe UI", Arial, sans-serif; line-height: 1.2; margin: 0 0 6pt; color: #0b1730 }
h2 { font: 700 14.5pt "Segoe UI", Arial, sans-serif; margin: 20pt 0 6pt; color: #0b1730; border-bottom: 1.2px solid #c7d0e0; padding-bottom: 3pt; break-after: avoid }
h3 { font: 700 11.5pt "Segoe UI", Arial, sans-serif; margin: 13pt 0 4pt; color: #1d2f57; break-after: avoid }
h4 { font: 700 10.5pt "Segoe UI", Arial, sans-serif; margin: 10pt 0 3pt; break-after: avoid }
p { margin: 0 0 7pt; text-align: justify; hyphens: auto; orphans: 3; widows: 3 }
a { color: #1d4ed8; text-decoration: none }
code { font: 8.6pt Consolas, "Courier New", monospace; background: #eef1f7; padding: 0 2.5pt; border-radius: 2px }
pre { background: #f4f6fb; border: 1px solid #d9dfec; border-radius: 4px; padding: 6pt 8pt; font: 7.8pt/1.45 Consolas, "Courier New", monospace; white-space: pre-wrap; break-inside: avoid }
pre code { background: none; padding: 0 }
table { border-collapse: collapse; width: 100%; margin: 7pt 0 10pt; font: 7.9pt/1.35 "Segoe UI", Arial, sans-serif; break-inside: auto }
thead { display: table-header-group } tr { break-inside: avoid }
th { background: #e9eef8; text-align: left; font-weight: 700 } th, td { border: 0.6px solid #c4cde0; padding: 2.5pt 4pt; vertical-align: top }
tbody tr:nth-child(even) td { background: #f8f9fd }
figure { margin: 9pt 0 11pt; text-align: center; break-inside: avoid } figure img { max-width: 100%; max-height: 118mm; border: 0.5px solid #dde3ef }
figcaption { font: italic 8.6pt "Segoe UI", Arial, sans-serif; color: #444; margin-top: 3pt }
blockquote { border-left: 3px solid #b7c4e0; margin: 6pt 0; padding: 1pt 9pt; color: #333; background: #f7f9fd }
ul, ol { margin: 0 0 7pt; padding-left: 16pt } li { margin-bottom: 2pt }
.katex-display { margin: 7pt 0; overflow: visible } .katex { font-size: 1.02em }
.titleblock { margin-bottom: 10pt }
.authors { font: 11pt "Segoe UI", Arial, sans-serif; color: #333 }
</style></head><body>${html}</body></html>`
fs.writeFileSync(out, doc)
console.log('wrote', out, `(${doc.length} bytes)`)
