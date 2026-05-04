# SDG Demographic + Tonal Axes — Canonical Spec

**Status:** Active spec, ratified 2026-05-04 (Task #68)
**Authors:** SDG agent (Task #68)
**Sibling consumers:** Demographic-robustness eval gate (Task #69)

This document is the **single source of truth** for the demographic
and tonal axes the CAS-Native SDG pipeline uses to produce surface-form
variants of canonical Level 3 records. Both Task #68 (SDG expansion)
and Task #69 (eval gate) MUST reference the codes and definitions
here. The code lives at `cas-synthetic/generator/demographic_tonal_axes.py`;
this document mirrors and rationalizes that code.

## 1. Motivation

The SDG defines the model's world. If the corpus speaks one voice,
the model only learns one voice — and at deployment, every speaker
who deviates from that voice (different demographic, different
emotional state, different lexicon) gets bad CAS reads. We close that
gap by emitting K demographic-tonal variants per canonical CAS
structure: same labels, same CAS expression, **different surface
form**.

This sits ABOVE `Lever 3` (free-form English paraphrase) in the SDG
stack. Lever 3 produces demographic-neutral free-form English; #68
layers demographic + tonal variety on top of that. Combined corpus
(canonical + Lever 3 + #68) is the training target.

**Sequencing:** Apply #68 AFTER Lever 3 finishes. Concretely, the
input to `expand_jsonl_demographic_tonal.py` is the merged
canonical+Lever 3 JSONL, not the raw canonical-only file.

## 2. The 8 demographic profiles + 5 tonal registers

Profiles describe WHO is speaking. Tones describe WHAT EMOTIONAL
STATE they are in. The two axes are orthogonal: any profile can speak
in any tone. The rewriter composes them by first selecting profile
lexicon and then layering tone-shaped phrasing on top.

### Profiles (P1–P8)

| code | name | description | speech_traits |
|------|------|-------------|---------------|
| P1   | young_professional_technical | Early-career engineer/analyst, US-based, technical jargon, concise direct phrasing | direct, technical, concise, outcome_oriented |
| P2   | senior_academic_humanities  | University professor, English L1, formal register, qualified claims | formal, qualified, citation_minded, essayistic |
| P3   | mid_career_clinician_direct | Mid-career clinician, action-oriented, plain language | plain, action_oriented, clinical, patient_focused |
| P4   | global_english_indirect      | Non-native English speaker (L2), indirect phrasing, careful constructions | indirect, polite, careful, L2_constructions |
| P5   | lay_casual                   | Non-specialist, conversational, idioms and contractions | casual, idiomatic, contractive, everyday |
| P6   | skeptical_analyst            | Cautious, evidence-seeking, conditional framing | skeptical, conditional, evidence_seeking, tight |
| P7   | anxious_first_timer          | First-time user, hedge-heavy, apologetic openings | hedging, apologetic, uncertain, verbose_qualifier |
| P8   | confident_veteran            | Domain expert, terse, high information density | terse, high_density, expert, elliptical |

Each profile additionally specifies a **typical_lexicon** (concrete
tokens the profile WOULD use), an **avoid_lexicon** (tokens the
profile would NOT use; rewriter uses this as a negative constraint),
and **cultural_markers** (e.g. `US_idiomatic`, `global_english_L2`,
`academic_register` — available to the eval gate for stratified
slicing).

### Tones (T1–T5)

| code | name        | description | hedge_density | energy | length |
|------|-------------|-------------|--------------:|--------|--------|
| T1   | neutral     | Matter-of-fact baseline | 0.10 | medium | medium |
| T2   | anxious     | Hedge-heavy, verbose softeners | 0.85 | low    | long   |
| T3   | frustrated  | Venting, complaint-shaped, short emphatic | 0.05 | high   | short  |
| T4   | excited     | Enthusiastic, exclamatory | 0.05 | high   | short  |
| T5   | reflective  | Introspective, slow, longer sentences | 0.40 | low    | long   |

Each tone additionally specifies **sentence_starters**
("Honestly,", "Look,", etc.) and **sentence_enders** that the rewriter
prepends/appends with deterministic seeding.

### Why curated, not full cross-product

8 × 5 = 40 surface variants per CAS structure. Multiplied across
~19,454 canonicals, the full cross-product is ~778K records — too
large for a v0 corpus. Stratified sampling at K=4 picks 4 of those 40
cells per canonical, giving ~78K surface-form records, while the
sampler ensures every profile and every tone appear roughly equally
often across the full corpus.

## 3. K=4 stratified sampling rationale

`stratified_sample(pairs, k=4, seed=…)` runs three phases:

1. **Phase 1 — maximize profile coverage.** Iterate the shuffled
   pool, pick pairs whose profile has not yet been chosen. With K=4
   over 8 profiles we ALWAYS hit 4 distinct profiles (test:
   `test_stratified_sample_k4_covers_four_distinct_profiles`).
2. **Phase 2 — maximize tone coverage among residuals.** If K > 8
   (extension case), prefer pairs whose tone is unused.
3. **Phase 3 — random residual fill.** Any remaining slots draw from
   the shuffled pool with no preference.

Why K=4 specifically:
- Covers 4 of 8 profiles per canonical → every canonical is seen
  through 4 demographic lenses.
- 4 × 19,454 ≈ 78K records, well within the SDG GPU budget.
- Empirically: spread plus repetition. Each (profile, tone) pair gets
  ~78K / 40 ≈ 1,946 examples — enough that the model learns that
  surface form distribution rather than memorizing it.

Per-canonical seed derivation (driver script): `sha1("{global_seed}|{record_id}")[:12]`,
so the variants for `level2-000000` are reproducible across reruns
without depending on the global iteration order.

## 4. Label-preservation contract

The rewriter is a **pure surface transform**. The following fields
MUST be byte-identical between canonical and variant
(`SACRED_FIELDS` in `demographic_tonal_rewrite.py`):

```
id, source_level2_id, bucket, cas_expression,
natural_language_mapping, assistant_response, follow_up_question,
soft_operator_targets, soft_domain_targets,
turn_type, expression_family, transition_kind,
noetic, domain, drive, register_mode, registers,
authority, has_omega, has_meta_logic, meta_relations,
prior_cas_state
```

Allowed differences between canonical and variant:

- `user_prompt` — rewritten in profile/tone voice, but must preserve
  the recoverable slot block (`families: …; states: …; …`). Test
  `test_rewrite_preserves_slot_block_in_prompt` enforces this.
- `tags` — extended with `["demographic_tonal", "profile_<P>", "tone_<T>"]`;
  every original tag survives. Tags are not in `SACRED_FIELDS`
  because they're metadata, not labels.
- `demographic_profile` — top-level, set to the profile code.
- `tonal_register` — top-level, set to the tone code.
- `expansion_method` — top-level, currently `"rule_based_v1"`.
- `provenance.demographic_tonal` — sub-dict with profile_code,
  profile_name, tone_code, tone_name, expansion_method, seed.

The driver script ALSO regenerates `id` to a `l3conv-dt-…` form so
the variant has a unique identifier. `rewrite_record` itself does
NOT regenerate `id` — that responsibility lives in the driver — so
unit tests that call `rewrite_record` directly see id preserved.

## 5. Reusable interface for the eval gate (Task #69)

The Task #69 agent (demographic-robustness eval gate) consumes the
SAME spec module. The contract is:

```python
from cas_synthetic.generator.demographic_tonal_axes import (
    PROFILES, TONES, ALL_PROFILE_TONE_PAIRS,
    profile_for, tone_for, stratified_sample,
)
from cas_synthetic.generator.demographic_tonal_rewrite import (
    rewrite_record,  # canonical + (P,T) -> variant
    SACRED_FIELDS,   # what the eval gate must hold fixed when scoring
)
```

The eval gate should:

1. Take a held-out canonical eval slice.
2. For each canonical, call `rewrite_record(record, profile_code=…,
   tone_code=…)` to produce one or more variants.
3. Run the model on canonical AND variants.
4. Compute per-(profile, tone) head-accuracy gap vs canonical.
5. Surface gaps where head accuracy drops > some threshold (e.g.
   5pp) on a (profile, tone) cell.

`cultural_markers` on `DemographicProfile` lets the eval gate
stratify reports by region / register class without reading
profile-specific code.

## 6. How to extend (adding a 9th profile or 6th tone)

The spec is designed to be additive. To extend:

1. Add a new `DemographicProfile(...)` to `PROFILES` in
   `demographic_tonal_axes.py`, OR a new `TonalRegister(...)` to
   `TONES`. Use the next code (`P9`, `T6`).
2. Add a corresponding entry to `_PROFILE_FRAMES` and
   `_PROFILE_CLOSERS` in `demographic_tonal_rewrite.py` if it is a
   profile addition. Tone additions extend tone fields but require
   no new template entries — the existing frames absorb the new
   tone via `_apply_tone`.
3. Update `test_eight_profiles_present_and_fully_specified` (or
   `test_five_tones_present_and_fully_specified`) to expect the new
   count.
4. Update this spec doc — the table in §2.
5. Coordinate with the Task #69 eval gate before merging — the gate
   must accept the new code in its stratification.
6. Bump the rewriter's `_EXPANSION_METHOD` to `rule_based_v2` so
   downstream consumers can distinguish corpora produced before vs
   after the extension.

## 7. Path A vs Path B (rule-based vs Claude rewrite)

Task #68 ships **Path A** (rule-based, stdlib, free, deterministic).
Path B (offline Claude API rewrite) is a documented escalation
strategy:

- **Path A coverage estimate:** strong on the 5 high-frequency
  profiles (P1, P3, P5, P6, P8 — direct/clinical/casual/skeptical/expert)
  because their template frames are colloquially native. Weaker on
  P2 (academic) and P4 (L2 indirect): both require longer-form
  syntactic transformations that template substitution can only
  approximate.
- **When to escalate to Path B:** if eval-gate stratification
  (Task #69) shows P2 or P4 head-accuracy gaps > 5pp persisting
  after one full retrain, regenerate ONLY those (profile, tone)
  cells through Claude with a per-cell budget. Reuse the same
  `(canonical_record, profile, tone)` interface; the only difference
  is `expansion_method = "claude_v1"`.
- **Path B implementation sketch:** a stub function that emits
  `(canonical_prompt, profile, tone)` tuples to a batch JSON file,
  plus a separate Claude-side script that reads the batch and
  writes back rewritten prompts. Not implemented in v0 to avoid the
  $X budget on a corpus that may not need it.

## 8. Budget and operational notes

- **Corpus size:** 19,454 canonicals × K=4 = 77,816 demographic-tonal
  records. Driver wall-clock estimate: ~10–15 min on a single CPU
  thread (rule-based, no API calls).
- **Disk:** ~150–200 MB JSONL output (each record ~2 KB).
- **Determinism:** same `--seed` produces byte-identical output.
- **Reproducibility:** include the script invocation (input path,
  output path, `--variants-per-canonical`, `--seed`) in the run
  manifest.

## 9. References

- Code: `cas-synthetic/generator/demographic_tonal_axes.py`,
  `cas-synthetic/generator/demographic_tonal_rewrite.py`,
  `cas-synthetic/scripts/expand_jsonl_demographic_tonal.py`
- Tests: `cas-synthetic/tests/test_demographic_tonal.py`
- Inspirational prior art (NOT copied; different goal):
  `noetic-compass-scaffold/noetic-compass/cas-native/inference/rewrite_shim.py`
  (rule-based axis detector for the inverse direction:
  free-form-English → CAS slot block).
- Sibling task #69 (demographic-robustness eval gate) — must consume
  the SAME spec module.
