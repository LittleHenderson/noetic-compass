import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ACCOUNT_SESSION_STORAGE_KEY,
  AccountAuthProvider,
  LEGACY_LIVE_INVITE_STORAGE_KEY,
  useAccountAuth,
} from './AccountAuthProvider';

function segment(value: unknown): string {
  return btoa(JSON.stringify(value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function accountToken(): string {
  return `${segment({ alg: 'HS256' })}.${segment({
    sub: 'owner@example.com',
    account_id: 'acct-1',
    tenant_id: 'tenant-1',
    role: 'owner',
    jti: 'session-1',
    exp: Math.floor(Date.now() / 1000) + 3600,
  })}.signature`;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('AccountAuthProvider', () => {
  it('stores only the JWT in sessionStorage after a real account login', async () => {
    const token = accountToken();
    const fetchImpl = vi.fn(async () => jsonResponse({ token, expires_in_minutes: 60 }));
    const wrapper = ({ children }: { children: ReactNode }) => (
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>{children}</AccountAuthProvider>
    );
    const { result } = renderHook(() => useAccountAuth(), { wrapper });

    await act(async () => {
      await result.current.login('owner@example.com', 'casak_private');
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.claims).toMatchObject({ account_id: 'acct-1', role: 'owner' });
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBe(token);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.getItem('casak_private')).toBeNull();
  });

  it('restores only a valid unexpired account JWT and discards malformed state', () => {
    localStorage.setItem(LEGACY_LIVE_INVITE_STORAGE_KEY, 'legacy-live-secret');
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, accountToken());
    const { result, unmount } = renderHook(() => useAccountAuth(), {
      wrapper: ({ children }) => <AccountAuthProvider accountsEnabled>{children}</AccountAuthProvider>,
    });
    expect(result.current.isAuthenticated).toBe(true);
    expect(localStorage.getItem(LEGACY_LIVE_INVITE_STORAGE_KEY)).toBeNull();
    unmount();

    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, 'not-a-jwt');
    const malformed = renderHook(() => useAccountAuth(), {
      wrapper: ({ children }) => <AccountAuthProvider accountsEnabled>{children}</AccountAuthProvider>,
    });
    expect(malformed.result.current.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
  });

  it('revokes the server session on logout and always clears the browser session', async () => {
    const token = accountToken();
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, token);
    localStorage.setItem(LEGACY_LIVE_INVITE_STORAGE_KEY, 'legacy-live-secret');
    const fetchImpl = vi.fn(async () => jsonResponse({ detail: 'temporary outage' }, 503));
    const wrapper = ({ children }: { children: ReactNode }) => (
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>{children}</AccountAuthProvider>
    );
    const { result } = renderHook(() => useAccountAuth(), { wrapper });

    await act(async () => {
      await expect(result.current.logout()).rejects.toMatchObject({ httpStatus: 503 });
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.logoutWarning).toMatch(/server session revocation is unavailable/i);
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
    expect(localStorage.length).toBe(0);
    expect(fetchImpl).toHaveBeenCalledWith('/api/auth/logout', expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({ Authorization: `Bearer ${token}` }),
    }));
  });

  it('automatically attaches the account Bearer token and clears it on 401', async () => {
    const token = accountToken();
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, token);
    const fetchImpl = vi.fn(async () => jsonResponse({ detail: 'expired' }, 401));
    const wrapper = ({ children }: { children: ReactNode }) => (
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>{children}</AccountAuthProvider>
    );
    const { result } = renderHook(() => useAccountAuth(), { wrapper });

    await act(async () => {
      await result.current.authenticatedFetch('/api/cas-harness/audit/session', { method: 'POST' });
    });

    const init = fetchImpl.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).get('Authorization')).toBe(`Bearer ${token}`);
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('never attaches the account Bearer to an arbitrary third-party origin', async () => {
    const token = accountToken();
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, token);
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => (
      String(input).startsWith('https://evil.example')
        ? jsonResponse({ detail: 'third-party unauthorized' }, 401)
        : jsonResponse({ ok: true })
    ));
    const wrapper = ({ children }: { children: ReactNode }) => (
      <AccountAuthProvider
        accountsEnabled
        apiOptions={{ fetchImpl, baseUrl: 'https://api.example.test' }}
      >
        {children}
      </AccountAuthProvider>
    );
    const { result } = renderHook(() => useAccountAuth(), { wrapper });

    await act(async () => {
      await result.current.authenticatedFetch('https://evil.example/collect', {
        headers: { Authorization: 'Bearer inherited-secret' },
      });
    });
    expect(result.current.isAuthenticated).toBe(true);
    await act(async () => {
      await result.current.authenticatedFetch('https://api.example.test/api/cas-harness/audit/session');
    });

    const evilHeaders = new Headers((fetchImpl.mock.calls[0][1] as RequestInit).headers);
    const apiHeaders = new Headers((fetchImpl.mock.calls[1][1] as RequestInit).headers);
    expect(evilHeaders.get('Authorization')).toBeNull();
    expect(apiHeaders.get('Authorization')).toBe(`Bearer ${token}`);
  });

  it('rotates to a client-supplied credential, clears the token, and keeps a memory-only handoff', async () => {
    const token = accountToken();
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, token);
    const fetchImpl = vi.fn(async () => jsonResponse({
      rotated: true,
      credential_issued_at: '2026-07-12T12:00:00Z',
    }));
    const wrapper = ({ children }: { children: ReactNode }) => (
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>{children}</AccountAuthProvider>
    );
    const { result } = renderHook(() => useAccountAuth(), { wrapper });

    await act(async () => {
      await result.current.rotateCredential('casak_new_private');
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.credentialHandoff).toEqual({
      credential: 'casak_new_private',
      reason: 'rotation',
      issuedAt: '2026-07-12T12:00:00Z',
    });
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
    expect(localStorage.length).toBe(0);
  });
});
