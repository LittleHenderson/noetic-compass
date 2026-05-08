# Wave 2.5 Deterministic-Lane Calibration Report

Date: 2026-05-08

Status: NUMERIC PASS; HUMAN REVIEW STILL REQUIRED

## What Changed

After the layer-3 filter showed that free-form generation still corrupted
regular compiler shapes, all ten Wave 2.5 grammar lanes now render
deterministically instead of calling Haiku:

- `state_literal`
- `binary_composition`
- `let_binding`
- `rpm_chain`
- `meta_logic_relation`
- `inversion`
- `fractal_sequence`
- `cross_register_omega`
- `recipe`
- `diagram_export`

The last patch moved `recipe` and `diagram_export` to deterministic renderers
because the 20260508T150305Z manual review found real axis corruption in the
remaining Haiku lanes:

- `recipe`: `|E` embodied register was rendered as the `^E` evaluative domain,
  and one sample dropped an `F4` drive.
- `diagram_export`: one exported state dropped its explicit `^O` domain.
- `state_literal`: the single-state renderer said "A group containing ...";
  that wording is now reserved for multi-state literals only.

The deterministic renderers preserve source structure directly, then run through
the same validator stack as model-generated records.

## Local Validation

Focused tests:

```text
187 passed
```

Full deterministic-lane local checks:

| Lane | Seed Count | Accepted | Rejected | Model Calls |
| --- | ---: | ---: | ---: | ---: |
| state_literal | 1056 | 1056 | 0 | 0 |
| binary_composition | 746 | 746 | 0 | 0 |
| let_binding | 480 | 480 | 0 | 0 |
| rpm_chain | 384 | 384 | 0 | 0 |
| meta_logic_relation | 768 | 768 | 0 | 0 |
| inversion | 78 | 78 | 0 | 0 |
| fractal_sequence | 576 | 576 | 0 | 0 |
| cross_register_omega | 658 | 658 | 0 | 0 |
| recipe | 576 | 576 | 0 | 0 |
| diagram_export | 480 | 480 | 0 | 0 |

## Calibration Run

Run:

```text
cas-synthetic/data/path_d/wave3_step2_5_manifest_20260508T164739Z.json
```

Summary:

| Metric | Value |
| --- | ---: |
| Target | 500 |
| Accepted | 500 |
| Rejected | 0 |
| Errored | 0 |
| Accepted rate | 100.0% |
| Cost | $0.00 |
| API tokens | 0 in / 0 out |

Per-category result:

| Category | Accepted / Total | Rate |
| --- | ---: | ---: |
| binary_composition | 50 / 50 | 100.0% |
| cross_register_omega | 50 / 50 | 100.0% |
| diagram_export | 50 / 50 | 100.0% |
| fractal_sequence | 51 / 51 | 100.0% |
| inversion | 47 / 47 | 100.0% |
| let_binding | 50 / 50 | 100.0% |
| meta_logic_relation | 51 / 51 | 100.0% |
| recipe | 50 / 50 | 100.0% |
| rpm_chain | 50 / 50 | 100.0% |
| state_literal | 51 / 51 | 100.0% |

Renderer usage:

| Renderer | Records |
| --- | ---: |
| `deterministic_binary_composition_renderer` | 50 |
| `deterministic_cross_register_omega_renderer` | 50 |
| `deterministic_diagram_export_renderer` | 50 |
| `deterministic_fractal_renderer` | 51 |
| `deterministic_inversion_renderer` | 47 |
| `deterministic_let_binding_renderer` | 50 |
| `deterministic_meta_logic_renderer` | 51 |
| `deterministic_recipe_renderer` | 50 |
| `deterministic_rpm_chain_renderer` | 50 |
| `deterministic_state_literal_renderer` | 51 |

## Sample Read

I read the 30-record review pack generated from `20260508T164739Z`
(3 samples per category). No critical axis-preservation errors were visible in
that pack:

- `recipe` preserved coefficients and named outcomes in the sampled records.
- `diagram_export` preserved exported names and RHS structure in the sampled
  records.
- `state_literal` no longer used group/cluster wording for single-state
  records.
- Real `x`/product-like binary composition now renders as fusion instead of a
  generic group.

This is a spot-read, not a substitute for the project promotion gate.

## Verdict

This pass clears the numeric gates:

- Aggregate accepted rate is above 70%.
- Every category is above the 45% floor.
- All categories are deterministic, zero-cost, and 100% accepted under current
  validators.
- No paid model calls were made.

It is still not automatically promoted. The manual sample-read gate remains
load-bearing because the project has repeatedly found semantic failures after
numeric gates passed.

The review pack is:

```text
docs/working/wave3_step2_5_500_review_pack_20260508T164739Z.md
```

## Promotion Rule

Promote this Wave 2.5 corpus only if the review pack confirms that:

- `recipe` preserves every coefficient, state operand, drive, register, and
  named outcome.
- `diagram_export` preserves the exported variable name and the full RHS
  structure.
- `state_literal` no longer teaches cluster/group framing for single-state
  literals.
- No renderer introduces axis confusion between domain, drive, register, and
  named outcome.
