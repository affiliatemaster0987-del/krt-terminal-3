/* ═══════════ KRT AI 4.0 — LIVE (Angel One + Chartink) ═══════════ */
const CONFIG = { DASHBOARD:"/api/dashboard", NEWS:"/api/news", REFRESH_MS:15000, MARKET_CLOSE:"15:30" };
const $ = id => document.getElementById(id);
const fmt = n => Number(n||0).toLocaleString('en-IN');
const store = {
  get(k,d){ try{ const v=localStorage.getItem('krt_'+k); return v===null?d:JSON.parse(v);}catch(e){return d;} },
  set(k,v){ try{ localStorage.setItem('krt_'+k, JSON.stringify(v)); }catch(e){} }
};
const rnd = n => Math.round(n*100)/100;
const volFmt = v => v>=1e7 ? (v/1e7).toFixed(1)+' Cr' : v>=1e5 ? (v/1e5).toFixed(1)+' L' : fmt(v);

/* ---------- sound ---------- */
let soundOn=false, audioCtx=null;
$('sndBtn').onclick=()=>{ soundOn=!soundOn;
  $('sndBtn').textContent=soundOn?'🔊 Sound':'🔇 Sound';
  $('sndBtn').classList.toggle('on',soundOn);
  if(soundOn&&!audioCtx)audioCtx=new (window.AudioContext||window.webkitAudioContext)();
  if(soundOn)beep(); };
function beep(hi){ if(!soundOn||!audioCtx)return;
  const o=audioCtx.createOscillator(),g=audioCtx.createGain();
  o.type='sine';o.frequency.value=hi?520:880;g.gain.value=.08;o.connect(g);g.connect(audioCtx.destination);
  o.start();o.frequency.exponentialRampToValueAtTime(hi?300:1320,audioCtx.currentTime+.12);
  g.gain.exponentialRampToValueAtTime(.0001,audioCtx.currentTime+.3);o.stop(audioCtx.currentTime+.32); }

/* ---------- countdown ---------- */
function tick(){
  const now=new Date(new Date().toLocaleString('en-US',{timeZone:'Asia/Kolkata'}));
  const [h,m]=CONFIG.MARKET_CLOSE.split(':').map(Number);
  const c=new Date(now); c.setHours(h,m,0,0);
  let d=c-now;
  if(d<=0){$('countdown').textContent='CLOSED';return;}
  const H=Math.floor(d/36e5),M=Math.floor(d%36e5/6e4),S=Math.floor(d%6e4/1e3);
  $('countdown').textContent=`${String(H).padStart(2,'0')}:${String(M).padStart(2,'0')}:${String(S).padStart(2,'0')}`;
}
setInterval(tick,1000);tick();

function renderScore(s){
  $('mktScore').textContent=s;
  const a=$('scoreArc');
  a.style.strokeDashoffset=94.2-(94.2*s/100);
  a.style.stroke=s>=70?'#16d67a':s>=45?'#f5b840':'#ff4d5e';
  const b=$('mktBias');
  if(s>=75){b.textContent='🔥 STRONG BULLISH';b.className='bias bull';}
  else if(s>=55){b.textContent='▲ MILD BULLISH';b.className='bias bull';}
  else if(s>=45){b.textContent='— NEUTRAL';b.className='bias nt';}
  else{b.textContent='▼ BEARISH';b.className='bias bear';}
}
renderScore(50);

/* ---------- WhatsApp ---------- */
$('waNum').value=store.get('waNum','');
$('alSave').onclick=()=>{ store.set('waNum',$('waNum').value.trim());
  $('alStatus').textContent='✅ Saved — alerts will open in WhatsApp.'; $('alStatus').className='status ok'; };
function openWA(text){
  const num=store.get('waNum','').replace(/\D/g,'');
  window.open((num?`https://wa.me/${num}?text=`:`https://wa.me/?text=`)+encodeURIComponent(text),'_blank');
}
$('waTest').onclick=()=>openWA('✅ KRT AI Terminal — WhatsApp connected!');

