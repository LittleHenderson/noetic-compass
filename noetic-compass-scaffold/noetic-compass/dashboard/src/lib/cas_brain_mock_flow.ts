/**
 * CAS Brain Map — mock flow library.
 *
 * Pure-function data interface consumed by the new CAS Brain Map
 * visualization (the replacement for the rejected "cloud blob"
 * NeuralActivityMap). v1 ships with `mode='MOCK FLOW'` and uses the
 * fixtures returned from this file.
 *
 * Companion design doc:
 *   docs/working/cas_brain_map_2026_05_14/ARCHITECTURE_AND_DESIGN.md
 *
 * Layer manifest is derived from the three CAS-Native model files:
 *   - cas-native/model/cas_native_model.py
 *   - cas-native/model/nl_generation_head.py
 *   - cas-native/model/typed_fiber_decoder.py
 *
 * Honest framing: this is the real CAS-Native model topology rendered
 * as a navigable graph. It is NOT a claim about brain anatomy. The
 * five flows in this file are illustrative MOCKS, not real Mode 7
 * mechanistic-attribution streams. See ARCHITECTURE_AND_DESIGN.md
 * section 8 (Evidence-label discipline) for the four data-source
 * modes and the discipline around labelling them.
 *
 * Pure functions — no IO, deterministic — so tests can import them
 * and Agent A's Three.js component can render from them without
 * worrying about side effects.
 */

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type CASBrainLayerFamily =
  | 'embedding'
  | 'encoder_attn'
  | 'encoder_gate'
  | 'encoder_ffn'
  | 'special_branch'
  | 'decoder_attn'
  | 'decoder_ffn'
  | 'decoder_head'
  | 'output';

export interface CASBrainLayer {
  id: string;
  family: CASBrainLayerFamily;
  label: string;
  /** Plain-English purpose, 1-2 sentences. */
  casPurpose: string;
  /** Longer click-panel expansion, ~5 sentences. */
  whyItMatters: string;
  pipelinePosition: { stage: string; subIndex?: number; total?: number };
  dimensions: { d_model: number; n_heads?: number };
  position3d: { x: number; y: number; z: number };
  /** Size hint in the 0.5..1.5 range. 1.0 is the default. */
  size: number;
  /** Family hex color. Mirror of CAS_BRAIN_PALETTE. */
  color: string;
}

export interface CASBrainEdge {
  from: string;
  to: string;
  /** Edge weight in 0..1. Defaults to 0.5 when omitted. */
  weight?: number;
  /** True for special-branch edges that should be rendered curved. */
  curved?: boolean;
}

export interface CASBrainSignificantPoint {
  layerId: string;
  /** Short label, e.g. "Noetic locked: ^8". */
  label: string;
  /** Optional CAS-expression token (may be empty). */
  casToken: string;
}

export interface CASBrainFlowFrame {
  /** Frame time in ms, in [0, durationMs]. */
  tMs: number;
  activeLayerId: string;
  /** Activation strength in 0..1. */
  activationStrength: number;
  significantPoint?: CASBrainSignificantPoint;
}

export type CASBrainFlowCategory =
  | 'state_lookup'
  | 'recipe'
  | 'fractal'
  | 'inversion'
  | 'binary_composition';

export interface CASBrainFlow {
  flowId: string;
  inputPromptPreview: string;
  category: CASBrainFlowCategory;
  durationMs: number;
  frames: CASBrainFlowFrame[];
}

// ---------------------------------------------------------------------------
// Palette (mirrors ARCHITECTURE_AND_DESIGN.md section 4)
// ---------------------------------------------------------------------------

export const CAS_BRAIN_PALETTE: Record<CASBrainLayerFamily, string> = {
  embedding: '#60a5fa',
  encoder_attn: '#a78bfa',
  encoder_gate: '#fbbf24',
  encoder_ffn: '#2dd4bf',
  special_branch: '#cbd5e1',
  decoder_attn: '#fb7185',
  decoder_ffn: '#34d399',
  decoder_head: '#f59e0b',
  output: '#f59e0b',
};

// ---------------------------------------------------------------------------
// Model shape constants (mirror the Python config defaults)
// ---------------------------------------------------------------------------

const N_ENC_BLOCKS = 6;
const N_DEC_BLOCKS = 6;
const D_MODEL = 512;
const D_MODEL_DEC = 512;
const N_HEADS = 8;
const D_MODEL_TFD = 384;
const N_HEADS_TFD = 6;

// X-axis centers for encoder/decoder blocks (see design doc section 3).
const ENC_BLOCK_X: readonly number[] = [-13, -10, -7, -4, -1, 2];
const DEC_BLOCK_X: readonly number[] = [9, 11.5, 14, 16.5, 19, 21.5];

// ---------------------------------------------------------------------------
// Plain-English copy used in casPurpose / whyItMatters per family
// ---------------------------------------------------------------------------

