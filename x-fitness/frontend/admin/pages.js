/* Back-office pages. With the backend running, the dashboard, payments, bookings and promotions come from /api/admin/*
   (backoffice.py): changes are saved and the bot uses them on the next message. Without it (preview) they use
   ../shared/db.js and changes stay in memory. Leads are read-only; members are too, except website sign-ups (status pending)
   that staff confirm or turn down. */
const today = new Date().toISOString().slice(0, 10);
const stat = (label, value, sub = '', kind = '') => `<div class="stat ${kind}"><span>${label}</span><b>${value}</b><small>${sub}</small></div>`;
const linkStat = (href, label, value, sub = '', kind = '') => `<a href="${href}" class="stat ${kind}"><span>${label}</span><b>${value}</b><small>${sub}</small></a>`;
const statusPill = s => pill({ pending: 'สมัครใหม่ รอยืนยัน', active: 'ใช้งาน', inactive: 'ปิดอยู่', frozen: 'พักสมาชิก', expired: 'หมดอายุ', booked: 'จองแล้ว', cancelled: 'ยกเลิก', no_show: 'ไม่มา', awaiting_slip: 'ยังไม่ส่งสลิป', pending_slip: 'รอตรวจสลิป', paid: 'ชำระแล้ว', rejected: 'ไม่ผ่าน', upcoming: 'ยังไม่เริ่ม' }[s] || s,
  { active: 'ok', booked: 'ok', paid: 'ok', pending: 'warn', frozen: 'warn', pending_slip: 'warn', no_show: 'bad', rejected: 'bad' }[s] || 'dim');

/* ---------- business data: backend when online, else db.js in memory ---------- */
const TEST_IMG = location.protocol === 'file:' ? '../../qa/test-images/' : '../qa/';
const MEM = {
  payments: DB.payments.map(p => ({ ...p, slips: p.slip_image ? [{ sample: true, url: TEST_IMG + p.slip_image }] : [] })),
  bookings: DB.bookings.map(b => ({ ...b })),
  promotions: DB.promotions.map(p => ({ ...p }))
};
const BO = {
  async list(kind) { if (ChatStore.online) MEM[kind] = await ChatStore.api('GET', `/api/admin/${kind}`); return MEM[kind]; },
  async set(kind, id, status) {
    if (ChatStore.online) await ChatStore.api('PATCH', `/api/admin/${kind}/${id}`, { status });
    MEM[kind].find(x => x.id === id).status = status;
  },
  async reset() {
    if (!ChatStore.online) return toast('โหมดดูตัวอย่าง · ต้องรัน backend ก่อน');
    await ChatStore.api('POST', '/api/admin/test-data/reset'); toast('กลับเป็นข้อมูลตั้งต้นแล้ว'); route();
  }
};
const liveNote = () => ChatStore.online ? pill('ข้อมูลจาก backend · บอทใช้ค่านี้ทันที', 'ok') : pill('โหมดดูตัวอย่าง · ไม่ได้บันทึก', 'dim');
const resetBtn = '<button class="btn ghost sm" data-reset title="ล้างสถานะที่เปลี่ยนและสลิปที่ลูกค้าส่ง กลับเป็นข้อมูลตั้งต้น">รีเซ็ตข้อมูลทดสอบ</button>';
const left = id => (location.hash.slice(1) || 'dashboard') !== id;   // the user moved to another page while this one was loading
const loadFail = (v, e) => v.innerHTML = `<div class="empty">โหลดข้อมูลไม่ได้ · ${esc(e.message)}</div>`;
document.addEventListener('click', e => {
  if (e.target.closest('[data-reset]') && confirm('ล้างสถานะที่เปลี่ยนและสลิปที่ลูกค้าส่งทั้งหมด กลับเป็นข้อมูลตั้งต้น?')) BO.reset().catch(err => toast('รีเซ็ตไม่ได้ · ' + err.message));
});

