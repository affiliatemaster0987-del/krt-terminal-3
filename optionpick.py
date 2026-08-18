"""
KRT · OPTION PICKER
═══════════════════
A call that says "COFORGE SELL, spot target 1768" still leaves you asking
which option to actually buy. This picks one strike, gives its live premium,
and converts the spot targets into premium targets so the trade can be
tracked like any other call.

WHY ONE STRIKE, NOT THREE
Listing ATM / OTM1 / OTM2 pushes the decision back onto you. This ranks them
on delta, premium size and liquidity, then names the single best one.

DELTA IS AN ESTIMATE
Without a live Greeks feed, delta is approximated from moneyness: ~0.5 at
the money, falling as the strike moves out. Premium targets are therefore
indicative, not exact. Always check the live premium before entering.
"""

MIN_PREMIUM = 5.0        # anything cheaper is mostly noise and spread
MAX_PREMIUM_PCT = 0.06   # premium above 6% of spot is too expensive to hold


def _delta(spot, strike, side):
    """Rough delta from moneyness. ATM ~0.5, deep OTM approaches 0."""
    if not spot or not strike:
        return 0.5
    m = (strike - spot) / spot if side == "CE" else (spot - strike) / spot
    # m < 0 -> in the money, m > 0 -> out of the money
    if m <= -0.03:
        return 0.80
    if m <= -0.01:
        return 0.65
    if m <= 0.01:
        return 0.50
    if m <= 0.025:
        return 0.35
    if m <= 0.05:
        return 0.22
    return 0.12


def pick(chain, spot, side, spot_sl, spot_t1, spot_t2, spot_t3=None,
         entry_spot=None):
    """Choose the best strike and translate spot levels into premium levels.

    Returns None when the chain has nothing tradable — better to say
    "no clean option" than to name an illiquid strike.
    """
    if not chain or not spot:
        return None
    # A zone call triggers at the zone, not at the current price. Level maths
    # must use the trigger price or the risk-reward comes out wrong.
    ref = entry_spot or spot
    book = chain.get("strikes_ce" if side == "CE" else "strikes_pe") or {}
    if not book:
        return None

    def _levels(strike, prem, d):
        """Translate the spot plan into premium levels for one strike."""
        def to_prem(lv, floor=False):
            if lv is None:
                return None
            move = (lv - ref) if side == "CE" else (ref - lv)
            p = prem + d * move
            if floor:
                p = max(p, prem * 0.60)   # never show a stop worse than -40%
            return round(max(p, 0.5), 2)
        return (to_prem(spot_sl, floor=True), to_prem(spot_t1),
                to_prem(spot_t2), to_prem(spot_t3) if spot_t3 else None)

    best, best_score = None, -1
    for k, v in book.items():
        try:
            strike = float(k)
            prem = float(v.get("ltp") or 0)
        except Exception:
            continue
        if prem < MIN_PREMIUM or prem > spot * MAX_PREMIUM_PCT:
            continue
        oi = float(v.get("oi") or 0)
        vol = float(v.get("volume") or 0)
        d = _delta(spot, strike, side)
        p_sl, p_t1, p_t2, p_t3 = _levels(strike, prem, d)
        if not p_t1 or p_t1 <= prem:
            continue
        risk = prem - p_sl
        if risk <= 0:
            continue
        rr = (p_t1 - prem) / risk

        # Rank on the trade itself, not on delta alone. A deep ITM strike has
        # the best delta but the worst risk-reward once the stop floor
        # applies, which is why an earlier version kept picking it.
        score = rr * 40
        if rr < 1.0:
            score -= 40                   # risking more than the first target
        if 0.35 <= d <= 0.60:
            score += 20                   # near the money
        if oi > 0:
            score += min(15, oi / 60000)
        if vol > 0:
            score += min(12, vol / 25000)
        if prem < 15:
            score -= 12                   # cheap options decay fast
        if score > best_score:
            best_score, best = score, (strike, prem, d, oi, vol,
                                       p_sl, p_t1, p_t2, p_t3)

    if not best:
        return None
    strike, prem, d, oi, vol, p_sl, p_t1, p_t2, p_t3 = best
    risk = max(prem - p_sl, 0.01)
    reward = max((p_t1 or prem) - prem, 0.01)

    moneyness = ("ATM" if abs(strike - spot) / spot <= 0.01
                 else "OTM" if (strike > spot) == (side == "CE") else "ITM")

    return {
        "symbol": f"{chain.get('name', '')} {int(strike)} {side}".strip(),
        "strike": int(strike), "side": side, "moneyness": moneyness,
        "expiry": chain.get("expiry", ""),
        "entry": round(prem, 2),
        "sl": p_sl, "t1": p_t1, "t2": p_t2, "t3": p_t3,
        "sl_pct": round((p_sl - prem) / prem * 100, 1),
        "t1_pct": round(((p_t1 or prem) - prem) / prem * 100, 1),
        "t2_pct": round(((p_t2 or prem) - prem) / prem * 100, 1),
        "t3_pct": round(((p_t3 or prem) - prem) / prem * 100, 1) if p_t3 else None,
        "rr": round(reward / risk, 1),
        "delta": d, "oi": int(oi), "volume": int(vol),
        "why": f"{moneyness} · delta about {d:.2f} · premium {prem:.1f}",
        "note": ("Premium levels are derived from the spot targets using an "
                 "estimated delta. Check the live premium and spread before "
                 "entering."),
    }


def premium_map(picks):
    """{"COFORGE 1800 PE": 42.5} so the tracker can mark hits on premium."""
    out = {}
    for p in picks or []:
        if p and p.get("symbol") and p.get("entry"):
            out[p["symbol"]] = p["entry"]
    return out
