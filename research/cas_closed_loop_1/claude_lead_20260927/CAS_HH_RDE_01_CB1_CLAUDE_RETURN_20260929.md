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

## Addendum 06:19Z — Codex integration `d27172d57a3eb7c4d9fb742676cb6c4156c0ea63` (comment 5884742440): row-mapping check and one source fix

Verified from Git objects: my six files at `d27172d5` are byte-identical to `ccbd8866` (6/6); my follow-up
`a16e3aa2` (`binding_edits.py`, `test_binding_edits.py`) is not yet in that tree; my four RDE files there are
byte-identical to `54dac34e` (4/4). Codex's `public_task_adapter.analysis_binding_rows(packet, scheme)` builds
branch records `source_node_id / predicate="contains" / target_node_id` from public labels, passes the nodes in
the pointer reader's `/n` rank order, and calls my `public_graph` then `row_binding_sets`.

Row-mapping check (by reading, no execution): consistent. `public_graph` keeps the passed node order and refuses
an edge naming a node outside it, so row `i` of the returned sets is node `/n{i}`; fillers are the public labels,
which must be in the scheme's fixed `filler_vocabulary` (an unknown label refuses `FILLER_UNKNOWN`, by design);
edge order does not matter (binding sets are canonically sorted); a duplicate directed edge refuses
`DUPLICATE_EDGE`. One assumption to keep visible: `world["contains"]` must be the direct authored branches, not a
transitive closure, or depth-2 paths would double count; Codex's README states 1–90 acyclic direct branches.
No defect found in the mapping.

Codex's source finding on `freeze_plan`: CONFIRMED by reading. `max_delta_norm` was checked for type and
positivity only; `nan <= 0` and `inf <= 0` are both False, so a non-finite bound passed, and later
`norm > nan` is False as well, so the donor step would not have caught it either. Fix in `binding_edits.py`:
`math.isfinite` refusal at plan construction (`MAX_DELTA_NORM`); one test loop added covering NaN, +inf, -inf,
0, negative, bool, string and None. `consumer_inputs_for_plan` inherits the fix through the plan.

Updated identities: `binding_edits.py` sha256 `780c1fd1b557817bcb7f081b229b95ec10b1d9cd69956b698c3b22d21e919776` (301 lines); `test_binding_edits.py` sha256 `bc85180e32eb1ba44f15d0de71f225b774d8cc0dd9433f289af24495451d8440`
(268 lines, 6 cases). Written 23; collected 0; executed 0. For integration, only these two files changed since
`ccbd8866`. About 4 more active minutes (06:15Z–06:19Z); about 15 remain. NOT RUN; `ENGINEERED-NOT-VALIDATED`.

## Addendum 15:15Z — coordination request 5892809590 ("ChatGPT ORIGINAL HELM/CAS manager" intake, posted from the owner account; self-described as not an owner signature and granting nothing)

The request names a second v1.1 manager directive (98008 bytes, sha256 `38444787…`, adds CB37–CB42) that collides
with the one delivered at `fe2db4e9` (84156 bytes, `2d12f3c8…`), plus `ORIGINAL_CLAUDE_SCOPE.txt` (`e8ffc3d5…`).
None of it is in Git (all remotes re-fetched at 15:13Z; Codex head still `79c872e4`); it exists only at a Windows
path. Receipt posted as comment after 15:13Z: request received, package NOT received, two directive versions not
equated; current scope and hashes restated; the "first deliverable" it asks for (reconciliation with Codex's real
interfaces) is already delivered at `a16e3aa2` / `65904c16`, which the intake did not list; first remaining artifact
is a CB37–CB42 coverage map, dependent on Codex relaying the package to Git; allowance restated as about 15 of 90
active minutes (its "24-minute remainder" was my 06:10Z figure). No source changed. NOT RUN.

## Addendum 15:20Z — owner decision (chat, 2026-09-29): the `38444787…` package takes precedence for research and product requirements; upgrade the existing code, do not restart

Owner instruction received in my session (not an owner-signed record on the PR): adopt the newer, source-reviewed
package's research/product requirements (98008 bytes, `38444787…`, CB37–CB42); keep the earlier plan's execution
continuity, the strict Q1 exclusion and all existing implementation; map requirements to what exists and change
only missing or incorrect parts; apply each requirement at the stage where it matters; no combined master plan.
The package itself and `ORIGINAL_CLAUDE_SCOPE.txt` (`e8ffc3d5…`) remain unreadable here (Windows path; not in any
Git branch at 15:17Z).

### Difference-to-source record for my six files against the themes the owner's memo names (by reading; nothing run)

