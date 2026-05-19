# CAS Verification Stack Spec

Date: 2026-05-19

Status: `STAGE19C_MODE_SELECTOR_READY`

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

## Stage 19B Cross-Architecture Result

Stage 19B reran the runtime-safe Verification Stack on OLMo-1B and
Qwen2.5-1.5B Foundation fixtures. Gold labels were used only after acceptance
for scoring.

Report status:

`NULL`

Practical verdict:

`DIAGNOSTIC_ONLY_CROSS_ARCH`

| Model | Best single | Stack accepted acc | Coverage | Silent error | Suppressed |
|---|---:|---:|---:|---:|---:|
| OLMo-1B | `0.9060` | `0.9816` | `0.7173` | `0.0184` | `0.2827` |
| Qwen2.5-1.5B | `0.8537` | `0.9949` | `0.7457` | `0.0051` | `0.2543` |

Boundary:

> Stage 19B did not pass the pre-registered `0.800` coverage floor for a
> high-coverage cross-architecture product gate. It did pass the practical
> diagnostic test: accepted examples remain very precise on both architectures.

## Stage 19C User-Selectable Modes

Stage 19C packages the Stage 19B precision/coverage ladder as explicit product
modes. This is not a new hidden-state experiment and does not rewrite Stage
19B's strict-gate `NULL`. It exposes the tradeoff to the user.

| Mode | Intended use | OLMo acc / coverage / silent error | Qwen acc / coverage / silent error |
|---|---|---:|---:|
| `HIGH_PRECISION` | Regulator, legal, safety, and high-trust review where suppression is preferred over a wrong accepted answer. | `0.9816 / 0.7173 / 0.0184` | `0.9949 / 0.7457 / 0.0051` |
| `BALANCED` | Normal customer audit flow where throughput matters but factor conflicts should still be suppressed. | `0.9422 / 0.8240 / 0.0578` | `0.9661 / 0.8274 / 0.0339` |
| `MAX_COVERAGE_TRIAGE` | Exploratory triage and batch review queues where human review remains expected. | `0.8975 / 0.9039 / 0.1025` | `0.9281 / 0.8988 / 0.0719` |

Runtime product rule:

- Default new customers to `BALANCED`.
- Allow users to choose `HIGH_PRECISION` when trust is more important than
  throughput.
- Reserve `MAX_COVERAGE_TRIAGE` for queue-building and human review, not final
  high-confidence claims.

Source verification:

> `factor_consistent` was checked against the Stage 19B runner source. It first
> requires Foundation ensemble consensus, then independently requires Drive and
> Register consensus, recomposes Drive x Register into the 28-way Foundation
> label, and suppresses rows as `factor_conflicted` when recomposition disagrees
> with the Foundation prediction.

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

With Stage 19C modes:

> CAS Harness lets the user choose the verifier operating point. The product
> exposes precision, coverage, silent-error, and suppression tradeoffs instead
> of pretending one threshold profile fits every audit.

Default:

> `BALANCED`, because it restores `>= 0.800` coverage on both OLMo and Qwen
> while preserving factor-decomposition agreement.

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

Implement the mode selector in the CAS Harness product surface.

Required fields:

- `verification_mode`
- `mode_profile`
- `accepted`
- `decision_tier`
- `suppression_reasons`
- `accepted_accuracy`, `coverage`, and `silent_error_rate` for the selected
  mode/model profile

The UI must show the tradeoff before the user runs or exports a packet.
