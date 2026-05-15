/**
 * CASBrainMap — 3D navigable view of the CAS-Native model topology.
 *
 * Replaces the prior cloud-shaped NeuralActivityMap with an actual
 * neural-network rendering: every named layer in cas_native_model.py +
 * nl_generation_head.py + typed_fiber_decoder.py shows up as a 3D node,
 * wired together by synapses, with a glowing thought-packet animation
 * flowing input -> encoder -> decoder -> output.
 *
 * This is brain-evocative, not anatomical. We're not claiming biological
 * brain structure. What you see is the real model graph rendered as a
 * navigable spatial diagram, plus a mock thought-flow until live Mode 7
 * activation capture is wired in for every layer.
 *
 * Patterns reused from SggsScene.tsx:
 *   - WebGLRenderer + PerspectiveCamera + OrbitControls
 *   - AdditiveBlending + DoubleSide halo planes
 *   - ResizeObserver -> renderer.setSize + camera.aspect
 *   - Full dispose() chain on unmount
 *   - rAF loop with performance.now()-driven animations
 *
 * Component contract is intentionally the same as NeuralActivityMap so the
 * swap in Mode7LiveShell is a one-line import change. Props are accepted
 * but not heavily consumed in v1 — when real Mode 7 head-commit streams
 * land for every layer, the same surface consumes them.
 */
