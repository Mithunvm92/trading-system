"""
LAYER 4: NOTIFICATION SYSTEM
Runs: Daily 9:30 AM
Purpose: Update Google Sheets and send alerts
"""

import pandas as pd
import json
import requests
from datetime import datetime
import os

OUTPUT_DIR = "output/"
LOG_FILE = f"logs/notification_{datetime.now().strftime('%Y%m%d')}.txt"

# ═══════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════

def log(message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {message}"
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

# ═══════════════════════════════════════════════════════
# SAFE CREDENTIAL LOADER
# ═══════════════════════════════════════════════════════

def load_credentials():
    creds_file = "config/credentials.json"

    if not os.path.exists(creds_file):
        log("credentials.json not found – notifications disabled")
        return {}

    try:
        with open(creds_file, "r") as f:
            content = f.read().strip()
            if not content:
                log("credentials.json is empty – notifications disabled")
                return {}
            return json.loads(content)
    except Exception as e:
        log(f"Invalid credentials.json – notifications disabled ({e})")
        return {}

CREDS = load_credentials()

TELEGRAM_BOT_TOKEN = CREDS.get("telegram_bot_token")
TELEGRAM_CHAT_ID = CREDS.get("telegram_chat_id")

# ═══════════════════════════════════════════════════════
# TELEGRAM NOTIFICATION
# ═══════════════════════════════════════════════════════

def send_telegram_alert(signals):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("Telegram not configured – skipping")
        return

    try:
        message = f"📊 *TRADE SIGNALS – {datetime.now().strftime('%d %b %Y')}*\n\n"

        for _, row in signals.iterrows():
            message += (
                f"*{row['Stock']}*\n"
                f"Entry: ₹{row['Entry']}\n"
                f"SL: ₹{row['SL']}\n"
                f"T1: ₹{row['T1']}\n"
                f"T2: ₹{row['T2']}\n"
                f"Qty: {row['Quantity']} | RR: {row['RR']}\n\n"
            )

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        r = requests.post(url, data=payload, timeout=10)
        if r.status_code == 200:
            log("Telegram alert sent")
        else:
            log(f"Telegram error: {r.text}")

    except Exception as e:
        log(f"Telegram send failed: {e}")

# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    log("=" * 60)
    log("STARTING NOTIFICATION")
    log("=" * 60)

    today = datetime.now().strftime("%Y%m%d")
    file = f"{OUTPUT_DIR}daily_signals_{today}.csv"

    try:
        signals = pd.read_csv(file)
        log(f"Loaded {len(signals)} signals")
    except:
        log("No signals file found – nothing to notify")
        return

    send_telegram_alert(signals)

    log("=" * 60)
    log("NOTIFICATION COMPLETE")
    log("=" * 60)

if __name__ == "__main__":
    main()
