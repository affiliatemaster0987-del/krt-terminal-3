/* ═══════════ KRT AI 3.0 — LIVE (Angel One) ═══════════ */
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
  $('alStatus').textContent='✅ Saved — alerts WhatsApp-la open agum.'; $('alStatus').className='status ok'; };
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
      let score = 50 + Math.min(25,Math.round(r.chg*4)) + tags.length*7;
      if((r.volume||0)>1e7)score+=6;
      score=Math.min(99,score);
      return {...r, tags, score,
        setup: tags.length?tags.join(' + '):'Momentum',
        e:rnd(r.ltp), sl:rnd(Math.max(r.low||r.ltp*0.99, r.ltp*0.99)),
        t1:rnd(r.ltp*1.01), t2:rnd(r.ltp*1.02), t3:rnd(r.ltp*1.035)};
    })
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
  if(!jackpots.length){ $('jackpotList').innerHTML=`<div class="empty">Jackpot setups waiting… (momentum + breakout confirm aana varum)</div>`; return; }
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
  if(!dangers.length){ $('dangerList').innerHTML=`<div class="empty">Danger setups illa — market stable 👍</div>`; return; }
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
$('dgSendAll').onclick=()=>{ if(dangers.length) openWA('💀 KRT DANGER LIST\n\n'+dangers.slice(0,6).map(d=>`${d.symbol} ₹${fmt(d.ltp)} ▼${Math.abs(d.chg)}% | ${d.setup}\nE ${d.e} · SL ${d.sl} · T ${d.t1}/${d.t2}`).join('\n\n')+'\n\n⚠ Educational only.'); };

/* ---------- break lists ---------- */
function brkRows(list, el, tagEl, dir, label){
  $(tagEl).textContent=(list||[]).length+' HITS';
  if(!list || !list.length){ $(el).innerHTML=`<div class="empty">Waiting… (levels 9:20 apram ready agum)</div>`; return; }
  $(el).innerHTML=list.map(r=>{
    const lv = dir==='up' ? (r.pwh||r.pdh||r.orh) : r.pdl;
    return `<div class="brk-row">
      <div><b>${r.symbol}</b> <span class="sec">${r.sector}</span></div>
      <div class="brk-mid">${label} ${fmt(lv)} ✅ · ₹${fmt(r.ltp)}
        <span class="${dir==='up'?'up':'dn'}">${dir==='up'?'▲':'▼'}${Math.abs(r.chg)}%</span> · Vol ${volFmt(r.volume)}</div>
      <span class="chip ${dir==='up'?'up':'dn'}">${dir==='up'?'🟢 BUY':'🔴 SELL'}</span>
    </div>`;
  }).join('');
}

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
    pushAlert({symbol:'CHARTINK', reason:`${c.scan_name||c.alert_name||'Scanner'} → ${c.stocks||''}`, type:'CRASH'});
  });
}

/* ---------- news ---------- */
const TAGCLS={'CRASH RISK':'dn','NEGATIVE':'dn','STRONG POSITIVE':'up','POSITIVE':'up','NEUTRAL':'nt'};
function renderNews(items){
  if(!items||!items.length){ $('newsList').innerHTML=`<div class="empty">News loading…</div>`; return; }
  $('newsList').innerHTML=items.map(n=>`
    <div class="news-item"><div class="head">
      <span class="chip ${TAGCLS[n.tag]||'nt'}">${n.tag}</span>
      <span>${n.title}</span>
      <span class="impact">${n.impact}/10</span></div>
      <div class="ai-sum">${n.source}${n.stocks&&n.stocks.length?' · '+n.stocks.join(', '):''}</div></div>`).join('');
}
function renderNewsSignals(sig){
  const jp=(sig&&sig.jackpot)||[], dg=(sig&&sig.danger)||[], cr=(sig&&sig.market_crash)||[];
  $('newsJackpot').innerHTML = jp.length? jp.map(n=>`
    <div class="sig-card bull slim">
      <div class="sig-top"><b class="sym">${n.symbol}</b><span class="chip up">${n.tag}</span>
        <span class="impact">${n.impact}/10</span>${n.chg!=null?`<span class="${n.chg>=0?'up':'dn'}">${n.chg>=0?'▲':'▼'}${Math.abs(n.chg)}%</span>`:''}</div>
      <div class="nh">${n.headline}</div>
      <div class="sig-foot"><span class="up">${n.verdict}</span>
        <button class="btn wa mini" onclick="openWA(${JSON.stringify('📰 NEWS JACKPOT\n\n'+n.symbol+'\n'+n.headline+'\n\n'+n.verdict+'\n\n⚠ Educational only.').replace(/"/g,'&quot;')})">🟢 WA</button></div>
    </div>`).join('') : `<div class="empty">Positive news calls waiting…</div>`;
  $('newsDanger').innerHTML = (cr.map(c=>`
    <div class="sig-card bear slim">
      <div class="sig-top"><b class="sym dn">⚠ MARKET CRASH RISK</b><span class="impact">${c.impact}/10</span></div>
      <div class="nh">${c.headline}</div>
      <div class="sig-foot"><span class="dn">${c.action}</span></div>
    </div>`).join('') + dg.map(n=>`
    <div class="sig-card bear slim">
      <div class="sig-top"><b class="sym">${n.symbol}</b><span class="chip dn">${n.tag}</span>
        <span class="impact">${n.impact}/10</span>${n.chg!=null?`<span class="${n.chg>=0?'up':'dn'}">${n.chg>=0?'▲':'▼'}${Math.abs(n.chg)}%</span>`:''}</div>
      <div class="nh">${n.headline}</div>
      <div class="sig-foot"><span class="dn">${n.verdict}</span></div>
    </div>`).join('')) || `<div class="empty">Negative news illa 👍</div>`;

  // crash banner
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
    // indices
    if(d.indices) $('idxStrip').innerHTML=d.indices.map(ix=>{
      const up=ix.chg>=0;
      return `<span class="ix"><span class="nm">${ix.symbol}</span><b class="${up?'up':'dn'}">${fmt(ix.ltp)}</b> <span class="${up?'up':'dn'}">${up?'▲':'▼'}${Math.abs(ix.chg)}%</span></span>`;
    }).join('')+(d.updated?` <span class="upd">upd ${d.updated}</span>`:'');

    const stocks=[...(d.gainers||[]),...(d.losers||[]),...(d.volume||[])];
    const uniq=[...new Map(stocks.map(r=>[r.symbol,r])).values()];
    const brk=d.breaks||{};
    const sectors=d.sectors||[];
    const rank={}; sectors.forEach((s,i)=>rank[s.sector]=i+1);

    stockRows(d.gainers||[],'gainT');
    stockRows(d.losers||[],'loseT');
    brkRows(brk.pdh,'pdhList','pdhTag','up','PDH');
    brkRows(brk.pwh,'pwhList','pwhTag','up','PWH');
    brkRows(brk.or5,'orList','orTag','up','5min High');
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
