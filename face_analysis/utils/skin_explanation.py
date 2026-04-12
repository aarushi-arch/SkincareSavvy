"""Rule-based skin concern explanation generator."""


_CONCERN_DATA = {
    "acne": {
        "title": "Acne",
        "causes": "excess oil production, clogged pores, or hormonal changes",
    },
    "blackheads": {
        "title": "Blackheads",
        "causes": "oxidised sebum in open pores, excess oil, or infrequent cleansing",
    },
    "blackheades": {
        "title": "Blackheads",
        "causes": "oxidised sebum in open pores, excess oil, or infrequent cleansing",
    },
    "dark_spots": {
        "title": "Dark Spots",
        "causes": "sun exposure, post-inflammatory hyperpigmentation, or natural skin pigmentation",
    },
    "darkspots": {
        "title": "Dark Spots",
        "causes": "sun exposure, post-inflammatory hyperpigmentation, or natural skin pigmentation",
    },
    "wrinkles": {
        "title": "Wrinkles",
        "causes": "natural ageing, prolonged sun exposure, or skin dehydration",
    },
    "pores": {
        "title": "Enlarged Pores",
        "causes": "excess sebum, reduced skin elasticity, or sun damage",
    },
}


def generate_skin_explanation(label: str, confidence: float) -> dict:
    """
    Return a structured explanation dict for a detected skin concern.

    Args:
        label:      YOLO / CNN class label string
        confidence: float 0–1  (or 0–100 int — both handled)

    Returns:
        {
            "title":      str,
            "confidence": int   (0–100),
            "tone":       str   ("high" | "moderate" | "low"),
            "message":    str,
        }
    """
    # Normalise confidence to 0–100
    if confidence > 1:
        confidence_pct = round(confidence)
        confidence_frac = confidence / 100
    else:
        confidence_frac = confidence
        confidence_pct = round(confidence * 100)

    if confidence_frac >= 0.75:
        tone = "high"
    elif confidence_frac >= 0.50:
        tone = "moderate"
    else:
        tone = "low"

    key = label.replace(" ", "_").lower()
    concern = _CONCERN_DATA.get(key, {
        "title": label.replace("_", " ").title(),
        "causes": "common skin factors such as environment, lifestyle, or genetics",
    })

    message = (
        f"This looks like {concern['title']} with {tone} confidence ({confidence_pct}%). "
        f"It can sometimes be associated with {concern['causes']}. "
        f"This is an AI-based observation and may not be fully accurate — "
        f"please consult a dermatologist for a professional assessment."
    )

    return {
        "title":      concern["title"],
        "confidence": confidence_pct,
        "tone":       tone,
        "message":    message,
    }
