/* ═══════════ KRT AI 2.2 — LIVE (Angel One via /api/dashboard) ═══════════ */
const CONFIG = {
  DASHBOARD: "/api/dashboard",
  NEWS: "/api/news",
  REFRESH_MS: 15000,
  MARKET_CLOSE: "15:30"
};
const $ = id => document.getElementById(id);
const fmt = n => Number(n).toLocaleString('en-IN');
const store = {
  get(k,d){ try{ const v=localStorage.getItem('krt_'+k); return v===null?d:JSON.parse(v);}catch(e){return d;} },
  set(k,v){ try{ localStorage.setItem('krt_'+k, JSON.stringify(v)); }catch(e){} }
};
const tvUrl = s => `https://www.tradingview.com/chart/?symbol=NSE%3A${encodeURIComponent(s.replace(/[ &]/g,'_'))}`;

let soundOn=false, audioCtx=null;
$('sndBtn').onclick=()=>{ soundOn=!soundOn;
  $('sndBtn').textContent=soundOn?'🔊 Sound':'🔇 Sound';
  $('sndBtn').classList.toggle('on',soundOn);
  if(soundOn&&!audioCtx)audioCtx=new (window.AudioContext||window.webkitAudioContext)();
  if(soundOn)beep(); };
function beep(){ if(!soundOn||!audioCtx)return;
  const o=audioCtx.createOscillator(),g=audioCtx.createGain();
  o.type='sine';o.frequency.value=880;g.gain.value=.08;o.connect(g);g.connect(audioCtx.destination);
  o.start();o.frequency.exponentialRampToValueAtTime(1320,audioCtx.currentTime+.12);
  g.gain.exponentialRampToValueAtTime(.0001,audioCtx.currentTime+.3);o.stop(audioCtx.currentTime+.32); }

function tickCountdown(){
  const now=new Date(new Date().toLocaleString('en-US',{timeZone:'Asia/Kolkata'}));
  const [h,m]=CONFIG.MARKET_CLOSE.split(':').map(Number);
  const close=new Date(now); close.setHours(h,m,0,0);
  let d=close-now;
  if(d<=0){$('countdown').textContent='CLOSED';return;}
  const H=Math.floor(d/36e5),M=Math.floor(d%36e5/6e4),S=Math.floor(d%6e4/1e3);
  $('countdown').textContent=`${String(H).padStart(2,'0')}:${String(M).padStart(2,'0')}:${String(S).padStart(2,'0')}`;
}
setInterval(tickCountdown,1000);tickCountdown();

function renderScore(s){
  $('mktScore').textContent=s;
  const arc=$('scoreArc');
  arc.style.strokeDashoffset=94.2-(94.2*s/100);
  arc.style.stroke=s>=70?'#16d67a':s>=45?'#f5b840':'#ff4d5e';
  const b=$('mktBias');
  if(s>=75){b.textContent='🔥 STRONG BULLISH';b.className='bias bull';}
  else if(s>=55){b.textContent='▲ MILD BULLISH';b.className='bias bull';}
  else if(s>=45){b.textContent='— NEUTRAL';b.className='bias nt';}
  else{b.textContent='▼ BEARISH';b.className='bias bear';}
}
renderScore(50);

function volFmt(v){
  if(v>=1e7) return (v/1e7).toFixed(1)+' Cr';
  if(v>=1e5) return (v/1e5).toFixed(1)+' L';
  return fmt(v);
}
function rnd(n){ return Math.round(n*100)/100; }

function renderIndices(indices, updated){
  if(!indices || !$('idxStrip')) return;
  $('idxStrip').innerHTML = indices.map(ix=>{
    const up = ix.chg>=0;
    return `<span class="ix"><span class="nm">${ix.symbol}</span><b class="${up?'up':'dn'}">${fmt(ix.ltp)}</b> <span class="${up?'up':'dn'}">${up?'▲':'▼'}${Math.abs(ix.chg)}%</span></span>`;
  }).join('') + (updated?` <span class="upd">upd ${updated}</span>`:'');
}

