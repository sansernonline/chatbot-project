/* ---------- slide animations: stagger children, count numbers up, loop the step cards ---------- */
const wait=ms=>new Promise(r=>setTimeout(r,ms));
S.forEach(s=>s.querySelectorAll('.row>*,.pills>*,.list>*,.toc>*,.tbl tr,.node,.graph g,.tree>div,.cases>*').forEach((el,k,all)=>{
  const sib=[...el.parentNode.children].indexOf(el);el.dataset.k='';el.style.setProperty('--k',Math.min(sib,14));}));
let loop=null;
function onSlide(s){
  clearInterval(loop);document.querySelectorAll('.lit').forEach(x=>x.classList.remove('lit'));
  s.querySelectorAll('[data-count]').forEach(el=>{const end=el.dataset.count,[a,b]=end.split('/'),t0=performance.now();
    const step=t=>{const p=Math.min(1,(t-t0)/900),v=Math.round(+a*(1-Math.pow(1-p,3)));el.textContent=b?`${v}/${b}`:v;if(p<1)requestAnimationFrame(step)};requestAnimationFrame(step);});
  s.querySelectorAll('.growbar').forEach(b=>{b.style.height='0px';requestAnimationFrame(()=>requestAnimationFrame(()=>b.style.height=b.dataset.h+'px'));});
  const steps=[...s.querySelectorAll('[data-loop]>*')];   // e.g. the 6 cards of the request flow light up in turn
  if(steps.length){let k=0;const go=()=>{steps.forEach((x,j)=>x.classList.toggle('lit',j===k));k=(k+1)%steps.length};go();loop=setInterval(go,1400);}
  s.querySelectorAll('.play').forEach(p=>p.querySelector('input')?.focus({preventScroll:true}));
}
/* architecture walk-through: ⏮ reset · ◀ back · ▶/⏸ play · ⏭ next; each step lights its arrows and runs a dot along them */
const tourBar=document.querySelector('.tourbar');
if(tourBar&&DATA&&DATA.tour){
  const T=DATA.tour,svg=document.querySelector('#arch svg'),cap=tourBar.querySelector('.tcap'),num=tourBar.querySelector('.tstep'),pp=tourBar.querySelector('.pp');
  let k=-1,timer=null;const NS='http://www.w3.org/2000/svg';
  const draw=()=>{
    svg.querySelectorAll('.dot').forEach(d=>d.remove());svg.querySelectorAll('path.hot').forEach(p=>p.classList.remove('hot','back'));
    document.querySelectorAll('#arch .node.tour').forEach(n=>n.classList.remove('tour'));
    num.textContent=`${k+1}/${T.length}`;
    if(k<0){cap.textContent='กด ▶ เพื่อไล่ทางเดินของ 1 ข้อความ ตั้งแต่ลูกค้าพิมพ์จนได้คำตอบ';return;}
    const s=T[k];cap.textContent=s.text;
    document.querySelector(`#arch [data-key="${s.node}"]`).click();          // open the file card of this step
    svg.querySelectorAll('path.hot').forEach(p=>p.classList.remove('hot','back'));   // the picker lit its own arrows: show only this step's
    s.edges.forEach((g,n)=>g.split('|').forEach(e=>{const back=e.includes('<'),[a,b]=e.split(/[<>]/),p=svg.querySelector(`#e-${a}-${b}`);
      p.classList.add('hot');p.classList.toggle('back',back);svg.appendChild(p);[a,b].forEach(x=>document.querySelector(`#arch [data-key="${x}"]`).classList.add('tour'));
      const dot=document.createElementNS(NS,'circle');dot.setAttribute('r','8');dot.setAttribute('fill','#ff2536');dot.setAttribute('class','dot');
      const mo=document.createElementNS(NS,'animateMotion');mo.setAttribute('dur','1.3s');mo.setAttribute('repeatCount','indefinite');
      mo.setAttribute('begin',`${n*0.65}s`);mo.setAttribute('keyPoints',back?'1;0':'0;1');mo.setAttribute('keyTimes','0;1');mo.setAttribute('calcMode','linear');
      const mp=document.createElementNS(NS,'mpath');mp.setAttribute('href','#'+p.id);mo.appendChild(mp);dot.appendChild(mo);svg.appendChild(dot);}));
    svg.setCurrentTime&&svg.setCurrentTime(0);};
  const stop=()=>{clearInterval(timer);timer=null;pp.textContent='▶ เล่น';};
  const go=n=>{k=Math.max(-1,Math.min(T.length-1,n));draw();if(k===T.length-1)stop();};
  const run=()=>{clearInterval(timer);pp.textContent='⏸ หยุด';     // keep stepping every 3.2 s from where we are
    timer=setInterval(()=>{if(!tourBar.closest('.slide').classList.contains('on'))return stop();go(k+1);},3200);};
  const play=()=>{if(timer)return stop();go(k>=T.length-1?0:k+1);run();};
  const reset=()=>{const playing=!!timer;stop();go(0);if(playing)run();};   // back to step 1 (the website); keeps playing if it was
  tourBar.addEventListener('click',e=>{const t=e.target.closest('[data-t]');if(!t)return;
    ({reset,back:()=>{stop();go(Math.max(0,k-1));},next:()=>{stop();go(k+1);},play})[t.dataset.t]();});
  go(-1);}

