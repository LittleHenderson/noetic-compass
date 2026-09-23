# D-1: checker version 2. Build specification (for Codex) and acceptance tests (Claude)

- **Approved** by the owner on 2026-09-23 (`OWNER_DECISION_D1_20260923.md`).
- **Builder:** Codex. **Independent checker:** Claude. **Status:** `SPECIFIED_NOT_BUILT`.

## 1. Why it is needed (from facts on disk)

The frozen checker cannot score analogy or correspondence above 4 nodes:

| Location | Limit |
|---|---|
| `checker.py:20` `MAX_ISOMORPHISM_NODES = 4` | the isomorphism check |
| `checker.py:92-93` | refuses a bank if ANY world has more than 4 nodes, so one 5-node world breaks every analogy question on that bank |
| `answers.py:22` `MAX_PERMUTATION_NODES = 4` | correspondence candidates |
| `slots.py:47` `correspondence_max_nodes: 4` | correspondence slots (the profile) |

`source.py:20` already allows worlds of up to 10 nodes (`MAX_NODES = 10`) and banks of 64 worlds (65 with the
focus).

At 3-4 nodes, the sorted (in-degree, out-degree) multiset almost fully decides isomorphism: 1 collision among
28 shapes. So analogy and correspondence there cannot show structure reading (review S1/F2). At 5 nodes, 105 of
267 shape classes share a degree multiset with a non-isomorphic class. That gives real decoys.

## 2. What to build

- **S1. A new version, not an edit.** The files `checker.py`, `answers.py`, `slots.py`, `source.py` and
  `pointer_inputs.py` stay byte-identical, and the frozen `checker_profile()` digest is unchanged. The new
  version lives in new modules, or behind an explicit version argument whose default is the frozen behaviour.
  - Its profile has its own schema string, for example `cas.typed-teaching-semantic-profile/0.2`, and its own
    digest.
  - Its name never contains "frozen".
- **S2. Raised bound.** Proposed: `MAX_ISOMORPHISM_NODES = 6` and `MAX_PERMUTATION_NODES = 6`. That is 6! = 720
  permutations per pair, or at most 46,080 per analogy question on a 64-world bank.
  - The design uses 5-node worlds. 6 leaves headroom.
  - If Codex needs a different bound, state it and why.
- **S3. The same rules.** These stay exactly as the frozen profile declares them:
  - `UNROOTED_EXACT_DIRECTED_GRAPH_BIJECTION`;
  - `DISTINCT_DECLARED_DOMAIN_STRINGS`;
  - `ALL_VALID_ANSWERS_RETAINED_CANONICAL_BYTE_ORDER`;
  - `MAX_ADMISSIBLE_ANSWERS = 64`.

  Only the node bound moves. If a correspondence item would have more than 64 valid mappings, it is refused by
  the checker and excluded by the generator. It is never truncated silently.
- **S4. Slot compiler.** A matching slot-compiler version accepts correspondence up to the new bound. Its output
  on every existing record must be byte-identical to the frozen `compile_slots`.
- **S5. Helm's reader is NOT changed.** `pointer_inputs` groups each node's degrees into buckets 0-4, where 4
  means "4 or more". So HSET worlds are generated with **every node's in-degree and out-degree at most 4**,
  which is automatic at 5 nodes. That keeps what Helm sees exact. No change to Helm's input path is needed or
  allowed under D-1.
- **S6. Performance.** Record the maximum permutations checked per question, and the wall time to score 1,000
  generated 5-node analogy questions on the local CPU. Checking is non-neural, so the CPU is allowed.

## 3. Acceptance tests (run by Claude; a failure blocks use)

| Id | Test | Pass condition |
|---|---|---|
| A1 | Frozen files untouched | the LF sha256 of `checker.py`, `answers.py`, `slots.py`, `source.py` and `pointer_inputs.py` are unchanged; the frozen `checker_profile()` digest is unchanged |
| A2 | Nothing changes at 4 nodes or fewer | For all 564 registry records: v2's accepted-answer sets equal the frozen checker's. For every saved prediction of both historical studies (3,384 per study): v2's `correct` flag equals the frozen checker's (0 disagreements). For every existing record: v2's slot plans are byte-identical |
| A3 | Correct at 5-6 nodes | An **independent** oracle written by Claude, not derived from Codex's code: brute-force canonical form plus a second method, degree-refined backtracking. On generated banks it must give the same accepted-answer sets and correspondence mapping sets as v2. The banks include (a) every one of the 105 degree-colliding 5-node classes against its non-isomorphic partner, (b) the same shape in the same domain (must be excluded), (c) NO_MATCH cases, (d) an automorphism-rich shape at or below the 64-answer cap, and (e) a case above the cap (must refuse, never truncate) |
| A4 | Separate identity | v2's profile schema and digest differ from the frozen ones; the name does not contain "frozen" |
| A5 | Bank rules | one 5-node world in a bank no longer breaks analogy; a bank of more than 64 worlds (65 with the focus) is still refused |
| A6 | Performance | S6 is recorded; 1,000 5-node analogy questions score within the stated budget |

**What Claude prepares now,** independent of Codex's code: the A3 oracle and generator, and the A2 comparison
harness. They live under `records/helm_eval_design_20260923/d1_acceptance/`.

## 4. After acceptance

- **Who builds the test set.** The HSET-1 Stage 2 packet builder and the sealed test are **Claude's**, as
  custodian. A builder does not generate its own test. The builder uses checker v2 for answers, and Codex
  reviews the packet builder for buildability.
- **What still comes first.** Before any Stage 2 cell is read, section 1.3 of the design (the cluster sign test
  against the measured bar, and at least 10 clusters) must be signed.