PAGES.dashboard = {
  title: 'ภาพรวม',
  render(v) {
    if (!ChatStore.online) return drawDashboard(v, sampleDashboard());
    v.innerHTML = '<div class="empty">กำลังโหลด…</div>';
    ChatStore.api('GET', '/api/admin/dashboard').then(d => { if (left('dashboard')) return; drawDashboard(v, d); BO.list('payments').then(renderNav).catch(() => {}); }).catch(e => left('dashboard') || loadFail(v, e));
  }
};
function drawDashboard(v, d) {
  const max = Math.max(1, ...d.messages_by_hour), topMax = Math.max(1, ...d.handoff_topics.map(t => t[1]));
  v.innerHTML = `
    <div class="toolbar"><span class="dim">${d.sample ? pill('ตัวอย่าง · ไม่ได้รัน backend', 'dim') : `ข้อมูลจริง ณ ${thDate(d.today)}`}</span></div>
    <div class="stats">
      ${stat('แชตวันนี้', fmt(d.chats_today), `ทั้งหมด ${fmt(d.chats_total)} แชต`)}
      ${linkStat('#inbox', 'รอพนักงาน', d.waiting, 'ไปที่กล่องแชต →', d.waiting ? 'alert' : '')}
      ${linkStat('#payments', 'สลิปรอตรวจ', d.slips_pending.count, `${fmt(d.slips_pending.amount)} บาท · ยังไม่ส่งสลิป ${d.awaiting_slip}`, d.slips_pending.count ? 'warn' : '')}
      ${stat('สมาชิกใช้งาน', d.members_active, `จาก ${d.members_total} คน`)}
      ${linkStat('#members', 'สมัครใหม่รอยืนยัน', d.signups_pending, 'สมัครจากหน้าเว็บ →', d.signups_pending ? 'warn' : '')}
      ${linkStat('#bookings', 'การจองที่จะถึง', d.bookings_upcoming, 'ตั้งแต่วันนี้ →')}
      ${linkStat('#promotions', 'โปรที่เปิดอยู่', d.promotions_active, 'เปิด/ปิดได้ →')}
    </div>
    <div class="grid2">
      <section class="card"><h3>ข้อความจากลูกค้ารายชั่วโมง (วันนี้)</h3>
        <div class="bars">${d.messages_by_hour.map((h, i) => `<div title="${String(i).padStart(2, '0')}:00 · ${h} ข้อความ"><i style="height:${h / max * 100}%"></i>${i % 3 ? '' : `<small>${i}</small>`}</div>`).join('')}</div></section>
      <section class="card"><h3>เรื่องที่ลูกค้าขอคุยกับพนักงาน</h3>
        ${d.handoff_topics.length ? d.handoff_topics.map(([l, n]) => `<div class="hbar"><span>${esc(l)}</span><i style="--w:${n / topMax * 100}%"></i><b>${n}</b></div>`).join('') : '<div class="empty">ยังไม่มีการส่งต่อพนักงาน</div>'}</section>
    </div>
    <section class="card"><h3>คลาสวันนี้</h3>${table(['เวลา', 'คลาส', 'ห้อง', 'โค้ช', 'จอง'], d.classes_today.map(s => `<tr><td class="mono">${s.start}</td><td>${C(s.class_id).name}</td><td>${C(s.class_id).room}</td><td>${DB.trainers.find(t => t.id === s.trainer_id).nickname}</td><td>${s.booked}/${C(s.class_id).capacity}</td></tr>`))}</section>`;
}
function sampleDashboard() {   // preview mode: sample numbers, shaped like GET /api/admin/dashboard
  const chats = ChatStore.list(), pays = MEM.payments, pend = pays.filter(p => p.status === 'pending_slip'), d = new Date().getDay() || 7;
  return { sample: true, today, chats_today: 128 + chats.length, chats_total: 128 + chats.length, waiting: chats.filter(c => c.status === 'waiting').length,
    messages_by_hour: [3, 2, 1, 1, 2, 6, 11, 9, 7, 8, 12, 10, 6, 5, 7, 9, 14, 18, 15, 9, 5, 3, 2, 1],
    handoff_topics: [['ขอคืนเงิน', 5], ['สลิปไม่ผ่าน', 4], ['ขอส่วนลดพิเศษ', 3], ['ยกเลิกสมาชิก', 2]],
    slips_pending: { count: pend.length, amount: pend.reduce((s, p) => s + p.amount, 0) }, awaiting_slip: pays.filter(p => p.status === 'awaiting_slip').length,
    members_active: DB.members.filter(m => m.status === 'active').length, members_total: DB.members.length, signups_pending: DB.members.filter(m => m.status === 'pending').length,
    bookings_upcoming: MEM.bookings.filter(b => b.status === 'booked' && b.date >= today).length, promotions_active: MEM.promotions.filter(p => p.status === 'active').length,
    classes_today: DB.schedule.filter(s => s.day === d).map((s, i) => ({ ...s, booked: Math.min(C(s.class_id).capacity, 8 + (i * 7) % 15) })) };
}

