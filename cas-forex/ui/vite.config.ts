import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// vite-plugin-pwa registers a service worker so the app is installable on
// any modern phone via "Add to Home Screen" — no APK, no store, no Android
// Studio required. Existing manifest at public/manifest.webmanifest is used
// as-is so the icon set, theme colour, and shortcuts stay canonical.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      injectRegister: "auto",
      strategies: "generateSW",
      manifestFilename: "manifest.webmanifest",
      manifest: false, // use the existing public/manifest.webmanifest verbatim
      workbox: {
        // A new build must TAKE OVER immediately — the owner should never be
        // stuck on a stale cached shell after an update (2026-07-04). skipWaiting
        // activates the new service worker at once; clientsClaim makes it control
        // already-open tabs; cleanupOutdatedCaches drops the old precache.
        skipWaiting: true,
        clientsClaim: true,
        cleanupOutdatedCaches: true,
        // Precache only the first-paint app shell. Lazy route chunks are still
        // runtime-cached below when the owner actually opens those pages.
        globPatterns: [
          "index.html",
          "registerSW.js",
          "manifest.webmanifest",
          "assets/index-*.css",
          "assets/index-*.js",
          "assets/react-vendor-*.js",
        ],
        // CAS Forex API responses are always live — never cache them in the SW.
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            // Static assets: cache-first, long lived.
            urlPattern: ({ request }) =>
              ["style", "script", "worker", "image", "font"].includes(request.destination),
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: "cas-forex-assets-v1",
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 30 },
            },
          },
        ],
      },
      includeAssets: [
        "icons/cas-forex-192.png",
        "icons/cas-forex-512.png",
      ],
      devOptions: {
        enabled: false,
      },
    }),
  ],
  server: {
    port: 5174,
    open: true,
    proxy: {
      "/api/forex": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (
            id.includes("node_modules/react/")
            || id.includes("node_modules/react-dom/")
            || id.includes("node_modules/scheduler/")
          ) {
            return "react-vendor";
          }
        },
      },
    },
  },
});
