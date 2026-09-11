# Cross-Cube Face Grounding Plan v0.1
## Builder handoff: CUBE_FACE_GROUNDING_001

Concept origin: Little Henderson  
Status: PROPOSED CANDIDATE PLAN. No implementation, neural result, spending authorization, or promotion is asserted by this document.  
Purpose: Teach the meaning and use of the six face roles across many different cube concepts, not just a lookup from numbers to role names.

> Within one cube, different faces explain one idea. Across many cubes, the same face teaches one kind of meaning.

## 1. Source basis and the new proposal

The existing Cube Node Schema v0.1 defines a core, six stable face roles, explicit relationships, separate teacher and learner views, and boundaries between compiled lessons and delivered neural teaching. Its sections 9-10 explicitly require new task profiles and numerical adapters for face-specific work not expressible through the existing graph tasks. CUBE_TEACHING_PROFILE_001 and TASK_BINDINGS describe earlier preparation in which several faces were presentation-only. CANDIDATE_RUN_001 supplies the candidate-wrapper pattern, parameter scoping, before/after snapshots, per-step observations, and checkpoint verification.

This plan extends those designs. It does not claim that they already implement cross-cube category learning. It does not change historical results, declare the full seven-stage program successful, or validate a general theory of metaphor. The dataset sizes, schedule, tasks, comparison, and acceptance criteria below are proposed engineering choices, not requirements found in the sources or empirically established optimal settings.

The user’s notation `55555` means separate examples carrying the same face category. It does not mean feeding the integer 55,555 or an unbounded run of repeated digits to the network.

## 2. Fixed face-role registry

Keep the existing meanings and numbering:

| Face | Role | Bounded learning objective |
|---|---|---|
| 1 | Technical name, definition, function | Recognize and select a definition/function consistent with supplied facts. |
| 2 | Context, environment, interactions | Recognize and select a relevant contextual account consistent with supplied facts. |
| 3 | Analogy/metaphor with a declared scope | Recognize a bounded cross-domain comparison and select an analogy that preserves the specified relationship. |
| 4 | Explicit correspondence | Recognize and select the node-role and relationship mapping between supplied presentations. |
| 5 | Parts and structural relationships | Recognize decomposition and correctly identify constituents and their connections. |
| 6 | Recomposition/story/process | Recognize and select a valid account of how supplied parts or steps form a whole, within the declared process semantics. |

The core anchors the subject of the cube. Do not invent a Face 0. Face 5 is associated with the intended Male/^6 decomposition lesson; face numbers are not Noetic operator numbers.

A face-role marker is categorical, for example `CUBE_FACE_5`, not a scalar to average or rank. The definition/function facts and ordinary concept references remain distinct from this six-member face-role registry; opaque record identifiers are not additional semantic features. Preserve the association `(cube reference, face role, content)`. Different Face-5 contents must not be forced into identical vectors: their shared role and their different structures both matter.

The first profile labels an excerpt’s declared instructional purpose. It does not assume that all unrestricted natural-language passages have exactly one of six mutually exclusive meanings. Split mixed-purpose excerpts or mark them ambiguous and exclude them from single-answer role recognition. In particular, distinguish an analogy presentation (Face 3) from its explicit correspondence table (Face 4), and a structural inventory (Face 5) from an explanatory recomposition (Face 6).

## 3. Two learning axes

### Across cubes: same role, different subject

Group Face 5 from several different concepts and teach the common instructional move: identifying a whole’s constituents and their structural relationships. Repeat for each of the other five roles.

Examples may use authored mechanical assemblies, grammatical mini-worlds, procedures, arguments, containers, and other controlled domains. These examples are illustrations grounded in their declared local facts; they are not automatically authoritative claims about real machines, language, or causal systems.

The same face role does not imply that every example has the same graph topology. The broad role is shared; specific structures may match or differ. When teaching a more specific shared principle, record the exact scoped relation being preserved, rather than declaring every pair with the same face number equivalent.

### Within a cube: different roles, same subject

Return to one concept and present its definition, context, analogy, correspondence, decomposition, and recomposition. This teaches that the faces belong to one subject rather than six disconnected topics.

Cross-face sweeps, within-cube visits, optimizer updates, and the original seven-stage neural cycles are separate counters. A sweep over six roles is not automatically a full original seven-stage cycle.

## 4. The two numerical task profiles

Implement both profiles for all six face roles as bounded candidate tasks. The existing three-choice response shape can be reused where technically compatible; task meanings and input handling must be versioned. Do not mislabel analogy or role recognition as an existing LIST_PARTS operation just to satisfy an enum.

