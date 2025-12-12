# Product Scraping Guide

This guide explains how to scrape skincare products from INCI Decoder and add them to the database.

## Setup

1. Install required packages:
```bash
pip install beautifulsoup4 requests
```

2. Create and run migrations:
```bash
python manage.py makemigrations recommendations
python manage.py migrate
```

## Usage

### Basic Usage

Scrape products from INCI Decoder URLs:

```bash
python manage.py scrape_products --urls "https://incidecoder.com/products/product-name-1" "https://incidecoder.com/products/product-name-2"
```

### Options

- `--urls`: List of INCI Decoder URLs to scrape (required)
- `--delay`: Delay between requests in seconds (default: 2.0)
- `--timeout`: Request timeout in seconds (default: 10)

### Examples

```bash
# Scrape a single product
python manage.py scrape_products --urls "https://incidecoder.com/products/cerave-foaming-facial-cleanser"

# Scrape multiple products
python manage.py scrape_products --urls \
  "https://incidecoder.com/products/product-1" \
  "https://incidecoder.com/products/product-2" \
  "https://incidecoder.com/products/product-3"

# Scrape with custom delay (be more polite)
python manage.py scrape_products --urls "https://incidecoder.com/products/product-name" --delay 3.0
```

## How It Works

1. **Fetches the product page** from INCI Decoder
2. **Extracts product information**:
   - Product name
   - Brand
   - Category
   - Ingredients list
3. **Parses ingredients** from `li.ingred-bar` elements
4. **Saves to database**:
   - Creates or updates Product record
   - Creates Ingredient records for each ingredient
5. **Respects rate limits** with configurable delays between requests

## Data Structure

### Product Model
- `brand`: Product brand name
- `name`: Product name
- `category`: Product category
- `inci_decoder_url`: Unique URL identifier
- `ingredients_json`: JSON array of ingredient dictionaries
- `created_at`: Timestamp when created
- `updated_at`: Timestamp when last updated

### Ingredient Model
- `name`: Ingredient name (unique)
- `function`: Ingredient function/purpose
- `label`: Ingredient label (e.g., EWG rating)
- `created_at`: Timestamp when created

## Notes

- Products are identified by their `inci_decoder_url`, so re-scraping will update existing records
- Ingredients are created separately and can be reused across products
- The scraper includes error handling and will continue processing even if some URLs fail
- Always respect website terms of service and rate limits

