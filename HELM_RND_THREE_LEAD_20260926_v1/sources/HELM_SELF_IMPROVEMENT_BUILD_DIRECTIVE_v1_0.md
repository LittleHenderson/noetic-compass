# HELM-SI-1: Self-Improving Harness and Neural Growth
## Build directive, ownership, agent delegation, and acceptance contract

**Owner:** Little Henderson  
**Issued:** September 25, 2026  
**Version:** 1.0  
**Implementation lead:** Codex  
**Independent engineering and scientific review lead:** DeepSeek  
**Delivery status:** Directive prepared. No worker has been instantiated, code implemented, experiment executed, or release promoted by the creation of this document.

## 1. Mission

Build HELM toward the ability to identify its own limitations, construct and improve its execution harness, expand or reorganize its trainable neural structure, and learn which modifications produce useful improvements. Eventually, HELM should improve the procedure by which it discovers its next improvement.

The target is a capable learner that increasingly directs its own development, not an external language model that continually rebuilds a passive HELM. A deterministic compiler, optimizer, or test runner may execute HELM's decisions without invalidating native attribution. An external model making the consequential design decision does change that attribution.

Deliver three separately measured capabilities:

| Track | Intended capability | Evidence that does not substitute for it |
|---|---|---|
| Harness improvement | HELM selects, composes, and eventually writes useful changes to its task-execution software. | A hand-edited wrapper, configuration search labeled code invention, or a better diagram. |
| Neural growth | HELM selects useful additions or reorganizations of actual trainable neural structure. | More memory entries, longer prompts, more external-model calls, or unused parameters. |
| Improvement-policy learning | HELM becomes better at choosing or constructing subsequent modifications on unfamiliar failures. | A higher task score alone, a fixed growth script, or greater search spending. |

Preserve the ambition without requiring all three before the first useful result. Do not treat forty CAS entries, an initial controller size, or a starting network width as permanent capacity ceilings. The existing capability-first directive already makes this distinction. [S1]

## 2. Relationship to current work and authority

This is an additive workstream, not a reset, replacement learner, HELM version announcement, or a prerequisite imposed on the ongoing critical-mass training experiment. Preserve active jobs, source trees, original predictions, checkpoints, current scorer rules, and pending readouts. Do not inject harness or architecture changes into a training-amount-only comparison. [S2-S5]

Use the latest owner instructions and execution receipts to establish current truth. The September 22 source reports Q4 as NOT_RUN, while later execution/review documents report six Q4 A/B runs, input use, and no demonstrated overall lesson benefit. Do not repeat the earlier status as current, rename Q4 as HELM, or erase the negative result. These are document-reported facts, not a fresh checkout audit. [S1-S3]

Historical discovery anchors, not claims about today's HEAD:

```text
CAS recovery branch: codex/cas-closed-loop-1-recovery-20260925
Recorded status SHA: 318b22ad01304f80ed0f539420792cc951fe297a
Recorded tested SHA: 8f55cc3a462e438bcf706d7b64ddf9171d218039
Existing integration anchor: research/cas_closed_loop_1/
Existing model anchor:
  cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/
  research/helm_cas_expression_lab/
```

Resolve real successors and current instructions. Never fabricate missing commits. Existing records distinguish local CAS engineering evidence from AWS validation, learned-model benefit, and CAS-specific advantage. Preserve those distinctions. [S4-S5]

Existing explicit owner R&D approvals remain valid within their actual scope. This document does not revoke those approvals or require repeated routine permission. It also does not create unlimited resources, transfer protected-test custody, authorize purchases, or let an editable JSON file manufacture authority. Bind each job to a finite prospective envelope and the applicable existing approval. Reuse no dollar already committed to another lane. Resolve a scope extension prospectively under the existing owner process rather than silently borrowing another experiment's budget. [S2-S5]

Continue authorized lightweight implementation and public deterministic tests while a resource-dependent experiment waits. Do not substitute an unauthorized local neural run for a blocked cloud run. A scientific gate or unavailable custodian blocks only the dependent stage, not unrelated engineering.

## 3. Ownership and agent delegation