const PURPOSE: Record<string, { hover: string; click: string }> = {
  token_embedding: {
    hover:
      'Turns each input token into a dense vector the model can work with. ' +
      'This is the first numerical representation of language inside the model.',
    click:
      'Token embedding is where text becomes math. Every word, punctuation ' +
      'mark, and CAS token has its own vector here, learned from training. ' +
      "The cognitive state embedding next to it does a CAS-typed version of " +
      'the same job. Together they form the front door into the model. ' +
      'When you ask a question, this is where the model first sees it.',
  },
  cognitive_state_embedding: {
    hover:
      'Projects each token onto the 40-state CAS open simplex (10 Noetics ' +
      'across 4 Domains). The CAS-typed parallel branch.',
    click:
      'The cognitive state embedding is a parallel branch that runs ' +
      'alongside the main hidden state. It projects each token onto a ' +
      '40-dimensional simplex with one coordinate per CAS state ' +
      '(P0..P9, C0..C9, E0..E9, O0..O9). Every coordinate is strictly ' +
      "positive, so the model's CAS reading of a token is always a real " +
      'mixture of states. This typed branch is what makes the model ' +
      "CAS-Native rather than 'a transformer plus CAS labels.'",
  },
  positional_encoding: {
    hover:
      'Adds a sinusoidal position signal so the model knows token order. ' +
      'Standard transformer positional encoding.',
    click:
      'Positional encoding lets the model tell a token apart from its ' +
      'copies elsewhere in the sequence. Without it, a bag of tokens has ' +
      'no order — the model would treat "dog bites man" identically to ' +
      '"man bites dog." This block uses sine and cosine waves at ' +
      'different frequencies so each position gets a unique signature. ' +
      'It is added directly to the token embedding before the encoder ' +
      'stack begins.',
  },
  domain_attn: {
    hover:
      'Attention that respects CAS domain order ' +
      '(Principled before Cognitive before Evaluative before Operational). ' +
      'Higher-precedence domains can see lower-precedence ones but not the reverse.',
    click:
      'Domain Descent Attention is the CAS structural attention. Standard ' +
      'transformer attention lets every token see every other token; this ' +
      'version blocks attention across the CAS domain hierarchy in the ' +
      "wrong direction. The point is to keep Principled-domain reasoning " +
      "from being driven by Operational-domain noise. It runs in parallel " +
      'with Fractal Attention inside the same encoder block.',
  },
  fractal_attn: {
    hover:
      'Multi-scale attention inspired by iterated function systems. Lets ' +
      'the model attend at several zoom levels at once.',
    click:
      'Fractal Attention is a multi-scale companion to Domain Descent ' +
      'Attention. It maintains attention patterns at several zoom levels, ' +
      'which is useful for cognitive sequences that have nested causal ' +
      'structure (e.g. ^8 cause -> ^9 effect chains that themselves are ' +
      'causes for further effects). The encoder block learns a gate that ' +
      'mixes domain attention and fractal attention; both fire on every ' +
      'forward pass.',
  },
  prereq_gate: {
    hover:
      'The CAS Recursive Prerequisite Monad gate. Holds activations back ' +
      'until the prerequisites for a downstream cognitive operation are satisfied.',
    click:
      'The Prerequisite Gate is one of the load-bearing safety layers in ' +
      'CAS. Cognitive operations have an order — for example, you cannot ' +
      'do real wisdom-domain work without having done its developmental ' +
      'prerequisites. This gate measures whether the prerequisites are ' +
      'satisfied in the current activation and gates the signal ' +
      "accordingly. If a downstream operation is asked without its " +
      'prerequisites, the gate fails closed and the activation does not pass.',
  },
  encoder_ffn: {
    hover:
      'Standard transformer feed-forward block (Linear, GELU, Linear) with ' +
      '4x expansion. Most of the model parameters live here.',
    click:
      "The feed-forward block is the workhorse of transformer " +
      "architectures. Each token's representation is transformed by a " +
      'wide hidden layer (4x the model dimension), then projected back ' +
      "down. Most of the model's learned knowledge — facts, patterns, " +
      'associations — is stored in the weights of these FFN blocks. ' +
      'Layer normalization before and after keeps the signal stable ' +
      'across many stacked blocks. There are six of these in the encoder.',
  },
  encoder_final_norm: {
    hover:
      'Final layer-norm at the end of the encoder stack. Stabilizes the ' +
      'encoder output before special branches and the decoder read it.',
    click:
      'After six encoder blocks the hidden states get one last layer ' +
      'normalization. This is the encoder output that everything ' +
      'downstream reads: the LM head, the topos reasoner, the inversion ' +
      "detector, and the decoder's cross-attention all pull from here. " +
      "It is the encoder's main publishing surface.",
  },
  inversion_detector: {
    hover:
      'Scores the 7 CAS inversion axes from the pooled encoder output. ' +
      'Flags when the model is producing inverted / shadow-form cognition.',
    click:
      "The Inversion Detector is CAS's anti-drift watchdog. It takes the " +
      'pooled encoder representation and outputs a 7-dimensional score, ' +
      'one per inversion axis: Noetic, Domain, Drive, State, Sub-Drive, ' +
      'Pathway, and Compound. High scores mean the model is producing ' +
      'cognition that looks structurally correct on the surface but is ' +
      'inverted underneath. One of the most important safety surfaces.',
  },
  topos_reasoner: {
    hover:
      'Reads the pooled encoder state and outputs intuitionistic ' +
      '3-valued truth values (true / false / undetermined) over the ' +
      'ethical propositions.',
    click:
      'The Cognitive Topos Reasoner produces a 3-valued truth assignment ' +
      "(true / false / undetermined) for each of the model's tracked " +
      'propositions. The 3-valued logic matters because real ethical and ' +
      'cognitive judgments often live in the undetermined zone — saying ' +
      '"undetermined" is structurally different from saying "false." ' +
      'This is the head that lets the model report its own uncertainty ' +
      'about a proposition rather than forcing a binary answer.',
  },
  generative_head: {
    hover:
      'Auxiliary head for generative composition operations (the v7.7 ' +
      'generative operators).',
    click:
      'The Generative Head produces representations for compositional ' +
      "operations that the model is asked to perform — combining states, " +
      'integrating across registers, or building recipes. It is the ' +
      "model's compositional output surface. Most everyday inference does " +
      'not need it; it is engaged on prompts that involve compose, ' +
      'integrate, or recipe-style requests.',
  },
  lacunarity_gate: {
    hover:
      'Self-correction gate that detects over-concentrated activation on ' +
      'the 40-state simplex and rebalances it. Catches spotlight-bias failure modes.',
    click:
      'The Lacunarity Gate measures how concentrated the model\'s ' +
      'cognitive-state activation is. If almost all weight is on one or ' +
      'two states, the gate rebalances the distribution so the model is ' +
      "not effectively single-tracked. This catches a class of failures " +
      'where the model latches onto one state and treats everything ' +
      'through that lens.',
  },
  lacunarity_head: {
    hover:
      'Metacognitive head reporting how lacunar (gap-ridden) the ' +
      'activation pattern is.',
    click:
      "The Lacunarity Head reports the model's own metacognitive read on " +
      'whether the cognitive state has unhealthy gaps. It is a small ' +
      'reporting surface — not in the main inference path, but useful ' +
      "for monitoring whether the model's state coverage looks like it " +
      'should. Paired with the Lacunarity Gate above it on the data flow.',
  },
  expression_proposer: {
    hover:
      "Learned head that proposes CAS expressions from the encoder's " +
      'pre-final-norm hidden state. Opt-in v2 component.',
    click:
      'The Expression Proposer is an optional v2 component that learns ' +
      'to propose CAS expressions directly from the encoder hidden state ' +
      '(before the final layer-norm). When attached, its outputs are ' +
      'returned alongside the standard forward outputs. When not attached, ' +
      'the forward pass is byte-equivalent to the pre-v2 model. This is ' +
      'the head that lets the model say what it thinks the CAS expression ' +
      "for the current state should be.",
  },
  register_film: {
    hover:
      'Multiplicative FiLM modulation by Phenomenological Register ' +
      '(T / A / f / E) applied to the post-decoder hidden state.',
    click:
      'Register FiLM steers the same content into different operational ' +
      'characters — Transcendent, Analytical, Affective, Embodied. The ' +
      'same underlying state can be expressed analytically (chain of ' +
      'thought), affectively (value-laden), embodied (concrete, ' +
      'sensorimotor), or transcendentally (high-abstraction, ' +
      'purpose-orienting). FiLM applies a per-register gamma/beta affine ' +
      'transform to the decoder hidden state right before the LM head.',
  },
  typed_fiber_decoder: {
    hover:
      'Parallel decoder that emits compiler-valid CAS expressions ' +
      '(rather than English) via slot-typed pointer-copy plus generate.',
    click:
      'The Typed Fiber Decoder is the parallel path for emitting ' +
      'structured CAS output. It has its own 6-layer decoder with two ' +
      'cross-attention streams: one over the 40-state simplex trajectory ' +
      "and one over the encoder's source tokens. A 9-way slot-type head " +
      'classifies each output position (CONNECTIVE, OMEGA, STAGE_VAR, ' +
      'COEFFICIENT, REGISTER_LETTER, DOMAIN_LETTER, DRIVE_LETTER, ' +
      'FRACTAL_K_LITERAL, NOETIC_PHRASE) and pointer-copy reads from the ' +
      'source for typed positions.',
  },
  aux_heads: {
    hover:
      'Auxiliary supervision heads (H_card, H_pos, H_stop, H_cluster) ' +
      'attached during training. Provide additional supervision signals ' +
      'beyond the LM loss.',
    click:
      'The auxiliary heads are training-time helpers that give the model ' +
      'extra supervision beyond predicting the next token. H_card ' +
      'predicts cardinality (how many states are active), H_pos predicts ' +
      'per-position noetics, H_stop predicts where to stop generation, ' +
      'and H_cluster predicts cluster membership. They are not used at ' +
      "inference time but they shape what the model learns during " +
      'training.',
  },
  decoder_token_embedding: {
    hover:
      "Decoder-side token embedding. Independent from the encoder's " +
      'embedding so the decoder owns its own English vocab projection.',
    click:
      "Each decoder token has its own learned vector here, separate from " +
      "the encoder's embedding table. Keeping them independent is a " +
      "deliberate choice — the decoder learns an English-side " +
      "representation that does not have to match the encoder's typed " +
      "representation. This is the first numerical step on the response " +
      'side of the model.',
  },
  decoder_pos_embedding: {
    hover:
      'Learned positional embeddings for the decoder. Distinct from the ' +
      "encoder's sinusoidal encoding.",
    click:
      'The decoder uses learned positional embeddings rather than ' +
      'sinusoidal ones. Each position 0..max_len has its own learned ' +
      'vector that gets added to the token embedding. Learned positions ' +
      "let the model specialize early positions (start of response) " +
      'differently from middle and late positions (continuation, ' +
      'wrap-up). Added to the token embedding before the decoder stack.',
  },
  soft_prefix_proj: {
    hover:
      'Projects the 64-dim CAS bottleneck into 4 learned soft-prefix ' +
      "positions that prepend to the decoder's cross-attention KV stream.",
    click:
      'The soft prefix is how the continuous CAS conditioning enters the ' +
      "decoder. The encoder's pooled hidden state is sliced to a 64-dim " +
      'bottleneck and then projected up to four learned positions of ' +
      'd_model. Those four soft-prefix positions are concatenated with ' +
      "the encoder outputs and the decoder cross-attends to the " +
      'combined stream. This is the structural channel for "remember ' +
      'what the CAS state was when answering."',
  },
  self_attn: {
    hover:
      'Causally-masked self-attention over the decoder stream ' +
      '[CAS prefix | decoder tokens]. Standard transformer decoder self-attn.',
    click:
      'Decoder self-attention is causally masked: each position can only ' +
      'attend to itself and earlier positions. This is what makes ' +
      'left-to-right generation possible. Inside this layer the decoder ' +
      "also attends back to the CAS-prefix tokens prepended in front of " +
      'its stream, so the discrete CAS conditioning is available as ' +
      'attendable context. PAD positions in the prefix are masked out so ' +
      'they cannot leak into conditioning.',
  },
  cross_attn: {
    hover:
      'Cross-attention from the decoder to the encoder outputs plus the ' +
      'soft CAS prefix. Where the decoder looks back at the input.',
    click:
      'Decoder cross-attention is how the model grounds its output in ' +
      'the input. Each decoder position queries the encoder full output ' +
      'sequence (concatenated with the soft CAS prefix carrying the ' +
      '64-dim CAS bottleneck), and the attention weights tell us which ' +
      'input tokens the decoder is leaning on for each output token. ' +
      'This is the layer Mode 7 traces most heavily.',
  },
  decoder_ffn: {
    hover:
      'Decoder feed-forward block. Where decoder-side knowledge — ' +
      'vocabulary patterns, style, phrasing — is stored.',
    click:
      'The decoder feed-forward block is the mirror image of the ' +
      "encoder FFN. It transforms each decoder position's representation " +
      "through a wide hidden layer and projects back down. Most of the " +
      "model's English generation patterns — collocations, idiomatic " +
      'phrasing, sentence rhythm — live in the weights here. Combined ' +
      'with the cross-attention layer above, this is how to say it.',
  },
  decoder_final_norm: {
    hover:
      "Final layer-norm at the end of the decoder stack. Last " +
      'stabilization step before the LM head.',
    click:
      "After the six decoder blocks and the optional register-FiLM " +
      'modulation, the decoder hidden state passes through one last ' +
      "layer normalization. This stabilizes the signal before the LM " +
      "head reads it and projects to vocabulary logits. It is the " +
      "decoder's main publishing surface.",
  },
  lm_head: {
    hover:
      'Projects the final decoder hidden state to a probability over the ' +
      'whole vocabulary. The model last step before picking a token.',
    click:
      'The LM head is the model emission surface. Every output token is ' +
      'sampled from a distribution this layer produces. The weights are ' +
      "random-init and not tied to the input embedding — that decoupling " +
      'is deliberate, so the model can learn an emission distribution ' +
      'that is independent of input embedding geometry. Each time you ' +
      'see a token appear in a response, that token was drawn from the ' +
      'distribution this layer produced for its position.',
  },
  output: {
    hover:
      "The model's emitted token sequence. This is what the user sees.",
    click:
      'The output node represents the model finished response — the ' +
      'sequence of tokens that becomes the rendered reply. By the time ' +
      'a token reaches here, the entire pipeline behind it has already ' +
      'committed. The CAS Brain Map traces backwards from this point to ' +
      'show which layers contributed which signals. This is the right ' +
      'end of the visible mechanistic story.',
  },
};

