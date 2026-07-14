import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ACCOUNT_SESSION_STORAGE_KEY,
  AccountAuthProvider,
  LEGACY_LIVE_INVITE_STORAGE_KEY,
} from '../auth/AccountAuthProvider';
import { AuthGate } from '../components/auth/AuthGate';
import LoginPage from './LoginPage';
import ModelConfigPage from './ModelConfigPage';

function segment(value: unknown): string {
  return btoa(JSON.stringify(value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function accountToken(): string {
  return `${segment({ alg: 'HS256' })}.${segment({
    sub: 'owner@example.com', account_id: 'acct-1', tenant_id: 'tenant-1', role: 'owner',
    jti: 'session-1', exp: Math.floor(Date.now() / 1000) + 3600,
  })}.signature`;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function capabilityAwareFetch(
  next: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>,
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input).endsWith('/public/capabilities')) {
      return jsonResponse({ accounts_enabled: true });
    }
    return next(input, init);
  });
}

function LocationProbe(): JSX.Element {
  return <span data-testid="location">{useLocation().pathname}</span>;
}

function renderLogin(fetchImpl: typeof fetch, initialEntry = '/login') {
  return render(
    <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/model-config" element={<LocationProbe />} />
          <Route path="/audit-console" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </AccountAuthProvider>,
  );
}

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});
afterEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  vi.restoreAllMocks();
});

describe('LoginPage', () => {
  it('authenticates with the per-account credential and returns to the gated destination', async () => {
    const user = userEvent.setup();
    const fetchImpl = capabilityAwareFetch(
      async () => jsonResponse({ token: accountToken(), expires_in_minutes: 60 }),
    );
    render(
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>
        <MemoryRouter initialEntries={[{ pathname: '/login', state: { from: '/audit-console' } }]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/audit-console" element={<LocationProbe />} />
          </Routes>
        </MemoryRouter>
      </AccountAuthProvider>,
    );

    await user.type(await screen.findByLabelText('Email or username'), 'owner@example.com');
    await user.type(screen.getByLabelText('Account credential'), `casak_${'A'.repeat(43)}`);
    await user.click(screen.getByRole('button', { name: 'Sign in securely' }));

    expect(await screen.findByTestId('location')).toHaveTextContent('/audit-console');
    const loginCall = fetchImpl.mock.calls.find(([input]) => String(input).endsWith('/auth/token'))!;
    const body = JSON.parse(String((loginCall[1] as RequestInit).body));
    expect(body).toEqual({
      username: 'owner@example.com',
      api_credential: `casak_${'A'.repeat(43)}`,
    });
  });

  it('keeps the exact browser-generated credential across an interrupted redemption retry', async () => {
    const user = userEvent.setup();
    let redemptionAttempts = 0;
    const fetchImpl = capabilityAwareFetch(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/accounts/invite/redeem')) {
        redemptionAttempts += 1;
        if (redemptionAttempts === 1) {
          return jsonResponse({ detail: 'Invite code could not be redeemed.' }, 400);
        }
        return jsonResponse({
          account_id: 'acct-2', email_or_username: 'new@example.com', role: 'member',
          tenant_id: 'tenant-1', status: 'active', display_name: null,
          created_at: '2026-07-12T00:00:00Z', updated_at: '2026-07-12T00:00:00Z',
        });
      }
      return jsonResponse({ token: accountToken(), expires_in_minutes: 60 });
    });
    renderLogin(fetchImpl as typeof fetch);

    await user.click(await screen.findByRole('tab', { name: 'Redeem invite' }));
    await user.type(screen.getByLabelText('Invite code'), 'INVITE-ONE');
    await user.type(screen.getByLabelText('Email or username'), 'new@example.com');
    await user.click(screen.getByRole('button', { name: 'Generate my account credential' }));
    const generated = screen.getByLabelText('Generated account credential').querySelector('code')?.textContent;
    expect(generated).toMatch(/^casak_[A-Za-z0-9_-]{43}$/);
    await user.click(screen.getByLabelText('I saved this credential in a secure place.'));
    await user.click(screen.getByRole('button', { name: 'Redeem invite and sign in' }));

    expect(await screen.findByText(/same generated credential is retained/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Generated account credential')).toHaveTextContent(generated!);
    await user.click(screen.getByRole('button', { name: 'Redeem invite and sign in' }));
    expect(await screen.findByRole('button', { name: 'Continue to model selection' })).toBeInTheDocument();

    const redeemCalls = fetchImpl.mock.calls.filter(([input]) => String(input).endsWith('/accounts/invite/redeem'));
    const first = JSON.parse(String((redeemCalls[0][1] as RequestInit).body));
    const second = JSON.parse(String((redeemCalls[1][1] as RequestInit).body));
    expect(first.api_credential).toBe(generated);
    expect(second.api_credential).toBe(generated);
    expect(localStorage.length).toBe(0);
  });

  it('labels bootstrap and tenant provisioning as operator-only and exposes no secret field', async () => {
    const fetchImpl = capabilityAwareFetch(async () => jsonResponse({}));
    renderLogin(fetchImpl as typeof fetch);
    expect(await screen.findByText(/operator-only deployment workflows/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/bootstrap secret/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/platform secret/i)).not.toBeInTheDocument();
  });

  it('shows an explicit memory-only warning when server logout revocation cannot be confirmed', async () => {
    const user = userEvent.setup();
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, accountToken());
    localStorage.setItem(LEGACY_LIVE_INVITE_STORAGE_KEY, 'legacy-live-secret');
    const fetchImpl = capabilityAwareFetch(
      async () => jsonResponse({ detail: 'revocation unavailable' }, 503),
    );

    render(
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>
        <MemoryRouter initialEntries={['/model-config']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/model-config" element={<AuthGate><ModelConfigPage /></AuthGate>} />
          </Routes>
        </MemoryRouter>
      </AccountAuthProvider>,
    );

    await user.click(await screen.findByRole('button', { name: 'Sign out' }));
    expect(await screen.findByRole('heading', { name: 'Customer account access' })).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent(
      /Local sign-out completed, but server session revocation is unavailable/i,
    );
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
    expect(localStorage.getItem(LEGACY_LIVE_INVITE_STORAGE_KEY)).toBeNull();
  });
});
