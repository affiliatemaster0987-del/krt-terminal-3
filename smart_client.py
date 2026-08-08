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
    "AUBANK": "BANK", "RBLBANK": "BANK",
    # PSU BANK
    "SBIN": "PSU BANK", "BANKBARODA": "PSU BANK", "PNB": "PSU BANK",
    "CANBK": "PSU BANK", "UNIONBANK": "PSU BANK", "INDIANB": "PSU BANK",
    # NBFC / FIN
    "BAJFINANCE": "FINANCE", "BAJAJFINSV": "FINANCE", "CHOLAFIN": "FINANCE",
    "SHRIRAMFIN": "FINANCE", "LICHSGFIN": "FINANCE", "MUTHOOTFIN": "FINANCE",
    "PFC": "FINANCE", "RECLTD": "FINANCE", "HDFCLIFE": "FINANCE", "SBILIFE": "FINANCE",
    "ICICIGI": "FINANCE", "ICICIPRULI": "FINANCE", "LTF": "FINANCE", "ABCAPITAL": "FINANCE",
    # AUTO
    "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "M&M": "AUTO", "BAJAJ-AUTO": "AUTO",
    "HEROMOTOCO": "AUTO", "EICHERMOT": "AUTO", "TVSMOTOR": "AUTO", "ASHOKLEY": "AUTO",
    "MOTHERSON": "AUTO", "BOSCHLTD": "AUTO", "BHARATFORG": "AUTO", "SONACOMS": "AUTO",
    "EXIDEIND": "AUTO", "BALKRISIND": "AUTO", "MRF": "AUTO", "APOLLOTYRE": "AUTO",
    # ENERGY / OIL
    "RELIANCE": "ENERGY", "ONGC": "ENERGY", "IOC": "ENERGY", "BPCL": "ENERGY",
    "HINDPETRO": "ENERGY", "GAIL": "ENERGY", "OIL": "ENERGY", "PETRONET": "ENERGY",
    # POWER
    "NTPC": "POWER", "POWERGRID": "POWER", "TATAPOWER": "POWER", "ADANIPOWER": "POWER",
    "ADANIGREEN": "POWER", "NHPC": "POWER", "SJVN": "POWER", "TORNTPOWER": "POWER",
    # METAL
    "TATASTEEL": "METAL", "JSWSTEEL": "METAL", "HINDALCO": "METAL", "VEDL": "METAL",
    "JINDALSTEL": "METAL", "SAIL": "METAL", "NMDC": "METAL", "NATIONALUM": "METAL",
    "APLAPOLLO": "METAL", "HINDZINC": "METAL",
    # PHARMA
    "SUNPHARMA": "PHARMA", "CIPLA": "PHARMA", "DRREDDY": "PHARMA", "DIVISLAB": "PHARMA",
    "AUROPHARMA": "PHARMA", "LUPIN": "PHARMA", "ALKEM": "PHARMA", "TORNTPHARM": "PHARMA",
    "ZYDUSLIFE": "PHARMA", "GLENMARK": "PHARMA", "BIOCON": "PHARMA", "LAURUSLABS": "PHARMA",
    "MANKIND": "PHARMA", "ABBOTINDIA": "PHARMA",
    # HEALTHCARE
    "APOLLOHOSP": "HEALTHCARE", "MAXHEALTH": "HEALTHCARE", "FORTIS": "HEALTHCARE",
    "SYNGENE": "HEALTHCARE",
    # FMCG
    "ITC": "FMCG", "HINDUNILVR": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG",
    "DABUR": "FMCG", "MARICO": "FMCG", "GODREJCP": "FMCG", "COLPAL": "FMCG",
    "TATACONSUM": "FMCG", "VBL": "FMCG", "UBL": "FMCG", "PGHH": "FMCG",
    # DEFENCE / PSU
    "BEL": "DEFENCE", "HAL": "DEFENCE", "BDL": "DEFENCE", "MAZDOCK": "DEFENCE",
    "COCHINSHIP": "DEFENCE", "GRSE": "DEFENCE", "BHEL": "DEFENCE",
    # INFRA / CAPITAL GOODS
    "LT": "INFRA", "SIEMENS": "INFRA", "ABB": "INFRA", "CUMMINSIND": "INFRA",
    "THERMAX": "INFRA", "POLYCAB": "INFRA", "HAVELLS": "INFRA", "KEI": "INFRA",
    "RVNL": "INFRA", "IRFC": "INFRA", "IRCTC": "INFRA", "CONCOR": "INFRA",
    "ADANIPORTS": "INFRA", "GMRAIRPORT": "INFRA", "NBCC": "INFRA", "NCC": "INFRA",
    # CEMENT
    "ULTRACEMCO": "CEMENT", "GRASIM": "CEMENT", "SHREECEM": "CEMENT",
    "AMBUJACEM": "CEMENT", "ACC": "CEMENT", "DALBHARAT": "CEMENT", "JKCEMENT": "CEMENT",
    # REALTY
    "DLF": "REALTY", "GODREJPROP": "REALTY", "OBEROIRLTY": "REALTY",
    "PRESTIGE": "REALTY", "LODHA": "REALTY", "PHOENIXLTD": "REALTY",
    # CONSUMER / RETAIL
    "TITAN": "CONSUMER", "TRENT": "CONSUMER", "DMART": "CONSUMER", "JUBLFOOD": "CONSUMER",
    "PAGEIND": "CONSUMER", "VOLTAS": "CONSUMER", "BLUESTARCO": "CONSUMER",
    "DIXON": "CONSUMER", "CROMPTON": "CONSUMER", "WHIRLPOOL": "CONSUMER",
    "CGCONSUMER": "CONSUMER", "PGEL": "CONSUMER", "KALYANKJIL": "CONSUMER",
    # CHEMICAL
    "PIDILITIND": "CHEMICAL", "SRF": "CHEMICAL", "UPL": "CHEMICAL", "TATACHEM": "CHEMICAL",
    "DEEPAKNTR": "CHEMICAL", "AARTIIND": "CHEMICAL", "PIIND": "CHEMICAL",
    "ASIANPAINT": "CHEMICAL", "BERGEPAINT": "CHEMICAL",
    # TELECOM / MEDIA
    "BHARTIARTL": "TELECOM", "IDEA": "TELECOM", "INDUSTOWER": "TELECOM",
    "TATACOMM": "TELECOM", "ZEEL": "MEDIA", "PVRINOX": "MEDIA", "SUNTV": "MEDIA",
    # NEW AGE
    "ZOMATO": "NEW AGE", "SWIGGY": "NEW AGE", "PAYTM": "NEW AGE", "NYKAA": "NEW AGE",
    "POLICYBZR": "NEW AGE", "DELHIVERY": "NEW AGE",
    # DIVERSIFIED
    "ADANIENT": "DIVERSIFIED", "JSWENERGY": "DIVERSIFIED", "SIEMENSENGY": "DIVERSIFIED",
    "INDHOTEL": "HOTELS", "IGL": "GAS", "MGL": "GAS", "GUJGASLTD": "GAS",
}

