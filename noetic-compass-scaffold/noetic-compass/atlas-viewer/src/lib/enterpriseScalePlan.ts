import type { CasHarnessScalePlan } from './casHarnessAuditApi';

export type EnterpriseScalePlanSize = '20B' | '100B' | '300B';

export interface EnterpriseProbeWorkerAssignment {
  workerLabel: string;
  workerCount: number;
  layerRange: string;
  shardRange: string;
  focus: string;
}

export interface EnterpriseScalePlan {
  size: EnterpriseScalePlanSize;
  title: string;
  parameterBand: string;
  layerSpan: string;
  shardSpan: string;
  workerCount: number;
  orchestratorRole: string;
  expectedProofCoverage: string;
  coverageSignals: readonly string[];
  honestLimitations: readonly string[];
  workerAssignments: readonly EnterpriseProbeWorkerAssignment[];
}

export const ENTERPRISE_SCALE_RATIONALE_COPY =
  'CAS Harness open-weight scaling uses one Orchestrator + Probe Workers assigned by layer/shard ranges, not one harness per 1B params.';

const sharedLimitations = [
  'Requires open weights, tokenizer, model config, and a reproducible inference runner.',
  'Coverage is evidence from scheduled probes, not a guarantee that every parameter or activation path was exhaustively tested.',
  'Black-box audits are out of scope.',
] as const;

