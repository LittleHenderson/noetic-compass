# Prepared Q4 smoke runner and R2/checkpoint interfaces

No neural model or real job has run. The code-only check suite passes 92 tests
on Python 3.14.0. One metadata-only prepare command was exercised against the
explicitly pinned historical Q3 v0.4 dataset. v0.4 is a compatibility fixture,
not a claim about the latest data. Any later dataset must be selected by its
exact pinned version and path. No default selects the newest version.

## Added interfaces

`learner_q4_memory.from_structure` creates a bounded tree memory with stable
positions, parent/left/right roles, syntax attributes, explicit context, model
identity and one finite vector per node. Structure is deliberately available:
this is **not strict vector compression**. Vectors are supplied by the caller;
the module does not learn them. A target AST is not permitted as model-visible
input. `replace_vector` changes only one declared vector, for later controlled
interventions. It cannot fetch a reference answer or correct a prediction.

`q4_checkpoint` provides inference-only save, verify, and strict CUDA restore.
Verification requires source/data identity and a weight digest expected from
outside the checkpoint folder. Changing weights and resealing their local
manifest fails that external digest check. Deserialization uses the **same
verified bytes**, with `weights_only=True`; it never reopens the weight path
after verification. It enforces strict tensor loading. Model parameters are
created as float32 regardless of a caller's default tensor dtype.

These are not optimizer/RNG/schedule resume checkpoints. There is no automatic
migration, dropped-tensor acceptance, resumed training, or CPU fallback.
The tests use labelled fake bytes and fake objects, not a neural checkpoint.

## Prepare a single job

Run in this lab directory using the intended CUDA Python environment. This
command is a dry run: it reads metadata, external pins, and source files, but
does not read data rows, initialize a model, inspect GPU usage, or launch work.
It writes the optional plan using exclusive creation, so it cannot overwrite a
prior plan. Select the actual data version approved for the intended run.

```powershell
python q4_smoke_job.py prepare --data-dir .\data\q3_v0_4 --data-version helm-cas-expression-lab.q3-behaviour-records/0.4 --output "$env:TEMP\helm-q4-smoke-once-20260921" --plan-out .\q4-job-plan.json --seed 20260921 --width 64 --max-updates 128 --max-wall-seconds 1800 --train-examples 2048 --dev-examples 16 --device cuda:0
```

The output is `PREPARED_NOT_AUTHORIZATION`. Its digest binds the exact source
files (including the loader's reconstruction helper), dataset manifest and
external pins, contract, Python/package metadata, device, output, seed and
resource caps. Changed code, data, environment, or limits require a new plan.
Preparation may report `UNAVAILABLE` for a package; this is not a readiness
claim. The execute path fails if the required CUDA/runtime dependency is absent.

## Authorization and ownership

The handoff requires separate authorization for a named neural job. This code
does not create that authorization, a human attestation, an owner key, or an
owner signature. Tests use **TEST_ONLY** keys and never launch a real job.

An external trust anchor must first be established by the owner: a raw 32-byte
Ed25519 public key and its independently pinned SHA256 fingerprint. The key
must live outside the checkout, source-data folder, and output folder. A caller
merely supplying an arbitrary key does **not** establish that it belongs to the
owner. Signature verification proves agreement with that separately established
key, not human identity or legal authority.

The signed JSON has exactly `schema`, `plan_sha256`, `expires_utc`, and
`signature_base64`. Its schema is
`helm-cas-expression-lab.q4-signed-job/0.1`; the signature covers canonical
UTF-8 JSON of the other three fields (sorted keys, compact separators).
It must match the entire plan and have an unexpired timezone-aware deadline.
No approval/status keyword bypass exists. The `cryptography` package verifies
Ed25519 signatures; its absence fails closed.

Only after that job and key are actually authorized, the operator supplies the
three external inputs below. The variables intentionally have no invented
defaults; none is present in this work product.

```powershell
python q4_smoke_job.py execute --plan .\q4-job-plan.json --authorization $ownerSignedJob --trusted-public-key $ownerPublicKey --trusted-key-sha256 $ownerPinnedFingerprint
```

The supervisor reserves a new output directory, obtains an exclusive local Q4
lock across this user's GPUs, checks all GPUs through `nvidia-smi` for other
compute processes, and starts one worker.
An absent/failed GPU query or a nonempty process report fails closed. Remapped
`CUDA_VISIBLE_DEVICES` is refused to avoid checking a different physical GPU.
This conservative local-smoke scope avoids CUDA/physical ordinal confusion.
The lock coordinates Q4 jobs; the owner still coordinates unrelated tools.
An abandoned lock is preserved for inspection, never silently reclaimed.
There is no cloud/API command, device substitution, automatic retry, or resume.

The supervisor kills a timed-out worker and waits for it to exit. The worker
also checks its deadline between steps and decoder tokens. Timeout/failure
preserves output and does not produce a success result. Reusing an output
directory is refused. The worker requires the supervisor's one-use claim.

## What the unexecuted worker is written to do

It validates the source/data plan again, reads G **training** targets through
the checked loader, and applies at most 128 optimizer updates. Teacher-forcing
is used only for training loss. Gradients are checked/clipped and actual
updates are logged. It writes an inference checkpoint, then makes free-running
predictions from dev-visible inputs. Dev targets are loaded for scoring only
after those predictions are fixed. The loader checks full train/dev files;
only the plan's selected rows enter training or scoring. The eval split is not
opened. This is development measurement under `EVALUATION_NOT_INDEPENDENT`.

The result separates valid generated syntax from canonical AST equality by
depth and leaves operation/benefit unevaluated. Invalid or exhausted outputs
count as non-exact. Source/data identity is rechecked at completion. Device
name and actual Torch/CUDA versions are recorded. Deterministic CUDA float32
execution is requested; unsupported deterministic kernels fail, with no
fallback. Fresh-process neural reload, binding/refusal/execution scores and
held-out V25–V27 evidence remain open. T15 learned operations are not included.

```powershell
python -m pytest -q -p no:cacheprovider test_learner_q4.py test_q4_followup.py
```

The tests cover grammar/input boundaries, all 2,048 historical G training AST
codec round trips, R2 role/intervention isolation, checkpoint tampering and
file replacement, metadata-only preparation, scope/signature forgery, mocked
timeout/duplicate launch, and GPU busy/unavailable refusal. Their mocks are not
substitutes for a real authorized CUDA run.