// ---------------------------------------------------------------------------
// Layer construction
// ---------------------------------------------------------------------------

interface LayerSeed {
  id: string;
  family: CASBrainLayerFamily;
  label: string;
  purposeKey: keyof typeof PURPOSE;
  pipelinePosition: { stage: string; subIndex?: number; total?: number };
  dimensions: { d_model: number; n_heads?: number };
  position3d: { x: number; y: number; z: number };
  size?: number;
}

function buildLayer(seed: LayerSeed): CASBrainLayer {
  const copy = PURPOSE[seed.purposeKey];
  return {
    id: seed.id,
    family: seed.family,
    label: seed.label,
    casPurpose: copy.hover,
    whyItMatters: copy.click,
    pipelinePosition: seed.pipelinePosition,
    dimensions: seed.dimensions,
    position3d: seed.position3d,
    size: seed.size ?? 1.0,
    color: CAS_BRAIN_PALETTE[seed.family],
  };
}

function buildEncoderBlock(idx: number): CASBrainLayer[] {
  const cx = ENC_BLOCK_X[idx];
  // sub-positions inside the block: domain_attn (top-front), fractal_attn
  // (top-back), prereq_gate (bottom-front), ffn (bottom-back).
  return [
    buildLayer({
      id: `enc_block_${idx}.domain_attn`,
      family: 'encoder_attn',
      label: `Encoder ${idx + 1} - Domain Attn`,
      purposeKey: 'domain_attn',
      pipelinePosition: { stage: 'encoder_block', subIndex: idx, total: N_ENC_BLOCKS },
      dimensions: { d_model: D_MODEL, n_heads: N_HEADS },
      position3d: { x: cx - 0.4, y: 0.5, z: -0.4 },
    }),
    buildLayer({
      id: `enc_block_${idx}.fractal_attn`,
      family: 'encoder_attn',
      label: `Encoder ${idx + 1} - Fractal Attn`,
      purposeKey: 'fractal_attn',
      pipelinePosition: { stage: 'encoder_block', subIndex: idx, total: N_ENC_BLOCKS },
      dimensions: { d_model: D_MODEL, n_heads: N_HEADS },
      position3d: { x: cx - 0.4, y: 0.5, z: 0.4 },
    }),
    buildLayer({
      id: `enc_block_${idx}.prereq_gate`,
      family: 'encoder_gate',
      label: `Encoder ${idx + 1} - RPM Gate`,
      purposeKey: 'prereq_gate',
      pipelinePosition: { stage: 'encoder_block', subIndex: idx, total: N_ENC_BLOCKS },
      dimensions: { d_model: D_MODEL },
      position3d: { x: cx + 0.4, y: -0.5, z: -0.4 },
    }),
    buildLayer({
      id: `enc_block_${idx}.ffn`,
      family: 'encoder_ffn',
      label: `Encoder ${idx + 1} - FFN`,
      purposeKey: 'encoder_ffn',
      pipelinePosition: { stage: 'encoder_block', subIndex: idx, total: N_ENC_BLOCKS },
      dimensions: { d_model: D_MODEL },
      position3d: { x: cx + 0.4, y: -0.5, z: 0.4 },
    }),
  ];
}

