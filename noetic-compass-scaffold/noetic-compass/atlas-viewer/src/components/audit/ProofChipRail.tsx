import type { CSSProperties } from 'react';
import {
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
  TONE_TINT,
} from '../../lib/designTokens';
import type {
  ProvenanceChip,
  ProvenanceChipId,
} from '../../lib/casHarnessAudit';

export interface ProofChipRailProps {
  chips: ProvenanceChip[];
  className?: string;
}

const REQUIRED_ORDER: ProvenanceChipId[] = [
  'model_proof',
  'cas_readout',
  'causal_proof',
  'control_proof',
  'output_proof',
  'packet_proof',
];

// Customer-facing relabels (plan §5). Internal Stage-19/20/21 vocabulary stays
// out of this surface; only these plain names appear.
const CHIP_LABEL: Record<ProvenanceChipId, string> = {
  model_proof: 'Model proof',
  cas_readout: 'CAS readout',
  causal_proof: 'Causal check',
  control_proof: 'Matched control',
  output_proof: 'Output match',
  packet_proof: 'Evidence packet',
};

type ChipState = 'pass' | 'blocked' | 'unknown';

// Only verified / present count as a pass. Everything else (missing,
// unavailable, failed) is "blocked" and renders the LITERAL status word in a
// muted/amber tone — never teal/green.
function chipState(chip: ProvenanceChip | undefined): ChipState {
  if (!chip) return 'unknown';
  if (chip.status === 'verified' || chip.status === 'present') return 'pass';
  if (chip.status === 'missing' || chip.status === 'failed' || chip.status === 'unavailable') {
    return 'blocked';
  }
  return 'unknown';
}

// Render the literal backend status word. Pass states read "pass"; blocked
// states surface the exact AuditStatus word (missing / unavailable / failed).
function chipStatusWord(chip: ProvenanceChip | undefined): string {
  if (!chip) return 'pending';
  if (chip.status === 'verified' || chip.status === 'present') return 'pass';
  return chip.status;
}

function readyCount(chips: ProvenanceChip[]): number {
  const byId = new Map(chips.map((chip) => [chip.id, chip]));
  return REQUIRED_ORDER.reduce(
    (count, id) => (chipState(byId.get(id)) === 'pass' ? count + 1 : count),
    0,
  );
}

const shellStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
  fontFamily: FONT_FAMILY,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'baseline',
  justifyContent: 'space-between',
  gap: 8,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
};

const counterStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontFamily: FONT_MONO,
  fontSize: 12,
  fontWeight: 800,
};

const listStyle: CSSProperties = {
  display: 'grid',
  gap: 5,
  margin: 0,
  padding: 0,
  listStyle: 'none',
};

const rowStyle = (state: ChipState): CSSProperties => {
  const tone = state === 'pass' ? TONE_TINT.teal : state === 'blocked' ? TONE_TINT.amber : TONE_TINT.muted;
  return {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
    padding: '7px 10px',
    borderRadius: 6,
    border: `1px solid ${state === 'pass' ? tone.borderSoft : state === 'blocked' ? tone.borderSoft : COLORS.borderSubtle}`,
    background: tone.fillSoft,
  };
};

const nameStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontSize: 12.5,
  fontWeight: 700,
};

const statusWordStyle = (state: ChipState): CSSProperties => {
  const tone = state === 'pass' ? TONE_TINT.teal : state === 'blocked' ? TONE_TINT.amber : TONE_TINT.muted;
  return {
    flex: '0 0 auto',
    padding: '2px 7px',
    borderRadius: 4,
    color: state === 'unknown' ? COLORS.textMuted : tone.text,
    background: tone.fill,
    fontFamily: FONT_MONO,
    fontSize: 10,
    fontWeight: 800,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  };
};

/**
 * Vertical proof-chip status stack with an "N/6 ready" counter. Lifts the chip
 * grid out of the verdict explainer into the right rail. Honesty rule: only
 * verified/present are a pass (teal); missing/unavailable/failed render the
 * literal status word in amber, never teal. Color is never the only signal.
 */
export function ProofChipRail({ chips, className }: ProofChipRailProps): JSX.Element {
  const byId = new Map(chips.map((chip) => [chip.id, chip]));
  const ready = readyCount(chips);

  return (
    <section style={shellStyle} className={className} aria-label="Audit proof chips">
      <div style={headerStyle}>
        <p style={eyebrowStyle}>Proof chips</p>
        <span style={counterStyle} aria-label={`${ready} of 6 proof chips ready`}>
          {ready}/6 ready
        </span>
      </div>
      <ul style={listStyle} role="list">
        {REQUIRED_ORDER.map((id) => {
          const chip = byId.get(id);
          const state = chipState(chip);
          return (
            <li key={id} style={rowStyle(state)} data-state={state}>
              <span style={nameStyle}>{chip?.name ?? CHIP_LABEL[id]}</span>
              <span style={statusWordStyle(state)}>{chipStatusWord(chip)}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default ProofChipRail;
