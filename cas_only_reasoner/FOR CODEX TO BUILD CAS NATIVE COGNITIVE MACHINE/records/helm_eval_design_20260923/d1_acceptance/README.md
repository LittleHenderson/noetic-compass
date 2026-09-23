# D-1 acceptance tools (Claude, independent checker)

These are the tests for checker version 2. They are written **before** Codex builds it, and none of them derives
from Codex's code. Specification: `_handoffs/HELM_NEXT_PHASE_20260923/D1_CHECKER_V2_SPEC_AND_ACCEPTANCE.md`.

| File | Test | What it does |
|---|---|---|
| `oracle_isomorphism.py` | A3, with its own self-test | An independent isomorphism oracle using two methods that must agree: M1 (brute-force canonical form) and M2 (degree-refined backtracking, which enumerates every isomorphism). It also enumerates every weakly connected DAG class at 3-5 nodes, and finds the degree-multiset collisions: the hard decoys. `--selftest --frozen-crosscheck` checks the oracle against the FROZEN checker's own `_isomorphisms` on all 4,096 ordered pairs of the 64 bank worlds, where the frozen checker is trusted |
| `a2_compare_harness.py` | A2 and A4 | v2 against the frozen checker on all 564 registry records (accepted-answer sets) and on all 6,768 saved predictions of both studies (`correct` flags). It records both profile digests and the frozen files' hashes |

**Status.** Both are written. The oracle self-test runs after the current GPU queue, so the probe runs keep the
CPU to themselves. The A2 harness runs once Codex delivers v2.

**Pass conditions:** section 3 of the specification. A failure blocks the use of v2.
