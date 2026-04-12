"""
Clean purplle_suncare.csv and merge into the main dataset.
"""
import ast, re, shutil
import pandas as pd
from pathlib import Path

DATASET = Path("recommendations/notebooks/updated_products_with_images_npr.csv")
SOURCE  = Path("purplle_suncare.csv")
BACKUP  = DATASET.with_suffix(".bak.csv")

# ── Cleaners ──────────────────────────────────────────────────────────────────

def clean_name(name):
    if pd.isna(name): return ""
    s = str(name).strip()
    # Insert space between camelCase / PascalCase run-ons
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1 \2", s)
    return re.sub(r" {2,}", " ", s).strip()

def clean_ingreds(raw):
    """Wipe JS garbage; keep only real ingredient strings."""
    if pd.isna(raw): return "[]"
    s = str(raw).strip()
    try:
        items = ast.literal_eval(s)
        if isinstance(items, list):
            good = [i.strip().lower() for i in items
                    if isinstance(i, str)
                    and 2 < len(i.strip()) < 80
                    and not any(b in i for b in ['"', "assets", "modulepreload", ".js", "tag:", "href", "rel:"])]
            return str(good)
    except Exception:
        pass
    return "[]"

def clean_price(p):
    if pd.isna(p): return ""
    s = str(p).strip()
    if s.startswith("NPR"): return s
    digits = re.sub(r"[^\d.]", "", s)
    if digits:
        try: return f"NPR {round(float(digits)):,}"
        except ValueError: pass
    return s

def clean_list(val):
    if pd.isna(val) or str(val).strip() in ("", "[]"): return "[]"
    s = str(val).strip()
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return str([str(x).strip() for x in parsed if str(x).strip()])
    except Exception:
        pass
    parts = [x.strip().strip("'\"") for x in s.split(",") if x.strip()]
    return str(parts)

# ── Main ──────────────────────────────────────────────────────────────────────

existing = pd.read_csv(DATASET)
new      = pd.read_csv(SOURCE)

print(f"Existing dataset : {len(existing)} rows")
print(f"Suncare raw      : {len(new)} rows")

# Clean
new["product_name"]        = new["product_name"].apply(clean_name)
new["clean_ingreds"]       = new["clean_ingreds"].apply(clean_ingreds)
new["price"]               = new["price"].apply(clean_price)
new["suitable_skin_types"] = new["suitable_skin_types"].apply(clean_list)
new["notable_effects"]     = new["notable_effects"].apply(clean_list)
new["product_type"]        = "Sunscreen"

# Drop blanks
new = new[new["product_name"].str.len() > 3]
new = new[new["price"].str.len() > 0]

# Deduplicate
existing_names = set(existing["product_name"].str.lower().str.strip())
new_deduped = new[~new["product_name"].str.lower().str.strip().isin(existing_names)].copy()

print(f"New unique rows  : {len(new_deduped)}")

if new_deduped.empty:
    print("Nothing to add.")
else:
    print("\nPreview:")
    print(new_deduped[["product_name","product_type","price","rating",
                        "suitable_skin_types","notable_effects"]].to_string(index=False))

    # Backup + save
    shutil.copy(DATASET, BACKUP)
    combined = pd.concat([existing, new_deduped], ignore_index=True)
    combined.to_csv(DATASET, index=False)

    print(f"\nBackup  → {BACKUP}")
    print(f"Saved   → {DATASET}")
    print(f"Old count : {len(existing)}")
    print(f"Added     : {len(new_deduped)}")
    print(f"New total : {len(combined)}")
    print(f"\nSunscreen rows now: {len(combined[combined['product_type']=='Sunscreen'])}")