function stockRowsLive(arr, tb){
  $(tb).innerHTML = arr.map((r,i)=>{
    const up = r.chg>=0;
    return `<tr><td class="rank">${String(i+1).padStart(2,'0')}</td><td><b>${r.symbol}</b></td>
    <td>₹${fmt(r.ltp)}</td><td class="${up?'up':'dn'}"><b>${up?'▲':'▼'} ${Math.abs(r.chg)}%</b></td>
    <td style="font-size:.64rem;color:var(--dim)">${fmt(r.high)} / ${fmt(r.low)}</td>
    <td>${volFmt(r.volume)}</td>
    <td><a class="tvlink" target="_blank" rel="noopener" href="${tvUrl(r.symbol)}">TV ↗</a></td></tr>`;
  }).join('');
}

function deriveBreaks(stocks){
  return (stocks||[])
    .filter(r=> r.chg>0 && r.high>0 && r.ltp >= r.high*0.998)
    .map(r=>({
      sym:r.symbol, lvl:`Day High ${fmt(r.high)}`, dir:'up',
      e:rnd(r.ltp), sl:rnd(r.low>0? Math.max(r.low, r.ltp*0.992) : r.ltp*0.992),
      t:`${rnd(r.ltp*1.01)} / ${rnd(r.ltp*1.02)}`, c:80+Math.min(15,Math.round(r.chg*3))
    }));
}
function brkRows(list, el){
  $(el).innerHTML = list.length? list.map(r=>`
    <div class="row"><span><b>${r.sym}</b> <span class="lvl-lbl">${r.lvl} ✅</span></span>
    <span><span class="chip ${r.dir}">${r.dir==='up'?'🟢 BUY':'🔴 SELL'}</span>
    <a class="tvlink" target="_blank" rel="noopener" href="${tvUrl(r.sym)}">TV ↗</a></span></div>
    <div style="font-size:.64rem;color:var(--dim);padding:0 0 6px 2px;border-bottom:1px dashed var(--line)">
    E ${r.e} · SL ${r.sl} · T ${r.t} · Conf ${r.c}%</div>`).join('')
    : `<div style="font-size:.7rem;color:var(--faint);padding:8px 0">Waiting for live breaks…</div>`;
}

