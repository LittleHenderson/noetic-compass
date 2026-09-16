# Complementary Alternating Teaching for Recurrent CJTs v0.1
## Builder directive: CAS_COMPLEMENTARY_TEACHING_001

**Concept owner:** Little Henderson.  
**Parent work:** CAS_RDCJT_001 and RPM_CFC_CONSTRUCTOR_001.  
**Status:** PROPOSED_CANDIDATE_ADDENDUM; implementation and learning benefit unverified.  
**Immediate deliverable:** an opt-in training-schedule extension, actual learner bindings, tests, retained observations, and one future costed execution request.  
**Execution boundary:** preparation only. No model loading, neural computation, provider call, reservation, paid launch, or accepted-model mutation is authorized by this document.

> Train one continuing learner on the component decisions and the complete task. Use recurrent computation in both. Preserve its learning state when changing teaching modes. Measure whether the skills accumulate instead of replacing one another.

## 0. Finish the current work; do not substitute this experiment for it

The owner reports that CAS_RDCJT_001 is still being implemented and has no results yet. Treat that as reported status, not a verified repository or provider observation. This addendum does not assert that recurrence works or that the two methods have already demonstrated complementary benefits.

Leave that work's source freeze, package, data, initial comparison, authorization, active processes, ledger operations, and output locations unchanged. Prepare this extension in an isolated candidate location against a pinned interface. Incorporate the finished recurrent implementation as a versioned dependency when doing so cannot disturb its current work. Do not delay completion of the current deliverable to install this addendum.

This directive scopes the ordinary non-neural implementation of the extension, including its real learner binding, opt-in worker dispatch, tests, and packaging. Do not stop after every routine substep to ask permission. Reuse the lifecycle rather than build another launcher service; reuse does permit a new versioned experiment configuration and entrypoint. Return once with the runnable preparation and one unsigned execution request, or earlier only for a concrete contradiction or missing capability outside scope.

## 1. Source basis and proposed additions

| Source | What is retained | What it does not establish |
|---|---|---|
| S1: Recurrent Neural CJT v0.1, CAS_RDCJT_001, sections 3-4, 9-14, 17-18 | Shared recurrent core; original-input reinjection; transient per-question state; final-pass loss; CFC course; depth and cost accounting; preserved evidence | A measured recurrent-CJT benefit; the efficacy of this new teaching schedule |
| S2: RPM-Guided CAS PCBA Learning Constructor v0.1, sections 7 and 10-12 | CFC within/across/return teaching, maintenance, continuing learner state, separate planner/student, qualification and exact parent return | A proven optimal maintenance ratio or an already effective automatic lesson selector |
| S3: Deductive Logic in Language Models: Horizontal vs Vertical Reasoning, Maltoni and Ferrara, arXiv:2510.09340v2, abstract and introduction | Distinction between explicit intermediate-token reasoning and internal layer-wise reasoning; a source for investigating complementary instruction | CAS validation; proof that a shared recurrent CJT equals their vertical architecture; an alternating-CFC recipe |
| S4: Cube Verified-Step Teaching Schema v0.1, sections 2-9 | Checked component decisions, grounded contrasting errors, separate public exercises and teacher targets | Permission for an inference-time teacher to construct the learner's final answer |

**Everything normative below is a proposed CAS-specific extension.** The extra practice unit, three comparison conditions, fixed alternation, reference counts, and result rules are not measured findings from these sources.

Use the latest numerically connected six-face/CFC path described by S2. Older presentation-only documents are interface history, not grounds for downgrading a later implementation. Confirm actual current signatures and state identities once; do not reopen unrelated historical audits.

## 2. The precise hypothesis

At a fixed allowance, alternating checked component practice with independent whole-task practice may help a recurrent learner combine useful skills while retaining earlier ones.

Keep three questions distinct:

1. **Complementary content:** does some additional component practice help more than spending those same updates entirely on whole-task practice?
2. **Teaching order:** does component-then-whole block ordering help more than mixing the exact same component and whole examples?
3. **Retention:** does the complete learner keep component skills and earlier capabilities rather than merely trade one weakness for another?

A method improving one task does not establish that it trained a physically separate neuron group. This candidate uses the current permitted parameter group throughout; substantive component isolation would require separate evidence.

## 3. Two independent controls, not two rival architectures

**Teaching mode controls the question and corrective target. Recurrent depth controls how much internal computation precedes that prediction.**

