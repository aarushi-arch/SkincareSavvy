"""
Cleans purplle_moisturizers.csv and merges it into the main dataset.

What it fixes:
  - clean_ingreds: strips JS bundle garbage, keeps only real ingredient strings
  - product_name:  strips brand prefix run-ons (e.g. "DERMDOCby Purplle...")
  - Deduplicates against existing dataset by product_name
  - Appends cleaned rows to updated_products_with_images_npr.csv
"""

import ast
import re
import pandas as pd
from pathlib import Path

DATASET = Path("recommendations/notebooks/updated_products_with_images_npr.csv")
PURPLLE = Path("purplle_moisturizers.csv")
BACKUP  = DATASET.with_suffix(".bak.csv")

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_real_ingredient(s: str) -> bool:
    """Return True if the string looks like a cosmetic ingredient, not JS code."""
    s = s.strip()
    if len(s) < 3 or len(s) > 80:
        return False
    # Reject strings that look like JS / JSON / HTML
    bad = ['"', "'", "{", "}", "[", "]", "=>", "://", "modulepreload",
           "assets", "rel:", "href", "tag:", "key:", "attrs", ".js", ".css",
           "function", "return", "const ", "var ", "let ", "import"]
    for b in bad:
        if b in s:
            return False
    # Must contain at least one letter
    if not re.search(r"[a-zA-Z]", s):
        return False
    return True


def clean_ingreds(raw) -> str:
    """
    Parse the clean_ingreds cell and return a clean Python list string.
    Handles:
      - Already-clean list strings: "['glycerin', 'niacinamide']"
      - JS-garbage lists scraped from __INITIAL_STATE__
      - Empty / NaN
    """
    if pd.isna(raw) or str(raw).strip() in ("", "[]", "['']"):
        return "[]"

    raw_str = str(raw).strip()

    # Try to parse as a Python list
    try:
        items = ast.literal_eval(raw_str)
        if isinstance(items, list):
            clean = [i.strip().lower() for i in items if is_real_ingredient(str(i))]
            return str(clean)
    except (ValueError, SyntaxError):
        pass

    # Fallback: treat as comma-separated text
    parts = re.split(r"[,;]", raw_str)
    clean = [p.strip().lower() for p in parts if is_real_ingredient(p)]
    return str(clean)


def clean_name(name: str) -> str:
    """Fix run-on brand+name strings like 'DERMDOCby Purplle 10% ...'"""
    if pd.isna(name):
        return ""
    name = str(name).strip()
    # Insert space where a lowercase letter immediately follows an uppercase block
    # e.g. "DERMDOCby" → "DERMDOC by", "PondsSuper" → "Ponds Super"
    name = re.sub(r"([A-Za-z])([A-Z][a-z])", r"\1 \2", name)
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    # Collapse multiple spaces
    name = re.sub(r" {2,}", " ", name)
    return name.strip()


def clean_price(price) -> str:
    """Ensure price is in 'NPR X,XXX' format."""
    if pd.isna(price):
        return ""
    p = str(price).strip()
    if p.startswith("NPR"):
        return p
    digits = re.sub(r"[^\d.]", "", p)
    if digits:
        try:
            return f"NPR {round(float(digits)):,}"
        except ValueError:
            pass
    return p


def clean_list_col(val) -> str:
    """Ensure suitable_skin_types / notable_effects are valid list strings."""
    if pd.isna(val) or str(val).strip() in ("", "[]"):
        return "[]"
    s = str(val).strip()
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return str([str(x).strip() for x in parsed if str(x).strip()])
    except (ValueError, SyntaxError):
        pass
    # Comma-separated fallback
    parts = [x.strip().strip("'\"") for x in s.split(",") if x.strip()]
    return str(parts)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading datasets …")
    existing = pd.read_csv(DATASET)
    purplle  = pd.read_csv(PURPLLE)

    print(f"  Existing dataset : {len(existing)} rows")
    print(f"  Purplle raw      : {len(purplle)} rows")

    # ── Clean Purplle data ────────────────────────────────────────────────────
    print("\nCleaning Purplle data …")

    purplle["product_name"]        = purplle["product_name"].apply(clean_name)
    purplle["clean_ingreds"]       = purplle["clean_ingreds"].apply(clean_ingreds)
    purplle["price"]               = purplle["price"].apply(clean_price)
    purplle["suitable_skin_types"] = purplle["suitable_skin_types"].apply(clean_list_col)
    purplle["notable_effects"]     = purplle["notable_effects"].apply(clean_list_col)
    purplle["product_type"]        = "Moisturiser"

    # Drop rows with empty names or prices
    purplle = purplle[purplle["product_name"].str.len() > 3]
    purplle = purplle[purplle["price"].str.len() > 0]

    # ── Deduplicate against existing ──────────────────────────────────────────
    existing_names = set(existing["product_name"].str.lower().str.strip())
    purplle_deduped = purplle[
        ~purplle["product_name"].str.lower().str.strip().isin(existing_names)
    ].copy()

    print(f"  After dedup      : {len(purplle_deduped)} new rows to add")

    if purplle_deduped.empty:
        print("Nothing new to add — all Purplle products already exist in the dataset.")
        return

    # ── Show sample of what will be added ─────────────────────────────────────
    print("\nSample of new rows:")
    sample_cols = ["product_name", "product_type", "price", "rating",
                   "suitable_skin_types", "notable_effects"]
    print(purplle_deduped[sample_cols].head(10).to_string(index=False))

    # ── Backup + merge ────────────────────────────────────────────────────────
    existing.to_csv(BACKUP, index=False)
    print(f"\nBackup saved → {BACKUP}")

    # Align columns — Purplle has exactly the same columns as the dataset
    combined = pd.concat([existing, purplle_deduped], ignore_index=True)
    combined.to_csv(DATASET, index=False)

    print(f"\nDone.")
    print(f"  Old row count : {len(existing)}")
    print(f"  Added         : {len(purplle_deduped)}")
    print(f"  New total     : {len(combined)}")
    print(f"  Saved → {DATASET}")

    # ── Verify Moisturiser count ──────────────────────────────────────────────
    moisturisers = combined[combined["product_type"] == "Moisturiser"]
    print(f"\n  Moisturiser rows in dataset: {len(moisturisers)}")


if __name__ == "__main__":
    main()
