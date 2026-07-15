import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAccountAuth } from '../auth/AccountAuthProvider';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import { AuditSessionProgress, type AuditLifecycleStatus } from '../components/audit/AuditSessionProgress';
import { AuditSessionSummaryCard } from '../components/audit/AuditSessionSummaryCard';
import { AuditVerdictCard } from '../components/audit/AuditVerdictCard';
import { AuditVerdictExplainer } from '../components/audit/AuditVerdictExplainer';
import DistributedAuditRunPanel from '../components/audit/DistributedAuditRunPanel';
import EvidencePacketVerificationPanel from '../components/audit/EvidencePacketVerificationPanel';
import EvidencePacketFlightRecorderFaq from '../components/audit/EvidencePacketFlightRecorderFaq';
import EvidencePacketActions from '../components/audit/EvidencePacketActions';
import EnterpriseScalePlanCard from '../components/audit/EnterpriseScalePlanCard';
import FleetExecutorPanel from '../components/audit/FleetExecutorPanel';
import { ModelConnectionCard } from '../components/audit/ModelConnectionCard';
import { AuditPopover } from '../components/audit/AuditPopover';
import {
  buildDefaultProvenanceChips,
  type ProvenanceChip,
} from '../lib/casHarnessAudit';
import {
  buildCasHarnessFleetEvidenceFragmentRef,
  createCasHarnessDistributedAudit,
  createCasHarnessScalePlan,
  createCasHarnessAuditSession,
  dispatchCasHarnessDistributedAudit,
  fetchLiveWorkerHealth,
  leaseCasHarnessFleetJob,
  mergeCasHarnessDistributedAudit,
  mergeCasHarnessFleetRun,
  prepareCasHarnessFleetRun,
  registerCasHarnessFleetWorker,
  startCasHarnessAuditSession,
  submitCasHarnessFleetJobReceipt,
  verifyCasHarnessFleetRun,
  verifyCasHarnessModelTarget,
  type CasHarnessAuditApiOptions,
  type CasHarnessAuditScope,
  type CasHarnessAuditSession,
  type CasHarnessDistributedAudit,
  type CasHarnessFleetJob,
  type CasHarnessFleetRun,
  type CasHarnessFleetVerifierDecision,
  type CasHarnessFleetWorker,
  type CasHarnessLiveWorkerHealth,
  type CasHarnessScalePlanRequest,
} from '../lib/casHarnessAuditApi';
import {
  DEFAULT_ENTERPRISE_SCALE_PLAN,
  enterpriseScalePlanFromApi,
  getEnterpriseScalePlan,
  type EnterpriseScalePlan,
  type EnterpriseScalePlanSize,
} from '../lib/enterpriseScalePlan';
import {
  ACCENT_AMBER,
  ACCENT_CYAN,
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
  THEME,
} from '../lib/designTokens';

interface AuditStep {
  label: string;
  detail: string;
  command: string;
}

interface AuditTargetConfig {
  modelId: string;
  provider: string;
  endpointLabel: string;
  scenarioText: string;
  endpointUrl?: string | null;
  connectionId: string;
  checkedAt: string;
  statusDetail: string;
  canRunAudit: boolean;
  evidencePacketTraceId?: string | null;
}

const SELECTED_MODULES = [
  'model_proof',
  'cas_readout',
  'causal_proof',
  'control_proof',
  'output_proof',
  'packet_proof',
];

const SCALE_PLAN_REQUESTS: Record<EnterpriseScalePlanSize, CasHarnessScalePlanRequest> = {
  '20B': {
    model_id: 'customer/open-weight-20b',
    weight_access: 'open_weight',
    parameter_count_b: 20,
    num_layers: 40,
    precision: 'bf16',
    available_gpu_memory_gb: 80,
  },
  '100B': {
    model_id: 'customer/open-weight-100b',
    weight_access: 'open_weight',
    parameter_count_b: 100,
    num_layers: 120,
    precision: 'bf16',
    available_gpu_memory_gb: 80,
  },
  '300B': {
    model_id: 'customer/open-weight-300b',
    weight_access: 'open_weight',
    parameter_count_b: 300,
    num_layers: 160,
    precision: 'int4',
    available_gpu_memory_gb: 80,
  },
};

const HOSTED_PYTHIA_TARGET: AuditTargetConfig = {
  modelId: 'EleutherAI/pythia-160m',
  provider: 'CAS Harness hosted live worker',
  endpointLabel: '/api/cas-harness/live-worker/health',
  scenarioText:
    'Hosted real-weight Pythia audit: run the selected CAS modules and preserve the resulting Evidence Packet.',
  endpointUrl: null,
  connectionId: 'cas-target-reference-pending',
  checkedAt: '',
  statusDetail: 'Hosted Pythia target has not been verified by the backend yet.',
  canRunAudit: false,
  evidencePacketTraceId: null,
};

const S7_F28_TRACE_ID = 's7-f28-balanced-bridge-gpt-neox-20b-20260526';
const STAGE9_40E_TRACE_ID = 'stage9-40e-original-baseline-readout-20260527';

const S7_F28_PACKET_TARGET: AuditTargetConfig = {
  modelId: 'EleutherAI/gpt-neox-20b',
  provider: 'S7-F28 Balanced Bridge Method',
  endpointLabel: `/api/harness/evidence/${S7_F28_TRACE_ID}`,
  scenarioText:
    'Stage 7 Foundation-28 GPT-NeoX-20B evidence packet review using the S7-F28 Balanced Bridge Method.',
  endpointUrl: null,
  connectionId: 'cas-target-s7-f28-gpt-neox-20b',
  checkedAt: '',
  statusDetail:
    'S7-F28 GPT-NeoX-20B Evidence Packet selected. Run CAS audit to review the conservative human-review verdict.',
  canRunAudit: true,
  evidencePacketTraceId: S7_F28_TRACE_ID,
};

const STAGE9_40E_PACKET_TARGET: AuditTargetConfig = {
  modelId: 'EleutherAI/gpt-neox-20b',
  provider: 'Stage 9 original 40E validation packet',
  endpointLabel: `/api/cas-harness/audit/session · ${STAGE9_40E_TRACE_ID}`,
  scenarioText:
    'Stage 9 original 40-Element GPT-NeoX-20B validation packet. It carries a verifier ACCEPT decision, but routes to review unless WORM packet proof is attached.',
  endpointUrl: null,
  connectionId: 'cas-target-stage9-40e-gpt-neox-20b',
  checkedAt: '',
  statusDetail:
    'Stage 9 40E GPT-NeoX-20B validation packet selected. Run CAS audit to surface the verifier decision, proof chips, confidence basis, and WORM gate.',
  canRunAudit: true,
  evidencePacketTraceId: STAGE9_40E_TRACE_ID,
};

const AUDIT_STEPS: AuditStep[] = [
  {
    label: 'Choose model',
    detail: 'Choose the supported model target that this audit will evaluate.',
    command: 'CHOOSE',
  },
  {
    label: 'Connect key or worker',
    detail: 'Verify the selected target and show the live-worker connection truth.',
    command: 'CONNECT',
  },
  {
    label: 'Run CAS audit',
    detail: 'Run readout, causal, control, output, and packet checks.',
    command: 'RUN',
  },
  {
    label: 'Track progress',
    detail: 'Follow the backend lifecycle while evidence is validated and packaged.',
    command: 'PROGRESS',
  },
  {
    label: 'Result + evidence',
    detail: 'Review the evidence-gated verdict, proof chips, and Evidence Packet actions.',
    command: 'RESULT',
  },
];

