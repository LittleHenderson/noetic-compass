# Stage 6.0 Pilot Report - Role-Bound Noetic Counterfactual Fixture

**Status:** Pilot schema + validator built. Not training data. Not a locked benchmark.  
**Date:** 2026-05-16  
**Branch:** `experiment/cas-probe-pythia`

## Purpose

Stage 6.0 turns the roundtable plan into the first concrete fixture:

> Same sentence, both noetic roles present, only the focus marker changes the target label.

This is meant to make cheap bag-of-words shortcuts less useful. The model must track which role is being inspected.

## Artifacts

- `build_stage6_role_bound_pilot.py`
- `validate_stage6_role_bound.py`
- `stage6_role_bound_pilot_20260516.jsonl`
- `stage6_role_bound_pilot_manifest_20260516.json`
- `stage6_role_bound_pilot_validation_20260516.json`

## Dataset Shape

| Field | Value |
|---|---:|
| Records | 100 |
| Bundles | 10 |
| Counterfactual pairs | 50 |
| Rows per noetic | 10 |
| Train / val / test | 60 / 20 / 20 |

Each bundle contains the five hard noetic contrasts:

- `^0/^1`
- `^2/^3`
- `^4/^7`
- `^5/^6`
- `^8/^9`

Each contrast pair has two rows with the same `base_sentence`. One row focuses `A`; the other focuses `B`.

## Example

```json
{
  "english": "B is the alert ping and A is the incident checklist. B calls up A for the system. Focus: B.",
  "noetic_label": 8,
  "semantic_role": "source_cue"
}
```

```json
{
  "english": "B is the alert ping and A is the incident checklist. B calls up A for the system. Focus: A.",
  "noetic_label": 9,
  "semantic_role": "resulting_content"
}
```

The words are almost identical. The target changes because the focus changes.

## Validation Result

Validator command:

```powershell
python noetic-compass-scaffold\noetic-compass\research\cas_probe\validate_stage6_role_bound.py --input stage6_role_bound_pilot_20260516.jsonl --out-report stage6_role_bound_pilot_validation_20260516.json
```

Result:

| Check | Result |
|---|---:|
| Status | pass |
| Errors | 0 |
| Warnings | 49 |
| Records | 100 |
| Bundles | 10 |
| Counterfactual pairs | 50 |

The warnings are expected and useful at pilot scale:

- Label-ish token warnings: words like `toward`, `away`, `built`, `shaped`, and `loop` are visible to the model input. These are warnings because the pilot keeps both labels in each contrast sentence.
- Near-duplicate review warnings: four cross-split `^0/^1` rows have char-5 Jaccard in the manual-review band (`0.75-0.85`). No pair crossed the hard-fail threshold (`>=0.85`).
- Token concentration audit: high-frequency role words are tied across both labels in their contrast pair, so they are counterbalanced within the pair rather than predicting one class outright.

## What The Pilot Proves

The pilot proves the Stage 6 data shape is buildable and machine-checkable:

- Balanced 10-way class distribution.
- Balanced `A`/`B` focus markers per label.
- Paired rows share the same base sentence.
- Split isolation holds by bundle, lexical pack, and template.
- CAS notation and label names are kept out of model input.
- The validator can surface fuzzy duplicate and shortcut risks before scale-up.

## What The Pilot Does Not Prove

This pilot does not prove:

- Pythia has a CAS-semantic internal signal.
- The probe beats TF-IDF.
- The data is ready for public claims.
- The fixture is large enough for confirmatory statistics.

It is a schema and validation milestone only.

## Next Step

Stage 6.1 should run the pilot through the existing activation/probe pipeline:

1. Capture Pythia activations for the 100 pilot rows.
2. Train the v2 probe and text baselines on the pilot split.
3. Confirm the evaluator can handle role-bound rows.
4. Treat the result as a mechanics smoke only, not a scientific verdict.

If Stage 6.1 is mechanically clean, Stage 6.2 should expand from 10 bundles to the full 60-bundle fixture and freeze the locked-test manifest before any claim-bearing run.
