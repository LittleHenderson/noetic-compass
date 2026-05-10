# v1c + RPM Phase 3 Corrective Retry Audit

Source artifacts:

- `v1_eval_pack_24records_20260510T044827Z.md`
- `v1_eval_pack_24records_20260510T044827Z.jsonl`

Baseline:

- Phase 2 graded audit: `v1_eval_pack_24records_20260510T042914Z_CODEX_GRADED.md`

## Verdict

Phase 3 corrective retry is a negative experiment.

The safety heuristic worked: all three attempted RPM retries were rejected, and all 24 `final_text` values are byte-identical to the Phase 2 run.

The quality gate remains unchanged:

- Acceptable+: `16/24`
- Target: `>=18/24`
- Verdict: FAIL

## What Happened

Phase 3 attempted corrective prompts only on the three RPM chain records with semantic drifts.

| Record | Retry Attempted | Retry Used | Rejection Reason |
|---:|---|---|---|
| 19 | yes | no | retry lost stage coverage `1 vs 4` |
| 20 | yes | no | retry lost stage coverage `1 vs 4` |
| 21 | yes | no | retry drift count `3` not strictly less than original `3` |

Records 19 and 20 are the decisive failures. The retry prompt included useful semantic hints, but changing the prompt shape caused the model to abandon the multi-stage RPM rendering pattern. It produced fewer semantic drifts only because it stopped rendering the full chain. The comparison heuristic correctly rejected that.

Record 21 shows the softer failure: the retry preserved enough shape but did not reduce semantic drift.

## Interpretation

This confirms the model is not instruction-following enough for corrective prompt enrichment.

The model was trained on a narrow prompt format:

`Describe the following CAS expression in plain English:`

When Phase 3 adds a hint section, the prompt becomes out-of-distribution. The model does not reliably treat the hint as a constraint. It either collapses the RPM shape or repeats the original drift.

Correct claim:

> Phase 3 proves corrective retry is not the production path for RPM semantic fidelity.

Incorrect claim:

> Phase 3 almost worked and needs more prompt tuning.

The failure mode is structural, not wording.

## Grade Counts

Unchanged from Phase 2:

| Band | Count | Records |
|---|---:|---|
| Green | 7 | 1, 2, 4, 6, 7, 23, 24 |
| High yellow | 2 | 17, 21 |
| Yellow | 7 | 5, 8, 9, 11, 19, 20, 22 |
| Wrong / flop / incoherent | 8 | 3, 10, 12, 13, 14, 15, 16, 18 |

## Recommendation

Do not promote corrective retry to production. Keep it opt-in/diagnostic only.

The remaining choices are:

1. Accept RPM at Phase 1 + Phase 2 and shift focus to non-RPM wrong-band records.
2. Try seed-enrichment only with explicit approval, because it is closer to deterministic semantic scaffolding.
3. Run a small targeted RPM training wave, but only if the project wants to spend GPU time on RPM rather than attacking broader category failures.

My recommendation: choose path 1. RPM is no longer the main blocker after the seed and structural repair. The broader wrong band is now records `3, 10, 12, 13, 14, 15, 16, 18`.
