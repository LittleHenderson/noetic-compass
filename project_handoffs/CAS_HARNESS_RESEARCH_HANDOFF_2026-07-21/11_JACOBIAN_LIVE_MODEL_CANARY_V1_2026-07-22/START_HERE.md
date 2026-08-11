# Jacobian live-model canary V1 checkpoint

Captured: 2026-07-22 PDT/UTC

## Current corrected Attempt 4 routing

Controlling status:

`PRE_ANCHOR_FROZEN / WAITING_FOR_EXPLICIT_EXTERNAL_DISCLOSURE_APPROVAL / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

Attempt 3 later obtained a verified RFC3161 timestamp and was superseded
before wrapper/model/CUDA execution because the isolated child interpreter
lacked interpreter-level `-B` bytecode suppression. The controlling corrected
run is Attempt 4 at commit
`be97bc7f76d1e9f5e501702660678d4af3081f5e`, tree
`4eb382528e8a4cee81a1c043f65bf0dcfa369ccf`. Its fresh PRE, protocol, target
mapping, anchor payload, and exact 104-byte RFC3161 query are frozen. The query
SHA-256 is
`fa887272d01f436d37569f6d13b719f5392539dda897da870606c8845be11829`;
it is **UNSENT** and requires exact, byte-specific, single-use approval.

Continue only through
`04_PROTOCOL_AND_ANCHOR/ATTEMPT_04_CORRECTED_BYTECODE_GUARD_BE97BC7F/STATUS.md`.
Do not execute or replay the Attempt 2 or Attempt 3 instructions below.

## Historical final Attempt 2 result

Controlling status:

`RFC3161_ANCHOR_VERIFIED / OFFICIAL_SHADOW_ATTEMPT_FAILED_CLOSED_AT_PRE_CUDA_PREFLIGHT / NO_MODEL_OR_CUDA_EXECUTION / FAILED_CLOSED_EVIDENCE_CHAIN_VERIFIED_NO_SCIENTIFIC_CONCLUSION / SHADOW / NONE / NOT_LICENSED`

The exact 105-byte query was sent once after explicit approval. DigiCert's
6,035-byte response was independently verified against the nonce, payload
imprint, policy, signature chain, responder certificate, and pinned root. The
timestamp is `Jul 22 18:57:15 2026 GMT`; anchor-receipt SHA-256 is
`2b9daefdf02b03c6e071cc850f452c706844cddf99bac03dd47f6e9ab17bd63c`.

The official shadow run then failed closed in phase-one seccomp at
`PRE_CUDA_PREFLIGHT`. The exact failure was
`CanaryContractError: dependency bundle contains a linked directory` because
the remote mapping used `/root/cas-jlcv1-env` for both the clean 15-file
dependency source bundle and the live `.venv`. The verifier correctly rejected
the virtual environment's linked directories. CUDA was not initialized; model
and execution-token materialization were never authorized; retained counts are
zero model blocks, zero artifacts, and `0/1,248` autograd calls.

PRE/POST comparison is `IMMUTABLE_ENVIRONMENT_MATCH`. The standalone receiver
verified the complete negative chain and issued
`FAILED_CLOSED_EVIDENCE_CHAIN_VERIFIED_NO_SCIENTIFIC_CONCLUSION`; its receipt
SHA-256 is
`c0cef95574997d707e1fd30ad3286338182f7aa1f76bde81afab8a82659a28d1`.
The research A40 was stopped after evidence transfer and verification. The
production pod was untouched.

At that historical checkpoint, the planned Attempt 3 would have needed to keep
the clean dependency source bundle separate from the runtime virtual
environment, use a fresh empty workspace/output, and freeze a fresh PRE
capture, nonce, run ID, protocol, launch mapping, query/response, and anchor.
That route is superseded by Attempt 4. Attempt 2 remains unchanged as negative
evidence. The joined steering and `CJT_JSPACE_OHM_JOINED_CANARY_V0` experiment
remains downstream of an independently verified Jacobian technical pass.

The historical Attempt 3 checklist is retained in
`05_ATTEMPT_03_PREPARATION.md` and must not be executed or replayed. Current
operators must use the corrected Attempt 4 `STATUS.md` named at the top of this
file. Attempt 2's rejected local mapping pair and malformed wrapper-exit
transcript are explained without changing the evidence in
`04_PROTOCOL_AND_ANCHOR/ATTEMPT_02_OPERATOR_NOTES.md`.

## Historical superseded Attempt 3 persistent pre-stage

Status:

`PERSISTENT_PRESTAGE_VERIFIED / RESEARCH_POD_STOPPED / ATTEMPT_3_IDENTITY_NOT_FROZEN / NO_EXTERNAL_QUERY / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