function buildDecoderBlock(idx: number): CASBrainLayer[] {
  const cx = DEC_BLOCK_X[idx];
  // sub-positions: self_attn (top), cross_attn (middle), ffn (bottom).
  return [
    buildLayer({
      id: `dec_block_${idx}.self_attn`,
      family: 'decoder_attn',
      label: `Decoder ${idx + 1} - Self Attn`,
      purposeKey: 'self_attn',
      pipelinePosition: { stage: 'decoder_block', subIndex: idx, total: N_DEC_BLOCKS },
      dimensions: { d_model: D_MODEL_DEC, n_heads: N_HEADS },
      position3d: { x: cx, y: 0.6, z: 0 },
    }),
    buildLayer({
      id: `dec_block_${idx}.cross_attn`,
      family: 'decoder_attn',
      label: `Decoder ${idx + 1} - Cross Attn`,
      purposeKey: 'cross_attn',
      pipelinePosition: { stage: 'decoder_block', subIndex: idx, total: N_DEC_BLOCKS },
      dimensions: { d_model: D_MODEL_DEC, n_heads: N_HEADS },
      position3d: { x: cx, y: 0, z: 0 },
    }),
    buildLayer({
      id: `dec_block_${idx}.ffn`,
      family: 'decoder_ffn',
      label: `Decoder ${idx + 1} - FFN`,
      purposeKey: 'decoder_ffn',
      pipelinePosition: { stage: 'decoder_block', subIndex: idx, total: N_DEC_BLOCKS },
      dimensions: { d_model: D_MODEL_DEC },
      position3d: { x: cx, y: -0.6, z: 0 },
    }),
  ];
}

// ---------------------------------------------------------------------------
// getStaticLayers
// ---------------------------------------------------------------------------

