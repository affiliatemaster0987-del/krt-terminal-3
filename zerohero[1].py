"""
KRT · ZERO TO HERO
══════════════════
The trade you asked about: SENSEX 77200 PE going 51 → 500 after 3pm on expiry
day. A cheap far-OTM option that expires today is worth almost nothing because
the market says it will not get there. When the index does get there, the
option stops being a lottery ticket and becomes intrinsic value, and the
premium multiplies instead of adding.

WHAT MAKES ONE OF THESE, AND WHAT DOES NOT
This only ever works when four things are true at once:

  1. EXPIRY TODAY        — no overnight risk to price in, so the premium is
                           almost pure "will it travel" money.
  2. LATE SESSION        — after about 1:30. Earlier the option still carries
                           time value, so the multiple is far smaller.
  3. THE INDEX IS MOVING — a real directional leg, not chop. Measured on the
                           last 15 candles, not on the day change.
  4. THE STRIKE IS REACHABLE — close enough that the current speed can carry
                           price through it in the time left.

WHY MOST OF THESE LOSE
Be honest about this: the same cheap option that can do 10x is worthless at
3:30 far more often than not. It goes to zero on most days. The setup is only
worth taking when the move is already underway and the strike is genuinely
within reach — which is exactly what this module tries to measure, and why it
returns nothing on most days.

WHAT "INSTITUTIONAL" LOOKS LIKE HERE
Not a secret feed. It is visible in the option chain: open interest at a
strike falling while price advances towards it means writers are buying back
what they sold, which is the squeeze that produces the violent leg.
"""

from datetime import datetime, timedelta

IST = lambda: datetime.utcnow() + timedelta(hours=5, minutes=30)

# A far-OTM option that has any hope of moving is cheap but not dust.
MIN_PREMIUM = 3.0
MAX_PREMIUM = 90.0
EARLIEST_MIN = 13 * 60 + 15        # 1:15 pm — before this, time value is fat
LATEST_MIN = 15 * 60 + 5           # 3:05 pm — after this there is no runway


def _mins():
    n = IST()
    return n.hour * 60 + n.minute


def _velocity(candles, n=15):
    """Index points per minute over the recent leg, signed."""
    cs = (candles or [])[-n:]
    if len(cs) < 6:
        return 0.0
    return (cs[-1]["c"] - cs[0]["c"]) / len(cs)


def _straight(candles, n=15):
    """How one-directional the leg is: 1.0 = every candle the same way."""
    cs = (candles or [])[-n:]
    if len(cs) < 6:
        return 0.0
    ups = sum(1 for a, b in zip(cs, cs[1:]) if b["c"] > a["c"])
    downs = len(cs) - 1 - ups
    return abs(ups - downs) / max(len(cs) - 1, 1)


def _oi_unwind(chain, strike, side):
    """Writers buying back at this strike -> the squeeze that pays.

    Returns a small score, not a verdict: OI change is one clue, never proof.
    """
    book = chain.get("strikes_ce" if side == "CE" else "strikes_pe") or {}
    for k in (str(strike), str(float(strike)), str(int(strike))):
        if k in book:
            chg = float(book[k].get("chg") or 0)
            if chg < 0:
                return min(18, abs(chg) / 4000)
            return 0
    return 0


def find(name, spot, chain, candles, expiry_today, step=None):
    """Return zero-to-hero candidates for one underlying, best first.

    Returns [] far more often than not. That is the correct answer on a day
    with no strong late leg, and pretending otherwise would be the whole
    problem with a setup like this.
    """
    if not expiry_today or not chain or not spot:
        return []
    m = _mins()
    if not (EARLIEST_MIN <= m <= LATEST_MIN):
        return []

    left = LATEST_MIN + 25 - m               # minutes of runway to 3:30
    vel = _velocity(candles)
    straight = _straight(candles)
    if abs(vel) < (spot * 0.00004) or straight < 0.45:
        return []                            # no real leg, no lottery

    side = "CE" if vel > 0 else "PE"
    book = chain.get("strikes_ce" if side == "CE" else "strikes_pe") or {}
    if not book:
        return []
    step = step or chain.get("step") or max(spot * 0.001, 25)

    # How far can this speed plausibly carry price in the time that is left?
    reach = abs(vel) * left

    out = []
    for k, v in book.items():
        try:
            strike = float(k)
            prem = float(v.get("ltp") or 0)
        except Exception:
            continue
        if prem < MIN_PREMIUM or prem > MAX_PREMIUM:
            continue
        # distance price must still travel to put this strike in the money
        need = (strike - spot) if side == "CE" else (spot - strike)
        if need <= 0:
            continue                          # already ITM, not a zero-to-hero
        if need > reach:
            continue                          # unreachable at the current pace

        travel = need / reach                 # 0 = at the money, 1 = just reachable
        oi = float(v.get("oi") or 0)
        vol = float(v.get("vol") or v.get("volume") or 0)

        # Intrinsic value if price reaches the strike plus the same distance
        # again — the realistic good case, not the dream case.
        target_spot = spot + (reach if side == "CE" else -reach)
        intrinsic = max((target_spot - strike) if side == "CE"
                        else (strike - target_spot), 0)
        mult = round((intrinsic + prem * 0.2) / prem, 1) if prem else 0
        if mult < 2.5:
            continue                          # not worth the near-certain zero

        score = 0
        score += min(30, abs(vel) / (spot * 0.00004) * 10)   # speed
        score += straight * 20                                # cleanliness
        score += max(0, 20 - travel * 20)                     # closeness
        score += _oi_unwind(chain, strike, side)              # writer squeeze
        score += min(8, vol / 50000) + min(6, oi / 200000)    # liquidity
        score = int(min(99, score))
        if score < 55:
            continue

        out.append({
            "symbol": f"{name} {int(strike)} {side}",
            "underlying": name, "strike": int(strike), "side": side,
            "entry": round(prem, 2),
            "spot": round(spot, 2),
            "needs": round(need, 1),
            "reach": round(reach, 1),
            "mult": mult,
            "target": round(prem * mult, 1),
            "sl": round(prem * 0.5, 1),        # half the premium, nothing clever
            "score": score,
            "oi": int(oi), "volume": int(vol),
            "why": (f"index moving {abs(vel):.1f} pts/min, {int(straight*100)}% "
                    f"one-way · needs {need:.0f} pts, pace allows {reach:.0f}"),
            "risk": ("Expiry lottery. This premium goes to zero if the move "
                     "stalls, which is the usual outcome. Position size must "
                     "assume a total loss."),
            "at": IST().strftime("%H:%M"),
            "left": left,
        })

    out.sort(key=lambda x: -x["score"])
    return out[:3]


def scan(index_rows, chains, candles_map, expiry_map, steps=None):
    """Run every index and return the combined list, strongest first."""
    picks = []
    for r in index_rows or []:
        nm = r.get("symbol")
        ch = (chains or {}).get(nm)
        if not ch:
            continue
        picks += find(nm, r.get("ltp"), ch,
                      (candles_map or {}).get(nm, []),
                      (expiry_map or {}).get(nm, False),
                      (steps or {}).get(nm))
    picks.sort(key=lambda x: -x["score"])
    return picks[:5]
