"""
KRT — Telegram push notifications
Env vars (Render → Environment):
  TELEGRAM_BOT_TOKEN = BotFather-லேர்ந்து கிடைக்கும் token
  TELEGRAM_CHAT_ID   = உங்க chat id (@userinfobot-ல தெரியும்)
இல்லைனா silently skip ஆகும் — app crash ஆகாது.
"""
import os, json, threading
import urllib.request


def _send(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat, "text": text,
                           "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=8)
    except Exception as e:
        print("telegram error:", e)


def notify(text):
    """Fire-and-forget push (background thread, non-blocking)."""
    threading.Thread(target=_send, args=(text,), daemon=True).start()
