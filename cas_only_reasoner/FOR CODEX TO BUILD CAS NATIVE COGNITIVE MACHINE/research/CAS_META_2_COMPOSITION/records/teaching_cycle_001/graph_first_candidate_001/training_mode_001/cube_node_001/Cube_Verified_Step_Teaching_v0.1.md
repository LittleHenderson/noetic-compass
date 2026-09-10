# Cube Verified-Step Teaching Schema v0.1
## CUBE_VERIFIED_TEACHING_001: builder implementation directive

**Status:** Proposed, source-informed implementation directive. Implement the bounded data and teaching-compiler work described here. This document does not authorize neural execution, checkpoint loading, a GPU job, a reservation, or changes to accepted models.

**Core requirement:** Teach the decisions inside a whole-part answer, retain a checked reason for each correction, and keep the eventual independent answer separate from those worked solutions.

**Scope of the word verified:** A teaching step is verified against the declared graph and the existing reference semantics. This does not certify the real-world truth of a graph, a learner's internal reasoning, or successful learning.

## 1. Source basis and proposed adaptation

R1 is the supplied rStar-Math v1 paper, *rStar-Math: Small LLMs Can Master Math Reasoning with Self-Evolved Deep Thinking*, sections 3.2-3.4, PDF pages 4-7. It uses code-augmented search trajectories, selects successful traces for policy supervised fine-tuning, and separately trains a process preference model from positive/negative step pairs. Intermediate preference pairs generally share their preceding steps. Its learned judge, MCTS, Q-value machinery, and experimental results are not reproduced by this proposal.

R2 is `CUBE_NODE_SCHEMA_001.md`, uploaded as `CUBE_N~2.MD`, especially sections 2.3-2.5 and 5. It reports an implemented cube validator/compiler, separate learner and teacher objects, an answer-dependent masking scanner, target-dependent identifiers in the older non-cube pipeline, and seven prepared stages but no neural lesson delivery. Only decomposition and reinforcement currently have supported graph exercises.

R3 is `RETROSPECTIVE_CONTAINMENT_001.md`, sections 2-5. It records the list-selection weakness, missing practice predictions and per-choice scores, and a pending contrast probe. The option-length/readout mechanism is a hypothesis, not a result supplied by this directive.

R4 is `PROTOCOL(1).md`, the earlier seven-stage input-binding teaching protocol, especially its stage list, allocation, and assistance sections. Preserve its teach-first principle, but do not transplant that experiment's numerical allocation into this different candidate.

R5 is `ATTEMPT_GRAPH6_CURRICULUM_002_004_RESULT.md`. Preserve `VARIED_CURRICULUM_NOT_ESTABLISHED`, its evidence limitations, and the retained checkpoints.

**Everything normative below is a proposed CAS-specific adaptation, not an implementation supplied or validated by rStar-Math.** Borrow checked intermediate teaching examples and same-context comparisons. Use the existing exact graph checker instead of a learned judge. This is not an rStar-Math reproduction and is not a new CAS ontology.

## 2. Implement now; leave other work alone

Implement a pure-data extension to the cube compiler that produces teacher-checked subquestions, coherent worked traces, contrasting mistakes, separated learner views, and a stage-to-task binding report. Demonstrate the whole compilation and recording path with an explicitly simulated learner transport.

Do not add MCTS, beam search, a process reward/preference model, reinforcement learning, a new neural head, a recurrent controller, an arbitrary-code executor, new Noetic meanings, or an inference-time solver. Do not change token vectors, pooling, list normalization, the readout, or the registered plasticity scope in this work.

Preserve the original cube files, registered curricula and panels, accepted weights, historical negatives, retained checkpoints, pending `contrast_probe.py`, existing launchers, and budget ledger. Candidate-only, versioned additions are permitted; silently migrating old records is not.

