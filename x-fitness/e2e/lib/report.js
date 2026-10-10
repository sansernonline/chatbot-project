// Turn the collected results into <set>/results/x-fitness-ui-results.md (+ .json), with links to the screenshots.
const fs = require('fs');
const path = require('path');

const SUITES = {
  questions: ['1. ชุดคำถามทดสอบ', 'ผลตอบที่หน้าเว็บแสดง'],
  images: ['2. ชุดภาพทดสอบ', 'ผลวิเคราะห์ภาพ (JSON ที่หน้าเว็บแสดง) และคำตอบ'],
  safety: ['3. ชุดทดสอบความปลอดภัย', 'มาตรการที่ทำงาน และคำตอบ'],
};
const cell = s => String(s ?? '').replace(/\|/g, '/').replace(/\s*\n\s*/g, ' ').trim();
const avg = xs => (xs.reduce((a, b) => a + b, 0) / (xs.length || 1)).toFixed(1);

function analysis(r) {
  const parts = [];
  if (r.vision) parts.push('อ่านภาพ: ' + Object.entries(r.vision).filter(([k, v]) => k !== 'raw_text' && v != null && v !== '')
    .slice(0, 6).map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`).join(', '));
  parts.push(r.rules.length ? `guard ทำงาน: ${r.rules.join(', ')}` : r.vision ? '' : 'LLM ตอบจากคลังความรู้');
  if (r.quick.length) parts.push(`ปุ่มตอบด่วน: ${r.quick.join(', ')}`);
  return parts.filter(Boolean).join(' · ');
}

function write(results, outDir, meta) {
  fs.mkdirSync(outDir, { recursive: true });
  const all = Object.values(results).flat();
  const lines = [
    '# X Fitness Chatbot — ผลทดสอบผ่านหน้าเว็บ (Playwright)', '',
    '| รายการ | ค่า |', '|---|---|',
    '| โครงงาน | X Fitness Chatbot |', '| ผู้พัฒนา | 68076040 เบญจมาภรณ์ เจียนเกาะ · 68076065 สรรเสริญ มากเจริญ |',
    `| วันเวลาที่ทดสอบ | ${meta.started} |`,
    `| เว็บที่ทดสอบ | ${meta.baseURL} (${meta.mode}) |`,
    `| ชุดทดสอบ | \`${require('./testcases').label}\` ${meta.note} |`,
    '| วิธีทดสอบ | Playwright เปิด Chromium → ยืนยันสมาชิก (ถ้ามี) → เปิดแชต → แนบภาพ/พิมพ์ข้อความ → รอคำตอบ → ตรวจข้อความที่แสดงบนหน้าเว็บ → ถ่ายภาพหน้าจอ |',
    '| เวลาตอบ | วินาที จากกดส่งถึงคำตอบขึ้นบนหน้าจอ (รวมเวลาอ่านภาพ) |', '',
    '## สรุปผล', '', '| ชุดทดสอบ | ผ่าน | ไม่ผ่าน | เวลาตอบเฉลี่ย (วินาที) | เร็วสุด–ช้าสุด |', '|---|---|---|---|---|',
  ];
  for (const [key, [title]] of Object.entries(SUITES)) {
    const rows = results[key] || [];
    if (!rows.length) continue;
    const secs = rows.map(r => r.seconds), ok = rows.filter(r => r.pass).length;
    lines.push(`| ${title.replace(/^\d\. /, '')} | ${ok}/${rows.length} | ${rows.length - ok} | ${avg(secs)} | ${Math.min(...secs)}–${Math.max(...secs)} |`);
  }
  const okAll = all.filter(r => r.pass).length;
  lines.push(`| **รวม** | **${okAll}/${all.length}** | ${all.length - okAll} | ${avg(all.map(r => r.seconds))} | |`);

  for (const [key, [title, col]] of Object.entries(SUITES)) {
    const rows = results[key] || [];
    if (!rows.length) continue;
    lines.push('', `## ${title}`, '', `| รหัส | ข้อมูลเข้า | ผลที่คาดหวัง | ${col} | ผ่าน/ไม่ผ่าน | เวลาตอบ (วินาที) | อ้างอิง | หน้าจอ |`,
               '|---|---|---|---|---|---|---|---|');
    for (const r of rows) {
      const input = (r.image ? `ภาพ ${r.image} · ` : '') + `"${r.message}"` + (r.member ? ` · สมาชิก ${r.member}` : '');
      let got = cell(r.answer).slice(0, 320);
      if (key === 'images' || key === 'safety') got = `**${cell(analysis(r))}** — ${got}`;
      const verdict = r.pass ? '✅ ผ่าน' : `❌ ไม่ผ่าน — ${cell(r.problems.join('; '))}`;
      const notes = r.notes.length ? ` (${cell(r.notes.join('; '))})` : '';
      lines.push(`| ${r.id} | ${cell(input)} | ${cell(r.expected)} | ${got} | ${verdict}${notes} | ${r.seconds} | ${r.sources.join(' ')} | [ภาพ](screenshots/${r.shot}) |`);
    }
  }
  lines.push('', '## หมายเหตุ', '',
    '- ตัดสินผลอัตโนมัติจากข้อความที่หน้าเว็บแสดง ควรให้ผู้ทดสอบอ่านคำตอบและภาพหน้าจอทวน',
    '- "สลิปผ่าน" ตรวจไม่ได้จากหน้าเว็บ (หน้าเว็บไม่แสดงผลตรวจแยก) — ดูจากคำตอบ หรือผลของสคริปต์ API `qa/report/results/x-fitness-api-results.md`',
    '- คำตอบของ LLM ต่างกันได้เล็กน้อยในแต่ละรอบ · ข้อมูลทั้งหมดเป็นข้อมูลจำลอง');
  fs.writeFileSync(path.join(outDir, 'x-fitness-ui-results.md'), lines.join('\n') + '\n');
  fs.writeFileSync(path.join(outDir, 'x-fitness-ui-results.json'), JSON.stringify(results, null, 1));
}

module.exports = { write };
