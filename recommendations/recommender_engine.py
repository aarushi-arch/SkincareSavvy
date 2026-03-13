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
from sklearn.preprocessing import MinMaxScaler


# Use the updated products dataset with engineered features
DATASET_PATH = Path(__file__).resolve().parent / "notebooks" / "updated_products.csv"


@dataclass
class _ModelArtifacts:
    data: pd.DataFrame
    tfidf_matrix: np.ndarray
    cosine_sim_df: pd.DataFrame
    vectorizer: TfidfVectorizer


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

        # Filter out rows with empty product names
        data = data[data["product_name"].notna() & (data["product_name"] != "")]

        if data.empty:
            raise ValueError("Dataset is empty after filtering")

        # Build a richer text signal for TF-IDF: combine brand, type, effects, description, ingredients, skin types
        def _combine_text(row) -> str:
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
                str(row.get("clean_ingreds", "")),
                str(row.get("suitable_skin_types", "")),
            ]
            # Weight notable_effects and product_type slightly by repetition to influence TF-IDF
            return " ".join(parts + [effects_text, effects_text, parts[2]])

        data["combined_text"] = data.apply(_combine_text, axis=1)

        # Initialize a stronger TF-IDF configuration
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
            max_features=5000,
        )

        # Fit and transform the combined_text column
        tfidf_matrix = vectorizer.fit_transform(data["combined_text"].astype(str))

        # Calculate cosine similarity matrix
        cosine_sim = cosine_similarity(tfidf_matrix)

        # Create DataFrame with product names as index and columns
        cosine_sim_df = pd.DataFrame(
            cosine_sim,
            index=data["product_name"],
            columns=data["product_name"],
        )

        return _ModelArtifacts(
            data=data,
            tfidf_matrix=tfidf_matrix,
            cosine_sim_df=cosine_sim_df,
            vectorizer=vectorizer,
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
        
        # Filter out empty strings and return sorted list
        unique_effects = sorted([e for e in all_effects if e])
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
    columns_to_get = ['product_name', 'price', 'product_type']
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


def get_recommendations(user_inputs: Dict, top_k: int = 5) -> List[Dict]:
    """
    Return top-k recommendations based on user inputs.
    This is a compatibility function for the old API.
    """
    artifacts = _load_artifacts()
    data = artifacts.data.copy()
    
    concern = user_inputs.get("main_concern", "").strip()
    if concern:
        # Use combined text vectorizer for richer matching
        concern_vector = artifacts.vectorizer.transform([concern])
        scores = cosine_similarity(concern_vector, artifacts.tfidf_matrix).flatten()
    else:
        scores = np.ones(len(data))
    
    data["score"] = scores
    
    # Filter by skin type using binary columns
    skin_type = user_inputs.get("skin_type", "")
    if skin_type and skin_type in ['Normal', 'Dry', 'Oily', 'Combination', 'Sensitive']:
        data = data[data[skin_type] == 1]
    
    filtered = data.sort_values("score", ascending=False).head(top_k)
    
    recommendations: List[Dict] = []
    for _, row in filtered.iterrows():
        recommendations.append(
            {
                "name": row.get("product_name", ""),
                "brand": row.get("brand", ""),
                "type": row.get("product_type", ""),
                "concern": row.get("notable_effects", ""),
                "price": row.get("price", ""),
                "description": row.get("description", ""),
                "link": row.get("product_href", ""),
            }
        )
    
    return recommendations