PAGES.leads = {
  title: 'ผู้สนใจสมัคร (Leads)',
  render(v) {
    const CH = { web_chat: 'แชตบนเว็บ', line: 'LINE', walk_in: 'หน้าร้าน' }, ST = { new: ['ใหม่', 'warn'], contacted: ['ติดต่อแล้ว', 'ok'], trial: ['นัดทดลอง', 'ok'], lost: ['ไม่สนใจ', 'dim'] };
    const interest = id => P(id)?.name_th || DB.pt.find(x => x.id === id)?.name || id;
    v.innerHTML = table(['รหัส', 'ชื่อเล่น', 'สนใจ', 'ช่องทาง', 'วันที่', 'สถานะ', ''], (DB.leads || []).map(l => `<tr><td class="mono">${esc(l.id)}</td><td>${esc(l.nickname)}</td><td>${esc(interest(l.interest))}</td><td>${CH[l.channel] || esc(l.channel)}</td><td>${thDate(l.created)}</td><td>${pill(...(ST[l.status] || [l.status, 'dim']))}</td><td><button class="btn ghost sm" data-toast="บันทึกการโทรแล้ว">บันทึกการโทร</button></td></tr>`));
  }
};

PAGES.members = {
  title: 'สมาชิก',
  badge: () => DB.members.filter(m => m.status === 'pending').length,
  async render(v) {
    v.innerHTML = `<div class="toolbar"><input type="search" id="mSearch" placeholder="ค้นหารหัส ชื่อ หรือเบอร์"><select id="mFilter" style="max-width:220px"><option value="">ทุกสถานะ</option><option value="pending">สมัครใหม่ รอยืนยัน</option><option value="active">ใช้งาน</option><option value="frozen">พักสมาชิก</option><option value="expired">หมดอายุ</option><option value="cancelled">ยกเลิก (ไม่อนุมัติ)</option><option value="owing">มียอดค้างชำระ</option></select><button class="btn red sm" data-toast="ฟอร์มเพิ่มสมาชิก">+ เพิ่มสมาชิก</button></div>
      <p class="hint">${liveNote()} ลูกค้าสมัครจากปุ่ม <b>สมัครสมาชิก</b> บนหน้าเว็บ → ขึ้นที่นี่สถานะ <b>สมัครใหม่ รอยืนยัน</b> พร้อมรายการชำระในหน้า <a href="#payments">การชำระเงิน</a> · ตรวจชื่อ เบอร์ และสลิป แล้วกด <b>ยืนยันสมาชิก</b> (จองคลาสได้ทันที) หรือ <b>ไม่อนุมัติ</b></p>
      <div id="mTable"><div class="empty">กำลังโหลด…</div></div>`;
    if (ChatStore.online) try { DB.members = await ChatStore.api('GET', '/api/admin/members'); MEM.payments = await ChatStore.api('GET', '/api/admin/payments'); } catch (e) { return left('members') || loadFail($('#mTable'), e); }
    if (left('members')) return;
    const owing = id => MEM.payments.filter(p => p.member_id === id && ['awaiting_slip', 'pending_slip'].includes(p.status));   // unpaid: no slip yet · slip waiting for staff (business.DUE)
    const dupe = m => DB.members.find(x => x.member_id !== m.member_id && x.phone === m.phone && x.status !== 'cancelled');
    const draw = () => {
      const q = $('#mSearch').value.trim(), f = $('#mFilter').value;
      const rows = DB.members.filter(m => (!q || [m.member_id, m.first_name, m.last_name, m.phone].join(' ').includes(q)) && (!f || (f === 'owing' ? owing(m.member_id).length : m.status === f)))
        .sort((a, b) => (b.status === 'pending') - (a.status === 'pending'));
      $('#mTable').innerHTML = table(['รหัส', 'ชื่อ', 'โทร', 'แพ็กเกจ', 'หมดอายุ', 'แต้ม', 'PT คงเหลือ', 'ยอดค้างชำระ', 'สถานะ', ''], rows.map(m => {
        const due = owing(m.member_id), d = m.status === 'pending' && dupe(m);
        const dueCell = due.length ? `<b>${fmt(due.reduce((t, p) => t + p.amount, 0))} บาท</b>${due.map(p => `<br><a href="#payments" class="dim"><small>${p.id} · ${fmt(p.amount)}</small></a> ${statusPill(p.status)}`).join('')}` : '<span class="dim">ไม่มี</span>';
        const act = m.status === 'pending' ? `<button class="btn red sm" data-member="${m.member_id}" data-to="active">ยืนยันสมาชิก</button> <button class="btn ghost sm" data-member="${m.member_id}" data-to="cancelled">ไม่อนุมัติ</button>`
          : m.status === 'cancelled' ? `<button class="btn ghost sm" data-member="${m.member_id}" data-to="pending">ย้อนสถานะ</button>` : '';
        return `<tr><td class="mono">${m.member_id}</td><td>${esc(m.first_name)} ${esc(m.last_name)}${d ? `<br>${pill(`เบอร์ซ้ำกับ ${d.member_id}`, 'bad')}` : ''}</td><td class="mono">${esc(m.phone || '')}</td><td>${P(m.package_id).name_th}</td><td>${thDate(m.end_date)}</td><td>${fmt(m.points)}</td><td>${m.pt_sessions_left}</td><td>${dueCell}</td><td>${statusPill(m.status)}</td><td>${act}</td></tr>`;
      }));
    };
    $('#mSearch').oninput = draw; $('#mFilter').onchange = draw;
    if (DB.members.some(m => m.status === 'pending')) $('#mFilter').value = 'pending';
    draw();
    v.onclick = async e => {
      const b = e.target.closest('[data-member]'); if (!b) return;
      const m = DB.members.find(x => x.member_id === b.dataset.member);
      try {
        if (ChatStore.online) Object.assign(m, await ChatStore.api('PATCH', `/api/admin/members/${m.member_id}`, { status: b.dataset.to }));
        else m.status = b.dataset.to;
        if (!DB.members.some(x => x.status === 'pending') && $('#mFilter').value === 'pending') $('#mFilter').value = '';   // last sign-up done: show everyone
        draw(); renderNav(); toast(b.dataset.to === 'active' ? `ยืนยัน ${m.member_id} เป็นสมาชิกแล้ว` : 'บันทึกแล้ว');
      } catch (err) { toast('บันทึกไม่ได้ · ' + err.message); }
    };
  }
};

