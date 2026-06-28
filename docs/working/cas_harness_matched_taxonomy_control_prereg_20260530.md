# Stage MTC - Matched-Taxonomy Control Pre-Registration

**Date:** 2026-05-30  
**Status:** Draft v0.2 - do not freeze until WORM-anchored  
**Primary decision gate:** GPT-NeoX-20B Stage 9 40-Element and Stage 7 Foundation-28 fixtures  
**Conditional extension:** remaining validated model points only after the 20B gate is scored  
**Classification:** Confidential, NDA-gated pre-registration

## 0. Why This Stage Exists

The current evidence strongly supports this claim:

> The model linearly encodes the distinctions tracked by the CAS 40-Element and Foundation-28 labels, and parts of that encoding are causally load-bearing.

It does not, by itself, fully license this stronger claim:

> CAS is recovering a CAS-specific structure rather than relabeling an ordinary semantic partition that transformer hidden states also encode.

That second claim is comparative. It can only be earned against same-size, coherent alternatives run on the same activations with the same probe family, same splits, same lacunarity scoring, and same Evidence Packet discipline.

Plain English: we have shown that CAS labels are readable inside the model. This stage asks whether CAS is cleaner than serious opponents of the same size.

## 1. Stage Scope

### Stage MTC.1 - 20B Decision Gate

Run first on GPT-NeoX-20B only:

- Stage 9 40E: `10 Noetics x 4 Domains`
- Stage 7 F28: `7 Drives x 4 Registers`

This is the cheapest decisive gate because the 20B evidence has the strongest dynamic range:

- 40E hidden readout: 95.625%
- confirmed 40E text baseline: 49.241071%
- F28 nested lacunarity already measured:
  - Foundation flat: 0.006715
  - drive-within-Foundation: 0.002752
  - register-within-Foundation: 0.001283

### Stage MTC.2 - Conditional Cross-Architecture Extension

Only after MTC.1 is scored, decide whether to run the same control across:

- Pythia-160M
- Pythia-1B
- Pythia-2.8B
- OLMo-1B
- Qwen2.5-1.5B

If MTC.1 fails, the external "CAS-specific" claim is not licensed and there is no obligation to spend compute on a six-model sweep. If MTC.1 passes or lands grey, MTC.2 becomes high-value because it tests whether the specificity result survives scale and architecture changes.

## 2. Hypotheses

### H-MTC-1: Lift Dominance

CAS probe lift over its own text baseline exceeds every matched comparator's lift over its own text baseline by the pre-registered margin.

### H-MTC-2: Flat Factorization Dominance

CAS flat lacunarity is cleaner than every matched comparator's flat lacunarity by the pre-registered margin.

### H-MTC-3: Nested-Factor Specificity

CAS two-factor nesting is cleaner than the coherent non-CAS two-factor comparator:

- F28: `7 Drives x 4 Registers`
- non-CAS opponent: `7 topical settings x 4 discourse functions`

This is the strongest discriminator. CAS is not allowed to win H-MTC-3 merely by beating a flat taxonomy that was never designed to nest.

### H-MTC-4: Permutation Null

CAS probe accuracy exceeds the label-randomization null distribution. This is a sanity floor, not the decisive test.

## 3. Taxonomies And Controls

All controls use the same row order, same activation artifact, same split, same probe hyperparameters, and same scoring code.

### CAS Arms

1. **S9 40E:** `operator|domain`, 40 classes.
2. **S7 F28:** `drive|register`, 28 classes.

### Control A: Scrambled CAS Labels

Fixed-seed label permutations preserving class count, class balance, split membership, and row count.

Purpose: prove the result is not an artifact of class cardinality or probe capacity.

### Control B: Coherent Non-CAS 40-Way Taxonomy

Control ID: `NC40_TOPIC_FRAME_V1`

Design: 8 ordinary topic sectors x 5 ordinary communication/event frames.

The machine-readable label manifest is:

`noetic-compass-scaffold/noetic-compass/live-trace-worker/scenarios/matched_taxonomy_control_manifest_20260530.json`

The human-readable manifest is:

`docs/working/cas_harness_matched_taxonomy_label_manifest_20260530.md`

This comparator is not allowed to read CAS fields when assigning labels.

### Control C: Coherent Non-CAS 7 x 4 Nested Taxonomy

Control ID: `NC28_TOPIC_FUNCTION_NESTED_V1`

Design: 7 topical settings x 4 discourse functions.

This is the direct F28 nested opponent. It is the primary comparator for H-MTC-3.

### Control D: Lexical / TF-IDF Baseline

A surface-text classifier or matched-cardinality lexical clustering baseline, scored separately for every label set.

Purpose: detect whether the labels are recoverable from prompt wording without looking inside the model.

## 4. Carving Methodology For Coherent Alternatives

The non-CAS taxonomies are fixed before execution by the label manifest named above.

Rules:

1. Use only non-CAS prompt text or non-CAS metadata fields for assignment.
2. Do not use CAS label fields, CAS names, Foundation labels, Drive labels, Register labels, Domain labels, Noetic labels, or derived CAS expressions.
3. Keep class balance equal to the source CAS fixture within each frozen split.
4. If a balanced assignment cannot be produced without unsupported labels, block the run instead of weakening the comparator.
5. Record the assignment artifact hash in the Evidence Packet.