/* ---------- message builders ---------- */
function jpMsg(j){
  return `🎰 KRT JACKPOT — BUY\n\n${j.symbol}  ₹${fmt(j.ltp)} (▲${j.chg}%)\nSector: ${j.sector}\nScore: ${j.score}/100\nSetup: ${j.setup}\n\nEntry: ${j.e}\nSL: ${j.sl}\nT1: ${j.t1} | T2: ${j.t2} | T3: ${j.t3}\n\n⚠ Educational only. Not investment advice.`;
}
function dgMsg(d){
  return `💀 KRT DANGER — SELL / AVOID\n\n${d.symbol}  ₹${fmt(d.ltp)} (▼${Math.abs(d.chg)}%)\nSector: ${d.sector}\nRisk: ${d.score}/100\nReason: ${d.setup}\n\nEntry: ${d.e}\nSL: ${d.sl}\nT1: ${d.t1} | T2: ${d.t2}\n\n⚠ Educational only. Not investment advice.`;
}

/* ---------- JACKPOT / DANGER build ---------- */
let jackpots=[], dangers=[];
function buildJackpots(stocks, brk, sectorRank){
  const pdh=new Set((brk.pdh||[]).map(r=>r.symbol));
  const pwh=new Set((brk.pwh||[]).map(r=>r.symbol));
  const or5=new Set((brk.or5||[]).map(r=>r.symbol));
  jackpots = stocks.filter(r=>r.chg>=1 && (r.volume||0)>3e5)
    .map(r=>{
      const tags=[];
      if(pwh.has(r.symbol))tags.push('PWH Break');
      if(pdh.has(r.symbol))tags.push('PDH Break');
      if(or5.has(r.symbol))tags.push('5min High Break');
      const secRank = sectorRank[r.sector]||99;
      if(secRank<=3)tags.push('Sector Top-3');
      if(gapUpSet.has(r.symbol))tags.push('Gap Up Open');
      let score = 50 + Math.min(25,Math.round(r.chg*4)) + tags.length*7;
      if((r.volume||0)>1e7)score+=6;
      score=Math.min(99,score);
      return {...r, tags, score,
        setup: tags.length?tags.join(' + '):'Momentum',
        e:rnd(r.ltp), sl:rnd(Math.max(r.low||r.ltp*0.99, r.ltp*0.99)),
        t1:rnd(r.ltp*1.01), t2:rnd(r.ltp*1.02), t3:rnd(r.ltp*1.035)};
    })
    .filter(x=>x.score>=70 && x.tags.length>=1)
    .sort((a,b)=>b.score-a.score).slice(0,12);
  renderJackpots();
}
function buildDangers(stocks, brk, sectorRank, total){
  const pdl=new Set((brk.pdl||[]).map(r=>r.symbol));
  dangers = stocks.filter(r=>r.chg<=-1)
    .map(r=>{
      const tags=[];
      if(pdl.has(r.symbol))tags.push('PDL Breakdown');
      const secRank = sectorRank[r.sector]||99;
      if(secRank>=total-3)tags.push('Weak Sector');
      if(gapDownSet.has(r.symbol))tags.push('Gap Down Open');
      if((r.volume||0)>1e7)tags.push('Heavy Vol Selling');
      let score=50+Math.min(28,Math.round(Math.abs(r.chg)*4))+tags.length*7;
      score=Math.min(99,score);
      return {...r, tags, score,
        setup: tags.length?tags.join(' + '):'Weak momentum',
        e:rnd(r.ltp), sl:rnd(r.ltp*1.01),
        t1:rnd(r.ltp*0.99), t2:rnd(r.ltp*0.98)};
    })
    .sort((a,b)=>b.score-a.score).slice(0,12);
  renderDangers();
}
function renderJackpots(){
  $('jpTag').textContent=jackpots.length+' CALLS';
  if(!jackpots.length){ $('jackpotList').innerHTML=`<div class="empty">No strong jackpot setup yet — waiting for momentum + breakout confirmation</div>`; return; }
  $('jackpotList').innerHTML=jackpots.map((j,i)=>`
    <div class="sig-card bull">
      <div class="sig-top"><b class="sym">${j.symbol}</b>
        <span class="sec">${j.sector}</span>
        <span class="up">₹${fmt(j.ltp)} ▲${j.chg}%</span>
        <span class="sc">${j.score}<small>/100</small></span></div>
      <div class="sig-tags">${j.tags.map(t=>`<span class="t-chip">✅ ${t}</span>`).join('')||'<span class="t-chip dim">Momentum</span>'}</div>
      <div class="sig-lv"><span class="e">E ${j.e}</span><span class="s">SL ${j.sl}</span>
        <span class="t">T1 ${j.t1}</span><span class="t">T2 ${j.t2}</span><span class="t">T3 ${j.t3}</span></div>
      <div class="sig-foot"><span>Vol ${volFmt(j.volume)} · H ${fmt(j.high)} / L ${fmt(j.low)}</span>
        <button class="btn wa mini" onclick="waJP(${i})">🟢 WA</button></div>
    </div>`).join('');
}
function renderDangers(){
  $('dgTag').textContent=dangers.length+' CALLS';
  if(!dangers.length){ $('dangerList').innerHTML=`<div class="empty">No danger setups — market stable 👍</div>`; return; }
  $('dangerList').innerHTML=dangers.map((d,i)=>`
    <div class="sig-card bear">
      <div class="sig-top"><b class="sym">${d.symbol}</b>
        <span class="sec">${d.sector}</span>
        <span class="dn">₹${fmt(d.ltp)} ▼${Math.abs(d.chg)}%</span>
        <span class="sc dnsc">${d.score}<small>/100</small></span></div>
      <div class="sig-tags">${d.tags.map(t=>`<span class="t-chip bad">⚠ ${t}</span>`).join('')||'<span class="t-chip dim">Weak</span>'}</div>
      <div class="sig-lv"><span class="e">E ${d.e}</span><span class="s">SL ${d.sl}</span>
        <span class="t">T1 ${d.t1}</span><span class="t">T2 ${d.t2}</span></div>
      <div class="sig-foot"><span>Vol ${volFmt(d.volume)} · H ${fmt(d.high)} / L ${fmt(d.low)}</span>
        <button class="btn wa mini" onclick="waDG(${i})">🟢 WA</button></div>
    </div>`).join('');
}
function waJP(i){ openWA(jpMsg(jackpots[i])); }
function waDG(i){ openWA(dgMsg(dangers[i])); }
$('jpSendAll').onclick=()=>{ if(jackpots.length) openWA('🎰 KRT JACKPOT LIST\n\n'+jackpots.slice(0,6).map(j=>`${j.symbol} ₹${fmt(j.ltp)} ▲${j.chg}% | ${j.setup}\nE ${j.e} · SL ${j.sl} · T ${j.t1}/${j.t2}/${j.t3}`).join('\n\n')+'\n\n⚠ Educational only.'); };
$('dgSendAll').onclick=()=>{ if(dangers.length) openWA('💀 KRT DANGER LIST\n\n'+dangers.slice(0,6).map(d=>`${d.symbol} ₹${fmt(d.ltp)} ▼${Math.abs(d.chg)}% | ${d.setup}\nE ${d.e} · SL ${d.sl} · T ${d.t1}/${d.t2}`).join('\n\n')+'\n\n⚠ Educational only.'); };/* ---------- market mood ---------- */
function renderMood(m){
  if(!m||!$('moodPill'))return;
  $('moodPill').className='mood-pill mood-'+m.mood;
  $('moodPill').innerHTML=`<span class="em">${m.emoji}</span> MARKET MOOD: ${m.mood}
     <span class="nt2">· breadth ${m.breadth}% · ${m.note}</span>`;
}

