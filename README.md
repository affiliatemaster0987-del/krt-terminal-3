# KRT AI Terminal — Render Deploy Guide

## இது என்ன
Flask + Angel One SmartAPI live market terminal.
- API credentials கொடுத்தா → LIVE data (green dot)
- கொடுக்காட்டி → DEMO mode (gold dot) — site எப்பவும் வேலை செய்யும்

## Render-ல deploy பண்ற steps

### 1. GitHub-ல upload
இந்த folder-ஐ அப்படியே ஒரு GitHub repo-ல push பண்ணுங்க (எல்லா files-ும், folder structure மாறாம).

### 2. Render-ல புது service
- dashboard.render.com → New → **Web Service** (Static Site இல்ல!)
- உங்க GitHub repo-ஐ connect பண்ணுங்க
- Build Command : `pip install -r requirements.txt`
- Start Command : `gunicorn app:app --bind 0.0.0.0:$PORT`
- Plan: Free

### 3. Live data வேணும்னா — Environment Variables
Render → உங்க service → Environment → இந்த 4-ஐ add பண்ணுங்க:

| Key | Value |
|---|---|
| SMARTAPI_KEY | உங்க API key (chat-ல share பண்ணாதீங்க!) |
| SMARTAPI_CLIENT | Angel One client code (eg: A123456) |
| SMARTAPI_PIN | உங்க MPIN |
| SMARTAPI_TOTP | TOTP secret (smartapi.angelone.in/enable-totp-ல கிடைத்த token) |

⚠️ பழைய leak ஆன key-ஐ delete பண்ணி **புது key** create பண்ணி use பண்ணுங்க.

### 4. Deploy → Open URL
Deploy முடிஞ்சதும் URL open பண்ணுங்க. Header-ல:
- 🟢 LIVE · ANGEL ONE = real data
- 🟡 DEMO MODE = credentials இல்ல / market closed / login fail (Logs பாருங்க)

## Notes
- Market hours (9:15–15:30 IST) தான் live ticks நகரும்
- Free Render plan 15 நிமிஷம் idle-னா தூங்கும் — first load slow-ஆ இருக்கும்
- Watchlist மாத்த: `smart_client.py` → WATCHLIST (token = Angel One instrument master file-ல இருக்கு)
- இது educational/personal tool. Public-ஆ calls கொடுத்தா SEBI RA registration கட்டாயம்.

## v2 — புது features
### 1. Chartink Alerts (உங்க scanner alerts terminal-ல வர)
Chartink → உங்க Scan → Create/Edit Alert → **Webhook URL**:
`https://YOUR-APP.onrender.com/webhook/chartink`
(Chartink-ல webhook alert அவங்க paid plan-ல இருக்கு. Alert fire ஆனதும் terminal + Telegram ரெண்டுலயும் வரும்.)

### 2. Telegram Push Notifications
1. Telegram-ல **@BotFather** → /newbot → token கிடைக்கும்
2. **@userinfobot**-க்கு Hi சொல்லுங்க → உங்க chat id கிடைக்கும்
3. உங்க bot-ஐ ஒரு தடவை open பண்ணி /start அனுப்புங்க
4. Render → Environment → add:
   - TELEGRAM_BOT_TOKEN = (token)
   - TELEGRAM_CHAT_ID = (chat id)

### 3. Breakout/Breakdown + High Conviction
- Angel One previous-day candles வெச்சு PDH/PDL break auto-detect (15s refresh)
- Score ≥ 70 = High Conviction → Telegram push (live mode-ல, ஒரு நாளைக்கு ஒரு stock-க்கு ஒரு தடவை மட்டும்)

### 4. News AI
- Moneycontrol + ET Markets RSS (free) → sentiment tag + impact score, 90s refresh

## v3 — AI Engine
- **/api/ai** — AI Trade Scores, Best Call, RVol, Sectors, Breadth
- **AI Best Call** : score ≥ 75 வந்தா மட்டும் call generate ஆகும்; ≥ 85-ல் Telegram push (daily once)
- **Chartink Smart Filter** : alert வந்ததும் BUY / SELL / WATCH / AVOID auto-classify + reasons
- **Relative Volume** : today volume ÷ 20-day average
- Indicators: SMA20 trend, RSI(14), PDH/PDL, RVol, momentum, news sentiment
- ⚠️ Calls = educational signals only. Selling calls publicly needs SEBI RA registration.

## v4 — KRT JACKPOTS
- UI-ல Chartink பெயர் இல்ல — "KRT Jackpots Alerts" / "LIVE JACKPOT SIGNAL"
- Scanner alert → AI confirm → **CE/PE ATM strike + Entry zone + T1/T2/T3 + SL** auto-generate
- Premium: default estimate (est.). Live option premium வேணும்னா Render env-ல `OPTIONS_LIVE=1`
  (instrument master daily download — free tier-ல first load 1-2 min slow ஆகலாம்)
- **News Jackpots**: Positive news (impact ≥ 7) + AI score ≥ 65 → CALL-WORTHY ✅ / WAIT
- News refresh 90s → 45s
- ⚠️ Options high-risk. Calls = educational. Public-ஆ sell பண்ண SEBI RA கட்டாயம்.
