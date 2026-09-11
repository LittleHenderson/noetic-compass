# Cube–Face–Cube Learning Loop v0.1
## Builder plan: CFC_LOOP_001

**Concept origin:** Little Henderson.  
**Status:** Proposed candidate teaching design. Not implemented or experimentally validated by this document.  
**Scope:** Implement the alternating teaching schedule and its required machine-facing tasks using the existing cube and candidate-training infrastructure. This plan does not authorize neural execution, a cloud reservation, or a paid launch.

> The cube teaches an idea through multiple views. Matching faces teach a view through multiple ideas. Returning to a cube asks the learner to apply the shared view to the particular idea. Repeat with corrections and controlled variation.

## 1. What changes

The proposed change is a two-axis teaching curriculum, not new geometric hardware:

1. **WITHIN_CUBE:** hold the idea fixed and move through its views.
2. **ACROSS_FACE:** hold the view role fixed and compare it across different ideas.
3. **RETURN_TO_CUBE:** use those distinctions in a concrete whole-idea task.
4. Repeat the three-part round with the same learner and continuing optimizer state.

The loop is an explicit training schedule. It is not automatically a new recurrent neural architecture, a runtime RPM implementation, or proof of self-improvement. Nothing about a cube drawing supplies computation by itself.

Two learning questions remain distinct:

- **Role/category:** What kind of information does this face present?
- **Content/structure:** What does this particular face say, and which relationships actually match across examples?

A shared role does not require identical contents, topology, or embeddings. Do not train all Face-5 contents to become numerically identical.

## 2. Source basis and the necessary extension

The existing Cube Node Schema v0.1 defines one core and six faces, explicit graph relationships and view mappings, teach-first repetition, and separate teacher/learner views. Its face numbers are not Noetic operator IDs.

The uploaded TASK_BINDINGS record supports the existing LIST_PARTS, FIND_SHARED_PART, and REACHED_VIA exercises, but marks definition, analogy, explicit correspondence, and unrestricted story tasks as unsupported or presentation-only. The earlier CUBE_TEACHING_PROFILE_001 likewise distinguishes prepared presentations from numerical delivery.

This plan therefore **proposes new candidate task profiles and a candidate cube input adapter where required**. Scheduling unsupported prose in a loop is not an implementation of this proposal. All six roles must have an actual, bounded numerical teaching path before a run is called a full CFC loop trial.

The already completed checked-component pilot is a different experiment. Preserve its result and checkpoints. Its zero full seven-stage cycles do not become CFC cycles retrospectively.

## 3. Stable cube anatomy

| Address | Preserved role |
|---|---|
| core | Identity of the idea in its declared context |
| face_1 | Technical name, definition, and function |
| face_2 | Context, environment, and interactions |
| face_3 | Analogy/metaphor within a declared scope |
| face_4 | Explicit correspondence of roles and relations |
| face_5 | Parts and structural inspection |
| face_6 | Recomposition or bounded process/story |

Use one global role vocabulary for every cube. FACE_5 is a categorical marker, not a numerical magnitude. The owner's “55555” means examples from the same face role on different cubes, not a requirement to repeat a digit five times in a feature vector. Keep each example's cube identity and relationships attached to it.

Face 5 remains the decomposition teaching face associated with Male/^6. Do not reinterpret Face 3 as Noetic ^3 or Face 6 as the registered ^6 transform merely because the numerals match.

## 4. The three phases of one round

### A. WITHIN_CUBE: one idea, several connected views

Take a small cohort of four focal cubes from training families. For each focal cube:

- Anchor its core and technical account.
- Teach its context.
- Teach a bounded analogy.
- Show and practice the explicit correspondence.
- Teach its component relationships with checked corrections.
- Recompose the whole or a supported process.
- Reinforce with a content question linked to the same idea.

These are the original seven stages. The seventh stage is reinforcement, not a seventh face.

Each stage gets one declared supervised decision in the proposed initial numerical schedule. Short worked material can accompany it, but it must actually be included in the permitted numerical input to count as delivered teaching. A file reference or printed explanation outside the model input does not qualify.

### B. ACROSS_FACE: one role, several different ideas

For each face role f in 1..6, collect the f-th face from all four cohort cubes. Present examples together in one bounded learning input, preserving their separate identities and structures.

Give two kinds of supervised decisions:

1. **Role recognition:** use labelled support examples to teach what that kind of view does, then select a compatible, unlabelled presentation from three alternatives. The query/candidate role label is withheld; support labels may remain visible.
2. **Content-sensitive comparison:** keep the face role the same across all alternatives. Ask which relationship, correspondence, or description is actually supported. The common face number cannot settle this choice.

