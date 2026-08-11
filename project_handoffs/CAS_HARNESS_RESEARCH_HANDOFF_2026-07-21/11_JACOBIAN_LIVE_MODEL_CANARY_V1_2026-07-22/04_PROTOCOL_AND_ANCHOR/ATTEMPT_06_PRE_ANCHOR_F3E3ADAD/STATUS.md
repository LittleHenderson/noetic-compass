# Attempt 6 pre-anchor ceremony (in progress)

Controlling status:

`PRE_ANCHOR_FROZEN / QUERY_UNSENT / WAITING_FOR_EXPLICIT_BYTE_SPECIFIC_TSA_APPROVAL / NO_EXTERNAL_TRANSMISSION / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

## Frozen pre-anchor set (2026-07-23, final)

- Controller capture (create-once, frozen ceremony): 1,248 bytes, SHA-256
  `1e3c6b200f61c2d4d84c1160d874636d5cd54b782401b1f7e3acd5e492d20606`,
  captured `2026-07-23T15:20:32.657Z` from the operator-signed-in RunPod
  console read live through the operator's in-app browser session, plus an
  SSH runtime cross-check. GPU name `NVIDIA A40` was observed in the
  signed-in deploy page GPU-card DOM attribute
  (`data-ph-capture-attribute-gpu-card-selected`); advertised VRAM
  `48 GB` from the card text `1x A40 (48 GB VRAM)`. The raw retained
  observation is `control/runpod_provider_observation_raw.txt`. A first
  capture pass (14:48Z, `05486ad7...`, short GPU name and Telemetry
  45 GiB figure) is retained under `control/superseded_first_capture/`.
- PRE (third capture, final): main record SHA-256
  `73e043701b4151f17ac6cb29a0258e63412f8e4d6d6227c1163d1d96b892e963`,
  captured after the controller observation as the ceremony ordering
  invariant requires; independent same-host re-verify exit `0`,
  `CURRENT_RUNTIME_FILES_MATCH_CAPTURE`, 17,007 records, 5,089,508,503
  bytes. Two earlier PREs (pre-controller ordering) are retained as
  `environment_pre_superseded_ordering_20260723/` (main `a999ade0...`)
  and `environment_pre_superseded_precontroller_20260723/` (main
  `915a3fe7...`) with their re-verify receipts; neither was anchored or
  used.
- V1 protocol (frozen ceremony, full evidence chain validated): 8,141
  bytes, SHA-256
  `013c8b528c50e5cb260a9a642ed3d597304b6d8c3ebdd601a4a1523faf6cdc01`.
- Base V0 protocol canonical: 14,190 bytes, SHA-256 `1a674561...`
  (materialized against the ceremony's frozen pins).
- Anchor payload: 3,858 bytes, SHA-256
  `f51eefa42b735120eecf3a4d223242a71301e79585d07dd7b3ecbd83375adb0a`.
- RFC3161 query: exactly 104 bytes, SHA-256
  `c47ba9d88710deb3861f245252f48247b443e72d9a3c3cf756eddf4069578fc5`,
  UNSENT. Independent DER reconstruction from the anchor payload and
  nonce matched byte-for-byte; the pinned LF-emitting receiver OpenSSL
  (`2c6f2c64...`) decoded it and the repaired CRLF-safe parser verified
  policy OID `2.16.840.1.114412.7.1`, the exact nonce, the payload
  imprint, and the certificate-request flag; the nonce derives run ID
  `jlcv1-rfc3161-f3e3adad...`.

The next executable action is this exact single-use owner approval:

`I approve sending the exact 104-byte RFC3161 query with SHA-256 c47ba9d88710deb3861f245252f48247b443e72d9a3c3cf756eddf4069578fc5 to DigiCert.`

## PRE capture and independent re-verify (2026-07-23)

- Network guard plan (create-once, frozen builder on the pod):
  SHA-256 `b1d25efd7ca66248931f519bdc1312b1135005e9676ba7f95e2f27c5ce2e0afa`;
  live-probed `unshare -n` / `unshare -Urn` both `EPERM`; CAP_NET_ADMIN and
  CAP_SYS_ADMIN absent; pod-instance hashes computed with the frozen module
  (research `6a06b1fb...` — identical to the Attempt 5 binding — and
  production `a1c042b3...`).
- Tool bindings: receiver `9409fc7b...` (Windows Git + LF-emitting
  `usr/bin` OpenSSL `2c6f2c64...`); runner `ce16acc6...` (pod git+openssl).
- PRE capture: two fail-closed rejections preceded success and consumed
  nothing (`environment_pre` remained empty): first `transformers`
  unavailable under `python3.11 -I`, then `jlens` unavailable without the
  editable-source path. The successful capture used `/usr/bin/python3.11
  -B` with `PYTHONPATH` exposing the pinned bootstrap venv site-packages
  and the `jacobian_lens_v1` editable source — reproducing the exact
  import surface recorded in the Attempt 5 PRE (transformers 5.9.0, jlens
  at `/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/jlens`) — and
  the authentic pod-local `RUNPOD_POD_ID`.
- PRE main record: SHA-256
  `a999ade09f3ac028113fa4613c5ec6a962491e1476f27073b1173482dc2b997b`.
- Independent same-host re-verify (bootstrap venv `python -I -B`,
  read-only, create-once receipts): exit `0`,
  `CURRENT_RUNTIME_FILES_MATCH_CAPTURE`, 17,007 file records,
  5,089,508,503 bytes; `provider_authenticated=false` remains an explicit
  limitation as in Attempt 5.

## Exact identity

- Run ID:
  `jlcv1-rfc3161-f3e3adad7ff2b94a335fa199a0cda440dcd767e6ac7c10db8d39465b662ed541`
- Nonce:
  `7136326b17a6f94bff932dc5ec733a68bcc5f07265c85c15e2528e7bae37628b`
- Nonce record: 646 bytes, SHA-256
  `a673d02150f1372ed686329bc681268251ba4a61d51da563187ef0372ebeeb0c`
  (created create-once by the frozen `prepare_jacobian_lens_canary_v1.py
  nonce` tool at commit `29551624` on the operator workstation; retained at
  `control/jacobian_lens_canary_v1_nonce_record.json`).
- Research pod: `zp2s9pscgncn0b` (`69.30.85.51:22111`, host key pin
  `SHA256:V6BZrhQOBzY1vPKdVGF1XNWGWst6jwQWSD19YwM5xSw`).
- Official root: `/workspace/cas-jlcv1-official-29551624-f3e3adad`.
- Commit `29551624f4de0eec61c4035e364203be55d6c08a`, tree `0d70f8e8...`,
  parent `f72b89cd...`.

## Staged so far (2026-07-23)

Official root created create-once with `repo` (bundle clone, fsck strict,
clean, detached at the exact commit), `dependency` (verified 15-file
bundle, `uv.lock` `deb9d1f6...`), `frozen` (8 publication inputs),
`control` (implementation manifest + nonce record), and empty
`output`/`runlog`/`post`/`environment_pre`. Zero `.pyc`; zero GPU compute
applications; `chmod 0700` remains ineffective on the persistent volume
(mode 0777) — the same documented limitation as Attempts 3-5.

## Remaining before any transmission

1. Runner/receiver tool bindings and network guard plan (create-once).
2. PRE capture at the official root (requires the network-guard-plan
   receipt SHA-256 and provider-instance binding) plus the independent
   same-host PRE re-verify.
3. Provider controller capture — requires an authenticated RunPod UI DOM
   observation by the operator.
4. Protocol, anchor payload, and the exact 104-byte RFC3161 query
   (create-once, untransmitted).
5. Byte-specific owner approval of the exact new query bytes BEFORE any
   one-shot DigiCert transmission. The ceremony must pin the LF-emitting
   receiver OpenSSL `2c6f2c64...` (the repaired code tolerates either).

No Attempt 1-5 identity is reused. No TSA transmission, model load, or
CUDA execution has occurred for Attempt 6.
