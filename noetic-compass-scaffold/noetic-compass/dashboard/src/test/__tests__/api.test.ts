import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { apiFetch, ApiError } from '../../api/client';
import { setToken, clearToken, getToken, isAuthenticated } from '../../api/auth';

const server = setupServer();

function makeJwt(payload: Record<string, unknown>): string {
  const encoded = btoa(JSON.stringify(payload))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
  return `header.${encoded}.sig`;
}

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  clearToken();
});
afterAll(() => server.close());

describe('auth', () => {
  it('stores and retrieves token', () => {
    const token = makeJwt({ exp: Math.floor(Date.now() / 1000) + 3600 });
    setToken(token);
    expect(getToken()).toBe(token);
    expect(isAuthenticated()).toBe(true);
  });

  it('clears token', () => {
    setToken(makeJwt({ exp: Math.floor(Date.now() / 1000) + 3600 }));
    clearToken();
    expect(getToken()).toBeNull();
    expect(isAuthenticated()).toBe(false);
  });

  it('treats expired jwt as unauthenticated and clears it', () => {
    setToken(makeJwt({ exp: Math.floor(Date.now() / 1000) - 60 }));
    expect(isAuthenticated()).toBe(false);
    expect(getToken()).toBeNull();
  });
});

describe('apiFetch', () => {
  it('attaches Authorization header', async () => {
    setToken('my-jwt');
    let capturedAuth = '';
    server.use(
      http.get('/api/health', ({ request }) => {
        capturedAuth = request.headers.get('Authorization') ?? '';
        return HttpResponse.json({ status: 'ok' });
      }),
    );
    await apiFetch('/health');
    expect(capturedAuth).toBe('Bearer my-jwt');
  });

  it('throws ApiError on 401', async () => {
    setToken('my-jwt');
    server.use(
      http.post('/api/auth/token', () =>
        HttpResponse.json({ detail: 'Token mint failed' }, { status: 500 }),
      ),
      http.get('/api/config', () =>
        HttpResponse.json({ detail: 'Invalid token', error_type: 'auth_error' }, { status: 401 }),
      ),
    );
    try {
      await apiFetch('/config');
      expect.fail('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const err = e as ApiError;
      expect(err.status).toBe(401);
      expect(err.detail).toBe('Invalid token');
      expect(err.errorType).toBe('auth_error');
      expect(getToken()).toBeNull();
    }
  });

  it('refreshes the dashboard token once when Authorization is missing or invalid', async () => {
    setToken('stale-jwt');
    const authHeaders: string[] = [];
    server.use(
      http.post('/api/auth/token', () => HttpResponse.json({ token: 'fresh-jwt' })),
      http.get('/api/config', ({ request }) => {
        const auth = request.headers.get('Authorization') ?? '';
        authHeaders.push(auth);
        if (auth !== 'Bearer fresh-jwt') {
          return HttpResponse.json(
            { detail: 'Missing or invalid Authorization header', error_type: 'auth_error' },
            { status: 401 },
          );
        }
        return HttpResponse.json({ ok: true });
      }),
    );

    const result = await apiFetch<{ ok: boolean }>('/config');

    expect(result.ok).toBe(true);
    expect(authHeaders).toEqual(['Bearer stale-jwt', 'Bearer fresh-jwt']);
    expect(getToken()).toBe('fresh-jwt');
  });

  it('throws ApiError on 422', async () => {
    server.use(
      http.put('/api/config', () =>
        HttpResponse.json({ detail: 'dial out of range' }, { status: 422 }),
      ),
    );
    try {
      await apiFetch('/config', { method: 'PUT', body: '{}' });
      expect.fail('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(422);
    }
  });

  it('throws a network_error when the backend cannot be reached', async () => {
    server.use(
      http.get('/api/health', () => HttpResponse.error()),
    );
    try {
      await apiFetch('/health');
      expect.fail('Should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const err = e as ApiError;
      expect(err.status).toBe(0);
      expect(err.errorType).toBe('network_error');
      expect(err.detail).toContain('Unable to reach API');
    }
  });

  it('refreshes the dashboard token once when the monthly cap is exhausted', async () => {
    setToken('old-jwt');
    const authHeaders: string[] = [];
    server.use(
      http.post('/api/auth/token', () => HttpResponse.json({ token: 'fresh-jwt' })),
      http.post('/api/notation/compile', ({ request }) => {
        const auth = request.headers.get('Authorization') ?? '';
        authHeaders.push(auth);
        if (auth === 'Bearer old-jwt') {
          return HttpResponse.json(
            { detail: 'Monthly limit exceeded (50 assessments). Upgrade tier or wait until next month.' },
            { status: 429 },
          );
        }
        return HttpResponse.json({ valid: true });
      }),
    );

    const result = await apiFetch<{ valid: boolean }>('/notation/compile', {
      method: 'POST',
      body: JSON.stringify({ expression: 'Phi<3:8:5:2>' }),
    });

    expect(result.valid).toBe(true);
    expect(authHeaders).toEqual(['Bearer old-jwt', 'Bearer fresh-jwt']);
    expect(getToken()).toBe('fresh-jwt');
  });
});
