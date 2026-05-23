export const KNOB_TYPE_VALUES = ['enum', 'number', 'boolean', 'multiselect'] as const;

export type KnobType = (typeof KNOB_TYPE_VALUES)[number];

export interface KnobDef {
  id: string;
  label: string;
  type: 'enum' | 'number' | 'boolean' | 'multiselect';
  default: unknown;
  options?: readonly unknown[];
  description?: string;
}

export interface TestingMethod {
  id: string;
  name: string;
  description: string;
  reveals: string;
  stageAnchor: string;
  knobs: readonly KnobDef[];
  outputShape: string;
  costEstimateGpuMinutes: number;
  prerequisites: readonly string[];
  validatedArchs: readonly string[];
  orderIndex: number;
}

const FOUNDATION_PROBE: TestingMethod = {
  id: 'foundation_probe',
  name: 'Foundation Probe',
  description:
    'Reads the 7-drive Foundation signal from model hidden states using linear probes',
  reveals: 'Per-layer activation map showing which drives the model is engaging',
  stageAnchor: 'Stage 26 (linear probe readout, validated three families)',
  knobs: [
    {
      id: 'axis',
      label: 'Axis',
      type: 'enum',
      default: 'Drive',
      options: ['Noetic', 'Domain', 'Drive', 'Register'] as const,
    },
    {
      id: 'layer_range',
      label: 'Layer range',
      type: 'multiselect',
      default: [],
      description: 'Inclusive layer indices to sweep',
    },
  ],
  outputShape: 'Per-layer accuracy table + heatmap visualization',
  costEstimateGpuMinutes: 5,
  prerequisites: ['Forward-pass hidden state capture'],
  validatedArchs: ['Pythia-160M', 'OLMo-1B', 'Qwen2.5-1.5B'],
  orderIndex: 1,
};

const RPM_GATE_CHECK: TestingMethod = {
  id: 'rpm_gate_check',
  name: 'RPM Gate Check',
  description:
    "Tests whether prerequisite chains are complete along the model's reasoning path",
  reveals: 'Pass/fail status per pathway node (A0 → Dn → Wn → Pn → Outcome)',
  stageAnchor:
    'RPM monad implementation (Correction 2: section-retraction, one-directional)',
  knobs: [
    {
      id: 'pathway_nodes',
      label: 'Pathway nodes',
      type: 'multiselect',
      default: ['A0', 'D1', 'W1', 'P1'],
      options: [
        'A0',
        'D1',
        'D2',
        'D3',
        'D4',
        'D5',
        'D6',
        'D7',
        'W1',
        'W2',
        'W3',
        'W4',
        'W5',
        'W6',
        'W7',
        'P1',
        'P2',
        'P3',
        'P4',
        'P5',
        'P6',
        'P7',
      ] as const,
    },
    {
      id: 'strictness_threshold',
      label: 'Strictness threshold',
      type: 'number',
      default: 0.75,
    },
  ],
  outputShape: 'Pathway diagram with gate verdicts',
  costEstimateGpuMinutes: 2,
  prerequisites: ['Trace artifact with token-position alignment'],
  validatedArchs: ['Pythia-160M'],
  orderIndex: 2,
};

const INVERSION_SCAN: TestingMethod = {
  id: 'inversion_scan',
  name: 'Inversion Scan',
  description:
    'Scans for structural drift across 7 inversion axes (N / W / F / E / S / A / P)',
  reveals: 'Severity ranking of detected inversions',
  stageAnchor: '7-axis inversion scanner from `cas-engine`',
  knobs: [
    {
      id: 'axes',
      label: 'Axes',
      type: 'multiselect',
      default: ['N', 'W', 'F', 'E', 'S', 'A', 'P'],
      options: ['N', 'W', 'F', 'E', 'S', 'A', 'P'] as const,
    },
    {
      id: 'severity_threshold',
      label: 'Severity threshold',
      type: 'number',
      default: 0.5,
    },
  ],
  outputShape: 'Inversion report with axis-by-axis breakdown',
  costEstimateGpuMinutes: 3,
  prerequisites: ['Forward-pass hidden states + RPM trace'],
  validatedArchs: ['Pythia-160M'],
  orderIndex: 3,
};

