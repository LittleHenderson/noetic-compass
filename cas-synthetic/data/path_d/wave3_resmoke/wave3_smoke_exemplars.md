# Path D Wave 3 — Smoke run quality exemplars

Generated 2026-05-07T22:58:57Z. Best/worst 5 samples per slot for human review. Best = highest score, Worst = lowest score, where score reflects compiler-validity (for english_to_cas), reply length sanity, leakage status, and single-line shape.

## Slot: `cas_to_english` (n=119)

### Best 5

- **wave3_cas_to_english_00001** (source: `seed_meta_logic_relation_00289`, category/class: `meta_logic_relation`)
  - reply: A cluster of four cognitive states: one instance of Concept, three instances of Concept, one instance of Emotion, and three instances of Purpose. These states are grouped together as related elements within a single cognitive configuration.
  - leakage: False, cost: $0.00068

- **wave3_cas_to_english_00003** (source: `seed_binary_composition_00602`, category/class: `binary_composition`)
  - reply: A cognitive state oriented toward the world maps onto itself—the same state remains in place without transformation.
  - leakage: False, cost: $0.00053

- **wave3_cas_to_english_00004** (source: `seed_diagram_export_00030`, category/class: `diagram_export`)
  - reply: This expression defines a cognitive state called alpha_0029, which describes how a judgment forms. The judgment emerges from a combination of two inputs: one contribution from a foundational level and another from a higher-order level, which together produce the judgment outcome.
  - leakage: False, cost: $0.00073

- **wave3_cas_to_english_00005** (source: `seed_let_binding_00093`, category/class: `let_binding`)
  - reply: A reference point is being established and labeled. This reference point connects a specific cognitive state (marked as the first level of intensity) to a particular abstract domain, creating an anchor for subsequent cognitive operations or comparisons.
  - leakage: False, cost: $0.00066

- **wave3_cas_to_english_00006** (source: `seed_cross_register_omega_00619`, category/class: `cross_register_omega`)
  - reply: When two different ways of thinking about the same idea are brought together, they create a unified understanding that combines both perspectives.
  - leakage: False, cost: $0.00057

### Worst 5

- **wave3_cas_to_english_00091** (source: `seed_rpm_chain_00010`, category/class: `rpm_chain`)
  - reply: A basic state is set up at one level. A second state, marked as refined and involving perception, is then created at a deeper level. A third state, involving understanding at that same deeper level, is also established. A fourth state, involving experience at that deeper level, f...
  - leakage: False, cost: $0.00087

- **wave3_cas_to_english_00055** (source: `seed_recipe_00515`, category/class: `recipe`)
  - reply: The verification process combines two weighted mental operations: one involving pattern recognition at intensity level 5, weighted at 1.5 times, and another involving emotional or evaluative processing at intensity level 6, weighted at 2 times. These combine to form the complete ...
  - leakage: False, cost: $0.00076

- **wave3_cas_to_english_00011** (source: `seed_recipe_00116`, category/class: `recipe`)
  - reply: This recipe describes how engagement level 16 is constructed by combining three inputs: half-weighted contributions from a fourth-level thinking element and a fourth-level practical element, plus a one-and-a-half-weighted contribution from a fifth-level social element. These thre...
  - leakage: False, cost: $0.00080

- **wave3_cas_to_english_00002** (source: `seed_recipe_00323`, category/class: `recipe`)
  - reply: Decision 23 is formed by combining two foundational elements with one observational element. The first element is weighted twice as strongly as the second, which is weighted 1.5 times. The third element contributes equally to the first. Together, these three components determine ...
  - leakage: False, cost: $0.00079

- **wave3_cas_to_english_00120** (source: `seed_diagram_export_00146`, category/class: `diagram_export`)
  - reply: This is a grouping of three interconnected ideas or concepts, labeled as epsilon_0145, that are linked together as a unified cluster.
  - leakage: False, cost: $0.00059

## Slot: `english_to_cas` (n=117)

### Best 5

