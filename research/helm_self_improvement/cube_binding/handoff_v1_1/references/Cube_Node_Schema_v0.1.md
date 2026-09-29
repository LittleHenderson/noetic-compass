# Cube Node Schema v0.1
## One inner core, six teaching faces, explicit connections

**Project:** CASformer / graph-first targeted ^6 teaching  
**Concept origin:** Little Henderson  
**Specification status:** PROPOSED DESIGN; implementation and neural behavior unverified  
**Schema namespace:** `cas.cube-node/0.1`  
**Authorization scope:** A document and illustrative data, not a model change or paid-run authorization.

> A cube is one idea represented through six named views. Its core anchors what the views refer to. Its branches preserve how that idea relates to other ideas. A CJT learns to operate on the supplied information.

## 1. Basis and boundary

The owner's proposed geometry supplies the structure: one inner core and six faces. The earlier teaching protocol supplies the sequence: name/function, context, analogy, explicit correspondence, guided ^6 decomposition, recomposition, and reinforcement. The field names, validation rules, and access profiles below are NEW PROPOSALS that turn those ideas into a draft data contract. They are not claimed to be an existing CAS language standard.

The existing graph-first design defines nodes as idea boxes, branches as connectors, and three whole-part exercises: `LIST_PARTS`, `FIND_SHARED_PART`, and `REACHED_VIA`. This proposal preserves those meanings while giving each node structured teaching views. The current experimental result and retained checkpoints remain unchanged.

A cube is a data object, not automatically a neural module, a physical processing cell, or seven separate neuron groups. Six faces do not mean six maximum neighbors. A face can reference many facts or links; an idea can contain any number of declared parts subject to an experiment's resource limits. Three-dimensional rendering is optional and has no computational authority.

In this document, MUST means required by this proposed schema, not a new rule imposed on the accepted runtime.

## 2. Stable anatomy

| Component | Stored role | Plain question |
|---|---|---|
| `core` | Stable identity and intended meaning of this node in its declared context | Which idea are these views about? |
| `face_1` | Technical name, definition, and function | What is it, and what does it do? |
| `face_2` | Context, environment, and observed or authored interactions | Where does it occur, and what surrounds or acts on it? |
| `face_3` | Analogy, metaphor, or simile with a declared scope | What other presentation illustrates the same relationship? |
| `face_4` | Explicit technical/context/analogy correspondence | Exactly which things and relationships correspond? |
| `face_5` | Contained parts and structural inspection | What belongs inside this idea, and how is it connected? |
| `face_6` | Recomposition and story/process presentation | How do the parts form the whole or participate in the process? |

The core is the reference anchor, not a second copy of every explanation. `face_1` supplies the expanded teaching explanation. A core statement is authored knowledge with provenance, not proof of a metaphysical essence.

**Numbering distinction:** `face_5` is the decomposition teaching face associated with the intended Male/^6 lesson. `face_6` is the recomposition face. Face numbers are not Noetic numbers, CAS Drive numbers, or new operator IDs. The inner core is not Noetic ^0.

**Repetition is not another face.** It is the teaching process that revisits and connects all six faces around the same core.

## 3. Logical record contract

A cube record has this shape. This is a data-contract sketch, not executable Python or a completed JSON Schema validator:

```text
CubeNode {
  schema_version: "cas.cube-node/0.1",
  node_id: opaque stable string,
  revision: positive integer,
  context_id: string,
  core: {
    label: string,
    kind: "concept" | "instance" | "event" | "procedure",
    identity_statement: string
  },
  faces: {
    face_1: TechnicalFace,
    face_2: ContextFace,
    face_3: AnalogyFace,
    face_4: MappingFace,
    face_5: DecompositionFace,
    face_6: RecompositionFace
  },
  provenance_refs: [reference, ...]
}
```

Every face uses the same envelope:

```text
Face {
  availability: "populated" | "unknown" | "not_applicable",
  human_text: string,
  structured: face-specific object,
  provenance_refs: [reference, ...]
}
```

All six face keys MUST exist. `unknown` and `not_applicable` MUST carry an explanation; their `structured` object is empty. Missing knowledge must not be filled with fabricated content merely to complete a cube. A masked learner view is different from an unknown authoring face: the view records that content was deliberately withheld.

Identifiers are reference handles, not privileged semantic hints. Renaming a display label must not redirect a branch. Each experiment pins the exact node revisions it consumes. Source provenance and family/split identifiers remain audit metadata rather than hidden answer features.