### 3.1 Leads

**Codex owns implementation and integration.** Codex assigns source-writing leases, integrates accepted worker commits, maintains the source manifest, runs the permitted build lane, and hands exact commits to DeepSeek. Existing runner authority applies only where it is already granted.

**DeepSeek owns independent public-code review and scientific challenge.** DeepSeek reviews pinned implementations, produces public counterexamples and isolated reviewer-owned probes, checks controls, and reports the smallest corrective delta. DeepSeek does not edit Codex production files or inherit AWS or protected-test authority. This preserves the established role split. [S2-S5]

DeepSeek may write its assigned public review specifications, tests, and reports in a distinct review tree. That is useful independent work, not permission to become a second implementation writer. DeepSeek-authored material does not certify itself as an independently validated measurement standard. Codex must inspect compatibility; the established evaluation custodian controls protected evaluation and frozen scoring.

### 3.2 Mandatory worker allocation

Treat these as work packages. Each lead must instantiate supported subagents, record their actual identifiers, and assign bounded packets. Do not merely list fictional workers. When the interface cannot spawn agents, report `SERIAL_EXECUTION_NO_SUBAGENT_INTERFACE` and execute the packets sequentially under the lead's identity.

| Codex worker | Owned work | DeepSeek counterpart and review obligation |
|---|---|---|
| C1: Contracts and self-description | Read-only architecture/state adapter, typed proposals, model-visible manifest, compatibility map. | D1: Check source identity, reuse, temporal validity, CAS semantics, and capability boundaries. |
| C2: Harness construction | Allowed configuration changes, composition, typed code edits, isolated candidate building. | D2: Public adversarial probes for leakage, fake improvement, unauthorized edits, and unchanged actual execution. |
| C3: Neural structure | One supported growth operator, shape migration, optimizer policy, activation and gradient instrumentation. | D3: Review the mathematics, state mapping, functional claims, and causal-use evidence. |
| C4: Learning and experiment plumbing | Failure corpus, teacher provenance, native improvement policy, comparative runner and metrics. | D4: Freeze public analysis plans; review grouping, budgets, baselines, uncertainty, and native attribution. |
| C5: Lifecycle and CAS integration | Checkpoint/reload, atomic promotion and rollback through existing authority, RPM/branch integration, read-only atlas records. | D5: Probe process isolation, interruption, stale promotion, accounting, cleanup, and replay. |

Codex and DeepSeek leads remain the only integration and review coordinators. Initial concurrency is at most two active workers per lead, four total; this is a proposed limit for this lane, not an expansion of a smaller existing resource limit. Assign later packets in waves. No uncontrolled recursive spawning. Additional workers require a finite registered allocation. Existing HELM training and readout have scheduling priority.

Every writing worker gets a separate branch/worktree and an exclusive file set. Read-only reviewers may share a pinned snapshot. A worktree isolates changes; it is not, by itself, the execution security boundary. Workers do not merge into one another's trees, reset shared branches, force-push, run broad cleanup, or stage unrelated files.

### 3.3 Agent packet and handoff contract

Before a worker starts, record: actual worker and parent identifiers; task ID; source SHA and worktree; read/write allowlists; forbidden paths; dependency hashes; permitted tools; public/secret visibility; resource allocation; expected artifacts; exact acceptance command; and stop conditions. Unknown required fields block that task, not the entire program.

On return, require exact commit/files, commands, observed pass/fail/skip/NOT_RUN counts, reproduction artifacts, costs, unresolved defects, and next action. A lead must inspect a worker result before integrating or endorsing it. Empty status files do not count as a handoff.

Use the established coordination channel after verifying its location. A previously reported path is `D:\tksCAS-worktrees\codex-cas-closed-loop-1\.coordination`; it is a discovery hint, not permission to overwrite another lane. Create a distinct lane subdirectory only where ownership permits. Use unique request IDs, per-agent append-only updates or atomic replacement, and no ACK-of-ACK loops.

Report START, END, each milestone, and active-work updates no later than five minutes. Preserve a stricter existing 120-second worker contract where applicable. Include current work, completed change, blocker, next action, file/commit, and paid/cloud status. A blocked worker returns evidence and releases its allocation; it does not poll indefinitely.

