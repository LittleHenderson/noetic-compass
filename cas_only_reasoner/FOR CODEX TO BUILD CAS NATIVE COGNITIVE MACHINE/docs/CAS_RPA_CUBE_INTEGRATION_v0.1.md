# CAS-RPA cube and teaching integration v0.1

Status: **DESIGN_ONLY**. This document defines the next pure data bridge; that
bridge is not implemented here. Existing cube compilation was inspected and
probed without loading a learner. The compound runtime viewer is a separate,
ongoing implementation. Neither viewer work nor this design demonstrates learning.

Reviewed 2026-09-16 against checkout commit
`9597840c3a0344ea730c689bfc9ffc22401fe707` and the exact local source bytes listed
below. Frozen runtime, research sources, curricula and negative records were not
changed. No neural or tensor execution, provider call, reservation or spending
occurred in this review.

## Decision and project fit

Use the attachment's typed-relationship and shared-record proposal. A cube remains
the authored description of an idea; CAS-RPA provides a bounded projection of that
same description. Teaching compilation produces a checked exercise. Only an actual
learner response can establish whether the learner can answer it.

This serves the existing graph teaching, six-face teaching and perspective work.
It does not introduce a competing knowledge store, a new neural module, or a
prerequisite architecture that must finish before another lesson can be delivered.
Keep the current learner and its evidence boundary.

The first fixture should be the pinned six-cube Bicycle/Wheel/Frame/Cart/Platform/Rim
bundle already accepted by the cube validator. It has five directed containment
branches, three presentation views, one correspondence table, and six faces per
cube. Its context is `toy_scene_01`, family `illustration_family_01`, with
`closed_within_this_authored_scene` and `contains_inventory_complete: true`.
Source status is `ILLUSTRATIVE_NOT_EXPERIMENTAL_EVIDENCE`. These are authored
teaching facts, not an exhaustive physical bicycle inventory.

The later Kit/Toolbox/Wrench example already has a related pure family/compiler
in `cas_meta2/perspective_resonance.py`. It can become a second conformance fixture
after the cube bridge works; do not claim these are separate fresh test families
merely because their labels or presentation differ.

## Current implementation and exact binding

| Existing object | Implemented behavior | Integration boundary |
| --- | --- | --- |
| `cube_node.validate_bundle` | Validates core, six faces, context, provenance, directed branches, correspondence, declared completeness and face/branch consistency | Call before projecting. Never repair malformed authoring data silently. |
| `cube_node.containment_graph(bundle, view_id)` | Produces the existing graph and presentation labels | Preserve cube IDs and branch IDs alongside the projected graph; presentation labels are not canonical identity. |
| `cube_profile.compile_public_exercise` | Compiles three-choice public material plus teacher diagnostics | Its whole return value is **not** learner-safe; see the measured failure and allowlist below. |
| `cube_profile.attach_target` | Checks a supplied target against the graph-derived answer | Keep this teacher-side. A target must not shape learner input. |
| `reference.direct_parts/shared_parts/reach_kind` | Deterministic teacher/reference answers from stored `contains` branches | Successful traversal is compiler/checker behavior, not a learner result. |
| `adapter.public_records` | Existing problem string plus exactly three observations, each with eight numeric values; ordered options returned separately | Use the versioned cube compiler's result; do not reintroduce historical target-dependent record IDs. |
| `GraphLearner.predict(task_input)` | Actual learner chooses an option, using indexed or on-demand encoded input | Compatible input can be prepared now. Invocation remains outside this pure prototype. |
| `RecurrentGraphLearner` | Existing recurrent subclass uses the same registered `operation:^6` transform and readout | No recurrence change follows from atlas nesting. Preserve the negative results. |
| `AtlasSnapshot` | Typed nodes/links, immutable current/focus/hypothesis handles, finite directed expansion and explicit deferred work | Reuse this implementation; do not replace it with an untyped edge list. |
| `IdeaResponseProfile` | Separate native-flow, empirical-response, behavioral, coverage and cost fields | Attach existing measured records by identity; absent instruments remain unavailable. |

