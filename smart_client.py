"""
KRT AI Terminal — Angel One SmartAPI client
- Credentials இருந்தா  : real live data (LTP mode via Market Data API)
- Credentials இல்லைனா : DEMO mode (simulated data) — site எப்பவும் வேலை செய்யும்
Environment variables (Render dashboard → Environment):
  SMARTAPI_KEY      = your API key
  SMARTAPI_CLIENT   = Angel One client code  (e.g. A123456)
  SMARTAPI_PIN      = your MPIN
  SMARTAPI_TOTP     = TOTP secret (the token shown when you enabled TOTP)
"""
import os, time, math, random, threading

# ---- watchlist: symbol -> (exchange, symboltoken) ----
# Tokens from Angel One instrument master (OpenAPIScripMaster.json)
WATCHLIST = {
    "NIFTY 50":   ("NSE", "99926000"),
    "BANKNIFTY":  ("NSE", "99926009"),
    "INDIA VIX":  ("NSE", "99926017"),
    "RELIANCE":   ("NSE", "2885"),
    "TCS":        ("NSE", "11536"),
    "HDFCBANK":   ("NSE", "1333"),
    "INFY":       ("NSE", "1594"),
    "SBIN":       ("NSE", "3045"),
    "ICICIBANK":  ("NSE", "4963"),
    "ITC":        ("NSE", "1660"),
    "TATAMOTORS": ("NSE", "3456"),
    "BEL":        ("NSE", "383"),
    "VBL":        ("NSE", "18921"),
}

DEMO_BASE = {
    "NIFTY 50": 24812.35, "BANKNIFTY": 52140.60, "INDIA VIX": 13.42,
    "RELIANCE": 2941.50, "TCS": 4182.10, "HDFCBANK": 1712.40, "INFY": 1868.25,
    "SBIN": 862.30, "ICICIBANK": 1244.15, "ITC": 512.80, "TATAMOTORS": 712.90,
    "BEL": 312.70, "VBL": 612.40,
}

_cache = {"data": None, "ts": 0, "mode": "demo"}
_lock = threading.Lock()
CACHE_SECONDS = 3


def _has_creds():
    return all(os.environ.get(k) for k in
               ("SMARTAPI_KEY", "SMARTAPI_CLIENT", "SMARTAPI_PIN", "SMARTAPI_TOTP"))


_smart = None

def _login():
    """Login to SmartAPI once and reuse session."""
    global _smart
    if _smart is not None:
        return _smart
    from SmartApi import SmartConnect
    import pyotp
    sc = SmartConnect(api_key=os.environ["SMARTAPI_KEY"])
    totp = pyotp.TOTP(os.environ["SMARTAPI_TOTP"]).now()
    data = sc.generateSession(os.environ["SMARTAPI_CLIENT"],
                              os.environ["SMARTAPI_PIN"], totp)
    if not data or not data.get("status"):
        raise RuntimeError(f"SmartAPI login failed: {data}")
    _smart = sc
    return sc


def _fetch_live():
    """Fetch LTP + prev close for the whole watchlist using Market Data API (FULL mode)."""
    sc = _login()
    tokens = [t for (_, t) in WATCHLIST.values()]
    payload = {"mode": "FULL", "exchangeTokens": {"NSE": tokens}}
    resp = sc.getMarketData(payload["mode"], payload["exchangeTokens"])
    fetched = resp.get("data", {}).get("fetched", []) if resp else []
    by_token = {str(row.get("symbolToken")): row for row in fetched}
    out = []
    for name, (_, token) in WATCHLIST.items():
        row = by_token.get(str(token))
        if not row:
            continue
        ltp = float(row.get("ltp") or 0)
        close = float(row.get("close") or 0) or ltp
        chg = ((ltp - close) / close * 100) if close else 0.0
        out.append({
            "symbol": name, "ltp": round(ltp, 2), "chg": round(chg, 2),
            "high": row.get("high"), "low": row.get("low"),
            "volume": row.get("tradeVolume"), "open": row.get("open"),
            "close": close,
        })
    if not out:
        raise RuntimeError("Market Data API returned no rows")
    return out


def _fetch_demo():
    t = time.time()
    out = []
    for i, (name, base) in enumerate(DEMO_BASE.items()):
        wob = math.sin(t / 25 + i * 1.7) * base * 0.004 + random.uniform(-1, 1) * base * 0.0005
        ltp = base + wob
        chg = (wob / base) * 100 + [0.42, 0.31, -1.1, 0.6, 1.4, -0.3, 0.9,
                                    0.5, 0.7, -0.4, -2.8, 3.9, 6.8][i % 13]
        out.append({
            "symbol": name, "ltp": round(ltp, 2), "chg": round(chg, 2),
            "high": round(ltp * 1.008, 2), "low": round(ltp * 0.991, 2),
            "volume": int(abs(math.sin(t / 40 + i)) * 4_000_000 + 500_000),
            "open": round(base * 0.998, 2), "close": round(base, 2),
        })
    return out


def get_quotes():
    """Cached quotes. Returns (rows, mode) where mode = 'live' | 'demo'."""
    with _lock:
        now = time.time()
        if _cache["data"] and now - _cache["ts"] < CACHE_SECONDS:
            return _cache["data"], _cache["mode"]
        mode = "demo"
        try:
            if _has_creds():
                rows = _fetch_live()
                mode = "live"
            else:
                rows = _fetch_demo()
        except Exception as e:
            print("SmartAPI error, falling back to demo:", e)
            global _smart
            _smart = None          # force re-login next time
            rows = _fetch_demo()
        _cache.update(data=rows, ts=now, mode=mode)
        return rows, mode


def build_dashboard():
    rows, mode = get_quotes()
    indices = [r for r in rows if r["symbol"] in ("NIFTY 50", "BANKNIFTY", "INDIA VIX")]
    stocks = [r for r in rows if r not in indices]
    gainers = sorted(stocks, key=lambda r: r["chg"], reverse=True)[:5]
    losers = sorted(stocks, key=lambda r: r["chg"])[:5]
    by_vol = sorted(stocks, key=lambda r: r.get("volume") or 0, reverse=True)[:5]
    alerts = []
    for r in stocks:
        high, ltp, chg = r.get("high") or 0, r["ltp"], r["chg"]
        if high and ltp >= high * 0.999 and chg > 0.5:
            alerts.append({"symbol": r["symbol"], "type": "BUY",
                           "reason": "Day-High zone break", "chg": chg})
        if chg <= -2.5:
            alerts.append({"symbol": r["symbol"], "type": "WATCH",
                           "reason": "Sharp fall > 2.5%", "chg": chg})
    return {"mode": mode, "indices": indices, "gainers": gainers,
            "losers": losers, "volume": by_vol, "alerts": alerts,
            "updated": time.strftime("%H:%M:%S")}
