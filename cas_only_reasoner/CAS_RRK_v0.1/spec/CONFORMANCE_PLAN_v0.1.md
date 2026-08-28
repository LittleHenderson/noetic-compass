# Conformance Plan v0.1

## The tests that must exist before the build counts

**Status:** FROZEN. Implemented in tests/test_conformance.py.

| # | Test | Required result |
| --- | --- | --- |
| 1 | Scheduler emits DecisionCommitIntent | Reject as unauthorized |
| 2 | Branch attempts durable memory write | Reject |
| 3 | Branch attempts external action | Reject |
| 4 | RPM child returns without parent frame | Typed stack fault |
| 5 | Two intents mutate the same field | Deterministic resolution or typed conflict |
| 6 | Commitment with unresolved contradiction | Reject |
| 7 | Learning references discarded branch | Reject |
| 8 | Halt occurs before trace seal | Reject |
| 9 | Trace system requests mutation | Reject |
| 10 | Same input, state, seed, version run twice | Identical trace and final hash |
| 11 | Branch fails before commit | All branch-local changes rolled back |
| 12 | Missing premise | NEEDS_INFORMATION, not fabricated conclusion |
| 13 | RPM subgoal succeeds | Parent resumes at saved stage |
| 14 | RPM subgoal fails | Typed failure propagated to parent |
| 15 | Search exceeds branch budget | BUDGET_EXHAUSTED |
| 16 | Repeated state without progress | LOOP_LIMIT_REACHED |

## Native reasoning fixtures (CAS-Sem JSON, not English)

    1. modus_ponens        P, P -> Q, query Q
    2. transitive          precedes(A,B), precedes(B,C), query precedes(A,C)
    3. contradiction       P and not-P
    4. missing_information P -> Q, query Q, P absent
    5. candidate_planning  three plans, incompatible constraints
    6. rpm_recursion       goal requires missing knowledge; child resolves;
                           parent resumes

Each fixture has a golden expected result (golden/expected/) and, where
relevant, a golden expected failure (golden/expected_failures/). A
fixture pass requires: exact terminal status, exact committed
conclusion when applicable, and the sealed trace digest recorded in the
golden file when the fixture is declared trace-frozen.

## Ablation and replay (gates 7-8)

- Ablation: removing a fact or rule from a fixture must change the
  result in the documented direction (e.g., missing_information's
  absent premise removed -> SUPPORTED).
- Replay: tests/test_replay.py re-executes every fixture's sealed trace
  and requires identical per-tick state hashes and terminal status.
