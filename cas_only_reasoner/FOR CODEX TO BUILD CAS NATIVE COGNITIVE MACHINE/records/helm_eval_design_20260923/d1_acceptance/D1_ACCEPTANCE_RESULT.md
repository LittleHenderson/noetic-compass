# D-1 acceptance of checker version 2: **ACCEPTED** (2026-09-23)

- **Who emitted the verdict.** `d1_acceptance_run.py` emitted `"acceptance": "ACCEPTED"` from the measured
  values. A1 to A6 are all true, and so is the extra check X.
- **Artifact.** `../hset1a_aws_job/results/D1_ACCEPTANCE_RESULT.json`, with the log in
  `../hset1a_aws_job/results/acceptance.log`.
- **Pass conditions.** They were fixed in `_handoffs/HELM_NEXT_PHASE_20260923/D1_CHECKER_V2_SPEC_AND_ACCEPTANCE.md`
  before the build, and extended by Codex's handoff and by Claude's pre-launch review.

## What was accepted

The versions are Codex commit `7f85af1eb9eb0ed991d5a8c82fa7ec4db43e539d`, with these LF sha256:

| File | LF sha256 |
|---|---|
| `checker_v2.py` | `d24d8276955bacbe626ebe6293efe7b64c2cf36544100b60175f6d0ab80e6258` |
| `answers_v2.py` | `b0bdabfcfac656e4071f192d9bda8ff7dec8b88baf077f29131d8f94497d1bb5` |
| `slots_v2.py` | `7b9c2c3a0aca938acf0979aa7d74f1fea422726333926f079a5f8e06f5e7d2fb` |

| Profile | Schema | Digest |
|---|---|---|
| Checker profile | `cas.typed-teaching-semantic-profile/0.2` | `b0e565314a91083f8c5559ce1be16fd667e82a52d7dd224de88440bdb0709075` |
| Slot profile | `cas.typed-teaching-slot-profile/0.2` | `3f384e6053036c5eecd0464d32101fe773edf64ecb9e0481af92e80494aeb453` |

**The run.**
- **Machine.** AWS `c7i.2xlarge` `i-0681fa3905a7bb0eb`, Intel Xeon Platinum 8488C, 8 vCPU, Python 3.14.7.
- **Bundle.** Built from git objects: the original tree at `20208c92`, the v2 tree at `7f85af1e`, and Claude's
  scripts at `6dcf035c`.

## Measured values, per test

- **A1 (frozen files untouched): PASS.**
  - The five frozen files' LF sha256 equal the anchors computed from the original commit's blobs.
  - The frozen checker profile equals the historical anchor `2c95354e...0bd8a81` and the original tree's.
  - The slot profile equals the original tree's.
  - Every imported module came from the v2 tree.
- **A2 (nothing changes at 4 nodes or fewer): PASS.** It took 703.7 s.
  - Accepted-answer sets are identical on all 564 registry records.
  - Witnesses differ on 0 records, and coverage on 0.
  - Slot plans are byte-identical on all 564.
  - v2's `correct` equals the frozen checker's on all 6,768 saved predictions: Helm 1.0 and Helm 2.0, 3 seeds each,
    2 phases each.
  - The 12 prediction files equal their launch anchors, and also Codex's `INPUT_MANIFEST.json`, 12 of 12.
- **A3 (correct at 5 and 6 nodes, against Claude's independent two-method oracle): PASS.** It took 16.9 s, with
  0 mismatches.
  - It covered all 105 degree-colliding 5-node classes, in 38 groups: 210 analogy questions and 442
    correspondence questions. Same-shape same-domain worlds were excluded every time, and NO_MATCH was right every
    time.
  - It added 233 random 6-node correspondence questions against same-degree decoys.
  - **The answer cap.** Exactly 64 analogy answers were accepted. Correspondence sets of 24, 24, 48 and 36 mappings
    were equal to the oracle. Two 120-mapping shapes were refused with `TYPED_CHECKER_TARGET_SET_BOUND`, never
    truncated.
  - **The node bound.** Every 7-node case was refused with `TYPED_CHECKER_ISOMORPHISM_BOUND`: the focus, a
    same-domain bank world, a cross-domain bank world, and correspondence.
  - **The new slot path.** 5-node correspondence offered all 121 candidates, and 6-node offered all 721. Every
    accepted answer was among them. The frozen compiler refused these packets (`TYPED_PERMUTATION_BOUND`).
- **A4 (separate identity): PASS.**
  - The checker and slot profiles have their own schemas and digests.
  - `MAX_ISOMORPHISM_NODES` is 6 and `MAX_ADMISSIBLE_ANSWERS` is 64.
  - The rule strings named in spec S3 equal the frozen profile's.
  - No v2 name contains "frozen".
  - `TARGET_SCHEMA`, `CHECK_SCHEMA` and `DECISION_SCHEMA` are shared with the frozen versions. The spec allows this;
    a v2 target is told apart by the profile digest it carries.
- **A5 (bank rules): PASS.**
  - A bank holding one 5-node world: the frozen checker refuses it (`TYPED_CHECKER_ISOMORPHISM_BOUND`), and v2's
    answer equals the oracle.
  - 65 bank worlds: v2 refuses with `TYPED_SOURCE_PUBLIC_BANK_REFS`.
  - 64 bank worlds plus a separate focus: accepted.
  - The frozen 64-world training bank with a 5-node focus: the frozen checker refuses it, and v2's answer is
    NO_MATCH, which equals the oracle.
- **A6 (performance): PASS.**
  - 1,000 five-node analogy questions, each on a **64-world bank**, took **92.21 s** in one process, against a
    600 s budget (Codex `WORK_PLAN.md`).
  - At most 3,240 permutations per question, and 1,187,640 in total.
  - 1,000 of 1,000 answers equal the oracle.
  - For comparison, 100 six-node questions took 10.534 s, with at most 17,280 permutations per question.
  - Codex's own figure was 23.554114344 s with 3-world banks.
- **X (extra): PASS.** v2 gives the frozen gold on all 3,370 HSET-1A Stage 1 packets. That includes all 1,526
  sealed ones, which are reported as counts only.

## What ACCEPTED licenses, and what it does not

- **Licensed.**
  - Checker v2, at the file hashes above, may score Stage 2 cells (analogy and correspondence at 5 or 6 nodes).
  - The frozen checker stays the scorer of record for every historical result.
- **Not licensed.**
  - Any statement about Helm. No model was run.
  - Correctness beyond the tested scope: generated banks of 5 to 6 nodes, plus all historical records.
- **Custody.** Custody is not independent: Claude wrote both the oracle and the tests. An outside custodian has not
  repeated them.

The earlier, partial run (attempt 1, where A2 hit Claude's pool bug) is recorded in
`../hset1a_aws_job/RUN_LOG.md`. The verdict above comes only from attempt 2's complete run.
