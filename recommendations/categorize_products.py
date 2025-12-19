import django
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

from recommendations.models import Product

CATEGORIES = {
    "Cleanser": ["cleanser", "wash", "foaming", "gel", "face wash", "cleansing"],
    "Serum": ["serum", "elixir", "drop", "ampoule"],
    "Moisturizer": ["moisturizer", "cream", "lotion", "gel", "balm"],
    "Sunscreen": ["spf", "sun", "uv", "sunscreen", "block"],
    "Toner": ["toner", "mist", "water"],
    "Mask": ["mask", "masque", "pack"],
    "Exfoliant": ["peel", "exfoliant", "scrub", "acid"],
    "Eye Cream": ["eye", "contour"],
}

def categorize_product(name: str) -> str:
    name_lower = (name or "").lower()
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category
    return "Other"

def update_product_categories():
    products = Product.objects.all()
    updated_count = 0
    for p in products:
        if not p.category:
            p.category = categorize_product(p.name)
            p.save(update_fields=["category"])
            updated_count += 1
            print(f"Updated: {p.name} -> {p.category}")
    print(f"Total products categorized: {updated_count}")

if __name__ == "__main__":
    update_product_categories()
