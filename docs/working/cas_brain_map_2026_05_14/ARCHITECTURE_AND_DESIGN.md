# CAS Brain Map — Architecture & Design

Date: 2026-05-14
Branch: `codex/mode7-neural-activity-map`
Status: v1 spec (Agent B deliverable; Agent A builds the Three.js renderer in parallel)

This doc replaces the rejected "cloud blob" `NeuralActivityMap`. It specifies a CAS Brain Map that renders the real CAS-Native model topology as a navigable 3D graph, with mock flow data in v1 and a clear path to real Mode 7 wiring.

---

## 1. Honest framing

The user asked for the new map to be brain-evocative, not anatomical. This section says exactly what that means and exactly what it does not mean.

**What the CAS Brain Map IS:**

- A 3D navigable graph of the actual CAS-Native model topology. Every node is a real PyTorch module (a real layer or sub-layer) defined in the model files cited in Section 2 below.
- A traceability surface in the spirit of Mode 7 mechanistic attribution: when an input flows through the model and produces an output, the path through the layers is the mechanistic story of how that output was produced.
- A pedagogical and explanatory layer: hover/click reveals what the layer does in plain English.

**What the CAS Brain Map is NOT:**

- A claim about biological brain anatomy. No node corresponds to a cortical region, lobe, nucleus, or neural circuit. The visual language borrows from brain imaging (clustered nodes, glowing connections, particle flow) because it reads as alive, but the structural claim is purely about the CAS-Native model graph.
- A model of human cognition. The layout decisions (encoder on the left, decoder on the right, special branches above and below) are visualization affordances, not anatomical mappings.
- A real-time activity feed in v1. The default mode is `MOCK FLOW`. Real Mode 7 stream wiring is follow-up scope (see Section 8 below).

The genuine claim is mechanistic interpretability: this view shows which layers light up when the model processes a particular input. The aesthetic claim is "this should feel alive when you watch it work." Cortex anatomy is not on the table.

---

## 2. Complete layer manifest

Every named module from the three model files, in pipeline order. Each entry cites the source file and line number where the module is defined or instantiated.

### 2.1 Encoder side — `cas-native/model/cas_native_model.py`

| # | Module | Source | Purpose (plain English) | Input shape | Output shape | Pipeline position |
|---|---|---|---|---|---|---|
| 1 | `token_embedding` | `cas_native_model.py:247` (`nn.Embedding(vocab_size, d_model)`) | Turns each input token ID into a dense d_model vector. This is where words become numbers the model can work with. | `(B, S)` int | `(B, S, d_model)` | embedding |
| 2 | `PositionalEncoding` (`pos_encoding`) | `cas_native_model.py:74-94`, instantiated at `:248` | Adds a sinusoidal position signal so the model knows token order. Identical to vanilla Transformer positional encoding. | `(B, S, d_model)` | `(B, S, d_model)` | embedding |
| 3 | `CognitiveStateEmbedding` (`cognitive_embedding`) | `cas_native_model.py:253` (imported from `embedding.py`) | Projects each token's hidden state onto the 40-state CAS open simplex (10 Noetics x 4 Domains). This is the CAS-typed parallel branch that runs alongside the main hidden state. | `(B, S, d_model)` | `(B, S, 40)` | embedding (branch) |
| 4-9 | `CASTransformerLayer` x 6 (`layers[0..5]`) | `cas_native_model.py:97-196`, instantiated at `:256-259` | Six stacked CAS transformer blocks. Each one does the four sub-steps below in order. Six is the default `n_layers`. | `(B, S, d_model)` | `(B, S, d_model)` | encoder stack |
| 4a | `domain_attn` (`DomainDescentAttention`) | `cas_native_model.py:111-114` (instantiated); class in `domain_descent.py` | Attention masked by the P -> C -> E -> O domain descent rule. Higher-precedence domains see lower-precedence ones but not the reverse. This is the structural attention that enforces CAS domain ordering. | `(B, S, d_model)` + cognitive_state `(B, S, 40)` | `(B, S, d_model)` | enc block sub-1 |
| 4b | `fractal_attn` (`FractalAttentionHead`) | `cas_native_model.py:118-123` (instantiated); class in `fractal_attention.py` | Multi-scale attention inspired by iterated function systems. Lets the model attend at several "zoom levels" at once. Useful for fractal-style cognitive sequences (^8 cause -> ^9 effect chains). | `(B, S, d_model)` | `(B, S, d_model)` | enc block sub-2 |
| 4c | `rpm_gate` (`PrerequisiteGateLayer`) | `cas_native_model.py:130-133` (instantiated); class in `rpm_gate.py` | The CAS Recursive Prerequisite Monad gate. Holds activations back until the prerequisites for a downstream cognitive operation are satisfied. The "fail-closed" safety layer. | `(B, S, d_model)` | `(B, S, d_model)` + per-name satisfaction dict | enc block sub-3 |
| 4d | `ffn` | `cas_native_model.py:137-143` | Standard transformer feed-forward (Linear -> GELU -> Linear) with 4x expansion. Where most of the model's parameters live. | `(B, S, d_model)` | `(B, S, d_model)` | enc block sub-4 |
| 10 | `final_norm` | `cas_native_model.py:262` (`nn.LayerNorm`) | Final layer-norm before output heads. Stabilizes the encoder hidden state. | `(B, S, d_model)` | `(B, S, d_model)` | encoder final |

