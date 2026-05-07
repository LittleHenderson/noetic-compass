# Path D Wave 2D — Invalid CAS Coverage Report

- Total invalid samples emitted: **5581**
- Unexpected compiles (mutator bugs / compile-clean leaks): **0**
- Compiler-rejection rate: **100.0000%**

## Per error_class counts

| error_class | count |
|---|---|
| admissibility | 1269 |
| fractal | 692 |
| meta_logic | 692 |
| parse | 851 |
| recipe | 1154 |
| rpm | 923 |

## Per mutation_type counts (top 60)

| mutation_type | count |
|---|---|
| dangling_caret_no_domain | 250 |
| rpm_skip_to_undefined_stageP | 231 |
| rpm_skip_to_undefined_stageW | 231 |
| rpm_no_let_undefined_stages | 231 |
| recipe_missing_coefficient | 201 |
| coverof_non_subset_member | 199 |
| partitionof_overlap | 199 |
| partitionof_undercover | 199 |
| recipe_empty_target_parens | 196 |
| recipe_missing_equals | 193 |
| recipe_arrow_for_equals | 191 |
| recipe_drop_theta_wrapper | 188 |
| recipe_missing_arrow | 185 |
| fractal_empty_sequence | 173 |
| fractal_negative_digit | 173 |
| dropped_closing_brace | 166 |
| dropped_closing_paren | 101 |
| rpm_domain_descent_O_to_E | 58 |
| unknown_domain_X | 57 |
| cluster_drop_comma | 52 |
| unknown_domain_K | 48 |
| fractal_remove_colons | 47 |
| unknown_domain_Q | 47 |
| fractal_digit_out_of_range_99 | 44 |
| fractal_non_digit_foo | 43 |
| recipe_truncate_before_arrow | 40 |
| unknown_noetic_11 | 40 |
| fractal_non_digit_Y | 40 |
| rpm_domain_descent_O_to_C | 40 |
| recipe_swap_times_for_plus | 39 |
| unknown_domain_Z | 38 |
| rpm_domain_descent_O_to_P | 38 |
| rpm_domain_descent_E_to_C | 35 |
| fractal_digit_out_of_range_11 | 34 |
| unknown_noetic_15 | 33 |
| fractal_digit_out_of_range_17 | 33 |
| fractal_non_digit_Z | 33 |
| fractal_digit_out_of_range_13 | 32 |
| cross_register_no_omega_Tf | 31 |
| cross_register_no_omega_AT | 31 |
| unknown_noetic_10 | 31 |
| rpm_domain_descent_E_to_P | 31 |
| unknown_noetic_20 | 30 |
| unknown_noetic_12 | 30 |
| fractal_digit_out_of_range_10 | 30 |
| fractal_non_digit_abc | 29 |
| cross_register_no_omega_TA | 28 |
| fractal_non_digit_X | 28 |
| rpm_domain_descent_C_to_P | 28 |
| fractal_misplaced_colon_unicode | 26 |
| unknown_domain_W | 26 |
| cross_register_no_omega_Af | 26 |
| corrupted_drive_F11 | 25 |
| cross_register_no_omega_fA | 25 |
| cross_register_no_omega_fE | 23 |
| unknown_noetic_13 | 23 |
| unknown_noetic_99 | 22 |
| cross_register_no_omega_fT | 22 |
| cross_register_no_omega_ET | 20 |
| cross_register_no_omega_AE | 20 |

## 7-category surface coverage in `corrected_form`

Each row counts how many invalid samples have the given category present in the original (correct) seed expression. Coverage check: every category should be exercised so the repair-track curriculum touches the full grammar surface.

| category | seeds-with-surface |
|---|---|
| 1. state_literal | 5092 |
| 2. drive subscripts | 1969 |
| 3. registers | 1888 |
| 4. operators | 2716 |
| 5. recipes (Θ) | 1613 |
| 6. meta-logic | 693 |
| 7. fractals | 957 |

## Compiler-team follow-ups (gaps the mutator works around)

While building the mutators, three compiler typecheck gaps were identified. The mutators skip the affected seed shapes so every emitted sample rejects, but the compiler-team should consider tightening these checks:

1. **Recipe prereq drive subscripts not typechecked.** `Θ(Ω_x) = 0.7*^1^C_{F10} → Ω_x` compiles cleanly even though `F10` is out of the F1–F7 range. Standalone `^1^C_{F10}` correctly rejects with `drive number must be 1-7`. The check should propagate into recipe-prereq positions. Workaround: `mut_corrupt_drive_subscript` skips recipe seeds.

2. **Recipe prereq noetic indices not typechecked.** `Θ(Ω_x) = 0.7*^11^C → Ω_x` compiles cleanly even though `^11` is out of the 0–9 range. Standalone `^11` correctly rejects with `operator index must be 0-9`. Same propagation issue as the drive case. Workaround: `mut_unknown_noetic_index` skips recipe seeds.

3. **Right-side `^N^D|Ω_xxx` in cross-register expressions accepts structurally bad domain/noetic.** `(^9^O|f × ^9^O|E) = ^9^|Ω_judgment` and `(^8|f × ^8|A) = ^10|Ω_trust` both compile cleanly. The `|Ω_xxx` register-or-name path appears to swallow malformed left-of-pipe content. Workaround: `mut_dangling_caret`, `mut_unknown_noetic_index`, and `mut_unknown_domain` filter out the `|Ω_…` site when picking a mutation target.