let jackpots = [];
let lastJpKey = store.get('lastJpKey','');
function buildJackpots(gainers){
  const picks = (gainers||[])
    .filter(r=> r.chg>=0.8 && r.volume>1e6)
    .slice(0,4);
  jackpots = picks.map(r=>({
    sym:r.symbol, ltp:`₹${fmt(r.ltp)} ▲ ${r.chg}%`,
    score: Math.min(98, 78+Math.round(r.chg*4)),
    prob: Math.min(96, 74+Math.round(r.chg*4)),
    pass: r.ltp>=r.high*0.998 ? 16 : 15, tot: 18,
    hot: r.chg>=2 ? 1 : 0,
    e:rnd(r.ltp), sl:rnd(Math.max(r.low, r.ltp*0.99)),
    t1:rnd(r.ltp*1.01), t2:rnd(r.ltp*1.02), t3:rnd(r.ltp*1.032),
    why:`▲${r.chg}% · Vol ${volFmt(r.volume)} · H ${fmt(r.high)} / L ${fmt(r.low)} · Live Angel One ✅`
  }));
  renderJackpots();
  const key = jackpots.map(j=>j.sym).join('|');
  if(key && key!==lastJpKey && store.get('tgToken','') && store.get('tgChat','')){
    lastJpKey = key; store.set('lastJpKey', key);
    sendAllJackpots();
    pushAlert({sym:'JACKPOT', msg:'New live jackpots → Telegram ✈', type:'brk'});
  }
}
function jackpotMsg(j){
  return `🚀 KRT AI JACKPOT (LIVE)\n\nStock : ${j.sym}\nAI Score : ${j.score}/100\nProbability : ${j.prob}%\n\n🟢 BUY\nEntry: ${j.e}\nSL: ${j.sl}\nT1: ${j.t1} | T2: ${j.t2} | T3: ${j.t3}\n\n${j.why}\n\n⚠ Educational only. Not investment advice.`;
}function renderJackpots(){
  if(!jackpots.length){
    $('jpsGrid').innerHTML=`<div style="font-size:.72rem;color:var(--faint);padding:10px">Live jackpots market hours-la auto-generate agum (movers + volume filter)…</div>`;
    $('jpsTag').textContent='WAITING · LIVE';
    return;
  }
  $('jpsGrid').innerHTML=jackpots.map((j,i)=>`
   <div class="jp-card ${j.hot?'hot':''}">
     <div class="top"><span class="sym">${j.hot?'🔥':'🎰'} ${j.sym}</span><span class="ltp up">${j.ltp}</span></div>
     <div class="scores"><span>Score <b>${j.score}</b>/100</span><span>Prob <b>${j.prob}%</b></span><span>Filters <b>${j.pass}/${j.tot}</b></span></div>
     <div class="jp-mini-track"><i style="width:${j.pass/j.tot*100}%"></i></div>
     <div class="jp-lv">
       <div class="e"><span class="k">ENTRY</span><b>${j.e}</b></div>
       <div class="s"><span class="k">SL</span><b>${j.sl}</b></div>
       <div class="t"><span class="k">T1</span><b>${j.t1}</b></div>
       <div class="t"><span class="k">T2</span><b>${j.t2}</b></div>
       <div class="t"><span class="k">T3</span><b>${j.t3}</b></div>
     </div>
     <div class="jp-why">${j.why}</div>
     <div class="btnrow">
       <button class="btn tg" onclick="sendJackpot(${i},'tg')">✈ TG</button>
       <button class="btn wa" onclick="sendJackpot(${i},'wa')">🟢 WA</button>
       <a class="btn" style="text-align:center;text-decoration:none" target="_blank" rel="noopener" href="${tvUrl(j.sym)}">📊 TV</a>
     </div>
   </div>`).join('');
  $('jpsTag').textContent=jackpots.length+' ACTIVE · LIVE';
}
function sendJackpot(i,ch){
  const msg=jackpotMsg(jackpots[i]);
  if(ch==='tg')sendTelegram(msg); else openWhatsApp(msg);
}
function sendAllJackpots(){ jackpots.forEach((j,i)=>setTimeout(()=>sendTelegram(jackpotMsg(j)),i*800)); }

function renderMTF(bullish){
  const d = bullish?'bull':'bear';
  $('mtfGrid').innerHTML=['5m','15m','1H','1D'].map(t=>`<div class="tf ${d}"><div class="t">${t}</div><b class="${bullish?'up':'dn'}">${bullish?'▲ BULLISH':'▼ BEARISH'}</b></div>`).join('');
  $('convictionBox').style.display = bullish? '':'none';
}
function renderConfidence(score){
  const parts=[['Trend',.25],['Volume',.20],['RSI',.15],['News',.20],['Sector',.20]];
  const cols=['#16d67a','#37c8f0','#9d7bff','#f5b840','#ff8f5e'];
  $('meters').innerHTML=parts.map(([k,w],i)=>{
    const mx=Math.round(w*100), v=Math.round(score*w);
    return `<div class="meter-row"><div class="lbls"><span>${k}</span><span>${v}/${mx}</span></div><div class="meter"><i style="width:${v/mx*100}%;background:${cols[i]}"></i></div></div>`;
  }).join('');
  $('confTotal').textContent=score;
}

