"""
Advanced recommendation engine based on the notebook implementation.
Supports content-based, collaborative, and hybrid recommendation methods.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# from sklearn.preprocessing import MinMaxScaler


# Prefer the updated products dataset that includes image URLs when available
DATASET_DIR = Path(__file__).resolve().parent / "notebooks"
DEFAULT_DATASET_NAME = "updated_products_with_images_npr.csv"
FALLBACK_DATASET_NAME = "updated_products.csv"

# Use the image-enabled dataset if it exists, otherwise fall back to the original
DATASET_PATH = (DATASET_DIR / DEFAULT_DATASET_NAME) if (DATASET_DIR / DEFAULT_DATASET_NAME).exists() else (DATASET_DIR / FALLBACK_DATASET_NAME)


# Known active ingredients for skincare - easily extendable
KNOWN_ACTIVE_INGREDIENTS = {
    # Acne/Blemish Control
    "salicylic acid", "benzoyl peroxide", "sulfur", "resorcinol", "adapalene", "tretinoin", "isotretinoin",
    # Anti-Aging
    "retinol", "retinyl palmitate", "retinyl acetate", "retinoic acid", "niacinamide", "vitamin c", "ascorbic acid",
    "vitamin e", "tocopherol", "vitamin a", "hyaluronic acid", "sodium hyaluronate", "peptide", "palmitoyl tripeptide-1",
    "palmitoyl tetrapeptide-7", "acetyl hexapeptide-8", "matrixyl", "argireline",
    # Brightening
    "kojic acid", "azelaic acid", "tranexamic acid", "vitamin c", "ascorbic acid", "niacinamide", "licorice extract",
    "glycyrrhiza glabra", "arbutin", "alpha arbutin",
    # Hydration
    "hyaluronic acid", "sodium hyaluronate", "glycerin", "butylene glycol", "propylene glycol", "urea", "allantoin",
    # Soothing/Calming
    "aloe vera", "chamomile", "calamine", "zinc oxide", "panthenol", "bisabolol", "centella asiatica",
    # Exfoliation
    "glycolic acid", "lactic acid", "mandelic acid", "ahaf", "bha", "pha",
    # Oil Control
    "niacinamide", "zinc pca", "clays", "kaolin", "bentonite",
    # Barrier Repair
    "ceramide", "cholesterol", "fatty acids", "squalane", "shea butter", "jojoba oil",
    # Sun Protection
    "zinc oxide", "titanium dioxide", "avobenzone", "octinoxate", "oxybenzone",
    # Common allergens/irritants to watch for
    "fragrance", "parfum", "alcohol", "ethanol", "isopropanol", "phenoxyethanol", "parabens", "methylparaben",
    "propylparaben", "formaldehyde", "quaternium-15", "diazolidinyl urea", "imidazolidinyl urea", "dmdm hydantoin",
    "essential oils", "lavender oil", "tea tree oil", "peppermint oil", "eucalyptus oil"
}


def extract_active_ingredients(ingredients_text: str) -> List[str]:
    """
    Extract active ingredients from a product's ingredients list.

    Args:
        ingredients_text: String representation of ingredients list or comma-separated string

    Returns:
        List of active ingredients found in the product
    """
    if not ingredients_text or str(ingredients_text).strip() == '':
        return []

    try:
        # Try to parse as Python literal (list)
        if isinstance(ingredients_text, str) and ingredients_text.startswith('['):
            ingredients_list = ast.literal_eval(ingredients_text)
        else:
            # Treat as comma-separated string
            ingredients_list = [ing.strip().strip('\'"') for ing in str(ingredients_text).split(',')]

        if not isinstance(ingredients_list, list):
            return []

        # Convert to lowercase for matching
        ingredients_lower = [str(ing).lower().strip() for ing in ingredients_list if ing]

        # Find matches with known active ingredients
        active_ingredients = []
        for ingredient in ingredients_lower:
            # Check for exact matches or substring matches
            for known_active in KNOWN_ACTIVE_INGREDIENTS:
                if known_active in ingredient or ingredient in known_active:
                    if known_active not in active_ingredients:  # Avoid duplicates
                        active_ingredients.append(known_active)

        return active_ingredients

    except (ValueError, SyntaxError):
        # If parsing fails, return empty list
        return []


def check_allergies(product_ingredients: List[str], user_allergies: List[str]) -> Dict:
    """
    Check if a product contains ingredients that match user allergies.

    Args:
        product_ingredients: List of ingredients in the product
        user_allergies: List of user's known allergies

    Returns:
        Dict with allergy_warning flag and matched_allergens list
    """
    if not user_allergies or not product_ingredients:
        return {"allergy_warning": False, "matched_allergens": []}

    # Convert to lowercase for case-insensitive matching
    product_ing_lower = [str(ing).lower().strip() for ing in product_ingredients]
    user_allergies_lower = [str(allergy).lower().strip() for allergy in user_allergies]

    matched_allergens = []
    for allergy in user_allergies_lower:
        for ingredient in product_ing_lower:
            # Check for substring matches (e.g., "fragrance" matches "fragrance free" or "fragrance" in ingredient)
            if allergy in ingredient or ingredient in allergy:
                if allergy not in matched_allergens:
                    matched_allergens.append(allergy)

    return {
        "allergy_warning": len(matched_allergens) > 0,
        "matched_allergens": matched_allergens
    }


@dataclass
class _ModelArtifacts:
    data: pd.DataFrame
    tfidf_matrix: np.ndarray
    cosine_sim_df: pd.DataFrame
    vectorizer: TfidfVectorizer
    # New fields for weighted ingredients
    tfidf_ingredients: TfidfVectorizer
    tfidf_other: TfidfVectorizer
    tfidf_matrix_ingredients: np.ndarray
    tfidf_matrix_other: np.ndarray
    ingredient_weight: float


@lru_cache(maxsize=1)
def _load_artifacts():
    """
    Load the dataset and build TF-IDF artifacts once (cached).
    """
    try:
        data = pd.read_csv(DATASET_PATH, encoding="utf-8", index_col=None)

        # Ensure required columns exist
        if "product_name" not in data.columns:
            raise ValueError("Dataset must contain 'product_name' column")
        if "notable_effects" not in data.columns:
            raise ValueError("Dataset must contain 'notable_effects' column")

        # Clean base columns
        def _ensure_column(df: pd.DataFrame, name: str) -> pd.Series:
            if name in df.columns:
                return df[name].fillna("")
            return pd.Series([""] * len(df))

        data["notable_effects"] = _ensure_column(data, "notable_effects")
        data["description"] = _ensure_column(data, "description")
        data["clean_ingreds"] = _ensure_column(data, "clean_ingreds")
        data["product_type"] = _ensure_column(data, "product_type")
        data["brand"] = _ensure_column(data, "brand")
        data["suitable_skin_types"] = _ensure_column(data, "suitable_skin_types")
        data["image_url"] = _ensure_column(data, "image_url")
        
        # Ensure rating column exists, fill missing with 0
        if "rating" not in data.columns:
            data["rating"] = 0.0
        else:
            data["rating"] = pd.to_numeric(data["rating"], errors="coerce").fillna(0.0)

        # Filter out rows with empty product names
        data = data[data["product_name"].notna() & (data["product_name"] != "")]

        if data.empty:
            raise ValueError("Dataset is empty after filtering")

        # Build separate text signals for ingredients and other features
        def _combine_other_text(row) -> str:
            effects_val = row.get("notable_effects", "")
            effects_text = (
                " ".join(ast.literal_eval(effects_val))
                if isinstance(effects_val, str) and effects_val.startswith("[")
                else str(effects_val)
            )
            parts = [
                str(row.get("product_name", "")),
                str(row.get("brand", "")),
                str(row.get("product_type", "")),
                effects_text,
                str(row.get("description", "")),
                str(row.get("suitable_skin_types", "")),
            ]
            # Weight notable_effects and product_type slightly by repetition to influence TF-IDF
            return " ".join(parts + [effects_text, effects_text, parts[2]])

        def _get_ingredients_text(row) -> str:
            return str(row.get("clean_ingreds", ""))

        data["other_text"] = data.apply(_combine_other_text, axis=1)
        data["ingredients_text"] = data.apply(_get_ingredients_text, axis=1)

        # Extract active ingredients from the ingredients data
        # This creates a new column with list of active ingredients for each product
        data["active_ingredients"] = data["clean_ingreds"].apply(extract_active_ingredients)

        # Initialize TF-IDF vectorizers for ingredients and other features
        ingredient_weight = 3.0  # Configurable weight for ingredients

        tfidf_ingredients = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
            max_features=5000,
        )

        tfidf_other = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
            max_features=5000,
        )

        # Fit and transform separate corpora
        tfidf_matrix_ingredients = tfidf_ingredients.fit_transform(data["ingredients_text"].astype(str))
        tfidf_matrix_other = tfidf_other.fit_transform(data["other_text"].astype(str))

        # Store separate matrices - we'll combine similarities, not matrices
        # This avoids dimension mismatch issues

        # Calculate cosine similarity matrices separately
        cosine_sim_ingredients = cosine_similarity(tfidf_matrix_ingredients)
        cosine_sim_other = cosine_similarity(tfidf_matrix_other)

        # Combine similarity scores with weighting
        # For product-to-product recommendations, weight ingredient similarity higher
        cosine_sim = (cosine_sim_ingredients * ingredient_weight) + cosine_sim_other

        # Create DataFrame with product names as index and columns
        cosine_sim_df = pd.DataFrame(
            cosine_sim,
            index=data["product_name"],
            columns=data["product_name"],
        )

        # For user queries, we'll compute weighted similarities on-the-fly
        # Store the matrices for that purpose
        tfidf_matrix = tfidf_matrix_other  # Keep for backward compatibility

        return _ModelArtifacts(
            data=data,
            tfidf_matrix=tfidf_matrix,
            cosine_sim_df=cosine_sim_df,
            vectorizer=tfidf_other,  # Keep backward compatibility, use other vectorizer as main
            tfidf_ingredients=tfidf_ingredients,
            tfidf_other=tfidf_other,
            tfidf_matrix_ingredients=tfidf_matrix_ingredients,
            tfidf_matrix_other=tfidf_matrix_other,
            ingredient_weight=ingredient_weight,
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error loading artifacts: {str(e)}")
        raise


def get_unique_product_types() -> List[str]:
    """Get unique product types from the dataset."""
    artifacts = _load_artifacts()
    all_types = sorted(artifacts.data['product_type'].unique().tolist())
    # Only keep the specified categories (case-insensitive match)
    allowed_types = ["cleanser", "moisturiser", "serum", "sunscreen"]
    filtered = [pt for pt in all_types if pt.lower() in allowed_types]
    # Add 'Sunscreen' if it exists in database but not in dataset
    if 'Sunscreen' not in filtered:
        filtered.append('Sunscreen')
    # Replace 'Moisturiser' with 'Moisturizer' for American spelling
    return sorted(['Moisturizer' if pt == 'Moisturiser' else pt for pt in filtered])


def get_filtered_products(
    product_type: Optional[str] = None,
    skin_type: Optional[str] = None,
    notable_effects: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Filter products based on product type, skin type, and notable effects.
    
    Args:
        product_type: Filter by product type (e.g., 'Face Wash', 'Toner')
        skin_type: Filter by skin type ('Normal', 'Dry', 'Oily', 'Combination', 'Sensitive')
        notable_effects: List of notable effects to filter by
    
    Returns:
        Filtered DataFrame
    """
    artifacts = _load_artifacts()
    data = artifacts.data.copy()
    
    # Filter by product type
    if product_type:
        data = data[data['product_type'] == product_type]
    
    # Filter by skin type
    # suitable_skin_types is stored as a string representation of a list like "['Dry', 'Sensitive']"
    # Note: "Normal" skin type might not exist in dataset, so we skip filtering for it
    if skin_type and skin_type != 'Normal' and skin_type in ['Dry', 'Oily', 'Combination', 'Sensitive', 'Acne-prone']:
        def parse_skin_types(x):
            """Parse string representation of list to actual list."""
            if pd.isna(x) or not x or str(x).strip() == '':
                return []
            try:
                # Try to parse as Python literal (list)
                if isinstance(x, str) and x.startswith('['):
                    return ast.literal_eval(x)
                return [x] if isinstance(x, str) else []
            except (ValueError, SyntaxError):
                # If parsing fails, treat as comma-separated string
                return [s.strip().strip("'\"") for s in str(x).split(',')]
        
        # Check if the selected skin type is in the suitable_skin_types list
        if 'suitable_skin_types' in data.columns:
            mask = data['suitable_skin_types'].apply(
                lambda x: skin_type in parse_skin_types(x) if pd.notna(x) else False
            )
            data = data[mask]
    # If skin_type is "Normal" or not in the list, we don't filter by skin type (show all)
    
    # Filter by notable effects
    # notable_effects is stored as a string representation of a list like "['Hydrating', 'Barrier Repair']"
    if notable_effects and len(notable_effects) > 0:
        # Convert notable_effects to list if it's not already
        if isinstance(notable_effects, str):
            notable_effects = [notable_effects]
        
        def parse_notable_effects(x):
            """Parse string representation of list to actual list."""
            if pd.isna(x) or not x or str(x).strip() == '':
                return []
            try:
                # Try to parse as Python literal (list)
                if isinstance(x, str) and x.startswith('['):
                    return ast.literal_eval(x)
                return [x] if isinstance(x, str) else []
            except (ValueError, SyntaxError):
                # If parsing fails, treat as comma-separated string
                return [s.strip().strip("'\"") for s in str(x).split(',')]
        
        # Filter products where any of the selected effects appear in the notable_effects list
        mask = data['notable_effects'].apply(
            lambda x: any(effect in parse_notable_effects(x) for effect in notable_effects) if pd.notna(x) else False
        )
        data = data[mask]
    
    return data


