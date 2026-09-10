# CUBE NODE SCHEMA v0.1 — first bounded deliverable (data only)

**Owner directive:** the schema's §14 handoff — "Prepare a DATA-ONLY example using
the six-node scene in Section 6 … Then compile one guided and one unassisted lesson
for each existing graph operation, with targets separate and visibility recorded."

**Status of this record:** data work only. Nothing was trained, reserved, launched,
or sent to a GPU. No accepted model, retained checkpoint, registered curriculum or
panel, or paid-run decision was touched. The prepared zero-update contrast probe is
still pending an owner decision and is unchanged by this work.

**Claim state reached:** *schema valid* — the first of the five states the schema
keeps apart in §12 (schema valid → lesson delivered → practice improved → fresh
transfer demonstrated → accepted integration). This record does not reach the second
state: no module ever received a lesson, so there is no delivered teaching, no
practice measurement, and no transfer claim.

---

## 1. Pinned inputs (source identity)

The two delivered files were copied unchanged into this homebase and pinned:

| Pinned file | Origin | Bytes | sha256 |
|---|---|---|---|
| `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_node_001/Cube_Node_Example_v0.1.json` | `C:\Users\wakil\Downloads\Cube_Node_Example_v0.1.json` | 29,971 | `9e62538b807d0b7a6fc04890c4ee0504db53e45bc34b62504f001d7f0610eb32` |
| `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_node_001/Cube_Node_Schema_v0.1.md` | `C:\Users\wakil\Downloads\Cube_Node_Schema_v0.1.md` | 25,974 | `0f12fe19674658670668104e88e7d2c3afb9ad868b79734135c0ee6b89ad015b` |

The check tool re-reads the delivered copy on every run and reports whether the
pinned bytes still match it. This run: **match = true**. Sources are recorded in
`SOURCE.json` next to the pinned inputs.

Canonical bundle digest: `b3df2633ec6a49c6ad81d1572334ac00bcd123d09672d7a53a05979fc70b2c16`.

## 2. What was implemented

Three files, all inside the composition root:

- `cas_meta2/graph_teaching/cube_node.py` — the `cas.cube-node/0.1` data contract as
  executable validation, plus the lesson compiler, the seven-stage cycle, the §12
  contrast set, and the §8 leakage boundary.
- `tests/test_graph_teaching_cube_node.py` — 21 tests, all passing.
- `tools/graph6_cube_node_check.py` — the deterministic reading that produced
  `CUBE_NODE_CHECK.json` (80,153 bytes, sha256
  `1df29252dbf3a69f54726ff6f22208f0ad50fc9843f28a5b32fb95ff87226651`).

Nothing else was created. No launcher, no worker, no package, no adapter, no neural
head, no 3D renderer, no memory service — the exclusions §14 names.

### 2.1 The delivered bundle validates as written

`validate_bundle` accepts the delivered bundle with no changes: 6 cubes, 5 contains
branches, 3 views, 1 correspondence table, and the context declares its `contains`
inventory complete. Every §12 invariant that the data alone can decide is checked
and fails closed with a `CUBE_` code:

| §12 check | Implementation |
|---|---|
| Core and faces | exactly one core with the three declared fields; exactly the six face keys; an `unknown` or `not_applicable` face must be empty **and** carry an explanation |
| Referential integrity | node, branch, endpoint, commonality referent, view label, branch ref, mapping, role row, and provenance references must all resolve inside the pinned bundle |
| Scope and direction | `contains` is whole → direct constituent; the commonality referent must be the target; self-containment and `contains` cycles are refused; undeclared predicates are refused (`corresponds_to` and `depends_on` need a declared relation profile first) |
| Analogy fidelity | every role row must agree with each view's own label; every relation row must carry each view's own relation label; `exact_on_declared_scope` requires a row for every branch |
| Semantic nulls | unknown ≠ not applicable ≠ missing key ≠ empty list ≠ masked, each with a distinct meaning and a distinct refusal |
| Relevant contrasts | renaming, reordering, rewiring, and the analogy presentation are computed and compared |
| Leakage boundary | the learner view is compiled separately from the teacher target, and target mutation is tested against the frozen public encoding |
| Scope of updates | parameter changes, data edits, and presentations are reported as separate counts |

Two independent consistency rules tie the faces back to the stored branches:

- a cube's decomposition face must list exactly its own outgoing `contains` branches
  when it declares `complete` (`CUBE_FACE5_DIRECT_BRANCH_MISMATCH`);
- a cube's context face may only reference branches incident to that cube
  (`CUBE_FACE2_FACT_NOT_INCIDENT`), and a story step may only use branches outgoing
  from that cube (`CUBE_FACE6_BRANCH_NOT_OUTGOING`).

