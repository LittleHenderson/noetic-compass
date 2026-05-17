# Stage 11 Readout Coherence Audit

**Verdict:** `COHERENT_WITH_ADJACENT_CONFUSIONS`

## Headline

- Stage 11 status: `STAGE11_EXPRESSION_SHAPES_FULL_PASS`
- Readout/layer: `final_token` layer `2`
- Recomputed test accuracy: `0.9300`
- Reported test accuracy: `0.9300`

## Coherence Notes

- No class collapse: all 10 labels appear with at least 0.857 accuracy; worst class is fractal_sequence.
- The top errors are concentrated in structurally adjacent shapes rather than scattered uniformly.
- Readout-causal ablation remains the stronger mechanical check: targeted subspace removal drops the trained readout to exact chance.
- Largest confusion is fractal_sequence -> meta_logic_relation (40 examples); this is the first row to audit manually.

## Per-Class Accuracy

| Gold label | Accuracy | Correct / Total | Top errors |
|---|---:|---:|---|
| `state_literal` | 0.8905 | 374 / 420 | binary_composition: 26, meta_logic_relation: 20 |
| `binary_composition` | 0.9976 | 419 / 420 | inversion: 1 |
| `let_binding` | 0.8595 | 361 / 420 | meta_logic_relation: 37, recipe: 19, inversion: 3 |
| `recipe` | 0.9976 | 419 / 420 | meta_logic_relation: 1 |
| `rpm_chain` | 0.8881 | 373 / 420 | recipe: 35, meta_logic_relation: 7, binary_composition: 5 |
| `fractal_sequence` | 0.8571 | 360 / 420 | meta_logic_relation: 40, binary_composition: 11, recipe: 5, cross_register_omega: 3, state_literal: 1 |
| `cross_register_omega` | 0.9976 | 419 / 420 | meta_logic_relation: 1 |
| `meta_logic_relation` | 1.0000 | 420 / 420 | - |
| `inversion` | 0.9048 | 380 / 420 | meta_logic_relation: 20, recipe: 20 |
| `diagram_export` | 0.9071 | 381 / 420 | inversion: 19, binary_composition: 18, recipe: 2 |

## Top Confusions

| Gold | Predicted | Count |
|---|---|---:|
| `fractal_sequence` | `meta_logic_relation` | 40 |
| `let_binding` | `meta_logic_relation` | 37 |
| `rpm_chain` | `recipe` | 35 |
| `state_literal` | `binary_composition` | 26 |
| `inversion` | `meta_logic_relation` | 20 |
| `inversion` | `recipe` | 20 |
| `state_literal` | `meta_logic_relation` | 20 |
| `let_binding` | `recipe` | 19 |
| `diagram_export` | `inversion` | 19 |
| `diagram_export` | `binary_composition` | 18 |
| `fractal_sequence` | `binary_composition` | 11 |
| `rpm_chain` | `meta_logic_relation` | 7 |
| `fractal_sequence` | `recipe` | 5 |
| `rpm_chain` | `binary_composition` | 5 |
| `let_binding` | `inversion` | 3 |
| `fractal_sequence` | `cross_register_omega` | 3 |
| `diagram_export` | `recipe` | 2 |
| `fractal_sequence` | `state_literal` | 1 |
| `binary_composition` | `inversion` | 1 |
| `cross_register_omega` | `meta_logic_relation` | 1 |

## Audit Examples

Each label includes high-confidence correct rows, low-confidence correct rows, and high-confidence mistakes when present.

### state_literal

- `correct` gold=`state_literal` predicted=`state_literal` confidence=`1.0000`
  - sample_id: `s11_full_bundle041_patient_triage_shape_cycle_next_state_literal_vs_binary_composition_compressed_minimal_state_literal`
  - family: `compressed_minimal`; focus: `A`; contrast: `state_literal, binary_composition`
  - text: A is one marked condition stands by itself without another relation attached; B is two marked conditions are linked together so the relation between them is the point. Focus: A.
- `correct` gold=`state_literal` predicted=`state_literal` confidence=`1.0000`
  - sample_id: `s11_full_bundle042_disaster_relief_shape_cycle_next_state_literal_vs_binary_composition_compressed_minimal_state_literal`
  - family: `compressed_minimal`; focus: `A`; contrast: `state_literal, binary_composition`
  - text: A is one marked condition stands by itself without another relation attached; B is two marked conditions are linked together so the relation between them is the point. Focus: A.
- `correct` gold=`state_literal` predicted=`state_literal` confidence=`0.4811`
  - sample_id: `s11_full_bundle041_patient_triage_shape_cross_half_state_literal_vs_fractal_sequence_long_embedded_clause_state_literal`
  - family: `long_embedded_clause`; focus: `A`; contrast: `state_literal, fractal_sequence`
  - text: A is the role that remains active while medical team changes, because one marked condition stands by itself without another relation attached before the record settles; while the record unfolds, B is the role that remains active while medical team changes, because a repeating pattern of moves is applied in order so each pass follows the previous one before the record settles, and the focus chooses only one role. Focus: A.
