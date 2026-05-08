# Wave 3 Phase 1 Corpus — FROZEN AS AUDIT ARTIFACT

**Status (2026-05-08):** `NEEDS_REWORK` — DO NOT use as v1 training data.

## Summary

The 11,897-record corpus at `wave3_phase1_aggregate_20260508.jsonl` passed all four numerical anti-drift gates but **failed content-preservation audit on 2 of 4 slots**:

- `english_to_cas` (2,939 records) — **100% verbatim-copy parrot pipeline** (200/200 sampled). Prompt embeds the CAS as a "reference target" with no alternate English description. Zero training signal.
- `invalid_to_corrected` (2,972 records) — **~30% unrelated-correction rate** (estimated 889 records). The "corrected" expression has zero token overlap with the invalid one in those cases. Model writes plausible but unrelated valid expression and narrates it as a fix. Concentrated in `rpm` and `admissibility` error classes.
- `cas_to_english` (3,001 records) — **structural drift**: recipe coefficient drops (~83% of recipe samples), fractal k-misread as counts (~60-80% of fractal samples), occasional domain swaps. ~440-500 records affected.
- `invalid_to_explanation` (2,985 records) — **clean** (18/25 FAITHFUL, 5/25 MOSTLY, 2/25 minor drift, 0 major). Worth keeping wholesale.

Audit verdict: 2026-05-08 stratified sample (n=100 plus targeted 200-sample verbatim check + 30 leakage spot checks).

## Why NEEDS_REWORK and not just FILTER

The `english_to_cas` failure is a prompt-design defect (no English to translate from), not noise — filtering cannot recover it. The `invalid_to_corrected` failure is a corrector-instruction defect (free-form replacement allowed) — also structural. Both slots need regeneration with fixed prompts.

## What's keep-eligible (after fixes land)

- `invalid_to_explanation` — keep wholesale.
- `cas_to_english` minus recipe + fractal_sequence categories — keep with filters.
- The other two slots — regenerate from scratch.

## Required engineering before next promotion

1. **Review pack format** must include the source CAS expression alongside each output. The current `path_D_wave3_phase1_review_pack_2026_05_08.md` does not — making faithfulness audit impossible without dropping into the raw jsonl.
2. **Content-preservation scorer** — coefficient preservation, domain/register preservation, drive/noetic preservation, Ω target preservation, fractal k-index preservation, invalid→corrected token/AST overlap, English→CAS anti-copy check.
3. **Wave 3 prompt rewrites** — see `feedback_anti_drift_gates_not_content_preservation.md` in user memory.
4. Re-smoke at 500-1K records before any scale-up.

## Cross-references

- Aggregate JSONL: `wave3_phase1_aggregate_20260508.jsonl` (kept for audit).
- Manifest: `wave3_phase1_aggregate_manifest_20260508.json` (status updated to `NEEDS_REWORK`).
- Review pack: `docs/working/path_D_wave3_phase1_review_pack_2026_05_08.md` (frozen, format flaw documented above).
- Memory entries: `feedback_separate_evidence_levels_in_status.md`, `feedback_anti_drift_gates_not_content_preservation.md`.