### 2.2 Special branches — `cas_native_model.py`

These attach to the encoder's final hidden state and run alongside the main pipeline, not in series.

| # | Module | Source | Purpose | Input | Output | Pipeline position |
|---|---|---|---|---|---|---|
| 11 | `CognitiveToposReasoner` (`topos_reasoner`) | `cas_native_model.py:266-269` (instantiated); class in `topos_reasoner.py` | Reads pooled hidden state and outputs intuitionistic 3-valued truth values (true / false / undetermined) for `num_ethical_propositions` propositions. The CAS topos reasoning head. | `(B, d_model)` pooled | `(B, num_propositions, 3)` | special branch (above) |
| 12 | `InversionDetector` (`inversion_detector`) | `cas_native_model.py:199-225` (class), `:270` (instantiated) | Scores the 7 CAS inversion axes (N, W, F, E, S, A, P) from the pooled hidden state. Flags when the model is producing inverted / shadow-form cognition. | `(B, d_model)` pooled | `(B, 7)` in [0,1] | special branch (above) |
| 13 | `GenerativeHead` (`generative_head`) | `cas_native_model.py:271` (instantiated); class in `composition.py` | Auxiliary head for generative-composition operations (the v7.7 generative operators). | `(B, d_model)` | head-specific | special branch (above) |
| 14 | `LacunarityGate` (`lacunarity_gate`) | `cas_native_model.py:272` | Self-correction gate that detects over-concentrated activation on the 40-state simplex and rebalances it. Catches "spotlight bias" failure modes. | `(B, S, 40)` | corrected `(B, S, 40)` + scores | special branch (below) |
| 15 | `LacunarityHead` (`lacunarity_head`) | `cas_native_model.py:273` | Metacognitive head reporting how lacunar (gap-ridden) the activation pattern is. | `(B, S, d_model)` | meta-scores | special branch (below) |

Optional v2 components attached at runtime via `attach_*` methods:

- `expression_proposer` (`ExpressionProposerHead`) — attached at `cas_native_model.py:308-319`; consumes pre-final-norm hidden states; output: proposer outputs dict. Visualized as an optional special branch (above).
- `register_embedding` (`CognitiveStateEmbeddingWithRegister`) — v2 register-FiLM path; modulates the 40-state logits when register activations are passed (`:335-396`). Visualized as a special branch (below) tying into the cognitive embedding.

### 2.3 Decoder side — `cas-native/model/nl_generation_head.py`

The NL generation head is a 6-layer decoder. It is attached to the main model via `attach_nl_gen_head` (`cas_native_model.py:647-655`) and consumes the encoder's pooled hidden state plus the encoder outputs.

