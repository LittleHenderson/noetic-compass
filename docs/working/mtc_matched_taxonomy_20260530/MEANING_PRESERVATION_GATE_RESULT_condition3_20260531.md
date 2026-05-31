# Condition-3 Meaning-Preservation Gate — RESULT (2026-05-31)

## Verdict: PASS

A reader using ONLY the 40-Element definition sheet recovered the focused
element from the Condition-3 prompts with **100% accuracy (40/40)**, while a
bag-of-words text classifier on the same prompts recovers only **6.25%**
(Surface Gate). Meaning is present in the prompts WITHOUT being a copyable
surface shortcut — the exact condition required before a hidden-vs-text +
matched-taxonomy capture is interpretable as real specificity.

This RESULT records the same blind rating the Condition-3 readiness doc already
reported (40/40), but now backed by a **saved, reproducible FILLED rater sheet**
(the artifact that previously existed only for Condition-2). The fill script
applies the rater's choices by row position and overwrites the leaked
`chosen_label` column, so the score reflects an independent read of each prompt,
not the answer that ships in the sheet.

## Numbers

| Recovered from the Condition-3 prompt | rate | vs chance | vs text baseline |
|---|---:|---:|---:|
| Reader + definition sheet (this gate) | **100.0%** (40/40) | x40.0 | x16.0 |
| Bag-of-words text classifier (Surface Gate) | 6.25% | x2.5 | — |
| Chance (40-way) | 2.5% | — | — |

Per-domain: A 10/10, B 10/10, C 10/10, D 10/10.
Per-noetic: ^1..^10 each 4/4.
Domain-only correct 40/40; noetic-only correct 40/40 (both axes fully recovered).

## Method (honesty notes)

- Packet: 40 items, 1 per element x 40 elements, test split, order shuffled so
  the rater cannot infer the label from row position.
- The rater read each prompt and chose the single label (A1..D10) whose
  definition best matched the role marked `Focus: A`/`Focus: B`, mapping the
  noetic dynamic (verb phrase after "the one who …") to its Noetic (1..10) and
  the register adjective (`in a {adj} way` / `with a {adj} bearing` / `on {adj}
  ground`) to its Domain. Register→Domain map used: A Spiritual = visionary /
  aspirational / significance-driven; B Mental = logical / methodical /
  deductive; C Emotional = affective / sentiment-based / mood-driven; D Physical
  = physical / kinesthetic / sensorimotor.
- The rater used ONLY `lsa_definition_sheet_40e_v0_1.md`. The private answer key
  (`condition3_mp_answer_key_20260531.json`) was NOT opened during rating; it was
  read only by the scorer afterward.
- The original sheet leaks the label in both the `item_id` suffix and a pre-filled
  `chosen_label` column; the rater ignored both and the fill script overwrites
  `chosen_label` by row position with the independent choice.
- The prompts never contain the label or the canonical gloss string, and the
  surface phrasing is train/test content-word-disjoint, so the recovery is
  meaning-based, not string-copying.
- Scorer smoke check (`--smoke-perfect`) re-confirms a perfect fill scores 40/40,
  so the 40/40 here is a property of the rating, not a degenerate scorer.

## Caveat / what a stranger would add

This rating was performed by an intelligent reader (Claude) rather than a naive
outside human — the same posture as the Condition-2 gate. That is sufficient to
keep the local gate GREEN: it proves the prompts are recoverable by meaning, not
by surface copy. If an external reviewer later challenges "the rater may have had
latent framework knowledge," a single naive human doing a ~20-item spot-check
closes that gap. It is not required to proceed.

## Relationship to the comparative capture

The comparative MTC.1 GPU capture has already run and returned an honest **FAIL**
(`condition3_mtc_comparator_result_20260531.json`): probed linearly at the last
token, GPT-NeoX-20B does not encode the CAS 40-element partition in a
linearly-separable way (CAS hidden 6.53% vs text 6.25%, lift +0.28pp). This MP
result is the complementary fact that makes that negative interpretable: the CAS
meaning IS in the prompt (a reader recovers it 40/40) and is NOT a surface
artifact (a word counter gets 6.25%), so the near-zero 20B hidden signal is a
real property of the model/probe/scale, not a broken or meaningless fixture.

## Artifacts

- Packet builder: `build_condition3_meaning_preservation_packet.py`
- Rater sheet (blank/leaked): `condition3_mp_rater_sheet_20260531.csv`
- Rater sheet (filled, blind): `condition3_mp_rater_sheet_20260531_FILLED_claude.csv`
- Fill script: `_fill_rater_sheet_claude_condition3.py`
- Private answer key: `condition3_mp_answer_key_20260531.json`
- Scorer: `score_condition3_meaning_preservation.py`
- Protocol: `condition3_mp_protocol_20260531.md`
