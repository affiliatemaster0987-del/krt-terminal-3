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
              if all(v == 1 for v in vals):
            align = 1
        elif all(v == -1 for v in vals):
            align = -1
    return {"ready": len(vals) >= 2, "align": align, "tf": res}


def calc(sym):
    """Latest indicators for symbol."""
    with _lock:
        cs = list(CANDLES.get(sym, []))
    if not cs:
        return {"ready": False}
    closes = [c["c"] for c in cs]
    e9 = _ema(closes, 9); e21 = _ema(closes, 21)
    rsi = _rsi(closes); atr = _atr(cs); adx = _adx(cs); vw = _vwap(cs)
    day_h = max(c["h"] for c in cs); day_l = min(c["l"] for c in cs)
    # first 5 / 15 minute high-low
    first5 = [c for c in cs if c["t"] < cs[0]["t"] + 5 * 60]
    first15 = [c for c in cs if c["t"] < cs[0]["t"] + 15 * 60]
    prev = PREV_DAY.get(sym, {})
    return {
        "ready": len(cs) >= 15,
        "bars": len(cs),
        "rsi": round(rsi, 1) if rsi is not None else None,
        "ema9": round(e9, 2) if e9 else None,
        "ema21": round(e21, 2) if e21 else None,
        "atr": round(atr, 2) if atr else None,
        "adx": round(adx, 1) if adx else None,
        "vwap": round(vw, 2) if vw else None,
        "day_high": round(day_h, 2), "day_low": round(day_l, 2),
        "or5h": round(max(c["h"] for c in first5), 2) if first5 else None,
        "or5l": round(min(c["l"] for c in first5), 2) if first5 else None,
        "or15h": round(max(c["h"] for c in first15), 2) if first15 else None,
        "or15l": round(min(c["l"] for c in first15), 2) if first15 else None,
        "pdh": prev.get("high"), "pdl": prev.get("low"),
        "htf": htf_trend(sym),
    }


def enrich(rows):
    """Attach ind + ATR-based levels to each row in-place."""
    for r in rows:
        x = calc(r["symbol"])
        r["ind"] = x
        px = r.get("ltp") or 0
        atr = x.get("atr")
        # ATR isn't usable until enough real candles exist.  The old
        # high-low fallback made a 1.3% day range into a 6% T3, which looked
        # like a target but was just an arbitrary extrapolation.  Use a
        # conservative 0.6% proxy until the real 14-period ATR is ready.
        a = atr if atr and atr > 0 else (px * 0.006 if px else 0)
        if px and a:
            # 1.2 ATR risk, 1.5 / 2.5 / 4 ATR reward
            r["sl_long"] = round(px - 1.2 * a, 2)
            r["t1_long"] = round(px + 1.5 * a, 2)
            r["t2_long"] = round(px + 2.5 * a, 2)
            r["t3_long"] = round(px + 4.0 * a, 2)
            r["sl_short"] = round(px + 1.2 * a, 2)
            r["t1_short"] = round(px - 1.5 * a, 2)
            r["t2_short"] = round(px - 2.5 * a, 2)


def confirmations(r):
    """BUY confirmations list + score bonus."""
    x = r.get("ind") or {}
    tags, bonus = [], 0
    px = r.get("ltp") or 0
    if x.get("vwap") and px > x["vwap"]:
        tags.append("VWAP ✓"); bonus += 6
    if x.get("ema9") and x.get("ema21") and x["ema9"] > x["ema21"]:
        tags.append("EMA 9>21 ✓"); bonus += 5
    if x.get("rsi") is not None and 55 <= x["rsi"] <= 75:
        tags.append(f"RSI {x['rsi']} ✓"); bonus += 5
    if x.get("adx") is not None and x["adx"] >= 25:
        tags.append(f"ADX {x['adx']} ✓"); bonus += 5
    if x.get("day_high") and px >= x["day_high"] * 0.998:
        tags.append("Near day high ✓"); bonus += 4
    return tags, bonus