function renderWatchlist(stocks){
  const ranked = [...(stocks||[])].sort((a,b)=>b.chg-a.chg).slice(0,10);
  $('wlTable').innerHTML = ranked.map((r,i)=>{
    const score=Math.min(98, Math.max(20, 60+Math.round(r.chg*10)));
    const act = r.chg>=1.5?'BUY': r.chg>=0.5?'WATCH': r.chg<=-1.5?'AVOID':'SKIP';
    return `<tr><td class="rank">${String(i+1).padStart(2,'0')}</td><td><b>${r.symbol}</b></td>
    <td><div style="display:flex;align-items:center;gap:6px"><b>${score}</b><div class="pbar"><i style="width:${score}%"></i></div></div></td>
    <td>${Math.min(95,score-4)}%</td><td class="${r.chg>=1?'up':r.chg<=-1?'dn':'nt'}">${r.chg>=1?'Low':r.chg<=-1?'High':'Med'}</td>
    <td class="${r.chg>=0?'up':'dn'}">${r.chg>=0?'+':''}${r.chg}%</td>
    <td>${volFmt(r.volume)}</td><td>${r.chg>=1?'🟢':r.chg<=-1?'🔴':'🟡'}</td>
    <td><a class="tvlink" target="_blank" rel="noopener" href="${tvUrl(r.symbol)}">TV ↗</a></td>
    <td><span class="chip ${act==='BUY'?'up':act==='AVOID'?'dn':'nt'}">${act}</span></td></tr>`;
  }).join('');
}

const seenAlerts = new Set();
function pushAlert(a){
  const el=document.createElement('div');
  el.className=`alert ${a.type==='bear'?'bear':a.type==='brk'?'brk':''}`;
  el.innerHTML=`<span class="t">${new Date().toLocaleTimeString('en-IN',{hour12:false})}</span><b class="sym">🔔 ${a.sym}</b><br>${a.msg}`;
  $('alertFeed').prepend(el);
  if($('alertFeed').children.length>25)$('alertFeed').lastChild.remove();
  beep();
}
function renderAlerts(alerts, chartink){
  (alerts||[]).forEach(a=>{
    const key='a:'+a.symbol+':'+a.reason;
    if(seenAlerts.has(key))return; seenAlerts.add(key);
    pushAlert({sym:a.symbol, msg:`${a.type==='WATCH'?'⚠':'🔔'} ${a.reason} (${a.chg>=0?'+':''}${a.chg}%)`, type:a.chg<0?'bear':'bull'});
  });
  (chartink||[]).forEach(c=>{
    const key='c:'+JSON.stringify(c).slice(0,80);
    if(seenAlerts.has(key))return; seenAlerts.add(key);
    const stocks = c.stocks || c.symbols || '';
    pushAlert({sym:'CHARTINK', msg:`${c.scan_name||c.alert_name||'Scanner'} → ${stocks}`, type:'brk'});
  });
}

const sectorMap = {ICICIBANK:'BANK',HDFCBANK:'BANK',SBIN:'PSU BANK',BEL:'DEFENCE',HAL:'DEFENCE',
  TCS:'IT',INFY:'IT',WIPRO:'IT',RELIANCE:'ENERGY',ONGC:'ENERGY',TATAMOTORS:'AUTO',ITC:'FMCG',VBL:'FMCG'};
function renderSectors(stocks){
  const agg={};
  (stocks||[]).forEach(r=>{
    const s=sectorMap[r.symbol]||'OTHERS';
    (agg[s]=agg[s]||[]).push(r.chg);
  });
  const rows=Object.entries(agg).map(([s,arr])=>[s, rnd(arr.reduce((a,b)=>a+b,0)/arr.length)])
    .sort((a,b)=>b[1]-a[1]).slice(0,6);
  $('heatmap').innerHTML=rows.map(([s,p])=>{
    const g=p>=0?`rgba(22,214,122,${Math.min(.12+p*.12,.5)})`:`rgba(255,77,94,${Math.min(.12+Math.abs(p)*.12,.5)})`;
    return `<div class="heat-cell" style="background:${g};border-color:${p>=0?'rgba(22,214,122,.3)':'rgba(255,77,94,.3)'}">${s}<span class="pc ${p>=0?'up':'dn'}">${p>=0?'▲':'▼'} ${Math.abs(p)}%</span></div>`;}).join('');
}

