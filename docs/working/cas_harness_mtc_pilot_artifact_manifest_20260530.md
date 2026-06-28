# CAS Harness MTC Pilot Artifact Manifest - 2026-05-30

## Scope

Concise manifest for the Stage MTC dual-labeled pilot fixture artifacts. This manifest is informational only; it does not license claim-bearing activation capture.

## Generated Artifacts

### 40E Pilot

- Fixture JSON: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_40e_pilot_20260530.json`
- Assignment JSON: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_40e_pilot_assignments_20260530.json`
- Text-baseline diagnostic JSON: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_40e_pilot_text_baseline_20260530.json`
- Current text baseline scores:
  - CAS 40E: 32%
  - NC40: 6%

### F28 Pilot

- Fixture JSON: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_f28_pilot_20260530.json`
- Assignment JSON: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_f28_pilot_assignments_20260530.json`
- Text-baseline diagnostic JSON: `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/mtc_dual_labeled_f28_pilot_text_baseline_20260530.json`
- Current text baseline scores:
  - CAS F28: 10%
  - NC28: 0%

## Next Required Step

Before any claim-bearing activation capture, produce and verify a WORM-anchored evidence record for the fixture/assignment/diagnostic hashes. The required gate is per-anchor mechanical verification of S3 Object Lock/WORM status, not merely a recorded S3 receipt.

## Methodology Caveats

- This passes the pilot "worth running through a real model" gate. It does not prove text leakage has been eliminated.
- The current diagnostic uses `CountVectorizer(1-2 grams) + LogisticRegression`. Stronger text adversaries such as character n-grams, TF-IDF variants, parser extraction, or embedding classifiers remain untested.
- 40E CAS still has measurable surface predictability at 32%, even though it is below the 60% pilot ceiling and far below the prior 100% blocked fixture.
- The marker-balanced prompts are structured cue cards, not ordinary free prose. They are acceptable for pilot capture, but a later confirmatory fixture should add a stronger text-adversary suite.
- The pilot has 200 heldout 40E rows and 140 heldout F28 rows. Treat the numbers as pilot diagnostics, not stable population estimates.
