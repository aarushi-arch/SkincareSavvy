"""
Generate fallback descriptions for products with dead URLs or junk descriptions.
"""
import os, re
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
import django; django.setup()

from recommendations.models import Product


def is_junk(desc):
    if not desc: return True
    d = str(desc).strip()
    return d.startswith("[") or d.startswith("'[") or len(d) < 50


def make_description(p):
    name     = p.name or ""
    category = (p.category or "skincare product").lower()
    brand    = p.brand if p.brand and p.brand not in ("Skincare", "") else ""

    size_m = re.search(r"(\d+\s*(?:ml|g|oz))", name, re.I)
    size   = f" ({size_m.group(1)})" if size_m else ""

    brand_str = f"by {brand} " if brand else ""

    return (
        f"{name}{size} is a {category} {brand_str}designed to care for your skin. "
        f"This product is formulated to deliver visible results with consistent use. "
        f"Apply as directed on the packaging for best results."
    )


qs = list(Product.objects.exclude(product_url__isnull=True).exclude(product_url=""))
targets = [p for p in qs if is_junk(p.description)]
print(f"Products to fix: {len(targets)}")

updated = 0
for p in targets:
    p.description = make_description(p)
    p.save(update_fields=["description"])
    updated += 1

print(f"Updated: {updated}")
