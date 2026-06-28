# Native CAS-Native English Generation Head — Architecture Specification

**Date:** 2026-05-04
**Author:** Architecture-spec agent (parallel-track Opus)
**Status:** FINAL — load-bearing for tokenizer, SDG, model, and training agents
**Owning framework:** CAS v7.7 (Register Multiplicity & Operator Discipline)
**Module path under spec:** `cas-native/model/nl_generation_head.py` (new)

---

## §0. Hard constraints (non-negotiable)

These four constraints govern every design decision below. If a downstream agent
proposes a change that violates any of them, escalate before writing code.

1. **NO foreign pretrained models.** Zero use of TinyLlama, Llama, Qwen, Mistral,
   Phi, Gemma, GPT-2, BERT, or any other externally pretrained checkpoint. **All
   weights are random-initialized from scratch** using the existing
   `CASNativeModel._init_weights` pattern (xavier_uniform on Linear,
   normal(0, 0.02) on Embedding, ones/zeros on LayerNorm). The vocabulary is
   trained from scratch on the SDG corpus. This is a strategic, ratified
   commitment: *CAS is the architecture, not a wrapper.*
2. **Traceability is the spine.** Every generated token walks back through the
   stack to (a) its CAS conditioning, (b) layer activations, (c) bottleneck
   attribution, (d) the nearest-neighbor training pair in embedding space, and
   (e) a live CAS-grounding score. If a design choice loses trace, it is wrong.
3. **Reuse the existing CAS-Native infrastructure.** The 19 layer modules under
   `cas-native/model/` (`domain_descent`, `fractal_attention`, `register_film`
   incl. `RegisterLatent`, `rpm_gate`, `lacunarity_gate`, `lacunarity_head`,
   `topos_reasoner`, `composition`, `embedding`, `expression_proposer`,
   `production_semantics`, `emergent_register`, `meta_logic_constructs`,
   `structured_token_embedding`, `structured_prediction`, `type_constraints`,
   `loss`, `cas_native_model`) are not optional infrastructure — they ARE the
   architecture. The NL head is a new output surface mounted on existing CAS
   reasoning, not a parallel transformer.
4. **CAS gets the glory.** The encoder is `CASNativeModel`. Tokens are emitted
   by a decoder conditioned on the CAS state vector, the 40-state cognitive
   simplex, the Phenomenological Register FiLM via `RegisterLatent`, the
   structured-prediction backbone, and the RPM-gated hidden states. The decoder
   is a thin emission surface; the cognitive work lives in the CAS spine.

---

## §1. Goal and non-goals

### Goal

Produce a CAS-Native generation head that emits fluent English replies grounded
in CAS state, with traceability surface attached to every emitted token. The
model **first** computes a full CAS reading of the input — Noetic, Domain,
Drive, Register, RPM satisfaction, inversion flags, topos truth values — and
**then** decodes English text whose every token is conditioned on, and
attributable to, that CAS reading.

### Non-goals

- **Not a fine-tune of a foreign LM.** No TinyLlama / Llama / Qwen / Mistral /
  Phi / Gemma / GPT-2 / BERT in the dependency graph at any depth.
- **Not a pure template renderer.** The existing `cas_native.inference.cas_renderer`
  and `cas-native/dst/nl_generation_head.py` template stub remain as fallbacks
  but are not the destination state. The destination is a learned decoder.
- **Not a post-hoc CAS labeler.** The model is not "generate English then label
  it." CAS state is the conditioning input to the decoder; the decoder cannot
  emit a token without conditioning on it.
- **Not a chain-of-thought transcript renderer.** The decoder produces
  conversational English, not CAS algebra; the CAS algebra appears in the
  trace, not in the surface text (unless the user explicitly asks for it via
  the Exposure Button).

---

## §2. Architectural placement

### Decision: confirmed — parallel head on the d_model bottleneck

I confirm the shared baseline: an **English LM decoder mounted on the existing
`CASNativeModel`** as a third parallel output head, alongside the existing
`lm_head`, `topos_reasoner`, `inversion_detector`, `generative_head`,
`lacunarity_head`, and (when attached) `expression_proposer`. The decoder
consumes:

- the **final hidden states** `x` (post-`final_norm`) at d_model = 512,
- the **40-state cognitive simplex** `cognitive_state` (post-`lacunarity_gate`),
- the **pooled hidden state** `pooled_hidden_state` (for global conditioning),
- the **`StructuredPrediction`** discrete CAS reading (turn_type, expression
  family, transition_kind, noetic, domain, drive, registers, register_mode,
  authority, has_omega, has_meta_logic) when the structured-prediction head is
  attached to the encoder.

### Why parallel-head over alternatives

| Alternative | Verdict | Reason |
|---|---|---|
| Separate decoder transformer with its own embedding & encoder | Rejected | Loses the CAS spine. Decoder would have to re-learn CAS structure. Violates Constraint 3. |
| Hijack the existing `lm_head` | Rejected | `lm_head` is a token-classification head over the encoder vocabulary; making it generative would require causal masking that conflicts with the encoder's bidirectional path used for structured prediction. |
| Decoder-only model that subsumes CAS reasoning | Rejected | Throws away the 19 CAS layer modules, the Wave 7B v2 register FiLM, the lacunarity self-correction, the domain-descent feedback path, and the RPM gate — all of which are load-bearing. Violates Constraints 3 and 4. |
| Encoder-decoder where encoder is `CASNativeModel`, decoder is fresh-init transformer with cross-attention | **Selected** | Preserves CAS spine. Decoder is thin. Cross-attention is the conditioning channel. Trace is uniform. |

### ASCII architecture diagram

