def normalize_analysis(raw_result):
    """
    Takes raw AI output and returns clean data
    """

    # Take the highest confidence skin type
    skin_type = raw_result["skin_type"][0]["class"]

    # Keep only strong skin concerns
    skin_concerns = [
        c["class"]
        for c in raw_result["skin_concerns"]
        if c["confidence"] >= 0.6
    ]

    return {
        "skin_type": skin_type,
        "skin_concerns": skin_concerns
    }