/* ---------- global cues ---------- */
function renderGlobal(rows){
  if(!$('globalCues'))return;
  if(!rows||!rows.length){ $('globalCues').innerHTML=`<div class="empty">Global cues loading…</div>`; return; }
  $('globalCues').innerHTML=rows.map(g=>`<div class="glb-cell"><div class="k">${g.name}</div>
    <div class="v ${g.chg>=0?'up':'dn'}">${g.chg>=0?'▲':'▼'}${Math.abs(g.chg)}%</div></div>`).join('');
  const avg=rows.reduce((a,b)=>a+b.chg,0)/rows.length;
  $('glTag').textContent = avg>0.2?'GAP-UP BIAS':avg<-0.2?'GAP-DOWN BIAS':'FLAT';
}

/* ---------- options watchlist ---------- */
function renderOptions(stocks, sectorRank, total){
  const ce=[...stocks].filter(r=>r.chg>=1).sort((a,b)=>b.chg-a.chg).slice(0,6);
  const pe=[...stocks].filter(r=>r.chg<=-1).sort((a,b)=>a.chg-b.chg).slice(0,6);
  const line=(r,cls)=>{
    const rk=sectorRank[r.sector]||99, why=[cls==='up'?'trend up':'trend down'];
    if(cls==='up'&&rk<=3)why.push('strong sector');
    if(cls==='dn'&&rk>=total-3)why.push('weak sector');
    if((r.volume||0)>1e7)why.push('high volume');
    return `<div class="opt-row"><b>${r.symbol}</b><span class="sec">${r.sector||''}</span>
      <span class="${cls}">${r.chg>=0?'▲':'▼'}${Math.abs(r.chg)}%</span>
      <span class="why">${why.join(' · ')}</span></div>`;
  };
  $('ceList').innerHTML = ce.length? ce.map(r=>line(r,'up')).join('') : `<div class="empty">No clear CE bias</div>`;
  $('peList').innerHTML = pe.length? pe.map(r=>line(r,'dn')).join('') : `<div class="empty">No clear PE bias</div>`;
}