| # | Module | Source | Purpose | Input | Output | Pipeline position |
|---|---|---|---|---|---|---|
| 16 | `token_embedding` (decoder) | `nl_generation_head.py:323` | Decoder-side token embedding. Independent from encoder embedding so the decoder owns its own English vocab projection. | `(B, L)` int | `(B, L, d_model)` | decoder embedding |
| 17 | `pos_embedding` | `nl_generation_head.py:324` (`nn.Embedding(max_len, d_model)`) | Learned positional embeddings for the decoder. Note: learned, not sinusoidal — different from encoder. | `(B, L)` int | `(B, L, d_model)` | decoder embedding |
| 18 | `soft_prefix_proj` | `nl_generation_head.py:329-332` | Projects the 64-dim CAS bottleneck `z` into 4 learned "soft prefix" positions of `d_model`. The continuous CAS conditioning that prepends to the decoder. | `(B, 64)` | `(B, 4, d_model)` | decoder conditioning |
| 19-24 | `_NLDecoderLayer` x 6 (`layers[0..5]`) | `nl_generation_head.py:199-291` (class), `:335-337` (instantiated) | Six stacked decoder blocks. Each does masked self-attn, then cross-attn to the encoder+soft-prefix KV stream, then FFN. | `(B, L, d_model)` | `(B, L, d_model)` | decoder stack |
| 19a | `self_attn` | `nl_generation_head.py:221-226` (`nn.MultiheadAttention`) | Causally-masked self-attention over the decoder stream `[CAS prefix | decoder tokens]`. Standard transformer decoder self-attn. | `(B, L_dec, d_model)` | `(B, L_dec, d_model)` | dec block sub-1 |
| 19b | `cross_attn` | `nl_generation_head.py:229-234` | Cross-attention from the decoder to the encoder outputs concatenated with the soft prefix. With optional domain-mask gating on the encoder side. | `(B, L_dec, d_model)` Q; `(B, S_total, d_model)` KV | `(B, L_dec, d_model)` | dec block sub-2 |
| 19c | `ffn` (decoder FFN) | `nl_generation_head.py:237-243` | Standard transformer FFN, ffn_dim=2048 by default. | `(B, L_dec, d_model)` | `(B, L_dec, d_model)` | dec block sub-3 |
| 25 | `final_norm` (decoder) | `nl_generation_head.py:338` | Final layer-norm before LM head. | `(B, L, d_model)` | `(B, L, d_model)` | decoder final |
| 26 | `register_film` (`RegisterFiLM`) | `nl_generation_head.py:345-348` (instantiated); class in `register_film.py` | Multiplicative FiLM modulation by Phenomenological Register (T / A / f / E) applied to the post-decoder hidden state. Steers the same content into different operational characters. | `(B, L, d_model)` + register_id | modulated `(B, L, d_model)` | decoder side-modulation (special) |
| 27 | `lm_head` (output) | `nl_generation_head.py:342` | Linear projection from `d_model` to vocab_size. Produces the final English LM logits. Random-init, NOT tied to embedding. | `(B, L, d_model)` | `(B, L, vocab_size)` | output |

### 2.4 Typed Fiber Decoder side branch — `cas-native/model/typed_fiber_decoder.py`

This is the parallel structured-prediction decoder used for CAS-formal output (the path that emits compiler-valid CAS rather than English). In the brain map it lives as a side branch parallel to `NLGenerationHead`.

| # | Module | Source | Purpose | Input | Output | Pipeline position |
|---|---|---|---|---|---|---|
| 28 | `simplex_proj` | `typed_fiber_decoder.py:237` | Projects the 40-dim simplex trajectory up to `d_model` so it can be used as cross-attention keys/values. | `(B, L_src, 40)` | `(B, L_src, d_model)` | TFD conditioning |
| 29 | `src_token_proj` | `typed_fiber_decoder.py:242` | Projects encoder source hidden state for the pointer-copy cross-attention stream. | `(B, L_src, d_model)` | `(B, L_src, d_model)` | TFD conditioning |
| 30 | `_DecoderBlock` x 6 | `typed_fiber_decoder.py:164-197` (class), `:244-248` (instantiated) | Six decoder blocks. Each does: self-attn -> cross-attn to simplex stream -> cross-attn to source stream -> FFN. Only the final block exposes copy scores for pointer-copy. | `(B, L_out, d_model)` | `(B, L_out, d_model)` | TFD stack |
| 31 | `slot_type_head` | `typed_fiber_decoder.py:262` | 9-way head classifying the slot type at each output position (CONNECTIVE / OMEGA / STAGE_VAR / COEFFICIENT / REGISTER_LETTER / DOMAIN_LETTER / DRIVE_LETTER / FRACTAL_K_LITERAL / NOETIC_PHRASE). | `(B, L_out, d_model)` | `(B, L_out, 9)` | TFD output |
| 32 | `phrase_bias_table` + `phrase_bias_proj` | `typed_fiber_decoder.py:266-271` | Soft simplex-conditioned phrase bias for NOETIC_PHRASE positions. Pools the simplex trajectory to a top noetic `k*` and emits a phrase-bias term that mixes into the LM logits. | `(B, L_out, d_model)` + simplex | per-vocab bias | TFD output (special) |
| 33 | `lm_head` (TFD) | `typed_fiber_decoder.py:251` | Projects to English BPE vocab. Optionally weight-tied to `token_emb`. | `(B, L_out, d_model)` | `(B, L_out, V_eng)` | TFD output |

