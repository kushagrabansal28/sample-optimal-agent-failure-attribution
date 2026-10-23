import json
from pathlib import Path

import pytest

from afcr.experiments.run_one import load_spec, main
from afcr.experiments.suite import ALL

CONFIGS = Path(__file__).resolve().parents[1] / "configs"
SPECS = sorted(CONFIGS.glob("spec_*.json"))


def test_there_are_example_specs_for_every_instance_family():
    kinds = {load_spec(p)["kind"] for p in SPECS}
    assert kinds == {"bandit", "automaton", "toolagent"}
    assert len(SPECS) >= 8


@pytest.mark.parametrize("path", SPECS, ids=lambda p: p.name)
def test_every_example_spec_runs_and_is_reproducible(path, tmp_path):
    out = tmp_path / "row.json"
    assert main([str(path), "--budget", "1500", "--out", str(out)]) == 0
    a = json.loads(out.read_text())
    assert main([str(path), "--budget", "1500", "--out", str(out)]) == 0
    b = json.loads(out.read_text())
    for k in ("answer", "truth", "rollouts", "status", "correct"):
        assert a[k] == b[k]                                       # same spec + seed => same row (wall time may differ)
    assert a["rollouts"] <= 1500


def test_cli_overrides_and_validation(tmp_path):
    spec = CONFIGS / "spec_bandit_uniform.json"
    out = tmp_path / "r.json"
    main([str(spec), "--method", "lucb", "--seed", "3", "--budget", "3000", "--out", str(out)])
    row = json.loads(out.read_text())
    assert row["method"] == "lucb" and row["seed"] == 3
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"kind": "bandit", "method": "nope", "seed": 0}))
    with pytest.raises(ValueError):
        load_spec(bad)
    bad.write_text(json.dumps({"kind": "bandit"}))
    with pytest.raises(ValueError):
        load_spec(bad)


def test_suite_configs_reference_known_groups():
    for name in ("suite_default.json", "suite_quick.json"):
        cfg = json.loads((CONFIGS / name).read_text())
        assert set(cfg["groups"]) <= set(ALL) and cfg["trials"] >= 1 and cfg["workers"] >= 1
