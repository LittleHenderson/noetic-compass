import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  CasHarnessAuditApiError,
  createCasHarnessAuditSession,
  getCasHarnessAuditSessionStatus,
  listCasHarnessAuditSessions,
  parseAuditSessionResponse,
  resolveCasHarnessAuditBaseUrl,
  startCasHarnessAuditSession,
} from './casHarnessAuditApi';

function jsonResponse(
  body: unknown,
  status = 200,
  statusText?: string,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    statusText,
    headers: { 'Content-Type': 'application/json' },
  });
}

function pendingSession(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    audit_id: 'cas-audit-unit',
    status: 'SCAFFOLD_PENDING_RUNNER',
    model_status: 'NOT_CONNECTED_MOCK',
    model_id: 'EleutherAI/pythia-160m',
    endpoint_url: null,
    audit_mode: 'BALANCED',
    prompt_summary: null,
    scenario_summary: 'Audit this output.',
    selected_modules: ['model_proof', 'cas_readout'],
    created_at: '2026-05-25T11:00:00Z',
    updated_at: '2026-05-25T11:00:00Z',
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: null,
    atlas_deep_link: null,
    provenance_chips: [
      {
        id: 'model_proof',
        name: 'Model proof',
        status: 'missing',
        detail: 'No model proof has been verified for this audit session yet.',
      },
      {
        id: 'packet_proof',
        name: 'Packet proof',
        status: 'missing',
        detail: 'No Evidence Packet has been attached.',
      },
    ],
    lifecycle: [
      {
        status: 'DRAFT',
        message: 'Audit session created.',
        timestamp: '2026-05-25T11:00:00Z',
      },
    ],
    ...overrides,
  };
}

