# Replication and receipt — FROZEN law

## The execution receipt (one per Gate 1B campaign)

A single machine-readable receipt (`GATE1B_EXECUTION_RECEIPT.json`, committed with
the results) records, per job and in campaign totals:

- model revision SHA + per-weight-file SHA-256 (pinned at container build)
- code commit SHA (the frozen package commit the signed approval names)
- dataset digests (train/val/protected content SHA-256; the protected digest must
  equal the pre-registration `c911c1…a09563`)
- container image digest; pip freeze digest
- SCMPE table digest, balance counts, orthogonality statistic (pre-result)
- selected layer L* with the four selection accuracies and tie-break
- per run: arm, seed, instance type, region, start/end UTC, wall-clock seconds,
  training-curve digest, raw result-file digest, cost USD
- the deterministic status program's digest and its emitted statuses
- cost reconciliation against the AWS billing export

## Determinism and replay

- Everything on the result path is seeded and recorded; two runs of the same job
  spec must produce identical raw result files (bit-stable kernels where the stack
  allows; where GPU nondeterminism is irreducible, the receipt records the
  tolerance actually observed across the mandated duplicate of one arm/seed —
  S0/seed 11 is run twice for this purpose — and that observed tolerance is
  reported next to every claimed difference).

## Independent re-run law

- The receipt must contain everything a third party needs to re-run the campaign
  from the public checkpoint + the committed package: no hidden state, no
  unrecorded flags, no manual steps. An independent cross-model software audit of
  the Gate 1B results (fresh environment, receipt replay, status-program re-run)
  is REQUIRED before any Gate 1 claim status is treated as final — the same
  discipline that froze Gate 0.

## Honest-labels law

Receipts and reports use the claim-status vocabulary of THRESHOLDS_AND_STATUS_LAW
and the spec-sheet legend. Internal results are labeled internal; the independent
audit is labeled a cross-model software audit, not scientific replication; no
number is rounded or paraphrased.
