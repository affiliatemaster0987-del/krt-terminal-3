/* ═══════════ CONFIG ═══════════ */
const CONFIG = {
  API_BASE: "/api",   // same-domain backend (app.py)
  ENDPOINTS: { gainers:"/gainers", losers:"/losers", pd:"/breaks/pd", pw:"/breaks/pw", pm:"/breaks/pm", news:"/news", jackpot:"/jackpot", scan:"/scan" },
  REFRESH_MS: 45000,
  MARKET_CLOSE: "15:30"
};
const $ = id => document.getElementById(id);
const fmt = n => Number(n).toLocaleString('en-IN');
const store = {
  get(k,d){ try{ const v=localStorage.getItem('krt_'+k); return v===null?d:JSON.parse(v);}catch(e){return d;} },
  set(k,v){ try{ localStorage.setItem('krt_'+k, JSON.stringify(v)); }catch(e){} }
};
const tvUrl = s => `https://www.tradingview.com/chart/?symbol=NSE%3A${s}`;

/* ---------- Sound ---------- */
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

/* ---------- Countdown ---------- */
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

/* ---------- Market score ---------- */
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
renderScore(88);

/* ═══════════ KRT JACKPOTS — TOP 4 ═══════════ */
const jackpots=[
 {sym:'SBIN',ltp:'₹1,085.40 ▲ 1.8%',score:97,prob:94,pass:15,tot:18,hot:1,
  e:1085,sl:1072,t1:1096,t2:1107,t3:1120,
  why:'Positive News 9.6/10 · PMH Break · Delivery 72% · RVol 3.4× · RSI 68 · Put Writing ✅'},
 {sym:'BEL',ltp:'₹412.60 ▲ 6.8%',score:93,prob:90,pass:15,tot:18,hot:1,
  e:406,sl:399,t1:418,t2:426,t3:434,
  why:'Defence Order ₹4,800 Cr · PDH Break · RVol 3.1× · Sector Leader · ADX 31 ✅'},
 {sym:'RELIANCE',ltp:'₹3,012.50 ▲ 3.1%',score:91,prob:88,pass:16,tot:18,hot:0,
  e:2990,sl:2938,t1:3060,t2:3120,t3:3180,
  why:'₹12,000 Cr Order Win · PMH Break 2985 · RVol 5.8× · MACD Bullish ✅'},
 {sym:'HAL',ltp:'₹4,620.00 ▲ 4.8%',score:88,prob:85,pass:15,tot:18,hot:0,
  e:4590,sl:4520,t1:4680,t2:4760,t3:4850,
  why:'PWH Break 4580 · Defence Strong · Delivery 68% · RSI 66 · Supertrend Buy ✅'}];
function jackpotMsg(j){
  return `🚀 KRT AI JACKPOT\n\nStock : ${j.sym}\nAI Score : ${j.score}/100\nProbability : ${j.prob}%\nFilters : ${j.pass}/${j.tot} ✅\n\n🟢 BUY\nEntry: ${j.e}\nSL: ${j.sl}\nT1: ${j.t1} | T2: ${j.t2} | T3: ${j.t3}\n\n${j.why}\n\n⚠ Educational only. Not investment advice.`;
}
function renderJackpots(){
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
  $('jpsTag').textContent=jackpots.length+' ACTIVE';
}
function sendJackpot(i,ch){
  const msg=jackpotMsg(jackpots[i]);
  if(ch==='tg')sendTelegram(msg); else openWhatsApp(msg);
}
function sendAllJackpots(){ jackpots.forEach((j,i)=>setTimeout(()=>sendTelegram(jackpotMsg(j)),i*800)); }
renderJackpots();

/* ═══════════ MTF + Confidence ═══════════ */
const mtf=[['5m','bull'],['15m','bull'],['1H','bull'],['1D','bull']];
$('mtfGrid').innerHTML=mtf.map(([t,d])=>`<div class="tf ${d}"><div class="t">${t}</div><b class="${d==='bull'?'up':'dn'}">${d==='bull'?'▲ BULLISH':'▼ BEARISH'}</b></div>`).join('');
$('convictionBox').style.display=mtf.every(m=>m[1]==='bull')?'':'none';
const conf=[['Trend',25,25,'#16d67a'],['Volume',18,20,'#37c8f0'],['RSI',13,15,'#9d7bff'],['News',19,20,'#f5b840'],['Sector',16,20,'#ff8f5e']];
$('meters').innerHTML=conf.map(([k,v,mx,c])=>`<div class="meter-row"><div class="lbls"><span>${k}</span><span>${v}/${mx}</span></div><div class="meter"><i style="width:${v/mx*100}%;background:${c}"></i></div></div>`).join('');
$('confTotal').textContent=conf.reduce((a,c)=>a+c[1],0);