### Face-specific structured content

| Face | Minimum structured content when populated |
|---|---|
| `face_1` | `canonical_name`, `definition`, `function` |
| `face_2` | `view_refs`, `fact_refs`, `context_scope` |
| `face_3` | `view_refs`, `mapping_refs`, `analogy_scope`, `analogy_limits` |
| `face_4` | `mapping_refs` identifying explicit role and relationship correspondences |
| `face_5` | `direct_branch_refs`, `completeness`: `complete`, `partial`, or `unknown` |
| `face_6` | `steps`: ordered records containing `step_id`, `text`, and `uses_branch_refs`; also `sequence_kind` |

`direct_branch_refs` are references to stored facts, not copies of target answer strings. For `face_6`, `sequence_kind` distinguishes an explanatory order from a claimed temporal or causal sequence. A story's order alone does not establish causation.

The cube store holds facts once. Faces reference those facts. Contradictory views produce a validation issue; six restatements of one source do not count as six independent pieces of evidence.

## 4. Branches, commonality, and nesting

A branch is the typed connector between cubes. It is stored in the graph's branch table, not duplicated inside both endpoint nodes:

```text
Branch {
  branch_id,
  context_id,
  source_node_id,
  predicate,
  target_node_id,
  commonality: {kind, referent},
  provenance_refs
}
```

The initial teaching profile uses `contains`. Its direction is whole to direct constituent. The commonality names the constituent that participates in both the whole's composition and the part's own identity.

`corresponds_to` and `depends_on` may be recorded under separately declared relation profiles. Correspondence is a scoped analogy or role match, not literal identity. Dependency is a prerequisite statement, not automatically a proven cause. These relation names register data semantics only; they do not add executable CAS operations.

For example, in an authored concept graph:

```text
Bicycle --contains--> Wheel
Cart    --contains--> Wheel
Wheel   --contains--> Rim
```

Bicycle and Cart meet at the Wheel sub-idea. That is the shared constituent. The graph does not imply that two real objects literally use the same physical wheel: these nodes represent concepts in an explicitly declared teaching scene.

Wheel may have its own core and six faces. Thus a contained idea can itself be decomposed without changing the schema. Nesting uses references, not recursive copies of full cubes. The graph profile rejects cycles in `contains`; other relationship types require their own cycle policy.

A face number does not constrain where a branch may be drawn in an interface. Changing the picture's orientation must not change its meaning.

### Direct, indirect, absent, and unknown

`LIST_PARTS(W)` asks for direct constituents of W. `REACHED_VIA(W, X)` distinguishes a direct edge, a supported indirect path, and absence within the declared graph. Shared-part reasoning compares direct constituents unless a task explicitly requests another scope.

An empty list is not automatically evidence of no parts. Negative answers require declared completeness. In an open or incomplete graph, missing support means unknown, not absent. A bounded closed-world teaching fixture may explicitly declare its relation inventory complete.

Do not store computed intersections, reachability answers, or solved lists as extra answer edges in a learner's input. Derived conclusions belong in a separate prediction record. The public graph may supply the edges from which a learner must reason.

## 5. The golden-thread correspondence

A `ViewMapping` connects different presentations of the same bounded formal lesson:

```text
ViewMapping {
  mapping_id,
  lesson_family_id,
  view_ids,
  node_role_rows,
  relation_rows,
  coverage: "exact_on_declared_scope" | "partial",
  unmapped_items,
  limits,
  provenance_refs
}
```

Each node-role row identifies a role and its technical, contextual, and analogical presentations. Relation rows identify which directed relation is preserved between mapped endpoints. Merely placing three nouns in a row is insufficient.

The 1:1:1 requirement applies to the DECLARED CORRESPONDING ROLES. It does not assert that a bicycle and an explorer's kit are identical objects, or that all their real-world properties match. Partial analogies identify their unmapped properties instead of inventing total correspondence.

All presentations of one lesson family stay together for split assignment. A renamed analogy of a training lesson cannot silently become an independent final-test family.

## 6. Worked cube: the Bicycle idea

This is a deliberately incomplete model of everyday objects but a COMPLETE authored graph within `toy_scene_01`. Its facts are the lesson, not universal claims about bicycles or carts.

```text
Bicycle contains Wheel and Frame.
Cart contains Wheel and Platform.
Wheel contains Rim.
```

**Core:** The Bicycle idea in `toy_scene_01`.

