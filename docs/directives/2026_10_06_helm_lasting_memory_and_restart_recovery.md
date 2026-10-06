# HELM lasting memory and restart recovery directive

> **Canonical intent:** [`docs/HELM_VISION_AND_ROADMAP.md`](../HELM_VISION_AND_ROADMAP.md). This directive serves abilities 3 (retention), 6 (RPA) and 7 (built together), roadmap steps 1–4 and 6. It grants no merge, push, run, purchase or credential authority (its own words, below).
>
> **Provenance:** plain-text conversion of `HELM_lasting_memory_directive_to_Claude.docx` as received 2026-10-06; headings preserved, emphasis and footnote markers kept inline. The original .docx is the authority if the two differ.
>
> **Gate answer (§3 of the vision):** ability 3. Behavior: teach a fact, show it changes a later answer, save accepted state, terminate the process, restore, same behavior without reteaching; then correct or retract it and show every dependent answer changes before and after restart. Control: fresh recompute from the accepted event history (and record-first without RPA, for the RPA claim). Criterion: exact agreement on every deterministic case, zero stale fast-path answers, every acknowledged update recovered within the declared failure model, every replayed update applied once. Does not show: permanent retention, neural learning, or any lifetime guarantee.

*To Claude. From Little HendersonRevised for existing implementation reuse |  October 6 2026 PDT*

Claude, work with the RPA and recovery code we already have first. Revise them only where the evidence shows a gap. The next CAS-RPU step must demonstrate memory that changes later answers, survives a fresh process, and stays correct after corrections and retractions.

Keep the claim narrow: lasting memory here means correct behavior across the sessions, restarts and failure conditions we actually test. It does not mean permanent retention, neural learning or a lifetime guarantee.

## Reuse the existing implementation first

Start with _worktrees/codex-rpa-recorded-run at eb9985566bd11a89f485d627186ef0efa7177f02, the existing native and compound journal recovery, the CAS memory design proposal and Claude’s PR 248 organism. Audit what can be reused or extended before adding code. Keep one canonical implementation and entrypoint. Do not start a parallel RPA, a new memory framework or duplicate directories. Preserve the protected alternatives.

## The first result I want

Teach a new fact or reusable lesson. Show that it changes a later answer, save the accepted state, terminate the process, and show the same useful behavior after restart without teaching it again.

Correct or retract that knowledge. Show that every dependent answer changes appropriately before and after restart. Old answers must never escape through the faster path.

Measure whether answering from a valid held record avoids unnecessary reasoning work. Separately measure whether RPA contributes beyond an ordinary record index.

## Keep the current evidence honest

🏆 PR 248 at 4377a7da37176a0e9eecb25ad69a85ef89ec96ea demonstrated held symbolic beliefs, retraction and separation of guesses from facts on generated streams. The evaluation used 40 items and 89 questions per world condition, with a fresh organism for each item. The replay baseline also reached 100 percent. This establishes a bounded behavior result; it does not establish memory across items or process restarts. [1]

The 393 and 262 passing tests are preparation. Correct the PR headline that calls the replayer cheaper before review or merge consideration: the committed report marks the counters INCOMPARABLE. This directive grants no merge authority. The current unmarked-guess ablation had no measured effect. Add a meaningful probe, or report the change as hygiene. [2]

The English encoder currently accepts five rules and rejects other forms. The processor receives triples. Keep broader English testing separate from the memory claim.

## Protect the scope

Preserve PR 248. Any necessary schema or contract version is an extension of the existing contract, not a new project fork. This draft grants no merge, push, run, purchase or credential authority. The project ceiling is $250; the ledger is $97.59, with the actual bill pending reconciliation. Keep AWS-only execution and coordinated admission. No new run budget is granted. Resolve the blocked operator profile through the authorized route before dependent runs.

## 1 Define the memory authority

RPA means Recursive Possibility Atlas: a map of states and alternatives. Use it to locate relevant records and show branches. The accepted event history owns truth. RPA can be rebuilt from that history and must never silently promote a possibility into a fact.

