# Stage 20 Generation Readiness Gate Spec

Date: 2026-05-19

Branch: `experiment/cas-probe-pythia`

Status: `IMPLEMENTED_CPU_TESTED`

## Purpose

Stage 20 implements the safe version of the TKS valve idea for CAS Harness and
CAS-Native.

The old Phase 3 valve lineage is real prior work, but it is also a warning:
`PHASE3_VALVE_REPORT.md` records that learned multiplicative gates collapsed
generation by suppressing output. Stage 20 therefore does **not** port old
checkpoints, and it does **not** scale `bottleneck_z`, logits, hidden states, or
language-head tensors.

Instead, Stage 20 adds a diagnostic **Generation Readiness Gate**. It reads
existing CAS evidence and returns an auditable policy:

- `allow`
- `caveat`
- `constrain`
- `suppress`

This makes the valve a runtime safety and product-decision layer, not an
unseen neural choke point.

## Implementation

New module:

- `cas-native/model/generation_readiness_gate.py`

Exports:

- `GenerationReadinessConfig`
- `GenerationReadinessGate`
- `GenerationReadinessResult`
- mode constants: `HIGH_PRECISION`, `BALANCED`, `MAX_COVERAGE_TRIAGE`
- action constants: `allow`, `caveat`, `constrain`, `suppress`

CASNativeModel integration:

- `attach_generation_readiness_gate(gate)`
- `assess_generation_readiness(outputs, verification=None, mode=None)`

Boundary:

> `forward()` and `forward_with_lm()` are unchanged. The gate is only invoked
> when a caller explicitly calls `assess_generation_readiness`.

## Inputs

The gate consumes already-computed diagnostic signals:

- `lacunarity_scores`
- `lacunarity_meta.lacunarity`
- `lacunarity_meta.gap_map`
- `lacunarity_meta.domain_confidence`
- `inversion_flags`
- `rpm_satisfaction`
- optional Verification Stack decision:
  - `accepted`
  - `decision_tier`
  - `suppression_reasons`

It is compatible with the Stage 19C mode selector. Default mode is
`BALANCED`.

## Policy

The policy is deterministic and mode-aware:

| Mode | Caveat | Constrain | Suppress |
|---|---:|---:|---:|
| `HIGH_PRECISION` | `>= 0.20` | `>= 0.45` | `>= 0.75` |
| `BALANCED` | `>= 0.25` | `>= 0.55` | `>= 0.85` |
| `MAX_COVERAGE_TRIAGE` | `>= 0.30` | `>= 0.65` | `>= 0.95` |

Evidence sources add risk:

- high lacunarity
- high gap probability
- low domain confidence
- inversion flags
- low RPM satisfaction
- Verification Stack rejection or non-high-confidence tier

Verification Stack rejection is treated strongly:

- `HIGH_PRECISION` and `BALANCED`: `suppress`
- `MAX_COVERAGE_TRIAGE`: `constrain`

This preserves the Stage 19C product split: triage may still surface a
candidate, but it is not a high-confidence license-grade claim.

Medium/diagnostic accepted predictions are treated as a caveat-level signal in
`HIGH_PRECISION` and `BALANCED`. They remain accepted, but the packet should
tell the reviewer that the readout did not reach the high-confidence tier.

## Output

The gate returns a JSON-serializable packet:

```json
{
  "generation_readiness": "allow",
  "risk_score": 0.0,
  "reasons": ["all_readiness_signals_within_mode_thresholds"],
  "recommended_mode": "BALANCED",
  "mode": "BALANCED",
  "evidence": {
    "mode": "BALANCED",
    "verification_accepted": true,
    "max_lacunarity": 0.1,
    "max_gap_probability": 0.05,
    "mean_gap_probability": 0.05,
    "min_domain_confidence": 0.9,
    "inversion_flag_count": 0,
    "rpm_satisfaction": 0.95
  },
  "policy_version": "stage20_generation_readiness_gate_v1"
}
```

## What This Is Not

Stage 20 is not:

- a port of `valve_v2_final.pt`
- a learned valve controller
- hidden-state steering
- free-form output control
- a replacement for the Verification Stack

It is a product-safe boundary layer over the Verification Stack, lacunarity,
inversion, and RPM diagnostics.

## Tests

CPU tests:

```text
python -m py_compile \
  cas-native/model/generation_readiness_gate.py \
  cas-native/model/cas_native_model.py \
  cas-native/model/__init__.py

python -m pytest \
  cas-native/tests/model/test_generation_readiness_gate.py

python -m pytest \
  cas-native/tests/test_model.py \
  cas-native/tests/model/test_nl_generation_head.py::test_cas_native_model_forward_unchanged_without_lm_head \
  cas-native/tests/model/test_nl_generation_head.py::test_cas_native_model_forward_with_lm_returns_both_outputs
```

Result:

- `7 passed` for the new gate tests
- `16 passed` for the CASNativeModel regression slice

## Product Read

Stage 20 turns the old "valve" intuition into a deployable CAS Harness control
surface:

> CAS does not silently choke generation. CAS reports whether generation is
> supported, caveated, constrained, or suppressed, and records the exact
> structural reasons for that decision.

This is the right boundary for Glass House: transparent, auditable, configurable
by Stage 19C mode, and resistant to the old valve-collapse failure mode.
