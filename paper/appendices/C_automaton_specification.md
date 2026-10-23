# Appendix C. Specification of the 48-state agent automaton

Generated from `build_agent_model(48)`. 48 logical states, horizon 96, alphabet size 41, unconditional success probability 0.5607. Groups: PLAN (8), OBSERVE (8), TOOL (8), MEMORY (8), VALIDATE (8), TERMINAL (8).

Roles: *benign*, *decision* (carries a planted fault action), *fault_entry*, *corridor* (corrupted state), *recovery*, *terminal_success*, *terminal_failure*.

## States

| # | id | label | group | role | reference action | policy over actions |
|---|---|---|---|---|---|---|
| 0 | `PLAN_START` | Start | PLAN | benign | start | start: 1.00 |
| 1 | `PLAN_PARSE` | Parse task | PLAN | benign | parse | parse: 1.00 |
| 2 | `PLAN_DECOMP` | Decompose task | PLAN | benign | decompose | decompose: 1.00 |
| 3 | `PLAN_SUBGOAL` | Select subgoal | PLAN | decision | select_good | select_good: 0.75, select_wrong: 0.25 |
| 4 | `PLAN_SUBGOAL_WRONG` | Wrong subgoal selected | PLAN | fault_entry | propagate | propagate: 1.00 |
| 5 | `PLAN_TOOLS` | Plan tool use | PLAN | benign | plan_tools | plan_tools: 1.00 |
| 6 | `PLAN_REVISE` | Revise plan | PLAN | benign | revise | revise: 1.00 |
| 7 | `PLAN_COMMIT` | Commit plan | PLAN | benign | commit | commit: 1.00 |
| 8 | `OBS_QUERY` | Formulate query | OBSERVE | benign | query | query: 1.00 |
| 9 | `OBS_SEARCH` | Choose resource | OBSERVE | decision | search_good | search_good: 0.85, search_wrong: 0.15 |
| 10 | `OBS_WRONG_RESOURCE` | Wrong resource searched | OBSERVE | fault_entry | propagate | propagate: 1.00 |
| 11 | `OBS_RESULTS` | Search results | OBSERVE | benign | results | results: 1.00 |
| 12 | `OBS_BROWSE` | Browse page | OBSERVE | benign | browse | browse: 1.00 |
| 13 | `OBS_READ` | Interpret document | OBSERVE | decision | read_good | read_good: 0.80, misread: 0.20 |
| 14 | `OBS_MISREAD` | Document misread | OBSERVE | fault_entry | propagate | propagate: 1.00 |
| 15 | `OBS_EVIDENCE` | Evidence ready | OBSERVE | benign | extract | extract: 1.00 |
| 16 | `TOOL_SELECT` | Select tool | TOOL | decision | tool_valid | tool_valid: 0.90, tool_invalid: 0.10 |
| 17 | `TOOL_INVALID` | Invalid tool chosen | TOOL | fault_entry | propagate | propagate: 1.00 |
| 18 | `TOOL_ARGS` | Build arguments | TOOL | benign | args | args: 1.00 |
| 19 | `TOOL_CALL` | Call tool | TOOL | benign | call | call: 1.00 |
| 20 | `TOOL_OK` | Tool succeeded | TOOL | benign | ack | ack: 1.00 |
| 21 | `TOOL_ERROR` | Tool error | TOOL | benign | handle_error | handle_error: 1.00 |
| 22 | `TOOL_RETRY` | Retry tool | TOOL | recovery | retry | retry: 1.00 |
| 23 | `TOOL_PARSED` | Parse tool result | TOOL | benign | parse_result | parse_result: 1.00 |
| 24 | `MEM_READ` | Read memory | MEMORY | benign | recall | recall: 1.00 |
| 25 | `MEM_WRITE` | Write memory | MEMORY | decision | mem_write_ok | mem_write_ok: 0.85, mem_corrupt: 0.15 |
| 26 | `MEM_CORRUPT` | Memory corrupted | MEMORY | fault_entry | propagate | propagate: 1.00 |
| 27 | `REASON_STEP` | Reason over evidence | MEMORY | decision | reason_ok | reason_ok: 0.90, stop_early: 0.10 |
| 28 | `REASON_FLAWED` | Reasoning flawed | MEMORY | corridor | propagate | propagate: 1.00 |
| 29 | `DRAFT` | Draft answer | MEMORY | benign | draft | draft: 1.00 |
| 30 | `DRAFT_FLAWED` | Flawed draft | MEMORY | corridor | propagate | propagate: 1.00 |
| 31 | `EARLY_STOP` | Stopped early | MEMORY | fault_entry | propagate | propagate: 1.00 |
| 32 | `VAL_CHECK` | Validate answer | VALIDATE | benign | validate | validate: 1.00 |
| 33 | `VAL_FAIL` | Validation failed | VALIDATE | recovery | report_failure | report_failure: 1.00 |
| 34 | `VAL_FEEDBACK` | Collect feedback | VALIDATE | benign | collect | collect: 1.00 |
| 35 | `VAL_DIAGNOSE` | Diagnose and choose recovery | VALIDATE | decision | replan | replan: 0.44, retry_tool: 0.36, bad_recover: 0.20 |
| 36 | `VAL_REPLAN` | Replan | VALIDATE | recovery | restart_plan | restart_plan: 1.00 |
| 37 | `VAL_RETRY_TOOL` | Retry with tool | VALIDATE | recovery | restart_tool | restart_tool: 1.00 |
| 38 | `VAL_RECOVER_BAD` | Bad recovery | VALIDATE | fault_entry | flounder | flounder: 1.00 |
| 39 | `VAL_CHECK_FLAWED` | Validate flawed draft | VALIDATE | corridor | validate_flawed | validate_flawed: 1.00 |
| 40 | `DONE_SUCCESS` | Success (exact) | TERMINAL | terminal_success | — | — |
| 41 | `DONE_PARTIAL` | Success (partial) | TERMINAL | terminal_success | — | — |
| 42 | `FAIL_PLAN` | Failure: wrong plan | TERMINAL | terminal_failure | — | — |
| 43 | `FAIL_EVIDENCE` | Failure: bad evidence | TERMINAL | terminal_failure | — | — |
| 44 | `FAIL_TOOL` | Failure: tool misuse | TERMINAL | terminal_failure | — | — |
| 45 | `FAIL_MEMORY` | Failure: memory | TERMINAL | terminal_failure | — | — |
| 46 | `FAIL_EARLY_STOP` | Failure: premature stop | TERMINAL | terminal_failure | — | — |
| 47 | `FAIL_TIMEOUT` | Failure: timeout | TERMINAL | terminal_failure | — | — |

