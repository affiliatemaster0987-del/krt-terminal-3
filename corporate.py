"""
KRT · CORPORATE FILINGS
═══════════════════════
RSS news is a journalist writing *about* an event. This module reads the
event itself — what the company filed with the exchange. It is the original
source and it lands earlier.

TWO FEEDS
  1. ANNOUNCEMENTS  — orders won, FDA approvals, tender cancellations,
                      fund raises, clarifications sought by the exchange.
  2. RESULTS DIARY  — which companies have board meetings scheduled to
                      declare results, so you know *before* the day.

NSE is the primary source. NSE blocks plain requests, so we bootstrap a
cookie from the homepage first. BSE is the fallback when NSE refuses.
Both can fail on a cloud IP — everything is wrapped, and the terminal keeps
working without this section if it does.
"""

import json
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar

IST = timezone(timedelta(hours=5, minutes=30))

NSE_HOME = "https://www.nseindia.com"
NSE_ANN = "https://www.nseindia.com/api/corporate-announcements?index=equities"
NSE_CAL = "https://www.nseindia.com/api/event-calendar"
BSE_ANN = ("https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
           "?strCat=-1&strPrevDate={d}&strScrip=&strSearch=P&strToDate={d}&strType=C")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

_ann_cache = {"items": [], "ts": 0, "src": ""}
_cal_cache = {"items": [], "ts": 0}
ANN_TTL = 240          # 4 min
CAL_TTL = 21600        # 6 hrs — the diary barely changes intraday

_opener = None


def _get_opener():
    """NSE needs a cookie from the homepage before the API will answer."""
    global _opener
    if _opener is not None:
        return _opener
    cj = CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA),
                     ("Accept", "application/json, text/plain, */*"),
                     ("Accept-Language", "en-US,en;q=0.9"),
                     ("Referer", NSE_HOME + "/companies-listing/corporate-filings-announcements")]
    try:
        op.open(NSE_HOME, timeout=12).read(2048)
    except Exception as e:
        print("[corp] nse cookie warm failed:", str(e)[:90])
    _opener = op
    return op


def _fetch_json(url, opener=None, timeout=15):
    op = opener or _get_opener()
    with op.open(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


# ── classification ───────────────────────────────────────────────────────
BIG_POSITIVE = [
    ("order win", ["bags order", "wins order", "receives order", "order worth",
                   "letter of award", "loa", "work order", "contract awarded",
                   "ultra-mega", "mega order", "large order", "purchase order"]),
    ("approval", ["final approval", "usfda approval", "fda approval", "anda approval",
                  "marketing authorisation", "drug approval", "patent granted",
                  "approval received", "licence granted", "clearance received"]),
    ("expansion", ["acquisition", "stake increase", "share purchase agreement",
                   "new plant", "capacity expansion", "joint venture", "merger",
                   "commissioning", "commercial production"]),
    ("cash", ["dividend", "buyback", "bonus issue", "stock split", "fund raise",
              "qip", "preferential allotment"]),
]

BIG_NEGATIVE = [
    ("order loss", ["cancelled", "cancellation", "terminated", "termination",
                    "withdrawn", "revoked", "foreclosure of order"]),
    ("regulatory", ["clarification sought", "show cause", "penalty", "fine imposed",
                    "sebi order", "gst demand", "tax demand", "adjudication order",
                    "form 483", "warning letter", "import alert", "oai", "vai",
                    "observations", "non-compliance", "search and seizure"]),
    ("stress", ["resignation of", "auditor resign", "cfo resign", "insolvency",
                "nclt", "default", "downgrade", "pledge of shares", "block deal",
                "block market trade", "offer for sale", "stake sale by promoter",
                "encumbrance"]),
]

RESULT_WORDS = ["financial results", "quarterly results", "board meeting intimation",
                "unaudited results", "audited results", "outcome of board meeting"]

_WB = {}


def _hit(t, words):
    """Word-boundary match — plain substring matching creates false hits."""
    for w in words:
        rx = _WB.get(w)
        if rx is None:
            rx = _WB[w] = re.compile(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])")
        if rx.search(t):
            return w
    return None


FAVOURABLE = ["rejected", "dismissed", "in favour of", "quashed", "set aside",
              "upheld", "vacated", "relief granted"]


def _classify(subject, body=""):
    """-> (tag, direction, impact 1-10). direction: +1 / -1 / 0"""
    t = (subject + " " + body).lower()
    # "challenge rejected" reads negative word-by-word but is good news for
    # the company, so resolve that before the negative sweep.
    if _hit(t, FAVOURABLE) and _hit(t, ["challenge", "petition", "plea", "appeal",
                                        "request", "objection", "revocation"]):
        return "FAVOURABLE ORDER", 1, 8
    for kind, words in BIG_NEGATIVE:
        w = _hit(t, words)
        if w:
            imp = 9 if kind == "order loss" else 8
            return kind.upper(), -1, imp
    for kind, words in BIG_POSITIVE:
        w = _hit(t, words)
        if w:
            imp = 9 if kind in ("order win", "approval") else 7
            return kind.upper(), 1, imp
    if _hit(t, RESULT_WORDS):
        return "RESULTS", 0, 6
    return "FILING", 0, 3


def _ago(dt):
    if not dt:
        return ""
    mins = (datetime.now(IST) - dt).total_seconds() / 60
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{int(mins)}m ago"
    if mins < 1440:
        return f"{int(mins / 60)}h ago"
    return f"{int(mins / 1440)}d ago"