### 2.5 Auxiliary heads (Phase C)

Attached at runtime via `attach_aux_heads` (`cas_native_model.py:658-671`). The aux head module wraps four sub-heads (`H_card`, `H_pos`, `H_stop`, `H_cluster`). In the brain map these are visualized as a single special-branch node (since they share the aux_heads module) attached to the decoder side, with sub-labels in the click panel.

---

## 3. 3D layout strategy

Coordinate convention (right-handed):

- `x` runs left -> right; this is the pipeline axis (input on the left, output on the right).
- `y` runs bottom -> top; this is the dorsal/ventral axis used to float special branches above and below the main pipeline.
- `z` runs near -> far; lightly used for sub-module clustering (the 4 sub-modules of a transformer block sit at small `z` offsets so they read as a tight cluster, not a single point).

Approximate ranges so Agent A can use them directly:

| Region | x range | y range | z range | Notes |
|---|---|---|---|---|
| Embedding column | -22 to -16 | -1 to +3 | 0 | 3 nodes stacked vertically: token_embedding (top), cognitive_state_embedding (middle), positional_encoding (bottom) |
| Encoder transformer stack | -14 to +4 | -1 to +1 | -1 to +1 | 6 blocks across `x`, each block is a 4-node cluster at small `z` offsets |
| Encoder final norm | +5 | 0 | 0 | Single node at the right end of encoder column |
| Decoder transformer stack | +8 to +20 | -1 to +1 | -1 to +1 | 6 blocks across `x`, each block is a 3-node cluster (self_attn, cross_attn, ffn) |
| Decoder final norm | +21 | 0 | 0 | Single node before lm_head |
| Output (lm_head) | +24 | 0 | 0 | Large, gold; the "single big node on the far right" |
| Special branches ABOVE | -14 to +20 | +4 to +7 | 0 | Topos Reasoner, Inversion Detector, Expression Proposer, RegisterFiLM (decoder-side modulation) |
| Special branches BELOW | -14 to +20 | -7 to -4 | 0 | Lacunarity Gate, Lacunarity Head, Typed Fiber Decoder column (parallel) |
| Embedding-stage branch (cognitive_state_embedding) | -18 | +1.5 | 0 | Floats slightly up from token_embedding, paired with positional_encoding |
| Encoder block sub-clusters | block_x +/- 0.6 in x; +/- 0.5 in y; 0 to +0.7 in z | | | domain_attn (top-front), fractal_attn (top-back), prereq_gate (bottom-front), ffn (bottom-back) |
| Decoder block sub-clusters | block_x +/- 0.5 in x; +/- 0.5 in y; 0 to +0.5 in z | | | self_attn (top), cross_attn (middle), ffn (bottom) |

Spacing: encoder block centers at x = -13, -10, -7, -4, -1, +2 (delta = 3 between blocks). Decoder block centers at x = +9, +12, +15, +18, +21 — wait, that is 5 blocks; with 6 blocks use x = +9, +11.5, +14, +16.5, +19, +21.5 (delta = 2.5). Output node sits at x = +24.

Curved connection lines (Bezier or quadratic curves) for:

- RegisterFiLM connecting to all 6 decoder blocks (one source, six targets).
- Cognitive State Embedding connecting to each encoder block (it is recomputed inside the encoder loop, so the conceptual edge points from the embedding into every block).
- Topos Reasoner / Inversion Detector / Aux Heads connecting back from above into the encoder final norm and decoder hidden state.
- Lacunarity Gate connecting from below into the encoder output (the cognitive state pathway).
- Typed Fiber Decoder column connecting from below into the encoder final norm (parallel path to NL decoder).

Straight lines for all in-column adjacent edges (block N -> block N+1, sub-module 1 -> sub-module 2 within a block).

---

## 4. Color palette