Define three training roles:

| Role | Meaning |
|---|---|
| COMPONENT | A checked subproblem that supports an application, such as direct versus indirect containment or the relevance of one constituent |
| WHOLE | A complete application answered from permitted evidence without supplied component answers |
| MAINTENANCE | Practice from permitted earlier training families, not the retention audit |

All three roles use the same pinned recurrent student and the same current scoring path. The full existing six-face/CFC foundation remains in place. These role names are scheduling metadata, not new Noetics, neural modules, cube faces, or a new model-visible hint.

Do not assign one fixed recurrent depth exclusively to COMPONENT and another exclusively to WHOLE. That would confound instructional emphasis with computational allowance. Each round's inherited depth applies to every batch in that round, including maintenance.

This is not a new autoregressive reasoning-trace interface. No model-generated step sequence is fed back between independent questions in this version. Such a mechanism would require its own input/state and evaluation specification.

## 4. Preserve the recurrent core and the learning state

Reuse S1's implemented compute profile and its configured constants without changing the recurrence equation, encoder, token embeddings, normalization, final readout, permitted parameter group, or loss. Do not add heads, trainable adapters, memory slots, depth-specific parameters, a preference model, MCTS, a learned router, or gradient-surgery machinery.

The current candidate's allowed weights receive corrections in both teaching modes. Keep one optimizer instance and its accumulated state for the entire course within each learner. Keep any learning-rate schedule on one global update counter. Do not restart warmup, zero momentum, swap checkpoints, or create a different learner at a mode boundary.

Conversely, reset the temporary latent state before each independent question. Teacher answers, guided hidden states, and answer-bearing caches do not travel from COMPONENT to WHOLE. Learning in the weights is the intended carryover; a hidden worked solution is not.

Use separate model objects, optimizers, counters, buffers, and checkpoint directories across experimental conditions. The planner stays frozen. No accepted model or durable global Bias is updated by a candidate course.

## 5. Keep the full CFC foundation and add one small practice unit

Do not reduce the six-face program to the old eight-record fixture. Preserve each round's current teaching foundation:

| Existing phase | Decisions | Batch sizes | Updates |
|---|---:|---|---:|
| WITHIN_CUBE | 28 | 8, 8, 8, 4 | 4 |
| ACROSS_FACE | 12 | 8, 4 | 2 |
| RETURN_TO_CUBE | 8 | 8 | 1 |

After RETURN_TO_CUBE, add a **complementary practice unit of two batches of eight**. Then perform the existing maintenance batch of eight. This placement preserves the within/across/return ordering and puts maintenance after the added practice.

For the alternating condition, the unit is:

```text
8 COMPONENT questions -> one update
8 WHOLE questions     -> one update
8 MAINTENANCE items   -> one update
```

The COMPONENT update must complete before the WHOLE forward computations begin. Merely placing both sets in one accumulated-gradient update would not implement this blockwise alternation.

This introduces **16 extra decisions and two extra updates per round**. It is a new schedule profile, not a silent extension of the current experiment's budget.

### Reference course, explicitly proposed

| Scope | Target decisions | Maintenance decisions | Total decisions | Updates |
|---|---:|---:|---:|---:|
| One enhanced round | 64 | 8 | 72 | 10 |
| Sixteen enhanced rounds | 1,024 | 128 | 1,152 | 160 |
| Increment over S1's course | 256 | 0 | 256 | 32 |

There remain 16 complete CFC rounds plus 16 supplemental practice units. Do not call the supplement an extra seven-stage cycle. Sixteen rounds is a chosen pilot allowance, not a proof of sufficiency or an optimal dose.

If the current authoritative CFC profile differs from S1, preserve its exact identity and record a compatible derived schedule before freeze. Do not silently overwrite it to force these counts. A genuine interface incompatibility should be named precisely; ordinary scheduler integration remains within this assignment.

## 6. Construct connected lessons without constructing the answer for the student

For each round, prepare eight public whole-task exercises and eight corresponding component exercises from the permitted support families. There is one public relevance link from each component exercise to its parent application. Each small question checks a real part of the larger task, not necessarily every step needed to solve it.

Use current supported task profiles and reference semantics. For a complete-list parent, a component can ask REACHED_VIA about a publicly enumerated candidate. For a shared-part parent, component evidence can concern membership in each whole. For a route parent, it can concern a supported local connection. Do not invent a universal mapping where the current interface cannot express one.

