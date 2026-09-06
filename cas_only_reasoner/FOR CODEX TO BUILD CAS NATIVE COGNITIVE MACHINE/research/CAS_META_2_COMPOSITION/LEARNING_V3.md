# Learning v3 candidate: copy names and generate valid nested programs

This candidate now has a separate campaign, launch profile and audit tools.
Integration review and combined pure validation have passed; it has not run on
AWS or produced a learned checkpoint. The accepted executor and all older
experiment files stay unchanged. Do not use the old `learning_v2` profile.

## Verified launch-candidate source

The final combined check passed 1,137 test functions and 178 subtests, with
zero failures/errors and seven GPU modules skipped. All 97 code/asset/config
files and all 316 accepted protected files were identical before and after.
Receipt: `records/local_learning_v3_004/receipt.json`, SHA-256
`b1c3ba096a724c5934d01b89ae4ffe4798aebc041940ef598f25834e69c85043`.
The runner retained raw stdout/stderr, JUnit counts and source snapshots. The
single warning comes from an intentional duplicate-ZIP-member rejection test.
The additional 125-test focused check and final integration corrections are
recorded in `records/local_v3_integration_review_002/REVIEW.md`.

This source is prepared for its own launch-candidate commit. The bundle receipt
must identify the exact committed SHA; none is inferred from this document.

## Earlier component source basis

The combined pure check passed 948 test functions and 89 subtests, with zero
failures/errors and six GPU modules skipped. All 83 code/asset/config files
and all 316 accepted protected files were identical before and after the run.
The accepted baseline manifest digest was checked against its fixed pin.
Receipt: `records/local_learning_v3_003/receipt.json`, SHA-256
`36bc75247345154549ec45438cf415d072a420af74cb8a80d0a94ae8046a0207`.

Reproduce these local-only checks from this package directory with:

```powershell
C:/Python314/python.exe -B tools/validate_local_v3.py --output records/local_learning_v3_new
```

The output directory must be new. The runner blocks neural and live AWS-client
imports and has a 600-second child limit. It permits only the SDK's pure error
classes needed by existing mocked tests. These checks do not run model tensors,
GPU tests, training, native neural execution, or provider calls.

The earlier 180-second timeout has a separate observation record because the
old runner did not save its captured output. The first new-runner attempt
(`local_learning_v3_002`) completed with two failures caused by blocking those
pure SDK error classes. Its original failure receipt and outputs remain intact.
Only the new runner and its tests were corrected; no older evaluator or model
source was changed to make that run pass. This is a component/source-basis
checkpoint, not the paid-launch source freeze or a reproduced learning release.

## Why this revision exists

The second composition run solved 0/72 test tasks for both learned arms; the
rule parser solved 72/72. Its CAS validation program/binding matches reached
13/48 but none at depth 3 in the selected checkpoint. Frequent failures included
duplicate declarations, missing callees and incorrect references. The stored
diagnostic checked 1,778 traces and all 360 sealed choices. Full acceptance still
fails the original GPU-memory-cleanup gate; this new code does not amend it.

## Implemented candidate components

- `features_v3.py` marks exact occurrences of all 54 existing name symbols in
  the public problem. It preserves the complete frozen lossless encoding. It
  does not parse the requested program or expose private answers.
- `policy_v3.py` gives both CAS and generic encoders identical learned copy
  heads, the same observation-binding pointer and a shared causal decoder
  design. Repeated occurrences feed the unchanged 67-token action vocabulary.
  Shared initial parameters match; parameter-count matching uses real
  feed-forward width, not disconnected extra parameters.
- `grammar_v3.py` constrains program syntax and published IR limits equally
  for all four neural arms. It does not choose the correct operation from the
  problem. Wrong valid programs and dead ends still count as failures.
- `selection_v3.py` selects checkpoints by worst-depth generated accuracy,
  then macro-depth accuracy, overall accuracy, lower unweighted validation
  loss and earlier epoch. The trainer enforces exactly 32 validation cases at
  each depth. These are program/binding matches, not native-answer verdicts.
- `loss_v3.py` applies fixed 3:1 weights to semantic versus structural tokens,
  with zero weight on padding. The same loss is used by training and the new
  actual-copy GPU preflight.
- `curriculum_v3.py` specifies 3,072 training tasks (1,024 each at depths
  1/2/3), 96 validation tasks (32 each), and 72 test presentations arranged as
  24 matched triplets. The test changes wording and increases real call depth
  to 4 while preserving paired native work. Definitions can appear in shuffled
  order. Public wording is independently parsed after JSON reload.
- `train_v3.py` integrates those components, saves separate initial/selected/
  last checkpoints under format 3, records source hashes, seals all five arms
  before private test labels can be opened, and records actual paired steps.
  It also measures a fixed exposed training probe; that probe cannot select a
  checkpoint. An outer frame measures actual CUDA cleanup after all model,
  tensor and exception frames are released.