- `correct` gold=`state_literal` predicted=`state_literal` confidence=`0.5618`
  - sample_id: `s11_full_bundle055_ocean_survey_shape_cycle_next_state_literal_vs_binary_composition_long_embedded_clause_state_literal`
  - family: `long_embedded_clause`; focus: `A`; contrast: `state_literal, binary_composition`
  - text: A is the role that remains active while field vessel changes, because one marked condition stands by itself without another relation attached before the record settles; while the record unfolds, B is the role that remains active while field vessel changes, because two marked conditions are linked together so the relation between them is the point before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`state_literal` predicted=`binary_composition` confidence=`0.9754`
  - sample_id: `s11_full_bundle059_vehicle_recall_shape_cycle_next_state_literal_vs_binary_composition_long_embedded_clause_state_literal`
  - family: `long_embedded_clause`; focus: `A`; contrast: `state_literal, binary_composition`
  - text: A is the role that remains active while vehicle team changes, because one marked condition stands by itself without another relation attached before the record settles; while the record unfolds, B is the role that remains active while vehicle team changes, because two marked conditions are linked together so the relation between them is the point before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`state_literal` predicted=`binary_composition` confidence=`0.9660`
  - sample_id: `s11_full_bundle043_energy_grid_shape_cycle_next_state_literal_vs_binary_composition_long_embedded_clause_state_literal`
  - family: `long_embedded_clause`; focus: `A`; contrast: `state_literal, binary_composition`
  - text: A is the role that remains active while grid crew changes, because one marked condition stands by itself without another relation attached before the record settles; while the record unfolds, B is the role that remains active while grid crew changes, because two marked conditions are linked together so the relation between them is the point before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`state_literal` predicted=`binary_composition` confidence=`0.9614`
  - sample_id: `s11_full_bundle049_restaurant_service_shape_cycle_next_state_literal_vs_binary_composition_long_embedded_clause_state_literal`
  - family: `long_embedded_clause`; focus: `A`; contrast: `state_literal, binary_composition`
  - text: A is the role that remains active while dining crew changes, because one marked condition stands by itself without another relation attached before the record settles; while the record unfolds, B is the role that remains active while dining crew changes, because two marked conditions are linked together so the relation between them is the point before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`state_literal` predicted=`binary_composition` confidence=`0.9545`
  - sample_id: `s11_full_bundle041_patient_triage_shape_cycle_next_state_literal_vs_binary_composition_long_embedded_clause_state_literal`
  - family: `long_embedded_clause`; focus: `A`; contrast: `state_literal, binary_composition`
  - text: A is the role that remains active while medical team changes, because one marked condition stands by itself without another relation attached before the record settles; while the record unfolds, B is the role that remains active while medical team changes, because two marked conditions are linked together so the relation between them is the point before the record settles, and the focus chooses only one role. Focus: A.

### binary_composition

- `correct` gold=`binary_composition` predicted=`binary_composition` confidence=`1.0000`
  - sample_id: `s11_full_bundle051_public_transit_shape_cross_half_binary_composition_vs_cross_register_omega_system_process_binary_composition`
  - family: `system_process`; focus: `A`; contrast: `binary_composition, cross_register_omega`
  - text: A is the process signal showing how two marked conditions are linked together so the relation between them is the point inside route update; B is the process signal showing how one named outcome is carried across different modes of presentation without losing its identity inside route update. Focus: A.
- `correct` gold=`binary_composition` predicted=`binary_composition` confidence=`1.0000`
  - sample_id: `s11_full_bundle041_patient_triage_shape_cycle_next_binary_composition_vs_let_binding_counter_alias_hard_negative_binary_composition`
  - family: `counter_alias_hard_negative`; focus: `A`; contrast: `binary_composition, let_binding`
  - text: A is not the neighboring role, but the aspect where two marked conditions are linked together so the relation between them is the point; B is not the neighboring role, but the aspect where a temporary name is introduced first and then reused later inside the same record. Focus: A.
- `correct` gold=`binary_composition` predicted=`binary_composition` confidence=`0.4364`
  - sample_id: `s11_full_bundle059_vehicle_recall_shape_cycle_next_state_literal_vs_binary_composition_long_embedded_clause_binary_composition`
  - family: `long_embedded_clause`; focus: `B`; contrast: `state_literal, binary_composition`
  - text: A is the role that remains active while vehicle team changes, because one marked condition stands by itself without another relation attached before the record settles; while the record unfolds, B is the role that remains active while vehicle team changes, because two marked conditions are linked together so the relation between them is the point before the record settles, and the focus chooses only one role. Focus: B.
- `correct` gold=`binary_composition` predicted=`binary_composition` confidence=`0.4521`
  - sample_id: `s11_full_bundle052_wildlife_study_shape_cycle_next_state_literal_vs_binary_composition_long_embedded_clause_binary_composition`
  - family: `long_embedded_clause`; focus: `B`; contrast: `state_literal, binary_composition`
  - text: A is the role that remains active while study crew changes, because one marked condition stands by itself without another relation attached before the record settles; while the record unfolds, B is the role that remains active while study crew changes, because two marked conditions are linked together so the relation between them is the point before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`binary_composition` predicted=`inversion` confidence=`0.4203`
  - sample_id: `s11_full_bundle049_restaurant_service_shape_cycle_next_state_literal_vs_binary_composition_long_embedded_clause_binary_composition`
  - family: `long_embedded_clause`; focus: `B`; contrast: `state_literal, binary_composition`
  - text: A is the role that remains active while dining crew changes, because one marked condition stands by itself without another relation attached before the record settles; while the record unfolds, B is the role that remains active while dining crew changes, because two marked conditions are linked together so the relation between them is the point before the record settles, and the focus chooses only one role. Focus: B.

