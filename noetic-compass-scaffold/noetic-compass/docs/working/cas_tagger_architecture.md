# Learned CAS-Axis Tagger — Architecture Specification

**Status:** Wave 2-B design spec. Design-only document; no production code.
**Author:** session 2026-05-01.
**Audience:** the agent (or human) who picks up Wave 3 implementation. Self-contained.
**Sibling specs:** `cas_lexicon_scaling_methodology.md` (2-A), `cas_encoder_integration.md` (2-C), `cas_tokenizer_wave1_handoff.md`.

---

## 1. Problem framing

### 1.1 What the tagger is

A small, CPU-resident neural model that produces a `CASSignature` (10 noetic + 4 domain + 7 drive + 4 register floats in `[-1, +1]`, plus optional role tags) for a single word given a small context window of surrounding `StructuredToken`s. It is the LEARNED branch of `assembler.tokenize()` resolution order, sitting strictly between the LEXICON branch and the FALLBACK branch.

### 1.2 When it fires

Inference-only at tokenize-time. The current `assembler.tokenize()` resolution order is:

1. CAS-notation literal — confidence 1.0, source `CAS_NOTATION`
2. Multi-word lexicon match — `LEXICON`
3. Single-word lexicon lookup — `LEXICON`
4. **Fallback** — neutral signature, confidence 0.0, source `FALLBACK`

The tagger is inserted as **step 3.5**, between single-word lexicon lookup and the neutral fallback. It fires only when the lexicon misses a word-shaped span. **Lexicon ALWAYS wins.** A token that is in the lexicon never reaches the tagger. CAS-notation literals never reach the tagger. Whitespace, punctuation, and CAS-candidate fragments that fail recognizer validation never reach the tagger.

This minimizes the tagger's failure surface: it is asked to score only words for which we have no hand-vetted answer. The lexicon is the trusted source; the tagger is the best-effort gap-filler.

### 1.3 Latency budget

Hard target: **sub-millisecond per call on local CPU**, single-threaded, with batching across a typical sentence (~5-30 OOV words). Concretely:

- Per-call (cached): O(1) dict lookup, ~1 µs.
- Per-call (cold, single word): ≤ 1.0 ms (mean), ≤ 3 ms (p99).
- Batched cold (32 words at once): ≤ 8 ms total.

Why this is feasible: a 5-15M parameter model on CPU with int8 quantization and short context (window ≤ 16 tokens) sits comfortably in this envelope. The frozen-CAS-CLM-as-encoder failure mode (50M params, 128 context, ~5-30s/batch on CPU) is the cautionary baseline; we will not repeat it.

The tagger pays its inference cost at tokenize-time, not at training-time. A user-facing assessment should not slip its `<500ms` budget because of OOV tagging — hence the cache (§6.4) and the strict size cap (§2).

---

## 2. Architecture options

Three candidates were considered. All trained from scratch on the CAS SDG corpus; all forbidden from importing external pretrained weights ("us or nothing"); all sized to fit in CPU inference at production speed.

### Option A — Char-CNN over the word + BiLSTM over context (RECOMMENDED)

**Shape:** two parallel pathways merged at a thin head.

- **Word encoder** — char-level CNN over the surface form of the OOV word. Character vocab ~80 (ASCII letters + digits + apostrophe + a few diacritic-strip fallbacks). Char embedding dim 32. Three parallel conv filters (widths 2/3/4, 64 filters each), max-pool over time. Outputs a 192-dim word vector. This pathway captures morphology — suffixes like `-ing`/`-ed`/`-tion` carry strong CAS-axis signal even for unseen lemmas.
- **Context encoder** — small BiLSTM (1 layer, hidden 128, bidirectional → 256-dim output) over a window of 8 left + 8 right `StructuredToken`s. The LSTM input at each context position is the concatenation of (a) a learned 64-dim surface embedding from a frequency-clipped vocab, and (b) the **already-resolved CAS signature** of the context token (10+4+7+4 = 25 floats), passed straight through. The LSTM's job is to read the lexicon-tagged context as structure.
- **Fusion + heads** — concat word vector (192) + context summary (256, taken from the BiLSTM hidden state at the OOV position via a left/right join) → 448 → MLP (1 hidden layer, 256 units, GELU, dropout 0.1) → four parallel linear heads producing the 10 / 4 / 7 / 4 signature outputs with `tanh` activation to constrain into `[-1, +1]`. A fifth head emits a scalar **confidence logit** (calibrated; see §6.3). A sixth multi-label head emits role-tag probabilities over a closed vocabulary of ~30 tags taken from the seed lexicon.