The initial intended distribution is two parent applications per support cube across four support families. Freeze actual operation, candidate, direct/indirect/absent, list-length, and choice-position coverage in the dataset manifest. This allocation is illustrative until compiled against the current supported material; it is not permission to fabricate missing facts or silently expand task semantics.

Construct public questions, candidate choices, ordering, and identities without private targets. The teacher subsequently checks their answers. Do not choose the candidate to inspect solely because the answer key says it is a true part. Include supported inclusion and exclusion questions. Detect empty versus unknown inventories and ambiguous reference cases under existing rules.

**Example, authored for explanation:**

```text
A directly contains B and C.
B directly contains F.
D directly contains E.

COMPONENT: How is F related to A?
Teacher correction: indirectly, through B.

WHOLE: What does A directly contain?
Teacher correction after prediction: B and C.
```

The WHOLE input includes the permitted graph but no sentence saying which items were correct in the preceding component exercises. The teacher trace can explain the relation during instruction; its target-bearing fields remain separate from the subsequent unassisted query.

If two records ask the same graph/operation/named-argument question, record the duplicate exposure even if their role labels, IDs, or choices differ. A component question repeated as a whole question is not a new test. Retain semantic identity separately from presentation identity.

All related faces, analogies, subquestions, revisions, and renderings stay with their root family. Training on a component of a parent is legitimate instruction; testing a renamed copy of that family is not new-family transfer.

## 7. Three focused conditions, one common recurrent architecture

The new comparison uses three conditions, each with the same full CFC foundation and maintenance. Do not add a new one-pass architecture arm or retrain the planner in this study.

| Condition | Supplemental unit | What it tests |
|---|---|---|
| ALT_COMPONENT_WHOLE | A[0..7], then B[0..7], two homogeneous batches | The proposed complementary block schedule |
| MIXED_SAME_ITEMS | The exact same eight A and eight B items, in two mixed batches of four A/four B | Whether block order/batch grouping adds value beyond those same teaching examples |
| WHOLE_SUPPLEMENT | B[0..7], then the same B[0..7] again | Whether component practice helps more than spending the same supplemental budget on complete tasks |

A denotes a component item; B denotes its paired whole application. After a frozen public permutation of the eight pairs, MIXED uses pairs 0-3 in its first batch and pairs 4-7 in its second, interleaving A and B within each batch. ALT uses all A then all B. WHOLE_SUPPLEMENT repeats B in that same pair order. Every condition receives two supplemental updates and sixteen supplemental decisions per round.

ALT versus MIXED isolates **mode ordering and batch grouping together**, not pure ordering independent of grouping. ALT versus WHOLE changes target composition and whole-question exposure, not only order. WHOLE_SUPPLEMENT is not devoid of component teaching: it still receives the common CFC foundation. Do not call it an entirely final-answer-only model.

Within every seed, use the same pinned initial weights, optimizer initialization, encoder/tokenizer, recurrent profile, learning rate schedule, CFC records, maintenance, rendering rules, and allowed inputs. ALT and MIXED must have byte-identical supplemental examples as a multiset. Differences in their learned checkpoints are not pre-accepted benefits.

Reference training seeds: 101, 202, 303. Match the provenance rule for initialization, not the winning test score of the current experiment. If all starts use one incumbent, describe seed repeats as training-order/rendering repetitions, not independent weight initializations.

These three conditions are the proposed minimum for the two separate claims above. If a costed request omits MIXED, it may test component supplementation but may not claim an alternating-order advantage. A reduced comparison requires a named pre-execution profile amendment, never silent omission after a failed run.

## 8. Use recurrence in every mode, with explicit compute accounting

Inherit S1's per-round depth sequence:

```text
1,2,4,8, 2,4,8,1, 4,8,1,2, 8,1,2,4
```

The companion reference schedule assigns cyclic offsets 0, 1, and 2 to seeds 101, 202, and 303, respectively. All three conditions within a seed receive the same sequence. This offset mapping is a new explicit scheduling proposal. It does not modify the current experiment.

Each depth receives four complete enhanced rounds. Every batch uses the round's depth. Keep the existing final-pass supervised loss and full backpropagation through the declared unroll. One batch performs one optimizer update, not one update per latent pass. Intermediate observations do not create extra targets.

