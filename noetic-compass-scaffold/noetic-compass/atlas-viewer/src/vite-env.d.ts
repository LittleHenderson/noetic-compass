/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Absolute base URL for the Atlas backend API, injected at build time.
   *
   * Unset in `vite dev` (the dev server proxies `/api/atlas` to the backend).
   * Set in production builds so the frontend served from atlas.noeticcompass.com
   * can call atlas-api.noeticcompass.com directly without a same-origin proxy.
   */
  readonly VITE_ATLAS_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
