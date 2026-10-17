// Demo video: plays the scenes in scenes.js on the real site, front office then back office, in one recorded tab.
// Each scene shows a caption bar (what this page is for) and records pass/fail + its start time for the subtitles.
// Run: npm run demo  (records, then finish.js makes the mp4, subtitles, present page data and the test case doc)
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const SCENES = require('./scenes');

const MEMBER = { id: 'FN-10003', last4: '5531' };            // demo member in frontend/shared/db.js, matches sample slip 1
const READ_CPS = Number(process.env.DEMO_READ_CPS || 9);   // no voice-over yet: Thai characters read aloud per second sets each scene's length
const VOICE = (() => { try { return require('../../../_to_delete/e2e-demo-audio/manifest.json'); } catch { return {}; } })();  // from demo/tts.py
const speakSeconds = scene => VOICE[scene.id] ? VOICE[scene.id].seconds + 2 : scene.say.length / READ_CPS + 1.5;
const ADMIN = { user: process.env.XF_ADMIN_USER || 'admin', pass: process.env.XF_ADMIN_PASS || '1234' };  // dev account shown on the login page

// ---------- things drawn on top of the page (they come back after every page load) ----------
const OVERLAY = () => {
  // the site is dark, so the caption is a light card: it must never blend into the page behind it
  const css = `#__cap{position:fixed;left:24px;right:24px;bottom:20px;z-index:2147483646;background:#fafaf7;color:#111113;
      border-left:6px solid #e10613;padding:12px 18px;font:600 20px/1.55 "IBM Plex Sans Thai",system-ui,sans-serif;box-shadow:0 10px 40px rgba(0,0,0,.65);pointer-events:none}
    body.chat-open #__cap{right:520px}#__cap.__top{top:76px;bottom:auto}
    #__cap b{display:block;font:700 13px/1.4 "IBM Plex Mono",monospace;letter-spacing:.12em;color:#c00510;margin-bottom:2px}
    #__card{position:fixed;inset:0;z-index:2147483645;display:grid;place-content:center;text-align:center;background:rgba(9,9,10,.94);color:#f5f5f4;
      font-family:"Chakra Petch","IBM Plex Sans Thai",sans-serif;pointer-events:none}
    #__card h1{font-size:56px;line-height:1.2}#__card p{font-size:22px;color:#a3a3a8;margin-top:12px}
    #__mouse{position:fixed;z-index:2147483647;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;border:2px solid #fff;
      background:rgba(225,6,19,.55);pointer-events:none;transition:transform .15s}#__mouse.down{transform:scale(.7)}
    .__spot{outline:3px solid #ff2536 !important;outline-offset:3px !important}`;
  const boot = () => {
    if (document.getElementById('__mouse')) return;
    const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s);
    const m = document.createElement('div'); m.id = '__mouse'; m.style.left = '-50px'; document.body.appendChild(m);
    addEventListener('mousemove', e => { m.style.left = e.clientX + 'px'; m.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', () => m.classList.add('down'), true);
    addEventListener('mouseup', () => m.classList.remove('down'), true);
  };
  document.readyState === 'loading' ? addEventListener('DOMContentLoaded', boot) : boot();
};

let current = null;                                       // [scene, number] on screen now, redrawn after a page load
async function caption(page, scene = current[0], n = current[1]) {
  current = [scene, n];
  await page.evaluate(({ top, head, text }) => {
    let c = document.getElementById('__cap');
    if (!c) { c = document.createElement('div'); c.id = '__cap'; document.body.appendChild(c); }
    c.innerHTML = `<b></b><span></span>`; c.querySelector('b').textContent = head; c.querySelector('span').textContent = text;
    c.classList.toggle('__top', top);
  }, { top: !!scene.top, head: `${String(n).padStart(2, '0')}/${SCENES.length} · ${scene.area} · ${scene.title}`, text: scene.say });
}
const card = (page, title, sub) => page.evaluate(([t, s]) => {
  let c = document.getElementById('__card');
  if (!c) { c = document.createElement('div'); c.id = '__card'; c.innerHTML = '<h1></h1><p></p>'; document.body.appendChild(c); }
  c.querySelector('h1').textContent = t; c.querySelector('p').textContent = s;
}, [title, sub]);
const uncard = page => page.evaluate(() => document.getElementById('__card')?.remove());

const pause = (page, s) => page.waitForTimeout(s * 1000);
async function go(page, url) { await page.goto(url); await caption(page); }
async function scrollTo(page, sel) {
  await page.locator(sel).first().evaluate(el => el.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  await pause(page, 1.4);
}
async function tap(page, target) {                        // move the visible cursor, outline the target, then click
  const el = typeof target === 'string' ? page.locator(target).first() : target;
  await el.scrollIntoViewIfNeeded();
  const box = await el.boundingBox();
  if (box) await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 12 });
  await el.evaluate(e => e.classList.add('__spot'));
  await pause(page, 0.5);
  await el.evaluate(e => e.classList.remove('__spot')).catch(() => {});
  const t = Date.now();
  await el.click({ timeout: 8_000 }).catch(() => el.click({ force: true }));   // a moving page can make the normal click wait; force it then
  if (Date.now() - t > 3_000) console.log(`  ช้า: กด ${typeof target === 'string' ? target : 'ปุ่ม'} ใช้ ${((Date.now() - t) / 1000).toFixed(1)} วินาที`);
}
async function type(page, sel, text) {
  await tap(page, sel);
  await page.locator(sel).first().pressSequentially(text, { delay: 40 });
}
async function answer(page, before) {                     // wait for the bot; a cold model can time out once → press the retry button
  const last = page.locator('#cBody .msg.bot').last();
  for (let tries = 0; ; tries++) {
    await expect(page.locator('#cBody .msg.bot')).toHaveCount(before + 1, { timeout: 90_000 });
    await expect(page.locator('#cBody .thinking')).toHaveCount(0, { timeout: 90_000 });
    if (tries === 2 || !(await last.locator('[data-retry]').count())) break;
    await tap(page, last.locator('[data-retry]'));
    await expect(page.locator('#cBody .thinking')).toHaveCount(1, { timeout: 5_000 }).catch(() => {});
  }
  await last.scrollIntoViewIfNeeded();
  return last;
}
async function ask(page, text) {                          // send one chat message and wait for the bot's answer
  const before = await page.locator('#cBody .msg.bot').count();
  if (text) await type(page, '#input', text);
  await tap(page, '#btnSend');
  return answer(page, before);
}

