# Manapool Clawdbot Skill

A skill for [Clawdbot](https://github.com/clawdbot/clawdbot) to interact with the Mana Pool MTG marketplace.

## Features

- **Search Products**: Look up singles or sealed products by Scryfall ID, TCGPlayer ID, or Mana Pool Product ID.
- **Price Check**: Fetch real-time market prices for singles, sealed, and variants.
- **Cart Optimization**: Submit a wish list and receive an optimized cart based on price, package count, or balance.
- **Seller Inventory**: View your own seller inventory and listings.

## Setup

Requires a `MANAPOOL_API_TOKEN` set in your environment or Clawdbot config. For seller actions, `MANAPOOL_API_EMAIL` should also be set.

## Usage

The skill provides a CLI tool located at `scripts/manapool_cli.py`.

### Example Commands

```bash
# Search for a single
./scripts/manapool_cli.py search-singles --scryfall-ids <uuid>

# Check prices for all in-stock singles
./scripts/manapool_cli.py prices singles

# Fetch your seller inventory
./scripts/manapool_cli.py seller-inventory --limit 50
```

## References

- `references/openapi.json`: Full OpenAPI 3.1.0 specification for the Mana Pool API.
- `references/api_docs.md`: Detailed endpoint documentation and JSON schemas.
