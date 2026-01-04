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
    """
    Recommend products based on skin type and concerns.
    Handles 'all' skin type and mapping between CNN labels and DB tags.
    """
    skin_type = (analysis.get("skin_type") or "").strip().lower()
    raw_concerns = [(c or "").strip().lower() for c in (analysis.get("concerns") or []) if c]
    
    # Mapping from CNN labels/common terms to DB tags
    # DB Tags Sample: ['cleansing', 'balancing', 'gentle cleansing', 'foaming', 'exfoliating', 
    # 'brightening', 'healing', 'antioxidant', 'plumping', 'anti-inflammatory', 'anti-acne', 
    # 'moisturizing', 'soothing', 'sun protection', 'anti-aging', 'gentle exfoliating']
    CONCERN_MAP = {
        "acne": ["anti-acne", "cleansing", "balancing"],
        "blackheades": ["cleansing", "exfoliating", "balancing"], # Handling CNN typo
        "blackheads": ["cleansing", "exfoliating", "balancing"],
        "dark_spots": ["brightening", "exfoliating", "antioxidant"],
        "pores": ["cleansing", "balancing", "astringent"],
        "wrinkles": ["anti-aging", "plumping", "moisturizing", "antioxidant"],
        "dryness": ["moisturizing", "hydrating", "humectant", "emollient"],
        "oiliness": ["balancing", "cleansing", "foaming"],
        "sensitive": ["soothing", "gentle cleansing", "anti-inflammatory"],
    }
    
    # Expand concerns based on map
    concerns = set()
    for rc in raw_concerns:
        if rc in CONCERN_MAP:
            concerns.update(CONCERN_MAP[rc])
        else:
            concerns.add(rc)

    qs = Product.objects.all().only("brand", "name", "category", "rating", "skin_types", "skin_concerns", "product_url")
    matched = []
    
    for p in qs:
        # Normalize DB tags
        stypes = [str(s).lower() for s in (p.skin_types or [])]
        sconcs = [str(s).lower() for s in (p.skin_concerns or [])]
        
        # Skin type match
        # Match if user type is in product types OR if product is for "all"
        type_match = False
        if not skin_type:
            type_match = True # No type requested, anything goes? Or keep strict.
        elif skin_type in stypes or "all" in stypes:
            type_match = True
            
        if not type_match:
            continue
            
        # Score based on concerns
        score = 0
        matching_concerns = []
        
        if concerns:
            for c in concerns:
                if c in sconcs:
                    score += 1
                    # Capitalize for display, avoiding "Nan"
                    display_name = c.title() if c != 'nan' else None
                    if display_name and display_name not in matching_concerns:
                        matching_concerns.append(display_name)

        # Generate Match Reason
        if matching_concerns:
            # Sort for consistency
            matching_concerns.sort()
            if len(matching_concerns) > 2:
                 concerns_str = ", ".join(matching_concerns[:-1]) + ", and " + matching_concerns[-1]
            else:
                 concerns_str = " and ".join(matching_concerns)
            
            p.match_reason = f"Targets {concerns_str}"
        elif skin_type and (skin_type in stypes or "all" in stypes):
            p.match_reason = f"Great for {skin_type.title()} skin"
        else:
            p.match_reason = "Expertly selected for you"

        # Add to list with score
        matched.append((score, p))
        
    # Sort by Score (desc), then Rating (desc)
    # Filter out nan ratings for sorting
    matched.sort(key=lambda x: (-x[0], -(float(x[1].rating) if x[1].rating and x[1].rating != 'nan' else 0.0)))
    
    # Return top 20 (or 50 if requested, but let's keep it concise)
    return [m[1] for m in matched[:20]]