- **wave3_english_to_cas_00001** (source: `seed_diagram_export_00082`, category/class: `diagram_export`)
  - generated CAS: `export let alpha_0081 = ^2^O_{F2}`
  - compiler_validated: True (attempts: 1)
  - reply: export let alpha_0081 = ^2^O_{F2}
  - leakage: False, cost: $0.00085

- **wave3_english_to_cas_00004** (source: `seed_rpm_chain_00104`, category/class: `rpm_chain`)
  - generated CAS: `let stageA0_3_0103 = ^0^P; let stageD3_3_0103 = ^4^P_{F3}; let stageW3_3_0103 = ^4^C_{F3}; let stageP3_3_0103 = ^4^E_{F3}; stageD3_3_0103 -> stageW3_3_0103`
  - compiler_validated: True (attempts: 1)
  - reply: let stageA0_3_0103 = ^0^P; let stageD3_3_0103 = ^4^P_{F3}; let stageW3_3_0103 = ^4^C_{F3}; let stageP3_3_0103 = ^4^E_{F3}; stageD3_3_0103 -> stageW3_3_0103
  - leakage: False, cost: $0.00239

- **wave3_english_to_cas_00007** (source: `seed_recipe_00573`, category/class: `recipe`)
  - generated CAS: `Θ(Ω_rehearsal_73) = 1.5*^3^C_{F2} + 1.5*^9^E + 1.5*^7^P_{F1} → Ω_rehearsal_73 + 0.15*Λ·Ω_self_correction_side`
  - compiler_validated: True (attempts: 1)
  - reply: Θ(Ω_rehearsal_73) = 1.5*^3^C_{F2} + 1.5*^9^E + 1.5*^7^P_{F1} → Ω_rehearsal_73 + 0.15*Λ·Ω_self_correction_side
  - leakage: False, cost: $0.00204

- **wave3_english_to_cas_00009** (source: `seed_cross_register_omega_00310`, category/class: `cross_register_omega`)
  - generated CAS: `(^0^O|f × ^0^O|E) = ^0^O|Ω_refusal`
  - compiler_validated: True (attempts: 1)
  - reply: (^0^O|f × ^0^O|E) = ^0^O|Ω_refusal
  - leakage: False, cost: $0.00107

- **wave3_english_to_cas_00010** (source: `seed_diagram_export_00071`, category/class: `diagram_export`)
  - generated CAS: `export let beta_0070 = NoeticCluster{^0, ^8, ^9}`
  - compiler_validated: True (attempts: 1)
  - reply: export let beta_0070 = NoeticCluster{^0, ^8, ^9}
  - leakage: False, cost: $0.00094

### Worst 5

- **wave3_english_to_cas_00086** (source: `seed_inversion_00022`, category/class: `inversion`)
  - generated CAS: `^3^C -> ^3^E`
  - compiler_validated: True (attempts: 2)
  - reply: ^3^C -> ^3^E
  - leakage: False, cost: $0.00155

- **wave3_english_to_cas_00127** (source: `seed_state_literal_00873`, category/class: `state_literal`)
  - generated CAS: `^1^O_{F4}|A`
  - compiler_validated: True (attempts: 1)
  - reply: ^1^O_{F4}|A
  - leakage: False, cost: $0.00076

- **wave3_english_to_cas_00124** (source: `seed_binary_composition_00699`, category/class: `binary_composition`)
  - generated CAS: `^6^O -> ^4^O`
  - compiler_validated: True (attempts: 1)
  - reply: ^6^O -> ^4^O
  - leakage: False, cost: $0.00071

- **wave3_english_to_cas_00123** (source: `seed_fractal_sequence_00123`, category/class: `fractal_sequence`)
  - generated CAS: `Φ⟨0:5:7:8⟩`
  - compiler_validated: True (attempts: 1)
  - reply: Φ⟨0:5:7:8⟩
  - leakage: False, cost: $0.00077

- **wave3_english_to_cas_00117** (source: `seed_fractal_sequence_00116`, category/class: `fractal_sequence`)
  - generated CAS: `Φ⟨8:3:8:8:7:1:6:1⟩`
  - compiler_validated: True (attempts: 1)
  - reply: Φ⟨8:3:8:8:7:1:6:1⟩
  - leakage: False, cost: $0.00092

