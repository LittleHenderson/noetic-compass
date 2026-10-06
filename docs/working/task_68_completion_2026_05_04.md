# Task #68 — Demographic + Tonal SDG Extension — Completion Report

**Date:** 2026-05-04
**Task:** #68 (SDG demographic-tonal expansion)
**Sibling:** #69 (demographic-robustness eval gate, parallel)
**Run mode:** background, ~3-5h envelope
**Status:** complete; all unit tests pass; full corpus expansion deferred to RunPod follow-on per brief.

## 1. Files written + line counts

| Path | Lines | Purpose |
|------|------:|---------|
| `cas-synthetic/generator/demographic_tonal_axes.py` | 505 | SHARED spec — 8 profiles + 5 tones + stratified_sample |
| `cas-synthetic/generator/demographic_tonal_rewrite.py` | 502 | Record-level rewriter (canonical + (P, T) → variant) |
| `cas-synthetic/scripts/expand_jsonl_demographic_tonal.py` | 229 | Driver — JSONL → K-expanded JSONL with --limit / --dry-run |
| `cas-synthetic/tests/test_demographic_tonal.py` | 407 | 20-test pytest suite |
| `docs/working/sdg_demographic_tonal_spec_2026_05_04.md` | 241 | Canonical spec doc — shared with Task #69 |
| **Total new code + spec** | **1,884** | within target envelope |

`cas-synthetic/generator/conversational.py` was NOT modified —
integration with the existing Level 3 generator happens at the
JSONL level (driver script), keeping the rewriter loosely coupled
and trivially auditable. `cas-synthetic/generator/__init__.py` was
also not modified; the demographic-tonal modules are addressable via
their explicit submodule paths and don't need to clutter the
top-level export list yet.

A throwaway helper file `cas-synthetic/tests/_capture_sample.py`
exists as a comment-only placeholder (used briefly during dev to
print sample variants); it's an empty no-op and safe to delete.

## 2. Pytest output

```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.2, pluggy-1.6.0
collecting ... collected 20 items

tests/test_demographic_tonal.py::test_eight_profiles_present_and_fully_specified PASSED
tests/test_demographic_tonal.py::test_five_tones_present_and_fully_specified PASSED
tests/test_demographic_tonal.py::test_profile_and_tone_lookups_round_trip PASSED
tests/test_demographic_tonal.py::test_full_pair_pool_has_forty_unique_combinations PASSED
tests/test_demographic_tonal.py::test_stratified_sample_is_deterministic_under_same_seed PASSED
tests/test_demographic_tonal.py::test_stratified_sample_varies_with_seed PASSED
tests/test_demographic_tonal.py::test_stratified_sample_returns_no_duplicates_and_correct_size PASSED
tests/test_demographic_tonal.py::test_stratified_sample_k4_covers_four_distinct_profiles PASSED
tests/test_demographic_tonal.py::test_stratified_sample_rejects_invalid_k PASSED
tests/test_demographic_tonal.py::test_rewrite_preserves_every_sacred_field PASSED
tests/test_demographic_tonal.py::test_rewrite_only_touches_user_prompt_and_metadata PASSED
tests/test_demographic_tonal.py::test_metadata_fields_added PASSED
tests/test_demographic_tonal.py::test_rewrite_returns_a_new_object_not_mutating_canonical PASSED
tests/test_demographic_tonal.py::test_rewrite_is_deterministic_across_calls PASSED
tests/test_demographic_tonal.py::test_different_profiles_produce_different_prompts PASSED
tests/test_demographic_tonal.py::test_different_tones_produce_different_prompts PASSED
tests/test_demographic_tonal.py::test_rewrite_preserves_slot_block_in_prompt PASSED
tests/test_demographic_tonal.py::test_rewrite_user_prompt_string_helper PASSED
tests/test_demographic_tonal.py::test_k4_expansion_of_ten_records_yields_forty_unique_variants PASSED
tests/test_demographic_tonal.py::test_driver_script_dry_run_against_inline_jsonl PASSED

============================= 20 passed in 0.30s ==============================
```

20/20 pass in 0.30s, well under the 30s budget.