| Theme (owner memo) | My files | State |
|---|---|---|
| Whole/part argument order | `RELATION_ENDPOINT`: `(contains, out, d)` = filler is a part of the receiving node; `(contains, in, d)` = filler is a whole containing it; `test_cb07` checks both directions. Codex's `analysis_binding_rows` maps `source`→whole, `target`→part; that its `world["contains"]` is whole→part is Codex's contract (README says so). | COVERED; one Codex-side assumption recorded |
| "Role" = public text label vs internally represented relationship | Role paths are structural positions derived from public edges, never text labels and never a learned internal relationship; `BindingSet` from `public_graph` is authored structure. No model-inferred binding record exists in my files (readout detectors were not in CB1-A scope); none is claimed. | COVERED for authored; NOT BUILT for inferred (not claimed) |
| Edit before or after the model's rescaling | Edit site `graph.round_update` = `core_block` output, before the residual add and the next round's RMS (Codex `consumer_schedule`: `CORE_UPDATE_BEFORE_RESIDUAL_NOT_FINAL_NODE_STATE`). Analysis-side `TRAIN_ZSCORE` is a separate, train-only fit statistic; `delta` rescales by sigma only, bias never added. | COVERED as source; placement `SOURCE_CONSISTENT_NOT_EXECUTED` |
| Which downstream calculations rerun | `DESCENDANT_RECOMPUTATION` record; Codex `consumer_schedule.descendants_in_order`; fixture test shows `node_head` recomputed on the same forward. | RECORDED; real forward NOT RUN |
| Answer-length / answer-set shortcuts | Reconstructor fit refuses answers, labels, scores, splits (`FIT_INPUT_FORBIDDEN`); choices-only / answer-shape controls belong to Codex's packet view and DeepSeek's controls. | MINE: covered; CONTROL: not my file |
| Position versus relation | GAP found and closed this addendum: new `POSITIONAL` scheme (receiving-row scope, `(self)` + `(position, k)` by packet row rank, edges ignored, bounded by `max_positions`, default 10 = the bridge's row limit). Test: cannot tell the paired-edge scenes apart, `RELATION_ENDPOINT` can; node reordering changes `POSITIONAL` records and not the relation ones. | ADDED (source-only) |
| Familiar examples vs new combinations | `HOLDOUT_LEAK` refusal, `ATOMIC_PAIR` control refuses unseen pairs, TPR composes them. | COVERED |
| Optional algebraic screen | Not implemented, per the owner: not a prerequisite for the first capture. | NOT BUILT (by decision) |

Note: adding `max_positions` to `Scheme` changes every `scheme_digest`; nothing fitted or retained depends on the
old digests (all NOT RUN). Updated identities: `role_schemes.py` sha256 `6cd3ce0cd2dca1352aff1263c1ce8cc13e6d34e15f28a3dc45760d770a91a445` (401 lines); `test_role_schemes.py`
sha256 `166545eba84c767aedd9ef278a6adafaef6b6a1a5e00818b4d1096760cb0625d` (180 lines, 10 cases). Written now 24 (10 + 8 + 6); collected 0; executed 0. About 4 more active
minutes (15:15Z–15:19Z); about 11 remain. The CB37–CB42 coverage map waits on the package reaching Git.

## Addendum 15:25Z — receipt of the second v1.1 package at `701d41854b6063918dd2408a71bae51400cabe55` and CB37–CB42 coverage map (by reading; nothing run)

Received as Git data objects (no branch ref), fetched by commit id. Verified from the blobs: directive
`CAS_Cube_Binding_Manager_Directive_v1_1.md` 98008 bytes sha256
`38444787948c627755585315a3b82e137e6d8f09d62d8a12abb6ce7c269714f1`; `ORIGINAL_CLAUDE_SCOPE.txt` 2436 bytes sha256
`e8ffc3d58f43a607507f7a9a671145d86c1c6c862f20ad1e245872889a8d9b2e`; 17 files in `handoff_20260929_38444787/`
(source review, analysis/change log, three scopes, manager handoff, revision record, manifest, Codex intake receipt,
five DeepSeek `review_return_16` snapshots). The earlier `2d12f3c8…` directive is preserved and not equated.

My scope file focuses CB03–08, CB15–25, CB29, CB37/39–41 and HH07–14. Coverage of the six new rows against my six
files (head `c69a68a4`; DeepSeek protocol files and Codex serializers are not mine):

| Row | Requirement (directive §19) | My files | State |
|---|---|---|---|
| CB37 | Task meaning and role namespace pinned; named argument convention; asymmetric direction; separate cube-view / public-text / event-binding identities | `RELATION_ENDPOINT` pins direction by name (`out` = filler is a part of the receiving whole, `in` = filler is a whole containing the receiving part) and `test_cb07` checks the asymmetry per row; structural roles, `EVENT_FRAME` roles and fillers (public labels) are three separate namespaces; cube faces never enter my files. | COVERED on the analysis side; the named whole/part serializer is Codex's (its receipt: PARTIAL) |
| CB38 | Answer-menu shortcuts accounted for | Not my file (packet view / controls). My fit refuses answers, labels, scores and splits as inputs (`FIT_INPUT_FORBIDDEN`). | NOT MINE; no shortcut possible through my fit |
| CB39 | Structural specificity separated from withholding; crossed relation-versus-position edit; separate structure-selection / novel-binding panels | `POSITIONAL` scheme (`c69a68a4`) is the position arm; `delta`/`edit_bindings` are scheme-agnostic, so the same `FILLER_REPLACEMENT` runs under `RELATION_ENDPOINT` and `POSITIONAL` for the crossed comparison; novel-binding withholding is separate (`holdout_pairs`, `HOLDOUT_LEAK`, `ATOMIC_PAIR` refusing unseen pairs). | COVERED as source; panel definitions are DeepSeek's (Codex receipt: REVIEWER_SOURCE_AVAILABLE_NOT_INTEGRATED) |
| CB40 | Intervention location respects actual computation; before/after nonlinear normalization; observation forwarding; directed aggregation; recomputed consumers | Edit at `graph.round_update` = `core_block` output, before the residual add and before the next `_rms_unit`; the delta is never commuted across the learner's row-dependent nonlinear normalization (source review line 74); analysis-side `TRAIN_ZSCORE` is a fit statistic on captured values, not a model transform; `DESCENDANT_RECOMPUTATION` record; fixture test shows heads recomputed. | COVERED by design, `SOURCE_CONSISTENT_NOT_EXECUTED`; observation forwarding and directed aggregation are Codex/HELM-side (its receipt: PARTIAL) |
| CB41 | Analysis apparatus admits a simpler or negative model; frozen structured/atomic-pair calibration; order-insensitive comparison; no fit-only systematicity claim | `ATOMIC_PAIR` kind with `parameter_count` reported next to `TPR`; `IDENTITY_ONLY` and `ENDPOINT_BAG` baselines; binding sets canonically sorted, `same_records` order-insensitive; labelled synthetic calibration written in `test_reconstructor.py`; no systematicity claim made anywhere. | COVERED as source; calibration NOT RUN |
| CB42 | Six-view value measured fairly | Not my file; my scheme never consumes face contents. | NOT MINE |

Other scope items: no successful-path / correct-answer labels as roles (`FORBIDDEN_FIELDS`, `FIT_INPUT_FORBIDDEN`)
COVERED; multiplicity and paired event membership COVERED (`test_cb05`); parameter counts, regularization policy
(L2 on `W` only, no low-rank constraint: declared), normalization statistics (`mean`, `sigma`, `zero_variance_dims`),
fit split (`holdout_pairs`) and step bound (`max_steps`) reported in the fit manifest; affine offset once, native scale
restored, one application per site/round, finite bound, cleanup COVERED; auxiliary decoder = separate measurement
(`agreement_record`; no decoder in my files); counterfactual success separate from original correctness COVERED;
residuals reported per sample, never discarded. OPEN (minor, not changed now): `fit` bounds steps and dimensions but
carries no wall-clock or memory bound of its own; the job-level bound applies. NOT BUILT by decision: the optional
three-state algebraic screen.

One frozen candidate hypothesis (a hypothesis, not a run plan): for one checkpoint (Codex's named candidate
`5b37699d…`), site `graph.round_update`, one declared round, a `RELATION_ENDPOINT` TPR reconstructor fitted on
activation reconstruction only predicts the counterfactual Parts answer change of one `FILLER_REPLACEMENT` edit
beyond the matched `POSITIONAL` edit, the `NO_CHANGE` control and the incumbent matched control; original-task
correctness recorded separately. Smallest unresolved dependency: a real, host-anchored complete capture at that site
(Gate 2A) plus a separately admitted venue; then Codex's integration of my four changed files.

Allowance: about 4 more active minutes (15:20Z–15:24Z); about 7 remain. No source changed in this addendum.

## Packet PRIMARY-CB1-INTEGRATE-01 (owner directive, 2026-09-29; separate 30-active-minute clock started 17:54:17Z)

Attached file `PRIMARY_HELM_CB1_Integration_Directives_20260929_v1.md` is a Windows path and not readable here;
this packet follows the directive text in the owner's message. The 90-minute history is not reset; this clock is
recorded separately. No worker, wake, test, install, model load, fitting, cloud job or spending.

### Fit resource boundary (SECOND item), closed in `reconstructor.py`

New `FitBudget` (schema `helm.cube-binding.fit-budget/0.1`) and `declare_budget(max_samples, max_parameters,
max_tensor_elements, deadline_seconds, outside_runtime_limit)`; `fit` now REQUIRES `budget=` (refuses
`FIT_BUDGET_REQUIRED` without one) and takes optional `cancel=` (callable) and `clock=` (injectable, default
`time.monotonic`). Contract:
- Pre-allocation, before any tensor exists: `preallocation_estimate(design, n)` = `2·n·d_h + 2·parameters +
  d_f·d_r` float32 elements (targets and predictions, parameters and gradients, one binding tensor), plus a
  byte estimate; refusals `FIT_SAMPLE_LIMIT`, `FIT_PARAMETER_LIMIT`, `FIT_TENSOR_LIMIT`.
- In the loop, before every optimizer step: `FIT_DEADLINE_EXCEEDED` when `clock() - start > deadline_seconds`;
  `FIT_CANCELLED` when `cancel()` returns true. A refusal returns nothing: no partial reconstructor.
- Outside runtime limit: `outside_runtime_limit` names the hard bound (the admitted job's wall-clock and memory
  limits); the manifest records `python_checks_are_hard_memory_limits: False`. These Python checks are
  cooperative; they are not a process-memory limit and are not claimed as one.
- The manifest carries the budget, the estimate, `elapsed_seconds` and the outside limit; serialize/deserialize
  keep it. Every existing fit call in my tests now passes a budget (`_budget()` helper). One regression test added:
  mandatory budget, six bad declarations, the three pre-allocation refusals, deadline via injected clock,
  cancellation at the second step, non-callable cancel, and the manifest record round-tripped.
Nothing is fitted in this packet; the boundary blocks future fitting only.

### Integration handoff (FIRST item): declared successor

Final owned source at this packet's commit (all six files; four changed since `ccbd8866` plus the two reconstructor
files changed here):

