import numpy as np
import pytest

from afcr.automata.base import EPS, AutomatonError
from afcr.automata.benchmark48 import build_agent_model
from afcr.automata.dfa import DFA
from afcr.automata.lts import LTS, Transition
from afcr.automata.nfa import ENFA, NFA
from afcr.automata.pa import ProbabilisticAutomaton
from afcr.automata.pda import depth_bounded_dfa, nested_calls_pda, typed_nested_tools_pda
from afcr.automata.transducers import Moore, tool_call_controller_mealy
from afcr.automata.turing import binary_increment_tm, palindrome_tm


def even_a_dfa():
    return DFA({"e", "o"}, {"a", "b"}, {("e", "a"): "o", ("o", "a"): "e", ("e", "b"): "e", ("o", "b"): "o"}, "e", {"e"})


def test_dfa_total_deterministic_accepts():
    d = even_a_dfa()
    assert d.is_total() and d.is_deterministic()
    assert d.accepts("aab") and not d.accepts("ab") and d.accepts("")
    assert d.run("ab").steps[0].next_state == "o"


def test_dfa_missing_transition_raises_and_sink_completion():
    with pytest.raises(AutomatonError):
        DFA({"q"}, {"a", "b"}, {("q", "a"): "q"}, "q", {"q"})
    d = DFA({"q"}, {"a", "b"}, {("q", "a"): "q"}, "q", {"q"}, complete_with_sink=True)
    assert d.is_total() and d.accepts("aaa") and not d.accepts("ab") and d.logical_states() == {"q"}


def test_dfa_invalid_inputs():
    d = even_a_dfa()
    with pytest.raises(AutomatonError):
        d.accepts("c")
    with pytest.raises(AutomatonError):
        DFA({"q"}, {"a"}, {("q", "a"): "zz"}, "q", {"q"})


def ends_in_ab_nfa():
    return NFA({0, 1, 2}, {"a", "b"}, {(0, "a"): {0, 1}, (0, "b"): {0}, (1, "b"): {2}}, 0, {2})


def test_nfa_active_set_and_acceptance():
    n = ends_in_ab_nfa()
    t = n.run("aab")
    assert t.accepted and t.steps[0].next_state == frozenset({0, 1})
    assert not n.accepts("aba") and n.is_nondeterministic()


def test_nfa_to_dfa_equivalence():
    n = ends_in_ab_nfa()
    d = n.to_dfa()
    assert all(n.accepts(w) == d.accepts(w) for w in d.words_up_to(7))


def test_enfa_closure_and_equivalence():
    e = ENFA({0, 1, 2, 3}, {"a", "b"}, {(0, EPS): {1}, (1, EPS): {2}, (1, "a"): {1}, (2, "b"): {3}}, 0, {3})
    assert e.eps_closure({0}) == frozenset({0, 1, 2})
    assert e.eps_closure_steps({0})[0] == frozenset({0})
    n, d = e.to_nfa(), e.to_dfa()
    for w in d.words_up_to(6):
        assert e.accepts(w) == n.accepts(w) == d.accepts(w)


def test_pa_normalisation_and_probability():
    with pytest.raises(AutomatonError):
        ProbabilisticAutomaton({"s", "t"}, {"a"}, {("s", "a"): {"s": 0.5, "t": 0.4}}, "s", {"t"})
    pa = ProbabilisticAutomaton({"s", "t"}, {"a"}, {("s", "a"): {"s": 0.5, "t": 0.5}, ("t", "a"): {"t": 1.0}}, "s", {"t"})
    assert pa.acceptance_probability("aaa") == pytest.approx(1 - 0.5 ** 3)
    mc = pa.monte_carlo_acceptance("aaa", 4000, np.random.default_rng(0))
    assert mc["ci_lo"] <= 0.875 <= mc["ci_hi"]
    a = pa.sample_run("aaaa", np.random.default_rng(3)).to_json()
    b = pa.sample_run("aaaa", np.random.default_rng(3)).to_json()
    assert a == b


