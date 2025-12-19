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

ingredient_defaults = {
    "aloe barbadensis leaf extract": {"skin_type": "all", "notable_effects": "soothing, moisturizing"},
    "hyaluronic acid": {"skin_type": "all", "notable_effects": "hydrating, plumping"},
    "shea butter": {"skin_type": "dry", "notable_effects": "moisturizing, emollient"},
    "jojoba oil": {"skin_type": "all", "notable_effects": "moisturizing, balancing"},
    "glycerin": {"skin_type": "all", "notable_effects": "hydrating, humectant"},
    "panthenol": {"skin_type": "all", "notable_effects": "hydrating, soothing"},
    "salicylic acid": {"skin_type": "oily, acne-prone", "notable_effects": "exfoliating, anti-acne"},
    "glycolic acid": {"skin_type": "all", "notable_effects": "exfoliating, brightening"},
    "lactic acid": {"skin_type": "all", "notable_effects": "exfoliating, hydrating"},
    "mandelic acid": {"skin_type": "sensitive, all", "notable_effects": "gentle exfoliating, brightening"},
    "azelaic acid": {"skin_type": "all", "notable_effects": "anti-inflammatory, anti-acne, brightening"},
    "niacinamide": {"skin_type": "all", "notable_effects": "brightening, anti-inflammatory"},
    "vitamin c": {"skin_type": "all", "notable_effects": "brightening, antioxidant"},
    "vitamin e": {"skin_type": "all", "notable_effects": "antioxidant, moisturizing"},
    "retinol": {"skin_type": "all", "notable_effects": "anti-aging, cell turnover"},
    "coenzyme q10": {"skin_type": "all", "notable_effects": "antioxidant, anti-aging"},
    "argania spinosa kernel oil": {"skin_type": "dry", "notable_effects": "moisturizing, antioxidant"},
    "rosehip oil": {"skin_type": "all", "notable_effects": "brightening, anti-aging"},
    "squalane": {"skin_type": "all", "notable_effects": "hydrating, balancing"},
    "coconut oil": {"skin_type": "dry", "notable_effects": "moisturizing, emollient"},
    "benzoyl peroxide": {"skin_type": "oily, acne-prone", "notable_effects": "anti-acne, antibacterial"},
    "tea tree oil": {"skin_type": "oily, acne-prone", "notable_effects": "antibacterial, soothing"},
    "zinc oxide": {"skin_type": "all", "notable_effects": "sun protection, soothing"},
    "titanium dioxide": {"skin_type": "all", "notable_effects": "sun protection, soothing"},
    "caffeine": {"skin_type": "all", "notable_effects": "anti-inflammatory, depuffing"},
    "camellia sinensis leaf extract": {"skin_type": "all", "notable_effects": "antioxidant, soothing"},
    "chamomilla recutita extract": {"skin_type": "sensitive, all", "notable_effects": "soothing, anti-inflammatory"},
    "licorice root extract": {"skin_type": "all", "notable_effects": "brightening, anti-inflammatory"},
    "centella asiatica extract": {"skin_type": "all", "notable_effects": "soothing, healing"},
    "cocamidopropyl betaine": {"skin_type": "all", "notable_effects": "gentle cleansing"},
    "sodium lauryl sulfate": {"skin_type": "oily, all", "notable_effects": "cleansing, foaming"},
    "sodium cocoyl isethionate": {"skin_type": "all", "notable_effects": "gentle cleansing, foaming"},
    "cetyl alcohol": {"skin_type": "all", "notable_effects": "emollient, thickening"},
    "stearyl alcohol": {"skin_type": "all", "notable_effects": "emollient, thickening"},
    "glyceryl stearate": {"skin_type": "all", "notable_effects": "emollient, stabilizing"},
}

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
                defaults = ingredient_defaults.get(ing, {})
                w.writerow([ing, defaults.get("skin_type", ""), defaults.get("notable_effects", "")])
        print(f"Template created: {TEMPLATE_CSV}")
    else:
        updated = 0
        rows = []
        with open(TEMPLATE_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ing = clean_name(row.get("ingredient", ""))
                if ing in ingredient_defaults:
                    if not (row.get("skin_type") or "").strip():
                        row["skin_type"] = ingredient_defaults[ing]["skin_type"]
                        updated += 1
                    if not (row.get("notable_effects") or "").strip():
                        row["notable_effects"] = ingredient_defaults[ing]["notable_effects"]
                        updated += 1
                rows.append(row)
        with open(TEMPLATE_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ingredient", "skin_type", "notable_effects"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"{TEMPLATE_CSV} prefilled defaults for {updated} fields.")

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
