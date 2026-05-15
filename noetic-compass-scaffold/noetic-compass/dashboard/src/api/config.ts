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
