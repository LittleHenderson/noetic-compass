# Helm failure investigation: workspace and agent-team directive

Date: 2026-09-22  
For: the existing Codex project lead and a separate research team  
Status: proposed research assignment, not an executed investigation or new compute authorization

## 1. Purpose

Establish what the tested Helm versions actually did, precisely why Helm 2.0 did not meet its original pass rule, and which explanations for its strengths and weaknesses survive direct checks. Recommend the smallest useful next experiments or repairs. Do not turn this into another open-ended audit of every tool in the repository.

Separate four questions:

1. What is Helm's actual input-to-answer computation in each tested version?
2. Which exact recorded answers caused the official pass or fail?
3. What evidence explains those answers and the wider changes in performance?
4. What is the least expensive next step that can distinguish the remaining explanations?

The deliverable is an evidence-backed research conclusion and a prioritized next-action plan. It is not a rewritten historical result, a new model release, or permission to change the owner's books.

## 2. Workspace decision

Recommended arrangement: keep the current development workspace intact. Put the investigation in a new research workspace backed by a separate Git worktree of the SAME repository. A new GitHub repository fork is not required.

The existing project Codex prepares the handoff because it can inspect the actual local state. Do not treat this document's historical paths and commits as a substitute for that inspection.

Before forking or making a worktree, report:

- Current repository root, current directory, branch, full commit, and common Git directory.
- Uncommitted changes, untracked files, active agent sessions and running jobs.
- Which saved source versions, test versions, model checkpoints, datasets and original predictions the investigation will study.
- Required files outside the current sparse checkout, required local-only evidence and dependency versions.
- Proposed research workspace, branch, temporary directories, output paths and resource limits.

Preserve current changes and jobs. Do not reset, clean, auto-stash, force-push, remove worktrees or sweep unrelated files into a commit. A chat fork alone is not evidence that the filesystem has been separated. Verify actual paths and branches.

Use the freshest appropriate integration commit for research tooling, but load each historical study from its OWN pinned source and data. Do not run a historical checkpoint through a newer model implementation and call that the original experiment.

Latest integration reported by the owner: `5f7111d5204e872c18df717badc2e2021f31ad70`, branch `codex/cas-reconcile-20260922`. Resolve it and check for successors. Historical Helm 2.0 study source: `20208c92`; recover the full hash and original study records. Recover Helm 1.0's actual training-source identity from its records rather than guessing from an archive commit.

Give each agent that writes code or test files a separate worktree and branch. Read-only agents may share an immutable source snapshot, but each has an isolated output and temporary directory. Only the coordinator integrates research reports. The active development checkout is not the meeting room or shared scratchpad.

Worktrees share Git metadata. They are not a security boundary. Restrict write scope and coordinate repository-wide Git operations. A separate worktree also does not establish independent evaluator custody or authenticate a human owner.

## 3. Preserve context without sharing a preferred answer

Create a small handoff containing the project purpose, owner decisions, study identities, exact evidence paths, known missing artifacts, active-work exclusions and resource rules. Keep observed results distinct from past explanations of those results.

The coordinator may retain the existing conversation. First-round investigators should receive the common evidence manifest and their specific question, not a preferred root-cause narrative. They must submit their first findings before seeing their peers' new findings. Historical documents may already contain opinions; label those as opinions and record relevant prior exposure rather than claiming a perfectly blind investigation.

Keep separate copies or immutable references for large checkpoints and evidence. Verify any copied bytes. Do not assume ignored files, external archives, package dependencies or credentials automatically follow a new worktree. Do not copy credentials as part of a research evidence bundle.

Use the repository-wide module inventory and tracked Git history, not only files visible in a sparse checkout. Absence from one working folder is not proof that a module does not exist.

## 4. Starting facts to verify, not conclusions to inherit

The supplied lineage records report:

- Helm 1.0 passed the historical frozen rule. Its broader interpretation was narrowed because a simple no-learning program did well on the same questions, and held-world wiring patterns also occurred in teaching.
- Helm 2.0 failed that rule in two of three runs because each lost a previously correct answer. It nevertheless gained correspondence performance and had mixed results elsewhere.
- Some earlier documents attribute everything to the frozen-message loop, or attribute matching gains to one head. Those stronger causal claims need their own evidence; they are not assumptions for this investigation.
- The latest reconciliation documents mark Q4 neural execution as NOT_RUN. Preparation is not a failed learning run.
- The compiler, PCBA reader, Ohm arithmetic and atlas are separate engineering achievements. Their absence from an earlier checkpoint is not by itself an explanation of that checkpoint's errors.

Verify exact versions, dates and applicability before quoting any result. Read corrections beside the original reports. Preserve both successful and failed runs and all preregistered seeds.

