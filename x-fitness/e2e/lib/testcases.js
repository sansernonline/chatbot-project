// Read the report set qa/report/x-fitness-test-cases.md (same file the API script reads; built from the library qa/1-3).
// E2E_CASES=<file or folder> reads another set, e.g. E2E_CASES=../../qa for the whole library (qa/1-questions.md 2-images.md 3-safety.md).
// Each table row under "## 1." … "## 3." is one case ("###" sub-headings stay in the same suite):
// A message cell may hold several messages sent one after another: "msg 1 ⏎ msg 2", and "msg ×N" repeats one N times.
// | รหัส | ข้อความ | ภาพ | สมาชิก | ผลที่คาดหวัง | ต้องมีทุกคำ | ต้องมีอย่างน้อย 1 คำ | ห้ามมี | ตรวจเพิ่ม |
const fs = require('fs');
const path = require('path');

const QA_DIR = path.resolve(__dirname, '../../../qa');
const REPORT_FILE = path.join(QA_DIR, 'report', 'x-fitness-test-cases.md');
const CASES_FILE = process.env.E2E_CASES ? path.resolve(process.env.E2E_CASES) : REPORT_FILE;
const IS_REPORT = CASES_FILE === REPORT_FILE;
const OUT_DIR = process.env.E2E_OUT ? path.resolve(process.env.E2E_OUT)            // E2E_OUT=<folder> for a set kept elsewhere
  : path.join(QA_DIR, IS_REPORT ? 'report' : 'system', 'results');   // results sit next to their set
const SUITES = { 1: 'questions', 2: 'images', 3: 'safety' };

const list = cell => (cell === '-' || !cell ? [] : cell.split(' ; ').map(s => s.trim()).filter(Boolean));

function spec(all, any, none, extra) {
  const s = { all: list(all), any: list(any), none: list(none), vision: {} };
  for (const item of list(extra)) {
    const [key, val] = item.split('=');
    if (key === 'guard') s.rule = val;
    else if (key === 'อ้างอิง') s.source = val;
    else if (key === 'สลิปผ่าน') s.slip = val === 'ใช่';
    else if (key.startsWith('ภาพ.')) s.vision[key.slice(4)] = isNaN(Number(val)) ? val : Number(val);
    else if (key === 'หน้าเว็บแจ้ง') s.error = val;                 // expect this error title on screen (e.g. 429)
    else if (key === 'หมวดอันตราย' && val === 'ไม่มี') s.noHarm = true;   // no S1–S14 label: the message reached the LLM
  }
  return s;
}

function load(file = CASES_FILE) {
  if (fs.statSync(file).isDirectory())                                   // the library: 1-questions.md 2-images.md 3-safety.md
    return fs.readdirSync(file).filter(f => /^\d-.*\.md$/.test(f)).sort().flatMap(f => load(path.join(file, f)));
  const cases = [];
  let suite = null;
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const h = line.match(/^## (\d)\./);
    if (h) { suite = SUITES[h[1]]; continue; }
    if (!suite || !line.startsWith('| ') || line.startsWith('| รหัส') || line.startsWith('|---')) continue;
    const cells = line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
    if (cells.length !== 9) throw new Error(`${path.basename(file)}: ต้องมี 9 ช่อง: ${line.slice(0, 80)}`);
    const [id, message, image, member, expected, all, any, none, extra] = cells;
    cases.push({ suite, id, message, image: image === '-' ? null : image, member: member === '-' ? null : member,
                 expected, spec: spec(all, any, none, extra) });
  }
  return cases;
}

module.exports = { load, QA_DIR, CASES_FILE, OUT_DIR, label: path.relative(path.dirname(QA_DIR), CASES_FILE).replace(/\\/g, '/') };
