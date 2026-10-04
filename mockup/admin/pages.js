/* Back-office pages. Data comes from ../shared/db.js; actions here only change memory (only the inbox is backed by the API). */
const today = new Date().toISOString().slice(0, 10);
const stat = (label, value, sub = '', kind = '') => `<div class="stat ${kind}"><span>${label}</span><b>${value}</b><small>${sub}</small></div>`;
const statusPill = s => pill({ active: 'ใช้งาน', frozen: 'พักสมาชิก', expired: 'หมดอายุ', booked: 'จองแล้ว', cancelled: 'ยกเลิก', no_show: 'ไม่มา', pending_slip: 'รอตรวจสลิป', paid: 'ชำระแล้ว', rejected: 'ไม่ผ่าน', upcoming: 'ยังไม่เริ่ม' }[s] || s,
  { active: 'ok', booked: 'ok', paid: 'ok', frozen: 'warn', pending_slip: 'warn', no_show: 'bad', rejected: 'bad' }[s] || 'dim');
const MEM = { payments: DB.payments.map(p => ({ ...p })) };

PAGES.dashboard = {
  title: 'ภาพรวม',
  render(v) {
    const chats = ChatStore.list(), waiting = chats.filter(c => c.status === 'waiting').length;
    const active = DB.members.filter(m => m.status === 'active').length;
    const slips = MEM.payments.filter(p => p.status === 'pending_slip');
    const hours = [3, 2, 1, 1, 2, 6, 11, 9, 7, 8, 12, 10, 6, 5, 7, 9, 14, 18, 15, 9, 5, 3, 2, 1];
    const max = Math.max(...hours);
    const intents = [['ราคา/แพ็กเกจ', 31], ['ตารางคลาส', 24], ['ส่งสลิป', 14], ['เวลาเปิดปิด', 11], ['แต้ม/ของรางวัล', 8], ['ขอคืนเงิน/ส่วนลด', 5]];
    v.innerHTML = `
      <div class="stats">
        ${stat('แชตวันนี้', fmt(128 + chats.length), 'บอทตอบจบเอง 87%')}
        <a href="#inbox" class="stat ${waiting ? 'alert' : ''}"><span>รอพนักงาน</span><b>${waiting}</b><small>ไปที่กล่องแชต →</small></a>
        ${stat('สลิปรอตรวจ', slips.length, fmt(slips.reduce((s, p) => s + p.amount, 0)) + ' บาท', slips.length ? 'warn' : '')}
        ${stat('สมาชิกใช้งาน', active, `จาก ${DB.members.length} คน`)}
      </div>
      <div class="grid2">
        <section class="card"><h3>จำนวนแชตรายชั่วโมง (วันนี้)</h3>
          <div class="bars">${hours.map((h, i) => `<div title="${String(i).padStart(2, '0')}:00 · ${h} แชต"><i style="height:${h / max * 100}%"></i>${i % 3 ? '' : `<small>${i}</small>`}</div>`).join('')}</div></section>
        <section class="card"><h3>เรื่องที่ถามบ่อย</h3>
          ${intents.map(([l, n]) => `<div class="hbar"><span>${l}</span><i style="--w:${n / intents[0][1] * 100}%"></i><b>${n}%</b></div>`).join('')}</section>
      </div>
      <section class="card"><h3>คลาสวันนี้</h3>${table(['เวลา', 'คลาส', 'ห้อง', 'โค้ช', 'จอง'], todaySlots().map(s => `<tr><td class="mono">${s.start}</td><td>${C(s.class_id).name}</td><td>${C(s.class_id).room}</td><td>${DB.trainers.find(t => t.id === s.trainer_id).nickname}</td><td>${s.taken}/${C(s.class_id).capacity}</td></tr>`))}</section>`;
  }
};
function todaySlots() { const d = new Date().getDay() || 7; return DB.schedule.filter(s => s.day === d).map((s, i) => ({ ...s, taken: Math.min(C(s.class_id).capacity, 8 + (i * 7) % 15) })); }

