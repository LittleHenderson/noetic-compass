# Wave 3 v2 dry-run smoke (2026-05-08)

Hand-built 50-case smoke covering the four content-preservation failure modes the audit caught. **No API calls.** Every example output is hand-constructed; each is run through the corresponding v2 validator; the report records expected vs actual pass/fail.

Purpose: prove the validators reject the audit's known-bad cases and accept the audit's known-good shapes. This is NOT evidence that the new prompts produce faithful output at scale.

## Aggregate

- Total cases: 50
- Validator outcome correct (matches expected): 50
- Validator outcome wrong: 0

## Per-failure-mode breakdown

### `english_to_cas_verbatim`

- 13 cases (7 expected-pass, 6 expected-fail)
- Validator outcome correct: 13/13

### `fractal_count_misread`

- 12 cases (6 expected-pass, 6 expected-fail)
- Validator outcome correct: 12/12

### `invalid_to_corrected_unrelated`

- 13 cases (7 expected-pass, 6 expected-fail)
- Validator outcome correct: 13/13

### `recipe_coeff_drop`

- 12 cases (6 expected-pass, 6 expected-fail)
- Validator outcome correct: 12/12

## Per-case detail

### Case 01 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe single coeff + Ω stem present
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Θ(Ω_decision_47) = 0.7*^9^C|A → Ω_decision_47`
- `english_output`: `When 0.7 of an analytical thought-emergence combines, the production yields the outcome called decision_47.`

### Case 02 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe two coeffs + Ω stem
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Θ(Ω_reasoning_02) = 1.5*^6^E + 1.5*^6^P|T → Ω_reasoning_02`
- `english_output`: `1.5 of unpacking in evaluative judgment mixed with 1.5 of unpacking principled foundations produces the outcome called reasoning_02.`

### Case 03 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe with 0.15 leakage coeff (stems only)
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Θ(Ω_target_01) = 1*^5^P → Ω_target_01 + 0.15*Λ·Ω_side`
- `english_output`: `1 of shaped principled experience produces the outcome target_01 with a 0.15 leakage to outcome side.`

### Case 04 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe with named omega only (stem)
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Θ(Ω_focus_03) = 1*^1^P → Ω_focus_03`
- `english_output`: `1 of paying attention to a foundational principle produces the outcome called focus_03.`

### Case 05 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe with three coefficients + stem
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Θ(Ω_pipeline_88) = 0.5*^2^C + 0.3*^3^E + 0.2*^7^O → Ω_pipeline_88`
- `english_output`: `0.5 of cognitive attraction, 0.3 of evaluative aversion, and 0.2 of operational rhythm produce the outcome called pipeline_88.`

### Case 06 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe with decimal-style stem name
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Θ(Ω_v3_step_12) = 1.0*^4^P|A → Ω_v3_step_12`
- `english_output`: `1.0 of analytical resonance with a foundational principle produces the outcome called v3_step_12.`

### Case 07 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe coeff dropped
- Expected pass: `False` — Actual pass: `False`
- Validator reason: missing coefficients: ['0.7']; Ω_ prefix leaked into English output: ['Ω_d']
- `source_cas`: `Θ(Ω_decision_47) = 0.7*^9^C|A → Ω_decision_47`
- `english_output`: `An analytical thought-emergence produces the named target Ω_decision_47.`

### Case 08 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe Ω paraphrased away
- Expected pass: `False` — Actual pass: `False`
- Validator reason: missing named Ω target stems: ['reasoning_02', 'reasoning_02']
- `source_cas`: `Θ(Ω_reasoning_02) = 1.5*^6^E → Ω_reasoning_02`
- `english_output`: `1.5 of unpacking in evaluative judgment yields a reasoning outcome.`

### Case 09 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe both coefficients dropped
- Expected pass: `False` — Actual pass: `False`
- Validator reason: missing coefficients: ['1.5', '1.5']; Ω_ prefix leaked into English output: ['Ω_X']
- `source_cas`: `Θ(Ω_X) = 1.5*^6^E + 1.5*^6^P → Ω_X`
- `english_output`: `Unpacking in evaluative judgment mixes with unpacking in principled foundations to produce Ω_X.`

### Case 10 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe with 'partial' replacing 0.5
- Expected pass: `False` — Actual pass: `False`
- Validator reason: missing coefficients: ['0.5']; Ω_ prefix leaked into English output: ['Ω_f']
- `source_cas`: `Θ(Ω_focus_03) = 0.5*^1^P → Ω_focus_03`
- `english_output`: `Partial paying attention to a foundational principle produces Ω_focus_03.`