export const ENTERPRISE_SCALE_PLANS = [
  {
    size: '20B',
    title: '20B open-weight plan',
    parameterBand: '20B parameters',
    layerSpan: 'Layers 0-47',
    shardSpan: 'Shards S00-S11',
    workerCount: 6,
    orchestratorRole:
      'Builds one run manifest, dispatches six Probe Workers, and merges per-layer evidence receipts.',
    expectedProofCoverage:
      'Planner output: scheduled proof probes cover every declared layer band. Real proof coverage is measured only after worker evidence receipts return.',
    coverageSignals: [
      'Every transformer block receives a scheduled probe window.',
      'Boundary layers and anomaly shards receive replay before evidence packaging.',
      'Receipts preserve layer, shard, prompt set, seed, and probe method metadata.',
    ],
    honestLimitations: [
      ...sharedLimitations,
      'Adapters, external tools, and fine-tune deltas need their own manifest entries.',
    ],
    workerAssignments: [
      {
        workerLabel: 'PW-20-01',
        workerCount: 1,
        layerRange: '0-7',
        shardRange: 'S00-S01',
        focus: 'Embedding and early attention probes.',
      },
      {
        workerLabel: 'PW-20-02',
        workerCount: 1,
        layerRange: '8-15',
        shardRange: 'S02-S03',
        focus: 'Early residual stream and feature bridge probes.',
      },
      {
        workerLabel: 'PW-20-03',
        workerCount: 1,
        layerRange: '16-23',
        shardRange: 'S04-S05',
        focus: 'Mid-stack causal localization probes.',
      },
      {
        workerLabel: 'PW-20-04',
        workerCount: 1,
        layerRange: '24-31',
        shardRange: 'S06-S07',
        focus: 'Mid-to-late shard replay and proof receipts.',
      },
      {
        workerLabel: 'PW-20-05',
        workerCount: 1,
        layerRange: '32-39',
        shardRange: 'S08-S09',
        focus: 'Late residual and topology probes.',
      },
      {
        workerLabel: 'PW-20-06',
        workerCount: 1,
        layerRange: '40-47',
        shardRange: 'S10-S11',
        focus: 'Output head, final layer, and anomaly replay.',
      },
    ],
  },
  {
    size: '100B',
    title: '100B open-weight plan',
    parameterBand: '100B parameters',
    layerSpan: 'Layers 0-79',
    shardSpan: 'Shards S00-S31',
    workerCount: 16,
    orchestratorRole:
      'Builds one manifest, leases 16 Probe Workers, and reconciles receipts by layer band, shard band, and probe method.',
    expectedProofCoverage:
      'Planner output: all declared layer bands receive worker assignments. Real proof coverage is measured only after the Orchestrator merges worker receipts.',
    coverageSignals: [
      'Layer bands are split into five-layer windows for parallel probe runs.',
      'Shard receipts include causal trace, topology check, and replay status fields.',
      'The Orchestrator marks missing or failed worker evidence for follow-up instead of silently passing it.',
    ],
    honestLimitations: [
      ...sharedLimitations,
      'Long-context variants and router branches require separate shard manifests when present.',
    ],
    workerAssignments: [
      {
        workerLabel: 'PW-100-01',
        workerCount: 1,
        layerRange: '0-4',
        shardRange: 'S00-S01',
        focus: 'Embedding, token ingress, and first attention checks.',
      },
      {
        workerLabel: 'PW-100-02',
        workerCount: 1,
        layerRange: '5-9',
        shardRange: 'S02-S03',
        focus: 'Early residual bridge and activation drift probes.',
      },
      {
        workerLabel: 'PW-100-03',
        workerCount: 1,
        layerRange: '10-14',
        shardRange: 'S04-S05',
        focus: 'Early feature path localization.',
      },
      {
        workerLabel: 'PW-100-04',
        workerCount: 1,
        layerRange: '15-19',
        shardRange: 'S06-S07',
        focus: 'Attention head route and shard replay.',
      },
      {
        workerLabel: 'PW-100-05',
        workerCount: 1,
        layerRange: '20-24',
        shardRange: 'S08-S09',
        focus: 'Mid-stack causal intervention probes.',
      },
      {
        workerLabel: 'PW-100-06',
        workerCount: 1,
        layerRange: '25-29',
        shardRange: 'S10-S11',
        focus: 'Mid-stack topology and proof receipt checks.',
      },
      {
        workerLabel: 'PW-100-07',
        workerCount: 1,
        layerRange: '30-34',
        shardRange: 'S12-S13',
        focus: 'Anomaly replay for mid-layer route changes.',
      },
      {
        workerLabel: 'PW-100-08',
        workerCount: 1,
        layerRange: '35-39',
        shardRange: 'S14-S15',
        focus: 'Mid-to-late transition probes.',
      },
      {
        workerLabel: 'PW-100-09',
        workerCount: 1,
        layerRange: '40-44',
        shardRange: 'S16-S17',
        focus: 'Late residual stream localization.',
      },
      {
        workerLabel: 'PW-100-10',
        workerCount: 1,
        layerRange: '45-49',
        shardRange: 'S18-S19',
        focus: 'Late attention and induction path probes.',
      },
      {
        workerLabel: 'PW-100-11',
        workerCount: 1,
        layerRange: '50-54',
        shardRange: 'S20-S21',
        focus: 'Late topology checks and receipt reconciliation.',
      },
      {
        workerLabel: 'PW-100-12',
        workerCount: 1,
        layerRange: '55-59',
        shardRange: 'S22-S23',
        focus: 'High-risk shard replay window.',
      },
      {
        workerLabel: 'PW-100-13',
        workerCount: 1,
        layerRange: '60-64',
        shardRange: 'S24-S25',
        focus: 'Final-stack causal and activation probes.',
      },
      {
        workerLabel: 'PW-100-14',
        workerCount: 1,
        layerRange: '65-69',
        shardRange: 'S26-S27',
        focus: 'Final-stack route consistency checks.',
      },
      {
        workerLabel: 'PW-100-15',
        workerCount: 1,
        layerRange: '70-74',
        shardRange: 'S28-S29',
        focus: 'Output-adjacent proof receipts.',
      },
      {
        workerLabel: 'PW-100-16',
        workerCount: 1,
        layerRange: '75-79',
        shardRange: 'S30-S31',
        focus: 'Output head, final replay, and failure triage.',
      },
    ],
  },
  {
    size: '300B',
    title: '300B open-weight plan',
    parameterBand: '300B parameters',
    layerSpan: 'Layers 0-119',
    shardSpan: 'Shards S00-S47',
    workerCount: 48,
    orchestratorRole:
      'Builds a hierarchical manifest, leases 48 Probe Workers in worker groups, and merges evidence receipts through shard checkpoints.',
    expectedProofCoverage:
      'Planner output: sentinel probes and follow-up replay are scheduled by layer/shard group. Real proof coverage is measured after the distributed run completes.',
    coverageSignals: [
      'Layer bands are grouped so worker failures can be retried without restarting the whole run.',
      'Shard checkpoints keep partial evidence usable while late replay jobs continue.',
      'Coverage gaps are reported as follow-up work, not hidden inside the final receipt.',
    ],
    honestLimitations: [
      ...sharedLimitations,
      'MoE routing, quantized checkpoints, and cross-node memory pressure can reduce first-pass coverage.',
    ],
    workerAssignments: [
      {
        workerLabel: 'PW-300-01 to PW-300-04',
        workerCount: 4,
        layerRange: '0-9',
        shardRange: 'S00-S03',
        focus: 'Ingress, embeddings, and first attention bands.',
      },
      {
        workerLabel: 'PW-300-05 to PW-300-08',
        workerCount: 4,
        layerRange: '10-19',
        shardRange: 'S04-S07',
        focus: 'Early residual stream and feature bridge probes.',
      },
      {
        workerLabel: 'PW-300-09 to PW-300-12',
        workerCount: 4,
        layerRange: '20-29',
        shardRange: 'S08-S11',
        focus: 'Early-to-mid causal localization.',
      },
      {
        workerLabel: 'PW-300-13 to PW-300-16',
        workerCount: 4,
        layerRange: '30-39',
        shardRange: 'S12-S15',
        focus: 'Mid-stack topology and replay probes.',
      },
      {
        workerLabel: 'PW-300-17 to PW-300-20',
        workerCount: 4,
        layerRange: '40-49',
        shardRange: 'S16-S19',
        focus: 'Mid-stack anomaly triage.',
      },
      {
        workerLabel: 'PW-300-21 to PW-300-24',
        workerCount: 4,
        layerRange: '50-59',
        shardRange: 'S20-S23',
        focus: 'Mid-to-late transition probes.',
      },
      {
        workerLabel: 'PW-300-25 to PW-300-28',
        workerCount: 4,
        layerRange: '60-69',
        shardRange: 'S24-S27',
        focus: 'Late residual stream localization.',
      },
      {
        workerLabel: 'PW-300-29 to PW-300-32',
        workerCount: 4,
        layerRange: '70-79',
        shardRange: 'S28-S31',
        focus: 'Late attention path replay.',
      },
      {
        workerLabel: 'PW-300-33 to PW-300-36',
        workerCount: 4,
        layerRange: '80-89',
        shardRange: 'S32-S35',
        focus: 'Late topology and receipt reconciliation.',
      },
      {
        workerLabel: 'PW-300-37 to PW-300-40',
        workerCount: 4,
        layerRange: '90-99',
        shardRange: 'S36-S39',
        focus: 'Final-stack causal probes.',
      },
      {
        workerLabel: 'PW-300-41 to PW-300-44',
        workerCount: 4,
        layerRange: '100-109',
        shardRange: 'S40-S43',
        focus: 'Output-adjacent replay and anomaly checks.',
      },
      {
        workerLabel: 'PW-300-45 to PW-300-48',
        workerCount: 4,
        layerRange: '110-119',
        shardRange: 'S44-S47',
        focus: 'Output head, final receipts, and failed-job triage.',
      },
    ],
  },
] as const satisfies readonly EnterpriseScalePlan[];

