/* Inbox — the one admin page that really works.
   Reads/writes the same ChatStore as the customer chat widget (../index.html), so replies show up there live. */
const AGENT = 'แอดมิน';
const STATUS = { waiting: ['รอรับเรื่อง', 'warn'], agent: ['พนักงานดูแล', 'ok'], bot: ['บอทตอบ', ''], closed: ['ปิดแล้ว', 'dim'] };
const FILTERS = [['open', 'ต้องดูแล'], ['bot', 'บอทตอบ'], ['closed', 'ปิดแล้ว'], ['all', 'ทั้งหมด']];
const CANNED = [
  'สวัสดีค่ะ แอดมินรับเรื่องแล้วนะคะ',
  'ขอรหัสสมาชิกและเบอร์โทร 4 ตัวท้ายเพื่อตรวจสอบข้อมูลค่ะ',
  'ตรวจสลิปแล้ว ยอดถูกต้อง บันทึกการชำระเรียบร้อยค่ะ',
  'เรื่องนี้ต้องให้ผู้จัดการอนุมัติ จะแจ้งผลภายใน 1 วันทำการค่ะ',
  'ขอบคุณที่ติดต่อ X Fitness ค่ะ'
];
const IB = { sel: null, filter: 'open', q: '' };

const unread = c => c.msgs.slice(c.seen_admin || 0).filter(m => m.from === 'user' || m.from === 'system').length;
const needsAgent = c => c.status === 'waiting' || (c.status === 'agent' && unread(c) > 0);
const custName = c => c.name || 'ลูกค้าทั่วไป';
const lastMsg = c => c.msgs[c.msgs.length - 1];

PAGES.inbox = {
  title: 'กล่องแชตลูกค้า', real: true,
  badge: () => ChatStore.list().filter(needsAgent).length,
  render(view) {
    view.innerHTML = `
      <div class="inbox ${IB.sel ? 'has-sel' : ''}" id="inbox">
        <section class="ib-list">
          <div class="ib-tools">
            <input id="ibSearch" type="search" placeholder="ค้นหาชื่อ เลขเรื่อง ข้อความ" value="${esc(IB.q)}">
            <div class="seg" id="ibFilter">${FILTERS.map(([k, l]) => `<button data-f="${k}" aria-pressed="${IB.filter === k}">${l}</button>`).join('')}</div>
          </div>
          <div class="ib-items" id="ibItems"></div>
          <div class="ib-demo"><button class="btn ghost sm" id="ibSeed">สร้างแชตตัวอย่าง</button><button class="btn ghost sm" id="ibClear">ล้างแชตทั้งหมด</button></div>
        </section>
        <section class="ib-thread" id="ibThread"></section>
        <aside class="ib-info" id="ibInfo"></aside>
      </div>`;
    $('#ibSearch').oninput = e => { IB.q = e.target.value; drawList(); };
    $('#ibFilter').onclick = e => { const b = e.target.closest('[data-f]'); if (!b) return; IB.filter = b.dataset.f; $$('#ibFilter button').forEach(x => x.setAttribute('aria-pressed', x === b)); drawList(); };
    $('#ibItems').onclick = e => { const it = e.target.closest('[data-id]'); if (it) select(it.dataset.id); };
    $('#ibSeed').onclick = () => { seedDemo(); refreshInbox(); toast('สร้างแชตตัวอย่าง 3 รายการ'); };
    $('#ibClear').onclick = () => { if (!confirmClear()) return; ChatStore.clear(); IB.sel = null; refreshInbox(); };
    drawList(); drawThread();
  }
};

function confirmClear() { const b = $('#ibClear'); if (b.dataset.armed) return true; b.dataset.armed = 1; b.textContent = 'กดอีกครั้งเพื่อยืนยัน'; setTimeout(() => { delete b.dataset.armed; b.textContent = 'ล้างแชตทั้งหมด'; }, 3000); return false; }

function drawList() {
  const q = IB.q.trim().toLowerCase();
  const items = ChatStore.list().filter(c =>
    (IB.filter === 'all' || (IB.filter === 'open' ? ['waiting', 'agent'].includes(c.status) : c.status === IB.filter)) &&
    (!q || [c.ticket, c.name, c.member_id, c.topic, ...c.msgs.map(m => m.text)].join(' ').toLowerCase().includes(q)));
  $('#ibItems').innerHTML = items.map(c => {
    const [st, k] = STATUS[c.status], n = unread(c), last = lastMsg(c);
    return `<button class="ib-item ${c.id === IB.sel ? 'on' : ''} ${n ? 'unread' : ''}" data-id="${esc(c.id)}">
      <div class="r1"><b>${esc(custName(c))}</b><time>${thTime(c.updated)}</time></div>
      <div class="r2">${pill(st, k)}${c.ticket ? `<span class="mono">${c.ticket}</span>` : ''}${n ? `<b class="badge">${n}</b>` : ''}</div>
      <p>${last ? esc((last.from === 'agent' ? 'คุณ: ' : last.from === 'bot' ? 'บอท: ' : '') + last.text).slice(0, 90) : ''}</p>
    </button>`;
  }).join('') || `<div class="empty">ยังไม่มีแชตในหมวดนี้<br><small>เปิด <a href="../index.html" target="_blank">หน้าเว็บลูกค้า</a> แล้วพิมพ์ “คุยกับพนักงาน” หรือกด “สร้างแชตตัวอย่าง”</small></div>`;
}