/* ---------- CHARTINK scanner buckets ---------- */
function ckName(c){ return c.scan_name||c.alert_name||c.scanName||c.name||'Chartink scan'; }
function ckStocks(c){
  let st=c.stocks||c.symbols||c.stock||'';
  if(Array.isArray(st)) st=st.join(', ');
  if(!st&&c.data) st=(typeof c.data==='string'?c.data:JSON.stringify(c.data)).slice(0,150);
  return st;
}
function ckTime(c){ return c.triggered_at||c.at||c.time||''; }
const CK_BUCKETS=[
  {el:'pdhList',tag:'pdhTag',dir:'up',keys:['pdh','prev day high','previous day high','day high break']},
  {el:'pdlList',tag:'pdlTag',dir:'dn',keys:['pdl','prev day low','previous day low','day low break']},
  {el:'pwhList',tag:'pwhTag',dir:'up',keys:['pwh','prev week high','previous week high','week high']},
  {el:'pwlList',tag:'pwlTag',dir:'dn',keys:['pwl','prev week low','previous week low','week low']},
  {el:'orList', tag:'orTag', dir:'up',keys:['5 min','5min','five min','opening range','first candle','orb']},
];
function renderChartink(list){
  const all=(list||[]).slice().reverse();
  const used=new Set();
  CK_BUCKETS.forEach(b=>{
    const hits=all.filter(c=>{ const n=ckName(c).toLowerCase();
      const m=b.keys.some(k=>n.includes(k)); if(m)used.add(c); return m; });
    $(b.tag).textContent=hits.length+' HITS';
    $(b.el).innerHTML = hits.length? hits.slice(0,12).map(c=>`
      <div class="brk-row"><div><b>${ckStocks(c)||'—'}</b></div>
        <div class="brk-mid">${ckName(c)} ${ckTime(c)?'· '+ckTime(c):''}</div>
        <span class="chip ${b.dir}">${b.dir==='up'?'🟢 BUY':'🔴 SELL'}</span></div>`).join('')
      : `<div class="empty">No Chartink hits yet — create an alert with this keyword in the scanner name</div>`;
  });
  const others=all.filter(c=>!used.has(c));
  if($('ckOther')){
    $('ckOtherTag').textContent=others.length+' HITS';
    $('ckOther').innerHTML = others.length? others.slice(0,15).map(c=>`
      <div class="brk-row"><div><b>${ckStocks(c)||'—'}</b></div>
        <div class="brk-mid">${ckName(c)} ${ckTime(c)?'· '+ckTime(c):''}</div>
        <span class="chip nt">SCAN</span></div>`).join('')
      : `<div class="empty">Other Chartink scans appear here</div>`;
  }
}

