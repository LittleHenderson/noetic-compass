# CAS-Native Tokenizer — Wave 1 Handoff

**Status:** Wave 1 complete and ready for commit. 64 tokenizer tests pass; tokenizer + runtime/intent neighbors pass at 82 passed, 1 skipped; structured-prediction regressions pass at 14 passed, 1 skipped. Wave 2 design docs are present for review.

**Author of this doc:** session-38 build, May 1, 2026.

**Audience:** Codex or any other agent picking up the CAS-Native AI track in a fresh context. This document is self-contained.

---

## 0. Session 39 update - vocabulary and embedding bridge landed

Wave 1 is no longer only a tokenizer artifact. The next bridge is now implemented:

- `cas-native/tokenizer/vocabulary.py` assigns stable, source-aware vocabulary IDs to `StructuredToken` streams. It preserves the distinction between CAS literals (`cas:^2^P_{F4}|f`), lexicon phrases (`lex:drawn to`), learned tags, and fallback surfaces.
- `cas-native/training/structured_token_adapter.py` converts token streams into `StructuredTokenBatch`: `input_ids`, `attention_mask`, 25-dim CAS signature features, confidence, source IDs, and normalized span features.
- `cas-native/model/structured_token_embedding.py` fuses surface embeddings with CAS-side features through a gated adapter and can feed `StructuredPredictionHead` directly via `StructuredTokenStructuredPredictor`.

Verification for this update:

- `13 passed` for the direct vocabulary/adapter/embedding tests.
- `100 passed` for tokenizer + neighboring runtime/intent/structured-prediction tests.
- `26 passed, 1 skipped` for model/training regressions.

Role in the stack: this update is the first encoder-consumable CAS-native input substrate. It does not yet train a full CAS Transformer, but it gives the upcoming runner a real path from natural-language prompt -> structured tokens -> CAS-axis tensors -> hidden states -> structured prediction heads. The next implementation step is a train/eval mode over Level 3 data using `StructuredTokenEmbedding` + `StructuredPredictionHead`, measured against the 48.7% leak-fixed hash-feature baseline.

---

## 0.1 Session 40 update - structured-token train/eval runner landed

The train/eval mode named above now exists.

- `cas-native/training/train_structured_prediction.py --input-mode structured_token` trains `StructuredTokenEmbedding + StructuredPredictionHead`.
- The runner builds `StructuredTokenVocabulary` from filtered training `user_prompt` text only; eval prompts reuse the training vocabulary. Assistant responses, CAS expressions, and held-out eval answers are not used to build input features.
- Output artifacts: `manifest.json`, `samples.jsonl`, `structured_token_vocab.json`, and `best_structured_token_model.pt`.
- Every eval manifest includes `baseline_comparison` against the honest leak-fixed hash-feature baseline: `487/1000 = 48.7% all-heads-exact`.
- Real CLI smoke completed over Level 3 files with `--limit 256 --eval-limit 60 --epochs 1`; it produced `0/60` all-heads-exact, which is expected for a tiny wiring smoke. The value of that run is that the pipeline executes, writes artifacts, and reports the baseline delta explicitly.

Recommended next command shape for a real local comparison:

```powershell
& "C:\Users\wakil\AppData\Local\Programs\Python\Python312\python.exe" `
  noetic-compass-scaffold/noetic-compass/cas-native/training/train_structured_prediction.py `
  --input cas-synthetic/data/level2_scaffold/level3_recoverable_full.jsonl `
  --eval-input cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000.jsonl `
  --input-mode structured_token `
  --limit 19454 `
  --epochs 20 `
  --batch-size 128 `
  --d-model 128 `
  --bottleneck-dim 64 `
  --lr 0.001 `
  --weight-decay 0.0001 `
  --max-length 256 `
  --out-dir noetic-compass-scaffold/noetic-compass/cas-native/training/runs/structured-token-20epoch-local-YYYYMMDD