function select(id) {
  IB.sel = id; $('#inbox').classList.add('has-sel');
  $$('.ib-item').forEach(x => x.classList.toggle('on', x.dataset.id === id));
  drawThread(); $('#ibText')?.focus();
}

function drawThread() {
  const c = IB.sel && ChatStore.get(IB.sel);
  if (!c) { $('#ibThread').innerHTML = '<div class="empty big">เลือกแชตทางซ้ายเพื่อเริ่มตอบลูกค้า</div>'; $('#ibInfo').innerHTML = ''; return; }
  const [st, k] = STATUS[c.status], mine = c.status === 'agent';
  $('#ibThread').innerHTML = `
    <header class="ib-head">
      <button class="icon back" id="ibBack" aria-label="กลับไปรายการแชต">${icon('back')}</button>
      <div><b>${esc(custName(c))}</b><small>${c.ticket || 'ยังไม่มีเลขเรื่อง'} · ${pill(st, k)}</small></div>
      <div class="acts">
        ${mine ? '' : `<button class="btn red sm" id="ibTake">${c.status === 'waiting' ? 'รับเรื่อง' : 'เข้าดูแลแทนบอท'}</button>`}
        ${c.status === 'closed' || c.status === 'bot' ? '' : '<button class="btn ghost sm" id="ibClose">ปิดเรื่อง · คืนให้บอท</button>'}
      </div>
    </header>
    <div class="ib-msgs" id="ibMsgs">${c.msgs.map(msgHtml).join('')}</div>
    <footer class="ib-compose">
      <div class="canned">${CANNED.map(t => `<button data-c="${esc(t)}">${esc(t)}</button>`).join('')}</div>
      <div class="row"><textarea id="ibText" rows="2" placeholder="พิมพ์ตอบลูกค้า · Enter ส่ง · Shift+Enter ขึ้นบรรทัดใหม่"></textarea><button class="btn red" id="ibSend">ส่ง</button></div>
      <small class="dim">${mine ? 'ลูกค้าเห็นข้อความนี้ในแชตทันที' : 'ส่งข้อความแล้วระบบจะรับเรื่องให้อัตโนมัติ บอทหยุดตอบจนกว่าจะปิดเรื่อง'}</small>
    </footer>`;
  $('#ibBack').onclick = () => { IB.sel = null; $('#inbox').classList.remove('has-sel'); };
  $('#ibTake') && ($('#ibTake').onclick = () => { take(c.id); refreshInbox(); });
  $('#ibClose') && ($('#ibClose').onclick = () => {
    ChatStore.patch(c.id, { status: 'closed' });
    ChatStore.push(c.id, { from: 'system', notify: true, text: 'พนักงานปิดเรื่องนี้แล้ว ต่อจากนี้ผู้ช่วยอัตโนมัติเอ็กซ์จะตอบค่ะ' });
    refreshInbox(); toast(`ปิดเรื่อง ${c.ticket || ''} แล้ว`);
  });
  $('.canned').onclick = e => { const b = e.target.closest('[data-c]'); if (b) { $('#ibText').value = b.dataset.c; $('#ibText').focus(); } };
  $('#ibText').onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); reply(); } };
  $('#ibSend').onclick = reply;
  drawInfo(c); markSeen(c);
  const box = $('#ibMsgs'); box.scrollTop = box.scrollHeight;
}

function msgHtml(m) {
  if (m.from === 'system') return `<div class="m sys">${esc(m.text)} · ${thTime(m.at)}</div>`;
  const who = { user: 'ลูกค้า', bot: 'บอทเอ็กซ์', agent: m.by || AGENT }[m.from];
  return `<div class="m ${m.from}"><div class="b">${esc(m.text).replace(/\n/g, '<br>')}</div><small>${who} · ${thTime(m.at)}</small></div>`;
}

function drawInfo(c) {
  const m = c.member_id && M(c.member_id), pays = m ? DB.payments.filter(p => p.member_id === m.member_id && p.status !== 'paid') : [];
  $('#ibInfo').innerHTML = `
    <h3>ข้อมูลลูกค้า</h3>
    ${m ? `<dl>
      <dt>รหัสสมาชิก</dt><dd class="mono">${m.member_id}</dd>
      <dt>ชื่อ</dt><dd>${esc(m.first_name)} ${esc(m.last_name)}</dd>
      <dt>โทร</dt><dd class="mono">${m.phone}</dd>
      <dt>แพ็กเกจ</dt><dd>${esc(P(m.package_id).name_th)}</dd>
      <dt>สถานะ</dt><dd>${pill(m.status, m.status === 'active' ? 'ok' : 'warn')} ถึง ${thDate(m.end_date)}</dd>
      <dt>แต้ม</dt><dd>${fmt(m.points)}</dd>
      <dt>ยอดค้าง</dt><dd>${pays.length ? pays.map(p => `${fmt(p.amount)} บาท (${esc(p.description)})`).join('<br>') : 'ไม่มี'}</dd>
    </dl>` : '<p class="dim">ยังไม่ยืนยันตัวตน ขอรหัสสมาชิก + เบอร์ 4 ตัวท้ายก่อนเปิดเผยข้อมูลส่วนตัว</p>'}
    <h3>เรื่อง</h3>
    <dl>
      <dt>หัวข้อ</dt><dd>${esc(c.topic || '-')}</dd>
      <dt>เริ่มแชต</dt><dd>${thDate(c.created)} ${thTime(c.created)}</dd>
      <dt>ข้อความ</dt><dd>${c.msgs.length} รายการ</dd>
      <dt>เลขเรื่อง</dt><dd class="mono">${esc(c.ticket || c.id)}</dd>
    </dl>`;
}

