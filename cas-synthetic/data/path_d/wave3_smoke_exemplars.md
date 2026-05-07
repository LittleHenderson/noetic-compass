# Path D Wave 3 — Smoke run quality exemplars

Generated 2026-05-07T22:32:37Z. Best/worst 5 samples per slot for human review. Best = highest score, Worst = lowest score, where score reflects compiler-validity (for english_to_cas), reply length sanity, leakage status, and single-line shape.

## Slot: `cas_to_english` (n=1495)

### Best 5

- **wave3_cas_to_english_00001** (source: `seed_diagram_export_00414`, category/class: `diagram_export`)
  - reply: This represents a stored cognitive snapshot labeled alpha_0413. It captures a specific mental state or moment of understanding, preserved as a reference point that can be retrieved and examined later. Think of it as a mental bookmark or saved checkpoint of a particular thought or...
  - leakage: False, cost: $0.00047

- **wave3_cas_to_english_00002** (source: `seed_fractal_sequence_00347`, category/class: `fractal_sequence`)
  - reply: A recursive pattern that unfolds in seven distinct steps, beginning and ending at the same point, creating a complete cycle. It describes how something expands through intermediate stages before returning to its origin, like a spiral that closes on itself.
  - leakage: False, cost: $0.00044

- **wave3_cas_to_english_00003** (source: `seed_meta_logic_relation_00208`, category/class: `meta_logic_relation`)
  - reply: A collection of four interconnected thoughts or mental states (the 4th, 5th, 8th, and 9th ones in sequence) that belong together as a unified group within someone's thinking. These mental elements are bound together and function as a coherent whole.
  - leakage: False, cost: $0.00050

- **wave3_cas_to_english_00004** (source: `seed_fractal_sequence_00380`, category/class: `fractal_sequence`)
  - reply: A pattern that unfolds across six levels of detail, where the eighth element relates to the ninth in a way that repeats at different scales—like how a coastline looks similar whether you're zooming in or out, each layer containing echoes of the whole.
  - leakage: False, cost: $0.00047

- **wave3_cas_to_english_00005** (source: `seed_let_binding_00408`, category/class: `let_binding`)
  - reply: We're setting up a connection between two things. First, we identify something at position 1, then something at position 9. We then establish that the first thing points to or leads to the second thing.
  - leakage: False, cost: $0.00044

### Worst 5

- **wave3_cas_to_english_01498** (source: `seed_fractal_sequence_00215`, category/class: `fractal_sequence`)
  - reply: A recursive mental pattern that cycles through nine distinct conceptual layers, with emphasis points at the seventh and fourth levels, creating a self-similar structure that repeats at different scales of thought. It describes how a complex idea unfolds and mirrors itself at smal...
  - leakage: False, cost: $0.00048

- **wave3_cas_to_english_01492** (source: `seed_meta_logic_relation_00456`, category/class: `meta_logic_relation`)
  - reply: A collection of related mental states where one dominant configuration (appearing six times with high certainty) contrasts with a weaker alternative (appearing three times with lower certainty). These represent different ways the mind could organize the same information, with one...
  - leakage: False, cost: $0.00051

- **wave3_cas_to_english_01468** (source: `seed_diagram_export_00450`, category/class: `diagram_export`)
  - reply: A cognitive state is being defined where two distinct mental processes—one of high complexity and another of moderate complexity—combine to produce a withdrawal response. This represents how different levels of cognitive engagement work together to generate the behavioral outcome...
  - leakage: False, cost: $0.00049

- **wave3_cas_to_english_01463** (source: `seed_recipe_00448`, category/class: `recipe`)
  - reply: A translation process combines four units of carbon with five units of oxygen to produce a translation result. This main reaction generates the intended output while also creating a minor side effect—about fifteen percent of the energy or resources involved gets diverted into a s...
  - leakage: False, cost: $0.00051

