import { describe, expect, it, vi } from 'vitest';
import { askExplainer, askExplainerForPacket } from './explainerApi';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('explainerApi', () => {
  it('sends the account bearer token to Guide chat', async () => {
    const fetchMock = vi
      .fn<[RequestInfo | URL, RequestInit | undefined], Promise<Response>>()
      .mockResolvedValueOnce(jsonResponse({
        answer: 'Run the audit.',
        sources: ['guide.md'],
        used_gemini: false,
        model: 'mock',
        safety_mode: 'public_guide_only',
      }));

    await askExplainer('How do I run an audit?', {
      authToken: 'jwt-123',
      fetchImpl: fetchMock as unknown as typeof fetch,
    });

    expect(fetchMock).toHaveBeenCalledWith('/api/explainer/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer jwt-123',
      },
      body: JSON.stringify({ question: 'How do I run an audit?' }),
    });
  });

  it('sends the account bearer token to packet explanations', async () => {
    const fetchMock = vi
      .fn<[RequestInfo | URL, RequestInit | undefined], Promise<Response>>()
      .mockResolvedValueOnce(jsonResponse({
        trace_id: 'trace-1',
        verdict_echo: 'FLAG_FOR_HUMAN_REVIEW',
        segments: [],
        investigate_next: [],
        used_gemini: false,
        model: 'mock',
        safety_mode: 'packet_projection_only',
        disclaimer: 'Read the packet.',
      }));

    await askExplainerForPacket(' trace-1 ', {
      authToken: 'Bearer account-token',
      fetchImpl: fetchMock as unknown as typeof fetch,
    });

    expect(fetchMock).toHaveBeenCalledWith('/api/explainer/evidence/trace-1', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer account-token',
      },
    });
  });

  it('fails closed without an account token', async () => {
    await expect(
      askExplainer('What is CAS?', {
        fetchImpl: vi.fn() as unknown as typeof fetch,
      }),
    ).rejects.toThrow('Account session is required');
  });
});
