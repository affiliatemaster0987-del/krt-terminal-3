"""
KRT AI Terminal 3.0 — Angel One SmartAPI client
- 180+ F&O stocks (tokens auto-resolved from Angel One instrument master)
- Prev Day High/Low, Prev Week High, First 5-min candle High (opening range)
- Sector mapping -> strong sectors / weak sectors
- Credentials இல்லைனா DEMO mode (site எப்பவும் வேலை செய்யும்)

Environment variables (Render → Environment):
  SMARTAPI_KEY, SMARTAPI_CLIENT, SMARTAPI_PIN, SMARTAPI_TOTP
"""
import os, time, math, random, threading, json
import urllib.request
import indicators as IND
from datetime import datetime, timedelta

# ───────────────────────── INDICES (fixed tokens) ─────────────────────────
INDICES = {
    "NIFTY 50":  "99926000",
    "BANKNIFTY": "99926009",
    "INDIA VIX": "99926017",
}

# ───────────────────────── F&O UNIVERSE + SECTORS ─────────────────────────
# symbol : sector   (Angel token auto-resolve ஆகும் — hardcode இல்லை)
UNIVERSE = {
    # IT
    "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT", "TECHM": "IT",
    "LTIM": "IT", "PERSISTENT": "IT", "COFORGE": "IT", "MPHASIS": "IT", "OFSS": "IT",
    # BANK
    "HDFCBANK": "BANK", "ICICIBANK": "BANK", "AXISBANK": "BANK", "KOTAKBANK": "BANK",
    "INDUSINDBK": "BANK", "FEDERALBNK": "BANK", "IDFCFIRSTB": "BANK", "BANDHANBNK": "BANK",
    "AUBANK": "BANK",
    # PSU BANK
    "SBIN": "PSU BANK", "BANKBARODA": "PSU BANK", "PNB": "PSU BANK",
    "CANBK": "PSU BANK", "UNIONBANK": "PSU BANK",
    # NBFC / FIN
    "BAJFINANCE": "FINANCE", "BAJAJFINSV": "FINANCE", "CHOLAFIN": "FINANCE",
    "SHRIRAMFIN": "FINANCE", "LICHSGFIN": "FINANCE", "MUTHOOTFIN": "FINANCE",
    "PFC": "FINANCE", "RECLTD": "FINANCE", "HDFCLIFE": "FINANCE", "SBILIFE": "FINANCE",
    "ICICIGI": "FINANCE", "ICICIPRULI": "FINANCE", "LTF": "FINANCE", "ABCAPITAL": "FINANCE",
    # AUTO
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "M&M": "AUTO", "BAJAJ-AUTO": "AUTO",
    "HEROMOTOCO": "AUTO", "EICHERMOT": "AUTO", "TVSMOTOR": "AUTO", "ASHOKLEY": "AUTO",
    "MOTHERSON": "AUTO", "BHARATFORG": "AUTO", "SONACOMS": "AUTO", "BALKRISIND": "AUTO", "APOLLOTYRE": "AUTO",
    # ENERGY / OIL
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "IOC": "ENERGY", "BPCL": "ENERGY",
    "HINDPETRO": "ENERGY", "GAIL": "ENERGY", "PETRONET": "ENERGY",
    # POWER
    "NTPC": "POWER", "POWERGRID": "POWER", "TATAPOWER": "POWER", "ADANIPOWER": "POWER",
    "ADANIGREEN": "POWER",
    # METAL
    "TATASTEEL": "METAL", "JSWSTEEL": "METAL", "HINDALCO": "METAL", "VEDL": "METAL",
    "JINDALSTEL": "METAL", "SAIL": "METAL", "NMDC": "METAL", "HINDZINC": "METAL",
    # PHARMA
    "SUNPHARMA": "PHARMA", "CIPLA": "PHARMA", "DRREDDY": "PHARMA", "DIVISLAB": "PHARMA",
    "AUROPHARMA": "PHARMA", "LUPIN": "PHARMA", "TORNTPHARM": "PHARMA",
    "ZYDUSLIFE": "PHARMA", "BIOCON": "PHARMA",
    # HEALTHCARE
    "APOLLOHOSP": "HEALTHCARE", "MAXHEALTH": "HEALTHCARE",
    # FMCG
    "ITC": "FMCG", "HINDUNILVR": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG",
    "DABUR": "FMCG", "MARICO": "FMCG", "GODREJCP": "FMCG", "COLPAL": "FMCG",
    "TATACONSUM": "FMCG", "VBL": "FMCG",
    # DEFENCE / PSU
    "BEL": "DEFENCE", "HAL": "DEFENCE", "BHEL": "DEFENCE",
    # INFRA / CAPITAL GOODS
    "LT": "INFRA", "SIEMENS": "INFRA", "ABB": "INFRA", "CUMMINSIND": "INFRA", "POLYCAB": "INFRA", "HAVELLS": "INFRA",
    "RVNL": "INFRA", "IRFC": "INFRA", "IRCTC": "INFRA", "CONCOR": "INFRA",
    "ADANIPORTS": "INFRA", "GMRAIRPORT": "INFRA",
    # CEMENT
    "ULTRACEMCO": "CEMENT", "GRASIM": "CEMENT", "SHREECEM": "CEMENT",
    "AMBUJACEM": "CEMENT", "ACC": "CEMENT",
    # REALTY
    "DLF": "REALTY", "GODREJPROP": "REALTY", "OBEROIRLTY": "REALTY", "LODHA": "REALTY",
    # CONSUMER / RETAIL
    "TITAN": "CONSUMER", "TRENT": "CONSUMER", "DMART": "CONSUMER", "JUBLFOOD": "CONSUMER",
    "PAGEIND": "CONSUMER", "VOLTAS": "CONSUMER",
    "DIXON": "CONSUMER",
    # CHEMICAL
    "PIDILITIND": "CHEMICAL", "SRF": "CHEMICAL", "UPL": "CHEMICAL", "TATACHEM": "CHEMICAL",
    "DEEPAKNTR": "CHEMICAL", "PIIND": "CHEMICAL",
    "ASIANPAINT": "CHEMICAL", "BERGEPAINT": "CHEMICAL",
    # TELECOM / MEDIA
    "BHARTIARTL": "TELECOM", "IDEA": "TELECOM", "INDUSTOWER": "TELECOM",
    # NEW AGE
    "ZOMATO": "NEW AGE", "SWIGGY": "NEW AGE", "PAYTM": "NEW AGE", "NYKAA": "NEW AGE",
    "POLICYBZR": "NEW AGE", "DELHIVERY": "NEW AGE",
    # DIVERSIFIED
    "ADANIENT": "DIVERSIFIED", "JSWENERGY": "DIVERSIFIED",
    "INDHOTEL": "HOTELS", "IGL": "GAS",
}