## Inspect before extending

The RPA worktree at eb9985566bd11a89f485d627186ef0efa7177f02 separates current_state_id from inspection focus and hypothesis branches. Its native adapter replays trusted genesis plus an external digest, then projects the result. The recorded adapter excludes learner, Torch, checkpoint decoding and model calls; it labels its view ARCHIVED_RUN_RECORD_NOT_LIVE_HELM. Rebuild this read-only index only after authoritative restore validation. RPA is not the persistence engine. [4]

Audit existing native and compound journal recovery alongside PR 248’s organism. For each requirement, name the existing module, what it already does, the exact gap and the smallest compatible change. Workspace.snapshot is an inspection summary, not a reloadable checkpoint. The CAS memory substrate design remains a future proposal. [5] Reuse its design where applicable without claiming implemented durability.

## Use a small versioned contract

Identity: organism, project, context, branch and stream identifiers; schema and engine versions; the last committed sequence number. A record from one context must never answer for another by name collision.

Events: unique event ID, ordered sequence, event type, payload, source, explicit polarity, commit status and the version it expects to update. Include assertions, corrections, retractions, rule changes and branch promotions.

Beliefs and answers: stable proposition or query key, result, world semantics, evidence IDs, rule IDs, dependencies, validity status and the versions under which the result was derived. Store enough provenance to explain why an answer is supported.

Snapshots: a complete accepted-state checkpoint, versions, last included event, hashes and atomic manifest. Cover the workspace, cognitive memory, motivation, standing conclusions, event log, clock, query counters and heartbeat state. Specify what is retained, safely reset or deterministically rebuilt and why. Restore source status and context/world identity before answering.

RPA entries: references to accepted records or clearly marked uncommitted possibilities, dependency/version summaries and branch ownership. Do not let an atlas entry substitute for supporting evidence.

## Define update and conflict behavior

Use one writer for each authoritative stream. Let other components propose events through that owner. Either reject stale expected versions or serialize them explicitly. Preserve conflicting assertions with their provenance and apply a declared conflict policy. Never silently use last-write-wins to erase a disagreement.

Preserve the full verdict precedence in the current contract, including clean routes, disputed routes and INADMISSIBLE. An explicit denial does not automatically justify NO. Absence-based closed-world NO and open-world UNKNOWN can be invalidated by new facts. Assumptions currently count as ASSERTIVE; give them explicit context scope before multi-session reuse. Rules and world mode are dependencies too.

## Keep symbolic and neural retention separate

Saved beliefs and recipes are symbolic state. Current RPA does not restore neural state. A neural-retention claim needs separately verified weights, optimizer state, update counters and random-number-generator state, plus learned behavior before and after restart. A saved atlas, deserialized object or larger record count is insufficient.

## 2 Make answer reuse safe

Implement a guarded positive-answer path behind a feature flag. Initially reuse only a still-valid held positive that preserves the full existing verdict contract. Keep denial, conflict, INADMISSIBLE and unknown handling on the current path. Every uncertain check falls back. Start with whole-context invalidation, then refine dependencies after correctness is demonstrated.

## Required query sequence

Canonicalize the query without changing meaning. Bind context, branch, world mode, polarity and semantics version. Reject unsupported English instead of silently converting it into a different question.

Read a committed state version and look up candidate records. RPA may narrow this search. Keep an ordinary-index implementation available for the comparison.

Check commitment, context, provenance and all supporting facts and rules at their current versions. Preserve clean-route and disputed-route precedence. Calling Workspace.ask alone is insufficient because it does not enforce contested-route semantics. Reject stale, retracted, conflicting or unsupported dependencies.

Validate against one consistent state version. If an update commits during validation, retry or answer from an explicitly pinned read version. Never validate old dependencies and publish against new state.

Return the answer with its state version and support trace only after all checks pass. Preserve commit and trace bookkeeping. Otherwise run the existing derivation, verify its support and commit through the single writer. Validate restored state before any answer; the current post-event heartbeat is too late for this check.

