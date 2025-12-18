"""Django management command to scrape Paula's Choice products."""
import time
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recommendations.models import Product, Ingredient
from recommendations.scrapers.paulas_choice import PaulasChoiceScraper


class Command(BaseCommand):
    help = "Scrape skincare products from Paula's Choice website"

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            type=str,
            required=True,
            help="Category to scrape (e.g., 'cleansers', 'moisturizers', 'serums')",
        )
        parser.add_argument(
            "--max-products",
            type=int,
            default=None,
            help="Maximum number of products to scrape (default: all)",
        )
        parser.add_argument(
            "--skip-details",
            action="store_true",
            help="Skip scraping detailed product information (faster but less data)",
        )

    def handle(self, *args, **options):
        category = options["category"]
        max_products = options["max_products"]
        skip_details = options["skip_details"]
        
        # Normalize category name for database storage
        # e.g. "cleansers" -> "Cleanser"
        CATEGORY_MAP = {
            "cleansers": "Cleanser",
            "moisturizers": "Moisturizer",
            "serums": "Serum",
            "toners": "Toner",
            "exfoliants": "Exfoliant",
            "sunscreens": "Sunscreen",
            "eye-creams": "Eye Cream",
            "masks": "Mask",
        }
        db_category = CATEGORY_MAP.get(category, category.title().rstrip('s'))

        self.stdout.write(
            self.style.SUCCESS(f"Starting to scrape Paula's Choice {category} (DB Category: {db_category})...")
        )

        scraper = PaulasChoiceScraper()

        # Scrape category (basic info)
        self.stdout.write(f"Scraping category: {category}")
        products = scraper.scrape_category(category, max_products=max_products)

        if not products:
            self.stdout.write(self.style.WARNING("No products found."))
            return

        self.stdout.write(f"Found {len(products)} products. Processing...")

        scraped = 0
        failed = 0

        for product_data in products:
            try:
                # Get full details if not skipping
                details = None
                if not skip_details:
                    self.stdout.write(f"  Getting details for: {product_data.get('name', 'Unknown')}")
                    details = scraper.scrape_product_details(product_data.get('url', ''))

                # Prepare ingredients list
                ingredients_list = []
                if details and details.get('ingredients_list'):
                    ingredients_list = details['ingredients_list']
                elif details and details.get('ingredients'):
                    # Parse ingredients string into list
                    ing_text = details['ingredients']
                    if ':' in ing_text:
                        ing_text = ing_text.split(':', 1)[1]
                    ingredients_list = [i.strip() for i in ing_text.split(',') if i.strip()]

                # Convert ingredients to dict format for consistency
                ingredients_json = [
                    {"ingredient": ing, "function": None, "label": None}
                    for ing in ingredients_list
                ]

                # Determine URL to use (product_url takes precedence, fallback to inci_decoder_url)
                product_url = product_data.get('url')
                inci_url = product_url  # Use same URL for now

                # Use rating from details if available, else from category page
                rating = details.get('rating') if details and details.get('rating') is not None else product_data.get('rating')
                review_count = details.get('review_count') if details and details.get('review_count') is not None else product_data.get('review_count', 0)

                # Save to database
                with transaction.atomic():
                    product, created = Product.objects.update_or_create(
                        product_url=product_url,
                        defaults={
                            'brand': "Paula's Choice",
                            'name': product_data.get('name', 'Unknown Product'),
                            'category': db_category,
                            'product_id': product_data.get('product_id'),
                            'price': product_data.get('price'),
                            'image_url': product_data.get('image'),
                            'rating': rating,
                            'review_count': review_count,
                            'description': details.get('description', '') if details else '',
                            'how_to_use': details.get('how_to_use', '') if details else '',
                            'size': details.get('size', '') if details else '',
                            'ingredients_json': ingredients_json,
                            'skin_types': details.get('skin_types', []) if details else [],
                            'skin_concerns': details.get('skin_concerns', []) if details else [],
                            'inci_decoder_url': inci_url,
                        }
                    )

                    # Create Ingredient records
                    for ing_name in ingredients_list:
                        if ing_name:
                            Ingredient.objects.get_or_create(
                                name=ing_name,
                                defaults={
                                    "function": None,
                                    "label": None,
                                }
                            )

                    scraped += 1
                    action = "Created" if created else "Updated"
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {action}: {product.name}")
                    )

            except Exception as exc:
                failed += 1
                self.stderr.write(
                    f"  ✗ Failed to process {product_data.get('name', 'Unknown')}: {exc}"
                )

            # Small delay between products
            time.sleep(0.5)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'='*60}\n"
                f"Scraping finished!\n"
                f"Total scraped: {scraped}\n"
                f"Failed: {failed}\n"
                f"{'='*60}"
            )
        )

