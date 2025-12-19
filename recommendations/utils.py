"""
Utility helpers for the recommendations app.

If you later add image-based analysis or data loading helpers,
this is a good place to keep that logic.
"""

from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from recommendations.models import Product


def get_data_path(filename: str) -> Path:
    """
    Convenience helper to get the path to a file in recommendations/data.
    """
    return settings.BASE_DIR / "recommendations" / "data" / filename


def normalize_product_url(raw_url: str) -> str:
    """
    Normalize product URLs so links in the UI are valid/clickable.

    - Returns an empty string if the URL looks obviously invalid.
    - Adds ``https://`` if the URL is missing a scheme (e.g. starts with ``www.``).
    - Leaves already well‑formed http/https URLs as-is.
    """
    if not raw_url:
        return ""

    raw_url = raw_url.strip()
    if not raw_url:
        return ""

    parsed = urlparse(raw_url)

    # If there is no scheme but we have a netloc or it starts with www,
    # prepend https:// by default.
    if not parsed.scheme:
        # Common case: "www.example.com/..." stored without scheme
        if raw_url.startswith("www."):
            return f"https://{raw_url}"

        # urlparse without scheme treats "domain.com/path" as path,
        # so add https:// if it looks like a bare domain.
        if "." in raw_url.split("/")[0]:
            return f"https://{raw_url}"

    # Only accept http/https links; otherwise, treat as invalid.
    if parsed.scheme in ("http", "https"):
        return raw_url

    return ""

def recommend_products(analysis: dict):
    skin_type = (analysis.get("skin_type") or "").strip().lower()
    concerns = [(c or "").strip().lower() for c in (analysis.get("concerns") or []) if c]
    qs = Product.objects.all().only("brand", "name", "category", "rating", "skin_types", "skin_concerns")
    matched = []
    for p in qs:
        stypes = [str(s).lower() for s in (p.skin_types or [])]
        sconcs = [str(s).lower() for s in (p.skin_concerns or [])]
        if skin_type and skin_type not in stypes:
            continue
        if any(c not in sconcs for c in concerns):
            continue
        matched.append(p)
    matched.sort(key=lambda x: (-(x.rating or 0), (x.brand or ""), (x.name or "")))
    return matched[:50]
