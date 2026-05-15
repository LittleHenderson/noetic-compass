import {
  describe,
  it,
  expect,
  beforeAll,
  afterAll,
  afterEach,
} from 'vitest';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { ApiError } from '../api/client';
import { clearToken, setToken } from '../api/auth';
import {
  fetchEvidencePacket,
  verifyEvidenceHashes,
  type EvidencePacket,
  type VerifyHashesResponse,
} from './evidence_packet';

const server = setupServer();

function makeJwt(payload: Record<string, unknown>): string {
  const encoded = btoa(JSON.stringify(payload))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
  return `header.${encoded}.sig`;
}

function freshToken(): string {
  return makeJwt({ exp: Math.floor(Date.now() / 1000) + 3600 });
}

function fixturePacket(traceId: string): EvidencePacket {
  return {
    schema_version: 'evidence_packet.v1',
    trace_id: traceId,
    generated_at: '2026-05-15T12:00:00Z',
    input: { text: 'hello cas', user_id: 'demo-user', session_id: 'sess-1' },
    cas_expression: {
      text: '^2^P|A',
      compiler_valid: true,
      grammar_category: 'state',
    },
    output: { text: 'a reply', n_tokens: 12, max_new_tokens: 96 },
    copy_slot_trace: [
      {
        role: 'noetic',
        name: '^2',
        copied: true,
        source_token_index: 3,
        target_token_index: 11,
        claim_level: 'source_copy_evidence',
      },
    ],
    provenance: {
      model_checkpoint_id: 'ckpt_v1_step42',
      checkpoint_label: 'v1-step42',
      code_commit_sha: 'a'.repeat(40),
      code_commit_summary: 'feat: evidence packet',
      run_command: 'python train.py --foo bar',
      config_snapshot: { lr: 0.001 },
    },
    hashes: {
      weights_sha: 'b'.repeat(64),
      tokenizer_hash: 'c'.repeat(64),
      english_bpe_hash: 'd'.repeat(64),
      corpus_sha256: 'e'.repeat(64),
      on_disk_paths: {
        weights_path: '/srv/ckpts/v1_step42.pt',
        tokenizer_path: '/srv/tok/v1c.json',
        corpus_path: '/srv/data/wave3_step2_5.jsonl',
      },
    },
    claim_levels: [
      {
        claim: 'CAS expression compiles',
        level: 'cas_hard_trace',
        rationale: 'Direct call to compile().',
      },
      {
        claim: 'Identifier copy from input to output',
        level: 'source_copy_evidence',
        rationale: 'Pointer evidence over tokens 3 -> 11.',
      },
      {
        claim: 'Attention head 4 attends to user_id',
        level: 'neural_attribution_estimate',
        rationale: 'Probe over RandomBatch sample.',
      },
    ],
    caveats: ['Mode 7 attribution is an estimate, not a proof.'],
  };
}

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  clearToken();
});
afterAll(() => server.close());

