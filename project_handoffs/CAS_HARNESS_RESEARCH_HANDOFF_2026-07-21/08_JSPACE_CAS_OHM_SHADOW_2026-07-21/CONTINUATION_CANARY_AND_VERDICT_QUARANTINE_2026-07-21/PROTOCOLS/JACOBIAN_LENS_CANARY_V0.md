# Jacobian-lens technical canary v0

Status: **FROZEN TECHNICAL PREREGISTRATION / SHADOW / NOT LICENSED**

Canonical protocol: `JACOBIAN_LENS_CANARY_V0.json`

Canonical semantic SHA-256:
`1a6745617a641649fa9f270220c17921409b05b8168cfcb806b2056e6763aff5`

Raw-file SHA-256:
`fb302300829889072c68e5fd0f0e9ac1710daa58aab4aae5abc76a8eee360cb1`

This protocol tests one narrow question: can the pinned Jacobian-lens machinery
compute numerically reproducible local Jacobians, JVPs, VJPs, and
finite-difference responses on the exact registered Pythia-160M revision?

A pass means `TECHNICAL_CANARY_PASS`. It does not mean that J-Space,
CAS-Ohm, semantic probing, prompt-injection detection, output control,
universality, or 300B execution has passed.

## Why this is separate

The prior combined draft incorrectly described the already analyzed Stage-7
test split as unopened. Stage-7 is not used to make this technical canary
prospective. The canary uses eight deterministically selected, exact-token-ID
WikiText blocks and has no semantic licensing effect.

## Exact-token safeguard

The pinned upstream API normally accepts text, tokenizes with truncation, and
can force a BOS token. CAS Harness instead passes registered `block_id`
values to a hash-bound adapter. Its `encode` method returns exactly 128
registered token IDs and never calls the tokenizer. Any unknown block, wrong
length, out-of-range ID, or hash mismatch raises a non-skippable contract
error.

This is the difference between handing a lab the exact specimen and asking the
lab to recreate it from a description.

## Estimator frozen here

For source layer `l`, the matrix is:

`J_l = (1/111) * sum over t=16..126 of sum over t'=t..126 of
partial h_11,t' / partial h_l,t`

The future-target reduction is a sum. Only the 111 source positions are
averaged. Matrix rows are target dimensions and columns are source dimensions.

The tight JVP/VJP checks use each prompt's own local Jacobian. They do not
compare a corpus-average matrix to a different prompt and pretend those should
match.

## Required order

1. Run the protocol verifier. It checks both canonical semantic hashes and raw
   file hashes and rejects duplicate JSON keys.
2. Verify the pinned Anthropic source bundle and dependency lock.
3. Freeze the exact 1,000-block corpus manifest and its domain-separated Merkle
   root. The canary may use only selection ranks 0 through 7.
4. Place the canonical protocol digest in an independent timestamp or anchor.
   A neighboring local sidecar is not an external anchor.
5. Use a separate research environment and GPU with at least 24 GB VRAM. Do not
   modify or interrupt the production worker.
6. Run all eight blocks. Skipping is a failure.
7. Retain successful, failed, and interrupted receipts with hashes, GPU
   identity, peak VRAM, wall time, and measured provider cost.

## Hash files

`JACOBIAN_LENS_CANARY_V0.canonical.sha256` is the SHA-256 of restricted-JCS
canonical bytes. `JACOBIAN_LENS_CANARY_V0.sha256` is the ordinary SHA-256 of
the raw JSON file. They are deliberately different and must not be confused.

## 300B boundary

This canary is a dense 768-by-768 small-model test. A real 300B lane needs
projected JVP/VJP or randomized low-rank sketches, sharding, checkpoint/resume,
reconstruction-error gates, authenticated workers, and durable evidence.
