# DO NOT USE — meaning-stripped MTC fixtures (quarantined 2026-05-31)

The fixtures listed below strip the real TKS Element/Foundation meaning out of
their prompts. They produced the MTC **FALSIFY** null (CAS not recoverable
above chance from GPT-NeoX-20B hidden states; scrambled labels recover as well
as real). **That null is a fixture-design artifact of meaning-stripping, NOT
evidence against CAS.** The marker-balanced cue-card definitions additionally
DRIFT from canonical CAS (`^3` rendered analytical instead of visceral; `^8`
rendered as causal reasoning instead of associative triggering — both violate
the CLAUDE.md anti-drift annotations).

Do NOT capture activations from, probe, or cite these as a CAS specificity
instrument. Kept only as the documented record of what NOT to do.

## Quarantined builders
- `scripts/build_mtc_dual_labeled_fixture.py` (marker-balanced cue-cards)
- `scripts/build_mtc_v2_concrete_fixture.py` (concrete, meaning-stripped)

## Quarantined fixtures (this directory)
- `mtc_dual_labeled_40e_pilot_20260530.json`
- `mtc_dual_labeled_40e_pilot_assignments_20260530.json`
- `mtc_dual_labeled_40e_pilot_text_baseline_20260530.json`
- `mtc_dual_labeled_f28_pilot_20260530.json`
- `mtc_dual_labeled_f28_pilot_assignments_20260530.json`
- `mtc_dual_labeled_f28_pilot_text_baseline_20260530.json`
- `mtc_v2_concrete_40e_pilot_20260530.json`
- `mtc_v2_concrete_40e_pilot_assignments_20260530.json`
- `mtc_v2_concrete_40e_pilot_text_baseline_20260530.json`
- `mtc_v2_concrete_f28_pilot_20260530.json`
- `mtc_v2_concrete_f28_pilot_assignments_20260530.json`
- `mtc_v2_concrete_f28_pilot_text_baseline_20260530.json`

## Use instead
The Condition-2 real-TKS fixture, which keeps the real TKS meaning while
killing the copy-the-definition shortcut (local text leakage 50% -> 6.9%):
- `docs/working/mtc_matched_taxonomy_20260530/build_mtc_condition2_meaning_instantiated.py`
- `docs/working/mtc_matched_taxonomy_20260530/mtc_condition2_meaning_instantiated_20260531.jsonl`
- Evidence: `docs/working/mtc_matched_taxonomy_20260530/REAL_DEFINITION_TEXT_BASELINE_20260531.md`,
  `.../CONDITION2_SURFACE_GATE_20260531.md`, `.../RESULT_NOTE_20260531.md`