export const DEFAULT_ENTERPRISE_SCALE_PLAN = ENTERPRISE_SCALE_PLANS[1];

export function getEnterpriseScalePlan(
  size: EnterpriseScalePlanSize,
): EnterpriseScalePlan {
  const plan = ENTERPRISE_SCALE_PLANS.find((candidate) => candidate.size === size);
  if (!plan) {
    throw new Error(`Unknown enterprise scale plan: ${size}`);
  }
  return plan;
}

export function enterpriseScalePlanFromApi(
  plan: CasHarnessScalePlan,
): EnterpriseScalePlan {
  return {
    size: sizeForParameterCount(plan.parameter_count_b),
    title: `${formatParameterCount(plan.parameter_count_b)} open-weight plan`,
    parameterBand: `${formatParameterCount(plan.parameter_count_b)} parameters`,
    layerSpan: `Layers 0-${Math.max(0, plan.num_layers - 1)}`,
    shardSpan: `${plan.worker_assignments.length} layer shards`,
    workerCount: plan.recommended_worker_count,
    orchestratorRole: plan.orchestration_pattern,
    expectedProofCoverage:
      `Planner output: ${plan.recommended_worker_count} Probe Workers assigned across ` +
      `${plan.num_layers} layers. Real coverage is measured after worker evidence returns.`,
    coverageSignals: plan.expected_capability,
    honestLimitations: plan.limitations,
    workerAssignments: plan.worker_assignments.map((assignment) => ({
      workerLabel: assignment.worker_id,
      workerCount: 1,
      layerRange: `${assignment.layer_start}-${assignment.layer_end}`,
      shardRange: assignment.shard_id,
      focus: methodLabel(assignment.assigned_methods),
    })),
  };
}

function sizeForParameterCount(parameterCountB: number): EnterpriseScalePlanSize {
  if (parameterCountB <= 20) return '20B';
  if (parameterCountB <= 150) return '100B';
  return '300B';
}

function formatParameterCount(parameterCountB: number): string {
  return Number.isInteger(parameterCountB)
    ? `${parameterCountB}B`
    : `${parameterCountB.toFixed(1)}B`;
}

function methodLabel(methods: readonly string[]): string {
  if (methods.length === 0) return 'Probe assignment pending.';
  return methods
    .map((method) => method.replaceAll('_', ' '))
    .join(', ');
}
