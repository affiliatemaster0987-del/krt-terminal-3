"""
KRT · INSTITUTIONAL ENTRY
═════════════════════════
A fast scan of the whole F&O list for one thing: price taking out a level that
matters, with the volume to say somebody large did it.

THE TEN LEVELS
    Previous day high / low
    Previous week high / low
    Previous month high / low
    First 5-minute candle high / low
    First 15-minute candle high / low

WHY VOLUME IS NOT OPTIONAL
Price drifting through yesterday's high on ordinary volume is noise; it gets
faded within the hour. The same break on two or three times the average volume
is somebody with size having to get filled, and that is the only version worth
an alert. A level touch with no volume behind it is deliberately rejected here
even though it would look like a signal on a chart.

WHAT THIS IS NOT
It is not a claim to see institutional order flow. Retail data feeds do not
expose that. What it does is measure the footprint large orders leave behind —
volume well above normal, a close beyond the level rather than a wick through
it, and price holding on the right side of VWAP.

GRADING
    JACKPOT  every confirmation, rare
    PREMIUM  strong volume, VWAP and trend agree
    STRONG   good break, one confirmation missing
    NORMAL   valid but unremarkable
    WEAK     rejected before it is shown
"""

from datetime import datetime, timedelta

IST = lambda: datetime.utcnow() + timedelta(hours=5, minutes=30)

MKT_OPEN = 9 * 60 + 15
MKT_CLOSE = 15 * 60 + 30

# A break is only real if the close clears the level by this much — a wick
# through and back is exactly what traps people.
CLEAR_PCT = 0.0008
MIN_RVOL = 1.5          # below this it is drift, not participation


def hhmm12(dt=None):
    """12-hour clock with AM/PM. The terminal must never show 14:45."""
    d = dt or IST()
    return d.strftime("%I:%M %p").lstrip("0").rjust(8)


def to12(hhmm):
    """Convert a stored 24-hour 'HH:MM' to '10:10 AM'."""
    try:
        h, m = str(hhmm).split(":")[:2]
        h, m = int(h), int(m)
        ap = "AM" if h < 12 else "PM"
        hh = h % 12 or 12
        return f"{hh}:{m:02d} {ap}"
    except Exception:
        return str(hhmm)


def market_open_now():
    n = IST()
    if n.weekday() >= 5:
        return False
    m = n.hour * 60 + n.minute
    return MKT_OPEN <= m <= MKT_CLOSE


# Each level carries its own weight. A month high is far rarer, and far more
# meaningful, than the first 5-minute candle high.
LEVELS = [
    ("pmh", "Previous Month High", "up",   26),
    ("pml", "Previous Month Low",  "down", 26),
    ("pwh", "Previous Week High",  "up",   20),
    ("pwl", "Previous Week Low",   "down", 20),
    ("pdh", "Previous Day High",   "up",   15),
    ("pdl", "Previous Day Low",    "down", 15),
    ("or15h", "First 15-Min High", "up",   11),
    ("or15l", "First 15-Min Low",  "down", 11),
    ("or5h", "First 5-Min High",   "up",    8),
    ("or5l", "First 5-Min Low",    "down",  8),
]


def _grade(score, rvol, vwap_ok, trend_ok, closed_beyond):
    if score >= 82 and rvol >= 3 and vwap_ok and trend_ok and closed_beyond:
        return "JACKPOT"
    if score >= 72 and rvol >= 2.2 and vwap_ok:
        return "PREMIUM"
    if score >= 62 and rvol >= 1.8:
        return "STRONG"
    if score >= 50:
        return "NORMAL"
    return "WEAK"


def _strike(px, side):
    """Nearest tradable strike for a stock option."""
    p = float(px or 0)
    step = 2.5 if p < 100 else 5 if p < 250 else 10 if p < 500 \
        else 20 if p < 1000 else 50 if p < 2500 else 100
    return round(p / step) * step


