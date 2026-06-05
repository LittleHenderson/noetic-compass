import type { CSSProperties } from 'react';
import {
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
  TONE_TINT,
} from '../../lib/designTokens';
import type { AuditLifecycleStatus } from './AuditSessionProgress';

export interface AuditRunHeaderProps {
  /** Backend audit_id once a session exists. */
  auditId?: string | null;
  /** Model target under audit (session.model_id, falling back to the target). */
  modelTarget?: string | null;
  /** Audit mode (e.g. BALANCED). */
  mode?: string | null;
  /** Current lifecycle status — drives the status pill word + tone. */
  status?: AuditLifecycleStatus;
  className?: string;
}

// Plain status words for the header pill. These are presentation labels for the
// lifecycle union; the backend status union itself is unchanged.
const STATUS_LABEL: Record<AuditLifecycleStatus, string> = {
  draft: 'No active run',
  validating: 'Validating',
  running: 'Running',
  runner_pending: 'Runner pending',
  evidence_pending: 'Verifying',
  complete: 'Complete',
  failed: 'Failed',
};

type HeaderTone = 'teal' | 'amber' | 'rose' | 'muted';

function toneFor(status: AuditLifecycleStatus): HeaderTone {
  if (status === 'complete') return 'teal';
  if (status === 'failed') return 'rose';
  if (status === 'validating' || status === 'running' || status === 'evidence_pending') {
    return 'amber';
  }
  if (status === 'runner_pending') return 'amber';
  return 'muted';
}

const shellStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 12,
  padding: '12px 16px',
  borderRadius: 10,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(2, 6, 23, 0.34)',
  fontFamily: FONT_FAMILY,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 10.5,
  fontWeight: 800,
  letterSpacing: 0.8,
  textTransform: 'uppercase',
};

const idStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontFamily: FONT_MONO,
  fontSize: 13.5,
  fontWeight: 800,
  letterSpacing: 0,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const metaRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 8,
  color: COLORS.textSecondary,
  fontSize: 12,
  fontFamily: FONT_MONO,
};

const metaSepStyle: CSSProperties = {
  color: COLORS.textFaint,
};

const statusPillStyle = (tone: HeaderTone): CSSProperties => {
  const tint = TONE_TINT[tone];
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 7,
    minHeight: 28,
    marginLeft: 'auto',
    padding: '4px 11px',
    borderRadius: 999,
    border: `1px solid ${tone === 'muted' ? tint.borderSoft : tint.border}`,
    background: tint.fillSoft,
    color: tone === 'muted' ? COLORS.textSecondary : tint.text,
    fontFamily: FONT_MONO,
    fontSize: 11.5,
    fontWeight: 800,
    letterSpacing: 0.3,
    whiteSpace: 'nowrap',
  };
};

const dotStyle = (tone: HeaderTone): CSSProperties => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  background: tone === 'muted' ? COLORS.textMuted : TONE_TINT[tone].accent,
  flex: '0 0 auto',
});

/**
 * Calm one-row run header — audit_id · model · mode · status. Replaces the large
 * animated marketing H1 with a quiet status strip that reads like a Codex/Claude
 * Code run header. The status word is always present alongside the tone, never
 * color-only. No verdict is shown here (the right rail owns the decision).
 */
export function AuditRunHeader({
  auditId = null,
  modelTarget = null,
  mode = null,
  status = 'draft',
  className,
}: AuditRunHeaderProps): JSX.Element {
  const tone = toneFor(status);
  const hasMeta = Boolean(modelTarget || mode);

  return (
    <header style={shellStyle} className={className} aria-label="Audit run header">
      <div style={{ display: 'grid', gap: 3, minWidth: 0 }}>
        <p style={eyebrowStyle}>CAS Harness audit</p>
        <p style={idStyle}>{auditId ? `Audit ${auditId}` : 'New audit'}</p>
        {hasMeta ? (
          <div style={metaRowStyle} aria-label="Run target and mode">
            {modelTarget ? <span>{modelTarget}</span> : null}
            {modelTarget && mode ? <span style={metaSepStyle}>·</span> : null}
            {mode ? <span>{mode}</span> : null}
          </div>
        ) : (
          <div style={metaRowStyle}>
            <span style={{ color: COLORS.textMuted }}>
              Connect a model below to begin.
            </span>
          </div>
        )}
      </div>
      <span
        role="status"
        aria-label={`Run status: ${STATUS_LABEL[status]}`}
        style={statusPillStyle(tone)}
      >
        <span aria-hidden="true" style={dotStyle(tone)} />
        {STATUS_LABEL[status]}
      </span>
    </header>
  );
}

export default AuditRunHeader;