def get_unique_notable_effects(
    product_type: Optional[str] = None,
    skin_type: Optional[str] = None
) -> List[str]:
    """Get unique notable effects from filtered products."""
    try:
        filtered = get_filtered_products(product_type=product_type, skin_type=skin_type)
        
        # Check if filtered DataFrame is empty
        if filtered.empty or 'notable_effects' not in filtered.columns:
            return []
        
        # Parse notable_effects which are stored as string representations of lists
        all_effects = set()
        for effects_str in filtered['notable_effects'].dropna():
            if pd.isna(effects_str) or not effects_str or str(effects_str).strip() == '':
                continue
            try:
                # Try to parse as Python literal (list)
                if isinstance(effects_str, str) and effects_str.startswith('['):
                    effects_list = ast.literal_eval(effects_str)
                    if isinstance(effects_list, list):
                        all_effects.update([str(e).strip() for e in effects_list if str(e).strip()])
                else:
                    # If not a list format, treat as single value
                    all_effects.add(str(effects_str).strip())
            except (ValueError, SyntaxError):
                # If parsing fails, treat as comma-separated string
                effects_list = [s.strip().strip("'\"") for s in str(effects_str).split(',')]
                all_effects.update([e for e in effects_list if e])
        
        # Filter out empty strings and limit to core benefits
        core_benefits = {"Hydrating", "Brightening", "Anti-aging", "Acne Control", "Barrier Repair"}
        unique_effects = sorted([e for e in all_effects if e and e in core_benefits])
        return unique_effects
    except Exception as e:
        # Return empty list on any error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_unique_notable_effects: {str(e)}")
        return []


