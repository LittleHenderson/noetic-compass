import type { CSSProperties, ReactNode } from 'react';
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

export default function LicenseGate({ children }: { children?: ReactNode }) {
  return (
    <GlassPanel intensity="thin" padding={18} as="section" ariaLabel="License gate">
      <h2 style={headingStyle}>License gate</h2>
      <p style={bodyStyle}>
        Alpha placeholder — gating is enforced at the route level. Full license
        enforcement lands with roadmap item #11.
      </p>
      {children}
    </GlassPanel>
  );
}
