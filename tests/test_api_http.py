"""HTTP-layer behaviour of the API: validation, security of the static fallback, error contract."""
import pytest
from fastapi.testclient import TestClient

from afcr.api.app import DIST, app

client = TestClient(app)
BAD_REPLAY = [{"seed": -1, "arm": 0}, {"seed": 0, "arm": 0, "n_states": 500}, {"seed": 0, "arm": 0, "n_states": 10}, {"seed": 0, "arm": 0, "eps_plan": 1.5},
              {"seed": 0, "arm": -1}, {"seed": 0, "arm": 999}]


@pytest.mark.parametrize("body", BAD_REPLAY)
def test_replay_rejects_bad_input_with_422(body):
    r = client.post("/api/replay", json=body)
    assert r.status_code == 422 and r.json()["detail"]


def test_estimate_rejects_negative_seed_with_422():
    assert client.post("/api/replay/estimate", json={"seed": -3, "arm": 0, "n": 10}).status_code == 422


def test_no_endpoint_returns_500_for_out_of_range_numbers():
    for path, body in [("/api/attribute", {"seed": -1}), ("/api/attribute", {"n_states": 5}), ("/api/trajectory", {"seed": -1}),
                       ("/api/replay", {"seed": -1}), ("/api/replay/estimate", {"seed": -1, "n": 5}), ("/api/experiment/run", {"seed": -2}),
                       ("/api/automata/trace", {"model": "dfa", "seed": -1})]:
        assert client.post(path, json=body).status_code == 422, (path, body)


def test_oversized_experiment_is_refused_with_an_explanation():
    r = client.post("/api/experiment/run", json={"trials": 60, "algorithms": ["lucb"] * 12, "budget": 100000})
    assert r.status_code == 422 and "exceeds the limit" in r.json()["detail"]


def test_a_small_experiment_still_runs():
    r = client.post("/api/experiment/run", json={"trials": 1, "algorithms": ["lucb"], "budget": 500, "seed": 3})
    assert r.status_code == 200 and r.json()["rows"]


def test_replay_and_estimate_still_work_for_valid_input():
    assert client.post("/api/replay", json={"seed": 5, "arm": 3}).status_code == 200
    assert client.post("/api/replay/estimate", json={"seed": 5, "arm": 3, "n": 20}).status_code == 200


needs_dist = pytest.mark.skipif(not DIST.exists(), reason="website not built")


@needs_dist
@pytest.mark.parametrize("path", ["/../../pyproject.toml", "/..%2F..%2Fpyproject.toml", "/%2e%2e/%2e%2e/pyproject.toml", "/..%5C..%5Cpyproject.toml",
                                  "/assets/../../../pyproject.toml", "/....//....//pyproject.toml"])
def test_static_fallback_never_serves_files_outside_dist(path):
    r = client.get(path)
    assert "build-system" not in r.text and "setuptools" not in r.text


@needs_dist
def test_unknown_api_and_file_routes_are_404_json_but_pages_still_load():
    for p in ("/api/nope", "/api/models", "/api/results/groups", "/files/nope.md"):
        r = client.get(p)
        assert r.status_code == 404 and r.headers["content-type"].startswith("application/json"), p
    for p in ("/", "/lab", "/dashboard", "/some/unknown/page"):
        r = client.get(p)
        assert r.status_code == 200 and "<div id=\"root\">" in r.text, p


@needs_dist
def test_built_assets_are_still_served():
    index = client.get("/").text
    import re
    js = re.search(r'src="(/assets/[^"]+\.js)"', index).group(1)
    r = client.get(js)
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]


def test_openapi_summaries_are_meaningful():
    spec = client.get("/openapi.json").json()
    for path, methods in spec["paths"].items():
        for m, d in methods.items():
            assert len((d.get("summary") or "").strip()) >= 3, (m, path)
