from django import forms
from .recommender_engine import (
    get_unique_product_types,
    get_unique_notable_effects,
    get_unique_product_names,
)


class RecommendationForm(forms.Form):
    """
    Form for skincare product recommendations matching the Streamlit application.
    """
    
    SKIN_TYPES = [
        ("", "Select skin type"),
        ("Normal", "Normal"),
        ("Dry", "Dry"),
        ("Oily", "Oily"),
        ("Combination", "Combination"),
        ("Sensitive", "Sensitive"),
    ]
    
    # Skin problems/concerns (internal values match dataset; labels are in English)
    SKIN_PROBLEMS = [
        # Selecting 5 main important options as requested
        ("Jerawat", "Acne"),
        ("Flek Hitam", "Dark Spots"),
        ("Garis Halus dan Kerutan", "Fine Lines and Wrinkles"),
        ("Pori-pori Besar", "Large Pores"),
        ("Kemerahan", "Redness"),
    ]
    
    # Product category
    product_category = forms.ChoiceField(
        label="Product Category",
        choices=[("", "Select category")] + [(pt, pt) for pt in get_unique_product_types()],
        required=True,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    
    # Skin type
    skin_type = forms.ChoiceField(
        label="Your Skin Type",
        choices=SKIN_TYPES,
        required=True,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    
    # Skin problems (single select)
    skin_problems = forms.ChoiceField(
        label="Your Skin Concerns",
        choices=SKIN_PROBLEMS,
        required=False,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"})
    )
    
    # Notable effects (will be populated dynamically)
    notable_effects = forms.ChoiceField(
        label="Desired Benefits",
        choices=[],
        required=False,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"})
    )
    
    # Product selection (will be populated dynamically)
    selected_product = forms.ChoiceField(
        label="Recommended Product for You",
        choices=[("", "Select a product")],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Try to populate dynamic fields if POST data exists
        if args:
            from django.http import QueryDict
            if isinstance(args[0], (QueryDict, dict)):
                data = args[0]
                product_category = data.get('product_category', '')
                skin_type = data.get('skin_type', '')
                
                # Update notable effects choices
                if product_category and skin_type:
                    try:
                        notable_effects = get_unique_notable_effects(
                            product_type=product_category,
                            skin_type=skin_type
                        )
                        self.fields['notable_effects'].choices = [(ne, ne) for ne in notable_effects]
                        
                        # Update product choices based on selected notable effects
                        notable_effects_list = []
                        if hasattr(data, 'getlist'):
                            notable_effects_list = data.getlist('notable_effects', [])
                        elif isinstance(data, dict):
                            notable_effects_list = data.get('notable_effects', [])
                            if isinstance(notable_effects_list, str):
                                notable_effects_list = [notable_effects_list]
                        
                        products = get_unique_product_names(
                            product_type=product_category,
                            skin_type=skin_type,
                            notable_effects=notable_effects_list if notable_effects_list else None
                        )
                        self.fields['selected_product'].choices = [("", "Select a product")] + [(p, p) for p in products]
                    except Exception as e:
                        # If there's an error, keep default empty choices
                        # Dynamic updates will be handled by JavaScript
                        pass