/* ---------- connection to the real bot (falls back to recorded answers) ---------- */
const BOT={base:'',live:false};
async function connect(base){
  BOT.base=base.replace(/\/+$/,'');BOT.live=false;paintConn('… กำลังเชื่อม');
  try{const r=await fetch(BOT.base+'/api/health',{signal:AbortSignal.timeout(5000)});BOT.live=!!(await r.json()).llm;}catch(e){}
  try{localStorage.setItem('xf_base',BOT.base)}catch(e){}
  paintConn();}
function paintConn(text){document.querySelectorAll('.conn').forEach(c=>{c.className='conn '+(BOT.live?'on':'off');
  c.title=BOT.live?'เชื่อมกับ '+BOT.base:'ใช้คำตอบที่บันทึกจากการทดสอบ · คลิกเพื่อเชื่อมบอทจริง';c.textContent=text||(BOT.live?'● บอทจริง':'● ออฟไลน์');});}
document.body.insertAdjacentHTML('beforeend','<div id="connbox">บอทจริงที่ <input id="connurl" spellcheck="false"><button id="connok">เชื่อม</button><button id="connx" style="background:#26262b">ปิด</button></div>');
const connbox=document.getElementById('connbox');
document.addEventListener('click',e=>{if(e.target.closest('.conn')){document.getElementById('connurl').value=BOT.base;connbox.classList.add('on');}});
document.getElementById('connok').onclick=()=>{connbox.classList.remove('on');connect(document.getElementById('connurl').value.trim());};
document.getElementById('connx').onclick=()=>connbox.classList.remove('on');
connect(location.protocol.startsWith('http')?location.origin:(()=>{try{return localStorage.getItem('xf_base')}catch(e){}})()||'http://localhost:8000');

/* ---------- playground: chat + the 6 steps of chat.answer() ---------- */
const STEPS=[['guard ขาเข้า','guard.check_input'],['ยืนยันสมาชิก','verify_step'],['LightRAG ค้น','rag.context'],
             ['กฎร้านจากโค้ด','business.rules_for · check_slip'],['Typhoon ตอบ','llm.chat'],['guard ขาออก','guard.check_output']];
const OUT_CODE=/^(G-|N-05$)/;
function sourcesHtml(src){return src.length?src.slice(0,4).map((s,j)=>`<span class="tag ${j?'':'red'}" title="${esc(DATA.kb[s]||'')}">${esc(s)}</span>`).join(' ')+` <span style="font-size:17px">${esc(DATA.kb[src[0]]||'')}</span>`:'ไม่พบในคลังความรู้ → ปุ่มคุยกับพนักงาน';}

