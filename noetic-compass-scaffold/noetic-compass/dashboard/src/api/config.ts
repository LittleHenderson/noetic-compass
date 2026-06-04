/**
 * API base URL.
 *
 * - Dev/default: use VITE_API_URL when provided, otherwise "/api"
 * - Vercel production: use same-origin "/api" and let Vercel rewrite to Render
 * - Local static production builds: use the deployed Render API directly
 *
 * The local static case matters for stakeholder demos run from `dist/` with a
 * simple file server. That server can serve JS, but it cannot proxy POST
 * requests to `/api`, so same-origin `/api` fails with "Unsupported method".
 */
const DEPLOYED_API_BASE = 'https://noetic-compass-api.onrender.com';

function isLocalStaticHost(): boolean {
  if (typeof window === 'undefined') return false;
  return ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname);
}

export const API_BASE = import.meta.env.PROD
  ? (isLocalStaticHost() ? DEPLOYED_API_BASE : '/api')
  : (import.meta.env.VITE_API_URL ?? '/api');

/**
 * Mint credential headers for `POST /auth/token` (CAS Harness scoped-beta Phase 1).
 *
 * The API's token mint is locked in production: a request must present the shared
 * `NC_AUTH_MINT_SECRET` or it is refused with 401. The official dashboard build carries
 * the same value via `VITE_AUTH_MINT_SECRET` and sends it as the `X-Auth-Mint-Secret`
 * header. Left unset (local dev against a `debug` API), no header is sent and the open
 * mint still works — so local work is unaffected.
 *
 * Caveat: a secret baked into a client bundle is readable by anyone who downloads the
 * bundle, so this only raises the bar above an anonymous request; it is explicitly an
 * interim Phase-1 measure. Phase 2 replaces the shared secret with per-account issued
 * API keys (the dashboard authenticates the human, not the client build).
 */
export function authMintHeaders(): Record<string, string> {
  const secret = import.meta.env.VITE_AUTH_MINT_SECRET ?? '';
  return secret ? { 'X-Auth-Mint-Secret': secret } : {};
}
