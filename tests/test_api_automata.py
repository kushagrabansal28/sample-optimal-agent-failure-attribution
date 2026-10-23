"""The automata laboratory API: q-numbered states, truthful per-model results, and every documented example case."""
import re

import pytest
from fastapi.testclient import TestClient

from afcr.api import lab
from afcr.api.app import app

client = TestClient(app)
MODELS = [m for m in lab.MODEL_INFO if m != "agent48"]


def graph(model, **q):
    r = client.get("/api/automata/graph", params={"model": model, **q})
    assert r.status_code == 200, r.text
    return r.json()


def trace(model, word, seed=0):
    return client.post("/api/automata/trace", json={"model": model, "word": word, "seed": seed})


@pytest.mark.parametrize("model", MODELS)
def test_every_graph_has_q_numbered_states_one_start_and_valid_edges(model):
    g = graph(model)
    ids = [n["id"] for n in g["nodes"]]
    assert ids == [n["qid"] for n in g["nodes"]]
    assert all(re.fullmatch(r"q\d+", i) for i in ids) and len(set(ids)) == len(ids)
    assert sorted(int(i[1:]) for i in ids) == list(range(len(ids)))               # q0 … q(n-1), no gaps
    starts = [n for n in g["nodes"] if n.get("start")]
    assert len(starts) == 1 and starts[0]["id"] == "q0"                            # the initial state is q0
    assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])
    assert g["n_states"] == len(ids) and g["kind"] and g["info"]["description"]


def test_agent48_states_are_q0_to_q47_and_the_count_is_48():
    g = graph("agent48")
    assert [n["qid"] for n in g["nodes"]] == [f"q{i}" for i in range(48)]
    assert g["count_logical_states"] == 48 and g["state_count_validated"] is True
    assert g["nodes"][0]["name"] == "PLAN_START" and g["nodes"][0]["qid"] == "q0"


def test_agent48_dfa_view_is_total_and_draws_the_sink_without_counting_it():
    g = graph("agent48", view="dfa")
    sink = [n for n in g["nodes"] if n.get("sink")]
    assert len(sink) == 1 and len(g["nodes"]) == 49 and g["count_logical_states"] == 48
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])
    logical = {n["id"] for n in g["nodes"]} - {sink[0]["id"]}
    to_sink = {e["source"] for e in g["edges"] if e["target"] == sink[0]["id"]}
    assert to_sink <= logical and len(to_sink) > 0                                # every non-total state has a default edge to the sink


def test_derived_views_of_nfa_and_enfa():
    d = graph("nfa", view="dfa")
    assert d["view"] == "dfa" and {n["name"] for n in d["nodes"]} >= {"{q0}", "{q0,q1}", "{q0,q2}"}      # subset construction
    assert {"nfa", "dfa"} == set(graph("nfa")["views"])
    e = graph("enfa", view="nfa")
    assert not any(x["label"] == "ε" for x in e["edges"])                         # ε-removal leaves no silent moves
    de = graph("enfa", view="dfa")
    assert any(n.get("dead") for n in de["nodes"]) and de["nodes"][0]["name"] == "{q0,q1,q2}"   # start = ε-closure, ∅ is the dead state
    assert client.get("/api/automata/graph", params={"model": "dfa", "view": "nfa"}).status_code == 422


def test_toy_dfa_is_total_and_has_a_dead_state():
    g = graph("dfa")
    table = g["transition_table"]
    assert all(set(row) == {"a", "b"} for row in table.values())                  # δ total
    dead = [n for n in g["nodes"] if n["name"] == "dead"]
    assert dead and all(table[dead[0]["id"]][a] == dead[0]["id"] for a in "ab")