PAGES.leads = {
  title: 'ผู้สนใจสมัคร (Leads)',
  render(v) {
    const leads = [['LD-001', 'น้องฟ้า', '08x-xxx-1234', 'PKG-STU', 'แชตบอท', 'ใหม่'], ['LD-002', 'คุณบอย', 'LINE @boyfit', 'PKG-ANNUAL', 'หน้าเว็บ', 'โทรแล้ว'], ['LD-003', 'คุณแนน', '09x-xxx-8899', 'PKG-12M', 'แชตบอท', 'นัดทดลอง']];
    v.innerHTML = table(['รหัส', 'ชื่อเล่น', 'ติดต่อ', 'สนใจ', 'ช่องทาง', 'สถานะ', ''], leads.map(l => `<tr><td class="mono">${l[0]}</td><td>${l[1]}</td><td class="mono">${l[2]}</td><td>${P(l[3]).name_th}</td><td>${l[4]}</td><td>${pill(l[5], l[5] === 'ใหม่' ? 'warn' : 'ok')}</td><td><button class="btn ghost sm" data-toast="บันทึกการโทรแล้ว">บันทึกการโทร</button></td></tr>`));
  }
};

PAGES.members = {
  title: 'สมาชิก',
  render(v) {
    v.innerHTML = `<div class="toolbar"><input type="search" id="mSearch" placeholder="ค้นหารหัส ชื่อ หรือเบอร์"><button class="btn red sm" data-toast="ฟอร์มเพิ่มสมาชิก">+ เพิ่มสมาชิก</button></div><div id="mTable"></div>`;
    const draw = q => $('#mTable').innerHTML = table(['รหัส', 'ชื่อ', 'โทร', 'แพ็กเกจ', 'หมดอายุ', 'แต้ม', 'PT คงเหลือ', 'สถานะ'],
      DB.members.filter(m => !q || [m.member_id, m.first_name, m.last_name, m.phone].join(' ').includes(q)).map(m =>
        `<tr><td class="mono">${m.member_id}</td><td>${m.first_name} ${m.last_name}</td><td class="mono">${m.phone}</td><td>${P(m.package_id).name_th}</td><td>${thDate(m.end_date)}</td><td>${fmt(m.points)}</td><td>${m.pt_sessions_left}</td><td>${statusPill(m.status)}</td></tr>`));
    $('#mSearch').oninput = e => draw(e.target.value.trim()); draw('');
  }
};

PAGES.payments = {
  title: 'การชำระเงิน',
  badge: () => MEM.payments.filter(p => p.status === 'pending_slip').length,
  render(v) {
    v.innerHTML = '<div id="payTable"></div>';
    const draw = () => $('#payTable').innerHTML = table(['เลขรายการ', 'สมาชิก', 'รายการ', 'ยอด', 'ครบกำหนด', 'สถานะ', ''], MEM.payments.map(p => {
      const m = M(p.member_id);
      return `<tr><td class="mono">${p.id}</td><td>${p.member_id}<br><small class="dim">${m.first_name} ${m.last_name}</small></td><td>${p.description}</td><td>${fmt(p.amount)}</td><td>${thDate(p.due)}</td><td>${statusPill(p.status)}</td>
        <td>${p.status === 'pending_slip' ? `<button class="btn red sm" data-pay="${p.id}" data-to="paid">ยืนยันชำระ</button> <button class="btn ghost sm" data-pay="${p.id}" data-to="rejected">ไม่ผ่าน</button>` : ''}</td></tr>`;
    }));
    v.onclick = e => { const b = e.target.closest('[data-pay]'); if (!b) return; MEM.payments.find(p => p.id === b.dataset.pay).status = b.dataset.to; draw(); renderNav(); toast('บันทึกแล้ว'); };
    draw();
  }
};

PAGES.bookings = {
  title: 'การจองคลาส',
  render(v) {
    v.innerHTML = table(['เลขจอง', 'วันที่', 'คลาส', 'เวลา', 'สมาชิก', 'สถานะ'], DB.bookings.map(b => {
        const s = DB.schedule.find(x => x.id === b.slot_id);
        return `<tr><td class="mono">${b.id}</td><td>${thDate(b.date)}</td><td>${C(s.class_id).name}</td><td class="mono">${s.day_th} ${s.start}</td><td>${b.member_id}</td><td>${statusPill(b.status)}</td></tr>`;
      }));
  }
};

