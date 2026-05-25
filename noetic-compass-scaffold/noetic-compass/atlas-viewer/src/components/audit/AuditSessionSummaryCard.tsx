import type { CSSProperties } from 'react';
import { GlassPanel } from '../ui/GlassPanel';
import { COLORS, FONT_FAMILY, FONT_MONO } from '../../lib/designTokens';
import type { AuditVerdict } from '../../lib/casHarnessAudit';
import type { AuditLifecycleStatus } from './AuditSessionProgress';

export interface AuditSessionSummaryCardProps {
  auditId?: string | null;
  modelTarget?: string | null;
  mode?: string | null;
  selectedModulesCount?: number | null;
  status?: AuditLifecycleStatus;
  verdict?: AuditVerdict | null;
  confidence?: number | null;
  evidencePacketId?: string | null;
  updatedAt?: string | null;
  className?: string;
}

const verdictLabels: Record<AuditVerdict, string> = {
  ACCEPT: 'ACCEPT',
  SUPPRESS: 'SUPPRESS',
  FLAG_FOR_HUMAN_REVIEW: 'FLAG FOR HUMAN REVIEW',
};

const statusLabels: Record<AuditLifecycleStatus, string> = {
  draft: 'Draft',
  validating: 'Validating',
  running: 'Running',
  runner_pending: 'Runner pending',
  evidence_pending: 'Evidence pending',
  complete: 'Complete',
  failed: 'Failed',
};

const shellStyle: CSSProperties = {
  display: 'grid',
  gap: 16,
  fontFamily: FONT_FAMILY,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12,
  fontWeight: 800,
  letterSpacing: 0,
  textTransform: 'uppercase',
};

const titleStyle: CSSProperties = {
  margin: '5px 0 0',
  color: COLORS.textPrimary,
  fontSize: 18,
  lineHeight: 1.25,
  fontWeight: 850,
  letterSpacing: 0,
};

const statusPillStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  minHeight: 30,
  padding: '5px 10px',
  borderRadius: 6,
  border: `1px solid ${COLORS.borderStrong}`,
  background: 'rgba(255, 255, 255, 0.04)',
  color: COLORS.textSecondary,
  fontSize: 12,
  fontWeight: 800,
  whiteSpace: 'nowrap',
};

const gridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))',
  gap: 10,
};

const tileStyle: CSSProperties = {
  padding: '11px 12px',
  borderRadius: 8,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(2, 6, 23, 0.34)',
};

const labelStyle: CSSProperties = {
  display: 'block',
  color: COLORS.textMuted,
  fontSize: 11,
  fontWeight: 750,
  letterSpacing: 0,
  textTransform: 'uppercase',
};

const valueStyle: CSSProperties = {
  display: 'block',
  marginTop: 6,
  color: COLORS.textPrimary,
  fontSize: 13,
  fontWeight: 750,
  overflowWrap: 'anywhere',
};

const verdictStyle = (verdict?: AuditVerdict | null): CSSProperties => ({
  ...valueStyle,
  color:
    verdict === 'ACCEPT'
      ? '#ccfbf1'
      : verdict === 'SUPPRESS'
        ? '#ffe4e6'
        : verdict === 'FLAG_FOR_HUMAN_REVIEW'
          ? '#fef3c7'
          : COLORS.textSecondary,
});

function moduleCountLabel(count?: number | null): string {
  if (count == null) return 'Not selected';
  if (!Number.isFinite(count) || count < 0) return 'Not selected';
  const rounded = Math.trunc(count);
  return rounded === 1 ? '1 module selected' : `${rounded} modules selected`;
}

function confidenceLabel(confidence?: number | null): string {
  if (confidence == null) return 'Not computed';
  if (!Number.isFinite(confidence) || confidence < 0) return 'Not computed';
  const normalized = confidence <= 1 ? confidence * 100 : confidence;
  return `${Math.min(100, Math.round(normalized))}%`;
}

export function AuditSessionSummaryCard({
  auditId,
  modelTarget,
  mode,
  selectedModulesCount,
  status = 'draft',
  verdict = null,
  confidence = null,
  evidencePacketId,
  updatedAt,
  className,
}: AuditSessionSummaryCardProps): JSX.Element {
  return (
    <GlassPanel
      as="section"
      intensity="thin"
      padding={18}
      className={className}
      ariaLabel="Audit session summary"
    >
      <div style={shellStyle}>
        <div style={headerStyle}>
          <div>
            <p style={eyebrowStyle}>Session summary</p>
            <h2 style={titleStyle}>
              {auditId ? `Audit ${auditId}` : 'No audit session yet'}
            </h2>
          </div>
          <span style={statusPillStyle}>{statusLabels[status]}</span>
        </div>

        <div style={gridStyle}>
          <div style={tileStyle}>
            <span style={labelStyle}>Audit ID</span>
            <span style={{ ...valueStyle, fontFamily: FONT_MONO }}>
              {auditId ?? 'Not created'}
            </span>
          </div>
          <div style={tileStyle}>
            <span style={labelStyle}>Model target</span>
            <span style={valueStyle}>{modelTarget ?? 'Not connected'}</span>
          </div>
          <div style={tileStyle}>
            <span style={labelStyle}>Mode</span>
            <span style={valueStyle}>{mode ?? 'Not selected'}</span>
          </div>
          <div style={tileStyle}>
            <span style={labelStyle}>Selected modules</span>
            <span style={valueStyle}>{moduleCountLabel(selectedModulesCount)}</span>
          </div>
          <div style={tileStyle}>
            <span style={labelStyle}>Verdict</span>
            <span style={verdictStyle(verdict)}>
              {verdict ? verdictLabels[verdict] : 'No verdict yet'}
            </span>
          </div>
          <div style={tileStyle}>
            <span style={labelStyle}>Confidence</span>
            <span style={valueStyle}>{confidenceLabel(confidence)}</span>
          </div>
          <div style={tileStyle}>
            <span style={labelStyle}>Evidence Packet</span>
            <span style={{ ...valueStyle, fontFamily: evidencePacketId ? FONT_MONO : undefined }}>
              {evidencePacketId ?? 'Not created'}
            </span>
          </div>
          <div style={tileStyle}>
            <span style={labelStyle}>Updated</span>
            <span style={valueStyle}>{updatedAt ?? 'Not updated'}</span>
          </div>
        </div>
      </div>
    </GlassPanel>
  );
}

export default AuditSessionSummaryCard;
