# Stage MTC Dual-Labeled Fixture Build Plan

**Date:** 2026-05-30  
**Status:** Pilot fixture generated; text-baseline gate passed for pilot capture  
**Reason:** Existing Stage9 40E and Stage7 F28 fixtures are CAS-valid but matched-comparator ineligible.

## Why This Is Needed

The old 20B Stage9 and Stage7 fixtures were built to test whether CAS labels are readable and causally useful. They were not built to carry an independent ordinary semantic taxonomy.

The matched-taxonomy control needs every row to carry two independent label systems before activation capture:

1. CAS label:
   - 40E: `10 Noetics x 4 Domains`
   - F28: `7 Drives x 4 Registers`
2. Non-CAS comparator label:
   - NC40: `8 topic sectors x 5 event frames`
   - NC28: `7 topical settings x 4 discourse functions`

If the non-CAS labels are added after the fact by guessing from abstract CAS role-bound prompts, the test becomes unfair. The materializer correctly blocked that path.

## Build Target

Create a new MTC fixture with ordinary concrete scenarios, not abstract A/B role-bound prompts.

Minimum pilot:

- 40E: 40 classes x 25 rows/class = 1,000 rows
- F28: 28 classes x 25 rows/class = 700 rows

Full confirmatory:

- 40E: 40 classes x 100 rows/class = 4,000 rows
- F28: 28 classes x 100 rows/class = 2,800 rows

## Required Row Fields

Each row must include:

```json
{
  "id": "...",
  "prompt": "...",
  "expected_cas_axes": {
    "operator": "^0..^9",
    "domain": "P|C|E|O",
    "element": "^i|D",
    "drive": "F1..F7",
    "register": "T|A|f|E",
    "foundation": "FjR"
  },
  "control_semantic": {
    "topic_40": "healthcare|education|commerce_finance|...",
    "frame_40": "classification|causal_explanation|procedure|tradeoff_decision|risk_mitigation",
    "topic_7": "medical_care|learning_assessment|...",
    "function_4": "describe_state|explain_cause|choose_action|evaluate_risk"
  },
  "metadata": {
    "split": "train|test",
    "fixture_family": "mtc_dual_labeled_v1",
    "authoring_rule": "concrete ordinary scenario; no CAS/TKS source vocabulary in surface text"
  }
}
```

## Non-Negotiable Rules

1. The prompt must be ordinary-world prose, not a CAS/TKS definition prompt.
2. CAS labels and non-CAS labels must both be assigned before model activation capture.
3. Do not put CAS source vocabulary into the prompt as obvious labels.
4. The text baseline must be recomputed for every label set.
5. The materializer must pass before any GPU capture.
6. The fixture JSON, pre-registration, and assignment artifact must be WORM-anchored before claim-bearing capture.
7. Marker or clue systems must be balanced across classes. If a surface marker becomes a class badge, the fixture is invalid even if the labels are technically balanced.

## Execution Steps

1. Build the dual-labeled fixture generator. **Done.**
2. Generate the 1,000-row 40E pilot and 700-row F28 pilot. **Done.**
3. Run the materializer eligibility gate. **Done.**
4. Run text-baseline diagnostics first. **Done for pilot.**
5. If text baseline is too high, rewrite prompts before any GPU capture.
6. Capture GPT-NeoX-20B activations.
7. Run MTC.1 matched-taxonomy runner.
8. Merge Evidence Packet and WORM-anchor.
9. Only if MTC.1 passes or lands grey, plan MTC.2 cross-architecture.

## 2026-05-30 Pilot Fixture Result

The first direct-wording pilot was blocked because CAS labels were 100% recoverable by text-only classification. The fix was a marker-balanced prompt format: every row includes all possible cue definitions, but the selected marker cycles independently of the class. This prevents a bag-of-words text baseline from treating a visible marker as a class badge.

Current pilot artifacts:

- 40E fixture: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_40e_pilot_20260530.json`
- 40E assignments: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_40e_pilot_assignments_20260530.json`
- 40E text diagnostic: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_40e_pilot_text_baseline_20260530.json`
- F28 fixture: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_f28_pilot_20260530.json`
- F28 assignments: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_f28_pilot_assignments_20260530.json`
- F28 text diagnostic: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_f28_pilot_text_baseline_20260530.json`

Pilot text-only gate:

| Axis | CAS text-only baseline | Non-CAS text-only baseline | Gate |
|---|---:|---:|---|
| 40E | 32.00% | 6.00% | Pass for pilot capture |
| F28 | 10.00% | 0.00% | Pass for pilot capture |

This does not prove CAS. It only proves the pilot prompt set is hard enough that a cheap text-only classifier is not already holding the answer. That makes GPU activation capture worth running.

## Current Blocked Evidence

- 40E blocked assignment artifact:
  - `docs/working/cas_harness_mtc_stage9_40e_assignment_blocked_20260530.json`
  - SHA256: `5C9A8B7BD494A838236BF7A849C4C440267B31C2A9CD8922A07975A7C45F06B3`
- F28 blocked assignment artifact:
  - `docs/working/cas_harness_mtc_stage7_f28_assignment_blocked_20260530.json`
  - SHA256: `9D648331360D102FA555DFE3BFC8363AB63EB33882B9C22F1D71D4E495B7E0C1`

## Plain-English Status

The old fixtures are still valid evidence that CAS is readable inside GPT-NeoX-20B. They are not valid fixtures for the hard matched-taxonomy specificity test.

The new pilot fixtures are now eligible for fresh 20B activation capture because the materializer passes and the text-only baseline no longer trivially solves the labels.