**The structural rules reproduce the delivered example exactly.** Re-deriving the
faces and the correspondence rows from the branch table alone returns the pinned
bundle byte-for-byte under canonical JSON (`test_rebuild_reproduces_the_delivered_bundle`).
That is the strongest available statement that the implemented rules match the
authored example rather than a rule set invented beside it.

### 2.2 The three worked answers reproduce from the unchanged checker

The cube is compiled into the existing exercise contract and the answers are
computed by `reference.py`, unchanged — no new answer logic was written:

| Operation | Question | Answer computed | Schema §6 says |
|---|---|---|---|
| `LIST_PARTS` | Bicycle | `["Frame", "Wheel"]` | `[Frame, Wheel]` |
| `FIND_SHARED_PART` | Bicycle, Cart | `Wheel` | `Wheel` |
| `REACHED_VIA` | Rim, Bicycle | `via:Wheel` | `via:Wheel` |

The cube can ask 51 questions in total (6 `LIST_PARTS`, 15 `FIND_SHARED_PART`, 30
`REACHED_VIA`) and none was rejected for ambiguity in the delivered scene. In a
variant where Cart also contains Frame (a second shared constituent), the
shared-part question for (Bicycle, Cart) is **rejected** with
`FIND_SHARED_PART_MULTI_ANSWER` rather than quietly scored — §9's rule.

### 2.3 Lessons: public view and private target are separate objects

Six lessons were compiled: one guided and one unassisted for each of the three
existing operations. Each lesson carries:

- a **learner view** (family, task id, view, operation, assistance level, question,
  the three ordered choices, the public graph scope, the visible and masked field
  paths, provenance) — and no target key of any kind;
- a **teacher target** (expected answer, declared correct choice index, worked
  solution, corrective feedback, and whether it was delivered).

Choice order is fixed by a digest of **public content only**. So changing which of
the three public choices is declared correct leaves the learner's bytes untouched —
verified for all 6 lessons against 2 alternative targets each, on both the learner
view digest and the frozen public-record digest from `public_records`. This is the
one place where the cube is deliberately stricter than the existing lesson records:
`lessons._record` folds `"correct"` into `record_id`, and `adapter.public_records`
derives slot order from `record_id`, so in the existing pipeline slot order does
depend on the private target. Nothing existing was changed; the cube simply does not
copy that property, and the difference is recorded here as an open item for the
owner (§6 below).

**What the mask actually hides.** The scanner resolves every face leaf to the set of
cubes it references (directly, through branch references, or by naming a label in any
view) and withholds every path that references any cube of the answer. For
`LIST_PARTS(Bicycle)` the answer-bearing paths are:

```
node_001.face_2.structured.fact_refs
node_001.face_5.structured.direct_branch_refs
node_001.face_6.structured.steps[1].uses_branch_refs
node_001.face_6.structured.steps[1].text
node_001.face_6.structured.steps[2].uses_branch_refs
node_001.face_6.structured.steps[2].text
node_001.face_6.structured.steps[*].uses_branch_refs
node_001.face_6.structured.steps[*].text
```

Two findings follow from that list, and both are findings about the **delivered
bundle**, not about the schema text:

1. In the delivered example, a whole cube's `face_2.fact_refs` and its
   `face_5.direct_branch_refs` are the *same two branches*. Either one presented
   during a scored list-parts question hands over the answer inventory. Masking only
   face 5 would not have been enough, exactly as §8 warns.
2. Masking is scoped to the cubes the question asks about. Other cubes' faces stay
   visible as teaching context, because the graph scope itself is the legitimate
   evidence for an unassisted part-list task.

Guided lessons withhold nothing and are labelled assisted; unassisted lessons
withhold every answer-bearing path. The two are scored separately.

### 2.4 One complete seven-stage cycle, exactly as a learner would receive it

`compile_cycle` emits all seven stages with per-stage learner payloads, the
withheld leaves marked `[withheld: answer-bearing for this question]`, and the
teacher payload attached only where teaching is delivered (stages 5 and 6). For a
guided cycle of `LIST_PARTS(Bicycle)` the counts are:

```json
{"stages_delivered": 7, "assistance_states_recorded": 7, "complete_cycles": 1,
 "presentations": 7, "corrective_examples": 2, "optimizer_updates": 0,
 "delivered_neural_lessons": 0, "distinct_graph_families": 1,
 "scored_task_tokens": 49, "stage_visible_paths": 88, "stage_masked_paths": 0,
 "elapsed_seconds": null, "elapsed_note": "not measured in this data-only draft"}
```

A cycle counts as complete only when all seven stage deliveries and their assistance
states are recorded, which is §7's rule. **`delivered_neural_lessons` is 0**: this
draft has no module to deliver to, and a compiled cycle is not a delivered neural
lesson. The unassisted cycle of the same question records 0 corrective examples, 16
masked stage paths and 72 visible ones.