describe('fetchEvidencePacket', () => {
  it('calls GET /api/evidence/{traceId} and returns the parsed packet', async () => {
    setToken(freshToken());
    const traceId = 'trace-abc-123';
    let capturedAuth = '';
    server.use(
      http.get(`/api/evidence/${traceId}`, ({ request }) => {
        capturedAuth = request.headers.get('Authorization') ?? '';
        return HttpResponse.json(fixturePacket(traceId));
      }),
    );
    const packet = await fetchEvidencePacket(traceId);
    expect(packet.trace_id).toBe(traceId);
    expect(packet.schema_version).toBe('evidence_packet.v1');
    expect(packet.claim_levels).toHaveLength(3);
    expect(capturedAuth).toMatch(/^Bearer /);
  });

  it('url-encodes trace IDs with slashes / special chars', async () => {
    setToken(freshToken());
    const traceId = 'trace/with spaces';
    let capturedPath = '';
    server.use(
      http.get('/api/evidence/:encoded', ({ params, request }) => {
        capturedPath = new URL(request.url).pathname;
        const encoded = String(params.encoded);
        return HttpResponse.json({
          ...fixturePacket(decodeURIComponent(encoded)),
        });
      }),
    );
    const packet = await fetchEvidencePacket(traceId);
    expect(packet.trace_id).toBe(traceId);
    expect(capturedPath).toContain(encodeURIComponent(traceId));
  });

  it('surfaces ApiError on 404', async () => {
    setToken(freshToken());
    server.use(
      http.get('/api/evidence/missing', () =>
        HttpResponse.json(
          { detail: 'No such trace_id', error_type: 'not_found' },
          { status: 404 },
        ),
      ),
    );
    try {
      await fetchEvidencePacket('missing');
      expect.fail('should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(404);
      expect(apiErr.detail).toBe('No such trace_id');
      expect(apiErr.errorType).toBe('not_found');
    }
  });

  it('surfaces ApiError on 500', async () => {
    setToken(freshToken());
    server.use(
      http.get('/api/evidence/boom', () =>
        HttpResponse.json({ detail: 'internal error' }, { status: 500 }),
      ),
    );
    try {
      await fetchEvidencePacket('boom');
      expect.fail('should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(500);
    }
  });
});

describe('verifyEvidenceHashes', () => {
  it('calls POST /api/evidence/{traceId}/verify and returns the result', async () => {
    setToken(freshToken());
    const traceId = 'trace-abc-123';
    const fixture: VerifyHashesResponse = {
      trace_id: traceId,
      verified_at: '2026-05-15T12:05:00Z',
      checks: [
        {
          artifact: 'Weights',
          expected: 'b'.repeat(64),
          actual: 'b'.repeat(64),
          match: true,
        },
        {
          artifact: 'Tokenizer',
          expected: 'c'.repeat(64),
          actual: 'c'.repeat(64),
          match: true,
        },
      ],
      overall: 'all_match',
    };
    let capturedMethod = '';
    server.use(
      http.post(`/api/evidence/${traceId}/verify`, ({ request }) => {
        capturedMethod = request.method;
        return HttpResponse.json(fixture);
      }),
    );
    const result = await verifyEvidenceHashes(traceId);
    expect(result.overall).toBe('all_match');
    expect(result.checks).toHaveLength(2);
    expect(capturedMethod).toBe('POST');
  });

  it('parses partial_mismatch result correctly', async () => {
    setToken(freshToken());
    server.use(
      http.post('/api/evidence/t1/verify', () =>
        HttpResponse.json({
          trace_id: 't1',
          verified_at: '2026-05-15T12:05:00Z',
          checks: [
            {
              artifact: 'Weights',
              expected: 'a'.repeat(64),
              actual: 'z'.repeat(64),
              match: false,
              notes: 'changed since this trace',
            },
            {
              artifact: 'Tokenizer',
              expected: 'b'.repeat(64),
              actual: 'b'.repeat(64),
              match: true,
            },
          ],
          overall: 'partial_mismatch',
        }),
      ),
    );
    const result = await verifyEvidenceHashes('t1');
    expect(result.overall).toBe('partial_mismatch');
    expect(result.checks[0].match).toBe(false);
    expect(result.checks[0].notes).toBe('changed since this trace');
  });

  it('surfaces ApiError on 422', async () => {
    setToken(freshToken());
    server.use(
      http.post('/api/evidence/badtrace/verify', () =>
        HttpResponse.json(
          { detail: 'Trace not verifiable', error_type: 'validation_error' },
          { status: 422 },
        ),
      ),
    );
    try {
      await verifyEvidenceHashes('badtrace');
      expect.fail('should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(422);
      expect((err as ApiError).errorType).toBe('validation_error');
    }
  });

  it('surfaces ApiError on 503', async () => {
    setToken(freshToken());
    server.use(
      http.post('/api/evidence/t2/verify', () =>
        HttpResponse.json(
          { detail: 'Verifier offline' },
          { status: 503 },
        ),
      ),
    );
    try {
      await verifyEvidenceHashes('t2');
      expect.fail('should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(503);
    }
  });
});