Include different content and different structures within each face category. For example, two Face-5 descriptions may both be decompositions even though only one preserves a particular branching pattern. Do not label one as “not decomposition” just because its topology differs.

Do not force an ambiguous description into a single role. Context and decomposition can restate the same facts; analogy and explicit mapping can overlap. Construct tasks with a unique declared instructional function and a unique admissible answer, or reject them as ambiguous under the current three-choice profile.

### C. RETURN_TO_CUBE: apply the view to the idea

Return to each focal cube, rather than ending with an abstract label exercise. Give two decisions:

1. Select a valid missing/re-expressed face from supplied evidence.
2. Answer a whole-idea question without being handed the teacher's component answers or a solved correspondence.

The first question must be answerable from the visible evidence. Do not require the learner to invent a function, environmental fact, or story that is not determined by that evidence. Reject an underdetermined item or use a separately declared insufficient-information answer profile.

During training these are practice decisions with feedback. They are not final evaluation. Their errors lead to worked corrections and subsequent planned practice, not immediate abandonment of the teaching method.

Then move to the next training cohort and repeat. Subsequent sweeps revisit ideas, change permitted surface presentations, and vary cross-cube groupings while preserving the registered exposure counts.

## 5. What each face asks the learner to do

All rows below are **proposed bounded tasks**, not claims that the current graph adapter already supports them.

| Face | Machine-facing task | Teacher check |
|---|---|---|
| 1 | Select the correct scoped definition or function from three alternatives. | Match the authored identity/function facts and task scope; do not infer real-world functions from a graph alone. |
| 2 | Select a relevant contextual relationship, given a stated query and public facts. | Check the relevant endpoints, predicate, and declared relevance condition. |
| 3 | Select a candidate analogy that preserves specified relations. | Verify the declared partial mapping and its relation preservation; do not demand a total real-world isomorphism. |
| 4 | Select a valid role correspondence or complete a missing correspondence. | Check source/target roles and directed edges; reject ambiguous symmetric alternatives rather than choosing arbitrarily. |
| 5 | Select a direct-part list, shared constituent, or direct/indirect/absent relation. | Use the existing reference semantics, with completeness required for absence. |
| 6 | Select a recomposition or short explanatory sequence consistent with the facts. | Check completeness and any declared order/dependency constraints. Do not treat explanatory order as real causation. |

Prefer a shared three-option selector and ordinary cross-entropy for this first candidate profile. Reuse the registered ^6 transform as a candidate learner where the declared input/output can express these tasks. This does not establish that all six face meanings are native ^6 meanings or that the transform has adequate capacity for all of them.

New task semantics must have explicit names. Do not disguise analogy selection as REACHED_VIA just to pass a validator. Implement the smallest versioned candidate adapter needed to convey the actual content, face role, cube identity, support/query roles, and relation endpoints.

Reuse the present readout only if it represents the new choices correctly. Any needed readout or trainable-parameter change must be explicit and identical in the two planned comparison conditions. Do not silently add a head; do not retain a broken interface solely to claim that no architecture changed.

For broad natural-language metaphors and narratives, the source documents do not supply an exact general checker. Start with controlled authored graphs, short templates, and scoped mappings whose answers can be checked. This tests a bounded version of analogy/recomposition, not unrestricted language understanding.

## 6. A worked alternation

The following is an illustrative authored comparison, not an assertion about complete real objects.

Cube A's graph:

    Bicycle contains Wheel and Frame.
    Wheel contains Rim.

Cube B's graph:

    Kit contains Rope and Torch.
    Rope contains Strand.

A within-cube pass teaches each idea through its six views. The cross-face pass compares the two decomposition views:

    whole -> direct constituent -> indirect constituent

The scoped correspondence is Bicycle/Kit, Wheel/Rope, Frame/Torch, and Rim/Strand. It preserves the listed connections. It does not say that Rope performs Wheel's physical function.

A contrasting example moves Strand from Rope to Torch while keeping the nouns. It is still a valid Face-5 description, but the original Wheel-to-Rope correspondence no longer preserves that child connection.

The return pass asks the learner which route reaches Rim or Strand, or which complete direct-part description matches the visible graph. The solved correspondence is withheld for an unassisted measurement; it can be shown during a worked teaching event.

This teaches both “these are descriptions of constituent structure” and “these particular constituent structures do or do not correspond.”

## 7. Teach first, repeatedly, with a bounded allocation

Use a fixed schedule for the first comparison rather than allowing early test performance to steer the curriculum.

**Proposed numerical planning example, not a sufficient-learning guarantee:**

