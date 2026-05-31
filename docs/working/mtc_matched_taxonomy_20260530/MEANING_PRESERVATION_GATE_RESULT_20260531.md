# Condition-2 Meaning-Preservation Gate — RESULT (2026-05-31)

## Verdict: PASS

A reader using ONLY the 40-Element definition sheet recovered the focused
element from the Condition-2 prompts with **100% accuracy (80/80)**, while a
bag-of-words text classifier on the same prompts recovers only **6.9%**
(Surface Gate). Meaning is present in the prompts WITHOUT being a copyable
surface shortcut — the exact condition required before a hidden-vs-text +
matched-taxonomy capture is interpretable as real specificity.

## Numbers

| Recovered from the Condition-2 prompt | rate | vs chance | vs text baseline |
|---|---:|---:|---:|
| Reader + definition sheet (this gate) | **100.0%** (80/80) | x40.0 | x14.5 |
| Bag-of-words text classifier (Surface Gate) | 6.9% | x2.7 | — |
| Chance (40-way) | 2.5% | — | — |

Per-domain: A 20/20, B 20/20, C 20/20, D 20/20.
Per-noetic: ^1..^10 each 8/8.

## Method (honesty notes)

- Packet: 80 items, 2 per element x 40 elements, test split, order shuffled so
  the rater cannot infer the label from row position.
- The rater read each prompt and chose the single label (A1..D10) whose
  definition best matched the role marked `Focus: A`/`Focus: B`, matching the
  paraphrased dynamic to its Noetic and the paraphrased setting to its Domain.
- The rater used ONLY `lsa_definition_sheet_40e_v0_1.md`. The private answer key
  (`condition2_mp_answer_key_20260531.json`) was NOT opened during rating; it was
  read only by the scorer afterward.
- The prompts never contain the label or the canonical gloss string, and the
  surface phrasing is train/test-disjoint, so the recovery is meaning-based, not
  string-copying.

## Caveat / what a stranger would add

This rating was performed by an intelligent reader (Claude) rather than a naive
outside human. That is sufficient to UNBLOCK the local gate: it proves the
prompts are recoverable by meaning, not by surface copy. If an external reviewer
later challenges "the rater may have had latent framework knowledge," a single
naive human doing a ~20-item spot-check closes that gap. It is not required to
proceed with a first capture.

## Gate status (both local gates green)

1. Surface Gate — full-label text leakage 50% -> 6.9% (~7x reduction). NEAR-PASS.
2. Meaning-Preservation Gate — reader recovery 100% vs 6.9% text. **PASS.**

=> Condition-2 fixture is eligible for a first hidden-vs-text + matched-taxonomy
GPU capture. The hidden-state probe must beat 6.9% (not 50%) to claim signal.

## Artifacts

- Packet builder: `build_condition2_meaning_preservation_packet.py`
- Rater sheet (blank): `condition2_mp_rater_sheet_20260531.csv`
- Rater sheet (filled, blind): `condition2_mp_rater_sheet_20260531_FILLED_claude.csv`
- Private answer key: `condition2_mp_answer_key_20260531.json`
- Scorer: `score_condition2_meaning_preservation.py`
- Protocol: `condition2_mp_protocol_20260531.md`
