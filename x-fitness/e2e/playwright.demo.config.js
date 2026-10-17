// Demo video settings: npm run demo → records demo/demo.spec.js, then demo/finish.js builds the mp4 and present page data.
// Raw output (webm, trace) goes to _to_delete/ at the project root; finished files go to present/ and qa/demo/.
const { defineConfig } = require('@playwright/test');
const fs = require('fs');
const base = require('./playwright.config');

// start the backend with its own virtualenv when there is one (the plain `python` may lack the backend's packages)
const venv = ['../backend/.venv/Scripts/python.exe', '../backend/.venv/bin/python'].find(p => fs.existsSync(p));
const webServer = base.webServer && venv ? { ...base.webServer, command: `"${require('path').resolve(venv)}" -m uvicorn app.main:app --port 8000` } : base.webServer;

module.exports = defineConfig({
  ...base,
  testDir: 'demo',
  globalSetup: undefined, globalTeardown: undefined,
  webServer,
  outputDir: '../../_to_delete/e2e-demo',
  use: { ...base.use, viewport: { width: 1280, height: 720 }, video: { mode: 'on', size: { width: 1280, height: 720 } }, trace: 'off' },
});
