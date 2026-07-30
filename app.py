"""KRT AI Terminal v2 — Flask server (Render-ready)."""
import os
from flask import Flask, jsonify, render_template, request
from smart_client import build_dashboard
from scanner import scan_breakouts, add_chartink_alert, get_chartink_alerts
from news import get_news, get_news_signals
from ai_engine import build_ai

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():
    try:
        d = build_dashboard()
        d["chartink"] = get_chartink_alerts()
        return jsonify(d)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scanner")
def api_scanner():
    try:
        return jsonify(scan_breakouts())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai")
def api_ai():
    try:
        return jsonify(build_ai())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/news")
def api_news():
    try:
        return jsonify({"items": get_news(), "signals": get_news_signals()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/webhook/chartink", methods=["POST"])
def chartink_webhook():
    """Chartink alert webhook receiver.
    Chartink → Scanner → Create Alert → Webhook URL:
      https://<your-app>.onrender.com/webhook/chartink
    """
    try:
        payload = request.get_json(force=True, silent=True) or {}
        n = add_chartink_alert(payload)
        return jsonify({"status": "ok", "received": n})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