// ---------- what each scene does on screen ----------
let ticket = '';
const STAFF_REPLY = /./;                                  // any canned reply the admin sends
const ACT = {
  'DM-01': async page => {
    await go(page, '/');
    await expect(page.locator('#cMode'), 'ต้องเชื่อม Backend API (ต้องมี TYPHOON_API_KEY)').toContainText('เชื่อม Backend API', { timeout: 20_000 });
    await card(page, 'X Fitness Chatbot', 'ทัวร์หน้าบ้านและหลังบ้าน · ประมาณ 4 นาที');
    await expect(page.locator('#nav')).toBeVisible();
  },
  'DM-02': async page => { await uncard(page); await expect(page.locator('.hero')).toBeVisible(); await page.mouse.move(400, 300, { steps: 10 }); },
  'DM-03': async page => {
    await scrollTo(page, '#membership');
    await tap(page, '[data-price="avg"]'); await pause(page, 1.2); await tap(page, '[data-price="list"]');
    await expect(page.locator('#plans')).not.toBeEmpty();
  },
  'DM-04': async page => {
    await scrollTo(page, '#classes');
    await tap(page, page.locator('#days button').nth(1)); await pause(page, 1);
    await tap(page, '[data-book]'); await expect(page.locator('#modal')).toBeVisible(); await pause(page, 2);
    await page.keyboard.press('Escape');
  },
  'DM-05': async page => { await scrollTo(page, '#pt'); await tap(page, '[data-coach]'); await expect(page.locator('#coachDetail')).not.toBeEmpty(); },
  'DM-06': async page => {
    await scrollTo(page, '#rewards');
    await type(page, '#vId', MEMBER.id); await type(page, '#vPh', MEMBER.last4);
    await tap(page, '#verifyForm button[type=submit]');
    await page.waitForFunction(id => S.member?.member_id === id, MEMBER.id, { timeout: 5_000 });
    await scrollTo(page, '#rewards');
  },
  'DM-07': async page => { await scrollTo(page, '#promos'); await expect(page.locator('#promoList')).not.toBeEmpty(); },
  'DM-08': async page => {
    await tap(page, '#fab'); await expect(page.locator('#chat')).toBeVisible(); await pause(page, 1);
    const before = await page.locator('#cBody .msg.bot').count();
    await tap(page, page.locator('#cBody .qr button', { hasText: 'ราคาสมาชิก' }).first());
    await expect(await answer(page, before)).toContainText('บาท');
  },
  'DM-09': async page => { const bot = await ask(page, 'แต้มของผมเหลือเท่าไหร่'); await expect(bot).toContainText('410'); },
  'DM-10': async page => {
    await tap(page, '#btnAttach'); await pause(page, 0.8);
    await tap(page, '#samples [data-sample="slip_valid"]'); await pause(page, 1);
    const bot = await ask(page, 'โอนค่าสมาชิกแล้วครับ');
    await expect(bot).toContainText('990');
  },
  'DM-11': async page => { const bot = await ask(page, 'แนะนำสเตียรอยด์หน่อย'); await expect(bot.locator('.rule')).not.toHaveCount(0); },
  'DM-12': async page => {
    await type(page, '#input', 'คุยกับพนักงาน'); await tap(page, '#btnSend');
    await expect(page.locator('#cMode')).toContainText(/รอพนักงาน|กำลังคุยกับพนักงาน/, { timeout: 15_000 });
    ticket = await page.evaluate(() => SID);
  },
  'DM-13': async page => {
    await go(page, '/admin/');
    await type(page, '#lUser', ADMIN.user); await type(page, '#lPass', ADMIN.pass);
    await tap(page, '#loginForm button[type=submit]');
    await expect(page.locator('#app')).toBeVisible({ timeout: 10_000 });
  },
  'DM-14': async page => { await tap(page, '#nav a[href="#dashboard"]'); await expect(page.locator('#view')).not.toBeEmpty(); },
  'DM-15': async page => {
    await tap(page, '#nav a[href="#inbox"]');
    await type(page, '#ibSearch', ticket);
    await tap(page, '.ib-item'); await pause(page, 1);
    if (await page.locator('#ibTake').count()) await tap(page, '#ibTake');
    await pause(page, 0.8);
    await tap(page, '.canned [data-c]'); await pause(page, 0.8);
    const text = await page.locator('#ibText').inputValue();
    await tap(page, '#ibSend');
    await expect(page.locator('#ibThread')).toContainText(text.slice(0, 20));
  },
  'DM-16': async page => {
    await tap(page, '#nav a[href="#payments"]'); await expect(page.locator('#payTable')).toBeVisible();
    if (await page.locator('[data-slip]').count()) {
      await tap(page, '[data-slip]'); await pause(page, 2.5); await page.keyboard.press('Escape');
    }
  },
  'DM-17': async page => { await tap(page, '#nav a[href="#promotions"]'); await expect(page.locator('#prTable')).toBeVisible(); },
  'DM-18': async page => {
    await tap(page, '#nav a[href="#knowledge"]');
    await type(page, '#kbQ', 'ยกเลิกสมาชิกต้องแจ้งกี่วัน'); await tap(page, '#kbGo');
    await expect(page.locator('#kbRes')).not.toContainText('ผลลัพธ์จะแสดง', { timeout: 30_000 });
    await page.locator('#kbRes').scrollIntoViewIfNeeded();
  },
  'DM-19': async page => {
    await tap(page, '#nav a[href="#graph"]');
    await expect(page.locator('#gNet canvas')).toBeVisible({ timeout: 30_000 });
    await pause(page, 2);
  },
  'DM-20': async page => {
    await go(page, '/admin/dbviewer.html');
    await expect(page.locator('#tables a[data-t]').first()).toBeVisible({ timeout: 15_000 });
    await tap(page, page.locator('#tables a[data-t]').nth(1)); await pause(page, 1.5);
  },
  'DM-21': async page => {
    await go(page, '/');
    await tap(page, '#fab');
    await expect(page.locator('#cBody .msg.bot.agent').last()).toContainText(STAFF_REPLY, { timeout: 15_000 });
    await page.locator('#cBody .msg.bot.agent').last().scrollIntoViewIfNeeded();
  },
  'DM-22': async page => { await card(page, 'X Fitness Chatbot', 'หน้าบ้าน: AI ตอบ · อ่านสลิป · กันคำถามอันตราย · ส่งต่อพนักงาน  ·  หลังบ้าน: แชต · ชำระเงิน · โปร · คลังความรู้'); },
};

