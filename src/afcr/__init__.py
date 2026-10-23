"""AFCR — Automata-Aware Fixed-Confidence Replay.

Subpackages
-----------
automata     formal models (DFA, NFA, eps-NFA, probabilistic automaton, LTS, Mealy, Moore, PDA, TM)
             and the 48-state agent benchmark automaton
statistics   Bernoulli KL, confidence sequences (the *only* place bounds are defined)
replay       replay environments (arms) incl. automaton-induced and tool-agent environments
attribution  decision rules (targets), allocation algorithms, the engine
agents       controlled tool-using agent, model-provider abstraction
benchmarks   adapters for ALFWorld / HotpotQA (interfaces; full runs pending)
experiments  config-driven runners, aggregation, plotting
evaluation   metrics and statistical analysis of results
api          FastAPI application consumed by the website
"""

__version__ = "0.1.0"
