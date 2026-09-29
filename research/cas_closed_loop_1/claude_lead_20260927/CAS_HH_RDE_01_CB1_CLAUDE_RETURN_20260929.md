# CAS-HH-RDE-01-CB1 v1.1 / CB1-A — Claude first return (2026-09-29)

Format: `00_START_HERE.md` first-return format. Plain English; claim states separated. Everything below is
SOURCE-ONLY and NOT RUN: no local test, no torch, no model, no AWS, no third job, no worker.

## TASK / ACTUAL LEAD / ACKNOWLEDGED FILES

- Task `CB1-A` (analysis mathematics), parent `CAS-HH-RDE-01-CB1 v1.1`. Lead: this session (PR #245).
- Package received at Git commit `fe2db4e90430274e93556543b345c7dbaeef568f`
  (`research/helm_self_improvement/cube_binding/handoff_v1_1/`). Manifest check from Git blobs: 14 of 19 files
  present and byte-identical; 5 named subset omissions (`CONTEXT_1/2/3`, the v1.0 original, `verify_package.py`);
  0 mismatches. Receipt acknowledged on PR #245 (comment 5884579738) before any source was written.
- Acknowledged exclusive files (all new; namespace `research/helm_self_improvement/cube_binding/`):
  `role_schemes.py`, `reconstructor.py`, `binding_edits.py`, `test_role_schemes.py`, `test_reconstructor.py`,
  `test_binding_edits.py`, plus the one-line `__init__.py` (shared; Codex may overwrite identically).
- Not touched: Codex's `contracts.py` / `public_task_adapter.py` / `consumer_bridge.py` / `evidence_view.py`,
  DeepSeek's `review/cas_hh_rde_01/cube_binding/`, my four RDE files (byte-identical to `54dac34e`), the
  learner, runner, authority files, checkpoints, graders and the CAS runtime.

## EXACT SOURCE / INPUT / ROLE-SCHEME IDENTITIES

| File | sha256 | Lines |
|---|---|---:|
| `cube_binding/__init__.py` | `5d53610a376aa374d0471c0e72900ba20cf7086eed44ccf904a3e7343e6ade1d` | 1 |
| `cube_binding/role_schemes.py` | `423b989245bbd6e3add31d388a2ded065c8017ed3821fe8b803c9f88dde45770` | 374 |
| `cube_binding/reconstructor.py` | `cb0b3852020140df2404db4fc3be7ad6d651dc97335a0adb460e794e70c97222` | 389 |
| `cube_binding/binding_edits.py` | `734a589b15e4fc7b76a980f274ecfd4c59ad3f2fb0a42ff4da0ea12a4c907724` | 255 |
| `cube_binding/test_role_schemes.py` | `8324bcd3b1ab594c264c1f7a9cf2c4fb416a532b16015dbcbbc6006fc53b803a` | 154 |
| `cube_binding/test_reconstructor.py` | `a12f20f4e0e002f7714c928bf27259de18172697727d23bd38387f5b70c746cd` | 192 |
| `cube_binding/test_binding_edits.py` | `ebc35f6f561265b9e8876ce21ada9aba089eb162a3b4abeb9dbb900a566457ad` | 224 |

Inputs the source depends on (reused, not copied): `diagnostic_configuration.py` and `diagnostic_intervention.py`
at my head (`c2850c86…` / `5294db17…`; the `ae940c44`-lineage bytes at `54dac34e` expose the same names the new
modules import: `canonical`, `digest`, `AUTHORITY`, `BASIS`, `CORE_ROUNDS`, `SITE_SEMANTICS`, `LEARNER_SHA256`,
`Donor`/`donor`, `declare`, `apply`, `Receipt`, `caller_binding`). Cube anchor by reference only:
`cube_node.py` at scientific ref `c45f775f` (sha256 `9d3363a960298715c0b13256593693dff7b07d70563b9a1b044d5d9042431e4a`),
not importable from this branch; its forbidden-field list is copied into `role_schemes.FORBIDDEN_FIELDS`
(relationship `SEMANTIC_CORRESPONDENCE`). Seam: Codex comment 5884514028 (`graph.round_update` = real `core_block`
post-hook; descendants recompute on the same forward), recorded as `SOURCE_CONSISTENT_NOT_EXECUTED`.

Role schemes (schema `helm.cube-binding.role-scheme/0.1`; digest = `scheme_digest(scheme)`, computed at use):
`IDENTITY_ONLY` (graph bag), `ENDPOINT_BAG` (roles, no pairing; the section 3.1 collapse control),
`RELATION_ENDPOINT` (receiving-row scope; role paths `("self",)`, `(<predicate>, "out"|"in", <depth 1..max>)`;
vocabulary size `1 + 2 * max_path_length`, shape-independent), `EVENT_FRAME` (declared predicate profiles, e.g.
`("help", "helper", "recipient")`; surface form is never a binding input). Occurrence keys (concrete node paths /
event ids) keep multiplicity and stay out of the fitted features.

## IMPLEMENTED FUNCTIONS

- `role_schemes.py`: `declare_scheme`, `scheme_digest`, `public_graph` (branch records
  `source_node_id/predicate/target_node_id`; refuses answer-bearing fields, unknown predicate/filler, self edge,
  duplicate edge, dangling reference), `graph_bindings` (bounded depth; cycle refused; truncated count, never
  "absent"), `row_binding_sets`, `event_bindings`, `scene_bindings`, `same_records`, `distinguishes`,
  `binding_set_digest`, `scheme_to_json`, `scheme_from_json` (retained digest mandatory).
- `reconstructor.py`: `declare_design` (kind `TPR` | `ATOMIC_PAIR`; `d_f`, `d_r`, `d_h`, seed, learning rate,
  L2, bounded `max_steps`, normalization `NONE` | `TRAIN_ZSCORE`, site), `parameter_count`, `initialise`,
  `binding_tensor` (`vec` order `FILLER_MAJOR`: index `i*d_r + j`; occurrences add), `reconstruct`
  (`W @ v + bias`, de-normalised once), `fit` (activation-reconstruction MSE + L2 on `W` only; samples are
  `(binding_set, target)` and nothing else; `HOLDOUT_LEAK` refusal; `analysis_optimizer_updates` counted;
  `helm_optimizer_updates` 0 by construction), `residuals`, `agreement_record` (agreement with original,
  original correctness, reconstructed correctness, wrong-to-different-wrong as separate columns), `serialize`,
  `deserialize` (retained state digest mandatory).
- `binding_edits.py`: `declare_edit` (`NO_CHANGE`, `FILLER_REPLACEMENT` supported; `ROLE_REASSIGNMENT`,
  `TWO_ROLE_SWAP`, `ENDPOINT_SWAP` named and refused this packet), `edit_bindings`, `delta`
  (`W @ (vec(new) - vec(old))`; bias never added; `sigma`-only rescale under `TRAIN_ZSCORE`), `freeze_plan`
  (one site `graph.round_update`, one round, one row, expected effect, max delta norm, reconstructor design and
  state digests), `donor_for_plan` (composes `h_original + delta` into the incumbent `Donor`; provenance
  `STIMULUS_ONLY` unless the caller declares `GOLD_INFORMED`, which the incumbent path caps at
  `ORACLE_ASSISTED_DIAGNOSIS_NOT_DEPLOYABLE`), `declaration_for_plan` (incumbent `SAME_INPUT_PATCH` declaration
  via `diagnostic_intervention.declare`), `verify_single_application` (exactly one targeted hit, planned round,
  planned delta norm, caller-verified binding, hooks removed, parameters unchanged; `DOUBLE_APPLICATION` refused).
  Application itself stays with `diagnostic_intervention.apply` under the trusted caller; passive `emit` stays
  read-only; no new action enters `diagnostic_intervention.py`.

## WRITTEN / COLLECTED / EXECUTED TESTS

| File | Written | Collected | Executed |
|---|---:|---:|---:|
| `test_role_schemes.py` (pure Python; CB03, CB04, CB05, CB07, refusals, reload) | 9 | 0 | 0 |
| `test_reconstructor.py` (torch; vec order, dimensions, bounded fit on a labelled synthetic TPR, holdout custody, forbidden fit inputs, train-only z-score, reload, agreement columns) | 8 | 0 | 0 |
| `test_binding_edits.py` (torch; bias cancels, sigma-only, exact swap-back, NO_CHANGE through `apply` = `APPLIED_NO_CHANGE`, filler replacement applied once with the planned delta and recomputed heads on a `FIXTURE_NOT_HELM` container, double application / unverified binding / no hit refused, plan refusals) | 5 | 0 | 0 |

Total written 22. Collected 0, executed 0: the namespace `conftest.py` refuses without
`HELM_SI_EXECUTION_VENUE=ADMITTED_AWS`, torch is not installed here, and the CB1 package grants no local test
venue. Syntax checked with `py_compile` only. Requirement rows mapped: CB03, CB04, CB05, CB07 (data-only),
CB15, CB16, CB17, CB18, CB19, CB20 (single application; descendant schedule recorded, not executed), CB21
(controls: `NO_CHANGE`, identity-only and atomic-pair comparators exist as source), CB22 (`agreement_record`),
CB23 (through the incumbent `apply`), CB24/CB25 partially (analysis holdout only; learner holdout is not this
file's), CB36 (digest-anchored reload). None counts as a current pass.

## OBSERVED RESULT / NOT_RUN

NOT_RUN, all of it. No reconstructor has been fitted to anything real. No edit has been applied to any model.
No claim about HELM. Status vocabulary: `ENGINEERED-NOT-VALIDATED`.

## OPEN DEFECT AND MINIMUM FIX

None found by reading. Two interface notes for Codex, not defects: (1) `donor_for_plan` needs the captured
original row values of the planned row at the planned site/round from the SAME input and checkpoint; the
intended source is Codex's passive capture (`convert_observation` output), not a fresh observe pass; (2) the
first edit site is `graph.round_update` only, per the seam statement; `graph.node_state` stays refused.

## ALLOCATED / USED / REMAINING RESOURCES

90-minute CAS-HH-RDE-01 allocation (shared with this extension; no reset). My ledger: about 54 active minutes
used before this packet; this packet about 12 active minutes (05:58Z–06:10Z); about 24 remain. Serial, no child
worker, $0, no cloud call, no model call.

## NEXT READY TASK / EXACT DEPENDENCY

Next ready: nothing further in my files until Codex's `contracts.py` / `consumer_bridge.py` exist, so the
binding-set input (`public_task_adapter` output) and the captured-row input can be typed against real records
instead of the test fixtures. Exact dependency for any execution: Gate 2A (the incumbent passive capture with
real HELM forwards) plus a separately admitted numerical venue; both are outside my authority. If the owner
wants the 22 cases collected, that is a job-side decision on the existing process, not a request from me.

## Addendum 06:13Z — receipt and disposition of Codex's CB1-C (`c9b0bfd37b0968251415037c08cb13fe246c49ec`, comment 5884654485)

Verified from Git objects: Codex's tree adds `contracts.py` (`625e88a8…`), `public_task_adapter.py` (`95b99325…`),
`consumer_bridge.py` (`c4eebee1…`), `evidence_view.py` (`47140b81…`), their three test files, `README.md`,
`SOURCE_PINS.json`, `REFERENCE_SOURCE_INDEX.json`, six `reference_source/*.py.txt` review snapshots
(`cube_node.py.txt` sha256 `9d3363a9…` = the `c45f775f` blob I cite), and DeepSeek's relayed return under
`handoff_v1_1/review_returns/` (report `98092a8a…`, fixtures `ea6b43ca…`, controls `0f0a795b…`, matching its
`PROVENANCE.json`). My four RDE files at `c9b0bfd3` are byte-identical to `54dac34e` (4/4). Codex wrote
`cube_binding/__init__.py` (`e123755d…`).

Disposition of Codex's asks:
- "Omit the shared `__init__.py`": done, removed from my branch in this commit; Codex is the one writer.
- "Keep sigma/delta/bias handling in your exclusive `binding_edits.py`": it is there (`delta`: bias never added,
  sigma-only rescale). New `consumer_inputs_for_plan(plan, delta, original_values=capture.signed_values,
  shape=capture.shape, torch=…, provenance=…)` returns exactly the keyword set of Codex's
  `prepare_consumer_declaration` (`native_values`, `max_abs_delta`, `donor_provenance`, `hypothesis_id`,
  `predicted_change`): the whole captured tensor row-major with only the planned row replaced by
  `h_original + delta`, an elementwise finite bound derived from the delta, explicit provenance. A `NO_CHANGE`
  plan maps to the bridge's no-op path (`native_values=None`, incumbent `NO_OP_CONTROL`), and
  `verify_single_application` now accepts a `NO_OP_VERIFIED` receipt for a `NO_CHANGE` plan. My own
  one-row `donor_for_plan`/`declaration_for_plan` stay as the fixture path; the bridge is the integration path.
- "Preserve pairing without per-example audit IDs as fitted roles": `RELATION_ENDPOINT` roles are
  `("self",)` and `(predicate, out|in, depth)`; occurrence keys are outside `BindingSet.records()`.

Cross-check with DeepSeek's relayed algebra: its `vec` is row-major over `outer(filler, role)`, which is the same
index rule as my `FILLER_MAJOR` (`i*d_r + j`); its `tpr_reconstruct` adds one bias per reconstruction, as mine does.
Its 43 local executions are its own report; venue reconciliation is between Codex and DeepSeek, not mine.

Two compatibility facts to keep visible (not defects): the bridge requires site width 64 and at most 10 rows
(`CB1_CONSUMER_DIMENSIONS`), so a real plan needs `d_h = 64`; my fixture width 16 is test-only. The bridge's
no-op is the sham `NO_OP_CONTROL`, my fixture no-op is `SAME_INPUT_PATCH` with identical values
(`APPLIED_NO_CHANGE`); both are accepted for a `NO_CHANGE` plan and named separately in the receipt.

Updated identities: `binding_edits.py` sha256 `825d2166d1ee1de2fb2e4ddd442cfdce4a1df089fb97fe65fe3925264c5814b1`
(297 lines), `test_binding_edits.py` sha256 `8c3eeea0ab058c703208d444ac4ea685f1c6128b41d0673fec2a270c73ca7ee2`
(266 lines, 6 cases). Tests written now 23 (9 + 8 + 6); collected 0; executed 0. About 5 more active minutes
(06:10Z–06:15Z); about 19 remain. Still NOT RUN, still `ENGINEERED-NOT-VALIDATED`.
