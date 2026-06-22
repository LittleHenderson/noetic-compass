// A labeled key→value chip, e.g. "Mode · PAPER_MT5" or "Paper proof · 1 / 30".
// Used across the banner and proof panels for compact status readouts.

import type { CSSProperties, ReactNode } from 'react';
import { COLORS } from '../../lib/designTokens';
import { toneColor, type ChipTone } from './chipStyles';

export interface ForexStatusChipProps {
  label: string;
  value: ReactNode;
  tone?: ChipTone;
  title?: string;
  style?: CSSProperties;
}

const wrapStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 0,
  borderRadius: 6,
  overflow: 'hidden',
  border: `1px solid ${COLORS.borderSubtle}`,
  fontSize: 11,
  letterSpacing: 0.3,
  whiteSpace: 'nowrap',
};

const labelStyle: CSSProperties = {
  padding: '3px 8px',
  background: 'rgba(255, 255, 255, 0.03)',
  color: COLORS.textMuted,
  fontWeight: 600,
  textTransform: 'uppercase',
};

export function ForexStatusChip({ label, value, tone = 'neutral', title, style }: ForexStatusChipProps) {
  const c = toneColor(tone);
  const valueStyle: CSSProperties = {
    padding: '3px 9px',
    background: c.bg,
    color: c.fg,
    fontWeight: 700,
    fontVariantNumeric: 'tabular-nums',
  };
  return (
    <span
      style={{ ...wrapStyle, ...style }}
      title={title}
      data-testid="forex-status-chip"
      data-label={label}
      data-tone={tone}
    >
      <span style={labelStyle}>{label}</span>
      <span style={valueStyle}>{value}</span>
    </span>
  );
}

export default ForexStatusChip;
