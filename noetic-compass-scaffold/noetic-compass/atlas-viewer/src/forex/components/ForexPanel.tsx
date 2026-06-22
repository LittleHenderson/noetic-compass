// A titled GlassPanel section used to compose the proof cockpit pages.

import type { CSSProperties, ReactNode } from 'react';
import { GlassPanel } from '../../components/ui/GlassPanel';
import { COLORS } from '../../lib/designTokens';

export interface ForexPanelProps {
  title: string;
  subtitle?: string;
  /** Optional right-aligned header content (chips, counts). */
  aside?: ReactNode;
  children: ReactNode;
  style?: CSSProperties;
}

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 12,
  marginBottom: 12,
};

const titleStyle: CSSProperties = {
  margin: 0,
  fontSize: 13,
  fontWeight: 700,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
  color: COLORS.textPrimary,
};

const subtitleStyle: CSSProperties = {
  margin: '3px 0 0',
  fontSize: 12,
  color: COLORS.textMuted,
  lineHeight: 1.45,
};

export function ForexPanel({ title, subtitle, aside, children, style }: ForexPanelProps) {
  return (
    <GlassPanel intensity="regular" padding={18} ariaLabel={title} style={{ width: '100%', ...style }}>
      <div style={headerStyle}>
        <div>
          <h2 style={titleStyle}>{title}</h2>
          {subtitle ? <p style={subtitleStyle}>{subtitle}</p> : null}
        </div>
        {aside ? <div style={{ flexShrink: 0 }}>{aside}</div> : null}
      </div>
      {children}
    </GlassPanel>
  );
}

export default ForexPanel;
