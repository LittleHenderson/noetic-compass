import type { CSSProperties } from 'react';
import { GlassPanel } from '../ui/GlassPanel';
import { AuditVerdictChip } from '../audit/AuditVerdictChip';
import { ScopeRibbon } from '../audit/ScopeRibbon';
import { ProofChipRail } from '../audit/ProofChipRail';
import EvidencePacketVerificationPanel from '../audit/EvidencePacketVerificationPanel';
import { COLORS, FONT_FAMILY, FONT_MONO, TONE_TINT } from '../../lib/designTokens';
import type { AuditVerdict, ProvenanceChip } from '../../lib/casHarnessAudit';
import { requestPacketExplanation } from '../../lib/packetExplainerBus';
import { epFieldAnchorProps } from '../../lib/packetExplainerLinks';

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
  authToken?: string | null;
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

// The "Explain this packet (plain English)" action. Teal-accented like the
// other primary evidence affordances; only rendered once a packet trace exists.
const explainButtonStyle: CSSProperties = {
  minHeight: 36,
  padding: '8px 12px',
  borderRadius: 6,
  border: `1px solid ${TONE_TINT.teal.border}`,
  background: TONE_TINT.teal.fill,
  color: TONE_TINT.teal.text,
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 12.5,
  fontWeight: 800,
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
  authToken = null,
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
        {/* Anchored so a ref-chip for `verdict` / `verdict_echo` scrolls here. */}
        <div {...epFieldAnchorProps('verdict')}>
          <AuditVerdictChip
            verdict={verdict}
            confidence={confidence}
            customerSafe={customerSafe}
          />
        </div>

        <ScopeRibbon verifierDecision={verifierDecision} auditScope={auditScope} />

        <hr style={dividerStyle} />

        {/* Each proof chip row is anchored by its id so a ref-chip for
            `proof_chips.<id>.status` scrolls to that exact chip. */}
        <ProofChipRail chips={chips} anchorRef={epFieldAnchorProps} />

        <hr style={dividerStyle} />

        {/* Anchored so a ref-chip for `anchor.status` scrolls to the packet
            / WORM-anchor panel. */}
        <div style={packetPanelStyle} {...epFieldAnchorProps('anchor.status')}>
          <p style={packetEyebrowStyle}>Evidence packet</p>
          {evidencePacketTraceId ? (
            <>
              <p style={{ ...packetIdStyle, color: COLORS.textSecondary }}>Packet trace ID</p>
              <p style={packetIdStyle}>{evidencePacketTraceId}</p>
              <button
                type="button"
                style={explainButtonStyle}
                onClick={() =>
                  requestPacketExplanation({
                    traceId: evidencePacketTraceId,
                    epVerdict: verdict ?? '',
                  })
                }
                data-testid="explain-packet-button"
              >
                Explain this packet (plain English)
              </button>
              <EvidencePacketVerificationPanel
                traceId={evidencePacketTraceId}
                authToken={authToken}
              />
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
