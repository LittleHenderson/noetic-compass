# Failed v6 training run: evidence boundary

Original source: `acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0`.
Original job: `cas-meta2-20260906064703-c0d74ffa`.
This run is **failed**, not a completed learning evaluation.

## What actually completed

Both candidate families finished 200 epochs and 8,000 optimizer steps.
The byte-checked validation measure is exact freely generated program plus
binding, not verified native task correctness:

| Family | Before | Selected validation | Depth 1 | Depth 2 | Depth 3 | Selected epoch |
| --- | --- | --- | --- | --- | --- | --- |
| CAS | 0/96 | 30/96 | 30/32 | 0/32 | 0/32 | 180 |
| Generic | 0/96 | 29/96 | 29/32 | 0/32 | 0/32 | 160 |

Checkpoint choice used validation only. All 72 neural prediction rows and all
72 five-arm prediction rows were sealed before private evaluation.

Native evaluation stopped after completing cases 0, 3 and 6. Case 9's trained
CAS program reached the executor, then raised:

`RuntimeContractError: repair cannot open without a durable distinct ^6 round trip`

It left seven committed ACCEPT traces. The failed next tick has no committed
receipt. No complete 72-task correctness score is available from this failed
run. One admitted candidate failure stopped the other case workers.

## Separate experiments, separate claims

- Earlier held-out result: CAS **0/72**, generic **12/72**, rule **72/72**.
- Familiar-program practice fit: both families **0/24 -> 24/24**. That was not
  fresh-task generalization or native execution.
- This v6 run: 640 training, 96 validation, 72 test variants. It used the broader
  contrast construction method but **did not include the literal original
  256 practice records**.
- The exact-original256 bridge is separate v7 preparation. No completed
  896/96/72 experiment is claimed here.

The 72 test variants represent 24 matched triplets, not 72 independent program
structures. They compare new depth-3 structures with familiar wording,
wording-shift variants of the same structure and observations, and related
depth-4 variants. This is not an isolated test of new inputs for already-known
programs, and it is not unrestricted natural-language reasoning.

## Recovery boundary

A separately frozen evaluation-only recovery may execute the **same saved
five-arm choices**, without training, changing actions, or resealing predictions.
It must remain labelled as evaluation on an already-exposed test. It cannot
turn the original failed campaign into a completed campaign or a new fresh test.

The recovery may contain only the exact known post-start runtime exception.
It must count that attempt as incorrect, not as a pre-execution rejection.
Unrecognized exceptions, source changes, reference failures and verifier
failures remain fatal. Partial committed work is a lower bound; missing failed
tick compute must stay unknown.

## Evidence and cost

- Result packet SHA-256:
  `db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def`.
- Packet: 74,958,249 bytes; 879 members; no omitted files. Complete collection of
  this failed run is not complete evaluation.
- Failure review receipt:
  `records/contrast_failure_review_v6_001/run_002/failure_review_receipt.json`,
  SHA-256 `d479c90f711d417f2f585b87a0b746e250db8db12029df1586a4fbabf3b82420`.
- Compute, disk and public-IP estimate: **$2.036618596444444444444444444**.
  S3, transfer and tax are excluded; this is not an AWS invoice.
- Cleanup receipt confirms all seven resource checks passed. The original
  $7 reservation remains reserved; no automatic refund has been made.