def get_unique_product_names(
    product_type: Optional[str] = None,
    skin_type: Optional[str] = None,
    notable_effects: Optional[List[str]] = None
) -> List[str]:
    """Get unique product names from filtered products."""
    try:
        filtered = get_filtered_products(
            product_type=product_type,
            skin_type=skin_type,
            notable_effects=notable_effects
        )
        
        # Check if filtered DataFrame is empty or column doesn't exist
        if filtered.empty or 'product_name' not in filtered.columns:
            return []
        
        return sorted(filtered['product_name'].unique().tolist())
    except Exception as e:
        # Return empty list on any error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_unique_product_names: {str(e)}")
        return []


def skincare_recommendations(
    product_name: str,
    top_k: int = 5
) -> pd.DataFrame:
    """
    Get skincare product recommendations based on a selected product.
    
    This function uses cosine similarity to find products similar to the selected one.
    Matches the Streamlit implementation logic.
    
    Args:
        product_name: Name of the product to get recommendations for
        top_k: Number of recommendations to return
    
    Returns:
        DataFrame with recommended products including product_name, product_href, price, description
    """
    artifacts = _load_artifacts()
    
    # Check if product exists in the similarity matrix
    if product_name not in artifacts.cosine_sim_df.columns:
        # Return empty DataFrame if product not found
        return pd.DataFrame(columns=['product_name', 'product_href', 'price', 'description', 'product_type', 'similarity_score'])
    
    # Get the similarity scores for the selected product (matching Streamlit logic)
    similarity_scores_series = artifacts.cosine_sim_df.loc[:, product_name]
    similarity_scores = similarity_scores_series.to_numpy()
    
    # Using argpartition to get top k+1 products (top_k + the selected product itself)
    # Range(-1, -k, -1) means we want the top k+1 items
    index = similarity_scores.argpartition(range(-1, -(top_k + 1), -1))
    
    # Get the closest products (top k+1, excluding the selected product)
    closest = artifacts.cosine_sim_df.columns[index[-(top_k + 1):]]
    
    # Drop the selected product from the list
    closest = closest.drop(product_name, errors='ignore')
    
    # Get similarity scores for the closest products
    closest_similarity_scores = similarity_scores_series[closest]
    
    # Get product details for the recommendations
    # Use product_url instead of product_href based on the actual dataset structure
    columns_to_get = ['product_name', 'price', 'product_type', 'image_url']
    if 'product_href' in artifacts.data.columns:
        columns_to_get.append('product_href')
    elif 'product_url' in artifacts.data.columns:
        columns_to_get.append('product_url')
    if 'description' in artifacts.data.columns:
        columns_to_get.append('description')
    elif 'clean_ingreds' in artifacts.data.columns:
        # Use clean_ingreds as description if description doesn't exist
        columns_to_get.append('clean_ingreds')
    
    items = artifacts.data[columns_to_get].copy()
    
    # Rename columns for consistency
    if 'product_url' in items.columns and 'product_href' not in items.columns:
        items = items.rename(columns={'product_url': 'product_href'})
    if 'clean_ingreds' in items.columns and 'description' not in items.columns:
        items = items.rename(columns={'clean_ingreds': 'description'})
    
    # Merge with items to get full product information
    recommendations_df = items[items['product_name'].isin(closest)].copy()
    
    # Add similarity scores to the recommendations
    # Create a mapping of product names to similarity scores
    similarity_dict = closest_similarity_scores.to_dict()
    
    # Add similarity_score column
    recommendations_df['similarity_score'] = recommendations_df['product_name'].map(similarity_dict)
    
    # Sort by similarity score (descending) to ensure best matches are first
    recommendations_df = recommendations_df.sort_values('similarity_score', ascending=False)
    
    # Limit to top_k after sorting
    recommendations_df = recommendations_df.head(top_k)
    
    return recommendations_df


