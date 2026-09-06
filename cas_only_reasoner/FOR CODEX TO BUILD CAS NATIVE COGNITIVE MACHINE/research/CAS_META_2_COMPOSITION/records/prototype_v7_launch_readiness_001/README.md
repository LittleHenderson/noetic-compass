# Exact-original v7 launch evidence

The frozen source passed clean-checkout checks before paid launch. The single
bounded AWS job then passed its GPU gate, assembled the declared dataset, and
entered training. This is launch evidence, not a completed learning result.

- Source commit: `42f9164754312f12850d9b8789c062fa7fb8069f`.
- Source archive: `../aws_prototype_v7_source_001`, SHA256
  `f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9`.
  It contains 603 closed source files plus the launch manifest.
- Clean proof: `../clean_source_prototype_v7_002/run_003/receipt.json`, SHA256
  `d761a19b9db1cc469b2439e44da8fda98460064fb88e22b28a276bff929c10c3`.
  1,908 test functions and 356 subtests passed; 11 skipped, 2 deselected,
  1 intentional duplicate-ZIP warning, no failures or errors. This used an
  existing Python environment, not a new environment installation.
- Plan-only proof: `run_002/receipt.json`, SHA256
  `fef50b4a11dd726108ee151a45f41d14b74fb498c2e71b16140a2a280cfc4847`.
  No provider calls, reservation, neural execution, or new task generation
  occurred in that check. Its separate clean-suite field predates the passing
  final clean proof above and is not a claim that it ran that suite itself.

The earlier plan-wrapper write-guard refusal and missing-subnet command refusal
are retained here. Neither launched an instance or reserved another job.

## Actual bounded launch

Job: `cas-meta2-20260906094002-39762c47`.
Instance: `i-0cba54498bb3a3745`, `g7.2xlarge`, one RTX PRO 4500 GPU.
The job uses AWS for neural work; no local model or checkpoint loading is allowed.
The accepted baseline model and executor are unchanged.

```powershell
C:/Python314/python.exe -B aws/launch_prototype_v7.py --execute --archive records/aws_prototype_v7_source_001 --sha256 f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9 --source-sha 42f9164754312f12850d9b8789c062fa7fb8069f --approved-cap-usd 400.00 --subnet-id subnet-0eb3ca4bf5ca98f24 --receipt-dir records/aws_prototype_v7_001
```

This command runs from the CAS_META_2_COMPOSITION package directory. The provider
receipt is `../aws_prototype_v7_001/launch_receipt.json`; it remains live until
the launcher finishes. Do not treat its initial STARTING state as a final result.

Canonical budget revision 11 reserves $7 for this job, $78 across the campaign,
and leaves $322 unreserved under the existing $400 cap. Remaining capacity is
not a spending target. Reservations are not invoices and are not automatically
refunded. The plan's conservative $6.46 bound fits inside this reservation.

The independent termination schedule was confirmed for
`2026-09-06T11:50:17Z`. The job has no automatic retry or deadline extension.
Phase limits are GPU gate 450 seconds, dataset 180, training 3,300, native
evaluation 2,700, parent 6,900, compute window 7,200, instance 7,800.

## Observed assembly, not yet independent final-packet admission

Public observation `../aws_prototype_v7_observation_001/status_20260906T095157233974.json`
records the AWS parent entering training after assembly:

| Partition | Actual records | Depth distribution |
|---|---:|---|
| Training | 896 | depth 1: 128; depth 2: 384; depth 3: 384 |
| Validation | 96 | depth 1: 32; depth 2: 32; depth 3: 32 |
| Held-out test | 72 | depth 3: 48; depth 4: 24 |

The public log records all original 256 training records imported and assembly
receipt SHA256 `0547a6cf730272c409cf4e4e691679df5591aa368c34e71d6835cc327d104f91`.
The actual complete packet, training recount, and native task results still
require independent checks after collection. No new held-out score is asserted
here. Checkpoint selection uses validation only.

The 72 test variants form 24 related triplets. They test unseen program
combinations and fresh observations together, with a separate wording contrast
and depth-4 extension. They do not separately estimate fresh-instance performance
for familiar programs. Earlier familiar 24/24 and held-out CAS 0/72 findings
remain separate, unchanged evidence.