Eight families, each with one canonical hex. Distinct enough to read at a glance, harmonious enough to sit together. Chosen from the tailwind/shadcn spectrum the rest of the dashboard already uses.

| Family | Hex | What it labels |
|---|---|---|
| `embedding` | `#60a5fa` (blue-400) | Token embedding, cognitive state embedding, positional encoding |
| `encoder_attn` | `#a78bfa` (violet-400) | Encoder domain_attn and fractal_attn (both inside each encoder block) |
| `encoder_gate` | `#fbbf24` (amber-400) | Encoder PrerequisiteGate (RPM) — flagged distinctively because the gate is load-bearing for CAS safety |
| `encoder_ffn` | `#2dd4bf` (teal-400) | Encoder FFN and encoder final_norm |
| `special_branch` | `#cbd5e1` (slate-300, silver) | Topos Reasoner, Inversion Detector, Lacunarity Gate/Head, Expression Proposer, RegisterFiLM, Typed Fiber Decoder column, Aux Heads |
| `decoder_attn` | `#fb7185` (rose-400) | Decoder self_attn and cross_attn |
| `decoder_ffn` | `#34d399` (emerald-400) | Decoder FFN and decoder final_norm |
| `decoder_head` + `output` | `#f59e0b` (amber-500, darker) | LM head and the final output node. Distinct from encoder_gate `#fbbf24` (lighter amber-400) by lightness — pairs naturally as "gate yellow" vs "output gold." |

Note: `encoder_gate` and `decoder_head` are both in the amber family on purpose — gates and outputs share a "this is where it commits" semantic — but they are different lightnesses so they read as distinct.

---

## 5. Animation strategy

Particles flow along edges in the direction of pipeline flow. Each "flow" is a sequence of pulses through the graph following a particular input's path.

Per-flow loop:

1. A particle spawns at the input side (token_embedding or cognitive_state_embedding depending on the flow).
2. The particle travels along the edge to the first encoder block in ~80-120 ms.
3. When the particle reaches a node, the node's halo brightens for ~200 ms (the "pulse"). The halo color matches the node's family color but at higher intensity.
4. The particle continues to the next layer in pipeline order. Sub-modules within a block are visited in the order `domain_attn -> fractal_attn -> prereq_gate -> ffn` for encoder blocks, and `self_attn -> cross_attn -> ffn` for decoder blocks.
5. Significant-point markers appear next to the layer that triggered them. A marker is a short text label such as `Noetic locked: ^8` floating ~0.6 units in `+y` from the node. It fades in over 100 ms, holds for ~600 ms, fades out over 100 ms (total dwell ~800 ms).
6. Special-branch nodes pulse when the flow reaches its attachment point on the main pipeline — for example, when the encoder final_norm pulses, the Inversion Detector pulses ~50 ms later (representing the parallel branch firing on the same data).
7. The full flow completes in ~4000 ms. After a short pause (~500 ms), the next flow plays.

The default v1 cadence is "auto-cycle through the 5 mock flows" with a small UI to pause / step / replay.

---

## 6. Mock flow generator design

Each mock flow corresponds to a prompt category that exercises a distinct path through the model. Five flow types ship in v1.

### 6.1 `state_lookup` — "what is ^3?"

The model is asked to look up the meaning of a single state literal. Short path: shallow encoder traversal, minimal recipe construction, short decoder emission.

- Encoder traffic: 1-2 blocks light up, mostly the first two.
- The InversionDetector pulses briefly when ^3 is identified (Negative is one of the involution-pair states, so it gets a low-amplitude inversion check).
- Decoder emits a short answer (~6-10 tokens), so the decoder stack pulses 1-2 times.

### 6.2 `recipe` — "walk me through how a decision gets made"

The model constructs a multi-step recipe (v7.6 Theta(Omega) notation). Deep encoder traversal because the recipe assembly is structurally heavy. Multiple PrerequisiteGate pulses (RPM chain checks).

- Encoder traffic: all 6 blocks fire, with the PrerequisiteGate sub-module pulsing 2-3 times per block.
- FractalAttention fires once (recipe construction is a one-shot multi-scale operation, not iterative).
- Decoder emits a longer recipe (~30-50 tokens), so the decoder stack cycles ~3-4 times.

### 6.3 `fractal` — "a thought led to an aversion led to..."

The model traces a fractal cause -> effect chain (^8 -> ^9 -> ^8 -> ^9 pattern). Heavy FractalAttention traffic.

