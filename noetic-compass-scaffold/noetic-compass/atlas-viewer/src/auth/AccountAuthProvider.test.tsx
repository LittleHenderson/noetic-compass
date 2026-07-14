import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ACCOUNT_CAPABILITY_TIMEOUT_MS,
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

function capabilityAwareFetch(
  accountsEnabled: boolean,
  next: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>,
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input).endsWith('/public/capabilities')) {
      return jsonResponse({ accounts_enabled: accountsEnabled });
    }
    return next(input, init);
  });
}

function AccountStateProbe() {
  const auth = useAccountAuth();
  return (
    <div data-testid="account-state">
      {auth.accountsEnabled ? 'accounts-enabled' : 'accounts-disabled'}
    </div>
  );
}

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

describe('AccountAuthProvider', () => {
  it('does not render account state while the exact API capability is loading', () => {
    const fetchImpl = vi.fn(() => new Promise<Response>(() => undefined));

    render(
      <AccountAuthProvider
        accountsEnabled
        apiOptions={{ fetchImpl, baseUrl: 'https://api.example.test' }}
      >
        <AccountStateProbe />
      </AccountAuthProvider>,
    );

    expect(screen.getByRole('status')).toHaveTextContent(/verifying customer account mode/i);
    expect(screen.queryByTestId('account-state')).not.toBeInTheDocument();
    expect(fetchImpl).toHaveBeenCalledWith(
      'https://api.example.test/public/capabilities',
      expect.objectContaining({
        method: 'GET',
        credentials: 'omit',
        redirect: 'error',
      }),
    );
    const headers = new Headers((fetchImpl.mock.calls[0][1] as RequestInit).headers);
    expect(headers.get('Authorization')).toBeNull();
  });

  it.each([
    [true, 'accounts-enabled'],
    [false, 'accounts-disabled'],
  ])('renders only after matching a %s client/server account mode', async (
    accountsEnabled,
    expected,
  ) => {
    vi.stubEnv('VITE_ACCOUNTS_ENABLED', String(accountsEnabled));
    const fetchImpl = capabilityAwareFetch(accountsEnabled, async () => jsonResponse({}));

    render(
      <AccountAuthProvider apiOptions={{ fetchImpl }}>
        <AccountStateProbe />
      </AccountAuthProvider>,
    );

    expect(await screen.findByTestId('account-state')).toHaveTextContent(expected);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(fetchImpl.mock.calls[0][0]).toBe('/api/public/capabilities');
  });

  it('fails closed when the Atlas build flag disagrees with the API capability', async () => {
    vi.stubEnv('VITE_ACCOUNTS_ENABLED', 'false');
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, accountToken());
    const fetchImpl = capabilityAwareFetch(true, async () => jsonResponse({}));

    render(
      <AccountAuthProvider apiOptions={{ fetchImpl }}>
        <AccountStateProbe />
      </AccountAuthProvider>,
    );

    expect(await screen.findByRole('alert')).toHaveAttribute(
      'data-account-capability-state',
      'mismatch',
    );
    expect(screen.queryByTestId('account-state')).not.toBeInTheDocument();
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
  });

  it('fails closed when the API capability is unavailable', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error('offline');
    });

    render(
      <AccountAuthProvider accountsEnabled={false} apiOptions={{ fetchImpl }}>
        <AccountStateProbe />
      </AccountAuthProvider>,
    );

    expect(await screen.findByRole('alert')).toHaveAttribute(
      'data-account-capability-state',
      'unavailable',
    );
    expect(screen.queryByTestId('account-state')).not.toBeInTheDocument();
  });

  it('fails closed on a bounded deadline when the capability request hangs', async () => {
    vi.useFakeTimers();
    try {
      const fetchImpl = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => (
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
        })
      ));

      render(
        <AccountAuthProvider accountsEnabled={false} apiOptions={{ fetchImpl }}>
          <AccountStateProbe />
        </AccountAuthProvider>,
      );

      expect(screen.getByRole('status')).toBeInTheDocument();
      await act(async () => {
        await vi.advanceTimersByTimeAsync(ACCOUNT_CAPABILITY_TIMEOUT_MS);
      });
      expect(screen.getByRole('alert')).toHaveAttribute(
        'data-account-capability-state',
        'unavailable',
      );
      expect(screen.queryByTestId('account-state')).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it('stores only the JWT in sessionStorage after a real account login', async () => {
    const token = accountToken();
    const fetchImpl = capabilityAwareFetch(
      true,
      async () => jsonResponse({ token, expires_in_minutes: 60 }),
    );
    const wrapper = ({ children }: { children: ReactNode }) => (
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>{children}</AccountAuthProvider>
    );
    const { result } = renderHook(() => useAccountAuth(), { wrapper });

    await waitFor(() => expect(result.current.accountsEnabled).toBe(true));

    await act(async () => {
      await result.current.login('owner@example.com', 'casak_private');
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.claims).toMatchObject({ account_id: 'acct-1', role: 'owner' });
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBe(token);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.getItem('casak_private')).toBeNull();
  });

  it('restores only a valid unexpired account JWT and discards malformed state', async () => {
    const fetchImpl = capabilityAwareFetch(true, async () => jsonResponse({}));
    localStorage.setItem(LEGACY_LIVE_INVITE_STORAGE_KEY, 'legacy-live-secret');
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, accountToken());
    const { result, unmount } = renderHook(() => useAccountAuth(), {
      wrapper: ({ children }) => (
        <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>
          {children}
        </AccountAuthProvider>
      ),
    });
    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));
    expect(result.current.isAuthenticated).toBe(true);
    expect(localStorage.getItem(LEGACY_LIVE_INVITE_STORAGE_KEY)).toBeNull();
    unmount();

    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, 'not-a-jwt');
    const malformed = renderHook(() => useAccountAuth(), {
      wrapper: ({ children }) => (
        <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>
          {children}
        </AccountAuthProvider>
      ),
    });
    await waitFor(() => expect(malformed.result.current.accountsEnabled).toBe(true));
    expect(malformed.result.current.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
  });

  it('revokes the server session on logout and always clears the browser session', async () => {
    const token = accountToken();
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, token);
    localStorage.setItem(LEGACY_LIVE_INVITE_STORAGE_KEY, 'legacy-live-secret');
    const fetchImpl = capabilityAwareFetch(
      true,
      async () => jsonResponse({ detail: 'temporary outage' }, 503),
    );
    const wrapper = ({ children }: { children: ReactNode }) => (
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>{children}</AccountAuthProvider>
    );
    const { result } = renderHook(() => useAccountAuth(), { wrapper });

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

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
    const fetchImpl = capabilityAwareFetch(
      true,
      async () => jsonResponse({ detail: 'expired' }, 401),
    );
    const wrapper = ({ children }: { children: ReactNode }) => (
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>{children}</AccountAuthProvider>
    );
    const { result } = renderHook(() => useAccountAuth(), { wrapper });

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

    await act(async () => {
      await result.current.authenticatedFetch('/api/cas-harness/audit/session', { method: 'POST' });
    });

    const init = fetchImpl.mock.calls[1][1] as RequestInit;
    expect(new Headers(init.headers).get('Authorization')).toBe(`Bearer ${token}`);
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('never attaches the account Bearer to an arbitrary third-party origin', async () => {
    const token = accountToken();
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, token);
    const fetchImpl = capabilityAwareFetch(true, async (input: RequestInfo | URL) => (
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

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

    await act(async () => {
      await result.current.authenticatedFetch('https://evil.example/collect', {
        headers: { Authorization: 'Bearer inherited-secret' },
      });
    });
    expect(result.current.isAuthenticated).toBe(true);
    await act(async () => {
      await result.current.authenticatedFetch('https://api.example.test/api/cas-harness/audit/session');
    });

    expect(fetchImpl.mock.calls[0][0]).toBe('https://api.example.test/public/capabilities');
    const capabilityInit = fetchImpl.mock.calls[0][1] as RequestInit;
    const capabilityHeaders = new Headers(capabilityInit.headers);
    const evilHeaders = new Headers((fetchImpl.mock.calls[1][1] as RequestInit).headers);
    const apiHeaders = new Headers((fetchImpl.mock.calls[2][1] as RequestInit).headers);
    expect(capabilityInit.credentials).toBe('omit');
    expect(capabilityHeaders.get('Authorization')).toBeNull();
    expect(evilHeaders.get('Authorization')).toBeNull();
    expect(apiHeaders.get('Authorization')).toBe(`Bearer ${token}`);
  });

  it('rotates to a client-supplied credential, clears the token, and keeps a memory-only handoff', async () => {
    const token = accountToken();
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, token);
    const fetchImpl = capabilityAwareFetch(true, async () => jsonResponse({
      rotated: true,
      credential_issued_at: '2026-07-12T12:00:00Z',
    }));
    const wrapper = ({ children }: { children: ReactNode }) => (
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>{children}</AccountAuthProvider>
    );
    const { result } = renderHook(() => useAccountAuth(), { wrapper });

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

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