### 4.1 ROLE_FROM_CONTENT

Learner receives a neutralized, unlabelled face excerpt plus only the source context needed to interpret it. The three options are three face-role labels. Exactly one fits the excerpt’s declared purpose.

The excerpt’s own face ID, role title, source file path, category-specific object type, teacher explanation, generation-rule identifier, and other equivalent metadata are not model inputs. The query ID is public-content-based, not derived from its target.

Rotate candidate triples so all six roles compete against every other role. The same three-role group must not be used permanently. Balance target positions and report the actual encoded ordering. Accuracy is three-choice conditional accuracy, not six-way classification accuracy.

Recognition events are interleaved across roles. Do not supply a support group consisting only of the correct category during this task: that would answer the classification through context. Do not expose a block label or state variable that reveals the hidden role.

Learning signal: ordinary cross-entropy against the checked correct slot. This requires actual supervised examples with the query label withheld, not a number-to-description copying exercise.

### 4.2 FACE_APPLY

Learner receives a requested view, public source facts for a new query cube, and three alternative responses. The alternatives all attempt the same requested kind of view; only one is consistent with the source and declared relation scope.

During the labelled guidance phase, the query also carries the shared face marker and three worked support examples from other training families. Each support example contains that other concept’s source facts and a checked illustration of the requested view. No support is a renamed, rewired, or otherwise derived version of the query’s own family.

Support examples and their answers are legitimate teacher guidance. The query’s answer remains private until the prediction is recorded. Worked explanations only count as neural input when the adapter actually delivers them.

Bounded application tasks:

| Face | Query | Correctness basis |
|---|---|---|
| 1 | Select the definition/function matching the supplied object contract. | Consistency with the declared identity/function facts, not a world-knowledge guess. |
| 2 | Select the contextual account matching the supplied setting and interactions. | Correct participants, relation direction, and setting facts. |
| 3 | Select the target example preserving the specified source relationship. | An explicit teacher-side mapping that preserves the declared scoped structure; no solved mapping given to the query model. |
| 4 | Select the valid correspondence between two supplied examples. | Correct mapped endpoints and preserved relations. |
| 5 | Select a correct complete decomposition or relation answer. | Existing exact graph semantics where applicable, including direct versus indirect and complete versus unknown inventory. |
| 6 | Select the valid explanatory reconstruction from supplied parts. | Correct endpoints and completeness; temporal/dependency order only where it is explicitly part of the supplied semantics. |

For Face 6, a harmless change in the order of an unordered inventory is not an error. For Face 3, word overlap is not structural correspondence. If two options satisfy the declared rule, repair the exercise or reject it; do not arbitrarily score one as wrong.

This first profile uses bounded controlled descriptions and structured facts. It does not establish unrestricted metaphor comprehension, free-form story generation, or open-world conceptual reasoning.

## 5. One worked teaching episode

For the Face-5 block, show three distinct training concepts, each with its own public facts and checked constituent description. For example: an authored assembly, an authored sentence structure, and an authored procedure. Label all three with the shared category marker 5.

Then present a separate query scene:

```
R contains P.
R contains Q.
P contains Z.
S contains T.
```

Requested view: Face 5, direct constituents of R.

Three response candidates:

```
[P, Q]    correct
[P, Z]    substitutes an indirect part
[P, T]    substitutes a part belonging to another whole
```

The label 5 identifies the kind of question. It cannot choose among these three answers. The checked correction explains both inclusion and exclusion from R’s direct inventory.

For Face 3, present two supplied source/target scenes and three possible analogous examples. Make a same-vocabulary but wrongly connected target a negative. Make a differently named but correctly connected target a positive. Keep claimed correspondence limited to the declared substructure.

Later, in ROLE_FROM_CONTENT practice, remove the number and ask which face role an unlabelled structural inspection expresses. Do not leave the answer in a schema key such as `decomposition`.

## 6. Corpus and partition proposal

Starting target: 96 cube-centered lesson families, each with six supported face presentations.

| Partition | Families | Base face presentations |
|---|---:|---:|
| Training | 64 | 384 |
| Development | 16 | 96 |
| Final held-out | 16 | 96 |
| Total | 96 | 576 |

A family is a base lesson and all dependent renderings, analogies, label substitutions, recompositions, subquestions, and hard negatives derived from it. Group them before splitting. Multiple cubes from a connected authored lesson are not automatically independent families.

