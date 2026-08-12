"""
KRT — News AI 4.0
✅ FRESH news mattum (last 6 hours) — pazhaya news block
✅ Indian market affect panra news mattum
✅ Categories: RESULTS / ORDER WIN / COMPANY RISK / CRASH RISK / POSITIVE / NEGATIVE
✅ US-only opinion articles (Buffett, Wall Street, crypto) filter out
No API key needed.
"""
import time, threading, re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

MAX_AGE_HOURS = 12
POLL_SECONDS = 45

FEEDS = [
    ("Moneycontrol Mkt",  "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("Moneycontrol Buzz", "https://www.moneycontrol.com/rss/buzzingstocks.xml"),
    ("Moneycontrol Res",  "https://www.moneycontrol.com/rss/results.xml"),
    ("Moneycontrol Biz",  "https://www.moneycontrol.com/rss/business.xml"),
    ("ET Markets",        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("ET Stocks",         "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("BS Markets",        "https://www.business-standard.com/rss/markets-106.rss"),
    ("BS Companies",      "https://www.business-standard.com/rss/companies-101.rss"),
]

RESULT_WORDS = ["q1 results", "q2 results", "q3 results", "q4 results", "quarterly results",
                "net profit", "revenue rises", "revenue falls", "ebitda", "earnings",
                "profit jumps", "profit falls", "profit rises", "beats estimates",
                "misses estimates", "guidance", "dividend declared", "results today"]
ORDER_WORDS = ["order win", "wins order", "bags order", "wins contract", "bags contract",
               "new order", "letter of intent", "awarded", "secures order",
               "defence contract", "government order", "export order", "signs pact",
               "signs mou", "acquires", "acquisition", "stake buy", "expansion plan"]
COMPANY_RISK = ["fraud", "probe", "penalty", "raid", "resigns", "steps down",
                "cfo quits", "ceo quits", "auditor resigns", "default", "insolvency",
                "nclt", "downgrade", "cut to sell", "pledge", "promoter sells",
                "stake sale", "plant shut", "fire at plant", "recall", "ban",
                "licence cancelled", "gst notice", "show cause", "sebi order"]
STRONG_POS = ["record high", "all-time high", "lifetime high", "upper circuit",
              "profit surges", "beats estimates", "multibagger", "buyback",
              "bonus issue", "stock split", "upgrade to buy", "target raised"]
POS_WORDS = ["surge", "rally", "gains", "jumps", "soars", "upgrade", "outperform",
             "strong growth", "expansion", "inflows", "recovery", "rate cut", "revival"]
NEG_WORDS = ["falls", "drops", "slump", "tanks", "plunges", "lower circuit", "weak",
             "outflows", "sell-off", "cuts guidance", "loss widens"]

CRASH_EVENT = ["war", "airstrike", "missile attack", "invasion", "nuclear",
               "terror attack", "military strike", "sanctions on", "border conflict",
               "market crash", "bloodbath", "panic selling", "circuit breaker",
               "black monday", "meltdown", "sensex crashes", "nifty crashes",
               "sensex tanks", "nifty tanks", "rupee crashes", "crude spikes",
               "recession fears", "global sell-off", "trade war", "tariff shock"]
MARKET_CTX = ["sensex", "nifty", "market", "markets", "stocks", "stock", "dalal street",
              "investors", "india", "indian", "rupee", "crude", "oil", "fii", "dii", "bse", "nse",
              "bank", "banks", "banking", "rbi", "sebi", "repo", "inflation", "gdp", "ipo",
              "war", "tariff", "trade", "fed", "policy", "results", "profit", "revenue",
              "shares", "share", "equity", "sector", "index", "futures", "psu", "gst"]

NOISE = ["bitcoin", "ethereum", "crypto", "buffett", "berkshire", "how to",
         "should you", "here's why you", "top 5 tips", "webinar", "podcast",
         "horoscope", "in 5 years", "best sip", "astrology", "recipe"]

STOCK_KEYWORDS = ["RELIANCE", "TCS", "HDFC", "INFOSYS", "INFY", "SBI", "ICICI", "ITC",
                  "TATA MOTORS", "TATA STEEL", "BEL", "HAL", "VARUN", "VBL", "ADANI",
                  "NIFTY", "SENSEX", "MARUTI", "AXIS", "KOTAK", "WIPRO", "BAJAJ",
                  "SUN PHARMA", "CIPLA", "TITAN", "TRENT", "ZOMATO", "SWIGGY", "PAYTM",
                  "NTPC", "ONGC", "COAL INDIA", "POWER GRID", "MOTHERSON", "AUROBINDO",
                  "FORTIS", "HINDALCO", "GRASIM", "DIXON", "LT", "L&T", "VEDANTA",
                  "JSW", "DLF", "DMART", "NESTLE", "BRITANNIA", "APOLLO", "CROMPTON",
                  "CHOLA", "BHEL", "IRFC", "RVNL", "IRCTC", "PFC", "REC", "GAIL",
                  "BPCL", "IOC", "TECH MAHINDRA", "HCL", "LTIMINDTREE", "PERSISTENT"]

_news_cache = {"items": [], "ts": 0}
_lock = threading.Lock()


def _age_hours(pubdate):
    if not pubdate:
        return None
    try:
        dt = parsedate_to_datetime(pubdate)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    except Exception:
        return None


def _ago(h):
    if h is None:
        return ""
    m = int(h * 60)
    if m < 1:
        return "just now"
    if m < 60:
        return f"{m}m ago"
    return f"{int(h)}h ago"


def _is_noise(t):
    return any(w in t for w in NOISE)


def _india_relevant(t):
    return any(w in t for w in MARKET_CTX) or any(s.lower() in t for s in STOCK_KEYWORDS)


def _classify(title):
    t = title.lower()
    ev = [w for w in CRASH_EVENT if w in t]
    if ev and _india_relevant(t):
        return "CRASH RISK", min(10, 8 + len(ev))
    if any(w in t for w in COMPANY_RISK):
        return "COMPANY RISK", min(10, 7 + sum(1 for w in COMPANY_RISK if w in t))
    if any(w in t for w in ORDER_WORDS):
        return "ORDER WIN", min(10, 7 + sum(1 for w in ORDER_WORDS if w in t))
    if any(w in t for w in RESULT_WORDS):
        pos = sum(1 for w in ["profit jumps", "profit rises", "beats estimates",
                              "revenue rises", "dividend declared"] if w in t)
        neg = sum(1 for w in ["profit falls", "misses estimates", "loss", "revenue falls"] if w in t)
        return "RESULTS", min(10, 6 + max(pos, neg) * 2)
    if any(w in t for w in STRONG_POS):
        return "STRONG POSITIVE", min(10, 8 + sum(1 for w in STRONG_POS if w in t))
    pos = sum(1 for w in POS_WORDS if w in t)
    neg = sum(1 for w in NEG_WORDS if w in t)
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
        if not title:
            continue
        low = title.lower()
        age = _age_hours((item.findtext("pubDate") or "").strip())
        if age is not None and age > MAX_AGE_HOURS:
            continue
        if _is_noise(low):
            continue
        tag, impact = _classify(title)
        out.append({"source": source, "title": title,
                    "link": (item.findtext("link") or "").strip(),
                    "age_h": round(age, 2) if age is not None else 99, "ago": _ago(age),
                    "tag": tag, "impact": impact, "stocks": _affected(title)})
    return out[:15]


_ORDER = {"CRASH RISK": 0, "COMPANY RISK": 1, "ORDER WIN": 2, "RESULTS": 3,
          "STRONG POSITIVE": 4, "NEGATIVE": 5, "POSITIVE": 6, "NEUTRAL": 7}


def get_news():
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
        items.sort(key=lambda x: (_ORDER.get(x["tag"], 8), x["age_h"], -x["impact"]))
        if not items:
            print("[news] no items after filters — feeds may be blocked")
        _news_cache.update(items=items[:25], ts=now)
        return _news_cache["items"]


def news_debug():
    """Feed-by-feed status — /api/news/debug."""
    out = []
    for source, url in FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 KRT-Terminal"})
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()
            root = ET.fromstring(raw)
            total = len(list(root.iter("item")))
            kept = len(_fetch_feed(source, url))
            out.append({"source": source, "http": "ok", "items": total, "kept": kept})
        except Exception as e:
            out.append({"source": source, "http": "FAIL", "error": str(e)[:150]})
    return {"feeds": out, "cached": len(_news_cache["items"]), "window_h": MAX_AGE_HOURS}


_ALIAS = {"INFOSYS": "INFY", "HDFC": "HDFCBANK", "ICICI": "ICICIBANK", "SBI": "SBIN",
          "TATA MOTORS": "TATAMOTORS", "TATA STEEL": "TATASTEEL", "VARUN": "VBL",
          "AXIS": "AXISBANK", "KOTAK": "KOTAKBANK", "SUN PHARMA": "SUNPHARMA",
          "COAL INDIA": "COALINDIA", "POWER GRID": "POWERGRID", "AUROBINDO": "AUROPHARMA",
          "L&T": "LT", "VEDANTA": "VEDL", "TECH MAHINDRA": "TECHM", "HCL": "HCLTECH",
          "LTIMINDTREE": "LTIM", "NESTLE": "NESTLEIND", "APOLLO": "APOLLOHOSP",
          "CHOLA": "CHOLAFIN", "REC": "RECLTD"}

GOOD_TAGS = ("ORDER WIN", "STRONG POSITIVE", "POSITIVE")
BAD_TAGS = ("COMPANY RISK", "NEGATIVE")


def get_news_signals():
    jackpot, danger, crash, results = [], [], [], []
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
        base = {"headline": n["title"][:130], "impact": n["impact"], "tag": tag,
                "ago": n["ago"], "source": n["source"], "link": n.get("link", "")}
        if tag == "CRASH RISK":
            crash.append({**base,
                          "action": "⚠ MARKET CRASH RISK — புது long வேண்டாம், SL tight"})
            continue
        syms = [_ALIAS.get(s, s) for s in n.get("stocks", [])]
        real = [s for s in syms if s not in ("NIFTY", "SENSEX")]
        sym = (real or syms or [None])[0]
        me = smap.get(sym) if sym else None
        row = {**base, "symbol": sym or "MARKET",
               "chg": (me or {}).get("chg"), "ltp": (me or {}).get("ltp")}

        if tag == "RESULTS":
            row["verdict"] = ("📊 RESULT — price up, momentum"
                              if me and (me.get("chg") or 0) > 0.5
                              else "📊 RESULT — price reaction paarunga")
            results.append(row)
            if me and (me.get("chg") or 0) > 1:
                jackpot.append({**row, "verdict": "🔥 RESULT JACKPOT — beat + price up"})
            elif me and (me.get("chg") or 0) < -1:
                danger.append({**row, "verdict": "💀 RESULT DANGER — miss + price down"})
        elif tag in GOOD_TAGS and n["impact"] >= 7:
            row["verdict"] = ("🔥 JACKPOT — news + price confirm"
                              if me and (me.get("chg") or 0) > 0.5
                              else "WAIT — technical confirm ஆகணும்")
            jackpot.append(row)
        elif tag in BAD_TAGS and n["impact"] >= 7:
            row["verdict"] = ("💀 DANGER — news + price falling"
                              if me and (me.get("chg") or 0) < -0.5
                              else "⚠ WATCH — company risk news")
            danger.append(row)

    def uniq(lst):
        seen, out = set(), []
        for x in lst:
            k = str(x.get("symbol", "")) + x.get("headline", "")[:30]
            if k in seen:
                continue
            seen.add(k); out.append(x)
        return out

    return {"jackpot": uniq(jackpot)[:10], "danger": uniq(danger)[:10],
            "market_crash": crash[:5], "results": uniq(results)[:8],
            "fresh_window_hours": MAX_AGE_HOURS}
