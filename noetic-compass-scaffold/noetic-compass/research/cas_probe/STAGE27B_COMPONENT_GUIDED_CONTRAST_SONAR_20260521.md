# Stage 27B Component-Guided Contrast Sonar

**Status:** `GREY_COMPONENT_GUIDED_CONTRAST_SONAR_PARTIAL`

## Contracts

- Stage 7 artifact: `LOCKED_ARTIFACT_MATCH`
- Stage 26 source status: `PASS_BOUNDED_COMPONENT_ATTRIBUTION`
- Stage 27A source status: `PASS_BOUNDED_COMPONENT_PATH_PATCHING`
- Formal gate valid: `True`

## Component-Guided Sonar

- Eval rows: `512`
- Mean target-minus-hard-partner margin: `0.003738`
- Median margin: `-0.005539`
- Positive-share: `0.4629`
- Matched-control p(random >= actual): `0.0323`

## Pair-Kind Breakdown

| Pair kind | n | mean margin | positive share |
|---|---:|---:|---:|
| `diff_drive_same_register` | 316 | 0.000974 | 0.4715 |
| `same_drive_diff_register` | 196 | 0.008194 | 0.4490 |

## Selected Components

- `L5H3`
- `L5H5`
- `L5H0`
- `L5H10`
- `L1H6`
- `L5H6`

## Token Signature Quality

- Readable rate: `1.0000`
- Readable top tokens: `672 / 672`

## Sample Extremes

- `stage7_pilot_bundle041_patient_triage_same_register_drive_cycle_A_F5A_F6A_system_process_F6A` F6A vs F5A (diff_drive_same_register): margin `-0.237992`
- `stage7_pilot_bundle041_patient_triage_same_register_drive_cycle_A_F5A_F6A_concrete_human_F6A` F6A vs F5A (diff_drive_same_register): margin `-0.208384`
- `stage7_pilot_bundle041_patient_triage_same_register_drive_cycle_A_F5A_F6A_role_inverse_minimal_F6A` F6A vs F5A (diff_drive_same_register): margin `-0.191245`
- `stage7_pilot_bundle041_patient_triage_same_register_drive_cycle_A_F5A_F6A_long_embedded_clause_F6A` F6A vs F5A (diff_drive_same_register): margin `-0.186232`
- `stage7_pilot_bundle041_patient_triage_same_register_drive_cycle_A_F1A_F2A_counter_alias_hard_negative_F2A` F2A vs F1A (diff_drive_same_register): margin `-0.181123`
- `stage7_pilot_bundle041_patient_triage_same_register_drive_cycle_T_F6T_F7T_no_alias_plain_F7T` F7T vs F6T (diff_drive_same_register): margin `0.276832`
- `stage7_pilot_bundle041_patient_triage_same_drive_register_f_E_F7f_F7E_role_inverse_minimal_F7E` F7E vs F7f (same_drive_diff_register): margin `0.266061`
- `stage7_pilot_bundle041_patient_triage_same_register_drive_cycle_T_F6T_F7T_compressed_minimal_F7T` F7T vs F6T (diff_drive_same_register): margin `0.253864`
- `stage7_pilot_bundle041_patient_triage_same_register_drive_cycle_T_F6T_F7T_long_embedded_clause_F7T` F7T vs F6T (diff_drive_same_register): margin `0.245860`
- `stage7_pilot_bundle041_patient_triage_same_register_drive_cycle_f_F7f_F1f_no_alias_plain_F1f` F1f vs F7f (diff_drive_same_register): margin `0.233840`

## Boundary

Stage 27B measures Foundation hard-partner token/logit contrast through the Stage 26/27A selected Pythia-160M attention-head path. It does not establish exact neurons, complete circuits, 40-Element component causality, raw CAS-symbol understanding, free-form generation control, or cross-model component generality.
