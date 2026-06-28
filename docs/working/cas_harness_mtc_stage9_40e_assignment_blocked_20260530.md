# Stage MTC 40E Assignment Blocker

**Date:** 2026-05-30  
**Axis:** GPT-NeoX-20B Stage9 40E  
**Status:** `BLOCKED_FIXTURE_NOT_ELIGIBLE`  
**Blocked artifact:** `docs/working/cas_harness_mtc_stage9_40e_assignment_blocked_20260530.json`  
**Blocked artifact SHA256:** `5C9A8B7BD494A838236BF7A849C4C440267B31C2A9CD8922A07975A7C45F06B3`

## What Happened

The row-level matched-taxonomy materializer was run against:

`D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527\stage9_original_40e_scenarios_20260527.json`

with the matched-control manifest:

`noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/matched_taxonomy_control_manifest_20260530.json`

The materializer correctly blocked:

`blocked_insufficient_nc40_candidate_cover`

## Why It Blocked

The Stage9 40E fixture is valid for CAS readout, but it is not shaped like an ordinary semantic benchmark. Its prompts are abstract A/B role-bound TKS/CAS comparisons. They do not contain enough ordinary topic/event content to fairly assign the coherent non-CAS 40-way taxonomy:

`8 ordinary topic sectors x 5 communication/event frames`

The materializer could only assign 142 of the 2,560 required train rows without unsupported guessing. Most target cells had zero candidate coverage.

## Correct Interpretation

This is not a CAS failure.

This is not evidence that the matched taxonomy beats CAS.

This is an eligibility failure: the fixture does not support the hard comparator. A claim-bearing MTC run needs either:

1. row-level `control_semantic.*` labels added by an auditable annotation pass, or
2. a newly built dual-labeled MTC fixture where every item has both CAS labels and coherent non-CAS comparator labels before activation capture.

## Claim Rule

Until a coherent matched comparator can be materialized on the same rows and same activations, the hard Claim B question remains:

`OPEN / BLOCKED`, not failed.

