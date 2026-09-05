# Learning v3 candidate: copy names and generate valid nested programs

This is unfinished candidate source, not a new learned checkpoint or a launchable
release profile. The accepted executor and all older experiment files stay
unchanged. Do not run this source under the old `learning_v2` profile.

## Verified source basis

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

The proposed model geometry remains d_model 64, four heads, two encoder layers,
one decoder layer, feed-forward widths 128, maximum input 1,024 and maximum
action length 256. Initial saturation scale is the float `2.0`. Both models use
the same batches, AdamW settings, fixed loss weights and syntax mask. Training
seed is 7; curriculum seed 20260919 is reserved for the next registered run.
The proposed limit is 60 epochs, at most 11,520 paired optimizer steps per model,
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

## Required before any paid learning launch

1. Add a separate version-3 campaign/profile and source-bundle manifest. Bind
   both exclusion assets, actual-copy preflight, shared cleanup code and all
   new tests. Generate data in its own process; pass the same development
   exclusions during generation, training checks and stored audit.
2. Add a source-bound outer inspector and unchanged-native-result audit for
   format-3 checkpoints, new selection scores, dataset identities and cleanup
   receipts. Do not weaken the v2 inspectors or reinterpret their failures.
3. Finish AWS-only integration tests: real copied-head gradients, causal
   masking, matching, weighted loss, strict checkpoint reload, before/after
   behavior and cold/warm/repeated zero-allocation cleanup. No such GPU result
   is claimed by local syntax, mock or pure-Python tests.
4. Freeze the separate source and run only through the existing shared $400
   ledger, provider identity and automatic time cutoff. No T4, no laptop neural
   work, no automatic retry and no automatic merge. The current ledger reserves
   $32 and leaves $368 unreserved; reservations are not invoices.
5. Compare actual native task correctness for untrained/trained CAS,
   untrained/trained generic and the rule parser. Preserve all failures, every
   case, checkpoints, raw outputs, compute and cleanup receipts.

The immediate target is improved held-out composition. Passing these component
checks will not establish that target, CAS-specific advantage, general language,
qualified learned memory, lifelong learning, full Noetic semantics, the complete
CNCM or physical analog hardware. The full destination remains in
`VISION_REQUIREMENTS.md`.
