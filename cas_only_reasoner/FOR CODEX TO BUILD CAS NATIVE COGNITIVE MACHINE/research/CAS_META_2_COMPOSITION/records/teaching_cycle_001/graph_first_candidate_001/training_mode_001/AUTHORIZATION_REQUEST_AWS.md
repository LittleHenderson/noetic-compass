# Targeted ^6 specialist — precise AWS authorization request (NOT LAUNCHED, NOT RESERVED)

Status: **AWAITING_OWNER_AUTHORIZATION.** The finished package exists; no
launch has occurred and no reservation has been made. The owner's signed
record must bind the exact identities below.

## Package identities (finished, byte-fixed)

| Field | Value |
|---|---|
| source_sha (freeze commit) | `ce1a3882c57400bb72a810c056c4baf978b72db6` |
| archive_sha256 | `52151c8bb00b45e5e442fd52246d15515c98fe6b2bc745237a4c08992206f580` |
| manifest_sha256 | `0b2801752dcf4dd46e858485584dd52130b76fdc951c33a597f60c294831d2b4` |
| package | `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/package_001/source.zip` (356,470 bytes, 30 members) |
| proposed job | `cas-meta2-teaching-graph-20260909011302-e654ae56` |

The package contains: the graph-teaching package (graph, reference, lessons,
adapter, real_framework, trainer), the frozen encoder path (public tokenizer +
fixed projection), the corrected worker (both conditions, original-inner-error
capture, evidence on failure), and the two frozen wheels. Execution uses
`aws/graph_training_launch.py`, which carries every binding-fit execution fix
(us-east-1 pricing client, bounded IAM propagation wait, cleanup detach and
inline-policy order, bounded termination wait before security-group deletion,
training_result naming, owner-record binding).

## What the run does (per ADAPTER_SPEC.md)

Graph + structured request → candidate `^6` decompose module → frozen
dot-product readout → option prediction → checker-derived correction →
AdamW updates to `operation:^6` parameters ONLY → digest-verified containment
report → sealed-split evaluation with predictions recorded before answers.

## Budget (resolved: per condition AND totals, one job)

| Scope | Value |
|---|---|
| per condition (cas, generic) | 64 optimizer steps, 600.0 wall seconds, lr 0.003 |
| totals, one job | 128 optimizer steps, 1200.0 wall seconds |
| conditions | `prompt_framing_only` — same graphs, options, and answers; framing differs. NOT an architecture comparison |
| instance | one `g7.2xlarge` (`RTX PRO 4500`), account `807562639912`, `us-west-2`, AMI `ami-0fbbd0facbc9e3cff`, torch `2.11.0+cu128` |
| reservation | ONE new `4.00` USD reservation, no refund, no automatic retry |
| data | train 48 + practice 16 (whole-part); validation 16 + test 16 sealed, post-training only |

## Deliverables on completion

Per-arm and total: before/after per-op training loss, per-op lesson exposure
(records and updates), actual completed updates, checkpoint identities,
containment report (forbidden changes named), execution/cleanup outcomes, and
the sealed-split evaluation (validation/test predictions sealed before
answers). Original errors preserved on any failure.

## Explicitly not authorized

- No automatic retry; no second reservation; no modification of accepted
  models, trainers, the ledger, frozen negatives, or sealed splits.
- No promotion of the binding-fit CUDA hypothesis (stays hypothesis-only).
- No reading of protected final-test answers of any other task.

## Signing procedure

The owner's signed record must bind this document's sha256 and the identities
above. Until that record exists and is committed, the launch request stays
`launch_authorized: false` and nothing runs.
