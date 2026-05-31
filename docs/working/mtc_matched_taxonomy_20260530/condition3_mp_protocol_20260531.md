# Condition-3 Meaning-Preservation Gate -- protocol (20260531)

## Task
For each row in `condition3_mp_rater_sheet_20260531.csv`, read the `prompt` and
choose the single 40-Element label (A1..D10) whose definition best matches the
role marked by `Focus: A` or `Focus: B`. Put it in `chosen_label`. Optional:
`confidence_1to5`.

Use ONLY the definition sheet:
`docs/working/lsa_artifacts_20260530/lsa_definition_sheet_40e_v0_1.md`
(A=Spiritual, B=Mental, C=Emotional, D=Physical; 1..10 = the noetic dynamic).

The role carries the noetic dynamic (verb phrase after "the one who ...") AND the
domain-as-register (the adjective in "in a {adj} way" / "with a {adj} bearing"
/ "on {adj} ground"). IGNORE the everyday scenario (topic + frame) -- it is
orthogonal scaffold and does not determine the element. The prompt never shows the
label or a canonical gloss string.

## Items
40 items, 1 per element x 40 elements, test split.
Order is shuffled. Chance = 0.0250 (2.5%).

## Gate
PASS if reader recovery is well above chance (target: overall >= ~50%, and clearly
> the 6.25% Surface-Gate text baseline). PASS + near-chance text baseline => meaning
is present without a surface shortcut => Condition-3 carries real CAS meaning.
FAIL (recovery near chance) => the instantiations no longer carry the element
meaning; revise before any capture.

## Scoring
`python score_condition3_meaning_preservation.py --filled <rater_sheet.csv>`
compares against the private answer key and reports overall / per-domain /
per-noetic recovery vs chance and vs the 6.25% text baseline.
