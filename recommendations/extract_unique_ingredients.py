import os
import sys
from pathlib import Path
import json
import django

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

from recommendations.models import Product

OUTPUT_FILE = BASE_DIR / "recommendations" / "notebooks" / "unique_ingredients.txt"

def iter_ingredient_names(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = (item.get("ingredient") or "").strip().lower()
                if name:
                    yield name
            else:
                name = (str(item) or "").strip().lower()
                if name:
                    yield name

def main():
    unique = set()
    for p in Product.objects.all():
        for name in iter_ingredient_names(p.ingredients_json):
            unique.add(name)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for ing in sorted(unique):
            f.write(ing + "\n")
    print(f"Extracted {len(unique)} unique ingredients.")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
