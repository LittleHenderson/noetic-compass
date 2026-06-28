import type { CSSProperties } from 'react';
import { GlassPanel } from '../ui/GlassPanel';
import {
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
  GLASS_PANEL_FILL,
  RADIUS,
} from '../../lib/designTokens';
import {
  DEFAULT_ENTERPRISE_SCALE_PLAN,
  ENTERPRISE_SCALE_RATIONALE_COPY,
  type EnterpriseProbeWorkerAssignment,
  type EnterpriseScalePlan,
} from '../../lib/enterpriseScalePlan';

export interface EnterpriseScalePlanCardProps {
  plan?: EnterpriseScalePlan;
  className?: string;
}

const panelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
  fontFamily: FONT_FAMILY,
  color: COLORS.textPrimary,
  minWidth: 0,
  maxWidth: 820,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: ACCENT_TEAL,
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: 0,
  textTransform: 'uppercase',
};

const titleStyle: CSSProperties = {
  margin: '3px 0 0 0',
  color: '#f8fafc',
  fontSize: 22,
  lineHeight: 1.15,
  fontWeight: 750,
  letterSpacing: 0,
};

const bodyTextStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.55,
};

const summaryGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
  gap: 8,
};

const metricStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 3,
  minWidth: 0,
  padding: '10px 11px',
  borderRadius: RADIUS.md,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: GLASS_PANEL_FILL,
};

const metricLabelStyle: CSSProperties = {
  color: COLORS.textMuted,
  fontSize: 11,
  fontWeight: 650,
  letterSpacing: 0,
  textTransform: 'uppercase',
};

const metricValueStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontSize: 13,
  lineHeight: 1.35,
  fontWeight: 700,
};

const sectionTitleStyle: CSSProperties = {
  margin: 0,
  color: '#f8fafc',
  fontSize: 13,
  fontWeight: 750,
  letterSpacing: 0,
};

const sectionStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
};

const assignmentGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 8,
};

const assignmentCardStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 7,
  padding: 10,
  borderRadius: RADIUS.md,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(15, 23, 42, 0.44)',
  minWidth: 0,
};

const workerHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 8,
};

const monoLabelStyle: CSSProperties = {
  color: '#ccfbf1',
  fontFamily: FONT_MONO,
  fontSize: 12,
  fontWeight: 700,
  lineHeight: 1.3,
};

const workerCountStyle: CSSProperties = {
  flex: '0 0 auto',
  padding: '2px 6px',
  borderRadius: RADIUS.sm,
  color: COLORS.textSecondary,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(255, 255, 255, 0.03)',
  fontSize: 11,
  fontWeight: 650,
};

const rangeRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
};

const rangePillStyle: CSSProperties = {
  padding: '3px 7px',
  borderRadius: RADIUS.sm,
  color: COLORS.textPrimary,
  background: 'rgba(45, 212, 191, 0.1)',
  border: '1px solid rgba(45, 212, 191, 0.18)',
  fontSize: 12,
  fontWeight: 650,
};

const listStyle: CSSProperties = {
  margin: 0,
  paddingLeft: 18,
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.55,
};

function Metric({
  label,
  value,
  testId,
}: {
  label: string;
  value: string;
  testId?: string;
}) {
  return (
    <div style={metricStyle}>
      <span style={metricLabelStyle}>{label}</span>
      <span data-testid={testId} style={metricValueStyle}>
        {value}
      </span>
    </div>
  );
}

function workerTestId(assignment: EnterpriseProbeWorkerAssignment): string {
  return assignment.workerLabel.replace(/[^A-Za-z0-9-]/g, '-');
}

function WorkerAssignment({ assignment }: { assignment: EnterpriseProbeWorkerAssignment }) {
  const workerLabel =
    assignment.workerCount === 1
      ? '1 worker'
      : `${assignment.workerCount} workers`;

  return (
    <article
      data-testid={`enterprise-worker-assignment-${workerTestId(assignment)}`}
      style={assignmentCardStyle}
    >
      <div style={workerHeaderStyle}>
        <span style={monoLabelStyle}>{assignment.workerLabel}</span>
        <span style={workerCountStyle}>{workerLabel}</span>
      </div>
      <div style={rangeRowStyle}>
        <span style={rangePillStyle}>Layers {assignment.layerRange}</span>
        <span style={rangePillStyle}>Shards {assignment.shardRange}</span>
      </div>
      <p style={bodyTextStyle}>{assignment.focus}</p>
    </article>
  );
}

export function EnterpriseScalePlanCard({
  plan = DEFAULT_ENTERPRISE_SCALE_PLAN,
  className,
}: EnterpriseScalePlanCardProps) {
  return (
    <GlassPanel
      as="section"
      intensity="regular"
      padding={16}
      className={className}
      ariaLabel={`${plan.size} enterprise open-weight audit plan`}
      data-testid="enterprise-scale-plan-card"
      style={panelStyle}
    >
      <header>
        <p style={eyebrowStyle}>Enterprise open-weight audit plan</p>
        <h2 style={titleStyle}>{plan.title}</h2>
      </header>

      <p style={bodyTextStyle}>{ENTERPRISE_SCALE_RATIONALE_COPY}</p>
      <p style={bodyTextStyle}>{plan.orchestratorRole}</p>

      <div style={summaryGridStyle} aria-label="Enterprise plan summary">
        <Metric label="Parameter Band" value={plan.parameterBand} />
        <Metric
          label="Probe Workers"
          value={`${plan.workerCount} Probe Workers`}
          testId="enterprise-plan-worker-count"
        />
        <Metric label="Layer Range" value={plan.layerSpan} />
        <Metric label="Shard Range" value={plan.shardSpan} />
      </div>

      <section style={sectionStyle} aria-labelledby="enterprise-proof-coverage">
        <h3 id="enterprise-proof-coverage" style={sectionTitleStyle}>
          Expected Proof Coverage
        </h3>
        <p style={bodyTextStyle}>{plan.expectedProofCoverage}</p>
        <ul style={listStyle}>
          {plan.coverageSignals.map((signal) => (
            <li key={signal}>{signal}</li>
          ))}
        </ul>
      </section>

      <section style={sectionStyle} aria-labelledby="enterprise-worker-assignments">
        <h3 id="enterprise-worker-assignments" style={sectionTitleStyle}>
          Worker Assignments
        </h3>
        <div style={assignmentGridStyle}>
          {plan.workerAssignments.map((assignment) => (
            <WorkerAssignment
              key={assignment.workerLabel}
              assignment={assignment}
            />
          ))}
        </div>
      </section>

      <section style={sectionStyle} aria-labelledby="enterprise-limitations">
        <h3 id="enterprise-limitations" style={sectionTitleStyle}>
          Honest Limitations
        </h3>
        <ul style={listStyle}>
          {plan.honestLimitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </section>
    </GlassPanel>
  );
}

export default EnterpriseScalePlanCard;