PAGES.promotions = {
  title: 'โปรโมชัน',
  render(v) {
    v.innerHTML = `<div class="toolbar"><span></span><button class="btn red sm" data-toast="ฟอร์มสร้างโปร">+ สร้างโปรโมชัน</button></div>` +
      table(['โค้ด', 'ชื่อโปร', 'ใช้กับ', 'ช่วงเวลา', 'สถานะ'], DB.promotions.map(p => {
        const st = today < p.start ? 'upcoming' : today > p.end ? 'expired' : 'active';
        return `<tr><td class="mono">${p.code}</td><td>${p.title}<br><small class="dim">${p.detail}</small></td><td>${p.applies_to.map(a => a === 'ALL' ? 'ทุกแพ็กเกจ' : P(a).name_th).join(', ')}</td><td>${thDate(p.start)} – ${thDate(p.end)}</td><td>${statusPill(st)}</td></tr>`;
      }));
  }
};

PAGES.knowledge = {
  title: 'คลังความรู้ (RAG)',
  render(v) {
    const ENGINE = { lightrag: 'LightRAG (กราฟความรู้ + เวกเตอร์)', keyword: 'ค้นด้วยคำ · ยังไม่ได้ตั้ง TYPHOON_API_KEY' };
    const STATUS = { ready: ['พร้อมใช้', 'ok'], indexing: ['กำลังสร้างดัชนี', 'warn'], not_indexed: ['ยังไม่มีดัชนี', 'bad'], keyword: ['ค้นด้วยคำ', 'dim'] };
    const SAMPLE = { engine: 'preview', docs: [['KB-01', 'ข้อมูลทั่วไป เวลาเปิด-ปิด'], ['KB-02', 'แพ็กเกจสมาชิกและราคา'], ['KB-03', 'คลาสและตารางเรียน'], ['KB-04', 'เทรนเนอร์ส่วนตัว'], ['KB-05', 'นโยบาย พัก ยกเลิก คืนเงิน'], ['KB-06', 'การชำระเงินและสลิป'], ['KB-07', 'โปรโมชัน แต้ม สินค้า'], ['KB-08', 'กฎการใช้ยิมและความปลอดภัย'], ['KB-09', 'บริการลูกค้า ติดต่อพนักงาน']].map(([doc_id, title]) => ({ doc_id, title, file: '', status: 'ready' })) };
    const live = ChatStore.online, offline = () => toast('โหมดดูตัวอย่าง · ต้องรัน backend ก่อน');
    v.innerHTML = `<div class="toolbar"><span class="dim" id="kbEngine"></span><label class="btn ghost sm">อัปโหลดเอกสาร (.md)<input type="file" id="kbFile" accept=".md" hidden></label><button class="btn red sm" id="kbReindex">สร้างดัชนีใหม่</button></div>
      <div id="kbList"><div class="empty">กำลังโหลด…</div></div>
      <section class="card"><h3>ทดสอบค้นคลังความรู้</h3><div class="toolbar"><input placeholder="เช่น ยกเลิกสมาชิกต้องแจ้งกี่วัน" id="kbQ"><button class="btn ghost sm" id="kbGo">ค้นหา</button></div><div id="kbRes" class="dim">ผลลัพธ์จะแสดงส่วนของเอกสารที่ใกล้เคียงที่สุด 3 ส่วน</div></section>`;
    const load = async () => {
      try {
        const d = live ? await ChatStore.api('GET', '/api/admin/kb') : SAMPLE;
        $('#kbEngine').textContent = 'ตัวค้น: ' + (ENGINE[d.engine] || 'โหมดดูตัวอย่าง (ไม่ได้รัน backend)');
        $('#kbList').innerHTML = table(['รหัส', 'เอกสาร', 'ไฟล์', 'ดัชนี'], d.docs.map(x => `<tr><td class="mono">${esc(x.doc_id)}</td><td>${esc(x.title)}</td><td class="mono">${esc(x.file)}</td><td>${pill(...(STATUS[x.status] || [x.status, 'dim']))}</td></tr>`));
        if (d.docs.some(x => x.status === 'indexing') && location.hash === '#knowledge') setTimeout(load, 3000);
      } catch (e) { $('#kbList').innerHTML = `<div class="empty">โหลดรายการเอกสารไม่ได้ · ${esc(e.message)} <button class="btn ghost sm" id="kbRetry">ลองใหม่</button></div>`; $('#kbRetry').onclick = load; }
    };
    $('#kbReindex').onclick = async () => {
      if (!live) return offline();
      try { await ChatStore.api('POST', '/api/admin/kb/reindex'); toast('เริ่มสร้างดัชนีแล้ว'); setTimeout(load, 500); } catch (e) { toast('สร้างดัชนีไม่ได้ · ' + e.message); }
    };
    $('#kbFile').onchange = async e => {
      const f = e.target.files[0]; e.target.value = '';
      if (!f) return; if (!live) return offline();
      const fd = new FormData(); fd.append('file', f);
      try { await ChatStore.api('POST', '/api/admin/kb', fd); toast(`อัปโหลด ${f.name} แล้ว กำลังสร้างดัชนี`); setTimeout(load, 500); } catch (err) { toast('อัปโหลดไม่ได้ · ' + err.message); }
    };
    $('#kbGo').onclick = async () => {
      const q = $('#kbQ').value.trim(), res = $('#kbRes');
      if (!q) { res.textContent = 'พิมพ์คำถามก่อน'; return; }
      if (!live) { res.innerHTML = '<ol><li>KB-05 · “ยกเลิกแบบไม่มีสัญญาต้องแจ้งล่วงหน้า 30 วัน…”</li><li>KB-02 · “Monthly Flex ตัดบัตรอัตโนมัติ…”</li><li>KB-05 · “พักสมาชิกได้ 1–3 เดือน…”</li></ol><small>ตัวอย่าง · ไม่ได้รัน backend</small>'; return; }
      res.textContent = 'กำลังค้น…';
      try {
        const { hits } = await ChatStore.api('POST', '/api/admin/kb/search', { q });
        res.innerHTML = hits.length ? `<ol>${hits.map(h => `<li>${esc(h.doc_id || '-')}${h.score != null ? ` · score ${h.score}` : ''} · “${esc(h.text)}…”</li>`).join('')}</ol>` : 'ไม่พบส่วนที่เกี่ยวข้อง';
      } catch (e) { res.textContent = 'ค้นไม่สำเร็จ · ' + e.message; }
    };
    $('#kbQ').onkeydown = e => { if (e.key === 'Enter') $('#kbGo').click(); };
    load();
  }
};