export function getStaticLayers(): CASBrainLayer[] {
  const layers: CASBrainLayer[] = [];

  // Embedding stage (3 nodes).
  layers.push(
    buildLayer({
      id: 'token_embedding',
      family: 'embedding',
      label: 'Token Embedding',
      purposeKey: 'token_embedding',
      pipelinePosition: { stage: 'embedding' },
      dimensions: { d_model: D_MODEL },
      position3d: { x: -20, y: 1, z: 0 },
      size: 1.1,
    }),
    buildLayer({
      id: 'cognitive_state_embedding',
      family: 'embedding',
      label: 'Cognitive State Embedding',
      purposeKey: 'cognitive_state_embedding',
      pipelinePosition: { stage: 'embedding' },
      dimensions: { d_model: D_MODEL },
      position3d: { x: -19, y: 2.5, z: 0 },
    }),
    buildLayer({
      id: 'positional_encoding',
      family: 'embedding',
      label: 'Positional Encoding',
      purposeKey: 'positional_encoding',
      pipelinePosition: { stage: 'embedding' },
      dimensions: { d_model: D_MODEL },
      position3d: { x: -19, y: -0.5, z: 0 },
    }),
  );

  // Encoder stack (6 blocks * 4 sub-modules = 24 nodes).
  for (let i = 0; i < N_ENC_BLOCKS; i += 1) {
    layers.push(...buildEncoderBlock(i));
  }

  // Encoder final norm.
  layers.push(
    buildLayer({
      id: 'encoder_final_norm',
      family: 'encoder_ffn',
      label: 'Encoder Final Norm',
      purposeKey: 'encoder_final_norm',
      pipelinePosition: { stage: 'encoder_final' },
      dimensions: { d_model: D_MODEL },
      position3d: { x: 5, y: 0, z: 0 },
      size: 1.1,
    }),
  );

  // Special branches ABOVE.
  layers.push(
    buildLayer({
      id: 'topos_reasoner',
      family: 'special_branch',
      label: 'Cognitive Topos Reasoner',
      purposeKey: 'topos_reasoner',
      pipelinePosition: { stage: 'special_branch_above' },
      dimensions: { d_model: D_MODEL },
      position3d: { x: 4.5, y: 5, z: 0 },
      size: 1.1,
    }),
    buildLayer({
      id: 'inversion_detector',
      family: 'special_branch',
      label: 'Inversion Detector',
      purposeKey: 'inversion_detector',
      pipelinePosition: { stage: 'special_branch_above' },
      dimensions: { d_model: D_MODEL },
      position3d: { x: 6.5, y: 5.5, z: 0 },
      size: 1.2,
    }),
    buildLayer({
      id: 'generative_head',
      family: 'special_branch',
      label: 'Generative Head',
      purposeKey: 'generative_head',
      pipelinePosition: { stage: 'special_branch_above' },
      dimensions: { d_model: D_MODEL },
      position3d: { x: 8.5, y: 5, z: 0 },
    }),
    // RegisterFiLM tied to the decoder side as a special-above branch.
    buildLayer({
      id: 'register_film',
      family: 'special_branch',
      label: 'Register FiLM',
      purposeKey: 'register_film',
      pipelinePosition: { stage: 'special_branch_above' },
      dimensions: { d_model: D_MODEL_DEC },
      position3d: { x: 15, y: 5.5, z: 0 },
      size: 1.1,
    }),
  );

  // Special branches BELOW.
  layers.push(
    buildLayer({
      id: 'lacunarity_gate',
      family: 'special_branch',
      label: 'Lacunarity Gate',
      purposeKey: 'lacunarity_gate',
      pipelinePosition: { stage: 'special_branch_below' },
      dimensions: { d_model: D_MODEL },
      position3d: { x: 4, y: -5, z: 0 },
    }),
    buildLayer({
      id: 'typed_fiber_decoder',
      family: 'special_branch',
      label: 'Typed Fiber Decoder (parallel)',
      purposeKey: 'typed_fiber_decoder',
      pipelinePosition: { stage: 'special_branch_below' },
      dimensions: { d_model: D_MODEL_TFD, n_heads: N_HEADS_TFD },
      position3d: { x: 15, y: -5.5, z: 0 },
      size: 1.2,
    }),
  );

  // Decoder embedding stage (3 nodes).
  layers.push(
    buildLayer({
      id: 'decoder_token_embedding',
      family: 'embedding',
      label: 'Decoder Token Embedding',
      purposeKey: 'decoder_token_embedding',
      pipelinePosition: { stage: 'decoder_embedding' },
      dimensions: { d_model: D_MODEL_DEC },
      position3d: { x: 7, y: 1.5, z: 0 },
    }),
    buildLayer({
      id: 'decoder_pos_embedding',
      family: 'embedding',
      label: 'Decoder Positional Embedding',
      purposeKey: 'decoder_pos_embedding',
      pipelinePosition: { stage: 'decoder_embedding' },
      dimensions: { d_model: D_MODEL_DEC },
      position3d: { x: 7, y: -1.5, z: 0 },
    }),
    buildLayer({
      id: 'soft_prefix_proj',
      family: 'embedding',
      label: 'Soft Prefix Proj (CAS bottleneck)',
      purposeKey: 'soft_prefix_proj',
      pipelinePosition: { stage: 'decoder_embedding' },
      dimensions: { d_model: D_MODEL_DEC },
      position3d: { x: 7, y: 0, z: 0 },
    }),
  );

  // Decoder stack (6 blocks * 3 sub-modules = 18 nodes).
  for (let i = 0; i < N_DEC_BLOCKS; i += 1) {
    layers.push(...buildDecoderBlock(i));
  }

  // Decoder final norm.
  layers.push(
    buildLayer({
      id: 'decoder_final_norm',
      family: 'decoder_ffn',
      label: 'Decoder Final Norm',
      purposeKey: 'decoder_final_norm',
      pipelinePosition: { stage: 'decoder_final' },
      dimensions: { d_model: D_MODEL_DEC },
      position3d: { x: 22.5, y: 0, z: 0 },
      size: 1.1,
    }),
  );

  // LM head + output.
  layers.push(
    buildLayer({
      id: 'lm_head',
      family: 'decoder_head',
      label: 'LM Head',
      purposeKey: 'lm_head',
      pipelinePosition: { stage: 'output' },
      dimensions: { d_model: D_MODEL_DEC },
      position3d: { x: 24, y: 0, z: 0 },
      size: 1.3,
    }),
    buildLayer({
      id: 'output',
      family: 'output',
      label: 'Output (tokens)',
      purposeKey: 'output',
      pipelinePosition: { stage: 'output' },
      dimensions: { d_model: D_MODEL_DEC },
      position3d: { x: 26.5, y: 0, z: 0 },
      size: 1.5,
    }),
  );

  return layers;
}

// ---------------------------------------------------------------------------
// getStaticEdges
// ---------------------------------------------------------------------------

export function getStaticEdges(): CASBrainEdge[] {
  const edges: CASBrainEdge[] = [];

  // ---- Embedding stage -> first encoder block ----
  edges.push(
    { from: 'token_embedding', to: 'positional_encoding', weight: 1.0 },
    { from: 'positional_encoding', to: 'enc_block_0.domain_attn', weight: 1.0 },
    // Cognitive state embedding routes into every encoder block (the
    // model recomputes it inside the encoder loop). Curved so the wiring
    // does not visually compete with the main spine.
    ...Array.from({ length: N_ENC_BLOCKS }, (_, i) => ({
      from: 'cognitive_state_embedding',
      to: `enc_block_${i}.domain_attn`,
      weight: 0.5,
      curved: true,
    })),
  );

  // ---- Encoder block sub-modules (intra-block) ----
  for (let i = 0; i < N_ENC_BLOCKS; i += 1) {
    edges.push(
      { from: `enc_block_${i}.domain_attn`, to: `enc_block_${i}.fractal_attn`, weight: 0.8 },
      { from: `enc_block_${i}.fractal_attn`, to: `enc_block_${i}.prereq_gate`, weight: 0.8 },
      { from: `enc_block_${i}.prereq_gate`, to: `enc_block_${i}.ffn`, weight: 0.9 },
    );
  }

  // ---- Encoder block N -> Encoder block N+1 ----
  for (let i = 0; i < N_ENC_BLOCKS - 1; i += 1) {
    edges.push({
      from: `enc_block_${i}.ffn`,
      to: `enc_block_${i + 1}.domain_attn`,
      weight: 1.0,
    });
  }

  // ---- Last encoder block -> encoder_final_norm ----
  edges.push({
    from: `enc_block_${N_ENC_BLOCKS - 1}.ffn`,
    to: 'encoder_final_norm',
    weight: 1.0,
  });

  // ---- Special branches above attached to encoder_final_norm ----
  edges.push(
    { from: 'encoder_final_norm', to: 'topos_reasoner', weight: 0.6, curved: true },
    { from: 'encoder_final_norm', to: 'inversion_detector', weight: 0.8, curved: true },
    { from: 'encoder_final_norm', to: 'generative_head', weight: 0.6, curved: true },
  );

  // ---- Special branches below ----
  // Lacunarity gate sits on the cognitive state path; conceptually it
  // consumes the simplex output (which is recomputed in the encoder
  // loop). Tie it to the encoder_final_norm via curved edge.
  edges.push(
    { from: 'encoder_final_norm', to: 'lacunarity_gate', weight: 0.5, curved: true },
    // Typed fiber decoder runs parallel to the NL decoder — fed from
    // encoder_final_norm (source hidden + simplex trajectory).
    { from: 'encoder_final_norm', to: 'typed_fiber_decoder', weight: 0.6, curved: true },
  );

  // ---- Decoder embedding stage ----
  edges.push(
    { from: 'decoder_token_embedding', to: 'decoder_pos_embedding', weight: 1.0 },
    { from: 'decoder_pos_embedding', to: 'dec_block_0.self_attn', weight: 1.0 },
    // Soft prefix feeds cross-attn KV (concatenated with encoder output).
    { from: 'soft_prefix_proj', to: 'dec_block_0.cross_attn', weight: 0.8, curved: true },
    // Encoder -> decoder cross-attn (every decoder block reads encoder_final_norm).
    ...Array.from({ length: N_DEC_BLOCKS }, (_, i) => ({
      from: 'encoder_final_norm',
      to: `dec_block_${i}.cross_attn`,
      weight: 0.9,
      curved: true,
    })),
  );

  // ---- Decoder block sub-modules (intra-block) ----
  for (let i = 0; i < N_DEC_BLOCKS; i += 1) {
    edges.push(
      { from: `dec_block_${i}.self_attn`, to: `dec_block_${i}.cross_attn`, weight: 0.9 },
      { from: `dec_block_${i}.cross_attn`, to: `dec_block_${i}.ffn`, weight: 0.9 },
    );
  }

  // ---- Decoder block N -> Decoder block N+1 ----
  for (let i = 0; i < N_DEC_BLOCKS - 1; i += 1) {
    edges.push({
      from: `dec_block_${i}.ffn`,
      to: `dec_block_${i + 1}.self_attn`,
      weight: 1.0,
    });
  }

  // ---- Last decoder block -> decoder_final_norm -> lm_head -> output ----
  edges.push(
    { from: `dec_block_${N_DEC_BLOCKS - 1}.ffn`, to: 'decoder_final_norm', weight: 1.0 },
    { from: 'decoder_final_norm', to: 'lm_head', weight: 1.0 },
    { from: 'lm_head', to: 'output', weight: 1.0 },
  );

  // ---- RegisterFiLM connects to all 6 decoder blocks (curved). ----
  for (let i = 0; i < N_DEC_BLOCKS; i += 1) {
    edges.push({
      from: 'register_film',
      to: `dec_block_${i}.ffn`,
      weight: 0.5,
      curved: true,
    });
  }

  return edges;
}