The six stored face roles remain exactly:

1. `face_1`: technical identity.
2. `face_2`: context and environment.
3. `face_3`: analogy and metaphor.
4. `face_4`: explicit correspondence.
5. `face_5`: decomposition.
6. `face_6`: recomposition and story.

Repetition is activity around this cube, not a seventh stored face. Preserve face
availability (`populated`, `unknown`, `not_applicable`), explanation, structured
content and provenance. An unknown face must not become an empty, complete fact.

## Required namespace mapping

| Source meaning | CAS-RPA representation | Prohibited inference |
| --- | --- | --- |
| Cube branch `contains`, whole to direct constituent | `contains_part`, with original branch ID, commonality and provenance | Direction alone does not establish cause or a later state. |
| Graph task `REACHED_VIA(part, idea)` | Teacher query over one or more `contains_part` links; target `direct`, `via:<constituent>`, or `absent` | Never translate the task name into RPA `reachable_via`. |
| RPA `reachable_via` | State successor through a named action/event, with candidate/observed/rejected status | Containment traversal is not execution. A selected command is not its observed outcome. |
| Another label/view of the same canonical cube | Same scoped `idea_id`, distinct view/context record; optional `references_same_idea` | Similar labels or CAS profiles do not establish identity. |
| More precise description of the same situation | `refines_state` only if the existing subset and shared-field checks hold | A rewritten graph is not automatically a refinement. |
| Rewired hypothetical family | Separate hypothetical state/version tied to its immutable base | Selecting or displaying it cannot replace the supported current record. |
| Computed shared constituent | Teacher witness or explanation referencing existing branch IDs | Do not add answer-bearing `shares` edges to the learner graph. An RPA overlap certificate has its own checked-witness contract. |

The original graph's `requires`, `triggers`, property relations and
`produced_by` semantics do not all fit these five RPA link names. This first
bridge accepts the declared cube `contains` profile only and refuses undeclared
predicates. It must not reinterpret every branch as containment. In particular,
the current `containment_graph` helper labels all incoming bundle branches
`contains`; the bridge must verify the predicate restriction itself before
calling that helper.

Keep the observation context, source bundle revision and selected presentation
view explicit. Use a source-scoped canonical identity such as the digest of
`(source namespace, context_id, cube node_id)`, not the rendered label. Carry
revision and source digest in the contextual view key. Different source namespaces
must not merge merely because both contain `node_001`.

The atlas's current state is the **loaded authored snapshot** in this first bridge.
Its status describes the observed source bytes; it is not the CNCM runtime state
and not observed world truth. A source receipt must say so. The inspector can
focus on any cube or face while `current_state_id` remains the same. A hypothesis
handle points only to a hypothetical node. No GUI action commits an execution.

## What / Where / Why / How

| Teaching demand | First supported behavior | Status |
| --- | --- | --- |
| What directly belongs to this idea? | Existing `LIST_PARTS` and graph-derived target | Existing scored interface, no new learner result |
| Where is this constituent relative to this idea? | Existing `REACHED_VIA`, with explicit context and direction | Existing scored interface; screen coordinates carry no semantic role |
| What do these ideas share? | Existing `FIND_SHARED_PART` | Existing scored interface; ambiguous multiple answers must be refused |
| Why does this structural answer follow? | Inspector exposes the exact supporting branch chain or direct inventory | Teacher explanation only; no new scored causal task |
| How would an action change this arrangement? | Show a declared action proposal only when its preconditions/effects/checker are supplied | No action executor or scored How curriculum in this prototype |

There is no source for "why someone packed this kit" in containment alone. Do not
invent that cause. A face-six explanatory sequence is not automatically temporal
or causal. Definition, analogy, correspondence and story material remain guided
presentation unless a separately specified scored task makes them learnable and
testable. The current cube teaching profile scores only the three graph operations.