PAGES.bot = {
  title: 'ตั้งค่าบอท',
  render(v) {
    const rules = [['D-03', 'ไม่รู้ให้บอกว่าไม่รู้ และเสนอส่งต่อพนักงาน'], ['D-04', 'ยืนยันตัวตนก่อนเปิดเผยข้อมูลสมาชิก'], ['D-06', 'ตรวจสลิปแล้วส่งพนักงานยืนยัน'], ['N-02', 'ห้ามให้ส่วนลดนอกโปรที่ประกาศ'], ['N-05', 'ห้ามอนุมัติคืนเงินหรือบันทึกการชำระเอง']];
    const sw = (l, d, on) => `<div class="switch"><div>${l}<small>${d}</small></div><button class="sw" role="switch" aria-checked="${on}" data-sw></button></div>`;
    v.innerHTML = `
      <div class="grid2">
        <section class="card"><h3>การทำงาน</h3>
          ${sw('เปิดบอทตอบอัตโนมัติ', 'ปิดแล้วทุกแชตจะเข้ากล่องพนักงาน', true)}
          ${sw('ส่งต่อพนักงานอัตโนมัติเมื่อไม่มั่นใจ', 'คะแนนความมั่นใจต่ำกว่า 0.55', true)}
          ${sw('ตอบนอกเวลาทำการ', 'แจ้งว่าพนักงานจะตอบภายในเวลาทำการ', true)}
          ${sw('วิเคราะห์ภาพ (สลิป ใบเสร็จ ผลวัด)', 'ใช้ vision model', true)}
          <label class="field">โมเดลตอบแชต (ตั้งใน backend/.env)<input readonly value="${esc(ChatStore.health?.model || 'โหมดดูตัวอย่าง')}"></label>
          <label class="field">โมเดลอ่านภาพ (vision)<input readonly value="${esc(ChatStore.health?.vision_model || 'โหมดดูตัวอย่าง')}"></label>
          <label class="field">ตัวค้นคลังความรู้<input readonly value="${esc({ lightrag: 'LightRAG', keyword: 'ค้นด้วยคำ (ไม่มี Typhoon key)' }[ChatStore.health?.rag] || 'โหมดดูตัวอย่าง')}"></label>
          <label class="field">ข้อความต้อนรับ<textarea rows="3">สวัสดีค่ะ เอ็กซ์เป็นผู้ช่วยของ X Fitness ถามเรื่องแพ็กเกจ คลาส เทรนเนอร์ หรือส่งภาพสลิปมาให้ตรวจได้ค่ะ</textarea></label>
          <button class="btn red sm" data-toast="บันทึกแล้ว">บันทึก</button></section>
        <section class="card"><h3>กฎสำคัญ (ตัวอย่างจาก docs/03_bot-rules.md)</h3>
          ${table(['รหัส', 'กฎ'], rules.map(([k, t]) => `<tr><td class="mono">${k}</td><td>${t}</td></tr>`))}</section>
      </div>`;
    v.onclick = e => { const s = e.target.closest('[data-sw]'); if (s) s.setAttribute('aria-checked', s.getAttribute('aria-checked') !== 'true'); };
  }
};