// ---------------------------------------------------------------------------
// Mock flows
// ---------------------------------------------------------------------------

interface FrameSpec {
  tMs: number;
  activeLayerId: string;
  activationStrength: number;
  significantPoint?: CASBrainSignificantPoint;
}

function buildFlow(
  flowId: string,
  category: CASBrainFlowCategory,
  inputPromptPreview: string,
  durationMs: number,
  frameSpecs: FrameSpec[],
): CASBrainFlow {
  // Defensive sort by tMs.
  const sorted = [...frameSpecs].sort((a, b) => a.tMs - b.tMs);
  const frames: CASBrainFlowFrame[] = sorted.map((s) => ({
    tMs: s.tMs,
    activeLayerId: s.activeLayerId,
    activationStrength: s.activationStrength,
    significantPoint: s.significantPoint,
  }));
  return { flowId, inputPromptPreview, category, durationMs, frames };
}

// --- 6.1 state_lookup ---
function buildStateLookupFlow(): CASBrainFlow {
  const D = 4000;
  return buildFlow('mock_state_lookup_v1', 'state_lookup', 'what is ^3?', D, [
    { tMs: 0, activeLayerId: 'token_embedding', activationStrength: 1.0 },
    { tMs: 100, activeLayerId: 'positional_encoding', activationStrength: 0.9 },
    {
      tMs: 200,
      activeLayerId: 'cognitive_state_embedding',
      activationStrength: 0.9,
      significantPoint: {
        layerId: 'cognitive_state_embedding',
        label: 'State token detected: ^3',
        casToken: '^3',
      },
    },
    { tMs: 350, activeLayerId: 'enc_block_0.domain_attn', activationStrength: 0.7 },
    { tMs: 450, activeLayerId: 'enc_block_0.fractal_attn', activationStrength: 0.4 },
    { tMs: 550, activeLayerId: 'enc_block_0.prereq_gate', activationStrength: 0.5 },
    { tMs: 650, activeLayerId: 'enc_block_0.ffn', activationStrength: 0.7 },
    { tMs: 800, activeLayerId: 'enc_block_1.domain_attn', activationStrength: 0.7 },
    { tMs: 900, activeLayerId: 'enc_block_1.fractal_attn', activationStrength: 0.4 },
    {
      tMs: 1000,
      activeLayerId: 'enc_block_1.prereq_gate',
      activationStrength: 0.6,
      significantPoint: {
        layerId: 'enc_block_1.prereq_gate',
        label: 'Prereqs OK for lookup',
        casToken: 'RPM:ok',
      },
    },
    { tMs: 1100, activeLayerId: 'enc_block_1.ffn', activationStrength: 0.7 },
    {
      tMs: 1300,
      activeLayerId: 'encoder_final_norm',
      activationStrength: 0.9,
      significantPoint: {
        layerId: 'encoder_final_norm',
        label: 'Encoded: state lookup for ^3',
        casToken: 'lookup(^3)',
      },
    },
    {
      tMs: 1450,
      activeLayerId: 'inversion_detector',
      activationStrength: 0.6,
      significantPoint: {
        layerId: 'inversion_detector',
        label: 'No inversion (^3 visceral check)',
        casToken: 'inv:N=0.05',
      },
    },
    { tMs: 1700, activeLayerId: 'soft_prefix_proj', activationStrength: 0.7 },
    { tMs: 1850, activeLayerId: 'decoder_token_embedding', activationStrength: 0.9 },
    { tMs: 2000, activeLayerId: 'dec_block_0.self_attn', activationStrength: 0.7 },
    {
      tMs: 2100,
      activeLayerId: 'dec_block_0.cross_attn',
      activationStrength: 0.9,
      significantPoint: {
        layerId: 'dec_block_0.cross_attn',
        label: 'Cross-attn binds to ^3 in input',
        casToken: '^3',
      },
    },
    { tMs: 2200, activeLayerId: 'dec_block_0.ffn', activationStrength: 0.7 },
    { tMs: 2500, activeLayerId: 'dec_block_3.cross_attn', activationStrength: 0.8 },
    { tMs: 2800, activeLayerId: 'dec_block_5.ffn', activationStrength: 0.7 },
    {
      tMs: 3000,
      activeLayerId: 'decoder_final_norm',
      activationStrength: 0.9,
      significantPoint: {
        layerId: 'decoder_final_norm',
        label: 'Decoder ready to emit',
        casToken: '',
      },
    },
    {
      tMs: 3200,
      activeLayerId: 'lm_head',
      activationStrength: 1.0,
      significantPoint: {
        layerId: 'lm_head',
        label: 'Emit: ^3 = Negative',
        casToken: '^3=Negative',
      },
    },
    { tMs: 3500, activeLayerId: 'output', activationStrength: 1.0 },
  ]);
}

