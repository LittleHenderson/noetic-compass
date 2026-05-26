import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  CasHarnessAuditApiError,
  createCasHarnessAuditSession,
  getCasHarnessAuditSessionStatus,
  listCasHarnessAuditSessions,
  parseAuditSessionResponse,
  parseModelTargetVerificationResponse,
  resolveCasHarnessAuditBaseUrl,
  startCasHarnessAuditSession,
  verifyCasHarnessModelTarget,
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

function targetVerification(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    connection_id: 'cas-target-demo',
    connection_state: 'CONNECTED',
    model_status: 'CONNECTED',
    can_run_audit: true,
    target: {
      kind: 'demo_reference',
      provider: 'cas_harness_reference',
      model_id: 'EleutherAI/pythia-160m',
      endpoint_url: null,
      credential_mode: 'none',
      timeout_ms: 10000,
    },
    detail:
      'CAS Harness reference target verified locally. No verdict was created.',
    checked_at: '2026-05-26T10:00:00Z',
    provenance_chip: {
      id: 'model_proof',
      name: 'Model proof',
      status: 'verified',
      detail: 'Reference target verified for target connection only.',
    },
    verdict: null,
    confidence: null,
    evidence_packet_trace_id: null,
    reference_evidence_packet_trace_id: 'cas_harness_reference_accept_001',
    atlas_deep_link: null,
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

  it('verifies the built-in demo reference target without fabricating a verdict', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(targetVerification()));

    const result = await verifyCasHarnessModelTarget(
      { target: { kind: 'demo_reference' } },
      {
        baseUrl: '/api/cas-harness/audit/',
        fetchImpl,
      },
    );

    expect(result.connection_id).toBe('cas-target-demo');
    expect(result.connection_state).toBe('CONNECTED');
    expect(result.model_status).toBe('CONNECTED');
    expect(result.target).toMatchObject({
      kind: 'demo_reference',
      model_id: 'EleutherAI/pythia-160m',
      credential_mode: 'none',
    });
    expect(result.verdict).toBeNull();
    expect(result.confidence).toBeNull();
    expect(result.reference_evidence_packet_trace_id).toBe(
      'cas_harness_reference_accept_001',
    );
    expect(result.provenance_chip).toMatchObject({
      id: 'model_proof',
      status: 'verified',
      statusLabel: 'Verified',
    });
    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('/api/cas-harness/audit/target/verify');
    expect(init).toMatchObject({
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });
    expect(JSON.parse(String((init as RequestInit).body))).toEqual({
      target: { kind: 'demo_reference' },
    });
  });

  it('verifies an API endpoint target using a credential reference', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(targetVerification({
        connection_id: 'cas-target-api',
        connection_state: 'CONFIGURED',
        model_status: 'READY',
        target: {
          kind: 'api_endpoint',
          provider: 'customer_gateway',
          model_id: 'customer/model-a',
          endpoint_url: 'https://models.example/v1/chat/completions',
          credential_mode: 'credential_ref',
          timeout_ms: 15000,
        },
        provenance_chip: {
          id: 'model_proof',
          name: 'Model proof',
          status: 'present',
          detail: 'Endpoint target configuration passed schema validation.',
        },
        reference_evidence_packet_trace_id: null,
      })),
    );

    const result = await verifyCasHarnessModelTarget(
      {
        target: {
          kind: 'api_endpoint',
          provider: 'customer_gateway',
          model_id: 'customer/model-a',
          endpoint_url: 'https://models.example/v1/chat/completions',
          credential_ref: 'cred_live_customer_model_a',
          timeout_ms: 15000,
        },
      },
      { baseUrl: '/api/cas-harness/audit', fetchImpl },
    );

    expect(result.connection_id).toBe('cas-target-api');
    expect(result.connection_state).toBe('CONFIGURED');
    expect(result.model_status).toBe('READY');
    expect(result.target).toEqual({
      kind: 'api_endpoint',
      provider: 'customer_gateway',
      model_id: 'customer/model-a',
      endpoint_url: 'https://models.example/v1/chat/completions',
      credential_mode: 'credential_ref',
      timeout_ms: 15000,
    });
    expect(result.provenance_chip.status).toBe('present');
    expect(result.verdict).toBeNull();
    expect(result.confidence).toBeNull();
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

  it('rejects target verification responses that pretend to include a verdict or confidence', () => {
    expect(() => parseModelTargetVerificationResponse(targetVerification({
      verdict: 'ACCEPT',
      confidence: null,
    }))).toThrow(/target verification must not return a verdict/);

    expect(() => parseModelTargetVerificationResponse(targetVerification({
      verdict: null,
      confidence: 0.88,
    }))).toThrow(/target verification must not return confidence/);
  });

  it('rejects malformed target verification payloads', () => {
    expect(() => parseModelTargetVerificationResponse(targetVerification({
      target: {
        kind: 'api_endpoint',
        provider: 'customer_gateway',
        model_id: 'customer/model-a',
        endpoint_url: 'https://models.example/v1/chat/completions',
        credential_mode: 'raw_key_echoed',
        timeout_ms: 15000,
      },
    }))).toThrow(/Unsupported CAS Harness credential mode/);

    expect(() => parseModelTargetVerificationResponse(targetVerification({
      can_run_audit: 'yes',
    }))).toThrow(/can_run_audit must be boolean/);
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

  it('uses the derived hosted audit API URL for target verification', async () => {
    vi.stubEnv('VITE_ATLAS_API_BASE_URL', 'https://noetic-compass-api.onrender.com/atlas');
    const fetchImpl = vi.fn(async () => jsonResponse(targetVerification()));

    await verifyCasHarnessModelTarget(
      { target: { kind: 'demo_reference' } },
      { fetchImpl },
    );

    expect(fetchImpl.mock.calls[0][0]).toBe(
      'https://noetic-compass-api.onrender.com/api/cas-harness/audit/target/verify',
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