function setupPlay(el){
  const sid='deck-'+Math.random().toString(36).slice(2,10),focus=+el.dataset.focus||0;let member=null,busy=false;
  const chips=(el.dataset.presets||'').split(',').filter(Boolean);
  el.innerHTML=`<div class="phone"><div class="bar"><span><i></i> เอ็กซ์ · ลองเล่น</span><span class="conn off"></span></div>
    <div class="chatlog"></div><div class="pl-chips"></div>
    <form class="pl-in"><input placeholder="พิมพ์คำถามแล้วกด Enter" maxlength="500"><button>ส่ง</button></form></div>
    <div class="trace"><div class="top"><span class="kicker">ข้อความนี้ผ่านขั้นไหนบ้าง</span><button class="btn ghost" type="button" data-reset style="font-size:17px;padding:8px 14px">เริ่มใหม่</button></div>
    ${STEPS.map((s,j)=>`<div class="st ${j+1===focus?'focus':''}"><span class="n">${j+1}</span><b>${s[0]}<small>${s[1]}</small></b><span class="s">—</span></div>`).join('')}
    <p class="pl-note" style="font-size:17px;color:var(--dim)">ขั้นที่ผ่านอ่านจากผลที่ API ส่งกลับ (rules · sources · member · slip_check)</p></div>`;
  paintConn();
  const log=el.querySelector('.chatlog'),st=[...el.querySelectorAll('.st')],input=el.querySelector('input');
  const add=(cls,html)=>{const d=document.createElement('div');d.className=cls;d.innerHTML=html;log.appendChild(d);log.scrollTop=log.scrollHeight;return d};
  const mark=(j,cls,text)=>{st[j].className='st '+(j+1===focus?'focus ':'')+cls;st[j].querySelector('.s').innerHTML=text;};
  el.querySelector('.pl-chips').innerHTML=chips.map(c=>{const k=DATA.all[c],im=k&&k.img;
    return `<button type="button" data-chip="${esc(c)}">${im?`<img src="${im}" alt="">`:''}${esc(k?k.q:c.replace(/^t:/,''))}</button>`}).join('');
  el.querySelector('.pl-chips').addEventListener('click',e=>{const b=e.target.closest('[data-chip]');if(b)send(b.dataset.chip);});
  el.querySelector('form').addEventListener('submit',e=>{e.preventDefault();const t=input.value.trim();if(t){input.value='';send('t:'+t);}});
  el.querySelector('[data-reset]').onclick=()=>{log.innerHTML='';member=null;st.forEach((x,j)=>mark(j,'','—'));};
  el.addEventListener('click',e=>{const a=e.target.closest('.acts span');if(a)send('t:'+a.textContent);});

  async function send(chip){if(busy)return;busy=true;
    const c=DATA.all[chip],text=c?c.q:chip.replace(/^t:/,''),t0=performance.now();
    if(c&&c.img)add('b u',`<img src="${c.img}" alt="">`);add('b u',esc(text));
    st.forEach((x,j)=>mark(j,'','—'));const ty=add('typing','<span></span><span></span><span></span>');
    let k=0;const run=setInterval(()=>{if(k<5){mark(k,'run','กำลังทำ…');k++;}},380);   // walk the steps while waiting
    let r;
    try{r=BOT.live?await live(c,text):await offline(c,text);}
    catch(e){r={answer:'เรียกบอทไม่สำเร็จ: '+e.message+' — สลับเป็นคำตอบที่บันทึกไว้',sources:[],rules:[],actions:[],error:true};
      if(c){const o=await offline(c,text);r={...o,answer:o.answer};}}
    clearInterval(run);ty.remove();
    const sec=BOT.live?((performance.now()-t0)/1000).toFixed(1):r.sec;   // offline: only the time recorded in the tests
    if(r.member)member=r.member;
    const b=add('b a','');for(let n=0;n<=r.answer.length;n+=4){b.textContent=r.answer.slice(0,n);log.scrollTop=log.scrollHeight;await wait(10);}
    b.textContent=r.answer;
    if(r.actions&&r.actions.length)b.insertAdjacentHTML('beforeend',`<div class="acts">${r.actions.map(a=>`<span>${esc(a)}</span>`).join('')}</div>`);
    log.scrollTop=log.scrollHeight;paint(r,sec,c);busy=false;}

  function paint(r,sec,c){const rules=r.rules||[],src=r.sources||[];
    const verify=rules.includes('D-04'),outHit=rules.filter(x=>OUT_CODE.test(x));
    const blocked=!verify&&!src.length&&rules.length&&!outHit.length;
    mark(0,blocked?'stop':'ok',blocked?`จับได้ <span class="tag red">${esc(rules.join(' · '))}</span> ตอบข้อความตายตัว ไม่เรียก AI`:'ผ่าน');
    if(blocked){[1,2,3,4,5].forEach(j=>mark(j,'skip','ข้าม'));mark(4,'skip',sec?`ข้าม · ตอบใน ${sec} วินาที`:'ข้าม');return;}
    if(verify){mark(1,'hit',r.member?`ยืนยันแล้ว <span class="tag ok">${esc(r.member.member_id)}</span>`:'ถาม/ตรวจรหัส FN-xxxxx + เบอร์ 4 ตัวท้าย');
      [2,3,4,5].forEach(j=>mark(j,'skip','ข้าม'));return;}
    mark(1,member?'hit':'ok',member?`สมาชิก <span class="tag ok">${esc(member.member_id)}</span>`:'ไม่ต้อง (ไม่ได้ถามเรื่องส่วนตัว)');
    mark(2,src.length?'ok':'hit',sourcesHtml(src));
    const slip=r.slip_check,vis=c&&c.vision;
    mark(3,slip||vis?'hit':'ok',slip?`ตรวจสลิป ${slip.checks.filter(x=>x.pass).length}/${slip.checks.length} ข้อ${slip.short_by?` · ขาด ${slip.short_by} บาท`:''} → ${slip.ok?'รอพนักงานยืนยัน':'ส่งพนักงาน'}`
      :vis?`อ่านภาพ: <span class="mono" style="font-size:16px">${esc(vis)}</span>`:'ไม่มีกฎพิเศษสำหรับคำถามนี้');
    mark(4,'ok',sec?`ตอบใน ${sec} วินาที`:'ไม่ได้บันทึกเวลา');
    mark(5,outHit.length?'stop':'ok',outHit.length?`ตัดคำตอบ <span class="tag red">${esc(outHit.join(' · '))}</span>`:'ผ่าน ไม่มีตัวเลข ลิงก์ เวลา ที่แต่งขึ้น');}

  async function live(c,text){
    let vision=null;
    if(c&&c.hint&&!member){const v=await post({message:c.hint.split(': ')[1].split(' (')[0]});if(v.member)member=v.member;}
    if(c&&c.img){const fd=new FormData();fd.append('image',await (await fetch(c.img)).blob(),c.imgPath.split('/').pop());fd.append('session_id',sid);
      const r=await fetch(BOT.base+'/api/vision',{method:'POST',body:fd,signal:AbortSignal.timeout(40000)});if(!r.ok)throw new Error('vision '+r.status);vision=await r.json();}
    const j=await post({message:text,vision});if(vision)j.visionText=`type=${vision.type}`;return j;}
  async function post(body){const r=await fetch(BOT.base+'/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(40000),
      body:JSON.stringify({session_id:sid,member_id:member&&member.member_id,phone_last4:member&&member.phone_last4,...body})});
    if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}
  async function offline(c,text){await wait(700);
    const k=c||Object.values(DATA.all).find(x=>x.q===text)||DATA.canned[text.replace(/\s+/g,' ').trim()];
    if(!k)return {answer:'(ออฟไลน์) เลือกคำถามตัวอย่างด้านล่าง หรือคลิกป้ายสีเหลืองมุมขวาบนของโทรศัพท์เพื่อเชื่อมบอทจริง',sources:[],rules:[],actions:[]};
    return {answer:k.a,sources:k.src||[],rules:k.rules||[],actions:k.actions||[],member:k.member,sec:k.sec};}
}
if(DATA)document.querySelectorAll('.play').forEach(setupPlay);