// --- 6.2 recipe ---
function buildRecipeFlow(): CASBrainFlow {
  const D = 4000;
  const frames: FrameSpec[] = [
    { tMs: 0, activeLayerId: 'token_embedding', activationStrength: 1.0 },
    { tMs: 80, activeLayerId: 'positional_encoding', activationStrength: 0.9 },
    { tMs: 160, activeLayerId: 'cognitive_state_embedding', activationStrength: 0.9 },
  ];
  // Deep encoder traversal; gate fires multiple times.
  let t = 280;
  for (let i = 0; i < N_ENC_BLOCKS; i += 1) {
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.domain_attn`, activationStrength: 0.7 });
    t += 60;
    // FractalAttention fires once (block 2).
    frames.push({
      tMs: t,
      activeLayerId: `enc_block_${i}.fractal_attn`,
      activationStrength: i === 2 ? 0.9 : 0.4,
      significantPoint:
        i === 2
          ? {
              layerId: `enc_block_${i}.fractal_attn`,
              label: 'Recipe spine assembled',
              casToken: 'Θ(Ω)',
            }
          : undefined,
    });
    t += 60;
    frames.push({
      tMs: t,
      activeLayerId: `enc_block_${i}.prereq_gate`,
      activationStrength: 0.85,
      significantPoint: {
        layerId: `enc_block_${i}.prereq_gate`,
        label: `Prereq check #${i + 1}`,
        casToken: `RPM[${i}]`,
      },
    });
    t += 60;
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.ffn`, activationStrength: 0.8 });
    t += 80;
  }
  frames.push(
    { tMs: 1900, activeLayerId: 'encoder_final_norm', activationStrength: 0.95 },
    {
      tMs: 2050,
      activeLayerId: 'generative_head',
      activationStrength: 0.8,
      significantPoint: {
        layerId: 'generative_head',
        label: 'Generative compose: recipe',
        casToken: 'Θ(decision)',
      },
    },
    { tMs: 2200, activeLayerId: 'soft_prefix_proj', activationStrength: 0.85 },
    { tMs: 2300, activeLayerId: 'decoder_token_embedding', activationStrength: 0.9 },
  );
  // Decoder cycles ~3-4 times.
  let dt = 2400;
  for (let i = 0; i < N_DEC_BLOCKS; i += 1) {
    frames.push({ tMs: dt, activeLayerId: `dec_block_${i}.self_attn`, activationStrength: 0.7 });
    dt += 50;
    frames.push({ tMs: dt, activeLayerId: `dec_block_${i}.cross_attn`, activationStrength: 0.85 });
    dt += 50;
    frames.push({ tMs: dt, activeLayerId: `dec_block_${i}.ffn`, activationStrength: 0.75 });
    dt += 60;
  }
  frames.push(
    {
      tMs: 3500,
      activeLayerId: 'register_film',
      activationStrength: 0.7,
      significantPoint: {
        layerId: 'register_film',
        label: 'Register: Analytical',
        casToken: '|A',
      },
    },
    { tMs: 3700, activeLayerId: 'decoder_final_norm', activationStrength: 0.95 },
    {
      tMs: 3850,
      activeLayerId: 'lm_head',
      activationStrength: 1.0,
      significantPoint: {
        layerId: 'lm_head',
        label: 'Emit recipe text',
        casToken: 'Θ(Ω)=…',
      },
    },
    { tMs: 3990, activeLayerId: 'output', activationStrength: 1.0 },
  );
  return buildFlow(
    'mock_recipe_v1',
    'recipe',
    'walk me through how a decision gets made',
    D,
    frames,
  );
}

// --- 6.3 fractal ---
function buildFractalFlow(): CASBrainFlow {
  const D = 4000;
  const frames: FrameSpec[] = [
    { tMs: 0, activeLayerId: 'token_embedding', activationStrength: 1.0 },
    { tMs: 80, activeLayerId: 'positional_encoding', activationStrength: 0.9 },
    {
      tMs: 160,
      activeLayerId: 'cognitive_state_embedding',
      activationStrength: 0.9,
      significantPoint: {
        layerId: 'cognitive_state_embedding',
        label: 'Chain head: ^8 cause',
        casToken: '^8',
      },
    },
  ];
  let t = 280;
  for (let i = 0; i < N_ENC_BLOCKS; i += 1) {
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.domain_attn`, activationStrength: 0.65 });
    t += 50;
    // FractalAttention is the star.
    frames.push({
      tMs: t,
      activeLayerId: `enc_block_${i}.fractal_attn`,
      activationStrength: 0.95,
      significantPoint: {
        layerId: `enc_block_${i}.fractal_attn`,
        label: i % 2 === 0 ? 'Fractal scale: ^8 trigger' : 'Fractal scale: ^9 land',
        casToken: i % 2 === 0 ? '^8' : '^9',
      },
    });
    t += 50;
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.prereq_gate`, activationStrength: 0.55 });
    t += 50;
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.ffn`, activationStrength: 0.75 });
    t += 80;
  }
  frames.push(
    { tMs: 2050, activeLayerId: 'encoder_final_norm', activationStrength: 0.95 },
    {
      tMs: 2200,
      activeLayerId: 'inversion_detector',
      activationStrength: 0.55,
      significantPoint: {
        layerId: 'inversion_detector',
        label: 'Chain integrity OK',
        casToken: 'inv:N=0.07',
      },
    },
    { tMs: 2400, activeLayerId: 'soft_prefix_proj', activationStrength: 0.8 },
    { tMs: 2500, activeLayerId: 'decoder_token_embedding', activationStrength: 0.9 },
  );
  let dt = 2600;
  for (let i = 0; i < N_DEC_BLOCKS; i += 1) {
    frames.push({ tMs: dt, activeLayerId: `dec_block_${i}.self_attn`, activationStrength: 0.65 });
    dt += 45;
    frames.push({ tMs: dt, activeLayerId: `dec_block_${i}.cross_attn`, activationStrength: 0.8 });
    dt += 45;
    frames.push({ tMs: dt, activeLayerId: `dec_block_${i}.ffn`, activationStrength: 0.7 });
    dt += 55;
  }
  frames.push(
    { tMs: 3650, activeLayerId: 'decoder_final_norm', activationStrength: 0.9 },
    {
      tMs: 3800,
      activeLayerId: 'lm_head',
      activationStrength: 1.0,
      significantPoint: {
        layerId: 'lm_head',
        label: 'Emit chain narrative',
        casToken: '^8→^9→^8',
      },
    },
    { tMs: 3960, activeLayerId: 'output', activationStrength: 1.0 },
  );
  return buildFlow(
    'mock_fractal_v1',
    'fractal',
    'a thought led to an aversion led to a decision',
    D,
    frames,
  );
}