- `gpu_preflight_copy_v3.py` checks the actual copy-policy factory and loss at
  the registered batch-16 geometry. `gpu_preflight_v3.py` alone remains only
  a frozen-v2-geometry candidate plus shared cleanup primitives; it does not
  validate the new copy architecture.

The registered model geometry remains d_model 64, four heads, two encoder layers,
one decoder layer, feed-forward widths 128, maximum input 1,024 and maximum
action length 256. Initial saturation scale is the float `2.0`. Both models use
the same batches, AdamW settings, fixed loss weights and syntax mask. Training
seed is 7; curriculum seed 20260919 is reserved for the next registered run.
The registered limit is 60 epochs, at most 11,520 paired optimizer steps per model,
with a 2,700-second training allocation and separate prediction/evaluation time.
This follows the saved failure diagnosis: more varied training data, not a
longer repeat of the previous overfitting run. An unfinished paired epoch or
deadline failure cannot be reported as a completed learning result.

## Holdout and claim boundaries

Production construction and every later identity/manifest/full-data audit must
use `registered_development_exclusions()` explicitly. The two portable assets
exclude 4,488 unique graphs: previous experiments, the exposed capacity search,
and the small development fixtures. The 177 development signatures overlap the
4,312 base by one graph. None of the registered evaluation tasks were generated
locally. Local tests reuse marked diagnostic seeds only.

The public language still describes operations and dependencies. This is
instruction-to-program learning, not discovering an algorithm from an outcome
alone. Every curriculum target has explicit ABC permissions because the current
sentence syntax cannot express different permission scopes. R repair, new
Noetic meanings, Foundation recursion and pulsation are not in this curriculum.
Their absence does not remove them from the full vision.

## Campaign and audit integration

`EXPERIMENT_V3.json` registers only `learning_v3`, with entrypoint
`cas_meta2.campaign_v3`. The new launcher and source-bundle builder are
`aws/launch_v3.py` and `tools/build_launch_bundle_v3.py`. They bind the two
exclusion assets, candidate components, tests and spec to committed Git bytes.
Before paid execution, local packaged source must match those same bytes.
The canonical budget module, ledger and resource plan remain unchanged.

The campaign constructs its dataset in a separate process, which exits before
the learner receives data. It hashes private test bytes without opening their
answers until all 360 choices are sealed. Native admission, execution, stored
verification and denominators remain unchanged. Wrong valid programs and
rejections remain in the results. No more favorable subset is selected.

The AWS job first runs 4 native-contract tests and 27 policy/loss tests. After
construction, the campaign runs 3 actual-copy cold/warm/repeated tests and
2 trainer integration tests. One trainer test uses real paired updates and
strict checkpoint save/reload on an authored fixture. The other explicitly
replaces the inner workload while exercising real CUDA and the actual outer
cleanup. Neither fixture proves the production training pipeline completed.
The subsequent real campaign must produce that evidence.

The separate inspectors are `tools/inspect_cloud_packet_v3.py` and
`tools/audit_stored_packet_v3.py`. They check version-3 receipts, dataset and
source bindings, validation-based selection, and stored native outcomes. Local
inspection does not deserialize checkpoints or run neural inference. Binary
checkpoint hashes and source-bound writers are checked locally; actual CUDA
checkpoint reload is a separate cloud check. Frozen version-2 tools and their
failed evidence are not changed.

## Remaining release and learning gates

1. Commit this checked launch-candidate source and create its pinned ZIP. Check
   the launch and both audit entry points against the real Git commit in fresh
   processes. Passing local tests does not prove GPU behavior.
2. Use the unchanged shared $400 ledger, fresh provider identity/price/capacity
   checks and automatic cutoff for one bounded AWS launch. Each launch reserves
   $7. The current ledger reserves $32 and leaves $368 unreserved; reservations
   are not invoices. No T4, laptop neural work, automatic retry or merge.
3. Pass the cloud gates above before training. The campaign keeps separate
   allocations for training (2,700 seconds), predictions (480), native evaluation
   (2,400) and final evidence (180). It refuses to start learning if those
   reserves no longer fit. Campaign time is at most 6,600 seconds; the resource
   cutoff remains 7,200 seconds.
4. Measure all five arms on the complete held-out tasks, then independently
   inspect the saved bytes and recheck stored native outcomes. Keep all failed
   attempts, six main checkpoints, raw outputs, commands and compute receipts.
5. Verify AWS cleanup directly and preserve a separate evidence commit bound
   to the frozen source. Only measured held-out performance can establish
   improved composition; successful software checks alone cannot.

The immediate target is improved held-out composition. Passing these component
checks will not establish that target, CAS-specific advantage, general language,
qualified learned memory, lifelong learning, full Noetic semantics, the complete
CNCM or physical analog hardware. The full destination remains in
`VISION_REQUIREMENTS.md`.