### 2.5 Which stages the current three-choice interface can already express

| Stage | Content | Exercise status |
|---|---|---|
| 1 Name/function | core + face 1 | new task profile required |
| 2 Context | face 2 | new task profile required |
| 3 Analogy | face 3 | new task profile required |
| 4 Explicit mapping | face 4 | new task profile required |
| 5 Guided ^6 decomposition | face 5 | **existing interface** (`LIST_PARTS`, `FIND_SHARED_PART`, `REACHED_VIA`) |
| 6 Recomposition/story | face 6 | new task profile required |
| 7 Reinforcement | revisit the cube | **existing interface** (same three ops, declared variations) |

Two of seven stages are expressible with the interface that exists today; five need
a separately specified output vocabulary, loss, and training adapter before anything
could run. Every stage's *content* can be presented as teaching material now — it is
the scored exercise that is missing, not the data.

### 2.6 The §12 contrast set

| Variant | Arrangement (label-invariant) | Answers (label-invariant) | Reading |
|---|---|---|---|
| consistent renaming of the presented labels | preserved | preserved | renaming is not structural novelty |
| harmless reordering (cubes, branches, refs, steps) | preserved | preserved | order alone carries no meaning |
| rewiring `branch_05` from Wheel to Frame | changed | changed (8 questions) | rewiring genuinely alters the representation |
| analogy view (Kit A / Rope / Torch …) | same as context view | same as context view | the analogy is the same lesson family, not an independent test case |

The two consistency rejections also fire as required:

- renaming the presented labels **without** updating the correspondence table →
  `CUBE_MAPPING_ROLE_LABEL_MISMATCH:view_context:node_001`;
- rewiring a branch **without** rebuilding the dependent faces →
  `CUBE_FACE2_FACT_NOT_INCIDENT:branch_05` on full validation, and
  `CUBE_FACE5_DIRECT_BRANCH_MISMATCH:node_002` when the inventory rule is probed on
  its own. Validation fails closed on the first violation, so the two probes are
  reported separately.

The rewiring contrast changed 8 of 51 questions, including
`REACHED_VIA(Rim, Bicycle)`: `via:Wheel` → `via:Frame`, and `LIST_PARTS(Wheel)`:
`["Rim"]` → `[]`. That is the structural behaviour a cube must have.

## 3. The six design-review questions (§14)

Every answer is generated from the bundle by `design_review_report`, not written by
hand; the text below is the reading of `CUBE_NODE_CHECK.json`.

1. **What idea is stored?** Six cubes, each with one core (`label`, `kind`,
   `identity_statement`) and six faces. Example: `Bicycle` is `concept`, identity
   statement "The Bicycle idea within toy_scene_01, not a universal real-world
   inventory."
2. **What does each face contribute?** face 1 technical identity
   (`canonical_name`, `definition`, `function`); face 2 context (`view_refs`,
   `fact_refs`, `context_scope`); face 3 analogy (`view_refs`, `mapping_refs`,
   `analogy_scope`, `analogy_limits`); face 4 correspondence (`mapping_refs`);
   face 5 decomposition (`direct_branch_refs`, `completeness`); face 6
   recomposition (`steps`, `sequence_kind`). All six are `populated` in the
   delivered example; no face is unknown, masked, or invented.
3. **What does each branch assert?** Five stored branches, each naming a predicate
   and a commonality: `Bicycle contains Wheel`, `Bicycle contains Frame`,
   `Cart contains Wheel`, `Cart contains Platform`, `Wheel contains Rim`. Every
   commonality referent is the branch's own target. No computed intersection,
   reachability answer, or solved list is stored.
4. **What reaches the learner?** For an unassisted lesson: the public graph scope
   (cubes and `contains` facts), the question, and three unmarked choices — plus the
   technical identity of the asked cubes. Withheld: the decomposition inventory, the
   context fact list, and the recomposition story on those cubes. `LIST_PARTS`
   encodes to 49 tokens; `FIND_SHARED_PART` and `REACHED_VIA` to 50 each.
5. **What is the learner expected to predict?** One of three public choices:
   a complete direct-part list, a single shared constituent, or a reach label
   (`direct` / `via:<constituent>` / `absent`).
6. **What feedback teaches it?** The teacher target's worked solution and corrective
   feedback, delivered during guided instruction (stages 5 and 6) and withheld
   during an unassisted test, where it exists only as a scoring reference.
7. **What evidence would show improvement?** The schema's own separation: schema
   valid (reached here) → lesson delivered → practice fit improved → fresh transfer
   demonstrated → accepted integration. This record supports only the first, and the
   existing measured result stays as it is: `VARIED_CURRICULUM_NOT_ESTABLISHED` from
   attempt 004, with the cube proposal carrying **no** evidence that it improves
   learning.

