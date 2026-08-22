"""
KRT — Indicators + Signal Tracker (no historical API needed)
------------------------------------------------------------
• Live polls-la irundhu 1-minute candles self-build pannum
• RSI(14), EMA(9/21), ATR(14), VWAP, ADX(14) — real calculation
• ATR-based SL / T1 / T2 / T3 (fixed % illa)
• Signal tracker: ovvoru jackpot/danger signal-um log agum,
  T1 / SL hit track pannum -> WIN RATE
Day 1: indicators ~30-45 min market open aana apram ready agum.
"""
import time, threading, json, os
from datetime import datetime, timedelta

_lock = threading.Lock()
CANDLES = {}          # sym -> [{t,o,h,l,c,v}] 1-min
PREV_DAY = {}         # sym -> {"high","low","close","date"}
_today = ""

MAX_CANDLES = 400     # ~6.5 hours of 1-min


def _ist():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


# ═════════ candle builder ═════════
MAX_TICK_JUMP = 0.10      # 1 min-la 10%-ku mela jump = bad tick, reject


def feed(rows, live=True):
    """Ovvoru dashboard poll-layum call agum. rows = live stock list.

    live=False (demo/fallback data) na candle-la POdaadhu — illena fake price
    real price-oda mix aagi ATR vedichidum.
    """
    global _today
    if not live:
        return
    now = _ist()
    day = now.strftime("%Y-%m-%d")
    minute = now.replace(second=0, microsecond=0).timestamp()

    with _lock:
        if _today and _today != day:            # naal maarina -> roll over
            for sym, cs in CANDLES.items():
                if cs:
                    PREV_DAY[sym] = {"high": max(c["h"] for c in cs),
                                     "low": min(c["l"] for c in cs),
                                     "close": cs[-1]["c"], "date": _today}
            CANDLES.clear()
        _today = day

        for r in rows:
            sym, px = r.get("symbol"), r.get("ltp")
            if not sym or not px:
                continue
            vol = r.get("volume") or 0
            cs = CANDLES.setdefault(sym, [])
            # ── bad-tick guard: last close-la irundhu 10%-ku mela jump = reject ──
            if cs:
                last_c = cs[-1]["c"]
                if last_c and abs(px - last_c) / last_c > MAX_TICK_JUMP:
                    continue
            if cs and cs[-1]["t"] == minute:
                c = cs[-1]
                c["h"] = max(c["h"], px); c["l"] = min(c["l"], px)
                c["c"] = px; c["v"] = vol
            else:
                cs.append({"t": minute, "o": px, "h": px, "l": px, "c": px, "v": vol})
                if len(cs) > MAX_CANDLES:
                    del cs[0:len(cs) - MAX_CANDLES]


# ═════════ indicator math ═════════
def _ema(vals, n):
    if len(vals) < n:
        return None
    k = 2 / (n + 1)
    e = sum(vals[:n]) / n
    for v in vals[n:]:
        e = v * k + e * (1 - k)
    return e


