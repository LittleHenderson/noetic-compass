# CAS-Native Encoder Integration — Wave 2-C Design

**Status:** Design only. No code written. No existing files modified.
**Author:** Wave 2-C background agent, May 1, 2026.
**Audience:** Engineer or agent picking up Wave 4 implementation. Self-contained.
**Inputs assumed read:** `cas_tokenizer_wave1_handoff.md`; `cas-native/tokenizer/structured_token.py`; `cas-native/tokenizer/assembler.py`; `cas-native/model/structured_prediction.py`; `cas-native/training/train_structured_backbone.py`; `cas-native/training/structured_backbone_adapter.py`; `cas-native/training/tokenizer.py`; `memory/project_cas_transformer_modality_mismatch_pivot.md`; `memory/project_cas_transformer_nl_front_door_architecture.md`.

---

## 0. Scope and architectural commitments

The encoder is the input-side substrate immediately downstream of `tokenize(text) -> list[StructuredToken]` and immediately upstream of the existing `StructuredPredictionHead`. Wave 1 already pre-decodes CAS structure at the token level: every `StructuredToken` carries explicit `(noetic, domain, drive, register)` axis floats plus a `role_tags` annotation. The encoder's job becomes **compose pre-decoded structure into IntentIR**, not "discover CAS structure from raw IDs."

Architectural commitments — load-bearing, do not relax:

- "Us or nothing." No external pretrained encoders (DistilBERT / MiniLM / BGE / Qwen / etc.). The encoder is from scratch, trained on our SDG corpus.
- The existing `HybridCASTokenizer` (`cas-native/training/tokenizer.py`, vocab=698) is preserved on the **output** side (CAS-CLM decoding, structured emergence). It is NOT used on the input side. Input is `StructuredToken` streams from the Wave-1 assembler.
- The CAS-CLM checkpoint is empirically falsified as an input encoder (~100x under hash baseline, modality mismatch). Do not propose it.
- `StructuredPredictionHead` (12 typed axes) is preserved unchanged. The encoder must produce a tensor compatible with the head's `(B, seq_len, d_model)` or `(B, d_model)` interface.
- The harness `train_structured_backbone.py` is preserved unchanged. The new encoder plugs in through the existing backbone-class interface.

---

## 1. Embedding-layer design

The encoder receives `list[StructuredToken]`. Each token carries: `surface_text`, `surface_span`, `cas_signature` (10 + 4 + 7 + 4 = 25 floats, plus role_tags), `confidence`, `source`, `vocab_id`. Three candidate designs:

### 1a. GATED FUSION (recommended)

```
e_v   = VocabEmbedding(vocab_id)              shape (d_model,)
e_c   = SignatureMLP(cas_signature_vector)    shape (d_model,)
α     = sigmoid(W_g · [e_v ; e_c] + b_g)      shape (d_model,) elementwise gate
e_out = α ⊙ e_v + (1 - α) ⊙ e_c
```

**Recommended dimensions:**
- `d_model = 256` for the warm-up stage, `d_model = 384` for full SDG. Keeps total params under ~30M for a 4-6 layer transformer (well within "us-or-nothing" small-model discipline).
- `signature_input_dim = 25` (10 noetic + 4 domain + 7 drive + 4 register), plus an optional `role_tag_embed_dim = 16` summed-pooled over `role_tags`.
- `SignatureMLP`: Linear(25 + 16 → 128) → GELU → LayerNorm → Linear(128 → d_model). Two layers, no residual; output L2-norm-bounded into the same scale as the vocab embedding (use LayerNorm at output).
- Gate `W_g`: Linear(2·d_model → d_model). Elementwise gate (per-feature), not scalar. Reasoning: some features in `e_v` (surface-form information) should win for distinguishing homonyms; some features in `e_c` (CAS-axis information) should win for unfamiliar surfaces. Per-feature gate lets the encoder learn that distinction.
- Initialization: bias `b_g` initialized to logit(0.5) so α ≈ 0.5 at start (neutral fusion); `SignatureMLP` final layer initialized small (≤0.01 std) so vocab embedding dominates initially and the encoder learns to lean on signature only when it helps.

