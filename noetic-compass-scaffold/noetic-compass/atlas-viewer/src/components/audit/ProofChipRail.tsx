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
  /**
   * Optional anchor-prop factory. When provided, each chip row is stamped with
   * the props returned for `proof_chips.<chipId>.status`, so the packet
   * explainer's ref-chips can scroll to that exact chip. Kept generic so this
   * shared component never imports the explainer link module directly.
   */
  anchorRef?: (ref: string) => Record<string, string>;
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
// out of this surface; only these plain names appear. These labels intentionally
// WIN over the backend chip.name on this customer surface so the rail reads in
// plain language; the API chip id + status words are untouched.
const CHIP_LABEL: Record<ProvenanceChipId, string> = {
  model_proof: 'Model proof',
  cas_readout: 'CAS readout (model-internal signal)',
  causal_proof: 'Causal check (ablation)',
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
    // Align to the top so a wrapped two-line label keeps the status word pinned
    // to the first line rather than vertically centering against tall content.
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 10,
    padding: '7px 10px',
    borderRadius: 6,
    border: `1px solid ${state === 'pass' ? tone.borderSoft : state === 'blocked' ? tone.borderSoft : COLORS.borderSubtle}`,
    background: tone.fillSoft,
  };
};

const nameStyle: CSSProperties = {
  // The relabeled names (e.g. "CAS readout (model-internal signal)") are long
  // for the 360px rail. Let them wrap cleanly to a second line instead of
  // overflowing: min-width 0 lets the flex item shrink, overflowWrap breaks the
  // longest token if needed. The full label is also exposed via `title`.
  flex: '1 1 auto',
  minWidth: 0,
  color: COLORS.textPrimary,
  fontSize: 12.5,
  fontWeight: 700,
  lineHeight: 1.3,
  overflowWrap: 'anywhere',
};

const statusWordStyle = (state: ChipState): CSSProperties => {
  const tone = state === 'pass' ? TONE_TINT.teal : state === 'blocked' ? TONE_TINT.amber : TONE_TINT.muted;
  return {
    flex: '0 0 auto',
    // Nudge down so the pill optically aligns with the first line of a wrapped
    // (flex-start) label rather than sitting above the cap height.
    marginTop: 1,
    padding: '2px 7px',
    borderRadius: 4,
    color: state === 'unknown' ? COLORS.textMuted : tone.text,
    background: tone.fill,
    fontFamily: FONT_MONO,
    fontSize: 10,
    fontWeight: 800,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
    whiteSpace: 'nowrap',
  };
};

/**
 * Vertical proof-chip status stack with an "N/6 ready" counter. Lifts the chip
 * grid out of the verdict explainer into the right rail. Honesty rule: only
 * verified/present are a pass (teal); missing/unavailable/failed render the
 * literal status word in amber, never teal. Color is never the only signal.
 */
export function ProofChipRail({ chips, className, anchorRef }: ProofChipRailProps): JSX.Element {
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
          const anchorProps = anchorRef ? anchorRef(`proof_chips.${id}.status`) : null;
          return (
            <li key={id} style={rowStyle(state)} data-state={state} {...anchorProps}>
              <span style={nameStyle} title={CHIP_LABEL[id]}>
                {CHIP_LABEL[id]}
              </span>
              <span style={statusWordStyle(state)}>{chipStatusWord(chip)}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default ProofChipRail;
