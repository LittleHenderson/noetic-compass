# Prospective Attempt 5 offline repair handoff

Controlling status:

`PROSPECTIVE_ATTEMPT_5_OFFLINE_REPAIR_GATE_PASS / RETAINED_ATTEMPT_4_TSR_COMPATIBILITY_PASS / NO_PRE_OR_FROZEN_ATTEMPT_5_RUN_IDENTITY / NO_ATTEMPT_5_RFC3161_QUERY / NO_EXTERNAL_TRANSMISSION / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

## Outcome

The prospective repair is committed on local branch
`fix/jacobian-openssl-stdin-compat-20260723` at commit
`f72b89cd2ec574400ffe69ad7bd1540791fb73c3`, tree
`71c45fd5999b1d3f31636bbae8bd199d166ab2f5`, with exact parent
`be97bc7f76d1e9f5e501702660678d4af3081f5e`.

On Linux/OpenSSL 3.0.13, the candidate removes only `-in -` from the two
byte-mode `openssl x509` invocations while continuing to provide the same PEM
bytes on stdin. Signature, chain, query, message-imprint, policy-OID, nonce,
responder fingerprint/serial/EKU, trust-root, executable, seccomp, and
fail-closed checks remain present.

The repair also closes the failure-evidence gaps found during independent
review:

- producer, ceremony, and independent receiver all bind post-run capture
  schema `v2`;
- command failures retain an allow-listed code, canonical `argv_sha256`,
  return-code semantics, bounded `stderr_sha256`, byte count, retention
  truncation, and capture-completeness state without publishing raw argv or
  stderr;
- stdout and stderr are drained concurrently and independently capped at
  4 MiB; timeout or overflow kills and reaps the process before receipt
  construction;
- launch, timeout, nonzero-exit, and output-bound failures remain distinct and
  fail closed;
- bootstrap hard pins match the exact committed first-party source bytes.

## Verification

- Narrow failure/streaming checks: `7 passed, 2 skipped, 80 deselected`.
- Focused receipt/runner/ceremony/receiver checks: `184 passed, 2 skipped`.
- Complete worker suite with the documented Python 3.14 environment:
  `933 passed, 2 skipped in 186.99s`.
- The two Windows-skipped sealed-memfd tests were run directly under WSL with
  Python 3.12.3 and OpenSSL 3.0.13 and passed:
  `ATTEMPT5_OPENSSL3_LINUX_BOUNDED_STREAM_REGRESSIONS_PASS`.
- The immutable Attempt 4 payload/query/TSR passed the complete candidate
  bounded-stream verification path offline:
  `ATTEMPT5_RETAINED_TSR_OPENSSL3_BOUNDED_STREAM_COMPATIBILITY_PASS`.
- Two independent code/security reviews returned `GO` after the bounded
  streaming and completeness fixes.
- The committed diff passes `git diff --check`; only Windows autocrlf notices
  were printed while the files were unstaged.
- The isolated worktree is clean after commit. Generated Python/pytest caches
  were removed. The only ignored test content is the exact pinned
  `drand-client` fixture under `node_modules`.

## Retained Attempt 4 evidence used offline

- Payload SHA-256:
  `49235313dad9541ec029d78b8a6ab9d1de90f5117cde9fb64ad6e2ec778a139b`
- Exact 104-byte query SHA-256:
  `fa887272d01f436d37569f6d13b719f5392539dda897da870606c8845be11829`
- Exact 6,033-byte response SHA-256:
  `08c2a34b3ea398bb1d64c9dd6fb6ae580becd9ba713d36652bae2a54f4e3f4f9`
- Anchor receipt SHA-256:
  `577c9bb94b87e395444c2f9a1c65a500a4aae85878970db8deddf6e37387bc65`
- Nonce:
  `29044c20e70a805d3112d6c6bc1f789dda29ee27bcfb1cf248032271ef6d092e`
- Verified policy: `2.16.840.1.114412.7.1`
- Verified responder serial: `0A80EF184B8DF10582D1C476A7957468`
- Verified responder EKU: `CRITICAL_TIME_STAMPING_ONLY`
- Verified root fingerprint SHA-256:
  `552f7bdcf1a7af9e6ce672017f4f12abf77240c78e761ac203d1d9d20ac89988`

Attempt 4 remains consumed and immutable. Its query, nonce, run ID, anchor,
launch identity, and remote root were evidence inputs only. They were not
retransmitted, regenerated as Attempt 5, or executed again.

## Honesty and licensing boundary

No Attempt 5 PRE, model manifest, implementation manifest, Git bundle,
protocol, nonce, run ID, RFC3161 query, RFC3161 response, anchor, launch
configuration, provider execution, model load, CUDA operation, steering,
ablation, or prompt-injection experiment occurred. No network request was made
to DigiCert or RunPod during this offline repair phase.

This evidence does not create `ACCEPT`, a technical-canary pass, a scientific
conclusion, or any capability license. `verdict` remains `NONE`,
`claim_status` remains `NOT_LICENSED`, and `scientific_conclusion` remains
`NO_SCIENTIFIC_CONCLUSION`.

The following remain `OPEN / NOT_LICENSED`: `300B_EXECUTION`, `CAS_OHM`,
`CJT`, `CROSS_ARCHITECTURE_UNIVERSALITY`,
`JSPACE_SEMANTIC_CORRESPONDENCE`, `OUTPUT_CONTROL`,
`PROMPT_INJECTION_DETECTION`, `RPM`, and `SEMANTIC_PROBING`.

## Next executable gate

From this clean commit, independently construct and reconstruct a new
implementation manifest and complete Git bundle in a new empty Attempt 5
root. Then create fresh PRE evidence, protocol, nonce, run ID, RFC3161 query,
anchor, and launch configuration. Attempt 4 bytes and identities may not be
reused. Any future query requires its own exact byte-specific approval before
external transmission.

The later technical execution gate still requires phase-two TSYNC and
post-guard CUDA proof, 213 artifacts, 1,248 autograd calls,
`IMMUTABLE_ENVIRONMENT_MATCH`, and an independent receiver result. This
offline repair does not change the whole-project score of approximately
`0.33 / 1.00`.
