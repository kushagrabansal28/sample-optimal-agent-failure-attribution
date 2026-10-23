"""Screenshot every website page with headless Edge (API must be running on :8000 and the site built).

    python scripts/take_screenshots.py            # -> report/screens/*.png
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "screens"
BASE = "http://localhost:8000"
EDGE = next((p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if Path(p).exists()), None)
PAGES = {
    "overview": "/", "related": "/related", "lab": "/lab", "lab_pda": "/lab?model=pda", "explorer": "/explorer?autoload=1",
    "dashboard": "/dashboard?autorun=1", "studio": "/studio", "theory": "/theory",
    "reproducibility": "/reproducibility", "docs": "/docs",
}


def main() -> int:
    if not EDGE:
        print("Edge not found"); return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for name, path in PAGES.items():
        dest = OUT / f"{name}.png"
        with tempfile.TemporaryDirectory() as prof:
            cmd = [EDGE, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--hide-scrollbars", "--force-prefers-reduced-motion",
                   "--window-size=1440,1000", "--virtual-time-budget=14000", f"--screenshot={dest}", BASE + path]
            subprocess.run(cmd, capture_output=True, timeout=120)
        print(name, "ok" if dest.exists() else "FAILED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
