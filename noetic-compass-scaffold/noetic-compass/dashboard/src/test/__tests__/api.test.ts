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
});