YF = "https://query1.finance.yahoo.com/v8/finance/chart/"
SCRIP_MASTER_URL = ("https://margincalculator.angelbroking.com/OpenAPI_File/"
                    "files/OpenAPIScripMaster.json")

_tokens = {}          # symbol -> token
_tokens_ready = False
_cache = {"data": None, "ts": 0, "mode": "demo"}
_levels = {"pdh": {}, "pdl": {}, "pwh": {}, "orh": {}, "day": "", "or_day": ""}
_preopen = {"day": "", "rows": [], "final": False}
_diag = {"source": "angel", "tokens": 0, "pdh_ok": 0, "orh_ok": 0, "last_error": "", "sample_error": "",
         "login": "not tried", "running": False, "started": ""}
_lock = threading.Lock()
CACHE_SECONDS = 3


# ───────────────────────── credentials / login ─────────────────────────
def _has_creds():
    return all(os.environ.get(k) for k in
               ("SMARTAPI_KEY", "SMARTAPI_CLIENT", "SMARTAPI_PIN", "SMARTAPI_TOTP"))


_smart = None

def _login():
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


# ───────────────────────── instrument master (token resolve) ─────────────────────────
def _load_tokens():
    """Angel scrip master-la irundhu NSE equity tokens resolve pannum (once)."""
    global _tokens, _tokens_ready
    if _tokens_ready:
        return _tokens
    try:
        req = urllib.request.Request(SCRIP_MASTER_URL,
                                     headers={"User-Agent": "KRT-Terminal"})
        with urllib.request.urlopen(req, timeout=60) as r:
            rows = json.loads(r.read().decode())
        want = set(UNIVERSE.keys())
        found = {}
        for row in rows:
            if row.get("exch_seg") != "NSE":
                continue
            sym = str(row.get("symbol", ""))
            if not sym.endswith("-EQ"):
                continue
            name = sym[:-3]
            if name in want and name not in found:
                found[name] = str(row.get("token"))
        _tokens = found
        _tokens_ready = True
        _diag["tokens"] = len(found)
        print(f"[scrip master] resolved {len(found)}/{len(want)} tokens")
    except Exception as e:
        _diag["last_error"] = "scrip master: " + str(e)[:200]
        print("scrip master error:", e)
    return _tokens


def _tok_map():
    """symbol -> token (indices + resolved equities)."""
    m = dict(INDICES)
    m.update(_load_tokens())
    return m


