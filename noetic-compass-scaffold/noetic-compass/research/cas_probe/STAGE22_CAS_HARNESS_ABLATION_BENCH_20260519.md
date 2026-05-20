# Stage 22 CAS Harness Ablation Bench

**Status:** `STAGE22_NO_GPU_ABLATION_BENCH_COMPLETE`

## Headline

| Layer | Status | Key result |
|---|---|---|
| Raw floor | `MEASURED_FROM_CPL2_NONE_CONDITION` | no-prefix mean margin `0.0498` |
| Eta-to-epsilon bridge | `SUPPORTED_ACROSS_LOCKED_MODELS` | mean CPL2 delta `0.5640`, range `0.2828` to `0.7960`, positives `433/560` |
| BALANCED selector | `MODE_SUPPORTED_CROSS_ARCH` | mean coverage `82.6%`, mean accepted accuracy `95.4%` |
| HIGH_PRECISION selector | `MODE_SUPPORTED_CROSS_ARCH` | mean accepted accuracy `98.8%`, mean coverage `73.2%` |
| Evidence Packet surface | `EVIDENCE_PACKET_SURFACE_COMPLETE_FOR_CANONICAL_PACKETS` | `4/4` canonical packets complete |
| Frontier ceiling | `REFERENCE_ONLY_NOT_RUN` | not run in this no-GPU pass |

## CPL2 Bridge Rows

| Model | Delta vs none | Partner margin | Raw-symbol delta | Positive share |
|---|---:|---:|---:|---:|
| EleutherAI/pythia-160m | `0.2828` | `0.6829` | `-0.0011` | `0.723` |
| EleutherAI/pythia-1b | `0.5542` | `1.2460` | `-0.0227` | `0.804` |
| EleutherAI/pythia-2.8b | `0.5832` | `1.3363` | `0.0027` | `0.821` |
| allenai/OLMo-1B-hf | `0.6037` | `1.3047` | `0.0063` | `0.777` |
| Qwen/Qwen2.5-1.5B | `0.7960` | `1.6253` | `-0.0002` | `0.741` |

## Mode Selector

| Mode | Coverage | Accepted accuracy | Silent error | Suppressed | Product read |
|---|---:|---:|---:|---:|---|
| `BALANCED` | `82.6%` | `95.4%` | `4.6%` | `17.4%` | Normal customer audit flow where throughput matters but factor conflicts should still be suppressed. |
| `HIGH_PRECISION` | `73.2%` | `98.8%` | `1.2%` | `26.8%` | Regulator, legal, safety, and high-trust review where suppression is preferred over a wrong accepted answer. |

## Readiness Policy

Readiness is measured from Stage 20B policy counts. It turns verification outcomes into `allow`, `caveat`, `constrain`, or `suppress`; it does not rerun hidden-state inference.

| Source | Mode | Useful-output rate | Suppression rate |
|---|---|---:|---:|
| Pythia-160M formula fixture | `BALANCED` | `87.6%` | `12.4%` |
| Pythia-160M formula fixture | `MAX_COVERAGE_TRIAGE` | `100.0%` | `0.0%` |
| OLMo-1B | `BALANCED` | `71.7%` | `28.3%` |
| OLMo-1B | `MAX_COVERAGE_TRIAGE` | `100.0%` | `0.0%` |
| Qwen2.5-1.5B | `BALANCED` | `74.6%` | `25.4%` |
| Qwen2.5-1.5B | `MAX_COVERAGE_TRIAGE` | `100.0%` | `0.0%` |

## Boundary

Stage 22 measures harness-layer contribution over locked artifacts. It supports CAS Harness as an auditable wrapper stack; it does not claim weight modification, raw CAS-symbol understanding, or visible free-form generation control.