@pytest.mark.parametrize("model", MODELS)
def test_every_documented_example_behaves_as_stated(model):
    info = lab.MODEL_INFO[model]
    assert info["examples"], model
    for exm in info["examples"]:
        r = trace(model, exm["word"])
        if exm["expect"] == "error":
            assert r.status_code == 422, (model, exm)
            continue
        assert r.status_code == 200, (model, exm, r.text)
        d = r.json()
        assert isinstance(d["steps"], list) and d["kind"] == info["kind"]
        if exm["expect"] == "accept":
            assert d["accepted"] is True, (model, exm)
        elif exm["expect"] == "reject":
            assert d["accepted"] is False and d["reason"], (model, exm)
        elif exm["expect"] == "unknown":
            assert d["unknown"] is True and d["accepted"] is None and "unknown" in d["reason"], (model, exm)
        elif exm["expect"] == "probability":
            assert 0.0 <= d["exact_acceptance_probability"] <= 1.0 and "accepted" not in d
        elif exm["expect"] == "output":
            assert "outputs" in d or "output" in d, (model, exm)
            assert "accepted" not in d or d["accepted"] is not False


def test_probabilistic_automaton_reports_a_probability_not_a_verdict():
    d = trace("pa", ["go", "go", "go"]).json()
    assert "accepted" not in d and "sample_ended_accepting" in d
    assert d["exact_acceptance_probability"] == pytest.approx(0.868, abs=1e-9)
    assert d["monte_carlo"]["ci_lo"] >= 0.0 and d["monte_carlo"]["ci_lo"] <= d["exact_acceptance_probability"] <= d["monte_carlo"]["ci_hi"] + 0.02


@pytest.mark.parametrize("model", ["mealy", "moore"])
def test_transducers_have_outputs_and_no_acceptance(model):
    d = trace(model, ["task", "error", "ok"]).json()
    assert "accepted" not in d and d["outputs"]
    assert len(d["outputs"]) == (3 if model == "mealy" else 4)                      # Mealy: n outputs, Moore: n+1


def test_pda_rejection_still_shows_where_it_failed():
    d = trace("pda", ["call", "ret", "ret"]).json()
    assert d["accepted"] is False and len(d["steps"]) >= 2 and "stack" in d["reason"]
    assert d["steps"][0]["stack_after"][0] == "C"
    d = trace("pda_typed", ["open_search", "end_calc"]).json()
    assert d["accepted"] is False and "stack top S" in d["reason"]


def test_turing_machine_traces_are_consistent_and_unknown_is_not_reject():
    d = trace("tm", list("1011")).json()
    assert isinstance(d["steps"], list) and d["n_steps"] == len(d["steps"]) == len(d["trace"]) - 1
    assert d["output"] == "1100" and d["accepted"] is True and d["steps"][0]["state"] == "q0"
    loop = trace("tm_loop", list("01")).json()
    assert loop["status"] == "step_limit" and loop["unknown"] and loop["accepted"] is None and loop["halted"] is False


def test_nfa_trace_exposes_active_sets_and_enfa_the_initial_closure():
    d = trace("nfa", ["a", "a", "b"]).json()
    assert d["steps"][0]["state"] == ["q0"] and d["steps"][0]["next_state"] == ["q0", "q1"] and d["accepted"]
    e = trace("enfa", ["a", "b"]).json()
    assert e["initial_active"] == ["q0", "q1", "q2"] and e["accepted"]
    dead = trace("nfa", ["b", "b"]).json()
    assert dead["accepted"] is False and dead["steps"][-1]["next_state"] == ["q0"]


def test_lts_blocked_step_is_reported():
    d = trace("lts", ["plan", "answer", "plan"]).json()
    assert d["blocked"] == {"state": "q3", "label": "plan"} and "blocked" in d["reason"]
    assert d["steps"][-1]["blocked"] is True and d["deadlocks"] == []          # q3/q4 are terminal, not deadlocks


def test_unknown_model_and_oversized_state_counts_are_rejected():
    assert trace("nope", []).status_code == 404
    assert client.get("/api/automata/graph", params={"model": "nope"}).status_code == 404
    assert client.get("/api/automata/graph", params={"model": "agent48", "n_states": 1000}).status_code == 422
    assert client.post("/api/automata/trace", json={"model": "agent48", "n_states": 1000}).status_code == 422