```
                         INPUT ENGLISH (user utterance)
                                     |
                                     v
                    +--------------------------------+
                    |  HybridCASTokenizer (extended  |     §5
                    |  with English BPE merges, all  |
                    |  CAS reserved tokens kept)     |
                    +--------------------------------+
                                     |
                                     v
            +------------------------------------------------+
            |        CAS-NATIVE ENCODER (CASNativeModel)     |
            |                                                |
            |  token_embedding -> pos_encoding               |
            |        |                                       |
            |        v                                       |
            |  +-- CASTransformerLayer x N=6 ------+         |
            |  |                                   |         |
            |  | DomainDescentAttention            |         |
            |  |   (P>=C>=E>=O slot-attention      |         |
            |  |    over 40-state simplex)         |         |
            |  | FractalAttentionHead (IFS)        |         |
            |  | PrerequisiteGateLayer (RPM)       |         |
            |  | FFN + LN                          |         |
            |  +-----------------------------------+         |
            |        |                                       |
            |        v                                       |
            |   final_norm                                   |
            |        |                                       |
            |   +----+--------+----------+----+-----+--+     |
            |   |             |          |    |     |  |     |
            |   v             v          v    v     v  v     |
            | lm_head    topos_reasoner  ...  inversion lac  |
            |             (existing parallel heads)          |
            |                                                |
            |   v2_components (when attached):               |
            |   - register_embedding (RegisterLatent ADR-08) |
            |   - expression_proposer (ADR-07)               |
            +------------------------------------------------+
                          |          |          |
                hidden_   |  cognitive_state    | StructuredPrediction
                states    |  (B,seq,40)         | (turn_type, family,
                (B,seq,d) v  pooled (B,d)       v noetic, domain, drive,
                          |                     | registers, register_mode,
                          |                     | authority, omega, meta_logic)
                          |                     |
                          +-------+-------------+
                                  |
                                  v
            +----------------------------------------------+
            |  CAS-CONDITIONING ASSEMBLY (3 channels)      |     §4
            |                                              |
            |  Channel A: Discrete CAS prefix tokens       |
            |    [CAS] ^3^P|A F3 ... [/CAS] [RESPONSE]     |
            |    -- via HybridCASTokenizer reserved tokens |
            |                                              |
            |  Channel B: Continuous soft-prefix           |
            |    pooled_hidden_state -> 4 learned slot     |
            |    projections -> 4 d_model "virtual tokens" |
            |    prepended to decoder input embedding      |
            |                                              |
            |  Channel C: Cross-attention memory           |
            |    encoder hidden_states (B, seq_in, d)      |
            |    + 40 cognitive-state slot states (B,40,d) |
            |    -> 1 unified KV memory of length seq_in+40|
            +----------------------------------------------+
                                  |
                                  v
            +----------------------------------------------+
            |        NL GENERATION DECODER  (NEW)          |     §3
            |        cas-native/model/nl_generation_head.py|
            |                                              |
            |  N_dec = 6 CASNLDecoderLayer                 |
            |    each layer:                               |
            |    - LN -> Causal Self-Attn (8h, d=512)      |
            |    - Residual                                |
            |    - LN -> Cross-Attn to CAS memory          |
            |        masked by DomainDescentMask           |
            |        on the 40 slot-state keys             |
            |    - Residual                                |
            |    - LN -> FractalAttentionHead OPTIONAL     |
            |        (multi-scale self-attn, fractal_depth |
            |         from config)                         |
            |    - LN -> FFN (d, 4d, GELU, dropout, d)     |
            |    - Residual                                |
            |    - PrerequisiteGateLayer (RPM)             |
            |    - RegisterFiLM_d (post-block, via         |
            |        RegisterLatent.compute_gamma_beta_d)  |
            |                                              |
            |  final_norm                                  |
            |  nl_lm_head: Linear(d, V_total)              |
            +----------------------------------------------+
                                  |
                                  v
            +----------------------------------------------+
            |   TRACE CAPTURE (live, per-token)            |     §7
            |   GenerationTrace extends LiveTrace patterns |
            |   (cas-native/trace/live_capture.py)         |
            +----------------------------------------------+
                                  |
                                  v
                       OUTPUT ENGLISH + TRACE BUNDLE
```

The encoder is unchanged — every existing test continues to pass byte-for-byte
when `with_nl_head=False` (the default). The new decoder is mounted only when
explicitly enabled.

### One revision to the shared baseline

The shared baseline says "soft-prefix as 4 learned position embeddings." I
revise this to **4 learned slot-projections of the pooled hidden state**, not
4 free-floating learned embeddings. The projection is a `Linear(d_model, 4 *
d_model)` reshape. Reason: free-floating embeddings carry no CAS information
on their own and would have to learn it from scratch through the cross-attention
gradient path — slow and trace-opaque. Projecting from `pooled_hidden_state`
makes Channel B a *deterministic function* of the encoder's CAS reading, which
is what the trace needs.

**Flag for orchestrator: revised baseline assumption.** If the model agent has
already begun building the 4-free-embedding variant, switch to projection.

---

## §3. Decoder block

### `CASNLDecoderLayer` (new module)

A single decoder layer composes, in order:

1. **LayerNorm 1** (pre-norm style, matching encoder convention).
2. **Causal multi-head self-attention** — 8 heads, head_dim = 64, d_model = 512.
   Uses standard causal mask. This is a fresh `nn.MultiheadAttention` (random
   init, not borrowed). The token-position causal mask is the *only* structural
   constraint here; CAS-structure constraints come in step 4.
3. **Residual.**
4. **LayerNorm 2 + cross-attention to CAS memory.** The K/V memory is the
   concatenation of (a) encoder `hidden_states` of length `seq_in`, and (b) the
   40 slot states produced by `DomainDescentAttention._aggregate_slots`. The
   slot states are aligned with the cognitive-state simplex and are the
   CAS-structural injection point. **A domain-descent mask is applied to the
   slot half of the memory:** decoder query at any timestep can attend to all
   `seq_in` encoder positions but only to the slot range up to the current
   "decoded domain." For early decoder timesteps this defaults to the full
   slot bank; under §6 curriculum, the mask narrows during training on
   structured-output examples to teach P→C→E→O ordering of domain references.
5. **Residual.**
6. **LayerNorm 3 + (OPTIONAL) FractalAttentionHead.** Multi-scale self-attention
   over the decoder's own past tokens, gated by a learnable scalar starting at
   0. Initially a no-op (preserves training-loss landscape); the gate opens
   only if the model finds it useful. Reuses
   `cas_native.model.fractal_attention.FractalAttentionHead`.
7. **Residual.**
8. **LayerNorm 4 + FFN.** `Linear(d, 4d) -> GELU -> Dropout -> Linear(4d, d) ->
   Dropout`. Identical structure to the encoder's `CASTransformerLayer.ffn`.
9. **Residual.**
10. **PrerequisiteGateLayer** (RPM). Reuses
    `cas_native.model.rpm_gate.PrerequisiteGateLayer`. Returns a per-position
    satisfaction tensor that flows into the trace and into the §6 RPM-aware
    auxiliary loss.
11. **Residual on the gated output.**
12. **RegisterFiLM modulation** (post-block, before passing to next layer).
    Uses the encoder's `v2_components["register_embedding"]` `RegisterLatent`
    via its `compute_gamma_beta_d()` head. The active register is selected by
    the `StructuredPrediction.register_mode` and `registers` fields:
    - `"single"` → use the single active register's gamma/beta.
    - `"set_spec"` (`|⟨…⟩`), `"co_presence"` (`+`) → mean-pool the gamma/beta
      across the active registers.
    - `"integration"` (`×`) → use the active registers' gamma/beta but apply
      sequentially (matches the closed-form composition in
      `CASNativeModel._apply_register_film_to_logits`).
    - `"none"` → identity (no FiLM applied).

The Register FiLM at d_model is the **same** `RegisterLatent` learned during
encoder training, not a fresh decoder-specific FiLM. Single source of truth
per ADR-08 Option E. This is the load-bearing reuse choice.

### Decoder hyperparameters