const SPARSE_NEURON_COVER: TestingMethod = {
  id: 'sparse_neuron_cover',
  name: 'Sparse Neuron-Cover Discovery',
  description:
    'Finds the smallest neuron set causally responsible for a target class',
  reveals: 'Model-native neuron coordinates (e.g. `L5N2648`) per class',
  stageAnchor: '27F/27G (sparse MLP-neuron-cover causal localization)',
  knobs: [
    {
      id: 'target_class',
      label: 'Target class',
      type: 'enum',
      default: 'F1',
      options: ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7'] as const,
    },
    {
      id: 'sparsity_budget',
      label: 'Sparsity budget',
      type: 'number',
      default: 0,
      description: 'Greedy until `clean_margin < threshold` when 0',
    },
  ],
  outputShape: '`neuron_cover` list with `clean_margin` + `targeted_drop` scores',
  costEstimateGpuMinutes: 15,
  prerequisites: ['Stage 26-style probe + ablation harness'],
  validatedArchs: ['Pythia-160M', 'Qwen2.5-1.5B'],
  orderIndex: 4,
};

const DRIVE_LOCAL_ERASER: TestingMethod = {
  id: 'drive_local_eraser',
  name: 'Drive-Local Eraser Steering',
  description:
    "Suppresses a specific Foundation drive at the model's output side via a calibrated cover",
  reveals: 'Whether the drive is causally controllable (vs merely readable)',
  stageAnchor:
    '27O / 27P (validated cross-arch on Pythia + Qwen; asymmetric closure flagged for OLMo)',
  knobs: [
    {
      id: 'drive',
      label: 'Drive',
      type: 'enum',
      default: 'F1',
      options: ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7'] as const,
    },
    {
      id: 'gain',
      label: 'Gain',
      type: 'number',
      default: 1.0,
      description: 'Calibrated cover gain',
    },
  ],
  outputShape: 'Pre/post output-distribution shift + matched-control p-value',
  costEstimateGpuMinutes: 10,
  prerequisites: ['Module 4 output (neuron cover) for the target drive'],
  validatedArchs: ['Pythia-160M', 'Qwen2.5-1.5B'],
  orderIndex: 5,
};

const BLINDSPOT_DETECTION: TestingMethod = {
  id: 'blindspot_detection',
  name: 'Blindspot Detection',
  description:
    'Reports per-drive eraser-channel cover positions across selected layers',
  reveals:
    "Where the model's representation is suppressing each drive (the \"blind spots\")",
  stageAnchor: '27P-derived (cover positions are by-product of Modules 4 + 5)',
  knobs: [
    {
      id: 'scope',
      label: 'Scope',
      type: 'enum',
      default: 'all_7',
      options: ['one_drive', 'all_7'] as const,
    },
    {
      id: 'layer_range',
      label: 'Layer range',
      type: 'multiselect',
      default: [],
      description: 'Inclusive layer indices to overlay',
    },
  ],
  outputShape: 'Per-drive blindspot overlay on NeuralNetScene + cover position table',
  costEstimateGpuMinutes: 0,
  prerequisites: ['Modules 4 + 5'],
  validatedArchs: ['Pythia-160M', 'Qwen2.5-1.5B'],
  orderIndex: 6,
};

const VERIFICATION_STACK: TestingMethod = {
  id: 'verification_stack',
  name: 'Verification Stack',
  description:
    'Multi-probe ensemble that decides whether to ACCEPT or SUPPRESS each generated token',
  reveals: 'Per-token verdict with confidence margin',
  stageAnchor: 'Verification Stack (assembled from Modules 1, 3, 6)',
  knobs: [
    {
      id: 'mode',
      label: 'Mode',
      type: 'enum',
      default: 'BALANCED',
      options: ['BALANCED', 'HIGH_PRECISION', 'MAX_COVERAGE_TRIAGE'] as const,
    },
  ],
  outputShape: 'Per-token ACCEPT / SUPPRESS / FLAG table',
  costEstimateGpuMinutes: 1,
  prerequisites: ['Modules 1, 3, 6 outputs'],
  validatedArchs: ['Pythia-160M'],
  orderIndex: 7,
};

const EVIDENCE_PACKET: TestingMethod = {
  id: 'evidence_packet',
  name: 'Evidence Packet',
  description: '15-field signed audit artifact bundling all module outputs for a run',
  reveals:
    'Full provenance — what was tested, with what knobs, on what model, under what license',
  stageAnchor:
    '`evidence_packet_v1` schema (already deployed in `dashboard/src/lib/evidencePacket.ts`)',
  knobs: [
    {
      id: 'include_per_token_detail',
      label: 'Include per-token detail',
      type: 'boolean',
      default: true,
    },
    {
      id: 'export_format',
      label: 'Export format',
      type: 'enum',
      default: 'JSON',
      options: ['JSON', 'markdown'] as const,
    },
  ],
  outputShape: 'Downloadable `.json` + `.md` + signed manifest',
  costEstimateGpuMinutes: 0,
  prerequisites: ['Any module output'],
  validatedArchs: ['Pythia-160M', 'OLMo-1B', 'Qwen2.5-1.5B'],
  orderIndex: 8,
};