| Planned training quantity | Per condition/seed | Nine courses: three conditions x three seeds |
|---|---:|---:|
| Teaching decisions | 1,152 | 10,368 |
| Optimizer updates | 160 | 1,440 |
| Batched core forward calls | 600 | 5,400 |
| Sample-level core passes | 4,320 | 38,880 |

Derivation: ten batches and 72 decisions per round; the depth sequence sums to 60. Thus 10 x 60 = 600 batched core calls and 72 x 60 = 4,320 sample-core passes.

These are **planning arithmetic only**. Backward computation, different input lengths, encoding, monitoring, final readouts, checkpoint reload, and evidence collection are additional costs. Matched call/update counts do not prove identical FLOPs or wall time. Reuse existing timing/memory counters and report actual values per mode and condition.

Do not import an older 64-update budget or silently loop its launcher to reach 160. Implement a declared candidate budget profile through the existing permitted mechanism. Bind the total job time, memory, storage, and reservation once in the future request. No current AWS price, account state, balance, or dollar ceiling is assumed here.

## 9. Make the transitions real, not metadata only

Extend compatible current modules rather than create a parallel trainer. Proposed logical interfaces, to be mapped to actual repository signatures:

```text
compile_complementary_course(cfc_manifest, checked_pairs, maintenance, profile)
    -> immutable schedule and per-condition data references

run_complementary_course(candidate, optimizer, schedule, observer, budget)
    -> training receipt and retained checkpoints

evaluate_complementary_course(checkpoint, public_panel, fixed_compute_profile)
    -> answer-free prediction rows; targets scored separately afterward
```

The common execution sequence is:

```text
Pin source/data/model/teacher/profile identities
Build separate candidate state per condition and seed
Scope allowed parameters; take the before snapshot
For every planned batch:
    verify sequence/cursor and remaining root budget
    encode only allowed public inputs; reset each question's latent state
    execute the declared recurrent passes and retain the final prediction
    release the checked target to the training loss
    backward once; update once; record update identity and exposure
At fixed observation points: evaluate without updates and restore training mode
Take after snapshot; calculate containment
Save/reload the required checkpoints and regenerate the report from raw rows
```

The method switch changes the next examples, not the model object or optimizer. Any scheduler state affecting randomness, batch order, precision, or learning rate persists and is checkpointed. An interruption restores the complete compatible bundle and cursor under the existing recovery policy. It cannot silently repeat an already recorded update or call a lost prediction an update.

No code snippet here asserts an existing callable signature. Verify the actual adapters once, implement the missing opt-in connections, and list them in one TASK_BINDINGS document.

## 10. Minimal record extensions

Reuse equivalent fields and serialization. Do not duplicate graphs or checkpoints in each row.

**ComplementaryProfile:** source recurrent-profile identity, training-mode policy, conditions, round/batch/depth schedule, optimizer profile, dataset/family/teacher identities, parameter scope, budgets, monitoring and final-analysis rules, activation state.

**TeachingPair:** root family, public graph/view identity, component exercise reference, whole exercise reference, public relevance relationship, semantic-question keys, separate teacher-target references, declared assistance.

**TrainingEvent:** condition/seed/round/phase/batch, actual sample IDs, public-input identities, current weight/optimizer/cursor identity, requested and completed depth, actual predictions and scores, target-release position, loss, actual update identity, timing scope, failure or incomplete state.

**SkillObservation:** checkpoint identity, monitor identity and split role, compute depth, component/whole/old-skill counts and raw predictions, per-operation breakdown, completed exposure, and interpretation status. Observed correctness is not evidence about isolated neuron groups.

**HandoffState:** current model/optimizer/scheduler/RNG state identities, course and data identity, last committed update, next batch cursor, completed phase counts, remaining root budgets, and evidence location. No cross-question latent answer state is required for training-course continuation.

Schema/profile fields are candidate contracts, not an assertion that they already exist. Keep absent measurements unavailable. Simulated events retain explicit mode and zero actual neural presentations and updates.

## 11. Teach repeatedly; observe without moving the goalposts

Deliver the declared sixteen-round minimum. Early wrong answers receive corrections; they do not trigger a mastery failure or an automatic reallocation of teaching. Stop early only for numerical/contract failure, hard resource limits, or an explicit external cancellation. Preserve unfinished exposure as TEACHING_INCOMPLETE.