Do not produce 96 renamed versions of a few templates and report 96 independent arrangements. Produce a coverage table for base graphs, scoped relationships, domains, renderer templates, and wording variants. Report structure overlap separately from family overlap. Separate familiar-structure/new-instance tests from unseen-arrangement tests; never silently call the former the latter.

Every training domain contributes all six face roles. Multiple rendering styles occur within every face role. The same domain, word, option length, or formatting convention must not perfectly identify a role.

Balance the role-recognition targets across all six roles. Balance semantic application subtypes, especially direct/indirect/absent, shared/none, and empty/nonempty inventories where those tasks occur. Balance correct positions through the actual codec, not merely the authoring layout.

Empty-list answers cannot have three distinct alternatives all of length zero. Keep such cases, report them separately, and measure length-based baselines instead of claiming equal length everywhere.

Use source facts and scope-checked teacher rules. Generated prose alone is not the correctness authority. Do not define a gold category as 'whatever face file this came from' while allowing that file name or equivalent key into the learner input. Human-readable purpose labels need an auditable content rule and ambiguity handling.

## 7. Concrete teach-first schedule proposal

The numbers below are starting design choices, not universal requirements or empirically sufficient amounts of teaching. This profile explicitly differs from the old 64-update graph profile. Do not restart a frozen 64-step function repeatedly to evade its limit.

### Phase A: repeated guided grounding

16 complete sweeps of the 64 training families across all six face roles.

Each family-role pair receives one FACE_APPLY query per sweep, accompanied by three worked supports from other training families. Rotate support identities, concept order, and permitted surface variants according to a frozen schedule. Role blocks are visible as intentional teaching guidance; change their order across sweeps. Use actual cross-cube support content, not just shared number metadata.

Count:

- 64 x 6 x 16 = 6,144 supervised query presentations.
- Three supports per query = 18,432 worked-support presentations, not independent queries or optimizer updates.
- With minibatches of 8 independent query episodes: 768 optimizer updates.

Correct every practice error. Do not issue an independent mastery pass/fail before the full guided minimum. Software checks, finiteness checks, and training-loss logging are not mastery judgments and remain active.

### Phase B: mixed practice and use without worked supports

8 further sweeps of the same training family-role pairs: 4 ROLE_FROM_CONTENT sweeps and 4 FACE_APPLY sweeps without worked supports. Interleave roles and query families. Recognition queries have no hidden-label hint. Application queries may name the requested face but all answer options implement that same requested role. Provide corrective targets after recorded predictions throughout training.

Count:

- Recognition: 64 x 6 x 4 = 1,536 supervised queries.
- Application without supports: 64 x 6 x 4 = 1,536 supervised queries.
- Total: 3,072 supervised queries and 384 optimizer updates at batch size 8.

### Per-condition totals

9,216 supervised query presentations; 18,432 worked-support presentations; 1,152 optimizer updates at batch size 8. Support tokens and any explanatory tokens are included in time/memory accounting. These are face-grounding sweeps, not 24 completed seven-stage neural cycles.

Batching must be supported by the actual learner. If it is not, implement the bounded candidate batching path or report its exact impact on update counts and limits before freezing the executable profile. Eight sequential updates are not equivalent to one minibatch update and must not be relabelled.

The builder must report fit within token length, memory, wall-clock, and proposed cost limits. Shortfalls stop with saved state and TEACHING_INCOMPLETE. Do not silently truncate supports or reduce the guided minimum. Any reduction before execution must be recorded in a revised plan, not presented as delivery of this schedule.

No final held-out cases are used to decide whether to continue training. Use the final scheduled checkpoint, not a checkpoint selected by final-test performance. Any development checks occur only after the guided minimum and do not silently extend the run.

## 8. One matched pilot, not a series of micro-runs

Proposed first comparison: one paired initialization, two conditions, one bounded job.

- STABLE_FACE_CUES: explicit shared face-number cues in the guided/application inputs.
- NEUTRAL_CUE_CONTROL: the same examples, support identities, questions, targets, order, token budget as closely as possible, and training allocation; explicit in-input face-number cues are replaced by one common neutral cue. Do not replace them with false or contradictory categories.

In both conditions, role-recognition targets and offered role labels retain their proper meanings. Thus, this comparison isolates the added value of explicit in-input stable face markers during teaching, not 'semantic labels versus absolutely no semantic labels'. Both systems can learn from the correctness supervision.