The research pod was briefly restarted to correct the deployment layout on its
persistent volume. The unchanged frozen verifier now accepts
`/workspace/cas-jlcv1-dependency-bundle-a8969eb7` with exactly 15 regular
files, no links or extras, file-manifest SHA-256
`10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00`,
and lock SHA-256
`deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b`.
The runtime environment is separate at
`/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv`.

The exact code commit/tree, implementation bundle/manifest, five-file regular
Pythia snapshot, and frozen model/source/token publications also rehashed
correctly. No fresh provider-bound PRE, network plan, nonce, run ID, protocol,
anchor, query, CUDA initialization, or model run was created. The pod was
stopped again after preparation; the production pod remained untouched.

This pre-stage is preserved as history. Its old continuation route is
superseded by the corrected Attempt 4 `STATUS.md` named above. Do not reuse its
nonce, run ID, PRE, protocol, query, approval, timestamp, or execution
checklist.
The unanchored pre-stage operator record is
`05_ATTEMPT_03_PRESTAGE_OPERATOR_RECORD.json`, SHA-256
`15ae9676a0abdea93b006dd4712a860cf01a018f41f341d3777796f5847b9604`.

## Superseded Attempt 2 pre-anchor checkpoint (historical)

Attempt 1 obtained and independently verified a genuine DigiCert RFC3161
timestamp, then failed closed before model execution because Git-for-Windows
OpenSSL treated `OPENSSL_CONF=nul` as a literal file. That attempt is retained
as `NO_MODEL_EXECUTION / SHADOW / NONE / NOT_LICENSED`.

The repaired final identity is commit
`a8969eb71c6d3e5c43d7ee2b7c7d4aa90dd70fc0`, tree
`cce2d477bb0f423ee6a2669ee680eaac7b999322`, manifest SHA-256
`5561105d014d0bd3a943fc9d498ebc6f657b2e1024018ff95af06f244a9974fa`,
and bundle SHA-256
`0db2c2f6deb3bf797af2b9a42b84714236f66cce48e6c74b769ccbb63c101fff`.
The final complete regression passed `920` tests with one Linux-only test
skipped on Windows. Independent local and RunPod reconstruction verified all
31 manifest files.

Attempt 2 has a fresh controller capture, two-phase network plan, 16,811-file
PRE capture, and canonical protocol. Its prepared 105-byte RFC3161 query has
SHA-256
`2cdd55bcc9af08ffe478b5a0e5f6a0e68172ccbf70588d4a6d8c1cbcada542f4`.
At this superseded checkpoint it had not been sent and required fresh explicit
approval because it differed from the previously approved 104-byte query.

Historical checkpoint status (superseded):

`PRE_ANCHOR_FROZEN / WAITING_FOR_EXPLICIT_EXTERNAL_DISCLOSURE_APPROVAL / NO_MODEL_EXECUTION / SHADOW / NONE / NOT_LICENSED`

This technical canary still does not test prompt-injection detection, output
steering, the joined CJT/J-Space/RPM/CAS-Ohm design, universality, or 300B.
Those remain subsequent frozen gates, not abandoned goals.

## Superseded controlling answer (historical)

The new design has reached a real-model **technical-preparation** checkpoint,
not a combined product result. Exact Pythia-160M model bytes, exact WikiText
source bytes, and a deterministic 1,000-block token manifest now exist and
reopen through fail-closed consumers. A nonofficial local CPU diagnostic also
confirmed that the exact Pythia graph supports connected hidden-state
intervention, JVP, VJP, and downstream-logit differentiation.