## A measured API mismatch and safe compatibility path

The current source docstring says `compile_public_exercise` accepts a public case
with no target. This direct probe on the unchanged pinned bundle fails:

```python
from cas_meta2.graph_teaching import cube_node, cube_profile

bundle = cube_node.load_bundle()
case = cube_node.answer_cases(bundle, "view_formal")["cases"][0]
cube_profile.compile_public_exercise(
    bundle, cube_profile.public_case(case),
    assistance="guided", view_id="view_formal",
)
# KeyError: 'correct'
# compile_public_exercise -> visible_after_profile -> disclosure_audit
# -> answer_refs -> correct = case["correct"]
```

This is preserved as an observed failure; no frozen implementation was rewritten
to make the statement true. `answer_refs` uses the answer for a disclosure audit
after the declared mask. That audit is a legitimate teacher-side check, but the
current call still requires a teacher-shaped case.

A pure compatibility wrapper can derive that case from the public graph:

```python
public_case = {"op": operation, "question": question}
teacher_case = {
    **public_case,
    "correct": cube_profile.derived_answer(bundle, public_case, view_id),
}
compiled = cube_profile.compile_public_exercise(
    bundle, teacher_case, assistance=assistance, view_id=view_id,
)
```

This path was probed for all 51 questions in each of three views and both guided
and unassisted settings: **306 compilations**, no refusals. Each produced public
bytes and task IDs identical to the corresponding existing full-case compilation.
The process blocked imports of `torch`, `numpy`, `boto3`, `botocore`,
`requests` and `cas_cjt`; none loaded. Neural calls and optimizer updates were
zero. These are compiler conformance observations, not delivered lessons or tests
of the proposed RPA bridge.

Both probes were repeated with their exact code saved under
`records/rpa_cube_001/design_probe_001/`. The failing probe retains its nonzero
exit and complete traceback; the successful probe retains its JSON output.
`run_probes.py` refuses to overwrite evidence, records the exact process arguments,
checks the 17 named source records and attachment before/after, and binds the 11
actual transitive project imports to their bytes observed before the process.
`receipt.json` binds all ten probe/source/output artifacts. Receipt SHA-256:
`c46872e8dfc1e70a884c6ca7a619ed4743f1204254b8ce34f5982f6e4bdfd278`.
All ten artifact identities were reread and matched after completion. The
record-local `.gitattributes` preserves JSON and raw text bytes in Git.

The whole `compiled` object includes `derived_answer`,
`encoding.encoded_correct_index`, `record.correct`, and other teacher fields.
It must never be passed through as a learner input. The new wrapper needs a closed
allowlist with exactly the existing prediction input:

```python
learner_input = {
    "record_id": public_input_identity,
    "public": copy.deepcopy(compiled["encoding"]["public"]),
    "encoded_options": copy.deepcopy(compiled["encoding"]["encoded_options"]),
}
teacher_sidecar = {
    "record_id": public_input_identity,
    "source_bundle_digest": expected_bundle_digest,
    "operation": operation,
    "question": copy.deepcopy(question),
    "expected_answer": copy.deepcopy(teacher_case["correct"]),
    "encoded_correct_index": compiled["encoding"]["encoded_correct_index"],
    "reference_branch_ids": supporting_branch_ids,
    "assistance_level": assistance,
    "visibility_profile_id": compiled["visibility"]["profile"]["profile_id"],
}
```

Define `public_input_identity` from the exact public input, ordered choices and
versioned encoding context. Keep an additional stable semantic-question ID for
comparisons across presentations. The old cube public identity covers family,
view, question and candidate set; it does not cover all graph bytes. Reusing that
ID after a presentation changes risks hitting `GraphLearner`'s cached indexed
vector. A new input ID must change when input bytes change, without including a
private answer. Model/checkpoint, tokenizer/encoder, content revision and
visibility identities must bind any actual encoded cache.