### let_binding

- `correct` gold=`let_binding` predicted=`let_binding` confidence=`1.0000`
  - sample_id: `s11_full_bundle047_child_tutoring_shape_cycle_next_let_binding_vs_recipe_role_inverse_plain_let_binding`
  - family: `role_inverse_plain`; focus: `A`; contrast: `let_binding, recipe`
  - text: A is the selected aspect of reading log where a temporary name is introduced first and then reused later inside the same record; B is the selected aspect of reading log where a desired outcome is built from required contributors with different amounts of influence. Focus: A.
- `correct` gold=`let_binding` predicted=`let_binding` confidence=`1.0000`
  - sample_id: `s11_full_bundle059_vehicle_recall_shape_cycle_next_let_binding_vs_recipe_role_inverse_plain_let_binding`
  - family: `role_inverse_plain`; focus: `A`; contrast: `let_binding, recipe`
  - text: A is the selected aspect of warranty records where a temporary name is introduced first and then reused later inside the same record; B is the selected aspect of warranty records where a desired outcome is built from required contributors with different amounts of influence. Focus: A.
- `correct` gold=`let_binding` predicted=`let_binding` confidence=`0.5724`
  - sample_id: `s11_full_bundle054_housing_case_shape_cycle_next_let_binding_vs_recipe_long_embedded_clause_let_binding`
  - family: `long_embedded_clause`; focus: `A`; contrast: `let_binding, recipe`
  - text: A is the role that remains active while housing office changes, because a temporary name is introduced first and then reused later inside the same record before the record settles; while the record unfolds, B is the role that remains active while housing office changes, because a desired outcome is built from required contributors with different amounts of influence before the record settles, and the focus chooses only one role. Focus: A.
- `correct` gold=`let_binding` predicted=`let_binding` confidence=`0.8399`
  - sample_id: `s11_full_bundle041_patient_triage_shape_cross_half_let_binding_vs_meta_logic_relation_counter_alias_hard_negative_let_binding`
  - family: `counter_alias_hard_negative`; focus: `A`; contrast: `let_binding, meta_logic_relation`
  - text: A is not the neighboring role, but the aspect where a temporary name is introduced first and then reused later inside the same record; B is not the neighboring role, but the aspect where one rule speaks about how another rule relates, follows, or holds together. Focus: A.
- `ERROR` gold=`let_binding` predicted=`meta_logic_relation` confidence=`0.9847`
  - sample_id: `s11_full_bundle049_restaurant_service_shape_cross_half_let_binding_vs_meta_logic_relation_long_embedded_clause_let_binding`
  - family: `long_embedded_clause`; focus: `A`; contrast: `let_binding, meta_logic_relation`
  - text: A is the role that remains active while dining crew changes, because a temporary name is introduced first and then reused later inside the same record before the record settles; while the record unfolds, B is the role that remains active while dining crew changes, because one rule speaks about how another rule relates, follows, or holds together before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`let_binding` predicted=`meta_logic_relation` confidence=`0.9617`
  - sample_id: `s11_full_bundle042_disaster_relief_shape_cross_half_let_binding_vs_meta_logic_relation_long_embedded_clause_let_binding`
  - family: `long_embedded_clause`; focus: `A`; contrast: `let_binding, meta_logic_relation`
  - text: A is the role that remains active while relief desk changes, because a temporary name is introduced first and then reused later inside the same record before the record settles; while the record unfolds, B is the role that remains active while relief desk changes, because one rule speaks about how another rule relates, follows, or holds together before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`let_binding` predicted=`meta_logic_relation` confidence=`0.9563`
  - sample_id: `s11_full_bundle056_hardware_repair_shape_cross_half_let_binding_vs_meta_logic_relation_long_embedded_clause_let_binding`
  - family: `long_embedded_clause`; focus: `A`; contrast: `let_binding, meta_logic_relation`
  - text: A is the role that remains active while repair shop changes, because a temporary name is introduced first and then reused later inside the same record before the record settles; while the record unfolds, B is the role that remains active while repair shop changes, because one rule speaks about how another rule relates, follows, or holds together before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`let_binding` predicted=`meta_logic_relation` confidence=`0.9465`
  - sample_id: `s11_full_bundle052_wildlife_study_shape_cross_half_let_binding_vs_meta_logic_relation_long_embedded_clause_let_binding`
  - family: `long_embedded_clause`; focus: `A`; contrast: `let_binding, meta_logic_relation`
  - text: A is the role that remains active while study crew changes, because a temporary name is introduced first and then reused later inside the same record before the record settles; while the record unfolds, B is the role that remains active while study crew changes, because one rule speaks about how another rule relates, follows, or holds together before the record settles, and the focus chooses only one role. Focus: A.

### recipe

