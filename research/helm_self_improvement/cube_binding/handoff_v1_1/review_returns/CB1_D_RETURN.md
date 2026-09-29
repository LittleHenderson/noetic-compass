# CB1-D return — independent relational fixtures, validators and algebra controls

Task **CB1-D**, parent **CAS-HH-RDE-01-CB1 v1.1**, lead file `03_DEEPSEEK_CB1.md`.
Reviewer lane: DeepSeek. Exclusive area: `review/cas_hh_rde_01/cube_binding/*`.
Date: 2026-09-29. Cost: **$0.00**, 0 cloud jobs, 0 paid calls, 0 model loads, CPU only.

Second source packet, items 1-4 are delivered as executable code. Item 5 (the frozen
natural-structure study) is prepared and **NOT_RUN**, because the incumbent passive capture
has produced no real HELM forward.

## 1. Exact source and input identities

| Identity | Value |
| --- | --- |
| Current corrected original-team tip | `54dac34efa62db4d8a877fdcfe15f4b8a02346bf` |
| Branch | `codex/helm-si-three-lead-20260927` |
| Executed passive source (62 cases, 61 passed) | `ae2482fc93bc562c855037e90273da794a33b1f9` |
| Claude's integrated fix | `b054dee4352fbbad5a35d2eead033365b0635fd9` |
| Scientific HELM source | `c45f775f225dd06cc20cdf313f0a0398486e0d61` |
| `graph_teaching/cube_node.py` | blob `941437dd4347e460d2e4255876206da61cef2bf5`, 79970 bytes |
| `graph_teaching/cube_profile.py` | blob `644f9378d96bfd8df0e0521297142e1f9c7c4114`, 49852 bytes |
| CB1 package reviewed | `CAS_Cube_Binding_Handoff_v1_1`, `03_DEEPSEEK_CB1.md` sha256 `ff55f073c8c05cbd9e7a94c0b8fcc99eb7fb8de3df1cc984afbec62b4dcba3ca` |
| Manager directive v1.1 | sha256 `2d12f3c89f52a35a1caf1857fe308a78b08d1149e38e24332235657548d9dec5` |

## 2. Implemented functions

`review/cas_hh_rde_01/cube_binding/cb1_relational_fixtures.py` — 35910 bytes,
sha256 `ea6b43ca33660e81eb4a56db3ed8c1c480a5b3489ddbb1ef74f8277d51c0c596`.

Nine independent fixtures: pairing swap, role reversal, active/passive, two events with the
same people, repeated occurrence in the same role, shared constituent across two wholes,
direct/indirect/absent/unknown, analogy that preserves relations only, and the unpaired
repeated-edge case.

Validators and algebra: `RelationFrame` with a declared pairing state and answer-bearing
role-label refusal; `role_labeled_bindings` for three authored forms with an explicit bare
form; `SplitPlan` with family grouping, linked-view retention and cross-split leak
detection; `private_target_independence`; `audit_public_closure` over 21 named surfaces with
explicit present / withheld / absent / unaudited states; `RoleScheme` with a bounded
vocabulary and frame scope; `role_path_count`; `tpr_reconstruct` with the reference
dimensions, a single affine bias and one documented `vec` ordering; `training_only_normalization`;
`resource_guard`; `truncated_is_not_absent`; and the deliberately naive representations
(`naive_endpoint_role_bag`, `naive_unscoped_bag`, `naive_role_name_multiset`, `bag_payload`)
that exist so each counterexample has teeth.

`review/cas_hh_rde_01/cube_binding/test_cb1_controls.py` — 33331 bytes,
sha256 `0f0a795b423cb82afad5539d4c4daac2dbec616cd2c83b1a0332bb70c9f2880c`.

## 3. Written, collected, executed

| Measure | Value |
| --- | --- |
| Authored | 43 checks |
| Collected | 43 |
| Executed | 43 |
| Passed | **43** |
| Failed / errors / skipped | 0 / 0 / 0 |
| NOT_RUN | the frozen natural-structure study; any real-model step |
| Whole reviewer suite | 43 passed (the CB1-D file is the only currently collected one under the reviewer root) |

## 4. Observed result

Every symbolic claim holds under exact equality. The load-bearing observations:

- The v1.1 hardening is real, and the collapse is now demonstrated rather than asserted. With
  one frame per edge, the endpoint bag reports sources `['A']` and targets `['B']` whether the
  edge appears once or twice. The role-name and filler-name multisets are the only quantity
  that grows, and they do not say which frame the extra copy came from.
- A scheme whose role paths name only the endpoint side sorts fillers by side, so two edges
  inside one frame collapse. Frame scope alone does not save it. I recorded that as a stated
  limitation of the scheme in the suite rather than a defect of a builder, and showed the same
  scheme separates the arrangements once there is one frame per edge.
- `cube_node.py` at `c45f775f` already builds edges as typed `(source, predicate, target)`
  relations in `containment_graph`, so the graph layer keeps pairing. The risk sits in the
  layer above it, which is where a new binding record could drop it.
- Active and passive keep the same semantic participant binding while the syntactic subject
  changes. A parser that equates the syntactic subject with the helper role fails that check.
- Target independence is testable directly: a view whose option order depends on the private
  answer produces two distinct public digests and fails.

## 5. Open defects and dependencies

| ID | Level | Finding | Minimum fix |
| --- | --- | --- | --- |
| CB1-D-01 | DEPENDENCY | `research/helm_self_improvement/cube_binding/` does not exist at `54dac34e`, so CB1-C and CB1-A have no source to review. My controls therefore import nothing from a builder. | Codex publishes the CB1-C lease and commit; Claude publishes the CB1-A lease and commit. Then I re-point the checks at the actual `role_schemes.py` / `reconstructor.py` / `binding_edits.py` interfaces. |
| CB1-D-02 | MAJOR (for the fit) | The reference formulation sums a multiset of `outer(filler, role)` products. A reconstructed block is therefore order-invariant and cannot, by itself, carry which edge belongs with which when two edges share both endpoint sets. | A fit that must separate the pairing-swap scene needs the role path to include the structural or event position, not only the endpoint side. That is a design decision for CB1-A, and my fixtures measure whether it was made. |
| CB1-D-03 | NOTE | `MARGIN_SAT`-class constants and Pythia-empirical margins must not enter a CB1 readout as if calibrated. This is inherited from the RDE review and re-flagged here because CB1 adds a second readout path. | No transferred constant in the CB1 readout without a HELM calibration record. |

## 6. Resources

| Measure | Value |
| --- | --- |
| Source allocation used by this return | within the existing CAS-HH-RDE-01 90-active-minute per-lead allowance |
| New model-job slots | 0 (both consumed; this package creates none) |
| Cloud / paid calls / local model execution | 0 / 0 / 0 |
| Local execution | CPU, model-free, no checkpoint, no project import |

## 7. Next ready task and exact dependency

**Next ready task:** re-point the 43 checks at the real CB1 interfaces the moment either
lease lands, and add the two remaining control families the lead file names that need real
source: the reconstruction-error versus task-correctness separation against an actual
reconstructor, and the algebra control against an actual edit operator.

**Exact dependency:** the CB1-C and CB1-A source identities. Nothing in CB1-D needs a model
job; the natural-structure study does, and it stays NOT_RUN until Gate 2A has real evidence.

## 8. Falsification

Any of the 43 checks turning red falsifies the corresponding claim. CB1-D-01 is falsified the
moment either namespace appears at a reachable commit. CB1-D-02 is falsified if a delivered
role scheme separates the pairing-swap scene while using only endpoint-side role paths.
