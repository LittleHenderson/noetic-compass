# Attempt 9 guarded shadow canary — GPU execution, FAILED CLOSED at LOCAL JVP/VJP numerical subgates

Controlling status:

`OFFICIAL_SHADOW_ATTEMPT_FAILED_CLOSED_AT_NUMERICAL_SUBGATES / OWNER_5e-4_FUNCTIONAL_FIX_VALIDATED_IN_OFFICIAL_RUN / FULL_1248_AUTOGRAD_CONTRACT_MET / ALL_213_ARTIFACTS_PRODUCED / LOCAL_VJP_FLOOR_4.24e-3_IS_THE_REAL_WALL / SHADOW / NONE / NOT_LICENSED`

## Identity

- Code commit `6d676840d575488cc71e95017c79aa372fd9813f` (owner-directed 5e-4 recalibration).
- Fresh Attempt 9 identity: run `jlcv1-rfc3161-179fa0ff51dcef07db7f1b6627ba08a2285a1624849b843b098b9b2cabf28b82`, nonce `7364d32a…`.
- Protocol raw `6d73a3f8…`; official run dir `cas-jlcv1-official-6d676840-179fa0ff` on pod `zp2s9pscgncn0b` (A40, `GPU-b7638993…`).
- Real DigiCert RFC3161 anchor: tsq `e68e955d…` (104 bytes), tsr `0299b29a…` (6033 bytes), TSA time `Jul 24 07:57:24 2026 GMT`, status `QUERY_NONCE_IMPRINT_POLICY_SIGNATURE_CHAIN_RESPONDER_AND_TRUST_ROOT_VERIFIED`.
- Execution receipt `30d9891fd39853857572d6da13d81479884c0858d1f69209d4de717e26adc864`.

## What this run proves (deepest run to date)

The owner-directed recalibration of `GRADIENT_ANALYTIC_RELATIVE_ERROR_LIMIT` (1e-4 -> 5e-4) is VALIDATED in an official guarded run: it cleared Attempt 8's exact failure (the functional analytic-vs-gradient cross-check). The run advanced strictly further than any prior attempt:

- `MODEL_LOAD`, two-phase seccomp guard, full measurement: all PASS.
- The full **1248-autograd-call contract is MET**: `observed_total = 1248` of `1248` (functional_direction 8 + functional_measurement 16 + local_derivative 72 + matrix_estimator 1152). Attempt 8 reported `0` here (a failure-path default); Attempt 9 reaches the SUCCESS accounting.
- **All 213 artifacts produced** (`artifact_count = 213`; A8 produced 212).
- Every numerical subgate PASSES except two: `REPEAT_RELATIVE_FROBENIUS` (1e-5), `MIDDLE_DOSE_MEDIAN`/`P90`, `SIGN_AGREEMENT` (1.0), `AFFINE_R2` (min 0.9994), and the functional derivative gate all pass.

It is NOT a technical-canary pass: wrapper exit `0`, `producer_status = TECHNICAL_CANARY_FAIL`, `official_pass_authorized = false`, `failure_stage = NUMERICAL_SUBGATES`, `failed_gates = [LOCAL_JVP_RELATIVE_ERROR, LOCAL_VJP_RELATIVE_ERROR]`. Claim `SHADOW / NONE / NOT_LICENSED`, score stays `0.33`.

## The precise finding — the real wall is the LOCAL VJP gate, not the functional gate

The two remaining failures are SEPARATE constants from the one the owner recalibrated:
`JVP_RELATIVE_ERROR_LIMIT = 1e-4` and `VJP_RELATIVE_ERROR_LIMIT = 1e-4` (jacobian_lens_canary_core.py:51-52). They check the same forward-vs-reverse autodiff agreement, but for the LOCAL per-block directional derivatives (72 grad calls), which `execute_canary_raw` measures but does not itself gate — so the earlier `execute_canary_raw`-at-5e-4 confirmation (213 artifacts) did not exercise them.

Empirical local forward-vs-reverse floor on this stack (float32, A40, torch 2.12/cu13; `local_jvp_vjp_float32_distribution.txt`):
- **JVP**: max `5.35e-4` (23/24 > 1e-4; 2 > 5e-4; 0 > 1e-3).
- **VJP**: max **`4.24e-3`** (10/24 > 5e-4; **5 > 1e-3**).

The VJP worst case `4.24e-3` is the exact number the Attempt 8 STATUS attributed to "the fuller comparison set" and the owner's Deep Dive flagged: widening a gate that far "would make it a weak agreement check (2 significant figures) and materially weaken the scientific claim — it must NOT be silently loosened to force a pass."

So the owner's 5e-4 is correct for the FUNCTIONAL gate but the LOCAL VJP gate is ~20x looser (`4.24e-3` vs `2.2e-4`) and is the binding constraint. Reverse-mode vs forward-mode VJP agree to only ~2.4 significant figures worst-case on this stack for 5 of 24 local measurements. No functional-gate recalibration alone can make the canary pass.

## Owner scientific decision required (NOT taken autonomously)

Passing the canary requires an owner decision on the LOCAL JVP/VJP gates specifically, because the sensible-default path (widen VJP to ~5e-3) is one the owner explicitly warned weakens the claim. Options:

(A) Recalibrate local gates from the empirical floor (JVP ~1e-3, VJP ~5e-3), documented — fastest to a PASS, but the VJP check drops to ~2 significant figures.
(B) Investigate the 5 worst VJP measurements first (float64 targeted reconstruction + conditioning of their target-space directions) to determine whether `4.24e-3` is a benign precision/conditioning floor or a real VJP-path defect, THEN set the threshold — the rigorous branch of the owner's own A8 decision framework. (float64 via the full executor is blocked by float32-only norm-capture assertions, so this needs a targeted reconstruction like A8's conditioning test.)
(C) Hold / tighten the VJP formulation so the cross-check can stay strict.

Recommendation: (B) — characterize the VJP floor before setting any threshold, exactly as was done for the functional gate; then the local-gate recalibration (if the floor is benign) is defensible rather than a force-pass.
