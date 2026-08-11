# Attempt 4 remote preparation

Controlling status:

`PERSISTENT_ATTEMPT_4_PRESTAGE_VERIFIED / LINUX_BYTECODE_GUARD_PASS / NO_PRE_OR_FROZEN_RUN_IDENTITY / NO_RFC3161_QUERY / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

## Outcome

The corrected Attempt 4 implementation was transferred to the already-running
research pod and reconstructed without executing the canary. The exact
36,536,084-byte Git bundle SHA-256 is
`3ddf60a6f24c204489a70c62465efed3ccd421baa7739bffa923d26821512b67`.
The clean reconstructed repository is
`/workspace/cas-jlcv1-repo-be97bc7f` at commit
`be97bc7f76d1e9f5e501702660678d4af3081f5e`, tree
`4eb382528e8a4cee81a1c043f65bf0dcfa369ccf`.

The remote 31-file implementation manifest reconstruction was byte-identical
to the transferred manifest: 5,689 bytes, SHA-256
`bbaaa973372cd95c3c99472a31664ab2add699cf1d844a5b2ab28a763dd04ffb`.

The fresh exact dependency root is
`/workspace/cas-jlcv1-dependency-bundle-be97bc7f`. It verifies as exactly 15
files with file-manifest SHA-256
`10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00`
and lock SHA-256
`deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b`.

## Fail-closed preparation finding

An initial dependency reconstruction with `git archive` was rejected because
Git normalized the vendored `LICENSE` from 11,560 bytes to 11,358 bytes. Its
SHA-256 became
`cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`
instead of the required
`3ddf9be5c28fe27dad143a5dc76eea25222ad1dd68934a047064e56ed2fa40c5`.
The rejected tree is preserved at
`/workspace/cas-jlcv1-dependency-bundle-rejected-git-archive-line-endings-be97bc7f`.
The verifier was not weakened. The fresh Attempt 4 root was copied
byte-for-byte from the unchanged, already verified Attempt 3 15-file root;
`diff -qr` confirmed byte identity and the Attempt 3 source root was not
modified.

## Linux bytecode-guard evidence

- The real Linux seccomp wrapper under `-I` without `-B` returned `2` with
  `FAILED_CLOSED: Python bytecode writes must be disabled (-B).`
- The real Linux bootstrap under `-I` without `-B` returned `2` with
  `FAILED_CLOSED: relaunch with Python bytecode writes disabled (-B).`
- A disposable ordinary-`-I` import of the actual vendored `jlens` package
  created exactly seven `.pyc` files and was rejected with
  `dependency bundle file set differs`.
- The positive `-I -B` import loaded actual `jlens`, `jlens.fitting`, and
  `jlens.hf` source from the fresh Attempt 4 dependency root while using an
  in-memory Torch stub. No real Torch, CUDA, GPU, or model API was loaded.
- After that import, the official dependency root still verified as exactly 15
  files with zero `.pyc` files.

## Boundary

No Attempt 4 PRE capture, nonce, run ID, protocol, launch mapping, anchor
payload, RFC3161 query, timestamp request, timestamp response, launch config,
model load, CUDA call, GPU execution, producer receipt, POST capture, or
scientific result was created. Attempt 3 output, POST, and runlog directories
remain at zero files. Production pod `hilj2rzs54gi06` was not used or changed.

Next executable action is a separate fresh Attempt 4 identity-and-PRE ceremony.
It must remain stopped before any RFC3161 transmission until the exact new
query byte count and SHA-256 receive explicit approval.
