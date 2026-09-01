"""
KRT · OPTION ENGINE
═══════════════════
One place that answers, for any signal on the terminal:

    WHAT TO TRADE · WHICH CE/PE · WHICH STRIKE · AT WHAT PREMIUM
    WHAT SL · WHAT T1/T2/T3 · WHAT CONFIDENCE · WHAT DOES OI SAY

Call of the Day, Jackpot Suggest, Top AI Calls, Jackpot List and the breakout
alerts all used to name a strike by rounding the spot price. That is the wrong
strike whenever the nearest one is illiquid, and it never told you the premium,
the OI or whether the contract could actually be traded.

STRIKE SELECTION IS NOT "NEAREST ATM"
A strike is scored on eight things, not one:
    delta band, premium affordability, open interest, change in OI,
    traded volume, bid/ask spread, distance to the expected move, and IV.
A deep ITM strike has the best delta and the worst risk-reward once a stop is
applied; a far OTM strike is cheap and usually expires worthless. The engine
is built to reject both.

ABOUT THE PROBABILITIES
These are estimates from price structure and option positioning, not a
guarantee and not a pricing model. A 70% reading means the evidence leans that
way, and roughly three of ten such setups will still fail. Treat them as a
ranking tool between setups, never as a promise about one trade.

IV WITHOUT A GREEKS FEED
Angel does not publish IV on this endpoint, so it is backed out from the
premium with a compact Black-Scholes inversion. It is close enough to compare
strikes against each other, which is all it is used for.
"""

import math
from datetime import datetime, timedelta

IST = lambda: datetime.utcnow() + timedelta(hours=5, minutes=30)

MIN_PREMIUM = 3.0          # below this the spread eats the trade
MAX_PREMIUM_PCT = 0.06     # premium above 6% of spot is too expensive to hold
MIN_OI = 20000             # thinner than this and the exit is a problem


# ────────────────────────── maths helpers ──────────────────────────
def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs_price(spot, strike, t, vol, side):
    """Black-Scholes with zero rate — enough to invert for IV."""
    if t <= 0 or vol <= 0 or spot <= 0 or strike <= 0:
        return max((spot - strike) if side == "CE" else (strike - spot), 0.0)
    d1 = (math.log(spot / strike) + 0.5 * vol * vol * t) / (vol * math.sqrt(t))
    d2 = d1 - vol * math.sqrt(t)
    if side == "CE":
        return spot * _norm_cdf(d1) - strike * _norm_cdf(d2)
    return strike * _norm_cdf(-d2) - spot * _norm_cdf(-d1)


def implied_vol(spot, strike, premium, days, side):
    """Back IV out of the premium by bisection. None when it cannot converge."""
    try:
        t = max(days, 0.5) / 365.0
        lo, hi = 0.01, 5.0
        intrinsic = max((spot - strike) if side == "CE" else (strike - spot), 0)
        if premium <= intrinsic:
            return None
        for _ in range(60):
            mid = (lo + hi) / 2
            if _bs_price(spot, strike, t, mid, side) > premium:
                hi = mid
            else:
                lo = mid
        iv = (lo + hi) / 2
        return round(iv * 100, 1) if 1 < iv * 100 < 300 else None
    except Exception:
        return None


def delta_of(spot, strike, days, iv_pct, side):
    """True BS delta when IV is known, moneyness approximation otherwise."""
    try:
        if iv_pct and iv_pct > 0:
            t = max(days, 0.5) / 365.0
            v = iv_pct / 100.0
            d1 = (math.log(spot / strike) + 0.5 * v * v * t) / (v * math.sqrt(t))
            d = _norm_cdf(d1)
            return round(d if side == "CE" else d - 1, 3)
    except Exception:
        pass
    m = (strike - spot) / spot if side == "CE" else (spot - strike) / spot
    approx = 0.80 if m <= -0.03 else 0.65 if m <= -0.01 else 0.50 \
        if m <= 0.01 else 0.35 if m <= 0.025 else 0.22 if m <= 0.05 else 0.12
    return round(approx if side == "CE" else -approx, 3)


def _days_to_expiry(expiry):
    try:
        d = datetime.strptime(str(expiry), "%d%b%Y").date()
        return max((d - IST().date()).days, 0)
    except Exception:
        return 3