def confirmations_short(r):
    """SELL confirmations."""
    x = r.get("ind") or {}
    tags, bonus = [], 0
    px = r.get("ltp") or 0
    if x.get("vwap") and px < x["vwap"]:
        tags.append("Below VWAP ✓"); bonus += 6
    if x.get("ema9") and x.get("ema21") and x["ema9"] < x["ema21"]:
        tags.append("EMA 9<21 ✓"); bonus += 5
    if x.get("rsi") is not None and 25 <= x["rsi"] <= 45:
        tags.append(f"RSI {x['rsi']} ✓"); bonus += 5
    if x.get("adx") is not None and x["adx"] >= 25:
        tags.append(f"ADX {x['adx']} ✓"); bonus += 5
    if x.get("day_low") and px <= x["day_low"] * 1.002:
        tags.append("Near day low ✓"); bonus += 4
    return tags, bonus


# ═════════ SIGNAL TRACKER ═════════
SIGNAL_FILE = os.path.join(os.path.dirname(__file__), "krt_signals.json")
_signals = []
_last_save = 0


def _load_signals():
    global _signals
    try:
        with open(SIGNAL_FILE) as f:
            _signals = json.load(f)
    except Exception:
        _signals = []


_load_signals()


def _save():
    global _last_save
    try:
        with open(SIGNAL_FILE, "w") as f:
            json.dump(_signals[-500:], f)
        _last_save = time.time()
    except Exception:
        pass


def log_signal(sym, side, entry, sl, t1, t2=None, t3=None,
               score=0, reason="", kind="JACKPOT"):
    """Log once per symbol+side per day. Returns True if new."""
    day = _ist().strftime("%Y-%m-%d")
    key = f"{day}|{sym}|{side}|{kind}"
    with _lock:
        if any(s.get("key") == key for s in _signals):
            return False
        _signals.append({
            "key": key, "day": day, "time": _ist().strftime("%H:%M:%S"),
            "sym": sym, "side": side, "entry": round(entry, 2),
            "sl": round(sl, 2) if sl else None,
            "t1": round(t1, 2) if t1 else None,
            "t2": round(t2, 2) if t2 else None,
            "t3": round(t3, 2) if t3 else None,
            "score": score, "reason": reason, "kind": kind,
            "status": "RUNNING", "exit": None, "exit_time": None,
            "max_price": round(entry, 2), "min_price": round(entry, 2),
            "max_pct": 0, "pnl_pct": 0,
        })
        _save()
        return True


def update_tracker(price_map):
    """Current prices -> running signals update."""
    changed = False
    with _lock:
        for s in _signals:
            if s.get("status") != "RUNNING":
                continue
            px = price_map.get(s["sym"])
            if px is None:
                continue
            try:
                px = float(px)
            except Exception:
                continue
            entry = s.get("entry") or px
            side = s.get("side", "BUY")
            s["max_price"] = round(max(s.get("max_price") or entry, px), 2)
            s["min_price"] = round(min(s.get("min_price") or entry, px), 2)
            pnl = ((px - entry) / entry * 100) if side == "BUY" else ((entry - px) / entry * 100)
            s["pnl_pct"] = round(pnl, 2)
            best = ((s["max_price"] - entry) / entry * 100) if side == "BUY" else ((entry - s["min_price"]) / entry * 100)
            s["max_pct"] = round(max(s.get("max_pct") or 0, best), 2)

            hit = None
            if side == "BUY":
                if s.get("sl") and px <= s["sl"]:
                    hit = "SL"
                elif s.get("t3") and px >= s["t3"]:
                    hit = "T3"
                elif s.get("t2") and px >= s["t2"]:
                    hit = "T2"
                elif s.get("t1") and px >= s["t1"]:
                    hit = "T1"
            else:
                if s.get("sl") and px >= s["sl"]:
                    hit = "SL"
                elif s.get("t3") and px <= s["t3"]:
                    hit = "T3"
                elif s.get("t2") and px <= s["t2"]:
                    hit = "T2"
                elif s.get("t1") and px <= s["t1"]:
                    hit = "T1"
            if hit:
                s["status"] = hit
                s["exit"] = round(px, 2)
                s["exit_time"] = _ist().strftime("%H:%M:%S")
                changed = True
        if changed or time.time() - _last_save > 30:
            _save()


