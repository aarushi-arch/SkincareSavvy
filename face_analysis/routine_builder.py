from recommendations.models import Product
import json


def build_routine(clean_data):
    """
    Builds morning & night routine from clean skin data
    """

    skin_type = clean_data["skin_type"]
    skin_concerns = clean_data["skin_concerns"]

    routine = {
        "cleanser": None,
        "treatment": None,
        "moisturizer": None,
        "sunscreen": None,
    }

    # Helper function to get category-appropriate products
    def get_product_for_category(category, skin_type, skin_concerns=None):
        """Fetch a product for a given category."""
        query = Product.objects.filter(category__iexact=category)
        
        # Filter by skin type compatibility if not "Normal"
        if skin_type and skin_type.lower() != "normal":
            # Products with matching skin types
            skin_type_match = []
            for product in query:
                if product.skin_types:
                    # Check if skin_type is in the list
                    types = product.skin_types if isinstance(product.skin_types, list) else json.loads(product.skin_types)
                    if skin_type in types or any(skin_type.lower() in str(t).lower() for t in types):
                        skin_type_match.append(product)
            
            if skin_type_match:
                query = skin_type_match
        
        # If we have skin concerns, prioritize products that address them
        if skin_concerns and isinstance(skin_concerns, list) and len(skin_concerns) > 0 and category == "treatment":
            concern_match = []
            for product in query:
                if product.skin_concerns:
                    concerns = product.skin_concerns if isinstance(product.skin_concerns, list) else json.loads(product.skin_concerns)
                    for concern in skin_concerns:
                        if concern and any(concern.lower() in str(c).lower() for c in concerns):
                            concern_match.append(product)
            
            if concern_match:
                query = concern_match
        
        # Prefer products with images
        products_with_image = [p for p in query if p.image_url]
        if products_with_image:
            return products_with_image[0]
        elif query:
            return list(query)[0] if isinstance(query, list) else query.first()
        return None

    # MORNING
    routine["cleanser"] = get_product_for_category("cleanser", skin_type)
    routine["moisturizer"] = get_product_for_category("moisturizer", skin_type)
    routine["sunscreen"] = get_product_for_category("sunscreen", skin_type)

    # NIGHT
    routine["treatment"] = get_product_for_category("treatment", skin_type, skin_concerns)

    return routine