## 4. System design and editable boundaries

Use one integrated loop:

```text
Observe a real failure or inefficiency
  -> diagnose alternative causes
  -> propose a typed modification, including NO_CHANGE
  -> build an isolated candidate from a pinned parent
  -> run permitted development tests
  -> compare checked behavior, retention, and total cost
  -> submit a qualified candidate for independent evaluation
  -> retain or reject through existing authority
  -> learn from permitted development outcomes
```

The existing transaction/commit path remains authoritative. RPM may manage prerequisite experiments; the branch manager may isolate alternatives; CAS-RPA may display recorded alternatives and outcomes. Do not invent a new tick, second state writer, or separate approval hierarchy when existing components suffice. Atlas inspection cannot run a candidate or publish a model. Missing CAS-Ohm or neural measurements remain missing. [S1-S3]

Separate the **candidate-editable surface** from the **evaluation and authority surface**. Initially editable surfaces are admitted harness modules, approved model submodules, and the improvement policy. Scorers, protected data, source-of-truth budgets, credential stores, final-test custody, baseline artifacts, audit anchors, and promotion authority remain outside that surface.

The candidate cannot write the test or scoring rule used to approve itself. Future improvements to evaluators belong to a separately versioned workstream and cannot retroactively validate the candidate that proposed them. Autonomy inside a preauthorized envelope does not require owner approval for every small experiment; expanding the envelope is a different operation.

### 4.1 Minimum logical records

Extend existing schemas rather than duplicating them. Names below describe required concepts, not files proven to exist.

| Record | Required contents |
|---|---|
| `SelfDescription` | Parent source/checkpoint, modules, interfaces, shapes, dtypes, trainable/frozen state, supported edits, observed resource costs, and visibility rules. |
| `FailureObservation` | Task family, input/trace identity, original prediction, actual permitted feedback, measured state, missing measurements, and natural versus injected failure. |
| `ModificationProposal` | Parent identity, hypothesis, alternative diagnoses, target, operation, predicted benefit/cost, proposer identity, dependencies, and allowed experiment. |
| `CandidateBuild` | Exact code diff, generated source, configuration and dependency hashes, architecture/weights/migration lineage, build logs, and isolation identity. |
| `ExperimentReceipt` | Frozen protocol, source/model/data/evaluator identities, all attempted cases, raw predictions, checks, costs, seeds, failures, and disposition. |
| `PromotionRecord` | Expected parent, candidate bundle, qualifying receipts, current authority, atomic activation result, and rollback target. |
| `ImprovementEpisode` | Who diagnosed/proposed/selected/built/evaluated, feedback visibility, costs, outcome, and what the policy learned. |

Use content hashes for identification, but do not mistake a digest recomputable by the candidate for authenticated evidence. Anchor authoritative receipts outside candidate write access using existing custody/integrity mechanisms. Reject stale parents, foreign branches, shape/version mismatches, and fabricated observations.

## 5. Harness buildout

Progress through explicit levels; do not call an early level the final achievement:

| Level | Allowed scope | Required distinction |
|---|---|---|
| H1 | Select existing settings or policies. | Configuration selection, not code invention. |
| H2 | Compose supported typed components into a new executable arrangement. | New composition, not a newly invented primitive. |
| H3 | Generate a bounded AST/DSL patch in an admitted module. | Preserve generated source and demonstrate changed executed code. |
| H4 | Implement a new tool or harness module with a typed interface and independent tests. | The module was absent from the initial executable library. |
| H5 | Modify the policy that proposes future improvements. | Requires the separate meta-improvement experiment in section 10. |

Begin at an actual existing HELM boundary, preferably evidence selection or branch scheduling. Change one mechanism in the first experiment. Keep model weights, task data, scorer, stopping behavior, and inference budget fixed when claiming harness-only benefit. Instrument actual reads and calls, not just displayed choices. Required evidence and runtime obligations cannot be discarded to improve a score.

