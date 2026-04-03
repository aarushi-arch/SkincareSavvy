import os
import django
import pandas as pd
import re
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from recommendations.models import Product

def sync():
    csv_path = 'recommendations/notebooks/updated_products_with_images_npr.csv'
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    print(f"Loading {len(df)} products from CSV...")

    count_updated = 0
    count_created = 0

    for i, row in df.iterrows():
        url = row.get('product_url')
        if not url or pd.isna(url):
            continue

        # Extract numeric price from "Rs. 1,234"
        price_str = str(row.get('price', ''))
        price_val = None
        if 'Rs.' in price_str:
            # Strip "Rs. " and commas
            clean_price = price_str.replace('Rs.', '').replace(',', '').strip()
            try:
                price_val = Decimal(clean_price)
            except:
                pass
        
        # If still None, try to find any numbers
        if price_val is None:
            numbers = re.findall(r'\d+(?:\.\d+)?', price_str)
            if numbers:
                price_val = Decimal(numbers[0])

        # Prepare product data
        product_data = {
            'name': row.get('product_name', '')[:500],
            'brand': row.get('brand', 'Skincare')[:200],
            'category': row.get('product_type', '')[:200],
            'image_url': row.get('image_url', ''),
            'price': price_val,
            'description': row.get('description', '') or row.get('notable_effects', ''),
            # You can map more fields if needed
        }

        # Update or create based on product_url (original)
        # Use simple get_or_create to find by URL
        product, created = Product.objects.update_or_create(
            product_url=url,
            defaults=product_data
        )

        if created:
            count_created += 1
        else:
            count_updated += 1

        if (count_created + count_updated) % 100 == 0:
            print(f"Processed {count_created + count_updated} products...")

    print(f"\n✅ Synchronization complete!")
    print(f"Updated: {count_updated}")
    print(f"Created: {count_created}")

if __name__ == "__main__":
    sync()
