"""
KRT · CONFLUENCE ENGINE
═══════════════════════
Pulls every data point in the terminal into one place and checks 10
confirmations per stock. Only a setup where nearly all of them agree gets
the top grade.

THE 10 CONFIRMATIONS
  1. SECTOR    strong sector top-3 (BUY) / weak bottom-3 (SELL)
  2. LEADER    #1 or #2 stock in that sector, outperforming the sector
  3. NEWS      fresh catalyst pointing the same way
  4. PDH/PDL   previous day high / low broken
  5. PWH/PWL   previous week high / low broken
  6. VWAP      holding above VWAP (BUY) / below (SELL)
  7. VOLUME    2x or more of average daily volume
  8. HTF       15m and 1h trend aligned
  9. ADX       30+, real trend rather than chop
 10. RETEST    broke out, retested the level and held (no chasing)

Each carries a different weight — a retest hold or a month-high break is
worth far more than ADX above 30, because it is rarer and gives a better
entry. The weighted total becomes the score and the letter grade.
"""

MIN_SCORE = 6          # below this, do not show at all
SUPER_SCORE = 9        # 9+ confirmations = A+ grade

# Not every confirmation is worth the same. ADX 30 is common; a fresh
# month-high break with volume is rare. Weight them by how much edge each
# one actually adds, and by how hard it is to get.
WEIGHT = {
    "retest": 14,      # hardest + best entry (no chasing)
    "pwh":    12,      # weekly level = real structure
    "month":  12,      # rarest
    "volume": 11,      # conviction behind the move
    "sector":  9,
    "leader":  9,
    "pdh":     8,
    "htf":     8,
    "news":    7,
    "vwap":    6,      # common
    "adx":     4,      # most common
}
MAX_RAW = sum(WEIGHT.values())      # 100

# Honest grade bands. A+ is meant to be rare — a few per WEEK, not per day.
GRADES = [
    (78, "A+", "MUST TRY",      "Rare — everything lines up"),
    (66, "A",  "STRONG",        "High quality, take it"),
    (54, "B+", "WORK POSSIBLE", "Decent — half size"),
    (42, "B",  "WATCH ONLY",    "Wait for one more confirmation"),
    (0,  "C",  "SKIP",          "Too thin, leave it"),
]


def _grade(raw):
    pct = round(raw / MAX_RAW * 100)
    for cut, letter, label, note in GRADES:
        if pct >= cut:
            return pct, letter, label, note
    return pct, "C", "SKIP", "Too thin"


def _rel_vol(r, avgvol):
    """Today volume / average volume, e.g. 2.8x."""
    av = avgvol.get(r["symbol"])
    v = r.get("volume") or 0
    if not av or av <= 0 or not v:
        return None
    return round(v / av, 1)


def _retest_ok(cs, level, side):
    """Did price break the level, come back to it, hold, and close beyond it?

    This is what stops you chasing. Over the last 60 candles: break the
    level, return within 0.4% of it, then close beyond it again.
    """
    if not level or len(cs) < 20:
        return False
    recent = cs[-60:]
    broke = touched = False
    for c in recent:
        if side == "BUY":
            if c["h"] > level:
                broke = True
            if broke and abs(c["l"] - level) / level < 0.004:
                touched = True
            if broke and touched and c["c"] > level:
                return True
        else:
            if c["l"] < level:
                broke = True
            if broke and abs(c["h"] - level) / level < 0.004:
                touched = True
            if broke and touched and c["c"] < level:
                return True
    return False


def _sweep_reclaim(cs, vwap, side):
    """Reversal: swept the day low then reclaimed VWAP (or the mirror)."""
    if not vwap or len(cs) < 30:
        return False
    lo = min(c["l"] for c in cs)
    hi = max(c["h"] for c in cs)
    last = cs[-1]["c"]
    tail = cs[-15:]
    if side == "BUY":
        swept = any(abs(c["l"] - lo) / lo < 0.002 for c in tail[:10])
        return swept and last > vwap
    swept = any(abs(c["h"] - hi) / hi < 0.002 for c in tail[:10])
    return swept and last < vwap


def _event_warn(days):
    """Results due? A scheduled event can override any chart setup."""
    if days is None:
        return ""
    if days == 0:
        return "RESULTS TODAY — event risk, skip or use a fraction of normal size"
    if days == 1:
        return "RESULTS TOMORROW — overnight gap risk, do not hold"
    if days <= 3:
        return f"Results in {days} days — keep it intraday only"
    return ""