Use one fixed development-monitor battery containing component, complete-task, and earlier-skill questions. It is separate from training and final audit material. Its exact counts, public selections, and timing budget are frozen before execution.

Observe initially and in rounds 4, 8, 12, and 16 at four points: after the common RETURN_TO_CUBE phase (before the supplement), after supplemental update 1, after supplemental update 2, and after MAINTENANCE. Use corresponding points for all conditions. This is 17 monitor snapshots per learner including the initial snapshot.

Each snapshot is read-only: fixed K=8, no teacher prefixes, no optimizer operation, and no mutable hidden context left for the next training batch. Preserve/restore any training RNG state that monitoring would otherwise consume, or use an independent evaluation RNG. Charge all monitoring work to the job.

These observations are **record-only** in this version. They do not choose checkpoints, change ratios, stop for success, pick pass counts, or extend the course. Their purpose is to reveal patterns such as component improvement followed by whole-task improvement, or improvement in one view accompanied by regression in another.

Do not label one phase's before/after difference a proven mechanistic cause. It is an observed training trajectory under the declared sequence. The matched final comparisons supply the stronger experiment-level evidence.

## 12. Test independent answers and retention on held-out families

Primary endpoint: independent whole-task accuracy after the fixed 160 updates, at K=8, on the same final panel for all conditions. Intermediate component answers must not be available when that whole question is answered.

Proposed final application panel: 30 new root families, one supported LIST_PARTS, FIND_SHARED_PART, and REACHED_VIA question per family, 90 whole-task questions. The count and novelty class must be validated against actual source supply before the future package is approved. Do not change graph depth, vocabulary, or semantic scope merely to evade duplicates.

Attach a declared set of component queries to those final families for an independent component audit. Reset latent state between every query. Keep all gold-derived targets in the evaluator. Do not use the component audit's answers to steer the whole-task prediction. A secondary joint metric may ask whether both a parent and its declared component queries were all correct, counted per family rather than as independent successes.

Use a separate earlier-skill audit with demonstrable starting competence. Maintenance samples come from earlier training, not this audit. Retain per-face results through the current supported evaluators; do not declare all six faces stable from three graph-task scores alone.

The current CAS_RDCJT_001 panel is not this new study's development material. Use a new versioned final panel disjoint from training/development and any already examined panel. Keep root families together with their faces, analogies, revisions, and renderings. A new exercise ID or option permutation does not create an unseen reasoning problem. Catalog semantic duplicates explicitly.

Freeze final checkpoint selection to the completed schedule. Retain all assigned failures and missing rows; missing evidence is not an incorrect numerical answer and is not dropped from the assigned denominator. The teacher may score preserved predictions, never choose between the learner's alternatives.

## 13. Result rules and what each outcome means

The following are **proposed engineering targets** for this addendum, not results or universal scientific criteria. Freeze any coherent change in the final execution profile before approval. Do not change S1's original rules.

**SUPPLEMENT_BENEFIT_SUPPORTED:** ALT minus WHOLE_SUPPLEMENT whole-task accuracy is at least +0.05, its family-clustered 95% confidence-interval lower bound is above zero, and the gain is positive in at least two of the three paired training seeds.

**ALTERNATION_ORDER_BENEFIT_SUPPORTED:** the same rule for ALT minus MIXED_SAME_ITEMS. This supports the declared ordering/batch-grouping policy. If MIXED also works equally well, report that complementary material helped without establishing a special advantage for blockwise alternation.

**OBSERVED_RETENTION_CONSTRAINT_MET:** final ALT component-audit accuracy is no more than 0.02 below either its initial K=8 reading or final MIXED at K=8; final earlier-skill accuracy is no more than 0.02 below either its initial K=8 reading or final WHOLE_SUPPLEMENT at K=8. Both audits and starting competence must exist. Report all per-operation/per-face/seed changes and intervals. This observed tolerance is not a confidence guarantee of no forgetting outside these audits.

**COMPLEMENTARY_TEACHING_CANDIDATE_QUALIFIED:** valid required evidence, supplement benefit, observed retention constraints, and ALT whole-task accuracy at least 0.50. An alternation-order benefit is reported separately, not silently required for any benefit of the combined teaching content.

An absent advantage produces NOT_ESTABLISHED for that contrast, not proof that the two methods can never complement each other. A numerical or delivery failure is EXECUTION_INVALID or TEACHING_INCOMPLETE as appropriate, not a negative learning result. Missing retention evidence is RETENTION_UNASSESSED, not a pass. No status automatically promotes the candidate or authorizes a retry.

