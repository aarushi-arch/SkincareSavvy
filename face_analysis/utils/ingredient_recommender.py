"""
Rule-based ingredient recommendation layer.
Maps detected skin concerns to helpful active ingredients.
"""

_MAPPING: dict[str, list[dict]] = {
    "acne": [
        {"name": "Salicylic Acid",   "why": "Unclogs pores and reduces inflammation"},
        {"name": "Niacinamide",      "why": "Controls sebum and calms redness"},
        {"name": "Benzoyl Peroxide", "why": "Kills acne-causing bacteria"},
        {"name": "Tea Tree Oil",     "why": "Natural antibacterial and anti-inflammatory"},
        {"name": "Azelaic Acid",     "why": "Reduces blemishes and post-acne marks"},
    ],
    "blackheads": [
        {"name": "Salicylic Acid",  "why": "Dissolves the debris that clogs pores"},
        {"name": "Niacinamide",     "why": "Minimises pore appearance"},
        {"name": "Retinol",         "why": "Speeds cell turnover to keep pores clear"},
        {"name": "Glycolic Acid",   "why": "Exfoliates dead skin that leads to blackheads"},
    ],
    "blackheades": [
        {"name": "Salicylic Acid",  "why": "Dissolves the debris that clogs pores"},
        {"name": "Niacinamide",     "why": "Minimises pore appearance"},
        {"name": "Retinol",         "why": "Speeds cell turnover to keep pores clear"},
        {"name": "Glycolic Acid",   "why": "Exfoliates dead skin that leads to blackheads"},
    ],
    "dark_spots": [
        {"name": "Vitamin C",        "why": "Brightens and fades hyperpigmentation"},
        {"name": "Niacinamide",      "why": "Inhibits melanin transfer to skin surface"},
        {"name": "Alpha Arbutin",    "why": "Gently lightens dark spots"},
        {"name": "Kojic Acid",       "why": "Reduces melanin production"},
        {"name": "Licorice Extract", "why": "Natural brightening and anti-inflammatory"},
    ],
    "darkspots": [
        {"name": "Vitamin C",        "why": "Brightens and fades hyperpigmentation"},
        {"name": "Niacinamide",      "why": "Inhibits melanin transfer to skin surface"},
        {"name": "Alpha Arbutin",    "why": "Gently lightens dark spots"},
        {"name": "Kojic Acid",       "why": "Reduces melanin production"},
        {"name": "Licorice Extract", "why": "Natural brightening and anti-inflammatory"},
    ],
    "wrinkles": [
        {"name": "Retinol",          "why": "Stimulates collagen and speeds cell renewal"},
        {"name": "Hyaluronic Acid",  "why": "Deeply hydrates and plumps fine lines"},
        {"name": "Peptides",         "why": "Signal skin to produce more collagen"},
        {"name": "Vitamin E",        "why": "Antioxidant that protects against skin ageing"},
        {"name": "Niacinamide",      "why": "Improves skin elasticity and barrier function"},
    ],
    "pores": [
        {"name": "Niacinamide",     "why": "Visibly tightens and minimises pores"},
        {"name": "Salicylic Acid",  "why": "Keeps pores clear of excess sebum"},
        {"name": "Retinol",         "why": "Refines skin texture over time"},
        {"name": "Clay / Kaolin",   "why": "Absorbs oil and temporarily tightens pores"},
    ],
}


def get_ingredients(concern: str) -> list[dict]:
    """Return ingredient list for a concern. Falls back to empty list."""
    return _MAPPING.get(concern.lower().replace(" ", "_"), [])


def get_advice(concern: str) -> dict | None:
    """
    Return a structured advice dict for a concern.

    Returns:
        {
            "concern":     str,
            "ingredients": [{name, why}, ...],
            "text":        str,   # human-readable summary
        }
        or None if concern is unknown.
    """
    ingredients = get_ingredients(concern)
    if not ingredients:
        return None

    names = ", ".join(i["name"] for i in ingredients)
    label = concern.replace("_", " ").title()

    return {
        "concern":     concern,
        "label":       label,
        "ingredients": ingredients,
        "text": (
            f"If you believe this detection is correct, products containing "
            f"{names} may help improve {label}."
        ),
    }
