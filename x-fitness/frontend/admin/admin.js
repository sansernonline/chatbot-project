/* Admin shell: helpers, login against the backend, hash router. Pages register themselves in PAGES (pages.js, inbox.js). */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = n => Number(n).toLocaleString('th-TH');
const thDate = s => new Date(s).toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: '2-digit' });
const thTime = s => new Date(s).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' });
const P = id => DB.packages.find(p => p.id === id);
const C = id => DB.classes.find(c => c.id === id);
const M = id => DB.members.find(m => m.member_id === id);
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove('show'), 2400); }
const pill = (text, kind = '') => `<span class="pill ${kind}">${esc(text)}</span>`;
const table = (head, rows) => `<div class="tbl-wrap"><table><thead><tr>${head.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('') || `<tr><td colspan="${head.length}" class="empty">ไม่มีข้อมูล</td></tr>`}</tbody></table></div>`;

/* ---------- line icons (stroke = currentColor, white in the sidebar) ---------- */
const ICON_PATHS = {
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  inbox: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-5A8 8 0 1 1 21 12z"/>',
  leads: '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0M19 8v6M22 11h-6"/>',
  members: '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0M16 4a4 4 0 0 1 0 8M22 21a7 7 0 0 0-4-6.3"/>',
  payments: '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19M7 15h4"/>',
  bookings: '<rect x="3" y="4.5" width="18" height="16.5" rx="2"/><path d="M8 2.5v4M16 2.5v4M3 10h18"/>',
  promotions: '<path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
  knowledge: '<path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H20v15H5.5A1.5 1.5 0 0 0 4 19.5zM4 19.5A1.5 1.5 0 0 0 5.5 21H20"/>',
  bot: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1.5 14h5M9.5 8h5M17.5 16h5"/>',
  reports: '<path d="M3 3v18h18M7 15l4-4 3 3 6-6"/>',
  users: '<path d="M12 21.5s8-3.5 8-10V5l-8-3-8 3v6.5c0 6.5 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  back: '<path d="M15 18l-6-6 6-6"/>',
  out: '<path d="M14 4h5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-5M10 16l-4-4 4-4M6 12h10"/>',
  ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>'
};
const icon = name => `<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_PATHS[name] || ''}</svg>`;

/* ---------- pages registry ---------- */
const PAGES = {};   // id → { title, render(view), badge?() } — icon comes from ICON_PATHS[id]
const NAV = [
  ['หลัก', ['dashboard']],
  ['บริการลูกค้า', ['inbox', 'leads']],
  ['ธุรกิจ', ['members', 'payments', 'bookings', 'promotions']],
  ['แชตบอท', ['knowledge', 'bot', 'reports']],
  ['ระบบ', ['users']]
];

/* ---------- login (checked by the backend, demo account admin / 1234) ---------- */
const AUTH_KEY = 'xf.admin.session';
const loggedIn = () => !!session();
const session = () => { try { return sessionStorage.getItem(AUTH_KEY); } catch { return null; } };
$('#loginForm').onsubmit = async e => {
  e.preventDefault();
  const { token, error } = await ChatStore.login($('#lUser').value.trim(), $('#lPass').value);
  if (token) {
    try { sessionStorage.setItem(AUTH_KEY, token); } catch {}
    $('#loginErr').textContent = ''; showApp();
  } else { $('#loginErr').textContent = error; $('#loginErr').classList.remove('info'); $('#lPass').value = ''; $('#lPass').focus(); }
};
function logout() { try { sessionStorage.removeItem(AUTH_KEY); } catch {} location.hash = ''; location.reload(); }
$('#logout').onclick = logout;

/* ---------- router ---------- */
function renderNav() {
  const cur = location.hash.slice(1) || 'dashboard';
  $('#nav').innerHTML = NAV.map(([g, ids]) => `<h6>${g}</h6>` + ids.map(id => {
    const p = PAGES[id], b = p.badge?.() || 0;
    return `<a href="#${id}" class="${id === cur ? 'on' : ''}">${icon(id)}<span>${p.title}</span>${b ? `<b class="badge">${b}</b>` : ''}</a>`;
  }).join('')).join('');
}
function route() {
  const id = PAGES[location.hash.slice(1)] ? location.hash.slice(1) : 'dashboard', p = PAGES[id];
  $('#pageTitle').textContent = p.title;
  document.body.dataset.page = id;
  document.body.classList.remove('nav-open');
  const view = $('#view'); view.innerHTML = ''; view.onclick = null; p.render(view);
  renderNav();
}
function showApp() {
  if (!ChatStore.online && !ChatStore.list().length) seedDemo();   // preview mode: sample chats so the inbox is not empty
  $('#login').hidden = true; $('#app').hidden = false; route();
}
addEventListener('hashchange', () => loggedIn() && route());
$('#menuBtn').onclick = () => document.body.classList.toggle('nav-open');
addEventListener('DOMContentLoaded', async () => {
  $$('[data-icon]').forEach(el => el.insertAdjacentHTML('afterbegin', icon(el.dataset.icon)));
  const online = await ChatStore.connect({ scope: 'admin', onAuthError: logout });
  $('#storeMode').innerHTML = online ? 'เก็บแชต: <b>SQLite (backend)</b>' : 'โหมดดูตัวอย่าง · ไม่ได้บันทึก';
  if (!online) { $('#loginErr').textContent = 'ไม่ได้รัน backend · เข้าโหมดดูตัวอย่างได้ ข้อมูลไม่ถูกบันทึก'; $('#loginErr').classList.add('info'); }
  if (!loggedIn()) return $('#lUser').focus();
  if (online && session() === 'preview') return logout();   // preview session from before the backend started
  await ChatStore.setToken(session());
  showApp();
});
