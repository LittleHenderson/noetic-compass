# Wave 2.5 Clean Subset Review Pack

Date: 2026-05-08
Source: cas-synthetic/data/path_d/wave3_step2_5_clean_current_validators_20260508T110453Z.jsonl
Sample plan: 25 deterministic stratified records (2 per category + extra weak-bucket coverage), seed=17.
Purpose: human-read the post-filter clean subset before promotion. Check for structural preservation, no CAS jargon leakage, and natural-but-faithful English.

## 1. binary_composition ? seed_binary_composition_00240

CAS:
```text
^2^C × ^6^C
```

English:
> Something you are drawn to in the cognitive realm merged into breaking down an idea in the cognitive realm.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_binary_composition

## 2. binary_composition ? seed_binary_composition_00628

CAS:
```text
^3^O -> ^1^O
```

English:
> A state in which you are pushed away from something in the operational arena transforms into a state in which you are paying attention in the operational arena.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_rpm_chain, cas_to_english_binary_composition

## 3. cross_register_omega ? seed_cross_register_omega_00538

CAS:
```text
(^3^E|f × ^3^E|A) = ^3^E|Ω_refusal
```

English:
> An aversion in evaluative judgment expressed through felt emotion and analytical reasoning, with those 2 modes fusing into the outcome called refusal.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_cross_register_omega

## 4. cross_register_omega ? seed_cross_register_omega_00485

CAS:
```text
(^1^O|E × ^1^O|f × ^1^O|T) = ^1^O|Ω_calm
```

English:
> Paying attention in operational behavior expressed through embodied sensorimotor awareness, felt emotion, and transcendent strategic perspective, with those 3 modes fusing into the outcome called calm.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_cross_register_omega

## 5. diagram_export ? seed_diagram_export_00149

CAS:
```text
export let alpha_0148 = ^8^O -> ^0^O
```

English:
> Export "alpha_0148" as a transformation: something that triggered a memory flows into a thought.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_rpm_chain, cas_to_english_let_binding, cas_to_english_diagram_export

## 6. diagram_export ? seed_diagram_export_00283

CAS:
```text
export let tau_0282 = Theta(Omega_explanation) = 1*^2^O + 1*^0^O -> Omega_explanation
```

English:
> Export tau_0282 as a recipe that produces the outcome called explanation. The recipe combines two inputs: first, 1 unit of something that speaks to me in an operational way, and second, 1 unit of a thought in an operational way. Together, these produce the named outcome explanation.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_recipe_preservation, cas_to_english_recipe_per_occurrence, cas_to_english_let_binding, cas_to_english_diagram_export

## 7. fractal_sequence ? seed_fractal_sequence_00125

CAS:
```text
Phi⟨2:4:8:0⟩
```

English:
> A fractal sequence where being drawn to something, then something that struck a chord, then something that triggered a memory, and finally a thought.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_fractal_k_indices

## 8. fractal_sequence ? seed_fractal_sequence_00071

CAS:
```text
Phi<6:2>
```

English:
> A fractal sequence where breaking it down leads to being drawn to something.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_fractal_k_indices

## 9. inversion ? seed_inversion_00044

CAS:
```text
StateCluster{^1^P, ^1^C, ^1^E, ^1^O}
```

English:
> A cognitive state comprising four simultaneous operations: paying attention in a principled way, using your head in a cognitive way, becoming aware through evaluative judgment, and acting in an operational way.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_diagram_export, cas_to_english_inversion

## 10. inversion ? seed_inversion_00024

CAS:
```text
^5^C -> ^5^E
```

English:
> Who one is, shaped by cognitive thinking, becomes evaluative judgment.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_rpm_chain, cas_to_english_inversion

## 11. let_binding ? seed_let_binding_00300

CAS:
```text
let vsrc_0299 = ^9^O; let vtgt_0299 = ^9^O; vsrc_0299 -> vtgt_0299
```

English:
> Let "vsrc_0299" name something that just clicked in an operational behavioral frame. Let "vtgt_0299" name something that just clicked in an operational behavioral frame. The first flows into the second.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_rpm_chain, cas_to_english_let_binding

## 12. let_binding ? seed_let_binding_00155

CAS:
```text
let balance_0154 = ^4^E_{F5}
```

English:
> Let "balance_0154" name something that struck a chord in the realm of evaluative judgment, with self-determination as the driving need.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_let_binding

## 13. meta_logic_relation ? seed_meta_logic_relation_00482

CAS:
```text
NoeticCluster{^2, ^3, ^8, ^9} ∩ NoeticCluster{^1, ^3}
```

English:
> The set of cognitive states where something triggered a memory (operator slot 8) or spoke to you (operator slot 2) or rubs the wrong way (operator slot 3) or popped into mind (operator slot 9), intersected with the set where paying attention (operator slot 1) or rubs the wrong way (operator slot 3) occurred—in other words, the cognitive states common to both groups.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_diagram_export

## 14. meta_logic_relation ? seed_meta_logic_relation_00741

CAS:
```text
|NoeticCluster{^0, ^6, ^7}|
```

English:
> A cognitive cluster gathering together three operator slots: a thought taking shape, the act of breaking down an idea, and practiced execution working in concert.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_diagram_export

## 15. recipe ? seed_recipe_00223

CAS:
```text
Θ(Ω_rest_23) = 0.7*^5^C + 1*^2^C + 2*^3^P → Ω_rest_23 + 0.05*Λ·Ω_rest_side
```

