import type { CSSProperties } from 'react';
import { COLORS, FONT_MONO, TONE_TINT } from '../../lib/designTokens';
import {
  licenseStateFor,
  type LicenseSignal,
  type LicenseState,
} from '../../lib/casHarnessAudit';

export interface LicenseChipProps {
  /** Real entitlement signal. When omitted, the chip reads LICENSE UNKNOWN. */
  signal?: LicenseSignal | null;
  /** Pre-resolved state (e.g. from a parent). Overrides `signal` when set. */
  state?: LicenseState;
  className?: string;
}

const chipStyle = (tone: 'teal' | 'rose' | 'muted'): CSSProperties => {
  const tint = TONE_TINT[tone];
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 7,
    minHeight: 26,
    padding: '4px 9px',
    borderRadius: 6,
    border: `1px solid ${tone === 'muted' ? tint.borderSoft : tint.border}`,
    background: tint.fillSoft,
    color: tint.text,
    fontFamily: FONT_MONO,
    fontSize: 11,
    fontWeight: 800,
    letterSpacing: 0.3,
    whiteSpace: 'nowrap',
  };
};

const dotStyle = (color: string): CSSProperties => ({
  width: 7,
  height: 7,
  borderRadius: '50%',
  background: color,
  flex: '0 0 auto',
});

function toneFor(state: LicenseState): 'teal' | 'rose' | 'muted' {
  if (state === 'LICENSED') return 'teal';
  if (state === 'NOT LICENSED') return 'rose';
  return 'muted';
}

/**
 * Persistent license chip — LICENSED / NOT LICENSED / LICENSE UNKNOWN, always
 * a status WORD plus a color. Derives from a real entitlement signal and never
 * speculatively reports LICENSED; an unresolved signal reads LICENSE UNKNOWN
 * (muted). Color is never the only signal.
 */
export function LicenseChip({ signal, state, className }: LicenseChipProps): JSX.Element {
  const resolved = state ?? licenseStateFor(signal);
  const tone = toneFor(resolved);
  const dotColor = tone === 'muted' ? COLORS.textMuted : TONE_TINT[tone].accent;

  return (
    <span
      role="status"
      aria-label={`License status: ${resolved}`}
      className={className}
      style={chipStyle(tone)}
    >
      <span aria-hidden="true" style={dotStyle(dotColor)} />
      {resolved}
    </span>
  );
}

export default LicenseChip;