PAGES.payments = {
  title: 'การชำระเงิน',
  badge: () => MEM.payments.filter(p => p.status === 'pending_slip').length,
  async render(v) {
    const FILTER = [['', 'ทุกสถานะ'], ['pending_slip', 'รอตรวจสลิป'], ['awaiting_slip', 'ยังไม่ส่งสลิป'], ['paid', 'ชำระแล้ว'], ['rejected', 'ไม่ผ่าน']];
    v.innerHTML = `<div class="toolbar"><select id="payFilter" style="max-width:200px">${FILTER.map(([k, l]) => `<option value="${k}">${l}</option>`).join('')}</select><span>${liveNote()} ${resetBtn}</span></div>
      <p class="hint">ทดสอบส่งสลิป: ที่หน้าเว็บยืนยันตัวตน <b>FN-10003</b> เบอร์ <b>5531</b> แล้วส่งภาพ 01_slip_valid.png (ผู้โอน ภาคิน) → สลิปขึ้นที่ PAY-2609-003 และผ่านครบ 6 ข้อ · <b>FN-10005</b> เบอร์ <b>1846</b> ส่ง 02_slip_amount_mismatch.png → ไม่ผ่าน ขาด 600 บาท</p>
      <div id="payTable"><div class="empty">กำลังโหลด…</div></div>`;
    try { await BO.list('payments'); } catch (e) { return left('payments') || loadFail($('#payTable'), e); }
    if (left('payments')) return;
    const verdict = s => s?.checks?.length ? pill(s.ok ? `ตรวจผ่าน ${s.checks.length}/${s.checks.length}` : `ไม่ผ่าน ${s.checks.filter(c => !c.pass).length} ข้อ`, s.ok ? 'ok' : 'bad') : '';
    const draw = () => {
      const f = $('#payFilter').value;
      $('#payTable').innerHTML = table(['เลขรายการ', 'สมาชิก', 'รายการ', 'ยอด', 'ครบกำหนด', 'สลิป', 'สถานะ', ''], MEM.payments.filter(p => !f || p.status === f).map(p => {
        const m = M(p.member_id), last = p.slips.at(-1);
        const slip = p.slips.length ? `<button class="btn ghost sm" data-slip="${p.id}">ดูสลิป${p.slips.length > 1 ? ` (${p.slips.length})` : ''}</button> ${verdict(last)}` : '<span class="dim">ยังไม่ส่ง</span>';
        const act = p.status === 'pending_slip' ? `<button class="btn red sm" data-pay="${p.id}" data-to="paid">ยืนยันชำระ</button> <button class="btn ghost sm" data-pay="${p.id}" data-to="rejected">ไม่ผ่าน</button>`
          : ['paid', 'rejected'].includes(p.status) ? `<button class="btn ghost sm" data-pay="${p.id}" data-to="${p.slips.length ? 'pending_slip' : 'awaiting_slip'}">ย้อนสถานะ</button>` : '';
        return `<tr><td class="mono">${p.id}</td><td>${p.member_id}<br><small class="dim">${esc(p.member_name || `${m.first_name} ${m.last_name}`)}</small></td><td>${esc(p.description)}${p.test_note ? `<br><small class="dim">${esc(p.test_note)}</small>` : ''}</td><td>${fmt(p.amount)}</td><td>${thDate(p.due)}</td><td>${slip}</td><td>${statusPill(p.status)}</td><td>${act}</td></tr>`;
      }));
    };
    $('#payFilter').onchange = draw;
    v.onclick = async e => {
      const s = e.target.closest('[data-slip]'); if (s) return showSlips(MEM.payments.find(p => p.id === s.dataset.slip));
      const b = e.target.closest('[data-pay]'); if (!b) return;
      try { await BO.set('payments', b.dataset.pay, b.dataset.to); draw(); renderNav(); toast('บันทึกแล้ว'); } catch (err) { toast('บันทึกไม่ได้ · ' + err.message); }
    };
    draw(); renderNav();
  }
};
// slip viewer: seed samples are public test images; slips customers sent need the admin token (fetched as a blob)
function showSlips(p) {
  let dlg = $('#slipDlg');
  if (!dlg) { document.body.insertAdjacentHTML('beforeend', '<dialog id="slipDlg" class="dlg"></dialog>'); dlg = $('#slipDlg'); dlg.onclick = e => { if (e.target === dlg || e.target.closest('[data-close]')) dlg.close(); }; }
  const slips = p.slips.slice().reverse();   // newest first
  dlg.innerHTML = `<div class="dlg-head"><b>สลิป ${esc(p.id)} · ${esc(p.member_id)} · ยอดค้าง ${fmt(p.amount)} บาท</b><button class="btn ghost sm" data-close>ปิด</button></div>
    <div class="dlg-body">${slips.map((s, i) => `<figure class="slip"><div class="slip-img" data-i="${i}">กำลังโหลดภาพ…</div><figcaption>
      ${s.sample ? pill('ภาพตัวอย่างจากข้อมูลตั้งต้น', 'dim') : `ส่งเมื่อ ${thDate(s.at)} ${thTime(s.at)} · ยอดในสลิป ${s.amount != null ? fmt(s.amount) + ' บาท' : '-'}`}
      ${s.checks?.length ? `<ul class="checks">${s.checks.map(c => `<li class="${c.pass ? 'ok' : 'bad'}">${c.pass ? '✓ ผ่าน' : '✗ ไม่ผ่าน'} · ${esc(c.rule)}</li>`).join('')}</ul>` : ''}</figcaption></figure>`).join('')}</div>`;
  dlg.showModal();
  slips.forEach(async (s, i) => {
    const box = dlg.querySelector(`[data-i="${i}"]`);
    try {
      const src = s.url.startsWith('/api/') ? await ChatStore.blob(s.url) : s.url.startsWith('/') ? ChatStore.base + s.url : s.url;
      box.innerHTML = `<a href="${src}" target="_blank" rel="noopener" title="เปิดภาพเต็ม"><img src="${src}" alt="สลิปของรายการ ${esc(p.id)}"></a>`;
    } catch (e) { box.textContent = 'โหลดภาพไม่ได้ · ' + e.message; }
  });
}

