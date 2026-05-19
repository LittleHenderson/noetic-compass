# Stage 19C Verification Mode Selector Spec

Date: 2026-05-19

Branch: `experiment/cas-probe-pythia`

Status: `MODE_SPEC_BEFORE_PACKET_UPDATE`

## Purpose

Stage 19C converts the Stage 19B cross-architecture result into a user-facing
mode selector.

This is not a fresh statistical test. Stage 19B already produced the measured
component ladder:

1. ensemble-only,
2. factor-consistent,
3. final trace-stability stack.

Stage 19C names those existing operating points as explicit product modes so a
reviewer or customer can choose the risk profile instead of receiving one hidden
threshold setting.

Default customer mode:

`BALANCED`

Rationale:

> `BALANCED` meets the Stage 19B coverage floor (`>= 0.800`) on both OLMo and
> Qwen while preserving the Drive/Register factor-decomposition agreement gate.
> `HIGH_PRECISION` is opt-in for regulator, legal, and safety workflows.
> `MAX_COVERAGE_TRIAGE` is opt-in for human-review queues.

## Locked Input

- `stage19b_cross_arch_foundation_verification_stack_20260519.json`

## Modes

### `HIGH_PRECISION`

Source component:

- final Stage 19B stack
- Foundation ensemble agreement
- Drive/Register factor consistency
- Foundation trace stability

Product use:

- regulator review
- legal or safety-sensitive audit
- cases where a suppression is better than a wrong accepted answer

Expected behavior from Stage 19B:

- lower coverage
- highest accepted accuracy
- lowest silent error

Mode target:

- accepted accuracy `>= 0.980`
- silent error rate `<= 0.020`
- no coverage floor

### `BALANCED`

Source component:

- Stage 19B factor-consistent layer
- Foundation ensemble agreement
- Drive/Register factor consistency
- no trace-stability suppression

Source verification:

> `factor_consistent` is the Stage 19B component that requires 2-of-3
> Foundation readout consensus, independently requires Drive and Register
> readout consensus, recomposes Drive x Register into the 28-way Foundation
> index, and suppresses rows as `factor_conflicted` when the recomposed label
> does not match the Foundation consensus.

Product use:

- normal customer audit flow
- cases where throughput matters but unsupported conflicts should still be
  suppressed

Mode target:

- coverage `>= 0.800`
- accepted accuracy `>= 0.940`
- silent error rate `<= 0.060`

### `MAX_COVERAGE_TRIAGE`

Source component:

- Stage 19B ensemble-only layer
- Foundation ensemble agreement
- no factor-consistency suppression
- no trace-stability suppression

Product use:

- exploratory triage
- batch review queues
- cases where broad surfacing is useful and human review remains expected

Mode target:

- coverage `>= 0.880`
- accepted accuracy `>= 0.880`

Boundary:

`MAX_COVERAGE_TRIAGE` is not a licensed high-confidence claim mode. It is a
triage mode.

## Output

The Stage 19C artifact must report, per model and mode:

- accepted count when available
- accepted accuracy
- coverage
- silent error rate
- suppressed rate
- target status
- recommended use

It must also report an overall cross-architecture status per mode:

- `MODE_SUPPORTED_CROSS_ARCH` when every tested model meets that mode target.
- `MODE_PARTIAL` when at least one model meets the target and at least one does
  not.
- `MODE_NOT_SUPPORTED` when no tested model meets the target.

## Required Product Boundary

Allowed:

> CAS Verification Stack exposes user-selectable operating modes. On the
> locked OLMo/Qwen Stage 19B artifacts, high-precision mode accepts fewer
> examples at 98-99.5% accuracy, balanced mode restores >80% coverage at
> 94-96.6% accuracy, and triage mode maximizes coverage with lower confidence.

Allowed:

> New customers default to `BALANCED`. `HIGH_PRECISION` is an opt-in trust mode
> and `MAX_COVERAGE_TRIAGE` is an opt-in review-queue mode.

Disallowed:

> Stage 19C makes every mode product-certified.

Disallowed:

> Users can choose accuracy without tradeoffs.