# ───────────────────────── live quotes ─────────────────────────
def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def _fetch_live():
    sc = _login()
    tmap = _tok_map()
    rev = {v: k for k, v in tmap.items()}
    tokens = list(tmap.values())
    fetched = []
    for grp in _chunks(tokens, 50):        # Angel limit: 50 tokens / request
        try:
            resp = sc.getMarketData("FULL", {"NSE": grp})
            fetched += (resp.get("data", {}).get("fetched", []) if resp else [])
        except Exception as e:
            print("market data chunk error:", e)
        time.sleep(0.25)
    out = []
    for row in fetched:
        name = rev.get(str(row.get("symbolToken")))
        if not name:
            continue
        ltp = float(row.get("ltp") or 0)
        close = float(row.get("close") or 0) or ltp
        chg = ((ltp - close) / close * 100) if close else 0.0
        out.append({
            "symbol": name, "ltp": round(ltp, 2), "chg": round(chg, 2),
            "chgpts": round(ltp - close, 2),
            "high": row.get("high"), "low": row.get("low"),
            "volume": row.get("tradeVolume"), "open": row.get("open"),
            "close": close, "sector": UNIVERSE.get(name, "INDEX"),
        })
    if not out:
        raise RuntimeError("Market Data API returned no rows")
    return out


def _fetch_demo():
    t = time.time()
    out = []
    names = list(INDICES.keys()) + list(UNIVERSE.keys())
    for i, name in enumerate(names):
        base = 100 + (hash(name) % 4000)
        if name == "NIFTY 50": base = 24812.35
        if name == "BANKNIFTY": base = 52140.60
        if name == "INDIA VIX": base = 13.42
        wob = math.sin(t / 25 + i * 1.7) * base * 0.004
        ltp = base + wob
        chg = round(math.sin(t / 90 + i * 2.3) * 4 + random.uniform(-.4, .4), 2)
        out.append({
            "symbol": name, "ltp": round(ltp, 2), "chg": chg,
            "chgpts": round(base * chg / 100, 2),
            "high": round(ltp * 1.008, 2), "low": round(ltp * 0.991, 2),
            "volume": int(abs(math.sin(t / 40 + i)) * 6_000_000 + 300_000),
            "open": round(base * 0.998, 2), "close": round(base, 2),
            "sector": UNIVERSE.get(name, "INDEX"),
        })
    return out


def get_quotes():
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
            _smart = None
            rows = _fetch_demo()
        _cache.update(data=rows, ts=now, mode=mode)
        return rows, mode


# ───────────── PDH / PDL / PWH  (daily candles, once per day) ─────────────
def _ist_now():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