/* ---------- flowcharts: buttons from DATA.flows[name]; a walk lights boxes one by one and runs a dot along each arrow ---------- */
const NS2='http://www.w3.org/2000/svg';const PACE={rag:2200};
function dotAlong(svg,path,dur){const c=document.createElementNS(NS2,'circle');c.setAttribute('r','8');
  const m=document.createElementNS(NS2,'animateMotion');m.setAttribute('dur',dur);m.setAttribute('repeatCount','indefinite');
  const mp=document.createElementNS(NS2,'mpath');mp.setAttribute('href','#'+path.id);m.appendChild(mp);c.appendChild(m);svg.appendChild(c);return c;}
document.querySelectorAll('.flowbar[data-flow]').forEach(bar=>{
  const name=bar.dataset.flow,walks=(DATA&&DATA.flows&&DATA.flows[name])||[],map=document.querySelector(`.flowmap[data-flow="${name}"]`),
        svg=map.querySelector('svg'),cap=document.querySelector(`.fcap[data-flow="${name}"]`),time=bar.querySelector('.ftime');let run=0;
  const clear=()=>{svg.querySelectorAll('circle').forEach(c=>c.remove());svg.querySelectorAll('path.hot').forEach(p=>{p.classList.remove('hot');p.style.markerEnd=p.dataset.blue||p.style.markerEnd;});
    map.querySelectorAll('.fnode').forEach(n=>n.classList.remove('f-ok','f-hit','f-stop'));
    map.querySelectorAll('.fnode span.found').forEach(sp=>{sp.textContent=sp.dataset.orig;sp.classList.remove('found');});};
  svg.querySelectorAll('path').forEach(p=>p.dataset.blue=p.style.markerEnd);
  bar.querySelector('.fbtns').innerHTML=walks.map((w,j)=>`<button type="button" data-w="${j}">${esc(w.label)}</button>`).join('');
  bar.addEventListener('click',async e=>{const b=e.target.closest('[data-w]');if(!b)return;const w=walks[+b.dataset.w],me=++run;
    bar.querySelectorAll('button').forEach(x=>x.classList.toggle('sel',x===b));clear();map.classList.add('walking');time.textContent='';cap.innerHTML='';
    const pace=PACE[name]||1300;                      // ms per step; "a|b" in a step lights several arrows and boxes at once
    for(const s of w.steps){if(me!==run)return;
      if(s.e){svg.querySelectorAll('circle').forEach(c=>c.remove());
        s.e.split('|').forEach(e=>{const p=svg.querySelector(`#fl-${name}-${e}`);if(p){p.classList.add('hot');svg.appendChild(p);p.style.markerEnd=p.dataset.red;dotAlong(svg,p,pace/1000+'s');}});}
      if(s.x)Object.entries(s.x).forEach(([k,txt])=>{const sp=map.querySelector(`[data-f="${k}"] span`);if(sp){sp.dataset.orig??=sp.textContent;sp.textContent=txt;sp.classList.add('found');}});
      const ns=s.n.split('|').map(k=>map.querySelector(`[data-f="${k}"]`)).filter(Boolean);ns.forEach(n=>n.classList.add('f-'+s.c));
      const title=ns.length>1?'':(ns[0]&&ns[0].querySelector('b').textContent)||'';
      cap.innerHTML=(title?`<b>${esc(title)}</b>`:'')+esc(s.t).replace(/ \| /g,'<br>');await wait(pace);}
    if(me!==run)return;time.textContent=w.sec?`ตอบใน ${w.sec} วินาที`:'';
    if(w.answer)cap.innerHTML=`<b>คำตอบ</b>${esc(w.answer.length>170?w.answer.slice(0,170)+' …':w.answer)}${w.acts&&w.acts.length?` <i>· ปุ่ม: ${esc(w.acts.join(' · '))}</i>`:''}`;});
});
/* overall architecture: a dot keeps running along every arrow */
document.querySelectorAll('.ovmap svg path').forEach((p,j)=>{const c=dotAlong(p.ownerSVGElement,p,(1.6+j*0.15)+'s');c.setAttribute('r','6');});

