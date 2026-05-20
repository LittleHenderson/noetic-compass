# Stage 23.B — Atlas Encoder Design Spec

**Status:** `DESIGN_LOCKED_NO_IMPLEMENTATION`
**Subject:** CAS Native (encoder design only — no code, no training, no eval results)
**Date:** 2026-05-20
**Builds on:** Stage 23.A (`STAGE23_ATLAS_SELF_READING_PREREG_20260519.md`), Stage 23.A.2 (`STAGE23_A_2_NOTATION_MAP_EXTENSION_20260519.md`)
**Blocks:** Stage 23.C (implementation), Stage 23.D (training + eval)

## Scope

Stage 23.B is the **design specification** for the encoder that, in a future implementation stage (23.C), will let CAS Native consume its own canonical 2D notation map as input during inference. This document locks the design boundary so 23.C cannot silently expand scope, and so 23.D has a falsifiable target to measure against.

**Stage 23.B ships exactly one artifact: this document.** No code, no tests, no training data, no model. Implementation is deliberately deferred to 23.C, which itself is gated on a stable v0 checkpoint as the ablation floor (per Stage 23.A's sequencing discipline).

## Naming Boundary

Continuing the discipline from Stages 23.A / 23.A.2 / 22:

| Term | Meaning |
|---|---|
| `atlas_encoder` | The neural module designed (not built) in this stage. Consumes positions from `notation_2d_map.py` and produces a d_model-dimensional representation the CAS Native decoder can attend to. |
| `position_embedding` | The component of the encoder that turns a single (x, y, kind) triple into a d_model vector. |
| `trace_graph_input` | The dynamic per-inference-step input shape the encoder consumes — a list of activated atlas positions with optional saliency weights, derived from the thought-tree builder. |
| `integration_point` | The specific decoder layer at which encoder output enters the CAS Native forward pass. |
| `static_layout` | The 157-primitive (x, y, kind) table emitted by `notation_2d_map.all_positions()`. Same every run. |
| `dynamic_atlas_state` | Per-inference-step accumulated thoughts, mapped onto the static layout via the trace-mapping module. |

Speculative or future-tense capabilities (Stage 23.C onward) are named so they cannot be conflated with what this spec locks down.

## Source of Truth

The encoder design is grounded in the canonical layout. Two artifacts are normative:

- `cas-native/atlas/notation_2d_map.py` — Python module. The encoder must consume positions returned by `all_positions()`. Each position is a `Position2D` dataclass with fields `primitive: str`, `kind: PrimitiveKind`, `x: float`, `y: float`. The 16 `PrimitiveKind` values (`noetic`, `domain`, `drive`, `register`, `cognitive_state`, `operation`, `inversion_axis`, `foundation`, `production`, `rpm_pathway`, `set_constructor`, `set_relation`, `set_operation`, `combinator`, `authority_set`, `cardinality_kind`) are the canonical type-tag vocabulary the encoder dispatches on.
- `research/cas_probe/stage23_a_notation_2d_layout_20260519.json` — emitted layout artifact, machine-readable mirror of `canonical_layout_payload()`.

Any divergence between the encoder spec and the live `notation_2d_map.py` resolves in favor of the Python module. If Stage 23.A.3 adds primitives (e.g., the 12 Ω_* emergent registers, currently out of scope), the encoder inherits them automatically; its dispatch over kinds is closed but its dispatch over primitive ids within a kind is open.

## 1. Read Schema

### What the encoder consumes per inference step

The encoder receives an **AtlasReadFrame** — a structured, fixed-shape input describing which atlas positions are currently active and how strongly. One AtlasReadFrame per decoder step (or per N decoder steps if step-frequency is tuned in 23.D).

The frame has three logical components:

1. **Static layout reference.** A pointer to the canonical 157-position table from `all_positions()`. This is the same every step. It is loaded once at model-init time as a fixed lookup table, not re-emitted per step.

2. **Activation vector.** A length-157 vector of activation weights, one per primitive in the static layout. Values are in `[0, 1]`. A zero entry means "this primitive is not currently active." A non-zero entry means "this primitive is currently lit up in the dynamic atlas state, with weight w."

3. **Provenance metadata.** A small set of bookkeeping fields per active primitive: which trace-graph node it came from, its CAS expression context, its step-index of first activation. Used downstream by Stage 23.D's traceability evaluation; the encoder does not consume provenance arithmetically but emits it as a side-channel for audit.

The frame schema is fixed-shape because the static layout is fixed. This avoids dynamic-shape headaches at inference time and lets the encoder pre-compute position embeddings once.

### How the trace graph maps to encoder input

The existing `cas-native/inference/thought_tree.py` builds a JSON-ready node-edge graph from a `cas-explain` report. The mapping from thought-tree nodes to AtlasReadFrame activation entries is the responsibility of a small adapter (to be built in 23.C), not of the encoder itself. The encoder treats AtlasReadFrame as its primitive input and does not parse trace graphs directly.

The adapter rule is straightforward and is locked here so 23.C does not invent it:

- For every thought-tree node carrying a CAS primitive id (e.g., `^3^P`, `F2`, `|A`), look up its `Position2D` via `get_position(primitive_id)`. Set the corresponding entry in the activation vector to the node's saliency weight (default 1.0 if untagged).
- For thought-tree nodes that do not carry a CAS primitive id (e.g., `user_prompt`, `model_generation`, raw English tokens), set no entries. These flow through the standard token stream, not the atlas stream. See §2 ("how to handle un-positioned primitives") below.
- Multiple thought-tree nodes mapping to the same primitive id additively combine, then clamp to `[0, 1]`.

### How dynamic atlas state combines with static positions

The static layout supplies **where** each primitive lives in 2D. The activation vector supplies **whether** it is currently active and **how strongly**. The encoder's job is to fuse the two: turn (static_x, static_y, kind, activation_weight) per primitive into a single d_model representation, then aggregate across active primitives.

This separation is load-bearing. The static positions never change during training or inference, which means their embeddings can be pre-computed and cached. The activation vector is what carries the per-step signal. This also keeps the encoder's parameter count bounded by `O(157 * d_model)` for the lookup, not by trace-graph size.

### Alternative read schemas considered

Three were considered; one was selected.

- **Single primitive lookup per step.** Encoder consumes one (x, y, kind) at a time. Rejected: serializes encoding work, prevents the decoder from attending to relationships among co-active primitives in a single step.
- **Full layout snapshot per step (157-entry tensor every step).** Rejected as a wire protocol but **selected as the in-memory representation**. The wire protocol can compress (delta updates), but the in-memory tensor the decoder cross-attends to is a 157-entry sequence. Fixed shape simplifies attention masking.
- **Delta updates only.** Encoder receives only the changes since the last step. Rejected: complicates the first-step bootstrap, makes attention masking awkward (the decoder would have to maintain its own running atlas state), and gives a measurable but not large memory saving over the 157-entry baseline.

**Selected: full-layout fixed-shape AtlasReadFrame, with activation vector as the dynamic component.** Constant shape, pre-computable static embeddings, clean attention semantics, low engineering risk.

## 2. Position Embedding Dimensionality

### From (x, y) to d_model

Each `Position2D` carries continuous `x` and `y` floats in the range roughly `[-5, 12]` by x and `[-9.5, 5.5]` by y. These must become a d_model-dimensional vector the rest of the model can attend to. Three families were considered.

- **Sinusoidal positional encoding** (transformer-style, fixed function of x, y). Pros: no learned parameters for position, generalizes to unseen coordinates if any are added later. Cons: the canonical CAS layout has structure (involution symmetry, domain precedence layering, foundation-grid alignment) that sinusoidal encoding flattens. A learned scheme can preserve it.
- **Fully learned embedding** (one d_model vector per primitive id, no use of (x, y) at all). Pros: maximum expressiveness; the model can learn whatever geometry it likes. Cons: throws away the carefully constructed 2D geometry the static map encodes. If the spatial relationships in `notation_2d_map.py` carry signal, this discards it.
- **Concat-then-project** (concatenate sinusoidal(x) + sinusoidal(y) + learned_kind_embedding + learned_primitive_id_embedding, then linear-project to d_model). Pros: gives the model access to both the geometry (via sinusoidal x/y) and the identity (via learned id), with the kind tag as a discrete bias.

**Selected: concat-then-project.** The encoder's input vector per primitive is:

```
input = concat([
    sinusoidal_encode(x, dim=d_pos),       # geometric signal
    sinusoidal_encode(y, dim=d_pos),       # geometric signal
    kind_embedding[primitive.kind],         # discrete type tag, dim=d_kind
    id_embedding[primitive_id],             # learned identity, dim=d_id
    activation_weight,                      # scalar, the dynamic per-step signal
])
projected = Linear(input.shape, d_model)(input)
```

with `d_pos = 32`, `d_kind = 16` (16 PrimitiveKind values, each gets a learned vector), `d_id = 64`, plus the scalar activation, yielding a pre-projection vector of dimension `2 * 32 + 16 + 64 + 1 = 145`. The projection to `d_model = 256` (initial recommendation for v0-scale encoder) is a single Linear. These dims are starting points for 23.C, not contractual; the spec locks the **structure** (concat-then-project with all four sources), not the specific dimensions.

The **kind embedding** gets its own stream because the 16 `PrimitiveKind` values carve up the atlas into semantically distinct regions (e.g., the Noetic ring vs. the Foundation grid vs. the RPM chain bottom rows). Giving the model a discrete kind tag lets it route attention by type without having to learn kind boundaries from coordinates alone.

### Handling un-positioned primitives

Some inference-step inputs do not have a CAS primitive id and therefore have no `Position2D`: raw English tokens, user-prompt text, model-generated function words, the `user_prompt` and `model_generation` thought-tree nodes themselves. These flow through the **standard token stream** of CAS Native; they do not enter the atlas encoder at all. The atlas encoder consumes only the AtlasReadFrame, which is keyed exclusively to the 157 primitives in `all_positions()`.

This separation matters: the atlas stream is **typed** and **bounded** (157 slots, fixed kinds). The token stream is **free-form** (vocabulary tokens, English, mixed). They merge at the integration point (§3), not at input.

Sentinel handling: if Stage 23.A.3 adds primitives, they become valid encoder inputs with zero engineering work. If 23.C ever needs to surface a non-positioned concept to the encoder, the correct move is to add it to `notation_2d_map.py` first, then it inherits a position and the encoder picks it up automatically — preserving the source-of-truth discipline.

## 3. CAS-Native Integration Point

The hardest design choice: which layer of CAS Native receives the atlas encoder output. Three alternatives were considered with serious tradeoff analysis.

### Alternative A: Additive at input embedding

Atlas encoder output is summed into the token-embedding tensor at the very bottom of the decoder. Every attention head sees the atlas signal mixed into every token.

- **Pros:** Simplest. No new attention machinery. Smallest parameter overhead. Works with any decoder architecture.
- **Cons:** Atlas information is smeared across every head. Traceability is lost — you cannot tell which heads use the atlas vs. ignore it. Cannot ablate atlas-conditioning without retraining. Couples the atlas signal into all of generation, including parts (function words, English) where it is irrelevant. Worst, it pre-commits the model to using the atlas everywhere, which makes Stage 23.D's eval question ("does atlas-reading help?") un-falsifiable post-hoc.

### Alternative B: Cross-attention head (targeted)

A dedicated cross-attention block where decoder hidden states query the AtlasReadFrame as a separate sequence. Only this block touches the atlas; other heads do not see it. Trainable per-block decision of whether to attend.

- **Pros:** Maximally targeted. Cleanly ablatable: zero out the cross-attention block and you have a no-atlas baseline. Traceability is preserved at the head level — attention weights from this block directly attribute which atlas positions the decoder cared about at each step.
- **Cons:** Adds parameters. Harder to train (a freshly initialized cross-attention block may collapse to no-use without careful warmup). Requires a specific architectural insertion point that may not exist in every CAS Native backbone choice.

### Alternative C: Gated parallel stream

The atlas encoder runs as a parallel stream alongside the main decoder, and a learned gate fuses the two streams at one or more layers. Each fusion point has a sigmoid gate deciding how much atlas vs. token signal to admit.

- **Pros:** Flexible — the model can learn per-layer how much atlas to use. Reasonably ablatable by forcing gates to zero. Preserves separation of concerns: token and atlas streams remain interpretable.
- **Cons:** More parameters than B. Two streams to debug. Gate dynamics introduce a second training-instability surface. Traceability becomes "which layer's gate opened" rather than "which atlas position the head attended to," which is less directly interpretable than cross-attention attribution.

### Recommendation: Alternative B — cross-attention head

The project's durable commitments (per the memory record on **TRACEABILITY** and **"Show your work, or don't ship it"**) make this the only defensible choice. Specifically:

1. **Per-step attribution is required, not optional.** A cross-attention head produces a per-step attention distribution over the 157 atlas positions. That distribution is directly a **per-step grounding trace** — for each decoder step, "the model looked at positions X, Y, Z in the atlas with weights w_x, w_y, w_z." This is the exact shape the Mode 7 / Network Attribution traceability surface needs.

2. **Cleanly ablatable.** Zero out the cross-attention block's output projection and the decoder regresses to the no-atlas baseline. Stage 23.D can compare with-atlas vs. zeroed-atlas on the same checkpoint, giving a clean A/B without retraining. This is what makes the eval criterion (§4) falsifiable.

3. **Bounded blast radius.** A failed atlas signal cannot corrupt the entire decoder — only the cross-attention block's contributions. The token stream's normal generation behavior is preserved as a floor.

4. **Matches the typed/free-form split established in §2.** The atlas is typed and bounded; the token stream is free-form. Two streams with a typed bridge (the cross-attention block) preserves that boundary architecturally. Additive (A) collapses the boundary. Parallel-gated (C) preserves it but is harder to attribute.

5. **The training-difficulty cost is real but acceptable.** It is paid once in Stage 23.C / 23.D and yields a permanent traceability surface. The alternative (additive) is cheaper but yields no attribution — and per the durable record on what's load-bearing, **traceability is the architectural spine, not a feature**.

The integration point is therefore: **one cross-attention block, inserted at decoder layer ⌊L/2⌋ (the middle of the decoder stack), where the query is the decoder's hidden state at that layer and the key/value sequence is the AtlasReadFrame encoded into 157 d_model vectors.** The exact insertion layer index is tunable in 23.C; the spec locks "one cross-attention block, single insertion point, middle-of-stack default."

## 4. Eval Criterion for Stage 23.C

Stage 23.C ships the implementation. Stage 23.D measures whether the implementation works. The criterion below is what 23.D must answer with a number, and which numeric threshold separates "atlas-reading works" from "the encoder is parameter overhead."

### Candidates

1. **Attention-attribution coverage.** For each generated CAS-bearing token, the cross-attention head should put non-trivial weight on the atlas position(s) of the CAS primitive(s) actually emitted. Measure: fraction of correct-emission steps where the top-3 attended atlas positions include the emitted primitive's `Position2D`. Threshold target: ≥ 60% top-3 hit-rate vs. a uniform-attention baseline (≈ 3/157 = 1.9%).

2. **Per-token grounding score.** Defined as the cosine similarity between the encoder's atlas output at step t and the embedding of the primitive emitted at step t, averaged across a held-out eval set. Higher = better grounding. Threshold target: ≥ 0.4 mean cosine on a 1000-example eval, vs. ≤ 0.1 with the cross-attention block zeroed.

3. **Ablation lift on CAS-emit accuracy.** With atlas cross-attention enabled vs. zeroed, measure per-sample CAS expression emit accuracy (exact-match on the canonical primitive ids). Threshold target: ≥ +5 percentage points lift on the 1000-sample held-out eval, with confidence interval excluding zero.

### Primary criterion (selected)

**Ablation lift on per-sample CAS-emit accuracy.** This is the sample-level outcome metric the project's durable record explicitly designates as the only true CAS-Native quality signal. Aggregate stats can lie; per-sample exact-match cannot. It is also the most directly falsifiable: if ablating the atlas cross-attention block does not move accuracy by at least +5pp on the held-out eval, the encoder is not earning its parameters and 23.C is rolled back.

**Falsifiable threshold for Stage 23.C promotion to 23.D:** with-atlas minus zeroed-atlas per-sample CAS-emit accuracy ≥ **+5.0 percentage points**, measured on a 1000-sample held-out eval set drawn from the same SDG distribution as v0 training, with bootstrap 95% CI lower bound > 0. If the lower bound includes 0 or the point estimate is below +5pp, atlas-reading is declared not-supported by evidence and Stage 23.C is reverted. Attention-attribution coverage (candidate 1) and per-token grounding score (candidate 2) become **secondary supporting metrics**, reported but non-gating.

This criterion can fail. That is the point.

## 5. Out-of-Scope Claims (mirrors Stage 22 / 23.A / 23.A.2 discipline)

Stage 23.B does not, and the resulting committed document must not be read as claiming:

- **Stage 23.B ships training code.** It does not. No `train_*.py`, no SDG corpus, no model weights, no gradient step. Implementation is Stage 23.C.

- **Stage 23.B ships an encoder.** It does not. No `atlas_encoder.py`, no `nn.Module`, no PyTorch class definition. Only this design document.

- **The encoder works.** Untrained at this stage. Stage 23.D measures whether it works against the falsifiable criterion in §4. Until then, "atlas-reading helps CAS Native" is a hypothesis, not a finding.

- **The encoder is optimal.** The (x, y) layout in `notation_2d_map.py` was selected for structural correctness (involution symmetry, domain precedence, foundation-grid alignment), not for optimality as an attention prior. Whether it is also a good attention prior is an empirical question Stage 23.D answers.

- **The encoder enumerates primitives.** Stage 23.B does not duplicate the 157-primitive table. That is the job of `notation_2d_map.all_positions()`. If a primitive count is needed, it is read from the module at runtime.

- **CAS Native currently reads its atlas.** It does not. The capability is locked in design here. It is built in 23.C and measured in 23.D.

- **The cross-attention integration point is the only viable architecture.** It is the recommended one. Alternatives A (additive) and C (parallel-gated) are documented and remain available if 23.C empirically demonstrates that B is unworkable for reasons not anticipated here. The spec locks the **default**, not the only-option.

## Sub-Stage Sequencing (updated)

| Sub-stage | Scope | Status / When | Blocker |
|---|---|---|---|
| 23.A | Initial 65-primitive coordinate system | ✓ shipped | — |
| 23.A.2 | 92 additional primitives covering full CAS vocabulary | ✓ shipped | — |
| 23.A.3 (optional) | Enumerate Ω_* group IF canonical names are defined | future | requires canonical Ω_* list from project owners |
| 23.A.1 | Dashboard TypeScript adapter consuming the layout | follow-up | 23.A + 23.A.2 must land |
| **23.B** | **Trace-as-input encoder design spec (this doc)** | **✓ this commit** | — |
| 23.C | Atlas-conditioning during inference — encoder implementation + cross-attention block + AtlasReadFrame adapter | post-v0 implementation | v0 stable checkpoint + 23.B sign-off |
| 23.D | Atlas-conditioned training signal + ablation eval — measurable claim that atlas-reading helps per §4 criterion | after 23.C | 23.C running end-to-end with both with-atlas and zeroed-atlas inference paths |

23.B is **document-only**. It does not block 23.A.1 (dashboard adapter) or 23.A.3 (Ω_* enumeration) — those run on their own tracks. It does block 23.C (which needs the design locked) and transitively 23.D.

## Files in this stage

- `research/cas_probe/STAGE23_B_ATLAS_ENCODER_DESIGN_SPEC_20260520.md` — this document. Sole artifact of 23.B.

No other file is added, modified, or deleted by Stage 23.B. In particular, `cas-native/atlas/notation_2d_map.py` is **not** modified by 23.B — it remains the source of truth, and any extension to it (e.g., a hypothetical 23.A.3) is a separate stage with its own preregistration.

## Connection to Stage 22 / 23.A / 23.A.2 discipline

The same pattern as the preceding stages applies:

- Lock the design boundary first.
- Name what is measured vs. not measured (here: 23.B claims nothing measurable; 23.D will, against the criterion in §4).
- Defer speculative work explicitly (23.C implementation, 23.D eval).
- Do not let the spec silently expand into implementation.
- Pick one recommendation among genuine alternatives, with reasoning grounded in the project's durable commitments (TRACEABILITY, sample-level outcomes, "show your work or don't ship it").

If any future commit on `experiment/cas-probe-pythia` claims to be 23.B but ships code, that commit is mis-labeled. 23.B is and remains design-only.
