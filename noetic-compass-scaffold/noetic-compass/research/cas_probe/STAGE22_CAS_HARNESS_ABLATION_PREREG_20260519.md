# Stage 22 CAS Harness Ablation Pre-Registration

**Status:** `PREREGISTERED_NO_GPU`

## Scope

Stage 22 ablates the external **CAS Harness** product around frozen open-weight model artifacts.
It does not ablate the future CAS Native inner loop. That later work should be named
**CAS Native Cognitive Runtime**, not CAS Harness, to avoid product ambiguity.

## Naming Boundary

| Term | Meaning |
|---|---|
| `cas_harness` | External inspection/conditioning product around open-weight models. |
| `cas_native_cognitive_runtime` | Future from-scratch CAS Native inner loop; not Stage 22. |

## Conditions

| Mode | Status | Active layers | Hypothesis | Boundary |
|---|---|---|---|---|
| `floor_raw_model` | `executable_now` | frozen_model_logits | Defines the no-harness floor for likelihood and output-quality metrics. | No CAS claims attach to this condition; it is a comparator. |
| `cpl2_bridge_only` | `executable_now` | frozen_model_logits, eta_probe_readout, epsilon_readable_prefix | Readable realization should shift semantic likelihood without safety layers. | Likelihood conditioning only; not visible-text control. |
| `mode_selector_balanced` | `executable_now` | frozen_model_logits, eta_probe_readout, epsilon_readable_prefix, verification_stack, mode_selector | Default customer mode should recover coverage while preserving factor consistency. | Balances precision and coverage; not a high-precision legal mode. |
| `mode_selector_high_precision` | `executable_now` | frozen_model_logits, eta_probe_readout, epsilon_readable_prefix, verification_stack, mode_selector | High-precision mode should minimize silent error at the cost of coverage. | Opt-in regulator/legal/safety mode. |
| `mode_selector_max_coverage_triage` | `executable_now` | frozen_model_logits, eta_probe_readout, epsilon_readable_prefix, verification_stack, mode_selector | Triage mode should maximize coverage for human-review queues while carrying a lower-confidence boundary. | Opt-in review-queue mode only; not a licensed high-confidence claim mode. |
| `readiness_balanced` | `executable_now` | frozen_model_logits, eta_probe_readout, epsilon_readable_prefix, verification_stack, mode_selector, generation_readiness_gate | Readiness policy should convert unsafe accept/suppress outcomes into useful allow/caveat/constrain/suppress decisions. | Policy packaging over existing signals; does not change host-model weights. |
| `evidence_packet_full` | `executable_now` | frozen_model_logits, eta_probe_readout, epsilon_readable_prefix, verification_stack, mode_selector, generation_readiness_gate, evidence_packet_export, atlas_trace_linkage | Full audit surface should maximize reviewer reproducibility, not necessarily raw output quality. | Audit completeness is a product metric separate from model accuracy. |
| `frontier_llm_ceiling` | `reference_only` | external_frontier_model | Provides a non-CAS quality ceiling for the same prompts/tasks. | Not a CAS mechanism and not comparable as a weight-level intervention. |

## Metrics

| Metric | Direction | Why it is required |
|---|---|---|
| `useful_output_rate` | `higher_is_better` | Prevents rewarding a harness that suppresses everything safely. |
| `unsupported_output_rate` | `lower_is_better` | Measures hallucinated or unsupported emission after the harness decision. |
| `accepted_accuracy` | `higher_is_better` | Precision of accepted per-example decisions when gold labels exist. |
| `coverage` | `higher_is_better` | Fraction of examples receiving an accepted or useful constrained decision. |
| `suppression_rate` | `report_only` | Interpretable only alongside useful_output_rate. |
| `cpl2_delta` | `higher_is_better` | Likelihood shift from eta-to-epsilon readable prefix conditioning. |
| `evidence_packet_completeness` | `higher_is_better` | How completely the run can be audited by a reviewer. |
| `latency_ms` | `lower_is_better` | Runtime cost of the harness condition. |

## Required Discipline

- Report floor and ceiling comparators; do not interpret a harness number alone.
- Pair suppression rate with useful-output rate and coverage.
- Treat `BALANCED` as the default customer mode unless Stage 22 data overturns it.
- Treat `HIGH_PRECISION` as opt-in for regulator/legal/safety workflows.
- Treat `MAX_COVERAGE_TRIAGE` as opt-in for human-review queues.
- Do not claim visible free-form generation control from likelihood-only evidence.

## Validation

- `floor_raw_model`: valid
- `cpl2_bridge_only`: valid
- `mode_selector_balanced`: valid
- `mode_selector_high_precision`: valid
- `mode_selector_max_coverage_triage`: valid
- `readiness_balanced`: valid
- `evidence_packet_full`: valid
- `frontier_llm_ceiling`: valid

## Claim Boundary

Stage 22 tests harness contribution and tradeoffs. Suppression rate is never interpreted without useful_output_rate and coverage.
