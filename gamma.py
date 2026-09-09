"""
KRT · GAMMA STRATEGY
════════════════════
The idea in one line: the people who sold you the option have to hedge, and
their hedging pushes the stock the same way you are betting.

HOW IT WORKS
When a dealer is short calls and the stock rises, his position loses delta
faster the closer price gets to the strike. To stay flat he must buy stock.
That buying pushes price up, which forces him to buy more. That feedback loop
is a gamma squeeze, and it is why a stock can travel much further than the news
seems to justify.

The mirror is true below the market with puts: short puts, price falls, dealer
sells stock, price falls further.

WHERE THE PRESSURE LIVES
Gamma is highest at the strikes with the most open interest nearest the spot.
Those strikes act like magnets when dealers are long gamma (price gets pinned)
and like accelerators when they are short (price runs). The distinction is what
this module tries to read from change in OI:

    OI RISING at a strike   → fresh writing → dealers getting shorter gamma
                              → price tends to accelerate through
    OI FALLING at a strike  → writers buying back → the squeeze already running

TWO REGIMES, TWO DIFFERENT TRADES
    SQUEEZE  price is approaching a heavy strike with OI unwinding — buy the
             direction, the move usually extends
    PIN      price sits on a heavy strike with OI building and balanced writing
             — the stock gets stuck, directional option buying loses to theta

BE CLEAR ABOUT THE LIMIT
Real gamma exposure needs dealer positioning data that no retail feed carries.
What is measurable here is open interest, its change, and volume — the visible
residue of that positioning. It is a good proxy and it is not the real thing,
so this module returns nothing far more often than it fires.
"""

from datetime import datetime, timedelta

IST = lambda: datetime.utcnow() + timedelta(hours=5, minutes=30)

MIN_WALL_OI = 150000        # a strike below this is not a wall
NEAR_PCT = 0.025            # a wall only matters within 2.5% of spot
MIN_SCORE = 62


def _walls(chain, spot, side):
    """Strikes near spot carrying enough OI to influence hedging."""
    book = chain.get("strikes_ce" if side == "CE" else "strikes_pe") or {}
    out = []
    for k, v in book.items():
        try:
            strike = float(k)
            oi = float(v.get("oi") or 0)
        except Exception:
            continue
        if oi < MIN_WALL_OI:
            continue
        if abs(strike - spot) / spot > NEAR_PCT:
            continue
        out.append({
            "strike": strike, "oi": oi,
            "chg_oi": float(v.get("chg") or 0),
            "vol": float(v.get("vol") or v.get("volume") or 0),
            "ltp": float(v.get("ltp") or 0),
            "dist": abs(strike - spot) / spot,
        })
    out.sort(key=lambda x: -x["oi"])
    return out[:4]


def _gamma_weight(strike, spot, days):
    """Gamma peaks at the money and decays with distance and with time.

    Not the Black-Scholes gamma — a shape that behaves like it, which is all
    that is needed to rank one strike against another.
    """
    d = abs(strike - spot) / spot
    width = max(0.010, 0.022 * (max(days, 0.5) ** 0.5))
    return round(2.718281828 ** (-(d / width) ** 2), 3)


