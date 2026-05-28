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

export type FleetVerifierGateStatus =
  | 'not_prepared'
  | 'waiting_for_workers'
  | 'waiting_for_receipts'
  | 'blocked_failed_worker'
  | 'blocked_missing_outputs'
  | 'ready_for_verifier';
export type FleetReadinessStatus = 'blocked' | 'waiting' | 'ready';

export interface FleetReadinessSummary {
  status: FleetReadinessStatus;
  headline: string;
  blockers: string[];
  next_actions: string[];
  verifier_owned: boolean;
}

export interface FleetExecutorPanelProps {
  registeredWorkers: number;
  leasedJobs: number;
  staleWorkers: number;
  completedFragments: number;
  totalJobs: number;
  mergedPacketStatus: 'not_created' | 'partial' | 'ready';
  verifierGateStatus: FleetVerifierGateStatus;
  readiness?: FleetReadinessSummary | null;
}

const panelStyle: CSSProperties = {
  display: 'grid',
  gap: 12,
  fontFamily: FONT_FAMILY,
  color: COLORS.textPrimary,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  justifyContent: 'space-between',
  gap: 12,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: ACCENT_TEAL,
  fontSize: 11,
  fontWeight: 850,
  textTransform: 'uppercase',
};

const titleStyle: CSSProperties = {
  margin: '4px 0 0',
  fontSize: 20,
  lineHeight: 1.15,
  fontWeight: 850,
  color: '#f8fafc',
};

const bodyStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.45,
};

const gridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))',
  gap: 8,
};

const metricStyle: CSSProperties = {
  display: 'grid',
  gap: 4,
  minHeight: 58,
  padding: '10px 11px',
  borderRadius: RADIUS.md,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: GLASS_PANEL_FILL,
};

const labelStyle: CSSProperties = {
  color: COLORS.textMuted,
  fontSize: 11,
  fontWeight: 800,
  textTransform: 'uppercase',
};

const valueStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontFamily: FONT_MONO,
  fontSize: 13,
  fontWeight: 850,
};

const noticeStyle = (tone: 'info' | 'warning' | 'error'): CSSProperties => ({
  margin: 0,
  padding: '9px 11px',
  borderRadius: RADIUS.md,
  border:
    tone === 'error'
      ? '1px solid rgba(248, 113, 113, 0.36)'
      : tone === 'warning'
        ? '1px solid rgba(251, 191, 36, 0.36)'
        : '1px solid rgba(45, 212, 191, 0.24)',
  background:
    tone === 'error'
      ? 'rgba(248, 113, 113, 0.08)'
      : tone === 'warning'
        ? 'rgba(251, 191, 36, 0.08)'
        : 'rgba(45, 212, 191, 0.07)',
  color:
    tone === 'error'
      ? '#fecaca'
      : tone === 'warning'
        ? '#fef3c7'
        : COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
});

const readinessPanelStyle = (status: FleetReadinessStatus): CSSProperties => ({
  display: 'grid',
  gap: 8,
  padding: '10px 11px',
  borderRadius: RADIUS.md,
  border:
    status === 'ready'
      ? '1px solid rgba(34, 197, 94, 0.34)'
      : status === 'blocked'
        ? '1px solid rgba(248, 113, 113, 0.34)'
        : '1px solid rgba(251, 191, 36, 0.34)',
  background:
    status === 'ready'
      ? 'rgba(34, 197, 94, 0.08)'
      : status === 'blocked'
        ? 'rgba(248, 113, 113, 0.08)'
        : 'rgba(251, 191, 36, 0.08)',
});

const readinessTitleStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 13,
  fontWeight: 900,
};

const readinessListStyle: CSSProperties = {
  margin: 0,
  paddingLeft: 18,
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
};

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={metricStyle}>
      <span style={labelStyle}>{label}</span>
      <span style={valueStyle}>{value}</span>
    </div>
  );
}