The historical `lessons._record` includes `correct` in its `record_id`;
`adapter.public_records` derives slot ordering from that ID. Preserve those old
records exactly, and use the newer public-identity construction for new material.
No claim here repairs the historical evidence retroactively.

## Smallest useful implementation

Add new modules and tests only, without edits to frozen research or runtime files:

- `cncm/rpa_cube_adapter.py`: pure validated projection, source binding,
  canonical cube/view lookup and teacher/learner export separation.
- `tests/test_rpa_cube_adapter.py`: data and namespace conformance.
- A new versioned tool/fixture receipt under `records/rpa_cube_001/`, keeping
  inspector JSON separate from the learner export and teacher target file.

Suggested API:

```python
cube_atlas_from_bundle(
    bundle, *, expected_bundle_digest, source_receipt,
    view_id="view_context",
) -> CubeAtlasDocument

compile_atlas_lesson(
    document, *, bundle, expected_bundle_digest,
    operation, question, assistance,
) -> {"learner_input": ..., "teacher_sidecar": ..., "binding": ...}
```

`CubeAtlasDocument` should hold one canonical cube catalog keyed by source
namespace/context/cube/revision and one `AtlasSnapshot` projection. Keep all six
face payloads and their view, mapping, branch and provenance references in that
catalog once. An inspector node references the source cube and face path; do not
create a second editable knowledge store. Authoring inspection and learner export
are different wire shapes. Inspector access to a face or teacher witness must not
silently widen a learner's declared input.

The source receipt binds the supplied file SHA-256, canonical bundle digest,
schema, namespace and explicitly supplied observation metadata. Hash equality
proves byte identity only, not trustworthy authorship or true physical facts.
No current timestamp, model identity or world observation should be invented to
fill a required field.

The projected snapshot must stay within existing RPA limits (512 nodes, 2,048
links, depth at most 32, 8 MiB atlas JSON). Add explicit catalog and export byte
bounds; refuse oversized complete documents rather than silently truncating them.
Bounded traversal can return deferred nodes/links. Deferred information is not
absent, and an incomplete graph cannot support a closed-world `absent` target.

For all six face crosslinks, compare the projection with the source's exact node
IDs, branch IDs, mapping role rows and view labels. Keep complete/incomplete
inventory and partial/exact analogy coverage visible. A presentation rename does
not create new structural novelty or an independent test family.

No action executor, score-driven lesson controller, recurrent-depth change,
neural head, model call, optimizer step or deployment is part of this prototype.

## Acceptance tests required before calling the bridge implemented

1. All six cubes, 36 faces, five directed branches, three views and one
   correspondence table resolve to exact source records with provenance.
2. Canonical IDs survive presentation renaming; context/source/revision changes
   stay distinguishable. Same CAS profiles never merge unrelated ideas.
3. `contains` maps only to `contains_part`; no `REACHED_VIA` lesson produces
   an RPA transition. Unsupported predicates fail explicitly.
4. All 51 questions in each of three views match unchanged reference semantics.
   Guided/unassisted teacher outputs remain distinct from the allowed learner
   fields. Keep the failed target-free legacy probe as a regression fixture.
5. Private-target mutation, deletion, or replacement cannot change learner bytes,
   input IDs, option order, masks or navigation. A supplied disagreeing teacher
   target is rejected. The bridge itself accepts no private target on its public
   compilation entry point.
6. Changing public graph/input bytes changes the new input identity even when
   family, question and option set stay the same. Cache tests must cover this case.
7. Renaming and harmless reordering preserve semantic answers; rewiring changes
   the affected inventory/routes. Stale dependent faces or correspondence rows
   are rejected, never silently refreshed.
