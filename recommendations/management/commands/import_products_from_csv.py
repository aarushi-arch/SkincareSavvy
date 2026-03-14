import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from recommendations.models import Product
import ast


class Command(BaseCommand):
    help = 'Import products from updated_products_with_images.csv'

    def handle(self, *args, **options):
        csv_path = 'recommendations/notebooks/updated_products_with_images.csv'
        
        try:
            df = pd.read_csv(csv_path)
            self.stdout.write(f'Loaded {len(df)} products from CSV')
        except FileNotFoundError:
            self.stderr.write(f'File not found: {csv_path}')
            return

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for _, row in df.iterrows():
                # Parse ingredients
                try:
                    ingredients = ast.literal_eval(row['clean_ingreds']) if pd.notna(row['clean_ingreds']) else []
                except:
                    ingredients = []

                # Parse skin types
                try:
                    skin_types = ast.literal_eval(row['suitable_skin_types']) if pd.notna(row['suitable_skin_types']) else []
                except:
                    skin_types = []

                # Parse notable effects
                try:
                    if pd.notna(row['notable_effects']):
                        if row['notable_effects'].startswith('['):
                            notable_effects = ast.literal_eval(row['notable_effects'])
                        else:
                            notable_effects = [row['notable_effects']]
                    else:
                        notable_effects = []
                except:
                    notable_effects = []

                # Clean price
                price = None
                if pd.notna(row['price']):
                    price_str = str(row['price']).replace('£', '').strip()
                    try:
                        price = float(price_str)
                    except:
                        pass

                product_data = {
                    'name': row['product_name'],
                    'product_url': row['product_url'],
                    'category': row['product_type'],
                    'price': price,
                    'image_url': row['image_url'] if pd.notna(row['image_url']) else None,
                    'ingredients_json': ingredients,
                    'skin_types': skin_types,
                    'skin_concerns': notable_effects,
                }

                # Try to get or create product
                product, created = Product.objects.get_or_create(
                    product_url=row['product_url'],
                    defaults=product_data
                )

                if created:
                    created_count += 1
                    self.stdout.write(f'Created: {product.name}')
                else:
                    # Update existing
                    for key, value in product_data.items():
                        setattr(product, key, value)
                    product.save()
                    updated_count += 1
                    self.stdout.write(f'Updated: {product.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully imported products. Created: {created_count}, Updated: {updated_count}'
            )
        )