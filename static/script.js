/* ═══════════ KRT AI 3.0 — LIVE (Angel One) ═══════════ */
const CONFIG = { DASHBOARD:"/api/dashboard", NEWS:"/api/news", REFRESH_MS:20000, MARKET_CLOSE:"15:30" };
const $ = id => document.getElementById(id);
const fmt = n => Number(n||0).toLocaleString('en-IN');
const store = {
  get(k,d){ try{ const v=localStorage.getItem('krt_'+k); return v===null?d:JSON.parse(v);}catch(e){return d;} },
  set(k,v){ try{ localStorage.setItem('krt_'+k, JSON.stringify(v)); }catch(e){} }
};
const rnd = n => Math.round(n*100)/100;
// skip re-render when the payload for a section has not changed (big CPU saver)
const _sig={};
function changed(key, val){
  const h = JSON.stringify(val);
  if(_sig[key]===h) return false;
  _sig[key]=h; return true;
}
const volFmt = v => v>=1e7 ? (v/1e7).toFixed(1)+' Cr' : v>=1e5 ? (v/1e5).toFixed(1)+' L' : fmt(v);

/* ---------- sound ---------- */
let soundOn=false, audioCtx=null;
$('sndBtn') && ($('sndBtn').onclick=()=>{ soundOn=!soundOn;
  $('sndBtn').textContent=soundOn?'🔊 Sound':'🔇 Sound';
  $('sndBtn').classList.toggle('on',soundOn);
  if(soundOn&&!audioCtx)audioCtx=new (window.AudioContext||window.webkitAudioContext)();
  if(soundOn)beep('buy'); });
// Distinct tones so you can tell what happened without looking at the screen.
//   buy    two rising notes
//   sell   two falling notes
//   target three quick rising notes
//   stop   low double thud
//   crash  urgent siren, repeated
const TONES = {
  buy:    {seq:[[520,.10],[780,.14]],          gain:.09},
  sell:   {seq:[[640,.10],[380,.16]],          gain:.09},
  target: {seq:[[660,.07],[880,.07],[1180,.16]],gain:.11},
  stop:   {seq:[[260,.14],[200,.20]],          gain:.10},
  crash:  {seq:[[880,.12],[500,.12],[880,.12],[500,.20]], gain:.13},
};
function tone(f, dur, gain, at){
  const o=audioCtx.createOscillator(), g=audioCtx.createGain();
  o.type = gain>.1 ? 'square' : 'sine';
  o.frequency.setValueAtTime(f, at);
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(gain, at+0.012);
  g.gain.exponentialRampToValueAtTime(0.0001, at+dur);
  o.connect(g); g.connect(audioCtx.destination);
  o.start(at); o.stop(at+dur+0.02);
}
function beep(kind){
  if(!soundOn||!audioCtx) return;
  if(kind===true) kind='sell';            // old call style
  const t = TONES[kind] || TONES.buy;
  let at = audioCtx.currentTime;
  t.seq.forEach(([f,d])=>{ tone(f,d,t.gain,at); at += d*0.85; });
}

/* ---------- countdown ---------- */
function renderStatus(st){
  if(!st||!$('mktStatus'))return;
  $('mktStatus').className='mkt-status s-'+st.state;
  $('mktStatus').innerHTML=`<b>${st.text}</b><span>${st.sub}</span>`;
}

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
if($('waNum')) $('waNum').value=store.get('waNum','');
$('alSave') && ($('alSave').onclick=()=>{ store.set('waNum',$('waNum').value.trim());
  $('alStatus').textContent='✅ Saved'; $('alStatus').className='status ok'; });