def _yf(symbol, rng, interval):
    """Yahoo Finance chart data — Angel historical fail aana fallback."""
    url = f"{YF}{symbol}?range={rng}&interval={interval}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def _yf_levels(sym):
    """(pdh, pdl, pwh) from Yahoo daily candles."""
    d = _yf(sym + ".NS", "1mo", "1d")
    res = d["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    ts = res["timestamp"]
    highs, lows = q["high"], q["low"]
    today = _ist_now().strftime("%Y-%m-%d")
    rows = []
    for i, t in enumerate(ts):
        if highs[i] is None or lows[i] is None:
            continue
        day = datetime.utcfromtimestamp(t + 19800).strftime("%Y-%m-%d")
        if day == today:
            continue
        rows.append((day, float(highs[i]), float(lows[i])))
    if not rows:
        return None
    pdh, pdl = rows[-1][1], rows[-1][2]
    past5 = rows[-5:]
    pwh = max(x[1] for x in past5)
    return round(pdh, 2), round(pdl, 2), round(pwh, 2)


def _yf_opening_high(sym):
    """First 5-min candle high (today 09:15–09:20) from Yahoo."""
    d = _yf(sym + ".NS", "5d", "5m")
    res = d["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    ts = res["timestamp"]
    today = _ist_now().strftime("%Y-%m-%d")
    for i, t in enumerate(ts):
        ist = datetime.utcfromtimestamp(t + 19800)
        if ist.strftime("%Y-%m-%d") == today and ist.hour == 9 and ist.minute == 15:
            if q["high"][i] is not None:
                return round(float(q["high"][i]), 2)
    return None


def _warm_levels_yahoo():
    """Yahoo-la irundhu PDH/PDL/PWH — Angel fail aana idhu run agum."""
    today = _ist_now().strftime("%Y-%m-%d")
    ok = 0
    for sym in list(_load_tokens().keys()):
        if sym in _levels["pdh"]:
            continue
        try:
            v = _yf_levels(sym)
            if v:
                _levels["pdh"][sym], _levels["pdl"][sym], _levels["pwh"][sym] = v
                ok += 1
        except Exception as ex:
            if not _diag["sample_error"]:
                _diag["sample_error"] = f"yahoo {sym}: {str(ex)[:150]}"
        time.sleep(0.15)
    _diag["pdh_ok"] = len(_levels["pdh"])
    _diag["source"] = "yahoo" if ok else _diag.get("source", "")
    if _levels["pdh"]:
        _levels["day"] = today
    print(f"[levels/yahoo] {ok} symbols")


def _warm_or_yahoo():
    today = _ist_now().strftime("%Y-%m-%d")
    now = _ist_now()
    if now.hour < 9 or (now.hour == 9 and now.minute < 21):
        return
    ok = 0
    for sym in list(_load_tokens().keys()):
        if sym in _levels["orh"]:
            continue
        try:
            h = _yf_opening_high(sym)
            if h:
                _levels["orh"][sym] = h
                ok += 1
        except Exception:
            pass
        time.sleep(0.15)
    _diag["orh_ok"] = len(_levels["orh"])
    if _levels["orh"]:
        _levels["or_day"] = today
    print(f"[OR/yahoo] {ok} symbols")


# ───────── Global cues (gap direction proxy) ─────────
_global = {"rows": [], "ts": 0}
GLOBAL_TICKERS = [("GIFT/SGX proxy", "^NSEI"), ("DOW Fut", "YM=F"),
                  ("NASDAQ Fut", "NQ=F"), ("NIKKEI", "^N225"), ("CRUDE", "CL=F")]


def get_global_cues():
    if time.time() - _global["ts"] < 300 and _global["rows"]:
        return _global["rows"]
    out = []
    for name, tk in GLOBAL_TICKERS:
        try:
            d = _yf(tk, "5d", "1d")
            m = d["chart"]["result"][0]["meta"]
            px = m.get("regularMarketPrice")
            pc = m.get("chartPreviousClose") or m.get("previousClose")
            if px and pc:
                out.append({"name": name, "px": round(float(px), 2),
                            "chg": round((px - pc) / pc * 100, 2)})
        except Exception:
            pass
    if out:
        _global.update(rows=out, ts=time.time())
    return _global["rows"]


def _warm_levels():
    """Prev day high/low + prev week high — daily candles (day-ku oru dhadava)."""
    today = _ist_now().strftime("%Y-%m-%d")
    if _levels["day"] == today:
        return
    if not _has_creds():
        _diag["last_error"] = "no SMARTAPI credentials in env"
        return
    try:
        _diag["running"] = True
        _diag["started"] = time.strftime("%H:%M:%S", time.gmtime(time.time() + 19800))
        sc = _login()
        _diag["login"] = "ok"
        tmap = _load_tokens()
        frm = (_ist_now() - timedelta(days=20)).strftime("%Y-%m-%d 09:15")
        to = _ist_now().strftime("%Y-%m-%d 15:30")
        for sym, tok in tmap.items():
            try:
                r = sc.getCandleData({"exchange": "NSE", "symboltoken": tok,
                                      "interval": "ONE_DAY", "fromdate": frm, "todate": to})
                c = (r or {}).get("data") or []
                if len(c) < 2:
                    continue
                prev = c[-2] if c[-1][0][:10] == today else c[-1]
                _levels["pdh"][sym] = round(float(prev[2]), 2)
                _levels["pdl"][sym] = round(float(prev[3]), 2)
                # prev week high: kadaisi 5 completed sessions (today thavira)
                past = [x for x in c if x[0][:10] != today][-5:]
                if past:
                    _levels["pwh"][sym] = round(max(float(x[2]) for x in past), 2)
            except Exception as ex:
                if not _diag["sample_error"]:
                    _diag["sample_error"] = f"{sym}: {str(ex)[:200]}"
            time.sleep(0.35)          # Angel historical rate limit
        _diag["pdh_ok"] = len(_levels["pdh"])
        _diag["running"] = False
        if _levels["pdh"]:
            _levels["day"] = today
        print(f"[levels] PDH/PWH ready for {len(_levels['pdh'])} symbols")
    except Exception as e:
        _diag["running"] = False
        _diag["login"] = "failed"
        _diag["last_error"] = "warm_levels: " + str(e)[:200]
        print("warm levels error:", e)


def _warm_opening_range():
    """First 5-min candle high (9:15–9:20) — 9:21 apram oru dhadava."""
    now = _ist_now()
    today = now.strftime("%Y-%m-%d")
    if _levels["or_day"] == today or not _has_creds():
        return
    if now.hour < 9 or (now.hour == 9 and now.minute < 21):
        return
    try:
        sc = _login()
        tmap = _load_tokens()
        for sym, tok in tmap.items():
            try:
                r = sc.getCandleData({"exchange": "NSE", "symboltoken": tok,
                                      "interval": "FIVE_MINUTE",
                                      "fromdate": f"{today} 09:15",
                                      "todate": f"{today} 09:20"})
                c = (r or {}).get("data") or []
                if c:
                    _levels["orh"][sym] = round(float(c[0][2]), 2)
            except Exception as ex:
                if not _diag["sample_error"]:
                    _diag["sample_error"] = f"OR {sym}: {str(ex)[:200]}"
            time.sleep(0.35)
        _diag["orh_ok"] = len(_levels["orh"])
        if _levels["orh"]:
            _levels["or_day"] = today
        print(f"[levels] 5-min opening range ready for {len(_levels['orh'])} symbols")
    except Exception as e:
        _diag["last_error"] = "warm_OR: " + str(e)[:200]
        print("warm OR error:", e)


def _bg_worker():
    while True:
        try:
            _load_tokens()
            _warm_levels()
            if len(_levels["pdh"]) < 20:
                _warm_levels_yahoo()
            _warm_opening_range()
            if len(_levels["orh"]) < 20:
                _warm_or_yahoo()
        except Exception as e:
            print("bg worker error:", e)
        time.sleep(120)


threading.Thread(target=_bg_worker, daemon=True).start()


# ───────────────────────── dashboard ─────────────────────────
def _update_preopen(stocks):
    """
    Pre-open gap list.
      09:00–09:15 IST : IEP (indicative) vs prev close -> live gap
      09:15 apram     : open price vs prev close -> final gap (freeze)
    """
    now = _ist_now()
    today = now.strftime("%Y-%m-%d")
    mins = now.hour * 60 + now.minute
    if _preopen["day"] != today:
        _preopen.update(day=today, rows=[], final=False)

    def snap(price_key, final):
        out = []
        for r in stocks:
            close = r.get("close") or 0
            px = r.get(price_key) or 0
            if not close or not px:
                continue
            gap = (px - close) / close * 100
            if abs(gap) < 0.25:
                continue
            out.append({"symbol": r["symbol"], "sector": r.get("sector"),
                        "close": round(close, 2), "price": round(px, 2),
                        "gap": round(gap, 2), "gappts": round(px - close, 2)})
        out.sort(key=lambda x: x["gap"], reverse=True)
        _preopen.update(rows=out, final=final)

    if 540 <= mins < 555:            # 09:00–09:15 live pre-open
        snap("ltp", False)
    elif mins >= 555 and not _preopen["final"]:   # 09:15 apram — freeze with open price
        snap("open", True)


def _market_mood(stocks, indices):
    """FEAR / HAPPY / CONFUSED / GREED — breadth + VIX + index move."""
    if not stocks:
        return {"mood": "UNKNOWN", "emoji": "❓", "note": "no data", "breadth": 0}
    ups = sum(1 for r in stocks if r["chg"] > 0)
    breadth = round(ups / len(stocks) * 100, 1)
    vix = next((i for i in indices if "VIX" in i["symbol"]), None)
    nifty = next((i for i in indices if "NIFTY 50" in i["symbol"]), None)
    vix_chg = (vix or {}).get("chg", 0)
    nf = (nifty or {}).get("chg", 0)
    if breadth >= 65 and vix_chg <= 2:
        m, e, note = "HAPPY", "😀", "Broad buying — trend trades work"
    elif breadth <= 35 and vix_chg >= 3:
        m, e, note = "FEAR", "😱", "Panic selling — avoid fresh longs, tight SL"
    elif breadth <= 35:
        m, e, note = "WEAK", "😟", "Selling pressure — favour short setups"
    elif abs(nf) < 0.25 and 40 <= breadth <= 60:
        m, e, note = "CONFUSED", "😐", "Choppy / rangebound — fewer trades, wait for breakout"
    elif breadth >= 75 and vix_chg < 0:
        m, e, note = "GREED", "🤑", "Euphoria — trail SL, avoid chasing"
    else:
        m, e, note = "MIXED", "🙂", "Stock-specific market — follow strong sectors"
    return {"mood": m, "emoji": e, "note": note, "breadth": breadth,
            "vix_chg": vix_chg, "nifty_chg": nf}


def build_dashboard():
    rows, mode = get_quotes()
    indices = [r for r in rows if r["symbol"] in INDICES]
    stocks = [r for r in rows if r["symbol"] not in INDICES]

    # levels attach
    for r in stocks:
        s = r["symbol"]
        r["pdh"] = _levels["pdh"].get(s)
        r["pdl"] = _levels["pdl"].get(s)
        r["pwh"] = _levels["pwh"].get(s)
        r["orh"] = _levels["orh"].get(s)

    # ── self-built candles + real indicators ──
    try:
        IND.feed(stocks)
        IND.enrich(stocks)
        IND.update_tracker({r["symbol"]: r["ltp"] for r in stocks})
    except Exception as e:
        print("indicator error:", e)

    _update_preopen(stocks)

    gainers = sorted(stocks, key=lambda r: r["chg"], reverse=True)[:25]
    losers = sorted(stocks, key=lambda r: r["chg"])[:25]
    by_vol = sorted(stocks, key=lambda r: r.get("volume") or 0, reverse=True)[:15]

    # ── sector performance ──
    agg = {}
    for r in stocks:
        agg.setdefault(r["sector"], []).append(r)
    sectors = []
    for sec, lst in agg.items():
        avg = sum(x["chg"] for x in lst) / len(lst)
        best = max(lst, key=lambda x: x["chg"])
        worst = min(lst, key=lambda x: x["chg"])
        sectors.append({
            "sector": sec, "chg": round(avg, 2), "count": len(lst),
            "top": [{"symbol": x["symbol"], "chg": x["chg"], "ltp": x["ltp"]}
                    for x in sorted(lst, key=lambda y: y["chg"], reverse=True)[:3]],
            "weak": [{"symbol": x["symbol"], "chg": x["chg"], "ltp": x["ltp"]}
                     for x in sorted(lst, key=lambda y: y["chg"])[:3]],
            "best": best["symbol"], "worst": worst["symbol"],
        })
    sectors.sort(key=lambda s: s["chg"], reverse=True)

    # ── breakout lists ──
    pdh_break, pwh_break, or_break, pdl_break = [], [], [], []
    for r in stocks:
        ltp = r["ltp"]
        if r.get("pdh") and ltp > r["pdh"] and r["chg"] > 0:
            pdh_break.append(r)
        if r.get("pwh") and ltp > r["pwh"] and r["chg"] > 0:
            pwh_break.append(r)
        if r.get("orh") and ltp > r["orh"] and r["chg"] > 0:
            or_break.append(r)
        if r.get("pdl") and ltp < r["pdl"] and r["chg"] < 0:
            pdl_break.append(r)
    key = lambda x: x["chg"]
    pdh_break.sort(key=key, reverse=True); pwh_break.sort(key=key, reverse=True)
    or_break.sort(key=key, reverse=True); pdl_break.sort(key=key)

    # ── alerts ──
    alerts = []
    for r in stocks:
        if r["chg"] >= 4:
            alerts.append({"symbol": r["symbol"], "type": "BUY",
                           "reason": f"Strong momentum +{r['chg']}%", "chg": r["chg"]})
        if r["chg"] <= -3:
            alerts.append({"symbol": r["symbol"], "type": "DANGER",
                           "reason": f"Sharp fall {r['chg']}%", "chg": r["chg"]})
    alerts = alerts[:20]

    # ── market status ──
    n = _ist_now(); mins = n.hour * 60 + n.minute
    if mins < 555:
        mstat = {"state": "PRE", "text": "MARKET OPENS AT 09:15 AM",
                 "sub": "Pre-open 09:00 - 09:15"}
    elif mins <= 930:
        mstat = {"state": "OPEN", "text": "MARKET OPEN",
                 "sub": "09:15 AM - 03:30 PM"}
    else:
        mstat = {"state": "CLOSED", "text": "MARKET CLOSED",
                 "sub": "Next open: 09:15 AM"}

    # ── breadth ──
    adv = sum(1 for r in stocks if r["chg"] > 0)
    dec = sum(1 for r in stocks if r["chg"] < 0)
    unch = len(stocks) - adv - dec
    above_v = sum(1 for r in stocks if (r.get("ind") or {}).get("vwap") and r["ltp"] > r["ind"]["vwap"])
    with_v = sum(1 for r in stocks if (r.get("ind") or {}).get("vwap"))
    breadth = {"adv": adv, "dec": dec, "unch": unch,
               "above_vwap": round(above_v / with_v * 100, 1) if with_v else None,
               "below_vwap": round((1 - above_v / with_v) * 100, 1) if with_v else None,
               "bias": "Bullish" if adv > dec * 1.3 else "Bearish" if dec > adv * 1.3 else "Neutral"}

    # ── server-side signal generation (tracked even if browser closed) ──
    try:
        srank = {x["sector"]: i + 1 for i, x in enumerate(sectors)}
        for r in stocks:
            ind = r.get("ind") or {}
            tags, tech = IND.confirmations(r)
            if r["chg"] >= 1 and (r.get("volume") or 0) > 3e5:
                vol_b = 6 if (r.get("volume") or 0) > 1e7 else 0
                sc_ = 52 + min(24, round(r["chg"] * 5)) + tech + vol_b + (8 if srank.get(r["sector"], 99) <= 3 else 0)
                sl_ = r.get("sl_long") or round(r["ltp"] * 0.99, 2)
                t1_ = r.get("t1_long") or round(r["ltp"] * 1.01, 2)
                t2_ = r.get("t2_long") or round(r["ltp"] * 1.02, 2)
                t3_ = r.get("t3_long") or round(r["ltp"] * 1.035, 2)
                if sc_ >= 82:
                    IND.log_signal(r["symbol"], "BUY", r["ltp"], sl_, t1_, t2_, t3_,
                                   min(99, sc_), " + ".join(tags) or "Momentum", "JACKPOT")
            tags2, tech2 = IND.confirmations_short(r)
            if r["chg"] <= -1:
                vol_b2 = 6 if (r.get("volume") or 0) > 1e7 else 0
                sc2 = 52 + min(24, round(abs(r["chg"]) * 5)) + tech2 + vol_b2 + (8 if srank.get(r["sector"], 99) >= len(sectors) - 2 else 0)
                sl2 = r.get("sl_short") or round(r["ltp"] * 1.01, 2)
                t1s = r.get("t1_short") or round(r["ltp"] * 0.99, 2)
                t2s = r.get("t2_short") or round(r["ltp"] * 0.98, 2)
                if sc2 >= 82:
                    IND.log_signal(r["symbol"], "SELL", r["ltp"], sl2, t1s, t2s, None,
                                   min(99, sc2), " + ".join(tags2) or "Weak momentum", "DANGER")
    except Exception as e:
        print("signal gen error:", e)

    # ── ZONE SUGGESTIONS (buy zone / sell zone) ──
    zones = []
    try:
        srank2 = {x["sector"]: i + 1 for i, x in enumerate(sectors)}
        for r in stocks:
            ind = r.get("ind") or {}
            px = r.get("ltp") or 0
            hi = r.get("high") or px
            lo = r.get("low") or px
            if not px or hi <= lo:
                continue
            rng = hi - lo
            vwap = ind.get("vwap")
            atr = ind.get("atr") or rng * 0.25
            pos = (px - lo) / rng if rng else 0.5      # where in day range
            rk = srank2.get(r["sector"], 99)
            strong_sec = rk <= 3
            weak_sec = rk >= max(1, len(sectors) - 2)
            vol = r.get("volume") or 0

            # ---- BUY ZONE: uptrend stock pulling back to support ----
            if r["chg"] >= 0.8 and vol > 5e5:
                z_lo = round(max(lo, (vwap or lo)) * 0.999, 2)
                z_hi = round(min(px, max(lo, vwap or lo) * 1.006), 2)
                if z_hi <= z_lo:
                    z_lo, z_hi = round(px * 0.994, 2), round(px * 1.001, 2)
                atr = max(atr, px * 0.006, rng * 0.30)
                sl = round(z_lo - 1.2 * atr, 2)
                t1 = round(z_hi + 1.5 * atr, 2)
                t2 = round(z_hi + 2.5 * atr, 2)
                t3 = round(z_hi + 4.0 * atr, 2)
                score = 50 + min(20, round(r["chg"] * 4))
                why = []
                if strong_sec: score += 10; why.append("sector top-3")
                if vwap and px > vwap: score += 8; why.append("above VWAP")
                if pos >= 0.7: score += 6; why.append("near day high")
                if vol > 1e7: score += 6; why.append("heavy volume")
                if ind.get("rsi") and 55 <= ind["rsi"] <= 72: score += 6; why.append(f"RSI {ind['rsi']}")
                if ind.get("adx") and ind["adx"] >= 25: score += 5; why.append(f"ADX {ind['adx']}")
                score = min(99, score)
                zones.append({
                    "symbol": r["symbol"], "sector": r["sector"], "side": "BUY",
                    "ltp": px, "chg": r["chg"], "zone_lo": z_lo, "zone_hi": z_hi,
                    "sl": sl, "t1": t1, "t2": t2, "t3": t3, "score": score,
                    "sl_pct": round(abs(sl - px) / px * 100, 2),
                    "t1_pct": round(abs(t1 - px) / px * 100, 2),
                    "t2_pct": round(abs(t2 - px) / px * 100, 2),
                    "t3_pct": round(abs(t3 - px) / px * 100, 2),
                    "why": ", ".join(why) or "momentum",
                    "must": score >= 85 and strong_sec and bool(vwap and px > vwap),
                    "note": "Buy on dip into zone" if px > z_hi else "In zone now",
                })

            # ---- SELL ZONE: downtrend stock bouncing to resistance ----
            if r["chg"] <= -0.8 and vol > 5e5:
                z_hi = round(min(hi, (vwap or hi)) * 1.001, 2)
                z_lo = round(max(px, min(hi, vwap or hi) * 0.994), 2)
                if z_hi <= z_lo:
                    z_lo, z_hi = round(px * 0.999, 2), round(px * 1.006, 2)
                atr = max(atr, px * 0.006, rng * 0.30)
                sl = round(z_hi + 1.2 * atr, 2)
                t1 = round(z_lo - 1.5 * atr, 2)
                t2 = round(z_lo - 2.5 * atr, 2)
                t3 = round(z_lo - 4.0 * atr, 2)
                score = 50 + min(20, round(abs(r["chg"]) * 4))
                why = []
                if weak_sec: score += 10; why.append("weak sector")
                if vwap and px < vwap: score += 8; why.append("below VWAP")
                if pos <= 0.3: score += 6; why.append("near day low")
                if vol > 1e7: score += 6; why.append("heavy selling volume")
                if ind.get("rsi") and ind["rsi"] <= 45: score += 6; why.append(f"RSI {ind['rsi']}")
                if ind.get("adx") and ind["adx"] >= 25: score += 5; why.append(f"ADX {ind['adx']}")
                score = min(99, score)
                zones.append({
                    "symbol": r["symbol"], "sector": r["sector"], "side": "SELL",
                    "ltp": px, "chg": r["chg"], "zone_lo": z_lo, "zone_hi": z_hi,
                    "sl": sl, "t1": t1, "t2": t2, "t3": t3, "score": score,
                    "sl_pct": round(abs(sl - px) / px * 100, 2),
                    "t1_pct": round(abs(t1 - px) / px * 100, 2),
                    "t2_pct": round(abs(t2 - px) / px * 100, 2),
                    "t3_pct": round(abs(t3 - px) / px * 100, 2),
                    "why": ", ".join(why) or "weak momentum",
                    "must": score >= 85 and weak_sec and bool(vwap and px < vwap),
                    "note": "Sell on bounce into zone" if px < z_lo else "In zone now",
                })
        zones.sort(key=lambda z: (-int(z["must"]), -z["score"]))
    except Exception as e:
        print("zone error:", e)

    # ── CALL OF THE DAY (single best conviction pick + option strikes) ──
    def _strike_step(p):
        if p < 200: return 5
        if p < 500: return 10
        if p < 1000: return 20
        if p < 2500: return 50
        if p < 5000: return 100
        return 250

    call_day = None
    try:
        pool = [z for z in zones if z.get("must")] or zones[:5]
        if pool:
            best = max(pool, key=lambda z: z["score"])
            px = best["ltp"]; step = _strike_step(px)
            atm = round(px / step) * step
            if best["side"] == "BUY":
                strikes = [{"strike": int(atm), "type": "CE", "label": "ATM"},
                           {"strike": int(atm + step), "type": "CE", "label": "OTM 1"},
                           {"strike": int(atm + 2 * step), "type": "CE", "label": "OTM 2"}]
                view = "Bullish — CE side"
            else:
                strikes = [{"strike": int(atm), "type": "PE", "label": "ATM"},
                           {"strike": int(atm - step), "type": "PE", "label": "OTM 1"},
                           {"strike": int(atm - 2 * step), "type": "PE", "label": "OTM 2"}]
                view = "Bearish — PE side"
            call_day = {**best, "view": view, "strikes": strikes, "atm": int(atm),
                        "step": step,
                        "plan": ("Enter only when price trades inside the zone. "
                                 "Book part at T1, trail rest. Exit all if SL breaks.")}
    except Exception as e:
        print("call of day error:", e)

    # ── opening-range break lists from own candles ──
    or5, or15 = [], []
    for r in stocks:
        ind = r.get("ind") or {}
        if ind.get("or5h") and r["ltp"] > ind["or5h"] and r["chg"] > 0:
            or5.append({**{k: r[k] for k in ("symbol", "ltp", "chg", "volume", "sector")},
                        "level": ind["or5h"], "dir": "up"})
        if ind.get("or15h") and r["ltp"] > ind["or15h"] and r["chg"] > 0:
            or15.append({**{k: r[k] for k in ("symbol", "ltp", "chg", "volume", "sector")},
                         "level": ind["or15h"], "dir": "up"})
    or5.sort(key=lambda x: -x["chg"]); or15.sort(key=lambda x: -x["chg"])

    return {
        "status": mstat, "breadth": breadth,
        "or5": or5[:12], "or15": or15[:12],
        "mode": mode, "indices": indices, "gainers": gainers, "losers": losers,
        "volume": by_vol, "alerts": alerts, "sectors": sectors,
        "breaks": {"pdh": pdh_break[:12], "pwh": pwh_break[:12],
                   "or5": or_break[:12], "pdl": pdl_break[:12]},
        "preopen": {"up": [x for x in _preopen["rows"] if x["gap"] > 0][:12],
                    "down": [x for x in _preopen["rows"] if x["gap"] < 0][:12],
                    "final": _preopen["final"], "count": len(_preopen["rows"])},
        "mood": _market_mood(stocks, indices),
        "global": get_global_cues(),
        "zones": zones[:14],
        "call_day": call_day,
        "tracker": IND.stats(),
        "ind_ready": sum(1 for r in stocks if (r.get("ind") or {}).get("ready")),
        "levels_ready": bool(_levels["pdh"]),
        "levels_diag": {**_diag, "pdh": len(_levels["pdh"]), "pwh": len(_levels["pwh"]),
                        "orh": len(_levels["orh"])},
        "universe": len(stocks),
        "updated": time.strftime("%H:%M:%S", time.gmtime(time.time() + 19800)),
    }