**Parameter count:** ~6-8M total — char-CNN ~0.3M, surface vocab embedding (50K × 64) ~3.2M, BiLSTM ~0.4M, MLP and heads ~1M, role-tag head ~0.1M. Comfortable in the 5-20M envelope with headroom.

**Why this is the recommendation:**

1. The context-encoder input is the **lexicon's already-decoded CAS signature**. We are not asking it to discover CAS structure from raw text — we are asking it to interpolate where the lexicon is silent, using the lexicon's own structural decoding of surrounding words. This is the same architectural insight that motivated the entire tokenizer pivot (the encoder should compose pre-decoded structure, not learn it).
2. Char-CNN handles morphology and OOV gracefully without any subword tokenizer dependency. "decompose," "decomposed," "decomposing," "decomposition," "decomposable" share root structure that a char-CNN reads for free.
3. BiLSTM at this scale is fast on CPU. PyTorch `nn.LSTM` ships int8 dynamic quantization; a 128-hidden 1-layer BiLSTM over 16 tokens is ~0.2 ms inference single-thread.
4. Avoids the transformer trap. The frozen-CAS-CLM run proved that a transformer-shaped backbone is the wrong tool for this modality at the encoder side. The tagger is a different problem (single-word classification with small context, not sequence-to-sequence), but the same lesson — small purpose-built model beats generic transformer — applies.

### Option B — Tiny transformer (rejected as primary, kept as a secondary research lane)

**Shape:** 2-layer transformer with `d_model=128`, 4 heads, FFN dim 512, RoPE positions, over a window of 16 tokens centered on the OOV. Surface embedding + CAS-signature concat at the input. Outputs taken from the OOV-position vector.

**Parameter count:** ~3-5M.

**Why secondary, not primary:**

- The tagger problem is local (a word and a small window). Self-attention's strength — long-range dependency mixing — is not needed here. A BiLSTM is strictly more efficient at this scale.
- We have a lived-experience signal that "transformer at the input layer" is a load-bearing failure mode in this codebase. Choosing a non-transformer primary keeps that lesson architecturally encoded.
- Worth keeping as a secondary lane because if Option A plateaus at the eval gates (§5), a small transformer is the next thing to try. But that is Wave 3.5 contingency, not Wave 3 ship.

### Option C — MLP on bag-of-context-features (rejected)

**Shape:** for each OOV word, build a feature vector that concatenates: (a) char n-gram hashes of the surface form, (b) summed CAS signatures of the surrounding 8 tokens, (c) a few handcrafted features (capitalization, length, position-in-sentence). Feed to a 2-3 layer MLP → 25 outputs.

**Parameter count:** ~1-2M.

**Why rejected:** loses sequential structure of context entirely. "drawn to" and "drawn from" both have "drawn" with similar bag-of-context CAS profiles, but the affinity reading depends on the immediately following preposition. Bag-of-context makes that distinction unrecoverable. The seed lexicon already has 17 multi-word entries where word order is load-bearing; the tagger needs to honor the same structure for unseen multi-word patterns. MLP cannot.

### Recommendation

**Option A** — char-CNN word + BiLSTM context + four signature heads + confidence + role-tag heads, ~6-8M parameters total. Fits in the ~5-20M envelope, sub-ms CPU inference is achievable with int8 dynamic quantization, and the architectural inductive bias (small purpose-built, not generic transformer) matches the project's hard-won lesson.