## Cover every cause of invalidation

Maintain reverse dependencies or an equivalent complete mechanism. Retraction and correction must reach transitive dependents. New facts can defeat an absence-based NO or resolve an UNKNOWN. Rule replacement, priority changes, changed thresholds, world-mode changes, context changes and schema/engine changes can also invalidate a record. Test each event type explicitly.

For each record, distinguish valid, dirty, unsupported and conflicting states. A dirty record may remain visible for explanation, but cannot supply a current answer. Mark the committed update and its invalidations as one atomic state transition. Correctness must not depend on a background cleanup finishing first.

## Keep guesses on uncommitted branches

Store a guess as a possibility with its source, assumptions and branch ID. It may guide exploration. Only an explicit accepted event may promote it. Promotion must validate support and receive a new committed version. Retraction of a promoted premise must invalidate its conclusions just like any other dependency.

Build the meaningful guess probe around a case where admitting the guess as a fact would change a later answer. Include an unsupported tempting guess, a supported competing fact and a subsequent correction. Freeze the expected outcomes before running the ablation. If the measured difference remains zero, report zero.

## Keep this optimization reversible

Allow record-first and RPA routing to be disabled independently without losing accepted events. Restore walk-first from the same state. Record hit, miss, rejection and fallback reasons. Organism._reason currently increments the scan count by the workspace size unconditionally; measure the work actually performed when adding the fast path.

## 3 Recover correctly after interruption

Write a durability contract before implementing persistence. Specify exactly when an update is acknowledged and what must survive after that acknowledgment. State the storage and filesystem assumptions. Ordinary file writes, rename and process-exit tests cannot establish survival through every disk, host or power failure.

Map the sequence below to the existing native and compound journal mechanisms first. These are required behaviors, not instructions to build replacement storage. Reuse compatible commit, replay and integrity checks; extend only the gaps identified in the audit.

## Commit and checkpoint sequence

Validate an event against the expected stream version. Assign a unique ID and deterministic ordering. Append a framed event with a checksum so an incomplete final write can be detected.

Reach the declared durable boundary before acknowledging success. Apply the event and all invalidations to a consistent committed state. If the implementation uses different ordering, document and prove its recovery rules.

Create a snapshot in a temporary location from a pinned committed version. Verify its contents and hash, then publish it through an atomic manifest. Apply file and directory sync where the supported filesystem requires it.

Retain the prior valid checkpoint and enough journal history to recover. Record snapshot and log retention limits. Never delete the only recovery path while a new checkpoint is incomplete or unverified.

## Restore sequence

Open the newest compatible, complete checkpoint. Verify its hash, schema, semantics and stream identity. Replay committed later events once, in order. Event IDs must make duplicate delivery harmless. Rebuild or validate RPA and dependency indexes, then compare the restored accepted-state digest and behavior to the declared reference.

Detect a torn final event and handle it under the declared acknowledgment contract. Quarantine corruption within committed history instead of skipping it and claiming success. If the latest checkpoint is damaged, try the previous verified checkpoint plus the journal. If recovery cannot establish a trustworthy state, stop answer serving and report the exact boundary lost.

## Faults to inject deliberately

Terminate a fresh operating-system process before and after each commit boundary; during log append; during snapshot write; before and after manifest publication; and during replay.

Replay the same event twice, interrupt recovery and restart it, present out-of-order events, and retry an update whose acknowledgment was lost. Each accepted logical update must appear exactly once.

Test truncated logs, corrupt snapshot bytes, a missing index, incompatible schema versions and a full storage budget. Rebuild a disposable index without changing accepted beliefs.

## Migration and rollback

Make schema migration explicit and versioned. Preserve an untouched compatible copy, validate the migrated state and behavior, then publish it atomically. Test rollback to the previous compatible reader or give a precise unsupported-rollback boundary. Do not overwrite data that the previous version needs.

Keep backups within the authorized environment and access scope. Set limits for event history, snapshots, RPA branches and answer records. Compaction must preserve accepted meaning, provenance needed for retraction and recovery. When limits prevent safe compaction, report the limit rather than silently dropping knowledge.