describe('casHarnessAuditApi', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('creates an audit session with the expected URL, method, headers, and body', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(pendingSession()));
    const payload = {
      model_id: 'EleutherAI/pythia-160m',
      audit_mode: 'BALANCED' as const,
      prompt: 'Audit this answer.',
      selected_modules: ['foundation_probe', 'verification_stack'],
      license_key: 'license-test',
    };

    const session = await createCasHarnessAuditSession(payload, {
      baseUrl: '/api/cas-harness/audit/',
      fetchImpl,
    });

    expect(session.audit_id).toBe('cas-audit-unit');
    expect(session.model_id).toBe('EleutherAI/pythia-160m');
    expect(session.audit_mode).toBe('BALANCED');
    expect(session.selected_modules).toEqual(['model_proof', 'cas_readout']);
    expect(session.lifecycle[0]?.status).toBe('DRAFT');
    expect(session.provenance_chips[0]).toMatchObject({
      id: 'model_proof',
      status: 'missing',
      statusLabel: 'Missing',
    });
    expect(session.verdict).toBeNull();
    expect(session.confidence).toBeNull();
    expect(session.verifier_decision).toBeNull();
    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('/api/cas-harness/audit/session');
    expect(init).toMatchObject({
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });
    expect(JSON.parse(String((init as RequestInit).body))).toEqual(payload);
  });

  it('gets session status with an encoded audit id', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(pendingSession({ audit_id: 'id/with spaces' })));

    const session = await getCasHarnessAuditSessionStatus('id/with spaces', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });

    expect(session.audit_id).toBe('id/with spaces');
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('/api/cas-harness/audit/session/id%2Fwith%20spaces/status');
    expect(init).toMatchObject({
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
  });

  it('lists sessions when the backend exposes the sessions endpoint', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ sessions: [pendingSession(), pendingSession({ audit_id: 'cas-audit-two' })] }),
    );

    const result = await listCasHarnessAuditSessions({
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });

    expect(result.sessions.map((session) => session.audit_id)).toEqual([
      'cas-audit-unit',
      'cas-audit-two',
    ]);
    expect(fetchImpl.mock.calls[0][0]).toBe('/api/cas-harness/audit/sessions');
    expect(fetchImpl.mock.calls[0][1]).toMatchObject({ method: 'GET' });
  });

  it('starts a session when the backend exposes the run endpoint', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(pendingSession({ status: 'RUNNING' })));

    const result = await startCasHarnessAuditSession('cas-audit-unit', {
      baseUrl: '/api/cas-harness/audit',
      fetchImpl,
    });

    expect(result.status).toBe('RUNNING');
    expect(fetchImpl.mock.calls[0][0]).toBe('/api/cas-harness/audit/session/cas-audit-unit/run');
    expect(fetchImpl.mock.calls[0][1]).toMatchObject({ method: 'POST' });
  });

  it('turns non-OK backend responses into useful API errors', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ detail: 'Either model_id or endpoint_url is required' }, 422),
    );

    await expect(
      createCasHarnessAuditSession(
        { prompt: 'x', selected_modules: ['verification_stack'] },
        { fetchImpl },
      ),
    ).rejects.toMatchObject({
      name: 'CasHarnessAuditApiError',
      httpStatus: 422,
      detail: 'Either model_id or endpoint_url is required',
      message: expect.stringContaining('Either model_id or endpoint_url is required'),
    });
  });

  it('preserves null verdict and confidence instead of fabricating result values', () => {
    const parsed = parseAuditSessionResponse(pendingSession({
      verdict: null,
      confidence: null,
    }));

    expect(parsed.verdict).toBeNull();
    expect(parsed.confidence).toBeNull();
  });

  it('treats missing verdict and confidence as null, not as ACCEPT or zero', () => {
    const raw = pendingSession();
    delete raw.verdict;
    delete raw.confidence;

    const parsed = parseAuditSessionResponse(raw);

    expect(parsed.verdict).toBeNull();
    expect(parsed.confidence).toBeNull();
  });

  it('validates known session status vocabulary', () => {
    expect(parseAuditSessionResponse(pendingSession({ status: 'COMPLETE' })).status).toBe('COMPLETE');
    expect(parseAuditSessionResponse(pendingSession({ status: 'EVIDENCE_PENDING' })).status).toBe('EVIDENCE_PENDING');
    expect(() => parseAuditSessionResponse(pendingSession({ status: 'DONE_ENOUGH' }))).toThrow(
      /Unsupported CAS Harness audit status/,
    );
  });

  it('validates known verdict vocabulary and rejects unknown verdicts', () => {
    expect(parseAuditSessionResponse(pendingSession({
      status: 'COMPLETE',
      verdict: 'FLAG_FOR_HUMAN_REVIEW',
      confidence: 0.77,
    })).verdict).toBe('FLAG_FOR_HUMAN_REVIEW');
    expect(() => parseAuditSessionResponse(pendingSession({
      verdict: 'ALLOW',
      confidence: 0.9,
    }))).toThrow(/Unsupported CAS Harness audit verdict/);
  });

  it('parses explicit verifier decision reason and source for UI explanation', () => {
    const parsed = parseAuditSessionResponse(pendingSession({
      status: 'COMPLETE',
      verdict: 'ACCEPT',
      confidence: 0.9816,
      verifier_decision: {
        verdict: 'ACCEPT',
        confidence: 0.9816,
        source: 'stage19_verification_stack+stage20_generation_readiness',
        reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
      },
    }));

    expect(parsed.verifier_decision).toEqual({
      verdict: 'ACCEPT',
      confidence: 0.9816,
      source: 'stage19_verification_stack+stage20_generation_readiness',
      reason: 'Stage 19 accepted the row and Stage 20 readiness action is allow.',
    });
  });

  it('rejects malformed verifier decision instead of inventing explanation text', () => {
    expect(() => parseAuditSessionResponse(pendingSession({
      verifier_decision: {
        verdict: 'ACCEPT',
        confidence: null,
        source: 'stage19',
        reason: 'missing confidence',
      },
    }))).toThrow(/verifier decision confidence is required/);
  });

  it('rejects invalid confidence instead of coercing it', () => {
    expect(() => parseAuditSessionResponse(pendingSession({ confidence: '0.9' }))).toThrow(
      /confidence must be null or a number/,
    );
    expect(() => parseAuditSessionResponse(pendingSession({ confidence: 1.5 }))).toThrow(
      /confidence must be null or a number/,
    );
  });

  it('derives the audit API URL from the Atlas API env var used by hosted builds', () => {
    vi.stubEnv('VITE_ATLAS_API_BASE_URL', 'https://noetic-compass-api.onrender.com/atlas');

    expect(resolveCasHarnessAuditBaseUrl()).toBe(
      'https://noetic-compass-api.onrender.com/api/cas-harness/audit',
    );
  });

  it('does not call fetch for empty audit ids', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(pendingSession()));

    await expect(
      getCasHarnessAuditSessionStatus('  ', { fetchImpl }),
    ).rejects.toBeInstanceOf(CasHarnessAuditApiError);
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});
