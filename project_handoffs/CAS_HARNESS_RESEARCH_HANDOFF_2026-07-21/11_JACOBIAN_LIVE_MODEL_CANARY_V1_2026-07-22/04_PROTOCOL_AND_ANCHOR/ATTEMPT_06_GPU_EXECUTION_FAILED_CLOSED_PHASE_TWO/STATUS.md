# Attempt 6 guarded shadow canary — GPU execution, FAILED CLOSED at phase two

Controlling status:

`OFFICIAL_SHADOW_ATTEMPT_FAILED_CLOSED_AT_PHASE_TWO_TSYNC_INSTALL_AND_UVM_CLOSE / CRLF_REPAIRED_PREFLIGHT_AND_ANCHOR_PASSED / CUDA_INITIALIZED_AND_BOOTSTRAP_TENSOR_COMPUTED / NO_MODEL_WEIGHTS_MATERIALIZED / ZERO_OF_1248_AUTOGRAD_CALLS / SHADOW / NONE / NOT_LICENSED`

## What this run proves and does not prove

This is the FIRST JLCV1 attempt ever to reach live CUDA execution. Attempt 4
failed closed at `PRE_CUDA_PREFLIGHT` (the OpenSSL `-in -` regression);
Attempt 5's one-shot was consumed and its anchor ceremony failed closed at
the CRLF-emitting verifier. Attempt 6, on the repaired implementation
`29551624`, passed both of those stages live and went materially further.

It does NOT constitute a technical-canary pass, a scientific result, or any
`LICENSED` capability. It produced zero artifacts, selected zero blocks for
measurement, and observed zero of the registered 1,248 autograd calls. Claim
status remains `SHADOW / NONE / NOT_LICENSED` and the whole-project score
remains approximately `0.33 / 1.00`; Gate 1's `0.38` requires the technical
canary to independently PASS, which it did not.

## Execution facts (create-once, recovered off-pod)

- Run ID
  `jlcv1-rfc3161-f3e3adad7ff2b94a335fa199a0cda440dcd767e6ac7c10db8d39465b662ed541`,
  research pod `zp2s9pscgncn0b`, official root
  `/workspace/cas-jlcv1-official-29551624-f3e3adad`.
- Post-anchor prelaunch guard passed (`f9377332...`): repository at commit
  `29551624`, tree `0d70f8e8...`, clean; all PRE, control, and anchor files
  byte-verified; GPU idle; zero prohibited processes.
- Wrapper invoked exactly once under `python -I -B`, exit code `0`,
  finished `2026-07-23T16:59:42Z`. Producer status `FAILED_CLOSED`.
- Execution receipt (v3) SHA-256
  `5dd76ac306aa67992f6b69de6a817ab92b58b33de3f3291e321e1505d1955c66`,
  receipt kind `FAILED`, verdict `NONE`, `official_pass_authorized=false`.
- Stages that PASSED live: `OUTPUT_DIRECTORY_PREFLIGHT`,
  `PRE_CUDA_PREFLIGHT` (the CRLF-repaired RFC3161/anchor verification —
  `preflight_completed_under_phase_one=true`), `ML_STACK_PREFLIGHT`,
  `DEPENDENCY_POST_IMPORT_REVERIFY`, `CUDA_BOOTSTRAP_UNDER_PHASE_ONE`
  (torch `2.12.0+cu130`, CUDA runtime `13.0`, driver `580.126.09`, A40; one
  1,024-element float32 tensor summed to exactly 1024.0 on
  `cuda:0`), `MODEL_FREE_CUDA_RUNTIME_IDENTITY`, `CUDA_UVM_LISTENER_MATCH`
  (sole UVM listener `@cuda-uvmfd-4026536912-21944@`, SOCK_SEQPACKET,
  close-on-exec identified).
- Stage that FAILED CLOSED: `PHASE_TWO_TSYNC_INSTALL_AND_UVM_CLOSE`. Failure
  code `NON_SUBPROCESS_FAIL_CLOSED`, stderr 0 bytes,
  `phase_two_install_attempted=true`,
  `phase_two_full_tsync_installed_before_uvm_close_proven=false`,
  `post_guard_cuda_proof_completed=false`. Phase-one seccomp was fully
  active and self-tested (AF_INET/AF_INET6/io_uring/pidfd_getfd all EPERM,
  TSYNC across the single thread, no_new_privs).

## Root cause (diagnosed with a bounded non-official diagnostic)

`research/jacobian_lens_network_guard.py:_proc_unix_record` verifies the sole
CUDA UVM listener by reading the SYSTEM-WIDE `/proc/net/unix` and requiring
the file's `stat` (size, mtime_ns) to be identical before and after the read
(lines 1080-1093). `install_phase_two_guard` performs this stability read
again to re-confirm the listener is unchanged, alongside a TSYNC
thread-inventory stabilization loop.

On the installed `torch 2.12.0+cu130` / CUDA 13.0 runtime, CUDA background
threads continuously open and close AF_UNIX sockets, so the system-wide
`/proc/net/unix` mutates during the read and the stability check raises
`/proc/net/unix changed while being read`. This is NON-DETERMINISTIC: the
official run passed the first `identify_sole_cuda_uvm_listener` and then
failed a phase-two re-read; the reproduction diagnostic failed the first
read. Across four diagnostic runs the CUDA UVM listener was confirmed to be
the ONLY socket fd (its inode rotates each run), so this is a read-stability
RACE against unrelated system-wide churn, not a persistent extra descriptor
and not a genuine isolation breach.

This is environment/version drift: the two-phase guard's quiescent-CUDA
read assumption held on the older torch/CUDA stack it was validated against
but is violated by the newer torch `2.12.0+cu130` installed in the pinned
venv. It is not a CRLF-boundary defect and not a model/scientific failure.

Diagnostic evidence: `diagnostic/phase_two_diagnostic.py` and
`diagnostic/phase_two_diagnostic_transcript.txt` (SHADOW, non-official,
installs seccomp only in its own process, writes no receipt).

## Proposed fix (Attempt 7, guard/trust-surface change — needs review)

Make the UVM-listener proof tolerant of unrelated system-wide `/proc/net/unix`
churn by reading with a bounded retry-until-stable loop — the same pattern
`_task_seccomp_proof` already uses for the thread inventory — accepting the
read only when two consecutive reads agree AND the exact singular UVM inode
record is present and identical. This STRENGTHENS the proof (still requires
the exact sole UVM record to be stable) rather than weakening isolation, and
avoids failing on churn from sockets that are not the UVM listener. A
secondary option is pinning torch to the guard's originally validated version
matching the container CUDA 12.4.1, but that is a dependency re-freeze that
does not fix the underlying fragility. Either path is a change to the frozen
implementation and therefore requires a new branch, regression tests, a full
suite pass, a fresh implementation freeze, and a fresh Attempt 7 identity
(new nonce/PRE/controller capture/anchor and a new owner query approval).
Attempt 6 identities are never reused.