def _classify(f, rvol, side="BUY"):
    """Name the setup, most significant pattern first."""
    ext = "highs" if side == "BUY" else "lows"
    if f["pdh"] and f["pwh"] and f["month"]:
        return "MULTI-BREAKOUT", f"Day, week and month {ext} all broken today"
    if f["pdh"] and f["pwh"]:
        return "MULTI-BREAKOUT", "Previous day and week levels both broken"
    if f["retest"]:
        return "BREAKOUT RETEST", "Broke out, came back, held the level"
    if f["reversal"]:
        return "REVERSAL", "Swept the day extreme, then reclaimed VWAP"
    if f["leader"] and f["sector"]:
        return "SECTOR LEADER", "Number one stock in the strongest sector"
    if f["news"]:
        return "NEWS + PRICE ACTION", "Catalyst and chart agree"
    if rvol and rvol >= 2 and f["adx"] and f["vwap"]:
        return "MOMENTUM EXPLOSION", "Volume surge, trend just starting"
    return "EARLY TREND", "Trend forming, still early"


def build(stocks, sectors, levels, news_map, candles, ist_min, results_map=None):
    """Scan every stock and return the confluence cards."""
    srank = {x["sector"]: i + 1 for i, x in enumerate(sectors)}
    total = len(sectors) or 1
    sec_chg = {x["sector"]: x["chg"] for x in sectors}
    avgvol = levels.get("avgvol", {})
    results_map = results_map or {}

    # rank stocks inside each sector so we can find the leader
    by_sec = {}
    for r in stocks:
        by_sec.setdefault(r["sector"], []).append(r)
    for v in by_sec.values():
        v.sort(key=lambda x: -x["chg"])
    lead_rank = {}
    for sec, rows in by_sec.items():
        for i, r in enumerate(rows):
            lead_rank[r["symbol"]] = i + 1

    out = []
    diag = {"not_ready": 0, "no_vwap": 0, "rsi_out": 0, "too_thin": 0, "best": 0}
    for r in stocks:
        ind = r.get("ind") or {}
        px = r.get("ltp") or 0
        if not px or not ind.get("ready"):
            diag["not_ready"] += 1
            continue

        side = "BUY" if r["chg"] > 0 else "SELL"
        rk = srank.get(r["sector"], 99)
        vwap = ind.get("vwap")
        cs = candles.get(r["symbol"], [])
        rvol = _rel_vol(r, avgvol)
        d_hi, d_lo = ind.get("day_high"), ind.get("day_low")

        pdh = levels["pdh"].get(r["symbol"]); pdl = levels["pdl"].get(r["symbol"])
        pwh = levels["pwh"].get(r["symbol"]); pwl = levels["pwl"].get(r["symbol"])
        pmh = levels["pmh"].get(r["symbol"]); pml = levels["pml"].get(r["symbol"])

        if side == "BUY":
            f = {
                "sector":  rk <= 3 and sec_chg.get(r["sector"], 0) > 0,
                "leader":  lead_rank.get(r["symbol"], 99) <= 2
                           and r["chg"] > sec_chg.get(r["sector"], 0),
                "news":    news_map.get(r["symbol"], 0) > 0,
                "pdh":     bool(pdh and px > pdh),
                "pwh":     bool(pwh and px > pwh),
                "month":   bool(pmh and px > pmh),
                "vwap":    bool(vwap and px > vwap),
                "volume":  bool(rvol and rvol >= 2),
                "htf":     ind.get("htf") == "up",
                "adx":     bool(ind.get("adx") and ind["adx"] >= 30),
                "retest":  _retest_ok(cs, pdh or ind.get("or15h"), "BUY"),
                "reversal": _sweep_reclaim(cs, vwap, "BUY"),
                "rsi_ok":  bool(ind.get("rsi") and 55 <= ind["rsi"] <= 78),
                "near":    bool(d_hi and px >= d_hi * 0.995),
            }
        else:
            f = {
                "sector":  rk >= total - 2 and sec_chg.get(r["sector"], 0) < 0,
                "leader":  lead_rank.get(r["symbol"], 99) >= len(by_sec.get(r["sector"], [1]))
                           and r["chg"] < sec_chg.get(r["sector"], 0),
                "news":    news_map.get(r["symbol"], 0) < 0,
                "pdh":     bool(pdl and px < pdl),
                "pwh":     bool(pwl and px < pwl),
                "month":   bool(pml and px < pml),
                "vwap":    bool(vwap and px < vwap),
                "volume":  bool(rvol and rvol >= 2),
                "htf":     ind.get("htf") == "down",
                "adx":     bool(ind.get("adx") and ind["adx"] >= 30),
                "retest":  _retest_ok(cs, pdl, "SELL"),
                "reversal": _sweep_reclaim(cs, vwap, "SELL"),
                "rsi_ok":  bool(ind.get("rsi") and 22 <= ind["rsi"] <= 45),
                "near":    bool(d_lo and px <= d_lo * 1.005),
            }

        # ── weighted score ──
        # Weighted, not a flat count — see WEIGHT above.
        keys = ["sector", "leader", "news", "pdh", "pwh",
                "vwap", "volume", "htf", "adx", "retest"]
        score = sum(1 for k in keys if f[k])
        raw = sum(WEIGHT[k] for k in keys if f[k])
        if f["month"]:
            score += 1
            raw += WEIGHT["month"]
        diag["best"] = max(diag["best"], score)
        if not f["vwap"]:
            diag["no_vwap"] += 1
            continue                       # mandatory
        if not f["rsi_ok"]:
            diag["rsi_out"] += 1
            continue                       # mandatory
        if score < MIN_SCORE:
            diag["too_thin"] += 1
            continue

        pct, letter, label, gnote = _grade(raw)
        if letter == "C":
            diag["too_thin"] += 1
            continue
        setup, why = _classify(f, rvol, side)
        # ATR here comes off 1-minute candles, so on a quiet stock it can be a
        # few paise. Used raw it produced a 0.05 stop on a 100 rupee stock —
        # levels tighter than the spread, which no trade can survive. Apply the
        # same floor indicators.py uses, based on today's actual range.
        atr = ind.get("atr") or 0
        day_rng = (ind.get("day_high") or px) - (ind.get("day_low") or px)
        floor = max(px * 0.005, min(day_rng, px * 0.05) * 0.30)
        atr = max(atr, floor)
        atr = min(atr, px * 0.025)
        sgn = 1 if side == "BUY" else -1

        txt = {
            "sector":  f"{r['sector']} #{rk} strong sector" if side == "BUY"
                       else f"{r['sector']} weak sector",
            "leader":  "Stock is sector leader",
            "news":    "Fresh catalyst",
            "pdh":     f"Prev day {'high' if side=='BUY' else 'low'} break",
            "pwh":     f"Prev week {'high' if side=='BUY' else 'low'} break",
            "vwap":    f"{'Above' if side=='BUY' else 'Below'} VWAP",
            "volume":  f"{rvol}x volume" if rvol else "High volume",
            "htf":     "15m + 1h aligned",
            "adx":     f"ADX {ind.get('adx')}",
            "retest":  "Breakout retest hold",
        }
        checks = [txt[k] for k in keys if f[k]]
        misses = [txt[k] for k in keys if not f[k]]
        if f["month"]:
            checks.insert(3, f"MONTH {'high' if side=='BUY' else 'low'} break")

        out.append({
            "symbol": r["symbol"], "sector": r["sector"], "side": side,
            "ltp": px, "chg": r["chg"], "score": pct,
            "grade": letter, "label": label, "gnote": gnote,
            "pts": score, "setup": setup, "why": why,
            "checks": checks, "misses": misses,
            "rvol": rvol, "rsi": ind.get("rsi"), "adx": ind.get("adx"),
            "super": letter == "A+",
            "entry": round(px, 2),
            "sl":  round(px - sgn * 1.2 * atr, 2),
            "t1":  round(px + sgn * 1.5 * atr, 2),
            "t2":  round(px + sgn * 2.5 * atr, 2),
            "t3":  round(px + sgn * 4.0 * atr, 2),
            "risk_pct": round(abs(1.2 * atr) / px * 100, 2),
            "rr": round(1.5 / 1.2, 2),
            "avoid": ("Closes back below VWAP"
                      if side == "BUY" else "Closes back above VWAP"),
            "event": _event_warn(results_map.get(r["symbol"])),
            "late": ist_min > 870,          # after 2:30 pm, too late for a fresh entry
        })

    out.sort(key=lambda x: (-x["pts"], -x["score"]))
    return out[:8], diag


def diagnose(stocks, levels, candles):
    """When nothing shows, say what is missing rather than just 'SCANNING'."""
    total = len(stocks)
    ready = sum(1 for r in stocks if (r.get("ind") or {}).get("ready"))
    lv = levels or {}
    return {
        "total": total,
        "ready": ready,
        "pdh": len(lv.get("pdh") or {}),
        "pwh": len(lv.get("pwh") or {}),
        "avgvol": len(lv.get("avgvol") or {}),
        "candles": sum(1 for v in (candles or {}).values() if len(v) >= 20),
    }
