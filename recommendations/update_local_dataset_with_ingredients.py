import csv
import json
import os
import sys
from pathlib import Path
import django

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

from recommendations.models import Product

CSV_FILE = BASE_DIR / "recommendations" / "notebooks" / "django_products_mapped.csv"
OUTPUT_CSV = BASE_DIR / "recommendations" / "notebooks" / "local_dataset_with_ingredients.csv"

def find_product(row) -> Product | None:
    url = (row.get("product_url") or "").strip()
    if url:
        p = Product.objects.filter(inci_decoder_url=url).first()
        if p:
            return p
        p = Product.objects.filter(product_url=url).first()
        if p:
            return p
    name = (row.get("product_name") or "").strip()
    if name:
        return Product.objects.filter(name=name).first()
    return None

def main():
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if "ingredients_json" not in fieldnames:
        fieldnames.append("ingredients_json")

    for row in rows:
        product = find_product(row)
        if product and product.ingredients_json:
            ing = product.ingredients_json
            if not isinstance(ing, str):
                ing = json.dumps(ing, ensure_ascii=False)
            row["ingredients_json"] = ing
        else:
            row["ingredients_json"] = ""

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated CSV saved to: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
