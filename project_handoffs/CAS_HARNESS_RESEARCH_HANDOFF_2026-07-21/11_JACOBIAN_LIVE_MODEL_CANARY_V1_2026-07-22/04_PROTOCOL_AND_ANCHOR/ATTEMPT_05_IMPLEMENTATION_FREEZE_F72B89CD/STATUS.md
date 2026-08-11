# Attempt 5 implementation freeze

Controlling status:

`IMPLEMENTATION_FREEZE_PASS / CROSS_RECONSTRUCTION_MATCH / COMPLETE_V2_SINGLE_HEAD_BUNDLE / DEPENDENCY_ARCHIVE_MATCH / NO_PRE_OR_RUN_IDENTITY / NO_EXTERNAL_TRANSMISSION / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

## Outcome

The prospective OpenSSL 3 stdin repair is now preserved independently from
the temporary candidate worktree. The frozen implementation identity is:

- branch `fix/jacobian-openssl-stdin-compat-20260723`;
- commit `f72b89cd2ec574400ffe69ad7bd1540791fb73c3`;
- tree `71c45fd5999b1d3f31636bbae8bd199d166ab2f5`; and
- parent `be97bc7f76d1e9f5e501702660678d4af3081f5e`.

The main `tksCAS` object store cannot resolve this commit. The source candidate
is a clean isolated worktree backed by
`C:\Users\wakil\CAS-Harness-Run\.git`, so the complete bundle is the required
portable preservation artifact.

## Corrected manifest boundary

The earlier roadmap and tracker phrase "canonical 10-file implementation
manifest" was incorrect. Ten files changed in the OpenSSL repair, but
`REQUIRED_IMPLEMENTATION_PATHS` contains 31 trust-surface files. The producer
and ceremony enforce those 31 ordered paths.

The frozen manifest is:

- 31 files;
- 5,689 bytes; and
- SHA-256
  `cb72ea06ef560b12eeeb0ec843aa46b777d16185bc41089339439a489ca51579`.

The manifest generated from an empty independent reconstruction is
byte-identical. All 31 entries match both the LF checkout bytes and canonical
Git blob bytes with zero mismatches. The ten-file
`SOURCE_HASHES.txt` in the prospective repair handoff remains a supplementary
repair-diff receipt, not the implementation manifest.

## Complete Git bundle

- Format: v2.
- Heads: exactly one.
- Head:
  `f72b89cd2ec574400ffe69ad7bd1540791fb73c3 refs/heads/fix/jacobian-openssl-stdin-compat-20260723`.
- Prerequisites: zero.
- History: complete.
- Byte count: 36,549,194.
- SHA-256:
  `360dfc7fab45b780eec2a52b049d9bdb660bc33251fb86dcecd5bc5e8748074b`.

The bundle was fetched into a fresh repository, passed
`git fsck --full --strict --no-reflogs`, and materialized at detached HEAD with
`core.autocrlf=false`, `core.eol=lf`, an empty hooks directory, no submodules,
and a clean status.

## Dependency archive

The retained dependency archive was independently extracted and verified by
the exact reconstructed dependency verifier:

- archive byte count: 706,560;
- archive SHA-256:
  `ed16af7ae5a1ac8d61c6d3e83cf946a8cb3669c10f0f679fb2351965d5922bb8`;
- exact regular files: 15;
- dependency file-manifest SHA-256:
  `10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00`;
- `uv.lock` SHA-256:
  `deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b`;
- upstream commit:
  `581d398613e5602a5af361e1c34d3a92ea82ba8e`; and
- `.pyc` files: zero.

The retained archive is used directly. Replacing it with `git archive` remains
prohibited because earlier testing showed that Windows materialization can
change the vendored `LICENSE` bytes.

## Post-freeze regression from the portable bundle

The first complete-suite run directly from the raw bundle checkout produced
`928 passed, 4 failed, 3 skipped`. All four failures were classified before
continuing:

- one test required the ignored, externally installed
  `drand-client@1.4.2` package; and
- three tests required the retained dependency archive bytes rather than the
  Git-materialized dependency directory.

The pristine reconstruction remained clean. A separate test checkout was
created from the bundle, the already installed pinned offline client was
copied without network access, and the verified 15-file retained dependency
archive was materialized. The four exact failures then passed (`4 passed`).
The complete suite subsequently passed:

- `933 passed, 2 skipped`;
- duration: 235.38 seconds; and
- skips: the two expected Windows skips for Linux sealed-memfd execution.

This demonstrates why the complete source bundle and the exact retained
dependency archive are separate required artifacts. A source-only checkout is
not a complete execution environment.

## Tooling note

The create-once manifest command initially used `python -I -B` and stopped
before creating output because isolated mode excludes the bound user-site
NumPy 2.3.5 installation. The successful deterministic command used
`C:\Python314\python.exe -B`. This does not weaken the manifest result:

- an independent reconstruction produced identical bytes;
- every manifest record was independently checked against checkout and raw
  Git blob bytes; and
- the exact Python, NumPy, and Git identities are bound in the freeze record.

## Evidence boundary

This is implementation-preservation evidence only. It is not a PRE capture,
run identity, RFC3161 query or response, timestamp anchor, launch
configuration, model run, CUDA run, hidden-state result, semantic probe,
steering result, ablation result, prompt-injection result, cross-architecture
result, 300B result, product verdict, or `LICENSED` capability.

No Attempt 1-4 nonce, run ID, PRE, query, approval, timestamp, anchor, launch
configuration, output root, or provider identity may be reused.

## Next executable action

Prepare a fresh isolated research GPU and complete non-model prestage checks.
Only after prestage passes may the operator create a fresh Attempt 5 nonce,
run ID, controller/tool/network bindings, PRE capture, V1 protocol, mapping,
anchor payload, and RFC3161 query. Any external transmission requires a new
approval for the exact new query byte count and SHA-256.
