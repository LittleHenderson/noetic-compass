# CAS Harness matched-taxonomy label manifest

**Date:** 2026-05-30
**Status:** Control-taxonomy/label manifest lane only
**Primary targets:** GPT-NeoX-20B Stage 9 40E and Stage 7 F28 fixtures
**Machine manifest:** `noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/matched_taxonomy_control_manifest_20260530.json`

## Scope

This document defines the control label spaces, fixed seeds, and deterministic
mapping rules for the matched-taxonomy control preregistered in
`docs/working/cas_harness_matched_taxonomy_control_prereg_20260530.md`.

This lane does not define or modify runner scripts. A runner consuming this
manifest must use the same activations, same frozen train/test split, same
balanced-logistic probe contract, same text baseline family, and same
lacunarity scoring required by the preregistration.

## Source anchors

- Preregistration: `docs/working/cas_harness_matched_taxonomy_control_prereg_20260530.md`
- Stage 9 method label: `S9-40E-ORIGINAL-BASELINE-READOUT`
- Stage 9 claim-bearing fixture: original role-bound/counterfactual 40E fixture
- Stage 9 known split/result: 8,320 rows, 40 classes, 208/class, frozen split
  3,840/4,480, hidden readout 95.625%, CountVectorizer text baseline
  49.241071%, text-hash 50.000%, shuffled-label mean 2.619%
- Stage 7 method label: `S7-F28-BALANCED-BRIDGE`
- Stage 7 F28 known fixture: exact Foundation-28 fixture, 4,368 rows,
  28 classes, 156/class
- F28 factorization note: F28 is 7 Drives x 4 Registers; 20B F28 trace note
  reports layer 40, heldout Foundation accuracy 86.8622%, Foundation
  lacunarity 0.006715, drive lacunarity 0.002752, register lacunarity 0.001283

## Shared execution rules

1. Reuse the frozen split from the source readout report or split manifest.
   Do not regenerate a split for this control. If the split mask cannot be
   recovered, block execution.
2. Reuse the same row order and row count as the source activation artifact.
   Do not drop rows for a headline matched-control result unless the Evidence
   Packet explicitly records a secondary downsampled diagnostic.
3. Stable row key priority:
   `scenario.id`, then `scenario.sample_id`, then `metadata.sample_ids`, then
   `sha256(dataset_artifact_sha256 + ":" + row_index)`.
4. Base prompt group key is the source prompt after stripping leading bracket
   framing tags, matching the existing Stage 9 helper behavior.
5. No coherent non-CAS mapping may read CAS target fields when assigning a
   non-CAS label. Prohibited fields include `labels_operator`, `labels_domain`,
   `foundation`, `drive`, `register`, `cas_expression`, and any derived CAS
   label. These fields may be used only for reporting CAS baselines and
   verifying non-derivation.
6. Every produced label-assignment artifact must include:
   label manifest hash, source scenario hash, activation dataset hash, split
   manifest hash, assignment algorithm version, seed, class counts by split,
   and a refusal/block reason if required quotas cannot be met.

## Fixed seeds

The manifest seed is `20260530`. Existing method-specific seeds are preserved
where already part of the source evidence: Stage 9 readout seed `20260527`,
Stage 9 bridge selection seed `20260528`.

Use these control seeds:

| Purpose | Seed(s) |
|---|---:|
| NC40 balanced assignment tie-break | 2026053040 |
| NC28 balanced assignment tie-break | 2026053028 |
| Scrambled 40E primary | 2026053140 |
| Scrambled F28 primary | 2026053128 |
| Scrambled 40E null sweep | 2026053401, 2026053402, 2026053403, 2026053404, 2026053405, 2026053406, 2026053407, 2026053408, 2026053409, 2026053410 |
| Scrambled F28 null sweep | 2026052801, 2026052802, 2026052803, 2026052804, 2026052805, 2026052806, 2026052807, 2026052808, 2026052809, 2026052810 |
| Text baseline vectorizer/probe tie-break | 2026053050 |
| Lacunarity bootstrap/tie-break | 2026053060 |

## CAS reference label spaces

### Stage 9 40E

Canonical construction: `operator|domain`, with operators `^0` through `^9`
and domains `P`, `C`, `E`, `O`. Order is operator-major, domain-minor:

`^0|P`, `^0|C`, `^0|E`, `^0|O`, `^1|P`, `^1|C`, `^1|E`, `^1|O`,
`^2|P`, `^2|C`, `^2|E`, `^2|O`, `^3|P`, `^3|C`, `^3|E`, `^3|O`,
`^4|P`, `^4|C`, `^4|E`, `^4|O`, `^5|P`, `^5|C`, `^5|E`, `^5|O`,
`^6|P`, `^6|C`, `^6|E`, `^6|O`, `^7|P`, `^7|C`, `^7|E`, `^7|O`,
`^8|P`, `^8|C`, `^8|E`, `^8|O`, `^9|P`, `^9|C`, `^9|E`, `^9|O`.

### Stage 7 F28

Canonical construction: `F{drive}{register}`, with drives `F1` through `F7`
and registers `T`, `A`, `f`, `E`. Order is drive-major, register-minor:

