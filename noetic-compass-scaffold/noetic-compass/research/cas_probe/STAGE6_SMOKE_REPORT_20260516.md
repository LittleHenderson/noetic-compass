# Stage 6.1 Smoke Report - Role-Bound Activation Probe Mechanics

**Status:** Mechanics smoke only. Not a scientific verdict.  
**Date:** 2026-05-16  
**Branch:** `experiment/cas-probe-pythia`

## Purpose

Stage 6.1 verifies that the Stage 6 role-bound pilot can flow through the Pythia activation pipeline and a probe/text-baseline evaluator.

This is the first run using the Stage 6 readout design:

- focus-token residual stream
- final-token residual stream
- mean-over-sequence residual stream

## Artifacts

- `capture_stage6_role_bound_activations.py`
- `evaluate_stage6_role_bound_smoke.py`
- `stage6_role_bound_pilot_activations_20260516.npz`
- `stage6_role_bound_pilot_activations_manifest_20260516.json`
- `stage6_role_bound_pilot_smoke_report_20260516.json`

## Activation Capture

Command:

```powershell
python noetic-compass-scaffold\noetic-compass\research\cas_probe\capture_stage6_role_bound_activations.py --input stage6_role_bound_pilot_20260516.jsonl --out-activations stage6_role_bound_pilot_activations_20260516.npz --out-manifest stage6_role_bound_pilot_activations_manifest_20260516.json
```

Result:

| Field | Value |
|---|---:|
| Records | 100 |
| Layer positions | 13 |
| Hidden dim | 768 |
| `X_focus` shape | `(100, 13, 768)` |
| `X_final` shape | `(100, 13, 768)` |
| `X_mean` shape | `(100, 13, 768)` |
| Runtime | 8.0s CPU |

The `embed_out.weight` warning from Transformers is expected here. The script loads `GPTNeoXModel` for hidden states, not the LM head.

## Smoke Evaluation

Command:

```powershell
python noetic-compass-scaffold\noetic-compass\research\cas_probe\evaluate_stage6_role_bound_smoke.py --input stage6_role_bound_pilot_20260516.jsonl --activations stage6_role_bound_pilot_activations_20260516.npz --out-report stage6_role_bound_pilot_smoke_report_20260516.json
```

Split:

| Split | Rows | Per noetic |
|---|---:|---:|
| Train | 60 | 6 |
| Val | 20 | 2 |
| Test | 20 | 2 |

Text baselines:

| Baseline | Val acc | Test acc |
|---|---:|---:|
| Majority | 0.10 | 0.10 |
| Stratified dummy | 0.10 | 0.10 |
| Metadata focus-only | 0.10 | 0.10 |
| Count vector word 1-2 | 0.50 | 0.50 |
| TF-IDF word 1-2 | 0.50 | 0.50 |
| TF-IDF char 3-5 | 0.50 | 0.50 |

Activation readout headline results:

| Readout | Headline layer | Val acc | Test acc | Lift over best text |
|---|---:|---:|---:|---:|
| Focus token | 6 | 1.00 | 1.00 | +0.50 |
| Final token | 5 | 1.00 | 0.95 | +0.45 |
| Mean over sequence | 5 | 0.75 | 0.75 | +0.25 |

Paired focus-token vs best text baseline:

| Field | Value |
|---|---:|
| Best text baseline | TF-IDF word 1-2 |
| Both correct | 10 |
| Probe-only correct | 10 |
| Text-only correct | 0 |
| Both wrong | 0 |
| Exact binomial McNemar p | 0.00195 |

## Interpretation

This is a strong mechanics result, not a science claim.

Useful signs:

- Metadata focus-only is at chance (`0.10`), so the raw `Focus: A/B` marker alone does not solve the task.
- Focus-token layer 0 is at chance (`0.10`), so the embedding of the focus letter alone does not solve the task.
- Mid-layer focus-token and final-token readouts separate the role-bound labels much better than text baselines on this tiny pilot.

Hard caveats:

- The test set has only 20 rows, 2 per noetic.
- The same hand-authored template grammar exists across train/val/test.
- The pilot was built after seeing Stage 5 failures.
- No claim-bearing evaluation is allowed until the full Stage 6 fixture is generated, hashed, and locked before probe training.

Allowed wording:

> Stage 6.1 confirms the role-bound pipeline works mechanically. Focus-token activations can be captured and scored, and the pilot smoke produces above-text results on a tiny non-claim-bearing fixture.

Not allowed:

- Pythia encodes CAS.
- Stage 6 proves mechanistic CAS semantics.
- Glass House is confirmed.

## Next Step

Stage 6.2 should decide between:

1. Build the full 60-bundle locked fixture before more probe work.
2. First improve the pilot wording to reduce the 49 validator warnings and near-duplicate review items.
3. Add focus-token capture tests to pin token-index behavior before scaling.

My recommendation: add lightweight unit tests for focus-token indexing, then scale to the full 60-bundle fixture.

## Stage 6.1A Patch - Focus-Token Index Tests

The focus-token indexing path is now pinned by a local pytest module:

- `tests/test_stage6_focus_token.py`

The tests cover:

- terminal `Focus: A/B` marker selection instead of earlier `A`/`B` letters
- marker without a final period
- missing marker rejection
- declared-focus mismatch rejection
- invalid expected focus rejection
- direct token-offset mapping
- whitespace-prefixed token fallback
- unmappable offset rejection

Verification:

```powershell
python -m pytest noetic-compass-scaffold\noetic-compass\research\cas_probe\tests\test_stage6_focus_token.py -q
```

Result: `8 passed`.

After hardening the helper, the 100-row capture and smoke were rerun. Headline metrics reproduced:

- focus-token layer 6: `1.00`
- final-token layer 5: `0.95`
- mean-over-sequence layer 5: `0.75`
- best text baseline: `0.50`
