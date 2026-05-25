import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProvenanceChips } from './ProvenanceChips';

describe('ProvenanceChips', () => {
  it('renders all required plain-English provenance labels', () => {
    render(<ProvenanceChips />);

    expect(screen.getByText('Model proof')).toBeInTheDocument();
    expect(screen.getByText('CAS readout')).toBeInTheDocument();
    expect(screen.getByText('Causal proof')).toBeInTheDocument();
    expect(screen.getByText('Control proof')).toBeInTheDocument();
    expect(screen.getByText('Output proof')).toBeInTheDocument();
    expect(screen.getByText('Packet proof')).toBeInTheDocument();
  });

  it('shows supplied proof states', () => {
    render(
      <ProvenanceChips
        proofs={[
          { key: 'model', state: 'verified' },
          { key: 'packet', state: 'missing', detail: 'Packet not exported' },
        ]}
      />,
    );

    expect(screen.getByText('Verified')).toBeInTheDocument();
    expect(screen.getByText('Missing')).toBeInTheDocument();
  });
});
