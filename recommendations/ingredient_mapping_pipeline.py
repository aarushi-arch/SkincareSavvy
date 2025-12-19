import re
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

TEMPLATE_CSV = BASE_DIR / "recommendations" / "notebooks" / "ingredient_mapping_template.csv"

def iter_ingredient_names(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = (item.get("ingredient") or "").strip()
                if name:
                    yield name
            else:
                name = (str(item) or "").strip()
                if name:
                    yield name

def clean_name(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[\*\d\(\)/\-\%]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def build_unique_ingredients() -> list[str]:
    unique = set()
    for p in Product.objects.all():
        for name in iter_ingredient_names(p.ingredients_json):
            cname = clean_name(name)
            if cname:
                unique.add(cname)
    return sorted(unique)

def ensure_template(ingredients: list[str]) -> None:
    TEMPLATE_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not TEMPLATE_CSV.exists():
        with open(TEMPLATE_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ingredient", "skin_type", "notable_effects"])
            for ing in ingredients:
                w.writerow([ing, "", ""])
        print(f"Template created: {TEMPLATE_CSV}")
    else:
        print(f"{TEMPLATE_CSV} already exists.")

def load_mapping() -> dict[str, dict[str, list[str]]]:
    mapping: dict[str, dict[str, list[str]]] = {}
    if not TEMPLATE_CSV.exists():
        return mapping
    with open(TEMPLATE_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ing = clean_name(row.get("ingredient", ""))
            skin = (row.get("skin_type") or "").strip()
            eff = (row.get("notable_effects") or "").strip()
            if not ing:
                continue
            def split_vals(v: str) -> list[str]:
                if not v:
                    return []
                parts = [p.strip() for p in re.split(r"[\/,]", v) if p.strip()]
                return parts
            mapping[ing] = {
                "skin_types": split_vals(skin),
                "effects": split_vals(eff),
            }
    return mapping

def apply_mapping(mapping: dict[str, dict[str, list[str]]]) -> None:
    if not mapping:
        print("No mapping loaded; skipping product updates.")
        return
    updated = 0
    for p in Product.objects.all():
        skins = set(p.skin_types or [])
        effects = set(p.skin_concerns or [])
        names = list(iter_ingredient_names(p.ingredients_json))
        for name in names:
            cname = clean_name(name)
            if cname in mapping:
                for s in mapping[cname]["skin_types"]:
                    if s:
                        skins.add(s)
                for e in mapping[cname]["effects"]:
                    if e:
                        effects.add(e)
        new_skins = sorted(skins)
        new_effects = sorted(effects)
        if new_skins != (p.skin_types or []) or new_effects != (p.skin_concerns or []):
            p.skin_types = new_skins
            p.skin_concerns = new_effects
            p.save(update_fields=["skin_types", "skin_concerns"])
            updated += 1
    print(f"Products updated: {updated}")

def main():
    ingredients = build_unique_ingredients()
    print(f"Found {len(ingredients)} unique ingredients.")
    ensure_template(ingredients)
    mapping = load_mapping()
    apply_mapping(mapping)

if __name__ == "__main__":
    main()
