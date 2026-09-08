# Read-only inspection of partial teaching saves

This is a support tool for inspecting a collected teaching job. It does not
resume training, create cloud resources, reserve money, or change the frozen
worker. A successful structural check is not a successful GPU restart.

## What is checked

- Independently supplied hashes bind the parent result, completion marker and
  original collected ZIP. Extracted files must match the ZIP before and after
  inspection.
- All saved checkpoint transactions, their file hashes and receipt chain are
  checked. Initial and latest references must match the original Linux paths.
- The frozen training records determine the record-registry identity. The
  declared CUDA mode, exact identity fields, allocation and batch size must match.
- The unchanged pure resume checks replay committed events up to, but never
  through, the actual tensor-restore call.
- Each arm reports committed updates, examples, teaching-cycle counts, unfinished
  allocation and any uncommitted tail. An uncommitted tail blocks continuation;
  it is never silently discarded or counted as saved learning.
- Real learner construction, real model scope, tokenizer/tensor geometry and
  optimizer restoration remain UNEXECUTED. These require a separate AWS check.

The original logical run ID and absolute campaign directory must be restored
unchanged for the existing worker's --resume-summary path. This inspector is
not a cloud continuation transport and grants no launch authority.

## Captured checks

The combined check passed **258 tests in 135.86 seconds**, exit 0, with unchanged
before/after hashes for 75 dependencies, including the canonical budget ledger.
The suite consists of the existing 229 transport checks and 29 new inspector
checks. Raw stdout/stderr, command, environments and hashes are retained in
continuation_checks_001. These tests use fake cloud clients and synthetic
CUDA-shaped records, not actual CUDA execution or tensor restoration.

Receipt SHA256:
381c17199c6e82752723ba9cc6d3554c786fe992b431b2aff6da9b7f57e8d1d9

Raw stdout SHA256:
ad6ae5722496062206be43022096151aa3472e51bdfff94ccc8b863ce18ee6e2

Run from this exact package directory:

    C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION

Use a fresh destination for another recorded check:

    & 'C:/Users/wakil/AppData/Local/Programs/Python/Python312/python.exe' -I -B tools/check_teaching_continuation.py records/teaching_cycle_001/continuation_checks_NEW

For a collected job, first verify and extract it with the existing
tools/evaluate_teaching_launch.py. The inspector accepts --parent-result,
--complete-marker, --archive, --extracted-root, and the three independently
supplied --parent-sha256, --complete-sha256 and --archive-sha256 values.
An optional --output must be a fresh file inside the teaching records directory.
No actual collected checkpoint was inspected in this test capture.

The owning agent's earlier 28-test run was transcript-only. The main agent then
added a frozen features_v2.py byte check and a registry-equivalence test against
the unchanged adapter before the captured 258-test run. The independent
read-only review and main review were support-tool reviews, not new core audits.

## Running job remains separate

At this record, the job remains cas-meta2-teaching-20260908052915-8b5df59c.
Its transport source is f0befae3956086eaf8d7115919f2d05349ec4b97; its frozen
worker source remains c8c0e558cf30cd5fe06c2bf3d475697e97698a3e. No running
source, accepted weights, native executor, allocation or reservation was changed.

The first CUDA-update marker is retained under job_003/launch/first_update.json.
It is worker-reported training activity, not a held-out improvement.
A separate read-only EC2 call at 2026-09-08 06:08:07.203 UTC observed instance
i-0272a6d80f3b5ad75 running (request a0271f7e-0c16-4294-bba6-e059de0421ad).
That call did not observe the worker's current training phase; its compact output
is in the task transcript, not a claimed full raw provider-response artifact.

The job's reservation stays $8. Canonical ledger revision 19 remains $118
reserved and $282 unreserved under the inclusive $400 cap. These are budget
reservations, not AWS invoices. No full allocation, final score, successful
GPU continuation, native execution or retention after new learning is claimed.
