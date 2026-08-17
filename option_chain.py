"""
KRT — Option Chain engine (Angel One SmartAPI)
-----------------------------------------------
• PCR (put/call OI ratio)
• Max Pain
• Support / Resistance strikes (highest OI)
• OI build-up read: LONG BUILDUP / SHORT BUILDUP / SHORT COVERING / LONG UNWINDING
• Writer bias -> confirms or blocks price signals

Angel credentials illa-na silent-a skip agum (terminal appadiye work agum).
"""
import os, time, threading, json
import urllib.request
from datetime import datetime, timedelta

_lock = threading.Lock()
_cache = {}          # sym -> {"ts":, "data":}
CACHE_SEC = 420          # 7 min — chain moves slowly, saves API load      # option chain 3 min-ku oru dhadava podhum
_master = {"rows": [], "ts": 0, "loading": False}

SCRIP_MASTER_URL = ("https://margincalculator.angelbroking.com/OpenAPI_File/"
                    "files/OpenAPIScripMaster.json")


def _ist():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


def _has_creds():
    return all(os.environ.get(k) for k in
               ("SMARTAPI_KEY", "SMARTAPI_CLIENT", "SMARTAPI_PIN", "SMARTAPI_TOTP"))


# ───────── option instrument master ─────────
def _load_master(blocking=False):
    """Master file ~150MB — request-kulla download panna dashboard hang aagum.
    Default-a non-blocking: background thread download pannum, request udane
    return aagum (chain andha poll-la illa, adutha poll-la varum)."""
    if _master["rows"] and time.time() - _master["ts"] < 86400:
        return _master["rows"]
    if not blocking:
        if not _master["loading"]:
            _master["loading"] = True
            threading.Thread(target=lambda: _load_master(blocking=True),
                             daemon=True).start()
        return _master["rows"]          # [] until the download finishes
    try:
        req = urllib.request.Request(SCRIP_MASTER_URL, headers={"User-Agent": "KRT"})
        with urllib.request.urlopen(req, timeout=60) as r:
            rows = json.loads(r.read().decode())
        opts = [x for x in rows if x.get("exch_seg") == "NFO"
                and x.get("instrumenttype") in ("OPTSTK", "OPTIDX")]
        _master.update(rows=opts, ts=time.time())
        print(f"[optchain] master loaded: {len(opts)} option contracts")
    except Exception as e:
        print("[optchain] master error:", e)
    _master["loading"] = False
    return _master["rows"]


def _nearest_expiry(sym):
    rows = [x for x in _load_master() if x.get("name") == sym]
    if not rows:
        return None, []
    today = _ist().date()
    exps = set()
    for x in rows:
        try:
            d = datetime.strptime(x["expiry"], "%d%b%Y").date()
            if d >= today:
                exps.add(d)
        except Exception:
            pass
    if not exps:
        return None, []
    exp = min(exps)
    tag = exp.strftime("%d%b%Y").upper()
    return tag, [x for x in rows if x.get("expiry", "").upper() == tag]