/* ---------- LINE OA page: ▶ plays the tested conversation; rich-menu taps ask the real bot when connected, else replay tested answers ---------- */
(function(){const ph=document.getElementById('lphone');if(!ph||!DATA.line)return;
  const log=ph.querySelector('.llog'),note=document.getElementById('line-note'),sid='line-'+Math.random().toString(36).slice(2,10);
  let run=0,member=null,clock=1;
  const now=()=>`10:${String(clock++).padStart(2,'0')}`;
  const add=html=>{log.insertAdjacentHTML('beforeend',html);log.scrollTop=log.scrollHeight;return log.lastElementChild;};
  const user=t=>add(`<div class="lm u"><span class="lt">อ่านแล้ว<br>${now()}</span><div class="lb">${esc(t)}</div></div>`);
  const pic=src=>add(`<div class="lm u"><span class="lt">อ่านแล้ว<br>${now()}</span><img class="li" src="${src}" alt="สลิป"></div>`);
  async function bot(t,acts,me){const ty=add('<div class="lm a"><span class="av">X</span><div class="ltyping"><span></span><span></span><span></span></div></div>');
    await wait(900);if(me!==run)return;ty.remove();
    const m=add(`<div class="lm a"><span class="av">X</span><div><p class="ln">X Fitness</p><div class="lw"><div class="lb"></div><span class="lt">${now()}</span></div>${(acts||[]).length?`<div class="lqr">${acts.map(x=>`<span>${esc(x)}</span>`).join('')}</div>`:''}</div></div>`);
    const b=m.querySelector('.lb');for(let k=0;k<=t.length;k+=4){if(me!==run)return;b.textContent=t.slice(0,k);log.scrollTop=log.scrollHeight;await wait(10);}
    b.textContent=t;log.scrollTop=log.scrollHeight;}
  async function steps(list,me){for(const s of list){if(me!==run)return;
    if(s.u){user(s.u);await wait(500);}else if(s.img){pic(s.img);await wait(500);}else await bot(s.a,s.acts,me);}}
  async function ask(text){const r=await fetch(BOT.base+'/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(40000),
      body:JSON.stringify({session_id:sid,message:text,member_id:member&&member.member_id,phone_last4:member&&member.phone_last4})});
    if(!r.ok)throw new Error('HTTP '+r.status);const j=await r.json();if(j.member)member=j.member;return j;}
  async function tap(i){const btn=DATA.line.buttons[i],me=++run;user(btn.text);await wait(400);
    if(BOT.live&&btn.live){try{const j=await ask(btn.text);note.textContent='คำตอบนี้มาจากบอทจริง ('+BOT.base+')';await bot(j.answer,j.actions,me);return;}
      catch(e){note.textContent='เรียกบอทไม่สำเร็จ ('+e.message+') ใช้คำตอบที่บันทึกไว้แทน';}}
    else note.textContent='ออฟไลน์ · '+btn.note;
    await steps(btn.steps,me);}
  ph.querySelectorAll('.rm').forEach(b=>b.addEventListener('click',()=>tap(+b.dataset.i)));
  ph.querySelector('.lbar').onclick=()=>ph.classList.toggle('menu-off');
  async function replay(){const me=++run;log.innerHTML='';clock=1;ph.classList.add('menu-off');
    note.textContent='▶ บทสนทนาจากผลทดสอบ: ยืนยันสมาชิก · Q01 · I01 สลิป · กดเมนูด้านล่างเพื่อถามต่อ';
    await steps(DATA.line.script,me);await wait(2500);if(me===run)ph.classList.remove('menu-off');}
  document.getElementById('replay-line').onclick=replay;replay();})();
