# Attempt 5 remote prestage

Captured at UTC: `2026-07-23T06:04:25Z`

Controlling status:

`REMOTE_PRESTAGE_PASS / IMPLEMENTATION_RECONSTRUCTION_MATCH / DEPENDENCY_MATCH / MODEL_AND_PUBLICATION_INPUTS_REHASHED / OPENSSL3_STDIN_PASS / CAPACITY_GATE_PASS / NO_PRE_OR_RUN_IDENTITY / NO_RFC3161_QUERY / NO_EXTERNAL_TSA_TRANSMISSION / NO_MODEL_OR_CUDA_EXECUTION / SHADOW / NONE / NOT_LICENSED`

## Outcome

The non-model remote prestage for prospective Attempt 5 passed on the dedicated
RunPod research pod observed as `zp2s9pscgncn0b`. It reconstructed and verified
the frozen implementation, dependency archive, exact model snapshot, published
input receipts, OpenSSL 3 stdin path, and minimum GPU-memory capacity without
creating an Attempt 5 execution identity and without loading a model or invoking
CUDA.

This receipt is time-bound to the exact signed-in provider observation and SSH
prestage transcript captured at `2026-07-23T06:04:25Z`. Mutable provider values
below are observations at capture, not claims about current provider state.

## Frozen implementation reconstruction

The remote reconstruction matched the canonical Attempt 5 freeze:

- commit `f72b89cd2ec574400ffe69ad7bd1540791fb73c3`;
- tree `71c45fd5999b1d3f31636bbae8bd199d166ab2f5`;
- parent `be97bc7f76d1e9f5e501702660678d4af3081f5e`;
- complete single-head Git bundle: 36,549,194 bytes, SHA-256
  `360dfc7fab45b780eec2a52b049d9bdb660bc33251fb86dcecd5bc5e8748074b`;
- implementation-freeze record: 5,523 bytes, SHA-256
  `cee9e89599e8cb48b061680af655e23817b269d70068959d8ce2bc435242dfe0`;
- canonical 31-file implementation manifest: 5,689 bytes, SHA-256
  `cb72ea06ef560b12eeeb0ec843aa46b777d16185bc41089339439a489ca51579`;
- remotely reconstructed manifest: the same 5,689 bytes and SHA-256; and
- `git fsck --full --strict` passed and the reconstructed repository was clean.

## Dependency, input, and capacity verification

The retained dependency archive matched the exact 15-file input: archive
SHA-256
`ed16af7ae5a1ac8d61c6d3e83cf946a8cb3669c10f0f679fb2351965d5922bb8`,
file-manifest SHA-256
`10c9cfab8284582c2a46484dd74bb5435ba9d2dd4c6d946f7dac4d97aae20a00`,
and `uv.lock` SHA-256
`deb9d1f618aac3df95e5b93e226153e196d6aecbb8f619ca7e1e6cb34d839d7b`.
Verification ran under bytecode-disabled isolated Python and left zero `.pyc`
files.

The exact `EleutherAI/pythia-160m` snapshot at revision
`50f5173d932e8e61f858120bcb800b97af589f46` and all eight frozen publication
inputs were rehashed without a model load. Exact file counts, byte counts, and
hashes are retained in `REMOTE_PRESTAGE_OBSERVATIONS.json`.

At capture, the dedicated container reported NVIDIA A40 UUID
`GPU-b7638993-cc34-ac95-7fc8-5002ce894e00`, driver `580.126.09`, and
48,305,799,168 bytes of GPU memory, exceeding the exact 24,000,000,000-byte
minimum gate. Python 3.11.10, Git 2.34.1, and OpenSSL 3.0.2 were observed.

The wrapper and child each failed closed with return code `2` when `-B` was
omitted. The empty-config-bound OpenSSL check passed. `openssl x509` accepted
the PEM certificate through stdin without `-in -`, exercising the repaired
OpenSSL 3-compatible path. The GPU compute-application count after all prestage
checks was zero.

## Security and provider boundary

Neither `CAP_NET_ADMIN` nor `CAP_SYS_ADMIN` was present. Network and
user/network namespace isolation through `unshare -n` and `unshare -Urn` was
unavailable. The persistent attempt root remained mode `0777` after
`chmod 0700`; filesystem isolation therefore relies on the dedicated
pod/container boundary plus exact retained evidence hashes. The container image
digest was `UNAVAILABLE`; the observed tag was
`runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`.

The signed-in RunPod UI showed research compute at `$0.44/hour`, research total
at `$0.45/hour`, and balance `$84.47` at capture. These values are historical
observations. Production pod `hilj2rzs54gi06` was not used or changed.

## Claim boundary

At this prestage boundary there was no nonce, run ID, PRE, protocol, query,
timestamp response, anchor, launch configuration, external TSA transmission,
model load, CUDA invocation, hidden-state result, steering, ablation,
prompt-injection result, cross-architecture result, 300B result, product
verdict, or scientific conclusion. The TSA transmission count was zero.

This receipt proves only that the frozen Attempt 5 inputs and non-model remote
preconditions passed the checks recorded in
`REMOTE_PRESTAGE_OBSERVATIONS.json`. Execution mode remains `SHADOW`, verdict
remains `NONE`, claim status remains `NOT_LICENSED`, and the whole-project
score remains approximately `0.33 / 1.00`.

Later identity creation and PRE artifacts belong to a separate evidence root
and do not retroactively expand this prestage receipt.
