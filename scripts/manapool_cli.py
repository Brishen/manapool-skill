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

def format_price(cents):
    if cents is None:
        return "N/A"
    return f"${cents/100:.2f}"

def handle_lowest_prices(args):
    params = {}
    if args.scryfall_ids: params.setdefault("scryfall_ids", []).extend(args.scryfall_ids)
    if args.tcgplayer_ids: params.setdefault("tcgplayer_ids", []).extend(args.tcgplayer_ids)
    if args.product_ids: params.setdefault("product_ids", []).extend(args.product_ids)

    if args.inventory_file:
        try:
            with open(args.inventory_file, "r") as f:
                inv_data = json.load(f)

            # Extract scryfall_ids from inventory
            inventory = inv_data.get("inventory", [])
            scryfall_ids = []
            for item in inventory:
                s_id = item.get("product", {}).get("single", {}).get("scryfall_id")
                if s_id:
                    scryfall_ids.append(s_id)

            if scryfall_ids:
                # Deduplicate
                scryfall_ids = list(set(scryfall_ids))
                params.setdefault("scryfall_ids", []).extend(scryfall_ids)
        except Exception as e:
            print(f"Error reading inventory file: {e}", file=sys.stderr)
            return

    if not params:
        print("Error: Must provide at least one search parameter (--scryfall-ids, --tcgplayer-ids, --product-ids, --inventory-file).", file=sys.stderr)
        return

    # Process Scryfall IDs in batches of 100
    all_data = []

    # Collect all IDs to fetch
    s_ids = params.get("scryfall_ids", [])
    t_ids = params.get("tcgplayer_ids", [])
    p_ids = params.get("product_ids", [])

    # If mixed params are present, the API says "Only one of... may be provided".
    # So we should prioritize or split calls.
    # For now, let's prioritize explicit arguments if mixed, or handle them sequentially.
    # Actually, the user might provide multiple.
    # The current implementation of make_request handles list params, but search_singles docs say:
    # "Only one of scryfall_ids, tcgplayer_ids, tcgplayer_sku_ids, or product_ids may be provided."

    # If we have multiple types, we need to make separate requests.

    requests_to_make = []

    if s_ids:
        # Deduplicate
        s_ids = list(set(s_ids))
        # Batch
        for i in range(0, len(s_ids), 100):
            requests_to_make.append({"scryfall_ids": s_ids[i:i+100]})

    if t_ids:
        t_ids = list(set(t_ids))
        for i in range(0, len(t_ids), 100):
            requests_to_make.append({"tcgplayer_ids": t_ids[i:i+100]})

    if p_ids:
        p_ids = list(set(p_ids))
        for i in range(0, len(p_ids), 100):
            requests_to_make.append({"product_ids": p_ids[i:i+100]})

    for req_params in requests_to_make:
        resp = search_singles(req_params)
        all_data.extend(resp.get("data", []))

    if not all_data:
        print("No products found.")
        return

    # Deduplicate results by ID to avoid printing duplicates if multiple batches return same (unlikely with ID batching but good practice)
    seen_ids = set()
    unique_data = []
    for item in all_data:
        # Use scryfall_id or product_id as key
        pid = item.get("scryfall_id") or item.get("product_id") or item.get("name") # Fallback
        if pid not in seen_ids:
            seen_ids.add(pid)
            unique_data.append(item)

    for item in unique_data:
        name = item.get("name")
        set_code = item.get("set_code")
        print(f"Product: {name} ({set_code})")

        # TCGPlayer info (Market)
        price_market = item.get("price_market")
        price_market_foil = item.get("price_market_foil")

        print(f"TCGPlayer Market Price: {format_price(price_market)} (NF), {format_price(price_market_foil)} (Foil)")
        print("-" * 55)
        print(f"{'Condition':<10} {'Finish':<10} {'Manapool Low':<15}")
        print("-" * 55)

        variants = item.get("variants", [])
        # Sort variants by finish then condition?
        # Condition order: NM, LP, MP, HP, DMG
        cond_order = {"NM": 1, "LP": 2, "MP": 3, "HP": 4, "DMG": 5}
        variants.sort(key=lambda x: (x.get("finish_id"), cond_order.get(x.get("condition_id"), 99)))

        for variant in variants:
            cond = variant.get("condition_id")
            finish = variant.get("finish_id")
            low = variant.get("low_price")

            print(f"{cond:<10} {finish:<10} {format_price(low):<15}")
        print("\n")

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

    # Lowest Prices
    lowest_prices = subparsers.add_parser("lowest-prices")
    lowest_prices.add_argument("--scryfall-ids", nargs="+")
    lowest_prices.add_argument("--tcgplayer-ids", nargs="+")
    lowest_prices.add_argument("--product-ids", nargs="+")
    lowest_prices.add_argument("--inventory-file", help="Path to inventory JSON file to check prices for")

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

    elif args.command == "lowest-prices":
        handle_lowest_prices(args)

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
            print(f"{'Name':<30} {'Set':<10} {'Price':>8} {'Qty':>4}")
            print("-" * 55)
            for item in inventory_resp.get("inventory", []):
                p = item.get("product", {})
                single = p.get("single", {})
                name = single.get("name", "Unknown")
                set_code = single.get("set", "???")
                price = item.get("price_cents", 0) / 100
                qty = item.get("quantity", 0)
                print(f"{name[:30]:<30} {set_code:<10} {price:>8.2f} {qty:>4}")
        else:
            print(json.dumps(inventory_resp, indent=2))

    elif args.command == "update-price":
        # Placeholder for update-price implementation if needed,
        # but the argparse is already there.
        print("Update price not fully implemented in this script snippet.")

if __name__ == "__main__":
    main()