The initial action interface must include `NO_CHANGE`, `CHANGE_CONFIG`, and `COMPOSE_SUPPORTED_COMPONENTS`. Add `PATCH_ALLOWED_MODULE` and `ADD_TYPED_MODULE` after isolation and behavioral tests are accepted. There must be an eventual path to generated code; do not permanently reduce this goal to a menu of human-written settings.

Generated source is untrusted until built and exercised in a bounded environment. Default to no network and no secrets; use staged, pinned dependencies. Deny filesystem escapes, symlink/hardlink bypasses, import-path shadowing, shell escape, uncontrolled subprocess creation, and writes to tests or frozen artifacts. A Python subprocess under the same unrestricted credentials is not sufficient isolation for arbitrary patches. When the available isolation supports only typed configuration edits, expose only that mode and report the limitation honestly.

First engineering witness: a real harness deficiency produces a failure trace; a proposal creates a candidate; actual execution changes; a public checker measures behavior; rejection or retention is recorded; fresh-process reload preserves the selected version. An externally proposed successful patch proves an engineering loop, not native HELM self-improvement.

Research basis: the Darwin Gödel Machine studies code-modifying agents, empirical testing, and an archive of variants, with foundation-model-assisted generation. Borrow the experimental idea, not its performance numbers or a claim that its underlying neural network grows. [R1]

## 6. Neural-growth buildout

### 6.1 What counts

Count hidden units/channels where those terms apply, trainable parameters, frozen parameters, total versus active capacity, connectivity, and measured runtime/memory separately. An adapter may add trainable capacity without constituting a width expansion of the original layer. Name the actual change.

CAS's forty semantic entries are not a forty-neuron ceiling. A new symbolic register, memory fact, or board description is not automatically a new trainable neural unit. Growth means a versioned change in the executed learnable structure; it does not create physical hardware.

### 6.2 First supported operator

C3 and D3 must inspect HELM's actual architecture and select one compatible operator. Prefer a bounded width expansion of an isolated compatible module, or a trainable residual/specialist module with unchanged external interfaces. Do not assume recurrent, attention, normalization, or custom CAS tensors satisfy a generic widening formula.

Define the operator's mathematical preconditions, parameter map, initialization, external I/O preservation, trainable set, optimizer migration, and rollback. If exact initial function preservation is justified, test it over declared inputs and tolerances. Otherwise label the operation `FUNCTION_CHANGING_GROWTH` and measure initial disruption; do not quietly call it Net2Net.

Net2Net supplies a precedent for function-preserving widening/deepening of compatible networks. Dynamically Expandable Networks supplies a precedent for selective retraining, expansion, and unit splitting in sequential tasks. Neither establishes compatibility with HELM without module-specific work. [R2-R3]

### 6.3 Migration and training requirements

Preserve the untouched parent checkpoint. Rebuild every affected tensor and associated shape contract. Migrate compatible weights and optimizer slots with an explicit map; initialize new optimizer state deliberately. Preserve or explicitly version update count, scheduler, RNG, sampler cursor, precision/scaler state, codec, and configuration. A declared optimizer reset is a new training condition, not an exact continuation.

Function preservation at initialization does not imply identical subsequent optimizer dynamics. Compare optimizer treatment fairly across experimental arms and disclose the change. Never continue a training-length-only study through an architecture mutation.

Apply growth at a declared episode/checkpoint boundary. Invalidate or migrate hidden states, caches, compiled graphs, and shape-dependent runtime state. Do not hot-swap a changed architecture into a suspended parent whose resume contract still assumes the old shapes.

Prove that added capacity is registered with the optimizer, participates in the forward graph, receives gradients under a suitable probe, changes through actual updates, and affects behavior when tested. Avoid zero-initializing every path so that new capacity cannot learn. Nonzero gradients are a trainability check, not sufficient proof of useful growth.

Compare learned expanded models with the original architecture given additional training. Declare whether the primary comparison matches compute, time, or exposure; do not claim that equal update counts imply equal compute across different widths. Later compare with a larger model trained from scratch and with a fixed/random admissible growth policy when claiming an advantage from adaptive growth.

