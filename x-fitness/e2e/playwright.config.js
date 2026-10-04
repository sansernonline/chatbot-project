// Playwright settings. The site under test is the running X Fitness backend (it serves the website).
// E2E_BASE_URL=https://x-fitness-chatbot.onrender.com npm test  → test a deployed site instead of starting one locally.
const { defineConfig } = require('@playwright/test');

const baseURL = process.env.E2E_BASE_URL || 'http://localhost:8000';

module.exports = defineConfig({
  testDir: 'tests',
  globalSetup: './lib/global-setup.js',         // clear the previous run
  globalTeardown: './lib/global-teardown.js',   // write qa/results/x-fitness-ui-results.md
  timeout: 120_000,                 // one case: load page + verify member + wait for the bot (Typhoon can take ~10 s)
  workers: 1,                       // one case at a time: like one customer, and Typhoon rate limits
  reporter: [['list']],
  use: { baseURL, viewport: { width: 1280, height: 900 }, locale: 'th-TH', trace: 'retain-on-failure' },
  // start the backend if nothing is listening yet (needs Python deps + backend/.env, see ../README.md)
  webServer: process.env.E2E_BASE_URL ? undefined : {
    command: 'python -m uvicorn app.main:app --port 8000',
    cwd: '../backend',
    url: `${baseURL}/api/health`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
