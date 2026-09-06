# Partial v7 native audit

This is a separate audit of a failed, fully collected run. It does not alter or bypass the frozen success-only v7 reviewer. It never emits `PROTOTYPE_V7_STORED_REVIEW_PASSED`.

Fixed job: `cas-meta2-20260906094002-39762c47`.
Source: `42f9164754312f12850d9b8789c062fa7fb8069f`.
Packet SHA256: `f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799`.

The native child exceeded its existing 2700-second evaluation limit with one of 72 futures unfinished. The parent captured exit 1; the outer process timeout flag is false. No retry, extension, new GPU job, or retraining is performed by this audit.

## Exact scope

The checker requires 71 complete case receipts, all 72 completed references, and the three completed comparison arms in case45. It verifies all 358 available arm outcomes with the unchanged saved-result verifier or exact pre-execution rejection checks. The known durable-round-trip runtime failure remains a separate post-start failure; its unchanged committed-prefix checker is reused only when that exact error record exists.

Case45 generic-trained has only a database plus WAL/SHM files. Its correctness stays unknown. The independent copied-database prefix receipt `fc444ba90f71cca2d1b539884da56f5ddc32d41b3e841c3dbf4c94867fd17fbe` is pinned, along with its packet/input/public/action identities. It supplies 37 committed runs and 2664 reserved policy units as lower bounds. It does not supply a final outcome or the cause of the unfinished work. The original WAL-bearing files are never opened writable here; their separate byte-safe audit is in `records/prototype_v7_timeout_prefix_001`.

Case45 rule did not start. Thus each arm retains all 72 scheduled slots, but rule has 71 actual attempts and one not-started slot. Generic-trained has 72 attempts, with one unfinished result. Unknowns are not relabeled false. A separate common-completed-71 comparison is reported without replacing the registered 72-slot view.

All completed worker receipts are source/model/baseline/environment checked. Case45 has no final worker identity receipt; the report states that gap. Its completed reference and three stored arm outcomes still have their applicable saved-result identities checked. No missing worker receipt is invented.

## Admission and evidence

- The extraction receipt `9bf40771df6dd7f67189d402d6bcfd8e05bd8cd997b71a6825fff21da105ae98` binds all2941 packet members. The original packet is not re-extracted.
- The independent training recount `452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76` binds the saved training and dataset. This checker independently rechecks source603/protected316, accepted baseline/wheels, all72 task/public/five-arm mappings, exact seals, and private-opening order before native reads.
- The original packet, extraction, source archive, helper bytes, and externally pinned receipts are checked again at the end. Only new local audit records are written.

The literal input-name and child-site diagnostics are separate from task correctness. Complete-event comparisons use the independently correct rule when available. Case45 uses the checked private reference, explicitly labeled as such, not an invented rule execution. Only recorded committed RUNs are compared for an unfinished prefix. The first recorded mismatch does not establish the earliest causal neural decision.

## Run and capture

From `research/CAS_META_2_COMPOSITION`:

```powershell
C:/Python314/python.exe -B records/prototype_v7_partial_native_001/capture.py execution_001 run_001
```

Use new directory names for later reruns. The capture runs 10 pure report tests and 10 fake-record boundary tests first, then starts the actual audit in a fresh child. It retains exact commands, process IDs, raw stdout/stderr, return codes and before/after helper hashes. The expected successful audit artifact is `run_001/partial_native_receipt.json`; a failure instead writes `run_001/failure.json` and exits nonzero. The existence of this README is not a passed result.

The audit's scope is stored evidence. It loads no checkpoint tensors, executes no neural model, calls no provider and changes no accepted verifier, model, source, or prediction. A passed **partial evidence audit** does not make the failed campaign complete or establish held-out improvement.

## Actual saved result

The captured audit completed on 2026-09-06 at 11:45:24 UTC, child PID 68180, exit 0, empty stderr, captured wall time 654.4237456 seconds. Receipt SHA256: `bc700054e18dad6de9e2516f441adccdfac0a9ace25a39fd0fce6a0879d37f4f`. Capture receipt SHA256: `2be450826c3d91c8671d8fe06094e2d48427f75a15918a22a853027f55c55696`.

Status is `PARTIAL_NATIVE_EVIDENCE_CHECKED`, with campaign and native evaluation still incomplete. CAS scored 0/72 before and after. Generic trained has 0 correct, 71 incorrect and one unfinished result across 72 attempts. Rule scored 71/71 actual attempts with one scheduled case not started. The final report and all 360 first-error rows are in the sibling `records/prototype_v7_report_001` package.