Reuse `cube_node.py`, the existing `reference.py` semantics, public codec/tokenizer contracts, and current validation/report machinery. Confirm real signatures in the repository before calling them. This document proposes interfaces, not claims about undocumented callable APIs. Stay out of other agents' in-flight files.

## 3. The first teaching target

Start with **LIST_PARTS**, with smaller **REACHED_VIA** questions explaining which candidate nodes are direct, indirect, or absent relative to the requested whole. Preserve the existing FIND_SHARED_PART and REACHED_VIA final tasks as compatibility fixtures; do not turn this into a new multi-operation campaign.

Use named roles everywhere:

```text
LIST_PARTS:       {whole_id}
FIND_SHARED_PART: {first_whole_id, second_whole_id}
REACHED_VIA:      {whole_id, candidate_id}
```

Map these to the actual frozen reference argument order in one tested wrapper. In particular, do not assume the positional order of REACHED_VIA from its English wording. Preserve `direct`, `via:<constituent>`, and `absent` meanings exactly. Unsupported paths, ambiguity, or multiple shared answers remain explicit exclusions under the existing contract.

For a LIST_PARTS teaching trace, enumerate every other node in the declared public scope as a candidate using a public-only ordering rule. Do not choose only the true parts, only the wrong options, or a target-derived number of subquestions. The teacher checks each candidate's relationship, then checks the complete final list.

The trace contains graph judgments and worked explanations. It is not the model's hidden reasoning, an executed native call chain, or proof that the model followed the same procedure.

## 4. Required records

Use separate typed records, with strict required fields and unknown fields rejected in authority-bearing objects. Reuse the project's declared canonical serializer. Do not add another generic serialization framework.

| Record | Required content | Access |
| --- | --- | --- |
| `LessonContext` | schema version; public context ID; cube revision/view; complete public node/branch scope; declared completeness; candidate universe | Learner-readable graph facts; no derived solution |
| `PublicExercise` | schema version; exercise ID; context ID; task profile; named question roles; exactly three distinct public choices; visibility profile; prefix mode | Learner input after compilation |
| `TeacherTarget` | exercise ID; expected answer and choice ID; grounded explanation; evidence witness; reference-verification status and identity | Teacher/evaluator only, except explicit guided release |
| `StepContrast` | exercise ID; identical public-context reference; positive and negative choice IDs; failed obligation; witness or counterexample | Teacher-only comparison; not a learned judge |
| `TeachingTrace` | context ID; ordered subquestion IDs; final exercise ID; teacher-only decision links; completeness check; all verification results | Worked teaching record, not public graph |
| `CyclePlan` | family ID; seven stages; face references; event kinds; exercise/feedback references; assistance states; repetition configuration | Delivery plan; not a neural-delivery receipt |
| `Observation` | event/phase; execution mode; exact input digest; actual prediction/scores if any; correction timing; source state; update/delivery counters | Evidence, never fed back as unassisted input |

A reference or digest of a private record does not make that record public. Keep teacher-only IDs, witnesses, preferred markers, correctness, and verification failures out of the numerical input.

### 4.1 PublicExercise

```text
PublicExercise {
  schema_version: "cas.cube-verified-teaching/0.1",
  exercise_id: public-content identity,
  context_id: public graph context,
  task_profile: "component-route/0.1" | "whole-answer/0.1",
  question: {operation, named_arguments},
  choices: [{choice_id, value}, {choice_id, value}, {choice_id, value}],
  visibility_profile: "graph-only/0.1",
  prefix_mode: "none"
}
```

Do not add a literal binary output such as YES/NO to the neural vocabulary. The initial component-route profile reuses the existing three-choice REACHED_VIA operation. The whole-answer profile reuses an existing final graph operation. New task meanings or a three-way classifier over explanations require a separate version, not an undocumented wrapper.

### 4.2 TeacherTarget and witnesses

