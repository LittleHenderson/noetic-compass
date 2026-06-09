import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { EvidencePacketFlightRecorderFaq } from './EvidencePacketFlightRecorderFaq';

describe('EvidencePacketFlightRecorderFaq', () => {
  it('keeps the FAQ collapsed until the user asks for it', () => {
    render(<EvidencePacketFlightRecorderFaq />);

    expect(screen.getByText('Evidence Packet = AI flight recorder')).toBeInTheDocument();
    expect(screen.queryByTestId('evidence-packet-flight-recorder-faq')).not.toBeInTheDocument();
  });

  it('opens the full reviewer FAQ and closes it on double click', () => {
    const requestAnimationFrameSpy = vi
      .spyOn(window, 'requestAnimationFrame')
      .mockImplementation((callback) => {
        callback(0);
        return 0;
      });

    render(<EvidencePacketFlightRecorderFaq />);

    const toggle = screen.getByRole('button', { name: 'Open FAQ' });
    fireEvent.click(toggle);

    const faq = screen.getByTestId('evidence-packet-flight-recorder-faq');
    expect(faq).toHaveTextContent('black-box flight recorder');
    expect(faq).toHaveTextContent('What Object Lock retained means.');
    expect(faq).toHaveTextContent('senior research and engineering reviewers');

    fireEvent.doubleClick(faq);

    expect(screen.queryByTestId('evidence-packet-flight-recorder-faq')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open FAQ' })).toHaveFocus();
    requestAnimationFrameSpy.mockRestore();
  });
});
