import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import EvidencePacketVerificationPanel from './EvidencePacketVerificationPanel';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('EvidencePacketVerificationPanel', () => {
  it('verifies a WORM-retained packet from the audit console', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse({
        trace_id: 'trace-123',
        verified_at: '2026-05-29T13:00:00Z',
        overall: 'all_match',
        checks: [
          {
            artifact: 'merged_packet_external_anchor',
            expected: 'a'.repeat(64),
            actual: 'a'.repeat(64),
            match: true,
            notes:
              'S3 anchor object was re-read, its manifest commits to this packet hash and hash-log entry, and Object Lock GOVERNANCE retention is active until 2026-06-28T13:00:00Z',
          },
        ],
      }),
    );

    render(
      <EvidencePacketVerificationPanel
        traceId="trace-123"
        authToken="verify-token"
        fetchImpl={fetchImpl}
      />,
    );

    expect(screen.getByText('Not checked')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Verify packet' }));

    expect(await screen.findByText('WORM retained')).toBeInTheDocument();
    expect(screen.getByText(/Object Lock GOVERNANCE retention is active/i)).toBeInTheDocument();
    expect(fetchImpl).toHaveBeenCalledWith('/api/evidence/trace-123/verify', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        Authorization: 'Bearer verify-token',
      },
      signal: undefined,
    });
  });

  it('distinguishes S3 verification without Object Lock retention', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse({
        trace_id: 'trace-123',
        verified_at: '2026-05-29T13:00:00Z',
        overall: 'all_match',
        checks: [
          {
            artifact: 'merged_packet_external_anchor',
            expected: 'a'.repeat(64),
            actual: 'a'.repeat(64),
            match: true,
            notes:
              'S3 anchor object was re-read and its manifest commits to this packet hash and hash-log entry; Object Lock was not requested',
          },
        ],
      }),
    );

    render(
      <EvidencePacketVerificationPanel
        traceId="trace-123"
        authToken="Bearer verify-token"
        fetchImpl={fetchImpl}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Verify packet' }));

    expect(await screen.findByText('S3 verified')).toBeInTheDocument();
    expect(screen.queryByText('WORM retained')).not.toBeInTheDocument();
  });

  it('disables verification honestly without a protected API token', () => {
    render(<EvidencePacketVerificationPanel traceId="trace-123" />);

    expect(screen.getByRole('button', { name: 'Verify packet' })).toBeDisabled();
    expect(screen.getByRole('note')).toHaveTextContent('protected API token');
  });

  it('resets a loaded result when the trace changes', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse({
        trace_id: 'trace-123',
        verified_at: '2026-05-29T13:00:00Z',
        overall: 'all_match',
        checks: [],
      }),
    );
    const { rerender } = render(
      <EvidencePacketVerificationPanel
        traceId="trace-123"
        authToken="verify-token"
        fetchImpl={fetchImpl}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Verify packet' }));
    expect(await screen.findByText('Hashes match')).toBeInTheDocument();

    rerender(
      <EvidencePacketVerificationPanel
        traceId="trace-456"
        authToken="verify-token"
        fetchImpl={fetchImpl}
      />,
    );

    expect(await screen.findByText('Not checked')).toBeInTheDocument();
    expect(screen.getByText('trace_id: trace-456')).toBeInTheDocument();
  });
});
