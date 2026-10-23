# Paper appendices

| File | Contents | Source |
|---|---|---|
| [A_proof_theorem2.md](A_proof_theorem2.md) | proof of Theorem 2 (successive elimination sample complexity) | `paper/main.md` |
| [B_confidence_sequences.md](B_confidence_sequences.md) | notes on the stack-KL / Hoeffding confidence sequences and the KL-LUCB rate | `paper/main.md` |
| [C_automaton_specification.md](C_automaton_specification.md) | every state, action and transition of the 48-state automaton | generated from the model |
| [D_full_result_tables.md](D_full_result_tables.md) | every experiment group's aggregated numbers and the paired statistics | generated from `results/processed` |

Regenerate with `python scripts/build_appendices.py`. Appendices C and D are generated, never typed by hand.
