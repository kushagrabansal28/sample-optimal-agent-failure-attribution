# Automata glossary and semantics

| Model | Definition | Acceptance / halting | Memory | Nondeterminism | Probability | Fit for agent traces | Limits for causal attribution |
|---|---|---|---|---|---|---|---|
| **DFA** | M = (Q, Σ, δ, q₀, F), δ: Q×Σ→Q **total** | final state ∈ F | finite | none | none | nominal skeleton of an agent | no uncertainty; cannot express stochastic replay |
| **NFA** | δ: Q×Σ→2^Q | some path accepts (active-state set meets F) | finite | formal, not randomness | none | possible environment outcomes | no likelihoods; cannot rank causes |
| **ε-NFA** | δ: Q×(Σ∪{ε})→2^Q | ε-closure before/after each symbol | finite | formal + silent moves | none | silent self-correction ("heal") as ε-moves | as NFA |
| **Probabilistic automaton** | each (q,a) → distribution over successors | P(w) = e_{q₀}ᵀ M_{a₁}…M_{aₙ} 1_F | finite | none | **yes** | natural model of a stochastic agent | finite memory; Markov |
| **LTS** | s —a→ s′ with labels (reasoning, tool use, observation, update, validation, recovery, success, failure) | reachability of accepting/rejecting states; deadlocks | finite | allowed | optional | execution as labelled actions | labels carry meaning only by convention |
| **Mealy** | λ: Q×Σ→Γ | transducer | finite | none | none | controller reacting to observations | no acceptance notion |
| **Moore** | λ: Q→Γ | transducer (n+1 outputs for n inputs) | finite | none | none | state = action being executed | Mealy→Moore needs state expansion |
| **PDA** | finite control + stack; transitions (q,a,X,q′,γ) | final state and/or empty stack | unbounded stack | allowed | none | nested / recursive tool invocation | single stack, no probabilities |
| **Turing machine (bounded)** | tape + head + δ; step limit and tape bound | accept / reject / step_limit / tape_bound | tape (bounded in this simulator) | none | none | general-computation demonstration | bound is a simulator convenience; hitting it means *unknown*, not *reject* |

**State numbering.** In the laboratory every machine is drawn with states `q0, q1, …`; the initial state is always `q0`. The meaning of a state (e.g. `idle`, `dead`, `PLAN_SUBGOAL`) is shown beside it.

**Cases each machine demonstrates.**

| Machine | Cases (one-click examples on the website) |
|---|---|
| DFA (starts with `a`, even number of `b`) | accepted · rejected · **dead (trap) state** · empty word · invalid symbol |
| NFA (ends in `ab`) | accepted · rejected · empty word · a dead branch · invalid symbol; *Show as → DFA* = subset construction |
| ε-NFA (`a*b`) | accepted · only `b` (closure already contains `q2`) · rejected · empty word · too many `b`; *Show as → NFA / DFA* = ε-removal / subset construction |
| Probabilistic automaton | a probability for each word, never a verdict; empty word = probability 0; invalid symbol |
| LTS | accepted · failure · **blocked action** · empty word · label that is never enabled |
| Mealy / Moore | outputs for a run (n resp. n+1 outputs) · empty word · invalid symbol |
| PDA (nested calls) and typed PDA | balanced · **stack underflow** · **unclosed call** · type mismatch · empty word · invalid symbol — a rejection shows how far the machine got and why it stopped |
| Turing machines | increment (output) · palindromes (accept / reject) · a machine that never halts → **unknown** (step limit), not reject |

**Important distinctions.**
* NFA nondeterminism ("does some path accept?") is a formal device. LLM sampling randomness is *probabilistic*: it belongs in the probabilistic automaton / the policy π of the agent model.
* A probabilistic automaton or an LTS is the natural model of a stochastic agent; DFA, NFA, PDA and Turing machines are used for formal-language demonstrations and as structural views of the same 48-state specification. They are **not** forced into the same causal interpretation.
* A finite-state machine cannot recognise arbitrarily deep nesting; the PDA can (the tests show a depth-3-bounded DFA failing on a depth-5 word).

## The 48-state agent automaton

Six groups of eight states (PLAN, OBSERVE, TOOL, MEMORY, VALIDATE, TERMINAL). Roles: *benign*, *decision* (carries a planted fault), *fault entry*, *corridor* (corrupted state), *recovery*, *terminal_success*, *terminal_failure*. Views: LTS (policy × kernel probabilities), DFA (most-likely successor, explicit sink), NFA (all successors), ε-NFA (heal edges are ε), probabilistic automaton (environment kernel). The state count is validated programmatically (unique ids and labels; the DFA sink is not counted).

Exact quantities: V_t(q) = P(success | q, t) by backward induction;
μ_t^rep = Σ_{q′} P(q′ | q_{t−1}, ρ(q_{t−1})) V_t(q′); μ_t^res = V_{t−1}(q_{t−1}).
