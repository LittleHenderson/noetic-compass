/**
 * API base URL — resolved at build time from VITE_API_URL.
 *
 * - Dev (default):  "/api"  → proxied by Vite to localhost:8000
 * - Production:     Set VITE_API_URL in Vercel env vars to your API origin
 *                   e.g. "https://api.noetic-compass.com"
 */
export const API_BASE = import.meta.env.VITE_API_URL ?? '/api';