def get_recommendations(user_inputs: Dict, top_k: int = 5, ingredient_weight: float = 3.0) -> List[Dict]:
    """
    Return top-k recommendations based on user inputs.
    This is a compatibility function for the old API.
    Now supports weighted ingredients with configurable weight.
    Filters notable_effects to show only those relevant to the concern.
    """
    artifacts = _load_artifacts()
    data = artifacts.data.copy()
    
    concern = user_inputs.get("main_concern", "").strip()  # Backward compatibility
    concerns = user_inputs.get("concerns", [])
    if isinstance(concerns, str):
        concerns = [concerns] if concerns else []
    elif not isinstance(concerns, list):
        concerns = []
    
    # If concerns list is provided, use it; otherwise fall back to main_concern
    if concerns:
        concern_text = " ".join(concerns)
    else:
        concern_text = concern
    
    ingredients_input = user_inputs.get("ingredients", "").strip()  # New: support for ingredient input
    
    # Map concerns to related beneficial effects (using actual dataset effect names)
    concern_to_effects = {
        "acne": ["Acne Control", "Exfoliating"],
        "wrinkles": ["Anti-aging"],
        "pores": ["Acne Control", "Exfoliating"],  # Pores often relate to acne/exfoliation
        "darkspots": ["Brightening"],
        "blackheads": ["Acne Control", "Exfoliating"],
        "dark_spots": ["Brightening"],
    }
    
    # Get relevant effects for all concerns
    relevant_effects = []
    for c in concerns:
        relevant_effects.extend(concern_to_effects.get(c.lower() if c else "", []))
    # Remove duplicates
    relevant_effects = list(set(relevant_effects))
    
    if concern_text or ingredients_input:
        # Create separate vectors for ingredients and other features
        if ingredients_input:
            ingredients_vector = artifacts.tfidf_ingredients.transform([ingredients_input])
            # Compute similarity scores for ingredients
            ingredients_scores = cosine_similarity(ingredients_vector, artifacts.tfidf_matrix_ingredients).flatten()
        else:
            # If no ingredients provided, use zero scores
            ingredients_scores = np.zeros(len(data))
        
        if concern_text:
            other_vector = artifacts.tfidf_other.transform([concern_text])
            # Compute similarity scores for other features
            other_scores = cosine_similarity(other_vector, artifacts.tfidf_matrix_other).flatten()
        else:
            # If no concern provided, use zero scores
            other_scores = np.zeros(len(data))
        
        # Combine similarity scores with weighting
        scores = (ingredients_scores * ingredient_weight) + other_scores
    else:
        scores = np.ones(len(data))
    
    data["score"] = scores
    
    # Filter by skin type using suitable_skin_types column
    skin_type = user_inputs.get("skin_type", "")
    if skin_type and skin_type != 'Normal' and skin_type in ['Dry', 'Oily', 'Combination', 'Sensitive', 'Acne-prone']:
        def parse_skin_types(x):
            """Parse string representation of list to actual list."""
            if pd.isna(x) or not x or str(x).strip() == '':
                return []
            try:
                # Try to parse as Python literal (list)
                if isinstance(x, str) and x.startswith('['):
                    return ast.literal_eval(x)
                return [x] if isinstance(x, str) else []
            except (ValueError, SyntaxError):
                # If parsing fails, treat as comma-separated string
                return [s.strip().strip("'\"") for s in str(x).split(',')]
        
        # Check if the selected skin type is in the suitable_skin_types list
        if 'suitable_skin_types' in data.columns:
            mask = data['suitable_skin_types'].apply(
                lambda x: skin_type in parse_skin_types(x) if pd.notna(x) else False
            )
            data = data[mask]
    
    # Filter by relevant effects if concerns are specified
    if relevant_effects:
        def has_relevant_effect(effects_str):
            """Check if product has any of the relevant effects."""
            if pd.isna(effects_str) or not effects_str:
                return False
            try:
                if isinstance(effects_str, str) and effects_str.startswith('['):
                    effects = ast.literal_eval(effects_str)
                else:
                    effects = [effects_str]
                
                # Check if any product effect matches any relevant effect
                for product_effect in effects:
                    for relevant in relevant_effects:
                        if str(product_effect).lower() == relevant.lower():
                            return True
                return False
            except:
                return False
        
        # Only keep products that have at least one relevant effect
        mask = data['notable_effects'].apply(has_relevant_effect)
        data = data[mask]

    # Exclude products containing user's allergens
    user_allergies = user_inputs.get("allergies", [])
    if user_allergies:
        def contains_allergen(ingreds_raw):
            if pd.isna(ingreds_raw) or not ingreds_raw:
                return False
            try:
                if isinstance(ingreds_raw, str) and ingreds_raw.startswith('['):
                    ingreds = ast.literal_eval(ingreds_raw)
                else:
                    ingreds = [i.strip() for i in str(ingreds_raw).split(',')]
                ingreds_lower = [str(i).lower().strip() for i in ingreds if i]
            except Exception:
                ingreds_lower = [str(ingreds_raw).lower()]

            for allergen in user_allergies:
                allergen_l = allergen.lower().strip()
                for ing in ingreds_lower:
                    if allergen_l in ing or ing in allergen_l:
                        return True
            return False

        allergen_mask = ~data['clean_ingreds'].apply(contains_allergen)
        data = data[allergen_mask]

    filtered = data.sort_values("score", ascending=False).head(top_k)
    
    recommendations: List[Dict] = []
    for _, row in filtered.iterrows():
        # Get active ingredients for this product
        active_ingredients = row.get("active_ingredients", [])
        
        # Check for allergies if user provided allergy information
        user_allergies = user_inputs.get("allergies", [])
        allergy_info = {"allergy_warning": False, "matched_allergens": []}
        if user_allergies:
            # Check both active ingredients and full ingredients list for allergies
            product_ingredients = []
            if active_ingredients:
                product_ingredients.extend(active_ingredients)
            
            # Also check the full ingredients list for allergens
            clean_ingreds = row.get("clean_ingreds", "")
            if clean_ingreds:
                try:
                    if isinstance(clean_ingreds, str) and clean_ingreds.startswith('['):
                        full_ingredients = ast.literal_eval(clean_ingreds)
                    else:
                        full_ingredients = [ing.strip().strip('\'"') for ing in str(clean_ingreds).split(',')]
                    product_ingredients.extend([str(ing).lower().strip() for ing in full_ingredients if ing])
                except:
                    pass
            
            allergy_info = check_allergies(product_ingredients, user_allergies)
        
        # Parse notable_effects and filter based on concern
        notable_effects = row.get("notable_effects", "")
        all_effects = []
        if notable_effects:
            try:
                if isinstance(notable_effects, str) and notable_effects.startswith('['):
                    all_effects = ast.literal_eval(notable_effects)
                else:
                    all_effects = [notable_effects]
            except:
                all_effects = [notable_effects]
        
        # Filter effects to show only those relevant to the concern
        effects_list = []
        if relevant_effects:
            for effect in all_effects:
                effect_lower = str(effect).lower()
                # Check if effect matches any of the relevant effects for this concern
                for relevant in relevant_effects:
                    if relevant.lower() in effect_lower or effect_lower in relevant.lower():
                        effects_list.append(effect)
                        break
            # If no relevant effects found, show the top ones
            if not effects_list and all_effects:
                effects_list = all_effects[:2] if len(all_effects) > 2 else all_effects
        else:
            # If no concern specified, show all effects
            effects_list = all_effects[:2] if len(all_effects) > 2 else all_effects
        
        recommendations.append(
            {
                "name": row.get("product_name", ""),
                "brand": row.get("brand", ""),
                "type": row.get("product_type", ""),
                "concern": effects_list,
                "price": row.get("price", ""),
                "description": row.get("description", ""),
                "ingredients": row.get("clean_ingreds", ""),
                "active_ingredients": active_ingredients,
                "image_url": row.get("image_url", ""),
                "link": row.get("product_href", ""),
                "rating": row.get("rating", None),
                "score": float(row.get("score", 0)),
                **allergy_info  # Include allergy warning info
            }
        )
    
    return recommendations