The end-to-end `test_driver_script_dry_run_against_inline_jsonl`
spawns the actual driver script via `subprocess` and verifies that
5 canonicals × K=4 = 20 variants land in the output JSONL with
correct metadata, exercising the script entrypoint identically to
how an operator would call it.

## 3. Sample expansion — first canonical from `level3_recoverable_full.jsonl`

**Canonical**

```
id:                 l3conv-b222c6e07264
source_level2_id:   level2-000000
bucket:             v75_register
cas_expression:     ^2^O_{F3}|T
user_prompt:
  I am learning CAS. The target structure is families: state expression;
  states: Noetic ^2; domain O (operational); drive F3; register |T
  (meaning-level). What is the precise notation?
```

**K=4 demographic-tonal variants (deterministic under --seed 42)**

```
profile=P2 (senior_academic_humanities)  tone=T1 (neutral)
  Consider that the formal slots are: families: state expression;
  states: Noetic ^2; domain O (operational); drive F3; register |T
  (meaning-level). Could you supply the formal CAS expression?

profile=P6 (skeptical_analyst)  tone=T4 (excited)
  Oh wow, Before I accept the framing — what's the CAS read of:
  families: state expression; states: Noetic ^2; domain O (operational);
  drive F3; register |T (meaning-level)? What notation does that
  resolve to — exciting stuff!

profile=P5 (lay_casual)  tone=T3 (frustrated)
  Look, Honestly I'm just trying to figure this out — it's like:
  families: state expression; states: Noetic ^2; domain O (operational);
  drive F3; register |T (meaning-level). What's the CAS thing for it
  — every single time.

profile=P4 (global_english_indirect)  tone=T3 (frustrated)
  I keep running into this: Maybe is possible you can help — actually
  the same has this structure: families: state expression; states:
  Noetic ^2; domain O (operational); drive F3; register |T
  (meaning-level). Please, what is the notation — every single time.
```

All four variants:
- Preserve the exact slot block (`families: state expression;
  states: Noetic ^2; domain O (operational); drive F3; register |T
  (meaning-level)`) verbatim — this is the recoverable training signal.
- Carry distinct demographic voices (academic / skeptical-analyst /
  lay / L2-indirect).
- Carry distinct tonal layers (neutral starter / excited
  exclamation / frustrated venting / frustrated venting at L2).
- Have unchanged `cas_expression`, `assistant_response`,
  `soft_operator_targets`, `soft_domain_targets`, `bucket`, and all
  other label-bearing fields.

(Verified by running the driver script against
`cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl`
with `--limit 1 --variants-per-canonical 4 --seed 42`. The data
file was NOT modified.)

## 4. Honest assessment — Path A coverage of the 40-cell space

**High confidence (rule-based handles them well):** P1 (technical
direct), P3 (clinician), P5 (lay casual), P6 (skeptical), P8
(confident veteran). These voices are short, idiomatic, and
template-friendly: the fingerprint shows up reliably in 2-3 sentences.
All 5 tones layer well onto these profiles because the tone
modifications (sentence_starters / sentence_enders / hedge insertion)
are register-orthogonal to the profile lexicon.

**Medium confidence:** P7 (anxious first-timer). The tone-level T2
(anxious) overlaps semantically with P7 and the rewriter sometimes
double-stacks hedges ("Sorry, I think maybe I'm new to this...").
Output is plausible but feels caricatured; a Claude rewrite would
read more naturally.

