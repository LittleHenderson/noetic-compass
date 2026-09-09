# Targeted ^6 specialist — AWS training-run authorization request (NOT LAUNCHED)

Status: **AWAITING_OWNER_AUTHORIZATION. No launch, no reservation, no neural
run has occurred.** This document is the executable authorization request the
owner may sign for the first graph-first training run.

## Proposed job identity (inert until signed)

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909011302-e654ae56` |
| arm | both `cas` and `generic` (two separate runs share the same job id suffix policy of prior campaigns; to be finalized in the signed authority) |
| entrypoint | `cas_meta2.graph_teaching.trainer.launch` |
| target module | `cas.cjt.operation.^6.decompose/0.2` |
| permitted plasticity | `operator.^6` only; everything else frozen |
| frozen budget | learning_rate `0.003`, max_optimizer_steps `64`, max_wall_seconds `600.0` |
| reservation | one new `4.00` USD reservation, no refund, no automatic retry |
| resource plan | to be frozen in the AWS adapter build: account `807562639912`, `us-west-2`, `ami-0fbbd0facbc9e3cff`, `g7.2xlarge`, one instance, `RTX PRO 4500`, torch `2.11.0+cu128` |
| training data | `dataset_001` train (48) + practice (16), whole-part ops only |
| sealed data | `dataset_001` validation (16) + test (16) — post-training evaluation only |

## What the signed authorization would pay for (build-first, then run)

1. AWS adapter build: `gpu_adapter.build_graph_training_framework` (real
   torch/CUDA, real decompose module, real plasticity resolution) + learner
   factory + package + launch lifecycle, all pure-tested before any paid run.
2. Exactly one launch attempt with bounded readiness checks, evidence capture
   preserving the original error on any failure, and verified cleanup.
3. Post-run deliverables: before/after per-op training loss and per-arm
   metrics, actual completed updates, checkpoint identities, containment
   report (forbidden parameter changes named), execution/cleanup outcomes, and
   the sealed-split evaluation through `evaluate_sealed`.

## Explicitly not authorized

- No automatic retry, no second reservation, no change to accepted models,
  trainers, the ledger, frozen negatives, or the sealed splits.
- No promotion of the CUDA hypothesis for binding-fit attempt 003 (remains
  hypothesis-only).
- No reading of protected final-test answers of any other task.

## Signing procedure (same as prior campaigns)

The owner's signed record will bind this document's sha256 and the launch
request built from the frozen package identities at adapter-build time. Until
that record exists, nothing runs.
