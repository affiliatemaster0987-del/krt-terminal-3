"""
KRT — AI Engine (v3)
Daily candles-லேர்ந்து per-stock indicators compute பண்ணி
AI Trade Score (0-100), Best Call, Relative Volume, Sector Strength,
Market Breadth, Entry Timing, Risk Meter எல்லாம் தரும்.

LIVE : Angel One ONE_DAY candles (ஒரு நாளைக்கு ஒரு தடவை fetch, cache)
DEMO : simulated indicators
"""
import time, threading, datetime, random

import smart_client
from notify import notify

SECTOR_MAP = {
    "RELIANCE": "Energy", "TCS": "IT", "INFY": "IT",
    "HDFCBANK": "Bank", "ICICIBANK": "Bank", "SBIN": "Bank",
    "ITC": "FMCG", "VBL": "FMCG",
    "TATAMOTORS": "Auto", "BEL": "Defence",
}

_hist = {"data": {}, "date": None}
_lock = threading.Lock()
_best_call_sent = {"date": None}


# ---------------- indicator maths ----------------
def _sma(vals, n):
    return sum(vals[-n:]) / n if len(vals) >= n else (sum(vals) / len(vals) if vals else 0)


def _rsi(closes, n=14):
    if len(closes) < n + 1:
        return 50.0
    gains, losses = [], []
    for i in range(-n, 0):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag, al = sum(gains) / n, sum(losses) / n
    if al == 0:
        return 100.0
    rs = ag / al
    return round(100 - 100 / (1 + rs), 1)


# ---------------- history fetch (daily cache) ----------------
def _fetch_history_live():
    sc = smart_client._login()
    today = datetime.date.today()
    frm = (today - datetime.timedelta(days=60)).strftime("%Y-%m-%d 09:15")
    to = today.strftime("%Y-%m-%d 09:00")
    out = {}
    for name, (exch, token) in smart_client.WATCHLIST.items():
        if name in ("NIFTY 50", "BANKNIFTY", "INDIA VIX"):
            continue
        try:
            resp = sc.getCandleData({"exchange": exch, "symboltoken": token,
                                     "interval": "ONE_DAY",
                                     "fromdate": frm, "todate": to})
            candles = (resp or {}).get("data") or []
            closes = [float(c[4]) for c in candles]
            vols = [float(c[5]) for c in candles]
            if closes:
                out[name] = {
                    "sma20": _sma(closes, 20),
                    "rsi": _rsi(closes),
                    "avg_vol20": _sma(vols, 20),
                    "pdh": float(candles[-1][2]),
                    "pdl": float(candles[-1][3]),
                }
            time.sleep(0.35)
        except Exception as e:
            print("hist error:", name, e)
    return out


def _fetch_history_demo():
    rows, _ = smart_client.get_quotes()
    out = {}
    for r in rows:
        if r["symbol"] in ("NIFTY 50", "BANKNIFTY", "INDIA VIX"):
            continue
        random.seed(hash(r["symbol"]) % 999)
        out[r["symbol"]] = {
            "sma20": r["ltp"] * random.uniform(0.94, 1.02),
            "rsi": round(random.uniform(35, 72), 1),
            "avg_vol20": (r.get("volume") or 1_000_000) / random.uniform(1.2, 5.5),
            "pdh": r["ltp"] * 0.988, "pdl": r["ltp"] * 0.956,
        }
    return out


def get_history():
    with _lock:
        today = datetime.date.today().isoformat()
        if _hist["date"] == today and _hist["data"]:
            return _hist["data"]
        data = {}
        try:
            if smart_client._has_creds():
                data = _fetch_history_live()
        except Exception as e:
            print("history fetch failed:", e)
        if not data:
            data = _fetch_history_demo()
        _hist.update(data=data, date=today)
        return data


# ---------------- news sentiment lookup ----------------
def _news_boost(symbol):
    try:
        from news import get_news
        for n in get_news():
            if any(symbol.startswith(s) or s in symbol for s in n.get("stocks", [])):
                if n["tag"] == "Positive":
                    return 8, "Positive News"
                if n["tag"] == "Negative":
                    return -10, "Negative News"
    except Exception:
        pass
    return 0, None