For both planned contrasts, use paired root-family differences, average the three fixed seed rows within each family, and bootstrap root families with replacement using 10,000 replicates and analysis seed 404. Preserve paired condition rows in every draw. The interval concerns sampled families conditional on these seeds; do not treat 270 repeated predictions as 270 independent graphs or infer all-initialization reliability.

Report both planned contrast intervals, counts, and pass/fail states without selecting the favorable one. They are separate claims, not two chances to win a single omnibus hypothesis. Report the protocol's multiplicity scope plainly; do not describe unadjusted per-contrast intervals as a simultaneous 95% guarantee.

## 14. Eventually allocate teaching by weakness, but do not hide that extra experiment here

This version implements actual **fixed alternation**. It does not merely describe alternation in a document. The purpose of the observations is to prepare evidence for a later, bounded weakness-responsive policy.

The existing constructor's LEARNING_RECIPE interface is the eventual integration site. Later policies could propose more component practice for a demonstrated component weakness, more whole-task practice for a demonstrated application gap, and maintenance when a supported old capability declines. An input/representation or tool failure calls for the appropriate non-teaching remedy.

In this version, store the observations and optional human-readable candidate diagnoses. Keep `adaptive_reallocation_enabled: false`. Do not implement another learned controller, treat self-confidence as competence, or infer internal failure location from one score.

A future adaptive profile must first specify observable evidence, minimum completed teaching, hysteresis/stability rules, per-skill exposure floors, authorized recipe choices, and a fixed total budget. It must use development or runtime qualification observations, never hidden final-test correctness. It may not expand the budget or alter authority by proposing a recipe.

Changing teaching methods is not itself RPM recursion. RPM may select a bounded learning recipe for a subgoal; the scheduler then executes its phases without opening a new child for each batch. Parent resumption and durable model/memory admission remain governed by the existing constructor.

## 15. Tests: reuse the existing suites

Implement pure tests against the actual course compiler and packaged dispatch, using explicit fakes only for neural/provider dependencies:

| Check | Required behavior |
|---|---|
| Opt-in isolation | Current CAS_RDCJT_001 configuration and output bytes remain unchanged when extension is disabled |
| Same learner | Candidate and optimizer identities persist across all modes; independent condition objects remain separate |
| Phase update boundary | ALT's component update completes before its paired whole forward begins; no concealed gradient accumulation across that boundary |
| State lifetime | New question/assistance/model revision resets latent state and invalidates answer-bearing caches |
| Exact data control | ALT/MIXED supplemental multisets match; WHOLE repeats the declared B set; existing CFC and maintenance agree across conditions |
| Semantic identity | Duplicate question exposure is retained, not falsely counted as fresh questions |
| Target independence | IDs, pairing, options, visibility, mode and depth cannot change with a private target mutation |
| Exact accounting | 72 decisions/10 updates per round; 1,152/160 per course; depth and partial batches produce the planned core counts |
| Update evidence | Before snapshot, actual final prediction, teacher release, loss/backward/update and committed cursor occur in order |
| Monitor boundary | Read-only monitoring cannot change weights, optimizer, training RNG/cursor, schedule or final checkpoint selection |
| Retention scope | Maintenance cannot draw from the retention audit; missing baseline competence does not become a retention claim |
| Recovery | Model/optimizer/cursor/data/profile restore coherently; prior updates are not duplicated and original errors survive |
| Packaged dispatch | The export invokes this candidate experiment through the existing lifecycle, not the previous worker by accident |
| Result restoration | Retained rows reproduce counts, paired differences and status; missing mandatory artifacts prevent completion |

Actual numerical tests belong in the one eventually authorized GPU job: gradients reach the same allowed core from both modes; recurrence remains connected under both inputs; parameter scoping and snapshots behave on real tensors; monitor passes make zero updates; final checkpoint reload reproduces independent predictions. Reuse S1's numerical core tests rather than create a second recurrence test framework.

No local CPU or GPU neural workload, monkeypatched execution bypass, hidden warmup training, or per-test paid launch is authorized by this directive.

## 16. Keep the implementation small and the evidence usable

Prefer an extension beside the current CFC schedule/evaluator. Logical functions are pair compilation, schedule construction, persistent-course execution, paired evaluation and reporting; these need not be separate services or packages.

