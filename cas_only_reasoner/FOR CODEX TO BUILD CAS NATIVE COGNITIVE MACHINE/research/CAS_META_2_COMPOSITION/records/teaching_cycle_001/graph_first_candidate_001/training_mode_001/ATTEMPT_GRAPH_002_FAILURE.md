# Graph-first ^6 training — AWS attempt 002: original inner error PRESERVED and diagnosed

Status: AWS_GRAPH_TRAINING_FAILED. The lifecycle worked (launch, reservation,
worker, wait, collect all succeeded); the worker's inner runner failed, and
this time the **original inner error was preserved verbatim** — the
error-capture fix from the review milestone did its job. The `$4.00`
reservation is consumed; this job is closed; no retry.

## Attempt identity (byte-bound)

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909021717-7891f672` |
| request sha256 | `9516bc88ea702feb4373f364769ce82969f60e13cc84c0d21c01c0ae9e952e46` |
| authority sha256 | `97986d963cfedeac2c8c577d7fd019be319bb85fc837d66a6bfada23679a6998` |
| owner record sha256 | `d0b44e814e8534bd001d3493f13c5c689e561f7063ebd616f433db2f96784437` |
| source_sha / archive / manifest | `fec63492…` / `e6c87689…` / `e435e411…` (unchanged from the authorization) |
| reservation | created, `4.00` USD, ledger revision 24 → 25 (`total_reserved_usd` 146.00 → 150.00, `remaining_unreserved_usd` 254.00 → 250.00) |
| instance | `i-0586228abeeea7733` — launched, terminated; never reached training |

Evidence directory:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909021717-7891f672/`

## What succeeded

Preflight; the single `$4.00` reservation; launch; the **wait/collect path**
(the attempt-001 defect is fixed — `NoSuchKey` polls were tolerated until the
worker uploaded its result); worker bootstrap (venv, torch 2.11.0+cu128,
wheels, requirements); the worker's failure report was uploaded and collected
with a verified sha256 sidecar.

## What failed — the PRESERVED original error (verbatim tail)

```text
INNER_RUNNER_EXIT_1
Traceback (most recent call last):
  File "/opt/cas-graph-training/package/_inner_runner.py", line 15, in <module>
    torch, device = gpu_adapter._cuda()
  File ".../cas_meta2/teaching_cycle/gpu_adapter.py", line 43, in _cuda
    execution_guard()
  File ".../cas_meta2/teaching_cycle/gpu_adapter.py", line 39, in execution_guard
    require(os.environ.get("CAS_META2_RUN_TEACHING_CYCLE") == "1", "EXPLICIT_ENABLE_REQUIRED")
ValueError: TEACHING_GPU:EXPLICIT_ENABLE_REQUIRED
```

Root cause: the teaching-cycle GPU machinery has an explicit enable gate —
environment variable `CAS_META2_RUN_TEACHING_CYCLE=1` — and the launch
bootstrap did not set it. The run never reached CUDA or training. This is a
launcher-side bootstrap defect, NOT a package defect: the package identities
remain valid.

(Note: binding-fit attempt 003's inner error was LOST and remains UNKNOWN;
the fact that the same guard class exists there is not promoted beyond
hypothesis.)

Cleanup left one security group behind because the instance was still
terminating when the 300 s wait expired; the instance was confirmed terminated
and the group (`sg-065d7c10aa198fce0`) was deleted manually and verified
absent.

## Fixes (committed with this record; all outside the package)

1. `GraphTrainingProvider._user_data()` now exports
   `CAS_META2_RUN_TEACHING_CYCLE=1` in the bootstrap (the explicit enable the
   guard requires for an owner-authorized teaching run).
2. `_await_terminated` timeout raised 300 s → 600 s so slow instance shutdown
   no longer strands the security group.
3. Three regression tests added (launcher suite now 16): user-data contains
   the enable export; termination-wait timeout pinned; plus the existing
   ClientError wiring assertions.

## Policy status

- Zero automatic retries: this job id is closed forever.
- The `$4.00` reservation stands; no refund.
- A corrected re-attempt requires the owner to authorize a NEW job id, a new
  `$4.00` reservation, and a new owner record binding the SAME package
  identities (`fec63492…` / `e6c87689…` / `e435e411…`).
