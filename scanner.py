"""
KRT — Scanner engine
1. Breakout / Breakdown : previous-day High/Low break detection
   - LIVE mode  : Angel One historical candles (previous trading day)
   - DEMO mode  : simulated
2. High Conviction score : breakout + %change + volume rank சேர்ந்த composite
3. Chartink webhook alerts : in-memory store (recent 30)
"""
import time, threading, datetime
from collections import deque

import smart_client
from notify import notify

# ---------------- Chartink alerts store ----------------
_chartink_alerts = deque(maxlen=30)
_ck_lock = threading.Lock()


def add_chartink_alert(payload):
    """
    Chartink webhook JSON format:
    {"stocks":"TCS,INFY","trigger_prices":"4182,1866",
     "triggered_at":"10:15 am","scan_name":"My Breakout Scan", ...}
    """
    stocks = [s.strip() for s in str(payload.get("stocks", "")).split(",") if s.strip()]
    prices = [p.strip() for p in str(payload.get("trigger_prices", "")).split(",")]
    scan = payload.get("scan_name") or payload.get("alert_name") or "Chartink Scan"
    at = payload.get("triggered_at", time.strftime("%H:%M"))
    items = []
    with _ck_lock:
        for i, s in enumerate(stocks):
            try:
                from ai_engine import classify_chartink
                verdict, reasons, opt = classify_chartink(scan, s)
            except Exception as e:
                print("classify error:", e); verdict, reasons, opt = "WATCH", [], None
            item = {"symbol": s.upper(),
                    "price": prices[i] if i < len(prices) else "",
                    "scan": scan, "time": at,
                    "verdict": verdict, "reasons": reasons, "option": opt}
            _chartink_alerts.appendleft(item)
            items.append(item)
    if items:
        lines = []
        for x in items[:6]:
            l = f"• {x['verdict']} — {x['symbol']} @ {x['price']}"
            if x.get("option"):
                o = x["option"]
                l += (f"\n   🎯 {o['instrument']} | Entry {o['entry']}"
                      f" | T {o['t1']}/{o['t2']}/{o['t3']} | SL {o['sl']}")
            lines.append(l)
        notify("🚨 <b>LIVE JACKPOT SIGNAL</b>\n" + f"({at})\n" + "\n".join(lines) +
               "\n\n⚠️ Educational only")
    return len(items)


def get_chartink_alerts():
    with _ck_lock:
        return list(_chartink_alerts)


# ---------------- Prev-day High/Low (for breakout detection) ----------------
_pdhl_cache = {"data": {}, "date": None}
_pd_lock = threading.Lock()


def _prev_day_levels_live():
    """Fetch previous trading day OHLC for the watchlist via SmartAPI candles."""
    sc = smart_client._login()
    today = datetime.date.today()
    frm = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d 09:15")
    to = today.strftime("%Y-%m-%d 09:00")   # today opening-க்கு முன்னாடி வரை
    out = {}
    for name, (exch, token) in smart_client.WATCHLIST.items():
        if name in ("NIFTY 50", "BANKNIFTY", "INDIA VIX"):
            continue
        try:
            resp = sc.getCandleData({
                "exchange": exch, "symboltoken": token,
                "interval": "ONE_DAY", "fromdate": frm, "todate": to})
            candles = (resp or {}).get("data") or []
            if candles:
                last = candles[-1]          # [ts, o, h, l, c, v]
                out[name] = {"pdh": float(last[2]), "pdl": float(last[3])}
            time.sleep(0.35)                # rate-limit friendly
        except Exception as e:
            print("candle error:", name, e)
    return out


def _prev_day_levels():
    with _pd_lock:
        today = datetime.date.today().isoformat()
        if _pdhl_cache["date"] == today and _pdhl_cache["data"]:
            return _pdhl_cache["data"]
        data = {}
        try:
            if smart_client._has_creds():
                data = _prev_day_levels_live()
        except Exception as e:
            print("pdhl fetch failed:", e)
        if not data:  # demo fallback: LTP-ஐ வெச்சு approx levels
            rows, _ = smart_client.get_quotes()
            for r in rows:
                if r["symbol"] in ("NIFTY 50", "BANKNIFTY", "INDIA VIX"):
                    continue
                data[r["symbol"]] = {"pdh": round(r["ltp"] * 0.985, 2),
                                     "pdl": round(r["ltp"] * 0.955, 2)}
        _pdhl_cache.update(data=data, date=today)
        return data


_notified = set()          # ஒரே alert-ஐ repeat-ஆ push பண்ணாம இருக்க


def scan_breakouts():
    """Breakout/Breakdown list + High Conviction score."""
    rows, mode = smart_client.get_quotes()
    levels = _prev_day_levels()
    stocks = [r for r in rows
              if r["symbol"] not in ("NIFTY 50", "BANKNIFTY", "INDIA VIX")]
    vol_rank = {r["symbol"]: i for i, r in enumerate(
        sorted(stocks, key=lambda x: x.get("volume") or 0, reverse=True))}

    breakouts, breakdowns, conviction = [], [], []
    for r in stocks:
        lv = levels.get(r["symbol"])
        if not lv:
            continue
        ltp, chg = r["ltp"], r["chg"]
        item = {"symbol": r["symbol"], "ltp": ltp, "chg": chg,
                "pdh": lv["pdh"], "pdl": lv["pdl"]}
        is_bo = ltp > lv["pdh"]
        is_bd = ltp < lv["pdl"]
        if is_bo:
            breakouts.append(item)
        if is_bd:
            breakdowns.append(item)

        # ---- High Conviction score (0–100) ----
        score = 0
        score += 40 if is_bo else (0 if not is_bd else -10)
        score += min(30, max(0, chg * 6))                    # momentum
        score += max(0, 20 - vol_rank.get(r["symbol"], 9) * 4)  # volume rank
        score += 10 if chg > 0 and (r.get("volume") or 0) > 0 else 0
        score = max(0, min(100, round(score)))
        if score >= 70:
            conviction.append({**item, "score": score})
            key = f"{r['symbol']}-{datetime.date.today()}"
            if key not in _notified and mode == "live":
                _notified.add(key)
                notify(f"💎 <b>PREMIUM JACKPOT SETUP</b>\n{r['symbol']} — Score {score}/100\n"
                       f"LTP ₹{ltp} ({'+' if chg>=0 else ''}{chg}%)\n"
                       f"PDH break ✅ | Vol rank #{vol_rank.get(r['symbol'],0)+1}")

    conviction.sort(key=lambda x: x["score"], reverse=True)
    return {"breakouts": breakouts, "breakdowns": breakdowns,
            "conviction": conviction[:5], "mode": mode}