**Face 1, technical:** A whole whose declared direct constituents in this scene are determined by its outgoing `contains` branches. The taught operation identifies direct constituents, not every visible node.

**Face 2, context:** The same graph rendered with the Bicycle, Cart, Wheel, Frame, Platform, and Rim labels. A learner can inspect where each connection starts and ends.

**Face 3, analogy:** Kit A contains Rope and Torch. Kit B contains Rope and Cloth. Rope contains Strand. This models conceptual composition, not shared physical ownership or equivalent physical functions.

**Face 4, mapping:**

| Role | Formal view | Context view | Analogy view |
|---|---|---|---|
| Requested whole | A | Bicycle | Kit A |
| Shared constituent | B | Wheel | Rope |
| Other constituent of A | C | Frame | Torch |
| Second whole | D | Cart | Kit B |
| Other constituent of D | E | Platform | Cloth |
| Constituent inside B | F | Rim | Strand |

All three views preserve `A contains B`, `A contains C`, `D contains B`, `D contains E`, and `B contains F`.

**Face 5, decomposition:** Point to the two direct Bicycle branches. Distinguish Wheel and Frame from the indirect Rim and the unrelated Platform. These are worked teaching facts; their visibility during a scored task depends on the task's input profile.

**Face 6, recomposition:** Begin with the Bicycle whole, reconnect Wheel and Frame, and then inspect Wheel's own Rim child. Wheel also connects the Bicycle and Cart concepts as a shared constituent. The narrative is an explanatory traversal, not evidence of a real assembly's temporal history.

Worked answers for instruction are `LIST_PARTS(Bicycle) = [Frame, Wheel]`, `FIND_SHARED_PART(Bicycle, Cart) = Wheel`, and `REACHED_VIA(Bicycle, Rim) = via:Wheel`. The teacher may show these during guided instruction. They must not be exposed as solved fields during an unassisted test of those same questions.

## 7. Teaching cycle: six faces plus reinforcement

The cube is the lesson object. The cycle is the delivery order:

| Stage | Visited content | Teacher and learner activity |
|---|---|---|
| 1. Name/function | Core and face 1 | Anchor the subject; teach its name, function, and the requested operation. |
| 2. Context | Face 2 | Show the idea inside a supplied graph, with relevant and irrelevant neighbors. |
| 3. Analogy | Face 3 | Present a second bounded context expressing the same relationship. |
| 4. Explicit mapping | Face 4 | Connect the roles and directed relations across all three views. |
| 5. Guided ^6 decomposition | Face 5 | Ask small parts questions, demonstrate correct reasoning, and supply corrections. |
| 6. Recomposition/story | Face 6 | Reconnect the parts and apply the complete task to the whole. |
| 7. Reinforcement | Revisit selected faces and the whole | Correct mistakes and repeat the connected lesson with declared variations. |

A core plus six faces gives seven stored components. It does NOT mean seven stored stages: stage 1 uses the core together with face 1; stage 7 is an operation over the cube.

Preserve the owner's instruction to TEACH repeatedly before demanding independent mastery. An experiment specifies a positive minimum of complete guided cycles per family and total guided exposure before readiness checks. This draft does not import the old binding experiment's 1,024-cycle allocation into the different graph specialist without a new budget decision.

Count presentations, corrective examples, optimizer updates, complete seven-stage cycles, unique graph families, tokens, and elapsed time separately. A cycle is complete only when all seven stage deliveries and their assistance states are recorded. A prose lesson that never reaches the learner is not a delivered neural lesson. A passive presentation is not an optimizer update.

Work pauses at the authorized limit and retains its state. Incomplete exposure is reported as incomplete exposure, not failure of the teaching principle. Do not use final-test results to decide how long to keep teaching.

## 8. Learner inputs versus teacher information

Maintain separate objects:

* **AuthoringCubeBundle:** complete source graph, core, all available teaching faces, mappings, and provenance.
* **LearnerView:** the fields explicitly allowed for one presentation or prediction.
* **TeacherTarget:** expected answer, worked solution, and corrective feedback delivered only through the declared teaching or scoring path.

These are actual access separations in a future implementation, not cosmetic dictionary labels. The learner must not receive the full authoring bundle and be trusted to ignore its solved fields.

A lesson specification records `task_id`, `family_id`, `operation`, public graph scope, question, choices, visible-field paths, assistance level, and a separate target reference. Assistance levels are `worked`, `guided`, `hinted`, and `unassisted`. Family and evidence metadata stay out of numerical model features unless explicitly declared as part of the task.

