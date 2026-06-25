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
        globPatterns: ["**/*.{js,css,html,svg,png,ico,webmanifest,json}"],
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
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
