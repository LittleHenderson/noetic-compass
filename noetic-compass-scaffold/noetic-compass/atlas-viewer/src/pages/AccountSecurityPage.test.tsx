import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ACCOUNT_SESSION_STORAGE_KEY, ACCOUNT_SESSION_API_KEY, accountSessionBinding, AccountAuthProvider } from '../auth/AccountAuthProvider';
import { AuthGate } from '../components/auth/AuthGate';
import AccountSecurityPage from './AccountSecurityPage';
import LoginPage from './LoginPage';

function segment(value: unknown): string {
  return btoa(JSON.stringify(value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function accountToken(): string {
  return `${segment({ alg: 'HS256' })}.${segment({
    sub: 'owner@example.com', account_id: 'acct-1', tenant_id: 'tenant-1', role: 'owner',
    jti: 'session-1', exp: Math.floor(Date.now() / 1000) + 3600,
  })}.signature`;
}

beforeEach(() => sessionStorage.clear());

describe('AccountSecurityPage', () => {
  it('rotates with a browser-generated credential, revokes the session, and hands off one visible copy', async () => {
    const user = userEvent.setup();
    const token = accountToken();
    sessionStorage.setItem(ACCOUNT_SESSION_API_KEY, accountSessionBinding());
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, token);
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => new Response(JSON.stringify(
      String(input).endsWith('/public/capabilities')
        ? { accounts_enabled: true }
        : {
          rotated: true,
          credential_issued_at: '2026-07-12T17:00:00Z',
        },
    ), {
      status: 200,
      headers: { 'Cache-Control': 'no-store', 'Content-Type': 'application/json' },
    }));

    render(
      <AccountAuthProvider accountsEnabled apiOptions={{ fetchImpl }}>
        <MemoryRouter initialEntries={['/account-security']}>
          <Routes>
            <Route path="/account-security" element={<AuthGate><AccountSecurityPage /></AuthGate>} />
            <Route path="/login" element={<LoginPage />} />
          </Routes>
        </MemoryRouter>
      </AccountAuthProvider>,
    );

    expect(await screen.findByText('acct-1')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Generate replacement credential' }));
    const generated = screen.getByText(/^casak_[A-Za-z0-9_-]{43}$/).textContent!;
    await user.click(screen.getByLabelText(/I securely saved this replacement credential/i));
    await user.click(screen.getByRole('button', { name: 'Rotate credential and sign out' }));

    expect(await screen.findByRole('heading', { name: 'Customer account access' })).toBeInTheDocument();
    expect(screen.getByText(/Credential rotation succeeded and revoked the old session/i)).toBeInTheDocument();
    expect(screen.getAllByText(generated).length).toBeGreaterThan(0);
    expect(sessionStorage.getItem(ACCOUNT_SESSION_STORAGE_KEY)).toBeNull();
    expect(localStorage.length).toBe(0);
    const rotationCall = fetchImpl.mock.calls.find(
      ([input]) => String(input).endsWith('/accounts/credential/rotate'),
    )!;
    const init = rotationCall[1] as RequestInit;
    expect(new Headers(init.headers).get('Authorization')).toBe(`Bearer ${token}`);
    expect(JSON.parse(String(init.body))).toEqual({ api_credential: generated });
  });
});