Retain both capability and efficiency candidates where appropriate. A worthwhile stronger model can cost more. A smaller, pruned, or better-routed model can also be an improvement. No-growth and retrain-existing-capacity must remain eligible actions.

## 7. Teach HELM to direct improvement

C4 builds an improvement-episode corpus from permitted training/development failures and modifications. Include successful changes, harmful changes, unsuccessful searches, stale proposals, inappropriate growth, useful no-change decisions, and cases where additional training or better data beats expansion.

Use a progression that fits the existing learner: predict the failure class; rank permitted remedies; select a target and edit size; compose a typed candidate; later generate a bounded patch or new module. Do not require unrestricted source generation before the first native decision. Do not quietly replace the existing HELM learner with an external LLM.

Codex/DeepSeek may supply authorized teaching examples. Record teacher identity, model/version where available, exact contribution, and visibility. Training-side reference answers may generate permitted labels; reference implementations and hidden targets must not become inference-time answer channels. Keep native, deterministic, and externally assisted results separate. [S1-S3]

For native attribution, retain HELM's original output and the action grammar exposed to it. Record validator rejections and every fallback. If HELM chooses an invalid action and a script selects a useful replacement, credit the script with that replacement. A fixed rule such as “grow after five failures” is automation, not a learned growth policy.

At native evaluation, freeze the designated improvement policy and its initial permitted memory. Disable external teacher/design assistance. Use unfamiliar failure structures or task families, not merely renamed copies. Compare against a strong simple policy and a matched admissible search baseline. A reduction in dependence on teacher intervention is measured, never assumed.

Do not confuse task answers with modification decisions: an external tool may compile a HELM-proposed patch, but an external model selecting the patch is assisted design. Keep provenance at each consequential step rather than giving the whole episode one flattering label.

## 8. Phases and promotion gates

| Phase | Work and dependencies | Exit evidence |
|---|---|---|
| SI0: Reconcile | Verify latest instructions, source, jobs, budgets, custody, reusable code, and actual worker interfaces. | `SOURCE_MANIFEST`, ownership leases, dependency map, exact first commands; no invented baseline status. |
| SI1: Instrument | Build self-description, shadow proposals, isolated candidate identity, public fixture, and lifecycle hooks. Depends on SI0. | Baseline behavior preserved when disabled; real observations; unknown fields stay unknown; candidate cannot mutate parent/evaluator. |
| SI2: Harness | Implement H1/H2 and the bounded H3/H4 path as prerequisites permit. Depends on SI1. | One complete candidate-build/test/reload episode; code-generation level and author honestly identified. Empirical benefit is a separate result. |
| SI3: Growth | Implement one real expansion operator and lifecycle tests. Depends on SI1, not on a favorable SI2 result. | Shape migration, activation, gradient/update, reload, rollback, and a bounded comparison when resources permit. |
| SI4: Native director | Train/evaluate HELM's modification decisions using SI2/SI3 interfaces and development episodes. | Native held-out harness/growth decision results versus simple controls, with teacher assistance disabled and full attribution. |
| SI5: Combined operation | Combine individually characterized mechanisms. Depends on accepted relevant SI2-SI4 evidence. | Baseline / harness-only / growth-only / both comparison; retained skills and combined costs reported. |
| SI6: Meta-improvement | Allow changes to the improvement policy through the same isolated candidate process. Depends on SI4 and stable lifecycle. | A newer policy finds better subsequent improvements on new families at matched total search budgets. |

Source/integrity gates are mandatory. Positive empirical results are not promised. A completed negative experiment exits as negative with preserved artifacts, not as a reason to loosen scoring. SI2 and SI3 engineering can proceed in parallel after SI1. Current critical-mass jobs retain priority; their readout is an input to neural-experiment design, not a reason to postpone isolated contracts and tests.

Use existing project statuses plus explicit claim tags: `ENGINEERED`, `EXECUTED`, `ASSISTED_GAIN`, `NATIVE_HARNESS_GAIN`, `NATIVE_GROWTH_GAIN`, `META_POLICY_GAIN`, `INCONCLUSIVE`, `NO_GAIN`, and `PROMOTED`. Map tags into the existing ledger; do not install a second release authority. A promotion also requires all applicable non-empirical controls.