PAGES.bookings = {
  title: 'การจองคลาส',
  async render(v) {
    v.innerHTML = `<div class="toolbar"><select id="bkFilter" style="max-width:200px"><option value="">ทุกวัน</option><option value="up">ตั้งแต่วันนี้</option></select><span>${liveNote()} ${resetBtn}</span></div>
      <p class="hint">สวิตช์ = เปิด/ยกเลิกการจอง · บอทนับเฉพาะการจองที่เปิดอยู่เมื่อสมาชิกถามว่าจองคลาสไว้กี่รายการ</p><div id="bkTable"><div class="empty">กำลังโหลด…</div></div>`;
    try { await BO.list('bookings'); } catch (e) { return left('bookings') || loadFail($('#bkTable'), e); }
    if (left('bookings')) return;
    const draw = () => {
      const up = $('#bkFilter').value === 'up';
      $('#bkTable').innerHTML = table(['เลขจอง', 'วันที่', 'คลาส', 'เวลา', 'สมาชิก', 'สถานะ', 'เปิดจอง'], MEM.bookings.filter(b => !up || b.date >= today).map(b => {
        const s = DB.schedule.find(x => x.id === b.slot_id) || {}, m = M(b.member_id);
        return `<tr><td class="mono">${b.id}</td><td>${thDate(b.date)}</td><td>${s.class_id ? C(s.class_id).name : '-'}</td><td class="mono">${s.day_th || ''} ${s.start || ''}</td><td>${b.member_id}<br><small class="dim">${esc(m ? m.first_name : '')}</small></td><td>${statusPill(b.status)}</td>
          <td><button class="sw" role="switch" aria-checked="${b.status === 'booked'}" aria-label="เปิดการจอง ${b.id}" data-book="${b.id}"></button></td></tr>`;
      }));
    };
    $('#bkFilter').onchange = draw;
    v.onclick = async e => {
      const b = e.target.closest('[data-book]'); if (!b) return;
      const to = MEM.bookings.find(x => x.id === b.dataset.book).status === 'booked' ? 'cancelled' : 'booked';
      try { await BO.set('bookings', b.dataset.book, to); draw(); toast(`${b.dataset.book} → ${to === 'booked' ? 'จองแล้ว' : 'ยกเลิก'}`); } catch (err) { toast('บันทึกไม่ได้ · ' + err.message); }
    };
    draw();
  }
};

