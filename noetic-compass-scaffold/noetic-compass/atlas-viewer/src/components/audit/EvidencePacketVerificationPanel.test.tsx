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
  it('verifies an Object Lock retained packet from the audit console', async () => {
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

    render(<EvidencePacketVerificationPanel traceId="trace-123" fetchImpl={fetchImpl} />);

    expect(screen.getByText('Not checked')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Verify packet' }));

    expect(await screen.findByText('Object Lock GOVERNANCE')).toBeInTheDocument();
    expect(screen.getByText(/Object Lock GOVERNANCE retention is active/i)).toBeInTheDocument();
    expect(fetchImpl).toHaveBeenCalledWith('/api/evidence/trace-123/verify', {
      method: 'POST',
      headers: { Accept: 'application/json' },
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

    render(<EvidencePacketVerificationPanel traceId="trace-123" fetchImpl={fetchImpl} />);
    fireEvent.click(screen.getByRole('button', { name: 'Verify packet' }));

    expect(await screen.findByText('S3 verified')).toBeInTheDocument();
    expect(screen.queryByText('Object Lock GOVERNANCE')).not.toBeInTheDocument();
  });
});