/* ---------- pre-open gap ---------- */
let gapUpSet=new Set(), gapDownSet=new Set(), preopenData={up:[],down:[]};
function renderPreopen(po){
  preopenData = po || {up:[],down:[]};
  const up=preopenData.up||[], dn=preopenData.down||[];
  gapUpSet=new Set(up.map(x=>x.symbol)); gapDownSet=new Set(dn.map(x=>x.symbol));
  $('poTag').textContent = (up.length+dn.length)
      ? `${up.length}▲ / ${dn.length}▼ ${preopenData.final?'· FINAL':'· LIVE'}`
      : 'WAITING 9:00 AM';
  const row=(x,i,cls)=>`<div class="po-row"><span class="rk">${String(i+1).padStart(2,'0')}</span>
      <b>${x.symbol}</b><span class="sec">${x.sector||''}</span>
      <span class="px">₹${fmt(x.price)}</span>
      <span class="gp ${cls}">${x.gap>=0?'▲':'▼'}${Math.abs(x.gap)}% (${x.gappts>=0?'+':''}${fmt(x.gappts)})</span></div>`;
  $('gapUp').innerHTML = up.length? up.map((x,i)=>row(x,i,'up')).join('')
      : `<div class="empty">No gap-up yet — fills after 9:00 AM</div>`;
  $('gapDown').innerHTML = dn.length? dn.map((x,i)=>row(x,i,'dn')).join('')
      : `<div class="empty">No gap-down yet — fills after 9:00 AM</div>`;
}
$('poSend').onclick=()=>{
  const up=preopenData.up||[], dn=preopenData.down||[];
  if(!up.length && !dn.length) return;
  openWA('🌅 KRT PRE-OPEN GAP LIST'+(preopenData.final?' (FINAL)':' (LIVE)')+'\n\n▲ GAP UP\n'+
    up.slice(0,8).map(x=>`${x.symbol} ₹${fmt(x.price)} ▲${x.gap}%`).join('\n')+
    '\n\n▼ GAP DOWN\n'+dn.slice(0,8).map(x=>`${x.symbol} ₹${fmt(x.price)} ▼${Math.abs(x.gap)}%`).join('\n')+
    '\n\n⚠ Educational only. Not investment advice.');
};

/* ---------- sectors ---------- */
function renderSectors(sectors){
  const strong=sectors.slice(0,6), weak=[...sectors].reverse().slice(0,6);
  $('strongSectors').innerHTML=strong.map(s=>`
    <div class="sec-row">
      <div class="sec-head"><b>${s.sector}</b><span class="up">▲ ${s.chg}%</span></div>
      <div class="sec-stocks">${s.top.map(t=>`<span class="s-chip up">${t.symbol} ${t.chg>=0?'+':''}${t.chg}%</span>`).join('')}</div>
    </div>`).join('');
  $('weakSectors').innerHTML=weak.map(s=>`
    <div class="sec-row">
      <div class="sec-head"><b>${s.sector}</b><span class="${s.chg>=0?'up':'dn'}">${s.chg>=0?'▲':'▼'} ${Math.abs(s.chg)}%</span></div>
      <div class="sec-stocks">${s.weak.map(t=>`<span class="s-chip dn">${t.symbol} ${t.chg}%</span>`).join('')}</div>
    </div>`).join('');
}