A target is verified only after the unchanged reference checker has recomputed the answer from the public graph, found the answer exactly once among the choices, and validated the proposed evidence. Authored expectations are marked `PENDING_REFERENCE_CHECK` until that happens.

A direct claim cites the actual directed branch. An indirect claim cites the contiguous path permitted by the reference. An absent claim requires a complete relevant inventory and a negative check over it; lack of a witness alone is not evidence of absence. A complete-list claim checks both inclusion and omission against the entire declared direct inventory. Unsupported or contradictory evidence causes rejection, not silent relabeling.

The validator must derive the witness relationship from endpoints and graph facts. Merely checking that a referenced branch ID exists is insufficient. Explanatory text should be generated from these checked facts with fixed templates. Do not treat arbitrary natural-language rationale or successful Python execution as proof.

### 4.3 Same-context contrasts

Each contrast compares a correct and incorrect choice under the same graph, question, visibility, and prefix. For example, `via:Wheel` versus `direct` for Rim relative to Bicycle. Preserve the mistaken choice as an example; never insert it into the factual graph.

Proposed teacher-side reason codes include `DIRECT_VS_INDIRECT`, `FOREIGN_PART`, `MISSING_REQUIRED_PART`, `EXTRA_PART`, `WRONG_WHOLE`, and `INCOMPLETE_INVENTORY`. Use only codes whose predicates are explicitly implemented and checked. These are explanation codes, not new Noetic classes.

Do not implement rStar-Math's Bradley-Terry/PPM loss here. Later authorized learner training uses the declared ordinary correct-choice loss for these small tasks. Multiple contrasts attached to one exercise are not automatically multiple updates.

### 4.4 Identity rules

Build learner-facing exercise identities from public graph facts, named question, candidate choices, public visibility profile, and declared public randomization only. Never include `correct`, targets, witnesses, preference labels, teacher text, or hashes containing those fields in the seed for option order.

Maintain a separate supervision identity that may bind the teacher material. It must not influence the public projection. Reject duplicate IDs attached to different contents. Preserve semantic answer identity separately from its current slot.

## 5. Worked teaching trace

Use the unchanged six-node authored cube fixture:

```text
Bicycle contains Wheel.
Bicycle contains Frame.
Cart contains Wheel.
Cart contains Platform.
Wheel contains Rim.
```

For LIST_PARTS(Bicycle), the teacher's logical sequence is:

| Candidate check | Checked answer | Teaching significance |
| --- | --- | --- |
| Cart relative to Bicycle | absent | Being another whole in the scene does not make it a part. |
| Frame relative to Bicycle | direct | Include a directly contained part. |
| Platform relative to Bicycle | absent | Do not include a part belonging to the other whole. |
| Rim relative to Bicycle | via:Wheel | An indirect constituent is not a direct constituent. |
| Wheel relative to Bicycle | direct | Include the other directly contained part. |
| Complete part list for Bicycle | [Frame, Wheel] | Include every direct part and no others. |

Candidate order above is illustrative public-label order. The implementation freezes an explicit public-only order and permutation rule, not a semantic importance rank.

A useful complete-list choice set is `[Frame, Platform]`, `[Frame, Wheel]`, `[Rim, Wheel]`. The three options have equal item counts. One distractor substitutes a foreign part; another substitutes an indirect part. The checker establishes which is correct after the public options are fixed.

Also retain boundary fixtures with a missing part, an extra part, a complete empty inventory, an unknown/incomplete inventory, ambiguity, consistent renaming, harmless reordering, and a meaningful rewire. Report excluded fixtures separately. A small authored example is not a balanced training dataset or a transfer panel.

**The learner must eventually predict the complete final list itself.** The primary unassisted evaluation must not assemble the answer by filtering teacher-verified component labels. A later rule-assisted composition test would be a distinct operating mode and claim.

## 6. Fit the records into the seven stages

