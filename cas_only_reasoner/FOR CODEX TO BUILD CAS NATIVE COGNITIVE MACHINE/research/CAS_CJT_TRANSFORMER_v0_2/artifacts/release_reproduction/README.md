# CASformer v0.2 clean release reproduction

Status: `CASFORMER_V0_2_RELEASE_REPRODUCED`

This evidence bundle binds the clean local reproduction to source-freeze commit `dec08c81644f1c47b4b94c29a406a9432df7c7bd`.

The release was built in a clean detached worktree. Its v0.1 and v0.2 wheels were installed into a new Python 3.14 virtual environment. Isolated imports resolved from that environment. The installed v0.2 demo ran from the wheel's installed data directory.

The following checks passed:

- 250 v0.2 tests.
- 5 v0.2 source-manifest tests.
- 89 frozen v0.1 tests.
- 181 CNCM regression tests and 403 subtests.
- The installed complete reasoning-transistor demo.
- All 6 stored traces against the published v0.2 schema.
- The seven required blocker-closure checks.
- Dependency compatibility after hash-locked installation.

The test suites use the source-freeze test files. Some frozen tests intentionally start child processes with pinned source paths. The isolated import check, installed demo, separate trace validator, and external compute-plan probe establish installed-wheel execution. Do not describe every test subprocess as wheel-only.

`CAS_CJT_TRANSFORMER_V0_2_CODE_AUDIT_PARTIAL.txt` is the owner-supplied assessment of GLM's reported execution audit. It states that its author did not personally execute the package. It is retained byte-for-byte and classified as `CAS_CJT_TRANSFORMER_V0_2_CODE_AUDIT_PARTIAL`; it is not presented as a new independent audit.

The pre-freeze local receipt is preserved for history. It is not the release receipt because it was bound to an untracked source tree and an earlier ambient Git commit.

Hashes in `PAYLOAD_SHA256SUMS.txt`, the Git evidence commit, and `VALIDATION_RECEIPT.json` bind the evidence. They are tamper evidence, not a signature, WORM anchor, third-party certification, or production attestation.

`commands/reproduce.ps1` is a fail-closed rerun recipe. It streams a fresh transcript and leaves its unique scratch directory in place for inspection. It does not rewrite this frozen evidence bundle. The original executed commands, outputs, and artifact hashes remain in `commands/COMMANDS.json`, `raw`, and `dist/ARTIFACTS.json`. A later rebuild can have different archive bytes because Python archives include build-time metadata; the script therefore prints fresh hashes and enforces the embedded 50-file source manifest rather than claiming byte-for-byte reproducible archives.

No result here establishes language capability, general reasoning capability, CAS-specific advantage, completion of the CNCM brain, AGI, or production readiness.
