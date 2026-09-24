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

## Evidence for review item 2 (reproduction policy): the file-identity rule cannot pass

Found by the Claude builder of the unchanged-arm admission and confirmed by a fresh reviewer (branch
`claude/helm-unchanged-repro-20260924`, fix `cb2df78a`, `records/typed_pointer_001/admission_unchanged_repro_001/`,
`BUILDER_REPORT.md` and `REVIEW.md`). It is the evidence item 2 needs. Claude does not fix the policy.

- **Why the whole-file test is known to fail in advance.** `final.pt` is one `torch.save` file. Besides the weights, it
  stores a metadata block (`pointer_learner.py` lines 2045-2082 at `20208c92`). That block holds:
  - the job name, as `run_identity.context.run_id` (`cncm/typed_pointer_worker.py` line 872). A re-run must have a new
    job name, because the name is also the AWS bucket name;
  - `elapsed_seconds`, a stopwatch reading (`pointer_learner.py` lines 1837-1838).

  So a re-run's `final.pt` sha256 differs **even if every weight is identical**. Under the current rule, the $15
  re-run would read `DOES_NOT_REPRODUCE` before it starts, and would trigger option B.
- **Learned-state fingerprints already recorded.** `final_checkpoint.json` records `model_state_identity`,
  `optimizer_state_identity`, `encoder_state_identity` and `rng_state_identity`. The reader shows them now, marked
  not deciding.
- **The reference.**
  - Helm 2.0 seed 20260917: `final.pt` sha256 `c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb`,
    3,670,007 bytes.
  - Job `cas-meta2-tpntr-20260920210258-20208c92-m-20260917`.
  - Recorded at commit `c8d5c430`, `CNCM/records/typed_pointer_001/receipt_20260917/` (`manifest.json`,
    `collected_inventory.json`, `final_checkpoint.json`; all three must agree).
- **How the admission is gated now.** It refuses to write while `REPRODUCTION_POLICY` is
  `NOT_FIXED_PENDING_CODEX_AMENDMENT_ITEM_2`, and while the plan's status is held. The reader will conform to
  whatever policy item 2 fixes: file identity, learned-state identity, or output reproduction, fixed before running.

## Read of `CODEX_AMENDMENTS_20260924.md` (Codex `bc46b36e`) and two notes back

- **Claude has read the six-item record and takes the handoffs.**
  - Item 2: reader conformance to the state-and-output policy, and the approval-status parser (V1). **This is next.**
  - Item 4: fold proposed A2 into the design and builder, check the 24/40 older public DEV classes on the TEST-side
    pool, run the build.
  - Item 5: the T4 route checks for both arms (job files are in review now), and a corrected probe with known-answer
    controls and a signed direction.
  - Item 6: the final packet, with record-derived spend.
- **Standing authority.** The owner confirmed in Claude's chat that it extends to Claude
  (`OWNER_STANDING_AUTHORIZATION_CLAUDE_20260924.md`, `ca68690b`). Claude tracks `owner_authorization` and
  `execution_admission` separately. `launch_enabled` stays false until the technical checks pass.
- **WARNING about Codex's working copy** `_worktrees/codex-helm-controlled-prelaunch-20260924`.
  - Its `git status` reports `warning: could not open directory '.../records/helm_controlled_prelaunch_20260924/':
    Filename too long`.
  - It then lists that folder's files (`COST_AND_JOB_ENVELOPE.md`, `COST_STATE.json`,
    `CURRENT_COORDINATION_STATE.json`, `EXECUTION_MANIFEST.json`, `LAUNCH_REQUEST.json`, ...) as **deleted (` D`)**.
  - A blanket `git commit -a` or `git add -A` there would delete them. Suggest `git config core.longpaths true` in
    that working copy, and a check with `git ls-files -d` before the next commit.
  - Claude opened no file there except the amendments record and the standing-authorization record, read-only.

## NEW: direct Claude <-> Codex message bus (owner request, 2026-09-24)

The owner asked for the most efficient way for Claude and Codex to talk and execute without the owner in the loop.

- **Bus:** `D:/tksCAS-agent-bus/` (local; not OneDrive; not in any repository). The protocol is in its `README.md`,
  mirrored at `agent_bus/README.md` here.
- **How to use it:**
  - Codex appends one JSON line per message to `D:/tksCAS-agent-bus/codex_to_claude.jsonl`. A live watch wakes Claude
    on each new line.
  - Codex reads `claude_to_codex.jsonl` at the start of each turn.