- **wave3_cas_to_english_01452** (source: `seed_recipe_00204`, category/class: `recipe`)
  - reply: This describes a self-correction process that combines three elements: a strong primary focus on external feedback, a moderate level of abstract pattern recognition, and a significant application of deliberate conscious effort. Together, these components activate the overall self...
  - leakage: False, cost: $0.00049

## Slot: `english_to_cas` (n=1462)

### Best 5

- **wave3_english_to_cas_00005** (source: `seed_diagram_export_00374`, category/class: `diagram_export`)
  - generated CAS: `export let xi_0373 = ^3^C -> ^0^C`
  - compiler_validated: True (attempts: 1)
  - reply: export let xi_0373 = ^3^C -> ^0^C
  - leakage: False, cost: $0.00085

- **wave3_english_to_cas_00006** (source: `seed_meta_logic_relation_00269`, category/class: `meta_logic_relation`)
  - generated CAS: `StateCluster{^7^E, ^1^E, ^4^P, ^8^O}`
  - compiler_validated: True (attempts: 1)
  - reply: StateCluster{^7^E, ^1^E, ^4^P, ^8^O}
  - leakage: False, cost: $0.00103

- **wave3_english_to_cas_00007** (source: `seed_meta_logic_relation_00087`, category/class: `meta_logic_relation`)
  - generated CAS: `NoeticCluster{^0, ^1, ^3, ^4, ^6, ^8}`
  - compiler_validated: True (attempts: 1)
  - reply: NoeticCluster{^0, ^1, ^3, ^4, ^6, ^8}
  - leakage: False, cost: $0.00100

- **wave3_english_to_cas_00008** (source: `seed_meta_logic_relation_00061`, category/class: `meta_logic_relation`)
  - generated CAS: `NoeticCluster{^0, ^4, ^5}`
  - compiler_validated: True (attempts: 1)
  - reply: NoeticCluster{^0, ^4, ^5}
  - leakage: False, cost: $0.00081

- **wave3_english_to_cas_00009** (source: `seed_cross_register_omega_00607`, category/class: `cross_register_omega`)
  - generated CAS: `(^9^E|A × ^9^E|E × ^9^E|T) = ^9^E|Ω_resolve`
  - compiler_validated: True (attempts: 1)
  - reply: (^9^E|A × ^9^E|E × ^9^E|T) = ^9^E|Ω_resolve
  - leakage: False, cost: $0.00119

### Worst 5

- **wave3_english_to_cas_01445** (source: `seed_meta_logic_relation_00094`, category/class: `meta_logic_relation`)
  - generated CAS: `NoeticCluster{^0, ^2, ^5, ^6, ^7, ^9}`
  - compiler_validated: True (attempts: 3)
  - reply: NoeticCluster{^0, ^2, ^5, ^6, ^7, ^9}
  - leakage: False, cost: $0.00364

- **wave3_english_to_cas_00900** (source: `seed_inversion_00022`, category/class: `inversion`)
  - generated CAS: `^3^C -> ^3^E`
  - compiler_validated: True (attempts: 2)
  - reply: ^3^C -> ^3^E
  - leakage: False, cost: $0.00155

- **wave3_english_to_cas_01137** (source: `seed_state_literal_00044`, category/class: `state_literal`)
  - generated CAS: `^8^C`
  - compiler_validated: True (attempts: 1)
  - reply: ^8^C
  - leakage: False, cost: $0.00061

- **wave3_english_to_cas_00771** (source: `seed_state_literal_00005`, category/class: `state_literal`)
  - generated CAS: `^4`
  - compiler_validated: True (attempts: 1)
  - reply: ^4
  - leakage: False, cost: $0.00055

- **wave3_english_to_cas_00579** (source: `seed_state_literal_00008`, category/class: `state_literal`)
  - generated CAS: `^7`
  - compiler_validated: True (attempts: 1)
  - reply: ^7
  - leakage: False, cost: $0.00055

## Slot: `invalid_to_explanation` (n=997)

### Best 5

