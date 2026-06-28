# Version B — Phase 1 SDG Plan

**Owner:** SDG track (CPU-bound, parallel with all GPU training)
**Window:** Months 1–3 (May–July 2026)
**Decision date:** 2026-05-04 — user committed to Version B (from-scratch CAS-Native conversational model) over Version A (renderer-wrapper). See `memory/project_version_b_conversational_plan.md`.

---

## 1. Audit of current state

Already shipped and working in `cas-synthetic/`:

- **Single-turn Level 3 conversational generator** — `cas-synthetic/generator/conversational.py` (~1050 lines). Deterministic template wrapper from Level 2 → Level 3. 6 styles (`recoverable_translation`, `direct_translation`, `tutoring`, `analyst_review`, `repair_check`, `dialogue_followup`) defined in `cas-synthetic/templates/level3_conversational_templates.yaml`. CAS expression is preserved verbatim from Level 2; soft operator/domain targets are inferred by regex.
- **Schema** — `cas-synthetic/schemas/level3_conversation.schema.json` enforces single-turn record shape. `provenance.turn_index` exists but is always 0 today.
- **Corpora on disk:**
  - `data/level2_scaffold/level3_recoverable_full.jsonl` — 19,454 records, 44 MB, recoverable_translation style only
  - `data/level3_pilot_full.jsonl` — 29,181 records, 58 MB, all six styles
  - `data/level2_scaffold/level3_recoverable_eval_1000_v77_relabeled.jsonl` — 1,000-record held-out eval at source-index ≥ 8000
- **Validation** — `cas-synthetic/validation/level3_conversation_validator.py` (schema + compiler check) and `cas-synthetic/validation/level3_review_gate.py` (uniqueness ratios, prompt/response length, CAS-in-response).
- **Tests** — `cas-synthetic/tests/test_level3_conversational.py` covers single-turn generation, style restriction, source-range slicing, schema/validator behavior.

**Uncommitted local changes (do not blow away):** `generator/conversational.py`, `scripts/generate_level3_conversations.py`, `tests/test_level3_conversational.py` — together they add `start_source_record`, `max_output_records`, and `variants_per_source=1` support. Used to produce the held-out eval at index 8000+. **Commit these first** so Phase 1 has a clean base.

What is missing for Version B Phase 1:

1. **Multi-turn dialogues** — every record today is one turn. No `conversation_id` chaining, no per-turn CAS state, no transition labels.
2. **Demographic axes** — no axis exists. Templates read neutral/clinical.
3. **Tonal axes** — `style_id` is the only register dimension. No urgency, no conversational distance, no emotional intensity.
4. **Speaker register modeling** — single voice. The four registers in scope (formal/casual/professional/visceral) are not realized as a labeled axis.
5. **Demographic-robustness eval gate** — no test that verifies CAS targets are stable across demographic axis values for the same underlying CAS expression.
6. **Throughput measurement** — generator has never been run end-to-end at 100K+. Pilot was 29K records / ~10 min wall (estimated). Needs a real benchmark before timeline commits.

---

## 2. Phase 1 work breakdown

### T1. Commit pre-Phase-1 hygiene (0.5 day)
Stage and commit the three modified files plus the `level3_recoverable_eval_1000_v77_relabeled.jsonl` artifact. Establishes Phase 1 baseline.

### T2. Demographic axis schema (2 days)
Add a `demographic_profile` block. Closed vocabularies, no free text:

- `age_band`: `youth | young_adult | adult | middle_aged | older_adult` (5)
- `dialect_family`: `general_american | aave | southern_us | british | south_asian_english | east_asian_english | latino_us | west_african_english` (8) — *linguistic varieties*, not racial labels
- `gender_register`: `feminine | masculine | neutral | non_binary` (4)
- `socioeconomic_register`: `working_class | middle_class | professional_class | academic` (4)
- `regional_setting`: `urban | suburban | rural` (3)

Total cell space = 1,920. We sample ~6 demographic combos per source record, not the full grid.

Schema change: extend `level3_conversation.schema.json` with optional `demographic_profile` object and `demographic_axis_version` in provenance.

