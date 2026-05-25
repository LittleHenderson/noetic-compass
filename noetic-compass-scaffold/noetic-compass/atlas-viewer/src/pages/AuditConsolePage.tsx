import { useMemo, useState, type CSSProperties } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import { AuditSessionProgress, type AuditLifecycleStatus } from '../components/audit/AuditSessionProgress';
import { AuditSessionSummaryCard } from '../components/audit/AuditSessionSummaryCard';
import { AuditVerdictCard } from '../components/audit/AuditVerdictCard';
import { ModelConnectionCard } from '../components/audit/ModelConnectionCard';
import { ProvenanceChips } from '../components/audit/ProvenanceChips';
import {
  buildDefaultProvenanceChips,
  type AuditVerdict,
  type ProvenanceChip,
} from '../lib/casHarnessAudit';
import {
  createCasHarnessAuditSession,
  startCasHarnessAuditSession,
  type CasHarnessAuditSession,
} from '../lib/casHarnessAuditApi';
import {
  ACCENT_AMBER,
  ACCENT_TEAL,
  COLORS,
  THEME,
} from '../lib/designTokens';

interface AuditStep {
  label: string;
  detail: string;
}

interface AuditTargetConfig {
  modelId: string;
  provider: string;
  endpointLabel: string;
  scenarioText: string;
}

const SELECTED_MODULES = [
  'model_proof',
  'cas_readout',
  'causal_proof',
  'control_proof',
  'output_proof',
  'packet_proof',
];

const M1_REFERENCE_TARGET: AuditTargetConfig = {
  modelId: 'EleutherAI/pythia-160m',
  provider: 'CAS Harness M1 reference path',
  endpointLabel: '/api/cas-harness/audit/session',
  scenarioText:
    'M1 audit smoke scenario: validate the CAS Harness audit contract without fabricating a verdict.',
};

const AUDIT_STEPS: AuditStep[] = [
  {
    label: 'Connect model',
    detail: 'Attach a supported model endpoint or validated reference worker.',
  },
  {
    label: 'Run CAS audit',
    detail: 'Execute the selected audit profile against the model output.',
  },
  {
    label: 'Get verdict',
    detail: 'Route each item to ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW.',
  },
  {
    label: 'Read evidence',
    detail: 'Show confidence and provenance chips next to the verdict.',
  },
  {
    label: 'Inspect in Atlas',
    detail: 'Open deep trace inspection only when trace evidence exists.',
  },
];

const VERDICT_COPY: Array<{ label: string; value: AuditVerdict; detail: string }> = [
  {
    label: 'ACCEPT',
    value: 'ACCEPT',
    detail: 'Allow the output to proceed under the active audit profile.',
  },
  {
    label: 'SUPPRESS',
    value: 'SUPPRESS',
    detail: 'Block, redact, or withhold the output.',
  },
  {
    label: 'FLAG FOR HUMAN REVIEW',
    value: 'FLAG_FOR_HUMAN_REVIEW',
    detail: 'Send the output to a person before trusting it.',
  },
];

const pendingChips = buildDefaultProvenanceChips({
  modelProof: {
    status: 'missing',
    detail: 'No model connection has been verified for this audit session yet.',
  },
  casReadout: {
    status: 'unavailable',
    detail: 'No CAS readout exists until the audit runner processes a model output.',
  },
  causalProof: {
    status: 'unavailable',
    detail: 'No ablation or intervention result exists for this audit session yet.',
  },
  controlProof: {
    status: 'unavailable',
    detail: 'No matched baseline/control result exists for this audit session yet.',
  },
  outputProof: {
    status: 'unavailable',
    detail: 'No output effect has been measured for this audit session yet.',
  },
  packetProof: {
    status: 'missing',
    detail: 'No Evidence Packet has been created for this audit session yet.',
  },
});

function chipsForSession(session: CasHarnessAuditSession | null): ProvenanceChip[] {
  if (!session) return pendingChips;

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
    return 'Prepare a supported audit target before creating a backend session.';
  }
  if (status === 'runner_pending') {
    return 'The backend created and ran the M1 lifecycle, then stopped honestly before verdict because the real audit runner is not wired yet.';
  }
  return null;
}

const headingStyle: CSSProperties = {
  margin: 0,
  fontSize: 34,
  lineHeight: 1.1,
  fontWeight: 750,
  letterSpacing: 0,
  color: COLORS.textPrimary,
};

const eyebrowStyle: CSSProperties = {
  margin: '0 0 10px 0',
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: 1.2,
  textTransform: 'uppercase',
  color: ACCENT_TEAL,
};

const subheadingStyle: CSSProperties = {
  margin: '12px 0 0 0',
  maxWidth: 760,
  fontSize: 15,
  lineHeight: 1.6,
  color: COLORS.textSecondary,
};

const framingStyle: CSSProperties = {
  marginTop: 18,
  padding: '12px 14px',
  borderRadius: 6,
  border: '1px solid rgba(45, 212, 191, 0.24)',
  background: 'rgba(45, 212, 191, 0.06)',
  color: COLORS.textPrimary,
  fontSize: 13,
  lineHeight: 1.55,
};

const topGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1.15fr) minmax(300px, 0.85fr)',
  gap: 18,
  alignItems: 'start',
};

const flowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
  gap: 8,
  marginTop: 18,
};

const stepStyle: CSSProperties = {
  minHeight: 116,
  padding: 12,
  borderRadius: 6,
  border: '1px solid rgba(255, 255, 255, 0.07)',
  background: 'rgba(255, 255, 255, 0.02)',
};

const stepNumberStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 22,
  height: 22,
  borderRadius: 4,
  border: '1px solid rgba(45, 212, 191, 0.28)',
  color: ACCENT_TEAL,
  fontSize: 11,
  fontWeight: 700,
  fontFamily: THEME.fontMono,
};

const stepLabelStyle: CSSProperties = {
  margin: '10px 0 6px 0',
  fontSize: 14,
  fontWeight: 700,
  color: COLORS.textPrimary,
};

const stepDetailStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  lineHeight: 1.45,
  color: COLORS.textSecondary,
};

const lowerGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 0.95fr) minmax(300px, 1.05fr)',
  gap: 16,
  marginTop: 16,
};

const sectionStyle: CSSProperties = {
  borderRadius: 8,
  border: '1px solid rgba(255, 255, 255, 0.07)',
  background: 'rgba(255, 255, 255, 0.02)',
  padding: 16,
};

const sectionHeadingStyle: CSSProperties = {
  margin: '0 0 12px 0',
  fontSize: 16,
  fontWeight: 750,
  color: COLORS.textPrimary,
};

const verdictListStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
};

const verdictRowStyle = (value: AuditVerdict): CSSProperties => ({
  padding: '10px 12px',
  borderRadius: 6,
  border:
    value === 'ACCEPT'
      ? '1px solid rgba(34, 197, 94, 0.35)'
      : value === 'SUPPRESS'
        ? '1px solid rgba(248, 113, 113, 0.35)'
        : '1px solid rgba(251, 191, 36, 0.35)',
  background:
    value === 'ACCEPT'
      ? 'rgba(34, 197, 94, 0.07)'
      : value === 'SUPPRESS'
        ? 'rgba(248, 113, 113, 0.07)'
        : 'rgba(251, 191, 36, 0.07)',
});

const verdictLabelStyle: CSSProperties = {
  display: 'block',
  marginBottom: 4,
  fontSize: 12,
  fontWeight: 800,
  letterSpacing: 0.4,
  fontFamily: THEME.fontMono,
  color: COLORS.textPrimary,
};

const verdictDetailStyle: CSSProperties = {
  margin: 0,
  fontSize: 12.5,
  lineHeight: 1.45,
  color: COLORS.textSecondary,
};

const noteStyle: CSSProperties = {
  margin: '12px 0 0 0',
  color: ACCENT_AMBER,
  fontSize: 12,
  lineHeight: 1.5,
};

const helperButtonStyle: CSSProperties = {
  minHeight: 34,
  marginTop: 12,
  padding: '7px 12px',
  borderRadius: 6,
  border: '1px solid rgba(45, 212, 191, 0.40)',
  background: 'rgba(45, 212, 191, 0.10)',
  color: '#ccfbf1',
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 13,
  fontWeight: 800,
};