## Slot: `invalid_to_explanation` (n=80)

### Best 5

- **wave3_invalid_to_explanation_00002** (source: `inv_seed_binary_composition_00666_rpm_00399`, category/class: `rpm`)
  - reply: The expression tries to move from one abstract category into a different abstract category that it is not allowed to enter. These two categories have a strict rule: the first cannot transition into the second. Because that transition is forbidden, the connection between the two s...
  - leakage: False, cost: $0.00237

- **wave3_invalid_to_explanation_00004** (source: `inv_seed_fractal_sequence_00249_fractal_00507`, category/class: `fractal`)
  - reply: The range specification contains a negative starting point, but this system only accepts plain whole numbers in that position. A negative value is not permitted there, so the compiler stops as soon as it encounters the minus sign, unable to make sense of what follows.
  - leakage: False, cost: $0.00219

- **wave3_invalid_to_explanation_00013** (source: `inv_seed_fractal_sequence_00511_parse_00494`, category/class: `parse`)
  - reply: The two numbers inside the angle brackets need to be separated by a comma, not just a space. Without that separator, the system reads the second number as an unexpected item and cannot finish parsing the closing bracket, so the whole expression is rejected.
  - leakage: False, cost: $0.00215

- **wave3_invalid_to_explanation_00015** (source: `inv_seed_recipe_00390_recipe_01114`, category/class: `recipe`)
  - reply: The expression tries to multiply two things together, but one of them is not a state — it is a process or action. Multiplication is only permitted between states. Because one of the items being multiplied is not a state, the operation is invalid and the expression cannot be compi...
  - leakage: False, cost: $0.00239

- **wave3_invalid_to_explanation_00017** (source: `inv_seed_state_literal_01028_admissibility_01001`, category/class: `admissibility`)
  - reply: The expression tries to name a specific internal tracking slot using the label "F," but that label isn't recognized. Only four labels are valid for that kind of slot, and "F" isn't one of them. The error is caught early, during the reading phase, before any deeper processing can ...
  - leakage: False, cost: $0.00250

### Worst 5

- **wave3_invalid_to_explanation_00080** (source: `inv_seed_state_literal_00095_admissibility_00587`, category/class: `admissibility`)
  - reply: The expression tries to attach a label to something, but where a valid category or domain should appear, there is instead just a name or identifier. The system expects to be told what broad type of thing is being referenced before a specific label is given, and that required type...
  - leakage: False, cost: $0.00231

- **wave3_invalid_to_explanation_00078** (source: `inv_seed_meta_logic_relation_00415_parse_00105`, category/class: `parse`)
  - reply: The expression tries to group two items together, but the second item is malformed. Where a category label is required, the expression instead supplies something that looks like a numbered slot or position marker. The compiler cannot interpret a positional marker as a category, s...
  - leakage: False, cost: $0.00244

- **wave3_invalid_to_explanation_00077** (source: `inv_seed_recipe_00572_recipe_00902`, category/class: `recipe`)
  - reply: One part of the recipe requires a plain number to specify how much of something is needed as a starting condition, but instead of a number, the expression supplies a concept-based value that the system cannot treat as a quantity. Because the recipe cannot interpret this as a meas...
  - leakage: False, cost: $0.00248

- **wave3_invalid_to_explanation_00076** (source: `inv_seed_diagram_export_00477_admissibility_00646`, category/class: `admissibility`)
  - reply: The expression tries to point to a destination category but puts an identifier name where that category label is required. The compiler expects a recognized category marker at that position, but instead finds what looks like a name or label. Because the destination is specified i...
  - leakage: False, cost: $0.00237

- **wave3_invalid_to_explanation_00075** (source: `inv_seed_meta_logic_relation_00493_meta_logic_00427`, category/class: `meta_logic`)
  - reply: The expression tries to establish that one group fully contains another, but the second group includes an item that simply isn't present in the first group. Because that item doesn't belong to the first group, the containment claim cannot hold — the first group doesn't cover ever...
  - leakage: False, cost: $0.00250

