# Attempt 6 implementation freeze

Controlling status:

`IMPLEMENTATION_FREEZE_PASS / CROSS_RECONSTRUCTION_MATCH / COMPLETE_V2_SINGLE_HEAD_BUNDLE / DEPENDENCY_ARCHIVE_UNCHANGED / NO_PRE_OR_RUN_IDENTITY / NO_EXTERNAL_TRANSMISSION / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

## Outcome

The prospective CRLF/bare-CR normalization repair for human-readable OpenSSL
output is preserved independently from the temporary candidate worktree. The
frozen implementation identity is:

- branch `fix/jacobian-openssl-crlf-compat-20260723`;
- commit `29551624f4de0eec61c4035e364203be55d6c08a`;
- tree `0d70f8e8e8d9dfd9f36ed88ade731ab466935be6`; and
- parent `f72b89cd2ec574400ffe69ad7bd1540791fb73c3` (the Attempt 5
  implementation-freeze commit).

The candidate worktree `C:\tmp\cas-jlcv1-attempt6-crlf-repair` is a clean
isolated clone of the Attempt 5 implementation bundle, so the complete bundle
in this directory is the required portable preservation artifact.

## What the repair changes

One normalization contract now governs every byte-mode decode of
human-readable OpenSSL stdout across the runner
(`_decode_bound_openssl_text`), the RFC3161 helper (`stdout_text` via
`_normalize_openssl_human_text`), and the independent receiver
(`_normalized_openssl_text`): exactly one CRLF-to-LF pass at the decode
boundary; any surviving carriage return (bare CR, or the residue of a
double-translated CRCRLF) or NUL fails closed. Downstream parsers keep their
strict no-CR gates as defense in depth. Binary outputs (DER, `-token_out`,
PEM blocks) are never normalized. Text-mode subprocess paths (`text=True`)
already receive Python universal-newline translation and are unchanged.

Audit findings repaired:

- The receiver decoded `ts -query -text` and `ts -reply -text` byte-mode
  stdout with no normalization and fed it to parsers that reject any CR, so a
  CRLF-emitting Windows OpenSSL build would fail closed after the one-shot
  TSA query is spent.
- The helper byte path fed `_parse_rfc3161_cms_signer_serial` unnormalized
  text whose CRLF silently produces zero `signerInfos` matches, yielding a
  misleading failure instead of a normalization failure.
- The Attempt 5 byte-mode migration normalized only the receiver CMS parser
  (`_cms_single_signer_serial`), leaving every other human-readable boundary
  inconsistent with it.

Empirical grounding, measured on this workstation on 2026-07-23:

- the exact pinned receiver OpenSSL 3.5.4 (`C:\Program Files\Git\usr\bin\
  openssl.exe`, SHA-256 `2c6f2c64612cf45349f15850e4647b2fe594c2759de63a695ec4
  cbe13b2404da`) currently emits LF-only text output, so this repair is
  prospective hardening for the exact pinned configuration; and
- the sibling native build in the same Git for Windows installation
  (`C:\Program Files\Git\mingw64\bin\openssl.exe`, same reported version
  string, SHA-256 `060b787efc1e058068bfe4ff1c162fc40173df33fff8ceac6543d1ebaf
  340424`) emits CRLF (`Version: 1\r\n...`), which reproduces the failure
  class one directory away from the pinned binary.

Correction (same day, after this STATUS was first written): the retained
Attempt 5 post-anchor failure record
(`../ATTEMPT_05_PRE_ANCHOR_DD55BC73/ATTEMPT_05_POST_ANCHOR_VERIFIER_FAILURE_RECORD.json`)
shows this failure class was not merely adjacent — the Attempt 5 anchor
ceremony itself had pinned the CRLF-emitting `mingw64` binary in its tool
binding, and after the owner-approved one-shot DigiCert transmission it
failed closed with `RFC3161 query text contains invalid controls`
(query-text `cr_count` 9). The 6,033-byte signed response (SHA-256
`2ea41173...`) is retained; no anchor receipt was created; Attempt 5 must
never resume. This repair therefore repairs a real consumed-attempt
failure, not only a prospective hazard.

The bootstrap hard-pin table in `scripts/run_jacobian_lens_canary_v1.py` was
updated for the three changed trust-surface files.

## Implementation manifest

- 31 files;
- 5,689 bytes;
- SHA-256
  `abaee8b11af0c8d57969bfab19a28914e074dc9ae5eb6c1536a141edee53385d`.

The manifest generated from an independent reconstruction (fresh clone of the
bundle) is byte-identical. All 31 entries match canonical Git blob bytes in
both the candidate worktree repository and the reconstruction with zero
mismatches.

## Complete Git bundle

- Format: v2.
- Heads: exactly one.
- Head:
  `29551624f4de0eec61c4035e364203be55d6c08a refs/heads/fix/jacobian-openssl-crlf-compat-20260723`.
- Prerequisites: zero.
- History: complete.
- Byte count: 36,557,255.
- SHA-256:
  `821dbc2dfad076dd8261768963f63d4cadd7726d2f6b635574ef0401f315088d`.

The bundle was cloned into a fresh repository with `core.autocrlf=false` and
`core.eol=lf`, passed `git fsck --full --strict --no-reflogs`, and
materialized at detached HEAD with a clean status.

## Dependency archive

This repair changes no dependency files. The retained 15-file dependency
archive from Attempt 3 remote recovery was re-verified unchanged:

- archive SHA-256
  `ed16af7ae5a1ac8d61c6d3e83cf946a8cb3669c10f0f679fb2351965d5922bb8`.

## Verification

- New CRLF regression tests: 5 (helper normalizer + parsers, receiver
  normalizer + parsers, runner decode boundary), all passing.
- Focused trust-path files (`test_cjt_ohm_statistical_cli`,
  `test_verify_jacobian_lens_canary_v1_independent`,
  `test_jacobian_lens_canary_runner`, `test_jacobian_lens_rfc3161`,
  `test_jacobian_lens_operator_ceremony`,
  `test_prepare_cjt_ohm_statistical_ceremony`): `225 passed, 2 skipped`.
- Complete `live-trace-worker` suite in the candidate worktree:
  `938 passed, 2 skipped` (Attempt 5 baseline `933 passed, 2 skipped` plus
  the 5 new regression tests; the 2 skips are the expected Windows skips for
  Linux sealed-memfd execution). The git-ignored `drand-client@1.4.2`
  offline fixture was materialized from the retained local copy first; before
  materialization the suite showed only that single pre-documented
  environmental failure.
- The two Linux-only sealed-memfd real-OpenSSL tests plus the new runner
  decode regression passed under WSL Ubuntu Python 3.12.3 / OpenSSL 3.0.13
  (`3 passed`), matching the Attempt 5 verification environment.
- Complete suite from the bundle reconstruction checkout: the first run
  before materializing the retained dependency archive produced
  `935 passed, 3 failed, 2 skipped`; all three failures were the
  pre-documented dependency-inventory tests that require the exact retained
  archive bytes rather than Git-materialized bytes (the pinned
  `uv.lock`/vendored hashes bind the upstream CRLF bytes while Git blobs are
  LF-normalized — the same materialization hazard this whole repair
  addresses). After materializing the verified retained archive
  (`ed16af7a...`), the three exact tests passed (`3 passed`) and the final
  complete suite from the reconstruction passed
  `938 passed, 2 skipped` in 171.12 seconds — identical to the candidate
  worktree result.
- Retained Attempt 4 RFC3161 replay: the immutable DigiCert-signed
  query/response pair (query `fa887272...`, response `08c2a34b...`) replayed
  PASS through the repaired receiver `verify_rfc3161` path with the exact
  pinned Windows OpenSSL 3.5.4, reverifying signature/chain/queryfile,
  nonce, imprint, policy OID, responder serial and EKU pins, and the pinned
  DigiCert root, with timestamp `Jul 23 00:40:00 2026 GMT` matching the
  tracker record.

## Evidence boundary

This is implementation-preservation evidence only. It is not a PRE capture,
run identity, RFC3161 query or response, timestamp anchor, launch
configuration, model run, CUDA run, hidden-state result, semantic probe,
steering result, ablation result, prompt-injection result,
cross-architecture result, 300B result, product verdict, or `LICENSED`
capability. No TSA was contacted and no model or CUDA execution occurred
during this freeze.

The frozen Attempt 5 pre-anchor identity (run
`jlcv1-rfc3161-dd55bc73...`, commit `f72b89cd`) binds the pre-repair
implementation. Its one-shot was consumed: the 104-byte query was
transmitted to DigiCert exactly once, the signed response is retained, and
the ceremony failed closed at the pinned CRLF-emitting verifier with no
anchor receipt created. Attempt 5 must never resume, and a run at the
repaired implementation requires a fresh Attempt 6 identity. No Attempt 1-5
nonce, run ID, PRE, query, approval, timestamp, anchor, launch
configuration, output root, or provider identity may be reused.

## Next executable action

Prepare a fresh isolated research GPU root for Attempt 6 at commit
`29551624f4de0eec61c4035e364203be55d6c08a` and complete non-model prestage
checks. Only after prestage passes may the operator create a fresh Attempt 6
nonce, run ID, controller/tool/network bindings, PRE capture, V1 protocol,
mapping, anchor payload, and RFC3161 query. Any external transmission
requires a new owner approval for the exact new query byte count and SHA-256.
