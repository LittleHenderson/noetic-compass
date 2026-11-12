import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: 'account-auth.isolated.spec.ts',
  outputDir: 'test-results/accounts',
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:4179',
    serviceWorkers: 'block',
    launchOptions: {
      chromiumSandbox: true,
      executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined,
    },
  },
  webServer: {
    command: 'npm run preview -- --host 127.0.0.1 --port 4179 --strictPort',
    url: 'http://127.0.0.1:4179',
    reuseExistingServer: false,
  },
});
