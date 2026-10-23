"""Run ONE trial from a JSON spec file and print the resulting row.

    python -m afcr.experiments.run_one configs/spec_automaton_prefix.json
    python -m afcr.experiments.run_one configs/spec_bandit_uniform.json --budget 5000 --seed 7 --out row.json

A spec is the same plain dict that the experiment suite builds (see afcr.experiments.core.run_spec); this CLI exists so that
any single number in the paper or on the website can be reproduced, inspected and varied from the command line.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import METHODS, run_spec

REQUIRED = ("kind", "method", "seed")


def load_spec(path: str | Path) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    spec = {k: v for k, v in spec.items() if not k.startswith("_")}          # keys starting with "_" are comments
    missing = [k for k in REQUIRED if k not in spec]
    if missing:
        raise ValueError(f"spec is missing required field(s): {missing}")
    if spec["kind"] not in ("bandit", "automaton", "toolagent"):
        raise ValueError(f"unknown kind {spec['kind']!r}")
    if spec["method"] not in METHODS:
        raise ValueError(f"unknown method {spec['method']!r}; choose from {sorted(METHODS)}")
    return spec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="path to a JSON spec")
    ap.add_argument("--seed", type=int, help="override the instance seed")
    ap.add_argument("--budget", type=int, help="override the rollout budget")
    ap.add_argument("--delta", type=float, help="override δ")
    ap.add_argument("--method", help="override the method")
    ap.add_argument("--out", help="write the row as JSON to this file")
    a = ap.parse_args(argv)
    spec = load_spec(a.spec)
    for k in ("seed", "budget", "delta", "method"):
        if getattr(a, k) is not None:
            spec[k] = getattr(a, k)
    row = run_spec(spec)
    text = json.dumps(row, indent=1, default=float)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