## 9. Evaluation and minimum acceptance tests

Separate engineering conformance from empirical improvement. Public deterministic probes may run before neural experiments where authorized. A test not executed against the real relevant path stays NOT_RUN.

### 9.1 Scientific protocol

Before outcome access, freeze task-family grouping, train/development/final split, permitted feedback, primary endpoint, smallest worthwhile effect, retention margins, seeds, sample-size rationale, budget, candidate limit, evaluation-query limit, and stopping rule. Use existing accepted thresholds where applicable; any amendment is prospective under a new experiment identity. Do not invent favorable numbers after results. [S1-S3]

Evaluate raw model accuracy, accepted-output accuracy, coverage, failed/invalid proposals, prior-skill retention, structural transfer, actual added-capacity use, task latency, peak memory, and total development/inference cost. Count rejected candidates, failed jobs, validators, teachers, repeated context, training, and evaluation. Include unfinished and difficult cases in the specified denominators.

Use paired analysis respecting task families and seeds. Report uncertainty and exploratory versus confirmatory status. Do not claim robust generalization from one favorable seed or structural transfer from renamed training instances.

Keep development selection separate from independent promotion evaluation. A protected evaluation queried repeatedly becomes an information source, even if only scores are returned. Bound queries and keep final-test access with its existing custodian. Any later policy trained from released final-test feedback must treat that feedback as development history; use fresh held-out families or a separately declared predict-then-update protocol for subsequent claims.

### 9.2 Mandatory checks

| ID | Requirement |
|---|---|
| SI-T01 | Disabled and shadow modes preserve authoritative baseline behavior, with instrumentation overhead disclosed. |
| SI-T02 | No future outcomes, hidden targets, protected answers, or evaluator-only fields enter proposals. |
| SI-T03 | Stale parent, wrong branch, incompatible shape/schema, or wrong checkpoint proposals are rejected. |
| SI-T04 | Candidate edits cannot modify source-of-truth evaluator, authority, budget, audit anchor, or baseline. |
| SI-T05 | Execution isolation rejects path/link/import/process escapes and unauthorized network access appropriate to the exposed edit mode. |
| SI-T06 | Required evidence, typed obligations, and existing execution/commit semantics survive harness edits. |
| SI-T07 | Actual model reads/tool calls/compiled code match the accepted candidate, not merely the display. |
| SI-T08 | A new H3/H4 artifact was generated, built, and executed; configuration changes are not mislabeled source invention. |
| SI-T09 | A wrong, stale, harmful, or no-benefit modification is rejected or retained only in a non-promoted research archive. |
| SI-T10 | Growth changes real declared structure; parameter/unit counts and trainable/active distinctions reconcile. |
| SI-T11 | All affected tensors, caches, interfaces, and runtime state obey the migration contract. |
| SI-T12 | Function-preservation claims meet stated preconditions/tolerances; unsupported claims fail rather than silently degrade. |
| SI-T13 | Added capacity is optimizer-visible, receives suitable gradients, updates, and participates in forward execution. |
| SI-T14 | A contribution probe and appropriate ablations distinguish useful capacity from dead or redundant additions; ablation degradation alone is not proof of a good growth policy. |
| SI-T15 | Checkpoint, optimizer policy, RNG/cursor, and configuration reload match the declared continuation law. |
| SI-T16 | Crash injection at build, training checkpoint, receipt, promotion, and activation boundaries preserves an unambiguous accepted version. |
| SI-T17 | Atomic expected-parent promotion rejects stale/concurrent candidates; rollback restores a complete compatible bundle. |
| SI-T18 | Exact parent/caller resume is preserved where applicable; changed architectures activate only at valid boundaries. |
| SI-T19 | Replay detects edited/truncated receipts; candidate-recomputed hashes cannot forge authoritative acceptance. |
| SI-T20 | Native evaluation cannot obtain external design choices through fallback or undeclared teachers. |
| SI-T21 | Harness-only and growth-only comparisons change only their declared factors and report real costs. |
| SI-T22 | Growth comparisons include the original model with additional training under the declared primary budget rule. |
| SI-T23 | Policy comparisons preserve allowed actions, information, starting targets, and search budgets; failures are not dropped. |
| SI-T24 | Resource caps, one-GPU coordination, zero automatic retries, cancellation, and cleanup operate on failure paths. |
| SI-T25 | Atlas views remain read-only; display/layout is never evidence of execution or exact return identity. |
| SI-T26 | Promotion checks prespecified benefit/retention criteria and fresh-process behavior; inconclusive results do not auto-promote. |

