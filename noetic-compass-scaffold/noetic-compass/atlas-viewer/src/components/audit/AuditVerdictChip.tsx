import type { CSSProperties } from 'react';
import {
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
  TONE_TINT,
  type ToneKey,
} from '../../lib/designTokens';
import {
  isAuditResultCustomerSafe,
  type AuditSessionSummary,
  type AuditVerdict,
} from '../../lib/casHarnessAudit';

// Verbatim labels — must match AuditVerdictCard's verdictLabels exactly.
const verdictLabels: Record<AuditVerdict, string> = {
  ACCEPT: 'ACCEPT',
  SUPPRESS: 'SUPPRESS',
  FLAG_FOR_HUMAN_REVIEW: 'FLAG FOR HUMAN REVIEW',
};

export interface AuditVerdictChipProps {
  verdict?: AuditVerdict | null;
  confidence?: number | null;
  /**
   * Customer-safe gate result. When omitted it is derived from `summary` via
   * `isAuditResultCustomerSafe`. A clean teal ACCEPT renders ONLY when this is
   * true; otherwise an ACCEPT verdict shows the amber scoped band.
   */
  customerSafe?: boolean;
  /** Session summary used to derive `customerSafe` when not passed explicitly. */
  summary?: AuditSessionSummary | null;
  className?: string;
}

function resolveCustomerSafe(
  customerSafe: boolean | undefined,
  summary: AuditSessionSummary | null | undefined,
): boolean {
  if (typeof customerSafe === 'boolean') return customerSafe;
  if (!summary) return false;
  try {
    return isAuditResultCustomerSafe(summary);
  } catch {
    return false;
  }
}

// Resolve the chrome tone. ACCEPT is teal ONLY when customer-safe; a scoped
// ACCEPT is amber. FLAG is amber, SUPPRESS rose, no-verdict muted.
function toneFor(
  verdict: AuditVerdict | null,
  customerSafe: boolean,
): { key: ToneKey; scopedAccept: boolean } {
  if (!verdict) return { key: 'muted', scopedAccept: false };
  if (verdict === 'ACCEPT') {
    return customerSafe ? { key: 'teal', scopedAccept: false } : { key: 'amber', scopedAccept: true };
  }
  if (verdict === 'SUPPRESS') return { key: 'rose', scopedAccept: false };
  return { key: 'amber', scopedAccept: false };
}

function confidencePercent(confidence: number | null | undefined): number | null {
  if (confidence == null || !Number.isFinite(confidence)) return null;
  const normalized = confidence <= 1 ? confidence * 100 : confidence;
  return Math.max(0, Math.min(100, Math.round(normalized)));
}

const shellStyle = (tone: ToneKey): CSSProperties => {
  const tint = TONE_TINT[tone];
  return {
    display: 'grid',
    gap: 12,
    padding: 16,
    borderRadius: 10,
    border: `1px solid ${tint.border}`,
    background: `linear-gradient(180deg, ${tint.fill}, rgba(255, 255, 255, 0.03))`,
    fontFamily: FONT_FAMILY,
  };
};

const eyebrowRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 8,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: 0.5,
  textTransform: 'uppercase',
};

const reviewEyebrowStyle: CSSProperties = {
  margin: 0,
  color: TONE_TINT.amber.accent,
  fontSize: 10.5,
  fontWeight: 900,
  letterSpacing: 0.5,
  textTransform: 'uppercase',
};

const verdictWordStyle = (tone: ToneKey): CSSProperties => ({
  margin: 0,
  // Shrunk for the 360px rail (was clamp(30px, 7vw, 64px) in the full card).
  fontSize: 'clamp(20px, 3vw, 30px)',
  lineHeight: 1.0,
  fontWeight: 900,
  letterSpacing: 0,
  color: TONE_TINT[tone].text,
  textWrap: 'balance',
});

const scopedBandStyle: CSSProperties = {
  display: 'grid',
  gap: 2,
  padding: '8px 10px',
  borderRadius: 6,
  border: `1px solid ${TONE_TINT.amber.border}`,
  background: TONE_TINT.amber.fillSoft,
};

const scopedBandTitleStyle: CSSProperties = {
  margin: 0,
  color: TONE_TINT.amber.text,
  fontSize: 11.5,
  fontWeight: 800,
};

const scopedBandBodyStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 11.5,
  lineHeight: 1.4,
};

const confidenceRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 10,
  color: COLORS.textSecondary,
  fontSize: 12,
  fontWeight: 700,
};

const meterTrackStyle: CSSProperties = {
  position: 'relative',
  height: 6,
  borderRadius: 3,
  overflow: 'hidden',
  background: 'rgba(255, 255, 255, 0.07)',
};

/**
 * Compact right-rail verdict chip — the honest decision surface.
 *
 * Honesty gate: a clean teal ACCEPT renders ONLY when the result is
 * customer-safe (`isAuditResultCustomerSafe`). A scoped ACCEPT still shows the
 * word ACCEPT but carries a persistent amber "scoped — not a customer-production
 * ACCEPT" band. FLAG carries an explicit "HUMAN REVIEW REQUIRED" eyebrow,
 * SUPPRESS is rose. Labels are verbatim; color is never the only signal.
 */
export function AuditVerdictChip({
  verdict = null,
  confidence = null,
  customerSafe,
  summary = null,
  className,
}: AuditVerdictChipProps): JSX.Element {
  const safe = resolveCustomerSafe(customerSafe, summary);
  const { key: tone, scopedAccept } = toneFor(verdict, safe);
  const pct = confidencePercent(confidence);
  const isFlag = verdict === 'FLAG_FOR_HUMAN_REVIEW';

  return (
    <section
      style={shellStyle(tone)}
      className={className}
      aria-label="Audit verdict"
    >
      <div style={eyebrowRowStyle}>
        <p style={eyebrowStyle}>Audit verdict</p>
        {isFlag ? <p style={reviewEyebrowStyle}>Human review required</p> : null}
      </div>

      <h2 style={verdictWordStyle(tone)}>
        {verdict ? verdictLabels[verdict] : 'NO VERDICT YET'}
      </h2>

      {scopedAccept ? (
        <div role="note" aria-label="Scoped ACCEPT caveat" style={scopedBandStyle}>
          <p style={scopedBandTitleStyle}>Scoped — not a customer-production ACCEPT</p>
          <p style={scopedBandBodyStyle}>
            This ACCEPT did not pass the customer-safety gate. Treat it as needing
            human review, not an automatic production trust signal.
          </p>
        </div>
      ) : null}

      <div aria-label={pct == null ? 'Confidence not available' : `Confidence ${pct}%`}>
        <div style={confidenceRowStyle}>
          <span>Confidence</span>
          <span style={{ color: TONE_TINT[tone].text, fontFamily: FONT_MONO }}>
            {pct == null ? 'Not computed' : `${pct}%`}
          </span>
        </div>
        <div style={{ ...meterTrackStyle, marginTop: 6 }}>
          <div
            style={{
              width: pct == null ? '0%' : `${pct}%`,
              height: '100%',
              borderRadius: 3,
              background: TONE_TINT[tone].accent,
            }}
          />
        </div>
      </div>
    </section>
  );
}

export default AuditVerdictChip;