PAGES.reports = {
  title: 'รายงานและบันทึกบอท',
  render(v) {
    const miss = [['มีที่จอดมอเตอร์ไซค์ไหม', 7, 'ไม่มีในคลัง'], ['รับสมัครเทรนเนอร์ไหม', 4, 'ไม่มีในคลัง'], ['ขอใบกำกับภาษีเต็มรูป', 3, 'ส่งต่อพนักงาน'], ['สลิปไม่ชัด', 3, 'วิเคราะห์ภาพไม่ได้']];
    v.innerHTML = `
      <div class="stats">${stat('ความพึงพอใจ', '4.6/5', 'จาก 214 คะแนน')}${stat('ตอบเฉลี่ย', '1.8 วิ', 'บอท')}${stat('พนักงานตอบเฉลี่ย', '6 นาที', 'ในเวลาทำการ')}${stat('ส่งต่อพนักงาน', '9%', 'ของแชตทั้งหมด')}</div>
      <section class="card"><h3>คำถามที่บอทตอบไม่ได้ (7 วัน)</h3>${table(['คำถาม', 'ครั้ง', 'ผล', ''], miss.map(([q, n, r]) => `<tr><td>${q}</td><td>${n}</td><td>${pill(r, 'warn')}</td><td><button class="btn ghost sm" data-toast="เพิ่มเป็น FAQ">เพิ่มเป็น FAQ</button></td></tr>`))}</section>
      <div class="toolbar"><span></span><button class="btn ghost sm" data-toast="ส่งออก CSV">ส่งออก CSV</button></div>`;
  }
};

PAGES.users = {
  title: 'ผู้ใช้และสิทธิ์',
  render(v) {
    const users = [['admin', 'แอดมิน', 'ผู้จัดการสาขา', 'ทุกเมนู'], ['staff01', 'พนักงานเคาน์เตอร์', 'พนักงาน', 'กล่องแชต สมาชิก ตรวจสลิป'], ['coach01', 'โค้ชเก่ง', 'โค้ช', 'การจองคลาส']];
    v.innerHTML = `<div class="toolbar"><span></span><button class="btn red sm" data-toast="เชิญผู้ใช้">+ เพิ่มผู้ใช้</button></div>` +
      table(['ชื่อผู้ใช้', 'ชื่อแสดง', 'บทบาท', 'สิทธิ์', 'เข้าใช้ล่าสุด'], users.map(u => `<tr><td class="mono">${u[0]}</td><td>${u[1]}</td><td>${pill(u[2])}</td><td>${u[3]}</td><td>${u[0] === 'admin' ? 'ตอนนี้' : thDate('2026-10-01')}</td></tr>`));
  }
};

/* buttons whose action is not connected to the backend yet */
const DONE = ['บันทึกแล้ว', 'บันทึกการโทรแล้ว'];
document.addEventListener('click', e => { const b = e.target.closest('[data-toast]'); if (b) toast(DONE.includes(b.dataset.toast) ? b.dataset.toast : `${b.dataset.toast} · เร็ว ๆ นี้`); });