```
d_model        : 512   (matches CASNativeConfig.d_model)
n_heads        : 8     (matches CASNativeConfig.n_heads)
head_dim       : 64
ffn_hidden     : 2048  (= 4 * d_model)
n_decoder_layers: 6
fractal_depth  : 3     (when fractal head enabled)
dropout        : 0.1
max_gen_len    : 256   (chat-length default; configurable up to max_seq_len)
```

Total decoder parameters at d_model=512, n_layers=6 with fractal head enabled:
≈48–55M. Plus the new English-extended LM head (Linear(d, V_total)) which is
512 × ~32K ≈ 16M. Encoder remains its existing ≈50M. **Total model: ~110–120M
parameters**, all random init, all CAS-Native, no foreign weights.

---

## §4. Conditioning surface — three channels

### Channel A: Discrete CAS prefix

The `HybridCASTokenizer` emits a sequence of reserved CAS tokens that name the
encoder's structured prediction. The decoder receives these prepended to its
own input embedding stream. Format:

```
[CAS] ^<noetic> ^<domain> F<drive> |<R1> |<R2> ... [/CAS] [RESPONSE] <reply tokens...>
```

For multi-register cases, the operator discipline of CAS v7.7 governs the
prefix: `|⟨A,f⟩` for set_spec, separate `|A |f` tokens for co-presence (each
preceded by `+`), and `(|A × |f)` (parenthesized with explicit `×`) for
integration. The `[CAS]…[/CAS]` block lets the decoder learn to distinguish
prefix from body. All these tokens are existing reserved entries in
`SPECIAL_TOKENS` and `CAS_RESERVED_TOKENS` (verified against
`cas-native/training/tokenizer.py` lines 19–106).

### Channel B: Continuous soft-prefix

`pooled_hidden_state` (shape `(B, d_model)`) is projected through
`Linear(d_model, 4 * d_model)` and reshaped to `(B, 4, d_model)`. These four
"virtual tokens" are prepended to the decoder's embedded input *after* token
embedding and before positional encoding. Positional encoding is applied to the
combined sequence so positions 0..3 are the soft-prefix and 4.. are the real
decoder tokens.

This is structurally equivalent to a 4-token Prefix-Tuning surface but with
the prefix being a deterministic projection of the encoder's CAS state, not
free parameters. Trace can attribute every decoder activation back to the four
soft-prefix dimensions and from there to `pooled_hidden_state` and from there
to the encoder's full CAS reading. **One unbroken trace path.**

### Channel C: Cross-attention KV memory

The cross-attention KV memory at every decoder layer is a concatenation:

- Encoder `hidden_states` of shape `(B, seq_in, d_model)`,
- 40 cognitive-state slot states of shape `(B, 40, d_model)`, computed by
  `DomainDescentAttention._aggregate_slots(hidden_states, cognitive_state, mask)`
  on the encoder's final hidden states.

Total memory length: `seq_in + 40`. The decoder has direct access to the
explicit 40-slot CAS bank, not just to the implicit signal in `hidden_states`.
The **domain-descent mask** is applied to the slot half of the memory: at
training time on structured-output examples, decoder positions decoding a
P-domain reference may attend only to slot indices [0, 10); a C-domain
reference, only to [0, 20); E to [0, 30); O to [0, 40). This trains the same
P≻C≻E≻O total order the encoder enforces. At inference and on free-text
positions, the mask defaults to fully open over the 40 slots (the encoder's
own prior already shapes their content).

### Where each existing CAS module applies in the decoder

| Module | Decoder usage |
|---|---|
| `DomainDescentAttention` | Indirectly — its `_aggregate_slots` produces the 40 slot states for Channel C; its `domain_mask` is the slot mask in cross-attention. |
| `RegisterLatent` (ADR-08) | Post-block FiLM at d_model, step 12 of each decoder layer. |
| `PrerequisiteGateLayer` | RPM gate after FFN, step 10 of each decoder layer. Per-position satisfaction tensor flows to trace + aux loss. |
| `FractalAttentionHead` | Optional self-attention head, step 6, gated to start at 0. |
| `LacunarityGate` | Run on `cognitive_state` BEFORE the decoder reads it (already done in encoder). Decoder consumes `corrected_state`. |
| `CognitiveToposReasoner` | Run on `pooled` (already done in encoder). Truth values flow into trace; do not condition decoder logits directly (avoids the topos head dragging decoder into ethical-classification objective during NL training). |
| `LacunarityHead` | Same as topos: trace-only at decoder side. |
| `expression_proposer` | When attached, its proposals can prime Channel A (CAS prefix). |
| `meta_logic_constructs` | Construct vocabulary already in tokenizer reserved tokens; decoder learns to emit them in Channel A and to reference them in body text. |
| `composition.GenerativeHead` | Trace-only signal to decoder (not a conditioning input). |

The decoder is **not** a parallel to the encoder transformer stack — it is a
generation surface mounted on the encoder's CAS work.

---

## §5. Vocabulary and tokenizer extension

### Approach: extend `HybridCASTokenizer`, do not replace it

The existing `HybridCASTokenizer` (`cas-native/training/tokenizer.py`) keeps
all CAS structural symbols exact, persists vocab to JSON, and is used by every
existing CAS-Native checkpoint. **Do not break it.** Extension procedure:

1. **Reserve all current tokens.** `SPECIAL_TOKENS` (15 entries) and
   `CAS_RESERVED_TOKENS` (the full set including `^0..^9`, `^P/C/E/O`,
   `F1..F7`, `|T/A/f/E`, the 33+ operator/delimiter symbols, `CO-0..CO-9`,
   `RPM`, `Phi`, `Φ`, set names like `Noetics/Domains/...`, the
   `Foundation_1..7` series, `Set/MetaSet/NoeticSet/...Cluster`, and the
   construct vocabulary from `meta_logic_constructs.CONSTRUCT_VOCABULARY`)
   keep their existing IDs. Existing checkpoints continue to load.
2. **Train an English BPE on the SDG corpus.** Cap at 16K English merges. The
   training corpus is the SDG-paired (CAS, English) reply side only — the
   decoder will never need to tokenize a full encyclopedia. 16K is sufficient
   for fluent conversational English in a constrained domain (compare:
   GPT-2's 50K is for open-domain web text; chat-only registers historically
   fit comfortably in 8–16K).
3. **Merge.** Final tokenizer vocab = `SPECIAL_TOKENS ∪ CAS_RESERVED_TOKENS ∪
   English-BPE merges`, with English merges occupying IDs after all reserved
   IDs. **No collision** is possible because every reserved token is a
   non-trivial multi-character string explicitly listed; the BPE training
   procedure pre-removes all reserved-substring matches before learning
   merges (see implementation note below).
4. **Cap total vocab at 32K.** `CASNativeConfig.vocab_size = 32000` is the
   ceiling. Reserved tokens consume ~500 IDs; English BPE gets ~16K; remaining
   ~15.5K headroom for future SDG vocabulary growth or tokenizer revision
   without resizing model embeddings.

### BPE training procedure (implementation detail for tokenizer agent)