### T3. Tonal axis schema (1 day)
Add a `tonal_profile` block:
- `emotional_register`: `calm | warm | distressed | agitated | resigned | curious | skeptical` (7)
- `conversational_distance`: `intimate | familiar | collegial | formal | adversarial` (5)
- `urgency`: `low | moderate | high | acute` (4)
- `speaker_register`: `formal | casual | professional | visceral` (4) — load-bearing for Version B

### T4. Demographic + tonal lexicon and template variants (5 days)
Build `cas-synthetic/templates/demographic_lexicon.yaml` and `tonal_lexicon.yaml`. Add a post-processing pass that rewrites `user_prompt` and `assistant_response` based on axis values **without touching `cas_expression`**.

**Critical invariant:** demographic + tonal axis values MUST NOT change `cas_expression`, `soft_operator_targets`, or `soft_domain_targets`. They only change surface form.

This is the single biggest content-creation task. ~50 lexical entries per axis value; do it style-by-style.

### T5. Multi-turn coherence labels (4 days)
Extend the generator with a multi-turn mode that produces 2–5 turn dialogues from a single Level 2 source. New per-turn fields:

- `conversation_id` already in provenance
- `prev_turn_id`
- `cas_state_transition` object: `{prev_top_noetic, this_top_noetic, transition_kind}` where `transition_kind ∈ {persist, refine, pivot, integrate, escalate, descend, name_emergent}`

Transition kinds are derived deterministically from CAS structural changes, not LLM-judged.

Multi-turn dialogues built by chaining: turn 0 = current Level 3 single-turn record; turns 1..k apply a deterministic transition operator to produce a new compiler-valid expression. Operators:
- **persist**: same CAS expression, new framing
- **refine**: tighten domain or register (e.g., `^2^P → ^2^P_{F3}|A`)
- **pivot**: change Noetic (e.g., `^2 → ^8^9` chain)
- **integrate**: introduce a named emergent (`Ω_*`)
- **escalate / descend**: change urgency tonal axis without changing CAS
- **name_emergent**: cross-register integration → Ω

### T6. Speaker register modeling
Folded into T3/T4. Validate via spot-check during T4.

### T7. Demographic-robustness eval gate (3 days)
New CI test in `cas-synthetic/tests/test_level3_demographic_robustness.py`. For 200 source CAS expressions, generate the same expression under all 8 dialect_family × all 4 speaker_registers × 3 emotional_register samples (~38K records). Assert:

- `cas_expression` is byte-identical across all variants for the same source
- `soft_operator_targets` and `soft_domain_targets` are identical (sum-equality with eps=1e-6)
- `bucket` is identical
- `assistant_response` length within 0.7×–1.4× of reference
- `unique_user_prompt_ratio` per (source × demographic_cell) ≥ 0.6 (catches degenerate template collapse)

Failure of any assertion fails CI.

### T8. Throughput scaling to 100K+ (3 days)
- Benchmark single-process generation on 1K-source slice. Measure records/sec.
- Add `multiprocessing.Pool` partitioning of `--start-source-record` / `--max-source-records` ranges.
- Target: 100K records in under 90 minutes wall on user's CPU (~6 cores usable while GPU is committed).
- Estimate from existing artifacts: ~50 records/sec single-process. 100K single-process ≈ 35 min. 4-way pool ≈ 10 min. **Comfortably feasible without GPU.**

### T9. Test coverage and validation gates (2 days)
- Schema tests for new fields
- Determinism tests (same seed + same axis values → byte-identical record)
- CAS preservation tests (random sample of 500 records, axis-rewriting did not change `cas_expression`)
- Compiler check on 100% of records
- Review gate extended with per-(demographic_cell, tonal_cell) uniqueness ratio thresholds

### T10. Generate the Phase 1 corpus (1 day wall, ~few hours compute)
Run on 10K Level 2 source corpus with 10 axis-combination variants per source = 100K target. Validate, ship as `level3_conversational_v1_100k.jsonl` plus `_metrics.json`.

---

## 3. Sequencing and dependencies

```
T1 (hygiene commit) ──► T2 (demo schema) ──┐
                    └─► T3 (tonal schema) ─┤
                                           ├─► T4 (lexicon + templates) ──► T7 (robust eval)
                                           │                            └─► T9 (tests)
                    └─► T5 (multi-turn) ───┘                            ──► T9
                                                                        ──► T8 (throughput) ──► T10 (100K corpus)
```