## Slot: `invalid_to_corrected` (n=80)

### Best 5

- **wave3_invalid_to_corrected_00006** (source: `inv_seed_state_literal_00504_parse_00167`, category/class: `parse`)
  - reply: A closing bracket was missing after the group label, causing the parser to reach the end of the input without finding it. Adding that closing bracket in the correct position completes the group reference properly and allows the rest of the expression to be read as a separate link...
  - leakage: False, cost: $0.00230

- **wave3_invalid_to_corrected_00008** (source: `inv_seed_fractal_sequence_00106_fractal_00614`, category/class: `fractal`)
  - reply: The fifth slot in this five-part descriptor requires a plain number, but a letter was written there instead. Replacing that letter with the number zero makes the expression valid, because every position in this kind of descriptor must be filled with a numeric value, not an alphab...
  - leakage: False, cost: $0.00237

- **wave3_invalid_to_corrected_00012** (source: `inv_seed_meta_logic_relation_00127_meta_logic_00558`, category/class: `meta_logic`)
  - reply: The expression included a reference numbered 15, but only references numbered 0 through 9 are permitted. That out-of-range reference was removed, leaving the remaining four valid references in place.
  - leakage: False, cost: $0.00220

- **wave3_invalid_to_corrected_00014** (source: `inv_seed_fractal_sequence_00489_fractal_00126`, category/class: `fractal`)
  - reply: The third slot in the sequence requires a plain number, but a letter was written there instead. Replacing that letter with the number 5 makes the expression valid.
  - leakage: False, cost: $0.00202

- **wave3_invalid_to_corrected_00017** (source: `inv_seed_recipe_00528_recipe_01045`, category/class: `recipe`)
  - reply: The expression listed what goes into a process but never stated what that process is meant to produce. The fix adds a destination — specifying that the rehearsal event is the intended output. Without that target, the instruction was incomplete and the system had nowhere to direct...
  - leakage: False, cost: $0.00254

### Worst 5

- **wave3_invalid_to_corrected_00080** (source: `inv_seed_binary_composition_00282_rpm_00135`, category/class: `rpm`)
  - reply: The original expression tried to move directly from one abstract domain into a different, incompatible abstract domain, which the system forbids — those two domains cannot connect that way. The fix abandons that attempted transition entirely and instead combines two separate, com...
  - leakage: False, cost: $0.00278

- **wave3_invalid_to_corrected_00079** (source: `inv_seed_diagram_export_00237_recipe_00545`, category/class: `recipe`)
  - reply: The expression tried to directly reassign a variable to itself as the target of a definition, which the compiler rejected. The fix wraps that variable in a snapshot or observation wrapper, making it the subject being defined rather than a bare assignment target. That small struct...
  - leakage: False, cost: $0.00268

- **wave3_invalid_to_corrected_00078** (source: `inv_seed_state_literal_00970_parse_00471`, category/class: `parse`)
  - reply: A closing bracket was missing at the end of a grouped label. The group was opened but never closed, so the system reached the end of the expression still waiting for that closing marker. Adding the missing closing bracket immediately after the label completes the group correctly ...
  - leakage: False, cost: $0.00234

- **wave3_invalid_to_corrected_00077** (source: `inv_seed_meta_logic_relation_00084_meta_logic_00300`, category/class: `meta_logic`)
  - reply: The original expression tried to split a group of four items into only two sub-groups, but those two sub-groups together only accounted for two of the four items, leaving the remaining two items unaccounted for. A valid partition must cover every item in the original group with n...
  - leakage: False, cost: $0.00288

- **wave3_invalid_to_corrected_00076** (source: `inv_seed_state_literal_00569_rpm_00678`, category/class: `rpm`)
  - reply: The original expression tried to pass control from a starting point that had never been defined, so the system had no record of it. The fix replaces that undefined starting point with a properly declared source, making the connection valid by ensuring both ends of the link actual...
  - leakage: False, cost: $0.00245