## 4. What this work does not claim

- It does not claim that a cube representation improves learning. No cube lesson has
  reached any module; the only graph-learning measurement remains attempt 004's
  negative result.
- It does not claim that the six faces fix the list-length or readout hypothesis
  (§10). No adapter was built, and the hypothesis stays unmeasured.
- It does not claim that the faces are understood by a learner. A face's existence
  is not evidence of comprehension (§11).
- It does not claim that the bundle is ready to feed to a module as it stands. §14
  says it is an authoring example, not an unassisted test input, and the leakage
  report shows why: two of its faces hand over the answer for two of the three
  operations.
- It does not claim that the delivered example is a good teaching scene. It is
  authored fixture data; its facts are the lesson, not claims about bicycles.

## 5. Gaps and open items (reported as gaps, not as plans)

1. **No numeric adapter exists.** §10's requirements (token-to-row lookup, face and
   role binding, pooling, scale, dtype and device placement, readout, invalid-ID
   errors) are unimplemented. The cube stops at the data boundary on purpose.
2. **No materialization profile.** §11 asks for declared limits on loaded nodes,
   visited branches, depth, and tokens, with exceeding a bound reported rather than
   silently truncated. Not implemented; the delivered scene is tiny.
3. **Cache keys are not implemented.** §11 wants encoded views cached by content
   revision, encoder identity, and visibility profile. There is nothing to cache yet,
   and the assisted-versus-unassisted separation currently holds because the compiler
   emits both objects explicitly.
4. **Selecting the askable questions is a policy decision.** The compiler enumerates
   all 51 questions in the scene and selects one per operation by a stated rule (most
   direct parts; first pair with exactly one shared constituent; first supported
   indirect path). Which questions a real curriculum should ask is a curriculum
   decision, not a schema decision.
5. **The existing lesson records put the private target into `record_id`**, so in the
   current pipeline the option slot order can depend on the target. The cube's
   `record_id` is computed over the public projection only. Aligning the existing
   pipeline is a change to registered records and was **not** made.
6. **The prepared contrast probe is still pending.** It is untouched by this work and
   still awaits an owner decision before any launcher, package, or reservation is
   created for it.

## 6. Recommendation

One recommendation, kept small and evidence-based:

> Keep the cube as a **data** design and review the delivered example with §3 of this
> record in hand. Before any adapter work, decide the two things the data cannot
> decide — which questions a cube lesson should ask, and whether an assisted cube
> presentation is allowed to display face 5 while the same question is being scored.
> If the answer is "no", the mask list in §2.3 (`face_2.fact_refs` and
> `face_5.direct_branch_refs` on the asked cube, plus the face-6 story) is the
> minimum withholding rule, and it is already enforced by the compiler.

No compute, no reservation, and no curriculum change is proposed here. The measured
weak spot from attempt 004 (`LIST_PARTS` at 23/180 = 12.8 % on the frozen panel
versus `FIND_SHARED_PART` at 71/180 = 39.4 % and `REACHED_VIA` at 62/180 = 34.4 %)
is still the open question, and the zero-update contrast probe prepared earlier
remains the smallest measurement that addresses it.

## 7. Reproduction

```
cd <composition root>
python -m tools.graph6_cube_node_check --output <new path>   # deterministic reading
python -m pytest tests/test_graph_teaching_cube_node.py -q   # 21 tests
```

The check tool refuses to overwrite an existing file, so a re-run proves
reproducibility by producing a byte-identical second copy. Verified this run: the
second copy hashes to
`1df29252dbf3a69f54726ff6f22208f0ad50fc9843f28a5b32fb95ff87226651`, identical to
`CUBE_NODE_CHECK.json`.

**Suite reading (exact numbers, no rounding):** the new file adds 21 tests and all 21
pass. The whole graph selection reads `295 passed, 11 skipped, 5203 deselected, 6
errors`; excluding the new file reads `274 passed, 11 skipped, 5224 deselected, 6
errors`, so exactly 21 tests were added and nothing else moved. The 6 errors are
**pre-existing and not caused by this work**: `test_graph_training_curriculum_worker.py`
and `test_graph_training_delivery_rehearsal.py` stub
`cas_meta2.teaching_cycle.gpu_adapter` through `sys.modules`, but in a full-suite run
the real module has already been imported and bound as an attribute of the
`cas_meta2.teaching_cycle` package, so their `execution_guard` call reaches the real
guard and fails closed with `TEACHING_GPU:LINUX_WORKER_REQUIRED` on this Windows
machine. Both files pass when run alone (`8 passed`). This is an environment-dependent
test-ordering defect in existing infrastructure; it was reported, not changed.

