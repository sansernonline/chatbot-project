/* Shared by dbviewer.html and graphviewer.html: the admin session (same key as admin.js), a redirect to the admin login, and GET calls.
   Read-only pages: they only ever call GET endpoints. */
const Viewer = (() => {
  const AUTH_KEY = 'xf.admin.session';
  const base = location.protocol.startsWith('http') ? '' : 'http://localhost:8000';   // opened from disk: the local backend
  const token = () => { try { return sessionStorage.getItem(AUTH_KEY); } catch { return null; } };
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  async function get(path) {
    const r = await fetch(base + path, { headers: token() ? { Authorization: 'Bearer ' + token() } : {} });
    if (r.status === 401) { try { sessionStorage.removeItem(AUTH_KEY); } catch {} throw Object.assign(new Error('ต้องเข้าสู่ระบบหลังบ้านก่อน'), { auth: true }); }
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `เรียก ${path} ไม่สำเร็จ (${r.status})`);
    return r.json();
  }

  // not logged in: go to the one admin login page, which sends the user back here afterwards
  function toLogin() {
    location.replace('index.html?next=' + encodeURIComponent(location.pathname.split('/').pop()));
    return new Promise(() => {});   // page is leaving; never resolve
  }

  async function withLogin(box, load) {
    if (!token()) return toLogin();
    try { return await load(); }
    catch (e) { if (e.auth) return toLogin(); throw e; }
  }
  return { get, esc, withLogin, base };
})();