The control still gets enough public context to solve every task. A task that becomes impossible without the role cue is not a fair control item; rewrite it so the worked examples or common task framing establish the requested role without revealing the answer.

Use matched starting weights, identical tokenizer/encoder and candidate adapter, separate optimizers and checkpoints, and a shared fixed task-order schedule. Do not mutate one learner and then reuse it for the other condition.

Two conditions at the schedule above imply 2,304 optimizer updates and 18,432 supervised query presentations in total. One initialization is an exploratory pilot, not multi-seed replication or proof of architectural superiority.

Perform initial input/gradient checks, the entire training allocation, checkpoint verification, and final evaluation in the same authorized job. Do not launch one paid job per face or per check. Retain initial and final checkpoints for both conditions and all material needed to reproduce them. The future resource request must give a real wall-time and cost ceiling; this plan does not approve a dollar amount.

## 9. Evaluation and interpretation

After all training for both conditions, evaluate the fixed final held-out families with no optimizer updates and no worked support solutions. Evaluate the retained initial checkpoints and the scheduled final checkpoints in this final evaluation-only segment; that supplies the before/after comparison without exposing the held-out panel to the training controller. Keep initial and final prediction records distinct.

### A. Recognize the role from new content

16 families x 6 face roles = 96 three-choice ROLE_FROM_CONTENT questions per condition. Query face IDs, role titles, filename/schema giveaways, and face-block hints are absent. Report each face’s count and the macro average. The independent-random-choice expectation is one third per question; it is not a six-way one-sixth baseline.

### B. Apply the role to a new cube

16 families x 6 roles = 96 FACE_APPLY questions per condition. The requested role is given, but all choices attempt that role. Correctness requires reading the specific content and relationships. Report each role separately, including semantic subtypes and empty/absent cases. A rule that ignores content and picks a fixed slot, fixed category, shortest choice, or frequent semantic answer must be reported as a baseline where applicable.

The 192 questions are repeated views of 16 base families, not 192 independent graph families. Report before/after changes and paired condition differences. Cluster any uncertainty calculations by base family and keep single-initialization uncertainty limitations explicit. Use per-question pairs rather than treating identical panels as unrelated samples.

### C. Targeted behavioral checks

Use a small frozen diagnostic subset after the primary evaluations:

- consistently rename concepts while preserving relationships;
- reorder unordered graph facts, but do not reorder a semantically ordered process;
- rewire one relationship while preserving token inventory where feasible;
- remove the explicit cue during application;
- give all options the same face marker and require content-dependent selection;
- compare equal-length meaningful alternatives and separately score unavoidable length differences.

Do not change the model in response to these diagnostics within the same run. Every rewording stays linked to its family and is not counted as an independent sample.

### Practical pilot milestones, proposed rather than scientifically validated

Use these as explicit advancement targets for a bounded prototype, not universal definitions of understanding:

- role recognition: macro accuracy at least 0.75, with every face at least 0.50;
- face application: macro accuracy at least 0.70, with every face at least 0.50;
- content-sensitive behavior: report both correct invariance on harmless edits and correct answer changes on meaningful rewiring, not mere output movement;
- label-benefit claim: report paired differences and family uncertainty. Meeting the capability targets does not establish STABLE_FACE_CUES beats the control.

On a 16-question per-face panel, report integer counts alongside percentages. These targets do not justify calling a one-seed result replicated or claiming unrestricted abstraction. No threshold is lowered after looking at outcomes.

Interpret outcomes separately:

- Label names can be recited but hidden-label content cannot be classified: association only.
- Hidden-label role recognition works but application fails: category recognition without demonstrated operational use.
- Both succeed on held-out families: bounded evidence of face-role grounding and application in this profile.
- Both conditions perform similarly: no demonstrated additional benefit from explicit face cues, even if both learned.
- A role fails while others succeed: report its boundary; do not hide it in a pooled average.

## 10. Numerical implementation requirements

Use one candidate learning path, not six new neural subsystems. Reuse the existing targeted transform and three-choice scoring where compatible. Record the research task profile separately from the accepted ^6 semantics; repurposing a candidate transform for a new task does not change what the accepted operator means.

The adapter must carry:

```
query source facts + requested role when permitted
+ worked support facts/answers when permitted
+ three public choices
                    -> actual numerical inputs
                    -> candidate neural module
                    -> the three scores used for the prediction and loss
```

ROLE_FROM_CONTENT and FACE_APPLY are new task semantics. Candidate-only versioned input handling, bounded multi-example encoding, categorical cue representation, scheduling, batching, and launcher dispatch are implementation work required by this plan. Do not leave them as stored prose while claiming the experiment implements the concept.

