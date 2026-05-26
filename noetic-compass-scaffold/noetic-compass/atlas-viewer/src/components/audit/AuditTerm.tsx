import type { CSSProperties, ReactNode } from 'react';
import {
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
} from '../../lib/designTokens';
import { AuditPopover } from './AuditPopover';

export type AuditTermKey =
  | 'baseline'
  | 'ablation'
  | 'matchedControl'
  | 'evidencePacket'
  | 'confidence'
  | 'coverage'
  | 'inversion'
  | 'blindspot';

export const AUDIT_TERM_DEFINITIONS: Record<AuditTermKey, string> = {
  baseline:
    'The comparison opponent. It answers: did CAS beat a simpler method, such as guessing from text or random/wrong-drive controls?',
  ablation:
    'A causal removal test. CAS removes or suppresses a selected internal direction or cover and checks whether the signal or output changes.',
  matchedControl:
    'The fair comparison. CAS repeats the test with random or wrong-drive removals to make sure the effect is not generic damage.',
  evidencePacket:
    'The flight-recorder record for a CAS run: model, prompt, verdict, confidence, proof chips, trace id, and hashes.',
  confidence:
    'The numeric strength of this verdict or interpretation under the active verifier. It is not mathematical certainty.',
  coverage:
    'The share of rows where CAS was willing to return a measured verdict instead of leaving the row for review.',
  inversion:
    'A structural drift risk: the model appears to flip, suppress, or distort a CAS signal compared with the expected direction.',
  blindspot:
    'A model-internal area where a human concern may be weak, missing, or suppressed, such as consent, safety, or long-term purpose.',
};

export interface AuditTermProps {
  term: AuditTermKey;
  children: ReactNode;
  className?: string;
}

const termStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  minHeight: 22,
  margin: '0 2px',
  padding: '1px 6px',
  borderRadius: 5,
  border: '1px solid rgba(45, 212, 191, 0.28)',
  background: 'rgba(45, 212, 191, 0.08)',
  color: '#ccfbf1',
  fontFamily: FONT_FAMILY,
  fontSize: '0.95em',
  fontWeight: 800,
  lineHeight: 1.4,
  cursor: 'help',
  outlineColor: ACCENT_TEAL,
  textDecoration: `underline dotted ${COLORS.textMuted}`,
  textUnderlineOffset: 3,
};

export function AuditTerm({
  term,
  children,
  className,
}: AuditTermProps): JSX.Element {
  const definition = AUDIT_TERM_DEFINITIONS[term];
  return (
    <AuditPopover briefing={definition} placement="top">
      <span
        aria-label={`${String(children)}: ${definition}`}
        className={className}
        role="note"
        style={termStyle}
      >
        {children}
      </span>
    </AuditPopover>
  );
}

export default AuditTerm;
