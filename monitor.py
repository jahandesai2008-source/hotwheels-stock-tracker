
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

PRODUCTS_FILE = Path("products.json")
STATE_FILE = Path("seen_products.json")


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


def load_json(path, default):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main():
    if not PRODUCTS_FILE.exists():
        raise RuntimeError("products.json has not been created yet.")

    products = load_json(PRODUCTS_FILE, [])
    previous = load_json(STATE_FILE, None)

    current = {}

    for product in products:
        product_id = str(product["id"])
        current[product_id] = product

    # First run: save a baseline without sending false alerts.
    if previous is None:
        STATE_FILE.write_text(
            json.dumps(current, indent=2),
            encoding="utf-8"
        )
        print("Initial product baseline saved.")
        return

    for product_id, product in current.items():
        old = previous.get(product_id)
        available = bool(product.get("in_stock"))

        if old is None and available:
            message = (
                "New Hot Wheels product found!\n\n"
                f"Product: {product['name']}\n"
                f"Store: {product['retailer']}\n"
                f"Price: {product.get('price', 'Not listed')}\n"
                f"Link: {product.get('url', 'Not available')}"
            )
            send_telegram(message)

        elif old and not old.get("in_stock") and available:
            message = (
                "Hot Wheels back in stock!\n\n"
                f"Product: {product['name']}\n"
                f"Store: {product['retailer']}\n"
                f"Price: {product.get('price', 'Not listed')}\n"
                f"Link: {product.get('url', 'Not available')}"
            )
            send_telegram(message)

    STATE_FILE.write_text(
        json.dumps(current, indent=2),
        encoding="utf-8"
    )

    print(f"Checked {len(current)} products.")


if __name__ == "__main__":
    main()
    
