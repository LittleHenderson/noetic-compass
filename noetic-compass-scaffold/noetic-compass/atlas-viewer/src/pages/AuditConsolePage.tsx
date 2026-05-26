import { useMemo, useState, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import { AuditSessionProgress, type AuditLifecycleStatus } from '../components/audit/AuditSessionProgress';
import { AuditSessionSummaryCard } from '../components/audit/AuditSessionSummaryCard';
import { AuditVerdictCard } from '../components/audit/AuditVerdictCard';
import { AuditVerdictExplainer } from '../components/audit/AuditVerdictExplainer';
import EnterpriseScalePlanCard from '../components/audit/EnterpriseScalePlanCard';
import { ModelConnectionCard } from '../components/audit/ModelConnectionCard';
import { AuditPopover } from '../components/audit/AuditPopover';
import {
  buildDefaultProvenanceChips,
  type ProvenanceChip,
} from '../lib/casHarnessAudit';
import {
  createCasHarnessScalePlan,
  createCasHarnessAuditSession,
  startCasHarnessAuditSession,
  verifyCasHarnessModelTarget,
  type CasHarnessAuditSession,
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
  ACCENT_CYAN,
  ACCENT_TEAL,
  COLORS,
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

const AUDIT_STEPS: AuditStep[] = [
  {
    label: 'Connect model',
    detail: 'Verify the model target, API route, and license gate.',
    command: 'CONNECT',
  },
  {
    label: 'Run CAS audit',
    detail: 'Run readout, causal, control, output, and packet checks.',
    command: 'RUN',
  },
  {
    label: 'Return verdict + evidence',
    detail: 'Return ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW with confidence and proof chips.',
    command: 'VERDICT',
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
  hasTarget: boolean,
  session: CasHarnessAuditSession | null,
  isAuditRunning: boolean,
  error: string | null,
): CommandState {
  if (error) return index < 2 ? 'done' : 'blocked';
  if (index === 0) return hasTarget ? 'done' : 'active';
  if (index === 1) {
    if (!hasTarget) return 'waiting';
    if (isAuditRunning) return 'active';
    return session ? 'done' : 'ready';
  }
  if (!session) return hasTarget ? 'waiting' : 'waiting';
  if (session.verdict) return 'done';
  return 'blocked';
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

export default function AuditConsolePage() {
  const navigate = useNavigate();
  const [target, setTarget] = useState<AuditTargetConfig | null>(null);
  const [session, setSession] = useState<CasHarnessAuditSession | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [targetError, setTargetError] = useState<string | null>(null);
  const [isTargetConnecting, setIsTargetConnecting] = useState(false);
  const [isAuditRunning, setIsAuditRunning] = useState(false);
  const [enterprisePlanSize, setEnterprisePlanSize] =
    useState<EnterpriseScalePlanSize>('100B');
  const [enterprisePlan, setEnterprisePlan] =
    useState<EnterpriseScalePlan>(DEFAULT_ENTERPRISE_SCALE_PLAN);
  const [enterprisePlanError, setEnterprisePlanError] = useState<string | null>(null);
  const [isEnterprisePlanLoading, setIsEnterprisePlanLoading] = useState(false);

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

  const connectReferenceTarget = async () => {
    setSession(null);
    setSessionError(null);
    setTargetError(null);
    setIsTargetConnecting(true);
    try {
      const verification = await verifyCasHarnessModelTarget({
        target: { kind: 'demo_reference' },
      });
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

  const disconnectTarget = () => {
    setTarget(null);
    setSession(null);
    setSessionError(null);
    setTargetError(null);
    setIsTargetConnecting(false);
    setIsAuditRunning(false);
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
      });
      setSession(created);
      const started = await startCasHarnessAuditSession(created.audit_id);
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

  return (
    <>
      <style>{headingWaveCss}</style>
      <PageShell cardMaxWidth={1180}>
      <GlassPanel intensity="regular" padding={24} ariaLabel="CAS Harness Audit Console">
        <div style={topGridStyle}>
          <div>
            <p style={eyebrowStyle}>CAS Harness Audit Console</p>
            <AuditPopover
              briefing="Licensed users attach a model, run the audit, and receive ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW with confidence and proof chips."
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
            isAuditRunning={isAuditRunning}
            canRunAudit={Boolean(target?.canRunAudit)}
            onConnect={connectReferenceTarget}
            onDisconnect={disconnectTarget}
            onRunAudit={runAudit}
          />
        </div>

        <section style={commandCenterStyle} aria-label="CAS audit command center">
          <div style={commandHeaderStyle}>
            <div>
              <h2 style={commandTitleStyle}>Audit command center</h2>
              <AuditPopover
                briefing="The user path is simple: connect the target, run CAS, then return a verdict with proof chips and an Evidence Packet."
                placement="bottom"
                width={340}
              >
                <p style={commandSubtitleStyle}>Connect. Run. Decide.</p>
              </AuditPopover>
            </div>
            <button
              type="button"
              style={commandActionStyle(commandButtonEnabled)}
              onClick={runPrimaryCommand}
              disabled={!commandButtonEnabled}
            >
              {commandButtonLabel}
            </button>
          </div>
          <section style={flowStyle} aria-label="Audit workflow">
            {AUDIT_STEPS.map((step, index) => {
              const state = commandStateFor(
                index,
                isConfigured,
                session,
                isAuditRunning,
                sessionError,
              );
              return (
                <article key={step.label} style={stepStyle(state)}>
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
            {showVerdictExplainer ? (
              <AuditVerdictExplainer
                verdict={session?.verdict ?? null}
                confidence={session?.confidence ?? null}
                chips={sessionChips}
                verifierDecision={session?.verifier_decision ?? null}
                lifecycleMessage={latestLifecycleMessage(session)}
              />
            ) : null}
          </div>
        </div>
      </GlassPanel>
      </PageShell>
    </>
  );
}
