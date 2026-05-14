# Track 1 + Track 2 Pre-flight Audit — 2026-05-14

**Owner:** Claude
**Trigger:** User directive 2026-05-14, ratified by Codex `codex_audit.md` 2026-05-14T00:??Z (commit `a0f64da`).
**Status:** DOC ONLY — no training launched. Awaiting Codex sign-off + user "go" before any pod work or API spend.

## Track 1 — Local NL corpus audit

### Corpus inventory

| File | Records | Source |
|---|---|---|
| `wave3_step2_5_english_descriptions_20260508T203848Z.jsonl` | 5,263 | Wave 2.5 paid run (commit `96ec022`) |
| `wave3_step2_5_english_descriptions_20260509T002355Z.jsonl` | 4 | Wave 2.5 backfill round 1 |
| `wave3_step2_5_english_descriptions_20260509T002541Z.jsonl` | 1 | Wave 2.5 backfill round 2 |
| `wave3_step2_5_layer3_clean_20260508T110453Z.jsonl` | 305 | Layer-3 validator pass, earlier same-day run |
| `wave3_step2_5_clean_current_validators_20260508T110453Z.jsonl` | 346 | Current-validator pass, same earlier run |

### Dedupe

- Wave 2.5 union: **5,268 unique seed_ids**.
- Wave 3 layer3 clean: **305 records**, of which **279 (91.5%) overlap** with Wave 2.5.
- Layer3 NEW (not in Wave 2.5): **26 records**.

**Net merged train pool: 5,294 unique records.**

### Schema compatibility

Both files share the load-bearing keys:

- `source_cas` (CAS expression string)
- `english_description` (NL render)
- `grammar_category` (one of 10 buckets)
- `seed_id`

Wave 2.5 main carries extra SFE metadata (`sfe_attempts_log`, `sfe_tries`). Wave 3 layer3 carries extra post-filter metadata (`post_filter_validators_*`). Neither extra group is needed by the trainer.

Encoding verified as genuine UTF-8 (the mojibake observed during PowerShell console inspection was console rendering only, not file corruption).

### Grammar category distribution

Wave 2.5 main (5,268):

| Category | Records | % |
|---|---|---|
| state_literal | 1,019 | 19.3% |
| binary_composition | 733 | 13.9% |
| meta_logic_relation | 710 | 13.5% |
| cross_register_omega | 579 | 11.0% |
| recipe | 481 | 9.1% |
| fractal_sequence | 466 | 8.8% |
| let_binding | 441 | 8.4% |
| diagram_export | 417 | 7.9% |
| rpm_chain | 359 | 6.8% |
| inversion | 63 | 1.2% (under-represented) |

Wave 3 layer3 NEW records skew toward inversion / fractal_sequence / cross_register_omega — the under-represented Wave 2.5 buckets. Worth keeping in.

### Schema mismatch — what model to train

`train_native_nl_gen.py` expects `(cas_expression, prompt_text, reply_text)` triples for the conversational generation task. The Wave 2.5 corpus is `(source_cas, english_description)` pairs with NO `prompt_text` field.

**Resolution per Stage 4 spec (`docs/working/stage4_minimal_nl_training_spec_2026_05_13.md`):**

- The user-ratified target is the **NL→CAS Front Door (Stage 4)**, not conversational generation.
- Direction is **inverted**: `english_description` → input, `source_cas` → target.
- Trainer is **`train_simplex_mvp.py`** reusing the Stage 3 simplex-MVP backbone, NOT `train_native_nl_gen.py`.
- A small adapter is needed to rewrite Wave 2.5 records into the simplex-MVP input contract.

### Recommended Track 1 next steps (pre-pod)

1. **Merge + dedupe** Wave 2.5 union ∪ Wave 3 layer3 NEW → `path_d/stage4_track1_merged_2026_05_14.jsonl` (5,294 records).
2. **Field inverter** script: emit (english_in, cas_out, grammar_category) rows under simplex-MVP input contract.
3. **Eval split:** dedupe vs `level3_recoverable_eval_1000_v77_relabeled.jsonl` (Stage 4 spec line 274; eval-only).
4. **CPU smoke** on 64-record slice via `train_simplex_mvp.py --smoke-test`.
5. **AUTHORIZED entry** in `decisions.md` for pod training (separate from this audit) — only after Codex sign-off on the inversion adapter.

## Track 2 — External Q&A → CAS SDG

