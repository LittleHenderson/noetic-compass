import type { SpatialEvidenceArtifact } from './visualPrimitives';
import { loadSpatialEvidenceArtifact } from './visualPrimitives';

export interface VisualGroundingApiOptions {
  baseUrl?: string;
  fixtureLoader?: () => Promise<SpatialEvidenceArtifact | null>;
  fetchImpl?: typeof fetch;
  signal?: AbortSignal;
}

const DEFAULT_BASE_URL = '/api/atlas';

function trimTrailingSlash(url: string): string {
  return url.endsWith('/') ? url.slice(0, -1) : url;
}

async function runFixtureFallback(
  loader: (() => Promise<SpatialEvidenceArtifact | null>) | undefined,
  reason: string,
): Promise<SpatialEvidenceArtifact> {
  if (!loader) {
    throw new Error(`no spatial evidence available: ${reason}`);
  }
  const fallback = await loader();
  if (fallback === null || fallback === undefined) {
    throw new Error(`no spatial evidence available: ${reason}`);
  }
  return fallback;
}

export async function fetchSpatialEvidence(
  traceId: string,
  options?: VisualGroundingApiOptions,
): Promise<SpatialEvidenceArtifact> {
  if (typeof traceId !== 'string' || traceId.length === 0) {
    throw new Error('fetchSpatialEvidence: traceId must be a non-empty string');
  }

  const baseUrl = trimTrailingSlash(options?.baseUrl ?? DEFAULT_BASE_URL);
  const fetchImpl = options?.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  if (!fetchImpl) {
    return runFixtureFallback(options?.fixtureLoader, 'fetch is not available in this runtime');
  }

  const url = `${baseUrl}/visual-grounding/${encodeURIComponent(traceId)}`;

  let response: Response;
  try {
    response = await fetchImpl(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: options?.signal,
    });
  } catch (err) {
    const reason = err instanceof Error ? err.message : 'network error';
    return runFixtureFallback(options?.fixtureLoader, reason);
  }

  if (response.status === 404) {
    return runFixtureFallback(options?.fixtureLoader, `backend returned 404 for trace_id "${traceId}"`);
  }

  if (!response.ok) {
    return runFixtureFallback(
      options?.fixtureLoader,
      `backend returned HTTP ${response.status}`,
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch (err) {
    const reason = err instanceof Error ? err.message : 'invalid JSON';
    return runFixtureFallback(options?.fixtureLoader, `response JSON parse failed: ${reason}`);
  }

  return loadSpatialEvidenceArtifact(body);
}

export function createDemoFixtureLoader(): () => Promise<SpatialEvidenceArtifact> {
  return async () => {
    const [demoJsonMod, demoImageMod] = await Promise.all([
      import('../fixtures/visualGroundingDemo.json'),
      import('../fixtures/visualGroundingDemoImage.svg?url'),
    ]);
    const raw = (demoJsonMod as { default?: unknown }).default ?? demoJsonMod;
    const imageUrl =
      (demoImageMod as { default?: string }).default ??
      (demoImageMod as unknown as string);
    const rawObj = raw as Record<string, unknown>;
    return loadSpatialEvidenceArtifact({ ...rawObj, image_url: imageUrl });
  };
}
