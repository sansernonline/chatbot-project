// One JSON line per finished case, so results survive a failed test (Playwright restarts the worker)
// and the report is built once at the very end (global teardown).
const fs = require('fs');
const path = require('path');
const { QA_DIR } = require('./testcases');
const report = require('./report');

const OUT_DIR = path.join(QA_DIR, 'results');
const RUN_FILE = path.join(OUT_DIR, '.ui-run.jsonl');

function reset() {
  fs.rmSync(path.join(OUT_DIR, 'screenshots'), { recursive: true, force: true });   // no screenshots left from older runs
  fs.mkdirSync(path.join(OUT_DIR, 'screenshots'), { recursive: true });
  fs.rmSync(RUN_FILE, { force: true });
}
const add = record => fs.appendFileSync(RUN_FILE, JSON.stringify(record) + '\n');

function finish() {
  if (!fs.existsSync(RUN_FILE)) return;
  const rows = fs.readFileSync(RUN_FILE, 'utf8').trim().split('\n').filter(Boolean).map(l => JSON.parse(l));
  if (!rows.length) return;
  const results = {};
  for (const r of rows.sort((a, b) => a.order - b.order)) (results[r.suite] ||= []).push(r);
  report.write(results, OUT_DIR, rows[rows.length - 1].meta);
  fs.rmSync(RUN_FILE, { force: true });
  console.log(`\nเขียนผลที่ ${path.join(OUT_DIR, 'x-fitness-ui-results.md')}`);
}

module.exports = { OUT_DIR, reset, add, finish };
