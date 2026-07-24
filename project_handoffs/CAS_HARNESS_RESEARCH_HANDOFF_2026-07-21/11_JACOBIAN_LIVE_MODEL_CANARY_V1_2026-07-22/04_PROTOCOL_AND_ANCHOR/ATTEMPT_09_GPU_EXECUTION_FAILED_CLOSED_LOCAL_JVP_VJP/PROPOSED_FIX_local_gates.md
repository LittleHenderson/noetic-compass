# Proposed fix for the LOCAL_JVP / LOCAL_VJP gates — for owner review (2026-07-24)

Owner asked (Option 3): show the exact diff, the before/after numbers on all 24
local measurements, proof the gate stays strict, and the rationale — before any
edit to the trust surface and before Attempt 10.

## Evidence (all 24 local measurements, faithful float32 reconstruction; `a9_metric_candidates.py`)

Four candidate metrics measured on the CLEAN (real, accurate) Jacobian and on a
CORRUPTED Jacobian (`M * 1.005`, a 0.5% error a valid gate MUST catch):

| metric | clean max | clean >1e-4 | clean >1e-3 | corrupt max | corrupt >1e-3 |
|---|---|---|---|---|---|
| **JVP** (vector, current metric) | `5.354e-4` | 23/24 | 0/24 | `5.13e-3` | 24/24 |
| **VJP_old** (current scalar bilinear) | `4.241e-3` | 18/24 | 5/24 | `8.52e-3` | 23/24 |
| **VJP_natural** (scalar / `‖v‖·‖Ju‖`) | `3.122e-5` | 0/24 | 0/24 | `2.75e-4` | **0/24** |
| **VJP_vector** (adjoint vector) | `5.354e-4` | 24/24 | 0/24 | `5.09e-3` | 24/24 |

Reading:
- **VJP_old is the bug** — ill-conditioned; `4.24e-3` because it divides by
  `|v^T J u|`, which collapses when the random target `v` is near-orthogonal to
  `Ju`. Not a measurement defect (see `INVESTIGATION_local_vjp.md`).
- **VJP_natural is DISPROVEN** — passing but neutered: on a 0.5% corrupted matrix
  it never exceeds `1e-3` (0/24) and clears `1e-4` in only 12/24. It cannot serve
  as a gate. (This is the Cauchy–Schwarz redundancy: `VJP_natural = |cosθ| · JVP`,
  ~`JVP/√768` on average.)
- **VJP_vector is correct** — compare the true reverse-mode VJP vector
  `A^T v` against `M^T v` with the SAME `vector_relative_error` the JVP already
  uses. Well-conditioned (no scalar collapse), independently tests the adjoint,
  passes the accurate matrix at `1e-3` (`5.35e-4`), and catches the 0.5%
  corruption at `5.1e-3`. It is the symmetric partner of the JVP vector check.
- **JVP** is already well-conditioned; its `5.35e-4` clean max is the estimator's
  genuine matrix-accuracy floor (DIM_BATCH=8 probes), so its `1e-4` limit is
  simply tighter than the estimator achieves — same situation the owner already
  resolved for the functional gate (`5e-4`).

## Recommended change (both local gates → well-conditioned vector checks at a documented 1e-3)

### 1. Limits — `research/jacobian_lens_canary_core.py`

```
-51: JVP_RELATIVE_ERROR_LIMIT = 1e-4
-52: VJP_RELATIVE_ERROR_LIMIT = 1e-4
+51: JVP_RELATIVE_ERROR_LIMIT = 1e-3   # empirical matrix-accuracy floor 5.35e-4 (DIM_BATCH=8); ~1.9x margin; catches 0.5% corruption at 5.1e-3
+52: VJP_RELATIVE_ERROR_LIMIT = 1e-3   # adjoint vector floor 5.35e-4; same margin; catches 0.5% corruption at 5.1e-3
```
`scalar_relative_error` (core.py:332) is unchanged and stays available for other
callers; it is simply no longer used for the VJP gate.

