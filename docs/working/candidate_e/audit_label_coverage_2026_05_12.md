# Pre-Stage-1 Audit — Label Coverage on rpm_chain Training Records

**Date:** 2026-05-12
**Scope:** Confirm whether the existing collator (`simplex_collator.SimplexCollator`) emits full-span vs head-only STAGE_VAR slot labels on rpm_chain training records.
**Method:** Production tokenizer (Stage 6 v6 artifacts, vocab 38,683) + `SimplexCollator(enable_simplex_aux=True)`. 20 rpm_chain records randomly sampled from `cas-synthetic/data/path_d/v1_mix_nlgen_train.jsonl`. For each record, compute `typed_slot_positions.argmax(dim=-1)` and identify contiguous STAGE_VAR spans.
**Companion runs:** the earlier 100-record copy-supervision firing probe (also 2026-05-12, confirmed `typed_slot_source >= 0` on 1836/1836 STAGE_VAR positions). This audit extends that with span-level analysis.

## Headline findings

| Property | Result |
|---|---|
| Records audited | 20 |
| STAGE_VAR spans per record | **2/2/2/2/2/...** (universally 2, n=20) |
| Span length (sub-tokens per span) | 8-10 (matches full identifier shape: `stage<X><n>_<m>_<dddd>`) |
| Unique identifiers in target text (avg) | 4 per record (A0 + D + W + P) |
| Total identifier occurrences in target text (avg) | 6 per record (4 unique + 2 repeats — typically `stageW...` and `stageP...` mentioned twice via the trailing "leads to" / "with X driving Y" connective) |
| **STAGE_VAR labelled coverage: unique** | **2/4 = 50%** |
| **STAGE_VAR labelled coverage: total occurrences** | **2/6 = 33%** |

## Sample evidence (3 records)

```
Record 1 (id: v1mix_cas_to_english_002621):
  identifiers in target: ['stageA0_2_0185', 'stageD2_2_0185', 'stageW2_2_0185', 'stageP2_2_0185',
                          'stageA0_2_0185', 'stageD2_2_0185']
  STAGE_VAR spans: 2
    [pos 2..10]  text='stageA0_2_0185'  src_idx=[2..10]   ← full-span, contiguous
    [pos 23..31] text='stageD2_2_0185'  src_idx=[20..28]  ← full-span, contiguous
  UNLABELED: stageW2_2_0185, stageP2_2_0185 (and the repeat-occurrences of A0 and D)

Record 2 (id: v1mix_cas_to_english_000949):
  identifiers: ['stageA0_7_0194', 'stageD7_7_0194', 'stageW7_7_0194', 'stageP7_7_0194',
                'stageW7_7_0194', 'stageP7_7_0194']
  STAGE_VAR spans: 2 (stageA0_7_0194 + stageD7_7_0194). W and P unlabeled.

Record 3 (id: v1mix_cas_to_english_003398):
  identifiers: ['stageA0_2_0381', 'stageD2_2_0381', 'stageW2_2_0381', 'stageP2_2_0381',
                'stageA0_2_0381', 'stageD2_2_0381']
  STAGE_VAR spans: 2 (stageA0_2_0381 + stageD2_2_0381). W and P unlabeled.
```

## Diagnosis

**Two-axis coverage analysis:**

| Axis | Coverage | Status |
|---|---|---|
| **Within-span** (does the labeller tag every sub-token of a labelled identifier?) | **FULL** — every sub-token in the 8-10-token span has `typed_slot_positions = STAGE_VAR` and `typed_slot_source` pointing at the corresponding source position. Per-token copy supervision is contiguous and aligned. | ✓ no fix needed |
| **Cross-chain** (does the labeller tag all identifiers in the chain?) | **PARTIAL** — only the first 2 unique identifiers per record (typically A0 + D stages). W and P stages are unlabeled as STAGE_VAR (presumably tagged CONNECTIVE by default). | **✗ needs fix in Stage 1** |
| **Repeat occurrences** (when an identifier appears 2+ times in the target text, are all occurrences labelled?) | **NONE labelled beyond the first occurrence.** Repeats are unlabeled. | **✗ needs fix in Stage 1** |

## Connecting to Codex's diagnosis

