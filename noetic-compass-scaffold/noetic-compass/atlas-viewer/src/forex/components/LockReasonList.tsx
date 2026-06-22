// Lists the reasons a capability is locked (blockers, live locks, missing
// gates). Empty list renders an explicit "clear" state rather than nothing, so
// the absence of locks is never ambiguous.

import type { CSSProperties } from 'react';
import { COLORS, ACCENT_TEAL } from '../../lib/designTokens';

export interface LockReasonListProps {
  reasons: string[];
  /** Message shown when there are no reasons. */
  emptyLabel?: string;
  /** Glyph before each reason. */
  glyph?: string;
  style?: CSSProperties;
}

const listStyle: CSSProperties = {
  listStyle: 'none',
  margin: 0,
  padding: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
};

const itemStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 8,
  fontSize: 12.5,
  lineHeight: 1.45,
  color: COLORS.textSecondary,
};

export function LockReasonList({
  reasons,
  emptyLabel = 'No active locks or blockers.',
  glyph = '🔒',
  style,
}: LockReasonListProps) {
  if (reasons.length === 0) {
    return (
      <div
        data-testid="lock-reason-empty"
        style={{ fontSize: 12.5, color: ACCENT_TEAL, display: 'flex', alignItems: 'center', gap: 8, ...style }}
      >
        <span aria-hidden="true">✓</span>
        <span>{emptyLabel}</span>
      </div>
    );
  }

  return (
    <ul style={{ ...listStyle, ...style }} data-testid="lock-reason-list">
      {reasons.map((reason, i) => (
        <li key={`${i}-${reason}`} style={itemStyle}>
          <span aria-hidden="true" style={{ flexShrink: 0 }}>
            {glyph}
          </span>
          <span>{reason}</span>
        </li>
      ))}
    </ul>
  );
}

export default LockReasonList;
