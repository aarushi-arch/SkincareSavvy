"""
Sync scraped descriptions from CSV into the Product DB model.
Matches by product_url. Only fills blank fields — never overwrites.

Usage:
    python sync_descriptions_to_db.py
"""
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

import pandas as pd
from recommendations.models import Product

CSV = "recommendations/notebooks/updated_products_with_images_npr.csv"

df = pd.read_csv(CSV)
print(f"CSV rows: {len(df)}")

# Only rows that have a description
has_desc = df["description"].notna() & (df["description"].str.len() > 10)
df_work = df[has_desc].copy()
print(f"Rows with description: {len(df_work)}")

updated = 0
not_found = 0

for _, row in df_work.iterrows():
    url = row.get("product_url", "")
    if not url or not str(url).startswith("http"):
        continue

    try:
        product = Product.objects.get(product_url=url)
    except Product.DoesNotExist:
        not_found += 1
        continue

    changed = False

    desc = str(row.get("description", "") or "").strip()
    if desc and not product.description:
        product.description = desc
        changed = True

    how_to = str(row.get("how_to_use", "") or "").strip()
    if how_to and how_to.lower() != "nan" and not product.how_to_use:
        product.how_to_use = how_to
        changed = True

    size = str(row.get("size", "") or "").strip()
    if size and size.lower() != "nan" and not product.size:
        product.size = size
        changed = True

    if changed:
        product.save(update_fields=["description", "how_to_use", "size"])
        updated += 1

print(f"\nUpdated : {updated}")
print(f"Not found in DB: {not_found}")
print(f"Done.")
