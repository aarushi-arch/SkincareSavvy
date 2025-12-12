from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
import pandas as pd

from .forms import RecommendationForm
from .recommender_engine import (
    get_unique_product_types,
    get_unique_notable_effects,
    get_unique_product_names,
    skincare_recommendations,
    get_filtered_products,
)
from .utils import normalize_product_url


def home(request):
    """
    Landing page showing the recommendation form.
    """
    form = RecommendationForm()
    context = {
        "form": form,
        "page_title": "Skincare Product Recommendation Application",  # Updated to English
    }
    return render(request, "recommendations/home.html", context)


def recommend(request):
    """
    Handle the recommendation form and display results.
    Supports both GET (form display) and POST (form submission).
    """
    recommendations_data = []
    form = RecommendationForm()
    error_message = None
    
    if request.method == "POST":
        form = RecommendationForm(request.POST)
        
        if form.is_valid():
            # Get form data
            product_category = form.cleaned_data.get("product_category") or ""
            skin_type = form.cleaned_data.get("skin_type") or ""
            notable_effects = form.cleaned_data.get("notable_effects") or []
            selected_product = form.cleaned_data.get("selected_product") or ""
            
            # If no product is selected, try to find one based on filters
            if not selected_product:
                try:
                    candidate_products = get_unique_product_names(
                        product_type=product_category or None,
                        skin_type=skin_type or None,
                        notable_effects=notable_effects if notable_effects else None,
                    )
                    if candidate_products:
                        # Use the first matching product as the anchor for recommendations
                        selected_product = candidate_products[0]
                except Exception as e:
                    error_message = f"Error finding products: {str(e)}"
                    selected_product = ""
            
            # Get recommendations based on selected product
            if selected_product:
                try:
                    recommendations_df = skincare_recommendations(selected_product, top_k=10)
                    
                    # If we have filters, further filter the recommendations to match user preferences
                    if product_category or skin_type or notable_effects:
                        # Get all products matching the filters
                        filtered_products = get_filtered_products(
                            product_type=product_category or None,
                            skin_type=skin_type or None,
                            notable_effects=notable_effects if notable_effects else None
                        )
                        filtered_product_names = set(filtered_products['product_name'].tolist())
                        
                        # Keep only recommendations that match the filters
                        recommendations_df = recommendations_df[
                            recommendations_df['product_name'].isin(filtered_product_names)
                        ]
                    
                    # Convert DataFrame to list of dictionaries
                    for _, row in recommendations_df.iterrows():
                        raw_href = row.get("product_href", "")
                        similarity_score = row.get("similarity_score", 0.0)
                        # Convert similarity score to percentage and round to 2 decimal places
                        similarity_percentage = round(float(similarity_score) * 100, 2) if pd.notna(similarity_score) else 0.0
                        recommendations_data.append({
                            "product_name": row.get("product_name", ""),
                            "product_href": normalize_product_url(raw_href),
                            "price": row.get("price", ""),
                            "description": row.get("description", ""),
                            "similarity_score": similarity_percentage,
                        })
                    
                    # Limit to top 5 recommendations
                    recommendations_data = recommendations_data[:5]
                    
                except Exception as e:
                    error_message = f"Error generating recommendations: {str(e)}"
                    recommendations_data = []
            else:
                error_message = "Please select a product or ensure your filters match available products."
    else:
        form = RecommendationForm()
    
    context = {
        "form": form,
        "recommendations": recommendations_data,
        "error_message": error_message,
        "page_title": "Skincare Product Recommendations",
    }
    return render(request, "recommendations/recommend.html", context)


@require_http_methods(["GET", "POST"])
def get_filtered_options(request):
    """
    AJAX endpoint to get filtered options based on selections.
    Returns JSON with available notable_effects and product_names.
    """
    try:
        if request.method == "POST":
            try:
                data = json.loads(request.body)
            except (json.JSONDecodeError, ValueError):
                data = request.POST
        else:
            data = request.GET
        
        product_category = data.get("product_category", "")
        skin_type = data.get("skin_type", "")
        notable_effects = data.get("notable_effects", [])
        
        if isinstance(notable_effects, str):
            notable_effects = [notable_effects] if notable_effects else []
        
        # Get filtered notable effects
        notable_effects_options = []
        if product_category and skin_type:
            try:
                notable_effects_options = get_unique_notable_effects(
                    product_type=product_category,
                    skin_type=skin_type
                )
            except Exception as e:
                # Log the error but return empty list
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting notable effects: {str(e)}")
                notable_effects_options = []
        
        # Get filtered product names
        product_names = []
        if product_category and skin_type:
            try:
                product_names = get_unique_product_names(
                    product_type=product_category,
                    skin_type=skin_type,
                    notable_effects=notable_effects if notable_effects else None
                )
            except Exception as e:
                # Log the error but return empty list
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting product names: {str(e)}")
                product_names = []
        
        return JsonResponse({
            "notable_effects": notable_effects_options,
            "product_names": product_names,
        })
    except Exception as e:
        # Return error response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_filtered_options: {str(e)}")
        return JsonResponse({
            "error": str(e),
            "notable_effects": [],
            "product_names": [],
        }, status=500)