/* ═══════════ TOP GAINERS / LOSERS — full lists ═══════════ */
const gainers=[
 ['BEL',412.6,6.8,'3.1×'],['SBIN',1085.4,4.2,'3.4×'],['RVNL',498.2,5.9,'2.7×'],
 ['HAL',4620.0,4.8,'2.2×'],['BHEL',288.4,4.5,'2.9×'],['IRFC',168.9,4.1,'2.4×'],
 ['TATAPOWER',432.7,3.8,'1.9×'],['NTPC',398.6,3.4,'1.7×'],['RELIANCE',3012.5,3.1,'5.8×'],
 ['COALINDIA',512.3,2.9,'1.6×'],['PFC',498.0,2.8,'1.8×'],['RECLTD',552.1,2.6,'1.5×'],
 ['ONGC',298.4,2.4,'1.4×'],['LT',3890.0,2.2,'1.3×'],['HDFCBANK',1742.6,2.0,'1.6×'],
 ['ADANIPORTS',1420.8,1.9,'1.4×'],['POWERGRID',342.2,1.8,'1.2×'],['AXISBANK',1245.5,1.6,'1.3×'],
 ['ICICIBANK',1310.2,1.4,'1.2×'],['MARUTI',12480.0,1.2,'1.1×']];
const losers=[
 ['INFY',1498.2,-3.4,'2.1×'],['TCS',3820.4,-2.8,'1.8×'],['WIPRO',488.6,-2.6,'1.9×'],
 ['TECHM',1542.0,-2.4,'1.6×'],['HCLTECH',1698.4,-2.2,'1.5×'],['LTIM',5240.0,-2.0,'1.4×'],
 ['TATAMOTORS',925.3,-1.8,'1.3×'],['M&M',2890.4,-1.6,'1.2×'],['BAJAJ-AUTO',9420.0,-1.5,'1.1×'],
 ['HEROMOTOCO',4680.2,-1.4,'1.2×'],['EICHERMOT',4998.6,-1.3,'1.0×'],['SUNPHARMA',1755.0,-1.1,'1.1×'],
 ['CIPLA',1620.4,-1.0,'1.0×'],['DRREDDY',6890.0,-0.9,'0.9×'],['NESTLEIND',2480.6,-0.8,'0.8×'],
 ['HINDUNILVR',2652.2,-0.7,'0.9×'],['TITAN',3410.5,-0.6,'1.0×'],['ASIANPAINT',2890.8,-0.6,'1.4×'],
 ['BRITANNIA',5720.0,-0.5,'0.7×'],['DIVISLAB',5980.4,-0.4,'0.8×']];
function stockRows(arr,tb){
  $(tb).innerHTML=arr.map((r,i)=>{
    const up=r[2]>=0;
    return `<tr><td class="rank">${String(i+1).padStart(2,'0')}</td><td><b>${r[0]}</b></td>
    <td>₹${fmt(r[1])}</td><td class="${up?'up':'dn'}"><b>${up?'▲':'▼'} ${Math.abs(r[2])}%</b></td>
    <td>${r[3]}</td><td><a class="tvlink" target="_blank" rel="noopener" href="${tvUrl(r[0].replace('&','_'))}">TV ↗</a></td></tr>`;
  }).join('');
}
stockRows(gainers,'gainT'); stockRows(losers,'loseT');