/* ---------- tables ---------- */
function stockRows(arr, tb){
  $(tb).innerHTML=arr.map((r,i)=>{
    const up=r.chg>=0;
    return `<tr><td class="rank">${String(i+1).padStart(2,'0')}</td><td><b>${r.symbol}</b></td>
      <td class="sec">${r.sector||''}</td><td>₹${fmt(r.ltp)}</td>
      <td class="${up?'up':'dn'}"><b>${up?'▲':'▼'} ${Math.abs(r.chg)}%</b></td>
      <td style="font-size:.62rem;color:var(--dim)">${fmt(r.high)} / ${fmt(r.low)}</td>
      <td>${volFmt(r.volume)}</td></tr>`;
  }).join('');
}

/* ---------- alerts ---------- */
const seen=new Set();
function pushAlert(a){
  const el=document.createElement('div');
  el.className=`alert ${a.type==='DANGER'?'bear':a.type==='CRASH'?'brk':''}`;
  el.innerHTML=`<span class="t">${new Date().toLocaleTimeString('en-IN',{hour12:false})}</span><b class="sym">🔔 ${a.symbol}</b><br>${a.reason}`;
  $('alertFeed').prepend(el);
  if($('alertFeed').children.length>30)$('alertFeed').lastChild.remove();
  beep(a.type==='DANGER');
}
function renderAlerts(alerts, chartink){
  (alerts||[]).forEach(a=>{
    const k='a:'+a.symbol+a.reason; if(seen.has(k))return; seen.add(k); pushAlert(a);
  });
  (chartink||[]).forEach(c=>{
    const k='c:'+JSON.stringify(c).slice(0,60); if(seen.has(k))return; seen.add(k);
    const nm = ckName(c), st = ckStocks(c);
    pushAlert({symbol:'CHARTINK', reason:`<b>${nm}</b>${st?' → '+st:' (no stocks in payload)'}`, type:'CRASH'});
  });
}

/* ---------- news ---------- */
const TAGCLS={'CRASH RISK':'dn','COMPANY RISK':'dn','NEGATIVE':'dn','ORDER WIN':'up','STRONG POSITIVE':'up','POSITIVE':'up','RESULTS':'nt','NEUTRAL':'nt'};
function renderNews(items){
  if(!items||!items.length){ $('newsList').innerHTML=`<div class="empty">No fresh market news in the last 6 hours</div>`; return; }
  $('newsList').innerHTML=items.map(n=>`
    <div class="news-item"><div class="head">
      <span class="chip ${TAGCLS[n.tag]||'nt'}">${n.tag}</span>
      <span>${n.title}</span>
      <span class="impact">${n.impact}/10 · ${n.ago||''}</span></div>
      <div class="ai-sum">🕒 ${n.ago||''} · ${n.source}${n.stocks&&n.stocks.length?' · '+n.stocks.join(', '):''}</div></div>`).join('');
}
function renderNewsSignals(sig){
  const jp=(sig&&sig.jackpot)||[], dg=(sig&&sig.danger)||[], cr=(sig&&sig.market_crash)||[];
  $('newsJackpot').innerHTML = jp.length? jp.map(n=>`
    <div class="sig-card bull slim">
      <div class="sig-top"><b class="sym">${n.symbol}</b><span class="chip up">${n.tag}</span>
        <span class="impact">${n.impact}/10 · ${n.ago||''}</span>${n.chg!=null?`<span class="${n.chg>=0?'up':'dn'}">${n.chg>=0?'▲':'▼'}${Math.abs(n.chg)}%</span>`:''}</div>
      <div class="nh">${n.headline}</div>
      <div class="sig-foot"><span class="up">${n.verdict}</span>
        <button class="btn wa mini" onclick="openWA(${JSON.stringify('📰 NEWS JACKPOT\n\n'+n.symbol+'\n'+n.headline+'\n\n'+n.verdict+'\n\n⚠ Educational only.').replace(/"/g,'&quot;')})">🟢 WA</button></div>
    </div>`).join('') : `<div class="empty">No fresh positive news (last 6 hrs)</div>`;
  $('newsDanger').innerHTML = (cr.map(c=>`
    <div class="sig-card bear slim">
      <div class="sig-top"><b class="sym dn">⚠ MARKET CRASH RISK</b><span class="impact">${c.impact}/10 · ${c.ago||''}</span></div>
      <div class="nh">${c.headline}</div>
      <div class="sig-foot"><span class="dn">${c.action}</span></div>
    </div>`).join('') + dg.map(n=>`
    <div class="sig-card bear slim">
      <div class="sig-top"><b class="sym">${n.symbol}</b><span class="chip dn">${n.tag}</span>
        <span class="impact">${n.impact}/10 · ${n.ago||''}</span>${n.chg!=null?`<span class="${n.chg>=0?'up':'dn'}">${n.chg>=0?'▲':'▼'}${Math.abs(n.chg)}%</span>`:''}</div>
      <div class="nh">${n.headline}</div>
      <div class="sig-foot"><span class="dn">${n.verdict}</span></div>
    </div>`).join('')) || `<div class="empty">No fresh negative news (last 6 hrs) 👍</div>`;

  if(cr.length){
    $('crashBanner').style.display='block';
    $('crashBanner').innerHTML=`🚨 <b>CRASH ALERT</b> — ${cr[0].headline} <span class="cb-act">${cr[0].action}</span>`;
    if(!seen.has('crash:'+cr[0].headline)){ seen.add('crash:'+cr[0].headline); beep(true); }
  } else { $('crashBanner').style.display='none'; }
}