8. Missing/partial inventory does not become `absent`; unknown, not applicable,
   missing, masked and empty remain different. Ambiguous shared-part questions
   fail rather than acquire an invented answer.
9. Selecting a cube, opening a face, paging, filtering, focusing a hypothetical
   graph and changing layout leave source/current identity and learner input
   unchanged. A hypothesis does not become observed by selection.
10. Ordinary graph BFS and RPA expansion agree for the identical nodes, relations,
    root and budgets, including revisits and deferred work. Count compiler work
    independently from any future learner effort.
11. Loader/cursor/source digest corruption, context mismatches, duplicate IDs,
    dangling references, cycles and oversize catalogs fail closed.
12. Pure adapter tests run with model/tensor/provider imports denied. All counts
    explicitly remain at zero for neural calls, optimizer updates and delivered
    neural lessons. Inspector export alone cannot mark competence achieved.

These checks establish faithful projection and lesson preparation only. A future
learning comparison must match information, lesson/update budgets, encoder,
initial weights and checkpoint handling across representations, retain predictions
sealed before target joins, and measure fresh structure, meaningful relation
changes, both-correct invariance and earlier-skill retention. Layout benefit,
navigation benefit, routing benefit and learned competence are different claims.

## Allocation, response and demonstrated competence

Keep three independently sourced records attached to an idea/context:

- **Allocation:** which declared branch/task received finite work, with budget,
  policy and actual allocation evidence. No positive allocation implies truth.
- **Response:** instrument, model/checkpoint, input, test point, units, depth,
  provenance and observed values. Do not fill missing measurements from loss,
  confidence, correctness or a picture.
- **Competence:** actual learner prediction, matching private reference,
  assistance, family split, changed-relation discrimination and retention.

The current perspective binding explicitly reports
`UNAVAILABLE_NO_NATIVE_FLOW_TAP` and
`UNAVAILABLE_NO_APPROVED_INTERVENTION_PORT`. Its adaptive policy is
`SHADOW_ONLY_DISABLED`; neural benefit, calibration validity and retention are
unmeasured. Existing simulated reports remain simulated. Do not normalize an
`IdeaResponseProfile` into the atlas's positive 40-component profile: the
measurement fields and coordinate semantics differ. A CAS descriptor is not a
probability distribution over outcomes, the complete idea identity, or a
competence score.

## Retained recurrence evidence and unsupported claims

The local retained delivered reports show the following fixed-weight R8-versus-R1
comparison, each over 216 panel items:

| Course seed | R1 correct | R8 correct | Gained | Lost |
| --- | ---: | ---: | ---: | ---: |
| 20260912 | 117 | 101 | 12 | 28 |
| 20260913 | 105 | 104 | 14 | 15 |
| 20260914 | 113 | 102 | 11 | 22 |

These are three retained runs, not new experiments. Their source identities are
below. Keep gains and losses separate; do not select a favorable depth using
checker outcomes or use a net count as the whole result. They do not demonstrate
a recurrent reasoning benefit. The atlas's repeated mapping interface neither
overturns these results nor requires this neural recurrence mechanism.

Keep the useful structural proposal; disregard stronger implications not supplied
by current evidence: no measured flower advantage, automatic causal explanations,
truth from selection or activation, physical resonance, universal probability
coordinates, general learned planning, or accepted integration of the full CNCM
vision. The data bridge is the next concrete connection, not completion of that
vision.

## Source identity record

User attachment, read unchanged:

`C:/Users/wakil/.codex/attachments/57331104-5f2e-4668-a58d-548f319893ee/pasted-text.txt`

- Bytes: 12,137.
- SHA-256: `12ecb8736f4c3f98ba754c3b3b21cfb42538400939a915534596068ab6daf125`.

Paths in the table below resolve under these exact roots:

- CNCM: `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/vision-next/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE`
- Composition: `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/vision-next/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION`

