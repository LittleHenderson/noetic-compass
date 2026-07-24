# Attempt 10 — PRODUCER TECHNICAL_CANARY_PASS_CANDIDATE (VJP fix works end-to-end); independent receiver blocked by a pre-existing torch-vs-NVML GPU-identity inconsistency

Controlling status:

`OFFICIAL_SHADOW_ATTEMPT / VJP_FIX_VALIDATED_IN_OFFICIAL_GUARDED_RUN / PRODUCER_STATUS_TECHNICAL_CANARY_PASS_CANDIDATE / ALL_NUMERICAL_SUBGATES_PASS / FULL_1248_AUTOGRAD_CONTRACT / 213_ARTIFACTS / RECEIVER_FAILED_CLOSED_ON_PREEXISTING_GPU_IDENTITY_METHOD_MISMATCH / GATE_1_NOT_YET_AUTHORIZED / SHADOW / NONE / NOT_LICENSED`

## The milestone: the VJP fix works in the official guarded run

Attempt 10 (commit `c2b56a671626210d24f6c938e1d288be0ae5f734`, the local VJP
vector-metric fix; fresh run `jlcv1-rfc3161-73499b56…`, real DigiCert RFC3161
anchor tsr `9b309aea…`, TSA time `Jul 24 15:57:29 2026 GMT`, full chain
verified) ran the full ceremony + guarded canary and the PRODUCER reached, for
the first time in Attempts 1-10, a passing producer status:

- `producer_status = TECHNICAL_CANARY_PASS_CANDIDATE_PENDING_INDEPENDENT_VERIFICATION`
- `failed_gates = []` (every numerical subgate passes, including the previously
  failing LOCAL_JVP / LOCAL_VJP)
- `autograd_grad_counters.observed_total = 1248` of `1248` (full contract)
- `artifact_count = 213`
- Execution receipt `4c5ef41c0682b80ecc1ed9b4b2058d49c148361dfb423af49f53e49be057df58`.

This confirms end-to-end, in an official anchored guarded run on real
`EleutherAI/pythia-160m` weights, that the local-VJP adjoint-vector fix (both
local limits `1e-3`) makes the canary's numerical gates pass while staying
strict. `official_pass_authorized = false` because the producer cannot
self-authorize a PASS — the independent receiver must confirm it.

## The blocker: a pre-existing torch-vs-NVML GPU-identity inconsistency (NOT the VJP fix)

The independent receiver (`verify_jacobian_lens_canary_v1_independent.py`, run
with the pinned minimal toolchain `/usr/bin/python3.11` + numpy 1.26.3, no
torch) failed closed at
`scripts/verify_jacobian_lens_canary_v1_independent.py:7221`:
`producer runtime differs from pre/post environment captures`.

Root cause (measured, `receiver.log` retained): the producer and the
environment capture read GPU identity by DIFFERENT methods, and the receiver
requires exact equality:

| field | producer runtime (execution receipt) | PRE/POST environment capture |
|---|---|---|
| source | torch `cuda.get_device_properties().total_memory` (`runtime.py:238`) | NVML `nvmlDeviceGetMemoryInfo` |
| gpu_total_vram_bytes | `47697690624` (torch CUDA-visible total) | `48305799168` (NVML board total) |
| gpu_uuid | `b7638993-cc34-ac95-7fc8-5002ce894e00` (torch, no prefix) | `GPU-b7638993-cc34-ac95-7fc8-5002ce894e00` (NVML, `GPU-` prefix) |

It is the SAME physical A40 (`b7638993`, driver `580.126.09`); the `~580 MiB`
VRAM delta and the `GPU-` prefix are stable measurement-method artifacts, not a
different device. `provider_instance_id_sha256` and `host_identity_sha256` both
MATCH. This receiver check on a PASSING receipt was never exercised before
(Attempts 1-9 never produced a passing producer receipt), so the latent
inconsistency surfaced now for the first time. It is unrelated to the VJP fix
(neither `runtime.py` nor the environment-capture code was touched by it).

## Gate status

Gate 1 (`0.38`, a receiver-confirmed technical canary PASS) is NOT yet
authorized. The producer half is done (PASS_CANDIDATE); the receiver half needs
the GPU-identity method inconsistency reconciled so the two captures agree.

## Candidate fixes (owner trust-surface decision; a fresh Attempt 11 is required either way)

1. Producer records GPU identity via the SAME source as the environment capture
   (NVML): change `runtime.py` to use `torch.cuda.mem_get_info()[1]` (which
   returns the NVML total `48305799168`) and the NVML/prefixed uuid, so producer
   == PRE/POST. Cleanest; makes the two captures genuinely consistent.
2. Receiver normalizes the known method difference: strip the `GPU-` prefix
   before comparing uuid, and compare VRAM by device identity rather than exact
   bytes (or tolerate the torch-vs-NVML delta). Smaller change, but slightly
   loosens the receiver's environment-equality check.
3. Environment capture records the torch/CUDA totals alongside NVML and the
   receiver compares those. More surface area.

Recommendation: (1) — reconcile at the source so both halves report identical
NVML GPU identity; the receiver's exact-equality check then stays strict and
passes. Either fix is a trust-surface change requiring tests, a full-suite pass,
a fresh implementation freeze, and a fresh Attempt 11 identity (new producer
run + new DigiCert anchor + receiver).

Evidence retained in `evidence/`: execution receipt `4c5ef41c` + publication
marker, `wrapper.stdout.log`, `launch_started/finished.json`, `receiver.log`
(the fail-closed line), and the anchor receipt.
