# Coordination amendment: temporary Claude takeover of the Helm builder role (2026-09-23)

This file is additive. Every earlier ownership record stays as written, as history: `COORDINATION_CODEX.md`,
`CODEX_*.md`, and Claude's `COORDINATION_CLAUDE.md` on `research/helm-integration-20260923`. Changes made after
this date on this branch are Claude's, not Codex's.

## Authority

The owner, in chat on 2026-09-23 (quoted exactly):

> "Codex is unavailable until the usage reset shown as September 28, 11:23 AM. I need you to continue the project
> temporarily."
>
> "Keep this conversation as coordinator and evaluation custodian. Where supported, use a separate Claude coding
> session for implementation and a fresh checking session for review. Give the builder public contracts and
> development examples, not hidden test answers or answer-exposed conversation history. Disclose any limitation in
> that separation."
>
> "Follow my current AWS preference and the actual standing authorization, job limits and cleanup requirements. Do
> not default to laptop computation or treat this staffing change as expanded spending permission."

**The owner's handoff document.** It is `CLAUDE_HELM_TEMPORARY_TAKEOVER_20260923.md` in this folder, a byte copy
of the file the owner attached, sha256 `f1390c0b79ad7d18fef3b58268703d1e9cf2d8b858ab88c5df15da0244babc34`. By its
own words it records no approval, spending or acceptance change. The owner's chat message above is what assigns
the work.

## Temporary roles, until Codex returns (usage reset shown as September 28, 11:23 AM)

| Role | Who | Where |
|---|---|---|
| Coordinator and evaluation custodian | The existing Claude session (the one that designed HSET, built the sealed test and ran the D-1 acceptance) | `research/helm-integration-20260923` in `D:/tksCAS-worktrees/helm-integration` |
| Temporary builder | A separate Claude sub-agent (Claude Code `Agent`, general-purpose). It does not inherit the coordinator's conversation | `claude/helm-builder-continuation-20260923` in `D:/tksCAS-worktrees/helm-builder`, parent `96644503` (Codex's newest source; no source change after `7f85af1e`) |
| Fresh reviewer | Another separate Claude sub-agent, started after the builder finishes, with no builder or coordinator history | read-only review of the builder's commits |
| Returning reviewer | Codex, on return | reviews the bounded change set listed in `CLAUDE_CONTINUATION_LOG.md`. It should not repeat completed work, and it should not merge automatically |

## Limits of the separation, disclosed

- **All three roles are Claude**, the same provider and model family. More Claude agents are not outside custody
  and not a different-provider audit. The D-1 report's limitation stands: Claude wrote both the oracle and the
  tests.
- **Sub-agents do not inherit the coordinator's conversation.** They start from their own brief and the
  repository's `CLAUDE.md` and `AGENTS.md` files.
- **Separation is by instruction, not by permission.** The builder and the reviewer run on the same laptop with
  the same file access and the same AWS account. So technically they **could** read
  `D:/tksCAS-archive/hset1a_sealed_20260923/` (the sealed TEST and its salt) and the S3 objects under
  `helm-integration/hset1a-build-*`. They are instructed not to. Their briefs contain no sealed material. Their
  reports must state every file outside their working copy that they opened.
- **The coordinator's own exposure.** It has seen the sealed build's totals (cell sizes, bars, W) and knows where
  the salt is. It has never displayed a TEST world, record id or answer, and it does not give any to the builder.
- **The builder's working copy.** It is a sparse checkout holding only `research/`, `tests/`, `_handoffs/`,
  `AGENTS.md`, `pyproject.toml` and `records/helm_peer_handoff_20260923/`. It contains no HSET files and no sealed
  material.

## Preservation rules for everyone

- Keep every Codex branch, working folder, checkpoint and receipt.
  - No reset, clean, delete or force-push.
  - Never commit on a Codex branch.
  - Two Codex working folders (`_worktrees/helm-failure-a3` and `_worktrees/helm-failure-a5`) have untracked
    `tmp/` folders. They are left untouched.
