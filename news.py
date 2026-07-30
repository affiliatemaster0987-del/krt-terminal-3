"""
KRT — News AI module
Polls free RSS feeds (Moneycontrol / Economic Times markets) every 90s,
tags each headline Positive / Negative / Neutral with keyword scoring.
No API key needed.
"""
import time, threading, re
import urllib.request
import xml.etree.ElementTree as ET

FEEDS = [
    ("Moneycontrol", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("Moneycontrol Biz", "https://www.moneycontrol.com/rss/business.xml"),
    ("ET Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
]

POS_WORDS = ["surge", "rally", "beats", "beat", "profit rises", "record high", "jumps",
             "gains", "upgrade", "buyback", "order win", "bags order", "rate cut",
             "strong", "growth", "soars", "all-time high", "dividend", "bonus"]
NEG_WORDS = ["falls", "plunge", "drops", "misses", "miss", "downgrade", "loss",
             "weak", "crash", "slump", "fraud", "probe", "penalty", "default",
             "tanks", "cuts guidance", "resigns", "fire", "strike", "ban"]

# stocks we watch — headline-ல இந்த பேர் வந்தா affected stock-ஆ tag பண்ணும்
STOCK_KEYWORDS = ["RELIANCE", "TCS", "HDFC", "INFOSYS", "INFY", "SBI", "ICICI",
                  "ITC", "TATA MOTORS", "BEL", "VARUN", "VBL", "ADANI", "NIFTY",
                  "SENSEX", "BANK"]

_news_cache = {"items": [], "ts": 0}
_lock = threading.Lock()
POLL_SECONDS = 45


def _classify(title):
    t = title.lower()
    pos = sum(1 for w in POS_WORDS if w in t)
    neg = sum(1 for w in NEG_WORDS if w in t)
    if pos > neg:
        return "Positive", min(10, 4 + pos * 2)
    if neg > pos:
        return "Negative", min(10, 4 + neg * 2)
    return "Neutral", 3


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
    return out[:10]


def get_news():
    """Cached, merged, de-duplicated news items (max 15)."""
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
        # முக்கியமான (impact அதிகமான) news முதல்ல
        items.sort(key=lambda x: x["impact"], reverse=True)
        if items:
            _news_cache.update(items=items[:15], ts=now)
        return _news_cache["items"]


# ---------------- News Jackpot signals ----------------
# Positive + impact >= 7 + watchlist stock match → "call எடுக்கலாமா" verdict
_ALIAS = {"INFOSYS": "INFY", "HDFC": "HDFCBANK", "ICICI": "ICICIBANK",
          "SBI": "SBIN", "TATA MOTORS": "TATAMOTORS", "VARUN": "VBL"}

def get_news_signals():
    out = []
    try:
        from ai_engine import compute_scores
        scored, _ = compute_scores()
        smap = {s["symbol"]: s for s in scored}
        for n in get_news():
            if n["tag"] != "Positive" or n["impact"] < 7:
                continue
            for st in n.get("stocks", []):
                sym = _ALIAS.get(st, st)
                me = smap.get(sym)
                if not me:
                    continue
                verdict = ("CALL-WORTHY ✅" if me["score"] >= 65
                           else "WAIT — technicals confirm ஆகணும்")
                out.append({"symbol": sym, "headline": n["title"][:90],
                            "impact": n["impact"], "score": me["score"],
                            "chg": me["chg"], "verdict": verdict,
                            "link": n.get("link", "")})
                break
    except Exception as e:
        print("news signals error:", e)
    seen, uniq = set(), []
    for s in out:
        if s["symbol"] in seen: continue
        seen.add(s["symbol"]); uniq.append(s)
    return uniq[:6]
