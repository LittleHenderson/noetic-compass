# Attempt 8 guarded shadow canary — GPU execution, FAILED CLOSED at canary execution

Controlling status:

`OFFICIAL_SHADOW_ATTEMPT_FAILED_CLOSED_AT_CANARY_EXECUTION / MODEL_LOAD_FIX_VALIDATED_IN_OFFICIAL_RUN / FULL_MEASUREMENT_RAN_212_ARTIFACTS_PRODUCED / AUTOGRAD_CALL_CONTRACT_UNMET_0_OF_1248 / SHADOW / NONE / NOT_LICENSED`

## What this run proves

Attempt 8 (commit `88b59de9`, run `jlcv1-rfc3161-77097e7b...`) applied the
confirmed `model_snapshot_root` correction (HF cache snapshot path) and ran
the full ceremony + guarded canary. It advanced TWO stages past Attempt 7:

- `MODEL_LOAD` now PASSES (the config fix is validated in the official run);
- the canary executed the FULL measurement and produced 212 real artifact
  files in `output/`: all 8 functional baseline logits
  (`functional-baseline-logits-r0..r7`) and every jvp/vjp matrix for all 8
  block ranks across source layers 3/6/9
  (`jvp-matrix-rN-lL.casf32`, `vjp-matrix-rN-lL.casf32`).

The seccomp phase-two guard (Attempt 7 fix), CUDA execution, model load
(Attempt 8 fix), block selection, norm capture, and the Jacobian matrix
estimation all ran. This is by far the deepest any attempt has reached.

It is NOT a technical-canary pass: wrapper exit `0`, producer status
`FAILED_CLOSED`, execution receipt
`e0a9221634f05402355e373616fddc58b9932e032c377885ce1815dfc09e32c0`, failure
stage `CANARY_EXECUTION` (`CANARY_EXECUTION_FAILURE`). Claim status
`SHADOW / NONE / NOT_LICENSED`, score `0.33`.

## The failure, precisely characterized

The receipt records `CANARY_EXECUTION` failure with the autograd-call
accounting at `observed_total = 0` of the contract `1248`, while all 212
measurement artifacts were produced. The failure is a generic
`NON_SUBPROCESS_FAIL_CLOSED` (empty stderr; the inner exception text is not
serialized, by the bounded-evidence contract — the retained
`failure_detail_sha256` `764c85a7...` is the generic non-subprocess record
hash, not exception-specific).

CORRECTED FINDING (a first hypothesis was tested and DISPROVEN): the first
guess was that the harness's `TaggedAutogradGradCounter` failed to
intercept jlens's `torch.autograd.grad`. A direct on-pod probe
(`attempt8_counter_probe.py`) DISPROVES that — the counter works: one
`jlens.fitting.jacobian_for_prompt` call is correctly counted as exactly
`96` `MATRIX_ESTIMATOR` grad calls (`d_model 768 / dim_batch 8 = 96`), with
`jlens.fitting.torch is torch` and `torch.autograd.grad` observed patched
to `counted_grad` inside the scope. Therefore the `observed_total = 0` in
the FAILURE receipt is a failure-path reporting DEFAULT (the live counts
are only threaded into a SUCCESS receipt), NOT the cause of the failure.

The exact exception is now CAPTURED by a faithful full reproduction
(`attempt8_faithful_repro.py`, which wraps the lens in `ExactTokenLensModel`
exactly as the runner does and produces the same 212 artifacts before
failing):

`CanaryContractError: functional analytic derivative differs from prepared
gradient norm` — raised at
`research/jacobian_lens_canary_torch.py:673` inside
`output_functional_measurements`.

This is the final SCIENTIFIC cross-check of the canary, not an
instrumentation or config failure. For each functional measurement the
harness compares two independent derivatives:
- `gradient_norm` — reverse-mode (`torch.autograd.grad`), prepared earlier;
- `analytic` — forward-mode (`torch.autograd.functional.jvp`, `strict=True`).
It requires `scalar_relative_error(analytic, gradient_norm)` <=
`GRADIENT_ANALYTIC_RELATIVE_ERROR_LIMIT = 1e-4`
(`jacobian_lens_canary_core.py:57`).

