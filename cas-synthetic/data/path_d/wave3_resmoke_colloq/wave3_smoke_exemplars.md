# Path D Wave 3 — Smoke run quality exemplars

Generated 2026-05-07T23:17:34Z. Best/worst 5 samples per slot for human review. Best = highest score, Worst = lowest score, where score reflects compiler-validity (for english_to_cas), reply length sanity, leakage status, and single-line shape.

## Slot: `cas_to_english` (n=119)

### Best 5

- **wave3_cas_to_english_00001** (source: `seed_meta_logic_relation_00455`, category/class: `meta_logic_relation`)
  - reply: Your sense of who you are—shaped by your past experiences and what defines you—connects strongly with how you evaluate and judge things, and that resonates deeply with how you actually respond and behave.
  - leakage: False, cost: $0.00119

- **wave3_cas_to_english_00002** (source: `seed_let_binding_00457`, category/class: `let_binding`)
  - reply: You start by paying attention to something evaluative, then you break that down into its component parts to examine what's underneath.
  - leakage: False, cost: $0.00113

- **wave3_cas_to_english_00003** (source: `seed_state_literal_00473`, category/class: `state_literal`)
  - reply: One thing led to another and brought to mind something connected to how you actually behave.
  - leakage: False, cost: $0.00106

- **wave3_cas_to_english_00004** (source: `seed_recipe_00202`, category/class: `recipe`)
  - reply: To synthesize something, you need twice as much of what triggered the memory combined with half as much of what struck a chord. That produces the synthesis itself, plus a small amount of residual rest-state activity as a side effect.
  - leakage: False, cost: $0.00126

- **wave3_cas_to_english_00005** (source: `seed_let_binding_00051`, category/class: `let_binding`)
  - reply: One thing leads to another—a judgment came to mind in the evaluative domain.
  - leakage: False, cost: $0.00106

### Worst 5

- **wave3_cas_to_english_00047** (source: `seed_recipe_00407`, category/class: `recipe`)
  - reply: This judgment forms when three things combine: getting into a groove with something (practice-based familiarity), who you are as a person (your accumulated experiences), and who you are as a person again (your core sense of self). The first element carries moderate weight, while ...
  - leakage: False, cost: $0.00134

- **wave3_cas_to_english_00014** (source: `seed_fractal_sequence_00492`, category/class: `fractal_sequence`)
  - reply: A sequence of four foundational principles unfolds in a particular order: one leads to the next, then the third, then back to the first, cycling through the second and third again before concluding. The pattern moves through these elements as: fourth, fifth, seventh, first, third...
  - leakage: False, cost: $0.00133

- **wave3_cas_to_english_00120** (source: `seed_inversion_00068`, category/class: `inversion`)
  - reply: When you push away from something in your thinking, push away from it in how you understand it, and push away from it in how you experience it together, that creates a unified state of rejection across all three dimensions.
  - leakage: False, cost: $0.00121

- **wave3_cas_to_english_00119** (source: `seed_binary_composition_00440`, category/class: `binary_composition`)
  - reply: You're applying a foundational principle to shape how you think about something, and that structured thinking then influences what you actually do.
  - leakage: False, cost: $0.00110

- **wave3_cas_to_english_00118** (source: `seed_fractal_sequence_00200`, category/class: `fractal_sequence`)
  - reply: A foundational thought about how eight distinct principles connect in sequence—starting from a core idea, moving through four intermediate points, and arriving at a final pairing that recalls the beginning, creating a cyclical pattern of reasoning.
  - leakage: False, cost: $0.00121

## Slot: `english_to_cas` (n=116)

### Best 5

- **wave3_english_to_cas_00001** (source: `seed_cross_register_omega_00582`, category/class: `cross_register_omega`)
  - generated CAS: `(^8^O|E × ^8^O|A × ^8^O|f) = ^8^O|Ω_discernment`
  - compiler_validated: True (attempts: 1)
  - reply: (^8^O|E × ^8^O|A × ^8^O|f) = ^8^O|Ω_discernment
  - leakage: False, cost: $0.00122