## 4 Prove behavior across sessions

Freeze the hypothesis, claim wording, generators, datasets, expected outcomes, seeds, code versions and pass criteria before the scored run. Use separate development and held-out evaluation sets. Have an evaluator independent of implementation custody hold the final seeds and expected answers until the implementation is frozen.

## Compare four paths on identical work

Fresh recompute: derive answers from the accepted event history for each query. Report its replay and construction costs explicitly.

Current walk-first: preserve the existing reasoning path and held state. Add only the persistence plumbing needed for the declared recovery comparison, and document that adaptation.

Record-first without RPA: use an ordinary keyed record index with the same validation, persistence and fallback logic.

Record-first with RPA: use the atlas to locate or organize those same records. Hold all other behavior constant so the difference can be attributed to RPA.

## Minimum behavior suite to propose and freeze

Start with 20 independent seeds and 5 successive sessions per seed, each restarted in a new operating-system process. This proposed 100-session minimum samples multiple streams and restart boundaries; it is a bounded coverage target, not proof of permanence. Confirm runtime and budget feasibility before freezing it. If it is reduced, explain the lost coverage before execution.

Include unseen facts and queries, multi-step derived answers, delayed reuse after unrelated activity, reversible corrections, transitive retractions, duplicate events and conflicting evidence.

Exercise open and closed world modes; clean and disputed route verdicts including INADMISSIBLE; additions that invalidate NO or UNKNOWN; changing rules; assumptions and identically named entities in different contexts; and uncommitted guesses.

Ask the same lesson through new instances or compositions, where the frozen lesson contract permits transfer. Compare taught and untaught controls to separate useful reuse from exact-answer lookup.

For every failure point in the recovery protocol, compare the recovered answers and support traces with an independent reference through the acknowledged prefix. Also continue learning after recovery, then restart again.

## Declare what passes

Require zero unsupported or stale fast-path answers, zero cross-context answers, zero guessed facts promoted without acceptance, and exact agreement with the independently computed expected answers for every deterministic case. Require every acknowledged update to recover within the declared failure model and every replayed update to apply exactly once.

These zero-tolerance rules protect the semantics of reuse. Report denominators and failures by category, plus confidence intervals for sampled accuracy. A single counterexample blocks the affected claim. Fix it on development data, freeze a new version, and run a fresh held-out evaluation. Never edit failed examples out of the report.

## 5 Measure useful retention and cost

Show a complete before-and-after trace for each claimed behavior: what was taught, the initial answer, the changed answer, what was saved, the process boundary, the restored answer and any later correction. Exact state equality supports the explanation; the changed and retained behavior is the result.

## Measure the same costs for every path

End-to-end elapsed time for the entire stream, including encoding, updates, dependency checks, invalidation, queries, audits, journal writes, snapshots, restart, reload and pre-answer restore validation. Report query and update latency distributions separately.

Peak and steady resident memory, on-disk log and snapshot size, atlas/index size, cumulative bytes written, reload time and work needed to rebuild discarded indexes.

Common work units with the same definition in every path, such as examined dependency edges and executed rule applications. Keep native counters as diagnostics and never compare different counter currencies as if they were equivalent.

Warm and cold starts; different repeated-query ratios, update/retraction rates, dependency depths and state sizes. Use identical inputs, seeds, machine type, storage, software versions and measurement boundaries.

## Decide whether reuse and RPA help

Compare record-first without RPA against current walk-first to estimate the value of answer reuse. Compare record-first with RPA against record-first without RPA to estimate the extra value of the atlas. Report the full tradeoff if faster queries require slower updates, larger memory or more expensive recovery.

For an initial practical-speed target, propose at least a 10 percent reduction in total elapsed time on a declared repeated-query workload, with a paired 95 percent confidence interval excluding zero improvement. Freeze repetitions and the interval method in advance. This threshold is an engineering choice to avoid celebrating timing noise; it is not a promised result. Report other workloads even if they regress.

