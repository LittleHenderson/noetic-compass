import { describe, expect, it, vi } from 'vitest';

import type { SpatialEvidenceArtifact } from './visualPrimitives';
import {
  createDemoFixtureLoader,
  fetchSpatialEvidence,
} from './visualGroundingApi';

const VALID_ARTIFACT: SpatialEvidenceArtifact = {
  schema_version: 'spatial_evidence_v1',
  trace_id: 'unit-trace-001',
  image_id: 'unit-image-001',
  image_url: '/fixtures/unit.svg',
  image_width: 100,
  image_height: 50,
  primitives: [
    {
      id: 'vp-a',
      kind: 'point',
      image_id: 'unit-image-001',
      coords_norm: [0.5, 0.5],
      source: 'fixture',
    },
  ],
  grounded_steps: [
    {
      trace_id: 'unit-trace-001',
      step_id: 'step-a',
      primitive_ids: ['vp-a'],
    },
  ],
};

function jsonResponse(body: unknown, init: { status?: number } = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('fetchSpatialEvidence', () => {
  it('returns the parsed artifact on a 200 + valid JSON response', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(VALID_ARTIFACT));
    const result = await fetchSpatialEvidence('unit-trace-001', { fetchImpl });
    expect(result.trace_id).toBe('unit-trace-001');
    expect(result.primitives).toHaveLength(1);
    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('/api/atlas/visual-grounding/unit-trace-001');
    expect((init as RequestInit | undefined)?.headers).toMatchObject({
      Accept: 'application/json',
    });
  });

  it('honors a custom baseUrl and strips trailing slash', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(VALID_ARTIFACT));
    await fetchSpatialEvidence('unit-trace-001', {
      fetchImpl,
      baseUrl: 'https://atlas.example.com/api/atlas/',
    });
    const [url] = fetchImpl.mock.calls[0];
    expect(url).toBe('https://atlas.example.com/api/atlas/visual-grounding/unit-trace-001');
  });

  it('falls back to fixtureLoader on a 404 response', async () => {
    const fetchImpl = vi.fn(async () => new Response('not found', { status: 404 }));
    const fixtureLoader = vi.fn(async () => VALID_ARTIFACT);
    const result = await fetchSpatialEvidence('missing-trace', { fetchImpl, fixtureLoader });
    expect(fixtureLoader).toHaveBeenCalledOnce();
    expect(result.trace_id).toBe('unit-trace-001');
  });

  it('falls back to fixtureLoader on a network error', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error('connection refused');
    });
    const fixtureLoader = vi.fn(async () => VALID_ARTIFACT);
    const result = await fetchSpatialEvidence('any-trace', { fetchImpl, fixtureLoader });
    expect(fixtureLoader).toHaveBeenCalledOnce();
    expect(result.image_id).toBe('unit-image-001');
  });

  it('throws "no spatial evidence available" on network error without fixtureLoader', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error('offline');
    });
    await expect(fetchSpatialEvidence('any-trace', { fetchImpl })).rejects.toThrow(
      /no spatial evidence available/,
    );
  });

  it('throws "no spatial evidence available" when fixtureLoader returns null on 404', async () => {
    const fetchImpl = vi.fn(async () => new Response('not found', { status: 404 }));
    const fixtureLoader = vi.fn(async () => null);
    await expect(
      fetchSpatialEvidence('missing-trace', { fetchImpl, fixtureLoader }),
    ).rejects.toThrow(/no spatial evidence available/);
  });

  it('throws a schema-validation error when the response body is malformed', async () => {
    const badBody = { schema_version: 'spatial_evidence_v1', trace_id: 'x' };
    const fetchImpl = vi.fn(async () => jsonResponse(badBody));
    await expect(fetchSpatialEvidence('x', { fetchImpl })).rejects.toThrow(
      /loadSpatialEvidenceArtifact/,
    );
  });

  it('rejects an empty traceId', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(VALID_ARTIFACT));
    await expect(fetchSpatialEvidence('', { fetchImpl })).rejects.toThrow(/traceId/);
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('passes the AbortSignal through to fetch', async () => {
    const controller = new AbortController();
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(init?.signal).toBe(controller.signal);
      return jsonResponse(VALID_ARTIFACT);
    });
    await fetchSpatialEvidence('unit-trace-001', { fetchImpl, signal: controller.signal });
    expect(fetchImpl).toHaveBeenCalledOnce();
  });
});

describe('createDemoFixtureLoader', () => {
  it('loads and validates the bundled demo fixture', async () => {
    const loader = createDemoFixtureLoader();
    const artifact = await loader();
    expect(artifact.schema_version).toBe('spatial_evidence_v1');
    expect(artifact.trace_id).toBe('demo-trace-001');
    expect(artifact.primitives.length).toBeGreaterThan(0);
    expect(artifact.grounded_steps.length).toBeGreaterThan(0);
  });
});