| Stage | Cube connection | Required v0.1 work |
| --- | --- | --- |
| 1 Name/function | Core + Face 1 | Prepare the bounded task definition and explanation. No claim of a trained definition exercise. |
| 2 Context | Face 2 | Present the public graph with directions and endpoints retained. |
| 3 Analogy | Face 3 | Prepare the corresponding fixture view with explicit scope limits. |
| 4 Explicit mapping | Face 4 | Validate the role and relation correspondence across views. |
| 5 Guided decomposition | Face 5 | Compile the component-route exercises and their worked corrections. |
| 6 Recomposition/story | Face 6 | Prepare the checked explanation and a restricted final-answer exercise. This is a proposed binding to LIST_PARTS, not general story comprehension. |
| 7 Reinforcement | Revisit the connected views | Re-present declared variants and the final task under the planned assistance state. |

Retain all seven stages in the cycle data. Do not equate preparing stage content with training it. The existing record reports that five stages lack scored task profiles; this directive does not erase that gap. Stage 6 gains a proposed restricted whole-answer binding, not a new neural text generator. Definitions, analogy, and mapping exercises remain explicit future profiles unless the existing interface actually expresses them.

Report `compiled_stages`, `presented_stages`, `neural_presentations`, `supervised_decisions`, `optimizer_updates`, and `complete_neural_cycles` separately. A complete neural cycle requires real receipts for all declared stage deliveries under an approved delivery profile. Pure compilation always reports zero neural delivery and zero updates.

## 7. Teaching and independent measurement

Use three distinct event phases:

**DEMONSTRATION:** The teacher may show Face 5, a worked trace, and a final answer. Any model response is assisted. This is instruction, not proof of independence.

**PREDICT_THEN_CORRECT:** The learner receives a fixed public exercise without its solution, produces a prediction, and only then receives the target and correction for a training update. Record both events in order. Use repeated guided cycles before an independent readiness decision. An incorrect practice response is an opportunity for correction, not a mastery failure.

**UNASSISTED_MEASUREMENT:** No worked solution, gold prefix, target witness, teacher-verified intermediate answer, or inference-time checker selection reaches the learner. Record the answer before evaluation. No correction or update occurs during this pass.

The primary final-answer exercise uses `prefix_mode: none`: each call receives the declared graph and task, not previous correct subanswers. Teaching can change weights between practice tasks, but this profile adds no cross-call hidden state. If a later profile supplies teacher prefixes, label it assisted and compare it separately. If it supplies learner-generated prefixes, preserve its errors rather than replace them with gold.

The minimum guided cycles per family, final-task fraction, operation mix, and stopping allocation belong in a future owner-approved experiment profile. Preparation must expose these fields and refuse an executable profile with them unset. Do not reuse 64 updates or the older 1,024-cycle allocation as an unexamined default. No indefinite repeat-until-pass loop.

## 8. Prevent answers from entering through the side door

The new compiler must use a fixed visibility policy by task and assistance phase, not answer-node-dependent masking. For `graph-only/0.1`, provide the full allowed raw graph, question, and three unmarked options. Withhold derived inventories, solved intersections, worked paths, narrative solutions, teacher receipts, and correction fields consistently across the accessible scene. A separate assisted event may explicitly release those fields.

This tightens the new candidate path without silently rewriting the frozen cube-001 or legacy pipeline. Record the versioned difference.

Test target independence through the complete public compile -> visibility -> ID -> choice permutation -> codec path. The public compiler must not accept TeacherTarget as an argument. With valid public material fixed, each alternate private target leaves public bytes and public order unchanged; independent teacher validation may reject the alternate target afterward. Do not force false targets to become semantically valid merely to pass this test.

Keep all renamings, analogies, subquestions, worked traces, and final questions from one underlying family in one split. A three-view lesson is not three independent examples. Final material must not be used to fit the tokenizer, choose lessons, construct corrective targets, or tune the pending contrast probe.

