# v1c VALIDTOK 5ep — Codex Human Audit

Source pack:
`cas-synthetic/data/path_d/v1_eval_pack_24records_20260510T031428Z.md`

Raw JSONL:
`cas-synthetic/data/path_d/v1_eval_pack_24records_20260510T031428Z.jsonl`

Evaluator: Codex acting with user consent.

## Verdict

Not green. The v1c task-token retrain improved several easy surfaces, but it
did **not** fix the primary rpm_chain hijack and did **not** clear the
acceptable+ target.

Primary gate:

- rpm_chain hijack target: `3/3 -> 0/3`
- result: `3/3 -> 3/3`
- verdict: FAIL

Secondary gate:

- acceptable+ target: `12/24 -> >=18/24`
- result: `13/24`
- verdict: FAIL

Strong band:

- green + high_yellow: `8/24`

## Grade Counts

| Band | Records | Count |
|---|---:|---:|
| green | 1, 2, 4, 6, 7, 23, 24 | 7 |
| high_yellow | 17 | 1 |
| yellow | 5, 8, 9, 11, 22 | 5 |
| flop / wrong / incoherent | 3, 10, 12, 13, 14, 15, 16, 18, 19, 20, 21 | 11 |

Acceptable+ = green + high_yellow + yellow = `13/24`.

## Per-Record Grades

| # | Category | Overall | Notes |
|---:|---|---|---|
| 1 | state_literal | green | Exact useful state rendering. |
| 2 | state_literal | green | Faithful; "analytical way" is close enough to analytical reasoning. |
| 3 | state_literal | flop | Meaning partly present, but "Amemory memory..." and repeated trigger phrasing are visibly broken. |
| 4 | binary_composition | green | Correct two-part composition and domain. |
| 5 | binary_composition | yellow | Correct broad direction and endpoint, but wording is awkward and the trigger relation is muddled. |
| 6 | binary_composition | green | Correct memory + practiced rhythm in evaluative judgment. |
| 7 | cross_register_omega | green | Strong output: correct fusion shape, registers, and outcome. |
| 8 | cross_register_omega | yellow | Outcome and identity shape are right, but affective register drifts to analytical/reasoned. |
| 9 | cross_register_omega | yellow | Outcome is repaired and task shape is right, but affective/embodied distinction collapses into embodied twice. |
| 10 | recipe | wrong | Outcome name fixed, but ingredients/noetics are wrong and it adds an extra wrong contribution. |
| 11 | recipe | yellow | Main recipe shape and some coefficients survive, but second term domain/register and side-output content drift. |
| 12 | recipe | wrong | Coefficients/body semantics and final outcome drift badly; ends with `tracking_78` instead of `judgment_78`. |
| 13 | fractal_sequence | wrong | Fluent sequence, but most k-values are wrong. |
| 14 | fractal_sequence | wrong | Target is simple aversion -> rhythm; output invents several extra wrong states. |
| 15 | fractal_sequence | wrong | Long, repetitive, and sequence content does not match source. |
| 16 | meta_logic_relation | wrong | Partition shape starts right but groups are incomplete/wrong; only one group is actually described. |
| 17 | meta_logic_relation | high_yellow | Product shape mostly correct; second cluster swaps a thought for who-one-is. |
| 18 | meta_logic_relation | wrong | Cover relation becomes partition and cluster contents are wrong. |
| 19 | rpm_chain | wrong | Valid rpm_chain misrendered as invalid undefined-destination explanation. |
| 20 | rpm_chain | wrong | Same invalid-explanation hijack. |
| 21 | rpm_chain | wrong | Same invalid-explanation hijack. |
| 22 | invalid_to_explanation | yellow | Correct incompatible-transition idea, but "second ... second" wording is sloppy. |
| 23 | invalid_to_explanation | green | Correct undefined-start explanation, clean and complete. |
| 24 | invalid_to_explanation | green | Correct undefined-destination explanation, clean and complete. |

## Comparison To Previous 24-Record Audit

The previous 24-record audit had roughly:

- strong band: `7/24`
- acceptable+ band: `12/24`
- wrong/flop: `12/24`

v1c has:

- strong band: `8/24`
- acceptable+ band: `13/24`
- wrong/flop: `11/24`

This is a small improvement, not a breakthrough. The easy surfaces sharpened,
but the load-bearing rpm_chain failure did not move.

## Technical Read

The `[VALID]` / `[INVALID]` prefix token is wired correctly but does not have
enough leverage to override the decoder's learned invalid-explanation opener
for valid rpm_chain shapes.

The earlier decoder-seeding diagnostic still matters: when the decoder is
seeded with `Let <stage> name`, the model can continue in a valid let-binding
silhouette. That means the content is partly latent, but first-token/opener
control is still the bottleneck.

## Recommendation

Do not call v1c chat-ready.

Next experiment should be an inference-side rpm_chain silhouette seed on the
v1c checkpoint:

- apply only when routing says `cas_to_english` and source has valid rpm_chain
  shape;
- seed decoder with `Let <first_stage> name `;
- run the same 24-record eval;
- primary question: does rpm_chain hijack move `3/3 -> 0/3`?

If yes, the near-term production path is a gated rpm_chain seeding fallback.
If no, the model needs a stronger architecture/training change than a single
task token.