# ---------------- AI Trade Score ----------------
def compute_scores():
    rows, mode = smart_client.get_quotes()
    hist = get_history()
    scored = []
    for r in rows:
        s = r["symbol"]
        if s in ("NIFTY 50", "BANKNIFTY", "INDIA VIX"):
            continue
        h = hist.get(s)
        if not h:
            continue
        ltp, chg, vol = r["ltp"], r["chg"], (r.get("volume") or 0)
        rvol = round(vol / h["avg_vol20"], 1) if h["avg_vol20"] else 0
        reasons, score = [], 0

        # Trend vs SMA20 (25)
        if ltp > h["sma20"]:
            score += 25; reasons.append("Above 20-SMA (uptrend)")
        # PDH break (20)
        if ltp > h["pdh"]:
            score += 20; reasons.append("Prev-Day High break")
        elif ltp < h["pdl"]:
            score -= 15; reasons.append("Prev-Day Low break ⚠️")
        # RSI zone (15)
        if 55 <= h["rsi"] <= 70:
            score += 15; reasons.append(f"RSI {h['rsi']} (strong zone)")
        elif h["rsi"] > 75:
            score += 5; reasons.append(f"RSI {h['rsi']} (overbought)")
        elif h["rsi"] < 35:
            score -= 5
        # Relative volume (20)
        if rvol >= 2:
            score += 20; reasons.append(f"Volume {rvol}x avg 🔥")
        elif rvol >= 1.3:
            score += 10; reasons.append(f"Volume {rvol}x avg")
        # Momentum (12)
        score += max(-6, min(12, round(chg * 4)))
        if chg >= 1:
            reasons.append(f"Momentum +{chg}%")
        # News (±8/10)
        nb, ntxt = _news_boost(s)
        score += nb
        if ntxt:
            reasons.append(ntxt)

        score = max(0, min(100, round(score + 30)))   # base 30
        buy_p = score
        scored.append({
            "symbol": s, "ltp": ltp, "chg": chg, "rvol": rvol,
            "rsi": h["rsi"], "score": score,
            "buy_prob": buy_p, "sell_prob": 100 - buy_p,
            "reasons": reasons[:7],
            "sector": SECTOR_MAP.get(s, "Other"),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored, mode


# ---------------- Best Call ----------------
def best_call(scored, mode, vix_ltp):
    if not scored:
        return None
    top = scored[0]
    if top["score"] < 75:
        return {"status": "NO_CALL",
                "note": "இன்னைக்கு 75+ score எந்த stock-க்கும் இல்ல — force trade வேணாம்."}
    e = top["ltp"]
    call = {
        "status": "CALL", "symbol": top["symbol"], "side": "BUY",
        "confidence": top["score"],
        "entry": round(e, 1), "sl": round(e * 0.988, 1),
        "t1": round(e * 1.010, 1), "t2": round(e * 1.020, 1), "t3": round(e * 1.032, 1),
        "reasons": top["reasons"],
        "timing": "BUY NOW" if top["score"] >= 85 else "WAIT — confirmation pending",
        "timing_prob": top["score"],
        "risk": "LOW" if (vix_ltp and vix_ltp < 14 and top["score"] >= 85)
                else ("MEDIUM" if top["score"] >= 78 else "HIGH"),
    }
    # Telegram — ஒரு நாளைக்கு ஒரு தடவை மட்டும் (live mode)
    today = datetime.date.today().isoformat()
    if mode == "live" and _best_call_sent["date"] != today and call["confidence"] >= 85:
        _best_call_sent["date"] = today
        notify("🔥 <b>KRT BEST JACKPOT</b>\n"
               f"<b>{call['symbol']}</b> — {call['side']} | Confidence {call['confidence']}%\n"
               f"Entry ₹{call['entry']} | SL ₹{call['sl']}\n"
               f"T1 ₹{call['t1']} · T2 ₹{call['t2']} · T3 ₹{call['t3']}\n"
               "Reason: " + " · ".join(call["reasons"][:4]) +
               "\n\n⚠️ Educational only. Not SEBI-registered advice.")
    return call


# ---------------- Sector strength / breadth ----------------
def sector_strength(scored):
    agg = {}
    for s in scored:
        agg.setdefault(s["sector"], []).append(s["chg"])
    out = []
    for sec, chgs in agg.items():
        avg = sum(chgs) / len(chgs)
        stars = 5 if avg >= 1.5 else 4 if avg >= 0.6 else 3 if avg >= 0 else 2 if avg >= -1 else 1
        out.append({"sector": sec, "avg": round(avg, 2), "stars": stars})
    out.sort(key=lambda x: x["avg"], reverse=True)
    return out


def market_breadth(scored):
    adv = sum(1 for s in scored if s["chg"] > 0)
    dec = sum(1 for s in scored if s["chg"] < 0)
    return {"advances": adv, "declines": dec,
            "adr": round(adv / dec, 2) if dec else adv,
            "bias": "Bullish" if adv > dec else "Bearish" if dec > adv else "Neutral"}


# ---------------- Chartink smart classify ----------------
BEAR_WORDS = ("sell", "short", "bear", "breakdown", "down", "fall", "weak")

def classify_chartink(scan_name, symbol):
    """BUY / SELL / WATCH / AVOID + reasons + CE/PE jackpot option call."""
    from options import build_option_call
    scan_l = (scan_name or "").lower()
    scored, _ = compute_scores()
    me = next((s for s in scored if s["symbol"] == symbol.upper()), None)
    score = me["score"] if me else None
    spot = me["ltp"] if me else None

    if any(w in scan_l for w in BEAR_WORDS):
        reasons = ["Bearish scan trigger"] + (me["reasons"][:2] if me else [])
        oc = build_option_call(symbol.upper(), "SELL", spot, score or 60) if spot else None
        return "SELL", reasons, oc
    if score is not None:
        if score >= 70:
            oc = build_option_call(symbol.upper(), "BUY", spot, score)
            return "BUY", me["reasons"][:4] + [f"AI Score {score}"], oc
        if score >= 45:
            return "WATCH", [f"AI Score {score} — breakout confirm ஆகட்டும்"], None
        return "AVOID", [f"AI Score {score} குறைவு — skip"], None
    return "WATCH", ["Watchlist-ல இல்லாத stock — manual-ஆ பாருங்க"], None


# ---------------- master endpoint ----------------
def build_ai():
    scored, mode = compute_scores()
    rows, _ = smart_client.get_quotes()
    vix = next((r["ltp"] for r in rows if r["symbol"] == "INDIA VIX"), None)
    rvol_list = sorted([s for s in scored if s["rvol"] >= 1.2],
                       key=lambda x: x["rvol"], reverse=True)[:6]
    radar = [s for s in scored if s["score"] >= 80][:3]
    return {
        "mode": mode,
        "scores": scored[:10],
        "best_call": best_call(scored, mode, vix),
        "rvol": rvol_list,
        "sectors": sector_strength(scored),
        "breadth": market_breadth(scored),
        "radar": radar,
        "vix": vix,
        "risk_market": "LOW" if (vix and vix < 13) else "MEDIUM" if (vix and vix < 17) else "HIGH",
        "updated": time.strftime("%H:%M:%S"),
    }