No synchronous upload per tensor or per mode switch. Reuse buffered scalar/logit recording and the established evidence-preservation layer. Store full activations only under S1's bounded diagnostic policy.

Checkpoint initial state, declared monitor-round completion states, and final state with the actual weights, optimizer, global cursor, recurrence/encoder/tokenizer/scoring identities, source and data references. Checkpoints at intermediate monitor rounds are diagnostic artifacts, not candidates for final-test shopping. Save partial state on a technical interruption under the existing recovery policy.

Preserve required artifacts before disposable summaries. Receiver verification and checkpoint restorability are separate from worker exit status. Terminate compute by deadline even when collection fails; retain evidence under the approved bounded policy and never delete its only copy before verified collection.

The extension's required artifacts belong to its own future job prefix, not the active experiment's evidence inventory. Include monitoring, analysis, all nine courses, numerical checks, final audit, retention, checkpoint reload, collection and storage in the one costed request. A lower-cost amended plan must name its narrower comparisons before approval.

## 17. Deliver one integrated implementation

Complete the following as one scoped assignment:

**Bind.** Read the current recurring learner/CFC/teacher/optimizer/observer/preservation interfaces once, record actual versions, and prepare an isolated candidate worktree.

**Build.** Implement the real opt-in schedule extension, connected component/whole lessons, persistent single-learner state, matched conditions, fixed observation points and evaluator. Do not leave production adapters as fakes or lists of future function names.

**Check.** Run the existing pure suites and packaged non-neural rehearsal. Keep inherited errors distinct from new failures. No routine fix requires another owner message within this scope.

**Package.** Bind the new configuration and worker entrypoint to the existing proven lifecycle. Populate implementation-derived fields, source/package/data identities, full schedule, numerical checks, metrics, total resource limits and reservation estimate. Leave owner authorization and signatures unfilled.

**Return.** Provide the runnable package, concise DESIGN/TASK_BINDINGS, actual pure test output, one retained example unit, schedule/coverage report, and one future execution request. Stop earlier only for a concrete out-of-scope blocker, with the exact decision needed.

Build-completion label: **COMPLEMENTARY_TEACHING_READY_NEURAL_UNTESTED**. It requires actual guarded production bindings and complete non-neural packaging. A fake learner passing the sequence establishes software behavior only. No performance claim, activation or paid run follows from build completion.

## 18. Ready-to-forward instruction

Implement CAS_COMPLEMENTARY_TEACHING_001 as an isolated, opt-in next-version extension to the current recurrent-CJT/CFC stack. Keep the current CAS_RDCJT_001 build and its first experiment unchanged.

Use one continuing student and optimizer within each condition. Preserve the full CFC foundation, then alternate checked component practice and whole-task practice with maintenance. Use the same recurrent compute profile in every mode; clear question-specific state without clearing learned weights or optimizer history.

Build the ALT, same-items MIXED, and WHOLE_SUPPLEMENT comparisons with explicit exposure and compute accounting. Preserve teacher/learner separation, task-family boundaries, fixed checkpoint selection, retention evidence and all earlier results. Do not introduce new heads, a second reasoner, a solver, an adaptive halt mechanism or a new controller.

Complete normal non-neural integration, tests, real worker dispatch and packaging without returning for permission after each ordinary substep. Return once with the runnable candidate and its costed execution request. No model loading, neural execution, reservation or launch is authorized by this document.

**The intended result is accumulated competence: the same learner uses the component skills and the complete-task skill together. Switching methods is the mechanism under test, not the success criterion.**

## Source locators and artifact status

S1: Recurrent_Neural_CJT_Implementation_Plan_v0.1.md and Recurrent_CJT_Profile_v0.1.json, supplied prior handoff.  
S2: RPM_Guided_CAS_PCBA_Learning_Constructor_v0.1(1).md, supplied source plan.  
S3: 2510.09340v2.pdf, abstract and introduction, especially pages 1-2.  
S4: Cube Verified-Step Teaching Schema v0.1, supplied directive; reviewed through Files, not redistributed here.

The attached machine-readable profile and schedule are proposed configuration artifacts, not model inputs, a trained system, or an execution authorization. Source hashes identify the available bytes; they do not verify a research claim. The handoff's pure checker validates its own schedules and integrity only, not the repository or any neural behavior.
