"""Utility functions for web scraping ingredient data."""
from bs4 import BeautifulSoup
from typing import Optional, Dict


def parse_ingredient_li(li_element) -> Optional[Dict[str, str]]:
    """
    Parse an ingredient from an <li class="ingred-bar"> element.
    
    Args:
        li_element: BeautifulSoup element representing an ingredient list item
    
    Returns:
        Dictionary with 'ingredient', 'function', and 'label' keys, or None
    """
    if not li_element:
        return None
    
    # Try to extract ingredient name
    ingredient = None
    
    # Common patterns for ingredient names in INCI Decoder
    # Look for spans, strong tags, or direct text
    name_elem = (
        li_element.find('span', class_='ingred-name') or
        li_element.find('strong') or
        li_element.find('a')
    )
    
    if name_elem:
        ingredient = name_elem.get_text(strip=True)
    else:
        # Fallback: get first text node
        text = li_element.get_text(strip=True)
        if text:
            # Split on common separators
            parts = text.split('—') or text.split('-') or [text]
            ingredient = parts[0].strip()
    
    if not ingredient:
        return None
    
    # Try to extract function
    function = None
    func_elem = li_element.find('span', class_='ingred-function') or li_element.find('em')
    if func_elem:
        function = func_elem.get_text(strip=True)
    
    # Try to extract label (e.g., "EWG Rating", "Safety")
    label = None
    label_elem = li_element.find('span', class_='ingred-label') or li_element.find('span', class_='label')
    if label_elem:
        label = label_elem.get_text(strip=True)
    
    return {
        "ingredient": ingredient,
        "function": function,
        "label": label,
    }

