import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { GlassPanel } from '../components/ui/GlassPanel';
import { AuditSessionProgress } from '../components/audit/AuditSessionProgress';
import type { AuditLifecycleStatus } from '../components/audit/AuditSessionProgress';
import { AuditStageLadder } from '../components/audit/AuditStageLadder';
import { AuditRunTranscript } from '../components/audit/AuditRunTranscript';
import { AuditRunHeader } from '../components/audit/AuditRunHeader';
import { AuditComposer } from '../components/audit/AuditComposer';
import { AuditScaleFleetTab } from '../components/audit/AuditScaleFleetTab';
import { MethodologyDrawer } from '../components/audit/MethodologyDrawer';
import { AuditAppFrame } from '../components/shell/AuditAppFrame';
import { AuditRail } from '../components/shell/AuditRail';
import { EvidenceRail } from '../components/shell/EvidenceRail';
import { Disclosure } from '../components/ui/Disclosure';
import { useAccountAuth } from '../components/auth/AccountAuthProvider';
import {
  buildDefaultProvenanceChips,
  isSessionCustomerSafe,
  licenseStateFor,
  scopeRibbonModel,
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
import { TreeOfLifeMark } from '../components/brand/TreeOfLifeMark';
import {
  ACCENT_AMBER,
  ACCENT_TEAL,
  COLORS,
} from '../lib/designTokens';

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

const M1_REFERENCE_TARGET: AuditTargetConfig = {
  modelId: 'EleutherAI/pythia-160m',
  provider: 'CAS Harness reference path',
  endpointLabel: '/api/cas-harness/audit/target/verify',
  scenarioText:
    'Reference audit smoke scenario: validate the CAS Harness audit contract without fabricating a verdict.',
  endpointUrl: null,
  connectionId: 'cas-target-reference-pending',
  checkedAt: '',
  statusDetail: 'Reference target has not been verified by the backend yet.',
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

const workspaceCardStyle: CSSProperties = {
  display: 'grid',
  gap: 18,
};

const ladderHeaderStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 10,
};

const whyVerdictButtonStyle: CSSProperties = {
  minHeight: 30,
  padding: '5px 11px',
  borderRadius: 6,
  border: '1px solid rgba(45, 212, 191, 0.42)',
  background: 'rgba(45, 212, 191, 0.10)',
  color: '#ccfbf1',
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 12,
  fontWeight: 700,
};

const composerEmptyStateStyle: CSSProperties = {
  display: 'grid',
  justifyItems: 'center',
  gap: 8,
  padding: '10px 8px 6px',
  textAlign: 'center',
};

const composerEmptyTitleStyle: CSSProperties = {
  margin: '4px 0 0',
  color: COLORS.textPrimary,
  fontSize: 16,
  fontWeight: 850,
};

const composerEmptyBodyStyle: CSSProperties = {
  margin: 0,
  maxWidth: 360,
  color: COLORS.textSecondary,
  fontSize: 12.5,
  lineHeight: 1.5,
};

const ladderCardStyle: CSSProperties = {
  display: 'grid',
  gap: 14,
  padding: 16,
  borderRadius: 10,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(2, 6, 23, 0.34)',
};

const sectionEyebrowStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
};

