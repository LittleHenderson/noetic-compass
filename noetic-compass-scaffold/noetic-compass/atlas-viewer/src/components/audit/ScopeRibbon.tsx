import type { CSSProperties } from 'react';
import { COLORS, FONT_FAMILY, TONE_TINT } from '../../lib/designTokens';
import {
  scopeRibbonModel,
  type ScopeRibbonModel,
} from '../../lib/casHarnessAudit';

interface VerifierDecisionLike {
  decisionScope?: string | null;
}

interface AuditScopeLike {
  label?: string | null;
  detail?: string | null;
  verdictDisposition?: string | null;
}

export interface ScopeRibbonProps {
  verifierDecision?: VerifierDecisionLike | null;
  auditScope?: AuditScopeLike | null;
  /** Pre-built model (used by tests); defaults to deriving from the inputs. */
  model?: ScopeRibbonModel;
  className?: string;
}

// A validation packet is amber (caveat); everything else is a calm teal scope
// note. Either way the boundary text is always-visible, never tooltip-only.
const ribbonStyle = (validation: boolean): CSSProperties => {
  const tone = validation ? TONE_TINT.amber : TONE_TINT.teal;
  return {
    display: 'grid',
    gap: 4,
    padding: '9px 11px',
    borderRadius: 8,
    border: `1px solid ${validation ? tone.border : tone.borderSoft}`,
    background: tone.fillSoft,
    fontFamily: FONT_FAMILY,
  };
};

const eyebrowStyle = (validation: boolean): CSSProperties => ({
  margin: 0,
  fontSize: 10.5,
  fontWeight: 800,
  letterSpacing: 0.5,
  textTransform: 'uppercase',
  color: validation ? TONE_TINT.amber.accent : TONE_TINT.teal.accent,
});

const scopeTextStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 12.5,
  fontWeight: 600,
  lineHeight: 1.4,
};

const boundaryTextStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
};

/**
 * Persistent validation-vs-production scope ribbon. Surfaces the verifier scope
 * label and — for a validation packet — the boundary caveat, always visible
 * under the verdict. Wording is preserved verbatim from the verifier strings.
 * Renders nothing when there is no scope signal at all.
 */
export function ScopeRibbon({
  verifierDecision,
  auditScope,
  model,
  className,
}: ScopeRibbonProps): JSX.Element | null {
  const resolved = model ?? scopeRibbonModel(verifierDecision, auditScope);
  if (!resolved.scopeLabel && !resolved.boundaryLabel && !resolved.dispositionLabel) {
    return null;
  }

  return (
    <section
      role="note"
      aria-label="Audit scope"
      className={className}
      style={ribbonStyle(resolved.isValidationPacket)}
    >
      <p style={eyebrowStyle(resolved.isValidationPacket)}>Scope</p>
      {resolved.scopeLabel ? <p style={scopeTextStyle}>{resolved.scopeLabel}</p> : null}
      {resolved.boundaryLabel ? (
        <p style={boundaryTextStyle}>{resolved.boundaryLabel}</p>
      ) : null}
      {resolved.dispositionLabel ? (
        <p style={boundaryTextStyle}>{resolved.dispositionLabel}</p>
      ) : null}
    </section>
  );
}

export default ScopeRibbon;
