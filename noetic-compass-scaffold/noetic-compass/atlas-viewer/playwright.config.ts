import { defineConfig, devices } from '@playwright/test';

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
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run preview',
    port: 4173,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
