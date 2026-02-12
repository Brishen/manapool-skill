import os
import sys
import requests
import urllib.parse

BASE_URL = "https://manapool.com/api/v1"

def get_headers():
    token = os.environ.get("MANAPOOL_API_TOKEN")
    email = os.environ.get("MANAPOOL_API_EMAIL")

    if not token or not email:
        # In a library/package, it's better to raise an exception than sys.exit
        # But for CLI usage, we can handle it in the CLI or here.
        # I'll raise an error here and handle it in CLI.
        raise ValueError("Both MANAPOOL_API_TOKEN and MANAPOOL_API_EMAIL environment variables must be set.")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-ManaPool-Access-Token": token,
        "X-ManaPool-Email": email
    }
    return headers

def make_request(path, method="GET", params=None, data=None):
    url = f"{BASE_URL}{path}"

    # requests handles params encoding, but the original script handled list params specifically.
    # requests handles lists in params by repeating keys (e.g. ?ids=1&ids=2) if passed as a list.
    # The original script does: for k, v in params.items(): ... query.append((k, item))
    # This is standard requests behavior too.

    headers = get_headers()

    try:
        resp = requests.request(method, url, headers=headers, params=params, json=data)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        # Try to get error body
        try:
            error_body = e.response.text
            print(f"HTTP Error {e.response.status_code}: {error_body}", file=sys.stderr)
        except:
            print(f"HTTP Error {e}", file=sys.stderr)
        raise e
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise e

def search_singles(query_params):
    return make_request("/products/singles", params=query_params)

def search_sealed(query_params):
    return make_request("/products/sealed", params=query_params)

def get_prices(category):
    return make_request(f"/prices/{category}")

def optimize_cart(cart_data):
    return make_request("/buyer/optimizer", method="POST", data=cart_data)

def get_seller_inventory(params):
    return make_request("/seller/inventory", params=params)

def get_lowest_price(item):
    stats = item.get("market_stats")
    if not stats: return None

    # Safely get product details
    product_single = item.get("product", {}).get("single", {})
    if not product_single: return None

    target_lang = product_single.get("language_id")
    target_cond = product_single.get("condition_id")
    target_finish = product_single.get("finish_id")

    for variant in stats.get("variants", []):
        if (variant.get("language_id") == target_lang and
            variant.get("condition_id") == target_cond and
            variant.get("finish_id") == target_finish):
            return variant.get("low_price")
    return None
