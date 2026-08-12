"""KRT — Chartink webhook store (keeps full payload)."""
from datetime import datetime, timedelta

_alerts = []


def _ist():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


def add_chartink_alert(payload):
    """Chartink alert-a apadiye store pannum — ella key-yum keep agum."""
    p = dict(payload or {})
    stocks = p.get("stocks") or p.get("symbols") or p.get("stock") or ""
    if isinstance(stocks, list):
        stocks = ", ".join(str(x) for x in stocks)
    name = (p.get("scan_name") or p.get("alert_name") or p.get("scanName")
            or p.get("name") or p.get("scan_url") or "Chartink scan")
    row = dict(p)
    row.update({
        "scan_name": str(name),
        "stocks": str(stocks),
        "trigger_prices": p.get("trigger_prices") or p.get("triggerPrices") or "",
        "triggered_at": p.get("triggered_at") or _ist().strftime("%H:%M:%S"),
        "raw_keys": list(p.keys()),
    })
    _alerts.append(row)
    del _alerts[:-200]
    print("[chartink]", row["scan_name"], "->", row["stocks"][:80], "| keys:", row["raw_keys"])
    return len(stocks.split(",")) if stocks else 0


def get_chartink_alerts():
    return _alerts[-60:]


def scan_breakouts():
    return {"alerts": _alerts[-60:], "count": len(_alerts)}
