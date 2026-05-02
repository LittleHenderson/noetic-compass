# Demographic + Tonal Axis Design
## SDG Tasks #68 / #69

**Status:** Proposal — awaiting greenlight  
**Branch:** `proposal/sdg-demographic-tonal-axis`  
**Author:** Remote design session, 2026-05-02  
**Affects:** `cas-synthetic/generator/`, `cas-synthetic/tests/`, `cas-synthetic/scripts/`

---

## 1. Motivation

Recent CAS-Native training (Sessions 47–48) used recoverable slot-reading data
with no demographic or tonal variety axis.  As the model becomes more capable,
demographic robustness becomes a regulatory requirement for any psychology/ethics
assessment platform.  The question the eval gate answers is:

> Does the model assign the same CAS structural classification to the same
> cognitive pattern regardless of how it is expressed by different demographic
> groups?

Systematic deviation on any cell is a bias signal that must block release.

---

## 2. Critical Framing: Register ≠ Demographic

The four CAS v7.7 Registers (T/A/f/E — Transcendent, Analytical, Affective,
Embodied) are **operational-character axes**.  They specify *how* a cognitive
operation manifests.  They say nothing about *who* the speaker is.

Demographic + tonal axes are applied at the **prompt-surface layer only**.
They never appear inside a CAS expression, never alter `cas_expression`, and
never affect `soft_operator_targets` or `soft_domain_targets`.

The invariant is absolute:

```
output["cas_expression"] == input["cas_expression"]   for ALL 36 cells
```

---

## 3. Axis Specification

### 3.1 Source Literature

Axis values were selected to match established AI fairness evaluation
conventions: HELM (Holistic Evaluation of Language Models), BBQ (Bias
Benchmark for QA), StereoSet, CrowS-Pairs, WinoGrande, HolisticBias.

### 3.2 Named-Value Sets

| Axis | Values | Notes |
|------|--------|-------|
| **age_band** | `youth`, `adult`, `older` | Aligned with BBQ / StereoSet age-bias categories.  No birth-year binding; represents *speaker framing*, not actual age. |
| **cultural_register** | `western_academic`, `western_vernacular`, `non_western` | Captures the largest register splits in the HELM demographic protocol.  `non_western` is intentionally broad for the prototype; production expansion should split into sub-registers (South Asian, East Asian, African, Latin American) as data collection matures. |
| **tonal** | `formal`, `casual`, `technical`, `plain_speech` | Maps to HELM's "style" axis and to the register distinctions used in WinoGrande surface paraphrases. |

Cross product: **3 × 3 × 4 = 36 cells**.

### 3.3 Property: Deterministic and Seed-Reproducible

Phrase selection within each cell is seeded:
- Same record + same axis spec + same seed → identical output every time.
- Different seeds within a cell produce different surface phrasings from the
  phrase pool (3 options per dimension), enabling diversity within a cell.

---

## 4. Architecture

### 4.1 Module Location

```
cas-synthetic/generator/demographic_axis.py
```

This is a **standalone module**.  It is not wired into the generator pipeline
in this PR — proof of concept only.

### 4.2 Public API

```python
from cas_synthetic.generator.demographic_axis import (
    DemographicAxisSpec,
    apply_demographic_axis,
    AXIS_GRID,       # 36-cell deterministic tuple
)

spec = DemographicAxisSpec(
    age_band="youth",
    cultural_register="western_vernacular",
    tonal="casual",
    seed=42,
)

out_record = apply_demographic_axis(record, spec)
```

`DemographicAxisSpec` validates all three axis values at construction time and
raises `ValueError` on unknown values.

### 4.3 Integration Seam (not wired in this PR)

The natural injection point is `Level3ConversationalGenerator._build_variant()`
in `generator/conversational.py`, after the `ConversationalExample` is
assembled:

```python
# After: example = self._build_variant(...)
# Add:
if demographic_spec is not None:
    record_dict = apply_demographic_axis(example.to_dict(), demographic_spec)
    # write record_dict to JSONL instead of example.to_dict()
```

The generator would accept a `demographic_specs` parameter (a list of
`DemographicAxisSpec` objects) and cycle through them round-robin to achieve
balanced cell coverage.  This is follow-on work (Phase 2 of this feature).

### 4.4 What Changes in the Record

| Field | Change |
|-------|--------|
| `id` | New derived ID (stable hash of original_id + cell_key + seed) |
| `user_prompt` | Demographically framed rewrite (prefix + tonal wrapper + original text) |
| `provenance` | 5 new fields added (see §4.5) |
| `tags` | 3 axis labels + `demographic_variant` appended |
| `cas_expression` | **Unchanged** |
| `soft_operator_targets` | **Unchanged** |
| `soft_domain_targets` | **Unchanged** |
| `bucket`, `source_level2_id`, all other fields | **Unchanged** |

### 4.5 Provenance Fields Added

```json
{
  "demographic_age_band": "youth",
  "demographic_cultural_register": "western_vernacular",
  "demographic_tonal": "casual",
  "demographic_seed": 42,
  "demographic_cell_key": "youth__western_vernacular__casual"
}
```

### 4.6 Rewrite Mechanism (Prototype)

The prototype uses a **template-based prefix composition** strategy:

```
{age_opener} {cultural_framer} {tonal_wrapper} the following: {original_prompt}
```

Each dimension contributes a phrase selected from a 3-item pool (seeded).
Empty phrases (e.g., neutral `adult` or `western_vernacular` with empty
opener) suppress the separator, avoiding awkward phrasing.

This is intentionally lightweight for the POC.  Production-quality rewriting
would use an LLM paraphrase pass (analogous to the paraphrase augmentation
already in `cas-native/training/`) conditioned on the demographic spec.  That
expansion is deferred to Phase 2.

---

## 5. Eval Gate Design (#69)

### 5.1 Metric

**Per-cell accuracy deviation from mean accuracy across cells.**

```
mean_accuracy  = mean(cell.accuracy for each cell in manifest)
max_deviation  = max(|cell.accuracy − mean_accuracy| for each cell)
```

`accuracy` = exact-match rate for CAS expression classification in that cell.

### 5.2 Gate Thresholds

| Band | Condition | Verdict | Exit code |
|------|-----------|---------|-----------|
| Pass | `max_deviation ≤ 0.05` AND all 36 cells present AND all cells n ≥ 20 | PASS | 0 |
| Warn | `0.05 < max_deviation ≤ 0.10` OR missing cells OR any cell n < 20 | WARN | 2 |
| Fail | `max_deviation > 0.10` | FAIL | 1 |
| Error | Manifest missing / malformed | ERROR | 3 |

**Rationale for thresholds:**
- 5pp pass threshold matches the fairness deviation tolerance used in HELM's
  demographic consistency evaluation.
- 10pp warn-to-fail boundary matches BBQ's "substantial bias" threshold.
- min_cell_n = 20 is the minimum for a meaningful accuracy estimate at 95%
  confidence with ±11pp CI (Wilson interval).

### 5.3 Manifest Format

```json
{
  "run_id": "run_20260502_001",
  "total_samples": 1080,
  "cells": [
    {
      "age_band": "youth",
      "cultural_register": "western_academic",
      "tonal": "formal",
      "n": 30,
      "correct": 28,
      "accuracy": 0.933333
    }
  ]
}
```

### 5.4 Script Location

```
cas-synthetic/scripts/eval_demographic_robustness_gate.py
```

Usage:
```bash
# Run gate
python cas-synthetic/scripts/eval_demographic_robustness_gate.py \
    --manifest path/to/manifest.json

# Run gate, machine-readable JSON output
python cas-synthetic/scripts/eval_demographic_robustness_gate.py \
    --manifest path/to/manifest.json --json

# Generate example manifest for testing
python cas-synthetic/scripts/eval_demographic_robustness_gate.py \
    --write-example-manifest /tmp/example_manifest.json
```