def open_signals():
    """Snapshot of running signals — option premium refresher uses this."""
    with _lock:
        return [dict(s) for s in _signals if s.get("status") == "RUNNING"]


def stats():
    """Today + all-time accuracy."""
    day = _ist().strftime("%Y-%m-%d")
    with _lock:
        all_s = list(_signals)
    today = [s for s in all_s if s.get("day") == day]
    done = [s for s in today if s.get("status") != "RUNNING"]
    wins = [s for s in done if s.get("status") in ("T1", "T2", "T3")]
    losses = [s for s in done if s.get("status") == "SL"]
    running = [s for s in today if s.get("status") == "RUNNING"]
    rate = round(len(wins) / len(done) * 100, 1) if done else None

    # all-time
    all_done = [s for s in all_s if s.get("status") != "RUNNING"]
    all_wins = [s for s in all_done if s.get("status") in ("T1", "T2", "T3")]
    all_rate = round(len(all_wins) / len(all_done) * 100, 1) if all_done else None

    return {
        "today": {
            "total": len(today),
            "done": len(done),
            "wins": len(wins),
            "losses": len(losses),
            "running": len(running),
            "rate": rate,
        },
        "all": {
            "total": len(all_s),
            "done": len(all_done),
            "wins": len(all_wins),
            "rate": all_rate,
        },
        "signals": list(reversed(today[-30:])),
    }


def recent_signals(limit=30):
    """Recent signals snapshot."""
    with _lock:
        return list(reversed([dict(s) for s in _signals[-limit:]]))


def reset_today():
    """Remove today's signals only."""
    day = _ist().strftime("%Y-%m-%d")
    global _signals
    with _lock:
        _signals = [s for s in _signals if s.get("day") != day]
        _save()


def reset_all():
    """Clear all stored signals."""
    global _signals
    with _lock:
        _signals = []
        _save()


def candle_snapshot(sym, limit=100):
    """Return recent candles for UI/debug."""
    with _lock:
        cs = list(CANDLES.get(sym, []))
    return cs[-limit:]


def indicator_snapshot(sym):
    """Full indicator snapshot for one symbol."""
    x = calc(sym)
    return {
        "symbol": sym,
        "indicator": x,
        "candles": candle_snapshot(sym, 50),
        "prev_day": PREV_DAY.get(sym),
    }


def all_indicator_status():
    """Quick status of all symbols currently building candles."""
    with _lock:
        syms = list(CANDLES.keys())
    out = []
    for sym in syms:
        x = calc(sym)
        out.append({
            "symbol": sym,
            "bars": x.get("bars", 0),
            "ready": x.get("ready", False),
            "rsi": x.get("rsi"),
            "ema9": x.get("ema9"),
            "ema21": x.get("ema21"),
            "atr": x.get("atr"),
            "adx": x.get("adx"),
            "vwap": x.get("vwap"),
            "htf": x.get("htf"),
        })
    return out


def cleanup_old_signals(days=30):
    """Keep signal file small by removing very old records."""
    global _signals
    cutoff = (_ist() - timedelta(days=days)).strftime("%Y-%m-%d")
    with _lock:
        _signals = [
            s for s in _signals
            if s.get("day", "") >= cutoff
        ]
        _save()


def diagnostics():
    """Basic diagnostics for terminal/debug page."""
    with _lock:
        candle_symbols = len(CANDLES)
        candle_count = sum(len(v) for v in CANDLES.values())
        sig_count = len(_signals)

    ready = 0
    for sym in list(CANDLES.keys()):
        try:
            if calc(sym).get("ready"):
                ready += 1
        except Exception:
            pass

    return {
        "today": _today,
        "symbols": candle_symbols,
        "candles": candle_count,
        "indicators_ready": ready,
        "signals": sig_count,
        "max_candles": MAX_CANDLES,
        "tick_guard": MAX_TICK_JUMP,
        "time": _ist().strftime("%Y-%m-%d %H:%M:%S"),
    }


# Clean old tracker records once when module loads.
try:
    cleanup_old_signals(30)
except Exception:
    pass