### Case 11 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe with 'mostly' replacing 0.7
- Expected pass: `False` — Actual pass: `False`
- Validator reason: missing coefficients: ['0.7']; Ω_ prefix leaked into English output: ['Ω_d']
- `source_cas`: `Θ(Ω_decision_47) = 0.7*^9^C|A → Ω_decision_47`
- `english_output`: `Mostly an analytical thought-emergence produces Ω_decision_47.`

### Case 12 — [OK] `recipe_coeff_drop` (`recipe_preservation`)

- Description: recipe Ω truncated
- Expected pass: `False` — Actual pass: `False`
- Validator reason: missing named Ω target stems: ['pipeline_88', 'pipeline_88']
- `source_cas`: `Θ(Ω_pipeline_88) = 1*^7^O → Ω_pipeline_88`
- `english_output`: `1 of operational rhythm produces a pipeline outcome.`

### Case 13 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: fractal Φ⟨9:4:7⟩ rendered as operators
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Φ⟨9:4:7⟩`
- `english_output`: `An idea popped into mind, then struck a chord, then turned into muscle memory.`

### Case 14 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: fractal Φ⟨0:1⟩ rendered as Idea→Mind
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Φ⟨0:1⟩`
- `english_output`: `A thought first sits all in your head, then you start paying attention to it.`

### Case 15 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: fractal Φ⟨3:5⟩ rendered with operator names
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Φ⟨3:5⟩`
- `english_output`: `Aversion (^3 Negative) gives way to the sum of one's experiences (^5 Female).`

### Case 16 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: fractal Φ⟨2:6⟩ with colloquialisms
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Φ⟨2:6⟩`
- `english_output`: `Drawn to an idea, then unpacking it to see what's underneath.`