---

## 3. Training data extraction

The CAS SDG corpus at `cas-synthetic/data/level3_pilot_full.jsonl` contains records of shape:

```
{
  "user_prompt":          "Help me preserve the target for ^2^O_{F3}|T ...",
  "cas_expression":       "^2^O_{F3}|T",
  "soft_operator_targets":[10 floats summing to 1],
  "soft_domain_targets":  [4 floats summing to 1],
  "bucket":               "v75_register" | "v76_production" | ...,
  ...
}
```

19,454 such records exist (Level 3 full pilot). Each gives us the relationship: *this NL prompt was generated to express this CAS expression*, with sample-level soft targets over operator and domain axes.

We need (word, CAS-signature) training pairs. Two extraction approaches were specified.

### 3.1 Approach 1 — word-level alignment (rejected)

Compute per-word attention or alignment between prompt words and target CAS axes via a learned attention head over the prompt, supervised by the prompt-level CAS expression. The word's target signature is the alignment-weighted projection of the prompt-level CAS axes onto that word.

**Why rejected:** chicken-and-egg. The alignment requires a model that already understands which words carry which CAS axes — exactly the model we are trying to train. Bootstrap variants (EM-style alternation, lexicon-seeded init, attention-from-positional-prior) are possible but introduce hard-to-debug bias and a discovery-vs-recall tradeoff that distracts from the core task.

### 3.2 Approach 2 — statistical association (RECOMMENDED)

For each non-stop word `w` appearing in at least `N_min` (≥ 50) prompts, compute the **conditional axis profile**:

```
axis_profile(w)[k] = E[ soft_target[k] | w in prompt ] - E[ soft_target[k] ]
```

This is the per-word excess over the corpus mean — how much does the presence of `w` shift the prompt-level CAS distribution above baseline. Computed independently per axis (10 noetic + 4 domain). For drive and register axes, the SDG records carry them in the `cas_expression` parse and the bucket label (`v75_register` records carry an explicit register; `v76_production` records carry production roles); we extract them by parsing the target expression with the existing `api/notation/compiler.py` and projecting onto the F1-F7 / T-A-f-E axes.

Smoothing: empirical Bayes shrinkage toward the corpus mean with prior strength proportional to `1/sqrt(count(w))`, so rare words shrink toward neutral and don't pick up high-variance noise.

Sign and scale: the raw profile is an excess; we normalize per axis to `[-1, +1]` by dividing by the empirical max absolute excess on that axis (95th percentile, not max, to limit tail influence). Output is the word's training-target signature.

**Why this approach:**

1. It is **non-circular**. Training targets come straight from corpus statistics; no helper model needed.
2. It is **interpretable**. The signature for `decompose` should look like ^6 with an analytical-register tilt; we can inspect the extraction and confirm it does, before training begins.
3. It is **monotone in data**. As the SDG corpus grows, the per-word profile gets sharper without algorithmic changes.
4. It admits straightforward **lexicon-anchor exclusion** (§3.3).

The extracted (word, profile) table becomes the training set. Each training sample also carries the original prompts the word appeared in, so the model gets context windows alongside the target profile.

### 3.3 Lexicon-anchored exclusion

To prevent the tagger from memorizing the lexicon and then trivially scoring high on lexicon-anchored eval, we apply a hard exclusion at training time:

- **Held-out set** = all single-word lexicon entries (currently 50+ of the 98 seed entries are single-word). These words are removed from the training pairs entirely. The tagger never sees them as targets during training.
- **At inference**, the assembler resolution order guarantees lexicon words go to the LEXICON branch and never reach the tagger. So the tagger needs to perform on words it has never been trained on — exactly the OOV situation it will face in production.
- **At eval** (§5), the held-out lexicon words are the gold standard for axis-correlation evaluation. Because the tagger was never trained on them, this is a clean OOV generalization measure.