// --- 6.4 inversion ---
function buildInversionFlow(): CASBrainFlow {
  const D = 4000;
  const frames: FrameSpec[] = [
    { tMs: 0, activeLayerId: 'token_embedding', activationStrength: 1.0 },
    { tMs: 80, activeLayerId: 'positional_encoding', activationStrength: 0.9 },
    {
      tMs: 160,
      activeLayerId: 'cognitive_state_embedding',
      activationStrength: 0.95,
      significantPoint: {
        layerId: 'cognitive_state_embedding',
        label: 'Involution pair detected: ^2/^3',
        casToken: '^2↔^3',
      },
    },
  ];
  // Mid-stack traversal: blocks 1..4 do the bulk of the work.
  let t = 300;
  for (let i = 1; i < 5; i += 1) {
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.domain_attn`, activationStrength: 0.85 });
    t += 60;
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.fractal_attn`, activationStrength: 0.4 });
    t += 60;
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.prereq_gate`, activationStrength: 0.6 });
    t += 60;
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.ffn`, activationStrength: 0.8 });
    t += 80;
  }
  frames.push(
    { tMs: 1450, activeLayerId: 'encoder_final_norm', activationStrength: 0.95 },
    {
      tMs: 1600,
      activeLayerId: 'inversion_detector',
      activationStrength: 1.0,
      significantPoint: {
        layerId: 'inversion_detector',
        label: 'Inversion axis N high',
        casToken: 'inv:N=0.92',
      },
    },
    {
      tMs: 1800,
      activeLayerId: 'topos_reasoner',
      activationStrength: 0.7,
      significantPoint: {
        layerId: 'topos_reasoner',
        label: 'Truth: contrast-valid',
        casToken: 'τ:contrast',
      },
    },
    { tMs: 2050, activeLayerId: 'soft_prefix_proj', activationStrength: 0.8 },
    { tMs: 2200, activeLayerId: 'decoder_token_embedding', activationStrength: 0.9 },
  );
  let dt = 2300;
  for (let i = 0; i < N_DEC_BLOCKS; i += 1) {
    frames.push({ tMs: dt, activeLayerId: `dec_block_${i}.self_attn`, activationStrength: 0.7 });
    dt += 50;
    frames.push({ tMs: dt, activeLayerId: `dec_block_${i}.cross_attn`, activationStrength: 0.8 });
    dt += 50;
    frames.push({ tMs: dt, activeLayerId: `dec_block_${i}.ffn`, activationStrength: 0.75 });
    dt += 60;
  }
  frames.push(
    { tMs: 3450, activeLayerId: 'decoder_final_norm', activationStrength: 0.9 },
    {
      tMs: 3650,
      activeLayerId: 'lm_head',
      activationStrength: 1.0,
      significantPoint: {
        layerId: 'lm_head',
        label: 'Emit involution-pair gloss',
        casToken: '^2 vs ^3',
      },
    },
    { tMs: 3900, activeLayerId: 'output', activationStrength: 1.0 },
  );
  return buildFlow(
    'mock_inversion_v1',
    'inversion',
    'compare ^2 and ^3',
    D,
    frames,
  );
}

// --- 6.5 binary_composition ---
function buildBinaryCompositionFlow(): CASBrainFlow {
  const D = 4000;
  const frames: FrameSpec[] = [
    { tMs: 0, activeLayerId: 'token_embedding', activationStrength: 1.0 },
    { tMs: 80, activeLayerId: 'positional_encoding', activationStrength: 0.9 },
    {
      tMs: 160,
      activeLayerId: 'cognitive_state_embedding',
      activationStrength: 0.95,
      significantPoint: {
        layerId: 'cognitive_state_embedding',
        label: 'Operands: X, Y',
        casToken: 'X × Y',
      },
    },
  ];
  let t = 280;
  for (let i = 0; i < N_ENC_BLOCKS; i += 1) {
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.domain_attn`, activationStrength: 0.75 });
    t += 55;
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.fractal_attn`, activationStrength: 0.6 });
    t += 55;
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.prereq_gate`, activationStrength: 0.7 });
    t += 55;
    frames.push({ tMs: t, activeLayerId: `enc_block_${i}.ffn`, activationStrength: 0.8 });
    t += 70;
  }
  frames.push(
    { tMs: 1900, activeLayerId: 'encoder_final_norm', activationStrength: 0.95 },
    {
      tMs: 2050,
      activeLayerId: 'generative_head',
      activationStrength: 0.9,
      significantPoint: {
        layerId: 'generative_head',
        label: 'Integrate: (X × Y) = Ω',
        casToken: '(X×Y)=Ω',
      },
    },
    { tMs: 2200, activeLayerId: 'soft_prefix_proj', activationStrength: 0.85 },
    { tMs: 2300, activeLayerId: 'decoder_token_embedding', activationStrength: 0.9 },
  );
  // Decoder hits BOTH self-attn and cross-attn heavily on every block.
  let dt = 2400;
  for (let i = 0; i < N_DEC_BLOCKS; i += 1) {
    frames.push({
      tMs: dt,
      activeLayerId: `dec_block_${i}.self_attn`,
      activationStrength: 0.9,
      significantPoint:
        i === 2
          ? {
              layerId: `dec_block_${i}.self_attn`,
              label: 'Self-attn looks back at CAS prefix',
              casToken: 'cas_prefix',
            }
          : undefined,
    });
    dt += 50;
    frames.push({
      tMs: dt,
      activeLayerId: `dec_block_${i}.cross_attn`,
      activationStrength: 0.95,
      significantPoint:
        i === 3
          ? {
              layerId: `dec_block_${i}.cross_attn`,
              label: 'Cross-attn binds operands',
              casToken: 'X⇄Y',
            }
          : undefined,
    });
    dt += 50;
    frames.push({
      tMs: dt,
      activeLayerId: `dec_block_${i}.ffn`,
      activationStrength: 0.8,
    });
    dt += 50;
  }
  frames.push(
    {
      tMs: 3400,
      activeLayerId: 'register_film',
      activationStrength: 0.85,
      significantPoint: {
        layerId: 'register_film',
        label: 'Register: Ω (fused)',
        casToken: '|Ω',
      },
    },
    { tMs: 3600, activeLayerId: 'decoder_final_norm', activationStrength: 0.95 },
    {
      tMs: 3800,
      activeLayerId: 'lm_head',
      activationStrength: 1.0,
      significantPoint: {
        layerId: 'lm_head',
        label: 'Emit fused expression',
        casToken: '(X×Y)=Ω',
      },
    },
    { tMs: 3970, activeLayerId: 'output', activationStrength: 1.0 },
  );
  return buildFlow(
    'mock_binary_composition_v1',
    'binary_composition',
    'X integrated with Y',
    D,
    frames,
  );
}

// ---------------------------------------------------------------------------
// getMockFlows
// ---------------------------------------------------------------------------

export function getMockFlows(): CASBrainFlow[] {
  return [
    buildStateLookupFlow(),
    buildRecipeFlow(),
    buildFractalFlow(),
    buildInversionFlow(),
    buildBinaryCompositionFlow(),
  ];
}