import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from 'react';
import {
  AdditiveBlending,
  AmbientLight,
  BufferGeometry,
  CanvasTexture,
  Color,
  DirectionalLight,
  DoubleSide,
  Group,
  Line,
  LineBasicMaterial,
  LOD,
  Mesh,
  MeshBasicMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  Raycaster,
  Scene,
  SphereGeometry,
  Vector2,
  Vector3,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { SggsCommit } from '../../lib/sggs_stream';
import type { AtlasTraceThoughtTree } from '../../lib/trace';
import {
  buildMediumViewSubstructure,
  type MediumViewSubstructureHandle,
} from './MediumViewSubstructure';
import {
  buildCloseViewMatrixGrid,
  type CloseViewMatrixGridHandle,
} from './CloseViewMatrixGrid';
import {
  CAS_BRAIN_WEIGHTS,
  CAS_BRAIN_WEIGHTS_IS_SYNTHETIC,
  getCheckpointSha256Prefix,
  getSubMatricesForLayer,
} from '../../lib/cas_brain_weights';
import type { CASBrainLayer as LibCASBrainLayer } from '../../lib/cas_brain_mock_flow';
import { EvidencePacket } from '../evidence/EvidencePacket';

// ── LOD thresholds (camera-distance in scene-units) ───────────────────────
// Pulled out as named constants per PHASE_2_LOD_DESIGN.md §1 so QA can tune
// without grepping. The numbers are tuned for the default 0,6,38 camera and
// the existing 6..140 OrbitControls min/max distance.
const FAR_THRESHOLD = 36;
const MEDIUM_THRESHOLD = 18;

// Default camera framing for the Reset View tween + ESC reset.
const DEFAULT_CAMERA_POS: [number, number, number] = [0, 6, 38];
const DEFAULT_CAMERA_TARGET: [number, number, number] = [4, 0, 0];
const RESET_TWEEN_MS = 1000;

// ── Public component contract (mirrors NeuralActivityMap) ─────────────────

export interface CASBrainMapProps {
  tree: AtlasTraceThoughtTree;
  commits: readonly SggsCommit[];
  selectedNodeId?: string | null;
  runtimeReady?: boolean;
  onSelectNode?: (nodeId: string) => void;
  className?: string;
}

// ── Mock-flow data shape (inline until Agent B ships cas_brain_mock_flow.ts) ─

// TODO(@CASBrainMap): when noetic-compass/dashboard/src/lib/
// cas_brain_mock_flow.ts lands, swap the inline getStaticLayers /
// getStaticEdges / getMockFlows below for the lib version. The shape is
// identical so the swap is a single import-and-delete-inline change.

type LayerFamily =
  | 'embedding'
  | 'encoder_attn'
  | 'encoder_gate'
  | 'encoder_ffn'
  | 'special_branch'
  | 'decoder_attn'
  | 'decoder_ffn'
  | 'decoder_head'
  | 'output';

interface CASBrainLayer {
  id: string;
  family: LayerFamily;
  label: string;
  casPurpose: string;
  pipelinePosition: { stage: string; subIndex?: number; total?: number };
  dimensions: { d_model: number; n_heads?: number };
  position3d: { x: number; y: number; z: number };
  size: number;
  color: string;
  /**
   * Parameter count for this sub-module group on the v0.2 CAS-Native model.
   * Real numbers from the loaded checkpoint. Sum across all layers is
   * 115,866,624 (~115.87M) — same as the cas_brain_mock_flow lib totals.
   */
  paramCount: number;
}

interface CASBrainEdge {
  from: string;
  to: string;
  weight?: number;
}

interface CASBrainSignificantPoint {
  layerId: string;
  label: string;
  casToken: string;
}

interface CASBrainFlowFrame {
  tMs: number;
  activeLayerId: string;
  activationStrength: number;
  significantPoint?: CASBrainSignificantPoint;
}

interface CASBrainFlow {
  flowId: string;
  inputPromptPreview: string;
  durationMs: number;
  frames: CASBrainFlowFrame[];
}

// 7-color palette per spec.
const FAMILY_COLOR: Record<LayerFamily, string> = {
  embedding: '#60a5fa',
  encoder_attn: '#a78bfa',
  encoder_gate: '#fbbf24',
  encoder_ffn: '#2dd4bf',
  decoder_attn: '#fb7185',
  decoder_ffn: '#34d399',
  decoder_head: '#fde68a',
  special_branch: '#cbd5e1',
  output: '#38bdf8',
};

const N_ENCODER_BLOCKS = 6;
const N_DECODER_BLOCKS = 6;
const D_MODEL = 512;
const N_HEADS = 8;

// ── Parameter counts ─────────────────────────────────────────────────────
// Real numbers measured on the v0.2 CAS-Native checkpoint. Sub-modules that
// the inline graph does not split out separately (e.g. layer-norms inside a
// transformer block) are folded into the nearest semantic neighbor so the
// running total matches the architecture sum of 115,866,624 (~115.87M).
// Documented inline at each fold so deviations stay visible.
const PARAM_COUNT = {
  token_embedding: 12_486_656,
  cognitive_state_embedding: 141_608,
  // Sinusoidal positional encoding is param-free. Carry 1 so the node has
  // a visible size under log-scale rendering.
  positional_encoding: 1,

  // Per encoder block. enc_ffn absorbs the two per-block norms (2 × 1,024).
  enc_domain_attn: 1_313_280,
  enc_fractal_attn: 1_100_559,
  enc_rpm_gate: 1_575_936,
  enc_ffn: 2_101_760,

  enc_final_norm: 1_024,
  enc_lm_head: 12_486_656,

  topos_reasoner: 2_563_605,
  inversion_detector: 133_127,
  // The inline graph does not split out generative_head / lacunarity_gate /
  // lacunarity_head. We attach their combined weight (plus the residual
  // needed to land on the architecture sum of 115,866,624) to the
  // typed_fiber_decoder branch since it represents the parallel side-stack.
  typed_fiber_decoder: 906_848,

  // Decoder-side token embedding + learned positional embedding folded into
  // a single inline node (12,486,656 + 262,144 = 12,748,800).
  dec_token_embedding: 12_748_800,
  dec_soft_prefix: 133_120,

  // Per decoder block. dec_ffn absorbs per-block norms (folded by 256 vs.
  // table FFN to land on 4,204,032 block total).
  dec_self_attn: 1_051_008,
  dec_cross_attn: 1_051_008,
  dec_ffn: 2_102_016,

  register_film: 4_096,
  dec_final_norm: 1_024,
  dec_lm_head: 12_486_656,
  // Output is pure dataflow; carry 1 for visibility under log-scale sizing.
  output_stream: 1,
} as const;

// Total — verified to land on 115,866,624 = ~115.87M. Header stats chip
// reads this; node sizing reads layer.paramCount via Math.log10.
const TOTAL_PARAM_COUNT = (() => {
  let s = 0;
  s += PARAM_COUNT.token_embedding + PARAM_COUNT.cognitive_state_embedding + PARAM_COUNT.positional_encoding;
  s += N_ENCODER_BLOCKS * (PARAM_COUNT.enc_domain_attn + PARAM_COUNT.enc_fractal_attn + PARAM_COUNT.enc_rpm_gate + PARAM_COUNT.enc_ffn);
  s += PARAM_COUNT.enc_final_norm + PARAM_COUNT.enc_lm_head;
  s += PARAM_COUNT.topos_reasoner + PARAM_COUNT.inversion_detector + PARAM_COUNT.typed_fiber_decoder;
  s += PARAM_COUNT.dec_token_embedding + PARAM_COUNT.dec_soft_prefix;
  s += N_DECODER_BLOCKS * (PARAM_COUNT.dec_self_attn + PARAM_COUNT.dec_cross_attn + PARAM_COUNT.dec_ffn);
  s += PARAM_COUNT.register_film + PARAM_COUNT.dec_final_norm + PARAM_COUNT.dec_lm_head;
  s += PARAM_COUNT.output_stream;
  return s;
})();

/** Format a param count for the header chip (e.g. 115_866_624 -> "115.87M"). */
function formatParamCountShort(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

/** Format for hover tooltip — short form when >= 100K, thousands-separator otherwise. */
function formatParamCountHover(n: number): string {
  if (n >= 100_000) return `${(n / 1_000_000).toFixed(2)}M parameters`;
  return `${n.toLocaleString()} parameters`;
}

/** Format for pinned panel — "1.31M (1,313,280)". */
function formatParamCountFull(n: number): string {
  if (n >= 100_000) {
    return `${(n / 1_000_000).toFixed(2)}M (${n.toLocaleString()})`;
  }
  return n.toLocaleString();
}

/** Log-scale radius multiplier from paramCount. 12M -> ~1.0, 1K -> ~0.77. */
function paramCountRadiusScale(n: number): number {
  return 0.6 + 0.4 * (Math.log10(n + 1) / 7);
}

/**
 * Family-specific "What this layer does" explanations for the close-view
 * info panel. Verbatim from PHASE_2_LOD_DESIGN.md §4.3 (locked copy).
 */
const LAYER_EXPLANATIONS: Record<LayerFamily, string> = {
  embedding:
    "This layer turns input tokens into numbers the model can work with. Each token gets a unique vector; position information and CAS state information get added in on parallel branches.",
  encoder_attn:
    "This layer decides which CAS Domain (P / C / E / O) your thought belongs to. The Q / K / V projections build a query-key-value space; the output projection blends the attended values back into the model's main stream.",
  encoder_gate:
    "This layer enforces RPM — the rule that a thought can't 'fire' unless its prerequisites have already been satisfied. The gate decides whether downstream layers see the signal.",
  encoder_ffn:
    "A two-layer MLP that mixes the dimensions of whatever the attention layer just attended to. This is where most of the model's 'pattern memory' lives — the FFN weights store what kinds of features go with what.",
  special_branch:
    "This is a parallel head that reads the encoder's final state and produces its own structured output — truth values, inversion scores, lacunarity scores, or typed CAS tokens. It runs alongside the main pipeline rather than in series.",
  decoder_attn:
    "This layer mixes the partially-generated output with the encoded input. The self-attention block looks at what's been generated so far; the cross-attention block looks back at the encoded source so the next token stays grounded.",
  decoder_ffn:
    "A two-layer MLP on the decoder side, mirroring the encoder FFN. It refines the cross-attended representation before the next decoder block sees it.",
  decoder_head:
    "This is the Phenomenological Register modulator. It multiplies the decoder hidden state by a register-specific gamma/beta pair, steering the same content into transcendent, analytical, affective, or embodied operational character.",
  output:
    "The final projection from the model's hidden dimension to the English vocabulary. Each output position becomes a probability distribution over all possible next tokens; the highest-scoring token gets generated.",
};

/** Plain-English one-liner: "What these weights do" per family. */
function paramRoleSentence(layer: CASBrainLayer): string {
  switch (layer.family) {
    case 'embedding':
      return 'Maps each vocabulary token to a 512-dim vector.';
    case 'encoder_attn':
      return 'Q, K, V, and output projection matrices that decide what to attend to.';
    case 'encoder_gate':
      return 'Gating weights that fire when prerequisites are met.';
    case 'encoder_ffn':
      return 'Two-layer MLP that mixes the dimensions of the attended representation.';
    case 'special_branch':
      if (layer.id === 'topos_reasoner') return "Side network for the Topos Reasoner.";
      if (layer.id === 'inversion_detector') return 'Side network for the Inversion Detector.';
      if (layer.id === 'typed_fiber_decoder') return 'Side network for the Typed Fiber Decoder.';
      return 'Side network for a parallel CAS branch.';
    case 'decoder_attn':
      return "Self-attention + cross-attention into the encoder's representation.";
    case 'decoder_ffn':
      return 'MLP mixing the cross-attended features.';
    case 'decoder_head':
      return 'Projection back to the vocab — emits the actual CAS or English.';
    case 'output':
      return 'Projection back to the vocab — emits the actual CAS or English.';
    default:
      return 'Learned weights for this CAS-Native sub-module.';
  }
}

// ── Layout constants ──────────────────────────────────────────────────────
// Left-to-right pipeline. X = stage column, Y = sub-module row within a
// transformer block, Z = depth offset for side branches.

const STAGE_X = {
  inputEmbedding: -18,
  cogStateEmbedding: -14,
  positional: -10,
  encoderStart: -6,
  encoderEnd: 6,
  encoderFinal: 9,
  decoderStart: 12,
  decoderEnd: 20,
  decoderFinal: 23,
  output: 26,
};

function makeLayers(): CASBrainLayer[] {
  const layers: CASBrainLayer[] = [];

  // ── Encoder column (left) ────────────────────────────────────────────
  layers.push({
    id: 'token_embedding',
    family: 'embedding',
    label: 'Token Embedding',
    casPurpose:
      'Maps each input token to a dense vector the model can work with. This is the first place the prompt becomes math.',
    pipelinePosition: { stage: 'Input embedding', subIndex: 1, total: 3 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.inputEmbedding, y: 0, z: 0 },
    size: 1.2,
    color: FAMILY_COLOR.embedding,
    paramCount: PARAM_COUNT.token_embedding,
  });
  layers.push({
    id: 'cognitive_state_embedding',
    family: 'embedding',
    label: 'Cognitive State Embedding',
    casPurpose:
      'Projects each token onto the 40-state CAS simplex (10 Noetics x 4 Domains). This is the substrate that lets the rest of the model think in CAS terms.',
    pipelinePosition: { stage: 'Input embedding', subIndex: 2, total: 3 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.cogStateEmbedding, y: 0, z: 0 },
    size: 1.35,
    color: FAMILY_COLOR.embedding,
    paramCount: PARAM_COUNT.cognitive_state_embedding,
  });
  layers.push({
    id: 'positional_encoding',
    family: 'embedding',
    label: 'Positional Encoding',
    casPurpose:
      'Adds sinusoidal position information so the model knows the order of the tokens.',
    pipelinePosition: { stage: 'Input embedding', subIndex: 3, total: 3 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.positional, y: 0, z: 0 },
    size: 1.0,
    color: FAMILY_COLOR.embedding,
    paramCount: PARAM_COUNT.positional_encoding,
  });

  // 6 encoder transformer blocks. Each block is a tight little column with
  // 4 sub-modules stacked vertically. The block itself walks left -> right.
  const encXStep =
    (STAGE_X.encoderEnd - STAGE_X.encoderStart) / Math.max(1, N_ENCODER_BLOCKS - 1);
  for (let b = 0; b < N_ENCODER_BLOCKS; b++) {
    const x = STAGE_X.encoderStart + b * encXStep;
    layers.push({
      id: `enc_${b}_domain_attn`,
      family: 'encoder_attn',
      label: `Domain Descent Attention (Enc ${b + 1})`,
      casPurpose:
        'Attends across tokens with a P -> C -> E -> O domain mask. This is where the model decides which processing tier each thought belongs to.',
      pipelinePosition: {
        stage: 'Encoder transformer',
        subIndex: 1,
        total: 4,
      },
      dimensions: { d_model: D_MODEL, n_heads: N_HEADS },
      position3d: { x, y: 3.2, z: 0 },
      size: 1.15,
      color: FAMILY_COLOR.encoder_attn,
      paramCount: PARAM_COUNT.enc_domain_attn,
    });
    layers.push({
      id: `enc_${b}_fractal_attn`,
      family: 'encoder_attn',
      label: `Fractal Attention (Enc ${b + 1})`,
      casPurpose:
        'Multi-scale attention that picks up self-similar structure across the sequence. Blended with the Domain Descent output.',
      pipelinePosition: {
        stage: 'Encoder transformer',
        subIndex: 2,
        total: 4,
      },
      dimensions: { d_model: D_MODEL, n_heads: N_HEADS },
      position3d: { x, y: 1.2, z: 0 },
      size: 1.0,
      color: FAMILY_COLOR.encoder_attn,
      paramCount: PARAM_COUNT.enc_fractal_attn,
    });
    layers.push({
      id: `enc_${b}_rpm_gate`,
      family: 'encoder_gate',
      label: `Prerequisite Gate (Enc ${b + 1})`,
      casPurpose:
        'RPM gate. Asks the question: do the upstream prerequisites for this thought hold? If not, the gate dims that signal.',
      pipelinePosition: {
        stage: 'Encoder transformer',
        subIndex: 3,
        total: 4,
      },
      dimensions: { d_model: D_MODEL },
      position3d: { x, y: -0.8, z: 0 },
      size: 1.05,
      color: FAMILY_COLOR.encoder_gate,
      paramCount: PARAM_COUNT.enc_rpm_gate,
    });
    layers.push({
      id: `enc_${b}_ffn`,
      family: 'encoder_ffn',
      label: `FFN (Enc ${b + 1})`,
      casPurpose:
        'Feed-forward network. Standard transformer mixer that lets each position rework its own representation.',
      pipelinePosition: {
        stage: 'Encoder transformer',
        subIndex: 4,
        total: 4,
      },
      dimensions: { d_model: D_MODEL },
      position3d: { x, y: -2.8, z: 0 },
      size: 0.95,
      color: FAMILY_COLOR.encoder_ffn,
      paramCount: PARAM_COUNT.enc_ffn,
    });
  }

  // Encoder final norm + encoder LM head sit on the right edge of the stack.
  layers.push({
    id: 'enc_final_norm',
    family: 'encoder_ffn',
    label: 'Encoder Final Norm',
    casPurpose:
      'Layer normalization on the encoder output. Keeps the encoder state stable before the heads read it.',
    pipelinePosition: { stage: 'Encoder output', subIndex: 1, total: 2 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.encoderFinal, y: 1.4, z: 0 },
    size: 0.9,
    color: FAMILY_COLOR.encoder_ffn,
    paramCount: PARAM_COUNT.enc_final_norm,
  });
  layers.push({
    id: 'enc_lm_head',
    family: 'decoder_head',
    label: 'Encoder LM Head',
    casPurpose:
      'Projects the encoder hidden state to the vocabulary. Used during pre-training and as one of the supervision signals.',
    pipelinePosition: { stage: 'Encoder output', subIndex: 2, total: 2 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.encoderFinal, y: -1.4, z: 0 },
    size: 0.9,
    color: FAMILY_COLOR.decoder_head,
    paramCount: PARAM_COUNT.enc_lm_head,
  });

  // ── Side branches ────────────────────────────────────────────────────
  layers.push({
    id: 'topos_reasoner',
    family: 'special_branch',
    label: 'Cognitive Topos Reasoner',
    casPurpose:
      'Reads the pooled encoder state and emits intuitionistic 3-valued truth values over the ethical propositions. This is the model checking its own logical commitments.',
    pipelinePosition: { stage: 'Special branch', subIndex: 1, total: 3 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: 4, y: 7.8, z: 4 },
    size: 1.1,
    color: FAMILY_COLOR.special_branch,
    paramCount: PARAM_COUNT.topos_reasoner,
  });
  layers.push({
    id: 'inversion_detector',
    family: 'special_branch',
    label: 'Inversion Detector',
    casPurpose:
      'Scans for the 7 inversion axes (Operator, Domain, Drive, State, Sub-drive, Pathway, Compound). Fires when the thought looks like a shadow form of itself.',
    pipelinePosition: { stage: 'Special branch', subIndex: 2, total: 3 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: 4, y: -7.8, z: 4 },
    size: 1.1,
    color: FAMILY_COLOR.special_branch,
    paramCount: PARAM_COUNT.inversion_detector,
  });
  layers.push({
    id: 'typed_fiber_decoder',
    family: 'special_branch',
    label: 'Typed Fiber Decoder',
    casPurpose:
      'Side decoder for typed-slot supervision. Routes Omega, Stage variables, Coefficients, Register letters, Domain letters, Drive letters, and Fractal k-literals through a pointer-generator head.',
    pipelinePosition: { stage: 'Special branch', subIndex: 3, total: 3 },
    dimensions: { d_model: 384, n_heads: 6 },
    position3d: { x: 16, y: -7.8, z: 4 },
    size: 1.05,
    color: FAMILY_COLOR.special_branch,
    paramCount: PARAM_COUNT.typed_fiber_decoder,
  });

  // ── Decoder column (right) ───────────────────────────────────────────
  layers.push({
    id: 'dec_token_embedding',
    family: 'embedding',
    label: 'Decoder Token+Position Embedding',
    casPurpose:
      'Embeds the partially-generated decoder tokens (the running answer) with positions.',
    pipelinePosition: { stage: 'Decoder input', subIndex: 1, total: 2 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.decoderStart - 2, y: 0, z: 0 },
    size: 1.0,
    color: FAMILY_COLOR.embedding,
    paramCount: PARAM_COUNT.dec_token_embedding,
  });
  layers.push({
    id: 'dec_soft_prefix',
    family: 'embedding',
    label: 'Soft Prefix Projection',
    casPurpose:
      'Pulls the pooled CAS-Native bottleneck (64-dim) into a 4-position soft prefix that conditions the decoder. The bridge between CAS state and English generation.',
    pipelinePosition: { stage: 'Decoder input', subIndex: 2, total: 2 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.decoderStart - 2, y: -2.6, z: 0 },
    size: 1.0,
    color: FAMILY_COLOR.embedding,
    paramCount: PARAM_COUNT.dec_soft_prefix,
  });

  const decXStep =
    (STAGE_X.decoderEnd - STAGE_X.decoderStart) / Math.max(1, N_DECODER_BLOCKS - 1);
  for (let b = 0; b < N_DECODER_BLOCKS; b++) {
    const x = STAGE_X.decoderStart + b * decXStep;
    layers.push({
      id: `dec_${b}_self_attn`,
      family: 'decoder_attn',
      label: `Self-Attention (Dec ${b + 1})`,
      casPurpose:
        'Decoder self-attention. Lets each position attend to earlier decoded positions while staying causal.',
      pipelinePosition: {
        stage: 'Decoder transformer',
        subIndex: 1,
        total: 3,
      },
      dimensions: { d_model: D_MODEL, n_heads: N_HEADS },
      position3d: { x, y: 3.2, z: 0 },
      size: 1.1,
      color: FAMILY_COLOR.decoder_attn,
      paramCount: PARAM_COUNT.dec_self_attn,
    });
    layers.push({
      id: `dec_${b}_cross_attn`,
      family: 'decoder_attn',
      label: `Cross-Attention (Dec ${b + 1})`,
      casPurpose:
        'Reads the encoder hidden state. This is where the decoder gets to ask the encoder questions about the prompt.',
      pipelinePosition: {
        stage: 'Decoder transformer',
        subIndex: 2,
        total: 3,
      },
      dimensions: { d_model: D_MODEL, n_heads: N_HEADS },
      position3d: { x, y: 0.6, z: 0 },
      size: 1.1,
      color: FAMILY_COLOR.decoder_attn,
      paramCount: PARAM_COUNT.dec_cross_attn,
    });
    layers.push({
      id: `dec_${b}_ffn`,
      family: 'decoder_ffn',
      label: `FFN (Dec ${b + 1})`,
      casPurpose:
        'Decoder feed-forward network. The decoder-side mixer.',
      pipelinePosition: {
        stage: 'Decoder transformer',
        subIndex: 3,
        total: 3,
      },
      dimensions: { d_model: D_MODEL },
      position3d: { x, y: -2.0, z: 0 },
      size: 0.95,
      color: FAMILY_COLOR.decoder_ffn,
      paramCount: PARAM_COUNT.dec_ffn,
    });
  }

  // Decoder final layers + output.
  layers.push({
    id: 'register_film',
    family: 'decoder_head',
    label: 'Register FiLM',
    casPurpose:
      'Modulates the decoder output by the Phenomenological Register (T / A / f / E). Tone, stance, and register settle here.',
    pipelinePosition: { stage: 'Decoder output', subIndex: 1, total: 3 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.decoderFinal, y: 1.6, z: 0 },
    size: 1.05,
    color: FAMILY_COLOR.decoder_head,
    paramCount: PARAM_COUNT.register_film,
  });
  layers.push({
    id: 'dec_final_norm',
    family: 'decoder_ffn',
    label: 'Decoder Final Norm',
    casPurpose:
      'Layer normalization on the decoder output. Final stabilization before the LM head.',
    pipelinePosition: { stage: 'Decoder output', subIndex: 2, total: 3 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.decoderFinal, y: -0.4, z: 0 },
    size: 0.9,
    color: FAMILY_COLOR.decoder_ffn,
    paramCount: PARAM_COUNT.dec_final_norm,
  });
  layers.push({
    id: 'dec_lm_head',
    family: 'decoder_head',
    label: 'Decoder LM Head',
    casPurpose:
      'Projects the decoder hidden state to the English vocabulary. Picks the next word.',
    pipelinePosition: { stage: 'Decoder output', subIndex: 3, total: 3 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.decoderFinal, y: -2.4, z: 0 },
    size: 1.05,
    color: FAMILY_COLOR.decoder_head,
    paramCount: PARAM_COUNT.dec_lm_head,
  });

  layers.push({
    id: 'output_stream',
    family: 'output',
    label: 'Output Stream',
    casPurpose:
      'The final visible answer leaves the model here, one token at a time.',
    pipelinePosition: { stage: 'Output', subIndex: 1, total: 1 },
    dimensions: { d_model: D_MODEL },
    position3d: { x: STAGE_X.output, y: 0, z: 0 },
    size: 1.4,
    color: FAMILY_COLOR.output,
    paramCount: PARAM_COUNT.output_stream,
  });

  return layers;
}

function makeEdges(layers: CASBrainLayer[]): CASBrainEdge[] {
  const edges: CASBrainEdge[] = [];
  const has = new Set(layers.map((l) => l.id));
  const push = (from: string, to: string, weight = 1) => {
    if (has.has(from) && has.has(to)) edges.push({ from, to, weight });
  };

  // Embedding chain.
  push('token_embedding', 'cognitive_state_embedding', 1);
  push('cognitive_state_embedding', 'positional_encoding', 1);
  push('positional_encoding', 'enc_0_domain_attn', 1);

  // Each encoder block: domain_attn -> fractal_attn (parallel blend) -> rpm_gate -> ffn -> next block.
  for (let b = 0; b < N_ENCODER_BLOCKS; b++) {
    push(`enc_${b}_domain_attn`, `enc_${b}_fractal_attn`, 0.6);
    push(`enc_${b}_fractal_attn`, `enc_${b}_rpm_gate`, 1);
    push(`enc_${b}_domain_attn`, `enc_${b}_rpm_gate`, 0.6);
    push(`enc_${b}_rpm_gate`, `enc_${b}_ffn`, 1);
    if (b < N_ENCODER_BLOCKS - 1) {
      push(`enc_${b}_ffn`, `enc_${b + 1}_domain_attn`, 1);
    } else {
      push(`enc_${b}_ffn`, 'enc_final_norm', 1);
    }
  }
  push('enc_final_norm', 'enc_lm_head', 0.5);

  // Side branches read pooled encoder state.
  push('enc_final_norm', 'topos_reasoner', 0.55);
  push('enc_final_norm', 'inversion_detector', 0.55);

  // Decoder soft prefix consumes pooled encoder state too.
  push('enc_final_norm', 'dec_soft_prefix', 0.85);

  // Decoder input chain.
  push('dec_token_embedding', 'dec_0_self_attn', 1);
  push('dec_soft_prefix', 'dec_0_self_attn', 0.7);

  // Each decoder block: self_attn -> cross_attn (from encoder) -> ffn -> next.
  for (let b = 0; b < N_DECODER_BLOCKS; b++) {
    push(`dec_${b}_self_attn`, `dec_${b}_cross_attn`, 1);
    push('enc_final_norm', `dec_${b}_cross_attn`, 0.55);
    push(`dec_${b}_cross_attn`, `dec_${b}_ffn`, 1);
    if (b < N_DECODER_BLOCKS - 1) {
      push(`dec_${b}_ffn`, `dec_${b + 1}_self_attn`, 1);
    } else {
      push(`dec_${b}_ffn`, 'register_film', 1);
    }
  }
  push('register_film', 'dec_final_norm', 1);
  push('dec_final_norm', 'dec_lm_head', 1);
  push('dec_lm_head', 'output_stream', 1);

  // Typed Fiber Decoder pathway — reads encoder, writes to output.
  push('enc_final_norm', 'typed_fiber_decoder', 0.45);
  push('typed_fiber_decoder', 'output_stream', 0.55);

  return edges;
}

function getStaticLayers(): CASBrainLayer[] {
  return makeLayers();
}

function getStaticEdges(): CASBrainEdge[] {
  return makeEdges(getStaticLayers());
}

function getMockFlows(): CASBrainFlow[] {
  const layers = getStaticLayers();
  // A "flow" walks the canonical pipeline. We pick a representative path
  // through the encoder + decoder and tag a few structural commitments.
  const path: string[] = [
    'token_embedding',
    'cognitive_state_embedding',
    'positional_encoding',
    ...Array.from({ length: N_ENCODER_BLOCKS }).flatMap((_, b) => [
      `enc_${b}_domain_attn`,
      `enc_${b}_fractal_attn`,
      `enc_${b}_rpm_gate`,
      `enc_${b}_ffn`,
    ]),
    'enc_final_norm',
    'dec_soft_prefix',
    'dec_token_embedding',
    ...Array.from({ length: N_DECODER_BLOCKS }).flatMap((_, b) => [
      `dec_${b}_self_attn`,
      `dec_${b}_cross_attn`,
      `dec_${b}_ffn`,
    ]),
    'register_film',
    'dec_final_norm',
    'dec_lm_head',
    'output_stream',
  ].filter((id) => layers.some((l) => l.id === id));

  const totalMs = 4200;
  const stepMs = totalMs / path.length;

  function buildFrames(
    commits: ReadonlyArray<CASBrainSignificantPoint & { atLayerId: string }>,
  ): CASBrainFlowFrame[] {
    return path.map((id, idx) => {
      const sp = commits.find((c) => c.atLayerId === id);
      return {
        tMs: Math.round(idx * stepMs),
        activeLayerId: id,
        activationStrength: 0.45 + 0.5 * Math.sin((idx / path.length) * Math.PI),
        significantPoint: sp
          ? { layerId: id, label: sp.label, casToken: sp.casToken }
          : undefined,
      };
    });
  }

  return [
    {
      flowId: 'flow_idea',
      inputPromptPreview:
        'Trace the first principles behind a stakeholder decision...',
      durationMs: totalMs,
      frames: buildFrames([
        {
          atLayerId: 'cognitive_state_embedding',
          layerId: 'cognitive_state_embedding',
          label: 'Noetic locked',
          casToken: '^8',
        },
        {
          atLayerId: 'enc_2_domain_attn',
          layerId: 'enc_2_domain_attn',
          label: 'Domain settled',
          casToken: 'C',
        },
        {
          atLayerId: 'enc_4_rpm_gate',
          layerId: 'enc_4_rpm_gate',
          label: 'Prereqs satisfied',
          casToken: 'F2 OK',
        },
        {
          atLayerId: 'register_film',
          layerId: 'register_film',
          label: 'Register set',
          casToken: '|A',
        },
      ]),
    },
    {
      flowId: 'flow_principle',
      inputPromptPreview: 'Surface the principled stance behind the decision...',
      durationMs: totalMs,
      frames: buildFrames([
        {
          atLayerId: 'cognitive_state_embedding',
          layerId: 'cognitive_state_embedding',
          label: 'Noetic locked',
          casToken: '^3',
        },
        {
          atLayerId: 'enc_1_domain_attn',
          layerId: 'enc_1_domain_attn',
          label: 'Domain settled',
          casToken: 'P',
        },
        {
          atLayerId: 'enc_3_rpm_gate',
          layerId: 'enc_3_rpm_gate',
          label: 'Prereqs satisfied',
          casToken: 'F7 OK',
        },
        {
          atLayerId: 'inversion_detector',
          layerId: 'inversion_detector',
          label: 'No inversion',
          casToken: 'clean',
        },
        {
          atLayerId: 'register_film',
          layerId: 'register_film',
          label: 'Register set',
          casToken: '|T',
        },
      ]),
    },
    {
      flowId: 'flow_recipe',
      inputPromptPreview: 'Walk the recipe for the requested production target...',
      durationMs: totalMs,
      frames: buildFrames([
        {
          atLayerId: 'cognitive_state_embedding',
          layerId: 'cognitive_state_embedding',
          label: 'Noetic locked',
          casToken: '^6',
        },
        {
          atLayerId: 'enc_2_fractal_attn',
          layerId: 'enc_2_fractal_attn',
          label: 'Fractal blend',
          casToken: 'multi-scale',
        },
        {
          atLayerId: 'enc_5_rpm_gate',
          layerId: 'enc_5_rpm_gate',
          label: 'Prereqs satisfied',
          casToken: 'F6 OK',
        },
        {
          atLayerId: 'typed_fiber_decoder',
          layerId: 'typed_fiber_decoder',
          label: 'Typed slot fired',
          casToken: 'OMEGA',
        },
        {
          atLayerId: 'register_film',
          layerId: 'register_film',
          label: 'Register set',
          casToken: '|E',
        },
      ]),
    },
  ];
}

// ── Evidence mode (mirrors NeuralActivityMap's label semantics) ──────────

type EvidenceMode = 'real_mode7' | 'fallback_stream' | 'derived_trace' | 'mock_flow';

function evidenceMode(
  commits: readonly SggsCommit[],
  runtimeReady: boolean,
  tree: AtlasTraceThoughtTree,
): EvidenceMode {
  const headCount = commits.filter((c) => c.kind === 'head_commit').length;
  if (runtimeReady && headCount > 0) return 'real_mode7';
  if (headCount > 0) return 'fallback_stream';
  if (tree?.node_count > 1) return 'derived_trace';
  return 'mock_flow';
}

function evidenceLabel(mode: EvidenceMode): string {
  if (mode === 'real_mode7') return 'REAL MODE 7 STREAM';
  if (mode === 'fallback_stream') return 'FALLBACK STREAM';
  if (mode === 'derived_trace') return 'DERIVED TRACE';
  return 'MOCK FLOW';
}

function evidenceHelp(mode: EvidenceMode): string {
  if (mode === 'real_mode7')
    return 'Per-layer activation is coming from the live CAS Native predictor.';
  if (mode === 'fallback_stream')
    return 'Live stream is active but per-layer activation is partial.';
  if (mode === 'derived_trace')
    return 'Layer highlights are derived from the current trace graph, not raw activations.';
  return 'Idle view: a representative thought-flow drives the animation until real Mode 7 capture lands for every layer.';
}

// ── 3D node + halo builders (mirroring SggsScene patterns) ───────────────

interface BrainNodeBundle {
  /** Top-level LOD container that owns the far/medium/close children. */
  lod: LOD;
  /** Far-view group containing the legacy single sphere + halo. */
  farGroup: Group;
  body: Mesh;
  halo: Mesh;
  /** Medium-view substructure (Agent D builder) + handle. */
  mediumGroup: Group;
  mediumBuilder: MediumViewSubstructureHandle;
  /** Close-view matrix grids (Agent D builder) + handle. */
  closeGroup: Group;
  closeBuilder: CloseViewMatrixGridHandle;
  layer: CASBrainLayer;
  baseScale: number;
}

/**
 * Build a layer node as a THREE.LOD with three levels: far (legacy sphere
 * + halo), medium (Agent D substructure plates), close (Agent D matrix
 * grids). The LOD swaps which child is rendered based on the camera's
 * distance to the LOD's anchor position. Camera-distance thresholds are
 * pulled from `FAR_THRESHOLD` / `MEDIUM_THRESHOLD`.
 *
 * The `layer` argument is the inline CAS Brain Map layer type (no
 * `whyItMatters`); Agent D's builders expect the lib type, so we widen
 * with a synthesized `whyItMatters` derived from the family explanation.
 */
function buildLayerLOD(layer: CASBrainLayer): BrainNodeBundle {
  // Far view — the existing single sphere + halo.
  const radius = 0.45 * layer.size * paramCountRadiusScale(layer.paramCount);
  const farGroup = new Group();

  const bodyGeom = new SphereGeometry(radius, 18, 14);
  const bodyMat = new MeshBasicMaterial({
    color: new Color(layer.color),
    transparent: true,
    opacity: 0.85,
  });
  const body = new Mesh(bodyGeom, bodyMat);
  body.userData = { 'data-layer-id': layer.id, role: 'body' };
  farGroup.add(body);

  const haloTex = makeHaloTexture(layer.color);
  const haloMat = new MeshBasicMaterial({
    map: haloTex,
    transparent: true,
    opacity: 0.18,
    blending: AdditiveBlending,
    depthWrite: false,
    side: DoubleSide,
  });
  const halo = new Mesh(new PlaneGeometry(radius * 4.6, radius * 4.6), haloMat);
  halo.userData = { 'data-layer-id': layer.id, role: 'halo' };
  farGroup.add(halo);

  // Lib-type widening — Agent D's components only read the fields we
  // already have, but the lib `CASBrainLayer` is structurally wider.
  // Synthesize `whyItMatters` from the existing plain-English helper so
  // a downstream consumer that ever does read it still gets sensible copy.
  const libLayer: LibCASBrainLayer = {
    ...layer,
    whyItMatters: plainEnglishWhy(layer),
  } as LibCASBrainLayer;

  // Medium view — Agent D substructure plates.
  const mediumBuilder = buildMediumViewSubstructure({
    layer: libLayer,
    baseSize: radius,
    familyColor: layer.color,
    active: false,
  });
  const mediumGroup = mediumBuilder.group;

  // Close view — Agent D matrix grids, fed real (or fallback) weights.
  const closeBuilder = buildCloseViewMatrixGrid({
    layer: libLayer,
    subMatrices: getSubMatricesForLayer(layer.id),
    active: false,
  });
  const closeGroup = closeBuilder.group;

  // Wrap into the LOD with three distance bands.
  const lod = new LOD();
  lod.position.set(layer.position3d.x, layer.position3d.y, layer.position3d.z);
  lod.autoUpdate = true;
  // Lower threshold = nearer. So order is: closest first.
  lod.addLevel(closeGroup, 0);
  lod.addLevel(mediumGroup, MEDIUM_THRESHOLD);
  lod.addLevel(farGroup, FAR_THRESHOLD);

  return {
    lod,
    farGroup,
    body,
    halo,
    mediumGroup,
    mediumBuilder,
    closeGroup,
    closeBuilder,
    layer,
    baseScale: 1,
  };
}

function makeHaloTexture(strokeHex: string): CanvasTexture | null {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  const W = 256;
  const H = 256;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.clearRect(0, 0, W, H);
  const g = ctx.createRadialGradient(W / 2, H / 2, W * 0.08, W / 2, H / 2, W * 0.5);
  g.addColorStop(0, `${strokeHex}ee`);
  g.addColorStop(0.46, `${strokeHex}8c`);
  g.addColorStop(0.74, `${strokeHex}34`);
  g.addColorStop(1, `${strokeHex}00`);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  const tex = new CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

// Note: buildLayerLOD (above) supersedes the prior buildNodeMesh helper.
// It returns a THREE.LOD with three children — far (legacy sphere + halo),
// medium (Agent D plates), close (Agent D matrix grids) — and is the
// single entry point for layer-mesh construction.

// ── Component ────────────────────────────────────────────────────────────

export function CASBrainMap({
  tree,
  commits,
  selectedNodeId: _selectedNodeId,
  runtimeReady = false,
  onSelectNode: _onSelectNode,
  className,
}: CASBrainMapProps) {
  // The prop bindings exist for forward-compatibility with the real Mode 7
  // stream consumer. v1 deliberately does not consume per-layer activation
  // (it doesn't exist yet), but the MOCK FLOW evidence label makes that
  // honest, and the swap to real data is a function-body change.
  void _selectedNodeId;
  void _onSelectNode;

  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const sceneRootRef = useRef<HTMLDivElement | null>(null);

  // Three.js graph refs (outlive React renders).
  const sceneRef = useRef<Scene | null>(null);
  const cameraRef = useRef<PerspectiveCamera | null>(null);
  const rendererRef = useRef<WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const nodesRef = useRef<BrainNodeBundle[]>([]);
  const edgeLinesRef = useRef<Line[]>([]);
  const particleMeshRef = useRef<Mesh | null>(null);
  const flowsRef = useRef<CASBrainFlow[]>([]);
  const flowIndexRef = useRef(0);
  const flowStartedAtRef = useRef(0);
  const rafRef = useRef<number | null>(null);
  const raycasterRef = useRef<Raycaster | null>(null);
  const hoveredLayerIdRef = useRef<string | null>(null);
  /** Currently-firing layer in the mock flow. Drives Agent D pulses + Tour. */
  const activeLayerIdRef = useRef<string | null>(null);
  /** Cached id of the layer currently in close view (LOD level 0). */
  const closeLayerIdRef = useRef<string | null>(null);
  /** Reset-view tween state: start ms, start camera pos, start target. */
  const resetTweenStartRef = useRef<{
    startMs: number;
    fromPos: [number, number, number];
    fromTarget: [number, number, number];
  } | null>(null);
  /** Tour-mode toggle (true => auto-orbit + auto-zoom active layer). */
  const tourModeRef = useRef(false);
  /** Captured by the mount effect — Reset View button calls this on click. */
  const tickResetTweenFnRef = useRef<((now: number) => void) | null>(null);

  // React state for UI overlays.
  const [hovered, setHovered] = useState<{
    layer: CASBrainLayer;
    clientX: number;
    clientY: number;
  } | null>(null);
  const [pinned, setPinned] = useState<CASBrainLayer | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [significant, setSignificant] = useState<{
    layerId: string;
    label: string;
    casToken: string;
    untilMs: number;
  } | null>(null);
  const [flowPreview, setFlowPreview] = useState<string>('');
  /** Layer id currently at LOD close-view level (drives the side info panel). */
  const [closeLayerId, setCloseLayerId] = useState<string | null>(null);
  /** Tour Mode toggle, React-side mirror of tourModeRef (drives button label). */
  const [tourMode, setTourMode] = useState(false);
  // Evidence Packet drawer — v1 wires to the dev fixture trace. Real
  // wiring is per-thought-node and arrives when chat REPL / Atlas hand
  // off real trace_ids. Until then, the button surfaces the example
  // packet so stakeholders can audit the format end-to-end.
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [evidenceTraceId, setEvidenceTraceId] = useState<string>('dev_example_001');

  const mode = useMemo<EvidenceMode>(
    () => evidenceMode(commits, runtimeReady, tree),
    [commits, runtimeReady, tree],
  );

  const layers = useMemo(() => getStaticLayers(), []);
  const edges = useMemo(() => getStaticEdges(), []);
  const flows = useMemo(() => getMockFlows(), []);

  const layerById = useMemo(() => {
    const m = new Map<string, CASBrainLayer>();
    for (const l of layers) m.set(l.id, l);
    return m;
  }, [layers]);

  // ── Scene construction (mount-only) ───────────────────────────────────
  useEffect(() => {
    const wrapper = sceneRootRef.current;
    if (!wrapper) return;
    if (typeof window === 'undefined') return;

    const width = Math.max(wrapper.clientWidth, 1);
    const height = Math.max(wrapper.clientHeight, 1);

    const scene = new Scene();
    scene.background = new Color('#03040b');

    const camera = new PerspectiveCamera(48, width / height, 0.1, 400);
    camera.position.set(0, 6, 38);
    camera.lookAt(0, 0, 0);

    let renderer: WebGLRenderer;
    try {
      renderer = new WebGLRenderer({ antialias: true, alpha: false });
    } catch (err) {
      // Let SggsErrorBoundary catch this.
      throw err;
    }
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setSize(width, height);
    renderer.setClearColor(new Color('#03040b'), 1);
    wrapper.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('data-testid', 'cas-brain-canvas');
    renderer.domElement.style.display = 'block';
    renderer.domElement.style.outline = 'none';

    const ambient = new AmbientLight(0xffffff, 0.7);
    scene.add(ambient);
    const dir = new DirectionalLight(0xffffff, 0.4);
    dir.position.set(2, 4, 6);
    scene.add(dir);

    // Float group — everything that should drift gently in space lives here.
    // Lights stay on the scene root so they don't move with the structure.
    // The tick loop animates this group's position + rotation with a slow
    // sine wave for a "floating in zero-G" feel; amplitudes are tiny so
    // LOD distance thresholds + raycast hover/click remain stable.
    const floatGroup = new Group();
    scene.add(floatGroup);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;
    controls.minDistance = 6;
    controls.maxDistance = 140;
    controls.target.set(4, 0, 0);

    // Build nodes — each layer is a THREE.LOD wrapping far / medium /
    // close children. Camera-distance triggers swap automatically per
    // `lod.update(camera)` inside the rAF loop.
    const nodes: BrainNodeBundle[] = [];
    for (const layer of layers) {
      const bundle = buildLayerLOD(layer);
      floatGroup.add(bundle.lod);
      nodes.push(bundle);
    }

    // Build edge lines.
    const nodeById = new Map(nodes.map((n) => [n.layer.id, n]));
    const edgeLines: Line[] = [];
    for (const edge of edges) {
      const a = nodeById.get(edge.from);
      const b = nodeById.get(edge.to);
      if (!a || !b) continue;
      const geom = new BufferGeometry().setFromPoints([
        new Vector3(a.layer.position3d.x, a.layer.position3d.y, a.layer.position3d.z),
        new Vector3(b.layer.position3d.x, b.layer.position3d.y, b.layer.position3d.z),
      ]);
      const mat = new LineBasicMaterial({
        color: new Color(b.layer.color),
        transparent: true,
        opacity: 0.32 + 0.45 * (edge.weight ?? 1),
      });
      const line = new Line(geom, mat);
      line.userData = { from: edge.from, to: edge.to };
      floatGroup.add(line);
      edgeLines.push(line);
    }

    // One reusable particle (we move it along the active edge each frame).
    const particleGeom = new SphereGeometry(0.34, 14, 10);
    const particleMat = new MeshBasicMaterial({
      color: new Color('#fef3c7'),
      transparent: true,
      opacity: 0.95,
    });
    const particle = new Mesh(particleGeom, particleMat);
    floatGroup.add(particle);

    // Raycaster for hover/click.
    const raycaster = new Raycaster();

    function pickLayerFromPointer(ev: PointerEvent | MouseEvent): {
      layer: CASBrainLayer;
      bundle: BrainNodeBundle;
    } | null {
      if (!cameraRef.current) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      const nx = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      const ny = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(new Vector2(nx, ny), cameraRef.current);
      const bodies = nodesRef.current.map((n) => n.body);
      const hits = raycaster.intersectObjects(bodies, false);
      if (hits.length === 0) return null;
      const id = (hits[0].object.userData as { 'data-layer-id'?: string })[
        'data-layer-id'
      ];
      if (!id) return null;
      const bundle = nodesRef.current.find((n) => n.layer.id === id);
      if (!bundle) return null;
      return { layer: bundle.layer, bundle };
    }

    function onPointerMove(ev: PointerEvent) {
      const hit = pickLayerFromPointer(ev);
      if (hit) {
        hoveredLayerIdRef.current = hit.layer.id;
        setHovered({ layer: hit.layer, clientX: ev.clientX, clientY: ev.clientY });
        renderer.domElement.style.cursor = 'pointer';
      } else {
        hoveredLayerIdRef.current = null;
        setHovered(null);
        renderer.domElement.style.cursor = 'grab';
      }
    }
    function onPointerLeave() {
      hoveredLayerIdRef.current = null;
      setHovered(null);
      renderer.domElement.style.cursor = 'grab';
    }
    function onPointerDown(ev: PointerEvent) {
      // Only left button picks; orbit owns the rest.
      if (ev.button !== 0) return;
      const hit = pickLayerFromPointer(ev);
      if (hit) {
        setPinned(hit.layer);
      }
    }
    renderer.domElement.addEventListener('pointermove', onPointerMove);
    renderer.domElement.addEventListener('pointerleave', onPointerLeave);
    renderer.domElement.addEventListener('pointerdown', onPointerDown);

    const ro = new ResizeObserver(() => {
      const w = Math.max(wrapper.clientWidth, 1);
      const h = Math.max(wrapper.clientHeight, 1);
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });
    ro.observe(wrapper);

    // ── Reset-view tween ──────────────────────────────────────────────
    // EaseInOutCubic per design spec.
    function easeInOutCubic(t: number): number {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    function tickResetTween(now: number): void {
      const state = resetTweenStartRef.current;
      if (!state) return;
      const elapsed = now - state.startMs;
      const t = Math.min(1, elapsed / RESET_TWEEN_MS);
      const e = easeInOutCubic(t);
      camera.position.set(
        state.fromPos[0] + (DEFAULT_CAMERA_POS[0] - state.fromPos[0]) * e,
        state.fromPos[1] + (DEFAULT_CAMERA_POS[1] - state.fromPos[1]) * e,
        state.fromPos[2] + (DEFAULT_CAMERA_POS[2] - state.fromPos[2]) * e,
      );
      controls.target.set(
        state.fromTarget[0] + (DEFAULT_CAMERA_TARGET[0] - state.fromTarget[0]) * e,
        state.fromTarget[1] + (DEFAULT_CAMERA_TARGET[1] - state.fromTarget[1]) * e,
        state.fromTarget[2] + (DEFAULT_CAMERA_TARGET[2] - state.fromTarget[2]) * e,
      );
      if (t >= 1) {
        resetTweenStartRef.current = null;
      }
    }

    // ── Tour mode: slowly orbit + zoom toward the active layer ────────
    function tickTourMode(now: number): void {
      if (!tourModeRef.current) return;
      const activeId = activeLayerIdRef.current;
      if (!activeId) return;
      const node = nodesRef.current.find((n) => n.layer.id === activeId);
      if (!node) return;
      // Move OrbitControls target toward the active layer's anchor.
      const lp = node.layer.position3d;
      controls.target.set(
        controls.target.x + (lp.x - controls.target.x) * 0.03,
        controls.target.y + (lp.y - controls.target.y) * 0.03,
        controls.target.z + (lp.z - controls.target.z) * 0.03,
      );
      // Pull camera in slowly toward a close-view distance, with a
      // slow orbit around the active layer's anchor.
      const desiredDist = 20;
      const dx = camera.position.x - lp.x;
      const dy = camera.position.y - lp.y;
      const dz = camera.position.z - lp.z;
      const curDist = Math.sqrt(dx * dx + dy * dy + dz * dz);
      const newDist = curDist + (desiredDist - curDist) * 0.01;
      // Orbit angle increments slowly.
      const orbitOmega = 0.00015;
      const angle = now * orbitOmega;
      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);
      camera.position.set(
        lp.x + newDist * cosA,
        lp.y + 4,
        lp.z + newDist * sinA,
      );
    }

    // Stash for the React-side button click handler.
    tickResetTweenFnRef.current = (now: number) => {
      resetTweenStartRef.current = {
        startMs: now,
        fromPos: [camera.position.x, camera.position.y, camera.position.z],
        fromTarget: [controls.target.x, controls.target.y, controls.target.z],
      };
    };

    // Disable Tour Mode the moment the user grabs the orbit controls.
    const onOrbitStart = () => {
      if (tourModeRef.current) {
        tourModeRef.current = false;
        setTourMode(false);
      }
    };
    controls.addEventListener('start', onOrbitStart);

    // ── Animation loop ────────────────────────────────────────────────
    let lastFrameMs = 0;
    function tick() {
      rafRef.current = requestAnimationFrame(tick);
      const now = performance.now();
      const dt = lastFrameMs === 0 ? 0 : Math.min(0.1, (now - lastFrameMs) / 1000);
      lastFrameMs = now;

      // Gentle floating-in-space drift on the whole structure. Tiny
      // amplitudes so LOD distance triggers + raycast hover stay stable.
      // We ease toward zero when a layer is in close-view so stakeholders
      // can inspect matrices without the scene swaying under them.
      const closeViewActive = closeLayerIdRef.current !== null;
      const floatScale = closeViewActive ? 0.0 : 1.0;
      const floatPrev = floatGroup.userData.floatScale ?? 1.0;
      const floatLerped = floatPrev + (floatScale - floatPrev) * 0.08;
      floatGroup.userData.floatScale = floatLerped;
      const t = now / 1000;
      floatGroup.position.y = Math.sin(t / 4.5) * 1.2 * floatLerped;
      floatGroup.position.x = Math.cos(t / 6.2) * 0.55 * floatLerped;
      floatGroup.position.z = Math.sin(t / 8.0) * 0.4 * floatLerped;
      floatGroup.rotation.x = Math.sin(t / 7.0) * 0.05 * floatLerped;
      floatGroup.rotation.y = Math.cos(t / 9.0) * 0.065 * floatLerped;
      floatGroup.rotation.z = Math.sin(t / 11.0) * 0.035 * floatLerped;

      // Reset-view tween: lerp camera + controls target into the default
      // far framing. Runs whenever resetTweenStartRef.current is non-null.
      tickResetTween(now);
      tickTourMode(now);

      // THREE.LOD swaps the rendered child based on camera distance. Has
      // to be called explicitly when the camera moves.
      for (const node of nodesRef.current) {
        node.lod.update(camera);
      }
      // Detect close view + propagate to React state for the info panel.
      const closeLayer = nodesRef.current.find(
        (n) => n.lod.getCurrentLevel() === 0,
      );
      const closeId = closeLayer?.layer.id ?? null;
      if (closeId !== closeLayerIdRef.current) {
        closeLayerIdRef.current = closeId;
        setCloseLayerId(closeId);
      }

      // Halos face the camera + subtle pulse + focus dim.
      const pulse = (Math.sin(now / 800) + 1) / 2;
      const anyClose = closeId !== null;
      for (const node of nodesRef.current) {
        node.halo.quaternion.copy(camera.quaternion);
        const isHovered = node.layer.id === hoveredLayerIdRef.current;
        const isFocused = anyClose && node.layer.id === closeId;
        const targetBodyOpacity = anyClose && !isFocused ? 0.2 : 0.85;
        const targetHaloOpacity = anyClose && !isFocused
          ? 0.05
          : (isHovered ? 0.42 : 0.16 + pulse * 0.04);
        const bodyMat = node.body.material as MeshBasicMaterial;
        const haloMat = node.halo.material as MeshBasicMaterial;
        bodyMat.transparent = true;
        haloMat.transparent = true;
        // Lerp opacities smoothly so dim/restore feels natural.
        bodyMat.opacity += (targetBodyOpacity - bodyMat.opacity) * 0.15;
        haloMat.opacity += (targetHaloOpacity - haloMat.opacity) * 0.15;
        // Subtle body opacity pulse for the special branches stays only
        // when nothing is in close view.
        if (!anyClose && node.layer.family === 'special_branch') {
          bodyMat.opacity = 0.65 + 0.18 * pulse;
        }

        // Tick Agent D builders for medium + close.
        const active = node.layer.id === activeLayerIdRef.current;
        node.mediumBuilder.update(active, dt);
        node.closeBuilder.update(dt, active);
      }

      // ── Active flow ─────────────────────────────────────────────────
      const list = flowsRef.current;
      if (list.length > 0) {
        const flow = list[flowIndexRef.current % list.length];
        if (flowStartedAtRef.current === 0) {
          flowStartedAtRef.current = now;
          setFlowPreview(flow.inputPromptPreview);
        }
        const elapsed = now - flowStartedAtRef.current;
        if (elapsed >= flow.durationMs) {
          flowIndexRef.current = (flowIndexRef.current + 1) % list.length;
          flowStartedAtRef.current = now;
        } else {
          // Find the frame interval that contains `elapsed`.
          const frames = flow.frames;
          let i = 0;
          while (i < frames.length - 1 && frames[i + 1].tMs <= elapsed) i++;
          const cur = frames[i];
          const nxt = frames[Math.min(frames.length - 1, i + 1)];
          const segDur = Math.max(1, nxt.tMs - cur.tMs);
          const segT = Math.min(1, (elapsed - cur.tMs) / segDur);

          const a = layerById.get(cur.activeLayerId);
          const b = layerById.get(nxt.activeLayerId);
          if (a && b) {
            const ax = a.position3d.x;
            const ay = a.position3d.y;
            const az = a.position3d.z;
            const bx = b.position3d.x;
            const by = b.position3d.y;
            const bz = b.position3d.z;
            particle.position.set(
              ax + (bx - ax) * segT,
              ay + (by - ay) * segT,
              az + (bz - az) * segT,
            );
            const t = Math.min(1, segT * 2);
            (particle.material as MeshBasicMaterial).color.set(b.color);
            (particle.material as MeshBasicMaterial).opacity = 0.85 + 0.1 * Math.sin(now / 80);
            const scale = 0.85 + 0.4 * Math.sin(t * Math.PI);
            particle.scale.set(scale, scale, scale);

            // Light up the currently-active node and propagate to the
            // active-layer ref so Agent D builders + Tour mode know.
            activeLayerIdRef.current = cur.activeLayerId;
            for (const node of nodesRef.current) {
              const isActive = node.layer.id === cur.activeLayerId;
              if (isActive) {
                node.body.scale.set(1.18, 1.18, 1.18);
              } else if (
                node.layer.id !== hoveredLayerIdRef.current &&
                node.body.scale.x !== node.baseScale
              ) {
                // Decay back to baseline.
                const s = node.body.scale.x;
                const next = s + (node.baseScale - s) * 0.18;
                node.body.scale.set(next, next, next);
              }
            }
          }

          // Significant point pop-up.
          if (cur.significantPoint && (!significant || significant.layerId !== cur.activeLayerId || significant.untilMs < now)) {
            setSignificant({
              layerId: cur.activeLayerId,
              label: cur.significantPoint.label,
              casToken: cur.significantPoint.casToken,
              untilMs: now + 1500,
            });
          }
        }
      }

      if (significant && significant.untilMs < now) {
        setSignificant(null);
      }

      controls.update();
      renderer.render(scene, camera);
    }

    sceneRef.current = scene;
    cameraRef.current = camera;
    rendererRef.current = renderer;
    controlsRef.current = controls;
    nodesRef.current = nodes;
    edgeLinesRef.current = edgeLines;
    particleMeshRef.current = particle;
    flowsRef.current = flows;
    flowIndexRef.current = 0;
    flowStartedAtRef.current = 0;
    raycasterRef.current = raycaster;

    tick();

    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      ro.disconnect();
      renderer.domElement.removeEventListener('pointermove', onPointerMove);
      renderer.domElement.removeEventListener('pointerleave', onPointerLeave);
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      for (const node of nodes) {
        // Far view: dispose legacy body + halo materials/geometries.
        node.body.geometry.dispose();
        (node.body.material as MeshBasicMaterial).dispose();
        node.halo.geometry.dispose();
        const mat = node.halo.material as MeshBasicMaterial;
        if (mat.map) mat.map.dispose();
        mat.dispose();
        // Medium + close: delegate to Agent D's per-handle dispose().
        node.mediumBuilder.dispose();
        node.closeBuilder.dispose();
        scene.remove(node.lod);
      }
      for (const line of edgeLines) {
        line.geometry.dispose();
        (line.material as LineBasicMaterial).dispose();
        scene.remove(line);
      }
      particle.geometry.dispose();
      (particle.material as MeshBasicMaterial).dispose();
      scene.remove(particle);
      controls.removeEventListener('start', onOrbitStart);
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentElement === wrapper) {
        wrapper.removeChild(renderer.domElement);
      }
      tickResetTweenFnRef.current = null;
      sceneRef.current = null;
      cameraRef.current = null;
      rendererRef.current = null;
      controlsRef.current = null;
      nodesRef.current = [];
      edgeLinesRef.current = [];
      particleMeshRef.current = null;
      raycasterRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layers, edges, flows]);

  // Fullscreen API + state.
  useEffect(() => {
    const onChange = () => {
      setFullscreen(document.fullscreenElement === wrapperRef.current);
    };
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

  const toggleFullscreen = useCallback(() => {
    const el = wrapperRef.current;
    if (!el) return;
    if (document.fullscreenElement === el) {
      void document.exitFullscreen?.();
    } else {
      void el.requestFullscreen?.();
    }
  }, []);

  const handleResetView = useCallback(() => {
    const start = tickResetTweenFnRef.current;
    if (!start) return;
    // Also drop Tour mode when the user explicitly resets.
    tourModeRef.current = false;
    setTourMode(false);
    start(performance.now());
  }, []);

  const handleToggleTour = useCallback(() => {
    const next = !tourModeRef.current;
    tourModeRef.current = next;
    setTourMode(next);
  }, []);

  // ESC: reset camera when in close view; always disable Tour mode.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      // Skip when fullscreen is exiting — browser already handles that key.
      if (closeLayerIdRef.current !== null) {
        handleResetView();
      } else if (tourModeRef.current) {
        tourModeRef.current = false;
        setTourMode(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [handleResetView]);

  const containerStyle: CSSProperties = {
    height: fullscreen ? '100vh' : 800,
    width: '100%',
    position: 'relative',
  };

  const familyLegend: ReadonlyArray<{ family: LayerFamily; label: string }> = [
    { family: 'embedding', label: 'Embedding' },
    { family: 'encoder_attn', label: 'Encoder attention' },
    { family: 'encoder_gate', label: 'RPM gate' },
    { family: 'encoder_ffn', label: 'Encoder FFN' },
    { family: 'decoder_attn', label: 'Decoder attention' },
    { family: 'decoder_ffn', label: 'Decoder FFN' },
    { family: 'decoder_head', label: 'LM head / Register' },
    { family: 'special_branch', label: 'Special branch' },
    { family: 'output', label: 'Output' },
  ];

  return (
    <section
      ref={wrapperRef}
      data-testid="cas-brain-map"
      style={containerStyle}
      className={[
        'overflow-hidden rounded-lg border border-cyan-400/20 bg-slate-950/85',
        'shadow-[0_0_42px_rgba(34,211,238,0.10)]',
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="absolute left-0 right-0 top-0 z-20 flex flex-wrap items-start justify-between gap-3 border-b border-white/[0.06] bg-slate-950/70 px-4 py-3 backdrop-blur-sm">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-cyan-300">
            CAS Brain Map
          </div>
          <h2 className="mt-1 text-base font-semibold text-slate-100">
            The CAS Native model, rendered as its actual network
          </h2>
          <p className="mt-1 max-w-xl text-xs leading-relaxed text-slate-400">
            Every named layer of the encoder, decoder, and special branches
            is a node here. Drag to orbit, scroll to zoom. Brain-evocative,
            not anatomical.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="rounded-md border border-cyan-300/20 bg-cyan-500/10 px-3 py-1.5 text-right"
            data-testid="cas-brain-stats-chip"
          >
            <div className="font-mono text-[9px] uppercase tracking-wider text-cyan-200">
              Architecture
            </div>
            <div className="mt-0.5 font-mono text-[11px] leading-snug text-slate-100">
              {formatParamCountShort(TOTAL_PARAM_COUNT)} params
              {' · '}6+6 transformer blocks
              {' · '}d_model {D_MODEL}
            </div>
          </div>
          <div className="rounded-md border border-cyan-300/20 bg-cyan-500/10 px-3 py-1.5 text-right">
            <div className="font-mono text-[9px] uppercase tracking-wider text-cyan-200">
              {evidenceLabel(mode)}
            </div>
            <div className="mt-0.5 max-w-[260px] text-[11px] leading-snug text-slate-300">
              {evidenceHelp(mode)}
            </div>
          </div>
          <button
            type="button"
            onClick={handleResetView}
            aria-label="Reset view"
            title="Reset camera to default framing"
            data-testid="cas-brain-reset-view"
            className="flex h-9 items-center justify-center rounded-md border border-white/[0.08] bg-black/40 px-3 text-xs text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
          >
            Reset view
          </button>
          <button
            type="button"
            onClick={handleToggleTour}
            aria-pressed={tourMode}
            aria-label={tourMode ? 'Disable tour mode' : 'Enable tour mode'}
            title="Auto-orbit + auto-zoom the currently-firing layer"
            data-testid="cas-brain-tour-mode"
            className={[
              'flex h-9 items-center justify-center rounded-md border px-3 text-xs transition-colors',
              tourMode
                ? 'border-amber-300/40 bg-amber-500/20 text-amber-50 hover:bg-amber-500/30'
                : 'border-white/[0.08] bg-black/40 text-slate-200 hover:bg-white/10 hover:text-white',
            ].join(' ')}
          >
            {tourMode ? 'Tour mode: on' : 'Tour mode: off'}
          </button>
          <button
            type="button"
            onClick={() => {
              setEvidenceTraceId('dev_example_001');
              setEvidenceOpen(true);
            }}
            aria-label="Open evidence packet"
            title="Open the Evidence Packet for this thought — input, CAS, hashes, claim levels"
            data-testid="cas-brain-open-evidence"
            className="flex h-9 items-center justify-center rounded-md border border-emerald-300/30 bg-emerald-500/15 px-3 text-xs text-emerald-100 transition-colors hover:bg-emerald-500/25 hover:text-emerald-50"
          >
            Open Evidence
          </button>
          <button
            type="button"
            onClick={toggleFullscreen}
            aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            title={fullscreen ? 'Exit fullscreen' : 'Fullscreen the CAS Brain Map'}
            className="flex h-9 w-9 items-center justify-center rounded-md border border-white/[0.08] bg-black/40 text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
          >
            {fullscreen ? (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M8 3v3a2 2 0 0 1-2 2H3" />
                <path d="M21 8h-3a2 2 0 0 1-2-2V3" />
                <path d="M3 16h3a2 2 0 0 1 2 2v3" />
                <path d="M16 21v-3a2 2 0 0 1 2-2h3" />
              </svg>
            ) : (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 7V5a2 2 0 0 1 2-2h2" />
                <path d="M17 3h2a2 2 0 0 1 2 2v2" />
                <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
                <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
              </svg>
            )}
          </button>
        </div>
      </div>

      <div ref={sceneRootRef} className="absolute inset-0 cursor-grab" />

      {/* Hover tooltip */}
      {hovered && (
        <div
          className="pointer-events-none absolute z-30 max-w-xs rounded-md border border-white/[0.08] bg-black/85 px-3 py-2 text-xs text-slate-100 shadow-lg backdrop-blur-sm"
          style={{
            left: Math.min(
              hovered.clientX -
                (wrapperRef.current?.getBoundingClientRect().left ?? 0) +
                14,
              (wrapperRef.current?.clientWidth ?? 0) - 280,
            ),
            top:
              hovered.clientY -
              (wrapperRef.current?.getBoundingClientRect().top ?? 0) +
              14,
          }}
        >
          <div className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
            {hovered.layer.pipelinePosition.stage}
            {hovered.layer.pipelinePosition.subIndex && hovered.layer.pipelinePosition.total
              ? ` - ${hovered.layer.pipelinePosition.subIndex} of ${hovered.layer.pipelinePosition.total}`
              : ''}
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-100">
            {hovered.layer.label}
          </div>
          <div className="mt-1 text-[11px] leading-relaxed text-slate-300">
            {hovered.layer.casPurpose}
          </div>
          <div className="mt-2 font-mono text-[10px] text-cyan-200">
            {formatParamCountHover(hovered.layer.paramCount)}
          </div>
          <div className="mt-1 font-mono text-[10px] text-slate-500">
            d_model={hovered.layer.dimensions.d_model}
            {hovered.layer.dimensions.n_heads !== undefined
              ? ` , heads=${hovered.layer.dimensions.n_heads}`
              : ''}
          </div>
        </div>
      )}

      {/* Significant-point badge near the active node */}
      {significant && (
        <SignificantBadge
          layer={layerById.get(significant.layerId)}
          label={significant.label}
          casToken={significant.casToken}
          camera={cameraRef.current}
          rendererEl={rendererRef.current?.domElement ?? null}
        />
      )}

      {/* Bottom info bar */}
      <div className="pointer-events-none absolute bottom-3 left-3 right-3 z-20 flex flex-wrap items-center justify-between gap-2 rounded-md border border-white/[0.08] bg-black/55 px-3 py-2 text-xs text-slate-300 backdrop-blur-sm">
        <span className="truncate">
          <span className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
            flow
          </span>{' '}
          {flowPreview || 'priming...'}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
          {layers.length} layers · {edges.length} synapses · {flows.length} mock flows
        </span>
      </div>

      {/* Family legend (top-left, below header — clears the 2-line subtitle) */}
      <div className="pointer-events-none absolute left-3 top-[180px] z-20 hidden gap-2 rounded-md border border-white/[0.08] bg-black/55 px-3 py-2 text-xs text-slate-300 backdrop-blur-sm md:flex md:flex-wrap md:max-w-md">
        {familyLegend.map((entry) => (
          <span key={entry.family} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              style={{ background: FAMILY_COLOR[entry.family] }}
              className="inline-block h-2.5 w-2.5 rounded-full"
            />
            <span className="text-[11px] text-slate-300">{entry.label}</span>
          </span>
        ))}
      </div>

      {/* Click-to-pin side panel — top matches the family legend for visual balance */}
      {pinned && (
        <aside
          className="absolute right-3 top-[180px] z-30 max-h-[calc(100%-212px)] w-80 overflow-y-auto rounded-md border border-cyan-300/25 bg-black/85 p-4 text-sm text-slate-200 shadow-xl backdrop-blur-sm"
          role="dialog"
          aria-label={`Layer details: ${pinned.label}`}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
                {pinned.pipelinePosition.stage}
                {pinned.pipelinePosition.subIndex && pinned.pipelinePosition.total
                  ? ` - ${pinned.pipelinePosition.subIndex} of ${pinned.pipelinePosition.total}`
                  : ''}
              </div>
              <h3 className="mt-1 text-base font-semibold text-slate-100">
                {pinned.label}
              </h3>
            </div>
            <button
              type="button"
              onClick={() => setPinned(null)}
              aria-label="Close layer details"
              className="rounded border border-white/[0.08] bg-white/[0.04] px-2 py-1 font-mono text-[10px] text-slate-300 hover:bg-white/10"
            >
              close
            </button>
          </div>

          <p className="mt-3 text-[12px] leading-relaxed text-slate-300">
            {pinned.casPurpose}
          </p>

          <dl className="mt-4 space-y-2 text-[12px]">
            <div className="rounded border border-white/[0.06] bg-white/[0.03] p-2">
              <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Dimensions
              </dt>
              <dd className="mt-1 text-slate-100">
                d_model = {pinned.dimensions.d_model}
                {pinned.dimensions.n_heads !== undefined
                  ? ` , heads = ${pinned.dimensions.n_heads}`
                  : ''}
              </dd>
            </div>
            <div className="rounded border border-white/[0.06] bg-white/[0.03] p-2">
              <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Family
              </dt>
              <dd className="mt-1 text-slate-100">
                {pinned.family.replace(/_/g, ' ')}
              </dd>
            </div>
            <div className="rounded border border-white/[0.06] bg-white/[0.03] p-2">
              <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Parameters
              </dt>
              <dd className="mt-1 font-mono text-[11px] text-slate-100">
                {formatParamCountFull(pinned.paramCount)}
              </dd>
              <dd className="mt-1 text-[11px] leading-relaxed text-slate-400">
                <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  What these weights do:
                </span>{' '}
                {paramRoleSentence(pinned)}
              </dd>
            </div>
            <div className="rounded border border-white/[0.06] bg-white/[0.03] p-2">
              <dt className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Recent activation (mock)
              </dt>
              <dd className="mt-1 text-[11px] leading-relaxed text-slate-300">
                <RecentActivationList layerId={pinned.id} flows={flows} />
              </dd>
            </div>
          </dl>

          <div className="mt-4 rounded border border-cyan-300/15 bg-cyan-500/[0.06] p-3">
            <div className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
              Why this matters
            </div>
            <p className="mt-2 text-[12px] leading-relaxed text-slate-300">
              {plainEnglishWhy(pinned)}
            </p>
          </div>
        </aside>
      )}

      {/* Close-view info panel + synthetic-weights banner (per
          PHASE_2_LOD_DESIGN.md §4.2 / §7.2). Renders only when the LOD
          has swapped a layer into the close-view level. */}
      {closeLayerId && (
        <CloseViewInfoPanel
          layer={layerById.get(closeLayerId) ?? null}
          synthetic={CAS_BRAIN_WEIGHTS_IS_SYNTHETIC}
        />
      )}

      {/* Evidence Packet drawer — v1 dev fixture mount. Real per-thought
          trace_ids arrive when chat REPL / Atlas wire handoffs. */}
      <EvidencePacket
        traceId={evidenceTraceId}
        open={evidenceOpen}
        onClose={() => setEvidenceOpen(false)}
      />
    </section>
  );
}

// ── Close-view info panel ────────────────────────────────────────────────

interface CloseViewInfoPanelProps {
  layer: CASBrainLayer | null;
  synthetic: boolean;
}

function CloseViewInfoPanel({ layer, synthetic }: CloseViewInfoPanelProps) {
  if (!layer) return null;
  const checkpointId = CAS_BRAIN_WEIGHTS.checkpoint_id;
  const shaPrefix = getCheckpointSha256Prefix(8);
  const downsample = CAS_BRAIN_WEIGHTS.downsample_grid;
  const fullParams = layer.paramCount;
  const cells = downsample * downsample;
  const avgPerCell = Math.max(1, Math.round(fullParams / cells));
  const explanation = LAYER_EXPLANATIONS[layer.family];
  return (
    <aside
      data-testid="cas-brain-close-info-panel"
      className="absolute right-3 top-[180px] z-40 max-h-[calc(100%-212px)] w-96 overflow-y-auto rounded-md border border-cyan-300/30 bg-black/90 text-sm text-slate-200 shadow-xl backdrop-blur-sm"
      role="dialog"
      aria-label={`Close view: ${layer.label}`}
    >
      {synthetic && (
        <div
          data-testid="cas-brain-synthetic-banner"
          className="border-b border-amber-200/40 bg-amber-300/90 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-amber-950"
        >
          SYNTHETIC WEIGHTS — illustrative only
        </div>
      )}
      <div className="p-4">
        <div
          className="text-[17px] font-semibold"
          style={{ color: FAMILY_COLOR[layer.family] }}
        >
          {layer.label}
        </div>
        <div className="mt-1 text-[12px] text-slate-400">
          {layer.family.replace(/_/g, ' ')} · {formatParamCountHover(fullParams)}
        </div>

        {synthetic ? (
          <div className="mt-4 text-[13px] leading-relaxed text-slate-300">
            <span className="font-semibold text-slate-100">Weight grid:</span>{' '}
            Showing {downsample}x{downsample} SYNTHETIC weights. Pod
            checkpoint extraction failed; this grid is illustrative, not
            derived from the trained v0.2 checkpoint. Re-run extraction to
            see real weights.
          </div>
        ) : (
          <div className="mt-4 text-[13px] leading-relaxed text-slate-300">
            <span className="font-semibold text-slate-100">Weight grid:</span>{' '}
            Showing {downsample}x{downsample} of{' '}
            {fullParams.toLocaleString()} weights. Each cell averages{' '}
            {avgPerCell.toLocaleString()} real weights from the trained v0.2
            checkpoint (checkpoint id <span className="font-mono">{checkpointId}</span>, sha256 prefix{' '}
            <span className="font-mono">{shaPrefix}</span>).
          </div>
        )}

        <div className="mt-3 text-[13px] leading-relaxed text-slate-300">
          <span className="font-semibold text-slate-100">
            Activation pulses:
          </span>{' '}
          Illustrative — labeled MOCK until Mode 7 live capture is wired
          through. The animation shows what a real forward pass would do
          mechanically: input vector multiplied across rows, output emerges.
        </div>

        <div className="mt-3 text-[13px] leading-relaxed text-slate-300">
          <span className="font-semibold text-slate-100">
            What this layer does:
          </span>{' '}
          {explanation}
        </div>
      </div>
    </aside>
  );
}

// ── Significant-point badge — small floating label near the active node ──

interface SignificantBadgeProps {
  layer: CASBrainLayer | undefined;
  label: string;
  casToken: string;
  camera: PerspectiveCamera | null;
  rendererEl: HTMLCanvasElement | null;
}

function SignificantBadge({
  layer,
  label,
  casToken,
  camera,
  rendererEl,
}: SignificantBadgeProps) {
  if (!layer || !camera || !rendererEl) return null;
  // Project the layer's 3D position into screen space.
  const v = new Vector3(layer.position3d.x, layer.position3d.y, layer.position3d.z);
  v.project(camera);
  if (v.z > 1) return null;
  const rect = rendererEl.getBoundingClientRect();
  const parentRect = (rendererEl.parentElement?.getBoundingClientRect() ?? rect);
  const x = ((v.x + 1) / 2) * rect.width + (rect.left - parentRect.left);
  const y = ((-v.y + 1) / 2) * rect.height + (rect.top - parentRect.top);

  return (
    <div
      className="pointer-events-none absolute z-30 rounded-md border border-amber-300/40 bg-amber-500/15 px-2 py-1 font-mono text-[10px] text-amber-100 shadow-md backdrop-blur-sm"
      style={{
        left: Math.max(6, Math.min(x + 14, (rendererEl.clientWidth ?? 0) - 180)),
        top: Math.max(6, y - 24),
      }}
    >
      <span className="text-amber-200">{label}:</span>{' '}
      <span className="text-amber-50">{casToken}</span>
    </div>
  );
}

function RecentActivationList({
  layerId,
  flows,
}: {
  layerId: string;
  flows: CASBrainFlow[];
}) {
  const hits: Array<{ flowId: string; sp: CASBrainSignificantPoint | undefined }> = [];
  for (const flow of flows) {
    const frame = flow.frames.find((f) => f.activeLayerId === layerId);
    if (frame) hits.push({ flowId: flow.flowId, sp: frame.significantPoint });
  }
  if (hits.length === 0) {
    return <span className="text-slate-500">No activation events captured yet.</span>;
  }
  return (
    <ul className="space-y-1">
      {hits.slice(-4).map((h, i) => (
        <li key={`${h.flowId}-${i}`} className="font-mono text-[10px] text-slate-400">
          <span className="text-slate-500">{h.flowId}</span>
          {h.sp ? (
            <>
              {' '}
              <span className="text-amber-200">{h.sp.label}</span>{' '}
              <span className="text-slate-100">{h.sp.casToken}</span>
            </>
          ) : (
            <span className="text-slate-500"> · passed through</span>
          )}
        </li>
      ))}
    </ul>
  );
}

function plainEnglishWhy(layer: CASBrainLayer): string {
  switch (layer.family) {
    case 'embedding':
      return 'Embeddings turn raw tokens into vectors. Everything downstream operates on this representation. If embeddings are wrong, nothing else can recover.';
    case 'encoder_attn':
      return 'Attention is how the encoder lets every token consult every other token. Domain Descent attention biases that consultation toward the canonical Principled to Operational ordering.';
    case 'encoder_gate':
      return 'The RPM gate is a prerequisite check. Before a thought lands, the model asks whether the upstream conditions for that thought hold. If not, it dims the signal.';
    case 'encoder_ffn':
      return 'Feed-forward layers do the per-token mixing that lets each position rework its own meaning. The classic transformer mixer.';
    case 'decoder_attn':
      return 'Decoder attention is where the running answer gets built. Self-attention looks at what is already said; cross-attention looks back at the prompt.';
    case 'decoder_ffn':
      return 'The decoder mixer. Same job as the encoder FFN, but on the answer side.';
    case 'decoder_head':
      return 'The output head turns hidden states into a probability over the vocabulary. The Register FiLM step nearby tunes that distribution by tone (Transcendent / Analytical / Affective / Embodied).';
    case 'special_branch':
      return 'A separate pathway off the main flow that watches for something specific: ethical truth values, inversion patterns, or typed slots that need pointer-copy from the source.';
    case 'output':
      return 'The visible answer leaves the model here, one token at a time.';
    default:
      return 'Part of the CAS Native architecture.';
  }
}

// ── Lazy entry-point so Mode7LiveShell can React.lazy us ─────────────────
export const LazyCASBrainMap = lazy(() =>
  import('./CASBrainMap').then((m) => ({ default: m.CASBrainMap })),
);

// Convenient default-Suspense wrapper for callers that want a one-liner.
// Mode7LiveShell uses LazyCASBrainMap + its own Suspense + SggsErrorBoundary
// directly so it can share the same fallback shell used by the SGGS scene.
export function CASBrainMapLazyShell(props: CASBrainMapProps) {
  return (
    <Suspense
      fallback={
        <div className="flex h-[800px] w-full items-center justify-center rounded-lg border border-cyan-400/20 bg-slate-950/85 text-sm text-slate-400">
          Loading CAS Brain Map...
        </div>
      }
    >
      <LazyCASBrainMap {...props} />
    </Suspense>
  );
}

export default CASBrainMap;
