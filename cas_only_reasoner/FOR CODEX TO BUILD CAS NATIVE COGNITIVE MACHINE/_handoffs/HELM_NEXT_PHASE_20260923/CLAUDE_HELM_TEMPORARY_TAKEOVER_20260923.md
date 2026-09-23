# Claude: temporary Helm implementation takeover

Date: 2026-09-23
Status: Proposed owner instruction. Copying or saving this document does not itself record approval, expand spending, or change an acceptance rule.

## Purpose

The owner reports that Codex is unavailable until the usage reset shown as September 28, 11:23 AM. Continue the existing project using Claude. Do not wait solely because the previously assigned builder is unavailable. This is a temporary ownership change, not a restart or a new research program.

Preserve Codex's existing code, branches, working folders, results and unfinished files. Do not rebuild accepted work. Determine the actual latest state before selecting a task.

## 1. Starting evidence and current status

The following status is based on the seven supplied handoff documents, not a new execution of their checks. Newer local evidence may supersede it; resolve that explicitly.

### Checker version 2: accepted for its stated scope

`D1_ACCEPTANCE_RESULT(1).md` records ACCEPTED for Codex source `7f85af1eb9eb0ed991d5a8c82fa7ec4db43e539d`. A1 through A6 and extra check X passed in the complete second acceptance run.

The report establishes agreement on all 564 historical registry records and their slot plans, and all 6,768 saved prediction correctness decisions. It accepts the new checker for five- and six-node analogy and correspondence within its stated bounds. It does not establish learned Helm ability, correctness outside those bounds, or outside evaluator custody.

Accepted file identities, LF-normalized SHA-256:

| File | SHA-256 |
|---|---|
| checker_v2.py | d24d8276955bacbe626ebe6293efe7b64c2cf36544100b60175f6d0ab80e6258 |
| answers_v2.py | b0bdabfcfac656e4071f192d9bda8ff7dec8b88baf077f29131d8f94497d1bb5 |
| slots_v2.py | 7b9c2c3a0aca938acf0979aa7d74f1fea422726333926f079a5f8e06f5e7d2fb |

The old statements that D-1 acceptance is pending are historical. Preserve them, then add a pointer to the later acceptance result. Do not rerun the full acceptance campaign merely because an older handoff says to do so. The current runner is `d1_acceptance_run.py`; its A2 supersedes the older `a2_compare_harness.py`.

The frozen checker remains the scorer of record for historical results. New checker acceptance is not permission to rewrite those results.

### Analogy repair: implemented; model acceptance remains separate

Codex's focus-to-candidate comparison repair is at `60e382b042d54eab68394393b1d8fe4540a1ac06`, later incorporated into its continued work. The implementation handoff reports public effect/interface checks and a larger ON architecture. It does not report a successfully trained repaired model.

The peer reconciliation identifies a remaining narrow interface issue: `analogy_focus_comparison` is a mutable public Boolean, although the agreed interface calls for a read-only setting. Verify whether a later commit already fixes it before editing.

OFF must preserve the old layout and scoring. ON adds five tensors and uses a separately identified model. Do not load historical weights non-strictly into ON and call the result the unchanged historical model.

### Larger questions: checker support is not full learner integration

`CODEX_D1_STATUS.md` states that the public learner still imports the old slots module. The new checker and candidate-generation tools alone do not prove that learned inference accepts larger packets. Inspect the actual current imports and exercise public development fixtures before asserting end-to-end support. Do not silently redirect the historical learner to the new rules.

### Other work

Keep the compiler, PCBA reader, exact CAS-Ohm calculations, atlas and saved-view work intact. Q4 is a separate expression-reconstruction experiment. Its first run already occurred; later failed launch attempts do not erase that result. Do not call Q4 unrun overall, call it Helm 2.0, or launch it incidentally while accepting the analogy repair.

## 2. Temporary division of responsibility

Use a small team, not another broad multi-agent research campaign.