- **wave3_invalid_to_explanation_00001** (source: `inv_seed_fractal_sequence_00138_fractal_00185`, category/class: `fractal`)
  - reply: The expression tries to open a comparison or range bracket but leaves it completely empty — there's nothing inside. The system expects at least one number to appear there, but instead it immediately hits the closing bracket. Something meaningful needs to go between those angle br...
  - leakage: False, cost: $0.00146

- **wave3_invalid_to_explanation_00004** (source: `inv_seed_recipe_00456_parse_00095`, category/class: `parse`)
  - reply: The expression tries to open a grouping and then immediately uses an assignment inside it, but that spot only allows a value or calculation, not an assignment. The system expected the grouping to close first before any assignment could happen, so it got confused and stopped readi...
  - leakage: False, cost: $0.00168

- **wave3_invalid_to_explanation_00009** (source: `inv_seed_fractal_sequence_00282_parse_00704`, category/class: `parse`)
  - reply: The expression opens a structured block with some kind of angled bracket but never closes it. The compiler reached the end of the input still waiting for the closing bracket that should wrap up the block. It's like opening a parenthesis in a sentence and never
  - leakage: False, cost: $0.00149

- **wave3_invalid_to_explanation_00011** (source: `inv_seed_state_literal_00937_rpm_00048`, category/class: `rpm`)
  - reply: The expression sets up a value and then tries to pass it along to a destination that was never defined anywhere. The receiving end simply doesn't exist, so the system has no idea where to send the result. It's like addressing a letter to someone who has no record of ever existing...
  - leakage: False, cost: $0.00167

- **wave3_invalid_to_explanation_00012** (source: `inv_seed_fractal_sequence_00254_fractal_00515`, category/class: `fractal`)
  - reply: The sequence of numbers inside contains a negative value at the sixth position, but this particular structure only accepts plain, positive whole numbers throughout. A negative number is not allowed there, so the system rejects it as soon as it encounters the minus sign.
  - leakage: False, cost: $0.00150

### Worst 5

- **wave3_invalid_to_explanation_00997** (source: `inv_seed_recipe_00325_recipe_00118`, category/class: `recipe`)
  - reply: The recipe lists ingredients and amounts needed to produce a result, but one of the required quantities isn't actually a number — it's an abstract, non-measurable concept. The system expects a concrete figure it can work with, and instead finds something it has no way to count or...
  - leakage: False, cost: $0.00181

- **wave3_invalid_to_explanation_00995** (source: `inv_seed_meta_logic_relation_00384_parse_00381`, category/class: `parse`)
  - reply: The second item inside the grouping is actually two separate items crammed together without a comma between them. The compiler reached what it thought was the closing boundary of the group, but instead found an unexpected extra element it wasn't prepared for. Adding a separator b...
  - leakage: False, cost: $0.00163

- **wave3_invalid_to_explanation_00994** (source: `inv_seed_meta_logic_relation_00320_meta_logic_00600`, category/class: `meta_logic`)
  - reply: The expression claims that one group of concepts is entirely contained within another, but that isn't true. The first group includes an idea that simply doesn't exist in the second group, so the "fits inside" relationship breaks down. You can't say something is a subset of a coll...
  - leakage: False, cost: $0.00188

- **wave3_invalid_to_explanation_00993** (source: `inv_seed_state_literal_00773_rpm_00627`, category/class: `rpm`)
  - reply: The expression tries to move from a higher-order level of abstraction down to a lower, more concrete one, but those two levels aren't directly connected in a way that permits that descent. It's like trying to jump from a general concept straight to a specific detail by skipping a...
  - leakage: False, cost: $0.00193

- **wave3_invalid_to_explanation_00992** (source: `inv_seed_meta_logic_relation_00655_rpm_00483`, category/class: `rpm`)
  - reply: The expression tries to move something from an observing state into a conceptualizing state, but those two mental activities belong to different levels of a strict hierarchy. Observation sits above conceptualization, and the rules only allow movement downward in one permitted dir...
  - leakage: False, cost: $0.00187

