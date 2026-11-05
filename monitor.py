

    import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# One shared monitor for all seven requested retailers.
# Each retailer is enabled only after an authorized JSON feed is supplied.
RETAILERS = {
    "Blinkit": "BLINKIT",
    "Zepto": "ZEPTO",
    "Swiggy Instamart": "INSTAMART",
    "BigBasket": "BIGBASKET",
    "FirstCry": "FIRSTCRY",
    "Hamleys": "HAMLEYS",
    "Crossword": "CROSSWORD",
}

STATE_FILE = Path("seen_products.json")
TIMEOUT_SECONDS = 25


def telegram_request(method, fields, photo_url=None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Telegram secrets are missing.")

    fields = dict(fields)
    fields["chat_id"] = chat_id

    if photo_url:
        endpoint = f"https://api.telegram.org/bot{token}/sendPhoto"
        fields["photo"] = photo_url
    else:
        endpoint = f"https://api.telegram.org/bot{token}/sendMessage"

    data = urllib.parse.urlencode(fields).encode()
    request = urllib.request.Request(endpoint, data=data)

    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not result.get("ok"):
        raise RuntimeError(f"Telegram {method} request failed.")


def send_alert(product, alert_type):
    label = "NEW HOT WHEELS PRODUCT" if alert_type == "new" else "HOT WHEELS BACK IN STOCK"
    message = (
        f"{label}\n\n"
        f"Product: {product['name']}\n"
        f"Store: {product['retailer']}\n"
        f"Price: {product.get('price') or 'Not listed'}\n"
        f"Link: {product.get('url') or 'Not available'}"
    )

    image = product.get("image")
    try:
        if image:
            telegram_request("sendPhoto", {"caption": message}, image)
        else:
            telegram_request("sendMessage", {"text": message})
    except Exception:
        # If the image URL is unavailable to Telegram, still deliver the alert.
        telegram_request("sendMessage", {"text": message})


def load_state():
    if not STATE_FILE.exists():
        return None
    with STATE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def is_hot_wheels(item):
    searchable = " ".join(
        str(item.get(key, ""))
        for key in ("name", "brand", "category", "description", "manufacturer")
    ).lower()
    return "hot wheels" in searchable or "hotwheels" in searchable


def normalize_product(raw, retailer):
    name = str(raw.get("name") or raw.get("title") or "").strip()
    if not name:
        return None

    raw_stock = raw.get("in_stock", raw.get("available", raw.get("is_available", False)))
    if isinstance(raw_stock, str):
        in_stock = raw_stock.strip().lower() in {
            "1", "true", "yes", "in stock", "available"
        }
    else:
        in_stock = bool(raw_stock)

    product_id = raw.get("id") or raw.get("sku") or raw.get("product_id") or raw.get("url")
    if not product_id:
        return None

    return {
        "id": f"{retailer.lower().replace(' ', '-')}-{product_id}",
        "name": name,
        "retailer": retailer,
        "price": raw.get("price") or raw.get("selling_price"),
        "url": raw.get("url") or raw.get("product_url"),
        "image": raw.get("image") or raw.get("image_url"),
        "in_stock": in_stock,
    }


def fetch_feed(retailer, prefix):
    feed_url = os.environ.get(f"{prefix}_FEED_URL")
    if not feed_url:
        print(f"{retailer}: skipped (authorized feed URL not configured).")
        return []

    headers = {"Accept": "application/json", "User-Agent": "HotWheelsStockMonitor/1.0"}
    api_token = os.environ.get(f"{prefix}_API_TOKEN")
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    request = urllib.request.Request(feed_url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"{retailer}: feed error ({type(error).__name__}).")
        return []

    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("products"), list):
        rows = payload["products"]
    else:
        print(f"{retailer}: unsupported feed format; expected a list or a products list.")
        return []

    products = []
    for row in rows:
        if not isinstance(row, dict) or not is_hot_wheels(row):
            continue
        product = normalize_product(row, retailer)
        if product:
            products.append(product)

    print(f"{retailer}: received {len(products)} Hot Wheels products.")
    return products


def main():
    current = {}
    configured = 0

    for retailer, prefix in RETAILERS.items():
        if os.environ.get(f"{prefix}_FEED_URL"):
            configured += 1
        for product in fetch_feed(retailer, prefix):
            current[product["id"]] = product

    if configured == 0:
        print("No retailer feeds are configured yet. No live stock checks were performed.")
        return

    previous = load_state()
    if previous is None:
        save_state(current)
        print("Initial baseline saved; no alerts sent on the first run.")
        return

    alerts_sent = 0
    for product_id, product in current.items():
        old = previous.get(product_id)

        if old is None and product["in_stock"]:
            send_alert(product, "new")
            alerts_sent += 1
        elif old and not old.get("in_stock") and product["in_stock"]:
            send_alert(product, "restock")
            alerts_sent += 1

    save_state(current)
    print(
        f"Checked {len(current)} products from {configured} configured retailer feed(s); "
        f"sent {alerts_sent} alert(s)."
    )


if __name__ == "__main__":
    main()

