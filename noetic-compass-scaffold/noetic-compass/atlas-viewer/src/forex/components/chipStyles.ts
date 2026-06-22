// Shared chip/pill tone palette for the CAS Forex cockpit. Built on the
// atlas-viewer design tokens (teal accent, amber secondary, slate text) plus a
// red danger tone reserved for the NOT LICENSED / FAIL / BLOCKED hard states.

import type { CSSProperties } from 'react';
import { ACCENT_TEAL, ACCENT_AMBER, COLORS } from '../../lib/designTokens';

export type ChipTone = 'teal' | 'amber' | 'danger' | 'muted' | 'neutral';

const DANGER = '#f87171'; // red-400

interface ToneColor {
  fg: string;
  bg: string;
  border: string;
}

export function toneColor(tone: ChipTone): ToneColor {
  switch (tone) {
    case 'teal':
      return { fg: ACCENT_TEAL, bg: 'rgba(45, 212, 191, 0.10)', border: 'rgba(45, 212, 191, 0.30)' };
    case 'amber':
      return { fg: ACCENT_AMBER, bg: 'rgba(251, 191, 36, 0.10)', border: 'rgba(251, 191, 36, 0.30)' };
    case 'danger':
      return { fg: DANGER, bg: 'rgba(248, 113, 113, 0.12)', border: 'rgba(248, 113, 113, 0.35)' };
    case 'muted':
      return { fg: COLORS.textMuted, bg: 'rgba(148, 163, 184, 0.08)', border: 'rgba(148, 163, 184, 0.20)' };
    case 'neutral':
    default:
      return { fg: COLORS.textSecondary, bg: 'rgba(255, 255, 255, 0.04)', border: COLORS.borderSubtle };
  }
}

export function chipStyle(tone: ChipTone, extra?: CSSProperties): CSSProperties {
  const c = toneColor(tone);
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '3px 9px',
    borderRadius: 6,
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: 0.4,
    color: c.fg,
    background: c.bg,
    border: `1px solid ${c.border}`,
    whiteSpace: 'nowrap',
    ...extra,
  };
}

/** Map a claim-status word to a tone. */
export function toneForClaim(status: string): ChipTone {
  const s = status.toUpperCase();
  if (s === 'NOT LICENSED' || s === 'NOT_LICENSED' || s === 'FAIL' || s === 'BLOCKED') return 'danger';
  if (s === 'OPEN' || s === 'PARTIAL' || s === 'WAIT_NEXT_TRADING_DAY') return 'amber';
  if (s === 'PASS' || s === 'VERIFIED' || s === 'MET' || s === 'READY_FOR_UI_UX') return 'teal';
  if (s === 'SUPPRESSED' || s === 'UNAVAILABLE') return 'muted';
  return 'neutral';
}

/** Map a pipeline-stage / evidence-packet status to a tone. */
export function toneForStage(status: string): ChipTone {
  const s = status.toUpperCase();
  if (s === 'LIVE_LOCKED' || s === 'WRITE_FAILED' || s === 'REJECTED' || s === 'FAIL' || s === 'CLOSED_LOSS') return 'danger';
  if (s === 'FLAG_FOR_HUMAN_REVIEW') return 'amber';
  if (
    s === 'PASS' || s === 'VERIFIED' || s === 'ALLOWED' || s === 'CLEAR' ||
    s === 'ROUTED' || s === 'EXECUTED' || s === 'ACCEPTED' || s === 'CLOSED_WIN'
  ) {
    return 'teal';
  }
  if (s === 'SUPPRESSED' || s === 'NO_ORDER' || s === 'NOT_RUN' || s === 'CANCELLED' || s === 'PROPOSED') return 'muted';
  return 'neutral';
}