- **wave3_english_to_cas_00002** (source: `seed_rpm_chain_00340`, category/class: `rpm_chain`)
  - generated CAS: `let stageA0_1_0339 = ^0^P; let stageD1_1_0339 = ^1^P_{F1}; let stageW1_1_0339 = ^1^C_{F1}; let stageP1_1_0339 = ^1^E_{F1}; stageW1_1_0339 -> stageP1_1_0339`
  - compiler_validated: True (attempts: 1)
  - reply: let stageA0_1_0339 = ^0^P; let stageD1_1_0339 = ^1^P_{F1}; let stageW1_1_0339 = ^1^C_{F1}; let stageP1_1_0339 = ^1^E_{F1}; stageW1_1_0339 -> stageP1_1_0339
  - leakage: False, cost: $0.00239

- **wave3_english_to_cas_00003** (source: `seed_recipe_00183`, category/class: `recipe`)
  - generated CAS: `Θ(Ω_decision_83) = 2*^4^C_{F7} + 0.7*^6^C → Ω_decision_83 + 0.15*Λ·Ω_reasoning_side`
  - compiler_validated: True (attempts: 1)
  - reply: Θ(Ω_decision_83) = 2*^4^C_{F7} + 0.7*^6^C → Ω_decision_83 + 0.15*Λ·Ω_reasoning_side
  - leakage: False, cost: $0.00164

- **wave3_english_to_cas_00004** (source: `seed_let_binding_00397`, category/class: `let_binding`)
  - generated CAS: `let vsrc_0396 = ^5^O; let vtgt_0396 = ^3^O; vsrc_0396 -> vtgt_0396`
  - compiler_validated: True (attempts: 1)
  - reply: let vsrc_0396 = ^5^O; let vtgt_0396 = ^3^O; vsrc_0396 -> vtgt_0396
  - leakage: False, cost: $0.00123

- **wave3_english_to_cas_00005** (source: `seed_meta_logic_relation_00403`, category/class: `meta_logic_relation`)
  - generated CAS: `StateVariantCluster{^5^O|E, ^5^P_{F6}|E}`
  - compiler_validated: True (attempts: 1)
  - reply: StateVariantCluster{^5^O|E, ^5^P_{F6}|E}
  - leakage: False, cost: $0.00104

### Worst 5

- **wave3_english_to_cas_00121** (source: `seed_fractal_sequence_00014`, category/class: `fractal_sequence`)
  - generated CAS: `Φ<2:1:6:9>`
  - compiler_validated: True (attempts: 1)
  - reply: Φ<2:1:6:9>
  - leakage: False, cost: $0.00070

- **wave3_english_to_cas_00119** (source: `seed_inversion_00025`, category/class: `inversion`)
  - generated CAS: `^0^E -> ^0^O`
  - compiler_validated: True (attempts: 1)
  - reply: ^0^E -> ^0^O
  - leakage: False, cost: $0.00070

- **wave3_english_to_cas_00112** (source: `seed_binary_composition_00628`, category/class: `binary_composition`)
  - generated CAS: `^3^O -> ^1^O`
  - compiler_validated: True (attempts: 1)
  - reply: ^3^O -> ^1^O
  - leakage: False, cost: $0.00071

- **wave3_english_to_cas_00110** (source: `seed_fractal_sequence_00255`, category/class: `fractal_sequence`)
  - generated CAS: `Φ<0:2:0>`
  - compiler_validated: True (attempts: 1)
  - reply: Φ<0:2:0>
  - leakage: False, cost: $0.00067

- **wave3_english_to_cas_00109** (source: `seed_inversion_00018`, category/class: `inversion`)
  - generated CAS: `^5^P -> ^5^C`
  - compiler_validated: True (attempts: 1)
  - reply: ^5^P -> ^5^C
  - leakage: False, cost: $0.00070

## Slot: `invalid_to_explanation` (n=80)

### Best 5

