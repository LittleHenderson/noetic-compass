# Stage 13 Blind-Spot Sanity Audit Gates

Date: 2026-05-19

## Purpose

Before publishing the Stage 13 blind-spot language, verify that the reported weak classes are not simply fixture imbalance or undocumented threshold tuning.

## Checks

1. Per-class population check:
   - Verify train/val/test counts for the Stage 12 fixture.
   - If the flagged classes have fewer rows, the blind-spot result is a fixture artifact.
   - If counts are equal, fixture imbalance is not the explanation.

2. Threshold provenance check:
   - Document the exact trace-kind thresholds used by `audit_stage13_multilayer_formula_trace.py`.
   - Confirm the post-registration bug fix changed only invalid `zip(..., strict=True)` switch-count iteration, not the thresholds.

3. Per-readout blind-spot check:
   - Report blind spots per readout, not only as a pooled aggregate.
   - Specifically inspect whether `relation_dependency` is weak under the best readout or only weak under a weaker readout path.

4. Layer-selection boundary:
   - Confirm Stage 13 is diagnostic and that `focus_token` layer 12 is a trace-audit finding, not a replacement for the Stage 12 claim-bearing `final_token` layer 2 result.

## Allowed Claim

> CAS Harness can expose hidden-activation blind spots as weak, unstable, or drifting evidence under a trained readout path.

## Not Allowed

- The model cannot represent the concept.
- CAS identified exact causal neurons.
- The fixture is perfect.
- Weights fired.