Instrumented magnitudes on the pinned stack (torch 2.12.0+cu130, CUDA 13.0,
A40, float32; `attempt8_instrument.py`): the last three measured
comparisons were relative error `9.62e-6`, `3.86e-6`, and `1.5128e-4`. The
third exceeds the `1e-4` limit — `analytic = 0.2004186809` vs
`gradient_norm = 0.2004490048`, i.e. agreement to four significant figures,
`1.5x` over a very tight gate. Forward-mode and reverse-mode float32 GPU
autodiff legitimately diverge at roughly this scale, and the `1e-4` limit
was evidently calibrated on a different (tighter) stack. Two of three
measurements passed; one measurement is ~15-40x looser than the others.

FULL DISTRIBUTION (shadow diagnostic `attempt8_distribution.py`, which
raises the limit so the gate records instead of fail-closing, across all
functional measurements on the pinned stack): of 40 forward-vs-reverse
comparisons, relerr min `1.18e-6`, median `1.07e-4`, MAX `4.24e-3`; 20 of
40 exceed `1e-4`, 10 exceed `5e-4`, and 5 exceed `1e-3`. A SECOND
analytic-vs-gradient gate (message "differs from gradient norm", distinct
from the "prepared gradient norm" one) also fails even with the first
relaxed.

So this is NOT one borderline measurement — the forward-mode
(`torch.autograd.functional.jvp`) and reverse-mode (`torch.autograd.grad`)
derivatives of the same quantity SYSTEMATICALLY disagree at the `1e-4` to
`4e-3` level on torch 2.12.0+cu130 / CUDA 13.0 / A40 / float32. Agreement
to only 2-3 significant figures (max `4.24e-3`) is large for float32 and
warrants a numerical-methods look before any threshold change: candidates
include ill-conditioning of specific measurement directions, forward-mode
jvp accuracy on this stack, residual TF32/algorithm nondeterminism despite
the deterministic settings, or the `1e-4` limit having been calibrated for
a tighter stack (e.g. float64 or torch 2.4/CUDA 12.4). Simply widening
`GRADIENT_ANALYTIC_RELATIVE_ERROR_LIMIT` to ~`5e-3` to pass all 40 would
make it a weak agreement check (2 significant figures) and materially
weaken the scientific claim — it must NOT be silently loosened to force a
pass.

This is an OWNER SCIENTIFIC DECISION with two branches: (a) investigate the
forward-vs-reverse divergence (conditioning / float64 jvp / stack) and, if
it is genuine float32-GPU autodiff behavior, set the threshold from the
empirical distribution with recorded justification; or (b) treat the
divergence as a real numerical defect to fix in the measurement before the
canary can honestly PASS. Either branch is a change to the frozen
implementation requiring tests, a full-suite pass, a fresh implementation
freeze, and a fresh Attempt 9 identity. Attempt 1-8 identities are never
reused.

Note the difference from a bounded local reproduction (`attempt8_canaryexec_diag.py`):
that diagnostic failed earlier, at `_validate_input_ids` on the first
block, because it loaded the token manifest via `load_manifest` (raw frozen
file) rather than the preflight-built manifest the official runner uses.
That is a diagnostic-harness artifact, NOT the official failure; the
official run passed `_validate_input_ids` for all 8 blocks (it produced the
per-block artifacts). A faithful reproduction must build the manifest
exactly as the preflight does.

## Next executable action

Faithfully reproduce the canary-execution path with the preflight-built
token manifest to capture the exact `CANARY_EXECUTION` exception, then
reconcile the `1248`-call autograd accounting contract with the pinned
jlens gradient path (either intercept the exact callable jlens uses, or
correct the expected-count contract to match the real call pattern). This
touches the measurement-accounting trust surface, so it is a code change
requiring tests, a full-suite pass, a fresh implementation freeze, and a
fresh Attempt 9 identity. Attempt 1-8 identities are never reused. A clean
official canary PASS earns Gate 1 (`0.38`).

## Float32-vs-float64 investigation (decisive, 2026-07-24)

Reproduced the exact failing measurements at both precisions
(`attempt8_conditioning_test.py`, real frozen blocks via
`ExactTokenLensModel`; `attempt8_precision_test.py` on synthetic input):

- `r7/l6` — the exact measurement that failed the official run
  (`gradient_norm = 0.2004`, matching the receipt): relerr float32
  `1.513e-4`, float64 `4.013e-7`. Float64 fixes it (~378x). This failure IS
  float32 rounding.
- `r7/l3`: relerr float32 `1.450e-4`, float64 `1.816e-4` — float64 does NOT
  help. A small residual forward-vs-reverse method difference that is not
  precision-limited.
