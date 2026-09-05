# CAS-META-1: learned CJT-program selection

Build status: verified small learning pilot. CASformer improved from 8/72 to
66/72 correctly solved held-out tasks; trained generic scored 61/72 and the
rule selector 72/72. All 360 saved outcomes were rechecked. AWS cleanup is closed.
See [RESULTS.md](RESULTS.md) and [AUDIT_START_HERE.md](AUDIT_START_HERE.md).
The Blackwell recovery preserved all original predictions and checkpoints.
Two attempts reserved $4 of the owner's $100 task cap; this is not the final AWS
bill. No neural work ran on the laptop. No further T4 use is permitted.

Accepted baseline: 0917267b1354e5d036263eaa6ba9a7197eafb776.
The CAS-META-0 restart round is closed. Historical evidence is not rewritten.

## The one skill being trained

Given a short task and three visible named inputs, choose one existing procedure
and bind one of those inputs. The controller proposes only two small indices.
The accepted meta executor still checks the program, permissions, budgets,
publication, and repair flow. The candidate never edits executor weights.

Three fixed library workflows are supported:

| Task goal | Existing workflow | Expected result |
| --- | --- | --- |
| First stage | A | Accepted L1 Effect |
| Second stage | A calls a B worker | Accepted L3 Effect |
| Final stage | A, B, rejected C, repair R, resumed C | Accepted L2 Effect and closed repair |

These are controlled synthetic stage goals, not unrestricted natural-language
understanding. Repair is the existing authored fixture's prerequisite sequence,
not a learned diagnosis of arbitrary failures. All operations remain ^6.

## Data and checking

The CAS-SDG-style curriculum constructs formal stage/source choices and small
numeric input variations first. It then renders wording and checks it through a
separately coded parser plus manually authored test anchors.

There are 864 training, 72 validation, and 72 held-out tasks. Every split balances
all nine procedure/binding combinations. Input instances and wording templates
are disjoint. The holdout remains internally authored, not an external audit.

The model receives only problem and observations. Training targets supervise the
two heads. The tokenizer learns vocabulary from TRAIN only. Test answers and
provenance are in a separate file; every arm's predictions must be saved and
hashed before the evaluator opens test_private.json. The simple rule selector
uses the same public fields.

Structural/surface checks are not neural outcome checks. On AWS, an independent
direct-native reference checks actual outputs. Task correctness requires the
right executed input, actual published result and output tensor, correct
workflow/repair state, and intact authority. A valid trace alone does not pass.

## Training and comparisons

A small separate CASformer encoder and learned positive-control adapter propose
the procedure and binding. The generic learned selector uses the same public
features, tokenizer, two-head objective, optimizer schedule, training examples,
and number of layers. Its real feed-forward width is chosen to match trainable
parameter count within 1%; no unused padding parameters are added.

The pilot compares CAS untrained, CAS trained, the simple rule, and generic
trained selectors. Generic untrained is retained as an additional before/after
control. The saved initial CAS checkpoint is the exact starting point for its
trained candidate. Validation chooses the checkpoint; test data does not tune it.

The initial pilot uses one preregistered seed, not a multi-seed performance claim.
Report fractions with numerators/denominators, procedure accuracy, binding
accuracy, task correctness, repair success, invalid actions, GPU/wall time,
memory, and native reserved policy units. Policy units are not GPU cost or FLOPs.
No CAS-specific advantage follows from a single successful learning run.

## GPU boundary and frozen code

All neural forwards, backwards, and evaluation execute on AWS CUDA. The code
refuses CPU fallback. The laptop runs only text generation, syntax/contract
checks, source hashing, packaging, and AWS control requests.

The accepted native runtime was CPU-oriented. A new pilot-owned device transport
adapter moves tensors and the fixed network to CUDA and requires the exact same
integer compute plan. It does not edit accepted source or bypass its guards.
This bridge itself must pass the AWS integration checks before a learning
result can be accepted.

BASELINE_MANIFEST.json protects 316 accepted files. Installed casformer and
cas_cjt files are compared byte-for-byte against the two frozen wheels. The
meta executor is imported from its declared accepted sibling. Every actual
execution also checks that its native model parameters remain unchanged.

## Running

Keep the portable package's research siblings together. From this pilot directory:

    python -m cas_meta1.curriculum --output a_new_dataset_directory
    python -m pytest -q

Default pytest excludes GPU-marked cases. Do not override that exclusion on the
laptop. The frozen wheels and requirements-gpu.txt are for the AWS environment;
do not install a CUDA training stack on the laptop.

On the AWS GPU only:

    export CAS_META1_RUN_GPU_TESTS=1
    python -m pytest -q -m gpu
    python -m cas_meta1.train --data data --output runs/aws_pilot

Use a NEW output directory. GPU exceptions and failed task cases must be kept
in the run evidence, not silently removed from the denominator.

The AWS launcher is plan-only by default:

    python aws/launch.py

See aws/README.md for the pinned-archive, approval, cloud deadline, artifact
download, and cleanup commands. The proposed first run is one g4dn.xlarge,
at most 60 minutes, with no automatic retry and a $2 per-launch reservation
against the owner's approved $100 task cap.

## Evidence and scope

records/ACCEPTED_BASELINE.md records the owner's restart acceptance. The supplied
acceptance text is preserved byte-for-byte. Original meta/v0.2 records remain
with their original snapshots, including the historical missing failing pair.

data/dataset_manifest.json records split identities and checks. GPU runs must
save initial and trained candidate checkpoints, all arm predictions, actual
execution evidence, environment, source/archives hashes, and metrics.

Missing until AWS execution: CUDA compatibility results, trained checkpoint,
actual task correctness, before/after improvement, cloud runtime and cost.
No result is invented to fill those fields. No training is performed in the
accepted native CJTs, and no baseline is automatically promoted.

No pulsation, extra Noetic meanings, Foundation recursion, dynamic program
synthesis, larger compiler, production readiness, or broad reasoning claim.

## Design sources

The owner request in this task authorizes learned selection.
The SDG construction/validation pattern was checked against:
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas-synthetic/README.md
SHA-256: 1635359fbc620c7a04e57e6ebca12a7aaff0f11873693face5286470f43af3c4

This pilot implements a small adapter for current runtime tasks. It does not
silently import the broader SDG language or claim its entire service is wired in.