Codex's framing was *"the copy signal is too weak / too local / too template-correlated to force source-grounded binding."* This audit gives that diagnosis a specific mechanistic locus on the supervision side:

- **"Too weak"**: per-record copy supervision applies to only 33% of identifier occurrences and 50% of unique identifiers. Two-thirds of the binding signal a 4-stage rpm chain *could* provide is silently dropped.
- **"Too local"**: the labelled spans (first two identifiers) are consecutive in the target text (positions ~2-31), inside the first sentence clause. Identifiers later in the reply (W, P, repeats) get no copy gradient. The model never learns to point at source positions that correspond to identifiers appearing later in the reply.
- **"Too template-correlated"**: combined with template homogeneity (most rpm replies use `"Let stage<X> name ..., stage<Y> name ..."`), the labelled positions are always at roughly the same target offsets. The copy head can satisfy the loss by attending to specific *positional* offsets in source, not by attending to the right *identifier*.

This is consistent with B3's broader-eval failure mode: on fresh records the model produces shape-correct identifiers (it learned the template + identifier-shape from the labelled positions) but with wrong digits (it never learned positional source binding for the later identifiers, and on fresh inputs the positional-offset shortcut breaks down).

## Implications for Candidate E Stage 1

The full-span requirement in the design doc's six structural properties is **already satisfied** within labelled spans. **The actual fix needed is cross-chain coverage:** Stage 1 SDG must produce records where ALL identifier occurrences in the target text — including W, P, and repeats — get `typed_slot_positions = STAGE_VAR` and a valid `typed_slot_source` index pointing at the corresponding source position.

Two implementation paths:

1. **Fix the existing `_derive_anchors` / `find_stage_var_spans` to tag all occurrences** (likely the cleanest — the bug is in the labeller, not the data). Then re-generate `rpm_copy_grounding_v2_*.jsonl` artifacts with the fixed labeller. After this fix, the existing v1 corpus may also benefit, but Candidate E only commits to the new corpus.

2. **Generate Stage 1 corpora with explicit full-identifier-list metadata** so the new collator/anchor logic always sees the complete identifier set per record. Same end result.

Either path: Stage 1 must verify post-generation that the per-record STAGE_VAR span count equals the per-record identifier count (allowing for the within-span full coverage that's already correct).

## Recommended Stage 1 spec update

Add as a 7th structural property of `rpm_copy_grounding_v2`:

> **Cross-chain full coverage.** Every distinct identifier occurrence in the target text (including W-, P-, and repeat-stage identifiers) must be labelled with `typed_slot_positions = STAGE_VAR` and a valid `typed_slot_source` pointing at the corresponding source CAS position. Per-record audit: STAGE_VAR span count == identifier occurrence count in target. Current collator behavior (50%-coverage two-spans-per-record) is the load-bearing labelling defect; Stage 1 must fix it.

## Out-of-scope (deferred, not part of this audit)

- Did the existing collator's partial coverage actually cause B3's failure (causal claim)? This audit demonstrates partial coverage is *consistent* with the diagnosis but does not prove causality. Stage 2b's TF gate is the falsifier: if full-coverage labelling + the data wedge produce ≥80% TF fresh recovery, the causality is confirmed empirically.
- Other slot types (OMEGA, COEFFICIENT, REGISTER_LETTER, DOMAIN_LETTER, DRIVE_LETTER, FRACTAL_K_LITERAL) — this audit only checked STAGE_VAR coverage on rpm_chain records. A separate audit of those slot types on their respective record categories would be useful but is not load-bearing for E.

## Companion data

- Audit script (inline above; not committed as a file — single-run probe)
- Probe records: 20 sampled with `random.seed(7)` from `v1_mix_nlgen_train.jsonl`
- Pattern is universal across all 20 samples (no outliers; spans-per-record = 2 for all 20 records)
- Span lengths: 9 tokens × 24 spans + 10 tokens × 14 spans + 8 tokens × 2 spans = 40 spans total

## Decision

**Audit verdict: cross-chain coverage gap confirmed.** Stage 1 spec must add the 7th structural property above before SDG generation begins. The fix lives in the labeller / anchor derivation, not in tokenization or in the model. The 5 artifact paths in the design doc remain correct.