```
1. Load SDG corpus (cas, english_reply) pairs from
   cas-native/data/<sdg_output>.jsonl
2. Strip the cas field; keep only english_reply text.
3. Pre-tokenize with whitespace + punctuation split.
4. Mask any reserved-token substring matches in the text BEFORE BPE
   training (replace with placeholder so they never enter merges).
5. Train BPE using the existing sentencepiece-equivalent procedure or
   Hugging Face tokenizers (BPE only, not unigram). Target vocab: 16K
   English merges.
6. Persist as bpe_merges.txt + bpe_vocab.json under the run directory.
7. Wire into HybridCASTokenizer via a new method `extend_with_english_bpe()`
   that merges the BPE table into the existing token-ID space at
   ID = len(reserved_token_table).
```

**Existing checkpoint compatibility.** Existing classifier checkpoints
(K=9 baseline, v1 Full Stack, etc.) load with the old vocab IDs unchanged.
The new English BPE merges only become live when the NL head is attached.
The encoder's `lm_head` is preserved (uses the original CAS-only vocab).
The new `nl_lm_head` is the one that ranges over the full extended vocab.

### Reserved-token handling at decode time

During generation, after the `[RESPONSE]` token is emitted, the decoder may
emit either reserved CAS tokens (e.g., when the response references a CAS
state explicitly per Exposure Button mode) or English BPE tokens. Both are
valid. The trace records the source of each emitted token (reserved vs BPE) —
this is one of the trace fields in §7.

---

## §6. Loss and curriculum

### Joint loss formulation

```
L_total = α · L_structured + β(t) · L_LM + γ · L_trace_consistency + δ · L_rpm

where:
  L_structured = existing structured_prediction_loss over the 12 heads
                 (turn_type, expression_family, transition_kind, noetic,
                  domain, drive, register, register_mode, meta_relation,
                  authority, omega, meta_logic)
  L_LM         = causal LM cross-entropy on the [RESPONSE] body, over the
                 nl_lm_head logits, computed only on positions after
                 [RESPONSE] token (positions in the CAS prefix and soft-prefix
                 are masked out of L_LM so the prefix-tuning prefix never
                 receives token-level supervision).
  L_trace_consistency = MSE between (a) the encoder's StructuredPrediction
                 argmax classes derived from `pooled_hidden_state` alone,
                 and (b) the StructuredPrediction the decoder *implies* by
                 rederiving the structured-prediction-head output from the
                 mean of decoder-input soft-prefix tokens. This forces the
                 soft-prefix to carry the same CAS reading the encoder
                 computed — a structural anti-drift constraint.
  L_rpm        = RPM-satisfaction regularizer: penalize the decoder's per-
                 position rpm_satisfaction tensor for falling below the
                 encoder's rpm_satisfaction. Mathematical form: hinge loss
                 max(0, encoder_rpm_mean - decoder_rpm_mean). Stops the
                 decoder from generating tokens that violate the encoder's
                 RPM-gate decisions.
```

### Curriculum on β

The structured head MUST NOT degrade. The K=9 baseline at 93.2% canonical
exact is the load-bearing classifier, and joint training has known capacity-
stealing risk (cf. PR #6 K9_DiagLoop graph encoder which traded 14pp canonical
for 5pp drive consistency). β schedule:

```
Phase 1 (steps 0     – 2,000):    β = 0.0       structured-only warmup
Phase 2 (steps 2,000 – 10,000):   β linear ramp 0.0 → 0.3 over 8K steps
Phase 3 (steps 10,000 – 30,000):  β = 0.3       joint training plateau
Phase 4 (steps 30,000 – 50,000):  β linear ramp 0.3 → 0.5 over 20K steps
Phase 5 (steps 50,000+):          β = 0.5       LM-priority continuation
```

α is fixed at 1.0 throughout. γ ramps with β (γ = 0.1 · β). δ is fixed at
0.05 for all steps where β > 0.

### Anti-degradation guard

Every 1,000 steps, evaluate the K=9 structured head on a fixed 1K canonical
exact slice. If canonical exact drops more than 2pp from the pre-NL baseline,
**halt** and report. This is the same guardrail used in the K=9 + bare-slot
paraphrase template eval. The agent must not ship a version that improves
fluency at the cost of structural accuracy.

### LR and optimizer

- AdamW, lr=3e-4 with linear warmup (1K steps) then cosine decay over 50K
  steps to lr=3e-5.
- Weight decay = 0.01 (excluding layer norms, biases, and the
  `RegisterLatent` parameters per the existing trainer convention).
- Encoder parameters are *unfrozen* — they learn from the LM gradient too.
  Frozen-encoder variants are explicitly forbidden by the modality-mismatch
  finding (project_cas_transformer_modality_mismatch_pivot — frozen CAS-CLM
  backbone underperforms hash features ~100x). The decoder is the new front
  door; the encoder must adapt to it.

---

## §7. Trace surface (LOAD-BEARING)

### Design

Per-token generation trace extending the patterns in
`cas-native/trace/live_capture.py`. The existing `LiveTrace` dataclass is for
single-prediction structured-output traces; the new `GenerationTrace` is a
per-token sequence of trace records covering an entire generation.

The new module is `cas-native/trace/generation_trace.py`. It registers
forward hooks on:

- The encoder's `final_norm` output (one per generation, captured once).
- The encoder's `pooled_hidden_state` (one per generation).
- The encoder's `cognitive_state` (one per generation).
- The decoder's per-layer output hidden states (each generation step).
- Each `CASNLDecoderLayer.cross_attn` attention weight tensor (each step).
- The decoder's `nl_lm_head` output logits (each step).
- The `PrerequisiteGateLayer` satisfaction tensor in each decoder layer
  (each step).
- The active `RegisterLatent.compute_gamma_beta_d()` for the current step.