- `correct` gold=`recipe` predicted=`recipe` confidence=`1.0000`
  - sample_id: `s11_full_bundle041_patient_triage_shape_cross_half_recipe_vs_inversion_compressed_minimal_recipe`
  - family: `compressed_minimal`; focus: `A`; contrast: `recipe, inversion`
  - text: A is a desired outcome is built from required contributors with different amounts of influence; B is the usual direction is turned around so source and result exchange their roles. Focus: A.
- `correct` gold=`recipe` predicted=`recipe` confidence=`1.0000`
  - sample_id: `s11_full_bundle042_disaster_relief_shape_cross_half_recipe_vs_inversion_compressed_minimal_recipe`
  - family: `compressed_minimal`; focus: `A`; contrast: `recipe, inversion`
  - text: A is a desired outcome is built from required contributors with different amounts of influence; B is the usual direction is turned around so source and result exchange their roles. Focus: A.
- `correct` gold=`recipe` predicted=`recipe` confidence=`0.5116`
  - sample_id: `s11_full_bundle048_forensics_lab_shape_cycle_next_let_binding_vs_recipe_long_embedded_clause_recipe`
  - family: `long_embedded_clause`; focus: `B`; contrast: `let_binding, recipe`
  - text: A is the role that remains active while forensics unit changes, because a temporary name is introduced first and then reused later inside the same record before the record settles; while the record unfolds, B is the role that remains active while forensics unit changes, because a desired outcome is built from required contributors with different amounts of influence before the record settles, and the focus chooses only one role. Focus: B.
- `correct` gold=`recipe` predicted=`recipe` confidence=`0.5440`
  - sample_id: `s11_full_bundle055_ocean_survey_shape_cycle_next_let_binding_vs_recipe_long_embedded_clause_recipe`
  - family: `long_embedded_clause`; focus: `B`; contrast: `let_binding, recipe`
  - text: A is the role that remains active while field vessel changes, because a temporary name is introduced first and then reused later inside the same record before the record settles; while the record unfolds, B is the role that remains active while field vessel changes, because a desired outcome is built from required contributors with different amounts of influence before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`recipe` predicted=`meta_logic_relation` confidence=`0.6038`
  - sample_id: `s11_full_bundle052_wildlife_study_shape_cycle_next_let_binding_vs_recipe_long_embedded_clause_recipe`
  - family: `long_embedded_clause`; focus: `B`; contrast: `let_binding, recipe`
  - text: A is the role that remains active while study crew changes, because a temporary name is introduced first and then reused later inside the same record before the record settles; while the record unfolds, B is the role that remains active while study crew changes, because a desired outcome is built from required contributors with different amounts of influence before the record settles, and the focus chooses only one role. Focus: B.

### rpm_chain

- `correct` gold=`rpm_chain` predicted=`rpm_chain` confidence=`1.0000`
  - sample_id: `s11_full_bundle041_patient_triage_shape_cycle_next_rpm_chain_vs_fractal_sequence_compressed_minimal_rpm_chain`
  - family: `compressed_minimal`; focus: `A`; contrast: `rpm_chain, fractal_sequence`
  - text: A is a starting point advances through staged checkpoints before a final pass is reached; B is a repeating pattern of moves is applied in order so each pass follows the previous one. Focus: A.
- `correct` gold=`rpm_chain` predicted=`rpm_chain` confidence=`1.0000`
  - sample_id: `s11_full_bundle042_disaster_relief_shape_cycle_next_rpm_chain_vs_fractal_sequence_compressed_minimal_rpm_chain`
  - family: `compressed_minimal`; focus: `A`; contrast: `rpm_chain, fractal_sequence`
  - text: A is a starting point advances through staged checkpoints before a final pass is reached; B is a repeating pattern of moves is applied in order so each pass follows the previous one. Focus: A.
- `correct` gold=`rpm_chain` predicted=`rpm_chain` confidence=`0.3497`
  - sample_id: `s11_full_bundle053_procurement_bid_shape_cycle_next_recipe_vs_rpm_chain_long_embedded_clause_rpm_chain`
  - family: `long_embedded_clause`; focus: `B`; contrast: `recipe, rpm_chain`
  - text: A is the role that remains active while procurement office changes, because a desired outcome is built from required contributors with different amounts of influence before the record settles; while the record unfolds, B is the role that remains active while procurement office changes, because a starting point advances through staged checkpoints before a final pass is reached before the record settles, and the focus chooses only one role. Focus: B.
