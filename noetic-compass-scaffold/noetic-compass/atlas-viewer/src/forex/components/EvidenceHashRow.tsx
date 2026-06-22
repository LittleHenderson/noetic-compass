// A monospace row for a single evidence hash with a verification marker.
// Truncates the middle of long SHA-256 digests so the prefix/suffix stay
// readable (and copyable in full via the title attribute).

import type { CSSProperties } from 'react';
import { COLORS, FONT_MONO, ACCENT_TEAL } from '../../lib/designTokens';

export interface EvidenceHashRowProps {
  label: string;
  hash: string;
  verified?: boolean;
  style?: CSSProperties;
}

function truncateMiddle(value: string, head = 10, tail = 8): string {
  if (value.length <= head + tail + 1) return value;
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

const rowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 12,
  padding: '6px 0',
  borderBottom: `1px solid ${COLORS.borderSubtle}`,
  fontSize: 12,
};

const labelStyle: CSSProperties = {
  color: COLORS.textSecondary,
  whiteSpace: 'nowrap',
};

const hashStyle: CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 11.5,
  color: COLORS.textPrimary,
  letterSpacing: 0.2,
};

export function EvidenceHashRow({ label, hash, verified, style }: EvidenceHashRowProps) {
  return (
    <div style={{ ...rowStyle, ...style }} data-testid="evidence-hash-row">
      <span style={labelStyle}>{label}</span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
        <code style={hashStyle} title={hash}>
          {truncateMiddle(hash)}
        </code>
        {verified !== undefined ? (
          <span
            aria-label={verified ? 'verified' : 'unverified'}
            title={verified ? 'Chain verified' : 'Not verified'}
            style={{
              color: verified ? ACCENT_TEAL : COLORS.textMuted,
              fontSize: 13,
              fontWeight: 700,
            }}
          >
            {verified ? '✓' : '—'}
          </span>
        ) : null}
      </span>
    </div>
  );
}

export default EvidenceHashRow;