const pendingChips = buildDefaultProvenanceChips({
  modelProof: {
    status: 'missing',
    detail: 'No model target has been verified yet.',
  },
  casReadout: {
    status: 'unavailable',
    detail: 'No CAS readout has been run yet.',
  },
  causalProof: {
    status: 'unavailable',
    detail: 'No ablation/intervention result yet.',
  },
  controlProof: {
    status: 'unavailable',
    detail: 'No matched control or baseline check yet.',
  },
  outputProof: {
    status: 'unavailable',
    detail: 'No output effect has been measured yet.',
  },
  packetProof: {
    status: 'missing',
    detail: 'No Evidence Packet has been created yet.',
  },
});

function chipsForSession(session: CasHarnessAuditSession | null): ProvenanceChip[] {
  if (!session) return pendingChips;
  if (session.provenance_chips.length > 0) return session.provenance_chips;

  return buildDefaultProvenanceChips({
    modelProof: {
      status: 'missing',
      detail: `Backend model status: ${session.model_status}. This is not a completed model proof.`,
    },
    casReadout: {
      status: 'unavailable',
      detail: 'CAS readout is pending until the audit runner processes the session.',
    },
    causalProof: {
      status: 'unavailable',
      detail: 'Causal proof is pending until ablation/intervention runs are attached.',
    },
    controlProof: {
      status: 'unavailable',
      detail: 'Control proof is pending until matched baseline checks are attached.',
    },
    outputProof: {
      status: 'unavailable',
      detail: 'Output proof is pending until the model output is evaluated.',
    },
    packetProof: {
      status: session.evidence_packet_trace_id ? 'present' : 'missing',
      detail: session.evidence_packet_trace_id
        ? `Evidence trace: ${session.evidence_packet_trace_id}`
        : 'Evidence Packet has not been created for this session yet.',
    },
  });
}

function lifecycleStatusFor(
  session: CasHarnessAuditSession | null,
  isAuditRunning: boolean,
  error: string | null,
): AuditLifecycleStatus {
  if (error) return 'failed';
  if (isAuditRunning) return 'validating';
  if (!session) return 'draft';

  switch (session.status) {
    case 'DRAFT':
      return 'draft';
    case 'VALIDATING':
      return 'validating';
    case 'RUNNING':
      return 'running';
    case 'SCAFFOLD_PENDING_RUNNER':
      return 'runner_pending';
    case 'EVIDENCE_PENDING':
    case 'EVIDENCE_READY':
      return 'evidence_pending';
    case 'COMPLETE':
      return 'complete';
    case 'FAILED':
      return 'failed';
  }
}

function progressDetail(
  status: AuditLifecycleStatus,
  hasTarget: boolean,
): string | null {
  if (!hasTarget && status === 'draft') {
    return 'Connect a supported target before running an audit.';
  }
  if (status === 'runner_pending') {
    return 'Session created. Verdict blocked until an Evidence Packet is attached.';
  }
  return null;
}

function latestLifecycleMessage(session: CasHarnessAuditSession | null): string | null {
  if (!session || session.lifecycle.length === 0) return null;
  return session.lifecycle[session.lifecycle.length - 1]?.message ?? null;
}

function verdictSummaryFor(session: CasHarnessAuditSession | null): string {
  if (!session?.verdict) {
    return 'No verdict yet. Run a CAS audit to create an evidence-gated decision.';
  }
  if (session.verdict === 'ACCEPT') {
    return 'Accepted: the verifier allowed it and required proof chips passed.';
  }
  if (session.verdict === 'SUPPRESS') {
    return 'Suppressed: the verifier rejected it under the active proof gate.';
  }
  return 'Human review: proof is missing/failed or the verifier requested review.';
}

function commandStateFor(
  index: number,
  hasModelChoice: boolean,
  hasTarget: boolean,
  session: CasHarnessAuditSession | null,
  isAuditRunning: boolean,
  isTargetConnecting: boolean,
  targetError: string | null,
  sessionError: string | null,
  isTraceReviewMode: boolean,
): CommandState {
  if (isTraceReviewMode) return index === 4 ? 'active' : 'done';
  if (index === 0) return hasModelChoice ? 'done' : 'active';
  if (index === 1) {
    if (!hasModelChoice) return 'waiting';
    if (targetError) return 'blocked';
    if (isTargetConnecting) return 'active';
    return hasTarget ? 'done' : 'ready';
  }
  if (index === 2) {
    if (!hasTarget) return 'waiting';
    if (sessionError) return 'blocked';
    if (!session) return isAuditRunning ? 'active' : 'ready';
    return 'done';
  }
  if (index === 3) {
    if (!session) return 'waiting';
    if (sessionError) return 'waiting';
    if (session.status === 'FAILED') return 'blocked';
    if (session.verdict || session.status === 'COMPLETE') return 'done';
    return 'active';
  }
  if (!session) return 'waiting';
  if (sessionError || session.status === 'FAILED') return 'waiting';
  return session.verdict || session.status === 'COMPLETE' ? 'done' : 'waiting';
}

function commandStatusLabel(state: CommandState): string {
  switch (state) {
    case 'active':
      return 'active';
    case 'ready':
      return 'ready';
    case 'done':
      return 'done';
    case 'blocked':
      return 'blocked';
    case 'waiting':
      return 'waiting';
  }
}

function replaceFleetJob(
  run: CasHarnessFleetRun,
  job: CasHarnessFleetJob,
): CasHarnessFleetRun {
  const jobForRun = {
    ...job,
    lease_token: null,
  };
  const jobs = run.jobs.some((candidate) => candidate.job_id === job.job_id)
    ? run.jobs.map((candidate) => (candidate.job_id === job.job_id ? jobForRun : candidate))
    : [...run.jobs, jobForRun];

  return {
    ...run,
    status: job.status === 'leased' ? 'LEASING' : run.status,
    verifier_gate_status:
      job.status === 'leased' && run.verifier_gate_status === 'waiting_for_workers'
        ? 'waiting_for_receipts'
        : run.verifier_gate_status,
    jobs,
    leased_jobs: jobs.filter((candidate) => candidate.status === 'leased').length,
    completed_fragments: jobs.filter((candidate) => candidate.status === 'completed').length,
    failed_jobs: jobs.filter((candidate) => candidate.status === 'failed').length,
    updated_at: job.updated_at,
  };
}

function mergedPacketStatusFor(
  run: CasHarnessFleetRun | null,
): 'not_created' | 'partial' | 'ready' {
  if (!run) return 'not_created';
  if (run.verifier_gate_status === 'ready_for_verifier' && run.merged_packet_trace_id) {
    return 'ready';
  }
  if (
    run.completed_fragments > 0 ||
    run.failed_jobs > 0 ||
    run.status === 'MERGE_PENDING' ||
    run.status === 'COMPLETE'
  ) {
    return 'partial';
  }
  return 'not_created';
}

function assignedFleetWorkerId(
  audit: CasHarnessDistributedAudit | null,
  run: CasHarnessFleetRun | null,
): string | null {
  const openJob = run?.jobs.find((job) => job.status !== 'completed');
  const anyJob = run?.jobs[0];
  return openJob?.assigned_worker_id ?? anyJob?.assigned_worker_id ?? audit?.worker_evidence[0]?.worker_id ?? null;
}

function canMergeFleetRun(run: CasHarnessFleetRun | null, isLoading: boolean): boolean {
  return Boolean(
    run &&
      !isLoading &&
      run.verifier_gate_status === 'ready_for_verifier' &&
      !run.merged_packet_trace_id &&
      run.total_jobs > 0 &&
      run.completed_fragments === run.total_jobs &&
      run.failed_jobs === 0 &&
      run.stale_workers.length === 0 &&
      run.jobs.every((job) => job.missing_outputs.length === 0),
  );
}