# ────────────────────────── probability ──────────────────────────
def move_probability(ind, chain, side_bias):
    """Chance the underlying keeps going the signalled way, 0-100.

    Built from six pieces of evidence that each carry a different weight.
    Deliberately capped: nothing here justifies a number above the high 80s.
    """
    ind = ind or {}
    score, seen = 50.0, []

    rsi = ind.get("rsi")
    if rsi is not None:
        if side_bias == "UP":
            if 55 <= rsi <= 72: score += 8;  seen.append(f"RSI {rsi}")
            elif rsi > 78:      score -= 6;  seen.append(f"RSI {rsi} overbought")
            elif rsi < 45:      score -= 8
        else:
            if 28 <= rsi <= 45: score += 8;  seen.append(f"RSI {rsi}")
            elif rsi < 22:      score -= 6;  seen.append(f"RSI {rsi} oversold")
            elif rsi > 55:      score -= 8

    adx = ind.get("adx")
    if adx:
        if adx >= 35: score += 10; seen.append(f"ADX {adx} strong trend")
        elif adx >= 25: score += 5; seen.append(f"ADX {adx}")
        elif adx < 18: score -= 6; seen.append(f"ADX {adx} choppy")

    htf = ind.get("htf")
    if htf == ("up" if side_bias == "UP" else "down"):
        score += 9; seen.append("15m + 1h aligned")
    elif htf:
        score -= 9; seen.append("higher timeframe against")

    vwap, px = ind.get("vwap"), ind.get("ltp") or ind.get("close")
    if vwap and px:
        above = px > vwap
        if above == (side_bias == "UP"):
            score += 7; seen.append("VWAP on side")
        else:
            score -= 9; seen.append("wrong side of VWAP")

    if chain:
        bias = chain.get("bias")
        if bias == ("BULLISH" if side_bias == "UP" else "BEARISH"):
            score += 10; seen.append(f"{chain.get('writer')} (PCR {chain.get('pcr')})")
        elif bias and bias != "NEUTRAL":
            score -= 12; seen.append(f"option writers against: {chain.get('writer')}")
        mp, sp = chain.get("max_pain"), chain.get("spot")
        if mp and sp:
            if (sp < mp) == (side_bias == "UP"):
                score += 4; seen.append(f"max pain {mp} on side")
            else:
                score -= 4

    return max(5, min(88, round(score))), seen


def premium_rise_probability(move_prob, delta, days, iv_pct):
    """Chance the premium itself gains — not the same as the spot moving.

    Theta and a delta below 1 both eat into it, and on expiry day that gap is
    at its widest. This is why a correct directional read can still lose money
    on the option.
    """
    p = move_prob * (0.55 + 0.45 * min(abs(delta or 0.5) / 0.6, 1.0))
    if days <= 0:
        p -= 12                      # expiry day: theta is brutal
    elif days <= 1:
        p -= 7
    if iv_pct and iv_pct > 60:
        p -= 5                       # rich IV, more to lose on a crush
    return max(5, min(85, round(p)))


# ────────────────────────── strike selection ──────────────────────────
def _spread_quality(v):
    """0-1. Angel gives best bid/ask on FULL quotes; fall back to volume."""
    try:
        bid = float(v.get("bid") or v.get("bestBid") or 0)
        ask = float(v.get("ask") or v.get("bestAsk") or 0)
        ltp = float(v.get("ltp") or 0)
        if bid > 0 and ask > bid and ltp > 0:
            return max(0.0, 1.0 - ((ask - bid) / ltp) / 0.06)
    except Exception:
        pass
    vol = float(v.get("vol") or v.get("volume") or 0)
    return min(1.0, vol / 200000)


def best_strike(chain, spot, side, expected_move=None, ind=None):
    """Pick the tradable strike, not merely the closest one.

    Returns None when nothing in the chain is worth trading — which is a real
    answer, and better than naming a strike nobody can get out of.
    """
    if not chain or not spot:
        return None
    book = chain.get("strikes_ce" if side == "CE" else "strikes_pe") or {}
    if not book:
        return None
    days = _days_to_expiry(chain.get("expiry"))
    exp_move = expected_move or (spot * 0.008)
    und = chain.get("symbol") or chain.get("name") or ""

    best, best_score, rejected = None, -1e9, 0
    for k, v in book.items():
        try:
            strike = float(k)
            prem = float(v.get("ltp") or 0)
        except Exception:
            continue
        if prem < MIN_PREMIUM or prem > spot * MAX_PREMIUM_PCT:
            rejected += 1
            continue
        oi = float(v.get("oi") or 0)
        chg_oi = float(v.get("chg") or 0)
        vol = float(v.get("vol") or v.get("volume") or 0)
        if oi < MIN_OI and vol < 50000:
            rejected += 1
            continue                        # illiquid, skip

        iv = implied_vol(spot, strike, prem, days, side)
        d = delta_of(spot, strike, days, iv, side)
        ad = abs(d)
        spread_q = _spread_quality(v)

        sc = 0.0
        # delta band: 0.35-0.60 is where a directional option actually pays
        sc += 26 - min(26, abs(ad - 0.47) / 0.30 * 26)
        # can the expected move actually reach and pass this strike?
        need = (strike - spot) if side == "CE" else (spot - strike)
        if need > exp_move * 1.6:
            rejected += 1
            continue                        # beyond any realistic move
        sc += 16 - min(16, max(need, 0) / max(exp_move, 1) * 10)
        sc += min(16, oi / 120000 * 16)             # open interest
        sc += min(12, vol / 250000 * 12)            # today's participation
        sc += spread_q * 12                         # exit quality
        if chg_oi > 0:                              # fresh positions building
            sc += min(8, chg_oi / 80000 * 8)
        if prem < 12:
            sc -= 10                                # cheap decays fast
        if iv and iv > 70:
            sc -= 6                                 # paying up for IV
        if sc > best_score:
            best_score, best = sc, dict(
                strike=strike, prem=prem, oi=oi, chg_oi=chg_oi, vol=vol,
                iv=iv, delta=d, spread_q=round(spread_q, 2))

    if not best:
        return None

    strike, prem, d = best["strike"], best["prem"], best["delta"]
    moneyness = ("ATM" if abs(strike - spot) / spot <= 0.006
                 else "OTM" if (strike > spot) == (side == "CE") else "ITM")
    return {
        "symbol": f"{und} {int(strike)} {side}".strip(),
        "underlying": und, "strike": int(strike), "side": side,
        "moneyness": moneyness, "expiry": chain.get("expiry", ""),
        "days_to_expiry": days,
        "ltp": round(prem, 2), "oi": int(best["oi"]),
        "chg_oi": int(best["chg_oi"]),
        "chg_oi_pct": (round(best["chg_oi"] / best["oi"] * 100, 1)
                       if best["oi"] else None),
        "volume": int(best["vol"]), "iv": best["iv"], "delta": d,
        "liquidity": ("GOOD" if best["spread_q"] > .6 else
                      "OK" if best["spread_q"] > .3 else "THIN"),
        "support": chain.get("support"), "resistance": chain.get("resistance"),
        "max_pain": chain.get("max_pain"), "pcr": chain.get("pcr"),
        "writer": chain.get("writer"),
        "strike_score": round(best_score, 1),
        "rejected": rejected,
    }