**Coordinator and evaluation custodian:** the existing Claude session retains the task ledger, acceptance specifications, and final-test custody. It supplies only public contracts, public development examples and source identities to implementation workers. It does not send hidden answers, item-specific final-test feedback, or its full answer-exposed conversation to the builder.

**Temporary builder:** a separate Claude coding session or agent receives the public handoff and an isolated implementation working folder. It completes the specific unfinished Codex task and records all changes. It must not inspect sealed evaluation files or outputs.

**Fresh reviewer:** where an actual separate session is available, it checks the patch against the frozen public specification and reproduces selected checks. It must report its exposure, permissions and exact work. Do not invent an independent reviewer when no such session ran.

Different chats or folder names alone do not establish isolation. Check actual file access, inherited prompts, exported logs and feedback. If the builder has already seen final-test material, record that exposure; opening another chat does not erase it. Continue useful public development, but do not claim protected evaluation until its custody requirements are met.

The D-1 report already states that Claude wrote both its oracle and tests and that outside custody has not been repeated. Preserve that limitation. Using more Claude agents is not equivalent to outside custody or a different-provider audit.

## 3. Recover before editing

Record the repository root, working folder, branch, full commit, uncommitted changes, active local/remote jobs, output folders and applicable instructions. Read AGENTS.md, CLAUDE.md where applicable, current coordination records and actual owner decisions.

Discover related source through tracked Git objects as well as materialized files. A partial checkout is not evidence that a module does not exist.

Create a new implementation branch and working copy from the verified current source containing the needed changes. Record the parent. A name such as `claude/helm-builder-continuation-20260923` is illustrative, not a pre-existing branch or mandatory destination.

Do not reset, clean, delete, force-push or overwrite Codex's work. Do not change source used by an active job. Stage explicit files and inspect the staged changes. Follow the actual current commit/push instructions.

Write a dated coordination amendment identifying the temporary builder and reviewer. Preserve earlier ownership records as history rather than pretending Codex made subsequent Claude changes.

## 4. Next work, in dependency order

### A. Preserve accepted D-1 and reconcile outstanding items

Verify the accepted source identities and locate its result and run logs. Mark D-1 complete only for that accepted scope. Keep remaining model acceptance, public larger-packet integration, evaluation design and custody as separate items.

Inspect the current rescorer review status. Preserve the original historical rule: Helm 1.0 PASS/PASS/PASS; Helm 2.0 PASS/PASS/FAIL. No automatic zero-loss veto. Do not replace the integrated rescorer with an earlier Claude reference implementation without an explicit reviewed change. The old-anchor compatibility versus new-anchor policy difference needs its current recorded resolution, not an assumed choice.

### B. Close the read-only comparison-setting issue

If it is still open, implement only the agreed read-only interface. Preserve OFF tensor keys, shapes, initialization behavior and scoring. Keep ON's additional tensors and model identity explicit. Add tests for the intended public interface and retain before/after evidence.

Do not mix this patch with a learning-rate change, wider model, different decoder or dataset replacement. A configuration repair is not a demonstrated improvement in answers.

### C. Perform the required model-preservation and effect checks

Use the pinned public acceptance plan and the current resource scope. The peer handoff specifies a same-job T4 comparison across nine models:

1. Run unchanged historical source as the control on the same T4.
2. Compare the repaired OFF path bit for bit with that control.
3. Require the control also to match the retained T4 references.
4. If the control does not reproduce, report `REFERENCE_NOT_REPRODUCIBLE_ON_T4`, not a preservation pass.
5. Retain strict historical checkpoint loading, original keys/shapes, 174,303 parameters in OFF, and the historical absence result.

Read the actual acceptance specification before execution. Do not guess which nine model records it names. CPU initialization checks or another device are not substitutes for a specifically required T4 result.

Newly initialized ON effects are not trained ON acceptance. Each future trained repaired checkpoint examined for this requirement must meet the declared `PRESENT_GRAPH_AND_DOMAIN` check. This remains distinct from correct answers and comparative learning benefit.

### D. Finish the public evaluation design and interface integration

