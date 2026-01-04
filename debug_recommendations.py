
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from recommendations.utils import recommend_products
from recommendations.models import Product

def test_recommendation():
    test_cases = [
        {
            "name": "Oily with Acne",
            "analysis": {
                "skin_type": {"predictions": [{"class": "Oily", "confidence": 0.95}]},
                "skin_concerns": {"predictions": [{"class": "acne", "confidence": 0.8}]}
            }
        },
        {
            "name": "Dry with Typo Blackheades",
            "analysis": {
                "skin_type": {"predictions": [{"class": "Dry", "confidence": 0.9}]},
                "skin_concerns": {"predictions": [{"class": "blackheades", "confidence": 0.7}]}
            }
        },
        {
            "name": "Normal with Pores and Wrinkles",
            "analysis": {
                "skin_type": {"predictions": [{"class": "Normal", "confidence": 0.9}]},
                "skin_concerns": {"predictions": [{"class": "pores", "confidence": 0.8}, {"class": "wrinkles", "confidence": 0.7}]}
            }
        }
    ]

    for case in test_cases:
        print(f"\n--- Testing: {case['name']} ---")
        analysis_result = case["analysis"]
        skin_type = ""
        concerns = []
        
        if "skin_type" in analysis_result and "predictions" in analysis_result["skin_type"]:
            preds = analysis_result["skin_type"]["predictions"]
            if preds:
                skin_type = preds[0]["class"]
                
        if "skin_concerns" in analysis_result and "predictions" in analysis_result["skin_concerns"]:
            preds = analysis_result["skin_concerns"]["predictions"]
            concerns = [p["class"] for p in preds]

        print(f"Extracted - Type: {skin_type}, Concerns: {concerns}")

        query = {
            "skin_type": skin_type,
            "concerns": concerns
        }
        
        recommended = recommend_products(query)
        print(f"Found {len(recommended)} products.")
        
        for p in recommended[:3]:
            print(f"- {p.name} (Types: {p.skin_types}, Results: {getattr(p, 'match_reason', 'N/A')})")

if __name__ == "__main__":
    test_recommendation()

if __name__ == "__main__":
    test_recommendation()
