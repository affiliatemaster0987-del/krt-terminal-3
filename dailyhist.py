"""
KRT · DAILY HISTORY
═══════════════════
Levels kept arriving for a handful of symbols out of 141, which left the
confluence engine, the institutional scanner and the gamma scan with almost
nothing to work on. The cause was never the logic — it was that both level
sources are outside our control:

    Angel historical   rate limited, and the 37MB scrip master truncates
    Yahoo              blocked or throttled from a cloud IP

This module removes that dependency. The terminal already streams every price
tick into one-minute candles all day. At the close, the day's high, low, close
and volume are written to disk. Tomorrow those become the previous day levels,
and after a few sessions the weekly and monthly levels build themselves.

WHAT THIS MEANS IN PRACTICE
    Day 1    nothing — there is no history yet, and that is honest
    Day 2    previous day high/low for every symbol that traded
    Day 6    previous week high/low
    Day 22   previous month high/low, and a real volume baseline

It is slower to start than an API call, but once running it covers the whole
universe, costs nothing, and cannot be rate limited. The external sources stay
in place and win when they answer; this fills the gap when they do not.
"""

import json
from datetime import datetime, timedelta

import store as _ST

HIST_FILE = "krt_daily.json"
KEEP_DAYS = 70            # enough for a month of levels plus a margin

_hist = {}                # sym -> [{"d","h","l","c","v"}, ...] oldest first
_loaded = False


def _ist():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


def load():
    global _hist, _loaded
    if _loaded:
        return _hist
    d = _ST.read_json(HIST_FILE) or {}
    if isinstance(d, dict):
        _hist = {k: v for k, v in d.items() if isinstance(v, list)}
    _loaded = True
    n = sum(len(v) for v in _hist.values())
    print(f"[dailyhist] {len(_hist)} symbols, {n} daily bars on disk")
    return _hist


def save():
    _ST.write_json(HIST_FILE, _hist)


def record(candles, today=None):
    """Fold today's candles into the history. Safe to call repeatedly.

    Called through the session as well as at the close, so a restart in the
    afternoon does not lose the morning — the row for today is simply updated
    with the wider range.
    """
    load()
    day = today or _ist().strftime("%Y-%m-%d")
    changed = 0
    for sym, cs in (candles or {}).items():
        if not cs or len(cs) < 5:
            continue
        try:
            hi = max(c["h"] for c in cs)
            lo = min(c["l"] for c in cs)
            close = cs[-1]["c"]
            vol = sum(c.get("v", 0) for c in cs)
        except Exception:
            continue
        rows = _hist.setdefault(sym, [])
        if rows and rows[-1].get("d") == day:
            r = rows[-1]
            r["h"] = max(r["h"], hi)
            r["l"] = min(r["l"], lo)
            r["c"] = close
            r["v"] = max(r.get("v", 0), vol)
        else:
            rows.append({"d": day, "h": round(hi, 2), "l": round(lo, 2),
                         "c": round(close, 2), "v": vol})
            changed += 1
        if len(rows) > KEEP_DAYS:
            del rows[:-KEEP_DAYS]
    if changed:
        print(f"[dailyhist] new session row for {changed} symbols")
    save()
    return changed


def levels(today=None):
    """Derive every level the terminal needs from what we have stored.

    Returns only what the history can actually support. A symbol with two
    sessions gets previous-day levels and nothing else, rather than a weekly
    level invented from two days of data.
    """
    load()
    day = today or _ist().strftime("%Y-%m-%d")
    out = {"pdh": {}, "pdl": {}, "pwh": {}, "pwl": {},
           "pmh": {}, "pml": {}, "avgvol": {}}
    for sym, rows in _hist.items():
        past = [r for r in rows if r.get("d") != day]
        if not past:
            continue

        prev = past[-1]
        out["pdh"][sym] = prev["h"]
        out["pdl"][sym] = prev["l"]

        if len(past) >= 4:
            wk = past[-5:]
            out["pwh"][sym] = max(r["h"] for r in wk)
            out["pwl"][sym] = min(r["l"] for r in wk)

        if len(past) >= 15:
            mo = past[-21:]
            out["pmh"][sym] = max(r["h"] for r in mo)
            out["pml"][sym] = min(r["l"] for r in mo)

        vols = [r.get("v", 0) for r in past[-20:] if r.get("v")]
        if len(vols) >= 3:
            out["avgvol"][sym] = sum(vols) / len(vols)
    return out


def merge_into(levels_dict, today=None):
    """Fill gaps in the live levels map without overwriting a real source.

    Angel and Yahoo win where they answered; this only supplies symbols they
    missed, which is most of them.
    """
    derived = levels(today)
    added = {}
    for key, vals in derived.items():
        target = levels_dict.setdefault(key, {})
        n = 0
        for sym, v in vals.items():
            if sym not in target:
                target[sym] = v
                n += 1
        if n:
            added[key] = n
    if added:
        print("[dailyhist] filled gaps:",
              ", ".join(f"{k} +{v}" for k, v in added.items()))
    return added


def coverage():
    load()
    sessions = sorted({r["d"] for rows in _hist.values() for r in rows})
    return {"symbols": len(_hist), "sessions": len(sessions),
            "first": sessions[0] if sessions else None,
            "last": sessions[-1] if sessions else None}