PAGES.promotions = {
  title: 'โปรโมชัน',
  async render(v) {
    v.innerHTML = `<div class="toolbar"><span>${liveNote()} ${resetBtn}</span><button class="btn red sm" data-toast="ฟอร์มสร้างโปร">+ สร้างโปรโมชัน</button></div>
      <p class="hint">สวิตช์ = เปิด/ปิดโปร บอทใช้สถานะในตารางนี้: เปิด = เสนอโค้ดนี้ได้ · ปิด = ตอบว่าโค้ดปิดอยู่ · ทดสอบ: เปิด FREECLASS แล้วถามบอทว่า "มีโปรอะไรบ้าง"</p><div id="prTable"><div class="empty">กำลังโหลด…</div></div>`;
    try { await BO.list('promotions'); } catch (e) { return left('promotions') || loadFail($('#prTable'), e); }
    if (left('promotions')) return;
    const draw = () => $('#prTable').innerHTML = table(['โค้ด', 'ชื่อโปร', 'ใช้กับ', 'ช่วงเวลา', 'สถานะ', 'เปิดใช้'], MEM.promotions.map(p =>
      `<tr><td class="mono">${p.code}</td><td>${esc(p.title)}<br><small class="dim">${esc(p.detail)}</small></td><td>${p.applies_to.map(a => a === 'ALL' ? 'ทุกแพ็กเกจ' : P(a).name_th).join(', ')}</td><td>${thDate(p.start)} – ${thDate(p.end)}${today > p.end ? '<br><small class="dim">เลยวันสิ้นสุดแล้ว</small>' : ''}</td><td>${statusPill(p.status)}</td>
        <td><button class="sw" role="switch" aria-checked="${p.status === 'active'}" aria-label="เปิดใช้โปร ${p.code}" data-promo="${p.id}"></button></td></tr>`));
    v.onclick = async e => {
      const b = e.target.closest('[data-promo]'); if (!b) return;
      const p = MEM.promotions.find(x => x.id === b.dataset.promo), to = p.status === 'active' ? 'inactive' : 'active';
      try { await BO.set('promotions', p.id, to); draw(); toast(`${p.code} → ${to === 'active' ? 'เปิดใช้' : 'ปิด'}`); } catch (err) { toast('บันทึกไม่ได้ · ' + err.message); }
    };
    draw();
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

PAGES.graph = {
  title: 'กราฟความรู้ (LightRAG)',
  async render(v) {
    if (!ChatStore.online) { v.innerHTML = '<div class="empty">ต้องรัน backend ก่อน · กราฟอ่านจากดัชนี LightRAG (data/rag-index/) ของเซิร์ฟเวอร์</div>'; return; }
    v.innerHTML = `<div class="toolbar"><input type="search" id="gSearch" placeholder="ค้นหา entity เช่น Ride, นักเรียน, YEAR13" style="max-width:300px">
        <select id="gType" style="max-width:180px"></select><select id="gDoc" style="max-width:160px"></select><span class="dim" id="gCount"></span></div>
      <p class="hint">จุด = entity ที่ Typhoon ดึงจากเอกสาร · เส้น = ความสัมพันธ์ · จุดใหญ่ = เชื่อมหลายเรื่อง · คลิกจุดเพื่อดูรายละเอียด · ลากเพื่อเลื่อน เลื่อนล้อเพื่อซูม</p>
      <div class="graph-wrap"><div id="gNet" class="graph-net"><div class="empty">กำลังโหลดกราฟ…</div></div><aside id="gInfo" class="card graph-info"><h3>รายละเอียด</h3><div class="dim">คลิกจุดในกราฟ</div></aside></div>`;
    let g;
    try { [g] = await Promise.all([ChatStore.api('GET', '/api/admin/kb/graph'), loadScript('https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js')]); }
    catch (e) { return left('graph') || loadFail($('#gNet'), e); }
    if (left('graph')) return;
    const COLORS = ['#ff2536', '#f59e0b', '#22c55e', '#38bdf8', '#a78bfa', '#f472b6', '#2dd4bf', '#fb923c'];
    const types = Object.entries(g.nodes.reduce((a, n) => (a[n.type] = (a[n.type] || 0) + 1, a), {})).sort((a, b) => b[1] - a[1]);
    const color = Object.fromEntries(types.slice(0, COLORS.length).map(([t], i) => [t, COLORS[i]]));
    const docs = [...new Set(g.nodes.flatMap(n => n.docs))].sort();
    $('#gType').innerHTML = `<option value="">ทุกประเภท (${types.length})</option>` + types.map(([t, n]) => `<option value="${esc(t)}">${esc(t)} (${n})</option>`).join('');
    $('#gDoc').innerHTML = '<option value="">ทุกเอกสาร</option>' + docs.map(d => `<option>${esc(d)}</option>`).join('');
    const byId = Object.fromEntries(g.nodes.map(n => [n.id, n]));
    const nodes = new vis.DataSet(), edges = new vis.DataSet();
    const net = new vis.Network($('#gNet'), { nodes, edges }, {
      nodes: { shape: 'dot', font: { color: '#e5e5e5', size: 13, face: 'IBM Plex Sans Thai, sans-serif' }, borderWidth: 0, scaling: { min: 6, max: 34 } },
      edges: { color: { color: 'rgba(255,255,255,.16)', highlight: '#ff2536' }, width: 1, smooth: false },
      physics: { solver: 'forceAtlas2Based', stabilization: { iterations: 150 }, forceAtlas2Based: { gravitationalConstant: -40, springLength: 90 } },
      interaction: { hover: true, tooltipDelay: 150 }
    });
    const draw = () => {
      const t = $('#gType').value, d = $('#gDoc').value;
      const keep = new Set(g.nodes.filter(n => (!t || n.type === t) && (!d || n.docs.includes(d))).map(n => n.id));
      const shown = g.edges.filter(e => keep.has(e.source) || keep.has(e.target));
      const ids = new Set([...keep, ...(t || d ? shown.flatMap(e => [e.source, e.target]) : [])]);   // a filter keeps the neighbours for context
      nodes.clear(); edges.clear();
      nodes.add([...ids].map(id => { const n = byId[id]; return { id, label: id, value: n.degree + 1, title: `${n.type} · ${n.docs.join(' ')}`, color: keep.has(id) ? (color[n.type] || '#8a8a92') : '#3a3a40' }; }));
      edges.add(shown.filter(e => ids.has(e.source) && ids.has(e.target)).map((e, i) => ({ id: i, from: e.source, to: e.target, title: e.keywords })));
      $('#gCount').textContent = `${ids.size} entity · ${edges.length} ความสัมพันธ์`;
    };
    const show = id => {
      const n = byId[id], rel = g.edges.filter(e => e.source === id || e.target === id);
      $('#gInfo').innerHTML = `<h3>${esc(id)}</h3><div>${pill(n.type)} ${n.docs.map(d => pill(d, 'ok')).join(' ')}</div><p>${esc(n.description)}</p>
        <h3>เชื่อมกับ ${rel.length} เรื่อง</h3><ul class="graph-rel">${rel.slice(0, 40).map(e => { const o = e.source === id ? e.target : e.source; return `<li><a href="#graph" data-node="${esc(o)}">${esc(o)}</a><small class="dim"> · ${esc(e.keywords)}</small></li>`; }).join('')}</ul>`;
    };
    net.on('click', p => p.nodes.length && show(p.nodes[0]));
    $('#gInfo').onclick = e => { const a = e.target.closest('[data-node]'); if (!a) return; e.preventDefault(); const id = a.dataset.node; if (!nodes.get(id)) { $('#gType').value = ''; $('#gDoc').value = ''; draw(); } net.selectNodes([id]); net.focus(id, { scale: 1.2, animation: true }); show(id); };
    $('#gType').onchange = $('#gDoc').onchange = draw;
    $('#gSearch').onkeydown = e => {
      if (e.key !== 'Enter') return;
      const q = e.target.value.trim().toLowerCase(), hit = g.nodes.filter(n => n.id.toLowerCase().includes(q)).sort((a, b) => b.degree - a.degree)[0];
      if (!q || !hit) return toast('ไม่พบ entity นี้');
      if (!nodes.get(hit.id)) { $('#gType').value = ''; $('#gDoc').value = ''; draw(); }
      net.selectNodes([hit.id]); net.focus(hit.id, { scale: 1.3, animation: true }); show(hit.id);
    };
    draw();
  }
};
// a script from a CDN, once (vis-network for the graph page)
function loadScript(src) {
  return loadScript[src] ||= new Promise((ok, fail) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = () => fail(new Error('โหลดไลบรารีวาดกราฟไม่ได้ (ต้องต่ออินเทอร์เน็ต)')); document.head.append(s); });
}

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
          <label class="field">ข้อความต้อนรับ<textarea rows="3">สวัสดีครับ เอ็กซ์เป็นผู้ช่วยของ X Fitness ถามเรื่องแพ็กเกจ คลาส เทรนเนอร์ หรือส่งภาพสลิปมาให้ตรวจได้ครับ</textarea></label>
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