- `correct` gold=`rpm_chain` predicted=`rpm_chain` confidence=`0.3752`
  - sample_id: `s11_full_bundle054_housing_case_shape_cycle_next_recipe_vs_rpm_chain_long_embedded_clause_rpm_chain`
  - family: `long_embedded_clause`; focus: `B`; contrast: `recipe, rpm_chain`
  - text: A is the role that remains active while housing office changes, because a desired outcome is built from required contributors with different amounts of influence before the record settles; while the record unfolds, B is the role that remains active while housing office changes, because a starting point advances through staged checkpoints before a final pass is reached before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`rpm_chain` predicted=`recipe` confidence=`0.8293`
  - sample_id: `s11_full_bundle047_child_tutoring_shape_cross_half_rpm_chain_vs_diagram_export_long_embedded_clause_rpm_chain`
  - family: `long_embedded_clause`; focus: `A`; contrast: `rpm_chain, diagram_export`
  - text: A is the role that remains active while learning coach changes, because a starting point advances through staged checkpoints before a final pass is reached before the record settles; while the record unfolds, B is the role that remains active while learning coach changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`rpm_chain` predicted=`recipe` confidence=`0.8122`
  - sample_id: `s11_full_bundle056_hardware_repair_shape_cross_half_rpm_chain_vs_diagram_export_long_embedded_clause_rpm_chain`
  - family: `long_embedded_clause`; focus: `A`; contrast: `rpm_chain, diagram_export`
  - text: A is the role that remains active while repair shop changes, because a starting point advances through staged checkpoints before a final pass is reached before the record settles; while the record unfolds, B is the role that remains active while repair shop changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`rpm_chain` predicted=`recipe` confidence=`0.8033`
  - sample_id: `s11_full_bundle060_youth_program_shape_cross_half_rpm_chain_vs_diagram_export_long_embedded_clause_rpm_chain`
  - family: `long_embedded_clause`; focus: `A`; contrast: `rpm_chain, diagram_export`
  - text: A is the role that remains active while youth staff changes, because a starting point advances through staged checkpoints before a final pass is reached before the record settles; while the record unfolds, B is the role that remains active while youth staff changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`rpm_chain` predicted=`recipe` confidence=`0.7962`
  - sample_id: `s11_full_bundle050_mobile_app_shape_cross_half_rpm_chain_vs_diagram_export_long_embedded_clause_rpm_chain`
  - family: `long_embedded_clause`; focus: `A`; contrast: `rpm_chain, diagram_export`
  - text: A is the role that remains active while app team changes, because a starting point advances through staged checkpoints before a final pass is reached before the record settles; while the record unfolds, B is the role that remains active while app team changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: A.

### fractal_sequence

- `correct` gold=`fractal_sequence` predicted=`fractal_sequence` confidence=`1.0000`
  - sample_id: `s11_full_bundle048_forensics_lab_shape_cycle_next_rpm_chain_vs_fractal_sequence_role_inverse_plain_fractal_sequence`
  - family: `role_inverse_plain`; focus: `B`; contrast: `rpm_chain, fractal_sequence`
  - text: A is the selected aspect of case notes where a starting point advances through staged checkpoints before a final pass is reached; B is the selected aspect of case notes where a repeating pattern of moves is applied in order so each pass follows the previous one. Focus: B.
- `correct` gold=`fractal_sequence` predicted=`fractal_sequence` confidence=`0.9999`
  - sample_id: `s11_full_bundle048_forensics_lab_shape_cross_half_state_literal_vs_fractal_sequence_role_inverse_plain_fractal_sequence`
  - family: `role_inverse_plain`; focus: `B`; contrast: `state_literal, fractal_sequence`
  - text: A is the selected aspect of case notes where one marked condition stands by itself without another relation attached; B is the selected aspect of case notes where a repeating pattern of moves is applied in order so each pass follows the previous one. Focus: B.
- `correct` gold=`fractal_sequence` predicted=`fractal_sequence` confidence=`0.8509`
  - sample_id: `s11_full_bundle051_public_transit_shape_cycle_next_fractal_sequence_vs_cross_register_omega_system_process_fractal_sequence`
  - family: `system_process`; focus: `A`; contrast: `fractal_sequence, cross_register_omega`
  - text: A is the process signal showing how a repeating pattern of moves is applied in order so each pass follows the previous one inside route update; B is the process signal showing how one named outcome is carried across different modes of presentation without losing its identity inside route update. Focus: A.
- `correct` gold=`fractal_sequence` predicted=`fractal_sequence` confidence=`0.9654`
  - sample_id: `s11_full_bundle051_public_transit_shape_cycle_next_rpm_chain_vs_fractal_sequence_system_process_fractal_sequence`
  - family: `system_process`; focus: `B`; contrast: `rpm_chain, fractal_sequence`
  - text: A is the process signal showing how a starting point advances through staged checkpoints before a final pass is reached inside route update; B is the process signal showing how a repeating pattern of moves is applied in order so each pass follows the previous one inside route update. Focus: B.