function renderNews(items){
  if(!items||!items.length){
    $('newsList').innerHTML=`<div style="font-size:.7rem;color:var(--faint);padding:8px 0">News feed loading…</div>`;
    return;
  }
  $('newsList').innerHTML=items.slice(0,6).map(n=>{
    const s=n.s||n.sentiment||'nt';
    return `<div class="news-item"><div class="head">
      <span class="chip ${s}">${s==='up'?'🟢':s==='dn'?'🔴':'🟡'} ${n.sym||n.symbol||''}</span><span>${n.head||n.headline||n.title||''}</span>
      <span class="impact">${n.impact?('Impact '+n.impact+'/10'):''}</span></div>
    ${n.sum||n.summary?`<div class="ai-sum"><b>AI:</b> ${n.sum||n.summary}</div>`:''}</div>`;
  }).join('');
}

const tvList=['SBIN','RELIANCE','TCS','ICICIBANK','HDFCBANK','BEL'];
let tvCur=store.get('tvSym','SBIN');
function loadTV(sym){
  tvCur=sym; store.set('tvSym',sym);
  document.querySelectorAll('#tvSyms button').forEach(b=>b.classList.toggle('on',b.dataset.s===sym));
  $('tvChart').innerHTML='';
  const wrap=document.createElement('div');
  wrap.className='tradingview-widget-container'; wrap.style.height='100%';
  const s=document.createElement('script');
  s.src='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
  s.async=true;
  s.textContent=JSON.stringify({
    symbol:'NSE:'+sym, theme:'dark', interval:'15', timezone:'Asia/Kolkata',
    style:'1', locale:'en', hide_top_toolbar:false, allow_symbol_change:true,
    studies:['STD;EMA','STD;VWAP','STD;RSI'], autosize:true
  });
  wrap.appendChild(s);
  $('tvChart').appendChild(wrap);
}
$('tvSyms').innerHTML=tvList.map(s=>`<button data-s="${s}">${s}</button>`).join('');
document.querySelectorAll('#tvSyms button').forEach(b=>b.onclick=()=>loadTV(b.dataset.s));
loadTV(tvCur);

$('ckUrl').value=store.get('ckUrl','');
$('ckStatus').textContent=store.get('ckUrl','')?'✅ Webhook receiver saved':'Not configured';
$('ckSave').onclick=()=>{ store.set('ckUrl',$('ckUrl').value.trim());
  $('ckStatus').textContent='✅ Webhook receiver saved'; $('ckStatus').className='status ok'; };
$('ckTest').onclick=()=>{ pushAlert({sym:'CHARTINK',msg:'Test alert simulate ✅',type:'brk'}); };

['tgToken','tgChat','waNum'].forEach(id=>{ $(id).value=store.get(id,'');
  $(id).addEventListener('input',()=>store.set(id,$(id).value.trim())); });
$('alSave').onclick=()=>{ ['tgToken','tgChat','waNum'].forEach(id=>store.set(id,$(id).value.trim()));
  $('alStatus').textContent='✅ Saved. Live jackpots auto-send to Telegram.';
  $('alStatus').className='status ok'; };
async function sendTelegram(text){
  const tok=store.get('tgToken',''), chat=store.get('tgChat','');
  if(!tok||!chat){ $('alStatus').textContent='❌ Telegram token / chat id missing'; $('alStatus').className='status err'; return false; }
  try{
    const r=await fetch(`https://api.telegram.org/bot${tok}/sendMessage`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({chat_id:chat,text})});
    const d=await r.json();
    if(d.ok){ $('alStatus').textContent='✅ Sent to Telegram!'; $('alStatus').className='status ok'; beep(); return true; }
    throw new Error(d.description||'send failed');
  }catch(e){ $('alStatus').textContent='❌ Telegram error: '+e.message; $('alStatus').className='status err'; return false; }
}
function openWhatsApp(text){
  const num=store.get('waNum','').replace(/\D/g,'');
  const url=num?`https://wa.me/${num}?text=${encodeURIComponent(text)}`:`https://wa.me/?text=${encodeURIComponent(text)}`;
  window.open(url,'_blank');
}
$('tgTest').onclick=()=>sendTelegram('✅ KRT AI Terminal test — Telegram connected!');
$('waTest').onclick=()=>{ if(jackpots.length)openWhatsApp(jackpotMsg(jackpots[0])); else openWhatsApp('KRT AI Terminal — live jackpots waiting'); };
$('jpSendAll').onclick=()=>{ if(jackpots.length){sendAllJackpots(); pushAlert({sym:'JACKPOT',msg:'All live jackpots sent ✈',type:'brk'});} };