def recommend_products(user_input: str, ingredient_weight: float = 3.0, top_k: int = 5, user_allergies: Optional[List[str]] = None) -> List[Dict]:
    """
    Recommend products based on user input text, with ingredients having higher weight.
    
    This function processes user input to extract both ingredient-related and general
    skincare concerns, then applies weighted TF-IDF similarity matching.
    
    Args:
        user_input: User's description of desired skincare product/ingredients/concerns
        ingredient_weight: Weight multiplier for ingredient similarity (default 3.0)
        top_k: Number of recommendations to return
        user_allergies: List of user's known allergies for warning system
    
    Returns:
        List of recommended products with their details, active ingredients, and allergy warnings
    """
    artifacts = _load_artifacts()
    data = artifacts.data.copy()
    
    # Simple heuristic: assume any comma-separated items might be ingredients
    # In a more sophisticated implementation, you could use NLP to classify input
    input_parts = [part.strip() for part in user_input.split(',') if part.strip()]
    
    # For now, treat the entire input as "other" features (concerns, benefits, etc.)
    # and assume no specific ingredients unless explicitly mentioned
    # This can be enhanced with better ingredient detection
    ingredients_input = ""
    other_input = user_input
    
    # Map concerns to related beneficial effects
    concern_to_effects = {
        "acne": ["acne control", "oil control", "pore cleansing"],
        "wrinkles": ["anti-aging", "firming", "elasticity"],
        "pores": ["pore minimizing", "mattifying", "texture refinement"],
        "darkspots": ["brightening", "dark spot correction", "evening skin tone"],
        "blackheads": ["blackhead removal", "deep cleansing", "pore cleansing"],
        "dark_spots": ["brightening", "dark spot correction", "evening skin tone"],
    }
    
    # Try to extract concern from user input
    user_concern = ""
    for concern_key in concern_to_effects.keys():
        if concern_key.lower() in other_input.lower():
            user_concern = concern_key
            break
    
    relevant_effects = concern_to_effects.get(user_concern.lower() if user_concern else "", [])
    
    # Create separate vectors for ingredients and other features
    if ingredients_input:
        ingredients_vector = artifacts.tfidf_ingredients.transform([ingredients_input])
        # Compute similarity scores for ingredients
        ingredients_scores = cosine_similarity(ingredients_vector, artifacts.tfidf_matrix_ingredients).flatten()
    else:
        # If no ingredients provided, use zero scores
        ingredients_scores = np.zeros(len(data))
    
    if other_input:
        other_vector = artifacts.tfidf_other.transform([other_input])
        # Compute similarity scores for other features
        other_scores = cosine_similarity(other_vector, artifacts.tfidf_matrix_other).flatten()
    else:
        # If no other input provided, use zero scores
        other_scores = np.zeros(len(data))
    
    # Combine similarity scores with weighting: ingredients get higher weight
    scores = (ingredients_scores * ingredient_weight) + other_scores
    
    data["score"] = scores
    
    filtered = data.sort_values("score", ascending=False).head(top_k)
    
    recommendations: List[Dict] = []
    for _, row in filtered.iterrows():
        # Get active ingredients for this product
        active_ingredients = row.get("active_ingredients", [])
        
        # Check for allergies if user provided allergy information
        allergy_info = {"allergy_warning": False, "matched_allergens": []}
        if user_allergies:
            # Check both active ingredients and full ingredients list for allergies
            product_ingredients = []
            if active_ingredients:
                product_ingredients.extend(active_ingredients)
            
            # Also check the full ingredients list for allergens
            clean_ingreds = row.get("clean_ingreds", "")
            if clean_ingreds:
                try:
                    if isinstance(clean_ingreds, str) and clean_ingreds.startswith('['):
                        full_ingredients = ast.literal_eval(clean_ingreds)
                    else:
                        full_ingredients = [ing.strip().strip('\'"') for ing in str(clean_ingreds).split(',')]
                    product_ingredients.extend([str(ing).lower().strip() for ing in full_ingredients if ing])
                except:
                    pass
            
            allergy_info = check_allergies(product_ingredients, user_allergies)
        
        # Parse notable_effects and filter based on concern
        notable_effects = row.get("notable_effects", "")
        all_effects = []
        if notable_effects:
            try:
                if isinstance(notable_effects, str) and notable_effects.startswith('['):
                    all_effects = ast.literal_eval(notable_effects)
                else:
                    all_effects = [notable_effects]
            except:
                all_effects = [notable_effects]
        
        # Filter effects to show only those relevant to the concern
        effects_list = []
        if relevant_effects:
            for effect in all_effects:
                effect_lower = str(effect).lower()
                # Check if effect matches any of the relevant effects for this concern
                for relevant in relevant_effects:
                    if relevant.lower() in effect_lower or effect_lower in relevant.lower():
                        effects_list.append(effect)
                        break
            # If no relevant effects found, show the top ones
            if not effects_list and all_effects:
                effects_list = all_effects[:2] if len(all_effects) > 2 else all_effects
        else:
            # If no concern specified, show all effects
            effects_list = all_effects[:2] if len(all_effects) > 2 else all_effects
        
        recommendations.append(
            {
                "name": row.get("product_name", ""),
                "brand": row.get("brand", ""),
                "type": row.get("product_type", ""),
                "concern": effects_list,
                "price": row.get("price", ""),
                "description": row.get("description", ""),
                "ingredients": row.get("clean_ingreds", ""),
                "active_ingredients": active_ingredients,
                "image_url": row.get("image_url", ""),
                "link": row.get("product_href", ""),
                "rating": row.get("rating", None),
                "score": float(row.get("score", 0)),
                **allergy_info  # Include allergy warning info
            }
        )
    
    return recommendations