def test_lts_reachability_deadlock():
    l = LTS({"a", "b", "c", "d"}, [Transition("a", "x", "b"), Transition("b", "y", "c")], "a", accepting={"c"})
    assert l.reachable() == {"a", "b", "c"} and l.accepting_reachable() and not l.rejecting_reachable()
    assert l.deadlocks() == set() and l.run_labels(["x", "y"]) == {"c"}
    l2 = LTS({"a", "b"}, [Transition("a", "x", "b")], "a")
    assert l2.deadlocks() == {"b"}


def test_mealy_moore():
    m = tool_call_controller_mealy()
    assert m.same_state_different_outputs()
    assert m.outputs_for(["task", "ok"]) == ["call_tool", "proceed"]
    mo = m.to_moore("start")
    w = ["task", "error", "ok", "task"]
    assert mo.outputs_for(w)[1:] == m.outputs_for(w) and len(mo.states) >= len(m.states)
    assert mo.to_mealy().outputs_for(w) == mo.outputs_for(w)[1:]
    with pytest.raises(AutomatonError):
        Moore({"q"}, {"a"}, {"x"}, {("q", "a"): "q"}, {}, "q")


def test_pda_requires_stack():
    p = nested_calls_pda()
    assert p.accepts(["call", "call", "ret", "ret"]) and not p.accepts(["call", "call", "ret"]) and not p.accepts(["ret"])
    d = depth_bounded_dfa(3)
    deep = ["call"] * 5 + ["ret"] * 5
    assert p.accepts(deep) and not d.accepts(deep)       # bounded memory fails on deeper nesting
    assert p.run(["call", "ret"]).steps[0].info["op"] == "push"
    t = typed_nested_tools_pda()
    assert t.accepts(["open_search", "open_calc", "end_calc", "end_search"])
    assert not t.accepts(["open_search", "open_calc", "end_search", "end_calc"])


def test_turing():
    inc = binary_increment_tm()
    assert inc.run("1011").final.contents() == "1100" and inc.run("111").final.contents() == "1000"
    pal = palindrome_tm()
    assert pal.accepts("abba") and pal.accepts("aba") and not pal.accepts("ab") and pal.accepts("")
    assert inc.run("1111", max_steps=2).status == "step_limit"
    assert inc.run("1" * 8, max_cells=9).status in ("tape_bound", "accept")


def test_agent48_state_count_and_validity():
    for n in (48, 64, 96):
        m = build_agent_model(n)
        m.validate()
        assert m.count_logical_states() == n
    m = build_agent_model(48)
    assert m.group_counts() == {g: 8 for g in ("PLAN", "OBSERVE", "TOOL", "MEMORY", "VALIDATE", "TERMINAL")}
    with pytest.raises(AutomatonError):
        build_agent_model(40)
    for sp in m.specs.values():
        assert sp.info.description and sp.info.label
        if sp.info.kind == "nonterminal":
            assert sp.actions


def test_agent48_views_and_formal_properties():
    m = build_agent_model(48)
    d = m.to_dfa()
    assert d.is_total() and d.sink_added and len(d.logical_states()) == 48
    assert d.reachable() & m.accepting and d.reachable() & m.rejecting
    assert m.to_enfa().has_epsilon() and m.to_nfa().is_nondeterministic()
    lts = m.to_lts()
    assert not lts.deadlocks() and lts.accepting_reachable() and lts.rejecting_reachable()
    for t in m.accepting | m.rejecting:
        assert not m.specs[t].actions                    # absorbing terminals
    rng = np.random.default_rng(0)
    n = 6000
    k = sum(m.simulate(rng, m.idx[m.init], 0, record=False).success for _ in range(n))
    p = m.success_probability()
    assert abs(k / n - p) < 4 * np.sqrt(p * (1 - p) / n)  # exact DP agrees with Monte Carlo


def test_exact_mu_planted_culprit_is_argmax():
    m = build_agent_model(48, eps={"PLAN_SUBGOAL": 0.6})
    tr = m.sample_failed(np.random.default_rng(2), require_fault=True)
    mu = m.exact_mu(tr, "repair")
    if len(tr.fault_steps) == 1:
        assert int(np.argmax(mu)) + 1 == tr.planted_cause
