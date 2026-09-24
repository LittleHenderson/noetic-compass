# Claude state for Codex (2026-09-24): what is running, who owns what, where the six review items touch

Written by the Claude coordinator after the owner's heads-up (`OWNER_HEADSUP_PLAN_REVIEW_20260924.md`): Codex works
the six amendments to HELM-REPAIR-CONTROLLED-1. **The main comparison is HELD. Nothing in it launches until one
complete amended launch request is approved.** Claude will not duplicate the six items.

## Running right now

| What | Where | Note |
|---|---|---|
| Switch-ON smoke **attempt 2** (enabled-path check, reduced schedule, ablations on) | AWS `i-039b7ae505c4c6245`, g7.2xlarge, us-west-2a; launched from `C:/.../CNCM/_worktrees/helm-on-launch-20260924` (branch `claude/helm-on-launch-20260924`, admission `1fcc15e5`) | Launched under the owner's earlier yes, before the hold. Attempt 1 was refused by AWS capacity before launch: $0 compute, $15 ledger booking |
| Workflow: Q4 A-versus-B job build and review, plus the larger-question path review and the rescorer 0.4 review, fix and verify | Q4: `D:/tksCAS-worktrees/q4-sdg`; larger-question review: `D:/tksCAS-worktrees/helm-builder`; rescorer: `D:/tksCAS-worktrees/helm-rescorer` | Q4 is separate. It launches nothing |
| Workflow: HSET-2 build code (public stage 0, sealed-stage builder, AWS job files), two-lens review, fix, verify | `D:/tksCAS-worktrees/hset2-build`, branch `claude/hset2-build-20260924` | Built against design v0.4 + Amendment A1. Review item 4 may require changes after it lands |
| Workflow: unchanged-arm reproduction admission (seed 20260917 of `20208c92`) and its verdict reader | `C:/.../CNCM/_worktrees/helm-unchanged-repro-20260924`, branch `claude/helm-unchanged-repro-20260924`, at `20208c92` | Its `read_reproduction.py` is being written for **checkpoint-file identity only**. Under review item 2 it must follow the policy Codex fixes, and it is not used before then |

## Where each review item touches existing files

| Item | Files | Owner so far |
|---|---|---|
| 1. Option C rationale; B versus C | `PLAN_HELM_REPAIR_CONTROLLED_1_DRAFT.md` section 4a. Claude added a marked CORRECTION only (`7b6e25f8`) | plan: Claude; amendment: Codex |
| 2. File identity versus learned-state identity versus output reproduction | the plan, section 4a; `read_reproduction.py` in the unchanged-repro checkout | Codex fixes the policy; Claude or a builder then conforms the reader |
| 3. "No regression" wording | `EVALUATION_DESIGN_v0_4.md` section 7.2 (the paired regression test; H1/H2/V gate set; gate pin `d3e0ea97`) and the plan, section 7 | design: Claude (evaluation custodian); amendment: Codex |
| 4. HSET-2 threshold selection, grouping, multiple claims | `EVALUATION_DESIGN_v0_4.md`, sections 5-7 and Amendment A1; the HSET-2 build code on `claude/hset2-build-20260924` | design: Claude. The build prints the real informative-case counts (binding W per comparator) before any training |
| 5. Larger-question route for both arms; bound versions; update allowance; 18 checkpoint checks | the larger-question path `785c9bd1` (`eval_paths/`, forward-only T4 checks not yet run); `MIGRATION_ON_SHAPES.json`; prereg A5 (`d7023288`); the launcher's `optimizer_updates_max` 1,488 against 1,470 main updates | built by a Claude builder; its review is in the running workflow |
| 6. The complete launch request | the plan | Codex drafts; Claude runs approved jobs |

## Custody and money (unchanged rules)

- **Sealed material stays with the Claude custodian.** That is the HSET-1A TEST, the HSET-1A and HSET-1B salts, and
  the future HSET-2 salt. Builders and Codex receive public material only.
- **The Q3 protected examination is committed in git.** See `PROTECTED_COPY_INVENTORY_20260924.md`.
- **The shared budget ledger is `_worktrees/meta1/...`** (Codex's working copy). The launcher wrote the two smoke
  bookings into it, $15 each; they are uncommitted there.
- **Spend so far on this line** (measured upper bounds):
  - T4 item 1: $0.5596 + $0.67;
  - Q4 diagnostic: $0.0673;
  - smoke attempt 1: $0 compute;
  - smoke attempt 2: running.

## What Claude will do meanwhile

- Keep the running preparation work going.
- File the smoke result.
- Keep custody.
- Fold Codex's amendments into the design and the job records, as each owner's file allows.
- Tell the owner only when the complete launch request is ready.

**Please record finished items in a file here**, for example `CODEX_AMENDMENTS_20260924.md`, so the two lines do
not collide.

## Update: prerequisite results since this note was written

- **Switch-ON smoke attempt 2: PASSED.**
  - Launch branch `claude/helm-on-launch-20260924` at `1ddf6a1e`, `SMOKE_RUN_LOG.md`.
  - All four frozen pass conditions hold. Ablations cover 53 of 53 keys, including `analogy_head`. Launcher exit 0.
    Cleanup complete.
  - Instance about 34.6 min; at most $3.18 (compute about $1.45).
  - Archive: `D:/tksCAS-archive/helm_on_smoke_attempt2_20260924/` (338 files, 3 sha256 confirms).
- **Rescorer 0.4 (historical-compatibility mode): APPROVE** after a fix round.
  - Fix `8e260c71`, verification `0d6bc2fd`, branch `claude/helm-rescorer-compat-20260924`.
  - The fix covered 1 blocker (the trusted check never validated recorded counts) and 2 majors (absent weights
    passed; `--out` could overwrite originals).
  - Its full 564-record reading and slow tests still need an AWS CPU run.
- **Larger-question path: CHANGES_REQUIRED** (review `cc68d8b3`). Its T4 check likely overran 3,600 s, with check d
  last. A fix workflow is running under coordinator decisions:
  - order d, c, b, a;
  - check a against the T4 item-1 digests;
  - a timing preflight;
  - `REQUIRED_INPUTS`;
  - 6-node reach claim-bearing (HSET-2 cross-checks reach gold); 6-node parts and edge_account diagnostic.
- **Q4** (separate line): the A-versus-B rules are being revised. "Architecture change justified" now needs total
  collapse.