export default function AuditConsolePage() {
  const navigate = useNavigate();
  const accountAuth = useAccountAuth();
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
  const [fleetAuthToken, setFleetAuthToken] = useState('');
  const [fleetExecutorError, setFleetExecutorError] = useState<string | null>(null);
  const [isFleetExecutorLoading, setIsFleetExecutorLoading] = useState(false);
  const [liveWorkerHealth, setLiveWorkerHealth] =
    useState<CasHarnessLiveWorkerHealth | null>(null);
  // Bumped after a run resolves so the left-rail Recent Runs list refetches.
  const [recentReloadKey, setRecentReloadKey] = useState(0);
  // "Why this verdict" methodology drawer (the only home for Stage-19/20/21,
  // accepted_accuracy, Generation Readiness, and the full proof prose).
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);
  const accountAuthToken = accountAuth.session?.token ?? '';
  const accountLabel = accountAuth.session?.account?.email_or_username ?? accountAuth.session?.email ?? null;

  // Probe the live-trace worker once on mount so the run controls can show an
  // honest connection-state chip. Never block the page: if the probe fails
  // (network/parse), we leave the chip in its calm "checking" state.
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    fetchLiveWorkerHealth({
      signal: controller.signal,
      authToken: accountAuthToken || undefined,
    })
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
  }, [accountAuthToken]);

  const isConfigured = target !== null;
  const sessionChips = useMemo(() => chipsForSession(session), [session]);
  const activeError = targetError ?? sessionError;
  const lifecycleStatus = lifecycleStatusFor(session, isAuditRunning || isTargetConnecting, activeError);
  const commandButtonEnabled =
    !isAuditRunning && !isTargetConnecting && (!isConfigured || !session?.verdict);
  const commandButtonLabel = !isConfigured
    ? isTargetConnecting
      ? 'Connecting target'
      : 'Prepare target'
    : isAuditRunning
      ? 'Running audit'
      : session?.verdict
        ? 'Verdict ready'
        : 'Run CAS audit';
  const showVerdictExplainer = Boolean(session?.verdict || session?.verifier_decision);
  const liveWorkerChip = useMemo(
    () => liveWorkerChipView(liveWorkerHealth),
    [liveWorkerHealth],
  );
  const protectedAuditApiOptions = useMemo<CasHarnessAuditApiOptions | undefined>(() => {
    const authToken = accountAuthToken.trim() || fleetAuthToken.trim();
    return authToken ? { authToken } : undefined;
  }, [accountAuthToken, fleetAuthToken]);
  const effectiveAuthToken = protectedAuditApiOptions?.authToken ?? null;
  const fleetRegisteredWorkers = fleetRun
    ? Math.max(fleetRun.registered_workers, registeredFleetWorker ? 1 : 0)
    : registeredFleetWorker
      ? 1
      : 0;
  const fleetTotalJobs = fleetRun?.total_jobs ?? distributedAudit?.total_workers ?? 0;
  const targetFleetWorkerId = assignedFleetWorkerId(distributedAudit, fleetRun);
  const canPrepareFleet =
    Boolean(distributedAudit && distributedAudit.status !== 'PLANNED' && !fleetRun) &&
    !isFleetExecutorLoading;
  const canRegisterFleetWorker = Boolean(distributedAudit && targetFleetWorkerId && !registeredFleetWorker) &&
    !isFleetExecutorLoading;
  const canLeaseFleetJob = Boolean(fleetRun && registeredFleetWorker && !leasedFleetJob) &&
    !isFleetExecutorLoading;
  const canSubmitFleetReceipt =
    Boolean(
      fleetRun &&
        leasedFleetJob &&
        leasedFleetJob.status === 'leased' &&
        leasedFleetJob.lease_token,
    ) && !isFleetExecutorLoading;
  const canMergeFleet = canMergeFleetRun(fleetRun, isFleetExecutorLoading);
  const canRunFleetVerifier =
    Boolean(fleetRun?.merged_packet_trace_id && !fleetVerifierDecision) &&
    !isFleetExecutorLoading;

  // --- Audit Bench derived values ---------------------------------------
  // Customer-safe gate for the verdict chip. A clean teal ACCEPT only renders
  // when this is true; otherwise an ACCEPT shows the amber scoped band.
  const sessionCustomerSafe = useMemo(
    () => isSessionCustomerSafe(session),
    [session],
  );
  // Persistent scope model (validation-vs-production). Drives the left-rail
  // scope chip and the right-rail ScopeRibbon from real verifier/scope signals.
  const scopeModel = useMemo(
    () => scopeRibbonModel(session?.verifier_decision ?? null, session?.audit_scope ?? null),
    [session],
  );
  const railScopeChip = scopeModel.scopeLabel
    ? { label: scopeModel.scopeLabel, validation: scopeModel.isValidationPacket }
    : null;
  // License state from the real entitlement signal available in this UI: a
  // protected bearer token, or the BYOK provider key. Unresolved => OPEN
  // (never speculatively LICENSED).
  const licenseState = useMemo(
    () =>
      licenseStateFor({
        authToken: effectiveAuthToken,
        redeemedKey: byokApiKey,
      }),
    [effectiveAuthToken, byokApiKey],
  );

  const connectReferenceTarget = async () => {
    setSession(null);
    setSessionError(null);
    setTargetError(null);
    setIsTargetConnecting(true);
    try {
      const verification = await verifyCasHarnessModelTarget({
        target: { kind: 'demo_reference' },
      }, protectedAuditApiOptions);
      setTarget({
        ...M1_REFERENCE_TARGET,
        modelId: verification.target.model_id,
        provider: verification.target.kind === 'demo_reference'
          ? 'CAS Harness reference path'
          : verification.target.provider,
        endpointUrl: verification.target.endpoint_url,
        connectionId: verification.connection_id,
        checkedAt: verification.checked_at,
        statusDetail: verification.reference_evidence_packet_trace_id
          ? `${verification.detail} Reference Evidence Packet ready: ${verification.reference_evidence_packet_trace_id}.`
          : verification.detail,
        canRunAudit: verification.can_run_audit,
        evidencePacketTraceId: verification.reference_evidence_packet_trace_id,
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
  };

  // Reset the workspace to a fresh audit (left-rail "+ New Audit" / brand mark).
  const startNewAudit = () => {
    disconnectTarget();
  };

  // Load a prior run from the left-rail Recent Runs list. The session already
  // carries its verdict / chips / scope, so we hydrate state directly without a
  // re-run. We do NOT fabricate a target; the run header reads from the session.
  const selectRecentSession = (recent: CasHarnessAuditSession) => {
    setSessionError(null);
    setTargetError(null);
    setIsTargetConnecting(false);
    setIsAuditRunning(false);
    setSession(recent);
  };

  const runAudit = async () => {
    if (!target) return;
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
      }, protectedAuditApiOptions);
      setSession(created);
      const trimmedKey = byokApiKey.trim();
      const started = await startCasHarnessAuditSession(
        created.audit_id,
        {
          ...protectedAuditApiOptions,
          apiKey: trimmedKey || undefined,
        },
      );
      setSession(started);
    } catch (error) {
      setSessionError(
        error instanceof Error ? error.message : 'Audit session request failed',
      );
    } finally {
      setIsAuditRunning(false);
      // Refresh the Recent Runs list now that a session exists/resolved.
      setRecentReloadKey((key) => key + 1);
    }
  };

  const runPrimaryCommand = () => {
    if (!isConfigured) {
      void connectReferenceTarget();
      return;
    }
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
      const plan = await createCasHarnessScalePlan(
        SCALE_PLAN_REQUESTS[size],
        protectedAuditApiOptions,
      );
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
        protectedAuditApiOptions,
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
    setDistributedAuditError(null);
    setIsDistributedAuditLoading(true);
    try {
      const audit = await dispatchCasHarnessDistributedAudit(
        distributedAudit.audit_id,
        protectedAuditApiOptions,
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
    setDistributedAuditError(null);
    setIsDistributedAuditLoading(true);
    try {
      const audit = await mergeCasHarnessDistributedAudit(
        distributedAudit.audit_id,
        protectedAuditApiOptions,
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
    setFleetExecutorError(null);
    setIsFleetExecutorLoading(true);
    try {
      const run = await prepareCasHarnessFleetRun(
        distributedAudit.audit_id,
        protectedAuditApiOptions,
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
      }, protectedAuditApiOptions);
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
    setFleetExecutorError(null);
    setIsFleetExecutorLoading(true);
    try {
      const job = await leaseCasHarnessFleetJob(
        distributedAudit.audit_id,
        {
          worker_id: registeredFleetWorker.worker_id,
        },
        protectedAuditApiOptions,
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
        protectedAuditApiOptions,
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
    setFleetExecutorError(null);
    setIsFleetExecutorLoading(true);
    try {
      const run = await mergeCasHarnessFleetRun(
        distributedAudit.audit_id,
        protectedAuditApiOptions,
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
    setFleetExecutorError(null);
    setIsFleetExecutorLoading(true);
    try {
      const decision = await verifyCasHarnessFleetRun(
        distributedAudit.audit_id,
        protectedAuditApiOptions,
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

  const logoutAccount = async (): Promise<void> => {
    await accountAuth.logout();
    navigate('/login', { replace: true });
  };

  const railNode = (
    <AuditRail
      licenseState={licenseState}
      scopeChip={railScopeChip}
      activeSessionId={session?.audit_id ?? null}
      onNewAudit={startNewAudit}
      onSelectSession={selectRecentSession}
      onHelp={() => setIsMethodologyOpen(true)}
      onSettings={() => navigate('/model-config')}
      reloadKey={recentReloadKey}
      authToken={effectiveAuthToken}
      accountLabel={accountLabel}
      onLogout={() => {
        void logoutAccount();
      }}
    />
  );

  const evidenceNode = (
    <EvidenceRail
      verdict={session?.verdict ?? null}
      confidence={session?.confidence ?? null}
      customerSafe={sessionCustomerSafe}
      chips={sessionChips}
      verifierDecision={session?.verifier_decision ?? null}
      auditScope={session?.audit_scope ?? null}
      evidencePacketTraceId={session?.evidence_packet_trace_id ?? null}
      authToken={effectiveAuthToken}
      onInspectInAtlas={session ? () => navigate('/cockpit') : undefined}
    />
  );

  const connectionStatus = isTargetConnecting
    ? 'connecting'
    : targetError
      ? 'error'
      : isConfigured
        ? 'connected'
        : 'disconnected';

  const composerEmptyState = !session && !isConfigured ? (
    <div className="cas-fade-in" style={composerEmptyStateStyle}>
      <TreeOfLifeMark size={72} animated title="CAS Harness" />
      <p style={composerEmptyTitleStyle}>Start an audit</p>
      <p style={composerEmptyBodyStyle}>
        Connect a model or load a demo packet, then run a CAS audit to get a
        verdict with evidence.
      </p>
    </div>
  ) : null;

  // Calm setup -> run transition: the run header fades in once when the
  // workspace crosses from the empty/setup state into an active run (keyed on
  // that boundary so it settles in, never replaying on every status tick).
  // prefers-reduced-motion freezes the fade via the global guard.
  const runPhaseKey = session || isConfigured ? 'run' : 'setup';

  const centerNode = (
    <>
      <div key={runPhaseKey} className="cas-fade-in">
        <AuditRunHeader
          auditId={session?.audit_id ?? null}
          modelTarget={session?.model_id ?? target?.modelId ?? null}
          mode={session?.audit_mode ?? (isConfigured ? 'BALANCED' : null)}
          status={lifecycleStatus}
        />
      </div>

      <AuditComposer
        connectionStatus={connectionStatus}
        modelName={target?.modelId ?? 'No model connected'}
        provider={target?.provider ?? 'License/API connector pending'}
        endpointLabel={target?.endpointLabel ?? 'Configure in Model'}
        statusDetail={
          targetError
            ? targetError
            : isConfigured
              ? target.statusDetail
              : 'Connect a supported target before running a CAS Harness audit.'
        }
        lastChecked={
          session
            ? 'Backend session accepted'
            : target?.checkedAt
              ? 'Target verified'
              : undefined
        }
        canRunAudit={Boolean(target?.canRunAudit)}
        onConnect={connectReferenceTarget}
        onDisconnect={disconnectTarget}
        mode="BALANCED"
        presets={[
          {
            id: 'stage9-40e',
            label: 'Load 20B validation packet',
            onSelect: loadStage940EPacketTarget,
          },
          {
            id: 's7-f28',
            label: 'Load 20B review packet',
            onSelect: loadS7F28PacketTarget,
          },
        ]}
        byokApiKey={byokApiKey}
        onByokApiKeyChange={setByokApiKey}
        isAuditRunning={isAuditRunning}
        isTargetConnecting={isTargetConnecting}
        onRun={runPrimaryCommand}
        runEnabled={commandButtonEnabled}
        runLabel={commandButtonLabel}
        liveChip={liveWorkerChip}
        emptyState={composerEmptyState}
      />

      <GlassPanel intensity="regular" padding={20} ariaLabel="Audit run progress and advanced tools">
        <div style={workspaceCardStyle}>
          <section style={ladderCardStyle} aria-label="Audit progress">
            <div style={ladderHeaderStyle}>
              <p style={sectionEyebrowStyle}>Audit progress</p>
              {showVerdictExplainer ? (
                <button
                  type="button"
                  style={whyVerdictButtonStyle}
                  onClick={() => setIsMethodologyOpen(true)}
                >
                  ? Why this verdict
                </button>
              ) : null}
            </div>
            <AuditStageLadder
              status={lifecycleStatus}
              verdict={session?.verdict ?? null}
            />
            <AuditRunTranscript session={session} />
          </section>

          <AuditSessionProgress
            status={lifecycleStatus}
            detail={progressDetail(lifecycleStatus, isConfigured)}
            errorMessage={activeError}
          />

          <Disclosure summary="Scale & fleet (advanced)">
            <AuditScaleFleetTab
              enterprisePlan={enterprisePlan}
              enterprisePlanSize={enterprisePlanSize}
              isEnterprisePlanLoading={isEnterprisePlanLoading}
              enterprisePlanError={enterprisePlanError}
              onSelectSize={(size) => {
                void loadEnterprisePlan(size);
              }}
              distributedAudit={distributedAudit}
              isDistributedAuditLoading={isDistributedAuditLoading}
              distributedAuditError={distributedAuditError}
              onCreateDistributedRun={() => {
                void createDistributedRun();
              }}
              onDispatchDistributedRun={() => {
                void dispatchDistributedRun();
              }}
              onMergeDistributedRun={() => {
                void mergeDistributedRun();
              }}
              fleetRegisteredWorkers={fleetRegisteredWorkers}
              fleetLeasedJobs={fleetRun?.leased_jobs ?? 0}
              fleetStaleWorkers={fleetRun?.stale_workers.length ?? 0}
              fleetCompletedFragments={fleetRun?.completed_fragments ?? 0}
              fleetTotalJobs={fleetTotalJobs}
              fleetMergedPacketStatus={mergedPacketStatusFor(fleetRun)}
              fleetVerifierGateStatus={fleetRun?.verifier_gate_status ?? 'not_prepared'}
              fleetReadiness={fleetRun?.readiness ?? null}
              fleetAuthToken={fleetAuthToken}
              onFleetAuthTokenChange={setFleetAuthToken}
              isFleetExecutorLoading={isFleetExecutorLoading}
              fleetExecutorError={fleetExecutorError}
              fleetRun={fleetRun}
              fleetVerifierDecision={fleetVerifierDecision}
              canPrepareFleet={canPrepareFleet}
              canRegisterFleetWorker={canRegisterFleetWorker}
              canLeaseFleetJob={canLeaseFleetJob}
              canSubmitFleetReceipt={canSubmitFleetReceipt}
              canMergeFleet={canMergeFleet}
              canRunFleetVerifier={canRunFleetVerifier}
              onPrepareFleet={() => {
                void prepareFleet();
              }}
              onRegisterFleetWorker={() => {
                void registerDemoFleetWorker();
              }}
              onLeaseFleetJob={() => {
                void leaseOneFleetJob();
              }}
              onSubmitFleetReceipt={() => {
                void submitOneFleetReceipt();
              }}
              onMergeFleet={() => {
                void mergeFleet();
              }}
              onRunFleetVerifier={() => {
                void runFleetVerifier();
              }}
            />
          </Disclosure>
        </div>
      </GlassPanel>

      <MethodologyDrawer
        open={isMethodologyOpen}
        onClose={() => setIsMethodologyOpen(false)}
        verdict={session?.verdict ?? null}
        confidence={session?.confidence ?? null}
        chips={sessionChips}
        verifierDecision={session?.verifier_decision ?? null}
        lifecycleMessage={latestLifecycleMessage(session)}
      />
    </>
  );

  return (
    <AuditAppFrame
      rail={railNode}
      center={centerNode}
      evidence={evidenceNode}
      authToken={effectiveAuthToken}
    />
  );
}