- Do not rebuild the analogy repair (`60e382b0`) or the accepted checker v2 (`7f85af1e`).
- Keep Q4 reconstruction and the late reach-error experiment separate. Neither is started by this takeover.
- One runner per job. No automatic duplicate jobs. AWS only, within the existing limits.

## State recovered at takeover (2026-09-23, before any edit)

- **Branches.** GitHub and local heads agree. Codex's newest is `codex/helm-stage2-checker-20260923` at `96644503`.
  - It contains `60e382b0` (analogy repair), `75013c13` (evidence integration), `d206b42a` and `7f85af1e`
    (checker v2).
- **Live AWS inventory**, checked read-only in 4 US regions:
  - no Helm instance, volume or SageMaker job;
  - one unrelated stopped `g6e.xlarge` (`i-0c3028734c8885542`, "cas-bridge-control-20260822", launched
    2026-08-24), with a 300 GB volume. It is not touched.
- **Checker v2 is ACCEPTED** at `7f85af1eb9eb0ed991d5a8c82fa7ec4db43e539d`. The record is on
  `research/helm-integration-20260923` at
  `records/helm_eval_design_20260923/d1_acceptance/D1_ACCEPTANCE_RESULT.md`. This is a checker result, not a
  learned-model result.
- **The first open item.** At `96644503`, `pointer_learner.py:731` sets `self.analogy_focus_comparison` as a
  plain, changeable attribute, and `_build_container` defaults it to `True` (line 703). The agreed interface asks
  for a read-only boolean.

## Independence: what is lost, said plainly

- **Who was supposed to check what.** The records name Claude as the independent checker of HELM-ANALOGY-REPAIR-1.
  The builder was Codex (`COORDINATION_CLAUDE.md`; `EVALUATION_DESIGN_v0_2.md` row HELM-ANALOGY-REPAIR-1).
- **What changes now.** A Claude builder now makes the read-only fix, and the Claude coordinator runs and reads
  the T4 checks. So builder and checker are the same model family. The fresh Claude reviewer does not restore
  independence.
- **How results are labelled.** Every result produced during this takeover is labelled `CLAUDE_BUILT_CLAUDE_CHECKED`.
  It becomes independently checked only after Codex's review on return, or an outside reviewer.

## Stale scope text

`CNCM/AGENTS.md:16-24` (at `96644503`) says "No new broad team, cloud spending or expanded agent allowance is
selected". Two later owner orders govern bounded jobs:
- the AWS order of 2026-09-23 (`docs/AWS_EXECUTION_PREFERENCE_20260923.md`);
- the takeover instruction above.

The text is not edited here. It still rules out a broad team and any budget expansion, and that stays true.

## Order of work and verification, decided before any run

1. **The builder** makes only the read-only change and one new test file, on
   `claude/helm-builder-continuation-20260923`.
   - The builder runs no torch on the laptop (owner's AWS rule), so its local checks are static.
2. **The fresh reviewer** checks the diff against the public contract, before any AWS run.
3. **One T4 job, run by the coordinator.**
   - Its source is pinned to the reviewed commit.
   - It runs the full switch test suite: the existing 11 cases unchanged, plus the new ones, including a CUDA case.
   - It then runs the A3 same-job OFF control on all 9 models, the OFF probes, and the fresh-ON reading (report
     only).
   - This meets Codex's condition, "AWS verification with the source pinned", and the review condition.
   - If the job finds a defect: fix, new commit, new review, then a new job. Never an automatic retry.
4. **Written before that job.** The failure names and the read-only check are frozen as preregistration
   amendment A4, before any result exists.

## Not covered by this takeover (needs the owner)

- Any training, including the first trained switch-ON checkpoint (acceptance item 2).
- HELM-REACH-LATE-1 and Q4-RECON-2.
- The Stage 1 next cut.
- The rescorer anchor policy.
- Any ceiling above the precedents: $3.00 for a T4 job, $1.50 for a CPU job.
