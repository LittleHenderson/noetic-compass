import type { CSSProperties } from 'react';
import { GlassPanel } from '../ui/GlassPanel';
import { AuditVerdictChip } from '../audit/AuditVerdictChip';
import { ScopeRibbon } from '../audit/ScopeRibbon';
import { ProofChipRail } from '../audit/ProofChipRail';
import EvidencePacketVerificationPanel from '../audit/EvidencePacketVerificationPanel';
import { COLORS, FONT_FAMILY, FONT_MONO, TONE_TINT } from '../../lib/designTokens';
import type { AuditVerdict, ProvenanceChip } from '../../lib/casHarnessAudit';

interface VerifierDecisionLike {
  decisionScope?: string | null;
}

interface AuditScopeLike {
  label?: string | null;
  detail?: string | null;
  verdictDisposition?: string | null;
}

export interface EvidenceRailProps {
  verdict?: AuditVerdict | null;
  confidence?: number | null;
  /** Customer-safe gate result for the verdict chip (computed by the page). */
  customerSafe?: boolean;
  chips: ProvenanceChip[];
  verifierDecision?: VerifierDecisionLike | null;
  auditScope?: AuditScopeLike | null;
  evidencePacketTraceId?: string | null;
  onInspectInAtlas?: () => void;
  className?: string;
}

const railStyle: CSSProperties = {
  display: 'grid',
  gap: 14,
  fontFamily: FONT_FAMILY,
};

const packetPanelStyle: CSSProperties = {
  display: 'grid',
  gap: 10,
  padding: 14,
  borderRadius: 8,
  border: `1px solid ${TONE_TINT.teal.borderSoft}`,
  background: 'rgba(2, 6, 23, 0.40)',
};

const packetEyebrowStyle: CSSProperties = {
  margin: 0,
  color: TONE_TINT.teal.accent,
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
};

const packetIdStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12,
  fontFamily: FONT_MONO,
  overflowWrap: 'anywhere',
};

const inspectButtonStyle: CSSProperties = {
  minHeight: 34,
  padding: '7px 12px',
  borderRadius: 6,
  border: `1px solid ${COLORS.borderStrong}`,
  background: 'rgba(255, 255, 255, 0.04)',
  color: COLORS.textPrimary,
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 12.5,
  fontWeight: 700,
  width: '100%',
};

const dividerStyle: CSSProperties = {
  height: 1,
  background: COLORS.borderSubtle,
  border: 'none',
  margin: 0,
};

/**
 * Right-rail evidence orchestrator — the consolidated, honest decision surface:
 * verdict chip (with the customer-safe ACCEPT gate) -> scope ribbon -> proof
 * chips -> compact packet verification + Inspect-in-Atlas. No raw JSON appears
 * here; the packet panel uses only its honest statusLabel.
 */
export function EvidenceRail({
  verdict = null,
  confidence = null,
  customerSafe,
  chips,
  verifierDecision = null,
  auditScope = null,
  evidencePacketTraceId = null,
  onInspectInAtlas,
  className,
}: EvidenceRailProps): JSX.Element {
  return (
    <GlassPanel
      as="aside"
      intensity="regular"
      padding={16}
      className={className}
      ariaLabel="Audit evidence rail"
    >
      <div style={railStyle}>
        <AuditVerdictChip
          verdict={verdict}
          confidence={confidence}
          customerSafe={customerSafe}
        />

        <ScopeRibbon verifierDecision={verifierDecision} auditScope={auditScope} />

        <hr style={dividerStyle} />

        <ProofChipRail chips={chips} />

        <hr style={dividerStyle} />

        <div style={packetPanelStyle}>
          <p style={packetEyebrowStyle}>Evidence packet</p>
          {evidencePacketTraceId ? (
            <>
              <p style={{ ...packetIdStyle, color: COLORS.textSecondary }}>Packet trace ID</p>
              <p style={packetIdStyle}>{evidencePacketTraceId}</p>
              <EvidencePacketVerificationPanel traceId={evidencePacketTraceId} />
            </>
          ) : (
            <p style={{ ...packetIdStyle, color: COLORS.textMuted }}>
              No Evidence Packet has been created for this run yet.
            </p>
          )}
          {onInspectInAtlas ? (
            <button type="button" style={inspectButtonStyle} onClick={onInspectInAtlas}>
              Inspect in Atlas
            </button>
          ) : null}
        </div>
      </div>
    </GlassPanel>
  );
}

export default EvidenceRail;