Hooks are torn down on every code path including exception (mirroring
`live_capture.capture_live_trace`'s try/finally pattern).

### `GenerationTrace` JSON schema

```json
{
  "schema_version": "generation_trace.v1",
  "encoder_state": {
    "input_text": "How should I tell my brother our father is dying?",
    "pooled_hidden_state_l2_norm": 12.34,
    "cognitive_state_top_k": [
      [33, 0.412, "P3"],
      [13, 0.187, "C3"],
      [22, 0.143, "E2"]
    ],
    "structured_prediction": {
      "turn_type": "ANSWER",
      "expression_family": "register_state",
      "transition_kind": "state",
      "noetic": 3,
      "domain": "P",
      "drive": "F4",
      "registers": ["A", "f", "T"],
      "register_mode": "co_presence",
      "authority": "admitted",
      "has_omega": false,
      "has_meta_logic": false
    },
    "cas_expression": "^3^P|⟨A,f,T⟩",
    "rpm_satisfaction": 0.84,
    "inversion_flags": {
      "N": 0.04, "W": 0.07, "F": 0.12, "E": 0.09,
      "S": 0.05, "A": 0.03, "P": 0.06
    },
    "topos_truth_values": [[0.9, 0.05, 0.05], ...],
    "lacunarity_scores": [...]
  },
  "soft_prefix": {
    "vector_l2_norms": [4.2, 3.8, 4.1, 4.0],
    "projection_top_k": [
      {"slot": 0, "top_dims": [[12, 0.21], [44, 0.17], [3, 0.13]]},
      {"slot": 1, "top_dims": [...]},
      {"slot": 2, "top_dims": [...]},
      {"slot": 3, "top_dims": [...]}
    ]
  },
  "tokens": [
    {
      "step": 0,
      "token_id": 17263,
      "token_str": "I",
      "token_source": "english_bpe",
      "logit": 8.42,
      "logit_topk": [[17263, 8.42], [3201, 7.89], [9012, 6.11]],
      "softmax_prob": 0.62,
      "decoder_layer_acts": [
        {"layer": 0, "l2_norm": 11.2, "max_abs": 4.3},
        {"layer": 1, "l2_norm": 12.1, "max_abs": 4.7},
        ...
      ],
      "cross_attn_to_encoder_seq": {
        "entropy": 1.42,
        "top_attended_positions": [[3, 0.31], [7, 0.18], [0, 0.12]]
      },
      "cross_attn_to_cas_slots": {
        "entropy": 0.91,
        "top_attended_slots": [
          [3, 0.41, "P3"],
          [13, 0.22, "C3"],
          [33, 0.14, "O3"]
        ]
      },
      "rpm_satisfaction_per_layer": [0.81, 0.83, 0.79, 0.85, 0.84, 0.86],
      "register_film_active": ["A", "f", "T"],
      "bottleneck_attribution_top_k": [
        [44, 0.092],
        [12, -0.071],
        [3, 0.058]
      ],
      "cas_grounding_score": 0.73,
      "nearest_neighbor_training_pair": {
        "pair_id": "sdg_42175",
        "embedding_distance": 0.23,
        "cas_state": "^3^P|⟨A,f,T⟩",
        "english_reply_preview": "I'd say it as plainly as you can..."
      }
    },
    {"step": 1, "token_id": 437, "token_str": " 'd", ...},
    ...
  ],
  "summary": {
    "total_tokens": 47,
    "mean_cas_grounding_score": 0.71,
    "min_cas_grounding_score": 0.42,
    "max_cas_grounding_score": 0.91,
    "rpm_violation_count": 0,
    "register_film_consistent": true,
    "structured_prediction_consistent_across_steps": true,
    "nearest_neighbor_distinct_pairs": 3,
    "generation_time_ms": 412.7
  },
  "diagnostics": [],
  "timing": {
    "encoder_ms": 14.2,
    "decoder_total_ms": 398.5,
    "decoder_per_token_avg_ms": 8.5,
    "trace_overhead_ms": 23.1
  }
}
```

### Field semantics

- **`token_source`** — one of `"reserved_cas"`, `"reserved_special"`,
  `"english_bpe"`. Lets downstream tooling distinguish CAS-prefix tokens
  from body tokens from punctuation/special tokens.
- **`cas_grounding_score`** — a [0, 1] scalar measuring how much of the
  decoder layer's cross-attention mass at this step landed on the 40 CAS
  slot states (vs. on the encoder's raw token positions). High score = the
  decoder is actively conditioning on CAS slots; low score = the decoder
  is "talking on its own" at this step. Computed as
  `slot_attn_mass / (slot_attn_mass + token_attn_mass)`, averaged over
  decoder layers and heads.
- **`nearest_neighbor_training_pair`** — at trace time, the pooled hidden
  state of the current generation is compared against a precomputed FAISS
  index of the SDG training pairs' pooled hidden states. The closest pair
  by L2 distance is recorded. **This is Mode 7 Network Attribution
  extended to the generation path** — every token can be walked back to
  its nearest training-data ancestor.
- **`bottleneck_attribution_top_k`** — gradient × input attribution from
  the current token's argmax logit back to the soft-prefix (Channel B).
  Top-K dimensions of the 4 × d_model soft-prefix bank by |grad × input|.
  Computed on demand (the trace defaults to one backward pass per
  generation, on the most recently emitted token; full-sequence
  attribution available behind `with_per_token_attribution=True` flag at
  proportional cost).

### Default and opt-in modes

```python
generate(
    user_text: str,
    *,
    with_trace: bool = False,
    trace_mode: Literal["minimal", "full", "attribution"] = "minimal",
    with_per_token_attribution: bool = False,
    nearest_neighbor_top_k: int = 1,
) -> GenerationResult | tuple[GenerationResult, GenerationTrace]:
```

- `with_trace=False` (default): no hooks, no overhead. Inference identical
  to a hookless decoder.
- `with_trace=True, trace_mode="minimal"`: encoder state + per-token
  argmax/logit_topk/cross_attn entropies. No layer activations, no
  attribution. ~5% overhead.
- `with_trace=True, trace_mode="full"`: above + per-layer activations and
  cross-attention top positions. ~15-20% overhead.
- `with_trace=True, trace_mode="attribution"` (full + per-token grad×input):
  ~50-100% overhead. Reserved for the Exposure Button "deep trace" panel.

This matches the existing `live_capture.capture_live_trace` discipline of
hooks-on-demand, hooks-always-cleaned-up.

---

## §8. Training data requirements

### Coverage axes

The SDG corpus must cover the full Cartesian product of CAS axes used by the
decoder, plus all combinatorial expressions in the grammar:

```
Singletons:
  10 Noetics × 4 Domains × 7 Drives × 4 Registers
                                = 1,120 atomic expression cells

Compounds:
  ^n^D ∈ State (40 cells)
  ^n^D|R ∈ register_state (160 cells)
  ^n^D|⟨R1,R2⟩ ∈ set_spec (~1,200 cells over reasonable register subsets)
  (^n^D|R1 + ^n^D|R2) ∈ co_presence
  (^n^D|R1 × ^n^D|R2) = ^n^D|Ω ∈ integration (Rule 4 fusion)

Recipe expressions (v7.6 production semantics):
  Θ(Ω) = a₁·X₁ + a₂·X₂ + ... → Ω
  Coverage: at least one recipe per outcome family in the SDG plan
  (the parallel SDG agent's plan governs final counts)

Meta-logic expressions:
  Set/MetaSet/NoeticSet/StateCluster/RelationSet
  Membership/Subset/Product/Cover/Partition/Pullback
  Authority (admitted/blocked)

Anti-drift cases:
  ^3 visceral vs ^6 analytical critique pairs
  ^8 associative-trigger vs ^6+^9 deductive-causal pairs
  ^4 etymological-cognate verification cases

Inversion-bearing cases:
  Pairs where the input English would look fluent but trip an inversion
  axis. Decoder must learn to either (a) flag-and-reframe, or (b) emit
  refusal language matching the encoder's authority="blocked" output.
```

### Quantity

- **Floor (smoke + Phase 1):** 50K paired examples. Sufficient to stand up
  the training loop, validate joint loss balance, and ship a v0 demo.
- **Target (Phase 2 fluency):** 200K-500K paired examples. From-scratch
  decoder fluency requires this floor (see §10).
- **Stretch (Phase 3 robustness):** 1M paired examples. Probably overkill
  for a domain-constrained chat decoder but available headroom.

The parallel SDG agent's plan is authoritative on the actual SDG generation
schedule. This spec defers quantity allocation across waves to that agent's
output. **Contract**: SDG hands this agent (CAS, English) JSONL pairs in the
schema:

```json
{
  "id": "sdg_42175",
  "cas_state": "^3^P|⟨A,f,T⟩",
  "structured_prediction": {
    "turn_type": "ANSWER", "noetic": 3, "domain": "P", "drive": "F4",
    "registers": ["A","f","T"], "register_mode": "set_spec", ...
  },
  "user_prompt": "How should I tell my brother our father is dying?",
  "english_reply": "I'd say it as plainly as you can...",
  "compiler_validated": true,
  "anti_drift_class": "control",
  "wave": "phase1_seed"
}
```

---

## §9. Eval metrics

In priority order (highest first — if you have to drop one, drop from the
bottom):

### 1. CAS-grounding rate (PRIMARY metric)

For each generated reply, `mean_cas_grounding_score` from the trace must
exceed 0.5. Threshold and target:

- **Threshold**: ≥ 0.4 mean per reply (below this, generation is "talking
  on its own" — drift signal).
- **Target**: ≥ 0.55 mean per reply at v0; ≥ 0.65 at v1.

This is the only metric that distinguishes "decoder grounded in CAS state"
from "decoder hallucinating fluent text alongside an unused CAS state."

### 2. Structured-head exact match (REGRESSION metric)

Per §6 anti-degradation guard, K=9 baseline canonical exact must remain
≥ 91% (-2pp from 93.2% baseline). This is a hard gate, not a soft target.

### 3. Fluency — perplexity on held-out SDG English replies

Lower is better. For a from-scratch 100M-class decoder trained on 200-500K
pairs, expect per-token perplexity in the 8–20 range on in-domain text.
Track but do not gate; use as direction signal.

### 4. Diversity — distinct-2 / distinct-3 across generations

For each (CAS, prompt) the model generates 5 sampled completions. Compute
distinct-2 and distinct-3 over the union. Target distinct-2 ≥ 0.55,
distinct-3 ≥ 0.75. Below these, the decoder is collapsing into templates.

### 5. Traceability sanity (BINARY gate)

Every generated reply must produce a complete `GenerationTrace` with all
required fields populated (no `null`/missing keys for required fields, no
hooks-failed diagnostics, all 6 decoder layers represented, all token
records present). 100% pass rate or the build fails.

### 6. Authority/refusal correctness

When `structured_prediction.authority == "blocked"`, the decoder must emit
a refusal-pattern reply (matched by an existing refusal classifier or by
the rule-based check in `cas_native.dst.dialog_grammar`). False-positive
rate (decoder emits non-refusal when authority is "blocked") must be < 2%.

### 7. RPM-violation rate

Over the eval set, `summary.rpm_violation_count` mean must be ≤ 0.5 per
reply. Spikes here mean the decoder is bypassing the encoder's RPM gate.

### 8. Anti-drift slice eval

Eval set includes the anti-drift pairs from CLAUDE.md (^3 vs ^6, ^8 vs
^6+^9). Decoder must produce English that, when re-tokenized and fed
through the encoder, scores within 0.05 of the original encoder output on
the relevant axis. This is the "consistency under the model's own gaze"
test.

### Eval implementation file

`cas-native/evaluation/native_nl_generation_eval.py` (new). Mirrors the
structure of `cas-native/inference/eval_semantic_reranker_on_heldout.py`.

---

## §10. From-scratch fluency analysis

### The honest assessment

A 100M-class decoder trained on 100K-500K paired examples will produce
fluent English **in a constrained domain** (chat about CAS-classifiable
situations) but **will not produce open-domain fluent English**. This is
acceptable for the product surface (chat assistant grounded in CAS) and
is consistent with the user-ratified Version B plan.

### Quantitative grounding

The Chinchilla scaling law (Hoffmann et al. 2022) puts compute-optimal
training tokens at ≈20× model parameters. For a 100M decoder, that is
≈2B training tokens. At a mean reply length of 50 tokens, 2B tokens
requires 40M paired examples — well beyond the SDG plan.

**However**, Chinchilla optimality is for open-domain pre-training. A
domain-constrained chat decoder over a small-vocabulary (32K) corpus is
under-served by Chinchilla scaling — the relevant comparison is
small-domain dialog systems, where 100K-1M dialog turns historically
suffice for fluent in-domain generation (compare Persona-Chat, MultiWOZ,
TopicalChat — all between 100K and 1M dialog turns, all producing fluent
English at 50-150M parameters from scratch).

### Mitigation if fluency is poor at v0

If 100K-200K paired examples produce stilted output:

1. **Scale SDG to 500K-1M.** Cheapest lever; CPU-bound; runs in parallel
   with training (per the durable parallelize-SDG-with-training memory).
2. **Add a CAS-themed corpus pretraining stage.** Generate 5M-20M tokens
   of CAS-themed monologue (no paired structured prediction) using the
   existing template generator + SDG infrastructure. Train decoder on
   pure LM objective for 1-2 epochs before joint training. Stays within
   the no-foreign-models constraint.
3. **Curriculum from short to long replies.** Phase 1 trains on replies
   of length ≤ 32 tokens; Phase 2 ≤ 64; Phase 3 ≤ 128. Gives the decoder
   a stable short-form fluency baseline before stretching.
4. **In-domain register and turn-type oversampling.** Heavy oversampling
   of ANSWER and MIRROR turns (which are the demoable surfaces) at
   expense of ACK/CLOSE/OPEN where templates already cover well.

### What is NOT a path

- Pretraining on a foreign corpus that requires foreign tokenizer ID
  alignment — that is a hidden form of foreign-model dependence and is
  forbidden by Constraint 1.
- Bolting CAS conditioning onto a frozen foreign decoder — same issue.
- Distillation from Claude/GPT-4 outputs as substitute for SDG —
  distillation from a foreign model is allowed *only* through the
  documented SDG path where the foreign model is the data oracle and not
  a runtime dependency. The runtime decoder is fully native.

### Verdict

100K-200K is a **starting** floor. 500K is the realistic Phase 2 target.
1M+ is the path to fully fluent open-domain chat. The decoder will work
at every level; quality scales with data. The user-ratified 4-8 weeks of
training and $200-500 of compute is consistent with reaching the 200K-500K
floor on an A6000-class pod.

---

## §11. Implementation file map

The implementation agent creates / modifies the following files. **All paths
are relative to** `noetic-compass-scaffold/noetic-compass/`.

### New files

| Path | Purpose |
|---|---|
| `cas-native/model/nl_generation_head.py` | `CASNLDecoderLayer`, `CASNLGenerationHead`, `NLGenerationConfig`. Full decoder stack. |
| `cas-native/training/train_native_nl_gen.py` | Joint training script. CLI flags `--limit 100000` (NOT 128 — guard against the recurring eval-file-slip / limit-default trap). Joint loss with curriculum on β. |
| `cas-native/evaluation/native_nl_generation_eval.py` | The 8-metric eval harness from §9. Reports per-metric scores + the binary trace-sanity gate. |
| `cas-native/trace/generation_trace.py` | `GenerationTrace`, `capture_generation_trace`. Extends `live_capture.py` patterns. Hooks always cleaned up. |
| `cas-native/training/english_bpe_extension.py` | English BPE training procedure from §5. Trains BPE on SDG English, merges into `HybridCASTokenizer`. Persists merged vocab to JSON. |
| `cas-native/inference/native_nl_generate.py` | The user-facing generation entry point. `generate(user_text, *, with_trace=False, trace_mode="minimal", ...) -> GenerationResult`. |
| `cas-native/tests/test_nl_generation_head.py` | Decoder layer + full generation forward/backward; soft-prefix shape; cross-attention slot mask; register FiLM consistency; RPM gate plumbing. |
| `cas-native/tests/test_generation_trace.py` | Trace capture, hook cleanup on exception, JSON schema round-trip, attribution top-K determinism, NN-pair lookup, all 8 §9 metric gates. |
| `cas-native/tests/test_english_bpe_extension.py` | BPE training reproducibility, reserved-token collision-free, vocab cap enforcement, existing-checkpoint compatibility (load with old IDs, no shifts). |
| `cas-native/tests/test_native_nl_generation_eval.py` | Eval harness regressions: synthetic CAS-grounding rate, structured-head no-regression check, anti-drift slice integrity. |

### Modified files

| Path | Modification |
|---|---|
| `cas-native/model/cas_native_model.py` | Add optional `nl_generation_head: CASNLGenerationHead \| None` attribute. Add `attach_nl_head(head)` method. Forward pass unchanged when head not attached (preserves byte-equivalence with v2 / v7.4 / Wave 7B path). New optional `forward_with_generation(input_ids, ..., max_new_tokens=128)` method that runs encoder + decoder. NEVER touch the existing `forward()` signature or return dict shape. |
| `cas-native/model/__init__.py` | Export `CASNLGenerationHead`, `NLGenerationConfig`, `CASNLDecoderLayer`. |
| `cas-native/trace/__init__.py` | Lazy-export `GenerationTrace`, `capture_generation_trace`. |
| `cas-native/training/tokenizer.py` | Add `extend_with_english_bpe(merge_path, max_total_vocab=32000)` method. NO change to existing token IDs or persisted format other than appended new merges. |
| `cas-native/dst/nl_generation_head.py` | Add a router so the engine can call either the existing template stub OR the new native generation. Default remains the template stub until the native checkpoint is validated; switch flag is env-controlled. |
| `cas-native/inference/chat.py` | Add `/generate` REPL command that calls `native_nl_generate.generate()` with `with_trace=True`, prints reply + brief trace summary. The existing `/sample`, `/raw`, `/help` commands remain. |
| `CHANGELOG.md` | Standard entries per the always-update-CHANGELOG project rule. |

### Files explicitly NOT modified by this agent's plan

`cas-native/model/cas_native_model.py` core forward path (only additive
methods); any existing test; `api/`; `cas-engine/`; `dashboard/`. The
implementation agent owns only the file map above.

---

## §12. Risk register

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| From-scratch fluency at 100K is poor | High | Medium | Scale SDG to 500K (§10 mitigation 1). Add CAS-themed pretraining stage (§10 mitigation 2). Curriculum on reply length (§10 mitigation 3). |
| Joint loss degrades structured head | High | Medium-high | Curriculum on β (§6). Anti-degradation guard at every 1K steps (§6). γ trace-consistency loss explicitly forces the soft-prefix to carry the structured prediction. |
| Trace overhead slows inference | Medium | High | `with_trace=False` default; three trace modes (minimal/full/attribution). Hook cleanup always-on per `live_capture.py` pattern. Trace overhead measured per-mode in eval. |
| Vocab explosion with English BPE | Low | Low | Cap at 16K English merges. 32K total vocab ceiling. Pre-mask reserved-token substrings during BPE training so collisions are impossible. |
| Capacity-stealing across heads (cf. PR #6 graph encoder) | High | Medium | Decoder is mounted on encoder, not parallel to it. Encoder capacity is not stolen — it's reused. New parameters all in decoder + new soft-prefix projection + extended LM head. Watch K=9 canonical exact every 1K steps. |
| Cross-attention to slot states ignored (decoder learns to ignore Channel C) | High | Medium | `cas_grounding_score` metric (§9 #1) explicitly tracks this. RPM-aux loss penalizes decoder choices that violate encoder RPM. Trace-consistency loss penalizes soft-prefix divergence. |
| Register FiLM at d_model in decoder destabilizes encoder's RegisterLatent | Medium | Medium | Use `RegisterLatent.set_scales_frozen(True)` for the first 2K steps of joint training (already the encoder's default warmup). Decoder FiLM consumes the encoder's frozen FiLM during warmup; both unfreeze together. |
| SDG schema mismatch with this spec | Medium | Medium | §8 contract is explicit. Implementation agent validates each SDG batch against the schema at load time and rejects malformed records. |
| Eval-file slip (recurrent: `_v77_relabeled` suffix) | High | High | Eval harness explicitly hardcodes the `_v77_relabeled` suffix as the only accepted pattern. Reject filenames that don't match. Per the durable feedback memory. |
| `--limit 128` default trap (recurrent) | High | High | `train_native_nl_gen.py` REQUIRES `--limit` to be explicitly passed; no default. Per the durable feedback memory. |
| Trace JSON files become enormous on long generations | Medium | Medium | `flat_preview` truncation at 8 dims (per `live_capture.py` convention). `bottleneck_attribution_top_k` at K=3 default. Layer-activation summaries are scalars (l2/mean/max), not raw tensors. |
| Foreign-model creep through indirect dependency | Critical | Low | Pre-merge audit script: `grep -ri 'tinyllama\|llama\|qwen\|mistral\|gpt-2\|bert-base' cas-native/` returns zero matches. CI gate. |

---

## §13. Multi-week roadmap

This is a planning-level schedule, not a contract. Calendar weeks are nominal.

### Week 1: Foundation + tokenizer + decoder skeleton

- **Tokenizer agent** delivers `english_bpe_extension.py`. Train BPE on
  the first 50K SDG examples (whatever is available). Persist merged
  tokenizer JSON. Tests pass.
- **Implementation agent** stands up `nl_generation_head.py` with a
  random-init decoder, no training, no trace. Forward pass through the
  full encoder + decoder stack on a synthetic batch. Shape checks pass.
- **SDG agent** delivers Wave 1: 50K paired examples covering the 1,120
  atomic cells.
- **Smoke run.** Train for 500 steps on the 50K corpus. Curriculum stays
  at β=0 (structured-only) the whole run; verify K=9 baseline does not
  shift more than noise.

### Week 2: Training-loop + first joint loss + trace v0

- Wire up joint loss with curriculum (§6). Run β=0 → 0.05 ramp over
  2K steps to validate the gradient path.
- **Trace agent** delivers `generation_trace.py` v0. Minimal mode only.
  Tests pass.
- First end-to-end demoable: encoder + decoder + minimal trace, 5K-step
  training on 50K corpus. Replies will be stilted; that is expected.
  Confirm the structured-head canonical exact is still ≥ 91%.

### Week 3: SDG scale to 100K-200K + first real training

- SDG agent ships Wave 2: scale to 200K paired examples.
- Real training run: 30K steps, β ramps per §6, K=9 canonical exact
  monitored every 1K steps. Cost: ~1 A6000 day, ≈$30.
- First eval pass with the §9 8-metric harness. CAS-grounding rate is
  the headline. Expect 0.45-0.55 mean per reply at this stage.

### Week 4: Eval iteration + fluency improvements

- If fluency is poor at Week 3 eval, deploy §10 mitigations: SDG to 500K
  (run in parallel during this week — CPU-bound), CAS-themed
  pretraining stage (1-2 days of A6000), reply-length curriculum.
- Re-eval. Target CAS-grounding rate ≥ 0.55, perplexity ≤ 15, distinct-2
  ≥ 0.55.

### Week 5: Trace surface complete + Mode 7 hookup

- Trace agent delivers `full` and `attribution` modes. Nearest-neighbor
  FAISS index built over all 200K-500K SDG pooled hidden states.
- `/generate` REPL command lands in `chat.py` with full trace plumbing.
- Mode 7 dashboard panel renders the `GenerationTrace` JSON.

### Week 6: Demoable v0 + dashboard integration

- End-to-end demo: user types in chat, sees fluent English back, clicks
  Exposure Button, sees full per-token trace including nearest-neighbor
  training pair and CAS-grounding score per token.
- Performance pass: minimal trace mode adds < 10% overhead. Generation
  latency p50 ≤ 800ms for a 50-token reply on A6000.

### Week 7: Hardening + edge cases

- Refusal correctness eval. Anti-drift slice eval. Inversion-bearing
  case eval. Fix any failures.
- RPM-aux loss tuning. Trace-consistency loss tuning. β-curriculum
  tuning if any axis is dragging another down.

### Week 8: Production-track decision point

- Final eval pass. If all §9 metrics pass and CAS-grounding rate ≥ 0.65,
  promote checkpoint to "Native NL v0" and replace the templated
  `cas-native/dst/nl_generation_head.py` default behind a feature flag.
- If fluency is still insufficient, commit to Phase 3 (1M SDG, longer
  pretraining, possibly d_model bump to 768 / decoder layers to 8).
  This is a Week 9-12 extension and is the user's call.

---

## §14. Open questions for user

These need explicit user decision before the implementation agent starts code.
The orchestrator should surface these.

1. **Tokenizer ID stability across existing checkpoints.** This spec assumes
   existing reserved CAS token IDs are preserved when English BPE is appended.
   Do you confirm the K=9 baseline and v1 Full Stack checkpoints should
   continue to load against the extended tokenizer? (Default in this spec: yes.
   Alternative: full retokenization wave, requires re-training every existing
   checkpoint.)
2. **Frozen-encoder vs unfrozen-encoder during NL training.** This spec
   commits to **unfrozen encoder** (per the durable modality-mismatch
   finding). Confirm this is the right call — frozen-encoder would protect
   K=9 canonical exact more aggressively but at the cost of decoder
   conditioning quality.
3. **CAS-themed pretraining stage (Week 4 fluency mitigation).** Is template-
   generated CAS monologue corpus an acceptable bridge between SDG and full
   training, given Constraint 1 (no foreign models)? It does not violate the
   constraint — the corpus is generated by our own templates — but it is a
   form of bootstrap that the user should be explicitly aware of.
4. **Default trace mode in production chat REPL.** This spec defaults to
   `with_trace=False` in `generate()` but the REPL `/generate` command
   defaults to `with_trace=True, trace_mode="minimal"`. Confirm this is the
   right product surface (full trace is opt-in via Exposure Button), or
   should the REPL also default to no-trace and require an explicit flag?
5. **Refusal-pattern enforcement strength when `authority="blocked"`.** Hard
   gate (decoder must emit a refusal token sequence) vs soft signal (decoder
   conditioned on it but free to emit any reply). This spec recommends soft
   signal during training plus hard rule-based check at output gate. Confirm.
6. **Single-vs-three-instance decoder under the dialectic plan.** The
   user-ratified three-instance dialectic architecture (durable memory,
   2026-05-04) wraps this NL head with a 2-instance dialog + 1-instance
   integrator. This spec produces ONE decoder. Two more instances of the
   same decoder (with different register-prior overrides) is the dialectic
   path. Confirm this is the correct sequencing — single decoder lands first,
   dialectic wraps it after Lever 3.
7. **Compute budget reaffirmation.** The user's prior commitment is $200-500
   total compute over 4-8 weeks. This spec is consistent with that; full
   200K-500K training is ~$50-150 of A6000 time. Stretch to 1M Phase 3 is
   $300-600 alone. Confirm $200-500 ceiling, with stretch authorized
   contingent on Week 4 results.

---

## §15. Implementation contract — what each parallel agent owns

This is the spec's commitment to the four other agents. **Read your row.**

| Agent | Owns | Consumes from this spec | Hands back to this spec |
|---|---|---|---|
| Tokenizer agent | `cas-native/training/english_bpe_extension.py`, BPE training procedure | §5 vocabulary plan, reserved-token list | Persisted tokenizer JSON, vocab cap honored |
| SDG agent | `cas-native/data/<sdg_*>.py`, SDG corpus generation | §8 schema, coverage axes, anti-drift cases | Paired (CAS, English) JSONL meeting §8 schema |
| Model implementation agent | `cas-native/model/nl_generation_head.py`, `cas_native_model.py` modifications | §3 decoder, §4 conditioning, §11 file map | Forward pass passes shape and behavior tests |
| Training/eval/trace agent | `train_native_nl_gen.py`, `native_nl_generation_eval.py`, `generation_trace.py` | §6 loss, §7 trace schema, §9 metrics, §13 roadmap | Trained checkpoint passing §9 metrics, trace JSON conforming to §7 |

This spec is the contract surface between the four parallel tracks. Any
divergence between an agent's implementation and this spec must be flagged
back to the orchestrator before code is written.

---

*End of spec.*
