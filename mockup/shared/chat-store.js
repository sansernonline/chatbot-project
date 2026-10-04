/* Chat store shared by the customer site and the admin inbox — backed by the backend's SQLite
   (/api/conversations for the customer, /api/admin/* for the admin).
   Reads are synchronous from a cache; writes update the cache at once, then the server.
   Without a running backend the store is offline: changes live in memory only (admin preview mode), nothing is saved.

   The customer's ticket (= conversation id) is 10 characters, letter and digit alternating (e.g. K3M8P2Q7R5),
   kept in localStorage so a reload returns to the same chat.

   conversation: { id, ticket, name, member_id, topic, status, agent, created, updated, seen_admin, msgs[] }
   status: 'bot' → 'waiting' (handed off) → 'agent' (agent replying) → 'closed' (back to bot)
   msg:    { from: 'user' | 'bot' | 'agent' | 'system', text, at, by? } */
const ChatStore = (() => {
  const TICKET_KEY = 'xf.chat.ticket', POLL_MS = 1500;
  const LETTERS = 'ABCDEFGHJKLMNPQRSTUVWXYZ', DIGITS = '23456789'; // no I/O/0/1, easy to read out on the phone
  const now = () => new Date().toISOString();
  const listeners = [];
  let online = false, health = null, base = '', scope = 'customer', sid = null, token = null, onAuthError = () => {};
  let cache = {}, lastSnap = '', pending = 0, queue = Promise.resolve();

  function newTicket() {
    const pick = s => s[crypto.getRandomValues(new Uint32Array(1))[0] % s.length];
    const t = Array.from({ length: 10 }, (_, i) => pick(i % 2 ? DIGITS : LETTERS)).join('');
    try { localStorage.setItem(TICKET_KEY, t); } catch {}
    return t;
  }
  function ticket() { try { const t = localStorage.getItem(TICKET_KEY); if (/^([A-Z][0-9]){5}$/.test(t)) return t; } catch {} return newTicket(); }

  // optimistic mirror of backend/app/db.py so the screen updates before the server answers
  function apply(all, id, op, arg = {}) {
    const c = all[id] || { id, ticket: id, name: null, member_id: null, topic: null, status: 'bot', agent: null, created: now(), seen_admin: 0, msgs: [] };
    if (op === 'push') c.msgs.push({ at: now(), ...arg.msg });
    if (op === 'patch') Object.assign(c, arg.fields);
    if (op === 'handoff') {
      if (c.status !== 'agent') c.status = 'waiting';
      Object.assign(c, { topic: arg.topic, name: arg.name, member_id: arg.member_id });
      c.msgs.push({ at: now(), from: 'system', text: `ลูกค้าขอคุยกับพนักงาน · ${arg.topic}` });
    }
    if (arg.touch !== false || !c.updated) c.updated = now();
    all[id] = c; return c;
  }

  async function api(method, path, body) {
    const form = body instanceof FormData;   // file upload: the browser sets the multipart header itself
    const r = await fetch(base + path, { method, headers: { ...(form ? {} : { 'Content-Type': 'application/json' }), ...(token ? { Authorization: 'Bearer ' + token } : {}) }, body: body && (form ? body : JSON.stringify(body)) });
    if (r.status === 401 && scope === 'admin') { onAuthError(); throw new Error('unauthorized'); }
    if (!r.ok) throw new Error(`${method} ${path} → HTTP ${r.status}`);
    return r.status === 204 ? null : r.json();
  }
  const ROUTES = {   // op → [method, path, body] per scope
    customer: { push: (id, a) => ['POST', `/api/conversations/${id}/messages`, a.msg], handoff: (id, a) => ['POST', `/api/conversations/${id}/handoff`, a] },
    admin: {
      push: (id, a) => ['POST', `/api/admin/conversations/${id}/messages`, a.msg],
      patch: (id, a) => ['PATCH', `/api/admin/conversations/${id}`, { ...a.fields, touch: a.touch !== false }],
      remove: id => ['DELETE', `/api/admin/conversations/${id}`],
      clear: () => ['DELETE', '/api/admin/conversations']
    }
  };
  function write(op, id, arg) {
    if (op === 'remove') delete cache[id]; else if (op === 'clear') cache = {}; else apply(cache, id, op, arg);
    emit();
    if (!online) return Promise.resolve(cache[id] || null);   // preview: memory only
    pending++;
    // one request at a time so messages keep their order
    const p = queue.then(() => api(...ROUTES[scope][op](id, arg)))
      .then(c => { if (c) cache[c.id] = c; return c; })
      .catch(e => { console.warn('[ChatStore]', e.message); return cache[id] || null; })
      .finally(() => { pending--; emit(); });
    queue = p; return p;
  }
  async function refresh(force) {
    if (!online || pending) return;
    try {
      if (scope === 'admin') { if (!token) return; cache = Object.fromEntries((await api('GET', '/api/admin/conversations')).map(c => [c.id, c])); }
      else if (sid && (cache[sid] || force)) { const r = await fetch(base + `/api/conversations/${sid}`); cache = r.ok ? { [sid]: await r.json() } : {}; }
      emit();
    } catch (e) { console.warn('[ChatStore]', e.message); }
  }

  // listeners run on the next tick so a listener that writes cannot re-enter itself
  function emit() { const s = JSON.stringify(cache); if (s !== lastSnap) { lastSnap = s; setTimeout(() => listeners.forEach(f => f())); } }
  setInterval(() => refresh(), POLL_MS);

  return {
    get online() { return online; },
    get health() { return health; },
    get base() { return base; },
    ticket, newTicket, api,
    // backend is the same origin when served by uvicorn, else localhost:8000 (page opened as file://)
    async connect(opts = {}) {
      ({ scope = 'customer', sid = null, onAuthError = () => {} } = opts);
      base = location.protocol.startsWith('http') ? '' : 'http://localhost:8000';
      try {
        const c = new AbortController(); setTimeout(() => c.abort(), 1500);
        health = await (await fetch(base + '/api/health', { signal: c.signal })).json();
        online = health.status === 'ok';
      } catch { online = false; }
      await refresh(true); return online;
    },
    // customer starts a new chat: new ticket, empty cache
    setSession(id) { sid = id; cache = {}; lastSnap = '{}'; },
    async login(user, password) {
      const r = await fetch(base + '/api/admin/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user, password }) }).catch(() => null);
      if (!r) return user === 'admin' && password === '1234' ? { token: 'preview' } : { error: 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง' }; // no backend: preview login
      if (!r.ok) return { error: 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง' };
      token = (await r.json()).token; online = true;
      await refresh(); return { token };
    },
    setToken(t) { token = t; return online ? refresh() : Promise.resolve(); },
    list: () => Object.values(cache).sort((a, b) => b.updated.localeCompare(a.updated)),
    get: id => cache[id] || null,
    push: (id, msg) => write('push', id, { msg }),
    patch: (id, fields, touch = true) => write('patch', id, { fields, touch }),
    handoff: (id, topic, who = {}) => write('handoff', id, { topic, name: who.name || null, member_id: who.member_id || null }),
    remove: id => write('remove', id),
    clear: () => write('clear'),
    onChange: cb => listeners.push(cb)
  };
})();