A correctness-preserving result below that target can still establish retained behavior. It cannot support the declared speed claim. An RPA result that matches an ordinary index may justify RPA for explanation or branch organization only if that separate benefit is demonstrated.

## Distinguish the outcome types

Retention: an accepted correction or lesson still changes a relevant answer after intervening sessions and fresh-process recovery, without being taught again.

Reasoning and transfer: the retained rule or recipe helps solve new supported cases or compositions. State the domain and compare against an untaught control.

Cooperation: independently developed components exchange a correctly interpreted lesson or state update and produce a useful behavior neither integration path previously demonstrated alone.

Neural growth: require a separate neural-state experiment with functional improvement and controls. Distinguish retrieval assistance from parameter retention by testing unseen cases with retrieval disabled as well as enabled. More files, branches, nodes or saved objects do not establish neural growth.

Separate demonstrated behavior in these categories from preparation. Builds, reviews, clean runs, serialization checks and passing software tests establish readiness for the experiment. Report failed behavior, unsupported claims and negative findings as plainly as positive results.

## 6 Coordinate Claude Codex and DeepSeek

Preserve the completed CNCM reconciliation boundary: the Codex home-base entrypoint is frozen at v0.1; nested vision-next remains a separate research repository; DeepSeek remains a protected alternate. They are not yet interchangeable implementations. [3]

## Proposed ownership before joining state

These assignments are proposed, not accepted commitments. No current DeepSeek lead or session has been verified, and no DeepSeek message or agreement has been obtained. Use a verified project-manager route to establish ownership before dispatch; do not use an old inbox that may start an unbounded paid run.

Claude: own the proposed changes within the existing CAS-RPU organism and PR 248 compatibility. Audit reuse first, then propose the smallest recovery and answer-reuse changes.

Codex: own integration through the frozen CNCM entrypoint and existing adapters. Identify one canonical RPA implementation and entrypoint; link to it instead of copying it. Preserve separate research repositories.

DeepSeek: inspect its own source and describe lesson, repair and reload semantics. Preserve its protected branch. Treat the owner’s source review as necessary before adopting Codex’s interpretation.

Name an independent evaluation custodian before the scored run. Keep final expected answers and seeds away from the implementation authors until the frozen code is committed for evaluation.

## Reconcile meanings before data exchange

Create small conformance fixtures for assertion, explicit negation, unknown, conflict, correction, retraction, rule or recipe storage, lesson promotion and reload. Resolve the existing difference between explicit polarity and a negation predicate. A field-name match is insufficient: each adapter must preserve the meaning and expected answer.

Define an interchange envelope with source engine and version, schema version, context and branch IDs, proposition semantics, provenance and dependency IDs, event sequence and accepted versus proposed status. Reject unsupported values rather than silently coercing them. Keep the source representation available for audit and round-trip checks.

The receiving stream owner validates and accepts an imported proposal. No component writes directly into another component’s authoritative files. An imported lesson gets its own accepted event and retains its origin. Prevent circular replay, duplicate intake and contradictory independent writers.

## Respect the demonstrated limits

🏆 Codex has shown bounded correction from 10 to 9 and reuse of a two-call solver in a fresh process. Treat the nested-prerequisite result as a separate demonstration. 🏆 DeepSeek has shown guarded rule and math repair plus grammar-lesson intake; its reported reload test was within the same process. Require a true fresh-process test before extending that claim. [3]

The proposed synergy is a hypothesis: RPA may find relevant retained state, CAS-RPU may validate and reuse it, and CNCM adapters may carry lessons with preserved meaning. Measure that chain. Do not promise automatic speed, learning or intelligence gains from connecting the components.

## Report model responsibility accurately

Record the exact model and configured reasoning or intelligence setting in this experiment’s manifest. Codex draft and review work is requested at xhigh. Claude Opus 5.5 was recorded for HELM R8, but that does not verify the current PR 248 session. DeepSeek’s current version and setting are unverified. Each operator must report its actual configuration before the experiment; use unknown until verified.