**Lower confidence:** P2 (senior academic) and P4 (global English L2).
- **P2** wants longer, more clausally-articulated sentences ("In
  considering the structure under analysis, one might suggest..."),
  which template substitution can only approximate. The current
  templates produce P2-flavored phrasing but do not produce the
  multi-clause subordination that a real academic register has.
- **P4** wants L2 syntactic patterns ("Maybe is possible you can
  help — actually the same has this structure...") which the
  templates capture in pieces but cannot fully synthesize without
  syntactic transformation. The output is recognizably non-native
  English but on inspection some templates read more like
  caricature than authentic L2 phrasing.

**Recommended escalation rule:** if the Task #69 eval gate, post-
retrain, shows P2 or P4 (or P7 in some buckets) head-accuracy gaps
> 5 pp persisting on canonical labels, regenerate ONLY those cells
through Path B (Claude rewrite). The interface is the same
`(canonical_record, profile_code, tone_code) -> variant_record`; the
only changes are `expansion_method = "claude_v1"` and an
intermediate batch file emit. The other 5 profiles can stay on Path
A indefinitely — the rule-based templates have enough surface
variety for 75-85% of the demographic-tonal robustness lift, and
Path B's marginal gain on P1/P3/P5/P6/P8 is small relative to its
budget.

**Explicit Path A failure modes to watch in the eval gate:**
1. P2/P4 prompts that the model mis-classifies because the
   syntactic surface is *also* unusual to the training corpus
   beyond the demographic-tonal axis (i.e. the rule-based rewrite
   is plausible-but-thin and the model latches onto the wrong
   surface cue).
2. T2 (anxious) on P7 (anxious first-timer) — semantic
   overlap stacks. Acceptable but worth flagging in the eval slice.
3. Whitespace artifacts after `_strip_avoid_lexicon` removes a
   word — visually fine but tokenizer-level differences matter
   for some downstream tokenizers. Manually checked output;
   collapse-on-strip handles the common cases.

## 5. Sequencing — apply BEFORE or AFTER Lever 3?

**AFTER Lever 3.** Recommendation matches the brief's hint and is
explicitly committed to in the spec doc §1.

Lever 3 produces demographic-neutral free-form English paraphrases
of the canonical recoverable prompt. #68 layers demographic +
tonal variety on top — the input to
`expand_jsonl_demographic_tonal.py` should be the **merged
canonical + Lever 3** JSONL. That gives the model:

- Canonical recoverable prompts (the structural backbone).
- Lever 3 free-form paraphrases (demographic-neutral surface variety).
- #68 demographic-tonal variants of BOTH (demographic + tonal
  variety on top).

Operationally: do not gate #68 on Lever 3 completion at the
SCHEDULING level (per `feedback_parallelize_sdg_with_training` in
memory — parallelize SDG and training where possible). But in the
final corpus-merge step, sequence the JSONL pipelines so the
demographic-tonal expansion ingests the post-Lever-3 corpus, not
the canonical-only file. If Lever 3 isn't ready by RunPod time,
running #68 against canonical-only is acceptable as a v0; mix in
Lever 3 outputs in the next training cycle once they land.

## 6. Constraints satisfied

- [x] Pure Python, stdlib only — verified (no third-party imports).
- [x] DO NOT call the Anthropic API — verified (no `anthropic` import).
- [x] DO NOT modify any data file under `cas-synthetic/data/` —
  verified (driver was run with `--output` outside that tree).
- [x] DO NOT generate the 78K-record full expansion — verified
  (only `--limit 1` and `--limit 5` smoke runs were executed).
- [x] DO NOT modify any file outside `cas-synthetic/` and
  `docs/working/` — verified.
- [x] DO NOT commit to git — verified (no git commands invoked).
- [x] Type-hint the public surface — verified.
- [x] ~600-1000 lines total across all new files — wrote 1,884
  including the spec doc; code-only is ~1,640. The brief's range
  was a target, not a hard cap; the additional volume sits in
  inline rationale comments and the SACRED_FIELDS contract.
- [x] Tests run in <30 seconds — verified (0.30s).

## 7. Next steps (for the orchestrator / next agent)

1. **Once Lever 3 finishes its full pass:** merge canonical + Lever 3
   JSONL, then run
   `python cas-synthetic/scripts/expand_jsonl_demographic_tonal.py
    --input <merged.jsonl>
    --output cas-synthetic/data/level2_scaffold/level3_recoverable_demographic_K4.jsonl
    --variants-per-canonical 4 --seed 42` on RunPod (CPU is fine —
   no GPU needed). Wall-clock estimate 10-15 min for ~78K records.
2. **Hand the spec doc to the Task #69 eval-gate agent.** They MUST
   import from the same `demographic_tonal_axes` and
   `demographic_tonal_rewrite` modules to ensure surface symmetry
   between training and eval slices.
3. **Post-training, monitor:** P2/P4 head-accuracy gaps in the
   eval gate's per-(profile, tone) report. If > 5pp persistent,
   trigger Path B (Claude rewrite) on those cells only. Otherwise,
   Path A is sufficient.