- `ERROR` gold=`fractal_sequence` predicted=`meta_logic_relation` confidence=`0.9159`
  - sample_id: `s11_full_bundle042_disaster_relief_shape_cycle_next_rpm_chain_vs_fractal_sequence_long_embedded_clause_fractal_sequence`
  - family: `long_embedded_clause`; focus: `B`; contrast: `rpm_chain, fractal_sequence`
  - text: A is the role that remains active while relief desk changes, because a starting point advances through staged checkpoints before a final pass is reached before the record settles; while the record unfolds, B is the role that remains active while relief desk changes, because a repeating pattern of moves is applied in order so each pass follows the previous one before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`fractal_sequence` predicted=`meta_logic_relation` confidence=`0.9140`
  - sample_id: `s11_full_bundle052_wildlife_study_shape_cross_half_state_literal_vs_fractal_sequence_long_embedded_clause_fractal_sequence`
  - family: `long_embedded_clause`; focus: `B`; contrast: `state_literal, fractal_sequence`
  - text: A is the role that remains active while study crew changes, because one marked condition stands by itself without another relation attached before the record settles; while the record unfolds, B is the role that remains active while study crew changes, because a repeating pattern of moves is applied in order so each pass follows the previous one before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`fractal_sequence` predicted=`meta_logic_relation` confidence=`0.9025`
  - sample_id: `s11_full_bundle052_wildlife_study_shape_cycle_next_rpm_chain_vs_fractal_sequence_long_embedded_clause_fractal_sequence`
  - family: `long_embedded_clause`; focus: `B`; contrast: `rpm_chain, fractal_sequence`
  - text: A is the role that remains active while study crew changes, because a starting point advances through staged checkpoints before a final pass is reached before the record settles; while the record unfolds, B is the role that remains active while study crew changes, because a repeating pattern of moves is applied in order so each pass follows the previous one before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`fractal_sequence` predicted=`meta_logic_relation` confidence=`0.8957`
  - sample_id: `s11_full_bundle056_hardware_repair_shape_cycle_next_rpm_chain_vs_fractal_sequence_long_embedded_clause_fractal_sequence`
  - family: `long_embedded_clause`; focus: `B`; contrast: `rpm_chain, fractal_sequence`
  - text: A is the role that remains active while repair shop changes, because a starting point advances through staged checkpoints before a final pass is reached before the record settles; while the record unfolds, B is the role that remains active while repair shop changes, because a repeating pattern of moves is applied in order so each pass follows the previous one before the record settles, and the focus chooses only one role. Focus: B.

### cross_register_omega

- `correct` gold=`cross_register_omega` predicted=`cross_register_omega` confidence=`0.9999`
  - sample_id: `s11_full_bundle055_ocean_survey_shape_cycle_next_fractal_sequence_vs_cross_register_omega_system_process_cross_register_omega`
  - family: `system_process`; focus: `B`; contrast: `fractal_sequence, cross_register_omega`
  - text: A is the process signal showing how a repeating pattern of moves is applied in order so each pass follows the previous one inside survey map; B is the process signal showing how one named outcome is carried across different modes of presentation without losing its identity inside survey map. Focus: B.
- `correct` gold=`cross_register_omega` predicted=`cross_register_omega` confidence=`0.9999`
  - sample_id: `s11_full_bundle041_patient_triage_shape_cycle_next_fractal_sequence_vs_cross_register_omega_system_process_cross_register_omega`
  - family: `system_process`; focus: `B`; contrast: `fractal_sequence, cross_register_omega`
  - text: A is the process signal showing how a repeating pattern of moves is applied in order so each pass follows the previous one inside care decision; B is the process signal showing how one named outcome is carried across different modes of presentation without losing its identity inside care decision. Focus: B.
- `correct` gold=`cross_register_omega` predicted=`cross_register_omega` confidence=`0.4210`
  - sample_id: `s11_full_bundle049_restaurant_service_shape_cross_half_binary_composition_vs_cross_register_omega_long_embedded_clause_cross_register_omega`
  - family: `long_embedded_clause`; focus: `B`; contrast: `binary_composition, cross_register_omega`
  - text: A is the role that remains active while dining crew changes, because two marked conditions are linked together so the relation between them is the point before the record settles; while the record unfolds, B is the role that remains active while dining crew changes, because one named outcome is carried across different modes of presentation without losing its identity before the record settles, and the focus chooses only one role. Focus: B.
- `correct` gold=`cross_register_omega` predicted=`cross_register_omega` confidence=`0.4721`
  - sample_id: `s11_full_bundle042_disaster_relief_shape_cross_half_binary_composition_vs_cross_register_omega_long_embedded_clause_cross_register_omega`
  - family: `long_embedded_clause`; focus: `B`; contrast: `binary_composition, cross_register_omega`
  - text: A is the role that remains active while relief desk changes, because two marked conditions are linked together so the relation between them is the point before the record settles; while the record unfolds, B is the role that remains active while relief desk changes, because one named outcome is carried across different modes of presentation without losing its identity before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`cross_register_omega` predicted=`meta_logic_relation` confidence=`0.6338`
  - sample_id: `s11_full_bundle049_restaurant_service_shape_cycle_next_cross_register_omega_vs_meta_logic_relation_long_embedded_clause_cross_register_omega`
  - family: `long_embedded_clause`; focus: `A`; contrast: `cross_register_omega, meta_logic_relation`
  - text: A is the role that remains active while dining crew changes, because one named outcome is carried across different modes of presentation without losing its identity before the record settles; while the record unfolds, B is the role that remains active while dining crew changes, because one rule speaks about how another rule relates, follows, or holds together before the record settles, and the focus chooses only one role. Focus: A.

### meta_logic_relation

- `correct` gold=`meta_logic_relation` predicted=`meta_logic_relation` confidence=`1.0000`
  - sample_id: `s11_full_bundle041_patient_triage_shape_cycle_next_cross_register_omega_vs_meta_logic_relation_compressed_minimal_meta_logic_relation`
  - family: `compressed_minimal`; focus: `B`; contrast: `cross_register_omega, meta_logic_relation`
  - text: A is one named outcome is carried across different modes of presentation without losing its identity; B is one rule speaks about how another rule relates, follows, or holds together. Focus: B.
