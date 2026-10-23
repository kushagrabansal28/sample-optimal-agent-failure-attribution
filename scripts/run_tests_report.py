"""Run the backend test-suite and write results/processed/test_report.json (shown live on the website).

Usage: python scripts/run_tests_report.py [pytest args]
"""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    xml = ROOT / "results" / "processed" / "_junit.xml"
    xml.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", "-q", f"--junitxml={xml}", *sys.argv[1:]]
    proc = subprocess.run(cmd, cwd=ROOT)
    tree = ET.parse(xml)
    xml.unlink(missing_ok=True)
    modules: dict[str, dict] = {}
    total = passed = failed = skipped = 0
    for tc in tree.iter("testcase"):
        mod = tc.get("classname", "").split(".")[-1] or "unknown"
        name = tc.get("name", "")
        outcome = "passed"
        if tc.find("failure") is not None or tc.find("error") is not None:
            outcome = "failed"
        elif tc.find("skipped") is not None:
            outcome = "skipped"
        m = modules.setdefault(mod, {"passed": 0, "failed": 0, "tests": []})
        m["tests"].append({"name": name, "outcome": outcome})
        total += 1
        if outcome == "passed":
            passed += 1; m["passed"] += 1
        elif outcome == "failed":
            failed += 1; m["failed"] += 1
        else:
            skipped += 1
    report = {"available": True, "total": total, "passed": passed, "failed": failed, "skipped": skipped, "modules": modules,
              "command": "python -m pytest", "ran_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
    out = ROOT / "results" / "processed" / "test_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"test report: {passed}/{total} passed, {failed} failed, {skipped} skipped -> {out}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
