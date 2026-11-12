import { expect, test } from '@playwright/test';

const token = () => [
  Buffer.from(JSON.stringify({ alg: 'HS256' })).toString('base64url'),
  Buffer.from(JSON.stringify({ sub: 'synthetic-owner', account_id: 'acct-test', tenant_id: 'tenant-test', role: 'owner', jti: 'session-test', exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url'),
  'synthetic-signature',
].join('.');

test('accounts-off API fails closed without displaying or sending credentials', async ({ page }) => {
  const requests: string[] = [];
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== 'http://127.0.0.1:4179') return route.abort();
    if (url.pathname.startsWith('/api/')) {
      requests.push(url.pathname);
      expect(route.request().headers()['authorization']).toBeUndefined();
      return route.fulfill({ json: { accounts_enabled: false }, headers: { 'Cache-Control': 'no-store' } });
    }
    return route.continue();
  });
  await page.goto('/login');
  await expect(page.getByRole('alert')).toContainText('could not be verified');
  await expect(page.getByLabel('Account credential')).toHaveCount(0);
  expect(requests).toEqual(['/api/public/capabilities']);
});

test('real browser uses a per-account credential, rechecks on reload, and signs out', async ({ page }) => {
  const requests: string[] = [];
  const jwt = token();
  await page.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== 'http://127.0.0.1:4179') return route.abort();
    if (!url.pathname.startsWith('/api/')) return route.continue();
    requests.push(url.pathname);
    expect(Object.keys(request.headers()).some(key => key.toLowerCase().includes('mint-secret'))).toBe(false);
    if (url.pathname === '/api/public/capabilities') {
      expect(request.headers()['authorization']).toBeUndefined();
      return route.fulfill({ json: { accounts_enabled: true }, headers: { 'Cache-Control': 'no-store' } });
    }
    if (url.pathname === '/api/auth/token') {
      expect(request.postDataJSON()).toEqual({ username: 'synthetic-owner', api_credential: `casak_${'A'.repeat(43)}` });
      return route.fulfill({ json: { token: jwt, expires_in_minutes: 60 } });
    }
    if (url.pathname === '/api/auth/logout') {
      expect(request.headers()['authorization']).toBe(`Bearer ${jwt}`);
      return route.fulfill({ json: { revoked: true } });
    }
    return route.abort();
  });
  await page.goto('/login');
  await page.getByLabel('Email or username').fill('synthetic-owner');
  await page.getByLabel('Account credential', { exact: true }).fill(`casak_${'A'.repeat(43)}`);
  await page.getByRole('button', { name: 'Sign in securely' }).click();
  await expect(page).toHaveURL(/\/model-config$/);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
  expect(requests.filter(path => path.endsWith('/public/capabilities'))).toHaveLength(2);
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByRole('heading', { name: 'Customer account access' })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('cas_harness.account.jwt.v1'))).toBeNull();
  expect(requests.filter(path => path.endsWith('/auth/token'))).toHaveLength(1);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});
