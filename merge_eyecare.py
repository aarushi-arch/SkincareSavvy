import ast, re, shutil
import pandas as pd
from pathlib import Path

DATASET = Path("recommendations/notebooks/updated_products_with_images_npr.csv")
SOURCE  = Path("purplle_eyecare.csv")
BACKUP  = DATASET.with_suffix(".bak.csv")

# Non-skincare keywords to reject
REJECT = ["hair gain", "hair tonic", "livon", "lash oil", "eyebrow oil",
          "eyelash growth", "face wash combo", "routine combo", "combo of"]

def is_eye_care(name):
    n = str(name).lower()
    return not any(r in n for r in REJECT)

def clean_name(name):
    if pd.isna(name): return ""
    s = str(name).strip()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1 \2", s)
    return re.sub(r" {2,}", " ", s).strip()

def clean_ingreds(raw):
    if pd.isna(raw): return "[]"
    s = str(raw).strip()
    try:
        items = ast.literal_eval(s)
        if isinstance(items, list):
            good = [i.strip().lower() for i in items
                    if isinstance(i, str) and 2 < len(i.strip()) < 80
                    and not any(b in i for b in ['"', "assets", "modulepreload", ".js", "tag:", "href"])]
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

# ── Load ──────────────────────────────────────────────────────────────────────
existing = pd.read_csv(DATASET)
new      = pd.read_csv(SOURCE)
print(f"Existing : {len(existing)} rows")
print(f"Raw new  : {len(new)} rows")

# ── Clean ─────────────────────────────────────────────────────────────────────
new["product_name"]        = new["product_name"].apply(clean_name)
new["clean_ingreds"]       = new["clean_ingreds"].apply(clean_ingreds)
new["price"]               = new["price"].apply(clean_price)
new["suitable_skin_types"] = new["suitable_skin_types"].apply(clean_list)
new["notable_effects"]     = new["notable_effects"].apply(clean_list)
new["product_type"]        = "Eye Care"

# Drop non-skincare and blanks
new = new[new["product_name"].apply(is_eye_care)]
new = new[new["product_name"].str.len() > 3]
new = new[new["price"].str.len() > 0]

# ── Deduplicate ───────────────────────────────────────────────────────────────
existing_names = set(existing["product_name"].str.lower().str.strip())
new_deduped = new[~new["product_name"].str.lower().str.strip().isin(existing_names)].copy()
print(f"New unique rows to add: {len(new_deduped)}")

if new_deduped.empty:
    print("Nothing to add.")
else:
    print("\nPreview:")
    print(new_deduped[["product_name","product_type","price","rating",
                        "suitable_skin_types","notable_effects"]].to_string(index=False))

    shutil.copy(DATASET, BACKUP)
    combined = pd.concat([existing, new_deduped], ignore_index=True)
    combined.to_csv(DATASET, index=False)

    eye_count = len(combined[combined["product_type"] == "Eye Care"])
    print(f"\nBackup  → {BACKUP}")
    print(f"Saved   → {DATASET}")
    print(f"Added   : {len(new_deduped)}")
    print(f"Total   : {len(combined)}")
    print(f"Eye Care rows in dataset: {eye_count}")