The latest peer note still lists Stage 1 cell thresholds, effective sample sizes and the final success rule as outstanding. Check for newer decisions. Preserve grouping by graph shape, explicit comparator selection, candidate-bank exposure checks and final-test answer isolation. Do not select thresholds after seeing future model outcomes.

Use public fixtures to verify the five-/six-node route and the chosen checker/slot profiles. If learner integration requires another change, scope and version it separately. Preserve old packet behavior.

Once the preceding requirements are met, select exactly one already-approved, clearly scoped next experiment. Analogy learning, a late-reach continuation and Q4 reconstruction remain separate jobs. Do not run all three simply because only one coding service is available.

## 5. Compute and permissions

The owner's September 23 AWS preference supersedes older advice to run new checks on the laptop. The supplied handoff records insufficient local memory and explicitly says not to repeat the memory-exhausted local probe automatically.

Use AWS for new tests and sustained computation according to `docs/AWS_EXECUTION_PREFERENCE_20260923.md` and the current project instructions. Lightweight source inspection, editing and receipt checks remain subject to those instructions. Preserve the actual devices of historical runs.

Standing research authorization is not a blank cheque, but do not repeatedly request a new general approval when the selected task is already covered. Resolve the task, source, instance/device, duration, work limit, cost ceiling, remaining allowance, stop conditions, evidence collection and cleanup before launch. Ask only for a genuinely missing or expanded authorization.

There must be one runner for each job. Inspect live provider state before launch. Old receipts saying instances were terminated are not a current inventory, and a Codex usage limit does not prove a previously launched cloud job has stopped.

No automatic duplicate jobs, unlimited retries, substitutions for a required device, new account keys, invented owner signatures or budget expansion. Record failed attempts separately and preserve outputs.

## 6. What to return to the owner

After each bounded task, report in plain English:

- The task completed, branch and full commit.
- Files changed and the source/specification used.
- Exact checks, outcomes and remaining failures.
- Whether a model ran, learned weights changed, or money was spent.
- What remains open, with one concrete next action.

Distinguish written test functions, input-specific cases and repeated runs. Preserve earlier failures and their later resolutions. Do not bundle unrelated counts into a new success headline.

Before Codex returns, maintain `CLAUDE_CONTINUATION_LOG.md` with a source/commit list, changed-file list, task statuses, run receipts, actual exposure to final tests and unresolved review items. Codex should review that bounded change set, not restart completed acceptance or automatically merge the branch.

## 7. First return and stopping point

First recover the real checkout and report the temporary assignment, accepted D-1 source and next unfinished task. Then carry out permitted work. Do not stop after writing another broad plan.

Stop the affected task, not every task, if required evidence, permissions, a reproducible control or protected evaluation access is missing. Continue unrelated authorized development. No outcome is promised by the Codex reset date.

## Source register

These attachments supplied the facts in this handoff. Locate their original project paths and latest successors before applying them.

- S1: `D1_ACCEPTANCE_RESULT(1).md`, acceptance of checker v2, 2026-09-23. Original result JSON/log under `hset1a_aws_job/results/` relative to the D-1 acceptance folder. Accepted source `7f85af1e...`.
- S2: `README(20260923-222439).md`, D-1 acceptance tools; runner v0.2 supersedes the old A2 harness.
- S3: `CODEX_~3.MD`, latest peer handoff reconciliation. Its pending D-1 wording predates S1.
- S4: `CODEX_RESULTS.md`, Codex implementation handoff; analogy source `60e382b0...`, evidence integration `75013c13...`.
- S5: `COORDI~1.MD`, Codex coordination record, evaluation design questions and source-preservation rules.
- S6: `CODEX_D1_STATUS.md`, D-1 implementation/AWS handoff, larger learner-interface limitation and September 23 AWS preference. Its pending acceptance wording predates S1.
- S7: `README(20260923-222811).md`, peer evidence reconciliation. Reference peer `dfe15fa6...`; builder source `7f85af1e...`; required OFF/T4 control and remaining read-only-setting correction.

This document is an implementation handoff recommendation. It creates no new project result, code change, training run, resource permission or independent acceptance.
