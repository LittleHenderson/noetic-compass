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

## Update 2026-09-23: `d1_acceptance_run.py` (runner v0.2) and a pre-launch review

`d1_acceptance_run.py` runs tests A1 to A6 end to end. An independent reviewer read version 0.1 before any run and
found 5 major and 10 minor defects, with no blocker. Three majors were tests that could pass even if v2 were wrong.
Version 0.2 fixes them:

- **The 65-bank-world refusal.** It is now asked of v2 itself, with the exact reason
  `TYPED_SOURCE_PUBLIC_BANK_REFS`.
- **The node bound, pinned from above.** A 7-node world in scope must be refused with
  `TYPED_CHECKER_ISOMORPHISM_BOUND`, whether it is the focus, a same-domain bank world or a cross-domain one.
- **The answer cap, pinned at exactly 64.** An analogy question with exactly 64 cross-domain isomorphs must be
  accepted, and a 120-map correspondence must be refused.
- **The new slot-compiler path** is now tested on 5- and 6-node correspondence packets.
- **Every test is wrapped,** and the result file is rewritten after each test.
- **A1 fails closed** without the original tree's profiles, and it checks that every imported module comes from
  the v2 tree.
- **v2's output** is captured and discarded while it runs on sealed packets.

`a2_compare_harness.py` is superseded by `d1_acceptance_run.py` test A2. It is kept unchanged as the reviewed
version.