## Transitions (policy probability × kernel probability)

| source | action | target | category | fault | kernel P | policy P | product |
|---|---|---|---|---|---|---|---|
| `PLAN_START` | start | `PLAN_PARSE` | reasoning |  | 0.97 | 1.00 | 0.970 |
| `PLAN_START` | start | `PLAN_START` | reasoning |  | 0.03 | 1.00 | 0.030 |
| `PLAN_PARSE` | parse | `PLAN_DECOMP` | reasoning |  | 0.97 | 1.00 | 0.970 |
| `PLAN_PARSE` | parse | `PLAN_PARSE` | reasoning |  | 0.03 | 1.00 | 0.030 |
| `PLAN_DECOMP` | decompose | `PLAN_SUBGOAL` | reasoning |  | 0.97 | 1.00 | 0.970 |
| `PLAN_DECOMP` | decompose | `PLAN_DECOMP` | reasoning |  | 0.03 | 1.00 | 0.030 |
| `PLAN_SUBGOAL` | select_good | `PLAN_TOOLS` | reasoning |  | 1.00 | 0.75 | 0.750 |
| `PLAN_SUBGOAL` | select_wrong | `PLAN_SUBGOAL_WRONG` | reasoning | yes | 1.00 | 0.25 | 0.250 |
| `PLAN_SUBGOAL_WRONG` | propagate | `OBS_WRONG_RESOURCE` | state_update |  | 0.86 | 1.00 | 0.860 |
| `PLAN_SUBGOAL_WRONG` | propagate | `PLAN_TOOLS` | state_update |  | 0.08 | 1.00 | 0.080 |
| `PLAN_SUBGOAL_WRONG` | propagate | `FAIL_PLAN` | state_update |  | 0.06 | 1.00 | 0.060 |
| `PLAN_TOOLS` | plan_tools | `PLAN_COMMIT` | reasoning |  | 0.90 | 1.00 | 0.900 |
| `PLAN_TOOLS` | plan_tools | `PLAN_REVISE` | reasoning |  | 0.10 | 1.00 | 0.100 |
| `PLAN_REVISE` | revise | `PLAN_TOOLS` | reasoning |  | 0.97 | 1.00 | 0.970 |
| `PLAN_REVISE` | revise | `PLAN_REVISE` | reasoning |  | 0.03 | 1.00 | 0.030 |
| `PLAN_COMMIT` | commit | `OBS_QUERY` | reasoning |  | 0.97 | 1.00 | 0.970 |
| `PLAN_COMMIT` | commit | `PLAN_COMMIT` | reasoning |  | 0.03 | 1.00 | 0.030 |
| `OBS_QUERY` | query | `OBS_SEARCH` | observation |  | 0.97 | 1.00 | 0.970 |
| `OBS_QUERY` | query | `OBS_QUERY` | observation |  | 0.03 | 1.00 | 0.030 |
| `OBS_SEARCH` | search_good | `OBS_RESULTS` | observation |  | 1.00 | 0.85 | 0.850 |
| `OBS_SEARCH` | search_wrong | `OBS_WRONG_RESOURCE` | observation | yes | 1.00 | 0.15 | 0.150 |
| `OBS_WRONG_RESOURCE` | propagate | `OBS_MISREAD` | state_update |  | 0.86 | 1.00 | 0.860 |
| `OBS_WRONG_RESOURCE` | propagate | `OBS_SEARCH` | state_update |  | 0.08 | 1.00 | 0.080 |
| `OBS_WRONG_RESOURCE` | propagate | `FAIL_EVIDENCE` | state_update |  | 0.06 | 1.00 | 0.060 |
| `OBS_RESULTS` | results | `OBS_BROWSE` | observation |  | 0.88 | 1.00 | 0.880 |
| `OBS_RESULTS` | results | `OBS_SEARCH` | observation |  | 0.12 | 1.00 | 0.120 |
| `OBS_BROWSE` | browse | `OBS_READ` | observation |  | 0.97 | 1.00 | 0.970 |
| `OBS_BROWSE` | browse | `OBS_BROWSE` | observation |  | 0.03 | 1.00 | 0.030 |
| `OBS_READ` | read_good | `OBS_EVIDENCE` | observation |  | 1.00 | 0.80 | 0.800 |
| `OBS_READ` | misread | `OBS_MISREAD` | observation | yes | 1.00 | 0.20 | 0.200 |
| `OBS_MISREAD` | propagate | `TOOL_INVALID` | state_update |  | 0.86 | 1.00 | 0.860 |
| `OBS_MISREAD` | propagate | `OBS_READ` | state_update |  | 0.08 | 1.00 | 0.080 |
| `OBS_MISREAD` | propagate | `FAIL_EVIDENCE` | state_update |  | 0.06 | 1.00 | 0.060 |
| `OBS_EVIDENCE` | extract | `TOOL_SELECT` | observation |  | 0.97 | 1.00 | 0.970 |
| `OBS_EVIDENCE` | extract | `OBS_EVIDENCE` | observation |  | 0.03 | 1.00 | 0.030 |
| `TOOL_SELECT` | tool_valid | `TOOL_ARGS` | tool_use |  | 1.00 | 0.90 | 0.900 |
| `TOOL_SELECT` | tool_invalid | `TOOL_INVALID` | tool_use | yes | 1.00 | 0.10 | 0.100 |
| `TOOL_INVALID` | propagate | `MEM_CORRUPT` | state_update |  | 0.86 | 1.00 | 0.860 |
| `TOOL_INVALID` | propagate | `TOOL_SELECT` | state_update |  | 0.08 | 1.00 | 0.080 |
| `TOOL_INVALID` | propagate | `FAIL_TOOL` | state_update |  | 0.06 | 1.00 | 0.060 |
| `TOOL_ARGS` | args | `TOOL_CALL` | tool_use |  | 0.97 | 1.00 | 0.970 |
| `TOOL_ARGS` | args | `TOOL_ARGS` | tool_use |  | 0.03 | 1.00 | 0.030 |
| `TOOL_CALL` | call | `TOOL_OK` | tool_use |  | 0.88 | 1.00 | 0.880 |
| `TOOL_CALL` | call | `TOOL_ERROR` | tool_use |  | 0.12 | 1.00 | 0.120 |
| `TOOL_OK` | ack | `TOOL_PARSED` | tool_use |  | 0.97 | 1.00 | 0.970 |
| `TOOL_OK` | ack | `TOOL_OK` | tool_use |  | 0.03 | 1.00 | 0.030 |
| `TOOL_ERROR` | handle_error | `TOOL_RETRY` | tool_use |  | 1.00 | 1.00 | 1.000 |
| `TOOL_RETRY` | retry | `TOOL_CALL` | recovery |  | 0.70 | 1.00 | 0.700 |
| `TOOL_RETRY` | retry | `TOOL_SELECT` | recovery |  | 0.20 | 1.00 | 0.200 |
| `TOOL_RETRY` | retry | `FAIL_TIMEOUT` | recovery |  | 0.10 | 1.00 | 0.100 |
| `TOOL_PARSED` | parse_result | `MEM_READ` | state_update |  | 0.97 | 1.00 | 0.970 |
| `TOOL_PARSED` | parse_result | `TOOL_PARSED` | state_update |  | 0.03 | 1.00 | 0.030 |
| `MEM_READ` | recall | `MEM_WRITE` | state_update |  | 0.97 | 1.00 | 0.970 |
| `MEM_READ` | recall | `MEM_READ` | state_update |  | 0.03 | 1.00 | 0.030 |
| `MEM_WRITE` | mem_write_ok | `REASON_STEP` | state_update |  | 1.00 | 0.85 | 0.850 |
| `MEM_WRITE` | mem_corrupt | `MEM_CORRUPT` | state_update | yes | 1.00 | 0.15 | 0.150 |
| `MEM_CORRUPT` | propagate | `REASON_FLAWED` | state_update |  | 0.86 | 1.00 | 0.860 |
| `MEM_CORRUPT` | propagate | `MEM_WRITE` | state_update |  | 0.08 | 1.00 | 0.080 |
| `MEM_CORRUPT` | propagate | `FAIL_MEMORY` | state_update |  | 0.06 | 1.00 | 0.060 |
| `REASON_STEP` | reason_ok | `DRAFT` | reasoning |  | 1.00 | 0.90 | 0.900 |
| `REASON_STEP` | stop_early | `EARLY_STOP` | reasoning | yes | 1.00 | 0.10 | 0.100 |
| `REASON_FLAWED` | propagate | `DRAFT_FLAWED` | state_update |  | 0.86 | 1.00 | 0.860 |
| `REASON_FLAWED` | propagate | `REASON_STEP` | state_update |  | 0.08 | 1.00 | 0.080 |
| `REASON_FLAWED` | propagate | `FAIL_MEMORY` | state_update |  | 0.06 | 1.00 | 0.060 |
| `DRAFT` | draft | `VAL_CHECK` | reasoning |  | 0.97 | 1.00 | 0.970 |
| `DRAFT` | draft | `DRAFT` | reasoning |  | 0.03 | 1.00 | 0.030 |
| `DRAFT_FLAWED` | propagate | `VAL_CHECK_FLAWED` | state_update |  | 0.86 | 1.00 | 0.860 |
| `DRAFT_FLAWED` | propagate | `REASON_STEP` | state_update |  | 0.08 | 1.00 | 0.080 |
| `DRAFT_FLAWED` | propagate | `FAIL_EVIDENCE` | state_update |  | 0.06 | 1.00 | 0.060 |
| `EARLY_STOP` | propagate | `DRAFT_FLAWED` | state_update |  | 0.67 | 1.00 | 0.670 |
| `EARLY_STOP` | propagate | `REASON_STEP` | state_update |  | 0.08 | 1.00 | 0.080 |
| `EARLY_STOP` | propagate | `FAIL_EARLY_STOP` | state_update |  | 0.25 | 1.00 | 0.250 |
| `VAL_CHECK` | validate | `DONE_SUCCESS` | validation |  | 0.87 | 1.00 | 0.870 |
| `VAL_CHECK` | validate | `VAL_FAIL` | validation |  | 0.08 | 1.00 | 0.080 |
| `VAL_CHECK` | validate | `DONE_PARTIAL` | validation |  | 0.05 | 1.00 | 0.050 |
| `VAL_FAIL` | report_failure | `VAL_FEEDBACK` | validation |  | 1.00 | 1.00 | 1.000 |
| `VAL_FEEDBACK` | collect | `VAL_DIAGNOSE` | validation |  | 0.97 | 1.00 | 0.970 |
| `VAL_FEEDBACK` | collect | `VAL_FEEDBACK` | validation |  | 0.03 | 1.00 | 0.030 |
| `VAL_DIAGNOSE` | replan | `VAL_REPLAN` | recovery |  | 1.00 | 0.44 | 0.440 |
| `VAL_DIAGNOSE` | retry_tool | `VAL_RETRY_TOOL` | recovery |  | 1.00 | 0.36 | 0.360 |
| `VAL_DIAGNOSE` | bad_recover | `VAL_RECOVER_BAD` | recovery | yes | 1.00 | 0.20 | 0.200 |
| `VAL_REPLAN` | restart_plan | `PLAN_SUBGOAL` | recovery |  | 1.00 | 1.00 | 1.000 |
| `VAL_RETRY_TOOL` | restart_tool | `TOOL_SELECT` | recovery |  | 1.00 | 1.00 | 1.000 |
| `VAL_RECOVER_BAD` | flounder | `FAIL_TOOL` | recovery |  | 0.50 | 1.00 | 0.500 |
| `VAL_RECOVER_BAD` | flounder | `VAL_DIAGNOSE` | recovery |  | 0.35 | 1.00 | 0.350 |
| `VAL_RECOVER_BAD` | flounder | `FAIL_PLAN` | recovery |  | 0.15 | 1.00 | 0.150 |
| `VAL_CHECK_FLAWED` | validate_flawed | `FAIL_EVIDENCE` | validation |  | 0.60 | 1.00 | 0.600 |
| `VAL_CHECK_FLAWED` | validate_flawed | `VAL_DIAGNOSE` | validation |  | 0.30 | 1.00 | 0.300 |
| `VAL_CHECK_FLAWED` | validate_flawed | `DONE_PARTIAL` | validation |  | 0.10 | 1.00 | 0.100 |

Fault actions: `bad_recover`, `mem_corrupt`, `misread`, `search_wrong`, `select_wrong`, `stop_early`, `tool_invalid`.

Exact quantities (see the paper, Section 5): $V_t(q)=P(\text{success}\mid q,t)$ by backward induction; $\mu_t^{rep}=\sum_{q'}P(q'\mid q_{t-1},\rho(q_{t-1}))V_t(q')$; $\mu_t^{res}=V_{t-1}(q_{t-1})$.