## 7 Follow the work tree and sequence

This proposed tree shows dependencies and alternatives for the experiment. Record each node’s status, verified owner and evidence as work proceeds. HELM-Q1 remains visible without making unrequested changes to its experimental contract.

HELM goal: useful learning, reasoning, retention and cooperation|-- Reuse audit | Claude and Codex | required before new code|   |-- Existing RPA recorded-run worktree | reuse first|   |-- Native and compound journal recovery | reuse first|   `-- PR 248 organism and CAS memory proposal | inspect|-- Targeted changes to existing CAS-RPU | proposed|   |-- One canonical implementation and entrypoint|   |-- Close only demonstrated recovery gaps|   |-- Valid record-first answering|   |   |-- Ordinary record index | required comparison|   |   `-- RPA-assisted lookup | proposed comparison|   `-- Independent multi-session behavioral evaluation|-- CNCM integration | Codex | frozen home-base v0.1|   |-- Shared meanings and single-writer adapter contract|   |-- Codex correction and solver reuse | bounded evidence|   |-- DeepSeek source inspection | protected alternate|   `-- Cross-engine lesson transfer | proposed, unproved|-- HELM-Q1 | existing owner | unchanged pending relevance|   `-- Use verified findings after compatibility review`-- Alternatives | retained for comparison or fallback    |-- Fresh recompute and current walk-first | baselines    |-- Whole-context invalidation | initial safe fallback    |-- Dependency-specific invalidation | after correctness    |-- Broader English, recipe coefficients | parked    `-- Consequence work, register-aware banks, Rust | parked

## Planning estimates and start conditions

These are proposed work-effort ranges, not a scheduled launch or completion promise. Before execution, replace them with calendar start and finish estimates in local Pacific time, PDT on October 6, and report blockers.

Reuse audit and contract: approximately 1 to 2 focused work hours after owners and the authorized environment are available. Identify the canonical modules, reusable journal recovery, exact gaps and compatible contract changes.

Targeted recovery and invalidation changes: provisionally 4 to 8 work hours after the audit and contract freeze. Reduce the estimate where existing code already suffices. Re-estimate before any wider change.

Record-first and RPA comparison paths: approximately 2 to 4 work hours after the safe restore path works. Keep either path independently reversible.

Fault tests, held-out evaluation and report: approximately 3 to 6 work hours after code and methods freeze, plus any authorized queue or runtime delay. Runtime cannot be promised until the budget and blocked operator profile are checked.

The experiment report should identify which branches were implemented, which remain proposed or blocked, and which alternatives were measured. Include actual start and finish times in local Pacific time, model-setting metadata, recorded costs and the evidence supporting each outcome.

## 8 Deliver the evidence and make the decision

## Return these items before claiming completion

A reuse map naming existing files, commits, owners and the canonical entrypoint. For every requirement, say reuse unchanged, extend compatibly or unresolved. Justify any unavoidable new component by a verified gap, rejected reuse options, its minimum scope and rollback.

The versioned memory and interchange contracts, ownership rules, state/branch diagram, commit/restore algorithm and declared durability limits.

Targeted changes to existing tests and documentation, with links instead of copied directories. Preserve existing behavior and protected alternatives. Version the existing contract when compatibility needs it; do not create a parallel project or memory framework.

The frozen evaluation plan, code and data hashes, independent custody record, exact model/settings and environment manifest, reproducible commands and budget accounting.

Per-case behavior traces and aggregate results for all four paths, including failures, confidence intervals, total costs, recovery costs, memory use and discarded or unsupported cases.

A short decision: keep record-first, keep or remove the RPA optimization, retain walk-first, or revise the design. Tie each recommendation to evidence and give the next bounded experiment.

## Stop conditions

Disable the affected fast path if it returns any unsupported, stale, cross-context or guessed-as-fact answer. Preserve failing inputs and traces, diagnose the cause, and repeat the frozen evaluation with a new version after repair. Do not hide a correctness failure behind faster average timing.

Pause the dependent work if accepted state cannot be recovered under the declared failure model, if single-writer ownership is unclear, if an adapter changes meaning, or if the authorized environment or remaining budget cannot support the run. Continue safe analysis and preparation that does not depend on the blocker.

The $250 ceiling and AWS-only restrictions remain. This draft grants no new run budget, credentials, access changes or external outreach. Require coordinated admission, reconcile remaining funds and obtain any mandatory confirmation before paid execution.

## Completion standard

Explain what was learned or retained, which useful answer changed, what survived restart and correction, and what the comparison proves. Separate preparation from demonstrated behavior and state the result’s limits. If RPA adds no measured value, say so and keep the simpler safe path.

## Evidence register

[1] PR 248 revision stream behavior and implementation

Pinned source head: 4377a7da37176a0e9eecb25ad69a85ef89ec96ea. Preserve this original contract when defining the next version.

[2] PR 248 cost report lines 233 to 269

[3] CNCM_WORKSTREAM_RECONCILIATION_20261006.md and CNCM_NEXT_BEHAVIOR_EXPERIMENT_20261006.md in the home-base docs folder record the frozen v0.1 entrypoint and bounded Codex and DeepSeek demonstrations.

[4] Existing RPA worktree and pinned commit identified on page 1. Branch: codex/helm-rpa-recorded-run-20260922. Relevant sources include cncm/rpa_model.py and rpa_recorded_helm.py. Verify the implementation checkout before editing.

[5] Existing CAS memory substrate proposal and design boundaries

---

## Amendment log

### 2026-10-06 — owner decisions on the points the directive left open

Recorded verbatim in substance from the owner's message ("the following speaks for me, so follow as my word"). These bind every document that points at this directive.

1. **Storage.** A folder on an AWS machine is not automatically lasting storage; it may disappear when the machine is terminated. Reuse the existing authorized storage arrangement and verify what survives shutdown and replacement. Every claim states which test was demonstrated: remembering after closing the program is one test; remembering after replacing the machine is a different one.
2. **Single writer.** The reuse audit decides. Choose the existing writer that preserves the required meanings and recovery behavior, with a clear explanation; reuse existing code before proposing another journal. The owner does not pick between journal modules.
3. **Retention limits.** Not "keep everything until measured". Set initial limits on bytes, events and branches before the first run, as conservative engineering choices revised from measurements later. When a limit is reached, stop safely and report it; never silently discard accepted knowledge.
4. **Evaluation custodian.** Need not be a human. A separately controlled evaluation agent may hold the test material. What matters is that the builder and learner cannot inspect or select against the final answers while improving the implementation. This is internal separation of responsibilities and is never advertised as an independent outside audit. The absence of a named human does not stop code preparation.
5. **Ownership.** Claude works on the assigned processor portion; Codex coordinates the integration map; DeepSeek's participation remains proposed until the actual current lead is reached. No one implies an agreement exists or starts another unrelated DeepSeek build.
6. **The 100 sessions.** Keep the design unless the estimate shows a problem: 20 starting conditions, each followed through five fresh processes, not 100 independent starting conditions. The crucial question is what survives each process boundary: a useful correction, its supporting reasons, and any later withdrawal. Opening the program 100 times proves little.
7. **Budget and access.** No new approval is needed for planning. The $250 project ceiling was explicitly approved; $97.59 is the last verified provisional commitment; actual billing still needs reconciliation. The three earlier $1 approvals belong to their specific jobs and do not fund this experiment. Design and estimation continue while the operator access is restored.
8. **Implementation.** Silence is not permission. Already-authorized, narrowly scoped implementation proceeds within its existing boundaries once the contract is clear. Writing tests and running them are separate actions under the AWS-only requirement. Pushing implementation changes, opening a new PR, merging and paid execution each fit the applicable authorization. A separate PR may ease review but must extend the existing project, not create a competing build.

**The result wanted, in the owner's words:** useful knowledge that changes answers, survives restart, and stays correct when its supporting facts change. Every decision stays tied to proving that behavior.