| Portion of one four-cube round | Supervised decisions |
|---|---:|
| Within-cube: 4 cubes x 7 stages | 28 |
| Across-face: 6 roles x 2 decisions | 12 |
| Return-to-cube: 4 cubes x 2 decisions | 8 |
| Total | 48 |

A proposed initial cohort inventory is 24 focal training cubes from 24 distinct source families, arranged in six four-cube cohorts per sweep. Sixteen sweeps then give:

    6 cohorts x 16 rounds x 48 supervised decisions = 4,608 updates per learner

This assumes one optimizer update per supervised decision. If batching changes that, report presentations and optimizer updates separately and use the same declared rule in both conditions.

Sixteen is a chosen starting repetition allocation, not a proven threshold at which concepts must appear. The value of this example is that it counts full, content-delivered rounds across multiple families rather than calling 64 unrelated updates “many complete cycles.”

The builder must estimate actual input sizes, compute, memory, checkpoint overhead, and total job cost before a paid request. This document does not claim 4,608 updates fit any existing cloud ceiling. A change from an old frozen update budget is a declared new candidate profile, not repeated restarts that evade a limit.

Keep guidance and corrections available throughout the initial teaching allocation. Do not terminate teaching because an early practice question is wrong. Technical failure, nonfinite computations, forbidden changes, or the authorized hard limit still stop execution and preserve the evidence.

If the job cannot complete the approved minimum exposure, record incomplete exposure and retain the state. Do not call that completion or a failure of the teaching principle. Never continue indefinitely “until success.”

## 8. What persists, and what feeds the next pass

Within each condition, preserve model weights, optimizer state, scheduler cursor, and exposure counts across within-cube, across-face, and return phases. A phase boundary does not reset the learner.

The accumulated learning is carried by the model's weights. Needed comparison examples must be present in the current numerical input. Do not assume a feed-forward learner remembers earlier demonstration text in an undeclared working memory.

In the initial fixed experiment, corrections come from checked teacher material. Do not feed the model's guessed abstractions back as unquestioned truth. A wrong correspondence can be shown as a labelled negative example, followed by the checked explanation.

Predicted abstractions may be retained as candidate observations. They do not become authoritative graph edges, solved memory entries, or new targets without the declared verification/admission path. No new persistent memory service is required for this schedule.

## 9. Minimal additional lesson/schedule fields

Extend existing records instead of replacing the cube store. A loop event needs these logical fields; reuse existing equivalents:

    round_id
    phase: WITHIN_CUBE | ACROSS_FACE | RETURN_TO_CUBE
    focal_cube_refs
    face_role or face_role_refs
    task_profile
    public_input_ref
    teacher_target_ref
    assistance_profile
    update_expected
    feedback_timing

Scheduler/audit IDs and split-family IDs stay out of model features. Meaning-bearing role markers enter only where the task permits them.

Actual delivery adds the existing observations: input identity, selected semantic answer, all three scores and loss from the actual forward path, correction timing, update identity, and checkpoint identity. Mandatory score capture should fail admission when unimplemented, rather than silently producing an entire run of missing values.

Count compiled events, neural presentations, supervised decisions, optimizer updates, within passes, cross-face passes, return passes, fully delivered rounds, and distinct families separately.

## 10. Avoid learning the label instead of the concept

During worked training the labels 1..6 are legitimate guidance. In evaluation:

- For a role-recognition question, hide the query's true face number, face name, path, and any schema discriminator that reveals it. The number among the answer choices is allowed.
- For a content-application question, the requested face role may remain visible, but all candidate answers have that role. The model must inspect their differing contents.
- Preserve cube identities and endpoints. Do not pool every face into one indistinguishable vector.
- Check relevant rewiring, harmless renaming/reordering, and matched-length wrong alternatives through the real numerical path.
- Compute public IDs, masks, candidate ordering, and encodings independently of private targets. A correct loss label is not itself leakage; its use in public construction would be.

Same-role examples can differ in structure. Same-structure examples can differ in wording. Same-word examples can differ in relationships. Include all three contrasts in teaching.

## 11. Data and evaluation

Use several genuinely different source families, not many renamings of the original Bicycle scene. Every cube should supply all six scoped teaching views or remain explicitly incomplete. Do not fill unknown faces with fabricated content.

Assign train, development, and final-test families before constructing cross-cube support/query groups. No cross-split group is allowed. All faces, analogies, renamings, subquestions, and derived lessons from a source family stay in that family's split.

Separate tests of new questions within a known scene, new instances of a familiar structure, and previously unseen structures. Do not claim all three from one panel.

Measure at least:

