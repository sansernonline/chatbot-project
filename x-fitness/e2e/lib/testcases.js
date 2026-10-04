// Read qa/x-fitness-test-cases.md — the test case document the team edits (same file the API script reads).
// Each table row under "## 1." … "## 4." is one case:
// | รหัส | ข้อความ | ภาพ | สมาชิก | ผลที่คาดหวัง | ต้องมีทุกคำ | ต้องมีอย่างน้อย 1 คำ | ห้ามมี | ตรวจเพิ่ม |
const fs = require('fs');
const path = require('path');

const QA_DIR = path.resolve(__dirname, '../../../qa');
const CASES_FILE = path.join(QA_DIR, 'x-fitness-test-cases.md');
const SUITES = { 1: 'questions', 2: 'images', 3: 'safety', 4: 'rules' };

const list = cell => (cell === '-' || !cell ? [] : cell.split(' ; ').map(s => s.trim()).filter(Boolean));

function spec(all, any, none, extra) {
  const s = { all: list(all), any: list(any), none: list(none), vision: {} };
  for (const item of list(extra)) {
    const [key, val] = item.split('=');
    if (key === 'guard') s.rule = val;
    else if (key === 'อ้างอิง') s.source = val;
    else if (key === 'สลิปผ่าน') s.slip = val === 'ใช่';
    else if (key.startsWith('ภาพ.')) s.vision[key.slice(4)] = isNaN(Number(val)) ? val : Number(val);
  }
  return s;
}

function load(file = CASES_FILE) {
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

module.exports = { load, QA_DIR, CASES_FILE };
