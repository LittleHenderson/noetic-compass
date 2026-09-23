# Helm next phase: coordination record, Claude side (2026-09-23)

The owner's recommendation of 2026-09-23 assigns the roles:

- **Codex** is the implementation lead.
- **Claude** is the independent-verification and evaluation-design lead.

**Claude's acceptance.** Claude accepts this division. This file is Claude's record.

**What Codex should do.** Codex should write its own record, `COORDINATION_CODEX.md`, in its own branch and
working folder. It should not edit this file. Nothing here counts as agreed until both records exist and the
owner confirms.

## 1. Claude's working folder and starting point

| Item | Value |
|---|---|
| Working folder | `D:/tksCAS-worktrees/helm-integration` (Claude only) |
| Branch | `research/helm-integration-20260923` |
| Started from | `4eb98682b983f9ceb22c9e0b5fa127e9d21cda0d` (the first authorized Q4 run) |
| Merged in | `research/helm-why-review-20260922` @ `26f1b465`, commit `f1156d03` |
| Merged in | `codex/helm-failure-research-20260922` @ `a6e6f95b`, commit `604c1f08` |

Neither merge changed any code. Both only add records.

## 2. Work already under way that conflicts with the division

The division arrived mid-turn. Per the owner, nothing was discarded and no active job was interrupted.

1. **Rescorer repair. It belongs to Codex now.**
   - **What Claude changed.** Before the division arrived, Claude changed
     `records/typed_pointer_001/trusted_rescore.py` on this branch. The change makes the tool version 0.3:
     - it applies the frozen grader's rule;
     - it binds that rule into a 0.3 anchor, checked as `PASS_RULE_IDENTITY`;
     - it compares each seed's pass result and exact p with the frozen reading;
     - it keeps `FUTURE_RELEASE_CRITERIA` separately named.
   - **The job in flight.** A non-neural CPU job was already running. It writes two 0.3 anchors and rescores
     both Helm studies. It was left to finish.
   - **Status: `CLAUDE_REFERENCE_IMPLEMENTATION`, not the active tool.** After the job finished, the changed
     file was renamed, byte for byte, to `records/typed_pointer_001/trusted_rescore_reference_claude_v0_3.py`.
     `trusted_rescore.py` was restored to its original 0.2 bytes, so the active tool is untouched for Codex
     and its existing tests still pass. The v0.3 anchors and readings name the old path in their `tool` field,
     but their `tool.pin.sha256_lf` equals the renamed file's hash.
   - Codex should build its own repair of the active tool in its own folder. Claude will then check Codex's
     result against two things:
     - the frozen grader's readings, seed by seed;
     - this reference implementation's readings.
   - **If Codex adopts this code instead,** Codex becomes its owner and must review it itself. Claude, as its
     author, would then not count as an independent checker of that code.
2. **Test-file edits were reverted.** Claude had started editing `test_trusted_rescore.py`. Only a docstring
   and two import lines had changed. That change is reverted. Section 5 lists the tests Claude intended, as
   input for Codex.
3. **Analogy repair: not started by Claude.** Claude only read `pointer_learner.py`. The missing path is in
   `GraphForward._world_scores`, lines `1484-1516` at `4eb98682`:
   - each candidate is scored on `[query-key . candidate, query-value . candidate, is_focus, is_target, 0, 0,
     candidate declaration]`;
   - an analogy query names no node, so the query vector is the same for every analogy question;
   - the focus world therefore enters only as the `is_focus` flag.
4. **Historical-account corrections.**
   - Claude's review branch already added a flag-only section at the top of `BRAIN_LINEAGE.md`. It is merged
     here.
   - In this phase, Claude will not edit `BRAIN_LINEAGE.md` or `AUDIT_PACK.md` again. Proposal: Codex is the
     single writer of those two files. Claude writes the correction evidence in its own new files, which Codex
     can cite.

## 3. Proposed ownership: one owner per file and per experiment

