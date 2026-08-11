# Attempt 5 pre-anchor freeze

Controlling status:

`PRE_ANCHOR_FROZEN / QUERY_UNSENT_BY_CONTROLLED_WORKFLOW / NO_TSA_RESPONSE_OR_RECEIPT_OBSERVED / WAITING_FOR_EXPLICIT_BYTE_SPECIFIC_TSA_APPROVAL / NO_OFFICIAL_MODEL_OR_CUDA_EXECUTION_ARTIFACTS / SHADOW / NONE / NOT_LICENSED`

## Outcome

Attempt 5 has passed the implementation freeze, isolated RunPod non-model
prestage, fresh `dd55bc73` PRE capture, independent PRE runtime
re-verification, exact protocol construction, remote control publication,
offline RFC3161 query reconstruction, and live continuity check.

The exact query is **104 bytes**, SHA-256
`e73850302dc31015af2cd5624eed70d445ef553a7de9acca640d5ba9cca9a846`.
The controlled Attempt 5 workflow has not transmitted it, and no TSA response
or receipt is present. Provider egress logs and TSA-side request logs are
unavailable, so this does not independently prove that no off-path historical
transmission ever occurred.

## Exact identity

- Run ID:
  `jlcv1-rfc3161-dd55bc73ab446ccc794d26c2aeaa2eec2b0997d1384db9752e0f7615d804c380`
- Nonce:
  `5c47d99e959b3137a8b77f4f4b469a16eb3ca4c4794e0bae0f99100013fc4842`
- Research pod: `zp2s9pscgncn0b`
- Production pod: `hilj2rzs54gi06` - not targeted by the controlled workflow;
  separately observed idle at audit time
- Remote root:
  `/workspace/cas-jlcv1-official-f72b89cd-dd55bc73`
- Commit: `f72b89cd2ec574400ffe69ad7bd1540791fb73c3`
- Tree: `71c45fd5999b1d3f31636bbae8bd199d166ab2f5`
- Parent: `be97bc7f76d1e9f5e501702660678d4af3081f5e`

The earlier `eeec3ec7` setup identity is superseded and must never be resumed,
repaired, or reused. Its retained negative-evidence record is under
`superseded_eeec3ec7/`.

## PRE and continuity evidence

The PRE main record is 3,683 bytes, SHA-256
`4ecd72100da14ccaa657cdd47ae85e8ba5373b66b6c5a71581aea597435ce097`.
The original SSH parent did not retain the original capture command's exit
status, so that historical exit status is `UNAVAILABLE`; it is not guessed.

A separate create-once verifier reopened the PRE and rehashed the current
runtime on the same pod. It passed with exit code `0`, verifying 16,351 file
records and 5,085,465,464 bytes. Provider authentication remains `false`, and
claim status remains `NOT_LICENSED`.

The corrected-wrapper live continuity check passed at
`2026-07-23T06:50:17Z`. It reverified the exact clean repository, dependency,
all frozen inputs, five model-snapshot files without loading the model, all PRE
files, all published protocol/query files, host/boot/machine identity, A40 GPU
identity and memory, empty output/runlog/POST directories, zero GPU compute
applications, and absence of timestamp response, anchor receipt, and launch
configuration. No official model/CUDA execution artifacts or live model/CUDA
process were observed. Provider historical process and production-pod mutation
logs are unavailable, so those observations are not global historical proof.

The exact current remote checker from the wrapper's executed path was recovered
as `operator/attempt5_live_continuity_check.sh`: 10,258 bytes, SHA-256
`73fa856e6e0be1b339c8f2437262fbfc71dcf8f15146312e71cd34848eb10171`.
It is byte-identical to the frozen root checker. Without immutable file-history
or provider audit logs, that current match does not independently prove the
bytes present at the earlier execution instant.

The persistent RunPod volume retained the attempt root at mode `0777`, not
`0700`. Isolation therefore relies on the dedicated pod/container boundary and
the exact retained hashes; it is not host-level exclusive-filesystem proof.

## Frozen protocol and query

- V1 protocol: 8,141 bytes, SHA-256
  `a038e18087a31956339f235a852e59a0fc67bc4088434f502787df68428abf34`
- 22-path launch mapping: 2,606 bytes, SHA-256
  `ceebdc5a9720bc3c466760bab3c9b378f70c2317293177adf3e9126b35ff9643`
- Anchor payload: 3,858 bytes, SHA-256
  `240d6f2de585c3f098d96b05a02fee4a121b3deb30f0165a28c40a79fe79c991`
- RFC3161 query: 104 bytes, SHA-256
  `e73850302dc31015af2cd5624eed70d445ef553a7de9acca640d5ba9cca9a846`
- Message imprint: SHA-256 of the exact anchor payload,
  `240d6f2de585c3f098d96b05a02fee4a121b3deb30f0165a28c40a79fe79c991`
- Policy OID: `2.16.840.1.114412.7.1`
- Certificate requested: `yes`

The exact frozen record is `ATTEMPT_05_PRE_ANCHOR_FREEZE_RECORD.json`: 8,977
bytes, SHA-256
`030acb27494bdf10fcceb7d3b19ac18b9c7afc073da11cedd438e15368bf0946`.
Its categorical negative wording is superseded in interpretation by
`ATTEMPT_05_PRE_ANCHOR_EVIDENCE_BOUNDARY_CORRECTION.json`: 3946
bytes, SHA-256
`11b38c42f04b2613064ae4b76882afb8297d7c720ed08110d814e0b339626803`. Both records are retained.

The correction is a separate governance addendum created after the frozen
query. It changes evidence interpretation, not any execution input, so this
Attempt 5 query remains the pre-execution query. The correction must be bound
into the final evidence-package manifest and final integrity anchor.

## Local recursive artifact manifest

`ARTIFACT_MANIFEST.json` is the self-excluding snapshot of every other local
file in this Attempt 5 package. It includes both the original freeze record and
the evidence-boundary correction. Read the manifest itself for its entry count,
artifact byte count, artifact-tree hash, and per-file hashes.

The manifest was created after the frozen pre-execution query, so it is not
bound by that query and is not a TSA receipt. The manifest, correction, and all
later execution artifacts must be bound by the final integrity anchor. Creating
this local inventory does not change the controlling status or license a result.
## Approval and execution boundary

The only acceptable approval for transmission is:

> I approve sending the exact 104-byte RFC3161 query with SHA-256 e73850302dc31015af2cd5624eed70d445ef553a7de9acca640d5ba9cca9a846 to DigiCert.

Earlier approvals are not reusable. Until that exact sentence is supplied,
do not transmit the query, build a timestamp receipt or launch configuration,
or execute the model/CUDA canary.

No hidden-state result, Jacobian result, J-Space result, CJT result, RPM
result, CAS Ohm result, steering result, ablation result, prompt-injection
detection result, cross-architecture result, 300B result, product verdict, or
scientific conclusion exists from Attempt 5. The whole-project score remains
approximately `0.33 / 1.00`.