/* ---------- chartink panel ---------- */
$('ckUrl').value=store.get('ckUrl','');
if(store.get('ckUrl','')) $('ckStatus').textContent='✅ Saved';
$('ckSave').onclick=()=>{ store.set('ckUrl',$('ckUrl').value.trim());
  $('ckStatus').textContent='✅ Saved'; $('ckStatus').className='status ok'; };

/* ═══════════ MAIN LOOP ═══════════ */
async function pull(u){ try{ const r=await fetch(u); return r.ok? await r.json():null; }catch(e){ return null; } }
async function refresh(){
  const d=await pull(CONFIG.DASHBOARD);
  if(d && !d.error){
    if(d.indices) $('idxStrip').innerHTML=d.indices.map(ix=>{
      const up=ix.chg>=0;
      const pts = ix.chgpts!=null ? `${up?'+':'−'}${fmt(Math.abs(ix.chgpts))}` : '';
      return `<span class="ix"><span class="nm">${ix.symbol}</span><b class="${up?'up':'dn'}">${fmt(ix.ltp)}</b> <span class="${up?'up':'dn'}">${pts} (${up?'▲':'▼'}${Math.abs(ix.chg)}%)</span></span>`;
    }).join('')+(d.updated?` <span class="upd">upd ${d.updated}</span>`:'');

    const stocks=[...(d.gainers||[]),...(d.losers||[]),...(d.volume||[])];
    const uniq=[...new Map(stocks.map(r=>[r.symbol,r])).values()];
    const brk=d.breaks||{};
    const sectors=d.sectors||[];
    const rank={}; sectors.forEach((s,i)=>rank[s.sector]=i+1);

    renderMood(d.mood);
    renderGlobal(d.global);
    renderOptions(uniq, rank, sectors.length);
    renderPreopen(d.preopen);
    stockRows(d.gainers||[],'gainT');
    stockRows(d.losers||[],'loseT');
    renderChartink(d.chartink);
    buildJackpots(uniq,brk,rank);
    buildDangers(uniq,brk,rank,sectors.length);
    renderSectors(sectors);
    renderAlerts(d.alerts,d.chartink);

    const ups=uniq.filter(r=>r.chg>0).length;
    renderScore(uniq.length? Math.round(35+(ups/uniq.length)*55) : 50);
    $('uniCount').textContent=d.universe||uniq.length;
    const live = d.mode==='live';
    $('gTag').textContent = live?'LIVE · ANGEL ONE':'DEMO MODE';
    $('lTag').textContent = live?'LIVE · ANGEL ONE':'DEMO MODE';
  }
  const n=await pull(CONFIG.NEWS);
  if(n && !n.error){ renderNews(n.items); renderNewsSignals(n.signals); }
}
refresh();
setInterval(refresh, CONFIG.REFRESH_MS);