def _parse_dt(s):
    for f in ("%d-%b-%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
              "%d-%b-%Y", "%d %b %Y %H:%M:%S"):
        try:
            return datetime.strptime(str(s).strip(), f).replace(tzinfo=IST)
        except Exception:
            pass
    return None


# ── announcements ────────────────────────────────────────────────────────
def _from_nse(universe):
    rows = _fetch_json(NSE_ANN)
    out = []
    for x in rows if isinstance(rows, list) else []:
        sym = (x.get("symbol") or "").strip().upper()
        if universe and sym not in universe:
            continue
        subj = (x.get("desc") or x.get("subject") or "").strip()
        body = (x.get("attchmntText") or x.get("smIndustry") or "").strip()
        dt = _parse_dt(x.get("an_dt") or x.get("sort_date") or "")
        if not subj:
            continue
        tag, dirn, imp = _classify(subj, body)
        out.append({"symbol": sym, "subject": subj[:180], "tag": tag,
                    "dir": dirn, "impact": imp, "ago": _ago(dt),
                    "at": dt.strftime("%d %b %H:%M") if dt else "",
                    "_ts": dt.timestamp() if dt else 0,
                    "link": x.get("attchmntFile") or ""})
    return out


def _from_bse(universe):
    d = datetime.now(IST).strftime("%Y%m%d")
    op = urllib.request.build_opener()
    op.addheaders = [("User-Agent", UA), ("Referer", "https://www.bseindia.com/")]
    data = _fetch_json(BSE_ANN.format(d=d), opener=op)
    rows = data.get("Table", []) if isinstance(data, dict) else []
    out = []
    for x in rows:
        sym = (x.get("SLONGNAME") or x.get("SCRIP_CD") or "").strip().upper()
        match = next((u for u in (universe or []) if u and u in sym), sym)
        if universe and match not in universe:
            continue
        subj = (x.get("NEWSSUB") or x.get("HEADLINE") or "").strip()
        if not subj:
            continue
        dt = _parse_dt(x.get("News_submission_dt") or x.get("DT_TM") or "")
        tag, dirn, imp = _classify(subj, x.get("MORE") or "")
        out.append({"symbol": match, "subject": subj[:180], "tag": tag,
                    "dir": dirn, "impact": imp, "ago": _ago(dt),
                    "at": dt.strftime("%d %b %H:%M") if dt else "",
                    "_ts": dt.timestamp() if dt else 0, "link": ""})
    return out


def get_announcements(universe=None):
    """Exchange filings for stocks in our universe, newest first."""
    now = time.time()
    if _ann_cache["items"] and now - _ann_cache["ts"] < ANN_TTL:
        return _ann_cache["items"]

    uni = set(universe or [])
    items, src = [], ""
    for name, fn in (("nse", _from_nse), ("bse", _from_bse)):
        try:
            items = fn(uni)
            if items:
                src = name
                break
        except Exception as e:
            print(f"[corp] {name} announcements failed:", str(e)[:110])

    # only material filings, and only today's
    cut = time.time() - 14 * 3600
    items = [x for x in items if x["impact"] >= 6 and (x["_ts"] == 0 or x["_ts"] > cut)]
    items.sort(key=lambda x: (-x["impact"], -x["_ts"]))
    items = items[:25]
    _ann_cache.update(items=items, ts=now, src=src)
    if items:
        print(f"[corp] {len(items)} announcements from {src}")
    return items


# ── results diary ────────────────────────────────────────────────────────
def get_results_calendar(universe=None, days=10):
    """Board meetings scheduled to declare results — know before the day."""
    now = time.time()
    if _cal_cache["items"] and now - _cal_cache["ts"] < CAL_TTL:
        return _cal_cache["items"]

    uni = set(universe or [])
    out = []
    try:
        rows = _fetch_json(NSE_CAL)
        today = datetime.now(IST).date()
        for x in rows if isinstance(rows, list) else []:
            sym = (x.get("symbol") or "").strip().upper()
            if uni and sym not in uni:
                continue
            purpose = (x.get("purpose") or "").strip()
            if "result" not in purpose.lower():
                continue
            dt = _parse_dt(x.get("date") or "")
            if not dt:
                continue
            delta = (dt.date() - today).days
            if delta < 0 or delta > days:
                continue
            out.append({
                "symbol": sym, "date": dt.strftime("%d %b"), "days": delta,
                "when": "TODAY" if delta == 0 else
                        "TOMORROW" if delta == 1 else f"in {delta} days",
                "purpose": purpose[:90],
                "note": ("Results today — expect a volatility spike, avoid fresh "
                         "positions before the announcement" if delta == 0 else
                         "Results tomorrow — size down, gap risk overnight" if delta == 1
                         else "Scheduled results — plan around it"),
            })
        out.sort(key=lambda x: x["days"])
    except Exception as e:
        print("[corp] results calendar failed:", str(e)[:110])

    _cal_cache.update(items=out[:30], ts=now)
    if out:
        print(f"[corp] results diary: {len(out)} companies in next {days} days")
    return _cal_cache["items"]


def sentiment_map(universe=None):
    """{"LUPIN": +1, "CEIGALL": -1} for the confluence engine.

    A filing is a much harder catalyst than an RSS headline, so this
    overrides the news sentiment where both exist.
    """
    out = {}
    for a in get_announcements(universe):
        if a["dir"] and a["impact"] >= 8:
            out[a["symbol"]] = a["dir"]
    return out


def results_soon(universe=None):
    """{"TCS": 0, "INFY": 1} — days until results. Used to warn on cards."""
    return {x["symbol"]: x["days"] for x in get_results_calendar(universe)}
