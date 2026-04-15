/**
 * API base URL.
 *
 * - Dev/default: use VITE_API_URL when provided, otherwise "/api"
 * - Production: always use same-origin "/api" and let Vercel rewrite to Railway
 *
 * This avoids stale cross-origin frontend builds breaking after backend URL changes.
 */
export const API_BASE = import.meta.env.PROD
  ? '/api'
  : (import.meta.env.VITE_API_URL ?? '/api');