- **wave3_invalid_to_explanation_00001** (source: `inv_seed_meta_logic_relation_00699_rpm_00806`, category/class: `rpm`)
  - reply: The expression tries to draw a connection from one named stage to another, but the starting stage has never been defined anywhere in the system. Because the source of the connection doesn't exist, the whole statement is meaningless — you can't connect from something the system ha...
  - leakage: False, cost: $0.00232

- **wave3_invalid_to_explanation_00003** (source: `inv_seed_meta_logic_relation_00348_parse_00841`, category/class: `parse`)
  - reply: The expression opens a grouped collection of items but never closes it — the ending bracket that should seal the group is simply missing. The compiler reached the end of the text still waiting for that closing marker, so it cannot treat the collection as complete and valid.
  - leakage: False, cost: $0.00224

- **wave3_invalid_to_explanation_00004** (source: `inv_seed_state_literal_00772_admissibility_00260`, category/class: `admissibility`)
  - reply: The expression tries to use 11 as a selector for a particular category, but only single-digit selectors — zero through nine — are permitted. Since 11 has two digits, the system cannot accept it. To fix this, the selector would need to be replaced with a valid single-digit value.
  - leakage: False, cost: $0.00240

- **wave3_invalid_to_explanation_00007** (source: `inv_seed_diagram_export_00202_parse_00673`, category/class: `parse`)
  - reply: The expression opens a grouping that is never closed. Something is meant to be wrapped together inside a pair of curly brackets, but the closing bracket is missing entirely. The text simply runs out before the structure is finished, leaving the whole thing incomplete and unreadab...
  - leakage: False, cost: $0.00231

- **wave3_invalid_to_explanation_00011** (source: `inv_seed_recipe_00372_recipe_00448`, category/class: `recipe`)
  - reply: One of the ingredients listed in this self-correction procedure is missing a required number that should indicate how much of it to use. Without that quantity, the system cannot process the instruction — it found a label where it expected a plain number.
  - leakage: False, cost: $0.00231

### Worst 5

- **wave3_invalid_to_explanation_00080** (source: `inv_seed_rpm_chain_00030_admissibility_00130`, category/class: `admissibility`)
  - reply: The expression tries to combine three separate mental states using an operator that is only valid when those states genuinely merge into something new. Because the three states remain distinct and no new unified result is produced, the combination is not permitted. To be valid, t...
  - leakage: False, cost: $0.00324

- **wave3_invalid_to_explanation_00079** (source: `inv_seed_diagram_export_00011_recipe_01126`, category/class: `recipe`)
  - reply: The expression tries to multiply two things together, but multiplication is only allowed when both items being combined are descriptions of states or conditions. Here, one of the items being multiplied is a transformation or process step, not a state description, so the multiplic...
  - leakage: False, cost: $0.00248

- **wave3_invalid_to_explanation_00078** (source: `inv_seed_state_literal_00855_parse_00720`, category/class: `parse`)
  - reply: The expression tries to specify a particular drive location using an identifier that falls outside the allowed range. Only the values one through seven are valid for that slot, but the identifier given — a two-character code starting with a letter — is not a number in that range ...
  - leakage: False, cost: $0.00247

- **wave3_invalid_to_explanation_00077** (source: `inv_seed_meta_logic_relation_00145_rpm_00919`, category/class: `rpm`)
  - reply: The expression tries to move from one category of thought to a different, incompatible category. These two categories have a strict rule: the second cannot follow from the first in a direct chain. The connection is therefore illegal because the system's rules do not allow that pa...
  - leakage: False, cost: $0.00251

- **wave3_invalid_to_explanation_00075** (source: `inv_seed_fractal_sequence_00479_fractal_00048`, category/class: `fractal`)
  - reply: The expression references a step in a sequence using the number 10, but only positions 0 through 9 are permitted. Since 10 falls outside that allowed range, the whole sequence is rejected. A careful reader would notice that the very first number listed already exceeds the maximum...
  - leakage: False, cost: $0.00249

