import { defineConfig, devices } from '@playwright/test';

const previewPort = Number.parseInt(process.env.PLAYWRIGHT_PORT ?? '4173', 10);
if (!Number.isInteger(previewPort) || previewPort < 1 || previewPort > 65535) {
  throw new Error('PLAYWRIGHT_PORT must be an integer between 1 and 65535.');
}
const previewUrl = `http://127.0.0.1:${previewPort}`;

// Atlas Viewer Wave 3: Playwright E2E config.
// - Uses Vite's `preview` server (built bundle) for stable test runs.
// - Chromium only at v0; firefox/webkit are wave-4 follow-ups.
// - HTML report is generated but not auto-opened so CI doesn't block.
export default defineConfig({
  testDir: './e2e',
  outputDir: 'test-results/',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: previewUrl,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: `npm run preview -- --host 127.0.0.1 --port ${previewPort} --strictPort`,
    url: previewUrl,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