Preserve cube identity, face role, view identity, and directed relationship endpoints through encoding. Do not flatten everything into a bag of words, globally normalize away required distinctions, or inject teacher-computed answers/correspondences into the query input.

Before training, measure the actual model-facing representation for changed roles, changed contents, and same-token rewiring. Check distinct token lookup, supported lengths without truncation, finite scores/losses, and useful target-dependent gradients. These checks belong to the single eventual job, not separately funded launches. Pure source/data/packaging checks happen first without any model load.

A learned extra readout, a different transformer, a general language teacher at inference, a new canonical operation, or expanded trainable-parameter scope is not silently included. If the existing candidate transform cannot represent a specified task, identify the concrete interface/capacity restriction rather than substituting an easier name-lookup task. An architectural extension requires its own explicit decision.

## 11. Answer boundary and observations

Keep public episodes, teacher targets, and audit metadata separate. The input compiler receives only the public object. Targets affect the loss after prediction, not public IDs, slot order, support selection, visibility shape, or input encoding.

For ROLE_FROM_CONTENT, retain the true query category only in the teacher object. For FACE_APPLY, the requested role is a legitimate public instruction, but candidate source face IDs must not reveal which option is correct. Query-derived family IDs, principal-rule IDs, and solver witnesses stay out of model features.

Cache keys include public content, role visibility, assistance state, encoder/adapter identity, and support-set identity. Assisted caches cannot be reused for unassisted views.

Per scored event, retain the exact input identity, actual predicted semantic value, all three scores, actual loss, target release, face role/task family, support count, token/item lengths, optimizer-update identity, and the checkpoint linkage. Capture the scores from the actual forward computation used for the correction, not an independent later call that merely has the same argmax.

Take a before snapshot before the first update and an after snapshot after the final update. Report changed permitted parameters, forbidden changes, immutable encoder/tokenizer checks, and the exact coverage of saved components. Missing critical scores or dropped evaluation rows prevent a completed-measurement status rather than being silently accepted as a successful deliverable.

## 12. Implementation deliverable and workflow

Prefer one small extension in the existing graph-teaching/cube package, its tests, a dataset manifest, and a versioned adapter/profile. Reuse the existing candidate runner, task boundaries, result collection, checkpoint verification, and launch lifecycle. Do not build a new controller service, 3D renderer, memory database, reward model, MCTS engine, or separate general-purpose launcher.

The first builder handoff must contain:

1. The six-role registry and all six bounded ROLE_FROM_CONTENT/FACE_APPLY task bindings.
2. The family-grouped source corpus, teacher rules, split/coverage report, and public/teacher exports.
3. One readable cross-cube teaching episode for every face, paired with its exact compiled learner input and target.
4. The actual numerical adapter, schedule, candidate worker connection, observation integration, and package built from those sources.
5. The existing-style non-neural end-to-end rehearsal, including answer independence, slot agreement, checkpoint/delivery stubs, and evidence preservation under injected failure.
6. One final execution request naming the complete package, shared and trainable state, both conditions, schedule counts, resource cap, no-automatic-retry rule, and collection/shutdown policy.

Do not stop after each schema, counter, or manifest repair to ask permission for the next ordinary integration step. If the owner approves implementation of this plan, that approval covers the non-neural candidate code and packaging work needed to complete this deliverable. Spending, model loading, and actual neural execution still require the final specific authorization. Never forge owner-signature fields or imply the present planning request approves cloud costs.

Return early only for a concrete blocker outside this scope, naming the exact decision needed. Stop at the final execution-approval boundary once, not at every implementation substep.

Historical negatives, accepted weights, the existing retained-checkpoint contrast probe, and old experiment files remain untouched. This plan does not assert that any prior scoring/representation issue has already been solved. It introduces a new, clearly named face-grounding candidate with shared implementation conditions.

## 13. Definition of done

Preparation is complete when the actual prepared package can conduct the declared teacher-to-learner sequence for every included face, its public/teacher and numerical boundaries are explicit and rehearsed, and one bounded execution request is ready. A set of populated face fields with no neural input path is not completion.

Learning is a later, measured state. The intended endpoint is a model that can recognize a view from new content and use that view on a new idea, rather than merely repeat the role name when it sees its number.

**The number is the teaching handle. The repeated, varied content supplies its meaning. Correct independent use is the evidence.**
