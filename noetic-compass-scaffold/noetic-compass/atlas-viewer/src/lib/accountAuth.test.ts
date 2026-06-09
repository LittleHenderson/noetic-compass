import { describe, expect, it, beforeEach, vi } from 'vitest';
import {
  ACCOUNT_SESSION_STORAGE_KEY,
  authorizationHeaderValue,
  clearStoredAccountSession,
  loginOrRedeemAccount,
  logoutAccountSession,
  readStoredAccountSession,
  resolveAccountApiBaseUrl,
  writeStoredAccountSession,
  type AccountProfile,
} from './accountAuth';

const account: AccountProfile = {
  account_id: 'acct-1',
  email_or_username: 'user@example.com',
  role: 'member',
  tenant_id: 'tenant-1',
  status: 'active',
  display_name: null,
  created_at: '2026-06-09T00:00:00Z',
  updated_at: '2026-06-09T00:00:00Z',
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('accountAuth', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.unstubAllEnvs();
    vi.useRealTimers();
  });

  it('redeems an invite, mints an account token, and normalizes storage', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-06-09T12:00:00Z'));
    const fetchMock = vi
      .fn<[RequestInfo | URL, RequestInit | undefined], Promise<Response>>()
      .mockResolvedValueOnce(jsonResponse(account))
      .mockResolvedValueOnce(jsonResponse({ token: 'jwt-123', expires_in_minutes: 30 }));

    const session = await loginOrRedeemAccount({
      email: ' USER@EXAMPLE.COM ',
      inviteCode: ' invite-1 ',
      mintSecret: 'mint-secret',
      fetchImpl: fetchMock as unknown as typeof fetch,
    });

    expect(session).toEqual({
      token: 'jwt-123',
      email: 'user@example.com',
      expiresAt: '2026-06-09T12:30:00.000Z',
      account,
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/accounts/invite/redeem');
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toMatchObject({
      code: 'invite-1',
      email_or_username: 'user@example.com',
    });
    expect(fetchMock.mock.calls[1][0]).toBe('/api/auth/token');
    expect(fetchMock.mock.calls[1][1]?.headers).toMatchObject({
      'X-Auth-Mint-Secret': 'mint-secret',
    });
  });

  it('persists and clears the account session', () => {
    const session = {
      token: 'jwt-123',
      email: 'user@example.com',
      expiresAt: null,
      account,
    };
    writeStoredAccountSession(session);

    expect(readStoredAccountSession()).toEqual(session);
    clearStoredAccountSession();
    expect(window.localStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
    expect(readStoredAccountSession()).toBeNull();
  });

  it('removes malformed stored sessions', () => {
    window.localStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, '{bad json');

    expect(readStoredAccountSession()).toBeNull();
    expect(window.localStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
  });

  it('calls logout with the bearer token', async () => {
    const fetchMock = vi
      .fn<[RequestInfo | URL, RequestInit | undefined], Promise<Response>>()
      .mockResolvedValueOnce(jsonResponse({ revoked: true }));

    await logoutAccountSession('jwt-123', {
      fetchImpl: fetchMock as unknown as typeof fetch,
    });

    expect(fetchMock).toHaveBeenCalledWith('/api/auth/logout', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        Authorization: 'Bearer jwt-123',
      },
    });
  });

  it('derives account API bases from Atlas API bases', () => {
    expect(resolveAccountApiBaseUrl()).toBe('/api');
    vi.stubEnv('VITE_ATLAS_API_BASE_URL', '/api/atlas');
    expect(resolveAccountApiBaseUrl()).toBe('/api');
    vi.stubEnv('VITE_ATLAS_API_BASE_URL', 'https://api.example.com/atlas');
    expect(resolveAccountApiBaseUrl()).toBe('https://api.example.com');
    vi.stubEnv('VITE_ATLAS_API_BASE_URL', 'https://api.example.com/api/atlas');
    expect(resolveAccountApiBaseUrl()).toBe('https://api.example.com');
  });

  it('normalizes bearer headers', () => {
    expect(authorizationHeaderValue('jwt-123')).toBe('Bearer jwt-123');
    expect(authorizationHeaderValue('Bearer jwt-123')).toBe('Bearer jwt-123');
    expect(authorizationHeaderValue('   ')).toBeNull();
  });
});