| File | sha256 | Lines | Cases |
|---|---|---:|---:|
| `role_schemes.py` | `6cd3ce0cd2dca1352aff1263c1ce8cc13e6d34e15f28a3dc45760d770a91a445` | 401 | |
| `reconstructor.py` | `9ddce0fd51a9051bf1727bac9f2239e07e038be7f3099d1bd787180b8fd3d248` | 465 | |
| `binding_edits.py` | `780c1fd1b557817bcb7f081b229b95ec10b1d9cd69956b698c3b22d21e919776` | 301 | |
| `test_role_schemes.py` | `166545eba84c767aedd9ef278a6adafaef6b6a1a5e00818b4d1096760cb0625d` | 180 | 10 |
| `test_reconstructor.py` | `97e9695f112c80b7061720140b7849dac390fd640df76f298ca7ab8ad4d94497` | 238 | 9 |
| `test_binding_edits.py` | `f0c7240488b28913a7387f47d362e2942836e51bc6adc517471df3326488a64c` | 275 | 6 |

Written 25; collected 0; executed 0. Scheme-digest change (from `max_positions`) is prospective: nothing
fitted or retained under the old digests; historical evidence untouched. When Codex names the integrated commit I
will byte-compare the six files and confirm: row alignment (`analysis_binding_rows` → `public_graph` order),
native-scale delta (`delta`, sigma only, bias never added), finite bounds (`MAX_DELTA_NORM`, `FitBudget`),
`POSITIONAL` versus `RELATION_ENDPOINT` (the crossed control), one application (`verify_single_application`), and
original downstream recomputation (`DESCENDANT_RECOMPUTATION`, Codex `consumer_schedule`).

### First hypothesis, kept small (unchanged)

One checkpoint (`5b37699d…`), site `graph.round_update`, one declared round; `RELATION_ENDPOINT` versus `POSITIONAL`
for one `FILLER_REPLACEMENT`; `NO_CHANGE` and the incumbent matched control; counterfactual effect, original-task
correctness and retained learning recorded as separate columns. No new role sweep, neural head, algebraic screen or
unsupported swap.

Exact remaining dependency: Codex's integrated commit carrying these six files, then a real host-anchored complete
capture at `graph.round_update` plus a separately admitted venue before any fit or edit runs.
