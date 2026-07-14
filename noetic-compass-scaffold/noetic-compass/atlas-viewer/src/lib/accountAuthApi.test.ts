import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  AccountAuthApiError,
  decodeAccountToken,
  fetchPublicAccountCapabilities,
  generateAccountCredential,
  loginAccount,
  redeemAccountInvite,
  resolveAccountApiBaseUrl,
  resolveAccountCapabilityUrl,
  rotateOwnAccountCredential,
} from './accountAuthApi';

function segment(value: unknown): string {
  return btoa(JSON.stringify(value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function accountToken(overrides: Record<string, unknown> = {}): string {
  return `${segment({ alg: 'HS256', typ: 'JWT' })}.${segment({
    sub: 'owner@example.com',
    account_id: 'acct-1',
    tenant_id: 'tenant-1',
    role: 'owner',
    jti: 'session-1',
    exp: Math.floor(Date.now() / 1000) + 3600,
    ...overrides,
  })}.signature`;
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe('accountAuthApi', () => {
  it('generates the backend casak_ credential shape from 256 random bits', () => {
    const getRandomValues = vi.fn((bytes: Uint8Array) => {
      bytes.forEach((_, index) => { bytes[index] = index; });
      return bytes;
    });
    const credential = generateAccountCredential({ getRandomValues } as unknown as Crypto);

    expect(getRandomValues).toHaveBeenCalledOnce();
    expect(credential).toMatch(/^casak_[A-Za-z0-9_-]{43}$/);
    expect(credential).toHaveLength(49);
  });

  it('fails closed when secure random generation is unavailable', () => {
    expect(() => generateAccountCredential({} as Crypto)).toThrow(AccountAuthApiError);
  });

  it('derives account root URLs from the Atlas API configuration', () => {
    vi.stubEnv('VITE_ATLAS_API_BASE_URL', 'https://noetic-compass-api.onrender.com/atlas');
    expect(resolveAccountApiBaseUrl()).toBe('https://noetic-compass-api.onrender.com');
    expect(resolveAccountCapabilityUrl()).toBe(
      'https://noetic-compass-api.onrender.com/public/capabilities',
    );
    expect(resolveAccountApiBaseUrl('https://api.example.test/root/')).toBe('https://api.example.test/root');
    expect(resolveAccountCapabilityUrl('/api')).toBe('/api/public/capabilities');
  });

  it('fetches the exact anonymous capability contract without browser credentials', async () => {
    const fetchImpl = vi.fn(async () => new Response(
      JSON.stringify({ accounts_enabled: true }),
      {
        status: 200,
        headers: {
          'Cache-Control': 'private, no-store, max-age=0',
          'Content-Type': 'application/json; charset=utf-8',
        },
      },
    ));

    await expect(fetchPublicAccountCapabilities({
      baseUrl: 'https://api.example.test',
      fetchImpl,
    })).resolves.toEqual({ accounts_enabled: true });

    expect(fetchImpl).toHaveBeenCalledWith(
      'https://api.example.test/public/capabilities',
      expect.objectContaining({
        method: 'GET',
        cache: 'no-store',
        credentials: 'omit',
        redirect: 'error',
        referrerPolicy: 'no-referrer',
      }),
    );
    const init = fetchImpl.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get('Authorization')).toBeNull();
  });

  it.each([
    ['scheme-relative', '//evil.example'],
    ['credentialed', 'https://user:secret@api.example.test'],
    ['query-bearing', 'https://api.example.test?tenant=one'],
    ['fragment-bearing', 'https://api.example.test#capabilities'],
    ['non-network scheme', 'data:application/json,{}'],
    ['route-relative', 'api'],
  ])('rejects a %s capability base before fetch', async (_label, baseUrl) => {
    const fetchImpl = vi.fn();

    await expect(fetchPublicAccountCapabilities({ baseUrl, fetchImpl }))
      .rejects.toThrow('Account API base URL is invalid.');
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it.each([
    ['extra field', '{"accounts_enabled":true,"provider":"stripe"}', 'application/json', undefined],
    ['duplicate field', '{"accounts_enabled":false,"accounts_enabled":true}', 'application/json', undefined],
    ['string boolean', '{"accounts_enabled":"true"}', 'application/json', undefined],
    ['wrong content type', '{"accounts_enabled":true}', 'text/html', undefined],
    ['missing no-store', '{"accounts_enabled":true}', 'application/json', undefined],
    ['oversized declared body', '{"accounts_enabled":true}', 'application/json', '300'],
    ['oversized actual body', `{"accounts_enabled":true}${' '.repeat(300)}`, 'application/json', undefined],
  ])('fails closed on a capability response with %s', async (
    _label,
    body,
    contentType,
    contentLength,
  ) => {
    const headers = new Headers({ 'Content-Type': contentType });
    if (_label !== 'missing no-store') headers.set('Cache-Control', 'no-store');
    if (contentLength) headers.set('Content-Length', contentLength);
    const fetchImpl = vi.fn(async () => new Response(body, { status: 200, headers }));

    await expect(fetchPublicAccountCapabilities({ fetchImpl }))
      .rejects.toThrow('Account capability response was malformed.');
  });

  it('fails closed even if a non-browser fetch implementation follows a capability redirect', async () => {
    const response = new Response('{"accounts_enabled":true}', {
      status: 200,
      headers: {
        'Cache-Control': 'no-store',
        'Content-Type': 'application/json',
      },
    });
    Object.defineProperty(response, 'redirected', { value: true });
    const fetchImpl = vi.fn(async () => response);

    await expect(fetchPublicAccountCapabilities({ fetchImpl }))
      .rejects.toThrow('Account capability response was malformed.');
  });

  it('posts per-account login credentials and accepts only account-scoped JWTs', async () => {
    const token = accountToken();
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify({
      token,
      expires_in_minutes: 60,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    await expect(loginAccount({
      username: ' owner@example.com ',
      apiCredential: ' casak_secret ',
    }, { baseUrl: 'https://api.example.test', fetchImpl })).resolves.toEqual({
      token,
      expires_in_minutes: 60,
    });
    expect(fetchImpl).toHaveBeenCalledWith('https://api.example.test/auth/token', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ username: 'owner@example.com', api_credential: 'casak_secret' }),
      cache: 'no-store',
      credentials: 'omit',
      redirect: 'error',
      referrerPolicy: 'no-referrer',
    }));
  });

  it('keeps invite credential client-held and maps the public profile response', async () => {
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify({
      account_id: 'acct-2',
      email_or_username: 'new@example.com',
      role: 'member',
      tenant_id: 'tenant-1',
      status: 'active',
      display_name: 'New User',
      api_credential: null,
      created_at: '2026-07-12T00:00:00Z',
      updated_at: '2026-07-12T00:00:00Z',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    const profile = await redeemAccountInvite({
      code: 'invite-1',
      emailOrUsername: 'new@example.com',
      apiCredential: 'casak_retry_safe',
      displayName: 'New User',
    }, { fetchImpl });

    expect(profile.account_id).toBe('acct-2');
    expect(profile).not.toHaveProperty('api_credential');
    expect(JSON.parse(String(fetchImpl.mock.calls[0][1]?.body))).toEqual({
      code: 'invite-1',
      email_or_username: 'new@example.com',
      api_credential: 'casak_retry_safe',
      display_name: 'New User',
    });
  });

  it('sends rotation with Bearer authorization and the browser-generated replacement', async () => {
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify({
      rotated: true,
      credential_issued_at: '2026-07-12T00:00:00Z',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    await rotateOwnAccountCredential('jwt-token', 'casak_replacement', { fetchImpl });
    const init = fetchImpl.mock.calls[0][1] as RequestInit;
    expect(init.headers).toMatchObject({ Authorization: 'Bearer jwt-token' });
    expect(JSON.parse(String(init.body))).toEqual({ api_credential: 'casak_replacement' });
  });

  it('rejects expired or non-account tokens and preserves backend error detail', async () => {
    expect(decodeAccountToken(accountToken({ exp: 1 }))).toBeNull();
    expect(decodeAccountToken(`${segment({})}.${segment({ sub: 'legacy', exp: 9999999999 })}.sig`)).toBeNull();

    const fetchImpl = vi.fn(async () => new Response(JSON.stringify({
      detail: 'Invalid account credentials.',
    }), { status: 401, headers: { 'Content-Type': 'application/json' } }));
    await expect(loginAccount({ username: 'x', apiCredential: 'y' }, { fetchImpl }))
      .rejects.toMatchObject({ httpStatus: 401, detail: 'Invalid account credentials.' });
  });
});
