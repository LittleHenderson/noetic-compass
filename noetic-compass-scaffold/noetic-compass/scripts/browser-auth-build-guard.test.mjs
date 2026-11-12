import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const require = createRequire(resolve(process.cwd(), 'package.json'));
const { build } = await import(pathToFileURL(require.resolve('vite')).href);
import { browserAuthBuildGuard, assertSafeBrowserEnvironment, assertSafeBrowserModule } from './browser-auth-build-guard.mjs';

const sentinel = 'SYNTHETIC_MINT_MUST_NOT_SHIP_7b4dc';
test('rejects synthetic browser mint env without echoing its value', () => {
  for (const key of ['VITE_AUTH_MINT_SECRET', 'NC_AUTH_MINT_SECRET']) {
    assert.throws(() => assertSafeBrowserEnvironment({ [key]: sentinel }), (error) =>
      error.message.includes('Remove the shared mint') && !error.message.includes(sentinel));
  }
});
test('account build requires the explicit mode flag', () => {
  for (const value of [undefined, '', 'false', 'TRUE']) {
    assert.throws(() => assertSafeBrowserEnvironment({ VITE_ACCOUNTS_ENABLED: value }, true));
  }
  assertSafeBrowserEnvironment({ VITE_ACCOUNTS_ENABLED: 'true' }, true);
});
test('rejects source references before Vite can inline the credential', () => {
  assert.throws(() => assertSafeBrowserModule('console.log(import.meta.env.VITE_AUTH_MINT_SECRET)'));
  assert.throws(() => assertSafeBrowserModule('const h = { "X-Auth-Mint-Secret": "synthetic" }'));
});
test('bundle hook rejects reintroduced mint headers', () => {
  assert.throws(() => browserAuthBuildGuard().generateBundle({}, {
    'index.js': { type: 'chunk', code: 'fetch("/auth/token", {headers:{"X-Auth-Mint-Secret":"test"}})' },
  }));
});
async function syntheticBundle(code, env = {}) {
  const result = await build({
    configFile: false, envFile: false, logLevel: 'silent', mode: 'accounts',
    plugins: [
      { name: 'synthetic-env', enforce: 'pre', configResolved(config) { Object.assign(config.env, { VITE_ACCOUNTS_ENABLED: 'true' }, env); } },
      browserAuthBuildGuard(),
      { name: 'synthetic-entry', resolveId(id) { if (id === 'fixture.js') return '\0fixture.js'; }, load(id) { if (id === '\0fixture.js') return code; } },
    ],
    build: { write: false, minify: false, rollupOptions: { input: 'fixture.js' } },
  });
  return JSON.stringify(result.output);
}
test('synthetic production build refuses contaminated configuration', async () => {
  await assert.rejects(syntheticBundle('console.log("safe")', { VITE_AUTH_MINT_SECRET: sentinel }), /Remove the shared mint/);
});
test('synthetic production build refuses an imported global mint path', async () => {
  await assert.rejects(syntheticBundle('console.log(import.meta.env.VITE_AUTH_MINT_SECRET)'), /Shared mint credentials/);
});
test('clean synthetic account bundle contains no shared credential', async () => {
  const output = await syntheticBundle('console.log("account credential required")');
  assert.ok(!output.includes(sentinel));
  assert.ok(!/AUTH_MINT_SECRET|X-Auth-Mint-Secret/.test(output));
});
