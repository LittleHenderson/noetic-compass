# Attempt 6 remote prestage

Captured at UTC: `2026-07-23` (see transcript).

Controlling status:

`REMOTE_PRESTAGE_PASS / IMPLEMENTATION_RECONSTRUCTION_MATCH / DEPENDENCY_MATCH / MODEL_AND_PUBLICATION_INPUTS_REHASHED / OPENSSL3_STDIN_PASS / CRLF_NORMALIZATION_CONTRACT_PASS_ON_POD / CAPACITY_GATE_PASS / NO_PRE_OR_RUN_IDENTITY / NO_RFC3161_QUERY / NO_EXTERNAL_TSA_TRANSMISSION / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

## Endpoint binding

Pod `zp2s9pscgncn0b` (research, NVIDIA A40, `$0.44/hr`) was observed RUNNING
via the authenticated RunPod REST API (`rest.runpod.io/v1/pods`, local
`~/.runpod/config.toml` key; the legacy GraphQL endpoint returned 403 for
this key). Endpoint `69.30.85.51:22111`; the scanned ed25519 host key
fingerprint `SHA256:V6BZrhQOBzY1vPKdVGF1XNWGWst6jwQWSD19YwM5xSw` exactly
matches the retained Attempt 5 live-continuity pin, and all connections
used an isolated known-hosts file with `StrictHostKeyChecking=yes`. This is
an authenticated provider API observation plus retained-pin continuity, not
an independent third-party host-key attestation. Production pod
`hilj2rzs54gi06` was observed RUNNING and was not targeted or changed.

## What passed (full transcript retained)

- Host identity: hostname `13e938fc50e8`; boot-id and machine-id SHA-256
  equal the frozen Attempt 5 values (same boot); GPU
  `GPU-b7638993-cc34-ac95-7fc8-5002ce894e00`, driver `580.126.09`,
  48,305,799,168 bytes >= the 24,000,000,000-byte gate.
- Tool identities: `/usr/bin/git` 2.34.1, `/usr/bin/openssl` 3.0.2,
  `/usr/bin/python3.11` 3.11.10 — executable SHA-256s identical to the
  Attempt 5 prestage observations.
- Uploads verified byte-exact: Attempt 6 bundle (36,557,255 bytes,
  `821dbc2d...`), implementation manifest (5,689 bytes, `abaee8b1...`),
  dependency archive (706,560 bytes, `ed16af7a...`), and the 8 frozen input
  publication files (model/source/token manifests, markers, provider
  metadata, attestation) — all matching their frozen hashes.
- Bundle verified (v2, one head, complete history), cloned with
  `core.autocrlf=false`/`core.eol=lf`, `git fsck --full --strict` clean,
  detached at commit `29551624f4de0eec61c4035e364203be55d6c08a`, tree
  `0d70f8e8...`, parent `f72b89cd...`, clean status.
- Remote implementation manifest reconstruction: byte-identical
  (5,689 bytes, `abaee8b1...`) — the third independent reconstruction
  (Windows candidate, Windows bundle-recon, Linux pod).
- Dependency bundle: 15 files, file-manifest `10c9cfab...`, `uv.lock`
  `deb9d1f6...`, upstream `581d3986...`, zero `.pyc`, verified with the
  frozen verifier under `python3.11 -I -B`.
- Model snapshot `/workspace/cas-model-a8969eb7`: exactly 5 files, all
  SHA-256s match the frozen model manifest; no model load.
- OpenSSL: empty-config bound check passed; `x509` accepted the PEM root
  certificate on stdin without `-in -`; root fingerprint
  `552f7bdc...` exact.
- NEW (Attempt 6): CRLF normalization contract verified on the pod against
  real `openssl ts -query -text` output — pod OpenSSL emits LF (zero CR);
  the receiver normalizer is the identity on LF, repairs a synthetic CRLF
  variant to identical bytes, and fails closed on bare CR; the helper
  normalizer behaves identically; the runner's sealed-memfd
  `_run_bound_openssl` real-binary path plus `_decode_bound_openssl_text`
  passed on the real binary.
- Wrapper fail-closed: rc 2 without `-I` (isolated-mode message) and rc 2
  with `-I` but without `-B` (bytecode message).
- GPU compute application count after all checks: 0.
- Identity boundary: no nonce, run ID, PRE, protocol, query, response,
  anchor, or launch artifacts exist under the prestage root
  `/workspace/cas-jlcv1-attempt6-prestage-29551624-20260723`.

## Claim boundary

Non-model prestage evidence only: no nonce, run ID, PRE, protocol, query,
TSA transmission, anchor, launch configuration, model load, CUDA
invocation, or scientific result. Execution mode remains `SHADOW`, verdict
`NONE`, claim status `NOT_LICENSED`, whole-project score approximately
`0.33 / 1.00`. Attempt 1-5 identities are never reused; Attempt 5's
consumed one-shot and retained response are unaffected.

## Next gate

Create the fresh Attempt 6 create-once identity: nonce record and run ID,
official root `/workspace/cas-jlcv1-official-29551624-<run8>`, staged
repo/dependency/frozen/model, PRE capture and independent re-verify,
protocol, tool bindings (pin the LF-emitting receiver OpenSSL
`2c6f2c64...`; the repaired code tolerates either), network guard plan,
anchor payload, and the exact RFC3161 query. Any transmission then requires
a new byte-specific owner approval for the exact new query bytes. The
provider controller capture step requires an authenticated RunPod UI DOM
observation by the operator.