**Auxiliary inputs added to the fusion as small additive terms:**
- `confidence_embed`: a 1-d feature (the token's `confidence` float) projected to d_model via a small MLP. Tells the encoder whether to trust `e_c`.
- `source_embed`: 4-way categorical embedding for `TokenSource` (LEXICON / LEARNED / CAS_NOTATION / FALLBACK). LEXICON and CAS_NOTATION should get the encoder's trust; FALLBACK should not.

Final per-token vector: `e_out + confidence_embed + source_embed`, then position-add (Section 3), then transformer body.

### 1b. CONCAT (rejected as primary)

`[e_v ; e_c]` concatenated, projected via Linear(2·d_model → d_model). Fewer params than dual-stream, but loses the gating dynamic — the encoder can't learn to ignore noisy/neutral signatures on FALLBACK tokens. Forces a single fixed mixing.

### 1c. DUAL-STREAM (rejected as primary)

Separate vocab and signature streams attended together via cross-attention before the transformer body. Richer; ~2-3× more parameters; harder to debug. Worth revisiting in Wave 5+ if gated fusion saturates short of target.

### Why gated fusion wins

- Signature reliability is heterogeneous: CAS_NOTATION tokens carry confidence 1.0 with hard signal; LEXICON tokens carry 0.7-1.0; FALLBACK carries 0.0 (neutral signature, no information). A learned per-feature gate lets the encoder selectively attend to `e_c` only on tokens where it has signal.
- The OOV path (Section 2) means many tokens will have a vocab_id but a neutral signature. The gate will learn α → 1 there (vocab dominates).
- The lexicon-hit path means high-quality multi-word tokens will have a strong, hand-crafted signature but no vocab_id (or a synthetic one — see Section 2). The gate will learn α → 0 there (signature dominates).
- Backward-compatible with concat as a degenerate case (set α to a learned constant scalar).

---

## 2. Vocabulary construction

Each StructuredToken needs a `vocab_id`. The current `vocab_id: int | None` field on the schema means the embedding adapter, not the tokenizer, owns vocabulary assignment. Codex review after Wave 2 locked the first implementation path as **strict word/phrase IDs plus char-CNN fallback**. BPE-on-our-corpus remains a contingency if the selected path fails the Stage-0 gate, not the default.

### 2.1 Stable assignment rules (independent of algorithm)

Apply uniformly across algorithms (a)-(d):

- **Reserved IDs (0-7):** PAD, BOS, EOS, UNK, MASK, CAS_LITERAL, LEXICON_HIT, FALLBACK_NEUTRAL. PAD = 0 by convention.
- **CAS_NOTATION tokens:** assign vocab_ids per-symbol class. Each compound state pattern (`^n^D_{F_k}|R`), each bare Noetic (`^0`..`^9`), each domain (`^P`,`^C`,`^E`,`^O`), each drive (`F1`..`F7`), each register (`|T`,`|A`,`|f`,`|E`), each set relation (`∈`, `∉`, `⊂`, `⊆`, `⊃`, `⊇`, `∪`, `∩`, `∖`, `∅`), each arrow (`→`,`←`,`↔`,`->`,`<-`,`<->`), each Ω/Θ/Φ symbol — distinct stable ID. Total CAS_NOTATION vocab ≈ 200-400 IDs depending on compound coverage. These IDs are allocated first, deterministically, so the CAS-notation vocabulary block is reproducible across runs.
- **Multi-word lexicon entries:** single vocab_id for the full multi-word surface (e.g., `"can't stomach"` → one ID, not three). Reasoning: the StructuredToken already encodes the multi-word phrase as one unit; the signature is a hand-crafted property of the phrase as a whole; decomposing for vocab purposes would discard that. ~98 seed multi-word IDs at Wave 1; scales to ~5K-10K at Wave 3 lexicon scale.
- **Single-word lexicon entries:** stable vocab_id per surface, lowercased. Already covered by lexicon entries; allocated as a contiguous block after the multi-word block.
- **FALLBACK tokens:** vocab_id assignment follows the selected strict word/phrase-ID path. Known surfaces get stable IDs; truncated/OOV tail surfaces use char-CNN fallback.

### 2.2 OOV algorithm options (DECISION LOCKED)

The selected path is (a): strict word/phrase IDs with char-CNN tail. The other options remain documented as contingencies, but Wave 4 implementation should not start with BPE.

#### (a) Strict word-level + phrase IDs with char-CNN tail (SELECTED)

Every distinct surface in the training corpus gets its own vocab_id. Vocabulary grows with corpus.

- **Pros:** Maximum fidelity. No subword artifacts. Fully ours.
- **Cons:** Vocabulary explosion. Level 3 SDG at 19,454 records likely yields 30-50K unique surfaces; production demographic-augmented SDG (Wave 3) likely 100-200K. At Wave 4 demographic + adversarial scale, possibly 300K+. Embedding table dominates parameter count.
- **OOV at inference:** any surface not seen in training is `[UNK]`. Demographic robustness suffers for unseen registers and dialects.
- **Implementation decision:** cap vocabulary at 64K, frequency-truncate the tail; tail surfaces use character-CNN augmentation rather than collapsing to informationless `[UNK]` whenever surface text is available (see Section 4).

#### (b) BPE algorithm with vocabulary trained on OUR corpus

The Byte-Pair Encoding *algorithm* is public-domain (Sennrich et al. 2015, Gage 1994). The trained vocabulary is ours (trained on our SDG, not loaded from external sources).

- **Pros:** Compact vocabulary (16K-32K typical). Strong OOV coverage by subword composition. Standard, well-understood.
- **Cons:** Subword splits may break lexicon-aligned phrases. **Critical interaction with the lexicon:** if "stomach" gets split as `stom@@ ach`, the `"can't stomach"` multi-word lexicon hit is undermined when `vocab_id` for the surface text doesn't exist as a single ID. Mitigation: protect lexicon surfaces as **never-split atomic tokens** in the BPE merger; train BPE only over FALLBACK regions of the corpus.
- **OOV at inference:** subword fallback. Very robust.
- **Recommendation if picked:** train BPE only on FALLBACK token surfaces (skip CAS_NOTATION and LEXICON), with lexicon surfaces pinned as protected atoms. Vocabulary size 16K. Algorithm is ours-the-public-domain-1994-paper, vocabulary file is hand-trained on our data.
- **"Us or nothing" check:** algorithm ≠ pretrained model. The BPE algorithm is a deterministic merge procedure, not a learned artifact; using it does not import external knowledge. The trained vocabulary file is a corpus statistic, no different from a frequency table. This passes the purity rule but the user must confirm.

#### (c) Character-level

No word vocabulary. A character-CNN runs over the surface text of each token and produces the per-token embedding (replacing or augmenting the vocab embedding).

- **Pros:** Zero OOV. Fully ours. Robust to typos, slang, and dialect.
- **Cons:** Slower (CNN per token). Embedding signal is purely surface-orthographic — no prior word-identity inductive bias. May require more training data to reach the same accuracy as (a) or (b).
- **Recommendation if picked:** per-token char-CNN with kernel sizes 2/3/4/5, 64 filters each, max-pooled, projected to d_model. Char vocab ≈ 256 (UTF-8 bytes) plus a few control IDs.
- **Risk:** sample complexity. Beating the 48.7% hash baseline with character-only features is harder than with word features.

#### (d) CAS-Native rule-based segmentation

Custom segmenter — morphological / syllabic rules we author ourselves. Vocab is the segmentation atoms.

- **Pros:** Maximally ours. Linguistically interpretable. Aligns with the Wave 1 lexicon discipline (hand-built, anti-drift-checked, Colloquialism-Test-validated). Lexical boundaries respect morphology.
- **Cons:** Highest engineering cost. Months of rule-writing for English; multilingual extension is multiplicative effort. Risk of brittleness on slang and creative usage. May still need a residual character-CNN for rule-misses.
- **Recommendation if picked:** hybrid — rule-based morphological splitter for productive prefixes/suffixes (`un-`, `-ing`, `-ed`, `-tion`, etc.), with a frequency-pruned word vocab as the atomic layer. Segmentation rules versioned and tested like the lexicon.

### 2.3 Codex decision after Wave 2 review

**Codex-selected path: strict word-level / phrase-level vocabulary with char-CNN tail.** This supersedes the original Wave 2-C default below. BPE-on-our-corpus remains documented as a contingency, but Wave 4 implementation should start with exact word/phrase IDs for traceability and use char-CNN for OOV surface tails.

**Default-recommend (b) BPE-on-our-corpus** if the user accepts that "BPE algorithm public-domain, vocabulary trained on our data" passes the "us or nothing" rule. It's the lowest engineering cost path with strongest OOV coverage and acceptable vocabulary size. Lexicon surfaces are pinned as atomic — the BPE trainer never breaks `"can't stomach"`.

**Fallback-recommend (a) strict word-level with char-CNN tail** if the user reads "us or nothing" strictly enough that even the BPE algorithm is excluded. Acceptable performance ceiling is lower; vocabulary management is more painful at scale; but every byte is unambiguously ours.

**Do not recommend (c) char-only or (d) custom rules as primary.** (c) sacrifices too much sample efficiency; (d) is multi-month effort that gates the entire Wave 2-C track. Both are viable as augmentation layers atop (a) or (b).

Original Wave 2-C decision blocker is now resolved by Codex review: start with strict word/phrase IDs plus char-CNN tail.

---

## 3. Position-embedding handling

`StructuredToken.surface_span` is `(start, end)` over the original input. Multi-word lexicon hits cover wide spans (`"can't stomach"` ≈ 13 chars); punctuation covers 1 char. Two designs:

### 3a. TOKEN-INDEX positions (recommended)

Position k = the k-th token in the stream, regardless of surface width. Standard sinusoidal or learned positional embedding. d_pos = d_model.

- **Pros:** Standard. Compatible with rotary / sinusoidal / learned schemes. Easier debugging. Lower variance in position usage.
- **Cons:** Loses information about surface gaps (skipped whitespace, punctuation skipped at `include_whitespace=False`).

### 3b. CHARACTER-OFFSET positions

Position = `surface_span[0]` (start char offset), normalized by max input length.

- **Pros:** Preserves surface-level structure exactly. Useful if downstream attention should weight tokens by physical proximity in the input.
- **Cons:** Sparse position usage (long jumps between tokens). Standard sinusoidal embeddings handle this poorly. Requires explicit continuous-position scheme (Fourier features over normalized offset).

### Recommendation

Use **token-index positions** as the primary positional signal. ADD a small **surface-span feature** as auxiliary input — `[start/max_len, (end-start)/max_len]` projected through Linear(2 → 16) → projected to d_model and added as a residual. This gives the encoder both standard sequential structure (token-index, well-understood) and a hint about surface-physical layout (span feature, useful for diagnostics and attention provenance) without committing to character-offset as the primary scheme.

---

## 4. `vocab_id is None` handling

Multi-word lexicon hits and FALLBACK tokens may have `vocab_id = None` until vocabulary is built. Handle in two phases:

### 4.1 Vocabulary build time (preferred)

A `build_vocabulary(corpus)` step runs once before training. It enumerates all observed `StructuredToken` surfaces (single-word, multi-word, CAS-notation literals) across the corpus and force-assigns a stable `vocab_id` to each. After this step, a separate `assign_vocab_ids(tokens, vocab)` pass mutates each token's `vocab_id`. Tokens with no match become `UNK` (vocab_id = 3).

This is the **strongly preferred** path: vocabulary is deterministic, reproducible, and a hard contract. Run vocabulary-build as a one-off offline job; serialize to `vocabulary.json`; load at training and inference.

### 4.2 Inference-time fallback (safety net)

If a token still has `vocab_id is None` at embedding time (shouldn't happen post-build, but guard anyway):

- **lookup-or-zero** with a mask flag: vocab embedding gets a learned zero vector; the encoder's `source_embed` flags this as FALLBACK_NEUTRAL; the gated fusion's α drives toward 0 (signature-only). Allows the encoder to still produce a per-token vector using only the signature features (which are zero for FALLBACK, but non-zero for LEXICON multi-word hits without vocab assignment).
- **char-CNN fallback** (selected): for FALLBACK tokens with surface text, run a small char-CNN over the surface and use the CNN output as `e_v`. This is the selected rescue path for OOV under the strict word/phrase-ID vocabulary.

Recommendation: use lookup-or-zero only when surface text is absent or intentionally masked. Use char-CNN fallback as the selected OOV surface path for Wave 4.

---

## 5. Backward-compatibility path

Goal: existing `train_structured_backbone.py` runs with structured tokens via an adapter, **without** rewriting the harness.

### 5.1 Current harness contract

`train_structured_backbone.py`:
- Imports `CASBackboneStructuredPredictor` from `structured_backbone_adapter.py`.
- Calls `records_to_backbone_batch(batch_records, tokenizer, max_length, device)` to get `BackboneBatch(input_ids, attention_mask)`.
- Calls `model(batch.input_ids, attention_mask=batch.attention_mask)` and expects a dict containing `pooled_hidden_state` and the StructuredPredictionHead logits.

### 5.2 Minimum-diff design

Add — do not modify — two new modules:

**`cas-native/model/structured_token_backbone.py`** (new)
Defines `StructuredTokenBackbone(nn.Module)`:
- Constructor takes `(d_model, n_layers, n_heads, vocab_size, max_seq_len, signature_dim, dropout)`.
- `forward(input_ids, attention_mask, signature_features, confidence_features, source_features) -> dict[str, Tensor]`. Returns `{"hidden_states": (B, L, d), "pooled_hidden_state": (B, d), "attention_mask": (B, L)}`.
- Internally: gated-fusion embedding (Section 1) → positional add (Section 3) → standard transformer encoder (4-6 layers) → mean-pool with attention mask.
- `pooled_hidden_state` is shape-compatible with the existing `StructuredPredictionHead._pool` and forward.

**`cas-native/training/structured_token_adapter.py`** (new, sibling to `structured_backbone_adapter.py`)
Defines:
- `StructuredTokenBatch(input_ids, attention_mask, signature, confidence, source)` — extension of `BackboneBatch`.
- `records_to_structured_token_batch(records, vocab, max_length, device) -> StructuredTokenBatch` — runs `tokenize()` from Wave 1, runs `assign_vocab_ids()` from Section 4, packs `signature` as `(B, L, 25)` float tensor, packs `confidence` as `(B, L)`, packs `source` as `(B, L)` int.
- `CASStructuredTokenPredictor(nn.Module)` — composes `StructuredTokenBackbone` with `StructuredPredictionHead`. Mirrors `CASBackboneStructuredPredictor`'s interface.

**Harness modification:** add a CLI flag `--encoder-mode {backbone, structured_token}` to `train_structured_backbone.py`. When `structured_token` is selected, swap:
- `records_to_backbone_batch` → `records_to_structured_token_batch`
- `CASBackboneStructuredPredictor` → `CASStructuredTokenPredictor`
- `tokenizer = HybridCASTokenizer` → `vocab = StructuredTokenVocabulary.load()`

The harness's training loop, eval loop, manifest writing, leak-fix overlap filter, and progress logging all stay identical. Only the batch construction and model class change. Total harness diff: ~30 lines, additive only. The existing `--backbone-checkpoint` / `--allow-eval-overlap` / `--out-dir` flags continue to work for the legacy path.

This design preserves M2 baseline reproducibility — anyone can rerun `--encoder-mode backbone` with the old flags to reproduce hash baselines, and `--encoder-mode structured_token` for the new path.

---

## 6. Migration from hash baseline / frozen-CAS-CLM reproducibility

The M2 baselines are: hash features 487/1000 (48.7%) at epoch 19; semantic reranker 105/1000 (10.5%) leak-fixed; frozen CAS-CLM ~3-7/1000 (0.3-0.7%) over 11 epochs.

### 6.1 Same eval split

The new encoder is evaluated on the **same** held-out 1K eval at `cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000.jsonl` so comparisons are apples-to-apples. No re-splitting. The harness's `--eval-input` flag points at the same file. The existing `_is_heldout_eval_path` and `filter_eval_overlapping_records` discipline (already in `train_structured_backbone.py` / `train_structured_prediction.py`) carries over without change.

### 6.2 Reproducibility of prior baselines

The `--encoder-mode backbone` legacy path keeps existing baseline reproducibility. Anyone can rerun with the old flags and reproduce the M2 numbers.

### 6.3 Comparison metrics

The encoder reports the same metrics: `all_heads_exact_rate`, `per_head_acc` for each of 12 axes, `by_bucket` breakdown, sample-level `samples.jsonl`. Per the user's "real metric is samples" memory, the headline number is `all_heads_exact_rate`, not internal losses.

---

## 7. Eval gates

The encoder must clear these before declaring success:

| Gate | Threshold | Source / rationale |
|---|---|---|
| `all_heads_exact_rate` (overall) | **> 48.7%** (must beat hash baseline) | M2 hash baseline. Below this is empirically falsified per the same logic that retired the frozen CAS-CLM. |
| `all_heads_exact_rate` (per-bucket worst floor) | **≥ 25%** | Worst-bucket floor. Reflects the gradient-of-capability memory: complex buckets (omega, meta_logic, production) may lag, but no bucket should be near-random. |
| Paraphrase robustness (eval set 2) | **≥ 0.85 × overall rate** | Wave 4 paraphrase eval. Same intent paraphrased N ways should preserve at least 85% of the prediction stability of the canonical phrasing. |
| Demographic-robustness (Wave 3) | **≥ 0.80 × overall rate** | Cross-register evaluation: academic / working_class / child / regional variants should all map onto the same underlying CAS axes. Same source intent across registers should preserve at least 80% prediction agreement. |
| Leak-discipline | **No train/eval overlap** | Already enforced by `filter_eval_overlapping_records`; assert overlap_report.removed = 0 after filter. |
| Sample-level `top1` and `top5` | top1 ≥ 50%, top5 ≥ 75% | Per `feedback_real_metric_is_samples.md`. Sample-level outcomes are the only "real" metric. |

If any gate fails, do not declare success. Diagnose failure mode (Section 9) before adding parameters.

---

## 8. Training stages

Per the device-sizing memory, any run with > 1K steps through a real transformer goes to a RunPod GPU, not local CPU. Stage A is the only local-CPU stage.

### Stage A — small-corpus warm-up (local CPU)

- Slice: 500 records from Level 3 train set. 50 records eval (held out from same slice).
- d_model = 128, n_layers = 2, n_heads = 4, max_seq_len = 64. Total params < 5M.
- Epochs: 5. Batch size: 8. LR: 3e-4.
- Goal: validate gradient flow end-to-end (tokenize → embed → encode → head → loss → backward). Numbers irrelevant; we want non-zero gradients on every parameter and convergence to non-trivial accuracy on the tiny slice (memorization expected). Wall-clock target: < 30 minutes on CPU.
- **Falsification:** if Stage A doesn't memorize 500 records to ≥ 90% all-heads-exact, the design has a wiring bug. Stop and fix before Stage B.

### Stage B — full SDG training (cloud GPU)

- Slice: full 19,454 Level 3 train set (leak-filtered against 1K eval).
- d_model = 256, n_layers = 4, n_heads = 8, max_seq_len = 128. ~15-20M params.
- Epochs: 20. Batch size: 64. LR: 5e-4 with cosine decay. AdamW, weight_decay = 0.01. Warmup 1000 steps.
- Wall-clock estimate: A6000, ~3-4 hours.
- Headline metric: `all_heads_exact_rate` on the held-out 1K eval. Must clear the 48.7% hash bar.

### Stage C — demographic-augmented SDG (cloud GPU, gated on Wave 3)

- Slice: Level 3 + Wave 3 demographic extension (~30-50K records, projected).
- Same model size as Stage B. Continue training from Stage B's best checkpoint.
- Goal: lift demographic-robustness eval from baseline to ≥ 0.80 × overall rate.

### Stage D — adversarial paraphrase batches (cloud GPU, gated on Wave 4)

- Slice: Level 3 + Wave 3 + Wave 4 adversarial paraphrase batches.
- Same model size, continue from Stage C.
- Goal: lift paraphrase-robustness eval to ≥ 0.85 × overall rate.

Per stage: write a manifest + samples.jsonl to `cas-native/training/runs/v3-encoder-{stage}-{date}-{hash}/`. Mirror the existing run-directory convention.

---

## 9. Risk and unknowns

The biggest unknown: **does the gated-fusion embedding give the encoder enough signal to beat the hash baseline?**

Hash features hit 48.7% by burning vocabulary positions on every token. Our gated-fusion embedding is parameterically denser but trains from scratch — no pretraining advantage, no external knowledge. The risk is that 19K records is insufficient for the encoder to learn good attention patterns over 25-d signature features plus 16-32K vocabulary, and we end up under-training.

### 9.1 Falsification experiment (cheap, definitive)

**Stage 0 — gated-fusion sanity check on a single bucket (≤ 3 GPU-hours).**

Pick the easiest Level 3 bucket (`v74_baseline` if it has the most records). Train Stage B configuration but only on that bucket's data (~3-5K records). Eval against that bucket's slice of the 1K held-out (~150-300 records).

- **Pass criteria:** all_heads_exact_rate on this single-bucket slice > 60% within 5 epochs. Per-head accuracy on `noetic`, `domain`, `register` heads > 70%.
- **Fail criteria:** stuck at random or near-hash levels after 5 epochs. Indicates the gated fusion is not extracting usable signal from the signature features.

If Stage 0 passes, proceed to Stage A → B with confidence. If Stage 0 fails, before scaling up:
1. Inspect gate values α post-training. If α ≈ 1.0 everywhere, the encoder isn't using the signature; the SignatureMLP is broken or too cold-initialized.
2. Inspect attention patterns over signature-rich vs FALLBACK tokens. If attention is uniform, position embedding may be dominating.
3. Try concat instead of gated fusion (Section 1b) as A/B; if concat works and gate doesn't, the gate parameterization is the bug.
4. Try DUAL-STREAM (Section 1c) as a last resort before declaring the embedding strategy wrong.

### 9.2 Other risks (smaller, mitigatable)

- **Vocabulary scale risk.** The selected strict word/phrase-ID path can grow large as demographic SDG expands. Mitigation: cap at 64K, keep CAS/lexicon atoms stable, frequency-truncate the tail, and use char-CNN fallback for OOV surfaces. Revisit BPE only if Stage 0 fails.
- **Lexicon coverage gap.** At 98 seed entries, FALLBACK rate on Level 3 prompts is likely 70-90% (most words are unseen). Most tokens carry neutral signatures. The encoder ends up doing most of the work on vocab embeddings alone — the gated fusion benefit is small. Mitigation: Wave 2-A (lexicon scaling) and Wave 2-B (learned tagger) close this gap; until they ship, expect the encoder to perform closer to a pure-vocab baseline.
- **Multi-word lexicon hit rate.** Multi-word entries are the highest-value signature carriers. Wave 1 has ~30 multi-word entries. Until lexicon scales, multi-word hits will be rare. Same mitigation as above.
- **Surface-span feature dominance.** If the auxiliary surface-span feature (Section 3) over-shadows the token-index position, the encoder may learn surface-physical-layout shortcuts and overfit to SDG layout artifacts. Mitigation: ablate the span feature in Stage 0; if it dominates, drop it.
- **Confidence feature noise.** FALLBACK tokens carry confidence 0.0; LEXICON 0.7-1.0; CAS_NOTATION 1.0. The confidence_embed feature could leak labels (high-confidence = high-information surface). Mitigation: ablate; verify the encoder isn't memorizing confidence patterns.

### 9.3 Decision rule on falsification

If Stage 0 fails after gate / concat / dual-stream A/B, the embedding-layer thesis is suspect. The likely correct response then is **not** to add more parameters but to revisit the input: the lexicon may be too sparse for the encoder to extract leverage, in which case Wave 2-A (lexicon scaling) becomes the gating wave for Wave 2-C, not parallel to it. This is a sequence-of-waves decision the user should make if Stage 0 fails.

---

## 10. Summary of decisions for the user

| # | Decision | Recommendation | Blocking |
|---|---|---|---|
| 1 | Embedding-layer design | **Gated fusion** with per-feature elementwise α, d_model = 256-384 | Wave 4 implementation |
| 2 | Vocabulary algorithm | **Selected: strict word/phrase IDs + char-CNN tail**; BPE-on-our-corpus is contingency only | Wave 4 implementation |
| 3 | Position embedding | **Token-index** primary + small surface-span auxiliary feature | Wave 4 implementation |
| 4 | `vocab_id is None` handling | **Vocabulary-build-time force-assignment**; lookup-or-zero as inference safety net | Wave 4 implementation |
| 5 | Harness backward-compat | **Additive `--encoder-mode structured_token` flag**, no harness rewrite | Wave 4 implementation |
| 6 | Eval split | Same held-out 1K at `cas-synthetic/data/level2_scaffold/level3_recoverable_eval_1000.jsonl` | None — locked |
| 7 | Eval gates | overall > 48.7%, worst bucket ≥ 25%, paraphrase ≥ 0.85×, demographic ≥ 0.80× | None — locked |
| 8 | Falsification experiment | Stage 0 single-bucket sanity check, ≤ 3 GPU-hours, before scaling | None — gates Stage A/B |

The original Wave-2 decision-blocker, **vocabulary algorithm (#2)**, is resolved: strict word/phrase IDs plus char-CNN tail. Everything else has a recommended default that can ship without further user input.

---

## 11. What this design does NOT cover (out of scope)

- Lexicon scaling methodology — see Wave 2-A spec.
- Learned CAS-axis tagger architecture — see Wave 2-B spec.
- Conversational renderer (output side, Phase-2) — separate track.
- Output-side CAS-CLM integration with structured emergence — separate track.
- Multilingual encoders — future wave; English-only at Wave 4.
- The 8-stage Wrap pipeline integration — separate track when encoder graduates to product surface.
- Dashboard visualization of encoder attention provenance — separate track, depends on Phase A radial display.

These tracks proceed independently of Wave 2-C and do not block encoder design.