- `correct` gold=`meta_logic_relation` predicted=`meta_logic_relation` confidence=`1.0000`
  - sample_id: `s11_full_bundle042_disaster_relief_shape_cycle_next_cross_register_omega_vs_meta_logic_relation_compressed_minimal_meta_logic_relation`
  - family: `compressed_minimal`; focus: `B`; contrast: `cross_register_omega, meta_logic_relation`
  - text: A is one named outcome is carried across different modes of presentation without losing its identity; B is one rule speaks about how another rule relates, follows, or holds together. Focus: B.
- `correct` gold=`meta_logic_relation` predicted=`meta_logic_relation` confidence=`0.7922`
  - sample_id: `s11_full_bundle049_restaurant_service_shape_cycle_next_meta_logic_relation_vs_inversion_applied_human_meta_logic_relation`
  - family: `applied_human`; focus: `A`; contrast: `meta_logic_relation, inversion`
  - text: A is what the server notices when one rule speaks about how another rule relates, follows, or holds together in the case; B is what the server notices when the usual direction is turned around so source and result exchange their roles in the case. Focus: A.
- `correct` gold=`meta_logic_relation` predicted=`meta_logic_relation` confidence=`0.8840`
  - sample_id: `s11_full_bundle051_public_transit_shape_cycle_next_meta_logic_relation_vs_inversion_system_process_meta_logic_relation`
  - family: `system_process`; focus: `A`; contrast: `meta_logic_relation, inversion`
  - text: A is the process signal showing how one rule speaks about how another rule relates, follows, or holds together inside route update; B is the process signal showing how the usual direction is turned around so source and result exchange their roles inside route update. Focus: A.

### inversion

- `correct` gold=`inversion` predicted=`inversion` confidence=`1.0000`
  - sample_id: `s11_full_bundle052_wildlife_study_shape_cross_half_recipe_vs_inversion_role_inverse_plain_inversion`
  - family: `role_inverse_plain`; focus: `B`; contrast: `recipe, inversion`
  - text: A is the selected aspect of species records where a desired outcome is built from required contributors with different amounts of influence; B is the selected aspect of species records where the usual direction is turned around so source and result exchange their roles. Focus: B.
- `correct` gold=`inversion` predicted=`inversion` confidence=`0.9999`
  - sample_id: `s11_full_bundle050_mobile_app_shape_cycle_next_meta_logic_relation_vs_inversion_role_inverse_plain_inversion`
  - family: `role_inverse_plain`; focus: `B`; contrast: `meta_logic_relation, inversion`
  - text: A is the selected aspect of bug history where one rule speaks about how another rule relates, follows, or holds together; B is the selected aspect of bug history where the usual direction is turned around so source and result exchange their roles. Focus: B.
- `correct` gold=`inversion` predicted=`inversion` confidence=`0.6020`
  - sample_id: `s11_full_bundle048_forensics_lab_shape_cycle_next_meta_logic_relation_vs_inversion_long_embedded_clause_inversion`
  - family: `long_embedded_clause`; focus: `B`; contrast: `meta_logic_relation, inversion`
  - text: A is the role that remains active while forensics unit changes, because one rule speaks about how another rule relates, follows, or holds together before the record settles; while the record unfolds, B is the role that remains active while forensics unit changes, because the usual direction is turned around so source and result exchange their roles before the record settles, and the focus chooses only one role. Focus: B.
- `correct` gold=`inversion` predicted=`inversion` confidence=`0.6279`
  - sample_id: `s11_full_bundle052_wildlife_study_shape_cycle_next_meta_logic_relation_vs_inversion_long_embedded_clause_inversion`
  - family: `long_embedded_clause`; focus: `B`; contrast: `meta_logic_relation, inversion`
  - text: A is the role that remains active while study crew changes, because one rule speaks about how another rule relates, follows, or holds together before the record settles; while the record unfolds, B is the role that remains active while study crew changes, because the usual direction is turned around so source and result exchange their roles before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`inversion` predicted=`recipe` confidence=`0.8357`
  - sample_id: `s11_full_bundle050_mobile_app_shape_cycle_next_inversion_vs_diagram_export_long_embedded_clause_inversion`
  - family: `long_embedded_clause`; focus: `A`; contrast: `inversion, diagram_export`
  - text: A is the role that remains active while app team changes, because the usual direction is turned around so source and result exchange their roles before the record settles; while the record unfolds, B is the role that remains active while app team changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`inversion` predicted=`recipe` confidence=`0.8012`
  - sample_id: `s11_full_bundle047_child_tutoring_shape_cycle_next_inversion_vs_diagram_export_long_embedded_clause_inversion`
  - family: `long_embedded_clause`; focus: `A`; contrast: `inversion, diagram_export`
  - text: A is the role that remains active while learning coach changes, because the usual direction is turned around so source and result exchange their roles before the record settles; while the record unfolds, B is the role that remains active while learning coach changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`inversion` predicted=`recipe` confidence=`0.7656`
  - sample_id: `s11_full_bundle056_hardware_repair_shape_cycle_next_inversion_vs_diagram_export_long_embedded_clause_inversion`
  - family: `long_embedded_clause`; focus: `A`; contrast: `inversion, diagram_export`
  - text: A is the role that remains active while repair shop changes, because the usual direction is turned around so source and result exchange their roles before the record settles; while the record unfolds, B is the role that remains active while repair shop changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: A.
