import { describe, expect, it, vi } from 'vitest';
import { verifyEvidencePacket } from './evidencePacketVerification';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('evidencePacketVerification', () => {
  it('sends the account bearer token when verifying a packet', async () => {
    const fetchMock = vi
      .fn<[RequestInfo | URL, RequestInit | undefined], Promise<Response>>()
      .mockResolvedValueOnce(jsonResponse({
        trace_id: 'trace-1',
        verified_at: '2026-06-09T00:00:00Z',
        overall: 'all_match',
        checks: [],
      }));

    await verifyEvidencePacket(' trace-1 ', {
      authToken: 'jwt-123',
      fetchImpl: fetchMock as unknown as typeof fetch,
    });

    expect(fetchMock).toHaveBeenCalledWith('/api/evidence/trace-1/verify', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        Authorization: 'Bearer jwt-123',
      },
      signal: undefined,
    });
  });
});