Do not include private evaluator files in the learner's mounted input set for a later final evaluation. A digest proves binding, not that answers were inaccessible or opened later. Capture the actual prediction-commit and target-open order using the existing evaluation boundary.

If an encoded cache is used, key it by exact public bytes, encoder identity, and assistance/visibility profile. Reuse the existing cache mechanism or use no cache for this small fixture. Never reuse a worked-example encoding for an unassisted input.

## 9. Numerical integration boundary

The immediate deliverable stops before neural execution. Produce a `TASK_BINDINGS.md` showing how each supported exercise maps to the actual graph adapter, public-record codec, tokenizer, candidate ^6 module, choice score, and existing cross-entropy target. List unsupported presentation/task bindings explicitly.

Do not invent callable signatures. Use one tested compatibility wrapper where needed. Pure codec fitting/encoding may run only under the project's existing local permissions; no tensor construction, checkpoint neural restore, CUDA, or provider calls are part of this handoff.

In a future authorized neural implementation, only the existing `operation:^6` candidate scope is eligible. Freeze encoder/projection, accepted modules, and readout unless a separately approved diagnosis justifies a versioned change. The present list-length concern is not declared fixed by shorter component questions.

Counter checks must distinguish an informative update from merely changed weights. Log actual choices and per-choice logits, token/item lengths, and option norms when the authorized numerical path exists. Expose missing observations as unavailable, not zero. Sum-pooled list length can be a diagnostic variable without becoming a new input that reveals the correct answer.

This is a training-content change, not permission to add a hidden inference algorithm. Syntax validation may reject malformed data; it may not eliminate semantically wrong choices until only the correct one remains in an unassisted prediction.

## 10. Verification and failure semantics

A `TeachingTrace` is admissible only when every component answer, each used evidence witness, and the final answer agree with the existing reference semantics. A correct final answer does not rescue a false intermediate explanation. Preserve false-step examples separately as negative contrasts; do not concatenate them into an approved positive trace.

Use bounded teacher-side graph traversal or the existing checker, not an LLM judge or arbitrary Python generated by a model. Record the checker identity. Conditions such as incomplete inventories, unsupported paths, and multiple valid answers must appear as explicit construction rejections. Validation excludes unsupported cases; it does not establish broader semantics.

Proposed construction outcomes are `SCHEMA_INVALID`, `REFERENCE_MISMATCH`, `UNSUPPORTED_CASE`, `PUBLIC_BOUNDARY_FAILED`, and `TEACHING_DATA_READY_NEURAL_UNTESTED`. These are compiler statuses only. No PASS for learned skill follows from them.

## 11. Required tests in one suite

Reuse existing fixture, mutation, and check infrastructure. Cover these independent behaviors:

| Area | Required test |
| --- | --- |
| Reference compatibility | The three original worked answers reproduce; named-role wrapper catches a reversed REACHED_VIA call. |
| Direct versus indirect | Rim is not a direct Bicycle part; the wrong direct claim is rejected even when the final list is correct. |
| Completeness | Missing/extra list members are detected; unknown inventory is not treated as an empty complete one. |
| Evidence binding | A real but wrong branch ID, reversed endpoint pair, and noncontiguous path do not validate a claim. |
| Unchanged context | Positive and negative step choices compare under identical public inputs, not different graphs. |
| Alternative correctness | An equivalent correct choice is not mislabeled a negative; duplicate semantic options and ambiguous tasks are refused. |
| Public boundary | Target mutation traverses the complete public pipeline without changing masks, IDs, candidate order, or encoded bytes. |
| Raw facts retained | Unassisted inputs still contain every raw fact needed for the task but no derived answer inventory. |
| Assistance | Guided release is recorded; unassisted mode cannot read the released target or an assisted cache. |
| Contrasts | Consistent renaming preserves meanings, harmless unordered graph reordering preserves answers, meaningful rewiring recomputes dependent faces and answers. Preserve meaningful story-step order. |
| Shortcuts | Record correct-slot and answer-length distributions; exercise equal-length list distractors and `none` as both correct and incorrect when applicable. |
| Delivery truth | A seven-stage compiled or simulated walkthrough yields zero actual neural cycles and zero optimizer updates. |
| Replay/output | Repeated pure compilation produces the same canonical contents and refuses output overwrite. |
| Scope | The implementation cannot import neural/provider code or modify protected files during this preparation. |