### Dataset pick — SQuAD v2 (Codex/user recommendation)

- **HF card:** `rajpurkar/squad_v2`
- **License:** **CC BY-SA 4.0** (NOT plain CC BY)
- **Field:** `question` (string)
- **Pilot size:** 2K–5K questions

**License flag — share-alike clause:** CC BY-SA means any **derivative dataset we publish** inherits the SA license. Training a model on the corpus is the gray-zone normal case (most jurisdictions treat trained weights as not a derivative of training data), but **if we ever publish or ship the training corpus itself as an artifact**, that artifact is SA-bound. Codex's audit did not flag this. Treat the SQuAD-derived corpus as quarantined: locally used for training only, never shipped, never published, never included in any released dataset artifact. Surface to IP attorney as part of the broader v0 IP review.

### Pipeline (external Q → SDG → SFE → train pair)

```
SQuAD v2 questions only (drop answers + context)
   ↓
CAS SDG seed enumerator (existing: cas-synthetic/scripts/generate_path_d_seeds.py)
   ↓
SDG generator (existing: deterministic renderers + optional Haiku drafter)
   ↓
SFE round-trip gate (existing: cas-synthetic/validation/level3_review_gate.py + Wave 2.5 SFE pipeline)
   ↓
Promoted (English_Q, CAS_expression) pair → Tier 1+
```

**Scope departure from Stage 4 spec:** the Stage 4 spec §3.3 originally treated Tier 3 (HF/Kaggle) as **English-side STYLE PRIORS only**. The user/Codex's framing extends this to "external Q as seed for SDG-generated CAS supervision." This is OK in principle — output passes the same SFE gate Wave 2.5 went through, ending up Tier-1-equivalent — but the Stage 4 spec should be amended to admit this as a sanctioned corpus-construction path before launch.

### Recommended Track 2 next steps (pre-API-spend)

1. **License re-confirm:** read SQuAD v2 HF card directly, screenshot license string for the record.
2. **Spec amendment:** small patch to Stage 4 spec §3 admitting "external-question-as-SDG-seed" as a sanctioned Tier 1 input path (subject to SFE gate).
3. **Sample read:** pull 5K SQuAD v2 questions via `datasets` library, sample-read 50 to confirm question shape + filter out CAS-irrelevant prompts (math, named-entity factoid, dates).
4. **SDG pilot:** run 100-question pilot through the existing path_d SDG pipeline, sample-read promoted output, compute SFE acceptance rate before scaling.
5. **AUTHORIZED entry** for 2K–5K pilot run with budget cap ≤ $30 (per the Wave 2.5 cost reference of ~$0.0058/record).

## Combined invariants (apply to both tracks)

- No foreign-model answer text enters any training target. SQuAD v2 answers and `context` fields are **discarded**, not stored alongside questions.
- All training pairs compile via `api/notation/compiler.py`. Compiler is authoritative grammar.
- All Stage 4 outputs populate `traceability_v0` per the Mode 7 trace contract.
- 50K Claude dialogue file in `cas-synthetic/data/native_nl/` is **excluded from training** per `feedback_cas_native_data_strategy_2026_05_13.md`. Kept on disk for offline reference only.
- Per `feedback_back_up_successful_runs_imperative.md`: any successful training checkpoint copied to `D:\tksCAS-archive\` immediately on completion.
- Per `feedback_parallelize_sdg_with_training.md`: Track 2 SDG runs on laptop CPU in parallel with Track 1 training on pod — never serialize.

## What's NOT in this doc

- Pod launch commands. A separate AUTHORIZED entry in `decisions.md` will surface the locked launch command after Codex sign-off.
- API spend authorization. Track 2 API spend gated separately.
- Stage 4 spec amendment text. Will draft as a follow-up patch if user agrees to the scope departure.

## Open decisions for user

1. **Track 1 direction confirm:** train the inverted (English → CAS) direction via `train_simplex_mvp.py`, not the CAS → English direction via `train_native_nl_gen.py`. Is this the intent?
2. **Track 2 scope departure:** admit external-question-as-SDG-seed as a Tier 1 input path. OK to amend Stage 4 spec, or keep Track 2 quarantined as Tier 3 style-priors only?
3. **SQuAD v2 SA license:** quarantine-only (no artifact publication) acceptable, or do we want to switch to an Apache 2.0 alternative (OpenAssistant OASST1, Natural Questions) before any API spend?