Critical path: **T1 → T2 → T4 → T7 → T10**. ~14 working days.

---

## 4. Time estimates (single dev + Claude Code pace)

| Task | Effort | Calendar |
|------|--------|----------|
| T1 hygiene commit | 0.5 d | day 1 |
| T2 demographic schema | 2 d | days 1–3 |
| T3 tonal schema | 1 d | days 2–3 (parallel) |
| T4 lexicon + templates | 5 d | days 4–9 |
| T5 multi-turn + transitions | 4 d | days 4–8 (parallel with T4) |
| T7 robustness eval | 3 d | days 10–12 |
| T8 throughput | 3 d | days 8–10 (parallel with T4 tail) |
| T9 tests | 2 d | days 10–12 (overlap T7) |
| T10 100K corpus | 1 d | day 13 |

**Phase 1 total: ~13–15 working days of focused work.** Comfortably inside Months 1–3 with buffer for review, IP attorney consult cycles, and slippage. Phase 1 is achievable with margin.

---

## 5. Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Demographic lexicon needs expert linguistic review (e.g., AAVE surface forms misrendered) | Medium | High (credibility) | Keep dialect_family closed and minimal; flag any axis values you cannot confidently surface; budget one external reviewer pass before public release |
| Demographic axis rewriting accidentally changes CAS-relevant content and shifts soft targets | Medium | High | T7 robustness gate is exactly this check; if it fails, narrow lexicon entries |
| Multi-turn transition operators produce CAS expressions that fail the compiler | Medium | Medium | Run compiler validation per generated turn; reject and resample on failure; T9 makes this CI-blocking |
| 100K records yields huge prompt/response duplication once axes are crossed (template collapse) | High | Medium | T7's per-cell uniqueness ratio threshold catches this; lexicon expansion is the response |
| Held-out eval split (source_index ≥ 8000) gets contaminated by variant generation | Low | High (eval integrity) | Document split in `provenance`; T9 adds test asserting Phase 1 corpus uses only source_index < 8000 |
| Schema migration breaks existing consumers | Low | Low | New fields are optional; `demographic_axis_version` defaults to "v0" for legacy records |
| Speaker register "visceral" produces content that trips the existing review gate's "no diagnostic / no overclaiming" rules | Medium | Medium | Visceral lexicon must avoid clinical, predictive, or diagnostic verbs; let the review gate bite, then narrow templates |
| Throughput surprise: tokenizer or compiler overhead dominates | Low | Low | T8 benchmarks before commitment; if slow, ship 50K and double in Phase 1.5 |

**No GPU risk** — entire phase is CPU-bound, unaffected by any training run.

---

## 6. Concrete first three tasks for tomorrow morning

1. **Commit the pending hygiene changes (T1, ~30 min).** Stage `cas-synthetic/generator/conversational.py`, `cas-synthetic/scripts/generate_level3_conversations.py`, `cas-synthetic/tests/test_level3_conversational.py`, and the held-out eval artifact. Run `pytest cas-synthetic/tests/test_level3_conversational.py` first; commit only if green.

2. **Draft `docs/working/level3_conversational_v2_axis_spec.md` (T2 + T3 schema, ~2–3 hours).** Lock the closed vocabularies for demographic_profile and tonal_profile in writing before coding. Single page each. This is the doc that Phase 2 (Dialogue State Tracker) will read to know what axis labels exist.

3. **Run the throughput benchmark (T8 prep, ~1 hour).** Time `python cas-synthetic/scripts/generate_level3_conversations.py --max-source-records 1000 --variants-per-source 5` end-to-end on cold cache. Records/sec is the only number that decides whether T8 needs `multiprocessing` or whether single-process is fine.

---

## Critical files for implementation

- `cas-synthetic/generator/conversational.py`
- `cas-synthetic/schemas/level3_conversation.schema.json`
- `cas-synthetic/templates/level3_conversational_templates.yaml`
- `cas-synthetic/validation/level3_review_gate.py`
- `cas-synthetic/tests/test_level3_conversational.py`