These are requirements, not 26 claimed passes. Reuse equivalent existing checks and record coverage rather than inflating test counts. A public probe is not a protected final test. Exact event replay and bitwise neural regeneration across arbitrary hardware are different claims; declare tolerances and supported environments. [S1]

## 10. Proving improvement of the improver

After a native policy exists, compare policy P0 with candidate P1 on new improvement problems. Give each a clone of the same target-model/harness starting state, the same permitted observations, action interfaces, task families, external-tool access, and total search budget. Freeze the experimental endpoints before evaluation.

Measure the proportion of independently useful modifications, checked task improvement per total search cost, cost to reach a declared target where estimable, harmful-change rate, and performance on unfamiliar failure classes. Report censored/unsuccessful searches rather than hiding them.

A P1 advantage caused solely by more teachers, a larger hand-supplied edit library, more attempts, or easier starting targets is not evidence for the claimed policy improvement. Those are separate factors. Keep learned policy changes, persistent memory changes, and proposal-space changes identifiable; add ablations when the distinction is essential to the claim.

The meta-policy may propose a successor to itself, but it may not certify that successor, raise its own resource allocation, grant itself new permissions, disable evaluation, or transfer protected custody. Policy candidates use the same build/evaluate/retain path as other candidates.

Research basis: Hyperagents studies an editable meta-level modification procedure as well as task-agent modification. It motivates this distinct experiment; it does not demonstrate HELM's capability or guarantee accelerating progress. [R4]

## 11. Integration, resources, and failure handling

Represent a promoted system as a compatible versioned bundle: harness, model architecture, weights, optimizer/continuation state when relevant, codec, normalizer, memory schema, and policy. Publish only through the existing authority using expected-parent checks. Never partially activate a new harness with an incompatible old checkpoint.

Maintain immutable parents and candidate lineage, including rejected and negative-result artifacts within declared storage limits. Archive content may be compacted prospectively under retention rules; never erase adverse results to improve the reported history.

For every paid or resource-gated job record the provider, runner, machine/region if relevant, current price evidence, wall/work/token/memory limits, total cost cap, already committed spending, evaluation limit, watchdog, cleanup destination, and retry count zero. Child budgets are subdivisions of the parent envelope, not additional money. Include coordinator/reviewer/API costs where charged. The existing one-GPU-global restriction and incumbent-job priority remain in force. [S2-S5]

At 80% of an applicable lane cap, stop discretionary work and protect readout/cleanup reserve as the existing execution directive requires. Stop immediately on a proven custody breach, source mismatch, evaluator tampering, unexplained nonfinite training behavior, ineffective resource enforcement, or corrupted activation. Preserve evidence, clean up owned resources, and return the exact blocker. Do not conceal the fault with automatic retries or a fresh favorable seed. [S2]

Claude or another established custodian does not lose protected-test custody because it is unavailable. Codex and DeepSeek continue public work and report `PROMOTION_EVAL_BLOCKED_BY_CUSTODY` for the dependent final evaluation. Do not read secrets or impersonate an unavailable runner.

## 12. Delivery layout and review cycle

First map these logical destinations to the actual repository and reuse equivalents. Suggested new namespace, only when none exists: `<HELM_ROOT>/research/helm_self_improvement/`. DeepSeek's public probes/reports live in its separate review worktree. Neither location is claimed to exist now.

The minimum deliverables are: source/compatibility manifest; actual agent and write-lease registry; extended typed schemas; executable candidate pipeline; one harness operator; one growth operator; migration and lifecycle tests; improvement-episode dataset specification; native-policy training/evaluation path; frozen experimental plans; source-bound receipts; rejection/retention evidence; read-only atlas integration; and a concise current status.

