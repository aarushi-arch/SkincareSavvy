import csv
import os
import sys
from pathlib import Path
import django

# Ensure project root on sys.path and setup Django
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

from recommendations.models import Product

CSV_FILE = "django_products_mapped.csv"

def _source_url(product: Product) -> str | None:
    return product.inci_decoder_url or product.product_url

def main():
    products = Product.objects.all()
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "product_name",
                "product_url",
                "product_type",
                "clean_ingredients",
                "suitable_skin",
                "notable_effects",
            ],
        )
        writer.writeheader()
        for p in products:
            writer.writerow(
                {
                    "product_name": p.name,
                    "product_url": _source_url(p) or "",
                    "product_type": p.category or "",
                    "clean_ingredients": "",
                    "suitable_skin": "",
                    "notable_effects": "",
                }
            )
    print(f"Exported {products.count()} products to {CSV_FILE}")

if __name__ == "__main__":
    main()
