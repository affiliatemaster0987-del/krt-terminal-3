"""
KRT — News AI 3.0
RSS feeds poll pannum (Moneycontrol / ET / Reuters India), ovvoru headline-ayum
tag pannum: STRONG POSITIVE / POSITIVE / NEUTRAL / NEGATIVE / CRASH RISK
War, geopolitical, crash keywords -> immediate CRASH ALERT.
No API key needed.
"""
import time, threading, re
import urllib.request
import xml.etree.ElementTree as ET

FEEDS = [
    ("Moneycontrol", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("Moneycontrol Biz", "https://www.moneycontrol.com/rss/business.xml"),
    ("ET Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("ET World", "https://economictimes.indiatimes.com/news/international/rssfeeds/1898055174.cms"),
]

# ───────────── keyword banks ─────────────
STRONG_POS = ["record high", "all-time high", "order win", "bags order", "wins contract",
              "wins order", "profit surges", "profit jumps", "beats estimates",
              "rate cut", "buyback", "stake buy", "upgrade to buy", "multibagger",
              "bonus issue", "merger approved", "approval granted", "new high"]
POS_WORDS = ["surge", "rally", "beats", "beat", "profit rises", "jumps", "gains",
             "upgrade", "dividend", "strong", "growth", "soars", "expansion",
             "hikes target", "outperform", "revival", "recovery", "inflows"]
NEG_WORDS = ["falls", "drops", "misses", "miss", "downgrade", "loss", "weak",
             "slump", "probe", "penalty", "default", "tanks", "cuts guidance",
             "resigns", "strike", "ban", "fraud", "raid", "outflows", "sell-off"]
# ⚠ crash / geopolitical — highest priority
CRASH_WORDS = ["war", "attack", "missile", "strike on", "invasion", "airstrike",
               "nuclear", "terror", "iran", "israel", "russia ukraine", "conflict",
               "crash", "plunge", "bloodbath", "circuit breaker", "meltdown",
               "recession", "emergency", "collapse", "tariff war", "trade war",
               "oil spike", "crude spikes", "bans exports", "sanctions",
               "market crash", "panic selling", "black monday"]

STOCK_KEYWORDS = ["RELIANCE", "TCS", "HDFC", "INFOSYS", "INFY", "SBI", "ICICI", "ITC",
                  "TATA MOTORS", "TATA STEEL", "BEL", "HAL", "VARUN", "VBL", "ADANI",
                  "NIFTY", "SENSEX", "BANK", "MARUTI", "AXIS", "KOTAK", "WIPRO",
                  "BAJAJ", "LT", "SUN PHARMA", "CIPLA", "TITAN", "TRENT", "ZOMATO",
                  "SWIGGY", "PAYTM", "NTPC", "ONGC", "COAL INDIA", "POWER GRID",
                  "MOTHERSON", "AUROBINDO", "FORTIS", "HINDALCO", "GRASIM", "DIXON"]

_news_cache = {"items": [], "ts": 0}
_lock = threading.Lock()
POLL_SECONDS = 45


def _classify(title):
    """returns (tag, impact 1-10)"""
    t = title.lower()
    crash = sum(1 for w in CRASH_WORDS if w in t)
    spos = sum(1 for w in STRONG_POS if w in t)
    pos = sum(1 for w in POS_WORDS if w in t)
    neg = sum(1 for w in NEG_WORDS if w in t)
    if crash:
        return "CRASH RISK", min(10, 8 + crash)
    if spos:
        return "STRONG POSITIVE", min(10, 8 + spos)
    if pos > neg:
        return "POSITIVE", min(9, 5 + pos * 2)
    if neg > pos:
        return "NEGATIVE", min(9, 5 + neg * 2)
    return "NEUTRAL", 3


def _affected(title):
    up = title.upper()
    return [s for s in STOCK_KEYWORDS if s in up][:4]


def _fetch_feed(source, url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 KRT-Terminal"})
    with urllib.request.urlopen(req, timeout=10) as r:
        xml = r.read()
    root = ET.fromstring(xml)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if not title:
            continue
        tag, impact = _classify(title)
        out.append({"source": source, "title": title, "link": link,
                    "time": pub[:22], "tag": tag, "impact": impact,
                    "stocks": _affected(title)})
    return out[:12]


_ORDER = {"CRASH RISK": 0, "STRONG POSITIVE": 1, "NEGATIVE": 2,
          "POSITIVE": 3, "NEUTRAL": 4}


def get_news():
    """Cached, merged, de-duplicated news (max 20). Crash/strong news mudhal-la."""
    with _lock:
        now = time.time()
        if _news_cache["items"] and now - _news_cache["ts"] < POLL_SECONDS:
            return _news_cache["items"]
        items, seen = [], set()
        for source, url in FEEDS:
            try:
                for it in _fetch_feed(source, url):
                    key = re.sub(r"\W+", "", it["title"].lower())[:60]
                    if key in seen:
                        continue
                    seen.add(key)
                    items.append(it)
            except Exception as e:
                print("news feed error:", source, e)
        items.sort(key=lambda x: (_ORDER.get(x["tag"], 5), -x["impact"]))
        if items:
            _news_cache.update(items=items[:20], ts=now)
        return _news_cache["items"]


# ───────────── News-based JACKPOT + CRASH signals ─────────────
_ALIAS = {"INFOSYS": "INFY", "HDFC": "HDFCBANK", "ICICI": "ICICIBANK", "SBI": "SBIN",
          "TATA MOTORS": "TATAMOTORS", "TATA STEEL": "TATASTEEL", "VARUN": "VBL",
          "AXIS": "AXISBANK", "KOTAK": "KOTAKBANK", "SUN PHARMA": "SUNPHARMA",
          "COAL INDIA": "COALINDIA", "POWER GRID": "POWERGRID", "AUROBINDO": "AUROPHARMA"}


def get_news_signals():
    """
    returns {"jackpot": [...], "danger": [...], "market_crash": [...]}
      jackpot      = positive/strong-positive news + stock match
      danger       = negative news + stock match
      market_crash = war / geopolitical / crash headlines (whole market risk)
    """
    jackpot, danger, crash = [], [], []
    smap = {}
    try:
        from smart_client import build_dashboard
        d = build_dashboard()
        for r in (d.get("gainers", []) + d.get("losers", []) + d.get("volume", [])):
            smap[r["symbol"]] = r
    except Exception as e:
        print("news signals quote error:", e)

    for n in get_news():
        tag = n["tag"]
        if tag == "CRASH RISK":
            crash.append({"headline": n["title"][:120], "impact": n["impact"],
                          "source": n["source"], "link": n.get("link", ""),
                          "action": "⚠ MARKET CRASH RISK — புது long வேண்டாம், SL tight"})
            continue
        for st in n.get("stocks", []):
            sym = _ALIAS.get(st, st)
            me = smap.get(sym)
            row = {"symbol": sym, "headline": n["title"][:110], "impact": n["impact"],
                   "tag": tag, "chg": (me or {}).get("chg"), "ltp": (me or {}).get("ltp"),
                   "link": n.get("link", "")}
            if tag in ("STRONG POSITIVE", "POSITIVE") and n["impact"] >= 7:
                row["verdict"] = ("🔥 JACKPOT — news + price confirm"
                                  if me and (me.get("chg") or 0) > 0.5
                                  else "WAIT — technical confirm ஆகணும்")
                jackpot.append(row)
            elif tag == "NEGATIVE" and n["impact"] >= 7:
                row["verdict"] = ("💀 DANGER — news + price falling"
                                  if me and (me.get("chg") or 0) < -0.5
                                  else "WATCH — negative news")
                danger.append(row)
            break

    def uniq(lst):
        seen, out = set(), []
        for x in lst:
            k = x.get("symbol") or x.get("headline")
            if k in seen:
                continue
            seen.add(k); out.append(x)
        return out

    return {"jackpot": uniq(jackpot)[:8], "danger": uniq(danger)[:8],
            "market_crash": crash[:5]}