export default function AuditConsolePage() {
  const navigate = useNavigate();
  const [target, setTarget] = useState<AuditTargetConfig | null>(null);
  const [session, setSession] = useState<CasHarnessAuditSession | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [isAuditRunning, setIsAuditRunning] = useState(false);

  const isConfigured = target !== null;
  const sessionChips = useMemo(() => chipsForSession(session), [session]);
  const lifecycleStatus = lifecycleStatusFor(session, isAuditRunning, sessionError);

  const connectReferenceTarget = () => {
    setTarget(M1_REFERENCE_TARGET);
    setSession(null);
    setSessionError(null);
  };

  const disconnectTarget = () => {
    setTarget(null);
    setSession(null);
    setSessionError(null);
    setIsAuditRunning(false);
  };

  const runAudit = async () => {
    if (!target) return;
    setSessionError(null);
    setIsAuditRunning(true);
    try {
      const created = await createCasHarnessAuditSession({
        model_id: target.modelId,
        audit_mode: 'BALANCED',
        scenario_text: target.scenarioText,
        selected_modules: SELECTED_MODULES,
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

  return (
    <PageShell cardMaxWidth={1180}>
      <GlassPanel intensity="regular" padding={24} ariaLabel="CAS Harness Audit Console">
        <div style={topGridStyle}>
          <div>
            <p style={eyebrowStyle}>CAS Harness Audit Console</p>
            <h1 style={headingStyle}>
              Connect a model. Run a CAS audit. Return a verdict with evidence.
            </h1>
            <p style={subheadingStyle}>
              This is the operator-facing product layer for licensed users:
              ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW, with confidence and
              provenance. Atlas remains the deep inspection cockpit when a case
              needs model-internal explanation.
            </p>
            <div style={framingStyle}>
              Current state: product shell plus M1 API session lifecycle. No
              final audit verdict is shown until a real audit runner computes it.
            </div>
          </div>

          <ModelConnectionCard
            status={isAuditRunning ? 'connecting' : isConfigured ? 'connected' : 'disconnected'}
            modelName={target?.modelId ?? 'No model connected'}
            provider={target?.provider ?? 'License/API connector pending'}
            endpointLabel={target?.endpointLabel ?? 'Configure in Model'}
            statusDetail={
              isConfigured
                ? 'M1 session target configured. This does not create a final verdict until the backend runner computes one.'
                : 'Connect or configure a supported audit target before running a CAS Harness audit.'
            }
            lastChecked={session ? 'Backend session accepted' : undefined}
            isAuditRunning={isAuditRunning}
            canRunAudit={isConfigured}
            onConnect={connectReferenceTarget}
            onDisconnect={disconnectTarget}
            onRunAudit={runAudit}
          />
        </div>

        <div style={lowerGridStyle}>
          <AuditSessionProgress
            status={lifecycleStatus}
            detail={progressDetail(lifecycleStatus, isConfigured)}
            errorMessage={sessionError}
          />
          <AuditSessionSummaryCard
            auditId={session?.audit_id}
            modelTarget={session?.model_id ?? target?.modelId}
            mode={session?.audit_mode ?? 'BALANCED'}
            selectedModulesCount={session?.selected_modules.length ?? (isConfigured ? SELECTED_MODULES.length : null)}
            status={lifecycleStatus}
            verdict={session?.verdict ?? null}
            confidence={session?.confidence ?? null}
            evidencePacketId={session?.evidence_packet_trace_id}
            updatedAt={session?.updated_at}
          />
        </div>

        {!isConfigured ? (
          <section style={sectionStyle} aria-labelledby="session-lifecycle-heading">
            <h2 id="session-lifecycle-heading" style={sectionHeadingStyle}>
              Session lifecycle
            </h2>
            <p style={verdictDetailStyle}>
              Run Audit stays disabled until a session target is configured.
              Use the M1 reference target to exercise the real session
              lifecycle without pretending a final audit verdict exists.
            </p>
            <button
              type="button"
              style={helperButtonStyle}
              onClick={connectReferenceTarget}
            >
              Prepare M1 reference session
            </button>
          </section>
        ) : null}

        <section style={flowStyle} aria-label="Audit workflow">
          {AUDIT_STEPS.map((step, index) => (
            <article key={step.label} style={stepStyle}>
              <span style={stepNumberStyle}>{index + 1}</span>
              <h2 style={stepLabelStyle}>{step.label}</h2>
              <p style={stepDetailStyle}>{step.detail}</p>
            </article>
          ))}
        </section>

        <div style={lowerGridStyle}>
          <AuditVerdictCard
            verdict={session?.verdict ?? null}
            confidence={session?.confidence ?? null}
            summary="No CAS audit verdict has been computed for this model yet. This prevents a demo confidence number from being mistaken for a real audit result."
            onInspectInAtlas={() => navigate('/cockpit')}
          />

          <section style={sectionStyle} aria-labelledby="provenance-heading">
            <h2 id="provenance-heading" style={sectionHeadingStyle}>
              Provenance required before a verdict
            </h2>
            <ProvenanceChips chips={sessionChips} />
            <p style={noteStyle}>
              A customer-safe ACCEPT requires model proof, CAS readout, causal
              proof, control proof, output proof, and packet proof. Missing
              evidence routes the item to review or keeps it pending.
            </p>
          </section>
        </div>

        <div style={lowerGridStyle}>
          <section style={sectionStyle} aria-labelledby="verdict-vocabulary">
            <h2 id="verdict-vocabulary" style={sectionHeadingStyle}>
              Verdict vocabulary
            </h2>
            <div style={verdictListStyle}>
              {VERDICT_COPY.map((item) => (
                <div key={item.value} style={verdictRowStyle(item.value)}>
                  <span style={verdictLabelStyle}>{item.label}</span>
                  <p style={verdictDetailStyle}>{item.detail}</p>
                </div>
              ))}
            </div>
          </section>

          <section style={sectionStyle} aria-labelledby="atlas-boundary">
            <h2 id="atlas-boundary" style={sectionHeadingStyle}>
              Atlas boundary
            </h2>
            <p style={verdictDetailStyle}>
              Audit Console is the decision workflow. Atlas is the evidence
              microscope. A user should not need Atlas to understand the
              verdict, but Atlas should be one click away when the evidence
              needs inspection.
            </p>
            <p style={noteStyle}>
              <Link to="/cockpit" style={{ color: ACCENT_TEAL }}>
                Open Atlas cockpit
              </Link>
            </p>
          </section>
        </div>
      </GlassPanel>
    </PageShell>
  );
}