| Work item | Builder / runner | Independent checker | Where |
|---|---|---|---|
| Active rescorer repair (`trusted_rescore.py`, its tests, new anchors, new readings) | Codex | Claude | Codex branch |
| Analogy focus-to-candidate repair (`pointer_learner.py`, behind a switch; declared shapes and weight migration) | Codex | Claude | Codex branch |
| Prospective evaluation design: Helm structure-transfer set and Q4 three-readout split | Claude (design, and custody of the sealed answers) | Codex (buildability review) | `records/helm_eval_design_20260923/` on this branch |
| Analogy wiring check ("changing what Helm compares changes the relevant scores") | Claude (probe; forward-only on the local GPU) | none | this branch |
| Late reach-loss experiment (Helm 2.0 seed 20260919 from pass 1, rate 0.003 vs 0.0003) | Codex (sole runner) | Claude | separate experiment id |
| Q4 expression-reading experiment (three readouts) | Codex (sole runner) | Claude (split design and check) | separate experiment id; never mixed with Helm 2.0 |
| `BRAIN_LINEAGE.md`, `AUDIT_PACK.md` | Codex (single writer this phase) | Claude | Codex branch |
| Integration and correction records | Claude | Codex | `records/helm_integration_20260923/` on this branch |

**Things to agree before any comparison is read:**
- the exact starting source (proposed: Helm 2.0-experimental `20208c923d41c24614504d4ecc2b289ecb66eda8`);
- matched starts;
- the evaluation-design digest;
- the pass and stop rules;
- the per-job limits under `docs/OWNER_RUN_AUTHORIZATION_20260922.md`.

## 4. Acceptance for the rescorer repair: what "reproduces the original rule" means

A repaired active tool must print every value below. Matching the label alone is not enough.

| Study | Seed | Gained / lost | Exact p | Kinds and worlds requirement | Seed result |
|---|---|---|---|---|---|
| Helm 1.0 | 20260917 | 10 / 0 | 1/1024 | applied | pass |
| Helm 1.0 | 20260918 | 12 / 0 | 1/4096 | applied | pass |
| Helm 1.0 | 20260919 | 11 / 0 | 1/2048 | applied | pass |
| Helm 2.0-exp | 20260917 | 11 / 1 | 13/4096 | applied | **pass** |
| Helm 2.0-exp | 20260918 | 12 / 0 | 1/4096 | applied | pass |
| Helm 2.0-exp | 20260919 | 7 / 1 | 9/256 | applied | **fail** |

The labels must be `LEARNS_NEW_WORLDS` for Helm 1.0 and `NO_TRANSFER_TO_NEW_WORLDS` for Helm 2.0-exp.

These must stay unchanged:
- the frozen grader `evaluate_gates.py` (LF sha256 `d3e0ea97...`);
- both `gate_reading.json` files;
- every receipt;
- the 0.2 anchors and readings.

## 5. Tests Claude intended for the rescorer (input for Codex; not written by Claude)

- The per-seed rule equals the grader's source text. Read `ALPHA`, `MIN_IMPROVED_KINDS` and
  `MIN_IMPROVED_WORLDS` out of `evaluate_gates.py` with `ast`. Do not import it.
- Check every (b, c) cell with b + c <= 18 against an independent exact binomial. Include these cells:
  - (11,1) passes; (7,1) fails;
  - (10,1) passes; (9,1) fails;
  - (7,0) passes; (6,0) fails.
- Breadth: gains in one kind only fail. Gains in one world only fail.
- A frozen reading whose counts agree but whose pass result differs must FAIL agreement. A reading that has
  no pass result must also fail.
- An anchor that still carries the 0.2 zero-loss rule is refused before any checker import.
- The 0.2 anchors and readings are pinned as preserved history. This includes the 0.2 Helm 2.0 reading's
  wrong `20260917 passed: false`, which is kept, not repaired in place.

## 6. What Claude will deliver next, in its role

1. **The prospective evaluation design**, digest-frozen, marked `PROPOSED_FOR_AGREEMENT`. It covers:
   - Helm structure transfer: familiar vs genuinely new shapes, isomorphism-checked;
   - the Q4 three-readout split.
2. **The analogy wiring probe**, with its "before" reading on unchanged Helm 2.0. It should show no
   dependency. The same probe then checks Codex's repair.
3. **An independent check** of Codex's rescorer repair against section 4.