No V1 GPU execution, independent technical pass, joined CJT/J-Space/RPM/
CAS-Ohm experiment, prompt-injection result, output-control result, universal
open-weight result, or 300B result exists at this checkpoint.

Controlling status:

`EXACT_INPUTS_FROZEN / DIFFERENTIABILITY_DIAGNOSTIC_OBSERVED / V1_GPU_CANARY_NOT_RUN / SHADOW / NOT_LICENSED`

This is a time-indexed evidence boundary, not a ceiling on the project.

## What is complete

- Exact public provider metadata was retrieved without credentials at
  `2026-07-22T09:16:47.246119Z` for the controlling v2 attestation. The
  earlier capture is retained only as superseded history.
- The local source manifest binds six WikiText-103-raw-v1 files and the exact
  five-file Pythia snapshot.
- A verified acquisition attestation reopens both the source manifest and the
  complete provider metadata receipt.
- The exact-token freezer read only the pinned local Parquet/tokenizer bytes
  with network access disabled.
- The resulting manifest contains 1,000 ordered 128-token blocks; the canary
  uses ranks 0 through 7.
- The implementation foundation includes deterministic runtime checks,
  real-autograd call accounting, canonical raw artifacts, producer receipts,
  and a separate receiver that cannot confer a product license.

## Historical superseded checklist (do not execute)

The separate 15-file source bundle and other reusable inputs are already
verified on persistent `/workspace`; that is pre-stage preparation, not an
official run.

1. Restart only the research pod and recheck the exact
   `24_000_000_000`-byte capacity gate plus every persistent hash.
2. Rerun the frozen dependency verifier against the separate 15-file root and
   confirm the clean `jlens` import boundary.
3. Capture fresh provider/host/tool/network bindings and fresh PRE evidence in
   a new empty Attempt 3 workspace/output.
4. Freeze a fresh nonce, run ID, protocol, launch mapping, RFC3161 query,
   response, and anchor. Never reuse Attempt 2's identity or anchor; present
   the new query's exact byte count and SHA-256 for separate approval before
   sending it.
5. Execute once on an isolated research GPU that satisfies the exact
   `24_000_000_000`-byte gate, retain
   all success or failure evidence, capture POST, and run the independent
   receiver. A technical pass requires the complete 213-artifact and 1,248-call
   contract.

RunPod was used for Attempt 2, but the execution stopped in phase-one pre-CUDA
preflight; CUDA and Pythia were never initialized or loaded. The A40 research
pod is stopped and shows only its idle volume charge. The production pod was
not used or changed.

## Exact frozen input identities

- source manifest SHA-256:
  `624f9c31208343ca9ea514d1abbd1c8d7a7af953ecd71337ce07e8390189886b`
- verified source marker SHA-256:
  `8e214cc1c8a6869a7fc8b6707693d2f26b80110d20ee979dc13f45f20f641cce`
- provider receipt SHA-256:
  `8a16fab2fd7b1a268a42759cbde5c0162571e4a4166ac975fe69bbf8a96e39ca`
- source attestation SHA-256:
  `6a133cae284710669f5a46acb9a990c0c200f64a9213a0a2271555001c031755`
- Pythia model manifest SHA-256:
  `e78edf3255f59a69c03659585da04e6a6ca624c707b1567556180873fd54be17`
- exact token manifest SHA-256:
  `9cf4549abfaf6b8e44bce8a2578428d27b45f3e207a32f0472b2f53adeb54b28`
- exact token publication marker SHA-256:
  `a953a9f3180391f21bfbb4763c47cba8d9df5669e7b3637a650823c4217d1c5f`
- token Merkle root SHA-256:
  `3c2af26f72738de116aae2cd3d106346eaef9e5a2e41dc71b1ca7485dc1c031f`

See `01_FROZEN_INPUTS/INPUT_PUBLICATION_RECEIPT.md` for every retained file.