function take(id) {
  const c = ChatStore.get(id); if (c.status === 'agent') return;
  ChatStore.patch(id, { status: 'agent', agent: AGENT, topic: c.topic || 'พนักงานเข้าดูแลเอง' }); // ticket is assigned by the store
  ChatStore.push(id, { from: 'system', notify: true, text: `${AGENT}เข้ามาดูแลแชตนี้แล้วค่ะ` });
}
function reply() {
  const t = $('#ibText').value.trim(); if (!t || !IB.sel) return;
  take(IB.sel);
  ChatStore.push(IB.sel, { from: 'agent', text: t.slice(0, 1000), by: AGENT });
  $('#ibText').value = ''; refreshInbox(); $('#ibText').focus();
}
function markSeen(c) { if ((c.seen_admin || 0) !== c.msgs.length) ChatStore.patch(c.id, { seen_admin: c.msgs.length }, false); }

/* keep the open thread's draft; only redraw the parts that changed */
function refreshInbox() {
  renderNav(); updateTitle();
  if (document.body.dataset.page !== 'inbox' || !$('#inbox')) return;
  const draft = $('#ibText')?.value, focused = document.activeElement?.id === 'ibText';
  drawList(); drawThread();
  if ($('#ibText') && draft) $('#ibText').value = draft;
  if (focused) $('#ibText')?.focus();
}
function updateTitle() { const n = PAGES.inbox.badge(); document.title = (n ? `(${n}) ` : '') + 'X Fitness Admin'; }
ChatStore.onChange(refreshInbox);
addEventListener('DOMContentLoaded', updateTitle);

function seedDemo() {
  const ago = min => new Date(Date.now() - min * 60000).toISOString();
  const mk = (id, fields, msgs) => { ChatStore.remove(id); msgs.forEach(([from, text, min]) => ChatStore.push(id, { from, text, at: ago(min) })); ChatStore.patch(id, fields); };
  mk('R2F3N4D5A6', { name: 'คุณกิตติพัฒน์ แก้วมณี', member_id: 'FN-10005', topic: 'ขอคืนเงิน', status: 'waiting' }, [
    ['user', 'สมัครไปเมื่อวานแต่ยังไม่ได้เข้าใช้เลย ขอคืนเงินได้ไหมคะ', 9],
    ['bot', 'การคืนเงินต้องให้ผู้จัดการสาขาอนุมัติ เอ็กซ์อนุมัติเองไม่ได้ค่ะ เงื่อนไขคือคืนเต็มจำนวนถ้ายกเลิกภายใน 7 วันหลังสมัครและยังไม่เคยเข้าใช้', 9],
    ['system', 'ลูกค้าขอคุยกับพนักงาน · ขอคืนเงิน', 8]]);
  mk('S2L3P4X5Y6', { name: 'คุณวรเมธ จันทร์หอม', member_id: 'FN-10007', topic: 'สลิปยอดไม่ตรง', status: 'agent' }, [
    ['user', '[แนบภาพ 02_slip_amount_mismatch.png] โอนค่าสมาชิกแล้วครับ', 25],
    ['bot', 'ตรวจสลิปเบื้องต้นไม่ผ่านค่ะ ยอดโอนขาดอยู่ 300 บาท เอ็กซ์ส่งเรื่องให้พนักงานตรวจสอบค่ะ', 25],
    ['system', 'ลูกค้าขอคุยกับพนักงาน · สลิปยอดไม่ตรง', 24],
    ['agent', 'สวัสดีค่ะ แอดมินรับเรื่องแล้วนะคะ ยอดค้าง 1,290 บาท สลิปโอนมา 990 บาทค่ะ', 20],
    ['user', 'โอนเพิ่ม 300 แล้วครับ เดี๋ยวส่งสลิปให้', 3]]);
  mk('H2R3S4Z5W6', { name: null, status: 'bot' }, [
    ['user', 'วันเสาร์เปิดกี่โมง', 40],
    ['bot', 'เสาร์–อาทิตย์และวันหยุดนักขัตฤกษ์ เปิด 08:00–20:00 น. เข้าได้ถึง 30 นาทีก่อนปิดค่ะ', 40]]);
}