This makes the opponent serious enough to matter, but prevents it from secretly inheriting CAS labels.

## 5. Pilot And Margin-Setting

MTC.1 begins with a pilot before confirmatory scoring.

### Fixture Eligibility Gate

Before any pilot or confirmatory MTC result can be claim-bearing, each fixture must pass a coherent-comparator eligibility check.

The fixture is **eligible** only if the row-level assignment materializer can produce balanced, split-preserving labels for the coherent non-CAS comparator without using CAS fields or unsupported semantic guesses.

Eligible means:

1. The coherent comparator labels are materialized for every required row.
2. Train/test class quotas match the CAS fixture quotas.
3. Assignment uses only explicit `control_semantic.*` fields or manifest-approved non-CAS text fields.
4. The assignment artifact is hashed and attached to the Evidence Packet.

Blocked means:

1. The fixture has abstract CAS/TKS role-bound prose but insufficient ordinary semantic topic/event content.
2. The materializer cannot satisfy balanced quotas without unsupported labels.
3. The coherent comparator is missing row-level labels.
4. The exact activation artifact for that axis is unavailable.

When this gate blocks, the correct status is `BLOCKED_FIXTURE_NOT_ELIGIBLE` or the more specific materializer block code. It is not a CAS failure and it is not evidence for or against Claim B.

### Text-Baseline Gate

After fixture eligibility passes and before any GPU activation capture, run a text-only baseline for every label set attached to the fixture.

The fixture is **eligible for activation capture** only if the text-only classifier cannot solve the label set from the prompt surface alone. The pre-registered pilot ceiling is `<= 60%` for each claim-bearing CAS or matched taxonomy label set.

If any claim-bearing label set returns a text-only score above the ceiling, the correct status is `BLOCKED_TEXT_BASELINE_TOO_HIGH`. The fixture must be rewritten before capture. A high text baseline is not a CAS win; it means the prompt wording carried the answer.

The 2026-05-30 dual-labeled pilot passed this gate after marker balancing:

| Axis | CAS text-only baseline | Non-CAS text-only baseline | Diagnostic artifact |
|---|---:|---:|---|
| 40E | 32.00% | 6.00% | `live-trace-worker/scenarios/mtc_dual_labeled_40e_pilot_text_baseline_20260530.json` |
| F28 | 10.00% | 0.00% | `live-trace-worker/scenarios/mtc_dual_labeled_f28_pilot_text_baseline_20260530.json` |

Plain English: the text-only opponent tried to guess the answers from the words on the page and failed badly enough that the pilot is worth running through a real model.

The pilot must include:

1. Scrambled-CAS controls on the 20B 40E and F28 fixtures.
2. A mini-pilot of the coherent non-CAS 40-way comparator.
3. A mini-pilot of the coherent non-CAS 7 x 4 nested comparator.

The pilot may use a deterministic 20% row slice per class if full-control runtime is too high. The slice must be selected by the fixed manifest seeds before scoring.

### Mechanical Delta Rule

Margins are set mechanically from the pilot before the confirmatory run.

Let:

- `gap_lift_pilot = CAS_lift - best_comparator_lift`
- `ratio_lac_pilot = best_comparator_lacunarity / CAS_lacunarity`
- `pooled_sd_lift = pooled standard deviation of lift estimates across pilot bootstrap seeds`
- `pooled_sd_lac = pooled standard deviation of lacunarity estimates across pilot bootstrap seeds`

Pre-registered margins:

- `delta_lift = max(0.05, gap_lift_pilot - 1.5 * pooled_sd_lift)`
- `delta_lac_ratio_pass = max(3.0, ratio_lac_pilot - 1.5 * pooled_sd_lac)`
- `delta_lac_ratio_falsify = 1.5`

Interpretation:

- A comparator within `1.5x` of CAS lacunarity is comparable cleanness and falsifies nested specificity at this tier.
- A comparator `3x` or worse than CAS supports a clean pass.
- Between `1.5x` and `3x` is grey unless the full decision rule below resolves it.

If the pilot produces an unstable or nonsensical margin, the stage pauses and records `BLOCKED_MARGIN_UNSTABLE`; the threshold is not manually tuned after seeing the result.

## 6. Metrics And Statistics

Every taxonomy must report:

1. Hidden readout accuracy and macro-F1.
2. Text-baseline accuracy and macro-F1 for that same label set.
3. Lift over text: hidden score minus text score.
4. Shuffled-label null: primary seed plus null sweep.
5. Flat lacunarity: `Var / Mean^2`.
6. Nested lacunarity where applicable:
   - parent-factor lacunarity
   - child-factor lacunarity
   - joint-class lacunarity
7. Best layer and neighboring-layer stability.
8. Split hash, scenario hash, activation artifact hash, label-assignment hash.

Permutation requirement:

- At least 100 full retrain permutations where computationally feasible.
- Up to 5,000 lightweight label/null permutations when the runner can compute them without retraining every layer.
- If fewer than 100 full retrain permutations are completed, the run is `BLOCKED_PERMUTATION_POWER`, not a pass.

Multiple comparisons:

- Holm correction across the MTC.1 primary family.
- Report raw and corrected values.

## 7. Decision Rules

### PASS - Comparative Specificity Licensed At 20B

All are true:

1. CAS 40E and/or F28 hidden readout remains at least 20 percentage points above its own text baseline.
2. CAS lift beats every coherent matched comparator by `delta_lift`.
3. CAS flat lacunarity is at least `delta_lac_ratio_pass` cleaner than the best coherent matched comparator.
4. F28 nested lacunarity beats the coherent non-CAS 7 x 4 nested comparator on at least 2 of 3 nested scores:
   - parent factor
   - child factor
   - joint class
5. Scrambled labels remain near chance and do not show clean nested structure.

Allowed claim:

> At 20B, CAS factorizes model representations more cleanly than cardinality-matched scrambled, coherent non-CAS, and lexical taxonomies, including in its designed nested two-factor structure.

Not allowed yet:

> CAS is universal across architectures.

That requires MTC.2.

### PARTIAL - Flat Specificity Only

H-MTC-1 and H-MTC-2 pass, but H-MTC-3 fails.

Allowed claim:

> CAS is cleaner than matched alternatives at the flat partition level on 20B; nested two-factor specificity remains open.

Not allowed:

> CAS nesting proves the framework is not invented.

### GREY - Mixed Evidence

Examples:

- CAS wins readout but not lacunarity.
- CAS wins lacunarity but not readout.
- CAS beats scrambled labels but not the coherent non-CAS opponent.
- Comparator is also strong and lands between `1.5x` and `3x` of CAS lacunarity.

Allowed claim:

> CAS is a strong model-internal taxonomy, but uniqueness versus matched semantic controls remains open.

### FAIL - Specificity Not Licensed

Any coherent non-CAS matched taxonomy matches or beats CAS on both:

- hidden readout lift over text
- flat-plus-nested lacunarity

Or:

- H-MTC-3 fails with the coherent non-CAS 7 x 4 nested comparator within `1.5x` of CAS on nested lacunarity.

Required claim:

> CAS labels recover a useful semantic structure, but this experiment does not show CAS is uniquely privileged over matched semantic taxonomies.

### BLOCKED

Use `BLOCKED`, not `FAIL`, when execution cannot fairly score the test:

- fixture lacks enough non-CAS semantic content to materialize the coherent comparator
- missing split artifact
- insufficient control-label coverage
- unstable pilot margins
- fewer than required permutation trials
- missing activation artifact
- label-assignment artifact cannot be hashed

## 8. Too-Good Comparator Branch

If the coherent non-CAS comparator also beats its text baseline and null cleanly, report it as a real result.

Meaning:

> Multiple semantic ontologies factorize transformer space.

This does not erase CAS. It limits the exclusivity claim. CAS can still be useful, predictive, and causal, but the language must stop short of "only CAS reveals this structure."

## 9. Evidence Packet Requirements

The Evidence Packet must include:

- this pre-registration hash
- WORM anchor trace ID for the frozen pre-registration
- CAS taxonomy report
- matched taxonomy reports
- text-baseline reports
- shuffled-label controls
- flat lacunarity table
- nested lacunarity table
- fixed seed list
- split manifest hash
- scenario artifact hashes
- activation artifact hashes
- label-assignment artifact hashes
- model provenance
- explicit PASS/PARTIAL/GREY/FAIL/BLOCKED verdict under this pre-registration

## 10. WORM Freeze Requirement

Before any MTC.1 pilot or confirmatory run is treated as claim-bearing:

1. Freeze this document as v1.0.
2. Compute SHA256.
3. Anchor the SHA256 and document metadata to S3 Object Lock under the Evidence Packet WORM flow.
4. Record the WORM trace ID in the MTC run directory.
5. Refuse claim-bearing execution if the pre-registration hash in the Evidence Packet does not match the frozen hash.

This prevents after-the-fact gate editing.

## 11. Tier-Closure Entry

| Evidence Tier | Status |
|---|---|
| Matched-taxonomy specificity, MTC.1 20B gate | OPEN - draft pre-registration; must freeze and WORM-anchor before claim-bearing run |
| Matched-taxonomy specificity, MTC.2 cross-architecture extension | CONDITIONAL - run only after MTC.1 is PASS or GREY |

## 12. Claim Map

Before MTC passes:

> The current evidence shows the model strongly encodes CAS-labeled distinctions. The matched-taxonomy control is the next pre-registered test of whether CAS is cleaner than same-size semantic alternatives.

If MTC.1 passes:

> At 20B, CAS factorizes model representations more cleanly than cardinality-matched scrambled, coherent non-CAS, and lexical taxonomies, including in its nested two-factor structure.

If MTC.2 later passes:

> CAS factorizes model representations more cleanly than matched alternatives across tested model families and scales.

If MTC fails:

> CAS remains a useful model-internal taxonomy, but the "CAS-specific rather than invented" claim is not licensed by this control tier.
