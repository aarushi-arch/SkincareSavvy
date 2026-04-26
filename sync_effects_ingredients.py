"""
Sync notable_effects → skin_concerns and clean_ingreds → ingredients_json
from the CSV into the Product DB model.

Usage:
    python sync_effects_ingredients.py
"""
import os, ast
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
import django; django.setup()

import pandas as pd
from recommendations.models import Product

CSV = "recommendations/notebooks/updated_products_with_images_npr.csv"
df  = pd.read_csv(CSV)
print(f"CSV rows: {len(df)}")

updated = 0
not_found = 0

for _, row in df.iterrows():
    url = str(row.get("product_url", "") or "").strip()
    if not url.startswith("http"):
        continue

    try:
        p = Product.objects.get(product_url=url)
    except Product.DoesNotExist:
        not_found += 1
        continue

    changed = False

    # ── notable_effects → skin_concerns ──────────────────────────────────────
    if not p.skin_concerns:
        raw = str(row.get("notable_effects", "") or "")
        if raw and raw.strip() not in ("", "[]", "nan"):
            try:
                effects = ast.literal_eval(raw)
                if isinstance(effects, list) and effects:
                    p.skin_concerns = [str(e).strip() for e in effects if str(e).strip()]
                    changed = True
            except Exception:
                pass

    # ── clean_ingreds → ingredients_json ─────────────────────────────────────
    if not p.ingredients_json:
        raw = str(row.get("clean_ingreds", "") or "")
        if raw and raw.strip() not in ("", "[]", "nan"):
            try:
                ingreds = ast.literal_eval(raw)
                if isinstance(ingreds, list) and ingreds:
                    p.ingredients_json = [str(i).strip() for i in ingreds if str(i).strip()]
                    changed = True
            except Exception:
                pass

    # ── suitable_skin_types → skin_types ─────────────────────────────────────
    if not p.skin_types:
        raw = str(row.get("suitable_skin_types", "") or "")
        if raw and raw.strip() not in ("", "[]", "nan"):
            try:
                types = ast.literal_eval(raw)
                if isinstance(types, list) and types:
                    p.skin_types = [str(t).strip() for t in types if str(t).strip()]
                    changed = True
            except Exception:
                pass

    if changed:
        p.save(update_fields=["skin_concerns", "ingredients_json", "skin_types"])
        updated += 1

print(f"Updated: {updated} | Not found: {not_found}")
