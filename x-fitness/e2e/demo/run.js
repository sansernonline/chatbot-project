// npm run demo: record the tour, then build the outputs even if a scene failed (the doc shows which one).
const { spawnSync } = require('child_process');
spawnSync('python demo/tts.py', { stdio: 'inherit', shell: true, cwd: __dirname + '/..', env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });  // voice-over first: scene lengths follow it
const rec = spawnSync('npx playwright test -c playwright.demo.config.js', { stdio: 'inherit', shell: true, cwd: __dirname + '/..' });
require('./finish');
process.exitCode = rec.status;