def _rsi(closes, n=14):
    if len(closes) < n + 1:
        return None
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0); losses += max(-d, 0)
    ag, al = gains / n, losses / n
    for i in range(n + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
    if al == 0:
        return 100.0
    rs = ag / al
    return 100 - (100 / (1 + rs))


def _atr(cs, n=14):
    if len(cs) < n + 1:
        return None
    trs = []
    for i in range(1, len(cs)):
        h, l, pc = cs[i]["h"], cs[i]["l"], cs[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < n:
        return None
    a = sum(trs[:n]) / n
    for tr in trs[n:]:
        a = (a * (n - 1) + tr) / n
    return a


def _adx(cs, n=14):
    if len(cs) < n * 2:
        return None
    plus, minus, trs = [], [], []
    for i in range(1, len(cs)):
        up = cs[i]["h"] - cs[i - 1]["h"]
        dn = cs[i - 1]["l"] - cs[i]["l"]
        plus.append(up if (up > dn and up > 0) else 0.0)
        minus.append(dn if (dn > up and dn > 0) else 0.0)
        h, l, pc = cs[i]["h"], cs[i]["l"], cs[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    def sm(x):
        s = sum(x[:n])
        out = [s]
        for v in x[n:]:
            s = s - s / n + v
            out.append(s)
        return out
    st, sp, sm_ = sm(trs), sm(plus), sm(minus)
    dxs = []
    for i in range(len(st)):
        if st[i] == 0:
            continue
        pdi = 100 * sp[i] / st[i]; mdi = 100 * sm_[i] / st[i]
        if pdi + mdi:
            dxs.append(100 * abs(pdi - mdi) / (pdi + mdi))
    if len(dxs) < n:
        return None
    return sum(dxs[-n:]) / n


def _vwap(cs):
    tv = pv = 0.0
    prev_v = 0
    for c in cs:
        v = max((c["v"] or 0) - prev_v, 0)
        prev_v = c["v"] or prev_v
        tp = (c["h"] + c["l"] + c["c"]) / 3
        pv += tp * v; tv += v
    return (pv / tv) if tv else None


def _resample(cs, minutes):
    """1-min candles -> N-min candles."""
    out, bucket = [], {}
    step = minutes * 60
    for c in cs:
        b = int(c["t"] // step) * step
        if bucket.get("t") != b:
            if bucket:
                out.append(bucket)
            bucket = {"t": b, "o": c["o"], "h": c["h"], "l": c["l"], "c": c["c"], "v": c["v"]}
        else:
            bucket["h"] = max(bucket["h"], c["h"])
            bucket["l"] = min(bucket["l"], c["l"])
            bucket["c"] = c["c"]; bucket["v"] = c["v"]
    if bucket:
        out.append(bucket)
    return out


def htf_trend(sym):
    """Higher timeframe alignment: 1m / 5m / 15m trend agree?"""
    with _lock:
        cs = list(CANDLES.get(sym, []))
    if len(cs) < 20:
        return {"ready": False, "align": 0, "tf": {}}
    res = {}
    for name, mins, need in (("m1", 1, 20), ("m5", 5, 6), ("m15", 15, 4)):
        bars = cs if mins == 1 else _resample(cs, mins)
        if len(bars) < need:
            res[name] = None
            continue
        cl = [b["c"] for b in bars]
        fast = _ema(cl, min(9, len(cl) - 1))
        slow = _ema(cl, min(21, len(cl) - 1)) or (sum(cl) / len(cl))
        if fast is None or slow is None:
            res[name] = None
        else:
            res[name] = 1 if fast > slow else -1
    vals = [v for v in res.values() if v is not None]
    align = 0
    if vals:
        if all(v == 1 for v in vals) and len(vals) >= 2:
            align = 1
        elif all(v == -1 for v in vals) and len(vals) >= 2:
            align = -1
    return {"ready": len(vals) >= 2, "align": align, "tf": res}


def opening_range(sym):
    """First 5-min & 15-min high/low from self-built candles (09:15 onward)."""
    with _lock:
        cs = list(CANDLES.get(sym, []))
    if not cs:
        return {}
    start = None
    for c in cs:
        t = datetime.utcfromtimestamp(c["t"] + 19800)
        if t.hour == 9 and t.minute >= 15:
            start = c["t"]; break
    if start is None:
        return {}
    five = [c for c in cs if start <= c["t"] < start + 300]
    fift = [c for c in cs if start <= c["t"] < start + 900]
    out = {}
    if five:
        out["or5h"] = round(max(c["h"] for c in five), 2)
        out["or5l"] = round(min(c["l"] for c in five), 2)
    if fift and len(fift) >= 10:
        out["or15h"] = round(max(c["h"] for c in fift), 2)
        out["or15l"] = round(min(c["l"] for c in fift), 2)
    return out


def indicators(sym):
    """Return dict of live indicators for a symbol (None-safe)."""
    with _lock:
        cs = list(CANDLES.get(sym, []))
    if len(cs) < 5:
        return {"ready": False, "bars": len(cs)}
    closes = [c["c"] for c in cs]
    e9, e21 = _ema(closes, 9), _ema(closes, 21)
    # RSI 0.0 / RSI 100.0 / ADX 100.0 were appearing on signal cards. Those are
    # not real readings — they come from a handful of candles that all move the
    # same way right after a restart. Require a real sample before calling the
    # indicators usable, so no signal is built on them.
    rsi_v = _rsi(closes)
    degenerate = (rsi_v is not None and (rsi_v <= 1 or rsi_v >= 99))
    out = {
        "ready": len(cs) >= 20 and not degenerate, "bars": len(cs),
        "rsi": round(_rsi(closes), 1) if _rsi(closes) is not None else None,
        "ema9": round(e9, 2) if e9 else None,
        "ema21": round(e21, 2) if e21 else None,
        "atr": round(_atr(cs), 2) if _atr(cs) else None,
        "adx": round(_adx(cs), 1) if _adx(cs) else None,
        "vwap": round(_vwap(cs), 2) if _vwap(cs) else None,
        "day_high": round(max(c["h"] for c in cs), 2),
        "day_low": round(min(c["l"] for c in cs), 2),
    }
    pd = PREV_DAY.get(sym)
    if pd:
        out["pdh"] = pd["high"]; out["pdl"] = pd["low"]; out["pdc"] = pd["close"]
    out.update(opening_range(sym))
    out["htf"] = htf_trend(sym)
    return out


def enrich(rows):
    """Attach indicators + ATR-based levels to each stock row."""
    for r in rows:
        ind = indicators(r["symbol"])
        r["ind"] = ind
        atr = ind.get("atr")
        px = r.get("ltp") or 0
        if px:
            day_rng = (ind.get("day_high") or px) - (ind.get("day_low") or px)
            floor = max(px * 0.005, min(day_rng, px * 0.05) * 0.30)
            atr = max(atr or 0, floor)
            # ── sanity cap: intraday ATR normal-a price-oda 0.3-1.5%.
            #    2.5%-ku mela pona data corrupt — clamp pannitta targets sane-a irukkum.
            atr = min(atr, px * 0.025)
            r["sl_long"] = round(px - 1.2 * atr, 2)
            r["t1_long"] = round(px + 1.5 * atr, 2)
            r["t2_long"] = round(px + 2.5 * atr, 2)
            r["t3_long"] = round(px + 4.0 * atr, 2)
            r["sl_short"] = round(px + 1.2 * atr, 2)
            r["t1_short"] = round(px - 1.5 * atr, 2)
            r["t2_short"] = round(px - 2.5 * atr, 2)
            r["t3_short"] = round(px - 4.0 * atr, 2)
            r["atr_pct"] = round(atr / px * 100, 2)
    return rows


def confirmations(r):
    """Real technical confirmations — jackpot scoring ku."""
    ind = r.get("ind") or {}
    tags, score = [], 0
    px = r.get("ltp") or 0
    if ind.get("rsi") is not None:
        if 55 <= ind["rsi"] <= 75:
            tags.append(f"RSI {ind['rsi']}"); score += 8
        elif ind["rsi"] > 75:
            tags.append(f"RSI {ind['rsi']} overbought")
    if ind.get("ema9") and ind.get("ema21") and ind["ema9"] > ind["ema21"]:
        tags.append("EMA 9>21"); score += 8
    if ind.get("vwap") and px > ind["vwap"]:
        tags.append("Above VWAP"); score += 8
    if ind.get("adx") and ind["adx"] >= 25:
        tags.append(f"ADX {ind['adx']}"); score += 8
    if ind.get("day_high") and px >= ind["day_high"] * 0.999:
        tags.append("At day high"); score += 6
    if ind.get("pdh") and px > ind["pdh"]:
        tags.append("PDH break"); score += 10
    return tags, score


def confirmations_short(r):
    ind = r.get("ind") or {}
    tags, score = [], 0
    px = r.get("ltp") or 0
    if ind.get("rsi") is not None and ind["rsi"] <= 45:
        tags.append(f"RSI {ind['rsi']}"); score += 8
    if ind.get("ema9") and ind.get("ema21") and ind["ema9"] < ind["ema21"]:
        tags.append("EMA 9<21"); score += 8
    if ind.get("vwap") and px < ind["vwap"]:
        tags.append("Below VWAP"); score += 8
    if ind.get("adx") and ind["adx"] >= 25:
        tags.append(f"ADX {ind['adx']}"); score += 8
    if ind.get("day_low") and px <= ind["day_low"] * 1.001:
        tags.append("At day low"); score += 6
    if ind.get("pdl") and px < ind["pdl"]:
        tags.append("PDL break"); score += 10
    return tags, score


# ═════════ SIGNAL TRACKER (T1/T2/T3 + times + accuracy) ═════════
import store as _ST
# /tmp is wiped on every Render deploy, which is why a full day of calls kept
# disappearing. store.py picks a persistent disk when one is attached.
TRACK_FILE = _ST.path("krt_signals.json")
# 1500 covered barely a fortnight. A year at ~80 calls a day needs far more,
# and the 30-day accuracy panel is meaningless if older rows are dropped.
KEEP_SIGNALS = 40000
_signals = []
COOLDOWN_MIN = 15


# Gunicorn runs more than one worker, and each one holds its own _signals
# list. The old _save() wrote that private list straight over the shared
# file, so whichever worker saved last wiped the calls the other worker had
# logged — the trade log kept dropping from 8 calls back to 1. Every read
# and write now merges against what is already on disk.
_ADVANCE = {"LIVE": 0, "T1 HIT": 1, "T2 HIT": 2, "T3 HIT": 3,
            "SL HIT": 3, "CLOSED": 3}


def _disk_read():
    try:
        if os.path.exists(TRACK_FILE):
            d = json.load(open(TRACK_FILE))
            return d if isinstance(d, list) else []
    except Exception:
        pass
    return []


def _merge(a, b):
    """Combine two signal lists. On a clash keep the further-along record."""
    out = {}
    for sig in list(a) + list(b):
        if not isinstance(sig, dict):
            continue
        k = sig.get("id") or f"{sig.get('sym')}-{sig.get('side')}-{sig.get('ts')}"
        cur = out.get(k)
        if cur is None:
            out[k] = sig
            continue
        if _ADVANCE.get(sig.get("status"), 0) >= _ADVANCE.get(cur.get("status"), 0):
            out[k] = sig
    rows = list(out.values())
    rows.sort(key=lambda x: (x.get("date", ""), x.get("ts", "")))
    return rows


def _load():
    global _signals
    _signals = _disk_read()


def _sync():
    """Pull in anything another worker logged since we last looked."""
    global _signals
    _signals = _merge(_disk_read(), _signals)
    return _signals


def _save():
    global _signals
    try:
        _signals = _merge(_disk_read(), _signals)[-KEEP_SIGNALS:]
        tmp = TRACK_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(_signals, f)
        os.replace(tmp, TRACK_FILE)      # atomic, never a half-written file
    except Exception:
        pass


_load()


def _mins_since(hhmm, date):
    try:
        d = datetime.strptime(date + " " + hhmm, "%Y-%m-%d %H:%M")
        return (_ist() - d).total_seconds() / 60
    except Exception:
        return 9999


def log_signal(sym, side, entry, sl, t1, t2, t3=None, score=None, setup="", source="JACKPOT"):
    """Cooldown: same stock+side 15 min-ku ulla thirumba log aagadhu."""
    # There was no time gate at all, so calls were being logged at 15:50 and
    # even 16:25 — after the close, on frozen prices. Those are the rows that
    # later showed impossible numbers. Only log inside 9:15am-3:15pm.
    n = _ist()
    mins = n.hour * 60 + n.minute
    if n.weekday() >= 5 or not (555 <= mins <= 915):
        return None
    _sync()
    today = _ist().strftime("%Y-%m-%d")
    for s in reversed(_signals):
        if s["sym"] == sym and s["side"] == side and s["date"] == today:
            if s["status"] in ("LIVE", "T1 HIT", "T2 HIT"):
                return None
            if _mins_since(s["ts"], s["date"]) < COOLDOWN_MIN:
                return None
            break
    pc = lambda v: round(abs(v - entry) / entry * 100, 2) if (v and entry) else None
    sig = {"id": f"{sym}-{side}-{_ist().strftime('%H%M%S')}", "sym": sym, "side": side,
           "entry": entry, "sl": sl, "t1": t1, "t2": t2, "t3": t3,
           "sl_pct": pc(sl), "t1_pct": pc(t1), "t2_pct": pc(t2), "t3_pct": pc(t3),
           "score": score, "setup": setup, "source": source,
           "ts": _ist().strftime("%H:%M"), "date": today,
           "status": "LIVE", "t1_at": None, "t2_at": None, "t3_at": None,
           "sl_at": None, "done_at": None, "best": entry, "pnl_pct": None}
    _signals.append(sig); _save()
    return sig


def open_signals():
    """Calls that are still live, so their price is worth refreshing."""
    _sync()
    return [s for s in _signals
            if s.get("status") in ("LIVE", "T1 HIT", "T2 HIT")]


def update_tracker(price_map):
    # Pre-open prints and post-close snapshots are not tradable prices. Judging
    # a call against them is what produced "SL HIT -83%" on a 0.6% stop at
    # 08:40. Only mark hits while the market is actually open.
    n0 = _ist()
    m0 = n0.hour * 60 + n0.minute
    if n0.weekday() >= 5 or not (555 <= m0 <= 930):
        return []
    _sync()
    changed = []
    now = _ist().strftime("%H:%M")
    for s in _signals:
        if s["status"] in ("TARGET COMPLETED", "SL HIT", "EXPIRED"):
            continue
        px = price_map.get(s["sym"])
        if not px or px <= 0:
            continue
        # A cash stock does not move 80% intraday. A price that far from entry
        # is bad data (stale feed, wrong key, pre-open print) — skip it rather
        # than write a nonsense result that poisons the accuracy figures.
        is_opt = len(str(s["sym"]).split()) == 3
        limit = 3.0 if is_opt else 0.25          # options can genuinely swing
        if abs(px - s["entry"]) / s["entry"] > limit:
            continue
        buy = s["side"] == "BUY"
        # best price after signal
        s["best"] = max(s["best"], px) if buy else min(s["best"], px)
        s["pnl_pct"] = round(((px - s["entry"]) if buy else (s["entry"] - px)) / s["entry"] * 100, 2)
        hit = lambda lvl: (px >= lvl) if buy else (px <= lvl)
        stop = (px <= s["sl"]) if buy else (px >= s["sl"])
        if stop:
            s.update(status="SL HIT", sl_at=now, done_at=now); changed.append(s); continue
        if s["t1"] and not s["t1_at"] and hit(s["t1"]):
            s.update(t1_at=now, status="T1 HIT"); changed.append(s)
        if s["t2"] and not s["t2_at"] and hit(s["t2"]):
            s.update(t2_at=now, status="T2 HIT"); changed.append(s)
        if s["t3"] and not s["t3_at"] and hit(s["t3"]):
            s.update(t3_at=now, status="TARGET COMPLETED", done_at=now); changed.append(s)
        # market close -> expire
        n = _ist()
        if n.hour >= 15 and n.minute >= 30 and s["status"] in ("LIVE", "T1 HIT", "T2 HIT"):
            s.update(status="EXPIRED" if s["status"] == "LIVE" else s["status"], done_at=now)
    if changed:
        _save()
    return changed


def _acc(rows):
    closed = [s for s in rows if s["status"] in ("TARGET COMPLETED", "SL HIT", "T1 HIT", "T2 HIT", "EXPIRED")
              and s["status"] != "LIVE"]
    settled = [s for s in rows if s["status"] in ("TARGET COMPLETED", "SL HIT", "EXPIRED", "T1 HIT", "T2 HIT")]
    wins = [s for s in settled if s["t1_at"]]
    sl = [s for s in settled if s["status"] == "SL HIT"]
    run = [s for s in rows if s["status"] in ("LIVE", "T1 HIT", "T2 HIT")]
    n = len(settled)
    t1 = len([s for s in settled if s["t1_at"]])
    t2 = len([s for s in settled if s["t2_at"]])
    t3 = len([s for s in settled if s["t3_at"]])
    buys = [s for s in settled if s["side"] == "BUY"]
    sells = [s for s in settled if s["side"] == "SELL"]
    pct = lambda a, b: round(a / b * 100, 1) if b else None
    return {"total": len(rows), "wins": len(wins), "sl": len(sl), "running": len(run),
            "accuracy": pct(len(wins), n),
            "t1_rate": pct(t1, n), "t2_rate": pct(t2, n), "t3_rate": pct(t3, n),
            "buy_acc": pct(len([s for s in buys if s["t1_at"]]), len(buys)),
            "sell_acc": pct(len([s for s in sells if s["t1_at"]]), len(sells)),
            "avg_pnl": round(sum(s["pnl_pct"] or 0 for s in settled) / n, 2) if n else 0}


def stats():
    _sync()
    today = _ist().strftime("%Y-%m-%d")
    d7 = (_ist() - timedelta(days=7)).strftime("%Y-%m-%d")
    d30 = (_ist() - timedelta(days=30)).strftime("%Y-%m-%d")
    t_rows = [s for s in _signals if s["date"] == today]
    completed = [s for s in t_rows if s["status"] in ("TARGET COMPLETED", "SL HIT", "T1 HIT", "T2 HIT", "EXPIRED")]
    return {
        "today_date": today,
        "today": _acc(t_rows),
        "d7": _acc([s for s in _signals if s["date"] >= d7]),
        "d30": _acc([s for s in _signals if s["date"] >= d30]),
        "live": [s for s in t_rows if s["status"] in ("LIVE", "T1 HIT", "T2 HIT")][::-1][:15],
        "completed": completed[::-1][:20],
        "history": _signals[-60:][::-1],
        "top": sorted([s for s in t_rows if (s.get("score") or 0) >= 75],
                      key=lambda x: -(x.get("score") or 0))[:25],
    }