## 5. Team

Use real separate agent sessions where available. Do not simulate a team by writing invented conversations. If concurrency is limited, stage the sessions in batches while retaining the first-report barrier. If only one session is available, disclose that it is a single-agent review rather than independent reviewers.

### A0: coordinator and evidence custodian

Resolve the workspace, freeze the subject manifest, allocate non-overlapping tasks, preserve original artifacts, manage resource limits and assemble the findings. Do not supply a preferred technical explanation. Do not act as final judge of the coordinator's own implementation.

### A1: pass-rule and recorded-answer investigator

Read the exact original pass rule. Reconstruct the before/after answer transitions on all recorded seeds using saved predictions and the applicable checker. Identify exact failing question IDs, raw answers and relevant source versions. Separate the narrow reason for the label from task-family performance. Do not change the rule, remove inconvenient questions or promote a version retroactively.

### A2: model structure and information-flow investigator

Trace the actual input representation, node updates, message aggregation, question information, pooling and task-specific answer components in Helm 1.0 and the tested Helm 2.0. Determine what distinctions survive and where they are lost. Check any hypothesis that different correct answers become indistinguishable to the model. Distinguish a local message-path limitation from a proved limitation of the whole model. Use source analysis and permitted non-neural probes first.

### A3: teaching data and transfer investigator

Inspect examples, splits, ordering, labels, available information and answer generation. Compare graph structures independently of their names. Check repeated structures, class imbalance, training/test exposure, answer leakage and simple shortcuts. Identify any representation collision or impossible labeling task with a concrete example. Do not label developer-examined questions as fresh hidden evaluation data.

### A4: training and retention investigator

Inspect the settings and update records that actually ran: initialization, data order, loss contributions, learning rate, clipping, numerical stability, parameter freezing, rehearsal, stopping and checkpoint restoration. Distinguish implemented options from active options. Investigate why previously correct answers were lost without assuming that a smaller training loss proves better reasoning. Do not initialize a model merely to inspect metadata when a non-executing route suffices.

### A5: answer selection and comparison investigator

Study candidate construction, decoding and scoring separately from learned scores. Check valid alternatives, one-to-one matching requirements, ties, ranks and name-based shortcuts. Register stronger simple comparison methods before using their results to judge the claimed advantage. Examine analogy and correspondence separately. Do not assume soft matching scores alone guarantee a valid final assignment.

### A6: independent reproducer and challenger

First, independently reconstruct a small source-bound part of the recorded result without consulting the other agents' new conclusions. After first reports are submitted, try to falsify the central claims. Re-run decisive bounded checks where permitted and review whether proposed experiments genuinely distinguish competing explanations. Record when a check reuses the same implementation rather than claiming independent implementation.

### A7: final judge

Use a fresh review session not responsible for the hypotheses or fixes being judged. Review the evidence matrix, original reports, challenges and follow-up results. Read decisive raw artifacts, not only vote counts or the coordinator's summary. Classify findings and rank next actions. The judge cannot grant spending permission, change canonical definitions, modify release criteria or turn a plausible explanation into an established cause.

## 6. Investigation process

### Stage 0: establish the subject

Produce the workspace report and exact source/evidence manifest. Identify newer records that supersede earlier summaries. Record any missing historical evidence. Reuse valid current records; do not rerun the whole repair history without a specific reason.

Select the exact scope of "did not pass." The default is the original Helm 2.0 study compared with Helm 1.0, plus their recorded wider strengths and weaknesses. List any later study separately. Q4 preparation is context, not a substitute subject.

### Stage 1: independent first reports

Agents A1 through A6 work independently. They may ask the coordinator for missing artifacts or clarify the shared question, but do not read each other's first conclusions before the submission barrier.

Every first report must include:

- The precise question investigated and subject versions.
- Facts checked, with paths, source lines and artifact fingerprints where applicable.
- Actual commands, environment, outputs and whether each check ran.
- Leading explanation and the strongest plausible alternative.
- Evidence that would disprove the leading explanation.
- The smallest discriminating next test, its inputs and expected outcomes under each explanation.
- What remains unknown and why.

A report can conclude that the evidence is insufficient to assign a cause. It cannot conclude that an unknown cause is absent.

### Stage 2: evidence conference

After all first reports are saved, distribute them to the investigators. Build a comparison table of agreement, disagreement and missing evidence. Each investigator responds to at least one competing explanation in its area. Record real findings and responses, not an invented meeting transcript.

Discuss at least these distinctions:

