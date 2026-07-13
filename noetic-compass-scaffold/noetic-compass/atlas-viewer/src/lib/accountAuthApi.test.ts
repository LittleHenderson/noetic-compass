import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  AccountAuthApiError,
  decodeAccountToken,
  generateAccountCredential,
  loginAccount,
  redeemAccountInvite,
  resolveAccountApiBaseUrl,
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
    expect(resolveAccountApiBaseUrl('https://api.example.test/root/')).toBe('https://api.example.test/root');
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
