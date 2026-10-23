"""Export paper/main.md and report/technical_report.md to PDF using node (markdown-it + KaTeX) and headless Edge/Chrome.

    python scripts/build_pdfs.py
Needs: `cd scripts/pdf && npm install` (once) and Microsoft Edge or Google Chrome.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "scripts" / "pdf"
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe", "/usr/bin/google-chrome", "/usr/bin/chromium", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]


def browser() -> str:
    for b in BROWSERS:
        if Path(b).exists():
            return b
    w = shutil.which("msedge") or shutil.which("chrome") or shutil.which("google-chrome")
    if not w:
        raise SystemExit("no Edge/Chrome found; open the generated HTML in a browser and print to PDF")
    return w


def build(md: Path, pdf: Path) -> None:
    html = ROOT / "results" / "processed" / f"_{md.stem}.html"
    subprocess.run(["node", str(PDF / "md2html.mjs"), str(md), str(html)], cwd=PDF, check=True)
    subprocess.run([browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=60000",
                    f"--print-to-pdf={pdf}", html.as_uri()], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    html.unlink(missing_ok=True)
    try:
        import pymupdf
        n = len(pymupdf.open(pdf))
    except Exception:
        n = "?"
    print(f"wrote {pdf.relative_to(ROOT)} ({pdf.stat().st_size // 1024} KB, {n} pages)")


if __name__ == "__main__":
    build(ROOT / "paper" / "main.md", ROOT / "paper" / "main.pdf")
    build(ROOT / "report" / "technical_report.md", ROOT / "report" / "technical_report.pdf")
