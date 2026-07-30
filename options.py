"""
KRT JACKPOTS — Options engine
Scanner/News signal → Bullish/Bearish confirm → CE/PE → ATM strike →
Entry zone / Targets / SL (premium % based).

Premium data:
  LIVE : Angel One instrument master-லேர்ந்து option token கண்டுபிடிச்சு LTP fetch
         (OPTIONS_LIVE=1 env var வெச்சா மட்டும் — free Render-ல memory காக்க default off)
  EST  : premium estimate (spot ~1.2% ATM rule) — "est." tag-ஓட காட்டும்
"""
import os, re, time, threading, datetime, urllib.request

import smart_client

STRIKE_STEP = {
    "RELIANCE": 10, "TCS": 20, "HDFCBANK": 10, "INFY": 10, "SBIN": 5,
    "ICICIBANK": 10, "ITC": 5, "TATAMOTORS": 5, "BEL": 5, "VBL": 5,
}

MASTER_URL = ("https://margincalculator.angelbroking.com/"
              "OpenAPI_File/files/OpenAPIScripMaster.json")

_opt_cache = {"tokens": {}, "date": None}
_lock = threading.Lock()


# ---------------- instrument master (optional, env-gated) ----------------
def _load_option_tokens():
    """Stream-scan the big instrument master; keep only NFO options
    for our watchlist symbols. Memory-safe chunk parsing."""
    names = set(STRIKE_STEP.keys())
    tokens = {}
    req = urllib.request.Request(MASTER_URL, headers={"User-Agent": "Mozilla/5.0"})
    buf = ""
    pat = re.compile(
        r'"token":"(\d+)".*?"symbol":"([A-Z0-9]+)(\d{2}[A-Z]{3}\d{2})(\d+)(CE|PE)"'
        r'.*?"name":"([A-Z0-9]+)".*?"expiry":"([0-9A-Z]+)".*?"strike":"([\d.]+)"',
        re.S)
    with urllib.request.urlopen(req, timeout=120) as r:
        while True:
            chunk = r.read(1 << 20).decode("utf-8", "ignore")
            if not chunk:
                break
            buf += chunk
            parts = buf.split("},{")
            buf = parts.pop()          # incomplete tail
            for p in parts:
                if '"exch_seg":"NFO"' not in p:
                    continue
                m = pat.search("{" + p + "}")
                if not m:
                    continue
                tok, _sym, _exp2, _strk, cepe, name, expiry, strike = m.groups()
                if name not in names:
                    continue
                key = (name, round(float(strike) / 100), cepe)
                tokens.setdefault(key, []).append(
                    {"token": tok, "expiry": expiry})
    # ஒவ்வொரு strike-க்கும் nearest expiry மட்டும்
    def exp_date(e):
        try:
            return datetime.datetime.strptime(e, "%d%b%Y")
        except Exception:
            return datetime.datetime.max
    slim = {}
    for k, lst in tokens.items():
        lst.sort(key=lambda x: exp_date(x["expiry"]))
        slim[k] = lst[0]
    return slim


def _get_tokens():
    if os.environ.get("OPTIONS_LIVE") != "1":
        return {}
    with _lock:
        today = datetime.date.today().isoformat()
        if _opt_cache["date"] == today:
            return _opt_cache["tokens"]
        try:
            _opt_cache.update(tokens=_load_option_tokens(), date=today)
            print("option tokens loaded:", len(_opt_cache["tokens"]))
        except Exception as e:
            print("instrument master error:", e)
            _opt_cache.update(tokens={}, date=today)
        return _opt_cache["tokens"]


def _option_ltp(symbol, strike, cepe):
    """Live premium via Market Data API — token கிடைச்சா மட்டும்."""
    info = _get_tokens().get((symbol, strike, cepe))
    if not info:
        return None, None
    try:
        sc = smart_client._login()
        resp = sc.getMarketData("LTP", {"NFO": [info["token"]]})
        rows = (resp or {}).get("data", {}).get("fetched", [])
        if rows:
            return float(rows[0]["ltp"]), info["expiry"]
    except Exception as e:
        print("option ltp error:", e)
    return None, info.get("expiry")


# ---------------- jackpot call builder ----------------
def build_option_call(symbol, side, spot, confidence):
    """side: BUY → CE, SELL → PE. Returns jackpot option call dict or None."""
    step = STRIKE_STEP.get(symbol)
    if not step or not spot:
        return None
    cepe = "CE" if side == "BUY" else "PE"
    atm = round(spot / step) * step
    strike = int(atm)                      # ATM default (liquidity best)

    prem, expiry = _option_ltp(symbol, strike, cepe)
    src = "live"
    if prem is None:
        prem = round(max(1.0, spot * 0.012), 1)   # rough ATM premium estimate
        src = "est"
    entry_lo = round(prem * 0.97, 1)
    entry_hi = round(prem * 1.03, 1)
    return {
        "instrument": f"{symbol} {strike} {cepe}",
        "symbol": symbol, "strike": strike, "type": cepe,
        "expiry": expiry or "nearest",
        "spot": round(spot, 1),
        "premium": round(prem, 1), "prem_src": src,
        "entry": f"{entry_lo} – {entry_hi}",
        "t1": round(prem * 1.25, 1),
        "t2": round(prem * 1.50, 1),
        "t3": round(prem * 1.80, 1),
        "sl": round(prem * 0.80, 1),
        "rr": "1 : 2.5",
        "confidence": confidence,
        "note": ("ATM strike — best liquidity"
                 if src == "live" else
                 "Premium estimate (est.) — live option data connect ஆனதும் exact ஆகும்"),
    }