1. **Face-role recognition:** can the model recognize an unlabelled view on new family content?
2. **Content-sensitive application:** can it use the requested view to choose the correct structure or correspondence?
3. **Return performance:** can it answer an idea-level question after learning across views?

Report each face/task separately and use a macro average across declared task strata. Retain raw counts, paired successes/failures, before/after losses, and actual answers. Report correct-slot distributions, semantic-answer distributions, and constant/majority baselines. Do not repeat a panel where mostly absent/none answers make a high aggregate score trivial.

Do not choose a checkpoint, stop early, alter the schedule, or change thresholds using the final test. Choose a fixed final update for the first bounded experiment. Later assistance fading or adaptive scheduling would need a declared development-only policy.

## 12. The first comparison

Use two learners with matched initial weights and identical architecture, adapter, tokenizer, choices, targets, task counts, update counts, teacher information, and output recording:

- **CFC_LOOP:** the coherent WITHIN -> ACROSS -> RETURN schedule.
- **MIXED_ORDER:** the exact same completed learning-event multiset in a fixed shuffled order.

Keep the internal support/context of each event intact in the control. Do not destroy the correct labels, remove analogies, or deny it information that the loop condition receives. The intended experimental difference is the grouping and ordering of events.

Use separate optimizers and checkpoints for the two learners. Do not train the second learner starting from the first learner's final weights.

This first comparison tests whether the alternating organization helps beyond the same instructional material delivered in a mixed order. It does not isolate the value of each face, prove CAS-specific architectural superiority, or establish an unrestricted reasoning machine.

A single-seed feasibility result is preliminary. Any advantage claim must use the predeclared analysis on the paired held-out families and later replication; do not manufacture a mastery verdict from an arbitrary post-run threshold.

## 13. Implementation and delivery without another preparation spiral

Reuse the existing cube validator, teacher verification, candidate runner, telemetry, checkpoint writer/verifier, and cloud lifecycle. Add the smallest versioned cube-task adapter, loop scheduler, and their tests. No new launcher, MCTS, learned reward model, external memory service, or autonomous theory generator is requested.

The builder should complete the bounded non-neural implementation, exported-package checks, and a final costed execution request in one work package, rather than returning for permission after every ordinary integration step.

The actual package must demonstrate with non-neural fixtures that:

- all six face task profiles carry their intended content and have valid targets;
- ambiguity, private-target-dependent inputs, and invalid correspondence are rejected;
- the two schedules contain exactly the same event multiset;
- learner/optimizer state persists across phase changes;
- prediction capture, correction, update, snapshots, and checkpoint delivery occur in order;
- unsupported numerical delivery cannot be counted as a completed round.

Stubs verify software behavior only. Real tensor separation, gradients, and learning must be measured in the eventual authorized GPU job. Put required numerical admission checks inside that job, followed by training if they pass; do not propose a paid micro-job for every stage.

Preserve existing readout/answer-bias investigations. Findings about an active encoding or scoring defect must be resolved or explicitly bound before interpreting a new teaching result. The new schedule is not a cure assumed in advance.

The final execution request binds the real package, adapter, both schedules, datasets, budget, runtime limits, initial state, evaluation rule, and checkpoint-delivery/cleanup policy. Build permission and paid-execution approval are separate. Do not fill an owner signature or launch from this document.

## 14. Completion target

Return:

- one concrete, machine-facing within/across/return round with all its exact public inputs and separate teacher targets;
- one implemented schedule manifest with derived exposure counts and one matched mixed-order manifest;
- the real task-binding table, including any explicitly versioned adapter change;
- tests against the actual exported package and a costed, bounded run request.

If a phase is still presentation-only, say which task is not connected. Do not report CFC implemented by running the old component worksheet under a new name.

**Central instruction:** Teach the idea, teach the view, return the view to the idea, and repeat with content-bearing corrections. The loop must connect learning tasks, not just document headings.

## Source basis, distinguished from this proposal

- **Cube Node Schema v0.1**, sections 2, 5, 7–10: face meanings, correspondence, repetition, teacher/learner separation, and adapter requirements.
- **CUBE_TEACHING_PROFILE_001**, sections 1–2: existing seven-stage preparation and the distinction between stored presentations and numerical teaching.
- **TASK_BINDINGS**, sections 2–4: existing graph-task bindings and unsupported face-specific exercises.
- **CANDIDATE_RUN_001**, sections 1–2: reusable candidate-runner entry point and ordered observation/update/checkpoint infrastructure.

The two-axis loop, numerical scheduling example, new face task profiles, and matched-order experiment in this document are new proposed design choices. The sources do not establish that this loop will improve learning.