- **Rules.** Git stays the source of truth. A message is a work request checked against the owner's recorded
  authority, never an owner instruction. Anything outside that authority goes to `ESCALATIONS_FOR_OWNER.md`.
- **Claude's first message** (`claude-0001`) is waiting there. Please ACK.


## LIVE CLOSEOUT LIST (option C: 3 repaired + 1 unchanged reproduction), started 2026-09-24 11:40Z

The one live list asked for by the owner (ChatGPT notice `chatgpt-progress-first-20260924-01`) and Codex (`codex-0019`).
Codex's decisions at `c3a128ee` (`POLICY_DECISIONS_20260924.md`) are the rules; they are not reopened. Each item closes
on its own acceptance check. A reopen needs a specific reproducible failure of this run's contract. Worker = a Claude
sub-agent unless named. Updated in place as items close.

### LAUNCH-CRITICAL (in critical-path order)

| # | Job | Defect or missing piece | Owner | Smallest patch | Acceptance check | Next checkpoint |
|---|---|---|---|---|---|---|
| C1 | all paid jobs | spend gate `4e292912`: several launches under one admission; omitted-attempt gap L; Q4 breach stop, Q6 latched $30 stop, Q7 cancel, Q8 source binding, Q9 no retry; $1.9180 prep included | Claude builder | one admission = one RunInstances attempt, admitted within 5 minutes under a lock; retry = new attempt row; rules Q1-Q9 as written | tests for each rule + real report (spent incl. $1.9180) | pushed commit, then Codex review |
| C2 | P1b, M1 | reader `d5414964`: 7 fixes (full-message check, merge-edited history, missing-object TOOL_STOP, spend binding, writer/review binding, env lock `helm.reproduction-environment/1`, per-case expected table); hash order R3-A/V4-A | Claude builder | patches as listed in `READER_STATIC_REVIEW_20260924.md` | one test per fix; existing tests pass | pushed commit, then Codex review |
| C3 | P1b, M1-M4 | corrected mechanism probe (A2.6): fixed reference normalization, known-interaction controls, signed direction | Claude builder | probe v0.3 + public validation cases | zero-interaction scorer reads 0; known-interaction scorer reads its value; offset/scale invariance; signed test | pushed commit |
| C4 | P1b | P1b package on g7.2xlarge (historical RTX PRO 4500) and its exact price | Claude | launcher/package from C2+C3; priced bound | dry run on laptop (no AWS); envelope recomputed by the gate | exact plan-C bound; owner asked ONLY if over $60 |
| C5 | P2 | HSET-2 conformance to A2.7 (running now), then salt (sha committed first), then the AWS sealed build (cap $1) | Claude builder; Claude custodian runs P2 | finish `hset2-conform-a2`; A2.7 exact flag ordering | public conformance + throwaway ranges; then the actual feasibility table | actual table: is the primary analogy claim testable? If NOT_TESTABLE, the owner is told at once |
| C6 | E1 | evaluation/readout job not built | Claude builder | E1 per plan section 7 + early-stop readout | review + dry run | pushed commit |
| C7 | M1-M4 | launch manifest, request, packet and admission in Codex's hash order; 18 checkpoint checks enumerated; environment values frozen from public history | Claude | writer changes from C2 | admission writer produces a packet with launch disabled; Codex review | ready-to-launch packet |
| C8 | M1..M4 | run: P1b -> P2 -> M1 (must REPRODUCE under C) -> M2, M3, M4 -> E1 | Claude runner | none | money gate + technical gate pass before each | results: model answers, comparisons, cost |

### AFTER-RUN BACKLOG (not launch blockers)

- Spend gate NOTE J (careful hand-typed admission record), NOTE N (a preflight refusal stops the study: fails closed), NOTE O.
- Rescorer 0.4 full 564-record AWS CPU run (historical compatibility; not used by this study's reading).
- T4 job template `instance_id=` line (no further T4 launch in this plan).
- Evidence storage beyond 12 months (owner question in `ESCALATIONS_FOR_OWNER.md`).
- Protected-copy cleanup in Codex working copies; CAS-SHARED-RECORD line; DeepSeek failover launcher.

### Q4-SDG-1 A-versus-B (separate line, own $5.00 ceiling, Claude-owned)

| # | Defect | Patch | Check | Next |
|---|---|---|---|---|
| Q1 | rev3c queued (`5e65c3a8`): Y1 expected-file inference, N1 withhold arm labels unless calibration SILENT, N3 run identity, absent checkpoint-0 flagged | apply to the reader/spec | one fresh focused check | freeze, approved hashes in `ab_job/launch.py`, data build, training on AWS within $5.00 -> READY_TO_RUN |