The canonical digest of the pinned cube bundle is
`b3df2633ec6a49c6ad81d1572334ac00bcd123d09672d7a53a05979fc70b2c16`.
This differs from the file hash because it hashes canonical JSON content.
The following are actual file-byte identities, including their existing line
endings; none was normalized or rewritten during this review.

| Root | Path | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| CNCM | `cncm/rpa_model.py` | 24726 | `323a53b951644a93603cd2f56204fd5a038a3161f4778e28777e650a4f966f01` |
| Composition | `cas_meta2/graph_teaching/graph.py` | 6829 | `1dfa2f67ab76847d0ae351d36f9e0ea6c6e1bea053640dd20ab898a550b63543` |
| Composition | `cas_meta2/graph_teaching/reference.py` | 5412 | `aab7af24638c842b7197e7468a168fdf05b9cd0dc951583eec5aa8590dc765ee` |
| Composition | `cas_meta2/graph_teaching/lessons.py` | 19198 | `deb271bb91e3c45a79fcf367e816ad6759a4945f3bdf6caaadc15f1770cf3fd6` |
| Composition | `cas_meta2/graph_teaching/adapter.py` | 8472 | `a373852553bf126e32923506f31662629591701f528524430903af3ef93a94b7` |
| Composition | `cas_meta2/graph_teaching/cube_node.py` | 79970 | `9d3363a960298715c0b13256593693dff7b07d70563b9a1b044d5d9042431e4a` |
| Composition | `cas_meta2/graph_teaching/cube_profile.py` | 49852 | `08493344a5daff10e2fcaed5a1711cdf5299a7fa3e332f5efb63a75e5ac8bfef` |
| Composition | `cas_meta2/graph_teaching/real_framework.py` | 20252 | `82c177e8f70e6931d90a79b65defe9fe6848cce6ab690c67f890b12c4799cd3c` |
| Composition | `cas_meta2/recurrent_cjt/learner.py` | 22677 | `158c8c9a391a8b73aa138f830663f6726e4697e1b50ada414845cacac6bc5787` |
| Composition | `cas_meta2/perspective_resonance.py` | 33667 | `45e876dacbefc04db0bcdd0d6dea6341d3b1efd0d58b63787e9e9709a5a6496f` |
| Composition | `records/perspective_resonance_001/DESIGN_TASK_BINDINGS.md` | 9611 | `22f6467ff2de9e0e4165b370e660379c18dfec91fd2609b227dc25a3b1ec3af5` |
| Composition | `records/complementary_teaching_001/preparation_20260916/DESIGN.md` | 6344 | `5c9c621a111ceb452e93f6f3cb088ea0dc026a0d989583800e9aeec0c3df0b83` |
| Composition | `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_node_001/Cube_Node_Schema_v0.1.md` | 25974 | `0f12fe19674658670668104e88e7d2c3afb9ad868b79734135c0ee6b89ad015b` |
| Composition | `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_node_001/Cube_Node_Example_v0.1.json` | 29971 | `9e62538b807d0b7a6fc04890c4ee0504db53e45bc34b62504f001d7f0610eb32` |
| Composition | `records/recurrent_cjt_001/receipt_cas-meta2-rdcjt-20260912152001-abf38e1e/curriculum_result.json` | 11623 | `5ed2188596df8888d5eb906f9f28988466630bc4e484eca67c89b5cf8f1d0edd` |
| Composition | `records/recurrent_cjt_001/receipt_cas-meta2-rdcjt-20260913183000-d27a44e4/curriculum_result.json` | 8890 | `b9aeaa2f8148e5286f079f5502fd87977d9a2c57f2cf3ee0fcb841aa1aee2e5c` |
| Composition | `records/recurrent_cjt_001/receipt_cas-meta2-rdcjt-20260913184000-d27a44e4/curriculum_result.json` | 10384 | `6367cabfc2b24b797fa9d6350285065770c5b08bcbc32f8c73c855047e804de9` |
