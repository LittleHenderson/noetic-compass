# Attempt 4 corrected implementation freeze

Controlling status:

`IMPLEMENTATION_CORRECTION_FROZEN / LOCAL_REGRESSION_PASS / CROSS_RECONSTRUCTION_MATCH / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

## Outcome

Attempt 3 was not executed after prelaunch review found that its anchored
seccomp launcher started the child interpreter with `-I` but omitted `-B`.
That child could create `__pycache__` files after the exact 15-file
dependency preflight and invalidate later evidence verification.

Commit `be97bc7f76d1e9f5e501702660678d4af3081f5e`, tree
`4eb382528e8a4cee81a1c043f65bf0dcfa369ccf`, corrects the defect by:

- requiring interpreter-level bytecode suppression in both wrapper and child;
- executing the child with exact flags `-I -B`;
- refusing to rely on `PYTHONDONTWRITEBYTECODE`;
- re-inventorying the dependency root immediately after `jlens` imports;
- re-inventorying it again before normal candidate or numerical-failure
  receipt construction and publication; and
- failing closed at either mutation boundary.

## Verification

- Focused suite: `94 passed, 1 skipped`.
- Complete live-worker suite: `926 passed, 1 skipped`.
- The sole skip is the expected Windows skip for Linux sealed-memfd execution.
- A real import of the 15 vendored `jlens` files proves `-I` creates
  disallowed `.pyc` entries while `-I -B` preserves the exact inventory.
- The first complete-suite run exposed only a missing ignored local
  `drand-client@1.4.2` test dependency (`924 passed, 1 failed, 2 skipped`).
  The exact already-installed copy from the frozen checkout was reused without
  a network download or tracked-source change; the targeted test passed, then
  the complete suite passed as reported above.

## Frozen artifacts

- Implementation manifest: 31 files, 5,689 bytes, SHA-256
  `bbaaa973372cd95c3c99472a31664ab2add699cf1d844a5b2ab28a763dd04ffb`.
- Independent reconstruction manifest: byte-identical, same size and SHA-256.
- Complete v2 single-head Git bundle: 36,536,084 bytes, SHA-256
  `3ddf60a6f24c204489a70c62465efed3ccd421baa7739bffa923d26821512b67`.
- Bundle head:
  `refs/heads/fix/jacobian-child-bytecode-guard-20260722`.
- Bundle verification: complete history.

## Evidence boundary and next action

This freeze is implementation evidence only. It is not a model run, steering
result, prompt-injection result, universality result, 300B result, product
verdict, or `LICENSED` claim.

An exception before that second checkpoint can publish only a `FAILED_CLOSED`
receipt and cannot publish a candidate or scientific result. The exception
path does not presently claim a second dependency re-inventory; broader
concurrent-writer filesystem hardening remains `OPEN / NOT_LICENSED`.

Next executable action: construct a completely fresh Attempt 4 RunPod
workspace and dependency root; verify the real Linux `-I -B` wrapper path;
capture fresh controller/tools/network-plan/PRE evidence; generate a fresh
nonce, run ID, protocol, mapping, payload, and RFC3161 query; then obtain
approval for those exact query bytes before one transmission.
