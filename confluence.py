"""
KRT · CONFLUENCE ENGINE
═══════════════════════
Terminal-la irukra ellaa data point-ayum ore edathula konduvandhu, ovvoru
stock-kum 10 confirmation check pannuthu. Ellaam ✅ aana mattum thaan
"SUPER CONFLUENCE" nu kaattum.

10 CONFIRMATIONS
  1. SECTOR    — strong sector top-3 (BUY) / weak bottom-3 (SELL)
  2. LEADER    — andha sector-la #1 or #2 stock, sector-ai outperform pannuthu
  3. NEWS      — fresh positive/negative catalyst
  4. PDH/PDL   — previous day high/low break
  5. PWH/PWL   — previous week high/low break
  6. VWAP      — VWAP mela hold (BUY) / keezha (SELL)
  7. VOLUME    — average-ai vida 2x+ volume
  8. HTF       — 15m + 1h trend align
  9. ADX       — 30+ (trend strength irukku, chop illa)
 10. RETEST    — breakout level-ku retest panni hold aachu (chase illa)

Ovvoru setup-kum oru type tag: MULTI-BREAKOUT, SECTOR LEADER, MOMENTUM
EXPLOSION, BREAKOUT RETEST, REVERSAL, NEWS + PRICE ACTION.
"""

MIN_SCORE = 6          # idhukku keezha kaattave koodadhu
SUPER_SCORE = 9        # 9+ = 👑 SUPER CONFLUENCE


def _rel_vol(r, avgvol):
    """Inniki volume / sarasari volume. 2.8x madhiri kaatta."""
    av = avgvol.get(r["symbol"])
    v = r.get("volume") or 0
    if not av or av <= 0 or not v:
        return None
    return round(v / av, 1)


def _retest_ok(cs, level, side):
    """Breakout aana level-ku thirumba vandhu, hold panni, mela close aacha?

    Chase pannaama entry edukka idhu thaan mukkiyam. Kadaisi 60 candle-la:
    level-ai break panni -> 0.4%-kku ulla thirumbi vandhu -> meendum mela.
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
    """Reversal: day low sweep panni VWAP-ai reclaim aacha (or reverse)."""
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


def _classify(f, rvol):
    """Endha setup-nu peyar vekkaradhu (mukkiyathuvam vari-sai-ppadi)."""
    if f["pdh"] and f["pwh"] and f["month"]:
        return "🚀 MULTI-BREAKOUT", "PDH + PWH + Month high ellaam ore naal"
    if f["pdh"] and f["pwh"]:
        return "🚀 MULTI-BREAKOUT", "Previous day + week level ready break"
    if f["retest"]:
        return "🎯 BREAKOUT RETEST", "Break aagi, retest panni, hold aachu"
    if f["reversal"]:
        return "🔄 REVERSAL", "Day extreme sweep panni VWAP reclaim"
    if f["leader"] and f["sector"]:
        return "🔥 SECTOR LEADER", "Strongest sector-oda #1 stock"
    if f["news"]:
        return "📰 NEWS + PRICE ACTION", "Catalyst + technical rendum align"
    if rvol and rvol >= 2 and f["adx"] and f["vwap"]:
        return "💥 MOMENTUM EXPLOSION", "Volume vெடிச்சு trend start aaguthu"
    return "⚡ EARLY TREND", "Trend aarambichukittu irukku"


def build(stocks, sectors, levels, news_map, candles, ist_min):
    """Ellaa stock-ayum scan panni, confluence card list-a thirupudhu."""
    srank = {x["sector"]: i + 1 for i, x in enumerate(sectors)}
    total = len(sectors) or 1
    sec_chg = {x["sector"]: x["chg"] for x in sectors}
    avgvol = levels.get("avgvol", {})

    # ovvoru sector-layum stock-ai chg vari-sai-ppadi -> leader kandupidikka
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
    for r in stocks:
        ind = r.get("ind") or {}
        px = r.get("ltp") or 0
        if not px or not ind.get("ready"):
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

        # ── 10-point score ──
        keys = ["sector", "leader", "news", "pdh", "pwh",
                "vwap", "volume", "htf", "adx", "retest"]
        score = sum(1 for k in keys if f[k])
        if f["month"]:
            score += 1                     # month break = bonus
        if not f["rsi_ok"] or not f["vwap"]:
            continue                       # idhu rendum kandippa venum
        if score < MIN_SCORE:
            continue

        setup, why = _classify(f, rvol)
        atr = ind.get("atr") or px * 0.006
        atr = min(atr, px * 0.025)
        sgn = 1 if side == "BUY" else -1

        label = {
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
        checks = [label[k] for k in keys if f[k]]
        misses = [label[k] for k in keys if not f[k]]
        if f["month"]:
            checks.insert(3, f"MONTH {'high' if side=='BUY' else 'low'} break")

        out.append({
            "symbol": r["symbol"], "sector": r["sector"], "side": side,
            "ltp": px, "chg": r["chg"], "score": min(99, 55 + score * 4),
            "pts": score, "setup": setup, "why": why,
            "checks": checks, "misses": misses,
            "rvol": rvol, "rsi": ind.get("rsi"), "adx": ind.get("adx"),
            "super": score >= SUPER_SCORE,
            "entry": round(px, 2),
            "sl":  round(px - sgn * 1.2 * atr, 2),
            "t1":  round(px + sgn * 1.5 * atr, 2),
            "t2":  round(px + sgn * 2.5 * atr, 2),
            "t3":  round(px + sgn * 4.0 * atr, 2),
            "avoid": ("VWAP keezha close aana veliya va"
                      if side == "BUY" else "VWAP mela close aana veliya va"),
            "late": ist_min > 870,          # 2:30 kku appuram = late entry
        })

    out.sort(key=lambda x: (-x["pts"], -x["score"]))
    return out[:8]