const headingStyle: CSSProperties = {
  margin: 0,
  fontSize: 34,
  lineHeight: 1.1,
  fontWeight: 750,
  letterSpacing: 0,
  color: COLORS.textPrimary,
};

const headingWaveStyle: CSSProperties = {
  ...headingStyle,
  color: 'transparent',
  backgroundImage:
    `linear-gradient(90deg, ${ACCENT_TEAL} 0%, ${ACCENT_CYAN} 50%, ${ACCENT_TEAL} 100%)`,
  backgroundSize: '280% 100%',
  backgroundClip: 'text',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  animation: 'cas-heading-wave 4.8s linear infinite',
};

const headingWaveCss = `
@keyframes cas-heading-wave {
  0% {
    background-position: 0% 50%;
  }

  100% {
    background-position: 280% 50%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cas-heading-wave {
    animation: none !important;
    background-position: 50% 50%;
  }
}
`;

const eyebrowStyle: CSSProperties = {
  margin: '0 0 10px 0',
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: 1.2,
  textTransform: 'uppercase',
  color: ACCENT_TEAL,
};

const monikerStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  marginTop: 14,
  padding: '7px 10px',
  border: '1px solid rgba(45, 212, 191, 0.30)',
  borderRadius: 6,
  background: 'rgba(45, 212, 191, 0.08)',
  color: COLORS.textPrimary,
  fontSize: 12,
  fontWeight: 750,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
};

const topGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1.15fr) minmax(300px, 0.85fr)',
  gap: 18,
  alignItems: 'start',
};

const liveWorkerChipBaseStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 7,
  alignSelf: 'center',
  padding: '6px 11px',
  borderRadius: 999,
  fontFamily: FONT_FAMILY,
  fontSize: 11.5,
  fontWeight: 650,
  letterSpacing: 0.2,
  whiteSpace: 'nowrap',
};

const liveWorkerDotStyle = (color: string): CSSProperties => ({
  width: 8,
  height: 8,
  borderRadius: 999,
  background: color,
  flex: '0 0 auto',
});

type LiveWorkerChipView = {
  accent: string;
  label: string;
};

// Resolve the honest connection-state presentation for the live-worker chip.
// Teal ONLY when real Pythia weights are confirmed; amber for reachable-demo
// AND unreachable (both are "no real audit" states the user must not mistake
// for a live run); muted/gray for not-configured and the pre-fetch unknown
// state. Never render teal off anything but confirmed real weights.
function liveWorkerChipView(
  health: CasHarnessLiveWorkerHealth | null,
): LiveWorkerChipView {
  if (health === null) {
    return { accent: COLORS.textMuted, label: 'Checking live worker…' };
  }
  if (!health.configured) {
    return { accent: COLORS.textMuted, label: health.label };
  }
  if (health.real_weights) {
    return { accent: ACCENT_TEAL, label: health.label };
  }
  return { accent: ACCENT_AMBER, label: health.label };
}

type CommandState = 'active' | 'ready' | 'done' | 'waiting' | 'blocked';

const commandCenterStyle: CSSProperties = {
  marginTop: 20,
  padding: 18,
  borderRadius: 8,
  border: '1px solid rgba(45, 212, 191, 0.34)',
  background:
    'linear-gradient(135deg, rgba(45, 212, 191, 0.16), rgba(2, 6, 23, 0.82) 42%, rgba(34, 211, 238, 0.10))',
  boxShadow: '0 24px 80px rgba(0, 0, 0, 0.28)',
};

const commandHeaderStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  marginBottom: 14,
};

const commandActionsStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  justifyContent: 'flex-end',
  gap: 10,
};

const commandTitleStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 20,
  fontWeight: 900,
  letterSpacing: 0,
};

const commandSubtitleStyle: CSSProperties = {
  margin: '5px 0 0',
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.45,
};

const commandActionStyle = (enabled: boolean): CSSProperties => ({
  minHeight: 42,
  padding: '9px 15px',
  borderRadius: 6,
  border: enabled
    ? '1px solid rgba(45, 212, 191, 0.56)'
    : '1px solid rgba(148, 163, 184, 0.24)',
  background: enabled ? 'rgba(45, 212, 191, 0.16)' : 'rgba(148, 163, 184, 0.06)',
  color: enabled ? '#ccfbf1' : COLORS.textMuted,
  cursor: enabled ? 'pointer' : 'not-allowed',
  fontFamily: 'inherit',
  fontSize: 13,
  fontWeight: 900,
  letterSpacing: 0.4,
  textTransform: 'uppercase',
});

const flowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
  gap: 12,
};

const stepStyle = (state: CommandState): CSSProperties => ({
  minHeight: 148,
  padding: 15,
  borderRadius: 8,
  border:
    state === 'done'
      ? '1px solid rgba(34, 197, 94, 0.46)'
      : state === 'active' || state === 'ready'
        ? '1px solid rgba(45, 212, 191, 0.56)'
        : state === 'blocked'
          ? '1px solid rgba(251, 191, 36, 0.42)'
          : '1px solid rgba(148, 163, 184, 0.20)',
  background:
    state === 'done'
      ? 'linear-gradient(180deg, rgba(34, 197, 94, 0.13), rgba(255, 255, 255, 0.025))'
      : state === 'active' || state === 'ready'
        ? 'linear-gradient(180deg, rgba(45, 212, 191, 0.16), rgba(255, 255, 255, 0.03))'
        : state === 'blocked'
          ? 'linear-gradient(180deg, rgba(251, 191, 36, 0.12), rgba(255, 255, 255, 0.025))'
          : 'rgba(2, 6, 23, 0.38)',
  boxShadow:
    state === 'active' || state === 'ready'
      ? '0 0 0 1px rgba(45, 212, 191, 0.10), 0 16px 42px rgba(45, 212, 191, 0.08)'
      : 'none',
});

const stepNumberStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 34,
  height: 34,
  borderRadius: 6,
  border: '1px solid rgba(45, 212, 191, 0.40)',
  color: '#ccfbf1',
  background: 'rgba(45, 212, 191, 0.12)',
  fontSize: 13,
  fontWeight: 900,
  fontFamily: THEME.fontMono,
};

const stepLabelStyle: CSSProperties = {
  margin: '12px 0 6px 0',
  fontSize: 18,
  fontWeight: 900,
  color: COLORS.textPrimary,
};

const commandBadgeStyle = (state: CommandState): CSSProperties => ({
  display: 'inline-flex',
  alignItems: 'center',
  minHeight: 24,
  marginTop: 12,
  padding: '3px 7px',
  borderRadius: 5,
  color:
    state === 'done'
      ? '#bbf7d0'
      : state === 'active' || state === 'ready'
        ? '#ccfbf1'
        : state === 'blocked'
          ? '#fef3c7'
          : COLORS.textMuted,
  background:
    state === 'done'
      ? 'rgba(34, 197, 94, 0.14)'
      : state === 'active' || state === 'ready'
        ? 'rgba(45, 212, 191, 0.14)'
        : state === 'blocked'
          ? 'rgba(251, 191, 36, 0.12)'
          : 'rgba(148, 163, 184, 0.08)',
  fontFamily: THEME.fontMono,
  fontSize: 11,
  fontWeight: 900,
  textTransform: 'uppercase',
});

const lowerGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 0.95fr) minmax(300px, 1.05fr)',
  gap: 16,
  marginTop: 16,
};

const singleColumnStyle: CSSProperties = {
  display: 'grid',
  gap: 16,
  marginTop: 16,
};

