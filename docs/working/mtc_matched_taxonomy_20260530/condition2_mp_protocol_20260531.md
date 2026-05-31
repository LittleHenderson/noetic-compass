# Condition-2 Meaning-Preservation Gate — protocol (20260531)

## Task
For each row in `condition2_mp_rater_sheet_20260531.csv`, read the `prompt` and
choose the single 40-Element label (A1..D10) whose definition best matches the
role marked by `Focus: A` or `Focus: B`. Put it in `chosen_label`. Optional:
`confidence_1to5`.

Use ONLY the definition sheet:
`docs/working/lsa_artifacts_20260530/lsa_definition_sheet_40e_v0_1.md`
(A=Spiritual, B=Mental, C=Emotional, D=Physical; 1..10 = the noetic dynamic).
The prompt never shows the label or the canonical gloss string.

## Items
80 items, 2 per element x 40 elements, test split.
Order is shuffled. Chance = 0.0250 (2.5%).

## Gate
PASS if human recovery is well above chance (target: macro recovery >= ~50%,
and clearly > the 6.9% Surface-Gate text baseline). PASS + near-chance text
baseline => meaning is present without being a surface shortcut => Condition-2
is eligible for GPU capture (hidden-vs-text + matched-taxonomy comparator).
FAIL (recovery near chance) => the prompts no longer carry the element meaning;
revise instantiations before any capture.

## Scoring
`python score_condition2_meaning_preservation.py --filled <rater_sheet.csv>`
compares against the private answer key and reports overall / per-domain /
per-noetic recovery vs chance.