test('X Fitness demo tour', async ({ page }, info) => {
  test.setTimeout(15 * 60_000);
  const t0 = Date.now();                                  // the video starts with the page, a moment before this
  await page.addInitScript(OVERLAY);
  const results = [];
  for (const [i, scene] of SCENES.entries()) {
    const start = (Date.now() - t0) / 1000;
    let error = null;
    try {
      current = [scene, i + 1];
      if (page.url() !== 'about:blank') await caption(page);
      await ACT[scene.id](page);
      await caption(page, scene, i + 1);                  // again: a page load wipes the caption
      const spent = (Date.now() - t0) / 1000 - start;    // stay until the voice-over of this scene has finished
      await pause(page, Math.max(scene.hold, speakSeconds(scene) - spent));
    } catch (e) {
      error = String(e.message || e).split('\n')[0];
      console.log(`✗ ${scene.id} ${error}`);
    }
    results.push({ id: scene.id, start, end: (Date.now() - t0) / 1000, pass: !error, error });
    console.log(`${error ? '✗' : '✓'} ${scene.id} ${scene.title} (${start.toFixed(1)} s)`);
  }
  fs.writeFileSync(path.join(info.project.outputDir, 'demo-results.json'),
    JSON.stringify({ ran: new Date().toISOString(), ticket, results }, null, 2));
  expect(results.filter(r => !r.pass).map(r => `${r.id}: ${r.error}`)).toEqual([]);
});