const fleetControlPanelStyle: CSSProperties = {
  display: 'grid',
  gap: 12,
  padding: 16,
  borderRadius: 8,
  border: '1px solid rgba(45, 212, 191, 0.22)',
  background: 'rgba(2, 6, 23, 0.40)',
};

const fleetControlHeaderStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 12,
};

const fleetControlTitleStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 17,
  fontWeight: 900,
};

const fleetButtonRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
};

const fleetAuthInputStyle: CSSProperties = {
  width: 'min(100%, 360px)',
  minHeight: 38,
  padding: '8px 10px',
  borderRadius: 6,
  border: '1px solid rgba(148, 163, 184, 0.26)',
  background: 'rgba(2, 6, 23, 0.48)',
  color: COLORS.textPrimary,
  fontFamily: THEME.fontMono,
  fontSize: 12,
  outline: 'none',
};

const fleetNoticeStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
};

const advancedDetailsStyle: CSSProperties = {
  marginTop: 20,
  border: `1px solid ${COLORS.borderSubtle}`,
  borderRadius: 8,
  background: 'rgba(2, 6, 23, 0.34)',
};

const advancedSummaryStyle: CSSProperties = {
  padding: '13px 16px',
  color: COLORS.textSecondary,
  cursor: 'pointer',
  fontFamily: FONT_FAMILY,
  fontSize: 13,
  fontWeight: 800,
};

const advancedStackStyle: CSSProperties = {
  display: 'grid',
  gap: 18,
  padding: '2px 16px 16px',
};

const savedPacketActionsStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
};

const verdictStackStyle: CSSProperties = {
  display: 'grid',
  gap: 16,
};

const verdictLabelStyle: CSSProperties = {
  display: 'block',
  marginBottom: 4,
  fontSize: 12,
  fontWeight: 800,
  letterSpacing: 0.4,
  fontFamily: THEME.fontMono,
  color: COLORS.textPrimary,
};

function AuditScopeBanner({ scope }: { scope: CasHarnessAuditScope }) {
  const hasInternalAccess = scope.internalActivationAccess;
  const accent = hasInternalAccess ? ACCENT_TEAL : '#fbbf24';
  return (
    <div
      role="note"
      aria-label="Audit scope"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        padding: '10px 14px',
        borderRadius: 8,
        border: `1px solid ${accent}33`,
        background: `${accent}14`,
        fontFamily: FONT_FAMILY,
      }}
    >
      <span
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: 0.4,
          textTransform: 'uppercase',
          color: accent,
        }}
      >
        Audit scope
      </span>
      <span style={{ fontSize: 13, color: COLORS.textPrimary, fontWeight: 500 }}>
        {scope.label}
      </span>
      {scope.detail ? (
        <span style={{ fontSize: 12, color: COLORS.textSecondary, lineHeight: 1.45 }}>
          {scope.detail}
        </span>
      ) : null}
    </div>
  );
}