For an unassisted list task, the public graph's raw `contains` facts are legitimate evidence. A precomputed list on face 5, a face-6 story enumerating the requested answer, or a cross-view solution revealing the answer must be withheld or the score labeled assisted. Removing one `answer` field is insufficient if another face repeats it.

With the public exercise fixed, changing the private target MUST leave the learner's input unchanged. The same rule applies to caches and retrieved neighboring faces.

A task may intentionally test recall from a complete cube, reconstruction from masked faces, or inference from supplied edges. Those are different tasks and receive separate scores. Copying a provided face is not evidence of independent graph reasoning.

## 9. Training tasks and integration boundary

The compatibility profile continues to use the existing three graph operations:

| Task | Required learner decision |
|---|---|
| `LIST_PARTS` | Select the complete direct-part list from three public alternatives. |
| `FIND_SHARED_PART` | Select the shared direct constituent or `none` in a complete graph. |
| `REACHED_VIA` | Select `direct`, `via:<constituent>`, or `absent` under the declared path scope. |

A task with several correct single-part or route choices must either use a declared multi-answer profile or be rejected as ambiguous. Do not quietly change the scorer to select an arbitrary answer.

Face-specific learning tasks can be proposed without pretending they are already supported by the current learner:

| Targeted face | Example proposed prediction | Status |
|---|---|---|
| Core + face 1 | Select the definition/function that matches the presented concept. | New task profile required. |
| Face 2 | Select a supplied contextual relation relevant to the question. | Must be mapped explicitly to an existing task or versioned as new. |
| Face 3 | Select the analogy preserving the same directed relationship. | New task profile required. |
| Face 4 | Select the correct role correspondence between two views. | New task profile required. |
| Face 5 | Select the direct-part list, shared part, or route label. | Existing task meanings; cube input adapter still proposed. |
| Face 6 | Select a recomposed whole or valid explanatory sequence from supplied parts. | New task profile unless restricted to an existing route question. |

Missing-face reconstruction is another candidate exercise. All new task profiles must specify output vocabulary, loss, and training adapter before execution. They do not already exist merely because fields now have names.

The first candidate integration should reuse the targeted `operation:^6` module only where its current interfaces can express the declared task. A cube does not create a trainable matrix, a new operation registration, or a new memory permission. Any added encoder, trainable readout, recurrent state, or multi-call objective is an explicit versioned change.

The cube is the information presented to the specialist. The specialist's weights are what learn from that information.

## 10. Numerical and relationship-preservation requirements

A future adapter must preserve distinctions such as:

```text
(node_id, face_id, field_path, value)
(source_node_id, predicate, target_node_id, context_id)
(view_id, role_id, node_ref)
```

It must not flatten every face and branch into one undifferentiated bag of words. Nor is adding a label such as `source` sufficient if later pooling erases which source pairs with which target.

The adapter must document valid token-to-row lookup, face/role binding, pooling, numerical scale, dtype/device placement, and the readout. Invalid internal IDs produce an explicit error; legitimate unknown words follow the declared tokenizer policy. Zero or nonfinite structural vectors are handled explicitly, not silently normalized into plausible features.

Adding the cube does not automatically correct the currently hypothesized list-length/readout effect. Variable-length lists and face text remain variable-length. Preserve and measure answer-order effects, option lengths, vector norms, score gaps, and task-dependent gradients rather than asserting that six slots remove those biases.

No specific neural encoding formula or similarity metric is adopted by this schema. Those remain adapter choices requiring bounded evidence.

## 11. Lightweight storage and test points

Store one core and six small face descriptors per node. Store lengthy prose, large examples, and nested subgraphs by versioned reference. Load only the allowed faces needed by a lesson or query. Cache encoded views by content revision, encoder identity, and the visibility profile so an assisted-view cache cannot leak into an unassisted task.

Do not expand every neighbor's six faces on every call. A materialization profile declares limits for loaded nodes, visited branches, depth, and token count. Exceeding a bound must be reported; silent truncation cannot become a false `none` answer.

The cube supplies places to attach observations, not a requirement to run seven checkers per node per tick. Record schema/reference checks on creation or revision and numerical/learning test points on selected actual executions.

Suggested test points are core/face identity preservation, branch-endpoint preservation, allowed-field visibility, option geometry and scores, gradient/update scope, and committed prediction identity. A face's existence is not evidence that the learner understood it. A measured value identifies the example, view, checkpoint, and assistance state that produced it.

