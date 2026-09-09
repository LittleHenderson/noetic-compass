# Graph-first ^6 — lookup-repaired diagnostic — one-job authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** Per the owner's directive, this returns
the exact package and the one-job request BEFORE any new reservation or
launch. Training remains pending.

## The only behavioral changes from the preceding (attempt-005) version

1. **Lookup repair (measured root cause):** `real_framework.build_encoder.embed`
   now maps token ids to projection rows directly — ids ARE vocabulary
   positions. Verified purely through the ACTUAL tokenizer-to-row path (real
   `LosslessPublicTokenizer` → real ids → repaired rows; distinct ids reach
   distinct rows). Invalid internal ids are REJECTED explicitly
   (`ENCODER_TOKEN_ID_OUT_OF_RANGE`), never silently mapped to row 0; there
   is no legitimate unknown token at runtime (the tokenizer's byte fallback
   keeps every unit in-vocabulary).
2. **Same-token-count graph rewiring contrast:** the graph-edit measurement
   gains a third valid edit — swapping the SOURCES of two `contains`
   connectors, which preserves the problem token multiset exactly while
   changing the relationships — plus per-edit token-count and
   token-multiset-equality fields. This distinguishes preserved vocabulary
   from preserved relationships.

Nothing else changed behaviorally: module weights (untrained initial state),
pooling variants (sum options with the content-only correction; mean
problem), lessons, and budgets are fixed exactly as in the preceding
version.

## What the job measures (zero updates, both arms, same examples and weights)

- individual tag vectors before pooling (do different part names reach
  different numbers now?),
- OLD vs CORRECTED option-vector score spreads, argmax, cosines,
- graph-edit response for all three edits (retarget, node contents,
  same-token rewiring) — token counts/multisets, output difference, decision
  changes,
- answer-score differences and alternative-target gradients (does a
  corrective signal survive that distinguishes the options?),
- module-output norms and pairwise cosines.

No correct untrained answer is demanded anywhere: the run measures whether
the relevant distinctions and corrective signals SURVIVE the pipeline.

## Exact package (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `6983d17fe043289686936ec6627665abc4bac650` |
| archive_sha256 | `3f67582734e90fc07611b43f246ad0604a77252abdf0b0db7b11b177ebc4a4ad` |
| manifest_sha256 | `ef68cea957eb7004d7b907e7e2a6ca08288bdefe9f7e4f48ba44eb5c09c1e315` |
| package | `training_mode_001/ln3_diagnostic_package_005/` |
| launcher | `aws/graph_training_ln3_diagnostic_launch.py` at commit `eac74033` (fixed) |

## The one-job request

- ONE measurement-only job (both framing arms), `optimizer_steps_permitted:
  0`, `max_wall_seconds: 1200.0`, sealed splits NOT consulted.
- ONE new `$4.00` reservation, exactly once, no refund, no automatic retry.
  Ledger today: revision 39, `$206.00` reserved / `$194.00` unreserved;
  after this job's reservation: revision 40, `$210.00` / `$190.00`.
- Worker fails closed if any weight changed; evidence persisted on every
  exit; verified cleanup.

On GO I will mint the job id, write the owner record binding these exact
identities, register the launch inputs, and execute — nothing before.
