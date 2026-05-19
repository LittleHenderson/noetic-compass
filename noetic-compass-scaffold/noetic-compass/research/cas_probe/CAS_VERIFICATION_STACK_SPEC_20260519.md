# CAS Verification Stack Spec

Date: 2026-05-19

Status: `STAGE19A_PASS_STRONG_AUDIT_CLEAN`

## Executive Summary

The CAS Verification Stack is the next product-grade layer on top of CAS
Harness. It does not replace the probe. It wraps the probe with independent
checks so the system can say:

> accepted, medium confidence, conflicted, structurally unsupported, or
> suppressed.

The goal is not 100% prediction. The goal is to convert hidden errors into
visible evidence states.

## Stage 19A Result

Stage 19A ran on the locked Stage 12 formula-family fixture using the existing
Stage 12 activation artifact on the pod.

Status:

`PASS_STRONG_AUDIT_CLEAN`

Headline:

| Metric | Value |
|---|---:|
| Baseline `focus_token` layer-12 accuracy | `0.9540` |
| Ensemble-only accuracy | `0.9550` |
| Ensemble-only coverage | `0.9569` |
| Stack accepted accuracy | `0.9978` |
| Stack coverage | `0.8760` |
| Stack silent error rate | `0.0022` |
| Stack suppressed rate | `0.1240` |
| Accepted examples | `3679/4200` |
| Suppressed examples | `521/4200` |
| Silent accepted errors | `8/3679` |

Product read:

> On this locked formula-family fixture, the runtime-safe verifier accepted
> 87.6% of examples at 99.78% accuracy and suppressed the remaining 12.4% as
> conflicted or unstable.

Audit-clean rerun:

> The initial gates and runner were written before the first pod run but not
> committed before execution. After commit `05ac687`, Stage 19A was rerun with
> the same script, same fixture, and same activation artifact. The rerun
> reproduced every headline metric exactly, resolving the caveat.

## Architecture

```text
activation snapshot
  |
  v
multi-readout probes
  |
  v
factor consistency checks
  |
  v
structural admissibility gates
  |
  v
trace stability classifier
  |
  v
verified prediction + confidence + caveats
```

## Layer 1: Multi-Readout Probes

For Stage 19A formula-family verification:

| Readout | Layer | Prior test accuracy |
|---|---:|---:|
| `focus_token` | 12 | `0.9540` |
| `final_token` | 7 | `0.9186` |
| `mean_over_seq_len` | 5 | `0.6752` |

Rule:

- two or three agree -> ensemble candidate.
- all disagree -> `CONFLICTED`.
- confidence margin required for correction, otherwise suppress.

Reason:

> A single probe can be right for the wrong reason. Agreement across readout
> positions is stronger evidence than one logit head alone.

## Layer 2: Factor Decomposition

For Foundation labels only:

| Factor | Prior result |
|---|---|
| Drive | `0.8907`, +22.3 pp over text, ablation to chance |
| Register | `0.8563`, readout-causal but text-explained |
| 28-way interaction | `0.7857`, +28.9 pp over text, ablation to chance |

Rule:

- Drive + Register can recompose a 28-way Foundation candidate.
- If recomposition disagrees with the 28-way probe, compare calibrated
  confidence.
- If confidence is not decisive, suppress as `FACTOR_CONFLICTED`.

Caveat:

> Register is useful as a consistency signal in this fixture, but Stage 7.2
> does not support Register as a beyond-text claim.

## Layer 3: Structural Admissibility

Structural gates must be deterministic.

Allowed output:

```json
{
  "rule_id": "register_multiplicity_named_omega",
  "status": "fail",
  "evidence": "same-noetic multi-register product lacks named emergent result",
  "replacement_label": null
}
```

Not allowed:

- vague "provably wrong" labels without a validator result.
- nearest-label correction without a deterministic distance metric.
- Dk, domain descent, or RPM claims when the expression does not expose the
  needed formal structure.

## Layer 4: Trace Stability Confidence

Stage 13 provides oracle trace classes for evaluation:

| Trace class | Product action |
|---|---|
| `stable_correct` | report-only validation label |
| `early_correct_then_drift` | report-only validation label |
| `late_emerging_correct` | report-only validation label |
| `stable_wrong` | report-only validation label |
| `conflicted` | report-only validation label |
| `uncertain` | report-only validation label |

Runtime acceptance cannot use labels that require knowing the answer. The
runtime trace states are:

| Runtime trace state | Meaning |
|---|---|
| `stable` | one label dominates at least 70% of layers and persists for at least 5 layers |
| `uncertain` | at least half of layers are low-confidence or high-entropy |
| `conflicted` | at least 5 switches or no majority over half the layers |
| `drifting` | signal changes over depth without crossing the conflict threshold |

Runtime rule:

- high confidence: ensemble agrees and `focus_token` trace is stable on that
  same label.
- medium confidence: ensemble agrees and at least two readout traces are stable
  on that same label.
- suppress: all-disagree ensemble, uncertain trace, conflicted trace, or
  unstable agreement.

Known Stage 13 aggregate:

- stable-like: `77.7%`
- problem-like: `22.3%`

Known Stage 13 best readout:

- `focus_token` layer 12, test accuracy `0.9540`, lacunarity `0.0016`.

## Product Meaning

Without the stack:

> CAS Harness gives a strong prediction and evidence packet.

With the stack:

> CAS Harness gives a verified prediction, confidence tier, and suppression
> reason when the evidence is unstable.

That is a major product upgrade because reviewers do not only see what CAS
thinks the label is. They see why CAS accepts, caveats, or refuses the label.

## Claim Boundary

Supported after implementation and passing gates:

- accepted-prediction accuracy,
- coverage,
- silent error rate,
- structured suppression reasons,
- rule-level structural gate results.

Not supported without further evidence:

- 100% accuracy,
- exact causal-neuron identification,
- host-model internal compiler execution,
- exact free-form output control.

## Next Build Step

Implement Stage 19A first.

Reason:

- It can likely run offline from existing Stage 13 artifacts.
- It tests the ensemble and trace-stability parts of the stack without new GPU.
- It avoids mixing Foundation factor claims with formula-family trace claims.

Only after Stage 19A is clean should Stage 19B add Drive/Register
recomposition on the Stage 7 Foundation fixture.
