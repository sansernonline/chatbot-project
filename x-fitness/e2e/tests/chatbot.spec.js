// Use the X Fitness website like a customer, one case per test, cases from qa/x-fitness-test-cases.md.
// Knows the site only by what a customer sees (element ids, text) — no chatbot code is imported.
//
// E2E_SUITES=questions,images   only these suites        E2E_RULES=10 E2E_SEED=7   random sample of suite 4
const { test, expect } = require('@playwright/test');
const path = require('path');
const testcases = require('../lib/testcases');
const runFile = require('../lib/run-file');

const IMAGES_DIR = path.join(testcases.QA_DIR, 'test-images');   // test assets live with the test cases
const suites = (process.env.E2E_SUITES || 'questions,images,safety,rules').split(',');
const seed = Number(process.env.E2E_SEED || Math.floor(Math.random() * 1000));

function pick(cases) {
  const rules = cases.filter(c => c.suite === 'rules');
  const n = Number(process.env.E2E_RULES || rules.length);
  let s = seed;                                               // small seeded shuffle so a draw can be repeated
  const rand = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  const sample = [...rules].sort(() => rand() - 0.5).slice(0, n);
  return cases.filter(c => suites.includes(c.suite) && (c.suite !== 'rules' || sample.includes(c)));
}

const CASES = pick(testcases.load());
const meta = { started: new Date().toLocaleString('th-TH'), baseURL: '', mode: '',
               note: `· สุ่มหมวด 4: ${process.env.E2E_RULES ? `${process.env.E2E_RULES} ข้อ (E2E_SEED=${seed})` : 'ทุกข้อ'}` };

const norm = s => s.replace(/,/g, '');
function check(spec, r) {
  const a = norm(r.answer), problems = [], notes = [];
  const miss = spec.all.filter(w => !a.includes(norm(w)));
  if (miss.length) problems.push(`ไม่มี ${miss.join(', ')}`);
  if (spec.any.length && !spec.any.some(w => a.includes(norm(w)))) problems.push(`ไม่มีคำใดใน [${spec.any.join(', ')}]`);
  const bad = spec.none.filter(w => a.includes(norm(w)));
  if (bad.length) problems.push(`มีคำต้องห้าม ${bad.join(', ')}`);
  if (spec.rule && !r.rules.includes(spec.rule)) problems.push(`guard ไม่ทำงาน (ต้องมี ${spec.rule})`);
  if (spec.source && !r.sources.includes(spec.source)) problems.push(`ไม่อ้าง ${spec.source}`);
  for (const [k, want] of Object.entries(spec.vision)) {
    const got = r.vision?.[k];
    if (typeof want === 'number' ? Math.abs(Number(got) - want) > 0.01 : got !== want) problems.push(`อ่านภาพ ${k}=${got} (ควรเป็น ${want})`);
  }
  if ('slip' in spec) notes.push('สลิปผ่าน ตรวจได้เฉพาะสคริปต์ API');
  if (r.error) problems.push(`หน้าเว็บแสดง error: ${r.error}`);
  return { problems, notes };
}

CASES.forEach((c, i) => {
  const shot = `${String(i + 1).padStart(2, '0')}-${c.id}.png`;     // ids can repeat (one rule, two tests)
  test(`${String(i + 1).padStart(2, '0')} ${c.id} ${c.message.slice(0, 40)}`, async ({ page, baseURL }) => {
    await page.goto('/');
    meta.baseURL = baseURL;
    // the site switches itself to the real backend when /api/health says the LLM is ready
    await expect(page.locator('#cMode'), 'หน้าเว็บต้องเชื่อม Backend API (ต้องมี TYPHOON_API_KEY)').toContainText('เชื่อม Backend API', { timeout: 15_000 });
    meta.mode = (await page.locator('#cMode').innerText()).trim();

    if (c.member) {                                           // verify like a customer, with the member's own last 4 digits
      const last4 = await page.evaluate(id => DB.members.find(m => m.member_id === id)?.phone.replace(/\D/g, '').slice(-4), c.member);
      await page.fill('#vId', c.member);
      await page.fill('#vPh', last4 || '0000');
      await page.locator('#verifyForm button[type=submit]').click();
      await page.waitForFunction(id => S.member?.member_id === id, c.member, { timeout: 5_000 });
    }

    await page.click('#fab');
    if (c.image) await page.setInputFiles('#file', path.join(IMAGES_DIR, c.image));
    if (c.message) await page.fill('#input', c.message);
    const before = await page.locator('#cBody .msg.bot').count();
    const t0 = Date.now();
    await page.click('#btnSend');
    await expect(page.locator('#cBody .msg.bot')).toHaveCount(before + 1, { timeout: 90_000 });
    await expect(page.locator('#cBody .thinking')).toHaveCount(0);
    const seconds = Math.round((Date.now() - t0) / 100) / 10;

    const bot = page.locator('#cBody .msg.bot').last();
    const r = await bot.evaluate(el => {
      const b = el.querySelector('.b').cloneNode(true);
      const details = b.querySelector('details.vision');
      let vision = null;
      if (details) { try { vision = JSON.parse(details.textContent.replace(details.querySelector('summary').textContent, '')); } catch {} details.remove(); }
      return { answer: b.innerText.trim(), vision, error: el.querySelector('.err-b') ? b.innerText.trim() : null,
               sources: [...el.querySelectorAll('.src')].map(x => x.textContent.trim()),
               rules: [...el.querySelectorAll('.rule')].map(x => x.textContent.trim()),
               quick: [...el.querySelectorAll('.qr button')].map(x => x.textContent.trim()) };
    });
    await page.locator('#chat').screenshot({ path: path.join(runFile.OUT_DIR, 'screenshots', shot) });

    const { problems, notes } = check(c.spec, r);
    runFile.add({ ...c, ...r, order: i, shot, seconds, pass: problems.length === 0, problems, notes, meta });
    expect(problems, `${c.id}: ${c.expected}`).toEqual([]);
  });
});