Multi-word lexicon entries are handled differently: their constituent words may legitimately appear in training (e.g., "drawn" appears in "drawn to" but is itself a useful per-word signal). Multi-word entries are checked at the multi-word-match step of `assembler.tokenize()` and never reach the single-word OOV path.

---

## 4. Loss formulation

The output is 25 floats (10 + 4 + 7 + 4) in `[-1, +1]`, plus a confidence scalar, plus role-tag multi-label probabilities.

### 4.1 Per-axis loss

**Smooth L1 (Huber) per axis, masked.** Specifically:

- For each of the 25 axis positions, compute `Huber(pred, target, delta=0.1)`.
- Weight axes by inverse-frequency: noetic axes occur often, register axes less so. Apply a per-axis weight `w_k = 1 / sqrt(activation_rate_k)` clipped to `[0.5, 2.0]`.

**Why Huber not MSE:** the target distribution is sparse — most positions are near 0 with a long thin tail at ±0.7-0.95 (the lexicon entries above sit mostly between 0.6 and 0.95 on their primary axis and zero elsewhere). MSE punishes large errors quadratically, which matches the desired training signal; but Huber's linear regime above `delta` prevents one strongly-loaded primary axis from dominating gradients. `delta=0.1` puts ~95% of training targets in the quadratic regime and the primary-axis hits in the linear regime.

