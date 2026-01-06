from recommendations.models import Product

def run():
    print("Starting category assignment...")
    # Fetch products with 'Unknown' category (handling both 'Unknown' and 'unknown' for safety)
    products = Product.objects.filter(category__iexact='Unknown')
    
    count = 0
    updates = {
        "cleanser": 0,
        "moisturizer": 0,
        "sunscreen": 0,
        "treatment": 0,
        "unknown": 0
    }
    
    for p in products:
        # Combine name and description and lowercase
        name_desc = (p.name + " " + (p.description or "")).lower()
        
        # Assign categories based on keywords
        if any(x in name_desc for x in ["cleanser", "face wash", "foam", "gel wash", "wash"]):
            p.category = "cleanser"
            updates["cleanser"] += 1
        elif any(x in name_desc for x in ["moisturizer", "cream", "lotion", "gel", "balm", "butter"]):
            p.category = "moisturizer"
            updates["moisturizer"] += 1
        elif any(x in name_desc for x in ["sunscreen", "spf", "sunblock", "uv"]):
            p.category = "sunscreen"
            updates["sunscreen"] += 1
        elif any(x in name_desc for x in ["serum", "treatment", "spot", "acne", "elixir", "ampoule"]):
            p.category = "treatment"
            updates["treatment"] += 1
        else:
            p.category = "unknown"  # keep unknown if no keywords match
            updates["unknown"] += 1
        
        p.save()
        count += 1
        
    print(f"Category assignment complete. Processed {count} products.")
    for cat, val in updates.items():
        print(f" - {cat.title()}: {val}")

if __name__ == "__main__":
    run()