def scan(stocks, levels, avgvol, seen, sectors=None, index_dir=0):
    """Return fresh institutional-entry signals.

    `seen` is a caller-owned dict that remembers what has already fired, so a
    stock that stays above a level does not re-alert on every poll. The first
    detection time is kept, which is the time the user actually needs.
    """
    if not market_open_now():
        return []

    out = []
    now24 = IST().strftime("%H:%M")
    sec_chg = {s["sector"]: s.get("chg", 0) for s in (sectors or [])}

    for r in stocks or []:
        sym = r.get("symbol")
        px = r.get("ltp") or 0
        ind = r.get("ind") or {}
        if not sym or not px or not ind.get("ready"):
            continue

        vol = r.get("volume") or 0
        av = (avgvol or {}).get(sym) or 0
        rvol = round(vol / av, 1) if av else 0
        if rvol < MIN_RVOL:
            continue                        # no participation, no alert

        vwap = ind.get("vwap")
        for key, label, direction, weight in LEVELS:
            lvl = (levels.get(key) or {}).get(sym) if key in levels else ind.get(key)
            if not lvl:
                continue

            if direction == "up":
                broke = px > lvl * (1 + CLEAR_PCT)
                vwap_ok = bool(vwap and px > vwap)
            else:
                broke = px < lvl * (1 - CLEAR_PCT)
                vwap_ok = bool(vwap and px < vwap)
            if not broke:
                continue

            tag = f"{sym}|{key}"
            first = seen.get(tag)
            if first:
                continue                    # already alerted, keep it quiet
            seen[tag] = now24

            side = "CE" if direction == "up" else "PE"
            htf_ok = ind.get("htf") == ("up" if direction == "up" else "down")
            adx = ind.get("adx") or 0
            rsi = ind.get("rsi")
            sec_ok = (sec_chg.get(r.get("sector"), 0) > 0) == (direction == "up")
            idx_ok = (index_dir > 0) == (direction == "up") if index_dir else False

            score = 30 + weight
            score += min(18, (rvol - 1) * 7)
            score += 10 if vwap_ok else -14
            score += 8 if htf_ok else 0
            score += 6 if adx >= 25 else 0
            score += 5 if sec_ok else 0
            score += 4 if idx_ok else 0
            if rsi is not None:
                if direction == "up" and rsi > 80:
                    score -= 6
                if direction == "down" and rsi < 20:
                    score -= 6
            score = int(max(5, min(99, score)))

            closed_beyond = abs(px - lvl) / lvl > CLEAR_PCT * 2
            grade = _grade(score, rvol, vwap_ok, htf_ok, closed_beyond)
            if grade == "WEAK":
                continue                    # rejected on purpose

            out.append({
                "symbol": sym, "sector": r.get("sector", ""),
                "kind": "BREAKOUT" if direction == "up" else "BREAKDOWN",
                "dir": direction,
                "level_name": label, "level": round(lvl, 2),
                "break_price": round(px, 2), "ltp": round(px, 2),
                "chg": r.get("chg"),
                "rvol": rvol,
                "volume_txt": ("VERY STRONG" if rvol >= 3 else
                               "STRONG" if rvol >= 2 else "ABOVE AVERAGE"),
                "vwap": round(vwap, 2) if vwap else None,
                "vwap_txt": ("Above VWAP" if vwap_ok and direction == "up" else
                             "Below VWAP" if vwap_ok else "VWAP not confirmed"),
                "rsi": rsi, "adx": adx,
                "htf_ok": htf_ok, "sector_ok": sec_ok, "index_ok": idx_ok,
                "grade": grade,
                "score": score,
                "side": side,
                "strike": _strike(px, side),
                "opt_hint": f"{sym} {_strike(px, side):g} {side}",
                "at": now24,
                "at12": to12(now24),
                "why": (f"{label} broken on {rvol}x volume · "
                        f"{'above' if direction == 'up' else 'below'} VWAP"
                        f"{' · 15m+1h aligned' if htf_ok else ''}"),
            })

    # Strongest first, then newest. Grade outranks raw score deliberately.
    rank = {"JACKPOT": 0, "PREMIUM": 1, "STRONG": 2, "NORMAL": 3}
    out.sort(key=lambda x: (rank.get(x["grade"], 9), -x["score"]))
    return out
