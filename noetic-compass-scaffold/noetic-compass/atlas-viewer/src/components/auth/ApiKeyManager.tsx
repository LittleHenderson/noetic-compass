import type { CSSProperties } from 'react';
import { GlassPanel } from '../ui/GlassPanel';
import { COLORS } from '../../lib/designTokens';

const headingStyle: CSSProperties = {
  margin: 0,
  fontSize: 14,
  fontWeight: 600,
  letterSpacing: 0.4,
  textTransform: 'uppercase',
  color: COLORS.textMuted,
};

const bodyStyle: CSSProperties = {
  margin: '6px 0 0 0',
  fontSize: 13,
  lineHeight: 1.5,
  color: COLORS.textSecondary,
};

export default function ApiKeyManager() {
  return (
    <GlassPanel intensity="thin" padding={18} as="section" ariaLabel="API key manager">
      <h2 style={headingStyle}>API keys</h2>
      <p style={bodyStyle}>
        Alpha placeholder — issuance, revocation, and per-key rate limits land
        with roadmap items #5 + #11.
      </p>
    </GlassPanel>
  );
}