## Slot: `invalid_to_corrected` (n=991)

### Best 5

- **wave3_invalid_to_corrected_00002** (source: `inv_seed_diagram_export_00171_recipe_00777`, category/class: `recipe`)
  - reply: The arrow used to introduce the recipe's output was the wrong kind — it implied a transformation rather than a definition. Replacing it with an equals sign correctly identifies this as a description of what the verification process looks like, not an instruction to convert it int...
  - leakage: False, cost: $0.00175

- **wave3_invalid_to_corrected_00005** (source: `inv_seed_fractal_sequence_00525_fractal_00159`, category/class: `fractal`)
  - reply: The sixth value in the sequence was written as a negative number, which isn't allowed in this position. The fix replaces it with a positive value of seven. Negative numbers are simply not permitted at that particular slot — only whole positive numbers are valid there.
  - leakage: False, cost: $0.00163

- **wave3_invalid_to_corrected_00007** (source: `inv_seed_fractal_sequence_00337_fractal_00347`, category/class: `fractal`)
  - reply: The step value at the end of the range cannot be negative here. A negative number was provided, but only a positive whole number is allowed in that position. Replacing it with a positive value fixes the problem.
  - leakage: False, cost: $0.00144

- **wave3_invalid_to_corrected_00012** (source: `inv_seed_recipe_00415_parse_00083`, category/class: `parse`)
  - reply: The opening function call was missing its closing parenthesis before the equals sign. The name being passed in was written as if it were part of an assignment rather than an argument to the function. Adding the closing parenthesis right after the argument, before the equals sign,...
  - leakage: False, cost: $0.00185

- **wave3_invalid_to_corrected_00013** (source: `inv_seed_fractal_sequence_00130_fractal_00119`, category/class: `fractal`)
  - reply: The fourth numerical slot contained a negative value, which this type of expression does not allow. Replacing it with a positive number — specifically nine instead of negative one — makes the expression valid. Negative numbers are simply not permitted in that position.
  - leakage: False, cost: $0.00158

### Worst 5

- **wave3_invalid_to_corrected_00988** (source: `inv_seed_meta_logic_relation_00366_admissibility_00426`, category/class: `admissibility`)
  - reply: The original expression wrongly implied that two distinct mental qualities at the same level were fusing into something new. Since no genuine fusion was happening, the fix was to simply list all the relevant mental states together as a cluster, without claiming any transformative...
  - leakage: False, cost: $0.00223

- **wave3_invalid_to_corrected_00984** (source: `inv_seed_recipe_00243_parse_00028`, category/class: `parse`)
  - reply: The statement was incomplete — it listed the ingredients and steps but never said what they were meant to produce. The fix was simply adding a destination at the end, making clear what the whole combination is supposed to result in. Without that target, the system didn't know whe...
  - leakage: False, cost: $0.00193

- **wave3_invalid_to_corrected_00979** (source: `inv_seed_state_literal_00384_rpm_00234`, category/class: `rpm`)
  - reply: The starting point referenced something that hadn't been defined anywhere, so the system had nothing to work with. The fix replaces that missing reference with a concrete, self-contained value — specifically a third-level grouping tied to a known category — so the expression can ...
  - leakage: False, cost: $0.00168

- **wave3_invalid_to_corrected_00977** (source: `inv_seed_recipe_00472_rpm_00099`, category/class: `rpm`)
  - reply: The error occurred because the system tried to move directly from one category of thing to a fundamentally incompatible category — like jumping from a measurement of distance to a measurement of temperature without conversion. The fix introduces proper intermediate steps and weig...
  - leakage: False, cost: $0.00211

- **wave3_invalid_to_corrected_00976** (source: `inv_seed_recipe_00388_parse_00564`, category/class: `parse`)
  - reply: A label identifying a specific category was accidentally left blank in the middle of the formula. The fix was simply inserting the missing category letter in that spot, giving the parser something concrete to attach the following details to instead of encountering an unexpected s...
  - leakage: False, cost: $0.00193
