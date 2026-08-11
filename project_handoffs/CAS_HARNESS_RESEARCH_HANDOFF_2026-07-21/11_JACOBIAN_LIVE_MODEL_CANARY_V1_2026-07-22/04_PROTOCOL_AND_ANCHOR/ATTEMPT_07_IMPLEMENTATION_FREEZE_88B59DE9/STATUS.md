# Attempt 7 implementation freeze — CUDA UVM proc-read churn hardening

Controlling status:

`IMPLEMENTATION_FREEZE_PASS / CROSS_RECONSTRUCTION_MATCH / COMPLETE_V2_SINGLE_HEAD_BUNDLE / DEPENDENCY_ARCHIVE_UNCHANGED / POD_PHASE_TWO_VALIDATED / NO_PRE_OR_RUN_IDENTITY / NO_EXTERNAL_TRANSMISSION / NO_MODEL_OR_CUDA_EXECUTION_IN_THIS_FREEZE / SHADOW / NONE / NOT_LICENSED`

## Outcome

Attempt 6's guarded canary reached live CUDA execution and then failed
closed at `PHASE_TWO_TSYNC_INSTALL_AND_UVM_CLOSE` because the seccomp
two-phase network guard proves the sole CUDA UVM listener by reading the
system-wide `/proc/net/unix` and requiring the file `stat` to be identical
before and after the read. On the installed `torch 2.12.0+cu130` / CUDA
13.0 runtime, CUDA background threads churn AF_UNIX sockets, so ~10% of
reads straddle an unrelated regeneration and fail closed non-deterministically
(measured 27/30 reads stable; only `st_mtime_ns` flips, `st_size` is always
0). Full diagnosis and evidence:
`../ATTEMPT_06_GPU_EXECUTION_FAILED_CLOSED_PHASE_TWO/`.

The frozen implementation identity is:

- branch `fix/jacobian-guard-procunix-churn-20260723`;
- commit `88b59de924857ad7c2f394122fe68f57ba97da77`;
- tree `d38d83c0971596cbe86006e1dadf077d8b1a62f0`; and
- parent `29551624f4de0eec61c4035e364203be55d6c08a` (the Attempt 6 CRLF
  freeze commit).

## What the repair changes

`research/jacobian_lens_network_guard.py` factors the `/proc/net/unix` read
into `_read_stable_proc_unix_bytes()`, which wraps the exact original
stat/read/stat atomicity check in a bounded retry-until-stable loop
(`MAXIMUM_PROC_UNIX_READ_ATTEMPTS = 64`), mirroring the existing
`_task_seccomp_proof` thread-inventory stabilization pattern. The per-read
guarantee is unchanged — a read is accepted only when the file did not
change during it — so the sole-UVM-record singularity and identity checks
are untouched; the guard simply no longer gives up after one unlucky
straddling read. This strengthens robustness without weakening isolation.
Oversize protection is preserved (>8 MiB fails closed). Three trust-surface
files change: the guard, the bootstrap hard-pin table
(`scripts/run_jacobian_lens_canary_v1.py`), and the guard tests.

## Verification

- Four new regression tests (retry-past-churn, fail-closed-when-never-stable,
  first-read-no-retry, oversized-payload) exercise the loop deterministically
  via mocked stat/read sequences.
- Complete `live-trace-worker` suite: `942 passed, 2 skipped` on Windows
  (Attempt 6 baseline `938` plus the 4 new tests).
- POD VALIDATION: the full live sequence phase-one -> CUDA bootstrap ->
  identify sole UVM listener -> phase-two TSYNC install + UVM close ->
  post-guard CUDA proof passed **13/13 consecutive runs** on research pod
  `zp2s9pscgncn0b` with the fixed guard, where the pre-fix guard failed
  non-deterministically at exactly this stage. Transcript:
  `pod_phase_two_validation_8x.txt` (last 8 of the 13).

## Implementation manifest and bundle

- 31-file implementation manifest: 5,689 bytes, SHA-256
  `af11038190763d477d43b87fdffb3b4e2dffa7f966ce95537384d740c59a7a72`;
  byte-identical from an independent bundle reconstruction; all 31 records
  match canonical Git blob bytes (blobs are LF; the modified files were
  normalized to LF so worktree == blob == pod checkout).
- Complete v2 single-head bundle: 36,560,536 bytes, SHA-256
  `693b4da1538131959b9511079e...` (full value in the freeze record);
  `git fsck --full --strict` clean, detached at the exact commit.
- Dependency archive unchanged (`ed16af7a...`).

## Evidence boundary

Implementation-preservation plus a non-official pod validation only. No
Attempt 7 PRE, nonce, run identity, RFC3161 query/response, anchor, launch
configuration, official model run, autograd measurement, artifact, product
verdict, or `LICENSED` capability exists. Execution mode `SHADOW`, verdict
`NONE`, claim status `NOT_LICENSED`, whole-project score approximately
`0.33 / 1.00` (Gate 1's `0.38` requires an official technical-canary PASS,
not yet run on this fix).

## Next executable action

Run the full Attempt 7 create-once ceremony on the repaired implementation:
fresh isolated-GPU prestage at commit `88b59de9`, fresh
nonce/run-ID/official-root/PRE/controller-capture/protocol/anchor/query,
byte-specific owner query authorization (the owner's standing
pre-authorization of 2026-07-23 covers project actions; each transmission
is still recorded byte-specifically), then the guarded canary, off-pod
recovery, and independent receiver. Attempt 1-6 identities are never reused.
