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
import type { CasHarnessDistributedAudit } from '../../lib/casHarnessAuditApi';

export interface DistributedAuditRunPanelProps {
  audit: CasHarnessDistributedAudit | null;
  isLoading?: boolean;
  error?: string | null;
  onCreateRun: () => void;
  onDispatchRun: () => void;
  onMergeRun: () => void;
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
  alignItems: 'flex-start',
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: ACCENT_TEAL,
  fontSize: 11,
  fontWeight: 800,
  textTransform: 'uppercase',
};

const titleStyle: CSSProperties = {
  margin: '3px 0 0',
  color: '#f8fafc',
  fontSize: 20,
  lineHeight: 1.2,
  fontWeight: 850,
};

const bodyStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.5,
};

const buttonRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
};

const buttonStyle = (enabled: boolean): CSSProperties => ({
  minHeight: 34,
  padding: '7px 10px',
  borderRadius: RADIUS.sm,
  border: enabled
    ? '1px solid rgba(45, 212, 191, 0.52)'
    : '1px solid rgba(148, 163, 184, 0.22)',
  background: enabled ? 'rgba(45, 212, 191, 0.14)' : 'rgba(148, 163, 184, 0.06)',
  color: enabled ? '#ccfbf1' : COLORS.textMuted,
  cursor: enabled ? 'pointer' : 'not-allowed',
  fontFamily: FONT_MONO,
  fontSize: 12,
  fontWeight: 850,
});

const metricsStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
  gap: 8,
};

const metricStyle: CSSProperties = {
  display: 'grid',
  gap: 4,
  padding: '9px 10px',
  borderRadius: RADIUS.md,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: GLASS_PANEL_FILL,
};

const metricLabelStyle: CSSProperties = {
  color: COLORS.textMuted,
  fontSize: 11,
  fontWeight: 750,
  textTransform: 'uppercase',
};

const metricValueStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontSize: 13,
  fontWeight: 800,
};

const workerGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: 8,
  maxHeight: 220,
  overflow: 'auto',
};

const workerStyle: CSSProperties = {
  display: 'grid',
  gap: 5,
  padding: 9,
  borderRadius: RADIUS.md,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(15, 23, 42, 0.48)',
  minWidth: 0,
};

const noticeStyle = (tone: 'info' | 'warning' | 'error'): CSSProperties => ({
  margin: 0,
  padding: '8px 10px',
  borderRadius: RADIUS.md,
  border:
    tone === 'error'
      ? '1px solid rgba(248, 113, 113, 0.36)'
      : tone === 'warning'
        ? '1px solid rgba(251, 191, 36, 0.36)'
        : '1px solid rgba(45, 212, 191, 0.22)',
  color:
    tone === 'error'
      ? '#fecaca'
      : tone === 'warning'
        ? '#fef3c7'
        : COLORS.textSecondary,
  background:
    tone === 'error'
      ? 'rgba(248, 113, 113, 0.08)'
      : tone === 'warning'
        ? 'rgba(251, 191, 36, 0.08)'
        : 'rgba(45, 212, 191, 0.07)',
  fontSize: 12,
  lineHeight: 1.45,
});

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={metricStyle}>
      <span style={metricLabelStyle}>{label}</span>
      <span style={metricValueStyle}>{value}</span>
    </div>
  );
}

export function DistributedAuditRunPanel({
  audit,
  isLoading = false,
  error = null,
  onCreateRun,
  onDispatchRun,
  onMergeRun,
}: DistributedAuditRunPanelProps) {
  const canDispatch = Boolean(audit && audit.status === 'PLANNED' && !isLoading);
  const canMerge = Boolean(audit && audit.status !== 'PLANNED' && !isLoading);

  return (
    <GlassPanel
      as="section"
      intensity="regular"
      padding={16}
      ariaLabel="Distributed CAS Harness audit run"
      data-testid="distributed-audit-run-panel"
      style={panelStyle}
    >
      <header style={headerStyle}>
        <div>
          <p style={eyebrowStyle}>Distributed audit runner</p>
          <h2 style={titleStyle}>Worker evidence, not planner theater</h2>
        </div>
        <div style={buttonRowStyle}>
          <button type="button" style={buttonStyle(!isLoading)} onClick={onCreateRun} disabled={isLoading}>
            Create run
          </button>
          <button type="button" style={buttonStyle(canDispatch)} onClick={onDispatchRun} disabled={!canDispatch}>
            Dispatch workers
          </button>
          <button type="button" style={buttonStyle(canMerge)} onClick={onMergeRun} disabled={!canMerge}>
            Merge evidence
          </button>
        </div>
      </header>

      <p style={bodyStyle}>
        A 20B/100B/300B audit is real only when assigned Probe Workers return
        evidence receipts. Missing, failed, or partial worker evidence cannot
        become ACCEPT.
      </p>

      {isLoading ? <p style={noticeStyle('info')}>Distributed audit request in flight...</p> : null}
      {error ? <p role="status" style={noticeStyle('error')}>{error}</p> : null}

      {audit ? (
        <>
          <div style={metricsStyle}>
            <Metric label="Run" value={audit.audit_id} />
            <Metric label="Status" value={audit.status} />
            <Metric label="Merge" value={audit.merge_status} />
            <Metric label="Workers" value={`${audit.ready_workers}/${audit.total_workers} ready`} />
            <Metric label="Verdict" value={audit.verdict ?? 'No verdict'} />
            <Metric label="Packet" value={audit.evidence_packet_trace_id ?? 'Not created'} />
          </div>
          <p style={noticeStyle(audit.merge_status === 'complete' ? 'info' : 'warning')}>
            {audit.merge_reason}
          </p>
          <div style={workerGridStyle} aria-label="Probe Worker evidence receipts">
            {audit.worker_evidence.map((worker) => (
              <article key={worker.worker_id} style={workerStyle}>
                <span style={{ ...metricValueStyle, fontFamily: FONT_MONO }}>{worker.worker_id}</span>
                <span style={bodyStyle}>Layers {worker.layer_start}-{worker.layer_end}</span>
                <span style={bodyStyle}>{worker.shard_id}</span>
                <span style={metricLabelStyle}>{worker.worker_status}</span>
              </article>
            ))}
          </div>
        </>
      ) : (
        <p style={noticeStyle('warning')}>
          No distributed run created yet. The scale card above is a plan; this
          panel creates the run object that waits for real worker evidence.
        </p>
      )}
    </GlassPanel>
  );
}

export default DistributedAuditRunPanel;
