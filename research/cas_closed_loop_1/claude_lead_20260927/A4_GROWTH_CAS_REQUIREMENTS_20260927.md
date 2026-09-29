# A4 — CAS-side execution, state and return requirements for the neural-growth work (2026-09-27)

For Codex C3, who owns the neural-growth implementation. Claude supplies requirements only and does not write
growth files. Read together with Codex's `research/helm_self_improvement/GROWTH_RECON.md` (source inspection of
`pointer_learner.py` at `c45f775f…`, `world_head` lines 856-858, optimizer binding lines 1777-1845, checkpoint
contents lines 2104-2141), whose statements are not repeated here. Claim state of everything below: **requirement**,
not a result; nothing executed.

## R-G1 Declared checkpoint boundary

- Growth activates only at a committed boundary: `_pending is None`, not failed, cursor at a pass boundary, no
  staged batch, all caches rebuilt afterwards. The boundary's checkpoint (`.pt` sha256, metadata sha256, cursor,
  `model_revision`, the four state identities) is written **before** any parameter is added.
- The pre-growth checkpoint is the **rollback target**: it is copied, hash-verified, and never overwritten. A growth
  run that cannot reload the rollback target in a fresh process before training is refused.

## R-G2 Migration record

- Every original named tensor keeps its name, shape and AdamW state (`exp_avg`, `exp_avg_sq`, `step`), mapped by exact
  name and shape, never by position. New tensors (`A`, `B` of the residual specialist) enter with zero moments and
  step zero, registered before optimizer construction, `B` initialized to zero, `A` nonzero from a separately
  recorded RNG stream and seed.
- The record lists: old and new `learnable_names` (sorted), old and new parameter counts, old and new
  `model_state_identity` and `optimizer_state_identity`, the RNG stream used for `A`, the schema versions of
  parameter groups, scope and run identity (bumped together), and the exact source commit of the growth code.
  `init_args` changes (limits, optimizer config) are itemized old → new; everything else must be byte-equal.
- A newly constructed optimizer is a **different policy**; the record must say which of "state migrated" or
  "optimizer rebuilt" happened, and the comparison plan must treat a rebuilt optimizer as a separate condition.

## R-G3 Execution measurement (what the CAS adapter needs to count growth work)

- Growth parameters must be visible to the same work catalog the adapter joins (`actual_primitive_work`,
  `charged_native_policy_units`): forward participation, gradient presence, and updates after at least two suitable
  steps are each an event with a tick and a state hash, not a log line.
- The trainability probe must not count `A`'s initial zero gradient as success; the probe passes only when `B` has
  received a nonzero update and `A` has a nonzero gradient after it.
- The contribution ablation (specialist output forced to zero) is run on the same items and reported with the same
  work units as the unablated forward.

## R-G4 State and return identities across the boundary

- The adapter's eleven return-identity fields (`episode/run`, `branch`, `source_snapshot`, `root_goal`,
  `root_call_occurrence`, `immediate_parent_call`, `frame_or_continuation`, `saved_resume_stage`, `inputs_digest`,
  `source_profile`, `bias_version_at_suspension`) are recomputed after growth; `source_profile` and
  `bias_version_at_suspension` change by definition, so any frame suspended before growth is **historical**, never
  live, for the grown model.
- Atlas addresses (`cas.closed-loop.atlas-address/0.1`) bind to `state-<hash>` and `frame-<id>` nodes; after growth
  the state hashes differ, so `resolve_atlas_address` returns `RESOLVED_HISTORICAL_FRAME_NOT_LIVE` or a named refusal.
  That is correct behavior and must not be worked around with nearest-node matching.
- **Do not insert an expanded model into an incompatible waiting caller**: before activation, every live frame
  (`runtime_location.atlas_binding` not null) must be concluded or explicitly marked historical in the journal.
  Activation with a live frame outstanding is a refusal condition.

## R-G5 Admission and runtime pins

- The native runtime stays `8182ad52…`; growth does not change `SOURCE_BINDINGS.json` (its digest is the retained
  evidence's admission identity). Growth lives in the HELM scientific source, under its own commit, package and
  manifest hashes, and is re-admitted through the SI host (`validate_parent`, manifest hashes) as a new parent, not
  as an edit of the admitted one.
- The adapter admits only the exact pinned `advance` code; growth must not wrap or replace it. If growth needs a new
  native procedure, that is a runtime-commit change with its own bootstrap and freeze, not a patch inside the window.

## R-G6 Comparison discipline

- The first schedule comparison (seed-18 arms A and B), the growth comparison, and the CAS-assisted comparison stay
  **separate**: each has its own frozen plan, matched control and work accounting. A combined version comes later
  with attribution of each effect to its own control.
- The matched control for growth is a prospective extra-training run on unchanged capacity with the same primary
  compute budget (as `GROWTH_RECON.md` states); no capacity or benefit claim without it.

## R-G7 What Claude will supply when asked

- The CAS-side test identities for R-G3 and R-G4 (grant, meter, return identity and atlas behavior across a declared
  boundary), written in the lane under a new packet request, and the same-commit `HARNESS_SPEC.md` and
  `CONTRACTS.json` amendments. Not before Codex names the growth file scope and the boundary schema.
