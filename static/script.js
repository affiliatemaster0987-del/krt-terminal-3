/* ═══════════ KRT AI 2.2 — LIVE (Angel One via /api/dashboard) ═══════════ */
const CONFIG = {
  DASHBOARD: "/api/dashboard",
  SCANNER: "/api/scanner",
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
      sym:r.symbo