SCRIP_MASTER_URL = ("https://margincalculator.angelbroking.com/OpenAPI_File/"
                    "files/OpenAPIScripMaster.json")

_tokens = {}          # symbol -> token
_tokens_ready = False
_cache = {"data": None, "ts": 0, "mode": "demo"}
_levels = {"pdh": {}, "pdl": {}, "pwh": {}, "orh": {}, "day": "", "or_day": ""}
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
        print(f"[scrip master] resolved {len(found)}/{len(want)} tokens")
    except Exception as e:
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


def _warm_levels():
    """Prev day high/low + prev week high — daily candles-la irundhu (day-ku oru dhadava)."""
    today = _ist_now().strftime("%Y-%m-%d")
    if _levels["day"] == today or not _has_creds():
        return
    try:
        sc = _login()
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
            except Exception:
                pass
            time.sleep(0.35)          # Angel historical rate limit
        _levels["day"] = today
        print(f"[levels] PDH/PWH ready for {len(_levels['pdh'])} symbols")
    except Exception as e:
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
            except Exception:
                pass
            time.sleep(0.35)
        _levels["or_day"] = today
        print(f"[levels] 5-min opening range ready for {len(_levels['orh'])} symbols")
    except Exception as e:
        print("warm OR error:", e)


def _bg_worker():
    while True:
        try:
            _load_tokens()
            _warm_levels()
            _warm_opening_range()
        except Exception as e:
            print("bg worker error:", e)
        time.sleep(120)


threading.Thread(target=_bg_worker, daemon=True).start()


# ───────────────────────── dashboard ─────────────────────────
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

    return {
        "mode": mode, "indices": indices, "gainers": gainers, "losers": losers,
        "volume": by_vol, "alerts": alerts, "sectors": sectors,
        "breaks": {"pdh": pdh_break[:12], "pwh": pwh_break[:12],
                   "or5": or_break[:12], "pdl": pdl_break[:12]},
        "levels_ready": bool(_levels["pdh"]),
        "universe": len(stocks),
        "updated": time.strftime("%H:%M:%S", time.gmtime(time.time() + 19800)),
    }