def premium_levels(pick, spot, spot_sl, spot_t1, spot_t2, spot_t3=None,
                   entry_spot=None):
    """Turn the spot plan into premium levels using the selected strike."""
    if not pick:
        return None
    ref = entry_spot or spot
    d, prem = abs(pick["delta"]) or 0.5, pick["ltp"]
    side = pick["side"]

    def to_prem(lv, floor=False):
        if lv is None:
            return None
        move = (lv - ref) if side == "CE" else (ref - lv)
        p = prem + d * move
        if floor:
            p = max(p, prem * 0.55)     # never show a stop worse than -45%
        return round(max(p, 0.5), 2)

    sl = to_prem(spot_sl, floor=True)
    t1, t2, t3 = to_prem(spot_t1), to_prem(spot_t2), to_prem(spot_t3)
    risk = max(prem - (sl or 0), 0.01)
    return {
        "entry": prem, "sl": sl, "t1": t1, "t2": t2, "t3": t3,
        "sl_pct": round((sl - prem) / prem * 100, 1) if sl else None,
        "t1_pct": round((t1 - prem) / prem * 100, 1) if t1 else None,
        "t2_pct": round((t2 - prem) / prem * 100, 1) if t2 else None,
        "t3_pct": round((t3 - prem) / prem * 100, 1) if t3 else None,
        "rr": round(max((t1 or prem) - prem, 0.01) / risk, 1),
    }


# ────────────────────────── the one entry point ──────────────────────────
def enrich(signal, chain, ind=None, expected_move=None):
    """Attach the full option decision to any signal on the terminal.

    `signal` needs: symbol, side (BUY/SELL), ltp, sl, t1, t2, [t3], [score].
    Returns None when no strike is worth trading, so a card can honestly say
    so instead of inventing a contract.
    """
    if not signal or not chain:
        return None
    side = "CE" if signal.get("side") == "BUY" else "PE"
    spot = signal.get("ltp") or signal.get("entry")
    if not spot:
        return None

    exp_move = expected_move or abs((signal.get("t2") or spot) - spot) or spot * 0.008
    pick = best_strike(chain, spot, side, exp_move, ind)
    if not pick:
        return None

    lv = premium_levels(pick, spot, signal.get("sl"), signal.get("t1"),
                        signal.get("t2"), signal.get("t3"),
                        entry_spot=signal.get("entry"))
    bias = "UP" if side == "CE" else "DOWN"
    prob, why = move_probability({**(ind or {}), "ltp": spot}, chain, bias)
    prem_prob = premium_rise_probability(prob, pick["delta"],
                                         pick["days_to_expiry"], pick["iv"])

    # Confidence blends the signal's own score with how good the contract is.
    base = signal.get("score") or 60
    conf = round(base * 0.55 + prob * 0.30 + min(pick["strike_score"], 80) * 0.15)
    conf = max(5, min(99, conf))

    out = {**pick, **(lv or {}),
           "up_prob": prob if bias == "UP" else 100 - prob,
           "down_prob": 100 - prob if bias == "UP" else prob,
           "move_prob": prob,
           "premium_rise_prob": prem_prob,
           "confidence": conf,
           "why": " · ".join(why[:4]) if why else "structure only",
           "at": IST().strftime("%H:%M"),
           "note": ("Probabilities are estimates from price structure and "
                    "option positioning, not guarantees. Check the live "
                    "premium and spread before entering.")}
    # Only the genuinely rare combinations earn a badge.
    if conf >= 88 and pick["liquidity"] == "GOOD" and (lv or {}).get("rr", 0) >= 1.5:
        out["badge"] = "GOLD"
    elif conf >= 80 and pick["liquidity"] != "THIN":
        out["badge"] = "MUST TRY"
    else:
        out["badge"] = None
    return out
