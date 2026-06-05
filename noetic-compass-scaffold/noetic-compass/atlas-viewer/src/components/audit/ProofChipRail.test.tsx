import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProofChipRail } from './ProofChipRail';
import type { ProvenanceChip } from '../../lib/casHarnessAudit';

// Minimal chip factory — the rail relabels by id on the customer surface, so the
// backend `name`/`statusLabel` text is intentionally distinct from what renders.
function chip(
  id: ProvenanceChip['id'],
  status: ProvenanceChip['status'],
): ProvenanceChip {
  return { id, name: `backend-${id}`, status, statusLabel: status, detail: '' };
}

const ALL_PASS: ProvenanceChip[] = [
  chip('model_proof', 'verified'),
  chip('cas_readout', 'present'),
  chip('causal_proof', 'verified'),
  chip('control_proof', 'present'),
  chip('output_proof', 'verified'),
  chip('packet_proof', 'present'),
];

describe('ProofChipRail', () => {
  it('renders the full long relabeled name and exposes it via a title tooltip', () => {
    // The long label is the one most likely to overflow the 360px rail; the
    // wrap fix must keep it intact (no truncation of the visible text) and put
    // the complete string in `title` as the fallback.
    render(<ProofChipRail chips={ALL_PASS} />);

    const label = screen.getByText('CAS readout (model-internal signal)');
    expect(label).toBeInTheDocument();
    expect(label).toHaveAttribute('title', 'CAS readout (model-internal signal)');
    // The wrap fix lets the long name break instead of overflowing.
    expect(label.style.overflowWrap).toBe('anywhere');
    // jsdom serializes the numeric `minWidth: 0` style as the unitless '0'.
    expect(label.style.minWidth).toBe('0');
  });

  it('counts only verified/present chips as ready', () => {
    render(<ProofChipRail chips={ALL_PASS} />);
    expect(screen.getByLabelText('6 of 6 proof chips ready')).toBeInTheDocument();
  });

  it('renders the literal backend status word for a blocked chip, never "pass"', () => {
    const chips: ProvenanceChip[] = [
      chip('model_proof', 'missing'),
      chip('cas_readout', 'unavailable'),
      chip('causal_proof', 'failed'),
      chip('control_proof', 'unavailable'),
      chip('output_proof', 'unavailable'),
      chip('packet_proof', 'missing'),
    ];
    render(<ProofChipRail chips={chips} />);

    // Honesty: blocked chips surface the exact AuditStatus word, not a pass.
    expect(screen.getAllByText('missing').length).toBeGreaterThan(0);
    expect(screen.getByText('failed')).toBeInTheDocument();
    expect(screen.getAllByText('unavailable').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('0 of 6 proof chips ready')).toBeInTheDocument();
  });
});