**Why not cross-entropy after binning:** binning `[-1, +1]` into discrete buckets discards the gradient magnitude. The downstream encoder uses these signatures as continuous features (the embedding layer's gated fusion expects floats, not class indices). Continuous regression with Huber preserves the modality.

### 4.2 Cross-axis correlation regularization

Add a small penalty term that discourages the tagger from putting nonzero mass on multiple primary noetic axes for the same word. Specifically:

```
L_sparsity = 0.01 * (||pred_noetic||_1 - ||pred_noetic||_∞)
```

The L1-minus-L∞ form is zero when all noetic mass is on one axis, positive when smeared. Same form for the domain axis. Drive and register axes are NOT regularized this way (multi-drive and multi-register signatures are legitimate; the lexicon already has examples).

### 4.3 Role-tag head loss

Standard binary cross-entropy with logits, summed over the closed tag vocabulary, weighted at 0.1× the axis loss so it cannot dominate.

### 4.4 Confidence head loss

The confidence scalar is trained against an **agreement-with-target** signal: the actual axis-loss value at training time is the supervised target for confidence (high-loss training examples teach the model to emit low confidence on similar inputs). Specifically:

```
target_conf = sigmoid(-axis_loss_per_example)
L_conf = MSE(pred_conf, target_conf.detach())
```

This is a calibration loss — the model learns that uncertain regions of input space yield high error, and emits low confidence there. At inference, the resulting confidence is a calibrated estimate of "how close is my prediction to ground truth on this kind of input."

### 4.5 Total loss

```
L = L_axis + 0.01 * L_sparsity + 0.1 * L_role_tags + 0.1 * L_confidence
```

---

## 5. Eval gates

The tagger ships only when all of these are met on a held-out eval split. None are aspirational; all are blocking.

| Gate | Threshold | Source |
|---|---|---|
| **Per-axis Pearson correlation** vs held-out single-word lexicon (the targets the tagger never saw at train time) | ≥ 0.55 on each of the 25 axes; mean ≥ 0.70 | the strongest direct OOV-generalization measure |
| **OOV coverage rate** — fraction of OOV tokens in a held-out NL eval set that receive `confidence ≥ 0.4` | ≥ 0.65 | confidence calibration check; the tagger is allowed to abstain, but not on most things |
| **Axis-consistency on lexicon-covered words** — when the tagger is run on lexicon words anyway (sanity check, with the lexicon override disabled), per-axis cosine similarity to lexicon ground truth | ≥ 0.70 | confirms the model has learned the right structure, not the wrong one |
| **Demographic-register robustness** — for the seeded register-variant pairs (`exhausted` / `hella tired` / `super sleepy` / `profoundly fatigued` etc.), the cross-variant signatures from the tagger should agree on noetic+domain+drive axes | cosine ≥ 0.80 between any two variant signatures on the (noetic, domain, drive) sub-vector | preserves the cross-register-robustness anchor that the lexicon enforces |
| **Anti-drift compliance** — words like `audit`, `scrutinize`, `find flaws` (currently in the lexicon as ^6, NOT ^3) — when masked from training, the tagger must NOT classify them as ^3 | held-out-anti-drift-set ^3 score < 0.2 AND ^6 score > 0.5 | preserves the load-bearing anti-drift guarantees of Wave 1 |
| **Latency** — single-call mean wall-clock on CPU (1 thread, int8) | ≤ 1.0 ms; p99 ≤ 3 ms | production constraint |
| **Model size on disk** — quantized int8 deployed model | ≤ 50 MB | CPU memory + cold-start budget |

If any gate fails, the integration in `assembler.py` defaults to FALLBACK (neutral signature, confidence 0). The tagger does not ship until all gates pass.

---

## 6. Integration spec

### 6.1 Resolution order with tagger

The new `assembler.tokenize()` order:

1. CAS-notation literal → `CAS_NOTATION` (conf 1.0)
2. Multi-word lexicon match → `LEXICON` (lexicon entry's confidence)
3. Single-word lexicon lookup → `LEXICON` (lexicon entry's confidence)
4. **NEW: tagger** — if word-shaped span and tagger is loaded → `LEARNED` (confidence as emitted by tagger, capped below max-lexicon-confidence; see 6.3)
5. Fallback → `FALLBACK` (neutral signature, confidence 0.0)

Lexicon ALWAYS wins. The tagger is consulted only when single-word lookup misses.

### 6.2 Source flag and confidence ceiling

- Tagger output gets `source=TokenSource.LEARNED`.
- Tagger confidence is capped at `0.85` (one tier below the canonical-colloquialism lexicon entries at 0.95). Even a maximum-confidence tagger output is recognizably less authoritative than a hand-vetted lexicon entry. Downstream eval and audit can filter on `source` to weight LEARNED tokens appropriately.

### 6.3 Confidence calibration

Three-stage pipeline:

1. Raw confidence-head logit → sigmoid → `[0, 1]`.
2. Temperature-scale on a held-out calibration split (Platt-style scalar `T` fit by minimizing NLL on target_conf vs pred_conf). Stored as a single fitted constant.
3. Cap at 0.85.

The temperature-scaling step ensures `confidence == 0.7` actually means ~0.7 expected axis-correlation with ground truth, so downstream consumers can use the value as-is.

### 6.4 Caching

**Yes, cache.** Tagger inference is fully deterministic given (surface_text, context-window-CAS-signature-tuple). Two-tier cache:

- **L1: per-word singleton cache** keyed on `surface_text.lower()`. This catches the pure-lexical case (most OOV words have stable signatures regardless of context). LRU, 32K entries (~5 MB at 25 floats + metadata per entry). Cache hit = ~1 µs.
- **L2: word-plus-context cache** keyed on `(surface_text, hash(context_signature_tuple))`. For words whose tagger output is sensitive to context (verbs that swing register, ambiguous nouns), this captures within-session reuse without being so big it bloats memory. LRU, 4K entries.

Cache invalidation: cache is per-tagger-checkpoint. Bumping the tagger version invalidates both tiers. The tagger model fingerprint is a hash of weights at load time, used as the cache namespace.

The cache is per-process. Cross-process or persistent cache is out of scope for the inference path; can be added in a later wave if profiling shows tokenize-time dominated by tagger inference.

### 6.5 Loading and lifecycle

The tagger is loaded lazily on first `tokenize()` call that requires it. Subsequent calls reuse the in-memory model. If the tagger model file is missing or fails to load, `assembler.tokenize()` logs a single warning and falls back to the pre-tagger resolution order (step 4 becomes FALLBACK directly). The tokenizer must remain fully functional without the tagger.

---

## 7. Training plan

### 7.1 Wall-clock arithmetic (per the device-sizing rule)

- Dataset: 19,454 SDG records → projected to ~15K-30K word/profile training pairs after dedup, frequency filtering, and lexicon exclusion.
- Per-step compute: char-CNN forward (cheap) + BiLSTM forward over 16 tokens (cheap at hidden=128) + heads (cheap). Estimated 5-15 ms/step on a single A6000 at batch 256.
- Steps to convergence (estimate from comparable small models): ~30-50K steps, 50-100 epochs of the dedup'd word table.
- Total wall clock: 30-50K steps × 10 ms = ~5-8 minutes per training pass on A6000.
- With validation, hyperparameter sweep (5-10 configs), and checkpoint-saving overhead: ~1-2 hours on a single A6000 to ship a candidate.

**Per the device-sizing rule:** the forward pass does NOT go through any pretrained transformer backbone. The model is small (~6-8M params). Total steps are 30-50K. By the rule-of-thumb (`forward_through_backbone OR steps > 1K → cloud GPU`), this is **borderline**.

**Recommendation:** train on cloud GPU (A6000 or smaller — even an L4 would work) anyway. Reasons:

1. ~30-50K steps is past the 1K threshold the rule sets.
2. Hyperparameter sweep across 5-10 configs amortizes pod cost cleanly.
3. Total cost is negligible at this size — ~1-2 hours × $0.50/hr = ~$1.

**CPU is acceptable for:** unit tests, smoke runs (a few hundred steps to verify the loop converges), per-axis sanity checks during development. CPU is NOT acceptable for the full training run; the directional rule is "if in doubt, pod." This run is not in doubt — pod.

### 7.2 Data sizing

- Minimum: 10K (word, profile) training pairs after lexicon exclusion. Below this, per-axis correlation gates likely miss.
- Target: 25K-30K pairs once the lexicon scaling work (Wave 2-A) lifts the lexicon to ~5K entries and enables a richer SDG-derived training set.
- The first tagger ship can be on the current 19K SDG records; subsequent retrains as the SDG corpus grows.

### 7.3 Checkpointing and reproducibility

- Save: model weights (fp32 master), int8-quantized inference copy, calibration temperature, tagger fingerprint hash, training config JSON, axis-correlation eval results JSON.
- Naming: `cas-native/tagger/runs/<date>-<short-hash>/`. Same convention as existing CAS-Native runs.
- Reproducibility: training is fully seeded; same SDG corpus + same seed = byte-identical weights.

### 7.4 What gets shipped

The deployed artifact is a single quantized `tagger.pt` file (~30-50 MB) plus a `tagger_config.json` (~1 KB) at a stable path under `cas-native/tokenizer/tagger/`. The `assembler.py` lazy loader picks it up automatically.

---

## 8. Inference contract

```python
def tag_oov(
    surface_text: str,
    context: list[StructuredToken],
    *,
    oov_position: int,                     # index in `context` of the OOV (lexicon-miss) token
) -> tuple[CASSignature, float]:
    """
    Returns (signature, confidence). Confidence is in [0.0, 0.85].

    - `surface_text`: the exact characters of the OOV token. NOT lowercased
      by the caller; the tagger handles casing internally.
    - `context`: a window of StructuredToken instances surrounding (and
      including) the OOV token. The tagger reads at most 8 tokens left and
      8 tokens right of `oov_position`. Excess context is truncated; missing
      context (sentence boundaries) is padded with neutral-signature
      sentinel tokens.
    - `oov_position`: which entry in `context` is the OOV. The tagger needs
      this because the OOV's StructuredToken has a neutral signature
      (FALLBACK), and the tagger should NOT read its own neutral signature
      as informative input — instead it reads the OOV's surface_text via
      the char-CNN pathway.
    """
```

### 8.1 Context window

- **Bidirectional**, 8 left + 8 right (16 tokens total in the BiLSTM input). Bidirectional because CAS-axis assignment is genuinely sensitive to following context (e.g., "drawn to X" vs "drawn from X" vs "drawn out X"). At tokenize-time the assembler has already produced the full token stream; bidirectional context is free.
- **Whitespace skipped**, punctuation included (punctuation carries register signal — em-dashes, ellipses, exclamation marks).
- **CAS-notation tokens included** — when the OOV is adjacent to literal CAS notation, the tagger sees the high-confidence CAS_NOTATION signature in context.
- **FALLBACK tokens (other OOV words in the same sentence)** are included with neutral signatures. The tagger learns to handle context that is itself partially OOV; it does not require all-lexicon context.

### 8.2 Stateless

The tagger is pure-functional: same inputs always yield same outputs. This is the contract the cache (§6.4) relies on. No hidden state, no batchnorm-running-stats, no sampling.

### 8.3 Batched form

```python
def tag_oov_batch(
    items: list[tuple[str, list[StructuredToken], int]],
) -> list[tuple[CASSignature, float]]:
    ...
```

For tokenize-time efficiency when a single input has many OOVs, items get bucketed by surface-text length and context-window length, padded, and run through the model in one forward pass. Caching is consulted before batching so cache hits don't waste the batch slot.

---

## 9. Failure modes and guardrails

### 9.1 Failure modes the tagger will exhibit

1. **Out-of-distribution surface forms** — words containing characters outside the trained char vocab (Cyrillic, CJK, heavy diacritics, mathematical symbols). Currently English-only; the lexicon is English-only too. The char-CNN will produce noise.
2. **Pure proper nouns** — names like "Gödel" or "Tehran" carry no real CAS signal but the model will still emit something. Likely low-magnitude but nonzero.
3. **Domain-specific jargon outside SDG coverage** — medical, legal, technical terminology not represented in the SDG distribution. The tagger will extrapolate from morphological cues (the "-ology" suffix biasing toward analytical register, etc.); these guesses can be wrong.
4. **Sarcasm and tonal inversion** — explicitly out of scope per Wave 1 handoff (Wave 4 encoder handles sarcasm via register contradiction). Tagger reports literal axis structure.
5. **Anti-drift regression** — the tagger trained from corpus statistics could in principle re-learn Scheme-A/B drift patterns ("audit" → ^3) if the SDG corpus is contaminated. This is what the anti-drift eval gate (§5 row 5) blocks.
6. **Confidence over-claim** — a poorly calibrated confidence head could emit `0.8` confidence on an entirely wrong signature. The temperature-scaling step (§6.3) is the calibration defense; the eval gate on per-axis correlation is the empirical defense.

### 9.2 Guardrails

1. **Confidence floor** — if the tagger's calibrated confidence on a token is below `0.3`, the assembler discards the tagger output and emits a FALLBACK token with neutral signature. The threshold is configurable; `0.3` matches the OOV-coverage gate's structure (gate requires `≥ 0.4` coverage; below `0.3` we explicitly abstain, the `[0.3, 0.4)` band is "tagger contributes a low-weight signal" but not high-confidence).
2. **Magnitude clamp** — the tagger's `tanh` output already constrains to `[-1, +1]`, but we also reject any signature where `||noetic||_1 > 2.0` or `||domain||_1 > 1.5` (the lexicon entries never exceed these L1 norms, so larger outputs are out-of-distribution and likely garbage). Out-of-bound outputs → FALLBACK.
3. **Anti-drift assertion at load time** — the tagger checkpoint, on load, runs the held-out anti-drift set (§5 row 5) and refuses to load if it fails. This makes anti-drift a runtime contract, not just a training-time eval gate.
4. **Source flag transparency** — every LEARNED token is flagged. Audit and dashboard tooling can filter LEARNED-only or compare LEARNED-vs-LEXICON token-density per assessment. If a future regression introduces drift, the affected sessions are isolable.
5. **Disable switch** — environment variable `CAS_TAGGER_DISABLE=1` (or config flag) bypasses the tagger entirely and reverts to LEXICON-or-FALLBACK. This is the kill switch if a deployed tagger misbehaves; the system degrades to Wave-1-tokenizer behavior, not to broken behavior.
6. **Test coverage as durable contract** — same pattern as Wave 1's anti-drift property tests. The Wave 3 ship includes a test suite that asserts: anti-drift words classify correctly; demographic-register variants produce similar signatures; sub-ms latency on representative inputs; cache hit/miss behavior; out-of-bound output rejection; disable switch works. If a future agent breaks these, the model or integration is wrong, not the tests.

### 9.3 Truly-neutral fallback path

When the tagger declines (low confidence, magnitude clamp, OOD characters, disabled), `assembler.tokenize()` emits the same FALLBACK token it emits today: neutral signature, confidence 0.0, source `FALLBACK`. The encoder's embedding adapter (Wave 2-C scope) treats FALLBACK tokens as surface-only — they participate in surface-vocab embedding but contribute no CAS-signature features. This is the truly-neutral path and matches the current pre-tagger behavior; the tagger is strictly additive.

---

## 10. Open questions and dependencies

1. **Lexicon scaling timing.** Wave 2-A scales the lexicon to 5K-15K entries. The tagger trains on lexicon-anchored exclusion; if the lexicon is much larger by tagger train time, the held-out lexicon set for eval is also larger and the per-axis-correlation gate is more robustly testable. Recommend: ship Wave 2-A first iteration (~1-2K entries), then train the tagger; retrain after each lexicon expansion wave.
2. **Encoder-integration gating (Wave 2-C).** The encoder's embedding layer consumes `cas_signature` features regardless of source. The tagger ships independently of Wave 2-C, but its outputs only become valuable downstream once the encoder reads them. Sequence: Wave 2-A → 2-C design → 2-B (this) implementation → encoder Wave 4 ship.
3. **Role-tag vocabulary lock.** The closed role-tag vocabulary (~30 tags from the seed lexicon) needs to be finalized before training. Today's tag set: `self_reference`, `affinity_marker`, `aversion_marker`, `visceral`, `metaphor`, `composition_marker`, `identity`, `possessive`, `resonance_marker`, `rhythm_marker`, `confidence_hedge`, `demonstrative`, `embodied_marker`, `cas_literal`, `compound_state`, plus headroom. Wave 2-A may expand this. Lock the vocabulary at first tagger train; bump versions for additions.
4. **Per-language scope.** English only at Wave 3. The architecture (char-CNN over an English-friendly char vocab + English BiLSTM) doesn't preclude multilingual extension, but the SDG corpus is English; multilingual is its own future wave with its own SDG.

---

## 11. Summary

The learned CAS-axis tagger is a small (~6-8M param) char-CNN-plus-BiLSTM model that fills in CAS signatures for OOV words at tokenize-time, sub-millisecond per call on local CPU. It trains from scratch on per-word statistical association profiles derived from the existing CAS SDG corpus, with lexicon-anchored words held out so it cannot memorize the lexicon. Lexicon ALWAYS wins; the tagger is the strict fallback between LEXICON and FALLBACK. Output gets `source=TokenSource.LEARNED`, confidence ceiling 0.85, calibrated by temperature scaling. Anti-drift is preserved by held-out anti-drift evaluation gating both training and runtime load. Training runs on cloud GPU (~1-2 hours, ~$1) per the device-sizing rule, even though borderline by parameter count. Failure modes are bounded by confidence floor, magnitude clamp, anti-drift load-time assertion, disable switch, and the existing FALLBACK path that preserves Wave-1 tokenizer behavior under any tagger failure.

The architectural through-line is the same as Wave 1's: small purpose-built model that composes pre-decoded structure beats generic transformer that has to discover structure from raw text. The tagger reads the lexicon's already-tagged context and interpolates within it, never asked to learn what the lexicon already knows.
