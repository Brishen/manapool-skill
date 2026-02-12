---
name: manapool
description: Interact with the Manapool platform to buy and sell Magic: The Gathering (MTG) products. Use this skill to search for cards, optimize buyer carts, place orders, and manage seller inventory and fulfillment.
---

# Manapool API Skill

This skill allows you to interact with the Mana Pool marketplace to programmatically buy and sell Magic: The Gathering products.

## Environment Setup
Ensure the following are set in the environment:
- `MANAPOOL_API_TOKEN`: Your API token.
- `MANAPOOL_API_EMAIL`: Your account email.

## Domain Concepts

When searching or listing items, use the following standard codes:

### Conditions
- `NM`: Near Mint
- `LP`: Lightly Played
- `MP`: Moderately Played
- `HP`: Heavily Played
- `DMG`: Damaged

### Finishes
- `NF`: Non-Foil
- `FO`: Foil
- `EF`: Etched Foil

### Languages
- Common: `EN` (English), `JA` (Japanese), `FR` (French), `IT` (Italian), `DE` (German)
- Others: `ES`, `PT`, `RU`, `KO`, `CH`, `CS`

## Tooling
Most interactions are handled via the CLI script: `/home/bhawkins/clawd/skills/manapool/scripts/manapool_cli.py`.

## Capabilities

### 1. Product Search & Information
Before buying or selling, you often need to identify the correct product or check market prices.

*   **Search Singles**: `./scripts/manapool_cli.py search-singles --scryfall-ids <id>`
*   **Search Sealed**: `./scripts/manapool_cli.py search-sealed --tcgplayer-ids <id>`
*   **Get Prices**: `./scripts/manapool_cli.py prices <singles|sealed|variants>`

### 2. Buying Cards
The buying process follows a sequence: **Optimize -> Create Order -> Purchase**.

*   **Step 1: Optimize Cart**
    *   Command: `./scripts/manapool_cli.py optimize <cart_json_file>`
    *   Finds the best combination of sellers for a list of desired items.
*   **Step 2 & 3: Order/Purchase**
    *   Requires direct API calls (see `references/api_docs.md`).
    *   `POST /buyer/orders/pending-orders` (to reserve items).
    *   `POST /buyer/orders/pending-orders/{id}/purchase` (to finalize).

### 3. Seller Inventory Management
Sellers can manage listings using various industry-standard IDs.

*   **List Inventory**: `./scripts/manapool_cli.py seller-inventory`
    *   Use `--summary` for a human-readable table with market comparison.
*   **Update Inventory**: `./scripts/manapool_cli.py update-price --sku <sku> --price-cents <price> --quantity <qty>`
    *   Updates price and quantity using TCGPlayer SKUs.

### 4. Order Fulfillment
Sellers must monitor and fulfill incoming orders.
*   Use direct API calls (see `references/api_docs.md`).
*   `GET /seller/orders` (list orders).
*   `PUT /seller/orders/{id}/fulfillment` (mark as shipped).

## References
- Detailed API docs: `/home/bhawkins/clawd/skills/manapool/references/api_docs.md`
- OpenAPI spec: `/home/bhawkins/clawd/skills/manapool/references/openapi.json`