- All measured top1-vs-top2 logit gaps are `0.87`-`5.16` (healthy, NOT
  near-ties), so the disagreement is NOT a degenerate/near-tie artifact.
- Well-conditioned measurements agree to ~`1e-5` in both precisions;
  float64 gives no systematic global improvement (0.5x-4.1x on synthetic
  input).

Conclusion: the forward-vs-reverse cross-check disagreement is a MIX of
float32 rounding (curable to ~`1e-7` by float64 for some measurements) and
a small inherent forward-mode-jvp vs reverse-mode-grad method floor (~`1e-4`
that persists at float64 for other measurements). The values agree to 4+
significant figures throughout; this is NOT a gross defect and NOT a
degeneracy. The `GRADIENT_ANALYTIC_RELATIVE_ERROR_LIMIT = 1e-4` gate is
simply tighter than this cross-check method can reliably achieve for all
measurements on the pinned torch 2.12 / CUDA 13 / float32 stack.

Owner decision, now fully evidence-based:
(a) run the functional cross-check in float64 (fixes the precision-limited
    cases; a measurement-code change), and/or
(b) recalibrate the limit to the empirical forward-vs-reverse floor on this
    stack (the full distribution's max was `4.24e-3`), recorded with this
    justification.
Either is a change to the frozen implementation -> tests, full-suite pass,
fresh freeze, fresh Attempt 9 identity. It must be an explicit scientific
decision, not a silent loosening.

## Full float32-vs-float64 distribution — float64 alone does NOT achieve a pass (2026-07-24)

Across all 24 primary functional analytic-vs-gradient measurements
(8 blocks x source layers 3/6/9; `attempt8_full_f64.py`):
- float32: min `3.88e-7`, median `9.62e-6`, max `1.51e-4`; 2 of 24 over `1e-4`.
- float64: min `2.83e-8`, median `7.86e-6`, max `1.82e-4`; 1 of 24 over `1e-4`.

CONCLUSION: float64 is NOT sufficient on its own — a residual
forward-vs-reverse method floor of ~`1.8e-4` persists at double precision on
the worst measurement (`r7/l3`), still exceeding the `1e-4` gate. (The fuller
comparison set including per-dose/second-gate checks reaches `4.24e-3`.)
Therefore a clean canary PASS is NOT reachable by a precision strengthening
alone; it genuinely requires recalibrating
`GRADIENT_ANALYTIC_RELATIVE_ERROR_LIMIT` to the empirical forward-vs-reverse
floor on this stack (documented), which is a SCIENTIFIC ACCEPTANCE
THRESHOLD change and therefore an explicit owner decision — it will not be
made silently to satisfy a score target.

## Method x precision matrix — NO clean fix reaches the 1e-4 gate (2026-07-24, conclusive)

Also tested a true forward-mode jvp (`torch.func.jvp`) as an alternative to
the harness's double-backward `torch.autograd.functional.jvp`
(`attempt8_jvpmethod.py`, `attempt8_fwdmode_full.py`). Max forward-vs-reverse
relerr across the 24 primary functional measurements:
- double-backward jvp, float32: `1.51e-4` (2 over `1e-4`)
- double-backward jvp, float64: `1.82e-4` (1 over)
- forward-mode jvp,   float32: `1.36e-4` (2 over)
- forward-mode jvp,   float64: `2.19e-4` (1 over)

CONCLUSIVE: no precision (float32/float64) and no jvp method
(double-backward/forward-mode) brings ALL measurements under the `1e-4`
gate. The forward-vs-reverse agreement floor is inherently ~`1.4e-4` to
`2.2e-4` for Pythia-160m on torch 2.12 / CUDA 13 — the two autodiff paths
genuinely do not agree to 4+ significant figures for every measurement.
The values are correct (agree to 3-4 sig figs); the `1e-4` acceptance gate
is simply tighter than this cross-check can achieve on this model/stack.

Therefore a canary PASS requires recalibrating
`GRADIENT_ANALYTIC_RELATIVE_ERROR_LIMIT` to the empirical floor (e.g. `1e-3`,
which clears the ~`2.2e-4` worst case with margin while still requiring
3-sig-fig forward-vs-reverse agreement), recorded with this evidence. This
is a SCIENTIFIC ACCEPTANCE THRESHOLD change — the owner's decision — and
will not be made silently to satisfy a score target. Recommended: set the
limit to `1e-3` with the above justification, optionally move the
cross-check to float64 as a strengthening, then Attempt 9.