## 12. Validation and evidence rules

A proposed schema-conformance check should cover the following invariants in the existing test framework:

| Check | Required behavior |
|---|---|
| Core and faces | Exactly one core and the six named face keys; unknowns remain explicit. |
| Referential integrity | All node, branch, view, mapping, and provenance references resolve within the pinned bundle. |
| Scope and direction | `contains` keeps whole/part roles, context, and direct-versus-indirect meaning. |
| Analogy fidelity | The declared mapping preserves its listed relations; unclaimed properties remain unmapped. |
| Semantic nulls | Empty, unknown, missing, and masked have different meanings. |
| Relevant contrasts | Rewiring can alter the representation; harmless list reordering preserves meaning; consistent renaming preserves correspondences. |
| Leakage boundary | Private-target mutation cannot alter the compiled public view, including cross-face references. |
| Scope of updates | Actual permitted parameter changes are recorded separately from data edits and mere presentation. |

Schema validity, delivered teaching, improved practice fit, fresh transfer, and accepted-model integration are separate evidence states. None automatically implies the next. Output records retain the learner's selected answer and per-choice scores, not only a correctness bit, so later audits can examine the behavior actually produced.

For training, retain real initial/final checkpoint files, encoder/tokenizer state, configuration, exposure events, and prediction records. An endpoint comparison supports claims only about stored components and endpoints. It cannot prove that unsaved modules stayed unchanged throughout the run.

## 13. Versioning and decisions still required

Node revisions are immutable snapshots. Graph manifests pin their node/branch versions. Changing a fact updates the affected graph/view revisions; dependent example and mapping validation must run against the new snapshot. A model-proposed cube or branch remains a proposal until the existing admission process accepts it.

Before a neural pilot, a separate run plan must choose the supported output profile, visible faces, minimum guided cycles, training budget, comparison condition, split-family definition, numerical tolerances, and success criteria. This schema intentionally supplies no automatic AWS authorization or new pass threshold.

A cube experiment must not silently change the current contrast-probe task, overwrite the retained checkpoints, or promote the specialist. Keep the new data design separate until its implementation is explicitly selected.

## 14. Codex handoff: the first bounded deliverable

Prepare a DATA-ONLY example using the six-node scene in Section 6: cube records, five `contains` branches, the three presentation views, and their correspondence table. Then compile one guided and one unassisted lesson for each existing graph operation, with targets separate and visibility recorded.

Use the current validator/test infrastructure for reference resolution, masking, and round-trip checks. Do not build a 3D renderer, new neural head, new launcher, large memory service, or separate verification campaign for this draft.

Show the exact learner inputs and targets for one complete seven-stage cycle, and count what would constitute a completed cycle. Report which stages are representable through the current three-choice interface and which require a separately specified task extension.

The deliverable is ready for design review when another reader can identify: what the core means, what each face contains, what each branch asserts, what the learner sees, what the teacher corrects, and what evidence would show improvement.

**Central design rule:** keep the identity, six views, relationships, and teacher feedback distinct enough that they can be connected deliberately rather than accidentally flattened together.

---

## Source basis and provenance notes

The cube layout and its six face meanings originate in the owner's conversation proposing a six-sided node with one inner information core. All schema field names and normative requirements above are new draft provisions.

- **PROTOCOL(1).md / CAS teaching cycle: input-binding candidate**, “What this teaches,” “Allocation and assistance,” and “Comparisons and partitions”: source for the original seven-stage sequence, repeated full guidance, separate exposure counts, and the fact that the earlier protocol targeted input binding rather than internal ^6 decomposition.
- **RESULTS.md / Graph-first candidate + targeted ^6 trainer mode, pure phase**, “What was built”: source for nodes, connector/branch meaning, no answer edges, and the three whole-part exercises.
- **OPERATION_EXPANSION.md / CJT operation registry and expansion path**, “Built-in operation identities,” “Current typed I/O contracts,” and “Operation contract”: source for the admitted ^6 identity and separation of data labels from executable operations.
- **RETROSPECTIVE_CONTAINMENT_001.md**, sections 1 through 4: source for the retained endpoint evidence, missing practice-option strings, current contrast-probe scope, and the unmeasured option-readout hypothesis. This specification does not replace that investigation.
- **GRAPH6_CURRICULUM_002 attempt 004 RESULT:** source for the preserved `VARIED_CURRICULUM_NOT_ESTABLISHED` result, not evidence that the proposed cube representation improves learning.