- Encoder traffic: all 6 blocks fire, with FractalAttention pulsing 2x per block (this is the high-traffic flow for the fractal sub-module).
- DomainAttention also fires regularly because the chain crosses domain boundaries.
- Decoder emits a chained narrative (~25-40 tokens).

### 6.4 `inversion` — "compare ^2 and ^3"

The model is asked to compose an involution pair. InversionDetector is the star.

- Encoder traffic: blocks 2-5 fire (the analysis happens mid-stack).
- InversionDetector pulses strongly (3-4x amplitude vs other flows).
- TopOS Reasoner pulses lightly (a compare/contrast involves implicit truth-value reasoning).
- Decoder emits a CO-form composition (^2 vs ^3 framing).

### 6.5 `binary_composition` — "X integrated with Y"

The model performs a v7.7 cross-register integration (X x Y = Omega). Both encoder self-attn and decoder cross-attn fire heavily because the operation is genuinely bilingual (state composition + emission).

- Encoder traffic: all 6 blocks fire evenly.
- Decoder traffic: both self-attn and cross-attn pulse on every decoder block (the cross-attn is the load-bearing operation for "looking back at the encoded operands").
- RegisterFiLM pulses on each decoder block (register-aware emission).

---

## 7. Hover and click info-panel UX

Each layer family has a short hover tooltip (2-3 sentences in plain English) and a longer click-expansion "Why is this important?" panel (~5 sentences).

### 7.1 `embedding`

- **Hover (token_embedding):** "Turns each input token into a dense vector the model can work with. This is the first numerical representation of language inside the model."
- **Click:** "Token embedding is where text becomes math. Every word, punctuation mark, and CAS token has its own vector here, learned from training. The cognitive state embedding next to it does a CAS-typed version of the same job — it projects the same tokens onto the 40-state cognitive simplex so the model has both a free-form representation and a CAS-typed one. Together they form the front door into the model."

### 7.2 `encoder_attn`

- **Hover (domain_attn):** "Attention that respects CAS domain order (Principled before Cognitive before Evaluative before Operational). Higher-precedence domains can see lower-precedence ones but not the reverse."
- **Click:** "Domain Descent Attention is the CAS structural attention. Standard transformer attention lets every token see every other token; this version blocks attention across the CAS domain hierarchy in the wrong direction. The point is to keep Principled-domain reasoning from being driven by Operational-domain noise. Fractal Attention next to it is a multi-scale companion that lets the model attend at several zoom levels at once — useful for cause-effect chains. Together they are the encoder's spatial reasoning."

### 7.3 `encoder_gate`

- **Hover (rpm_gate):** "The CAS Recursive Prerequisite Monad gate. Holds activations back until the prerequisites for a downstream cognitive operation are satisfied."
- **Click:** "The Prerequisite Gate is one of CAS's load-bearing safety layers. Cognitive operations have an order — for example, you cannot do real wisdom-domain work without having done its developmental prerequisites. This gate measures whether the prerequisites are satisfied in the current activation and gates the signal accordingly. If a downstream operation is asked without its prerequisites, the gate fails closed and the activation does not pass. Section-retraction in math terms: prerequisite satisfaction is one-directional."

### 7.4 `encoder_ffn`

- **Hover:** "Standard transformer feed-forward block (Linear -> GELU -> Linear, 4x expansion). Most of the model's parameters live here."
- **Click:** "The feed-forward block is the workhorse of transformer architectures. Each token gets its representation transformed by a wide hidden layer (4x the model dimension), then projected back down. Most of the model's learned knowledge — facts, patterns, associations — is stored in the weights of these FFN blocks. Layer normalization before and after keeps the signal stable across many stacked blocks. There are six of these in the encoder."

### 7.5 `special_branch`

- **Hover (inversion_detector):** "Scores the 7 CAS inversion axes from the encoder's pooled output. Flags when the model is producing inverted or shadow-form cognition."
- **Click:** "The Inversion Detector is CAS's anti-drift watchdog. It takes the pooled encoder representation and outputs a 7-dimensional score, one per inversion axis: Noetic, Domain, Drive, State, Sub-Drive, Pathway, and Compound. High scores mean the model is producing cognition that looks structurally correct on the surface but is inverted underneath — for example, an analytical critique that masquerades as a visceral aversion. This is one of the most important safety surfaces in the architecture."