export default function AuditConsolePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const accountAuth = useAccountAuth();
  const requestedModel = searchParams.get('model');
  const requestedTraceId = searchParams.get('trace')?.trim() ?? '';
  const queryTarget = requestedModel === 'pythia-160m' ? HOSTED_PYTHIA_TARGET : null;
  const [target, setTarget] = useState<AuditTargetConfig | null>(null);
  const [session, setSession] = useState<CasHarnessAuditSession | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [targetError, setTargetError] = useState<string | null>(null);
  const [isTargetConnecting, setIsTargetConnecting] = useState(false);
  const [isAuditRunning, setIsAuditRunning] = useState(false);
  const [byokApiKey, setByokApiKey] = useState('');
  const [enterprisePlanSize, setEnterprisePlanSize] =
    useState<EnterpriseScalePlanSize>('100B');
  const [enterprisePlan, setEnterprisePlan] =
    useState<EnterpriseScalePlan>(DEFAULT_ENTERPRISE_SCALE_PLAN);
  const [enterprisePlanError, setEnterprisePlanError] = useState<string | null>(null);
  const [isEnterprisePlanLoading, setIsEnterprisePlanLoading] = useState(false);
  const [distributedAudit, setDistributedAudit] =
    useState<CasHarnessDistributedAudit | null>(null);
  const [distributedAuditError, setDistributedAuditError] = useState<string | null>(null);
  const [isDistributedAuditLoading, setIsDistributedAuditLoading] = useState(false);
  const [fleetRun, setFleetRun] = useState<CasHarnessFleetRun | null>(null);
  const [registeredFleetWorker, setRegisteredFleetWorker] =
    useState<CasHarnessFleetWorker | null>(null);
  const [leasedFleetJob, setLeasedFleetJob] = useState<CasHarnessFleetJob | null>(null);
  const [fleetVerifierDecision, setFleetVerifierDecision] =
    useState<CasHarnessFleetVerifierDecision | null>(null);
  const [operatorApiToken, setOperatorApiToken] = useState('');
  const [fleetExecutorError, setFleetExecutorError] = useState<string | null>(null);
  const [isFleetExecutorLoading, setIsFleetExecutorLoading] = useState(false);
  const [liveWorkerHealth, setLiveWorkerHealth] =
    useState<CasHarnessLiveWorkerHealth | null>(null);

  // Probe the live-trace worker once on mount so the run controls can show an
  // honest connection-state chip. Never block the page: if the probe fails
  // (network/parse), we leave the chip in its calm "checking" state.
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    fetchLiveWorkerHealth({ signal: controller.signal })
      .then((health) => {
        if (active) setLiveWorkerHealth(health);
      })
      .catch(() => {
        // Fail soft — the indicator stays in its unknown/checking state.
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  const isConfigured = target !== null;
  const hasModelChoice = Boolean(target ?? queryTarget);
  const isTraceReviewMode = requestedTraceId.length > 0 && session === null;
  const advancedApiToken = accountAuth.accountsEnabled ? '' : operatorApiToken.trim();
  const hasAdvancedApiToken = advancedApiToken.length > 0;
  const effectiveEvidenceToken = accountAuth.accountsEnabled
    ? accountAuth.token
    : advancedApiToken;
  const evidenceAccessMessage = accountAuth.accountsEnabled
    ? 'Sign in with the customer account that owns this audit to enable packet access.'
    : 'Enter the memory-only operator token in Advanced scale & fleet tools to enable packet access.';
  const advancedAccessMessage = accountAuth.accountsEnabled
    ? 'Distributed/fleet customer account mode remains OPEN and is unavailable. Tenant-bound service credentials are not implemented.'
    : 'An operator API token is required for distributed and fleet actions.';
  const sessionChips = useMemo(() => chipsForSession(session), [session]);
  const activeError = targetError ?? sessionError;
  const lifecycleStatus = lifecycleStatusFor(session, isAuditRunning || isTargetConnecting, activeError);
  const commandButtonEnabled = !isAuditRunning && !isTargetConnecting && (
    isTraceReviewMode ||
    !isConfigured ||
    (Boolean(target?.canRunAudit) && !session?.verdict)
  );
  const commandButtonLabel = isTraceReviewMode
    ? 'Start a new audit'
    : !hasModelChoice
    ? 'Choose a model'
    : !isConfigured
    ? isTargetConnecting
      ? 'Connecting selected model...'
      : 'Connect selected model'
    : isAuditRunning
      ? 'Running CAS audit...'
      : session?.verdict
        ? 'Verdict ready'
        : !target?.canRunAudit
          ? 'Audit unavailable'
        : 'Run CAS audit';
  const showVerdictExplainer = Boolean(session?.verdict || session?.verifier_decision);
  const visibleEvidenceTraceId = session?.evidence_packet_trace_id ?? requestedTraceId;
  const liveWorkerChip = useMemo(
    () => liveWorkerChipView(liveWorkerHealth),
    [liveWorkerHealth],
  );
  const customerAuditApiOptions = useMemo<CasHarnessAuditApiOptions>(() => ({
    authToken: accountAuth.token,
    fetchImpl: accountAuth.authenticatedFetch,
  }), [accountAuth.authenticatedFetch, accountAuth.token]);
  const advancedAuditApiOptions = useMemo<CasHarnessAuditApiOptions | undefined>(() => (
    advancedApiToken ? { authToken: advancedApiToken } : undefined
  ), [advancedApiToken]);
  const fleetRegisteredWorkers = fleetRun
    ? Math.max(fleetRun.registered_workers, registeredFleetWorker ? 1 : 0)
    : registeredFleetWorker
      ? 1
      : 0;
  const fleetTotalJobs = fleetRun?.total_jobs ?? distributedAudit?.total_workers ?? 0;
  const targetFleetWorkerId = assignedFleetWorkerId(distributedAudit, fleetRun);
  const canPrepareFleet =
    Boolean(distributedAudit && distributedAudit.status !== 'PLANNED' && !fleetRun) &&
    hasAdvancedApiToken &&
    !isFleetExecutorLoading;
  const canRegisterFleetWorker = hasAdvancedApiToken &&
    Boolean(distributedAudit && targetFleetWorkerId && !registeredFleetWorker) &&
    !isFleetExecutorLoading;
  const canLeaseFleetJob = hasAdvancedApiToken &&
    Boolean(fleetRun && registeredFleetWorker && !leasedFleetJob) &&
    !isFleetExecutorLoading;
  const canSubmitFleetReceipt =
    hasAdvancedApiToken && Boolean(
      fleetRun &&
        leasedFleetJob &&
        leasedFleetJob.status === 'leased' &&
        leasedFleetJob.lease_token,
    ) && !isFleetExecutorLoading;
  const canMergeFleet = hasAdvancedApiToken && canMergeFleetRun(fleetRun, isFleetExecutorLoading);
  const canRunFleetVerifier =
    hasAdvancedApiToken && Boolean(fleetRun?.merged_packet_trace_id && !fleetVerifierDecision) &&
    !isFleetExecutorLoading;

  const connectHostedPythiaTarget = async () => {
    setSession(null);
    setSessionError(null);
    setTargetError(null);
    setIsTargetConnecting(true);
    try {
      const verification = await verifyCasHarnessModelTarget({
        target: {
          kind: 'hosted_open_weight',
          model_id: HOSTED_PYTHIA_TARGET.modelId,
        },
      });
      setTarget({
        ...HOSTED_PYTHIA_TARGET,
        modelId: verification.target.model_id,
        provider: verification.target.provider,
        endpointUrl: verification.target.endpoint_url,
        connectionId: verification.connection_id,
        checkedAt: verification.checked_at,
        statusDetail: verification.detail,
        canRunAudit: verification.can_run_audit,
        evidencePacketTraceId: null,
      });
    } catch (error) {
      setTarget(null);
      setTargetError(
        error instanceof Error ? error.message : 'Model target verification failed',
      );
    } finally {
      setIsTargetConnecting(false);
    }
  };

  const loadS7F28PacketTarget = () => {
    setSession(null);
    setSessionError(null);
    setTargetError(null);
    setIsTargetConnecting(false);
    setIsAuditRunning(false);
    setTarget({
      ...S7_F28_PACKET_TARGET,
      checkedAt: new Date().toISOString(),
    });
  };

  const loadStage940EPacketTarget = () => {
    setSession(null);
    setSessionError(null);
    setTargetError(null);
    setIsTargetConnecting(false);
    setIsAuditRunning(false);
    setTarget({
      ...STAGE9_40E_PACKET_TARGET,
      checkedAt: new Date().toISOString(),
    });
  };

  const disconnectTarget = () => {
    setTarget(null);
    setSession(null);
    setSessionError(null);
    setTargetError(null);
    setIsTargetConnecting(false);
    setIsAuditRunning(false);
    setByokApiKey('');
  };

  const runAudit = async () => {
    if (!target || !target.canRunAudit) return;
    const trimmedKey = byokApiKey.trim();
    // The customer key is request-scoped. Keep it only in this local closure
    // and clear the rendered/input state before any network work begins.
    setByokApiKey('');
    setSessionError(null);
    setTargetError(null);
    setIsAuditRunning(true);
    try {
      const created = await createCasHarnessAuditSession({
        model_id: target.modelId,
        endpoint_url: target.endpointUrl ?? undefined,
        audit_mode: 'BALANCED',
        scenario_text: target.scenarioText,
        selected_modules: SELECTED_MODULES,
        evidence_packet_trace_id: target.evidencePacketTraceId ?? undefined,
      }, customerAuditApiOptions);
      setSession(created);
      const started = await startCasHarnessAuditSession(
        created.audit_id,
        { ...customerAuditApiOptions, apiKey: trimmedKey || undefined },
      );
      setSession(started);
    } catch (error) {
      setSessionError(
        error instanceof Error ? error.message : 'Audit session request failed',
      );
    } finally {
      setIsAuditRunning(false);
    }
  };

  const runPrimaryCommand = () => {
    if (isTraceReviewMode) {
      navigate('/model-config');
      return;
    }
    if (!hasModelChoice) {
      navigate('/model-config');
      return;
    }
    if (!isConfigured) {
      void connectHostedPythiaTarget();
      return;
    }
    if (!target.canRunAudit) return;
    void runAudit();
  };

  const loadEnterprisePlan = async (size: EnterpriseScalePlanSize) => {
    setEnterprisePlanSize(size);
    setEnterprisePlan(getEnterpriseScalePlan(size));
    setEnterprisePlanError(null);
    setDistributedAudit(null);
    setDistributedAuditError(null);
    setFleetRun(null);
    setRegisteredFleetWorker(null);
    setLeasedFleetJob(null);
    setFleetVerifierDecision(null);
    setFleetExecutorError(null);
    setIsEnterprisePlanLoading(true);
    try {
      const plan = await createCasHarnessScalePlan(SCALE_PLAN_REQUESTS[size]);
      setEnterprisePlan(enterpriseScalePlanFromApi(plan));
    } catch (error) {
      setEnterprisePlanError(
        error instanceof Error
          ? `Backend planner unavailable; showing local planning scaffold. ${error.message}`
          : 'Backend planner unavailable; showing local planning scaffold.',
      );
    } finally {
      setIsEnterprisePlanLoading(false);
    }
  };

  const createDistributedRun = async () => {
    if (!hasAdvancedApiToken) {
      setDistributedAuditError(advancedAccessMessage);
      return;
    }
    setDistributedAuditError(null);
    setFleetRun(null);
    setRegisteredFleetWorker(null);
    setLeasedFleetJob(null);
    setFleetVerifierDecision(null);
    setFleetExecutorError(null);
    setIsDistributedAuditLoading(true);
    try {
      const audit = await createCasHarnessDistributedAudit(
        SCALE_PLAN_REQUESTS[enterprisePlanSize],
        advancedAuditApiOptions,
      );
      setDistributedAudit(audit);
    } catch (error) {
      setDistributedAuditError(
        error instanceof Error ? error.message : 'Distributed audit run creation failed',
      );
    } finally {
      setIsDistributedAuditLoading(false);
    }
  };

  const dispatchDistributedRun = async () => {
    if (!distributedAudit) return;
    if (!hasAdvancedApiToken) {
      setDistributedAuditError(advancedAccessMessage);
      return;
    }
    setDistributedAuditError(null);
    setIsDistributedAuditLoading(true);
    try {
      const audit = await dispatchCasHarnessDistributedAudit(
        distributedAudit.audit_id,
        advancedAuditApiOptions,
      );
      setDistributedAudit(audit);
    } catch (error) {
      setDistributedAuditError(
        error instanceof Error ? error.message : 'Distributed worker dispatch failed',
      );
    } finally {
      setIsDistributedAuditLoading(false);
    }
  };

  const mergeDistributedRun = async () => {
    if (!distributedAudit) return;
    if (!hasAdvancedApiToken) {
      setDistributedAuditError(advancedAccessMessage);
      return;
    }
    setDistributedAuditError(null);
    setIsDistributedAuditLoading(true);
    try {
      const audit = await mergeCasHarnessDistributedAudit(
        distributedAudit.audit_id,
        advancedAuditApiOptions,
      );
      setDistributedAudit(audit);
    } catch (error) {
      setDistributedAuditError(
        error instanceof Error ? error.message : 'Distributed evidence merge failed',
      );
    } finally {
      setIsDistributedAuditLoading(false);
    }
  };

  const prepareFleet = async () => {
    if (!distributedAudit) return;
    if (!hasAdvancedApiToken) {
      setFleetExecutorError(advancedAccessMessage);
      return;
    }
    setFleetExecutorError(null);
    setIsFleetExecutorLoading(true);
    try {
      const run = await prepareCasHarnessFleetRun(
        distributedAudit.audit_id,
        advancedAuditApiOptions,
      );
      setFleetRun(run);
      setLeasedFleetJob(null);
      setFleetVerifierDecision(null);
    } catch (error) {
      setFleetExecutorError(
        error instanceof Error ? error.message : 'Fleet preparation failed',
      );
    } finally {
      setIsFleetExecutorLoading(false);
    }
  };

  const registerDemoFleetWorker = async () => {
    if (!distributedAudit || !targetFleetWorkerId) return;
    if (!hasAdvancedApiToken) {
      setFleetExecutorError(advancedAccessMessage);
      return;
    }
    setFleetExecutorError(null);
    setIsFleetExecutorLoading(true);
    try {
      const worker = await registerCasHarnessFleetWorker({
        worker_id: targetFleetWorkerId,
        model_id: distributedAudit.plan.model_id,
        worker_url: `local://${targetFleetWorkerId}`,
        gpu_type: 'H100-80GB',
        capacity: 1,
        supported_methods: [
          'foundation_probe',
          'rpm_gate_check',
          'inversion_scan',
          'blindspot_detection',
          'verification_stack',
          'evidence_packet',
        ],
      }, advancedAuditApiOptions);
      setRegisteredFleetWorker(worker);
      setFleetVerifierDecision(null);
      setFleetRun((run) =>
        run
          ? {
              ...run,
              registered_workers: Math.max(run.registered_workers, 1),
              updated_at: worker.last_heartbeat_at,
            }
          : run,
      );
    } catch (error) {
      setFleetExecutorError(
        error instanceof Error ? error.message : 'Demo Probe Worker registration failed',
      );
    } finally {
      setIsFleetExecutorLoading(false);
    }
  };

  const leaseOneFleetJob = async () => {
    if (!distributedAudit || !registeredFleetWorker) return;
    if (!hasAdvancedApiToken) {
      setFleetExecutorError(advancedAccessMessage);
      return;
    }
    setFleetExecutorError(null);
    setIsFleetExecutorLoading(true);
    try {
      const job = await leaseCasHarnessFleetJob(
        distributedAudit.audit_id,
        {
          worker_id: registeredFleetWorker.worker_id,
        },
        advancedAuditApiOptions,
      );
      if (!job) {
        setFleetExecutorError('No fleet jobs are available for this worker.');
        return;
      }
      setLeasedFleetJob(job);
      setFleetVerifierDecision(null);
      setFleetRun((run) => (run ? replaceFleetJob(run, job) : run));
    } catch (error) {
      setFleetExecutorError(
        error instanceof Error ? error.message : 'Fleet job lease failed',
      );
    } finally {
      setIsFleetExecutorLoading(false);
    }
  };

  const submitOneFleetReceipt = async () => {
    if (!distributedAudit || !registeredFleetWorker || !leasedFleetJob?.lease_token) return;
    if (!hasAdvancedApiToken) {
      setFleetExecutorError(advancedAccessMessage);
      return;
    }
    setFleetExecutorError(null);
    setIsFleetExecutorLoading(true);
    try {
      const producedOutputs = leasedFleetJob.expected_outputs;
      const missingOutputs: string[] = [];
      const evidencePacketFragmentRef = await buildCasHarnessFleetEvidenceFragmentRef({
        audit_id: distributedAudit.audit_id,
        job_id: leasedFleetJob.job_id,
        worker_id: registeredFleetWorker.worker_id,
        model_id: registeredFleetWorker.model_id,
        layer_start: leasedFleetJob.layer_start,
        layer_end: leasedFleetJob.layer_end,
        shard_id: leasedFleetJob.shard_id,
        expected_outputs: leasedFleetJob.expected_outputs,
        produced_outputs: producedOutputs,
        missing_outputs: missingOutputs,
      });
      const run = await submitCasHarnessFleetJobReceipt(
        distributedAudit.audit_id,
        leasedFleetJob.job_id,
        {
          worker_id: registeredFleetWorker.worker_id,
          lease_token: leasedFleetJob.lease_token,
          produced_outputs: producedOutputs,
          missing_outputs: missingOutputs,
          evidence_packet_fragment_ref: evidencePacketFragmentRef,
          job_status: 'completed',
        },
        advancedAuditApiOptions,
      );
      setFleetRun(run);
      setLeasedFleetJob(null);
      setFleetVerifierDecision(null);
    } catch (error) {
      setFleetExecutorError(
        error instanceof Error ? error.message : 'Fleet receipt submission failed',
      );
    } finally {
      setIsFleetExecutorLoading(false);
    }
  };

  const mergeFleet = async () => {
    if (!distributedAudit) return;
    if (!hasAdvancedApiToken) {
      setFleetExecutorError(advancedAccessMessage);
      return;
    }
    setFleetExecutorError(null);
    setIsFleetExecutorLoading(true);
    try {
      const run = await mergeCasHarnessFleetRun(
        distributedAudit.audit_id,
        advancedAuditApiOptions,
      );
      setFleetRun(run);
      setFleetVerifierDecision(null);
    } catch (error) {
      setFleetExecutorError(
        error instanceof Error ? error.message : 'Fleet evidence merge failed',
      );
    } finally {
      setIsFleetExecutorLoading(false);
    }
  };

  const runFleetVerifier = async () => {
    if (!distributedAudit) return;
    if (!hasAdvancedApiToken) {
      setFleetExecutorError(advancedAccessMessage);
      return;
    }
    setFleetExecutorError(null);
    setIsFleetExecutorLoading(true);
    try {
      const decision = await verifyCasHarnessFleetRun(
        distributedAudit.audit_id,
        advancedAuditApiOptions,
      );
      setFleetVerifierDecision(decision);
    } catch (error) {
      setFleetExecutorError(
        error instanceof Error ? error.message : 'Fleet verifier decision failed',
      );
    } finally {
      setIsFleetExecutorLoading(false);
    }
  };

  return (
    <>
      <style>{headingWaveCss}</style>
      <PageShell cardMaxWidth={1180}>
      <GlassPanel intensity="regular" padding={24} ariaLabel="CAS Harness Audit Console">
        <div style={topGridStyle}>
          <div>
            <p style={eyebrowStyle}>CAS Harness Audit Console</p>
            <AuditPopover
              briefing="A reviewer attaches a model, runs the audit, and receives ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW with confidence and proof chips. Paid entitlement and billing remain OPEN."
              block
              placement="bottom"
              width={360}
            >
              <h1 className="cas-heading-wave" style={headingWaveStyle}>
                Connect a model. Run a CAS audit. Return a verdict with evidence.
              </h1>
            </AuditPopover>
            <AuditPopover
              briefing="The console keeps the visible path simple. Deeper explanations open only when the reviewer asks for them."
              placement="bottom"
              width={330}
            >
              <p style={monikerStyle}>TURN YOUR BLACK BOX INTO A GLASS HOUSE</p>
            </AuditPopover>
          </div>

          <ModelConnectionCard
            status={
              isTargetConnecting
                ? 'connecting'
                : targetError
                  ? 'error'
                  : isConfigured
                    ? 'connected'
                    : 'disconnected'
            }
            modelName={target?.modelId ?? queryTarget?.modelId ?? 'No model selected'}
            provider={target?.provider ?? queryTarget?.provider ?? 'Choose a supported model first'}
            endpointLabel={target?.endpointLabel ?? queryTarget?.endpointLabel ?? 'Configure in Model'}
            showSelectionDetails={Boolean(target ?? queryTarget)}
            statusDetail={
              targetError
                ? targetError
                : isConfigured
                  ? target.statusDetail
                  : queryTarget
                    ? 'Pythia-160M selected. Connect it before running a CAS Harness audit.'
                    : 'Choose a supported target before connecting or running an audit.'
            }
            lastChecked={
              session
                ? 'Backend session accepted'
                : target?.checkedAt
                  ? 'Target verified'
                  : undefined
            }
            isAuditRunning={isAuditRunning}
            canRunAudit={Boolean(target?.canRunAudit)}
            onConnect={hasModelChoice ? connectHostedPythiaTarget : () => navigate('/model-config')}
            onDisconnect={disconnectTarget}
            onRunAudit={runAudit}
          />
        </div>

        <section style={commandCenterStyle} aria-label="CAS audit command center">
          <div style={commandHeaderStyle}>
            <div>
              <h2 style={commandTitleStyle}>Audit command center</h2>
              <AuditPopover
                briefing="The launch path stays linear: choose a model, connect the target, run CAS, track progress, then review the evidence-gated result."
                placement="bottom"
                width={340}
            >
              <p style={commandSubtitleStyle}>Choose. Connect. Run. Track. Review.</p>
            </AuditPopover>
          </div>
          <div style={commandActionsStyle}>
            <span
              role="status"
              aria-label={`Live worker status: ${liveWorkerChip.label}`}
              title={liveWorkerChip.label}
              style={{
                ...liveWorkerChipBaseStyle,
                border: `1px solid ${liveWorkerChip.accent}59`,
                background: `${liveWorkerChip.accent}1f`,
                color: liveWorkerChip.accent,
              }}
            >
              <span style={liveWorkerDotStyle(liveWorkerChip.accent)} aria-hidden="true" />
              {liveWorkerChip.label}
            </span>
            <input
              type="password"
              aria-label="Bring your own provider API key (optional)"
              autoComplete="off"
              spellCheck={false}
              value={byokApiKey}
              onChange={(event) => setByokApiKey(event.target.value)}
              placeholder="Your provider API key (optional, sent once, never stored)"
              disabled={isAuditRunning || isTargetConnecting}
              style={{
                flex: '1 1 240px',
                minWidth: 220,
                padding: '8px 12px',
                borderRadius: 6,
                border: `1px solid ${COLORS.borderStrong}`,
                background: COLORS.bgPanel,
                color: COLORS.textPrimary,
                fontFamily: THEME.fontMono,
                fontSize: 12,
              }}
            />
            <button
              type="button"
              style={commandActionStyle(commandButtonEnabled)}
              onClick={runPrimaryCommand}
              disabled={!commandButtonEnabled}
            >
              {commandButtonLabel}
            </button>
          </div>
        </div>
          <section style={flowStyle} aria-label="Audit workflow">
            {AUDIT_STEPS.map((step, index) => {
              const state = commandStateFor(
                index,
                hasModelChoice,
                isConfigured,
                session,
                isAuditRunning,
                isTargetConnecting,
                targetError,
                sessionError,
                isTraceReviewMode,
              );
              return (
                <article
                  key={step.label}
                  style={stepStyle(state)}
                  data-launch-step={step.command.toLowerCase()}
                  data-state={state}
                >
                  <AuditPopover briefing={step.detail} block placement="bottom">
                    <span style={stepNumberStyle}>{index + 1}</span>
                    <h2 style={stepLabelStyle}>{step.command}</h2>
                    <p style={verdictLabelStyle}>{step.label}</p>
                    <span style={commandBadgeStyle(state)}>
                      {commandStatusLabel(state)}
                    </span>
                  </AuditPopover>
                </article>
              );
            })}
          </section>
        </section>

        <details style={advancedDetailsStyle} data-testid="advanced-scale-fleet-tools">
          <summary style={advancedSummaryStyle}>Advanced scale &amp; fleet tools</summary>
          <div style={advancedStackStyle}>
            <section aria-label="Saved packet tools" style={savedPacketActionsStyle}>
              <button
                type="button"
                style={commandActionStyle(!isAuditRunning && !isTargetConnecting)}
                onClick={loadStage940EPacketTarget}
                disabled={isAuditRunning || isTargetConnecting}
              >
                Load 20B validation packet
              </button>
              <button
                type="button"
                style={commandActionStyle(!isAuditRunning && !isTargetConnecting)}
                onClick={loadS7F28PacketTarget}
                disabled={isAuditRunning || isTargetConnecting}
              >
                Load 20B review packet
              </button>
            </section>

            <div style={singleColumnStyle}>
              <EnterpriseScalePlanCard
            plan={enterprisePlan}
            selectedSize={enterprisePlanSize}
            isLoading={isEnterprisePlanLoading}
            error={enterprisePlanError}
            onSelectSize={(size) => {
              void loadEnterprisePlan(size);
            }}
              />
            </div>

            <div style={singleColumnStyle}>
              <DistributedAuditRunPanel
            audit={distributedAudit}
            isLoading={isDistributedAuditLoading}
            error={distributedAuditError}
            hasProtectedAccess={hasAdvancedApiToken}
            accessNote={advancedAccessMessage}
            onCreateRun={() => {
              void createDistributedRun();
            }}
            onDispatchRun={() => {
              void dispatchDistributedRun();
            }}
            onMergeRun={() => {
              void mergeDistributedRun();
            }}
              />
            </div>

            <div style={singleColumnStyle}>
              <FleetExecutorPanel
            registeredWorkers={fleetRegisteredWorkers}
            leasedJobs={fleetRun?.leased_jobs ?? 0}
            staleWorkers={fleetRun?.stale_workers.length ?? 0}
            completedFragments={fleetRun?.completed_fragments ?? 0}
            totalJobs={fleetTotalJobs}
            mergedPacketStatus={mergedPacketStatusFor(fleetRun)}
            verifierGateStatus={fleetRun?.verifier_gate_status ?? 'not_prepared'}
            readiness={fleetRun?.readiness ?? null}
          />
          <section style={fleetControlPanelStyle} aria-label="Fleet executor controls">
            <div style={fleetControlHeaderStyle}>
              <div>
                <h2 style={fleetControlTitleStyle}>Fleet executor controls</h2>
                <p style={fleetNoticeStyle}>
                  These controls exercise the real fleet API path. Fleet merge
                  stays blocked until a leased job returns an Evidence Packet
                  fragment.
                </p>
                {accountAuth.accountsEnabled ? (
                  <p role="note" style={{ ...fleetNoticeStyle, color: '#fef3c7' }}>
                    Distributed/fleet customer account mode remains OPEN and is unavailable.
                    Tenant-bound service credentials are not implemented, so customer Bearer tokens
                    are never sent to these routes.
                  </p>
                ) : (
                  <>
                    <label htmlFor="advanced-api-token" style={verdictLabelStyle}>
                      Operator tools API token
                    </label>
                    <input
                      id="advanced-api-token"
                      type="password"
                      autoComplete="off"
                      spellCheck={false}
                      value={operatorApiToken}
                      onChange={(event) => setOperatorApiToken(event.target.value)}
                      placeholder="Memory-only operator token"
                      style={fleetAuthInputStyle}
                    />
                    <p role="note" style={fleetNoticeStyle}>
                      This memory-only override exists only in account-OFF operator posture.
                    </p>
                  </>
                )}
                {!hasAdvancedApiToken && !accountAuth.accountsEnabled ? (
                  <p role="note" style={fleetNoticeStyle}>
                    Distributed and fleet actions stay disabled until operator authorization is available.
                  </p>
                ) : null}
              </div>
              <div style={fleetButtonRowStyle}>
                <button
                  type="button"
                  style={commandActionStyle(canPrepareFleet)}
                  disabled={!canPrepareFleet}
                  onClick={() => {
                    void prepareFleet();
                  }}
                >
                  Prepare fleet
                </button>
                <button
                  type="button"
                  style={commandActionStyle(canRegisterFleetWorker)}
                  disabled={!canRegisterFleetWorker}
                  onClick={() => {
                    void registerDemoFleetWorker();
                  }}
                >
                  Register demo worker
                </button>
                <button
                  type="button"
                  style={commandActionStyle(canLeaseFleetJob)}
                  disabled={!canLeaseFleetJob}
                  onClick={() => {
                    void leaseOneFleetJob();
                  }}
                >
                  Lease one job
                </button>
                <button
                  type="button"
                  style={commandActionStyle(canSubmitFleetReceipt)}
                  disabled={!canSubmitFleetReceipt}
                  onClick={() => {
                    void submitOneFleetReceipt();
                  }}
                >
                  Submit one receipt
                </button>
                <button
                  type="button"
                  style={commandActionStyle(canMergeFleet)}
                  disabled={!canMergeFleet}
                  onClick={() => {
                    void mergeFleet();
                  }}
                >
                  Merge fleet
                </button>
                <button
                  type="button"
                  style={commandActionStyle(canRunFleetVerifier)}
                  disabled={!canRunFleetVerifier}
                  onClick={() => {
                    void runFleetVerifier();
                  }}
                >
                  Run fleet verifier
                </button>
              </div>
            </div>
            {isFleetExecutorLoading ? (
              <p role="status" style={fleetNoticeStyle}>
                Fleet executor request in flight...
              </p>
            ) : null}
            {fleetExecutorError ? (
              <p role="status" style={{ ...fleetNoticeStyle, color: '#fecaca' }}>
                {fleetExecutorError}
              </p>
            ) : null}
            {fleetRun?.merged_packet_trace_id ? (
              <p role="status" style={fleetNoticeStyle}>
                Merged Evidence Packet: {fleetRun.merged_packet_trace_id}
              </p>
            ) : null}
            {fleetVerifierDecision ? (
              <div
                data-testid="fleet-verifier-decision"
                style={{
                  display: 'grid',
                  gap: 8,
                  padding: 12,
                  borderRadius: 8,
                  border: '1px solid rgba(45, 212, 191, 0.28)',
                  background: 'rgba(15, 23, 42, 0.54)',
                }}
              >
                <p style={{ ...fleetNoticeStyle, color: COLORS.textPrimary, fontWeight: 800 }}>
                  Fleet verifier decision:{' '}
                  {fleetVerifierDecision.verdict.replace(/_/g, ' ')}
                </p>
                <p style={fleetNoticeStyle}>
                  Confidence:{' '}
                  {fleetVerifierDecision.confidence === null
                    ? 'not available'
                    : `${Math.round(fleetVerifierDecision.confidence * 100)}%`}
                  {' '}· Proof chips: {fleetVerifierDecision.proof_chip_gate}
                </p>
                <p style={fleetNoticeStyle}>{fleetVerifierDecision.reason}</p>
                {fleetVerifierDecision.blockers.length > 0 ? (
                  <p style={fleetNoticeStyle}>
                    Blocker: {fleetVerifierDecision.blockers.join(' ')}
                  </p>
                ) : null}
              </div>
            ) : null}
            {fleetRun ? (
              <p style={fleetNoticeStyle}>
                Fleet merge reason: {fleetRun.merge_reason}
              </p>
            ) : null}
              </section>
            </div>
          </div>
        </details>

        <div style={session ? lowerGridStyle : singleColumnStyle}>
          <AuditSessionProgress
            status={lifecycleStatus}
            detail={progressDetail(lifecycleStatus, isConfigured)}
            errorMessage={activeError}
          />
          {session ? (
            <AuditSessionSummaryCard
              auditId={session.audit_id}
              modelTarget={session.model_id ?? target?.modelId}
              mode={session.audit_mode}
              selectedModulesCount={session.selected_modules.length}
              status={lifecycleStatus}
              verdict={session.verdict ?? null}
              confidence={session.confidence ?? null}
              evidencePacketId={session.evidence_packet_trace_id}
              updatedAt={session.updated_at}
            />
          ) : null}
          {session?.audit_scope ? (
            <AuditScopeBanner scope={session.audit_scope} />
          ) : null}
        </div>

        <div style={singleColumnStyle}>
          <div style={verdictStackStyle}>
            <AuditVerdictCard
              verdict={session?.verdict ?? null}
              confidence={session?.confidence ?? null}
              summary={session?.verdict ? verdictSummaryFor(session) : undefined}
              evidencePacket={
                session?.evidence_packet_trace_id
                  ? { packetId: session.evidence_packet_trace_id }
                  : undefined
              }
              onInspectInAtlas={session ? () => navigate('/cockpit') : undefined}
            />
            <EvidencePacketActions
              key={visibleEvidenceTraceId || 'no-evidence-packet'}
              traceId={visibleEvidenceTraceId}
              authToken={effectiveEvidenceToken}
              fetchImpl={accountAuth.accountsEnabled ? accountAuth.authenticatedFetch : undefined}
              missingAuthMessage={evidenceAccessMessage}
            />
            {showVerdictExplainer ? (
              <AuditVerdictExplainer
                verdict={session?.verdict ?? null}
                confidence={session?.confidence ?? null}
                chips={sessionChips}
                verifierDecision={session?.verifier_decision ?? null}
                lifecycleMessage={latestLifecycleMessage(session)}
              />
            ) : null}
            {visibleEvidenceTraceId ? (
              <>
                <EvidencePacketVerificationPanel
                  key={visibleEvidenceTraceId}
                  traceId={visibleEvidenceTraceId}
                  authToken={effectiveEvidenceToken}
                  fetchImpl={accountAuth.accountsEnabled ? accountAuth.authenticatedFetch : undefined}
                  missingAuthMessage={evidenceAccessMessage}
                />
                <EvidencePacketFlightRecorderFaq />
              </>
            ) : null}
          </div>
        </div>
      </GlassPanel>
      </PageShell>
    </>
  );
}
