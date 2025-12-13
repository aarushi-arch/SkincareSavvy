# Paula's Choice Scraping Guide

This guide explains how to scrape skincare products from Paula's Choice website and add them to the database.

## Setup

1. Make sure you have the required packages:
```bash
pip install beautifulsoup4 requests
```

2. Create and run migrations for the updated Product model:
```bash
python manage.py makemigrations recommendations
python manage.py migrate
```

## Usage

### Basic Usage

Scrape products from a specific category:

```bash
python manage.py scrape_paulas_choice --category cleansers
```

### Options

- `--category`: Category to scrape (required)
  - Examples: `cleansers`, `moisturizers`, `serums`, `toners`, `exfoliants`, `sunscreens`
- `--max-products`: Maximum number of products to scrape (optional)
  - Example: `--max-products 10` (scrapes only first 10 products)
- `--skip-details`: Skip scraping detailed product information (faster but less data)

### Examples

```bash
# Scrape all cleansers
python manage.py scrape_paulas_choice --category cleansers

# Scrape first 20 moisturizers
python manage.py scrape_paulas_choice --category moisturizers --max-products 20

# Scrape serums without detailed information (faster)
python manage.py scrape_paulas_choice --category serums --skip-details

# Scrape toners with full details
python manage.py scrape_paulas_choice --category toners
```

## Available Categories

Common categories you can scrape:
- `cleansers` - Face cleansers
- `moisturizers` - Moisturizers and creams
- `serums` - Treatment serums
- `toners` - Toners and essences
- `exfoliants` - Chemical exfoliants (AHA/BHA)
- `sunscreens` - Sun protection products
- `eye-creams` - Eye care products
- `masks` - Face masks

## What Gets Scraped

### Basic Product Information (from category page)
- Product name
- Product URL
- Product ID
- Price
- Image URL
- Rating (if available)
- Review count (if available)

### Detailed Information (from product page, unless `--skip-details`)
- Full description
- How to use instructions
- Ingredients list
- Suitable skin types
- Skin concerns addressed
- Product size

## Data Structure

The scraper saves data to the `Product` model with the following fields:

- `brand`: "Paula's Choice"
- `name`: Product name
- `category`: Category name
- `product_url`: Original product URL (unique identifier)
- `product_id`: Product ID from website
- `price`: Product price
- `image_url`: Product image URL
- `rating`: Average rating
- `review_count`: Number of reviews
- `description`: Product description
- `how_to_use`: Usage instructions
- `size`: Product size
- `ingredients_json`: List of ingredient dictionaries
- `skin_types`: List of suitable skin types
- `skin_concerns`: List of addressed skin concerns

## Notes

- Products are identified by their `product_url`, so re-scraping will update existing records
- Ingredients are automatically created in the `Ingredient` model
- The scraper includes rate limiting to be respectful to the website
- Always respect website terms of service and robots.txt
- Scraping detailed information takes longer but provides more complete data

## Troubleshooting

### No products found
- Check if the category name is correct
- The website structure may have changed - you may need to update the scraper

### Connection errors
- Check your internet connection
- The website may be temporarily unavailable
- Try again after a few minutes

### Missing data
- Some products may not have all fields populated
- Use `--skip-details` only if you need basic information quickly

