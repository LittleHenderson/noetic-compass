// Browser builds must never contain the legacy shared mint credential.
const forbidden = /(?:VITE_|NC_)?AUTH_MINT_SECRET|X-Auth-Mint-Secret/i;

export function assertSafeBrowserModule(code, label = 'browser module') {
  if (forbidden.test(code)) throw new Error(`Shared mint credentials are forbidden in ${label}.`);
}

export function assertSafeBrowserEnvironment(env, requireAccounts = false) {
  for (const key of Object.keys(env)) {
    if (forbidden.test(key) && String(env[key] ?? '').trim()) {
      // Never include the value in errors or logs.
      throw new Error('Remove the shared mint credential from the browser build environment.');
    }
  }
  if (requireAccounts && env.VITE_ACCOUNTS_ENABLED?.trim() !== 'true') {
    throw new Error('Account builds require VITE_ACCOUNTS_ENABLED=true.');
  }
}

export function browserAuthBuildGuard() {
  return {
    name: 'browser-auth-build-guard',
    enforce: 'pre',
    configResolved(config) {
      assertSafeBrowserEnvironment({ ...process.env, ...config.env }, config.mode === 'accounts');
    },
    transform(code, id) {
      if (!id.includes('node_modules') && /\.[cm]?[jt]sx?(?:\?|$)/.test(id)) {
        assertSafeBrowserModule(code);
      }
      return null;
    },
    generateBundle(_options, bundle) {
      for (const output of Object.values(bundle)) {
        const source = output.type === 'chunk' ? output.code : output.source;
        assertSafeBrowserModule(typeof source === 'string' ? source : new TextDecoder().decode(source), 'browser bundle');
      }
    },
  };
}