## Slot: `invalid_to_corrected` (n=80)

### Best 5

- **wave3_invalid_to_corrected_00001** (source: `inv_seed_fractal_sequence_00569_fractal_00491`, category/class: `fractal`)
  - reply: The expression used an arrow symbol where an angle bracket was required to open the parameter list. Replacing that arrow with the correct opening bracket — and updating the first parameter from negative one to five — produces a valid expression the compiler can parse.
  - leakage: False, cost: $0.00221

- **wave3_invalid_to_corrected_00004** (source: `inv_seed_diagram_export_00264_parse_00127`, category/class: `parse`)
  - reply: The closing bracket that should end the grouping was missing, leaving the expression open and unfinished. Adding that closing bracket at the end completes the structure so the compiler knows where the grouping stops.
  - leakage: False, cost: $0.00218

- **wave3_invalid_to_corrected_00005** (source: `inv_seed_recipe_00463_admissibility_00460`, category/class: `admissibility`)
  - reply: The invalid version listed the same identifier twice inside a grouped qualifier, which is not allowed — each label in such a group must be unique. The fix removes the redundant duplicate, leaving only a single instance of that identifier in the qualifier. That makes the expressio...
  - leakage: False, cost: $0.00271

- **wave3_invalid_to_corrected_00015** (source: `inv_seed_let_binding_00057_parse_00745`, category/class: `parse`)
  - reply: The drive selector was set to a number beyond the allowed range — only values up to seven are permitted, but the value given was ten. Changing it to two brings it within the valid range and makes the expression well-formed.
  - leakage: False, cost: $0.00224

- **wave3_invalid_to_corrected_00016** (source: `inv_seed_fractal_sequence_00213_fractal_00036`, category/class: `fractal`)
  - reply: The first position in the three-part index had a value of 13, which exceeds the allowed maximum of 9. Replacing it with 7 brings all three values within the permitted range of 0 through 9, making the expression valid.
  - leakage: False, cost: $0.00237

### Worst 5

- **wave3_invalid_to_corrected_00080** (source: `inv_seed_recipe_00398_rpm_00342`, category/class: `rpm`)
  - reply: The invalid form referenced a starting point that hadn't been defined anywhere, so the system had nothing to work with. The fix replaces that undefined reference with a complete, properly structured statement that specifies weighted contributions from several recognized component...
  - leakage: False, cost: $0.00267

- **wave3_invalid_to_corrected_00079** (source: `inv_seed_fractal_sequence_00276_admissibility_00494`, category/class: `admissibility`)
  - reply: Two items at the same level of awareness were combined using an operator that implies they merge into something genuinely new. That was the error: no such fusion was defined. The fix replaces the whole construction with a single named state that properly represents an integrated ...
  - leakage: False, cost: $0.00301

- **wave3_invalid_to_corrected_00078** (source: `inv_seed_rpm_chain_00353_admissibility_00581`, category/class: `admissibility`)
  - reply: Three separate items at the same level were joined with a multiplication-style operator, implying they merge into a single new thing — but no such merged result was defined. The fix replaces that with a properly staged sequence: a starting point is named, intermediate steps are l...
  - leakage: False, cost: $0.00359

- **wave3_invalid_to_corrected_00077** (source: `inv_seed_recipe_00359_parse_00521`, category/class: `parse`)
  - reply: The equals sign was placed inside the opening parenthesis of a function call, making the parser expect a closing parenthesis instead. Moving the equals sign outside and after the closing parenthesis fixes it, so the function call is completed first and then its result is assigned...
  - leakage: False, cost: $0.00265

- **wave3_invalid_to_corrected_00075** (source: `inv_seed_rpm_chain_00366_rpm_00226`, category/class: `rpm`)
  - reply: The original expression tried to move directly from one step to another, but the starting point had never been defined — the system had no record of it existing. The fix introduces all necessary intermediate steps in sequence, properly establishing each one before referencing it,...
  - leakage: False, cost: $0.00275
