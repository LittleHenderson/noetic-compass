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

  it('labels verified packet proof as WORM retained when Object Lock proof is present', () => {
    render(
      <ProvenanceChips
        chips={[
          {
            id: 'packet_proof',
            name: 'Packet proof',
            status: 'verified',
            detail:
              'Evidence Packet trace-123 is WORM retained: S3 anchor re-read matched the packet/hash-log manifest and Object Lock GOVERNANCE retention is active.',
          },
        ]}
      />,
    );

    expect(screen.getByText('Packet proof')).toBeInTheDocument();
    expect(screen.getByText('WORM retained')).toBeInTheDocument();
  });

  it('labels verified packet proof as S3 verified when retention is not proven', () => {
    render(
      <ProvenanceChips
        chips={[
          {
            id: 'packet_proof',
            name: 'Packet proof',
            status: 'verified',
            detail:
              'Evidence Packet trace-123 is S3 verified: the anchor object was re-read and matched to the packet hash and hash-log entry.',
          },
        ]}
      />,
    );

    expect(screen.getByText('S3 verified')).toBeInTheDocument();
    expect(screen.queryByText('WORM retained')).not.toBeInTheDocument();
  });
});