### Case 17 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: fractal Φ⟨8:9⟩ trigger and effect
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Φ⟨8:9⟩`
- `english_output`: `That reminds me of something, and the thought just popped into mind.`

### Case 18 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: ASCII fractal Phi<7:4>
- Expected pass: `True` — Actual pass: `True`
- `source_cas`: `Phi<7:4>`
- `english_output`: `Practice makes perfect, and over time the activity hits hard like a chord struck.`

### Case 19 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: fractal misread as count of stages
- Expected pass: `False` — Actual pass: `False`
- Validator reason: k-values not rendered as operators: [2, 9, 6, 7, 8, 9, 2, 5]; count-misread patterns detected: ['8 stages', 'sequence of 8']
- `source_cas`: `Φ⟨2:9:6:7:8:9:2:5⟩`
- `english_output`: `A sequence of 8 stages moving through operations 2, 9, 6, 7, 8, 9, 2, 5.`

### Case 20 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: fractal misread as 9 domains
- Expected pass: `False` — Actual pass: `False`
- Validator reason: k-values not rendered as operators: [9, 9]; count-misread patterns detected: ['9 domains', '9 domains']
- `source_cas`: `Φ⟨9:9⟩`
- `english_output`: `The expression covers 9 domains of structured thought.`

### Case 21 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: fractal Φ⟨3:5⟩ rendered as bare numbers
- Expected pass: `False` — Actual pass: `False`
- Validator reason: k-values not rendered as operators: [3, 5]
- `source_cas`: `Φ⟨3:5⟩`
- `english_output`: `The path moves from 3 to 5 across abstract levels.`

### Case 22 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: fractal Φ⟨0:0:0⟩ count-only
- Expected pass: `False` — Actual pass: `False`
- Validator reason: k-values not rendered as operators: [0, 0, 0]; count-misread patterns detected: ['sequence of 3']
- `source_cas`: `Φ⟨0:0:0⟩`
- `english_output`: `A sequence of 3 zero-valued operations.`

### Case 23 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: ASCII fractal misread as operations count
- Expected pass: `False` — Actual pass: `False`
- Validator reason: k-values not rendered as operators: [6, 2, 8]; count-misread patterns detected: ['6 operations', '2 operations', '8 operations']
- `source_cas`: `Phi<6:2:8>`
- `english_output`: `There are 6 operations, then 2 operations, then 8 operations.`

### Case 24 — [OK] `fractal_count_misread` (`fractal_k_indices`)

- Description: fractal sequence reduced to abstract count
- Expected pass: `False` — Actual pass: `False`
- Validator reason: k-values not rendered as operators: [1, 2, 3]; count-misread patterns detected: ['3 steps']
- `source_cas`: `Φ⟨1:2:3⟩`
- `english_output`: `The expression encodes 3 steps of cognitive activity.`

### Case 25 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: independent generation, simple
- Expected pass: `True` — Actual pass: `True`
- `prompt_text`: `Translate to CAS: a thought drawn toward foundations.`
- `generated_cas`: `^0 ∘ ^2^P`

### Case 26 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: independent generation, recipe
- Expected pass: `True` — Actual pass: `True`
- `prompt_text`: `Translate to CAS: 0.7 of cognitive emergence and 1.5 of principled attention produce the named target Ω_reasoning_02.`
- `generated_cas`: `Θ(Ω_reasoning_02) = 0.7*^9^C|A + 1.5*^1^P|A → Ω_reasoning_02`

### Case 27 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: independent generation, fractal
- Expected pass: `True` — Actual pass: `True`
- `prompt_text`: `Translate to CAS: a thought popped into mind, struck a chord, then became muscle memory.`
- `generated_cas`: `Φ⟨9:4:7⟩`

### Case 28 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: independent generation, binary composition
- Expected pass: `True` — Actual pass: `True`
- `prompt_text`: `Translate to CAS: principled aversion combines with evaluative resonance.`
- `generated_cas`: `^3^P|A + ^4^E|f`

### Case 29 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: independent generation, meta-logic
- Expected pass: `True` — Actual pass: `True`
- `prompt_text`: `Translate to CAS: a Noetic cluster covering all 10 operators.`
- `generated_cas`: `NoeticCluster{^0..^9}`

### Case 30 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: independent generation, let-binding
- Expected pass: `True` — Actual pass: `True`
- `prompt_text`: `Translate to CAS: bind a source to ^5^P, a target to ^8^C, then connect them.`
- `generated_cas`: `let s = ^5^P; let t = ^8^C; s → t`

### Case 31 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: independent generation, cross-register Ω
- Expected pass: `True` — Actual pass: `True`
- `prompt_text`: `Translate to CAS: principled aversion across analytical, affective, and transcendent registers.`
- `generated_cas`: `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω`

### Case 32 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: verbatim copy of phase-1 reference target pattern
- Expected pass: `False` — Actual pass: `False`
- Validator reason: generated CAS is a verbatim substring of the prompt — copy detected
- `prompt_text`: `reference target (for guidance only — do not paste verbatim, render afresh): ^0^P|A + ^0^P|T`
- `generated_cas`: `^0^P|A + ^0^P|T`

### Case 33 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: verbatim copy of recipe in prompt
- Expected pass: `False` — Actual pass: `False`
- Validator reason: generated CAS is a verbatim substring of the prompt — copy detected
- `prompt_text`: `Express as CAS: Θ(Ω_x) = 1*^5^P → Ω_x`
- `generated_cas`: `Θ(Ω_x) = 1*^5^P → Ω_x`

### Case 34 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: verbatim copy of fractal in prompt
- Expected pass: `False` — Actual pass: `False`
- Validator reason: generated CAS is a verbatim substring of the prompt — copy detected
- `prompt_text`: `Express as CAS: Φ⟨9:4:7⟩`
- `generated_cas`: `Φ⟨9:4:7⟩`

### Case 35 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: verbatim copy of meta-logic constructor
- Expected pass: `False` — Actual pass: `False`
- Validator reason: generated CAS is a verbatim substring of the prompt — copy detected
- `prompt_text`: `The expression NoeticCluster{^0..^9} covers all operators.`
- `generated_cas`: `NoeticCluster{^0..^9}`

### Case 36 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: verbatim copy of let-binding
- Expected pass: `False` — Actual pass: `False`
- Validator reason: generated CAS is a verbatim substring of the prompt — copy detected
- `prompt_text`: `Render: let s = ^5^P; let t = ^8^C; s → t`
- `generated_cas`: `let s = ^5^P; let t = ^8^C; s → t`

### Case 37 — [OK] `english_to_cas_verbatim` (`anti_copy`)

- Description: verbatim copy of cross-register expression
- Expected pass: `False` — Actual pass: `False`
- Validator reason: generated CAS is a verbatim substring of the prompt — copy detected
- `prompt_text`: `Express: (^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω`
- `generated_cas`: `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω`

### Case 38 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: operator index 13->1 (single char fix)
- Expected pass: `True` — Actual pass: `True`
- `invalid_expression`: `^13^E|f + ^1^E|E`
- `corrected_expression`: `^1^E|f + ^1^E|E`

### Case 39 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: missing closing bracket added
- Expected pass: `True` — Actual pass: `True`
- `invalid_expression`: `Phi<6 2`
- `corrected_expression`: `Phi<6:2>`

### Case 40 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: missing domain letter inserted
- Expected pass: `True` — Actual pass: `True`
- `invalid_expression`: `^5^ + ^8^C`
- `corrected_expression`: `^5^P + ^8^C`

### Case 41 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: F8 -> F7 (single token fix)
- Expected pass: `True` — Actual pass: `True`
- `invalid_expression`: `let s = ^9^P_{F8}`
- `corrected_expression`: `let s = ^9^P_{F7}`

### Case 42 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: comma -> colon in fractal
- Expected pass: `True` — Actual pass: `True`
- `invalid_expression`: `Phi<6,2,7>`
- `corrected_expression`: `Phi<6:2:7>`

### Case 43 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: missing register letter added
- Expected pass: `True` — Actual pass: `True`
- `invalid_expression`: `^3^E| + ^1^E|E`
- `corrected_expression`: `^3^E|f + ^1^E|E`

### Case 44 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: plus -> times in recipe
- Expected pass: `True` — Actual pass: `True`
- `invalid_expression`: `Theta(Omega_x) = 0.7+^5^P -> Omega_x`
- `corrected_expression`: `Theta(Omega_x) = 0.7*^5^P -> Omega_x`

### Case 45 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: whole-expression rewrite, recipe to state literal
- Expected pass: `False` — Actual pass: `False`
- Validator reason: char-3gram Jaccard 0.000 < threshold 0.6 — corrected expression diverges too much from invalid
- `invalid_expression`: `Θ(Ω_x) = 0.7+^5^P → Ω_x`
- `corrected_expression`: `^3^P|A`

### Case 46 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: whole-expression rewrite, fractal to recipe
- Expected pass: `False` — Actual pass: `False`
- Validator reason: char-3gram Jaccard 0.000 < threshold 0.6 — corrected expression diverges too much from invalid
- `invalid_expression`: `Phi<6 2`
- `corrected_expression`: `Θ(Ω_y) = 1*^4^E → Ω_y`

### Case 47 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: whole-expression rewrite, RPM chain to bare state
- Expected pass: `False` — Actual pass: `False`
- Validator reason: char-3gram Jaccard 0.000 < threshold 0.6 — corrected expression diverges too much from invalid
- `invalid_expression`: `let s = ^9^P_{F8}; let t = ^9^C_{F7}; s -> t`
- `corrected_expression`: `^4^P`

### Case 48 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: whole-expression rewrite, meta-logic to recipe
- Expected pass: `False` — Actual pass: `False`
- Validator reason: char-3gram Jaccard 0.000 < threshold 0.6 — corrected expression diverges too much from invalid
- `invalid_expression`: `PartitionOf(StateSet{^0,^1,^2}, NoeticCluster{^3,^4})`
- `corrected_expression`: `Θ(Ω_z) = 1*^7^O → Ω_z`

### Case 49 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: whole-expression rewrite, cross-register to fractal
- Expected pass: `False` — Actual pass: `False`
- Validator reason: char-3gram Jaccard 0.000 < threshold 0.6 — corrected expression diverges too much from invalid
- `invalid_expression`: `(^3^P|A × ^3^P|f) = ^3^P|Ω`
- `corrected_expression`: `Φ⟨9:4:7⟩`

### Case 50 — [OK] `invalid_to_corrected_unrelated` (`jaccard`)

- Description: whole-expression rewrite, binary composition to let-binding
- Expected pass: `False` — Actual pass: `False`
- Validator reason: char-3gram Jaccard 0.054 < threshold 0.6 — corrected expression diverges too much from invalid
- `invalid_expression`: `^4^E × ^2^`
- `corrected_expression`: `let foo = ^1^P; let bar = ^2^C; foo -> bar`

## What this smoke does NOT prove

- That the new prompts produce faithful output. Every example output here is hand-constructed; the smoke only exercises the validators.
- That the new pipeline produces clean records at scale. Wave 3 phase 2 paid generation must be re-run by the user before any such claim. The validators are necessary but not sufficient.
- That the Wave 2.5 design produces useful English. The dry-run Wave 2.5 generates synthetic placeholder text; only paid model calls produce real English candidates for the english_to_cas slot.