- `ERROR` gold=`inversion` predicted=`recipe` confidence=`0.7512`
  - sample_id: `s11_full_bundle060_youth_program_shape_cycle_next_inversion_vs_diagram_export_long_embedded_clause_inversion`
  - family: `long_embedded_clause`; focus: `A`; contrast: `inversion, diagram_export`
  - text: A is the role that remains active while youth staff changes, because the usual direction is turned around so source and result exchange their roles before the record settles; while the record unfolds, B is the role that remains active while youth staff changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: A.

### diagram_export

- `correct` gold=`diagram_export` predicted=`diagram_export` confidence=`1.0000`
  - sample_id: `s11_full_bundle041_patient_triage_shape_cycle_next_inversion_vs_diagram_export_compressed_minimal_diagram_export`
  - family: `compressed_minimal`; focus: `B`; contrast: `inversion, diagram_export`
  - text: A is the usual direction is turned around so source and result exchange their roles; B is a named cluster is packaged as a reusable bundle for outside viewing. Focus: B.
- `correct` gold=`diagram_export` predicted=`diagram_export` confidence=`1.0000`
  - sample_id: `s11_full_bundle042_disaster_relief_shape_cycle_next_inversion_vs_diagram_export_compressed_minimal_diagram_export`
  - family: `compressed_minimal`; focus: `B`; contrast: `inversion, diagram_export`
  - text: A is the usual direction is turned around so source and result exchange their roles; B is a named cluster is packaged as a reusable bundle for outside viewing. Focus: B.
- `correct` gold=`diagram_export` predicted=`diagram_export` confidence=`0.5199`
  - sample_id: `s11_full_bundle052_wildlife_study_shape_cross_half_rpm_chain_vs_diagram_export_long_embedded_clause_diagram_export`
  - family: `long_embedded_clause`; focus: `B`; contrast: `rpm_chain, diagram_export`
  - text: A is the role that remains active while study crew changes, because a starting point advances through staged checkpoints before a final pass is reached before the record settles; while the record unfolds, B is the role that remains active while study crew changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: B.
- `correct` gold=`diagram_export` predicted=`diagram_export` confidence=`0.5745`
  - sample_id: `s11_full_bundle050_mobile_app_shape_cycle_next_inversion_vs_diagram_export_long_embedded_clause_diagram_export`
  - family: `long_embedded_clause`; focus: `B`; contrast: `inversion, diagram_export`
  - text: A is the role that remains active while app team changes, because the usual direction is turned around so source and result exchange their roles before the record settles; while the record unfolds, B is the role that remains active while app team changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`diagram_export` predicted=`inversion` confidence=`0.8459`
  - sample_id: `s11_full_bundle047_child_tutoring_shape_cycle_next_inversion_vs_diagram_export_long_embedded_clause_diagram_export`
  - family: `long_embedded_clause`; focus: `B`; contrast: `inversion, diagram_export`
  - text: A is the role that remains active while learning coach changes, because the usual direction is turned around so source and result exchange their roles before the record settles; while the record unfolds, B is the role that remains active while learning coach changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`diagram_export` predicted=`inversion` confidence=`0.8433`
  - sample_id: `s11_full_bundle060_youth_program_shape_cycle_next_inversion_vs_diagram_export_long_embedded_clause_diagram_export`
  - family: `long_embedded_clause`; focus: `B`; contrast: `inversion, diagram_export`
  - text: A is the role that remains active while youth staff changes, because the usual direction is turned around so source and result exchange their roles before the record settles; while the record unfolds, B is the role that remains active while youth staff changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`diagram_export` predicted=`inversion` confidence=`0.8378`
  - sample_id: `s11_full_bundle051_public_transit_shape_cycle_next_inversion_vs_diagram_export_long_embedded_clause_diagram_export`
  - family: `long_embedded_clause`; focus: `B`; contrast: `inversion, diagram_export`
  - text: A is the role that remains active while transit office changes, because the usual direction is turned around so source and result exchange their roles before the record settles; while the record unfolds, B is the role that remains active while transit office changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: B.
- `ERROR` gold=`diagram_export` predicted=`inversion` confidence=`0.8119`
  - sample_id: `s11_full_bundle055_ocean_survey_shape_cycle_next_inversion_vs_diagram_export_long_embedded_clause_diagram_export`
  - family: `long_embedded_clause`; focus: `B`; contrast: `inversion, diagram_export`
  - text: A is the role that remains active while field vessel changes, because the usual direction is turned around so source and result exchange their roles before the record settles; while the record unfolds, B is the role that remains active while field vessel changes, because a named cluster is packaged as a reusable bundle for outside viewing before the record settles, and the focus chooses only one role. Focus: B.

## Boundary

This audit checks readout coherence for the trained Stage 11 classifier. It does not prove formula solving, compiler execution, raw-symbol parsing, or visible generation control.
