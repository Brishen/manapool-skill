import click
import json
import sys
from .api import search_singles, search_sealed, get_prices, optimize_cart, get_seller_inventory, get_lowest_price

def format_price(cents):
    if cents is None:
        return "N/A"
    return f"${cents/100:.2f}"

def print_product_lowest_prices(item):
    name = item.get("name")
    set_code = item.get("set_code")
    print(f"Product: {name} ({set_code})")

    # TCGPlayer info (Market)
    price_market = item.get("price_market")
    price_market_foil = item.get("price_market_foil")

    print("-" * 75)
    print(f"{'Condition':<10} {'Finish':<10} {'Manapool Low':<15} {'TCG Market':<15}")
    print("-" * 75)

    variants = item.get("variants", [])
    # Sort variants by finish then condition?
    # Condition order: NM, LP, MP, HP, DMG
    cond_order = {"NM": 1, "LP": 2, "MP": 3, "HP": 4, "DMG": 5}
    variants.sort(key=lambda x: (x.get("finish_id"), cond_order.get(x.get("condition_id"), 99)))

    for variant in variants:
        cond = variant.get("condition_id")
        finish = variant.get("finish_id")
        low = variant.get("low_price")

        if not low: continue

        tcg_price = price_market_foil if finish in ["FO", "EF"] else price_market

        print(f"{cond:<10} {finish:<10} {format_price(low):<15} {format_price(tcg_price):<15}")
    print("\n")

@click.group()
def cli():
    """Manapool API CLI"""
    pass

@cli.command(name="search-singles")
@click.option("--scryfall-ids", multiple=True, help="Scryfall ID(s)")
@click.option("--tcgplayer-ids", multiple=True, help="TCGPlayer ID(s)")
@click.option("--product-ids", multiple=True, help="Product ID(s)")
def search_singles_cmd(scryfall_ids, tcgplayer_ids, product_ids):
    """Search for singles"""
    params = {}
    if scryfall_ids: params["scryfall_ids"] = list(scryfall_ids)
    if tcgplayer_ids: params["tcgplayer_ids"] = list(tcgplayer_ids)
    if product_ids: params["product_ids"] = list(product_ids)

    if not params:
        raise click.UsageError("Must provide at least one search parameter.")

    try:
        print(json.dumps(search_singles(params), indent=2))
    except Exception as e:
        raise click.ClickException(str(e))

@cli.command(name="search-sealed")
@click.option("--tcgplayer-ids", multiple=True, help="TCGPlayer ID(s)")
@click.option("--product-ids", multiple=True, help="Product ID(s)")
def search_sealed_cmd(tcgplayer_ids, product_ids):
    """Search for sealed product"""
    params = {}
    if tcgplayer_ids: params["tcgplayer_ids"] = list(tcgplayer_ids)
    if product_ids: params["product_ids"] = list(product_ids)

    if not params:
        raise click.UsageError("Must provide at least one search parameter.")

    try:
        print(json.dumps(search_sealed(params), indent=2))
    except Exception as e:
        raise click.ClickException(str(e))

@cli.command()
@click.argument("category", type=click.Choice(["singles", "sealed", "variants"]))
def prices(category):
    """Get prices for a category"""
    try:
        print(json.dumps(get_prices(category), indent=2))
    except Exception as e:
        raise click.ClickException(str(e))

@cli.command(name="lowest-prices")
@click.option("--scryfall-ids", multiple=True, help="Scryfall ID(s)")
@click.option("--tcgplayer-ids", multiple=True, help="TCGPlayer ID(s)")
@click.option("--product-ids", multiple=True, help="Product ID(s)")
@click.option("--inventory-file", type=click.Path(exists=True), help="Path to inventory JSON file")
def lowest_prices(scryfall_ids, tcgplayer_ids, product_ids, inventory_file):
    """Get lowest prices for items"""
    params = {}

    # Initialize lists if options provided
    # Click passes tuples for multiple=True
    s_ids = list(scryfall_ids) if scryfall_ids else []
    t_ids = list(tcgplayer_ids) if tcgplayer_ids else []
    p_ids = list(product_ids) if product_ids else []

    if inventory_file:
        try:
            with open(inventory_file, "r") as f:
                inv_data = json.load(f)

            # Extract scryfall_ids from inventory
            inventory = inv_data.get("inventory", [])
            for item in inventory:
                s_id = item.get("product", {}).get("single", {}).get("scryfall_id")
                if s_id:
                    s_ids.append(s_id)
        except Exception as e:
            raise click.ClickException(f"Error reading inventory file: {e}")

    # Check if we have any params
    if not s_ids and not t_ids and not p_ids:
        raise click.UsageError("Must provide at least one search parameter (--scryfall-ids, --tcgplayer-ids, --product-ids, --inventory-file).")

    # Deduplicate
    s_ids = list(set(s_ids))
    t_ids = list(set(t_ids))
    p_ids = list(set(p_ids))

    requests_to_make = []

    if s_ids:
        for i in s_ids:
            requests_to_make.append({"scryfall_ids": [i]})

    if t_ids:
        for i in t_ids:
            requests_to_make.append({"tcgplayer_ids": [i]})

    if p_ids:
        for i in p_ids:
            requests_to_make.append({"product_ids": [i]})

    found_any = False
    for req_params in requests_to_make:
        try:
            # We reuse search_singles from api
            resp = search_singles(req_params)
            data = resp.get("data", [])
            if data:
                found_any = True
                for item in data:
                    print_product_lowest_prices(item)
        except Exception as e:
            click.echo(f"Error fetching data for {req_params}: {e}", err=True)
            # Should we exit here? The original script continued.
            # "Error fetching data for ... continue"
            # So continuing is correct behavior for partial failure in batch processing.
            continue

    if not found_any:
        click.echo("No products found.")

@cli.command()
@click.argument("file", type=click.Path(exists=True))
def optimize(file):
    """Optimize cart from a JSON file"""
    try:
        with open(file, "r") as f:
            cart_data = json.load(f)
        print(json.dumps(optimize_cart(cart_data), indent=2))
    except Exception as e:
        raise click.ClickException(str(e))

@cli.command(name="seller-inventory")
@click.option("--limit", type=int, default=100, help="Number of items to fetch")
@click.option("--offset", type=int, default=0, help="Offset for pagination")
@click.option("--min-quantity", type=int, help="Filter by minimum quantity")
@click.option("--stats", is_flag=True, help="Include market stats for each item")
@click.option("--summary", is_flag=True, help="Print a human-readable summary")
def seller_inventory(limit, offset, min_quantity, stats, summary):
    """Get seller inventory"""
    params = {"limit": limit, "offset": offset}
    if min_quantity is not None:
        params["minQuantity"] = min_quantity

    try:
        inventory_resp = get_seller_inventory(params)

        if summary:
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
    except Exception as e:
        raise click.ClickException(str(e))

@cli.command(name="update-price")
@click.option("--sku", required=True, help="TCGPlayer SKU")
@click.option("--price-cents", type=int, required=True, help="Price in cents")
@click.option("--quantity", type=int, required=True, help="Quantity (Required to prevent accidental reset)")
def update_price(sku, price_cents, quantity):
    """Update price and quantity (Placeholder)"""
    click.echo("Update price not fully implemented in this script snippet.")