```

Interpretation gate: if the structured-token runner beats 48.7%, the CAS-native token substrate is already carrying useful signal beyond hashing. If it lands far below 48.7%, the runner is not the bottleneck; lexicon scale and learned CAS-axis tagger coverage are.

---

## 0.2 Session 41 update - structured-token run beat hash baseline

The interpretation gate was cleared.

Run: `cas-native/training/runs/structured-token-20epoch-gpu-20260502-001907/`

Result:

- Hash baseline: `487/1000 = 48.7%`
- Structured-token run: `853/1000 = 85.3%`
- Delta: `+36.6pp`
- Vocab size: `290`
- Train records after overlap filtering: `17,974`
- Held-out eval: `1,000`

Per-bucket exact:

- `v74_baseline`: `194/194 = 100.0%`
- `v75_register`: `217/262 = 82.8%`
- `v76_production`: `72/104 = 69.2%`
- `v77_rule_four`: `46/106 = 43.4%`
- `v77_omega`: `218/218 = 100.0%`
- `meta_logic`: `106/116 = 91.4%`

Interpretation: the CAS-native tokenizer/structured-token substrate is empirically useful, not decorative. It beats the deterministic hash feature baseline by a large margin on the same leakage-fixed held-out eval. The remaining weakness is not global CAS-axis recovery; most heads are above 94%. The main failure mode is `v77_rule_four` expression-family / transition-kind classification.

Engineering note: the first GPU attempt exposed a CPU-bound startup path. Commit `2366628` fixed it by caching token sequences once, loading the seed lexicon once per corpus pass, and logging tokenization progress every 1,000 records. GPU utilization is still low because tensor batches are built in Python per batch; next engineering step is a prebuilt tensor-cache dataset.

---

## 1. Why this exists — the pivot in one paragraph

On 2026-04-30 a frozen-CAS-CLM-as-encoder run on an A6000 produced ~0.3-0.7% all-heads-exact through 11 epochs over 19,454 Level 3 records. The hash-feature baseline reached 48.7%. The frozen pretrained CAS-CLM backbone underperformed primitive token-hash features by ~100x. Diagnosed as **modality mismatch**: the CAS-CLM was trained as a causal LM on CAS expressions, so its hidden states are optimized for next-CAS-token prediction, not for encoding natural-language prompts. Its tokenizer (HybridCASTokenizer, vocab=698) collapses NL prompts to mostly `[UNK]`. CAS-CLM is the right tool for the OUTPUT/decoding side of the pipeline; it is the wrong tool for INPUT encoding.

The user-locked architecture pivot is: **a natural-language front door INTO the CAS engine** with CAS as the reasoning spine. NL is the translation surface on both ends; CAS is causally upstream of every utterance. The user explicitly rejected the alternative ("LLM with CAS glued on" / "CAS as wrapper") and named "us or nothing" — no external pretrained LMs in the stack.

This pivot demanded a tokenizer that is *itself* CAS-native — that pre-decodes CAS-axis structure at the input layer rather than producing generic integer IDs. Wave 1 of that tokenizer ships in this session.

---

## 2. What got built (Wave 1 deliverables)

All under `cas-native/tokenizer/` and `cas-native/tests/tokenizer/`. Subtree clean isolation per the user's decision.

### Structured-token schema — `cas-native/tokenizer/structured_token.py`

```python
StructuredToken(
    surface_text:   str,
    surface_span:   tuple[int, int],   # (start, end) in original input
    cas_signature:  CASSignature,      # 10/4/7/4 floats + role tags
    confidence:     float,             # [0.0, 1.0]
    source:         TokenSource,       # LEXICON / LEARNED / CAS_NOTATION / FALLBACK
    vocab_id:       int | None,        # filled later by embedding adapter
)
CASSignature(
    noetic:    tuple[float, ...],     # length 10, ^0..^9, range [-1, +1]
    domain:    tuple[float, ...],     # length 4,  P/C/E/O
    drive:     tuple[float, ...],     # length 7,  F1..F7  (negatives = depletion)
    register:  tuple[float, ...],     # length 4,  T/A/f/E
    role_tags: tuple[str, ...],       # e.g., "self_reference", "confidence_hedge"
)
```

Schema-versioned (`structured_token.v1`). `to_dict` / `from_dict` round-trip. `validate() -> list[str]` for non-throwing self-checks (matching the `runtime_frame.py` convention).

### Pre-tokenizer — `cas-native/tokenizer/pretokenizer.py`

Deterministic span-tracking segmentation over input. Emits `PretokenSpan` with kinds `word` / `punct` / `whitespace` / `cas_candidate`. Apostrophes preserved inside words ("can't", "won't"). CAS-symbol-leading characters (`^`, `|`, `_`, `Ω`, `Θ`, `Φ`, `→`, `←`, `↔`, `⟨`, `⟩`) are flagged as `cas_candidate` for the recognizer to validate. Round-trip lossless: `reassemble(pretokenize(text)) == text`.

### CAS-notation recognizer — `cas-native/tokenizer/cas_notation.py`

CAS v7.7 notation coverage:

- Full compound state `^n^D_{F_k}|R`
- Partial compounds (`^n^D_{F_k}`, `^n^D|R`, `^n_{F_k}`, `^n|R`, `^n^D`)
- Bare Noetic (`^n`), Domain (`^D`), Drive (`F_k` / `Fk`), Register (`|R`)
- Register-set spec `|⟨R1,R2,...⟩` (v7.7)
- Production target `Ω_label`
- Recipe opener `Θ(`
- Arrows (`→`, `←`, `↔`, `->`, `<-`, `<->`)
- Set relations (`∈ ∉ ⊂ ⊆ ⊃ ⊇ ∪ ∩ ∖ ∅`)

Longest-match-first. Each match produces a `CASSignature` with `cas_literal` role tag; compound matches add `compound_state`. CAS-notation tokens always carry confidence 1.0.

### CAS lexicon — `cas-native/tokenizer/lexicon/`

`schema.py` — `LexiconEntry` + `CASLexicon`. Single-word index is O(1) hash lookup; multi-word index is sorted longest-first with context-required / context-blocked regex predicates. Context window is 32 chars before/after the candidate; a `␟` (unit-separator) sits between before and after, so context regex can anchor to either side via `[^␟]*␟` (before) or `␟[^]*` (after).

`build_seed.py` — generator script that produces `seed_lexicon.jsonl`. Source of truth in typed Python. Re-run to regenerate. Hand-edits to JSONL should be backported.

`seed_lexicon.jsonl` — **98 entries** covering:

- All 10 Noetics with canonical-colloquialism anchors
- All 4 Domains, all 7 Drives, all 4 Registers
- 3 demographic register-variant pairs (academic / working_class / child) all collapsing onto identical CAS axes (the cross-register-robustness anchor)
- Confidence hedges with context-required disambiguation
- Demonstratives, referent pronouns, reference markers
- Operational-domain markers

Entries are anti-drift compliant per CLAUDE.md: `^3` Negative is visceral (audit/scrutinize go to `^6`); `^8` Above/Cause is associative triggering (deductive reasoning is `^6` + `^9` compound, not `^8`); `^4` Vibration prefers etymological cognates (`struck a chord`).

### Assembler — `cas-native/tokenizer/assembler.py`

End-to-end entry point: `tokenize(text) -> list[StructuredToken]`. Resolution order at each cursor position:

1. CAS-notation literal (anchored at cursor; longest match)
2. Multi-word lexicon match (greedy longest-first, with context-required check)
3. Single-word lexicon lookup
4. Fallback (neutral signature, confidence 0.0, surface preserved for audit)

`tokenize_with_stats()` also returns a `TokenizeStats` summary with provenance breakdown — useful for audit and demographic-robustness eval.

### Tests — `cas-native/tests/tokenizer/`

64 passing tests across 5 files. Anti-drift properties asserted as load-bearing checks:

- `test_seed_lexicon_anti_drift_visceral_negatives` — `audit` and `scrutinize` MUST NOT fire `^3`.
- `test_seed_lexicon_anti_drift_associative_triggers` — `reminds me of` and `triggered` fire `^8`.
- `test_seed_lexicon_etymological_cognate_for_vibration` — `struck a chord` fires `^4` ≥ 0.9.
- `test_demographic_register_variants_share_axis` — `exhausted` / `hella tired` / `super sleepy` / `profoundly fatigued` all depress F3.
- `test_tokenize_visceral_aversion_anti_drift` — `can't stomach` fires `^3` and NOT `^6`.
- `test_tokenize_analytical_critique_anti_drift` — `audit` fires `^6` and NOT `^3`.

These tests are the durable contract. If a future agent breaks them, the lexicon/recognizer is wrong, not the tests.

---

## 3. Role in the stack — where the tokenizer fits

The Noetic Compass / CAS-Native AI stack now has the following layered architecture, with the tokenizer occupying the previously-empty input layer:

```
USER NATURAL-LANGUAGE INPUT
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  [NEW] CAS-NATIVE TOKENIZER  (cas-native/tokenizer/)             │
│  - pretokenizer.py    span-tracking segmentation                 │
│  - cas_notation.py    v7.7 CAS-literal recognizer (conf=1.0)     │
│  - lexicon/           hand-built signature dictionary (98 seed)  │
│  - assembler.py       tokenize(text) → list[StructuredToken]     │
│                                                                  │
│  Output: structured tokens, each with surface_span provenance,   │
│          explicit CAS-axis affinity vectors, source flag.        │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAS-NATIVE ENCODER  (cas-native/model/structured_prediction.py) │
│  - Embedding layer consumes structured tokens                    │
│    (vocab embedding + CAS-signature features, gated fusion)      │
│  - Transformer body (architecture per Wave 2 spec)               │
│  - StructuredPredictionHead — 12 typed axes already in place     │
│                                                                  │
│  Output: IntentIR fields predicted from CAS-pre-decoded input.   │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  INTENT-IR  (cas-native/intent/intent_ir.py)                     │
│  - typed contract: turn_type, expression_family, transition_kind │
│    noetic, domain, drive, registers, register_mode, …            │
│  Already on origin/master.                                       │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  DETERMINISTIC CAS BUILDERS                                      │
│  CASTurnRecord, CASTransition, RegisterBinding,                  │
│  ProductionTransition, DomainTransition, ProductionModifier      │
│  (cas-synthetic/schemas/cas_transformer.py — already shipped)    │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  COMPILER + ADMISSIBILITY GATES                                  │
│  api/notation/compiler.py — full v7.7 grammar + diagram exporter │
│  api/notation/turn_admissibility.py — 11 turn-type predicates    │
│  validate_compound_transition — 3-phase walk (register → prod →  │
│                                  domain)                          │
│  Already on origin/master.                                       │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  CAS RUNTIME FRAME + TURN EXECUTION                              │
│  cas-native/runtime/runtime_frame.py — 8 primitives (identity,   │
│    drive_state, salience, temporal_grain, affect, ambiguity,     │
│    feedback_history, default_state_distribution)                 │
│  cas-native/runtime/turn_execution.py — TurnExecutionRecord      │
│    binds: pre-frame, predicted intent, admissible candidates,    │
│    selected expression, compiler validation, diagram, rendered   │
│    response, post-frame, runtime_delta, transition_trace.        │
│  Already on origin/master (commits 1aa0ef4, c1eb8ec, 27ca0b5).   │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  CONVERSATIONAL RENDERER                                         │
│  Phase-1: deterministic Jinja2 templates per turn type           │
│  Phase-2: learned conversational decoder (gated on Wave 4)       │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
USER-FACING REPLY  (with full hidden CAS trace)
```

### How Wave 1 specifically benefits each downstream component

| Downstream component | Benefit from CAS tokenizer Wave 1 |
|---|---|
| **CAS encoder** | No longer has to discover from raw IDs that "drawn" implies `^2` — the tokenizer already says so. Embedding layer's job becomes: refine and combine pre-decoded structure rather than learn it from scratch. Strongly reduces sample complexity. |
| **StructuredPredictionHead** | Receives input where CAS-axis features are already explicit. Currently shape-compatible (12 typed axes); Wave 2 encoder integration plugs in directly without head changes. |
| **IntentIR resolution** | Token-level `surface_span` + `cas_signature` lets the IntentIR resolver cite specific input tokens for each predicted axis. The "user_prompt" → IntentIR mapping becomes traceable at the word/phrase level. |
| **Compiler + admissibility** | Unchanged. The compiler validates the IntentIR-derived expression; nothing about the tokenizer affects compiler inputs. The tokenizer just makes the IntentIR predictions more reliable, which means more compiler-passing transitions. |
| **RuntimeFrame** | Token-level `role_tags` (e.g., `confidence_hedge`, `demonstrative`, `embodied_marker`) feed directly into the AmbiguityState and SaliencePolicy primitives without needing a separate NL analyzer. |
| **TurnExecutionRecord** | Now has end-to-end character-level provenance: every field in `predicted_intent_ir` traces back via attention to a specific `surface_span` in the user's input. The "every meaningful reply has a hidden CAS trace" claim becomes deliverable to character precision, not just IntentIR-field precision. |
| **Diagram exporter** | The diagram can now highlight the input tokens that drove each predicted CAS structure — the audit graph extends from the rendered response all the way back to the literal characters of the user prompt. |
| **Wrap pipeline / NCCS scoring** | When CAS scores get wired into the existing 8-stage Wrap pipeline, the input-side scoring of operator activations becomes transparent: each operator's score has a token-level rationale. Reduces opacity of LLM-wrapper assessments. |

### What Wave 1 does NOT yet provide (and which wave handles it)

- **OOV coverage** — words not in the seed lexicon get fallback tokens with neutral signatures. **Wave 3** learned tagger fixes this.
- **Sarcasm / tonal inversion** — the tokenizer reports the literal CAS signature; sarcasm flips it contextually. **Wave 4** encoder-level pattern uses register-contradiction detection to handle sarcasm; the tokenizer's job is to be honest, not to be smart.
- **Demographic depth** — only 3 register variants × 1 axis (F3 vitality) seeded. **Wave 3** SDG demographic extension scales this to 7+ register variants × all axes.
- **Multilingual** — English only in Wave 1. Other languages get parallel lexicons in a future wave.
- **Encoder integration** — the embedding layer doesn't yet consume `cas_signature` features. **Wave 2** designs the integration; **Wave 4** ships it.

### Strategic value summary

The tokenizer changes the encoder's learning task from "discover CAS structure from text" to "compose pre-decoded CAS structure into IntentIR." That's a fundamentally smaller and better-conditioned problem. The frozen-CAS-CLM run failed because we asked the encoder to learn CAS structure from `[UNK]` token soup. Wave 1 ensures we never ask the encoder that question again — CAS structure is in the input by construction.

It also delivers traceability that was previously aspirational: every IntentIR field can cite specific input characters; the diagram exporter can highlight which words drove which CAS predictions; the audit trail is in the data, not bolted on. The "every reply has a hidden CAS trace" claim from `project_cas_transformer_nl_front_door_architecture.md` becomes a working property of the pipeline rather than a marketing line.

---

## 4. Where Wave 1 leaves off — exact pickup points

Repo state:

- All Wave-1 files written and tested green (64 tokenizer tests; 82 passed + 1 skipped across tokenizer/runtime/intent neighbors; 14 passed + 1 skipped across structured-prediction regressions).
- `CHANGELOG.md` Session 38 entry written.
- This handoff doc at `docs/working/cas_tokenizer_wave1_handoff.md`.
- Shared CAS-Native `tmp_path` fixture patched to avoid Windows/OneDrive `tempfile.mkdtemp(dir=...)` permission failures.
- Wave 2 design docs are present: `docs/working/cas_lexicon_scaling_methodology.md`, `docs/working/cas_tagger_architecture.md`, and `docs/working/cas_encoder_integration.md`.
- **Not yet committed in this document's source state.** If this doc appears on `origin/master`, the tokenizer bundle has landed.

To resume cold, a fresh agent should:

1. Read this doc top to bottom.
2. Read `memory/project_cas_transformer_nl_front_door_architecture.md` and `memory/project_cas_transformer_modality_mismatch_pivot.md` to understand the architectural commitment.
3. Read `cas-native/tokenizer/__init__.py` for the API surface.
4. Verify `pytest cas-native/tests/tokenizer/` is still green.
5. Pick up at Wave 2 (Section 5 below).

---

## 5. Wave 2 — design specs to dispatch in parallel

Per the user's instruction, Wave 2 runs as background specialist agents. Three independent design tasks; can run simultaneously since they're scoped to different concerns.

### Wave 2-A — Lexicon scaling methodology

**Question:** How do we scale the seed lexicon from 98 entries to 15K-30K, while preserving anti-drift discipline and demographic coverage?

**Inputs the agent should read first:**
- `cas-native/tokenizer/lexicon/build_seed.py` — current source-of-truth structure
- `cas-native/tokenizer/lexicon/seed_lexicon.jsonl` — current contents
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 6 — Colloquialism Test
- CLAUDE.md anti-drift annotations
- `cas-synthetic/data/level3_*.jsonl` — existing CAS SDG corpus, source of word-level association statistics

**Deliverable:** a written methodology + tooling spec covering:
1. Source priorities (CAS material, SDG-derived high-association words, parallel-register variants for demographic coverage).
2. Vetting protocol — Colloquialism Test + anti-drift checks at entry-construction time.
3. Scaling cadence (weekly batches? CI-gated lexicon coverage metric?).
4. Inter-rater protocol if multiple humans review entries.
5. Tooling: a `lexicon_extract.py` that mines candidate entries from CAS SDG, scores them against the existing lexicon for axis consistency, and emits diff-ready JSONL chunks.

**Output:** spec document at `docs/working/cas_lexicon_scaling_methodology.md`. No code changes from this agent — design only.

### Wave 2-B — Learned CAS-axis tagger architecture

**Question:** When the lexicon misses a word, what learned model fills in the CAS signature? Architecture, training data extraction, training/eval gates.

**Inputs the agent should read first:**
- `cas-native/tokenizer/structured_token.py` — `CASSignature` shape (10/4/7/4 floats)
- `cas-native/tokenizer/assembler.py` — current FALLBACK path that the tagger replaces
- `cas-native/tests/tokenizer/test_assembler.py::test_tokenize_unknown_words_fall_back_with_neutral_signature` — the case to fix
- `cas-native/training/train_structured_backbone.py` — backbone-agnostic harness the tagger plugs into
- `cas-synthetic/data/level3_*.jsonl` — corpus for tagger training

**Deliverable:** a design spec covering:
1. Architecture (tiny BiLSTM/conv/transformer? rough size cap, target ~5-20M params).
2. Training-data extraction from CAS SDG via word-level alignment between prompt words and target CAS axis vectors.
3. Loss formulation — per-axis MSE? per-axis cross-entropy after binning? cross-axis correlation regularization?
4. Eval gates: minimum per-axis correlation with held-out lexicon, OOV coverage rate, axis-consistency score.
5. Integration with assembler: tagger output is strict fallback (lexicon always wins).
6. Compute estimate (must run locally for inference, training goes to a pod per the device-rule memory).

**Output:** spec document at `docs/working/cas_tagger_architecture.md`. No code changes from this agent.

### Wave 2-C — Encoder integration design

**Question:** How does the embedding layer consume `StructuredToken` instead of raw `int` IDs? Backward-compat with the existing harness?

**Inputs the agent should read first:**
- `cas-native/model/structured_prediction.py` — current head (preserved unchanged)
- `cas-native/training/train_structured_backbone.py` — backbone-agnostic harness
- `cas-native/training/structured_backbone_adapter.py` — current backbone-input shape
- `cas-native/tokenizer/structured_token.py` — `StructuredToken` schema
- `cas-native/tokenizer/assembler.py` — `tokenize()` API

**Deliverable:** a design spec covering:
1. Embedding-layer redesign — gated fusion vs concat vs dual-stream (vocab embedding + CAS-signature MLP, joined how?).
2. Vocabulary construction — how does `vocab_id` get assigned? Codex decision after Wave 2 review: strict word/phrase IDs with a 64K cap and char-CNN fallback for OOV surface tails. BPE-on-our-corpus is contingency only.
3. Backward-compat path — can the existing harness run with structured tokens via an adapter without rewriting `train_structured_backbone.py`?
4. Position-embedding handling when tokens have variable surface widths.
5. `vocab_id is None` path — what does the embedding layer do for tokens without a vocab assignment (multi-word lexicon matches especially).
6. Migration plan from "tokens-as-int-IDs" to "tokens-as-StructuredToken" without breaking the M2 baseline reproducibility.

**Output:** spec document at `docs/working/cas_encoder_integration.md`. No code changes from this agent.

---

## 6. Resolved decisions and remaining questions for Wave 2+

1. **Vocabulary algorithm.** Resolved by Codex review: use strict word/phrase IDs plus char-CNN fallback first. BPE-on-our-corpus remains a contingency only if the selected path fails Stage 0.
2. **Tagger LM.** The Wave 2-B tagger trains on CAS SDG. Is a 5-20M-param tagger acceptable as part of the "us" stack? (It's not pretrained on external text; it's trained on our SDG.) The user's stack-purity rule is "no other LMs in our stack" — does that include task-specific small classifiers we train ourselves? My read: yes, ours is fine. Confirm.
3. **Demographic depth — Wave 3 SDG extension scope.** Three registers (academic / working_class / child) seeded as a smoke test. Production scale needs more (regional dialects, professional jargon registers, child age bands, cross-cultural English variants). What's the depth target? (Affects Wave 3 corpus size.)
4. **Commit note.** This document was authored before the final commit. If present on `origin/master`, the Wave 1 tokenizer bundle has landed.

---

## 7. Memory and references

Memory files written or updated this session:

- `memory/project_cas_transformer_nl_front_door_architecture.md` — locked architecture
- `memory/project_cas_transformer_modality_mismatch_pivot.md` — pivot diagnosis
- `memory/feedback_gpu_vs_cpu_for_real_training_runs.md` — device sizing rule (carries forward)
- `memory/feedback_real_metric_is_samples.md` — sample-level eval discipline (carries forward)
- `memory/feedback_cas_native_metrics_priority.md` — gradient-of-capability eval (carries forward)

CLAUDE.md anchors:

- The 10 Noetic definitions are canonical and verbatim. Tokenizer entries use authoritative verbs ("attracted toward," "adverse to," "resonates with," "triggers," "brought to Mind").
- Anti-drift annotations (^3 visceral, ^8 associative, ^4 etymological cognate) are load-bearing in the seed lexicon and asserted as test properties.
- 4 Domains, 7 Drives, 4 Registers, all axis cardinalities locked to the v7.7 ontology.

External docs:

- `cas-native/training/runs/v2-first-full-20260428-220635/` — frozen-backbone failure artifacts (preserved as the negative baseline).
- M2 baseline numbers: hash features 487/1000 (48.7%) at epoch 19; semantic reranker 105/1000 (10.5%) leak-fixed.

---

## 8. Why this is worth the effort (one-paragraph executive summary)

The frozen-CAS-CLM-as-encoder run wasted 5-6 hours of compute and produced a clean negative result: a CAS-trained CLM is not a NL encoder. The pivot direction the user committed to is "NL front door INTO the CAS engine." That commitment requires either (a) using an external NL-pretrained encoder ("us or nothing" rules this out) or (b) building an original CAS-native input layer. (b) is what Wave 1 ships. The tokenizer is the cheapest, most leverage-yielding piece of (b) because it converts the encoder's job from "learn CAS structure from text" to "compose pre-decoded CAS structure into IntentIR" — a fundamentally easier problem. Plus it makes the audit trail traceable to character precision, which is the platform's positioning advantage. Wave 1 is small (~1500 LOC + 98 lexicon entries) but it's the linchpin: every subsequent wave depends on the structured-token contract, the lexicon discipline, and the surface-span provenance laid down here.