function openWA(text){
  const num=store.get('waNum','').replace(/\D/g,'');
  window.open((num?`https://wa.me/${num}?text=`:`https://wa.me/?text=`)+encodeURIComponent(text),'_blank');
}
$('waTest') && ($('waTest').onclick=()=>openWA('✅ KRT AI Terminal — WhatsApp connected!'));

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
      const ind=r.ind||{};
      let tech=0;
      if(ind.rsi!=null && ind.rsi>=55 && ind.rsi<=75){tags.push('RSI '+ind.rsi);tech+=8;}
      if(ind.ema9&&ind.ema21&&ind.ema9>ind.ema21){tags.push('EMA 9>21');tech+=8;}
      if(ind.vwap&&r.ltp>ind.vwap){tags.push('Above VWAP');tech+=8;}
      if(ind.adx&&ind.adx>=25){tags.push('ADX '+ind.adx);tech+=8;}
      if(ind.pdh&&r.ltp>ind.pdh){tags.push('PDH Break');tech+=10;}
      let score = 40 + Math.min(20,Math.round(r.chg*3)) + tags.length*4 + tech;
      if((r.volume||0)>1e7)score+=6;
      score=Math.min(99,score);
      const useATR = r.sl_long!=null;
      return {...r, tags, score, ind, atrMode:useATR,
        setup: tags.length?tags.join(' + '):'Momentum',
        e:rnd(r.ltp),
        sl: useATR? r.sl_long : rnd(Math.max(r.low||r.ltp*0.99, r.ltp*0.99)),
        t1: useATR? r.t1_long : rnd(r.ltp*1.01),
        t2: useATR? r.t2_long : rnd(r.ltp*1.02),
        t3: useATR? r.t3_long : rnd(r.ltp*1.035)};
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
      const ind=r.ind||{}; let tech=0;
      if(ind.rsi!=null && ind.rsi<=45){tags.push('RSI '+ind.rsi);tech+=8;}
      if(ind.ema9&&ind.ema21&&ind.ema9<ind.ema21){tags.push('EMA 9<21');tech+=8;}
      if(ind.vwap&&r.ltp<ind.vwap){tags.push('Below VWAP');tech+=8;}
      if(ind.adx&&ind.adx>=25){tags.push('ADX '+ind.adx);tech+=8;}
      if(ind.pdl&&r.ltp<ind.pdl){tags.push('PDL Break');tech+=10;}
      let score=40+Math.min(22,Math.round(Math.abs(r.chg)*3))+tags.length*4+tech;
      score=Math.min(99,score);
      const useATR = r.sl_short!=null;
      return {...r, tags, score, ind, atrMode:useATR,
        setup: tags.length?tags.join(' + '):'Weak momentum',
        e:rnd(r.ltp),
        sl: useATR? r.sl_short : rnd(r.ltp*1.01),
        t1: useATR? r.t1_short : rnd(r.ltp*0.99),
        t2: useATR? r.t2_short : rnd(r.ltp*0.98)};
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
      <div class="sig-foot"><span>Vol ${volFmt(j.volume)} · H ${fmt(j.high)} / L ${fmt(j.low)}${j.atrMode?' · <b class="atrb">ATR levels</b>':' · fixed % levels'}</span>
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
      <div class="sig-foot"><span>Vol ${volFmt(d.volume)} · H ${fmt(d.high)} / L ${fmt(d.low)}${d.atrMode?' · <b class="atrb">ATR levels</b>':' · fixed % levels'}</span>
        <button class="btn wa mini" onclick="waDG(${i})">🟢 WA</button></div>
    </div>`).join('');
}
function waJP(i){ openWA(jpMsg(jackpots[i])); }
function waDG(i){ openWA(dgMsg(dangers[i])); }
$('jpSendAll') && ($('jpSendAll').onclick=()=>{ if(jackpots.length) openWA('🎰 KRT JACKPOT LIST\n\n'+jackpots.slice(0,6).map(j=>`${j.symbol} ₹${fmt(j.ltp)} ▲${j.chg}% | ${j.setup}\nE ${j.e} · SL ${j.sl} · T ${j.t1}/${j.t2}/${j.t3}`).join('\n\n')+'\n\n⚠ Educational only.'); });
$('dgSendAll') && ($('dgSendAll').onclick=()=>{ if(dangers.length) openWA('💀 KRT DANGER LIST\n\n'+dangers.slice(0,6).map(d=>`${d.symbol} ₹${fmt(d.ltp)} ▼${Math.abs(d.chg)}% | ${d.setup}\nE ${d.e} · SL ${d.sl} · T ${d.t1}/${d.t2}`).join('\n\n')+'\n\n⚠ Educational only.'); });

/* ---------- signal tracker (v5) ---------- */
const STCLS={'LIVE':'st-live','T1 HIT':'st-t1','T2 HIT':'st-t1','TARGET COMPLETED':'st-done','SL HIT':'st-sl','EXPIRED':'st-exp'};
function accBox(a,label){
  a = a || {};
  const p=v=>v==null?'—':v+'%';
  return `<div class="acc-card"><div class="acc-h">${label}</div>
    <div class="acc-big ${a.accuracy>=60?'up':a.accuracy!=null?'dn':''}">${p(a.accuracy)}</div>
    <div class="acc-sub">Signals ${a.total} · Win ${a.wins} · SL ${a.sl} · Running ${a.running}</div>
    <div class="acc-rates"><span>T1 ${p(a.t1_rate)}</span><span>T2 ${p(a.t2_rate)}</span><span>T3 ${p(a.t3_rate)}</span></div>
    <div class="acc-rates"><span>Buy ${p(a.buy_acc)}</span><span>Sell ${p(a.sell_acc)}</span><span class="${a.avg_pnl>=0?'up':'dn'}">Avg ${a.avg_pnl>=0?'+':''}${a.avg_pnl}%</span></div>
  </div>`;
}
function sigRow(s){
  const t=(x,at,pc)=>x? `<span class="tg ${at?'hit':''}">${at?'✅':'○'} ${x}${pc?` <i>+${pc}%</i>`:''}${at?' '+at:''}</span>`:'';
  return `<div class="sig-row ${STCLS[s.status]||''}">
    <div class="sr-top"><b>${s.sym}</b>
      <span class="chip ${s.side==='BUY'?'up':'dn'}">${s.side}</span>
      <span class="tm">${s.ts}${s.done_at?' → '+s.done_at:''}</span>
      ${s.score?`<span class="sc2">${s.score}/100</span>`:''}
      <span class="stt">${s.status}</span>
      ${s.pnl_pct!=null?`<span class="${s.pnl_pct>=0?'up':'dn'}">${s.pnl_pct>=0?'+':''}${s.pnl_pct}%</span>`:''}</div>
    <div class="sr-lv">E ${s.entry} · SL ${s.sl}${s.sl_pct?` <i>-${s.sl_pct}%</i>`:''} ${t('T1 '+s.t1,s.t1_at,s.t1_pct)} ${t('T2 '+s.t2,s.t2_at,s.t2_pct)} ${s.t3?t('T3 '+s.t3,s.t3_at,s.t3_pct):''}</div>
    ${s.setup?`<div class="sr-why">${s.setup}</div>`:''}</div>`;
}
function renderTracker(t, indReady){
  if(!t)return;
  if($('accBox')) $('accBox').innerHTML = accBox(t.today,"TODAY'S AI PERFORMANCE")+accBox(t.d7,'LAST 7 DAYS')+accBox(t.d30,'LAST 30 DAYS');
  if($('liveCalls')){
    $('liveTag').textContent=(t.live||[]).length+' RUNNING';
    $('liveCalls').innerHTML=(t.live||[]).map(sigRow).join('')||'<div class="empty">No running calls right now</div>';
  }
  if($('doneCalls')){
    $('doneTag').textContent=(t.completed||[]).length+' TODAY';
    $('doneCalls').innerHTML=(t.completed||[]).map(sigRow).join('')||'<div class="empty">No completed calls yet today</div>';
  }
  if($('topCalls')){
    window.__top = t.top || [];
    renderTop();
  }
  if($('histBox')) $('histBox').innerHTML=(t.history||[]).slice(0,40).map(sigRow).join('')||'<div class="empty">History builds up as signals fire</div>';
  if($('trkTag')&&indReady!=null) $('trkTag').textContent=indReady+' STOCKS INDICATOR-READY';
}

/* ---------- top calls with score tiers ---------- */
let TIER = store.get('tier', 75);
function tierName(sc){ return sc>=85?'PREMIUM':sc>=80?'STRONG':'GOOD'; }
function tierCls(sc){ return sc>=85?'tier-p':sc>=80?'tier-s':'tier-g'; }
function renderTop(){
  const all = window.__top || [];
  const rows = all.filter(s => (s.score||0) >= TIER);
  $('topTag').textContent = rows.length + ' CALLS · ' + TIER + '+';
  document.querySelectorAll('#tierBtns button').forEach(b=>
    b.classList.toggle('on', Number(b.dataset.t)===TIER));
  const counts = {75:0,80:0,85:0};
  all.forEach(s=>{ const sc=s.score||0; if(sc>=75)counts[75]++; if(sc>=80)counts[80]++; if(sc>=85)counts[85]++; });
  document.querySelectorAll('#tierBtns button').forEach(b=>{
    const t=Number(b.dataset.t);
    b.textContent = (t===75?'75+ GOOD':t===80?'80+ STRONG':'85+ PREMIUM')+` (${counts[t]||0})`;
  });
  $('topCalls').innerHTML = rows.length ? rows.map(s=>`
    <div class="top-row ${tierCls(s.score)}"><b>${s.sym}</b>
      <span class="chip ${s.side==='BUY'?'up':'dn'}">${s.side}</span>
      <span class="tier">${tierName(s.score)}</span>
      <span class="tm">${s.ts}</span>
      <span class="lvmini">E ${s.entry} · SL ${s.sl} · T1 ${s.t1}</span>
      <span class="sc2">${s.score}</span>
      <span class="stt">${s.status}</span>
      ${s.pnl_pct!=null?`<span class="${s.pnl_pct>=0?'up':'dn'}">${s.pnl_pct>=0?'+':''}${s.pnl_pct}%</span>`:''}
      <button class="btn wa mini" onclick="waTop('${s.sym}')">🟢 WA</button>
    </div>`).join('')
    : `<div class="empty">No ${TIER}+ score calls yet today — signals start after 9:35 AM</div>`;
}
function waTop(sym){
  const s=(window.__top||[]).find(x=>x.sym===sym); if(!s)return;
  openWA(`${s.side==='BUY'?'🚀':'⚠'} KRT AI ${s.side} ALERT\n\n${s.sym}  [${tierName(s.score)} ${s.score}/100]\n\nEntry: ₹${s.entry}\nSL: ₹${s.sl}\nT1: ₹${s.t1}\nT2: ₹${s.t2}${s.t3?`\nT3: ₹${s.t3}`:''}\n\nReason: ${s.setup||'-'}\nTime: ${s.ts}\nStatus: ${s.status}\n\n⚠ Educational only. Not investment advice.`);
}
function setTier(t){ TIER=t; store.set('tier',t); renderTop(); }

/* ---------- 👑 confluence super setups ---------- */
let conflData=[];
function conflWhy(d){
  if(!d || !d.total) return 'Waiting for the first data poll';
  if(d.ready < 5)
    return `Indicators still building — ${d.ready}/${d.total} stocks ready. Each needs 20 one-minute candles, so this fills in about 20 minutes after the server starts.`;
  if(!d.pdh && !d.pwh)
    return 'Previous day / week levels have not loaded yet. Without them a setup cannot score high enough to appear. Check the server log for [levels].';
  if(!d.avgvol)
    return `Average volume history not loaded, so the 2x volume check always fails. Best score so far today: ${d.best}/10.`;
  return `Scanned ${d.ready} stocks. Best today: ${d.best}/10 confirmations — below the 6 needed. ${d.no_vwap||0} were on the wrong side of VWAP, ${d.rsi_out||0} had RSI out of range.`;
}
function renderConfluence(list, diag){
  if(!$('conflBox'))return;
  if(!changed('confl', [list, diag])) return;
  conflData=list||[];
  const sup=conflData.filter(c=>c.super).length;
  $('conflTag').textContent = conflData.length
      ? `${conflData.length} SETUPS${sup?' · '+sup+' A+':''}` : 'SCANNING';
  $('conflBox').innerHTML = conflData.length? conflData.map((c,i)=>`
    <div class="cf-card ${c.side==='BUY'?'cfb':'cfs'} ${c.super?'cfsuper':''}">
      <div class="cf-top">
        ${c.super?'<span class="cf-crown">SUPER CONFLUENCE</span>':''}
        <span class="cf-grade g${c.grade.replace('+','p')}">${c.grade}</span>
        <span class="cf-label">${c.label}</span>
        <span class="cf-setup">${c.setup}</span>
        <span class="cf-pts">${c.pts}<small>/10</small></span>
      </div>
      <div class="cf-head">
        <b class="sym">${c.symbol}</b><span class="sec">${c.sector}</span>
        <span class="chip ${c.side==='BUY'?'up':'dn'}">${c.side}</span>
        <span class="${c.chg>=0?'up':'dn'}">₹${fmt(c.ltp)} ${c.chg>=0?'▲':'▼'}${Math.abs(c.chg)}%</span>
        <span class="cf-score">${c.score}<small>/100</small></span>
      </div>
      <div class="cf-why">${c.why} · <b>${c.gnote}</b></div>
      <div class="cf-checks">
        ${c.checks.map(x=>`<span class="cf-ok">✅ ${x}</span>`).join('')}
        ${c.misses.map(x=>`<span class="cf-no">⬜ ${x}</span>`).join('')}
      </div>
      <div class="sig-lv"><span class="e">E ${c.entry}</span><span class="s">SL ${c.sl}</span>
        <span class="t">T1 ${c.t1}</span><span class="t">T2 ${c.t2}</span><span class="t">T3 ${c.t3}</span></div>
      ${c.event?`<div class="cf-event">📅 ${c.event}</div>`:''}
      <div class="cf-avoid">⚠ AVOID IF: ${c.avoid}${c.late?' · LATE — after 2:30 pm, use half size':''}</div>
      <div class="sig-foot"><span>${c.rvol?c.rvol+'x vol · ':''}RSI ${c.rsi} · ADX ${c.adx}</span>
        <button class="btn wa mini" onclick="waConfl(${i})">🟢 WA</button></div>
    </div>`).join('')
    : `<div class="empty">No high-confluence setup right now — a stock only appears here once 6 or more confirmations line up.<br><br><b>Why nothing yet:</b> ${conflWhy(diag)}</div>`;
}
function waConfl(i){
  const c=conflData[i]; if(!c)return;
  openWA(`KRT CONFLUENCE${c.super?' — SUPER SETUP':''}\n\n${c.symbol} — ${c.side}\nGrade ${c.grade} · ${c.label} · ${c.score}/100\n${c.setup} (${c.pts}/10 confirmations)\n\n${c.checks.map(x=>'✅ '+x).join('\n')}\n\nEntry: ${c.entry}\nSL: ${c.sl}\nT1: ${c.t1} | T2: ${c.t2} | T3: ${c.t3}\n\n⚠ AVOID IF: ${c.avoid}\n\n⚠ Educational only. Not investment advice.`);
}
$('conflSend') && ($('conflSend').onclick=()=>{
  if(!conflData.length)return;
  openWA('KRT CONFLUENCE SETUPS\n\n'+conflData.slice(0,5).map(c=>
    `${c.symbol} ${c.side} · ${c.grade} ${c.label} · ${c.setup}\nE ${c.entry} · SL ${c.sl} · T1 ${c.t1}`).join('\n\n')+
    '\n\n⚠ Educational only. Not investment advice.');
});

/* ---------- corporate filings + results diary ---------- */
const ANNCLS={'ORDER WIN':'up','APPROVAL':'up','EXPANSION':'up','CASH':'up',
  'FAVOURABLE ORDER':'up','ORDER LOSS':'dn','REGULATORY':'dn','STRESS':'dn',
  'RESULTS':'nt','FILING':'nt'};
function renderAnnouncements(list){
  if(!$('annBox'))return;
  if(!changed('ann', list)) return;
  const L=list||[];
  $('annTag').textContent = L.length? L.length+' FILINGS' : 'NONE YET';
  $('annBox').innerHTML = L.length? L.map(a=>`
    <div class="ann-row ${a.dir>0?'aup':a.dir<0?'adn':''}">
      <span class="ann-at">${a.at||a.ago||''}</span>
      <b>${a.symbol}</b>
      <span class="chip ${ANNCLS[a.tag]||'nt'}">${a.tag}</span>
      <span class="ann-imp">${a.impact}/10</span>
      <span class="ann-sub">${a.subject}</span>
    </div>`).join('')
    : `<div class="empty">No material filings yet today — this reads what companies file with the exchange, which lands before the news sites pick it up</div>`;
}
function renderResultsDiary(list){
  if(!$('calBox'))return;
  if(!changed('cal', list)) return;
  const L=list||[];
  const t=L.filter(x=>x.days===0).length;
  $('calTag').textContent = L.length? `${L.length} SCHEDULED${t?' · '+t+' TODAY':''}` : 'NONE';
  $('calBox').innerHTML = L.length? L.map(x=>`
    <div class="cal-row ${x.days===0?'cal0':x.days===1?'cal1':''}">
      <span class="cal-when">${x.when}</span>
      <b>${x.symbol}</b>
      <span class="cal-date">${x.date}</span>
      <span class="cal-note">${x.note}</span>
    </div>`).join('')
    : `<div class="empty">No results scheduled in the next 10 days for stocks in this universe</div>`;
}

/* ---------- breadth ---------- */
function renderBreadth(b){
  if(!b||!$('breadthBox'))return;
  $('breadthBox').innerHTML=`<div class="trk-grid">
    <div class="trk-cell"><div class="k">ADVANCING</div><div class="v up">${b.adv}</div></div>
    <div class="trk-cell"><div class="k">DECLINING</div><div class="v dn">${b.dec}</div></div>
    <div class="trk-cell"><div class="k">UNCHANGED</div><div class="v">${b.unch}</div></div>
    <div class="trk-cell"><div class="k">ABOVE VWAP</div><div class="v up">${b.above_vwap!=null?b.above_vwap+'%':'—'}</div></div>
    <div class="trk-cell"><div class="k">BELOW VWAP</div><div class="v dn">${b.below_vwap!=null?b.below_vwap+'%':'—'}</div></div>
    <div class="trk-cell"><div class="k">BIAS</div><div class="v ${b.bias==='Bullish'?'up':b.bias==='Bearish'?'dn':'nt'}">${b.bias}</div></div>
  </div>`;
}

/* ---------- opening range breaks ---------- */
function orRows(list, el, tag, label){
  if(!$(el))return;
  $(tag).textContent=(list||[]).length+' HITS';
  $(el).innerHTML=(list||[]).length? list.map(r=>`<div class="brk-row">
      <div><b>${r.symbol}</b> <span class="sec">${r.sector||''}</span></div>
      <div class="brk-mid">${label} ${fmt(r.level)} ✅ · ₹${fmt(r.ltp)} <span class="up">▲${r.chg}%</span> · Vol ${volFmt(r.volume)}</div>
      <span class="chip up">🟢 BUY</span></div>`).join('')
    : `<div class="empty">No breaks yet — levels build from live candles after 9:20 AM</div>`;
}

/* ---------- market mood ---------- */
function renderMood(m){
  if(!m||!$('moodPill'))return;
  $('moodPill').className='mood-pill mood-'+m.mood;
  const P={HAPPY:['Buy breakouts: ALLOWED','Sell calls: LOW PRIORITY','Jackpot buy: ENABLED'],
    GREED:['Buy breakouts: ALLOWED','Trail SL tightly','Avoid chasing'],
    FEAR:['Fresh longs: AVOID','Sell setups: ALLOWED','Position size: SMALL'],
    WEAK:['Buy breakouts: WAIT','Sell setups: ALLOWED','Jackpot buy: LIMITED'],
    CONFUSED:['Jackpot calls: LIMITED','Breakout trading: WAIT','Aggressive trading: AVOID'],
    MIXED:['Stock-specific only','Follow strong sectors','Normal size']}[m.mood]||[];
  $('moodPill').innerHTML=`<span class="em">${m.emoji}</span> MARKET MOOD: ${m.mood}
     ${m.headline?`<span class="mood-hl ${m.focus==='PE'?'hl-pe':'hl-ce'}">${m.headline}</span>`:''}
     <span class="nt2">· breadth ${m.breadth}% · ${m.note}</span>`;
  if($('moodRules')) $('moodRules').innerHTML=P.map(x=>`<span class="rule">${x}</span>`).join('');
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
function renderChartink(list){
  if(!changed("ck", arguments[0])) return;
  const all=(list||[]).slice().reverse();
  if(!$('ckOther'))return;
  $('ckOtherTag').textContent=all.length+' CALLS';
  $('ckOther').innerHTML = all.length? all.slice(0,40).map(c=>{
    const nm=ckName(c), st=ckStocks(c), tm=ckTime(c), px=c.trigger_prices||'';
    const bear=/low|sell|down|short|breakdown|crash|weak/i.test(nm);
    return `<div class="sig-row ${bear?'st-sl':'st-live'}">
      <div class="sr-top"><b>${st||'—'}</b>
        <span class="chip ${bear?'dn':'up'}">${bear?'SELL':'BUY'}</span>
        <span class="tm">${tm}</span>
        <span class="stt">${nm}</span></div>
      ${px?`<div class="sr-lv">Trigger: ${px}</div>`:''}
    </div>`;
  }).join('') : `<div class="empty">No scanner calls yet — create a Chartink alert with this webhook URL</div>`;
}

/* ---------- jackpot suggest zones ---------- */
let zoneData=[];
function renderZones(list){
  if(!changed("zones", arguments[0])) return;
  zoneData=list||[];
  if(!$('zoneBox'))return;
  const must=zoneData.filter(z=>z.must).length;
  $('zoneTag').textContent=`${zoneData.length} ZONES${must?' · '+must+' MUST TRY':''}`;
  $('zoneBox').innerHTML = zoneData.length? zoneData.map((z,i)=>`
    <div class="zone-card ${z.side==='BUY'?'zb':'zs'} ${z.must?'must':''}">
      <div class="z-top">
        <b class="sym">${z.symbol}</b><span class="sec">${z.sector||''}</span>
        <span class="chip ${z.side==='BUY'?'up':'dn'}">${z.side}</span>
        ${z.must?`<span class="must-tag">⭐ MUST TRY · ${z.side==='BUY'?'LOOKING BIG JACKPOT — CE':'LOOKING BIG CRASH — PE'}</span>`:''}
        <span class="z-score">${z.score}<small>/100</small></span>
      </div>
      <div class="z-band">${z.side==='BUY'?'Buy zone':'Sell zone'}
        <b>${fmt(z.zone_lo)} – ${fmt(z.zone_hi)}</b>
        <span class="z-ltp">LTP ₹${fmt(z.ltp)} (${z.chg>=0?'▲':'▼'}${Math.abs(z.chg)}%)</span></div>
      <div class="z-lv"><span class="s">SL ${z.sl}<i>${z.sl_pct!=null?'-'+z.sl_pct+'%':''}</i></span>
        <span class="t">T1 ${z.t1}<i>${z.t1_pct!=null?'+'+z.t1_pct+'%':''}</i></span>
        <span class="t">T2 ${z.t2}<i>${z.t2_pct!=null?'+'+z.t2_pct+'%':''}</i></span>
        <span class="t">T3 ${z.t3}<i>${z.t3_pct!=null?'+'+z.t3_pct+'%':''}</i></span></div>
      <div class="z-foot"><span>${z.note} · ${z.why}</span>
        <button class="btn wa mini" onclick="waZone(${i})">🟢 WA</button></div>
    </div>`).join('') : `<div class="empty">No clean zones right now — zones appear when trend, sector and VWAP line up</div>`;
}
function zMsg(z){
  return `${z.side==='BUY'?'🎯 KRT BUY ZONE':'🎯 KRT SELL ZONE'}${z.must?(z.side==='BUY'?' ⭐ MUST TRY · LOOKING BIG JACKPOT — CE':' ⭐ MUST TRY · LOOKING BIG CRASH — PE'):''}\n\n${z.symbol} (${z.sector})\nLTP ₹${fmt(z.ltp)} (${z.chg>=0?'+':''}${z.chg}%)\n\n${z.side==='BUY'?'Buy zone':'Sell zone'}: ${z.zone_lo} – ${z.zone_hi}\nSL: ${z.sl}\nT1: ${z.t1}\nT2: ${z.t2}\nT3: ${z.t3}\n\nScore: ${z.score}/100\nWhy: ${z.why}\n${z.note}\n\n⚠ Educational only. Not investment advice.`;
}
function waZone(i){ if(zoneData[i]) openWA(zMsg(zoneData[i])); }
$('zoneSend') && ($('zoneSend').onclick=()=>{
  if(!zoneData.length)return;
  openWA('🎯 KRT JACKPOT SUGGEST — ZONES\n\n'+zoneData.slice(0,8).map(z=>
    `${z.must?'⭐ ':''}${z.symbol} ${z.side} ${z.zone_lo}–${z.zone_hi} | SL ${z.sl} | T ${z.t1}/${z.t2} | ${z.score}/100`).join('\n')+
    '\n\n⚠ Educational only. Not investment advice.');
});

/* ---------- today's trade log ---------- */
function renderTradeLog(t){
  if(!$('tradeLog')||!t)return;
  const rows=(t.history||[]).filter(s=>s.date===(t.today_date||s.date));
  if(!changed('log', rows)) return;
  rows.forEach(s=>{
    if(/HIT|COMPLETED/.test(s.status) && s.status!=='SL HIT'){
      const k='hit:'+s.sym+s.status; if(!seen.has(k)){ seen.add(k); beep('target'); }
    } else if(s.status==='SL HIT'){
      const k='sl:'+s.sym; if(!seen.has(k)){ seen.add(k); beep('stop'); }
    }
  });
  const done=rows.filter(s=>s.status!=='LIVE').length;
  $('logTag').textContent=`${rows.length} CALLS · ${done} CLOSED`;
  const res=s=>{
    const at = t => t? ` <i class="hit-t">@ ${t}</i>` : '';
    if(s.status==='TARGET COMPLETED') return `<span class="res win">✅ ALL TARGETS HIT${at(s.t3_at)}</span>`;
    if(s.status==='T2 HIT')  return `<span class="res win">✅ TARGET 2 HIT${at(s.t2_at)}</span>`;
    if(s.status==='T1 HIT')  return `<span class="res win">✅ TARGET 1 HIT${at(s.t1_at)}</span>`;
    if(s.status==='SL HIT')  return `<span class="res loss">❌ SL HIT${at(s.sl_at)}</span>`;
    if(s.status==='EXPIRED') return `<span class="res exp">— NO HIT (expired)</span>`;
    return `<span class="res run">⏳ RUNNING</span>`;
  };
  $('tradeLog').innerHTML = rows.length? rows.map(s=>`
    <div class="log-row ${STCLS[s.status]||''}">
      <span class="lg-time">${s.ts}</span>
      <b class="lg-sym">${s.sym}</b>
      <span class="chip ${s.side==='BUY'?'up':'dn'}">${s.side}</span>
      ${s.source==='INDEX'?'<span class="lg-tag idx">INDEX OPTION</span>':'<span class="lg-tag stk">STOCK</span>'}
      <span class="lg-lv">E ${s.entry} · SL ${s.sl} · T1 ${s.t1}</span>
      ${res(s)}
      <span class="lg-line">Given ${s.ts}${s.t1_at?` · T1 ✅ ${s.t1_at}`:''}${s.t2_at?` · T2 ✅ ${s.t2_at}`:''}${s.t3_at?` · T3 ✅ ${s.t3_at}`:''}${s.sl_at?` · SL ❌ ${s.sl_at}`:''}</span>
      ${s.done_at?`<span class="lg-done">at ${s.done_at}</span>`:''}
      ${s.pnl_pct!=null?`<span class="${s.pnl_pct>=0?'up':'dn'}">${s.pnl_pct>=0?'+':''}${s.pnl_pct}%</span>`:''}
    </div>`).join('') : `<div class="empty">No calls given yet today — calls appear here with their result</div>`;
}

/* ---------- structure alerts ---------- */
function renderStructure(list){
  if(!$('strBox'))return;
  if(!changed('str', list)) return;
  const L=list||[];
  $('strTag').textContent=L.length+' ALERTS';
  $('strBox').innerHTML = L.length? L.map(x=>`
    <div class="str-row ${x.dir==='up'?'sup':'sdn'}">
      <span class="str-at">${x.at||''}</span>
      <b>${x.symbol}</b><span class="sec">${x.sector||''}</span>
      ${x.news?'<span class="str-news">📰 NEWS</span>':''}
      <span class="str-ev ${x.dir==='up'?'up':'dn'}">${x.big?'⭐ ':''}${x.event}</span>
      <span class="${x.chg>=0?'up':'dn'}">₹${fmt(x.ltp)} ${x.chg>=0?'▲':'▼'}${Math.abs(x.chg)}%</span>
      <span class="str-note">${x.note}</span>
      <span class="str-act">${x.action}</span>
    </div>`).join('') : `<div class="empty">No breakout or breakdown yet — alerts fire when price clears the day high / low with volume</div>`;
}

/* ---------- live online count ---------- */
const _vid = (()=>{ let v=store.get('vid',''); if(!v){ v=Math.random().toString(36).slice(2); store.set('vid',v);} return v; })();
async function pingOnline(){
  try{ const r=await fetch('/api/online?id='+_vid); const j=await r.json();
    if($('onlineCount')) $('onlineCount').textContent = `👥 ${j.online} online`;
  }catch(e){}
}
pingOnline(); setInterval(pingOnline, 45000);

/* ---------- index option setups ---------- */
let idxData=[];
function renderIdxSetups(list){
  if(!changed("idx", arguments[0])) return;
  idxData=list||[];
  if(!$('idxSetupBox'))return;
  const best=idxData.find(x=>x.side&&x.conf>=2);
  $('idxSetTag').textContent = best? `BEST: ${best.index} ${best.side} · ${best.score}/100` : 'NO CLEAR SETUP';
  $('idxSetupBox').innerHTML = idxData.length? idxData.map(x=>{
    const isBest = best && x.index===best.index;
    const cls = x.side==='CE'?'ice':x.side==='PE'?'ipe':'iflat';
    return `<div class="idx-card ${cls} ${isBest?'best':''}">
      <div class="i-top"><b class="i-sym">${x.index}</b>
        ${x.side?`<span class="chip ${x.side==='CE'?'up':'dn'}">${x.side}</span>`:'<span class="chip nt">WAIT</span>'}
        ${isBest?'<span class="must-tag">⭐ BEST SETUP</span>':''}
        <span class="i-score">${x.score}<small>/100</small></span></div>
      <div class="i-spot">₹${fmt(x.spot)} <span class="${x.chg>=0?'up':'dn'}">${x.chg>=0?'▲':'▼'}${Math.abs(x.chg)}%</span>
        <span class="i-conf">conf ${x.conf} · bull ${x.bull} / bear ${x.bear}</span></div>
      ${x.strikes&&x.strikes.length?`<div class="opt-row2">${x.strikes.map(o=>`
        <span class="opt-chip ${o.type==='CE'?'ce':'pe'}">${x.opt} ${o.strike} ${o.type}<i>${o.label}</i></span>`).join('')}</div>`:''}
      ${x.trade?`<div class="prem-box">
        <div class="pb-head"><b>${x.trade.symbol}</b>
          <span class="pb-entry">ENTRY ₹${fmt(x.trade.entry)}</span>
          <span class="pb-rr">R:R 1:${x.trade.rr}</span></div>
        <div class="pb-grid">
          <div class="pb-cell sl"><div class="k">SL</div><div class="v">₹${fmt(x.trade.sl)}</div><div class="p">${x.trade.sl_pct}%</div></div>
          <div class="pb-cell tg"><div class="k">TARGET 1</div><div class="v">₹${fmt(x.trade.t1)}</div><div class="p">+${x.trade.t1_pct}%</div></div>
          <div class="pb-cell tg"><div class="k">TARGET 2</div><div class="v">₹${fmt(x.trade.t2)}</div><div class="p">+${x.trade.t2_pct}%</div></div>
          <div class="pb-cell tg"><div class="k">TARGET 3</div><div class="v">₹${fmt(x.trade.t3)}</div><div class="p">+${x.trade.t3_pct}%</div></div>
        </div>
        <div class="pb-spot">Spot levels — SL ${fmt(x.trade.spot_sl)} · T1 ${fmt(x.trade.spot_t1)} · T2 ${fmt(x.trade.spot_t2)} · T3 ${fmt(x.trade.spot_t3)}</div>
        <div class="pb-note">${x.trade.note}</div>
      </div>`
      : (x.spot_sl?`<div class="i-lv"><span class="s">Spot SL ${fmt(x.spot_sl)}</span>
        <span class="t">T1 ${fmt(x.spot_t1)}</span><span class="t">T2 ${fmt(x.spot_t2)}</span></div>`:'')}
      ${x.chain?`<div class="chain-grid mini">
        <div class="ch-cell"><div class="k">PCR</div><div class="v ${x.chain.pcr>=1?'up':'dn'}">${x.chain.pcr??'—'}</div></div>
        <div class="ch-cell"><div class="k">MAX PAIN</div><div class="v nt">${x.chain.max_pain??'—'}</div></div>
        <div class="ch-cell"><div class="k">SUPPORT</div><div class="v up">${x.chain.support??'—'}</div></div>
        <div class="ch-cell"><div class="k">RESIST</div><div class="v dn">${x.chain.resistance??'—'}</div></div>
        <div class="ch-cell"><div class="k">WRITERS</div><div class="v ${x.chain.bias==='BULLISH'?'up':x.chain.bias==='BEARISH'?'dn':'nt'}">${x.chain.writer}</div></div>
      </div>${x.chain.atm_ce!=null?`<div class="ch-prem">ATM ${x.chain.atm} · CE ₹${x.chain.atm_ce} · PE ₹${x.chain.atm_pe}</div>`:''}`:''}
      <div class="i-why">${x.why}</div>
      <div class="i-verdict ${x.side&&x.conf>=2?'ok':'warn'}">${x.verdict}</div>
      <div class="sig-foot"><button class="btn wa mini" onclick="waIdx('${x.index}')">🟢 WA</button></div>
    </div>`;
  }).join('') : `<div class="empty">Index data loading…</div>`;
}
function idxMsg(x){
  const t=x.trade;
  return `📈 KRT INDEX SETUP — ${x.index}\n\nSpot ₹${x.spot} (${x.chg>=0?'+':''}${x.chg}%)\nSetup: ${x.side||'WAIT'} · Score ${x.score}/100 · Conf ${x.conf}\n`+
    (t?`\n🎯 ${t.symbol}\nEntry: ₹${t.entry}\nSL: ₹${t.sl} (${t.sl_pct}%)\nT1: ₹${t.t1} (+${t.t1_pct}%)\nT2: ₹${t.t2} (+${t.t2_pct}%)\nT3: ₹${t.t3} (+${t.t3_pct}%)\nR:R 1:${t.rr}\n\nSpot SL ${t.spot_sl} · T1 ${t.spot_t1} · T2 ${t.spot_t2}\n${t.note}\n`
      : (x.strikes&&x.strikes.length?`\nStrikes: ${x.strikes.map(o=>`${x.opt} ${o.strike} ${o.type}`).join(', ')}\n`:''))+
    (x.chain?`\nOI: ${x.chain.writer} · PCR ${x.chain.pcr}\nSupport ${x.chain.support} · Resistance ${x.chain.resistance} · Max pain ${x.chain.max_pain}\n`:'')+
    `\nWhy: ${x.why}\n${x.verdict}\n\n⚠ Educational only. Not investment advice.`;
}
function waIdx(name){ const x=idxData.find(y=>y.index===name); if(x) openWA(idxMsg(x)); }
$('idxSend') && ($('idxSend').onclick=()=>{
  if(!idxData.length)return;
  openWA('📈 KRT INDEX OPTIONS VIEW\n\n'+idxData.map(x=>
    `${x.index}: ${x.side||'WAIT'} ${x.score}/100 · spot ${x.spot} (${x.chg>=0?'+':''}${x.chg}%)${x.strikes&&x.strikes.length?` · ${x.opt} ${x.strikes[0].strike} ${x.strikes[0].type}`:''}\n   ${x.verdict}`).join('\n\n')+
    '\n\n⚠ Educational only. Not investment advice.');
});

/* ---------- session + index bias ---------- */
function renderSession(sess, ib){
  if(sess && $('sessPill')){
    const cls = sess.mult>0?'ok':sess.mult<0?'bad':'nt';
    $('sessPill').className='sess-pill sp-'+cls;
    $('sessPill').innerHTML=`⏱ ${sess.phase} <span class="nt2">${sess.note}</span>`;
  }
  if(ib && $('idxBiasPill')){
    const cls = ib.bias==='BULLISH'?'ok':ib.bias==='BEARISH'?'bad':'nt';
    $('idxBiasPill').className='sess-pill sp-'+cls;
    $('idxBiasPill').innerHTML=`📊 INDEX ${ib.bias} <span class="nt2">avg ${ib.avg>=0?'+':''}${ib.avg}%</span>`;
  }
}

/* ---------- call of the day ---------- */
let codData=null;
function renderCOD(c){
  codData=c;
  if(!$('codBox'))return;
  if(!c){ $('codTag').textContent='WAITING';
    $('codBox').innerHTML=`<div class="empty">Waiting for a high-conviction setup — appears when trend, sector and VWAP all align</div>`; return; }
  $('codTag').textContent=`${c.symbol} · ${c.score}/100`;
  $('codBox').innerHTML=`
    <div class="cod-head">
      <b class="cod-sym">${c.symbol}</b><span class="sec">${c.sector||''}</span>
      <span class="chip ${c.side==='BUY'?'up':'dn'}">${c.side}</span>
      <span class="cod-view">${c.view}</span>
      <span class="cod-score">${c.score}<small>/100</small></span>
    </div>
    <div class="cod-grid">
      <div class="cod-cell"><div class="k">${c.side==='BUY'?'BUY ZONE':'SELL ZONE'}</div>
        <div class="v cy">${fmt(c.zone_lo)} – ${fmt(c.zone_hi)}</div></div>
      <div class="cod-cell"><div class="k">LTP</div><div class="v">₹${fmt(c.ltp)} <small class="${c.chg>=0?'up':'dn'}">${c.chg>=0?'▲':'▼'}${Math.abs(c.chg)}%</small></div></div>
      <div class="cod-cell"><div class="k">STOP LOSS</div><div class="v dn">${fmt(c.sl)} <small>${c.sl_pct}%</small></div></div>
      <div class="cod-cell"><div class="k">TARGET 1</div><div class="v up">${fmt(c.t1)} <small>+${c.t1_pct}%</small></div></div>
      <div class="cod-cell"><div class="k">TARGET 2</div><div class="v up">${fmt(c.t2)} <small>+${c.t2_pct}%</small></div></div>
      <div class="cod-cell"><div class="k">TARGET 3</div><div class="v up">${fmt(c.t3)} <small>+${c.t3_pct}%</small></div></div>
    </div>
    ${c.best_option?`<div class="bo-box">
      <div class="bo-head"><span class="bo-tag">BEST OPTION TO TAKE</span>
        <b>${c.best_option.symbol}</b>
        <span class="bo-mn">${c.best_option.moneyness}</span>
        <span class="bo-rr">R:R 1:${c.best_option.rr}</span></div>
      <div class="pb-grid">
        <div class="pb-cell"><div class="k">ENTRY</div><div class="v">₹${c.best_option.entry}</div></div>
        <div class="pb-cell sl"><div class="k">SL</div><div class="v">₹${c.best_option.sl}</div><div class="p">${c.best_option.sl_pct}%</div></div>
        <div class="pb-cell tg"><div class="k">TARGET 1</div><div class="v">₹${c.best_option.t1}</div><div class="p">+${c.best_option.t1_pct}%</div></div>
        <div class="pb-cell tg"><div class="k">TARGET 2</div><div class="v">₹${c.best_option.t2}</div><div class="p">+${c.best_option.t2_pct}%</div></div>
        ${c.best_option.t3?`<div class="pb-cell tg"><div class="k">TARGET 3</div><div class="v">₹${c.best_option.t3}</div><div class="p">+${c.best_option.t3_pct}%</div></div>`:''}
      </div>
      <div class="bo-meta">${c.best_option.why} · OI ${fmt(c.best_option.oi)} · expiry ${c.best_option.expiry}</div>
      <div class="bo-note">${c.best_option.note} This option is logged in the trade log, so target and SL hits update automatically.</div>
    </div>`:''}
    <div class="cod-opt">
      <div class="k">OTHER STRIKES (spot ${fmt(c.ltp)} · ATM ${c.atm})</div>
      <div class="opt-row2">${(c.strikes||[]).map(o=>`
        <span class="opt-chip ${o.type==='CE'?'ce':'pe'}">${c.symbol} ${o.strike} ${o.type}<i>${o.label}</i></span>`).join('')}</div>
    </div>
    ${c.chain?`<div class="cod-chain">
      <div class="k">OPTION CHAIN · ${c.chain.expiry} · updated ${c.chain.updated}</div>
      <div class="chain-grid">
        <div class="ch-cell"><div class="k">PCR</div><div class="v ${c.chain.pcr>=1?'up':'dn'}">${c.chain.pcr??'—'}</div></div>
        <div class="ch-cell"><div class="k">MAX PAIN</div><div class="v nt">${c.chain.max_pain??'—'}</div></div>
        <div class="ch-cell"><div class="k">SUPPORT</div><div class="v up">${c.chain.support??'—'}</div></div>
        <div class="ch-cell"><div class="k">RESISTANCE</div><div class="v dn">${c.chain.resistance??'—'}</div></div>
        <div class="ch-cell"><div class="k">WRITERS</div><div class="v ${c.chain.bias==='BULLISH'?'up':c.chain.bias==='BEARISH'?'dn':'nt'}">${c.chain.writer}</div></div>
        <div class="ch-cell"><div class="k">OI BIAS</div><div class="v ${c.chain.bias==='BULLISH'?'up':c.chain.bias==='BEARISH'?'dn':'nt'}">${c.chain.bias}</div></div>
      </div>
      ${c.chain.atm_ce!=null?`<div class="ch-prem">ATM ${c.chain.atm} · CE ₹${c.chain.atm_ce} · PE ₹${c.chain.atm_pe}</div>`:''}
    </div>`:''}
    <div class="cod-why">Why: ${c.why} · ${c.note}</div>
    <div class="cod-plan">${c.plan}</div>`;
}
function codMsg(c){
  return `🔥 KRT CALL OF THE DAY\n\n${c.symbol} (${c.sector}) — ${c.side}\nScore ${c.score}/100 · ${c.view}\n\n${c.side==='BUY'?'Buy zone':'Sell zone'}: ${c.zone_lo} – ${c.zone_hi}\nLTP: ₹${c.ltp}\n\nSL: ${c.sl} (${c.sl_pct}%)\nT1: ${c.t1} (+${c.t1_pct}%)\nT2: ${c.t2} (+${c.t2_pct}%)\nT3: ${c.t3} (+${c.t3_pct}%)\n\nOPTIONS:\n${(c.strikes||[]).map(o=>`• ${c.symbol} ${o.strike} ${o.type} (${o.label})`).join('\n')}\n\nWhy: ${c.why}\n${c.plan}\n\n⚠ Educational only. Not investment advice.`;
}
$('codSend') && ($('codSend').onclick=()=>{ if(codData) openWA(codMsg(codData)); });

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
$('poSend') && ($('poSend').onclick=()=>{
  const up=preopenData.up||[], dn=preopenData.down||[];
  if(!up.length && !dn.length) return;
  openWA('🌅 KRT PRE-OPEN GAP LIST'+(preopenData.final?' (FINAL)':' (LIVE)')+'\n\n▲ GAP UP\n'+
    up.slice(0,8).map(x=>`${x.symbol} ₹${fmt(x.price)} ▲${x.gap}%`).join('\n')+
    '\n\n▼ GAP DOWN\n'+dn.slice(0,8).map(x=>`${x.symbol} ₹${fmt(x.price)} ▼${Math.abs(x.gap)}%`).join('\n')+
    '\n\n⚠ Educational only. Not investment advice.');
});

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
  if(!changed("sec", arguments[0])) return;
  const strong=sectors.slice(0,6), weak=[...sectors].reverse().slice(0,6);
  $('strongSectors').innerHTML=strong.map(s=>`
    <div class="sec-row">
      <div class="sec-head"><b>${s.sector}</b><span class="up">▲ ${s.chg}%</span></div>
      <div class="sec-stocks">${(s.top||[]).map(t=>`<span class="s-chip up">${t.symbol} ${t.chg>=0?'+':''}${t.chg}%</span>`).join('')}</div>
    </div>`).join('');
  $('weakSectors').innerHTML=weak.map(s=>`
    <div class="sec-row">
      <div class="sec-head"><b>${s.sector}</b><span class="${s.chg>=0?'up':'dn'}">${s.chg>=0?'▲':'▼'} ${Math.abs(s.chg)}%</span></div>
      <div class="sec-stocks">${(s.weak||[]).map(t=>`<span class="s-chip dn">${t.symbol} ${t.chg}%</span>`).join('')}</div>
    </div>`).join('');
}

/* ---------- tables ---------- */
function stockRows(arr, tb){
  if(!changed('tbl'+tb, arr)) return;
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
  const side=a.side||(a.type==='DANGER'?'SELL':a.type==='BUY'?'BUY':'');
  el.innerHTML=`<div class="al-top"><b class="sym">${a.symbol}</b>
      ${side?`<span class="al-side ${side==='BUY'?'up':'dn'}">${side}</span>`:''}
      <span class="t">${new Date().toLocaleTimeString('en-IN',{hour12:false})}</span></div>
    <div class="al-body">${a.reason}</div>
    ${a.detail?`<div class="al-detail">${a.detail}</div>`:''}`;
  $('alertFeed').prepend(el);
  if($('alertFeed').children.length>30)$('alertFeed').lastChild.remove();
  beep(a.sound || (a.type==='DANGER'?'sell':'buy'));
}
function renderAlerts(alerts, chartink){
  (alerts||[]).forEach(a=>{
    const k='a:'+a.symbol+a.reason; if(seen.has(k))return; seen.add(k);
    const r=(window.__last||[]).find(x=>x.symbol===a.symbol)||{};
    pushAlert({...a, side:a.type==='DANGER'?'SELL':'BUY',
      detail:`Price ₹${fmt(r.ltp||0)} · Vol ${volFmt(r.volume||0)} · Sector ${r.sector||'—'}`});
  });
  (chartink||[]).forEach(c=>{
    const k='c:'+JSON.stringify(c).slice(0,60); if(seen.has(k))return; seen.add(k);
    const nm = ckName(c), st = ckStocks(c), tm = ckTime(c);
    const bear=/low|sell|down|crash|breakdown|short/i.test(nm);
    pushAlert({symbol: st||nm, side: bear?'SELL':'BUY', type: bear?'DANGER':'BUY',
      reason:`<b>KRT CALL · ${nm}</b>`,
      detail:`Scanner: ${nm}${tm?' · Time: '+tm:''}`});
  });
}

/* ---------- news ---------- */
const TAGCLS={'BREAKING':'brk','CRASH RISK':'dn','COMPANY RISK':'dn','NEGATIVE':'dn','ORDER WIN':'up','STRONG POSITIVE':'up','POSITIVE':'up','RESULTS':'nt','NEUTRAL':'nt'};
function renderNews(items){
  if(!items||!items.length){ $('newsList').innerHTML=`<div class="empty">No fresh market news in the last 6 hours</div>`; return; }
  $('newsList').innerHTML=items.map(n=>`
    <div class="news-item"><div class="head">
      <span class="chip ${TAGCLS[n.tag]||'nt'}">${n.fast?'⚡ ':''}${n.tag}</span>
      <span>${n.link?`<a class="nlink" href="${n.link}" target="_blank" rel="noopener">${n.title}</a>`:n.title}</span>
      <span class="impact imp${n.impact>=9?'9':n.impact>=7?'7':''}">${n.impact}/10 · ${n.ago||''}</span></div>
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
      ${c.affect?`<div class="aff aff-${c.affect.level}">IMPACT ${c.affect.level} · ${c.affect.note}${c.affect.focus!=='NONE'?' · FOCUS '+c.affect.focus:''}</div>`:''}
      <div class="sig-foot"><span class="dn">${c.action}</span></div>
    </div>`).join('') + dg.map(n=>`
    <div class="sig-card bear slim">
      <div class="sig-top"><b class="sym">${n.symbol}</b><span class="chip dn">${n.tag}</span>
        <span class="impact">${n.impact}/10 · ${n.ago||''}</span>${n.chg!=null?`<span class="${n.chg>=0?'up':'dn'}">${n.chg>=0?'▲':'▼'}${Math.abs(n.chg)}%</span>`:''}</div>
      <div class="nh">${n.headline}</div>
      <div class="sig-foot"><span class="dn">${n.verdict}</span></div>
    </div>`).join('')) || `<div class="empty">No fresh negative news (last 6 hrs) 👍</div>`;

  // crash banner
  if(cr.length){
    $('crashBanner').style.display='block';
    $('crashBanner').innerHTML=`🚨 <b>CRASH ALERT</b> — ${cr[0].headline} <span class="cb-act">${cr[0].action}</span>`;
    if(!seen.has('crash:'+cr[0].headline)){ seen.add('crash:'+cr[0].headline); beep('crash'); }
  } else { $('crashBanner').style.display='none'; }
}

/* ---------- chartink panel ---------- */
if($('ckUrl')) $('ckUrl').value=store.get('ckUrl','');
if($('ckStatus') && store.get('ckUrl','')) $('ckStatus').textContent='✅ Saved';
$('ckSave') && ($('ckSave').onclick=()=>{ store.set('ckUrl',$('ckUrl').value.trim());
  $('ckStatus').textContent='✅ Saved'; $('ckStatus').className='status ok'; });

/* ═══════════ MAIN LOOP ═══════════ */
async function pull(u){ try{ const r=await fetch(u); return r.ok? await r.json():null; }catch(e){ return null; } }
function safe(fn, name, ...args){
  try{ fn(...args); }
  catch(e){ console.error('[KRT] '+name+' failed:', e); (window.__krtFails=window.__krtFails||[]).push(name+': '+e.message); }
}
function apiDown(msg){
  const b=$('crashBanner'); if(!b) return;
  b.style.display='block';
  b.innerHTML='🔌 <b>BACKEND NOT RESPONDING</b> — '+msg+'. Check the Flask server / Render logs.';
}
async function refresh(){
  const d=await pull(CONFIG.DASHBOARD);
  if(!d){ apiDown('/api/dashboard returned nothing'); return; }
  if(d.error){ apiDown('/api/dashboard error: '+d.error); return; }
  window.__krtFails=[];
  if(d && !d.error){
    // indices
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

    window.__last=uniq;
    safe(renderStatus,'renderStatus',d.status);
    safe(renderConfluence,'renderConfluence',d.confluence, d.confl_diag);
    safe(renderAnnouncements,'renderAnnouncements',d.announcements);
    safe(renderResultsDiary,'renderResultsDiary',d.results_diary);
    safe(renderBreadth,'renderBreadth',d.breadth);
    safe(orRows,'orRows',d.or5||d.or15,'or5List','or5Tag','5-min High');
    safe(renderMood,'renderMood',d.mood);
    safe(renderTracker,'renderTracker',d.tracker, d.ind_ready);
    safe(renderOptions,'renderOptions',uniq, rank, sectors.length);
    safe(renderSession,'renderSession',d.session, d.index_bias);
    safe(renderIdxSetups,'renderIdxSetups',d.index_setups);
    safe(renderStructure,'renderStructure',d.structure);
    safe(renderTradeLog,'renderTradeLog',d.tracker);
    (d.structure||[]).forEach(x=>{
      const k='st:'+x.symbol+x.event; if(seen.has(k))return; seen.add(k);
      pushAlert({symbol:x.symbol, side:x.dir==='up'?'BUY':'SELL',
        type:x.dir==='up'?'BUY':'DANGER',
        reason:`<b>${x.at||''} · ${x.event}</b> — ${x.note}`,
        detail:`₹${fmt(x.ltp)} (${x.chg>=0?'+':''}${x.chg}%) · ${x.sector} · ${x.action}`});
    });
    safe(renderCOD,'renderCOD',d.call_day);
    safe(renderZones,'renderZones',d.zones);
    safe(renderPreopen,'renderPreopen',d.preopen);
    safe(stockRows,'stockRows',d.gainers||[],'gainT');
    safe(stockRows,'stockRows',d.losers||[],'loseT');
    safe(renderChartink,'renderChartink',d.chartink);
    safe(buildJackpots,'buildJackpots',uniq,brk,rank);
    safe(buildDangers,'buildDangers',uniq,brk,rank,sectors.length);
    safe(renderSectors,'renderSectors',sectors);
    safe(renderAlerts,'renderAlerts',d.alerts,d.chartink);

    const ups=uniq.filter(r=>r.chg>0).length;
    renderScore(uniq.length? Math.round(35+(ups/uniq.length)*55) : 50);
    $('uniCount').textContent=d.universe||uniq.length;
    const live = d.mode==='live';
    $('gTag').textContent = live?'LIVE · ANGEL ONE':'DEMO MODE';
    $('lTag').textContent = live?'LIVE · ANGEL ONE':'DEMO MODE';
  }
}
async function refreshNews(){
  const n=await pull(CONFIG.NEWS);
  if(n && !n.error){ renderNews(n.items); renderNewsSignals(n.signals); }
}
refresh(); refreshNews();
setInterval(refresh, CONFIG.REFRESH_MS);
setInterval(refreshNews, 90000);          // news every 90s — much lighter

