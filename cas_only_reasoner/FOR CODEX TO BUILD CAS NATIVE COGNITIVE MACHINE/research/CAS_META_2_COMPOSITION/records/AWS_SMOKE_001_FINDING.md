# First CAS-META-2 cloud preflight: failed, evidence preserved

This attempt established Blackwell compatibility for the preserved native GPU contract tests, but it did not reach composition execution or training.

## Exact identities

- Source: `2a3ec1132770b121881a49effee2aa5d4e0494fb`.
- Source archive SHA256: `a2acd19a441e287515c908fb1d4666d25be7002bfe44f2fee48c385c3dc676b8`.
- Job: `cas-meta2-20260905164134-b6dc38fe`.
- Instance: `i-0ff419349834386fd`, AWS `g7.2xlarge`, `us-west-2`.
- Observed GPU: `NVIDIA RTX PRO 4500 Blackwell Server Edition`.
- Observed software: Python `3.12.3`, PyTorch `2.11.0+cu128`, CUDA `12.8`.
- Downloaded packet SHA256: `66582357c3c39078ae1788eed2988abcc7342504b3fa216b168b2f6130711fc0`.

## Results and cause

The CUDA matrix check passed. The preserved META-1 native GPU contract suite reported **4 passed, 0 failed, 0 skipped**. The new META-2 policy suite reported **3 passed, 1 failed, 0 skipped**. The failing test was `test_both_generators_have_gradients_and_matched_active_parameters`.

The raw failure reports no nonzero gradient for CAS gate parameters including `raw_cutoff`, `raw_span`, `bias_projection.weight`, `diagnostic_projection.weight` and `diagnostic_projection.bias`. The candidate initialized saturation to `4.0` although native current is summed across valid keys. Static inspection of the unchanged CASformer gate shows that once normalized activation reaches its upper clamp, the gate is exactly one and those derivatives are zero. This is a candidate initialization problem, not evidence that the absolute-flow gate should be removed or that its test should be weakened.

The next candidate must keep the actual gate parameters trainable, use a length-appropriate starting range, and pass a real GPU gradient check at the intended training geometry. Any fix has a new source identity. The failed source and raw packet remain unchanged.

## Cleanup and budget

The launcher saved and verified the packet before requesting termination. It reported `CLEANUP_REQUIRES_ATTENTION` while EC2 was still shutting down. The later, separate correction receipt confirms termination, volume deletion, and removal of the job's security group, profile, two roles and schedule. The original failure receipt was not rewritten.

Cleanup was confirmed at `2026-09-05T16:51:45.238677+00:00`. All six source/result S3 objects remain under seven-day retention. The conservative compute-only estimate to observed termination is `$0.4134624375`; this is not an AWS invoice and excludes other charges. The full `$7` reservation remains in the shared `$400` ledger; no refund was invented.

## Audit files

- `aws_smoke_001/launch_receipt.json`: original launch and incomplete-cleanup receipt.
- `aws_smoke_001/cloud_artifacts.zip`: original downloaded cloud packet.
- `aws_smoke_001_cleanup/correction_receipt.json`: separate verified cleanup closure.
- `aws_smoke_001_cleanup/provider_calls.jsonl`: raw cleanup provider responses, SHA256 `5b0c04d073ce077da63bcbe6a76c23c0888e833b8f410c40233daa888a35ac4f`.

No training checkpoint, composition-smoke result, learning improvement, CAS-specific advantage or completed vision is claimed by this attempt.
