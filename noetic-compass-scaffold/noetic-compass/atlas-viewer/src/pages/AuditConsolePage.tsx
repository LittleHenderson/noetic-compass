import { useMemo, useState, type CSSProperties } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import { AuditSessionProgress, type AuditLifecycleStatus } from '../components/audit/AuditSessionProgress';
import { AuditSessionSummaryCard } from '../components/audit/AuditSessionSummaryCard';
import { AuditVerdictCard } from '../components/audit/AuditVerdictCard';
import { AuditVerdictExplainer } from '../components/audit/AuditVerdictExplainer';
import { AuditTerm } from '../components/audit/AuditTerm';
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
  ACCENT_CYAN,
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
  provider: 'CAS Harness reference path',
  endpointLabel: '/api/cas-harness/audit/session',
  scenarioText:
    'Reference audit smoke scenario: validate the CAS Harness audit contract without fabricating a verdict.',
};

const AUDIT_STEPS: AuditStep[] = [
  {
    label: 'Connect model',
    detail: 'Verify the model target, API route, and license gate.',
  },
  {
    label: 'Run CAS audit',
    detail: 'Run readout, causal, control, output, and packet checks.',
  },
  {
    label: 'Return verdict + evidence',
    detail: 'Return ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW with confidence and proof chips.',
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

const subheadingStyle: CSSProperties = {
  margin: '12px 0 0 0',
  maxWidth: 760,
  fontSize: 15,
  lineHeight: 1.6,
  color: COLORS.textSecondary,
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

const readinessStripStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(155px, 1fr))',
  gap: 8,
  marginTop: 16,
};

const readinessTileStyle: CSSProperties = {
  minHeight: 86,
  padding: '10px 12px',
  borderRadius: 6,
  border: '1px solid rgba(45, 212, 191, 0.18)',
  background: 'rgba(45, 212, 191, 0.045)',
};

const readinessLabelStyle: CSSProperties = {
  display: 'block',
  marginBottom: 5,
  color: COLORS.textMuted,
  fontSize: 10.5,
  fontWeight: 800,
  letterSpacing: 0.5,
  textTransform: 'uppercase',
};

const readinessValueStyle: CSSProperties = {
  display: 'block',
  color: COLORS.textPrimary,
  fontSize: 13,
  fontWeight: 850,
  overflowWrap: 'anywhere',
};

const readinessDetailStyle: CSSProperties = {
  display: 'block',
  marginTop: 5,
  color: COLORS.textSecondary,
  fontSize: 11.5,
  lineHeight: 1.35,
};

const flowStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
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

const verdictStackStyle: CSSProperties = {
  display: 'grid',
  gap: 16,
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

const termRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
  marginTop: 12,
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
  const readinessItems = [
    {
      label: 'Model',
      value: target?.modelId ?? 'Not connected',
      detail: target ? 'Target selected' : 'Choose a model endpoint',
    },
    {
      label: 'Runtime',
      value: target ? 'Reference backend' : 'Pending',
      detail: target ? 'No verdict without backend proof' : 'Worker not selected',
    },
    {
      label: 'License/API',
      value: target ? 'Alpha API route' : 'Pending',
      detail: target ? 'Session route ready' : 'License gate required',
    },
    {
      label: 'Audit mode',
      value: 'BALANCED',
      detail: 'Precision and coverage tradeoff',
    },
  ];

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
    <>
      <style>{headingWaveCss}</style>
      <PageShell cardMaxWidth={1180}>
      <GlassPanel intensity="regular" padding={24} ariaLabel="CAS Harness Audit Console">
        <div style={topGridStyle}>
          <div>
            <p style={eyebrowStyle}>CAS Harness Audit Console</p>
            <h1 className="cas-heading-wave" style={headingWaveStyle}>
              Connect a model. Run a CAS audit. Return a verdict with evidence.
            </h1>
            <p style={monikerStyle}>TURN YOUR BLACK BOX INTO A GLASS HOUSE</p>
            <p style={subheadingStyle}>
              Licensed users attach a model, run the audit, and receive a
              decision: ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW. The verdict
              carries confidence and proof chips; Atlas opens only when deeper
              inspection is needed.
            </p>
            <div style={framingStyle}>
              Current gate: the UI shows ACCEPT or SUPPRESS only when the
              backend returns an explicit verifier decision from an{' '}
              <AuditTerm term="evidencePacket">Evidence Packet</AuditTerm>.
            </div>
            <div style={readinessStripStyle} aria-label="Audit readiness">
              {readinessItems.map((item) => (
                <div key={item.label} style={readinessTileStyle}>
                  <span style={readinessLabelStyle}>{item.label}</span>
                  <span style={readinessValueStyle}>{item.value}</span>
                  <span style={readinessDetailStyle}>{item.detail}</span>
                </div>
              ))}
            </div>
          </div>

          <ModelConnectionCard
            status={isAuditRunning ? 'connecting' : isConfigured ? 'connected' : 'disconnected'}
            modelName={target?.modelId ?? 'No model connected'}
            provider={target?.provider ?? 'License/API connector pending'}
            endpointLabel={target?.endpointLabel ?? 'Configure in Model'}
            statusDetail={
              isConfigured
                ? 'Target ready. Final verdict requires an Evidence Packet and verifier decision.'
                : 'Connect a supported target before running a CAS Harness audit.'
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
              Run Audit stays disabled until a model target is configured.
              The reference path tests the session lifecycle without inventing a verdict.
            </p>
            <button
              type="button"
              style={helperButtonStyle}
              onClick={connectReferenceTarget}
            >
              Prepare reference session
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
          <div style={verdictStackStyle}>
            <AuditVerdictCard
              verdict={session?.verdict ?? null}
              confidence={session?.confidence ?? null}
              summary={verdictSummaryFor(session)}
              onInspectInAtlas={() => navigate('/cockpit')}
            />
            <AuditVerdictExplainer
              verdict={session?.verdict ?? null}
              confidence={session?.confidence ?? null}
              chips={sessionChips}
              verifierDecision={session?.verifier_decision ?? null}
              lifecycleMessage={latestLifecycleMessage(session)}
            />
          </div>

          <section style={sectionStyle} aria-labelledby="provenance-heading">
            <h2 id="provenance-heading" style={sectionHeadingStyle}>
              Proof chips
            </h2>
            <ProvenanceChips chips={sessionChips} />
            <p style={noteStyle}>
              ACCEPT requires model proof, CAS readout,{' '}
              <AuditTerm term="ablation">causal proof</AuditTerm>,{' '}
              <AuditTerm term="matchedControl">control proof</AuditTerm>, output
              proof, and packet proof. Missing evidence routes to review or keeps
              the case pending.
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
              verdict, but Atlas stays one click away for token traces,
              <AuditTerm term="blindspot">blindspots</AuditTerm>, and{' '}
              <AuditTerm term="inversion">inversion</AuditTerm> evidence.
            </p>
            <p style={noteStyle}>
              <Link to="/cockpit" style={{ color: ACCENT_TEAL }}>
                Open Atlas cockpit
              </Link>
            </p>
          </section>
        </div>

        <section
          style={{ ...sectionStyle, marginTop: 16 }}
          aria-labelledby="audit-term-help"
        >
          <h2 id="audit-term-help" style={sectionHeadingStyle}>
            Hover help
          </h2>
          <p style={verdictDetailStyle}>
            Keep the screen clean; hover these terms when a reviewer asks what
            a proof word means.
          </p>
          <div style={termRowStyle} aria-label="Audit term help">
            <AuditTerm term="baseline">baseline</AuditTerm>
            <AuditTerm term="ablation">ablation</AuditTerm>
            <AuditTerm term="matchedControl">matched control</AuditTerm>
            <AuditTerm term="evidencePacket">Evidence Packet</AuditTerm>
            <AuditTerm term="confidence">confidence</AuditTerm>
            <AuditTerm term="coverage">coverage</AuditTerm>
            <AuditTerm term="inversion">inversion</AuditTerm>
            <AuditTerm term="blindspot">blindspot</AuditTerm>
          </div>
        </section>
      </GlassPanel>
      </PageShell>
    </>
  );
}
