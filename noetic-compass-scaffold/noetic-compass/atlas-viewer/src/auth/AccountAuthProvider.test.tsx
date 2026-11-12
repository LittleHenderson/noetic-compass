import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ACCOUNT_CAPABILITY_TIMEOUT_MS,
  ACCOUNT_SESSION_STORAGE_KEY,
  ACCOUNT_SESSION_API_KEY,
  accountSessionBinding,
  AccountAuthProvider,
  LEGACY_LIVE_INVITE_STORAGE_KEY,
  mayAttachAccountBearer,
  useAccountAuth,
} from './AccountAuthProvider';

function segment(value: unknown): string {
  return btoa(JSON.stringify(value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function accountToken(jti = 'session-1'): string {
  return `${segment({ alg: 'HS256' })}.${segment({
    sub: 'owner@example.com',
    account_id: 'acct-1',
    tenant_id: 'tenant-1',
    role: 'owner',
    jti,
    exp: Math.floor(Date.now() / 1000) + 3600,
  })}.signature`;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Cache-Control': 'no-store',
      'Content-Type': 'application/json',
    },
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

    expect(screen.getByRole('status')).toHaveTextContent('Verifying customer account mode...');
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
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
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
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
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

    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
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
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
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
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
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
    expect(init).toMatchObject({
      cache: 'no-store',
      credentials: 'omit',
      redirect: 'error',
      referrerPolicy: 'no-referrer',
    });
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('never attaches the account Bearer to an arbitrary third-party origin', async () => {
    const token = accountToken();
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding('https://api.example.test'));
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
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
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

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

async function authHarness(next: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>) {
  const fetchImpl = capabilityAwareFetch(true, next);
  const hook = renderHook(() => useAccountAuth(), {
    wrapper: ({ children }) => <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>{children}</AccountAuthProvider>,
  });
  await waitFor(() => expect(hook.result.current.accountsEnabled).toBe(true));
  return { ...hook, fetchImpl };
}

describe('account operation ordering and quota safety', () => {
  it('a delayed login cannot restore a session after logout', async () => {
    const response = deferred<Response>();
    const { result, fetchImpl } = await authHarness(() => response.promise);
    let login!: Promise<unknown>;
    act(() => { login = result.current.login('owner', 'casak_synthetic').catch(error => error); });
    await act(async () => { await result.current.logout(); });
    await act(async () => { response.resolve(jsonResponse({ token: accountToken(), expires_in_minutes: 60 })); await login; });
    expect(result.current.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
    expect(fetchImpl.mock.calls.filter(([url]) => String(url).endsWith('/auth/token'))).toHaveLength(1);
  });

  it('the newest login wins when responses arrive in reverse order', async () => {
    const first = deferred<Response>();
    let requests = 0;
    const latest = accountToken('latest');
    const { result } = await authHarness(() => ++requests === 1 ? first.promise : Promise.resolve(jsonResponse({ token: latest, expires_in_minutes: 60 })));
    let old!: Promise<unknown>;
    act(() => { old = result.current.login('owner', 'casak_old').catch(error => error); });
    await act(async () => { await result.current.login('owner', 'casak_new'); });
    await act(async () => { first.resolve(jsonResponse({ token: accountToken('old'), expires_in_minutes: 60 })); await old; });
    expect(result.current.token).toBe(latest);
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBe(latest);
  });

  it('a delayed logout response cannot clear a newer login', async () => {
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, accountToken('old'));
    const revoke = deferred<Response>();
    const latest = accountToken('latest');
    const { result } = await authHarness((input) => String(input).endsWith('/auth/logout') ? revoke.promise : Promise.resolve(jsonResponse({ token: latest, expires_in_minutes: 60 })));
    let logout!: Promise<void>;
    act(() => { logout = result.current.logout(); });
    expect(result.current.isAuthenticated).toBe(false);
    await act(async () => { await result.current.login('owner', 'casak_new'); });
    await act(async () => { revoke.resolve(jsonResponse({ revoked: true })); await logout; });
    expect(result.current.token).toBe(latest);
  });

  it('a late 401 for the old session does not clear the newer session', async () => {
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, accountToken('old'));
    const oldRequest = deferred<Response>();
    const latest = accountToken('latest');
    const { result } = await authHarness((input) => String(input).endsWith('/auth/token') ? Promise.resolve(jsonResponse({ token: latest, expires_in_minutes: 60 })) : oldRequest.promise);
    let request!: Promise<Response>;
    act(() => { request = result.current.authenticatedFetch('/api/cas-harness/audit/session'); });
    await act(async () => { await result.current.login('owner', 'casak_new'); });
    await act(async () => { oldRequest.resolve(jsonResponse({ detail: 'old expired' }, 401)); await request; });
    expect(result.current.token).toBe(latest);
  });

  it('unmounting cancels login even when the fetch implementation ignores abort', async () => {
    const response = deferred<Response>();
    const { result, unmount } = await authHarness(() => response.promise);
    let pending!: Promise<unknown>;
    act(() => { pending = result.current.login('owner', 'casak_synthetic').catch(error => error); });
    unmount();
    response.resolve(jsonResponse({ token: accountToken(), expires_in_minutes: 60 }));
    await pending;
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
  });

  it('cancelled invite redemption never starts a follow-up login', async () => {
    const response = deferred<Response>();
    const { result, fetchImpl } = await authHarness(() => response.promise);
    let pending!: Promise<unknown>;
    act(() => { pending = result.current.redeemInvite({ code: 'SYNTHETIC', emailOrUsername: 'owner', apiCredential: 'casak_synthetic' }).catch(error => error); });
    act(() => result.current.cancelPendingAuth());
    await act(async () => {
      response.resolve(jsonResponse({ account_id: 'acct', email_or_username: 'owner', role: 'member', tenant_id: 'tenant', status: 'active', display_name: null, created_at: 'today', updated_at: 'today' }));
      await pending;
    });
    expect(fetchImpl.mock.calls.some(([url]) => String(url).endsWith('/auth/token'))).toBe(false);
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
  });

  it.each(['Monthly limit exceeded', 'Rate limit exceeded'])('retains the same identity and does not retry on 429: %s', async (detail) => {
    const token = accountToken();
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, token);
    const { result, fetchImpl } = await authHarness(async () => jsonResponse({ detail }, 429));
    await act(async () => { const response = await result.current.authenticatedFetch('/api/cas-harness/audit/session'); expect(response.status).toBe(429); });
    expect(result.current.token).toBe(token);
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBe(token);
    expect(screen.getByRole('alert')).toHaveTextContent('identity and session are unchanged');
    expect(fetchImpl.mock.calls).toHaveLength(2); // handshake plus one request, no mint or retry
  });

  it('strips Authorization inherited from a Request object sent to an untrusted origin', async () => {
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, accountToken());
    const { result, fetchImpl } = await authHarness(async () => jsonResponse({ ok: true }));
    await act(async () => { await result.current.authenticatedFetch(new Request('https://untrusted.example/collect', { headers: { Authorization: 'Bearer synthetic' } })); });
    expect(new Headers(fetchImpl.mock.calls[1][1]?.headers).has('Authorization')).toBe(false);
  });

  it('restricts the bearer to the exact verified API origin and path prefix', () => {
    expect(mayAttachAccountBearer('/api/private', 'https://api.example/root')).toBe(false);
    expect(mayAttachAccountBearer('https://api.example/other', 'https://api.example/root')).toBe(false);
    expect(mayAttachAccountBearer('https://api.example/root-evil', 'https://api.example/root')).toBe(false);
    expect(mayAttachAccountBearer('https://user@api.example/root/a', 'https://api.example/root')).toBe(false);
    expect(mayAttachAccountBearer('https://api.example/root/a', 'https://api.example/root')).toBe(true);
  });
});

describe('verified API session binding', () => {
  it('rejects a previously persisted token without an API binding', async () => {
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, accountToken());
    const { result } = await authHarness(async () => jsonResponse({}));
    expect(result.current.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
  });

  it('rejects A storage and every retained A auth callback after B verifies and signs in', async () => {
    const a = 'https://api-a.example';
    const b = 'https://api-b.example';
    const tokenA = accountToken('session-A');
    const tokenB = accountToken('session-B');
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding(a));
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, tokenA);
    const fetchImpl = capabilityAwareFetch(true, async (input) => String(input).endsWith('/auth/token')
      ? jsonResponse({ token: tokenB, expires_in_minutes: 60 })
      : jsonResponse({ ok: true }));
    let current!: ReturnType<typeof useAccountAuth>;
    function Probe() { current = useAccountAuth(); return <span>{current.isAuthenticated ? 'signed-in' : 'signed-out'}</span>; }
    const view = render(<AccountAuthProvider accountsEnabled apiOptions={{ baseUrl: a, fetchImpl }}><Probe /></AccountAuthProvider>);
    await waitFor(() => expect(current.token).toBe(tokenA));
    const stale = current;
    view.rerender(<AccountAuthProvider accountsEnabled apiOptions={{ baseUrl: b, fetchImpl }}><Probe /></AccountAuthProvider>);
    await waitFor(() => expect(screen.getByText('signed-out')).toBeInTheDocument());
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
    expect(fetchImpl.mock.calls.filter(([url]) => String(url).startsWith(b)).every(([,init]) => !new Headers(init?.headers).has('Authorization'))).toBe(true);
    await act(async () => { await current.login('B-owner', 'casak_synthetic-B'); });
    expect(current.token).toBe(tokenB);
    const before = fetchImpl.mock.calls.length;
    await expect(stale.login('old-owner', 'casak_synthetic-A')).rejects.toThrow('binding changed');
    await expect(stale.redeemInvite({ code: 'old', emailOrUsername: 'old-owner', apiCredential: 'casak_synthetic-A' })).rejects.toThrow('binding changed');
    await expect(stale.rotateCredential('casak_synthetic-A')).rejects.toThrow('binding changed');
    await expect(stale.logout()).rejects.toThrow('binding changed');
    await expect(stale.authenticatedFetch(`${a}/private`)).rejects.toThrow('binding changed');
    expect(fetchImpl.mock.calls).toHaveLength(before);
    expect(current.token).toBe(tokenB);
    expect(sessionStorage.getItem(ACCOUNT_SESSION_API_KEY)).toBe(accountSessionBinding(b));
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBe(tokenB);
    await act(async () => { await current.authenticatedFetch(`${b}/private`); });
    expect(new Headers(fetchImpl.mock.calls.at(-1)?.[1]?.headers).get('Authorization')).toBe(`Bearer ${tokenB}`);
  });

  it('never restores a stored A token when a fresh provider starts against B', async () => {
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding('https://api-a.example'));
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, accountToken('A'));
    const fetchImpl = capabilityAwareFetch(true, async () => jsonResponse({}));
    const { result } = renderHook(() => useAccountAuth(), {
      wrapper: ({ children }) => <AccountAuthProvider accountsEnabled apiOptions={{ baseUrl: 'https://api-b.example', fetchImpl }}>{children}</AccountAuthProvider>,
    });
    await waitFor(() => expect(result.current.accountsEnabled).toBe(true));
    expect(result.current.token).toBeNull();
    expect(fetchImpl.mock.calls).toHaveLength(1);
    expect(new Headers(fetchImpl.mock.calls[0][1]?.headers).has('Authorization')).toBe(false);
  });
});
