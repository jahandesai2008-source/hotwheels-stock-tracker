import os
import urllib.request
import urllib.parse
import json
import sys

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("Telegram secrets are missing.")

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message
    }).encode()

    request = urllib.request.Request(url, data=data)

    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode())

    if not result.get("ok"):
        raise RuntimeError("Telegram message failed.")

    print("Telegram message sent successfully.")

if __name__ == "__main__":
    send_telegram(
        "Hot Wheels Tracker: GitHub connection successful! "
        "Retailer stock monitoring is not active yet."
  )