/* ═══════════ BREAK CALL LISTS ═══════════ */
function brkRows(list,el){
  $(el).innerHTML=list.map(r=>`
    <div class="row"><span><b>${r.sym}</b> <span class="lvl-lbl">${r.lvl}</span></span>
    <span><span class="chip ${r.dir}">${r.dir==='up'?'🟢 BUY':'🔴 SELL'}</span>
    <a class="tvlink" target="_blank" rel="noopener" href="${tvUrl(r.sym)}">TV ↗</a></span></div>
    <div style="font-size:.64rem;color:var(--dim);padding:0 0 6px 2px;border-bottom:1px dashed var(--line)">
    E ${r.e} · SL ${r.sl} · T ${r.t} · Conf ${r.c}%</div>`).join('');
}
brkRows([
 {sym:'BEL',lvl:'PDH 405 ✅',dir:'up',e:'406',sl:'399',t:'418 / 426',c:92},
 {sym:'SBIN',lvl:'PDH 1078 ✅',dir:'up',e:'1080',sl:'1071',t:'1096 / 1107',c:94},
 {sym:'RVNL',lvl:'PDH 486 ✅',dir:'up',e:'488',sl:'479',t:'502 / 512',c:88},
 {sym:'INFY',lvl:'PDL 1512 ⚠',dir:'dn',e:'1508',sl:'1522',t:'1488 / 1472',c:84},
 {sym:'TATAMOTORS',lvl:'PDL 934 ⚠',dir:'dn',e:'931',sl:'941',t:'916 / 904',c:80},
],'pdList');
brkRows([
 {sym:'HAL',lvl:'PWH 4580 ✅',dir:'up',e:'4590',sl:'4520',t:'4680 / 4760',c:91},
 {sym:'BHEL',lvl:'PWH 282 ✅',dir:'up',e:'283',sl:'276',t:'292 / 299',c:87},
 {sym:'IRFC',lvl:'PWH 164 ✅',dir:'up',e:'165',sl:'160',t:'171 / 176',c:85},
 {sym:'PFC',lvl:'PWH 492 ✅',dir:'up',e:'493',sl:'484',t:'506 / 515',c:83},
],'pwList');
brkRows([
 {sym:'RELIANCE',lvl:'PMH 2985 ✅',dir:'up',e:'2990',sl:'2938',t:'3060 / 3120',c:96},
 {sym:'SBIN',lvl:'PMH 1069 ✅',dir:'up',e:'1072',sl:'1052',t:'1107 / 1140',c:93},
 {sym:'TATAPOWER',lvl:'PMH 424 ✅',dir:'up',e:'426',sl:'414',t:'441 / 452',c:89},
 {sym:'NTPC',lvl:'PMH 391 ✅',dir:'up',e:'393',sl:'384',t:'404 / 412',c:86},
],'pmList');