Do not use the builder's total test count as a learning metric. Report pre-existing failures separately rather than weakening guards or hiding errors.

## 12. Minimal implementation and deliverables

Preferred placement, relative to `research/CAS_META_2_COMPOSITION`:

```text
cas_meta2/graph_teaching/verified_teaching.py
  # Or a small extension to cube_node.py if it avoids duplication.
tests/test_graph_teaching_verified_teaching.py
tools/graph6_cube_node_check.py
  # Extend the existing checker; do not create another launch framework.
records/.../training_mode_001/cube_verified_teaching_001/
  DESIGN.md
  TASK_BINDINGS.md
  public_contexts.jsonl
  public_exercises.jsonl
  teacher_targets.jsonl
  teacher_traces.jsonl
  cycle_plan.json
  check_report.json
  SOURCE.json
```

Reuse an equivalent existing file instead of duplicating it. JSONL boundaries are proposed teaching artifacts, not cloud services. Bind inputs to repository-relative paths and hashes. An optional check against an external Downloads copy must not be required for a clean-checkout build.

Deliver the unchanged six-node scene, one detailed LIST_PARTS teaching trace, a guided and unassisted final exercise for each existing operation, the coherent seven-stage plan, and the edge cases from section 5. Separate public and teacher artifacts in the demonstration. A scripted fake predictor must be labeled `SIMULATED`, and its responses must never count as neural observations.

Return one review record containing: exact files changed; added/passing/skipped/failing tests; counts by operation, family, and stage; unsupported bindings; rejected cases; demonstrated privacy/identity boundaries; and any unresolved implementation decision. Do not report the entire schema as neural-ready merely because compilation succeeds.

## 13. Definition of done and stop point

The builder's output must show, for every scored teaching event:

> Here is the graph the learner would see. Here is the exact question and candidate set. Here is the choice it must predict. Here is the teacher's checked correction and its graph evidence. Here is when that correction would be revealed and used for an update.

It must additionally show one entire seven-stage cycle while stating which stages are prepared presentations, which are supported prediction tasks, and which still lack a numeric delivery binding.

Completion status: **`TEACHING_DATA_READY_NEURAL_UNTESTED`**. All neural execution, optimizer updates, reservations, launches, and capability promotions remain zero.

The next decision is whether this concrete teaching path should be connected to the candidate after considering the pending readout/contrast findings. Do not request a new paid campaign automatically. No new model architecture is authorized by this directive.

## 14. Future experiment boundary, not a launch plan

When the owner authorizes an actual experiment, preregister a comparison of final-answer-only teaching against checked intermediate teaching with an explicitly matched total supervision/compute budget. More component decisions are additional supervision, not free work. Record presentations, targets, updates, graph families, tokens, and wall time separately. Report final unaided whole-task accuracy separately from subquestion accuracy, worked-example accuracy, and any teacher-prefix score.

Use newly reserved evaluation families, not earlier opened panels disguised by renaming. Preserve fixed thresholds, failed seeds, the original negative results, and actual checkpoints. Inspect numerical relations, choice scores, and scoped changes through the admitted AWS path in the same bounded job rather than a chain of additional paid diagnostics.

This section does not prescribe a new budget, alter the current registered threshold, or authorize a run.

---

**Builder instruction in one sentence:** Implement a small, deterministic teacher that turns the existing cube graph into checked component decisions and a complete worked answer, compiles them into the existing lesson interfaces, and never lets the teacher's solution substitute for the learner's independent result.