def analyse(symbol, spot, chain, ind=None, days=None):
    """Read the gamma picture for one underlying.

    Returns None when the chain is too thin to say anything, which is the
    honest answer for most mid-cap F&O names.
    """
    if not chain or not spot:
        return None
    ind = ind or {}
    if days is None:
        try:
            d = datetime.strptime(str(chain.get("expiry")), "%d%b%Y").date()
            days = max((d - IST().date()).days, 0)
        except Exception:
            days = 3

    ce_walls, pe_walls = _walls(chain, spot, "CE"), _walls(chain, spot, "PE")
    if not ce_walls and not pe_walls:
        return None

    # Net gamma pressure: call walls above pull price up when they unwind,
    # put walls below push it down. Weight each by how close it is to spot.
    up_force = down_force = 0.0
    for w in ce_walls:
        g = _gamma_weight(w["strike"], spot, days)
        pull = w["oi"] * g
        if w["chg_oi"] < 0:          # writers buying back = squeeze fuel
            up_force += pull * 1.6
        else:                        # fresh writing = resistance overhead
            down_force += pull * 0.5
    for w in pe_walls:
        g = _gamma_weight(w["strike"], spot, days)
        pull = w["oi"] * g
        if w["chg_oi"] < 0:
            down_force += pull * 1.6
        else:
            up_force += pull * 0.5

    total = up_force + down_force
    if total <= 0:
        return None
    tilt = (up_force - down_force) / total        # -1 .. +1

    # The nearest heavy strike is the magnet price is working against.
    magnet = min(ce_walls + pe_walls, key=lambda w: w["dist"])
    at_magnet = magnet["dist"] < 0.004
    building = magnet["chg_oi"] > 0

    if at_magnet and building:
        regime = "PIN"
    elif abs(tilt) > 0.25:
        regime = "SQUEEZE"
    else:
        regime = "NEUTRAL"

    side = "CE" if tilt > 0 else "PE"
    bias = "UP" if tilt > 0 else "DOWN"

    score = 45 + min(30, abs(tilt) * 60)
    if regime == "SQUEEZE":
        score += 12
    if regime == "PIN":
        score -= 20                              # nothing to buy into a pin
    vwap, rsi, adx = ind.get("vwap"), ind.get("rsi"), ind.get("adx")
    if vwap:
        score += 8 if (spot > vwap) == (bias == "UP") else -12
    if adx and adx >= 25:
        score += 6
    if ind.get("htf") == ("up" if bias == "UP" else "down"):
        score += 8
    if days <= 1:
        score += 6                               # gamma is largest at expiry
    score = int(max(5, min(97, score)))

    return {
        "symbol": symbol, "spot": round(spot, 2),
        "regime": regime, "side": side, "bias": bias,
        "tilt": round(tilt, 2),
        "score": score,
        "days_to_expiry": days,
        "magnet": round(magnet["strike"], 2),
        "magnet_oi": int(magnet["oi"]),
        "magnet_chg_oi": int(magnet["chg_oi"]),
        "call_walls": [{"strike": w["strike"], "oi": int(w["oi"]),
                        "chg_oi": int(w["chg_oi"])} for w in ce_walls[:3]],
        "put_walls": [{"strike": w["strike"], "oi": int(w["oi"]),
                       "chg_oi": int(w["chg_oi"])} for w in pe_walls[:3]],
        "action": ("BUY" if bias == "UP" else "SELL") if regime == "SQUEEZE"
                  else "AVOID OPTIONS" if regime == "PIN" else "WAIT",
        "why": _explain(regime, bias, magnet, tilt, days),
        "at": IST().strftime("%I:%M %p").lstrip("0"),
        "note": ("Read from open interest, its change and volume — the visible "
                 "residue of dealer positioning, not the positioning itself, "
                 "which no retail feed carries."),
    }


def _explain(regime, bias, magnet, tilt, days):
    if regime == "PIN":
        return (f"Price is sitting on the {magnet['strike']:g} strike while open "
                f"interest builds there. Writers are defending it, so the stock "
                f"tends to get stuck — directional option buying bleeds to theta.")
    if regime == "SQUEEZE":
        d = "up" if bias == "UP" else "down"
        return (f"Open interest is unwinding at the {magnet['strike']:g} strike "
                f"while price presses into it. Writers buying back have to hedge "
                f"{d}, which extends the move. Gamma tilt {tilt:+.2f}"
                + (", and expiry is close, which makes it sharper." if days <= 1
                   else "."))
    return (f"Call and put walls are roughly balanced around {magnet['strike']:g}. "
            f"No hedging edge either way — wait for one side to unwind.")


def scan(stocks, chains, limit=6):
    """Rank the F&O list by gamma opportunity. Squeezes first, pins excluded."""
    out = []
    for r in stocks or []:
        sym, px = r.get("symbol"), r.get("ltp")
        ch = (chains or {}).get(sym)
        if not sym or not px or not ch:
            continue
        g = analyse(sym, px, ch, r.get("ind") or {})
        if not g or g["score"] < MIN_SCORE:
            continue
        if g["regime"] != "SQUEEZE":
            continue                     # only the tradable regime is shown
        g["sector"] = r.get("sector", "")
        g["chg"] = r.get("chg")
        out.append(g)
    out.sort(key=lambda x: -x["score"])
    return out[:limit]