### 2. VJP metric — `research/jacobian_lens_canary_torch.py` `local_jvp_vjp_check` (lines ~356-377)

Replace the scalar bilinear VJP with the adjoint VECTOR, mirroring the JVP:

```
   predicted_jvp = matrix_tensor @ source_vector
-  direct_vjp = torch.sum(gradient * tangent)
-  predicted_vjp = torch.dot(target_vector, predicted_jvp)
+  # reverse-mode VJP vector (adjoint): reduce the per-position gradient over the
+  # valid positions so that <reverse_vjp, source_vector> == sum(gradient*tangent).
+  reverse_vjp = gradient[0, valid_start : valid_end + 1, :].sum(dim=0)
+  predicted_vjp_vector = matrix_tensor.transpose(0, 1) @ target_vector
   ...
-  direct_vjp_float = float(direct_vjp.detach().cpu().item())
-  predicted_vjp_float = float(predicted_vjp.detach().cpu().item())
+  reverse_vjp_cpu = reverse_vjp.detach().to(dtype=torch.float32, device="cpu").contiguous()
+  predicted_vjp_cpu = predicted_vjp_vector.detach().to(dtype=torch.float32, device="cpu").contiguous()
   return LocalDerivativeResult(
       direct_jvp=direct_cpu,
       matrix_predicted_jvp=predicted_cpu,
       jvp_relative_error=vector_relative_error(direct_cpu.tolist(), predicted_cpu.tolist()),
-      direct_vjp_bilinear=direct_vjp_float,
-      matrix_predicted_vjp_bilinear=predicted_vjp_float,
-      vjp_relative_error=scalar_relative_error(direct_vjp_float, predicted_vjp_float),
+      direct_vjp=reverse_vjp_cpu,
+      matrix_predicted_vjp=predicted_vjp_cpu,
+      vjp_relative_error=vector_relative_error(reverse_vjp_cpu.tolist(), predicted_vjp_cpu.tolist()),
       graph_connected=True,
       gradient_nonzero=gradient_nonzero,
   )
```
`LocalDerivativeResult` (torch.py:27) changes its two VJP fields from scalars
(`direct_vjp_bilinear`, `matrix_predicted_vjp_bilinear`) to vectors
(`direct_vjp`, `matrix_predicted_vjp`).

### 3. Ripple (must change in lockstep — these are why this needs a full freeze, not a one-liner)

- `research/jacobian_lens_canary_executor.py` (~560-600): the `vjp-direct-*` /
  `vjp-matrix-*` artifacts become width-vectors (published like the JVP vectors via
  `_publish_tensor` instead of `_publish_scalar`); `DerivativeErrorRecord` is
  unchanged (still carries `relative_error`).
- `scripts/verify_jacobian_lens_canary_v1_independent.py` (line 243 limit; ~6850
  recompute): update the independent VJP limit to `1e-3` and recompute
  `maximum_vjp` as `vector_relative_error` over the new vector artifacts (it
  currently recomputes a scalar relative error).
- Tests for `local_jvp_vjp_check` / receipts / verifier; then bootstrap hard pins
  in `scripts/run_jacobian_lens_canary_v1.py`, full worker suite, fresh
  implementation freeze at a new commit, fresh Attempt 10 identity.

## Why this is a fix, not a loosening

The VJP gate stays strict: on a 0.5% matrix corruption VJP_vector reads `5.1e-3`
(24/24 over `1e-3`) — it fails loudly. What changes is that it now measures a
well-conditioned quantity (the adjoint's vector relative error) instead of a
scalar that divides by a random near-zero projection. The `1e-3` limit documents
the estimator's genuine ~`5.35e-4` accuracy floor with margin, exactly parallel
to the functional gate's `5e-4`. The rejected alternative (VJP_natural at any
limit) is not adopted precisely because the corruption test shows it is too weak.

Nothing here is applied yet. On your go I implement all of §1-§3, run the full
suite, re-freeze at a new commit, and take Attempt 10 to a clean pass.
