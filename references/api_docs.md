# Manapool API Reference

## Authentication
Requires `Authorization: Bearer <token>` header.
Token is generated in integration settings: https://manapool.com/seller/integrations/manapool-api

## Endpoints

### Products
- `GET /products/singles`: Search singles.
  - Query params: `scryfall_ids`, `tcgplayer_ids`, `product_ids` (arrays).
- `GET /products/sealed`: Search sealed products.
  - Query params: `tcgplayer_ids`, `product_ids`.

### Prices
- `GET /prices/singles`: All in-stock singles prices.
- `GET /prices/sealed`: All in-stock sealed prices.
- `GET /prices/variants`: All in-stock variant prices.

### Optimizer
- `POST /buyer/optimizer`: Optimize a cart.
  - Request body:
    ```json
    {
      "cart": [
        {
          "quantity_requested": 1,
          "type": "mtg_single",
          "name": "Card Name",
          "language_ids": ["EN"],
          "finish_ids": ["NF"],
          "condition_ids": ["NM"]
        }
      ],
      "model": "lowest_price",
      "destination_country": "US"
    }
    ```
