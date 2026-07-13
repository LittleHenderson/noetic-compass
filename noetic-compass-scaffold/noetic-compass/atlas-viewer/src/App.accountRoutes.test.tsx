import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { ACCOUNT_SESSION_STORAGE_KEY } from './auth/AccountAuthProvider';

function segment(value: unknown): string {
  return btoa(JSON.stringify(value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function accountToken(): string {
  return `${segment({ alg: 'HS256' })}.${segment({
    sub: 'owner@example.com', account_id: 'acct-1', tenant_id: 'tenant-1', role: 'owner',
    jti: 'session-1', exp: Math.floor(Date.now() / 1000) + 3600,
  })}.signature`;
}

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
}

beforeEach(() => {
  sessionStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe('App account-mode routing', () => {
  it.each(['/', '/login', '/license', '/model-config'])(
    'keeps account-OFF route %s on the working reference/demo model flow',
    async (path) => {
      vi.stubEnv('VITE_ACCOUNTS_ENABLED', 'false');
      renderAt(path);
      expect(await screen.findByRole('heading', { name: 'Choose a model' })).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: 'Customer account access' })).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: 'Account' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Sign out' })).not.toBeInTheDocument();
    },
  );

  it('keeps the account-OFF audit shell reachable without an account JWT', async () => {
    vi.stubEnv('VITE_ACCOUNTS_ENABLED', 'false');
    renderAt('/audit-console');
    expect(await screen.findByRole('heading', {
      name: /Connect a model\. Run a CAS audit\./i,
    })).toBeInTheDocument();
    expect(screen.getByLabelText('Operator tools API token')).toBeInTheDocument();
  });

  it.each(['/', '/login', '/model-config', '/audit-console'])(
    'routes account-ON unauthenticated path %s to real customer sign-in',
    async (path) => {
      vi.stubEnv('VITE_ACCOUNTS_ENABLED', 'true');
      renderAt(path);
      expect(await screen.findByRole('heading', { name: 'Customer account access' })).toBeInTheDocument();
      expect(screen.queryByText(/auth flow is not yet wired/i)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(/mint secret/i)).not.toBeInTheDocument();
    },
  );

  it('allows an account-ON signed-in session through model and audit gates', async () => {
    vi.stubEnv('VITE_ACCOUNTS_ENABLED', 'true');
    sessionStorage.setItem(ACCOUNT_SESSION_STORAGE_KEY, accountToken());
    const first = renderAt('/model-config');
    expect(await screen.findByRole('heading', { name: 'Choose a model' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Account' })).toBeInTheDocument();
    first.unmount();

    renderAt('/audit-console');
    expect(await screen.findByRole('heading', {
      name: /Connect a model\. Run a CAS audit\./i,
    })).toBeInTheDocument();
    expect(screen.queryByLabelText('Operator tools API token')).not.toBeInTheDocument();
    expect(screen.getAllByText(/Distributed\/fleet customer account mode remains OPEN and is unavailable/i).length).toBeGreaterThan(0);
  });
});
