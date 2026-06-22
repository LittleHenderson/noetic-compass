// A colored pill for a single claim-status word (NOT LICENSED, OPEN, PASS, …).
// Tone is derived from the word so the same status always reads the same color.

import type { CSSProperties } from 'react';
import { chipStyle, toneForClaim, type ChipTone } from './chipStyles';

export interface ClaimStatusChipProps {
  status: string;
  /** Override the auto-derived tone when needed. */
  tone?: ChipTone;
  title?: string;
  style?: CSSProperties;
}

export function ClaimStatusChip({ status, tone, title, style }: ClaimStatusChipProps) {
  const resolved = tone ?? toneForClaim(status);
  return (
    <span
      style={chipStyle(resolved, style)}
      title={title ?? status}
      data-testid="claim-status-chip"
      data-status={status}
      data-tone={resolved}
    >
      {status}
    </span>
  );
}

export default ClaimStatusChip;