- Failure of the original pass rule versus deterioration in useful behavior.
- Improvement relative to the untrained model versus improvement over a simple existing algorithm.
- An architecture being able to represent an answer versus actually learning it.
- Better numerical scores versus valid decoded answers.
- New names versus genuinely new structures.
- Old module defects versus defects in the exact code that produced the studied answer.
- Evidence of a correlation versus evidence isolating a cause.

Do not choose a winner by majority vote. Agreement among agents using the same evidence is not independent experimental confirmation.

### Stage 3: targeted follow-up

Choose only tests that can change the conclusion or the priority of a repair. State competing predicted outcomes before executing them. Separate numeric-invalid experiments from low-accuracy experiments. A NaN-producing configuration cannot be treated as a valid weak comparison model.

Rechecking stored predictions and writing small pure diagnostic probes may proceed only within existing applicable permissions. Loading a neural checkpoint to make predictions is model execution even when described as an audit. No new model initialization, inference, training, GPU use, paid API calls or cloud launch follows automatically from this directive.

Any requested new compute job must identify exact source, data, settings, comparisons, resource caps and stop conditions. Do not reuse an old job's permission for a materially changed job.

Default limit: at most two focused follow-up rounds after the initial conference. Stop earlier when decisive evidence is available. At the limit, report what is established and the smallest remaining experiment rather than reopening every topic. Extension requires an explicit revised scope and allowance.

If model changes need training to distinguish causes, keep shared weights and training conditions matched where possible, document unavoidable differences and use a declared migration when shapes differ. Evaluate prospective fixes on a separately planned fresh set as well as the historical diagnostic cases. Do not tune on historical failures and call success on those same failures fresh transfer.

### Stage 4: final judgment and research commits

The final judge issues a report with:

1. Exact historical pass/fail reason.
2. Observed strengths and weaknesses by task family and run.
3. Causes established within a stated scope, with decisive evidence.
4. Plausible causes that remain unproved.
5. Explanations contradicted or ruled out by the available checks.
6. At most three prioritized repairs or experiments, with expected benefit, risk and verification method.
7. Evidence gaps and unresolved dissent.
8. What can proceed now and what requires the owner's next decision.

Commit reports and non-invasive research probes on research branches using explicit staging. Preserve each first report and add revisions instead of silently rewriting it. Do not automatically merge experimental model changes, modify frozen graders or book definitions, replace historical receipts or update release labels. Publish only through the project's actual commit/push permissions, with no force-push.

## 7. Minimal deliverables

Use one newly named investigation directory following the repository's existing conventions. Suggested files:

- `WORKSPACE_REPORT.md`
- `SOURCE_AND_EVIDENCE_MANIFEST.json`
- `FIRST_ROUND/A1.md` through `A6.md`
- `FINDINGS_MATRIX.md`
- `FOLLOWUP_PLAN.md`
- Per-probe raw evidence and before/after identities
- `FINAL_JUDGMENT.md`
- `NEXT_ACTIONS.md`

Adapt filenames to established conventions. Do not build another general-purpose research platform, atlas renderer or authorization system for this task.

Report test functions, input-specific cases, repeat executions, selected scope and unavailable files separately. Do not call agent work "$0" merely because no GPU was rented; account for actual agent/tool allowance where available. Use plain English for owner-facing findings.

## 8. First message to the current project Codex

Inspect your actual current workspace and recommend the safest setup for this investigation. My preference is a new research workspace/worktree of this same repository, with the existing workspace preserved.

Do not start the full team in the current mutable checkout. First resolve current local changes, active jobs, study versions and required evidence. Return the exact source point, destination and any real blocker. Prepare the small handoff and, using the available worktree and agent tools within current permissions, proceed with isolated independent investigations, a findings conference, bounded targeted follow-up and a separate final judge as described above.

If the workspace must be created through the owner's UI, prepare everything possible and state the one action required. Do not pretend a new conversation has isolated the files. Do not let missing GPU permission block source and saved-record research that is actually permitted.

Return actual first-stage progress, not just acknowledgment. No research team has been launched by the preparation of this document.

## 9. Source basis and status

This directive draws its project starting facts from the supplied `BRAIN_LINEAGE.md`, `FIRST_RETURN_Q0` report, `LINEAGE_RATIFICATION_CLARIFICATIONS_20260921.md`, the September 22 reconciliation README and the shared-module inventory proposal. Some historical documents contain stronger causal explanations than their evidence supports; verifying those explanations is part of the assignment, not a reason to assume them.

The owner-reported latest reconciliation commit is a starting locator, not independently verified local state. OpenAI's current Worktrees and Subagents documentation was consulted for the general workspace recommendation. Codex must verify which features and permissions its actual installation provides.

The structure, roles and stopping rules here are proposed workflow choices. They are not a claim that the investigation ran, that a root cause has been found, or that any owner-only semantic or resource decision has been made.
