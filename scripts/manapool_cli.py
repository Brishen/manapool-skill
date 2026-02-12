#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import argparse

BASE_URL = "https://manapool.com/api/v1"

def get_headers():
    token = os.environ.get("MANAPOOL_API_TOKEN")
    email = os.environ.get("MANAPOOL_API_EMAIL")

    if not token or not email:
        print("Error: Both MANAPOOL_API_TOKEN and MANAPOOL_API_EMAIL environment variables must be set.", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-ManaPool-Access-Token": token,
        "X-ManaPool-Email": email
    }
    return headers

def make_request(path, method="GET", params=None, data=None):
    url = f"{BASE_URL}{path}"
    if params:
        query = []
        for k, v in params.items():
            if v is None: continue
            if isinstance(v, list):
                for item in v:
                    query.append((k, item))
            else:
                query.append((k, v))
        if query:
            url += "?" + urllib.parse.urlencode(query)

    req = urllib.request.Request(url, method=method, headers=get_headers())

    if data:
        req.data = json.dumps(data).encode("utf-8")

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"HTTP Error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

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

def main():
    parser = argparse.ArgumentParser(description="Manapool API CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Search Singles
    search_s = subparsers.add_parser("search-singles")
    search_s.add_argument("--scryfall-ids", nargs="+")
    search_s.add_argument("--tcgplayer-ids", nargs="+")
    search_s.add_argument("--product-ids", nargs="+")

    # Search Sealed
    search_z = subparsers.add_parser("search-sealed")
    search_z.add_argument("--tcgplayer-ids", nargs="+")
    search_z.add_argument("--product-ids", nargs="+")

    # Prices
    prices = subparsers.add_parser("prices")
    prices.add_argument("category", choices=["singles", "sealed", "variants"])

    # Optimize
    optimize = subparsers.add_parser("optimize")
    optimize.add_argument("file", help="Path to JSON file containing cart data")

    # Seller Inventory
    seller_inv = subparsers.add_parser("seller-inventory")
    seller_inv.add_argument("--limit", type=int, default=100)
    seller_inv.add_argument("--offset", type=int, default=0)
    seller_inv.add_argument("--min-quantity", type=int)
    seller_inv.add_argument("--stats", action="store_true", help="Include market stats for each item")
    seller_inv.add_argument("--summary", action="store_true", help="Print a human-readable summary")

    # Update Price - CHANGED: Quantity is now required to prevent accidents
    update_p = subparsers.add_parser("update-price")
    update_p.add_argument("--sku", required=True, help="TCGPlayer SKU")
    update_p.add_argument("--price-cents", type=int, required=True, help="Price in cents")
    update_p.add_argument("--quantity", type=int, required=True, help="Quantity (Required to prevent accidental reset)")

    args = parser.parse_known_args()[0]

    # ... [Keep logic for search, prices, optimize] ...
    if args.command == "search-singles":
        params = {}
        if args.scryfall_ids: params["scryfall_ids"] = args.scryfall_ids
        if args.tcgplayer_ids: params["tcgplayer_ids"] = args.tcgplayer_ids
        if args.product_ids: params["product_ids"] = args.product_ids
        print(json.dumps(search_singles(params), indent=2))

    elif args.command == "search-sealed":
        params = {}
        if args.tcgplayer_ids: params["tcgplayer_ids"] = args.tcgplayer_ids
        if args.product_ids: params["product_ids"] = args.product_ids
        print(json.dumps(search_sealed(params), indent=2))

    elif args.command == "prices":
        print(json.dumps(get_prices(args.category), indent=2))

    elif args.command == "optimize":
        with open(args.file, "r") as f:
            cart_data = json.load(f)
        print(json.dumps(optimize_cart(cart_data), indent=2))

    elif args.command == "seller-inventory":
        params = {"limit": args.limit, "offset": args.offset}
        if args.min_quantity is not None: params["minQuantity"] = args.min_quantity
        inventory_resp = get_seller_inventory(params)

        if args.summary:
            print(f"{'Name':<30} {'Set':<10} {'Price':>8} {'Low':>8} {'Qty':>4}")
            print("-" * 65)
            for item in inventory_resp.get("inventory", []):
                p = item.get("product", {})
                single = p.get("single", {})
                name = single.get("name", "Unknown")
                set_code = single.get("set_code", "???")
                price = item.get("price_cents", 0) / 100
                low = get_lowest_price(item)
                low_str = f"{low/100:>8.2f}" if low else "     N/A"
                qty = item.get("quantity", 0)
                print(f"{name[:30]:<30} {set_code:<10} {price:>8.2f} {low_str} {qty:>4}")
        else:
            print(json.dumps(inventory_resp, indent=2))

    elif args.command == "update-price":
        # Placeholder for update-price implementation if needed,
        # but the argparse is already there.
        print("Update price not fully implemented in this script snippet.")

if __name__ == "__main__":
    main()
