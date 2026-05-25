import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { AuditVerdictCard } from './AuditVerdictCard';

describe('AuditVerdictCard', () => {
  it('renders the direct verdict label and normalized confidence', () => {
    render(
      <AuditVerdictCard
        verdict="FLAG_FOR_HUMAN_REVIEW"
        confidence={0.87}
        evidencePacket={{ packetId: 'packet-42', evidenceCount: 6 }}
      />,
    );

    expect(screen.getByText('FLAG FOR HUMAN REVIEW')).toBeInTheDocument();
    expect(screen.getByLabelText('Confidence 87%')).toBeInTheDocument();
    expect(screen.getByText('packet-42')).toBeInTheDocument();
    expect(screen.getByText('6')).toBeInTheDocument();
  });

  it('fires Evidence Packet and Inspect in Atlas actions', () => {
    const openPacket = vi.fn();
    const inspect = vi.fn();

    render(
      <AuditVerdictCard
        verdict="ACCEPT"
        confidence={92}
        onOpenEvidencePacket={openPacket}
        onInspectInAtlas={inspect}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Evidence Packet' }));
    fireEvent.click(screen.getByRole('button', { name: 'Inspect in Atlas' }));

    expect(openPacket).toHaveBeenCalledTimes(1);
    expect(inspect).toHaveBeenCalledTimes(1);
  });
});