Per milestone: worker commits; Codex integrates and runs focused tests plus `git diff --check`; DeepSeek reviews the exact integrated SHA and public evidence; Codex addresses material defects; DeepSeek re-reviews only the changed scope. Broad philosophical review and cosmetic issues must not replace working code or delay unrelated tasks. BLOCKER/MAJOR findings need concrete evidence, impact, and the smallest fix. No self-certification as independent review. [S2-S3]

Return this format:

```text
STATUS: ACTIVE | BLOCKED | MILESTONE_COMPLETE
PHASE / TASK / ACTUAL AGENT IDS:
SOURCE: branch, full SHA, worktree, checkpoint
CHANGES: exact files and mechanism
EXECUTED: exact commands; pass/fail/error/skip/NOT_RUN
RESULT: engineering-only | assisted | native | comparative | meta-policy
REPRODUCTION: receipt and artifact identities
REVIEW: exact reviewed SHA; open BLOCKER/MAJOR findings
RESOURCES: allocated/used/remaining; jobs; cleanup
LIMITATION: what the evidence does not establish
NEXT: one exact unblocked action
```

### Immediate orders

**Codex:** reconcile the live project without interrupting incumbent work; publish actual worker IDs and leases; implement the smallest missing SI1-to-SI2 connection; prepare C3's compatible growth seam in parallel when source ownership permits. Do not return only another plan.

**DeepSeek:** assign public review packets; freeze the first experiment's scientific question and controls with Codex before outcomes; review SI1 contracts and the first integrated candidate; prepare independent migration and failure probes. Do not write a competing HELM implementation or revisit unrelated settled audits.

**Both leads:** build toward demonstrated capability, not an ever-growing scaffolding project. The first concrete target is one source-bound modification episode with honest authorship, changed real behavior, checked evidence, and restartable state. The eventual target is HELM making better such decisions on its own.

## Source notes

These sources establish prior constraints and research precedents. All new interfaces, assignments, phase gates, and test IDs above are proposed requirements, not reported implementation facts.

- **S1:** `CAS_Helm_State_Conditioned_Implementation_Directive_v1_0.md`, September 22, 2026; sections 1-3, 6-7, 10-14. Library source `file_00000000574081fdb21da6ea622fb7f5`, version 1.
- **S2:** `CODEX_CAS_HELM_EXECUTION_DIRECTIVE.md`; ownership, recovery, resource, reporting, and HELM R&D sections. Library source `file_000000001710823092dd4b5571d9b31a`, version 1.
- **S3:** `DEEPSEEK_CAS_HELM_REVIEW_DIRECTIVE.md`; independent review, claim separation, matched controls, negative-result preservation, resource and custody sections. Library source `file_000000006eec81f59ce0a3087e053744`, version 1.
- **S4:** `CODEX_COMPLETE_HELM_CAS_AWS_DIRECTIVE.md`; scope, source pins, engineering/learned claim boundaries, and current-lane controls. Library source `file_00000000eac081f581bb8c3d1b4031b6`, version 1.
- **S5:** `DEEPSEEK_REVIEW_HELM_CAS_AWS_DIRECTIVE.md`; source pins, review boundary, prefix fairness and continuation requirements. Library source `file_00000000eebc81fdb7e1de32d4bfaffa`, version 1.
- **R1:** Zhang et al., *Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents*, arXiv:2505.22954v3, revised March 12, 2026. Author abstract verified September 25, 2026.
- **R2:** Chen, Goodfellow, and Shlens, *Net2Net: Accelerating Learning via Knowledge Transfer*, arXiv:1511.05641v4, April 23, 2016. Author abstract verified September 25, 2026.
- **R3:** Yoon et al., *Lifelong Learning with Dynamically Expandable Networks*, arXiv:1708.01547v11, June 11, 2018. Author abstract verified September 25, 2026.
- **R4:** Zhang et al., *Hyperagents*, arXiv:2603.19461v1, submitted March 19, 2026. Author abstract verified September 25, 2026.
