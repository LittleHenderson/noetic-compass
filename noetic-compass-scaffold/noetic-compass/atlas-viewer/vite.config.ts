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
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
    css: false,
  },
});