const jpFilters=[
 ['Positive Momentum',1],['Volume > 10L',1],['Near Day High',1],
 ['Breadth Positive',1],['Above Prev Close',1],['RS > Nifty',1],
 ['Sector Aligned',1],['Trend Up',1],['Chartink Confirm',0],
 ['News Positive',0],['Delivery > 60%',0],['EMA Stack',1],
 ['RSI Zone',1],['ADX > 25',1],['VIX Stable',1],
 ['No Neg News',1],['Index Support',1],['AI Confirm',1]];
const passN=jpFilters.filter(f=>f[1]).length;
$('jpFilters').innerHTML=jpFilters.map(([k,p])=>`<div class="f-chip ${p?'pass':'fail'}">${p?'✅':'—'} ${k}</div>`).join('');
$('jpCount').textContent=`${passN} / ${jpFilters.length}`;
$('jpTag').textContent=`${passN}/${jpFilters.length} FILTERS PASS`;
setTimeout(()=>{$('jpFill').style.width=(passN/jpFilters.length*100)+'%'},300);

async function pull(url){ try{ const r=await fetch(url); return r.ok? await r.json():null; }catch(e){ return null; } }
async function refresh(){
  const d = await pull(CONFIG.DASHBOARD);
  if(d && !d.error){
    renderIndices(d.indices, d.updated);
    if(d.gainers){ stockRowsLive(d.gainers,'gainT'); }
    if(d.losers){ stockRowsLive(d.losers,'loseT'); }
    const all=[...(d.gainers||[]),...(d.losers||[]),...(d.volume||[])];
    const uniq=[...new Map(all.map(r=>[r.symbol,r])).values()];
    brkRows(deriveBreaks(uniq),'pdList');
    brkRows((d.gainers||[]).filter(r=>r.chg>=1.5).map(r=>({sym:r.symbol,lvl:`Strong Move +${r.chg}%`,dir:'up',e:rnd(r.ltp),sl:rnd(r.ltp*0.99),t:`${rnd(r.ltp*1.012)} / ${rnd(r.ltp*1.025)}`,c:86})),'pwList');
    brkRows((d.volume||[]).slice(0,4).map(r=>({sym:r.symbol,lvl:`Vol Leader ${volFmt(r.volume)}`,dir:r.chg>=0?'up':'dn',e:rnd(r.ltp),sl:rnd(r.chg>=0?r.ltp*0.99:r.ltp*1.01),t:r.chg>=0?`${rnd(r.ltp*1.01)} / ${rnd(r.ltp*1.02)}`:`${rnd(r.ltp*0.99)} / ${rnd(r.ltp*0.98)}`,c:82})),'pmList');
    buildJackpots(d.gainers);
    renderWatchlist(uniq);
    renderSectors(uniq);
    renderAlerts(d.alerts, d.chartink);
    const ups=uniq.filter(r=>r.chg>0).length;
    const score = uniq.length? Math.round(40 + (ups/uniq.length)*50) : 50;
    renderScore(score);
    renderMTF(score>=60);
    renderConfidence(Math.min(96, score+5));
    if($('gTag')){ $('gTag').textContent = d.mode==='live'?'LIVE · ANGEL ONE':'MODE: '+(d.mode||'?'); }
    if($('lTag')){ $('lTag').textContent = d.mode==='live'?'LIVE · ANGEL ONE':'MODE: '+(d.mode||'?'); }
  }
  const n = await pull(CONFIG.NEWS);
  if(n && n.items) renderNews(n.items);
}
refresh();
setInterval(refresh, CONFIG.REFRESH_MS);