/* ═══════════ TRADINGVIEW EMBED ═══════════ */
const tvList=['SBIN','BEL','RELIANCE','HAL','RVNL','INFY'];
let tvCur=store.get('tvSym','SBIN');
function loadTV(sym){
  tvCur=sym; store.set('tvSym',sym);
  document.querySelectorAll('#tvSyms button').forEach(b=>b.classList.toggle('on',b.dataset.s===sym));
  $('tvChart').innerHTML='';
  const wrap=document.createElement('div');
  wrap.className='tradingview-widget-container'; wrap.style.height='100%';
  const inner=document.createElement('div'); inner.style.height='100%';
  wrap.appendChild(inner);
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

/* ═══════════ CHARTINK CONNECT ═══════════ */
$('ckUrl').value=store.get('ckUrl','');
$('ckStatus').textContent=store.get('ckUrl','')?'✅ Webhook receiver saved':'Not configured';
$('ckSave').onclick=()=>{ store.set('ckUrl',$('ckUrl').value.trim());
  $('ckStatus').textContent='✅ Webhook receiver saved'; $('ckStatus').className='status ok'; };
$('ckTest').onclick=()=>{ pushAlert({sym:'CHARTINK',msg:'Scanner hit: "PWH Break + RVol>2" → HAL, BHEL, IRFC',type:'brk'}); };

/* ═══════════ TELEGRAM / WHATSAPP ALERTS ═══════════ */
['tgToken','tgChat','waNum'].forEach(id=>{ $(id).value=store.get(id,'');
  $(id).addEventListener('input',()=>store.set(id,$(id).value.trim())); });
$('alSave').onclick=()=>{ ['tgToken','tgChat','waNum'].forEach(id=>store.set(id,$(id).value.trim()));
  $('alStatus').textContent='✅ Saved. New jackpot signals will auto-send to Telegram.';
  $('alStatus').className='status ok'; };

function jackpotText(){ return jackpotMsg(jackpots[0]); }
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
$('waTest').onclick=()=>openWhatsApp(jackpotText());
$('jpSendAll').onclick=()=>{ sendAllJackpots(); pushAlert({sym:'JACKPOT',msg:'All 4 jackpots sent to Telegram ✈',type:'brk'}); };

/* When new jackpots arrive from backend, call: notifyJackpot() */
function notifyJackpot(){ sendAllJackpots(); pushAlert({sym:'JACKPOT',msg:'New jackpot signals sent to Telegram ✈',type:'brk'}); }

/* ═══════════ NEWS ═══════════ */
const demoNews=[
 {sym:'SBIN',s:'up',head:'Govt approves expansion plan',impact:9.6,conf:94,sum:'Approval + sector strength + volume → momentum setup.'},
 {sym:'RELIANCE',s:'up',head:'Wins ₹12,000 Cr new energy order',impact:9.2,conf:97,sum:'Order-win scanner hit; expected move ▲2–5%.'},
 {sym:'BEL',s:'up',head:'Defence contract ₹4,800 Cr signed',impact:8.4,conf:91,sum:'Defence category ✅ PWH break confirming.'},
 {sym:'INFY',s:'dn',head:'BFSI client ramp-down flagged',impact:7.1,conf:82,sum:'Guidance risk; sector weak → avoid longs.'},
];
$('newsList').innerHTML=demoNews.map(n=>`
  <div class="news-item"><div class="head">
    <span class="chip ${n.s}">${n.s==='up'?'🟢':'🔴'} ${n.sym}</span><span>${n.head}</span>
    <span class="impact">Impact ${n.impact}/10 · ${n.conf}%</span></div>
  <div class="ai-sum"><b>AI:</b> ${n.sum}</div></div>`).join('');

/* ═══════════ SECTORS ═══════════ */
const sectors=[['PSU BANK',2.4],['DEFENCE',1.9],['ENERGY',1.7],['BANK',1.2],['AUTO',-0.6],['IT',-1.3]];
$('heatmap').innerHTML=sectors.map(([s,p])=>{
  const g=p>=0?`rgba(22,214,122,${Math.min(.12+p*.12,.5)})`:`rgba(255,77,94,${Math.min(.12+Math.abs(p)*.12,.5)})`;
  return `<div class="heat-cell" style="background:${g};border-color:${p>=0?'rgba(22,214,122,.3)':'rgba(255,77,94,.3)'}">${s}<span class="pc ${p>=0?'up':'dn'}">${p>=0?'▲':'▼'} ${Math.abs(p)}%</span></div>`;}).join('');

/* ═══════════ ALERT FEED ═══════════ */
const demoAlerts=[
 {sym:'RELIANCE',msg:'🚨 PMH Break 2985 ✅ · New order news · AI 96%',type:'brk'},
 {sym:'BEL',msg:'PDH Break ✅ · RVol 3.1×',type:'bull'},
 {sym:'HAL',msg:'PWH Break 4580 ✅ · Defence sector leader',type:'bull'},
 {sym:'SBIN',msg:'VWAP Reclaim + PMH Break ✅',type:'bull'},
 {sym:'INFY',msg:'PDL Breakdown ⚠ · IT weak',type:'bear'},
];
function pushAlert(a){
  const el=document.createElement('div');
  el.className=`alert ${a.type==='bear'?'bear':a.type==='brk'?'brk':''}`;
  el.innerHTML=`<span class="t">${new Date().toLocaleTimeString('en-IN',{hour12:false})}</span><b class="sym">🔔 ${a.sym}</b><br>${a.msg}`;
  $('alertFeed').prepend(el);
  if($('alertFeed').children.length>25)$('alertFeed').lastChild.remove();
  beep();
}
demoAlerts.forEach((a,i)=>setTimeout(()=>pushAlert(a),i*400));

/* ═══════════ WATCHLIST ═══════════ */
const wl=[
 ['SBIN',97,94,'Low','+3.2%','4/4 ▲','🟢','BUY'],['BEL',93,90,'Low','+2.8%','4/4 ▲','🟢','BUY'],
 ['RELIANCE',91,88,'Med','+2.5%','3/4 ▲','🟢','BUY'],['HAL',88,85,'Low','+2.4%','4/4 ▲','🟢','BUY'],
 ['RVNL',84,80,'Med','+2.6%','3/4 ▲','🟢','WATCH'],['TATAPOWER',82,79,'Med','+2.2%','3/4 ▲','🟡','WATCH'],
 ['NTPC',76,72,'Low','+1.4%','2/4','🟡','WATCH'],['PFC',74,70,'Med','+1.6%','2/4','🟡','WATCH'],
 ['TATASTEEL',61,58,'High','+1.8%','2/4','🟡','SKIP'],['INFY',44,40,'High','−1.5%','1/4 ▼','🔴','AVOID']];
$('wlTable').innerHTML=wl.map((r,i)=>`
  <tr><td class="rank">${String(i+1).padStart(2,'0')}</td><td><b>${r[0]}</b></td>
  <td><div style="display:flex;align-items:center;gap:6px"><b>${r[1]}</b><div class="pbar"><i style="width:${r[1]}%"></i></div></div></td>
  <td>${r[2]}%</td><td class="${r[3]==='Low'?'up':r[3]==='High'?'dn':'nt'}">${r[3]}</td>
  <td class="${r[4].startsWith('−')?'dn':'up'}">${r[4]}</td><td>${r[5]}</td><td>${r[6]}</td>
  <td><a class="tvlink" target="_blank" rel="noopener" href="${tvUrl(r[0])}">TV ↗</a></td>
  <td><span class="chip ${r[7]==='BUY'?'up':r[7]==='AVOID'?'dn':'nt'}">${r[7]}</span></td></tr>`).join('');

/* ═══════════ JACKPOT FILTERS ═══════════ */
const jpFilters=[
 ['Positive News ≥ 8/10',1],['Order Win / Govt Contract',1],['Earnings Beat',1],
 ['Delivery > 60%',1],['Rel. Volume > 2×',1],['RS > Nifty',1],
 ['Sector Top-3',1],['Above VWAP',1],['PDH Break',1],
 ['PWH Break',1],['PMH Break',1],['EMA 9>21>50>200',1],
 ['RSI 60–75',1],['ADX > 25',1],['MACD Bullish',1],
 ['Supertrend Buy',0],['Put Writing > Call',0],['No Nearby Resistance',0]];
const pass=jpFilters.filter(f=>f[1]).length;
$('jpFilters').innerHTML=jpFilters.map(([k,p])=>`<div class="f-chip ${p?'pass':'fail'}">${p?'✅':'—'} ${k}</div>`).join('');
$('jpCount').textContent=`${pass} / ${jpFilters.length}`;
$('jpTag').textContent=`${pass}/${jpFilters.length} FILTERS PASS`;
setTimeout(()=>{$('jpFill').style.width=(pass/jpFilters.length*100)+'%'},300);

/* ═══════════ LIVE API BRIDGE ═══════════
   Flask backend (app.py) routes-la irundhu data pull:
   /api/gainers, /api/losers, /api/breaks/pd, /api/breaks/pw,
   /api/breaks/pm, /api/jackpot — 45s-ku oru dhadava refresh. */
async function pull(path){ if(!CONFIG.API_BASE)return null;
  try{ const r=await fetch(CONFIG.API_BASE+path); return r.ok? await r.json():null; }catch(e){ return null; } }
async function refresh(){
  const g=await pull(CONFIG.ENDPOINTS.gainers); if(g&&g.length)stockRows(g,'gainT');
  const l=await pull(CONFIG.ENDPOINTS.losers); if(l&&l.length)stockRows(l,'loseT');
  const pd=await pull(CONFIG.ENDPOINTS.pd); if(pd&&pd.length)brkRows(pd,'pdList');
  const pw=await pull(CONFIG.ENDPOINTS.pw); if(pw&&pw.length)brkRows(pw,'pwList');
  const pm=await pull(CONFIG.ENDPOINTS.pm); if(pm&&pm.length)brkRows(pm,'pmList');
  const jp=await pull(CONFIG.ENDPOINTS.jackpot); if(jp&&jp.newSignal)notifyJackpot();
}
setInterval(refresh,CONFIG.REFRESH_MS); refresh();