### 7.6 `decoder_attn`

- **Hover (cross_attn):** "Cross-attention from the decoder to the encoder outputs plus the soft CAS prefix. Where the decoder looks back at the input to decide what to say next."
- **Click:** "Decoder cross-attention is how the model grounds its output in the input. Each decoder position queries the encoder's full output sequence (concatenated with the soft CAS prefix carrying the 64-dim CAS bottleneck), and the attention weights tell us which input tokens the decoder is leaning on for each output token. This is the layer that Mode 7 mechanistic attribution traces most heavily — when you ask 'why did the model say that word?', the answer often lives in the cross-attention weights at this layer."

### 7.7 `decoder_ffn`

- **Hover:** "Standard decoder feed-forward block. Where decoder-side knowledge — vocabulary patterns, style, phrasing — is stored."
- **Click:** "The decoder feed-forward block is the mirror image of the encoder FFN. It transforms each decoder position's representation through a wide hidden layer and projects back down. Most of the model's English generation patterns — collocations, idiomatic phrasing, sentence rhythm — live in the weights here. Combined with the cross-attention layer above, this is where the model decides not just what to say, but how to say it."

### 7.8 `decoder_head` / `output`

- **Hover (lm_head):** "Projects the final decoder hidden state to a probability over the whole vocabulary. The model's last step before picking a token."
- **Click:** "The LM head is the model's emission surface. Every output token is sampled from a distribution this layer produces. The weights are random-init and not tied to the input embedding — that decoupling is deliberate, so the model can learn an emission distribution that is independent of input embedding geometry. Each time you see a token appear in a response, that token was drawn from the distribution this layer produced for its position."

---

## 8. Evidence-label discipline

Four data-source modes. Every rendered flow MUST carry one of these labels, visible in the UI.

| Mode | Meaning | v1 status |
|---|---|---|
| `REAL MODE 7 STREAM` | The flow comes from a live Mode 7 mechanistic attribution stream (SSE from the API). Layer activations and significant points are derived from real attention/gradient signals on a real forward pass. | Follow-up scope. v1 does NOT ship this. |
| `FALLBACK STREAM` | A real model forward pass produced the trace, but the mechanistic-attribution signals were unavailable so the stream is reconstructed from logits/hidden-state norms only. Strictly weaker than `REAL MODE 7 STREAM`. | Follow-up scope. |
| `DERIVED TRACE` | A trace replayed from a saved JSON record on disk (e.g., a `GenerationTrace` from `nl_generation_head.py:GenerationTrace`). Real provenance, deterministic playback. | Follow-up scope. |
| `MOCK FLOW` | Hand-crafted illustrative flow from `cas_brain_mock_flow.ts`. NOT derived from any real model run. v1 default. | v1 default. |

Discipline rules:

1. The mode label is always visible somewhere on screen when the map is rendered (badge in a corner, or a small line under the title).
2. NEVER label as `REAL MODE 7 STREAM` what is `MOCK FLOW`. NEVER label as `DERIVED TRACE` what is `MOCK FLOW`. The user has been burned by overclaim in the past (see MEMORY: "Be direct — separate wired/works/sample-looked-good/gate-passed/prototype/validated"). This rule is enforced in code: Agent A's component must accept a `mode` prop and render the label.
3. v1 ships with the default `mode='MOCK FLOW'` and the only mock-flow set is `cas_brain_mock_flow.ts`. Real Mode 7 wiring is follow-up scope tracked separately.

---

## Appendix — shipped artifact counts

The companion TypeScript fixture in `noetic-compass-scaffold/noetic-compass/dashboard/src/lib/cas_brain_mock_flow.ts` ships:

- 58 layers (3 embedding + 24 encoder sub-modules + 1 encoder_final_norm + 4 special-above + 2 special-below + 3 decoder-embedding + 18 decoder sub-modules + 1 decoder_final_norm + 1 lm_head + 1 output).
- 72 edges (intra-block, inter-block, cognitive-state broadcast to every encoder block, encoder-to-decoder cross-attn fan-out, RegisterFiLM curved-edge fan-out to every decoder block, special-branch curved edges).
- 5 mock flows (state_lookup, recipe, fractal, inversion, binary_composition), each with ~30-40 frames over 4000 ms.

Tests are at `cas_brain_mock_flow.test.ts` alongside the fixture; vitest run is green.

End of doc.