import { SPATIAL_EVIDENCE_MODULE } from './visualPrimitives';

export const TESTING_METHODS: readonly TestingMethod[] = [
  FOUNDATION_PROBE,
  RPM_GATE_CHECK,
  INVERSION_SCAN,
  SPARSE_NEURON_COVER,
  DRIVE_LOCAL_ERASER,
  BLINDSPOT_DETECTION,
  VERIFICATION_STACK,
  EVIDENCE_PACKET,
  SPATIAL_EVIDENCE_MODULE,
];

const LIVE_F1_ONLY_KNOB: KnobDef = {
  id: 'drive',
  label: 'Drive',
  type: 'enum',
  default: 'F1',
  options: ['F1'] as const,
  description: 'Alpha live worker has calibrated F1 cover/intervention only.',
};

export const LIVE_WORKER_METHODS: readonly TestingMethod[] = [
  {
    ...FOUNDATION_PROBE,
    description:
      'Sent to the live worker. Captures real Pythia hidden-state activity for the selected layers and paints the active neurons in the 3D scene.',
    reveals:
      'Which layers and neurons are carrying the selected Foundation signal during this live run',
    outputShape: 'Live token events with filtered top activated neurons',
  },
  {
    ...RPM_GATE_CHECK,
    description:
      'Sent to the live worker. Uses live attention-derived Mode 7 edges as the runtime prerequisite-chain readout.',
    reveals:
      'Which earlier tokens the current token depends on after the selected RPM threshold is applied',
    outputShape: 'Live Mode 7 arcs filtered by the selected strictness threshold',
    knobs: [
      RPM_GATE_CHECK.knobs[0],
      {
        id: 'strictness_threshold',
        label: 'Strictness threshold',
        type: 'number',
        default: 0,
        description: '0 shows all live Mode 7 arcs; raise to hide weaker edges.',
      },
    ],
  },
  {
    ...INVERSION_SCAN,
    description:
      'Sent to the live worker. Computes a live proxy from activation magnitude and confidence drift on every emitted token.',
    reveals: 'Per-token structural drift risk while the model is generating',
    outputShape: 'Live token events with inversion-risk side-channel metadata',
  },
  {
    ...SPARSE_NEURON_COVER,
    description:
      'Sent to the live worker. Selects the causal F1 neuron-cover set used by the live blindspot/intervention overlays.',
    reveals: 'The exact cover coordinates the live worker is using for F1',
    outputShape: 'Live neuron-cover event for the selected target class',
    knobs: [
      {
        id: 'target_class',
        label: 'Target class',
        type: 'enum',
        default: 'F1',
        options: ['F1'] as const,
      },
      {
        id: 'sparsity_budget',
        label: 'Sparsity budget',
        type: 'number',
        default: 0,
        description: '0 = use the full calibrated alpha cover.',
      },
    ],
  },
  {
    ...DRIVE_LOCAL_ERASER,
    description:
      'Sent to the live worker. Applies a real runtime MLP-output suppression hook to the selected F1 cover before logits are decoded.',
    reveals: 'Whether suppressing the live F1 cover changes the next tokens and confidence',
    outputShape: 'Live generation under the selected eraser gain',
    knobs: [LIVE_F1_ONLY_KNOB, DRIVE_LOCAL_ERASER.knobs[1]],
  },
  {
    ...BLINDSPOT_DETECTION,
    description:
      'Sent to the live worker. Controls which F1 cover coordinates are emitted for the red blindspot overlay.',
    reveals: 'Which F1 cover neurons are being watched during this live run',
    outputShape: 'Live neuron-cover event used directly by the 3D overlay',
    knobs: [
      {
        id: 'scope',
        label: 'Scope',
        type: 'enum',
        default: 'F1',
        options: ['F1'] as const,
      },
      BLINDSPOT_DETECTION.knobs[1],
    ],
  },
  {
    ...VERIFICATION_STACK,
    description:
      'Sent to the live worker. Controls confidence-margin verification emitted with each live token.',
    reveals: 'Whether each token has enough margin to accept under the selected mode',
    outputShape: 'Live confidence-margin values used by the cockpit badges',
  },
];

const METHOD_INDEX: ReadonlyMap<string, TestingMethod> = new Map(
  TESTING_METHODS.map((m) => [m.id, m]),
);

export function getMethod(id: string): TestingMethod | undefined {
  return METHOD_INDEX.get(id);
}

export function listMethods(): readonly TestingMethod[] {
  return [...TESTING_METHODS].sort((a, b) => a.orderIndex - b.orderIndex);
}
