# Attempt 4 finalized outcome

Controlling status:

`OFFICIAL_SHADOW_ATTEMPT_FAILED_CLOSED_AT_PRE_CUDA_PREFLIGHT / EVIDENCE_CHAIN_INDEPENDENTLY_VERIFIED / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

Attempt 4 is consumed and immutable. Do not retransmit its RFC3161 query,
reuse its nonce or run ID, or rerun its launch identity.

## What completed

- Commit: `be97bc7f76d1e9f5e501702660678d4af3081f5e`
- Tree: `4eb382528e8a4cee81a1c043f65bf0dcfa369ccf`
- Run ID: `jlcv1-rfc3161-4108653e11369d812517e7f5d3ab44c10aa860df3131ac2f8636a14db654c0fc`
- Exact 104-byte query SHA-256: `fa887272d01f436d37569f6d13b719f5392539dda897da870606c8845be11829`
- DigiCert response: 6,033 bytes, SHA-256 `08c2a34b3ea398bb1d64c9dd6fb6ae580becd9ba713d36652bae2a54f4e3f4f9`
- Verified timestamp: `2026-07-23T00:40:00Z`
- Anchor receipt SHA-256: `577c9bb94b87e395444c2f9a1c65a500a4aae85878970db8deddf6e37387bc65`
- Launch configuration SHA-256: `a8c9f45bcbfca9b2460dd6b3b04a253e441b9375e56e64b5fc3b0bad1eeb2445`
- Wrapper invocation count: exactly 1
- Wrapper exit code: `0`
- POST finalizer: `READY_FOR_INDEPENDENT_RECEIVER`

## Producer outcome

The producer receipt is 7,239 bytes with SHA-256
`c57005f90fadabaf9de84edb852f33e0c492599379e8d62755264cc0ab8fe732`.
Its status is `FAILED_CLOSED` at `PRE_CUDA_PREFLIGHT`, with gates:

- `PRE_CUDA_BINDINGS_UNVERIFIED`
- `PRE_CUDA_PREFLIGHT_FAILURE`

It retained zero artifacts, selected zero model blocks, and observed zero of
the registered 1,248 autograd calls. Phase-one seccomp ran, but Torch, CUDA,
model loading, hidden-state probing, steering, ablation, and prompt-injection
experiments did not begin. This is no scientific model result.

## Independent outcome

The off-pod receiver receipt is stored at
`RECOVERY_2026-07-23/receiver/jacobian_lens_canary_v1_independent_receiver_receipt.json`.
It is 6,662 bytes with SHA-256
`4183b510919b5f02232e6534a1c64cc8d51e6a31a99182199aa03934418d2c22`.
Its controlling status is
`FAILED_CLOSED_EVIDENCE_CHAIN_VERIFIED_NO_SCIENTIFIC_CONCLUSION`.
It independently verified the anchor, exact retained bytes, publication
chain, PRE/POST evidence, implementation, dependency, source, token,
model-manifest, and provider bindings. It preserves `NOT_LICENSED`, `NONE`,
and `NO_SCIENTIFIC_CONCLUSION` for all intended scientific/product claims.

The recovered archive is
`RECOVERY_2026-07-23/attempt4_complete_evidence.tar`, 708,382,720 bytes,
SHA-256
`6066694e00c519a1042cba952c866443532058d6caa4e699f98e85a75e266964`.
Local materialization matched all 2,762 regular files, 330 directories, and
11 archived symbolic links with zero mismatches.

## Root cause and next action

The retained failure-detail hash exactly identifies the outer error as
`PRE_CUDA_PREFLIGHT:CanaryLaunchError:RFC3161 cryptographic verification failed closed`.
The high-confidence reproduced inner defect is the runner's use of
`openssl x509 -in - ...` for PEM bytes on stdin. OpenSSL 3.0 treats `-` as a
filename; removing only `-in -` makes the same root/responder/EKU pin check
pass. The independent receiver already uses the compatible form.

Prospective Attempt 5 must fix both byte-mode `x509` calls without weakening
any cryptographic or seccomp guard, correct the mocked test, add a real Linux
OpenSSL 3.0 regression, retain bounded failure codes/stderr hashes, and then
create a completely new commit, manifest, bundle, protocol, nonce, run ID,
query, anchor, and launch configuration.

Research pod `zp2s9pscgncn0b` was stopped after recovery; RunPod showed
`Not running`. Production pod `hilj2rzs54gi06` was not changed.
