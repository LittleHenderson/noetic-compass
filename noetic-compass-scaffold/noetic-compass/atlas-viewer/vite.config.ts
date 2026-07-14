///<reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

const API_BASE_URL = process.env.ATLAS_API_BASE_URL ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    proxy: {
      // ORDER MATTERS: Vite matches proxy keys in object-insertion order and the
      // first prefix match wins, so the more-specific /api/cas-harness rule must
      // come BEFORE the general /api rule.
      //
      // The two backend routers mount asymmetrically:
      //   - cas_harness_audit router prefix = "/api/cas-harness/audit" (already
      //     includes /api), so its path must be forwarded UNCHANGED.
      //   - atlas_live router prefix = "/atlas/live" (no /api), so /api must be
      //     stripped: /api/atlas/x -> backend /atlas/x.
      // A single /api strip rule would turn /api/cas-harness/audit/x into
      // /cas-harness/audit/x and 404. Keep cas-harness un-rewritten.
      '/api/cas-harness': {
        target: API_BASE_URL,
        changeOrigin: true,
      },
      // Frontend client hits /api/atlas/...; FastAPI mounts /atlas/... under the
      // root. Strip /api when forwarding so /api/atlas/x -> backend /atlas/x.
      // Override with ATLAS_API_BASE_URL env var for non-default backend ports.
      '/api': {
        target: API_BASE_URL,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 350,
    rollupOptions: {
      output: {
        // Manual chunk splitting: isolate Three.js (heavy, only needed on the
        // cockpit route) and React vendor libs so the initial main bundle
        // stays small. All other modules fall back to rollup's default
        // chunking strategy.
        manualChunks: (id: string): string | undefined => {
          if (
            /[\\/]node_modules[\\/]three[\\/]/.test(id) ||
            /[\\/]node_modules[\\/]three-stdlib[\\/]/.test(id) ||
            /three[\\/]examples[\\/]jsm[\\/]/.test(id)
          ) {
            return 'three';
          }
          if (
            /[\\/]node_modules[\\/]react-dom[\\/]/.test(id) ||
            /[\\/]node_modules[\\/]react-router-dom[\\/]/.test(id) ||
            /[\\/]node_modules[\\/]react[\\/]/.test(id)
          ) {
            return 'react-vendor';
          }
          return undefined;
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
    css: false,
    // Exclude Playwright E2E specs; they have a different `test` import surface
    // (@playwright/test) and run via `npm run test:e2e`, not vitest.
    exclude: [
      'node_modules',
      'dist',
      'e2e/**',
      'scripts/**',
      'test-results/**',
      'playwright-report/**',
    ],
  },
});