`F1T`, `F1A`, `F1f`, `F1E`, `F2T`, `F2A`, `F2f`, `F2E`,
`F3T`, `F3A`, `F3f`, `F3E`, `F4T`, `F4A`, `F4f`, `F4E`,
`F5T`, `F5A`, `F5f`, `F5E`, `F6T`, `F6A`, `F6f`, `F6E`,
`F7T`, `F7A`, `F7f`, `F7E`.

## Control A: scrambled CAS labels

Control IDs:

- `SCR40E_BALANCED_SPLIT_SHUFFLE_V1`
- `SCRF28_BALANCED_SPLIT_SHUFFLE_V1`

Goal: preserve row count, class count, per-split class balance, and the frozen
split, while breaking the semantic relation between prompts/activations and
labels.

Algorithm:

1. For each split separately, collect the source canonical labels as a multiset.
2. Sort rows by stable row key.
3. Shuffle the multiset with `numpy.random.default_rng(seed).permutation`.
4. Repair accidental identity assignments by cyclically swapping assigned
   labels among identity rows. If a full repair is impossible, record the
   residual identity count and require it to be below 1% of rows in that split.
5. Emit one assignment artifact per seed.
6. Report the primary scrambled result and the mean/max over the null-sweep
   seeds.

Expected behavior: hidden readout near chance, high/dirty lacunarity, and no
clean nested structure.

## Control B: coherent non-CAS 40-way taxonomy

Control ID: `NC40_TOPIC_FRAME_V1`

This is a flat 40-way semantic taxonomy built from 8 ordinary topic sectors and
5 ordinary communication/event frames. It is intentionally not a CAS, TKS,
Noetic, Domain, Drive, or Register taxonomy.

Topic sectors:

1. `healthcare`
2. `education`
3. `commerce_finance`
4. `law_governance`
5. `software_data`
6. `logistics_operations`
7. `customer_support`
8. `public_safety`

Frames:

1. `classification`
2. `causal_explanation`
3. `procedure`
4. `tradeoff_decision`
5. `risk_mitigation`

Class ID format: `NC40_{topic}_{frame}`.

Mapping rule:

1. Prefer explicit non-CAS annotation fields if present:
   `control_semantic.topic_40` and `control_semantic.frame_40`.
2. Otherwise derive topic candidates from non-CAS source text only:
   `lexical_pack_id`, `domain_slug`, `task_slug`, `prompt`, and `reply`.
3. Derive frame candidates from non-CAS source text only:
   `paraphrase_family`, `surface_style`, `question_type`, `prompt`, and
   `reply`.
4. Use the keyword dictionaries in the machine manifest to produce candidate
   topics and frames. Candidate labels are the cross-product of candidates.
5. Solve a deterministic balanced assignment over the frozen train split and
   frozen test split separately, with target counts equal to the source CAS
   per-split class counts. Tie-break with seed `2026053040`.
6. If quotas cannot be satisfied without assigning a row to an unsupported
   semantic candidate, block and emit `blocked_insufficient_nc40_candidate_cover`.

This control is strongest when a human review pass confirms that each assigned
topic/frame is semantically plausible for the row and that no CAS label fields
were used.

## Control C: coherent non-CAS 7 x 4 nested taxonomy

Control ID: `NC28_TOPIC_FUNCTION_NESTED_V1`

This is a real two-factor non-CAS taxonomy: 7 topical settings x 4 discourse
functions. It is the direct F28 opponent for nested lacunarity.

Parent topic families:

1. `medical_care`
2. `learning_assessment`
3. `market_transaction`
4. `law_policy`
5. `technical_system`
6. `operations_planning`
7. `human_services`

Child discourse functions:

1. `describe_state`
2. `explain_cause`
3. `choose_action`
4. `evaluate_risk`

Class ID format: `NC28_{topic}_{function}`.

Mapping rule:

1. Prefer explicit non-CAS annotation fields if present:
   `control_semantic.topic_7` and `control_semantic.function_4`.
2. Otherwise derive topic/function candidates from non-CAS text and metadata
   only, using the keyword dictionaries in the machine manifest.
3. Solve a deterministic balanced assignment over train and test separately,
   with target counts equal to the source F28 per-split class counts. Tie-break
   with seed `2026053028`.
4. If quotas cannot be satisfied, block and emit
   `blocked_insufficient_nc28_candidate_cover`.

Nested metrics:

- Parent-factor lacunarity: 7 topic families
- Child-factor lacunarity: 4 discourse functions
- Joint-class lacunarity: 28 topic/function classes

## Evidence packet fields

The matched-control Evidence Packet must include, at minimum:

- This markdown manifest hash and machine JSON hash
- Source Stage 9 and Stage 7 artifact hashes
- Split manifest hash and split counts
- CAS label-space reports
- Scrambled control reports, including all seeds
- NC40 assignment report and readout/text/lacunarity reports
- NC28 assignment report and readout/text/flat-plus-nested lacunarity reports
- Explicit pass/grey/fail verdict under the preregistration

## Readiness

This manifest is concrete enough for an implementation to generate labels
without changing the scientific design: all label spaces, seeds, class IDs,
field priorities, and block conditions are fixed. It is not an execution report:
no runner was edited, no activation job was run, and no row-level assignment
artifact was materialized in this lane.