function gateCopy(status: FleetVerifierGateStatus): { tone: 'info' | 'warning' | 'error'; text: string } {
  switch (status) {
    case 'not_prepared':
      return { tone: 'warning', text: 'Fleet jobs have not been prepared from the distributed audit run.' };
    case 'waiting_for_workers':
      return { tone: 'warning', text: 'Waiting for registered, fresh-heartbeat workers for every assigned job.' };
    case 'waiting_for_receipts':
      return { tone: 'warning', text: 'Workers are present, but Evidence Packet fragment receipts are still missing.' };
    case 'blocked_failed_worker':
      return { tone: 'error', text: 'A worker failed. The run cannot become ACCEPT without rerun or human review.' };
    case 'blocked_missing_outputs':
      return { tone: 'error', text: 'A receipt is missing required outputs. The run cannot become ACCEPT.' };
    case 'ready_for_verifier':
      return { tone: 'info', text: 'All fragment receipts are present. Merge can assemble the distributed Evidence Packet for verifier review.' };
  }
}

function fallbackReadiness(
  verifierGateStatus: FleetVerifierGateStatus,
  complete: boolean,
): FleetReadinessSummary {
  const gate = gateCopy(verifierGateStatus);
  return {
    status: complete ? 'ready' : gate.tone === 'error' ? 'blocked' : 'waiting',
    headline: complete
      ? 'Large-model worker receipts are complete; verifier review is unblocked.'
      : gate.text,
    blockers: complete ? [] : [gate.text],
    next_actions: complete
      ? ['Merge fleet evidence, then run the verifier decision layer.']
      : ['Register workers, lease jobs, and submit Evidence Packet fragment receipts.'],
    verifier_owned: true,
  };
}

export function FleetExecutorPanel({
  registeredWorkers,
  leasedJobs,
  staleWorkers,
  completedFragments,
  totalJobs,
  mergedPacketStatus,
  verifierGateStatus,
  readiness,
}: FleetExecutorPanelProps) {
  const gate = gateCopy(verifierGateStatus);
  const complete = totalJobs > 0 && completedFragments === totalJobs && staleWorkers === 0;
  const readinessSummary = readiness ?? fallbackReadiness(verifierGateStatus, complete);

  return (
    <GlassPanel
      as="section"
      intensity="regular"
      padding={16}
      ariaLabel="CAS Harness fleet executor"
      data-testid="fleet-executor-panel"
      style={panelStyle}
    >
      <header style={headerStyle}>
        <div>
          <p style={eyebrowStyle}>Fleet executor</p>
          <h2 style={titleStyle}>Registry, leases, receipts, verifier gate</h2>
        </div>
      </header>

      <p style={bodyStyle}>
        A 100B/300B run cannot move forward from a scale plan alone. Workers
        must register, lease their assigned jobs, heartbeat while running, and
        return Evidence Packet fragments before the verifier can decide.
      </p>

      <div style={gridStyle}>
        <Metric label="Covered jobs" value={`${registeredWorkers}/${totalJobs}`} />
        <Metric label="Leases" value={`${leasedJobs}/${totalJobs}`} />
        <Metric label="Fragments" value={`${completedFragments}/${totalJobs}`} />
        <Metric label="Stale workers" value={`${staleWorkers}`} />
        <Metric label="Merged packet" value={mergedPacketStatus.replace('_', ' ')} />
        <Metric label="Verifier gate" value={verifierGateStatus.replaceAll('_', ' ')} />
      </div>

      <p data-testid="fleet-executor-gate" style={noticeStyle(gate.tone)}>
        {gate.text}
      </p>

      <section
        data-testid="fleet-readiness-summary"
        style={readinessPanelStyle(readinessSummary.status)}
        aria-label="Large-model eval readiness"
      >
        <h3 style={readinessTitleStyle}>Large-model eval readiness</h3>
        <p style={bodyStyle}>{readinessSummary.headline}</p>
        {readinessSummary.blockers.length > 0 ? (
          <ul data-testid="fleet-readiness-blockers" style={readinessListStyle}>
            {readinessSummary.blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        ) : null}
        <ul data-testid="fleet-readiness-actions" style={readinessListStyle}>
          {readinessSummary.next_actions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
        {readinessSummary.verifier_owned ? (
          <p style={bodyStyle}>Verifier-owned: fleet receipts can unblock review, but they cannot emit ACCEPT by themselves.</p>
        ) : null}
      </section>

      {!complete ? (
        <p data-testid="fleet-executor-block" style={noticeStyle('warning')}>
          Blocked: assigned workers and returned receipts are required before
          this can support a final CAS Harness verdict.
        </p>
      ) : null}
    </GlassPanel>
  );
}

export default FleetExecutorPanel;
