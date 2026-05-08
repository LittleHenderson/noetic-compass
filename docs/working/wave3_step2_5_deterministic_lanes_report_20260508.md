# Wave 2.5 Deterministic-Lane Calibration Report

Date: 2026-05-08

Status: STRONG NUMERIC PASS, HUMAN REVIEW STILL REQUIRED

## What Changed

After the layer-3 filter showed that free-form generation still corrupted
regular compiler shapes, eight lanes now render deterministically instead of
calling Haiku:

- `cross_register_omega`
- `fractal_sequence`
- `rpm_chain`
- `meta_logic_relation`
- `inversion`
- `state_literal`
- `binary_composition`
- `let_binding`

The new renderers preserve source structure directly, then run through the
same validator stack as model-generated records.

## Local Validation

Focused tests:

```text
184 passed
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

## Paid Calibration

Run:

```text
cas-synthetic/data/path_d/wave3_step2_5_manifest_20260508T150305Z.json
```

Summary:

| Metric | Value |
| --- | ---: |
| Target | 500 |
| Accepted | 459 |
| Rejected | 41 |
| Errored | 0 |
| Accepted rate | 91.8% |
| Cost | $0.270592 |

Per-category result:

| Category | Accepted / Total | Rate |
| --- | ---: | ---: |
| binary_composition | 50 / 50 | 100.0% |
| cross_register_omega | 50 / 50 | 100.0% |
| fractal_sequence | 51 / 51 | 100.0% |
| inversion | 47 / 47 | 100.0% |
| let_binding | 50 / 50 | 100.0% |
| meta_logic_relation | 51 / 51 | 100.0% |
| rpm_chain | 50 / 50 | 100.0% |
| state_literal | 51 / 51 | 100.0% |
| recipe | 30 / 50 | 60.0% |
| diagram_export | 29 / 50 | 58.0% |

## Verdict

This pass clears the numeric gates:

- Aggregate accepted rate is above 70%.
- Every category is above the 45% floor.
- Deterministic lanes are zero-cost and 100% accepted under current validators.

It is not automatically promoted. The manual sample-read gate still stands.
The review pack is:

```text
docs/working/wave3_step2_5_500_review_pack_20260508T150305Z.md
```

## Remaining Weak Lanes

The remaining rejections are concentrated in model-rendered lanes:

- `diagram_export`: 58.0%
- `recipe`: 60.0%

The next likely improvement is to deterministically render more
compiler-regular `diagram_export` shapes, then leave only genuinely fluent
paraphrase work to the model.