# ───────── chain fetch ─────────
def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def get_chain(sym, spot, sc=None):
    """Returns option-chain read for one symbol. None if unavailable."""
    with _lock:
        c = _cache.get(sym)
        if c and time.time() - c["ts"] < CACHE_SEC:
            return c["data"]
    if not _has_creds() or not spot:
        return None
    try:
        if sc is None:
            from smart_client import _login
            sc = _login()
        if sc is None:
            return None
        tag, rows = _nearest_expiry(sym)
        if not rows:
            return None
        # keep strikes within +/-10% of spot
        picked = []
        for x in rows:
            try:
                strike = float(x["strike"]) / 100.0
            except Exception:
                continue
            if abs(strike - spot) / spot <= 0.06:
                picked.append((strike, x))
        if not picked:
            return None
        tokens = [x["token"] for _, x in picked][:60]
        fetched = []
        for grp in _chunks(tokens, 50):
            try:
                resp = sc.getMarketData("FULL", {"NFO": grp})
                fetched += (resp.get("data", {}).get("fetched", []) if resp else [])
            except Exception as e:
                print("[optchain] md error:", e)
            time.sleep(0.25)
        by_tok = {str(r.get("symbolToken")): r for r in fetched}

        calls, puts = {}, {}
        for strike, x in picked:
            row = by_tok.get(str(x["token"]))
            if not row:
                continue
            oi = float(row.get("opnInterest") or 0)
            ltp = float(row.get("ltp") or 0)
            chg = float(row.get("netChange") or 0)
            vol = float(row.get("tradeVolume") or 0)
            side = "CE" if str(x.get("symbol", "")).endswith("CE") else "PE"
            (calls if side == "CE" else puts)[strike] = {
                "oi": oi, "ltp": round(ltp, 2), "chg": chg, "vol": vol}

        if not calls or not puts:
            return None

        tot_ce = sum(v["oi"] for v in calls.values())
        tot_pe = sum(v["oi"] for v in puts.values())
        pcr = round(tot_pe / tot_ce, 2) if tot_ce else None

        res_strike = max(calls, key=lambda k: calls[k]["oi"]) if calls else None
        sup_strike = max(puts, key=lambda k: puts[k]["oi"]) if puts else None

        # max pain
        strikes = sorted(set(list(calls) + list(puts)))
        pain, best = None, None
        for s in strikes:
            loss = 0
            for k, v in calls.items():
                if s > k:
                    loss += (s - k) * v["oi"]
            for k, v in puts.items():
                if s < k:
                    loss += (k - s) * v["oi"]
            if best is None or loss < best:
                best, pain = loss, s

        # writer bias near ATM (3 strikes each side)
        atm = min(strikes, key=lambda k: abs(k - spot))
        near = [s for s in strikes if abs(s - atm) <= 3 * (strikes[1] - strikes[0] if len(strikes) > 1 else 1)]
        ce_chg = sum(calls.get(s, {}).get("chg", 0) for s in near)
        pe_chg = sum(puts.get(s, {}).get("chg", 0) for s in near)
        ce_oi = sum(calls.get(s, {}).get("oi", 0) for s in near)
        pe_oi = sum(puts.get(s, {}).get("oi", 0) for s in near)

        if pe_oi > ce_oi * 1.15:
            writer = "PUT WRITING"; bias = "BULLISH"
        elif ce_oi > pe_oi * 1.15:
            writer = "CALL WRITING"; bias = "BEARISH"
        else:
            writer = "BALANCED"; bias = "NEUTRAL"

        data = {
            "symbol": sym, "expiry": tag, "spot": round(spot, 2), "atm": atm,
            "pcr": pcr, "max_pain": pain,
            "support": sup_strike, "resistance": res_strike,
            "writer": writer, "bias": bias,
            "ce_oi": int(ce_oi), "pe_oi": int(pe_oi),
            "atm_ce": calls.get(atm, {}).get("ltp"), "atm_pe": puts.get(atm, {}).get("ltp"),
            "strikes_ce": {str(k): v for k, v in calls.items()},
            "strikes_pe": {str(k): v for k, v in puts.items()},
            "step": (strikes[1] - strikes[0]) if len(strikes) > 1 else None,
            "updated": _ist().strftime("%H:%M:%S"),
        }
        with _lock:
            _cache[sym] = {"ts": time.time(), "data": data}
        return data
    except Exception as e:
        print("[optchain] error", sym, e)
        return None


def confirm(sym, spot, side):
    """
    Price signal + option chain agree-aa?
    returns (score_delta, tag, chain)
    """
    ch = get_chain(sym, spot)
    if not ch:
        return 0, None, None
    if side == "BUY":
        if ch["bias"] == "BULLISH":
            return 12, f"OI: {ch['writer']} (PCR {ch['pcr']})", ch
        if ch["bias"] == "BEARISH":
            return -15, f"OI blocks: {ch['writer']}", ch
    else:
        if ch["bias"] == "BEARISH":
            return 12, f"OI: {ch['writer']} (PCR {ch['pcr']})", ch
        if ch["bias"] == "BULLISH":
            return -15, f"OI blocks: {ch['writer']}", ch
    return 0, f"OI balanced (PCR {ch['pcr']})", ch


def strike_quote(chain, strike, side):
    """Premium + OI for a specific strike from an already-fetched chain."""
    if not chain:
        return None
    book = chain.get("strikes_ce" if side == "CE" else "strikes_pe") or {}
    for k in (str(strike), str(float(strike)), str(int(strike))):
        if k in book:
            q = book[k]
            return {"strike": float(k), "type": side, "ltp": q.get("ltp"),
                    "oi": q.get("oi"), "chg": q.get("chg")}
    return None


def est_delta(spot, strike, side, step):
    """Rough delta by moneyness — enough for premium target maths."""
    if not step:
        step = max(spot * 0.005, 1)
    steps_otm = ((strike - spot) / step) if side == "CE" else ((spot - strike) / step)
    if steps_otm <= -1.5: return 0.80      # deep ITM
    if steps_otm <= -0.5: return 0.65
    if steps_otm < 0.5:   return 0.50      # ATM
    if steps_otm < 1.5:   return 0.35
    if steps_otm < 2.5:   return 0.22
    return 0.14
