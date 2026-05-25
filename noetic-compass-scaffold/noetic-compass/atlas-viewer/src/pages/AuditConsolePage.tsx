import type { CSSProperties } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import { AuditVerdictCard } from '../components/audit/AuditVerdictCard';
import { ModelConnectionCard } from '../components/audit/ModelConnectionCard';
import { ProvenanceChips } from '../components/audit/ProvenanceChips';
import {
  buildDefaultProvenanceChips,
  type AuditVerdict,
} from '../lib/casHarnessAudit';
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

export default function AuditConsolePage() {
  const navigate = useNavigate();

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
              Current state: product shell plus API contract. No final audit
              verdict is shown until a real audit runner computes it.
            </div>
          </div>

          <ModelConnectionCard
            status="disconnected"
            modelName="No model connected"
            provider="License/API connector pending"
            endpointLabel="Configure in Model"
            statusDetail="Connect a supported model before running a real CAS Harness audit."
            canRunAudit={false}
            onConnect={() => navigate('/model-config')}
          />
        </div>

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
            verdict={null}
            confidence={null}
            summary="No CAS audit verdict has been computed for this model yet. This prevents a demo confidence number from being mistaken for a real audit result."
            onInspectInAtlas={() => navigate('/cockpit')}
          />

          <section style={sectionStyle} aria-labelledby="provenance-heading">
            <h2 id="provenance-heading" style={sectionHeadingStyle}>
              Provenance required before a verdict
            </h2>
            <ProvenanceChips chips={pendingChips} />
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