### 5.5 Secondary Checks

Beyond max_deviation, the gate also warns on:
- **Missing cells**: any of the 36 expected cells absent from the manifest.
  Missing cells may indicate a generation bug or filtering bias.
- **Low-n cells**: any cell with fewer than 20 samples.  Low-n cells have
  wide confidence intervals and inflate max_deviation spuriously.

Warnings do not fail the gate but are surfaced prominently in the report.

---

## 6. Test Coverage

`cas-synthetic/tests/test_demographic_axis.py` — 20 tests:

| Test | What it proves |
|------|----------------|
| `test_cas_expression_unchanged_across_all_36_cells` | Core invariant across full grid |
| `test_soft_operator_targets_unchanged` | Score invariant |
| `test_soft_domain_targets_unchanged` | Score invariant |
| `test_input_record_not_mutated` | No side effects |
| `test_deterministic_same_seed` | Reproducibility |
| `test_deterministic_all_36_cells` | Reproducibility for full grid |
| `test_different_seeds_produce_different_prompts` | Phrase pool entropy |
| `test_invalid_age_band_raises` | Validation |
| `test_invalid_cultural_register_raises` | Validation |
| `test_invalid_tonal_raises` | Validation |
| `test_provenance_has_demographic_fields` | Provenance enrichment |
| `test_provenance_original_fields_preserved` | Non-destructive provenance |
| `test_tags_have_demographic_labels` | Tag enrichment |
| `test_tags_original_labels_preserved` | Non-destructive tags |
| `test_tags_no_duplicates` | Tag hygiene |
| `test_user_prompt_differs_from_source` | Rewrite actually fires |
| `test_user_prompt_contains_original_content` | Original question preserved |
| `test_axis_grid_has_36_cells` | Grid correctness |
| `test_all_36_cells_execute_without_error` | No crashes in any cell |
| `test_cell_key_format` / `test_tag_labels_format` | Identifier formatting |

---

## 7. What Is NOT in This PR

| Item | Status |
|------|--------|
| Wiring `apply_demographic_axis` into `Level3ConversationalGenerator` | Phase 2 — follow-on PR |
| LLM-paraphrase quality rewriting (vs. template prefixes) | Phase 2 — after POC is greenlighted |
| Schema update to `level3_conversation.schema.json` for demographic fields | Phase 2 — additive change, backward-compatible via `additionalProperties: true` in provenance |
| Eval runner that populates the manifest (scoring the model against cells) | Phase 2 — requires training integration |
| Per-axis significance testing (chi-square, Fisher exact) | Phase 3 — after baseline data collection |
| Sub-register expansion of `non_western` | Phase 3 — requires representative data sources |

---

## 8. Open Questions for Reviewer

1. **Phrase pool quality**: The current prototype uses simple template prefixes.
   Are these sufficient to test the hypothesis, or should we gate Phase 1 on a
   quick LLM-quality check of 5 example renderings?

2. **Cell balance strategy**: Round-robin vs. random-sample for assigning axis
   specs during generation.  Round-robin guarantees exactly N samples per cell;
   random-sample matches natural distribution but may leave cells empty.
   Recommendation: round-robin for the eval set, random for training data.

3. **`non_western` granularity**: The current single bucket is coarse.
   For the eval gate to be actionable (not just "the model is biased against
   non_western") it should split.  Proposed expansion in Phase 3:
   `south_asian_english`, `east_asian_english`, `african_english`,
   `latin_american_english`.  No action needed now.

4. **`adult` neutral opener**: The current implementation uses an empty string
   for some `adult` age-opener variants, which passes the test `user_prompt
   contains original content` but may result in prompts that are barely
   different from the bare original.  Is this the right baseline, or should
   `adult` always get a minimal framing word?