English:
> To produce the outcome called rest_23, take 0.7 of who you are shaped by in cognitive thinking, add 1 of something drawn to you in cognitive thinking, and add 2 of something pushed away from you in foundational thinking — together these inputs yield the outcome called rest_23, with a side effect of 0.05 times the outcome called rest_side.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_recipe_preservation, cas_to_english_recipe_per_occurrence

## 16. recipe ? seed_recipe_00109

CAS:
```text
Θ(Ω_explanation_09) = 2*^7^O_{F7}|E + 0.5*^6^C_{F1} → Ω_explanation_09
```

English:
> To produce the outcome called explanation_09, combine 2 times the practice-makes-perfect operational behavior pulled by purpose and meaning with 0.5 times the breaking-down cognitive thinking pulled by unity and cohesion.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_recipe_preservation, cas_to_english_recipe_per_occurrence

## 17. rpm_chain ? seed_rpm_chain_00129

CAS:
```text
let stageA0_7_0128 = ^0^P; let stageD7_7_0128 = ^5^P_{F7}; let stageW7_7_0128 = ^5^C_{F7}; let stageP7_7_0128 = ^5^E_{F7}; stageD7_7_0128 -> stageW7_7_0128
```

English:
> Let stageA0_7_0128 name a foundational thought, stageD7_7_0128 name who one is shaped by a need for purpose and meaning in the evaluative arena, stageW7_7_0128 name cognitive thinking shaped by a need for purpose and meaning in the evaluative arena, and stageP7_7_0128 name evaluative judgment shaped by a need for purpose and meaning in the evaluative arena. stageD7_7_0128 leads to stageW7_7_0128.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_rpm_chain, cas_to_english_let_binding

## 18. rpm_chain ? seed_rpm_chain_00344

CAS:
```text
let stageA0_7_0343 = ^0^P; let stageD7_7_0343 = ^7^P_{F7}; let stageW7_7_0343 = ^7^C_{F7}; let stageP7_7_0343 = ^7^E_{F7}; stageA0_7_0343 -> stageD7_7_0343
```

English:
> Let stageA0_7_0343 name a foundational thought, stageD7_7_0343 name muscle memory in the arena of purpose, stageW7_7_0343 name practiced rhythm in the cognitive arena, and stageP7_7_0343 name practiced rhythm in the evaluative arena. stageA0_7_0343 then leads to stageD7_7_0343.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_rpm_chain, cas_to_english_let_binding

## 19. state_literal ? seed_state_literal_00783

CAS:
```text
^7^O_{F5}|A
```

English:
> Practice and muscle memory in operational behavior, driven by a need for agency and self-determination, expressed through an analytical way of thinking.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_state_literal_preservation

## 20. state_literal ? seed_state_literal_00377

CAS:
```text
^2^O|f
```

English:
> Something that speaks to you in operational behavior, expressed through an affective and felt way.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_state_literal_preservation

## 21. rpm_chain ? seed_rpm_chain_00322

CAS:
```text
let stageA0_5_0321 = ^0^P; let stageD5_5_0321 = ^3^P_{F5}; let stageW5_5_0321 = ^3^C_{F5}; let stageP5_5_0321 = ^3^E_{F5}; stageA0_5_0321 -> stageD5_5_0321
```

English:
> Let stageA0_5_0321 name a foundational thought, let stageD5_5_0321 name something that rubs the wrong way in the evaluative arena around the need for agency and self-determination, let stageW5_5_0321 name a cognitive pattern that rubs the wrong way around the need for agency and self-determination, and let stageP5_5_0321 name a judging response that rubs the wrong way around the need for agency and self-determination. stageA0_5_0321 then leads to stageD5_5_0321.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_rpm_chain, cas_to_english_let_binding

## 22. recipe ? seed_recipe_00171

CAS:
```text
Θ(Ω_engagement_71) = 0.5*^4^E_{F1}|E + 1*^6^E|f + 1*^7^E_{F1} → Ω_engagement_71 + 0.05*Λ·Ω_production_side
```

English:
> To produce the outcome called engagement_71, take 0.5 of something that struck a chord in evaluative judgment tied to cohesion, add 1 of breaking down an idea in evaluative judgment, and add 1 of practice making perfect in evaluative judgment tied to cohesion. These inputs together yield engagement_71, which also contributes 0.05 to a secondary effect on the outcome called production_side.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_recipe_preservation, cas_to_english_recipe_per_occurrence

## 23. meta_logic_relation ? seed_meta_logic_relation_00154

CAS:
```text
NoeticCluster{^1, ^3, ^4, ^5, ^8}
```

English:
> A cluster of five cognitive operations brought together: becoming aware, pushed away from something, struck a chord, shaped by experience, and one thing leading to another—these form an integrated set of mental states that relate to each other in a structured way.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_diagram_export

## 24. inversion ? seed_inversion_00050

CAS:
```text
StateVariantCluster{^2^P_{F2}, ^2^C_{F2}, ^2^E_{F2}, ^2^O_{F2}}
```

English:
> A cluster of four cognitive states, each drawn toward wisdom and insight: one expressed through principled thinking, one through mental reasoning, one through evaluative judgment, and one through operational behavior.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_diagram_export, cas_to_english_inversion

## 25. state_literal ? seed_state_literal_00186

CAS:
```text
^4^O_{F3}
```

English:
> Something that struck a chord in operational behavior, driven by a need for vitality.

Post-filter validators: no_cas_jargon_leakage, no_phantom_outcome_framing, cas_to_english_state_literal_preservation
